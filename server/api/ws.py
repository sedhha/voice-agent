"""WebSocket voice endpoint — bidi audio streaming via ADK Live API."""

import asyncio
import json

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

from server.agents import compliance_router
from server.config import settings
from server.session_state import persist_session_value
from server.tools.navigation_tools import nav_queues
from server.tools.suggestion_tools import suggestion_queues

router = APIRouter()
AUTH_TIMEOUT_SECONDS = 5.0


def _is_mostly_latin(text: str) -> bool:
    """Return True if >50% of alphabetic chars are Latin (ASCII/extended).

    Gemini's ASR sometimes transcribes English speech in Devanagari, Arabic,
    or other scripts.  This filter lets us suppress those mis-transcriptions
    while keeping the correctly-heard audio flowing to the model.
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return True  # No alpha chars — let it through (numbers, punctuation)
    latin_count = sum(1 for c in alpha_chars if c.isascii())
    return latin_count / len(alpha_chars) > 0.5

session_service = InMemorySessionService()
runner = Runner(
    app_name=settings.app_name,
    agent=compliance_router,
    session_service=session_service,
)


async def store_user_token(
    *,
    user_id: str,
    session_id: str,
    token_value: str,
) -> bool:
    """Persist the Firebase token in session state for downstream tool calls."""
    return persist_session_value(
        session_service=session_service,
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id,
        key="user_token",
        value=token_value,
    )


async def wait_for_auth(
    *,
    websocket: WebSocket,
    auth_ready: asyncio.Event,
    session_id: str,
    timeout_seconds: float = AUTH_TIMEOUT_SECONDS,
) -> bool:
    """Block the live runner until the client has sent an auth message."""
    try:
        await asyncio.wait_for(auth_ready.wait(), timeout=timeout_seconds)
        return True
    except TimeoutError:
        logger.warning("Voice session %s timed out waiting for auth", session_id)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": "Voice agent authentication timed out. Please try again.",
                }
            )
        )
        await websocket.close(code=4401, reason="Authentication required")
        return False


@router.websocket("/ws/voice/{user_id}/{session_id}")
async def voice_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """Bidirectional audio streaming endpoint.

    Receives PCM 16kHz mono audio from the browser mic,
    sends PCM 24kHz mono audio + text/transcript events back.
    """
    await websocket.accept()

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=settings.voice_name,
                )
            ),
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=100,
                silence_duration_ms=settings.silence_duration_ms,
            ),
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
            turn_coverage=types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        # NOTE: session_resumption and context_window_compression are NOT
        # supported by gemini-2.5-flash-native-audio on Gemini API (1008).
        # They require Vertex AI + gemini-live-* models.
    )

    # Create or resume session
    session = await session_service.get_session(
        app_name=settings.app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=settings.app_name, user_id=user_id, session_id=session_id
        )

    live_queue = LiveRequestQueue()
    auth_ready = asyncio.Event()

    async def upstream():
        """Client audio/text -> LiveRequestQueue -> Gemini."""
        try:
            while True:
                raw = await websocket.receive()
                if "bytes" in raw:
                    audio_blob = types.Blob(
                        mime_type="audio/pcm;rate=16000", data=raw["bytes"]
                    )
                    live_queue.send_realtime(audio_blob)
                elif "text" in raw:
                    msg = json.loads(raw["text"])
                    if msg.get("type") == "auth":
                        # Store Firebase token in session state for CC API calls
                        token_value = str(msg.get("token", "")).strip()
                        stored = await store_user_token(
                            user_id=user_id,
                            session_id=session_id,
                            token_value=token_value,
                        )
                        if stored and token_value:
                            auth_ready.set()
                        logger.info(
                            "Auth token stored for session %s (length=%d, stored=%s)",
                            session_id,
                            len(token_value),
                            stored,
                        )
                    elif msg.get("type") == "text":
                        content = types.Content(
                            parts=[types.Part(text=msg["text"])]
                        )
                        live_queue.send_content(content)
        except WebSocketDisconnect:
            pass

    async def _process_event(event):
        """Handle a single ADK live event — audio, transcription, queues."""
        # Notify the frontend when tools are executing (UI indicator only).
        # NOTE: We do NOT gate audio server-side because ADK manages tool
        # execution internally — get_function_responses() events may never
        # reach us, leaving the gate stuck closed and killing the mic.
        if hasattr(event, "get_function_calls") and event.get_function_calls():
            logger.debug("Tool call detected")
            await websocket.send_text(
                json.dumps({"type": "tool_executing", "active": True})
            )
        if hasattr(event, "get_function_responses") and event.get_function_responses():
            logger.debug("Tool response received")
            await websocket.send_text(
                json.dumps({"type": "tool_executing", "active": False})
            )

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.inline_data and part.inline_data.data:
                    assert part.inline_data.data is not None
                    await websocket.send_bytes(part.inline_data.data)
                elif part.text:
                    await websocket.send_text(
                        json.dumps({"type": "text", "text": part.text})
                    )

        if hasattr(event, "input_transcription") and event.input_transcription:
            transcript_text = event.input_transcription.text or ""
            # Gemini's ASR sometimes transcribes English speech in Devanagari
            # or other non-Latin scripts.  Filter those out — the audio itself
            # is still processed correctly by the model; this only affects the
            # display transcript sent to the frontend.
            if transcript_text and _is_mostly_latin(transcript_text):
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "input_transcript",
                            "text": transcript_text,
                        }
                    )
                )
        if hasattr(event, "output_transcription") and event.output_transcription:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "output_transcript",
                        "text": event.output_transcription.text,
                    }
                )
            )

        # Drain navigation/suggestion queues BEFORE turn_complete
        # so the frontend receives them while the agent bubble is
        # still active (not yet sealed).
        queue = nav_queues.get(session_id)
        if queue:
            while not queue.empty():
                cmd = queue.get_nowait()
                await websocket.send_text(json.dumps(cmd))

        sug_queue = suggestion_queues.get(session_id)
        if sug_queue:
            while not sug_queue.empty():
                sug = sug_queue.get_nowait()
                await websocket.send_text(json.dumps(sug))

        # Signal turn boundary AFTER queued payloads.
        if getattr(event, "turn_complete", False):
            await websocket.send_text(
                json.dumps({"type": "turn_complete"})
            )
        if getattr(event, "interrupted", False):
            await websocket.send_text(
                json.dumps({"type": "turn_complete", "interrupted": True})
            )

    MAX_RETRIES = 2

    async def downstream():
        """Gemini responses -> WebSocket -> Client speakers.

        Retries on transient 1011 errors (known Gemini server-side bug
        during tool execution). On final failure, notifies the frontend
        and closes the WebSocket so it can reconnect cleanly.
        """
        if not await wait_for_auth(
            websocket=websocket,
            auth_ready=auth_ready,
            session_id=session_id,
        ):
            return

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(
                    "Starting run_live for session %s (attempt %d)",
                    session_id, attempt + 1,
                )
                async for event in runner.run_live(
                    user_id=user_id,
                    session_id=session_id,
                    live_request_queue=live_queue,
                    run_config=run_config,
                ):
                    await _process_event(event)
                return  # Clean exit
            except Exception as e:
                err_str = str(e)
                is_transient = "1011" in err_str or "1008" in err_str
                if is_transient and attempt < MAX_RETRIES:
                    logger.warning(
                        "Transient Gemini error (attempt %d/%d): %s",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        err_str[:120],
                    )
                    await asyncio.sleep(1)
                    continue
                logger.exception("run_live error (final): %s", e)
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Voice connection interrupted. Please reconnect.",
                            }
                        )
                    )
                    await websocket.close(
                        code=1011, reason="Gemini connection lost"
                    )
                except Exception:
                    pass
                return

    try:
        await asyncio.gather(upstream(), downstream(), return_exceptions=True)
    finally:
        live_queue.close()
        nav_queues.pop(session_id, None)
        suggestion_queues.pop(session_id, None)

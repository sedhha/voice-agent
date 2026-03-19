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
HEARTBEAT_INTERVAL = 15
HEARTBEAT_TIMEOUT = 10
GATE_SAFETY_TIMEOUT = 15


def _is_mostly_latin(text: str) -> bool:
    """Return True if alphabetic chars meet the minimum Latin ratio threshold.

    Gemini's ASR sometimes transcribes English speech in Devanagari, Arabic,
    or other scripts.  This filter tags those mis-transcriptions as
    low-confidence while keeping the audio flowing to the model.
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return True  # No alpha chars — let it through (numbers, punctuation)
    latin_count = sum(1 for c in alpha_chars if c.isascii())
    return latin_count / len(alpha_chars) > settings.min_latin_ratio


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

    # Phase 1: Mutable session reference — retries create fresh sessions
    current_session_id = session_id
    # Mutable container so upstream() always sends to the current queue
    queue_ref: list[LiveRequestQueue] = [live_queue]

    # Phase 2: Server-side audio gate (open by default).
    # Closed during tool execution to prevent audio reaching Gemini
    # (which causes 1011 crashes). Safety timeout reopens if stuck.
    audio_gate = asyncio.Event()
    audio_gate.set()
    gate_safety_task: asyncio.Task | None = None

    # Phase 4: Heartbeat pong tracking
    pong_received = asyncio.Event()
    pong_received.set()

    async def upstream():
        """Client audio/text -> LiveRequestQueue -> Gemini."""
        try:
            while True:
                raw = await websocket.receive()
                if "bytes" in raw:
                    # Phase 2: Only forward audio when gate is open
                    if audio_gate.is_set():
                        audio_blob = types.Blob(
                            mime_type="audio/pcm;rate=16000", data=raw["bytes"]
                        )
                        queue_ref[0].send_realtime(audio_blob)
                elif "text" in raw:
                    msg = json.loads(raw["text"])
                    if msg.get("type") == "auth":
                        # Store Firebase token in session state for CC API calls
                        token_value = str(msg.get("token", "")).strip()
                        stored = await store_user_token(
                            user_id=user_id,
                            session_id=current_session_id,
                            token_value=token_value,
                        )
                        if stored and token_value:
                            auth_ready.set()
                        logger.info(
                            "Auth token stored for session %s (length=%d, stored=%s)",
                            current_session_id,
                            len(token_value),
                            stored,
                        )
                    elif msg.get("type") == "text":
                        content = types.Content(
                            parts=[types.Part(text=msg["text"])]
                        )
                        queue_ref[0].send_content(content)
                    elif msg.get("type") == "pong":
                        # Phase 4: Heartbeat response from client
                        pong_received.set()
        except WebSocketDisconnect:
            pass

    async def _process_event(event):
        """Handle a single ADK live event — audio, transcription, queues."""
        nonlocal gate_safety_task

        # Phase 2: Server-side audio gating during tool execution.
        # Close the gate when tools start, reopen when they finish.
        # Safety timeout prevents stuck gate if function_response never arrives.
        if hasattr(event, "get_function_calls") and event.get_function_calls():
            logger.debug("Tool call detected — closing audio gate")
            audio_gate.clear()
            if gate_safety_task and not gate_safety_task.done():
                gate_safety_task.cancel()

            async def _gate_safety_release():
                await asyncio.sleep(GATE_SAFETY_TIMEOUT)
                logger.warning(
                    "Audio gate safety release after %ds timeout (session %s)",
                    GATE_SAFETY_TIMEOUT,
                    current_session_id,
                )
                audio_gate.set()

            gate_safety_task = asyncio.create_task(_gate_safety_release())
            await websocket.send_text(
                json.dumps({"type": "tool_executing", "active": True})
            )

        if hasattr(event, "get_function_responses") and event.get_function_responses():
            logger.debug("Tool response received — opening audio gate")
            audio_gate.set()
            if gate_safety_task and not gate_safety_task.done():
                gate_safety_task.cancel()
                gate_safety_task = None
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

        # Phase 5: Send ALL transcripts — tag uncertain ones as low-confidence
        # instead of silently dropping them.
        if hasattr(event, "input_transcription") and event.input_transcription:
            transcript_text = event.input_transcription.text or ""
            if transcript_text:
                is_latin = _is_mostly_latin(transcript_text)
                if not is_latin:
                    logger.warning(
                        "Low-confidence transcript (non-Latin) in session %s: %.80s",
                        current_session_id,
                        transcript_text,
                    )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "input_transcript",
                            "text": transcript_text,
                            **({"low_confidence": True} if not is_latin else {}),
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
        queue = nav_queues.get(current_session_id)
        if queue:
            while not queue.empty():
                cmd = queue.get_nowait()
                await websocket.send_text(json.dumps(cmd))

        sug_queue = suggestion_queues.get(current_session_id)
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
        during tool execution). Phase 1: each retry creates a fresh
        session to prevent Gemini replaying old conversation context.
        """
        nonlocal current_session_id, gate_safety_task

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
                    current_session_id, attempt + 1,
                )
                async for event in runner.run_live(
                    user_id=user_id,
                    session_id=current_session_id,
                    live_request_queue=queue_ref[0],
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

                    # ── Phase 1: Session isolation on retry ──
                    # Create a fresh session so Gemini doesn't see prior
                    # conversation history and "replay" old context.
                    old_sid = current_session_id
                    current_session_id = f"{session_id}-retry-{attempt + 1}"

                    # Carry over user_token from old session
                    old_session = await session_service.get_session(
                        app_name=settings.app_name,
                        user_id=user_id,
                        session_id=old_sid,
                    )
                    user_token = (
                        old_session.state.get("user_token")
                        if old_session
                        else None
                    )

                    await session_service.create_session(
                        app_name=settings.app_name,
                        user_id=user_id,
                        session_id=current_session_id,
                    )

                    if user_token:
                        persist_session_value(
                            session_service=session_service,
                            app_name=settings.app_name,
                            user_id=user_id,
                            session_id=current_session_id,
                            key="user_token",
                            value=user_token,
                        )

                    # Migrate navigation/suggestion queues to new session
                    if old_sid in nav_queues:
                        nav_queues[current_session_id] = nav_queues.pop(old_sid)
                    if old_sid in suggestion_queues:
                        suggestion_queues[current_session_id] = (
                            suggestion_queues.pop(old_sid)
                        )

                    # Remove old retry session from memory
                    user_sessions = (
                        session_service.sessions
                        .get(settings.app_name, {})
                        .get(user_id, {})
                    )
                    user_sessions.pop(old_sid, None)

                    # Fresh LiveRequestQueue — old one may hold stale state
                    # from the crashed run_live call
                    queue_ref[0].close()
                    queue_ref[0] = LiveRequestQueue()

                    # Re-open audio gate for fresh session
                    audio_gate.set()
                    if gate_safety_task and not gate_safety_task.done():
                        gate_safety_task.cancel()
                        gate_safety_task = None

                    # Notify frontend that session was reset
                    try:
                        await websocket.send_text(
                            json.dumps({"type": "session_reset"})
                        )
                    except Exception:
                        pass

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

    async def heartbeat():
        """Phase 4: Periodic ping to detect stale/dead connections.

        Sends a ping every 15s.  If the client doesn't pong within 10s,
        close the WebSocket so the frontend's auto-reconnect can kick in.
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                pong_received.clear()
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    return  # WebSocket already closed
                try:
                    await asyncio.wait_for(
                        pong_received.wait(), timeout=HEARTBEAT_TIMEOUT
                    )
                except TimeoutError:
                    logger.warning(
                        "Heartbeat timeout for session %s — closing",
                        current_session_id,
                    )
                    try:
                        await websocket.close(
                            code=1001, reason="Heartbeat timeout"
                        )
                    except Exception:
                        pass
                    return
        except asyncio.CancelledError:
            pass

    try:
        await asyncio.gather(
            upstream(), downstream(), heartbeat(), return_exceptions=True
        )
    finally:
        queue_ref[0].close()
        if gate_safety_task and not gate_safety_task.done():
            gate_safety_task.cancel()
        nav_queues.pop(current_session_id, None)
        suggestion_queues.pop(current_session_id, None)

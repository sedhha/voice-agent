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

router = APIRouter()

session_service = InMemorySessionService()
runner = Runner(
    app_name=settings.app_name,
    agent=compliance_router,
    session_service=session_service,
)


@router.websocket("/ws/voice/{user_id}/{session_id}")
async def voice_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """Bidirectional audio streaming endpoint.

    Receives PCM 16kHz mono audio from the browser mic,
    sends PCM 24kHz mono audio + text/transcript events back.
    """
    await websocket.accept()

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=settings.voice_name,
                )
            )
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
                    if msg.get("type") == "text":
                        content = types.Content(
                            parts=[types.Part(text=msg["text"])]
                        )
                        live_queue.send_content(content)
        except WebSocketDisconnect:
            pass

    async def downstream():
        """Gemini responses -> WebSocket -> Client speakers."""
        logger.info("Starting run_live for session %s", session_id)
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_queue,
                run_config=run_config,
            ):
                logger.debug("Event: %s", type(event).__name__)
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data:
                            await websocket.send_bytes(part.inline_data.data)
                        elif part.text:
                            await websocket.send_text(
                                json.dumps({"type": "text", "text": part.text})
                            )

                if hasattr(event, "input_transcription") and event.input_transcription:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "input_transcript",
                                "text": event.input_transcription.text,
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
        except Exception as e:
            logger.exception("run_live error: %s", e)

    try:
        await asyncio.gather(upstream(), downstream(), return_exceptions=True)
    finally:
        live_queue.close()

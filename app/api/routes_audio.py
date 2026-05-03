from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.models.audio import AudioFrame, VadState
from app.models.triage import AzureHealth, ProviderMode
from app.services.audio_frame_service import AudioFrameError
from app.services.audio_session_processor import AudioSessionProcessor

router = APIRouter(tags=["audio"])


class SessionStart(BaseModel):
    type: str
    session_id: str | None = None
    provider_mode: ProviderMode | None = None


@router.get("/api/health/azure", response_model=AzureHealth)
async def azure_health(settings: Settings = Depends(get_settings)) -> AzureHealth:
    warnings: list[str] = []
    if settings.use_mock_services:
        warnings.append("USE_MOCK_SERVICES is enabled; Azure calls are bypassed.")
    elif not settings.azure_speech_openai_configured:
        warnings.append("Azure Speech/OpenAI credentials are incomplete; mock fallback may be used.")
    if not settings.cosmos_configured:
        warnings.append("Cosmos DB is not configured; local JSON storage is active.")

    return AzureHealth(
        use_mock_services=settings.use_mock_services,
        selected_provider=ProviderMode(settings.selected_provider),
        azure_speech_configured=settings.azure_speech_configured,
        azure_openai_configured=settings.azure_openai_configured,
        azure_voice_live_configured=settings.azure_voice_live_configured,
        cosmos_configured=settings.cosmos_configured,
        twilio_tts_response_enabled=settings.enable_twilio_tts_response,
        azure_speech_tts_configured=settings.azure_speech_tts_configured,
        azure_speech_voice=settings.azure_speech_voice,
        missing_variables=settings.missing_azure_variables(),
        warnings=warnings,
    )


@router.websocket("/ws/local-audio")
async def local_audio_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    settings = get_settings()
    session_id = f"session_{uuid4().hex[:12]}"
    requested_mode: ProviderMode | None = None
    processor = AudioSessionProcessor(settings=settings, session_id=session_id)

    try:
        while True:
            raw = await websocket.receive_json()
            message_type = raw.get("type")

            if message_type == "session.start":
                start = SessionStart.model_validate(raw)
                session_id = start.session_id or session_id
                requested_mode = start.provider_mode
                processor = AudioSessionProcessor(
                    settings=settings,
                    session_id=session_id,
                    requested_mode=requested_mode,
                )
                await websocket.send_json(
                    {
                        "type": "session.started",
                        "session_id": session_id,
                        "provider_mode": (requested_mode or ProviderMode(settings.selected_provider)).value,
                        "state": VadState.LISTENING.value,
                    }
                )
                continue

            if message_type == "assistant.playback.started":
                await websocket.send_json(processor.assistant_playback_started())
                continue

            if message_type == "assistant.playback.completed":
                await websocket.send_json(processor.assistant_playback_completed())
                continue

            if message_type == "session.close":
                await websocket.send_json({"type": "session.closed", "session_id": session_id})
                await websocket.close()
                return

            if message_type != "audio.frame":
                await websocket.send_json({"type": "error", "detail": f"Unsupported message type: {message_type}"})
                continue

            try:
                frame = AudioFrame.model_validate({**raw, "session_id": raw.get("session_id") or session_id})
            except (ValidationError, AudioFrameError, ValueError) as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue

            for payload in await processor.process_frame(frame):
                await websocket.send_json(payload)
    except WebSocketDisconnect:
        return

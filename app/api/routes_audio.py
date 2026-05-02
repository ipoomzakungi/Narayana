from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.models.audio import AudioDebugEvent, AudioDebugEventType, AudioFrame, VadState
from app.models.case import CrisisCase
from app.models.triage import AzureHealth, ProviderMode
from app.services.audio_frame_service import AudioFrameError
from app.services.case_repository import get_case_repository
from app.services.safety_rules import apply_safety_rules
from app.services.turn_manager import TurnManager
from app.services.voice_agent_provider import get_voice_provider

router = APIRouter(tags=["audio"])


class SessionStart(BaseModel):
    type: str
    session_id: str | None = None
    provider_mode: ProviderMode | None = None


def _event_payload(event: AudioDebugEvent) -> dict:
    return {"type": "debug.event", "event": event.model_dump(mode="json")}


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
        missing_variables=settings.missing_azure_variables(),
        warnings=warnings,
    )


@router.websocket("/ws/local-audio")
async def local_audio_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    settings = get_settings()
    session_id = f"session_{uuid4().hex[:12]}"
    requested_mode: ProviderMode | None = None
    manager = TurnManager()
    debug_events: list[AudioDebugEvent] = []

    try:
        while True:
            raw = await websocket.receive_json()
            message_type = raw.get("type")

            if message_type == "session.start":
                start = SessionStart.model_validate(raw)
                session_id = start.session_id or session_id
                requested_mode = start.provider_mode
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
                manager.set_speaking(True)
                await websocket.send_json(
                    _event_payload(
                        AudioDebugEvent(
                            session_id=session_id,
                            event_type=AudioDebugEventType.AI_RESPONSE_STARTED,
                            state=VadState.SPEAKING,
                        )
                    )
                )
                continue

            if message_type == "assistant.playback.completed":
                manager.set_speaking(False)
                await websocket.send_json(
                    _event_payload(
                        AudioDebugEvent(
                            session_id=session_id,
                            event_type=AudioDebugEventType.AI_RESPONSE_COMPLETED,
                            state=VadState.LISTENING,
                        )
                    )
                )
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
                result = manager.process_frame(frame)
            except (ValidationError, AudioFrameError, ValueError) as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue

            debug_events.extend(result.events)
            for event in result.events:
                await websocket.send_json(_event_payload(event))

            if result.committed_turn is None:
                continue

            provider = get_voice_provider(settings, requested_mode)
            await websocket.send_json(
                _event_payload(
                    AudioDebugEvent(
                        session_id=session_id,
                        event_type=AudioDebugEventType.AI_REQUEST_STARTED,
                        state=VadState.THINKING,
                        metadata={"turn_id": result.committed_turn.turn_id},
                    )
                )
            )
            provider_result = await provider.process_turn(result.committed_turn)
            safe_triage = apply_safety_rules(provider_result.triage, settings.low_confidence_threshold)
            case = CrisisCase.model_validate(safe_triage.model_dump())
            repository = get_case_repository(settings)
            record = await repository.create(
                case=case,
                session_id=session_id,
                source_provider=provider_result.provider_mode,
                debug_event_count=len(debug_events),
            )
            await websocket.send_json(
                {
                    "type": "triage.case.created",
                    "session_id": session_id,
                    "transcript": provider_result.transcript,
                    "provider_mode": provider_result.provider_mode.value,
                    "response_text": provider_result.response_text,
                    "warnings": provider_result.provider_warnings,
                    "record": record.model_dump(mode="json"),
                }
            )
    except WebSocketDisconnect:
        return

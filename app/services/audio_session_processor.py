from __future__ import annotations

from app.core.config import Settings
from app.models.audio import AudioDebugEvent, AudioDebugEventType, AudioFrame, VadState
from app.models.case import CrisisCase
from app.models.telephony import CallMetadata
from app.models.triage import ProviderMode
from app.services.audio_buffer_service import AudioBufferError, AudioBufferService
from app.services.case_repository import get_case_repository
from app.services.safety_rules import apply_safety_rules
from app.services.turn_manager import TurnManager
from app.services.voice_agent_provider import get_voice_provider


def event_payload(event: AudioDebugEvent) -> dict:
    return {"type": "debug.event", "event": event.model_dump(mode="json")}


class AudioSessionProcessor:
    def __init__(
        self,
        settings: Settings,
        session_id: str,
        requested_mode: ProviderMode | None = None,
        source_input_mode: str | None = None,
        call_metadata: CallMetadata | None = None,
    ) -> None:
        self.settings = settings
        self.session_id = session_id
        self.requested_mode = requested_mode
        self.source_input_mode = source_input_mode
        self.call_metadata = call_metadata
        self.manager = TurnManager()
        self.audio_buffer = AudioBufferService(settings.audio_store_path)
        self.debug_events: list[AudioDebugEvent] = []

    def assistant_playback_started(self) -> dict:
        self.manager.set_speaking(True)
        event = AudioDebugEvent(
            session_id=self.session_id,
            event_type=AudioDebugEventType.AI_RESPONSE_STARTED,
            state=VadState.SPEAKING,
        )
        self.debug_events.append(event)
        return event_payload(event)

    def assistant_playback_completed(self) -> dict:
        self.manager.set_speaking(False)
        event = AudioDebugEvent(
            session_id=self.session_id,
            event_type=AudioDebugEventType.AI_RESPONSE_COMPLETED,
            state=VadState.LISTENING,
        )
        self.debug_events.append(event)
        return event_payload(event)

    async def process_frame(self, frame: AudioFrame) -> list[dict]:
        try:
            result = self.manager.process_frame(frame)
            speech_started = any(event.event_type == AudioDebugEventType.VAD_SPEECH_START for event in result.events)
            self.audio_buffer.observe_frame(frame, speech_started=speech_started)
        except (AudioBufferError, ValueError) as exc:
            return [{"type": "error", "detail": str(exc)}]

        audio_warnings: list[str] = []
        if result.committed_turn is not None:
            try:
                audio_result = self.audio_buffer.write_committed_turn(result.committed_turn)
                result.committed_turn.audio_ref = audio_result.audio_ref
                result.committed_turn.audio_debug_id = audio_result.audio_debug_id
                for event in result.events:
                    if event.event_type == AudioDebugEventType.TURN_COMMITTED:
                        event.metadata.update(
                            {
                                "audio_ref": audio_result.audio_ref,
                                "audio_debug_id": audio_result.audio_debug_id,
                                "audio_frame_count": audio_result.frame_count,
                            }
                        )
            except AudioBufferError as exc:
                audio_warnings.append(f"Audio turn could not be saved: {exc}")
                for event in result.events:
                    if event.event_type == AudioDebugEventType.TURN_COMMITTED:
                        event.metadata["audio_error"] = str(exc)

        self.debug_events.extend(result.events)
        payloads = [event_payload(event) for event in result.events]

        if result.committed_turn is None:
            return payloads

        ai_event = AudioDebugEvent(
            session_id=self.session_id,
            event_type=AudioDebugEventType.AI_REQUEST_STARTED,
            state=VadState.THINKING,
            metadata={"turn_id": result.committed_turn.turn_id},
        )
        self.debug_events.append(ai_event)
        payloads.append(event_payload(ai_event))

        provider = get_voice_provider(self.settings, self.requested_mode)
        provider_result = await provider.process_turn(result.committed_turn)
        safe_triage = apply_safety_rules(provider_result.triage, self.settings.low_confidence_threshold)
        case = CrisisCase.model_validate(safe_triage.model_dump())
        repository = get_case_repository(self.settings)
        record = await repository.create(
            case=case,
            session_id=self.session_id,
            source_provider=provider_result.provider_mode,
            debug_event_count=len(self.debug_events),
        )
        case_payload = {
            "type": "triage.case.created",
            "session_id": self.session_id,
            "transcript": provider_result.transcript,
            "provider_mode": provider_result.provider_mode.value,
            "transcript_source": provider_result.transcript_source,
            "audio_ref": provider_result.audio_ref or result.committed_turn.audio_ref,
            "response_text": provider_result.response_text,
            "warnings": [*audio_warnings, *provider_result.provider_warnings],
            "record": record.model_dump(mode="json"),
        }
        if self.source_input_mode:
            case_payload["source_input_mode"] = self.source_input_mode
        if self.call_metadata:
            case_payload["call_metadata"] = self.call_metadata.model_dump(mode="json")
        payloads.append(case_payload)
        return payloads

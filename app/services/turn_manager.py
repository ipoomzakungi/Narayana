from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.audio import AudioDebugEvent, AudioDebugEventType, AudioFrame, CallerTurn, VadState
from app.services.vad_service import EnergyVadService


@dataclass
class TurnManagerResult:
    events: list[AudioDebugEvent] = field(default_factory=list)
    committed_turn: CallerTurn | None = None


class TurnManager:
    def __init__(
        self,
        vad: EnergyVadService | None = None,
        silence_threshold_ms: int = 750,
        pre_speech_padding_ms: int = 200,
    ) -> None:
        self.vad = vad or EnergyVadService()
        self.silence_threshold_ms = silence_threshold_ms
        self.pre_speech_padding_ms = pre_speech_padding_ms
        self.state = VadState.LISTENING
        self._in_speech = False
        self._silence_ms = 0
        self._speech_ms = 0
        self._turn_started_at: datetime | None = None
        self._barge_in = False

    def set_speaking(self, speaking: bool) -> None:
        self.state = VadState.SPEAKING if speaking else VadState.LISTENING

    def process_frame(self, frame: AudioFrame) -> TurnManagerResult:
        events = [
            AudioDebugEvent(
                session_id=frame.session_id,
                event_type=AudioDebugEventType.AUDIO_FRAME_RECEIVED,
                state=self.state,
                metadata={"sequence": frame.sequence},
            )
        ]
        speech = self.vad.is_speech(frame)

        if speech and frame.assistant_is_speaking:
            self._barge_in = True
            events.append(
                AudioDebugEvent(
                    session_id=frame.session_id,
                    event_type=AudioDebugEventType.BARGE_IN_DETECTED,
                    state=VadState.SPEECH,
                    metadata={"sequence": frame.sequence},
                )
            )

        if speech:
            if not self._in_speech:
                self._in_speech = True
                self._speech_ms = 0
                self._turn_started_at = datetime.now(timezone.utc)
                events.append(
                    AudioDebugEvent(
                        session_id=frame.session_id,
                        event_type=AudioDebugEventType.VAD_SPEECH_START,
                        state=VadState.SPEECH,
                    )
                )
            self.state = VadState.SPEECH
            self._speech_ms += frame.duration_ms
            self._silence_ms = 0
            return TurnManagerResult(events=events)

        if not self._in_speech:
            self.state = VadState.SILENCE
            return TurnManagerResult(events=events)

        self._silence_ms += frame.duration_ms
        if self._silence_ms < self.silence_threshold_ms:
            return TurnManagerResult(events=events)

        ended_at = datetime.now(timezone.utc)
        duration_ms = max(self._speech_ms, frame.duration_ms)
        turn = CallerTurn(
            turn_id=f"turn_{uuid4().hex[:12]}",
            session_id=frame.session_id,
            started_at=self._turn_started_at or ended_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            pre_speech_padding_ms=self.pre_speech_padding_ms,
            silence_threshold_ms=self.silence_threshold_ms,
            barge_in=self._barge_in,
        )
        events.extend(
            [
                AudioDebugEvent(
                    session_id=frame.session_id,
                    event_type=AudioDebugEventType.VAD_SPEECH_END,
                    state=VadState.SILENCE,
                    duration_ms=self._silence_ms,
                ),
                AudioDebugEvent(
                    session_id=frame.session_id,
                    event_type=AudioDebugEventType.TURN_COMMITTED,
                    state=VadState.THINKING,
                    duration_ms=turn.duration_ms,
                    metadata={"turn_id": turn.turn_id},
                ),
            ]
        )
        self.state = VadState.THINKING
        self._in_speech = False
        self._silence_ms = 0
        self._speech_ms = 0
        self._turn_started_at = None
        self._barge_in = False
        return TurnManagerResult(events=events, committed_turn=turn)

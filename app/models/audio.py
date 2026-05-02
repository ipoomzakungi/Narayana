from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.triage import ProviderMode


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InputMode(StrEnum):
    LOCAL_MIC = "local_mic"
    UPLOADED_AUDIO = "uploaded_audio"
    TWILIO_MEDIA_STREAM = "twilio_media_stream"
    ACS_AUDIO_STREAM = "acs_audio_stream"


class VadState(StrEnum):
    SILENCE = "silence"
    SPEECH = "speech"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class AudioDebugEventType(StrEnum):
    AUDIO_FRAME_RECEIVED = "audio.frame.received"
    VAD_SPEECH_START = "vad.speech.start"
    VAD_SPEECH_END = "vad.speech.end"
    TURN_COMMITTED = "turn.committed"
    AI_REQUEST_STARTED = "ai.request.started"
    AI_RESPONSE_STARTED = "ai.response.started"
    AI_RESPONSE_COMPLETED = "ai.response.completed"
    BARGE_IN_DETECTED = "barge_in.detected"


class AudioFrame(BaseModel):
    session_id: str
    sequence: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    encoding: str = "pcm16"
    sample_rate_hz: int = 16000
    channels: int = 1
    duration_ms: int = 20
    audio_base64: str
    assistant_is_speaking: bool = False


class AudioDebugEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    session_id: str
    case_id: str | None = None
    event_type: AudioDebugEventType
    state: VadState | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    duration_ms: int | None = None
    metadata: dict = Field(default_factory=dict)


class VoiceGatewaySession(BaseModel):
    session_id: str
    input_mode: InputMode = InputMode.LOCAL_MIC
    provider_mode: ProviderMode = ProviderMode.MOCK
    current_state: VadState = VadState.LISTENING
    sample_rate_hz: int = 16000
    frame_ms: int = 20
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    case_id: str | None = None


class CallerTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: f"turn_{uuid4().hex[:12]}")
    session_id: str
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime = Field(default_factory=utc_now)
    duration_ms: int
    pre_speech_padding_ms: int
    silence_threshold_ms: int
    audio_ref: str | None = None
    audio_debug_id: str | None = None
    barge_in: bool = False

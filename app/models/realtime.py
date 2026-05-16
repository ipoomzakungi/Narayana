from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.triage import utc_now


class RealtimeProviderMode(StrEnum):
    NONE = "none"
    AZURE_VOICE_LIVE = "azure_voice_live"
    AZURE_OPENAI_REALTIME = "azure_openai_realtime"


class RealtimeSessionStatus(StrEnum):
    DISABLED = "disabled"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    FALLBACK = "fallback"
    CLOSED = "closed"
    ERROR = "error"


class RealtimeAudioEventType(StrEnum):
    CONNECTED = "connected"
    INPUT_AUDIO_SENT = "audio.input.sent"
    OUTPUT_AUDIO_RECEIVED = "audio.output.received"
    CALLER_TRANSCRIPT_DELTA = "transcript.caller.delta"
    CALLER_TRANSCRIPT_COMPLETED = "transcript.caller.completed"
    ASSISTANT_TRANSCRIPT_DELTA = "transcript.assistant.delta"
    ASSISTANT_TRANSCRIPT_COMPLETED = "transcript.assistant.completed"
    STRUCTURED_EXTRACTION = "structured.extraction"
    RESPONSE_STARTED = "response.started"
    RESPONSE_COMPLETED = "response.completed"
    UNKNOWN_PROVIDER_EVENT = "unknown_provider_event"
    ERROR = "error"
    FALLBACK = "fallback"


class RealtimeAudioFormat(StrEnum):
    MULAW_8KHZ = "mulaw_8khz"
    PCM16 = "pcm16"
    UNKNOWN = "unknown"


class RealtimeLatencySample(BaseModel):
    stage: str
    provider: RealtimeProviderMode
    session_id: str
    call_id: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RealtimeConnectionResult(BaseModel):
    connected: bool
    provider: RealtimeProviderMode
    warnings: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None
    latency_ms: int = Field(default=0, ge=0)


class RealtimeSendResult(BaseModel):
    sent: bool
    provider: RealtimeProviderMode
    warnings: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None
    latency_ms: int = Field(default=0, ge=0)


class RealtimeAudioEvent(BaseModel):
    event_type: RealtimeAudioEventType
    provider: RealtimeProviderMode
    session_id: str | None = None
    call_id: str | None = None
    sequence: int | None = None
    audio_base64: str | None = None
    audio_format: RealtimeAudioFormat = RealtimeAudioFormat.UNKNOWN
    text: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RealtimeFallbackDecision(BaseModel):
    session_id: str
    provider: RealtimeProviderMode
    call_id: str | None = None
    reason: str
    latency_ms_before_fallback: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    occurred_at: datetime = Field(default_factory=utc_now)

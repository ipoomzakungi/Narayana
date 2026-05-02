from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VoiceInputMode(StrEnum):
    LOCAL_MIC = "local_mic"
    TWILIO_CALL = "twilio_call"
    ACS_CALL = "acs_call"


class TelephonyProvider(StrEnum):
    NONE = "none"
    TWILIO = "twilio"
    ACS = "acs"


class TelephonyCodec(StrEnum):
    MULAW = "mulaw"
    PCM16 = "pcm16"
    UNKNOWN = "unknown"


class CallMetadata(BaseModel):
    provider: TelephonyProvider
    call_id: str = Field(min_length=1)
    from_number: str | None = None
    to_number: str | None = None
    country: str | None = None
    codec: TelephonyCodec = TelephonyCodec.UNKNOWN
    sample_rate: int = Field(default=8000, gt=0)
    started_at: datetime = Field(default_factory=utc_now)
    raw_provider_payload: dict[str, Any] | None = None

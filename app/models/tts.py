from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, PrivateAttr, field_validator


class TTSProfile(StrEnum):
    NORMAL = "normal"
    FOLLOWUP = "followup"
    GREETING = "greeting"
    RED = "red"
    UNCLEAR = "unclear"
    CLOSING = "closing"
    SAFE_FALLBACK = "safe_fallback"


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str = "th"
    voice: str | None = None
    profile: TTSProfile = TTSProfile.NORMAL

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("TTS text must not be blank.")
        return stripped


class TTSResult(BaseModel):
    configured: bool
    voice: str
    audio_format: str = "mulaw_8khz"
    profile: TTSProfile = TTSProfile.NORMAL
    ssml_enabled: bool = True
    payload_count: int = 0
    total_bytes: int = 0
    estimated_duration_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)
    sanitized_text: str = ""
    _payloads: list[str] = PrivateAttr(default_factory=list)

    @property
    def payloads(self) -> list[str]:
        return list(self._payloads)

    def with_payloads(self, payloads: list[str]) -> "TTSResult":
        self._payloads = list(payloads)
        self.payload_count = len(payloads)
        return self


class TTSTestResponse(BaseModel):
    configured: bool
    voice: str
    audio_format: str = "mulaw_8khz"
    profile: TTSProfile = TTSProfile.NORMAL
    ssml_enabled: bool = True
    payload_count: int = 0
    total_bytes: int = 0
    estimated_duration_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)

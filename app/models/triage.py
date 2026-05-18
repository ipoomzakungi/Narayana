from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderMode(StrEnum):
    MOCK = "mock"
    AZURE_SPEECH_OPENAI = "azure_speech_openai"
    AZURE_VOICE_LIVE = "azure_voice_live"
    AZURE_OPENAI_REALTIME = "azure_openai_realtime"


class IncidentType(StrEnum):
    FLOOD = "flood"
    FIRE = "fire"
    MEDICAL = "medical"
    ACCIDENT = "accident"
    EARTHQUAKE = "earthquake"
    PUBLIC_SAFETY = "public_safety"
    UNKNOWN = "unknown"


class TriageLevel(StrEnum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class CaseStatus(StrEnum):
    PENDING = "pending"
    CONTACTED = "contacted"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SafetyRuleResult(BaseModel):
    forced_triage_level: Optional[TriageLevel] = None
    human_review_required: bool
    matched_rules: list[str] = Field(default_factory=list)
    reason: str


class TriageResult(BaseModel):
    case_id: str = Field(default_factory=lambda: f"case_{uuid4().hex[:12]}")
    language: str
    incident_type: IncidentType
    triage_level: TriageLevel
    confidence: float = Field(ge=0.0, le=1.0)
    location_text: str = ""
    people_affected: int | None = Field(default=None, ge=0)
    injuries: str = ""
    immediate_needs: list[str] = Field(default_factory=list)
    caller_phone_optional: str | None = None
    ai_summary: str
    triage_reason: str
    human_review_required: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    status: CaseStatus = CaseStatus.PENDING

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        value = value.strip().lower()
        if value in {"th-th", "thai"}:
            return "th"
        return value or "unknown"

    @field_validator("immediate_needs")
    @classmethod
    def normalize_needs(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item.strip()]

    def touch(self) -> "TriageResult":
        self.updated_at = utc_now()
        return self


class TriageFromTranscriptRequest(BaseModel):
    transcript: str = Field(min_length=1)
    language_hint: str = "th"
    provider_mode: ProviderMode | None = None
    caller_phone_optional: str | None = None


class AzureHealth(BaseModel):
    use_mock_services: bool
    selected_provider: ProviderMode
    azure_speech_configured: bool
    azure_openai_configured: bool
    azure_voice_live_configured: bool
    cosmos_configured: bool
    twilio_tts_response_enabled: bool = False
    twilio_initial_greeting_enabled: bool = False
    twilio_initial_greeting_text_configured: bool = False
    twilio_initial_greeting_profile: str = "greeting"
    assistant_display_name: str = "ระบบช่วยรับแจ้งเหตุ"
    assistant_system_prompt_version: str = "v1"
    assistant_scope: str = "crisis_intake_only"
    assistant_decline_off_topic: bool = True
    call_no_reply_seconds: float = 10.0
    call_no_reply_prompt_seconds: float = 15.0
    call_max_no_reply_prompts: int = 2
    call_max_off_topic_redirects: int = 2
    call_end_on_repeated_off_topic: bool = True
    call_end_on_no_reply: bool = True
    twilio_force_hangup_enabled: bool = False
    azure_speech_tts_configured: bool = False
    azure_speech_voice: str = "th-TH-PremwadeeNeural"
    tts_use_ssml: bool = True
    tts_output_format: str = "mulaw_8khz"
    enable_realtime_voice: bool = False
    realtime_provider: str = "none"
    azure_realtime_configured: bool = False
    azure_openai_realtime_configured: bool = False
    azure_voice_live_realtime_configured: bool = False
    realtime_input_audio_format: str = "pcm16"
    effective_realtime_input_audio_format: str = "pcm16"
    realtime_twilio_audio_passthrough: bool = False
    realtime_input_audio_passthrough_enabled: bool = False
    realtime_input_transcription_enabled: bool = False
    realtime_output_voice: str = "marin"
    realtime_warnings: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

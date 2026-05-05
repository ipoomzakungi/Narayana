from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.case import CaseRepositoryRecord
from app.models.triage import IncidentType, TriageLevel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationSpeaker(StrEnum):
    CALLER = "caller"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntakeAction(StrEnum):
    ASK_FOLLOWUP = "ask_followup"
    CREATE_CASE = "create_case"
    ESCALATE_HUMAN_REVIEW = "escalate_human_review"


class CaseGroup(StrEnum):
    RESCUE = "rescue"
    MEDICAL = "medical"
    FIRE = "fire"
    FLOOD = "flood"
    POLICE_PUBLIC_SAFETY = "police_public_safety"
    TOURIST_SUPPORT = "tourist_support"
    UTILITY_INFRASTRUCTURE = "utility_infrastructure"
    SHELTER_SUPPLIES = "shelter_supplies"
    MENTAL_HEALTH_SUPPORT = "mental_health_support"
    UNKNOWN_HUMAN_REVIEW = "unknown_human_review"


class IntakeSessionStatus(StrEnum):
    ACTIVE = "active"
    WAITING_FOR_FOLLOWUP = "waiting_for_followup"
    CASE_CREATED = "case_created"
    ESCALATED = "escalated"


class ConversationTurn(BaseModel):
    speaker: ConversationSpeaker
    text: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    turn_index: int = Field(ge=0)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("turn text cannot be blank")
        return value


class CallAuditTimelineEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex[:12]}")
    type: str = Field(min_length=1)
    speaker: ConversationSpeaker | None = None
    text: str | None = None
    tts_profile: str | None = None
    tts_status: str | None = None
    triage_level: TriageLevel | None = None
    case_group: str | None = None
    recommended_team: str | None = None
    guardrail_warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("text")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class IntakeCollectedFields(BaseModel):
    language: str = "th"
    incident_type: IncidentType = IncidentType.UNKNOWN
    location_text: str = ""
    people_affected: int | None = Field(default=None, ge=0)
    injuries: str = ""
    immediate_needs: list[str] = Field(default_factory=list)
    caller_phone_optional: str | None = None
    landmarks: list[str] = Field(default_factory=list)
    urgency_signals: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        value = value.strip().lower()
        if value in {"thai", "th-th"}:
            return "th"
        return value or "th"

    @field_validator("location_text", "injuries")
    @classmethod
    def trim_string(cls, value: str) -> str:
        return value.strip()

    @field_validator("immediate_needs", "landmarks", "urgency_signals", "missing_fields")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            clean = item.strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized


class IntakeSessionState(BaseModel):
    session_id: str = Field(min_length=1)
    call_id: str | None = None
    source_input_mode: str = "manual"
    conversation_turns: list[ConversationTurn] = Field(default_factory=list)
    timeline_events: list[CallAuditTimelineEvent] = Field(default_factory=list)
    collected_fields: IntakeCollectedFields = Field(default_factory=IntakeCollectedFields)
    triage_level: TriageLevel | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    human_review_required: bool = False
    followup_count: int = Field(default=0, ge=0)
    max_followups: int = Field(default=3, ge=1)
    case_group: CaseGroup | None = None
    recommended_team: str = ""
    final_case_id: str | None = None
    status: IntakeSessionStatus = IntakeSessionStatus.ACTIVE
    guardrail_warnings: list[str] = Field(default_factory=list)
    decision_audit: list[dict[str, Any]] = Field(default_factory=list)
    off_topic_count: int = Field(default=0, ge=0)
    redirect_count: int = Field(default=0, ge=0)
    last_off_topic_at: datetime | None = None
    last_assistant_redirect: str = ""
    no_reply_prompt_count: int = Field(default=0, ge=0)
    last_caller_speech_at: datetime | None = None
    greeting_sent_at: datetime | None = None
    call_end_recommended: bool = False
    call_end_reason: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> "IntakeSessionState":
        self.updated_at = utc_now()
        return self


class IntakeRequest(BaseModel):
    session_id: str = Field(min_length=1)
    transcript: str = Field(min_length=1)
    language_hint: str = "th"
    source_input_mode: str = "manual"
    call_id: str | None = None
    caller_phone_optional: str | None = None

    @field_validator("transcript")
    @classmethod
    def trim_transcript(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("transcript cannot be blank")
        return value


class IntakeGuardrailResult(BaseModel):
    forced_triage_level: TriageLevel | None = None
    forced_human_review: bool = False
    guardrail_reasons: list[str] = Field(default_factory=list)
    recommended_case_group: CaseGroup | None = None
    urgency_signals: list[str] = Field(default_factory=list)


class IntakeDecision(BaseModel):
    action: IntakeAction
    language: str = "th"
    updated_fields: IntakeCollectedFields = Field(default_factory=IntakeCollectedFields)
    case_group: CaseGroup = CaseGroup.UNKNOWN_HUMAN_REVIEW
    recommended_team: str = "human_review"
    triage_level: TriageLevel = TriageLevel.YELLOW
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    human_review_required: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    response_text: str = ""
    reason: str = ""
    guardrail_warnings: list[str] = Field(default_factory=list)

    @field_validator("response_text")
    @classmethod
    def trim_response_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_action_payload(self) -> "IntakeDecision":
        if self.action == IntakeAction.ASK_FOLLOWUP and not self.response_text:
            raise ValueError("ask_followup decisions require response_text")
        if self.action in {IntakeAction.CREATE_CASE, IntakeAction.ESCALATE_HUMAN_REVIEW} and not self.reason:
            raise ValueError("case decisions require reason")
        return self


class IntakeResponse(BaseModel):
    session_id: str
    action: IntakeAction
    response_text: str
    partial_state: IntakeSessionState
    case_group: CaseGroup
    recommended_team: str
    triage_level: TriageLevel
    human_review_required: bool
    missing_fields: list[str] = Field(default_factory=list)
    reason: str
    guardrail_warnings: list[str] = Field(default_factory=list)
    off_topic_count: int = 0
    redirect_count: int = 0
    no_reply_prompt_count: int = 0
    call_end_recommended: bool = False
    call_end_reason: str = ""
    last_assistant_redirect: str = ""
    created_case: CaseRepositoryRecord | None = None

    @model_validator(mode="after")
    def validate_created_case(self) -> "IntakeResponse":
        if self.action == IntakeAction.ASK_FOLLOWUP and self.created_case is not None:
            raise ValueError("ask_followup responses cannot include created_case")
        if self.action in {IntakeAction.CREATE_CASE, IntakeAction.ESCALATE_HUMAN_REVIEW} and self.created_case is None:
            raise ValueError("case actions require created_case")
        return self


class IntakeSessionListResponse(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    count: int = Field(ge=0)
    limit: int = Field(ge=1)
    sessions: list[IntakeSessionState] = Field(default_factory=list)

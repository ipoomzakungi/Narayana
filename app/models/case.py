from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.triage import ProviderMode, TriageResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CrisisCase(TriageResult):
    case_group: str | None = None
    recommended_team: str | None = None
    conversation_summary: str | None = None
    intake_session_id: str | None = None
    intake_audit: list[dict] = Field(default_factory=list)
    realtime_provider: str | None = None
    realtime_model_or_deployment: str | None = None
    realtime_transcript_turns: list[dict] = Field(default_factory=list)
    caller_tone: str | None = None
    recommended_operator_action: str | None = None
    call_started_at: datetime | None = None
    call_ended_at: datetime | None = None
    fallback_reason: str | None = None


class CreateCaseRequest(BaseModel):
    case: CrisisCase
    session_id: str | None = None
    source_provider: ProviderMode = ProviderMode.MOCK
    case_group: str | None = None
    recommended_team: str | None = None
    conversation_summary: str | None = None
    intake_session_id: str | None = None
    intake_audit: list[dict] = Field(default_factory=list)


class CaseRepositoryRecord(BaseModel):
    case: CrisisCase
    session_id: str | None = None
    source_provider: ProviderMode
    debug_event_count: int = Field(default=0, ge=0)
    stored_at: datetime = Field(default_factory=utc_now)
    case_group: str | None = None
    recommended_team: str | None = None
    conversation_summary: str | None = None
    intake_session_id: str | None = None
    intake_audit: list[dict] = Field(default_factory=list)
    realtime_provider: str | None = None
    realtime_model_or_deployment: str | None = None
    realtime_transcript_turns: list[dict] = Field(default_factory=list)
    caller_tone: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    recommended_operator_action: str | None = None
    call_started_at: datetime | None = None
    call_ended_at: datetime | None = None
    fallback_reason: str | None = None


class CaseSnapshotResponse(BaseModel):
    generated_at: datetime
    expires_at: datetime
    ttl_seconds: int = Field(ge=1)
    count: int = Field(ge=0)
    source: str
    cases: list[CaseRepositoryRecord]

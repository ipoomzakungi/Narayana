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


class CaseSnapshotResponse(BaseModel):
    generated_at: datetime
    expires_at: datetime
    ttl_seconds: int = Field(ge=1)
    count: int = Field(ge=0)
    source: str
    cases: list[CaseRepositoryRecord]

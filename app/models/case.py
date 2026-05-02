from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.triage import ProviderMode, TriageResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CrisisCase(TriageResult):
    pass


class CreateCaseRequest(BaseModel):
    case: CrisisCase
    session_id: str | None = None
    source_provider: ProviderMode = ProviderMode.MOCK


class CaseRepositoryRecord(BaseModel):
    case: CrisisCase
    session_id: str | None = None
    source_provider: ProviderMode
    debug_event_count: int = Field(default=0, ge=0)
    stored_at: datetime = Field(default_factory=utc_now)

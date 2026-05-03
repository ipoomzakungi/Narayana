from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.case import CaseRepositoryRecord, CrisisCase
from app.models.triage import IncidentType, ProviderMode, TriageLevel
from app.services.case_snapshot_cache import CaseSnapshotCache


def make_record(case_id: str) -> CaseRepositoryRecord:
    case = CrisisCase(
        case_id=case_id,
        language="th",
        incident_type=IncidentType.FLOOD,
        triage_level=TriageLevel.RED,
        confidence=0.91,
        location_text="หาดใหญ่",
        injuries="elderly person breathing difficulty",
        immediate_needs=["rescue", "medical"],
        ai_summary="Flood with trapped elderly person.",
        triage_reason="Trapped person and breathing difficulty.",
        human_review_required=True,
    )
    return CaseRepositoryRecord(case=case, session_id="session_1", source_provider=ProviderMode.MOCK)


class FakeRepository:
    def __init__(self) -> None:
        self.calls = 0

    async def list_recent(self, limit: int = 50) -> list[CaseRepositoryRecord]:
        self.calls += 1
        return [make_record(f"case_{self.calls}")][:limit]


@pytest.mark.asyncio
async def test_case_snapshot_cache_returns_cached_snapshot_until_ttl_expires() -> None:
    now = datetime(2026, 5, 3, 8, 0, tzinfo=timezone.utc)

    def now_provider() -> datetime:
        return now

    repository = FakeRepository()
    cache = CaseSnapshotCache(ttl_seconds=60, now_provider=now_provider)

    first = await cache.get_recent_cases(repository, limit=50)
    second = await cache.get_recent_cases(repository, limit=50)
    now += timedelta(seconds=61)
    third = await cache.get_recent_cases(repository, limit=50)

    assert first.source == "repository"
    assert second.source == "cache"
    assert third.source == "repository"
    assert repository.calls == 2
    assert first.generated_at == second.generated_at
    assert first.expires_at == second.expires_at
    assert third.generated_at > first.generated_at

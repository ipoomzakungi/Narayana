from __future__ import annotations

import pytest

from app.models.case import CrisisCase
from app.models.triage import CaseStatus, IncidentType, ProviderMode, TriageLevel
from app.services.local_case_repository import LocalCaseRepository


def make_case() -> CrisisCase:
    return CrisisCase(
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


@pytest.mark.asyncio
async def test_create_get_and_persist_local_case(tmp_path) -> None:
    path = tmp_path / "cases.json"
    repository = LocalCaseRepository(str(path))
    case = make_case()

    record = await repository.create(case, session_id="session_1", source_provider=ProviderMode.MOCK, debug_event_count=5)
    loaded = await LocalCaseRepository(str(path)).get(case.case_id)

    assert path.exists()
    assert record.case.status == CaseStatus.PENDING
    assert loaded is not None
    assert loaded.case.case_id == case.case_id
    assert loaded.debug_event_count == 5


@pytest.mark.asyncio
async def test_missing_case_returns_none(tmp_path) -> None:
    repository = LocalCaseRepository(str(tmp_path / "cases.json"))

    assert await repository.get("missing") is None


@pytest.mark.asyncio
async def test_repository_does_not_auto_dispatch_or_close(tmp_path) -> None:
    repository = LocalCaseRepository(str(tmp_path / "cases.json"))
    case = make_case()

    record = await repository.create(case, session_id=None, source_provider=ProviderMode.MOCK)

    assert record.case.status == CaseStatus.PENDING

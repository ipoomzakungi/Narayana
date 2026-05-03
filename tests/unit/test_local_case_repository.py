from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.case import CrisisCase
from app.models.triage import CaseStatus, IncidentType, ProviderMode, TriageLevel
from app.services.local_case_repository import LocalCaseRepository


def make_case(case_id: str = "case_test", created_at: datetime | None = None) -> CrisisCase:
    created = created_at or datetime(2026, 5, 2, tzinfo=timezone.utc)
    return CrisisCase(
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
        created_at=created,
        updated_at=created,
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
async def test_local_case_repository_persists_optional_intake_metadata(tmp_path) -> None:
    repository = LocalCaseRepository(str(tmp_path / "cases.json"))
    case = make_case()

    await repository.create(
        case,
        session_id="session_1",
        source_provider=ProviderMode.MOCK,
        case_group="rescue",
        recommended_team="rescue",
        conversation_summary="Caller reported flood.",
        intake_session_id="session_1",
        intake_audit=[{"action": "escalate_human_review"}],
    )
    loaded = await repository.get(case.case_id)

    assert loaded is not None
    assert loaded.case_group == "rescue"
    assert loaded.recommended_team == "rescue"
    assert loaded.conversation_summary == "Caller reported flood."
    assert loaded.intake_audit == [{"action": "escalate_human_review"}]


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


@pytest.mark.asyncio
async def test_list_recent_returns_newest_cases_first_and_applies_limit(tmp_path) -> None:
    repository = LocalCaseRepository(str(tmp_path / "cases.json"))
    oldest = make_case("case_old", datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc))
    newest = make_case("case_new", datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc))
    middle = make_case("case_mid", datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc))

    await repository.create(oldest, session_id="session_old", source_provider=ProviderMode.MOCK)
    await repository.create(newest, session_id="session_new", source_provider=ProviderMode.MOCK)
    await repository.create(middle, session_id="session_mid", source_provider=ProviderMode.MOCK)

    records = await repository.list_recent(limit=2)

    assert [record.case.case_id for record in records] == ["case_new", "case_mid"]

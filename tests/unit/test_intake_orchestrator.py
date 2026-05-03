from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.intake import IntakeAction, IntakeRequest
from app.services.intake_orchestrator import IntakeOrchestrator
from app.services.intake_session_store import IntakeSessionStore


def orchestrator(tmp_path, max_followups: int = 3) -> IntakeOrchestrator:
    settings = Settings(
        use_mock_services=True,
        case_store_path=str(tmp_path / "cases.json"),
        assistant_max_followups=max_followups,
    )
    return IntakeOrchestrator(settings=settings, store=IntakeSessionStore(default_max_followups=max_followups))


@pytest.mark.asyncio
async def test_missing_location_asks_location(tmp_path) -> None:
    service = orchestrator(tmp_path)

    response = await service.process_transcript(
        IntakeRequest(session_id="session_missing_location", transcript="น้ำท่วม", source_input_mode="manual")
    )

    assert response.action == IntakeAction.ASK_FOLLOWUP
    assert "location_text" in response.missing_fields
    assert "อยู่จุดไหน" in response.response_text
    assert response.created_case is None


@pytest.mark.asyncio
async def test_known_location_asks_injury_question_without_repeating_location(tmp_path) -> None:
    service = orchestrator(tmp_path)

    response = await service.process_transcript(
        IntakeRequest(session_id="session_known_location", transcript="น้ำท่วมอยู่ที่หาดใหญ่", source_input_mode="manual")
    )
    second = await service.process_transcript(
        IntakeRequest(session_id="session_known_location", transcript="ยังอยู่ที่หาดใหญ่", source_input_mode="manual")
    )

    assert response.action == IntakeAction.ASK_FOLLOWUP
    assert second.action == IntakeAction.ASK_FOLLOWUP
    assert "location_text" not in second.missing_fields
    assert "บาดเจ็บ" in second.response_text


@pytest.mark.asyncio
async def test_red_risk_creates_case_immediately(tmp_path) -> None:
    service = orchestrator(tmp_path)

    response = await service.process_transcript(
        IntakeRequest(
            session_id="session_red",
            transcript="น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
            source_input_mode="manual",
        )
    )

    assert response.action == IntakeAction.ESCALATE_HUMAN_REVIEW
    assert response.triage_level == "RED"
    assert response.human_review_required is True
    assert response.created_case is not None
    assert response.created_case.case_group == "rescue"
    assert response.created_case.case.human_review_required is True
    assert "dispatch" not in response.response_text.lower()


@pytest.mark.asyncio
async def test_max_followups_creates_human_review_case(tmp_path) -> None:
    service = orchestrator(tmp_path, max_followups=3)
    service.store.get_or_create("session_limit", max_followups=3)
    service.store._sessions["session_limit"].followup_count = 3

    response = await service.process_transcript(
        IntakeRequest(session_id="session_limit", transcript="เสียงไม่ชัด", source_input_mode="manual")
    )

    assert response.action == IntakeAction.ESCALATE_HUMAN_REVIEW
    assert response.created_case is not None
    assert response.human_review_required is True
    assert response.created_case.case.status == "pending"

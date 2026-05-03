from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.case import CaseRepositoryRecord, CrisisCase
from app.models.triage import CaseStatus, IncidentType, ProviderMode, TriageLevel, TriageResult


def test_triage_result_defaults_and_nullable_fields() -> None:
    result = TriageResult(
        language="thai",
        incident_type=IncidentType.FLOOD,
        triage_level=TriageLevel.RED,
        confidence=0.9,
        people_affected=None,
        caller_phone_optional=None,
        ai_summary="Flood with medical risk.",
        triage_reason="Caller reports breathing difficulty.",
    )

    assert result.language == "th"
    assert result.status == CaseStatus.PENDING
    assert result.people_affected is None
    assert result.caller_phone_optional is None
    assert result.case_id.startswith("case_")


def test_triage_rejects_invalid_enum_and_confidence() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            language="th",
            incident_type="storm",
            triage_level="BLUE",
            confidence=1.3,
            ai_summary="Invalid",
            triage_reason="Invalid",
        )


def test_case_repository_record_shape() -> None:
    case = CrisisCase(
        language="th",
        incident_type="medical",
        triage_level="YELLOW",
        confidence=0.8,
        location_text="Bangkok",
        ai_summary="Caller reports injury.",
        triage_reason="Injury without immediate RED indicator.",
    )
    record = CaseRepositoryRecord(
        case=case,
        session_id="session_1",
        source_provider=ProviderMode.MOCK,
        debug_event_count=3,
    )

    assert record.case.status == CaseStatus.PENDING
    assert record.source_provider == ProviderMode.MOCK
    assert record.debug_event_count == 3


def test_case_repository_record_accepts_optional_intake_fields() -> None:
    case = CrisisCase(
        language="th",
        incident_type="flood",
        triage_level="RED",
        confidence=0.92,
        location_text="หาดใหญ่",
        ai_summary="Flood with trapped person.",
        triage_reason="Trapped person.",
        case_group="rescue",
        recommended_team="rescue",
        conversation_summary="Caller reported flood.",
        intake_session_id="session_1",
        intake_audit=[{"action": "escalate_human_review"}],
    )
    record = CaseRepositoryRecord(
        case=case,
        session_id="session_1",
        source_provider=ProviderMode.MOCK,
        case_group="rescue",
        recommended_team="rescue",
        conversation_summary="Caller reported flood.",
        intake_session_id="session_1",
        intake_audit=[{"action": "escalate_human_review"}],
    )

    assert record.case.case_group == "rescue"
    assert record.recommended_team == "rescue"
    assert record.conversation_summary == "Caller reported flood."

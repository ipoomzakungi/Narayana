from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.intake import (
    CaseGroup,
    ConversationSpeaker,
    IntakeAction,
    IntakeDecision,
    IntakeRequest,
    IntakeResponse,
    IntakeSessionState,
)
from app.models.triage import TriageLevel


def test_intake_enums_and_defaults() -> None:
    state = IntakeSessionState(session_id="session_1")

    assert ConversationSpeaker.CALLER == "caller"
    assert IntakeAction.ASK_FOLLOWUP == "ask_followup"
    assert CaseGroup.RESCUE == "rescue"
    assert state.collected_fields.language == "th"
    assert state.max_followups == 3
    assert state.followup_count == 0
    assert state.off_topic_count == 0
    assert state.redirect_count == 0
    assert state.no_reply_prompt_count == 0
    assert state.call_end_recommended is False
    assert state.call_end_reason == ""
    assert state.last_assistant_redirect == ""
    assert state.last_off_topic_at is None
    assert state.last_caller_speech_at is None
    assert state.greeting_sent_at is None


def test_intake_request_rejects_blank_transcript() -> None:
    with pytest.raises(ValidationError):
        IntakeRequest(session_id="session_1", transcript="   ")


def test_followup_decision_requires_response_text() -> None:
    with pytest.raises(ValidationError):
        IntakeDecision(action=IntakeAction.ASK_FOLLOWUP)


def test_intake_response_created_case_rules() -> None:
    decision = IntakeDecision(
        action=IntakeAction.ASK_FOLLOWUP,
        response_text="มีใครบาดเจ็บไหมคะ?",
        triage_level=TriageLevel.YELLOW,
        reason="Missing injuries.",
    )

    response = IntakeResponse(
        session_id="session_1",
        action=decision.action,
        response_text=decision.response_text,
        partial_state=IntakeSessionState(session_id="session_1"),
        case_group=CaseGroup.FLOOD,
        recommended_team="flood_response",
        triage_level=TriageLevel.YELLOW,
        human_review_required=True,
        missing_fields=["injuries"],
        reason=decision.reason,
        off_topic_count=1,
        redirect_count=1,
        created_case=None,
    )

    assert response.created_case is None
    assert response.off_topic_count == 1

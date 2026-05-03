from __future__ import annotations

from app.models.intake import CaseGroup, IntakeAction, IntakeDecision, IntakeSessionStatus
from app.models.triage import TriageLevel
from app.services.intake_session_store import IntakeSessionStore


def test_session_store_reuses_state_and_orders_turns() -> None:
    store = IntakeSessionStore(default_max_followups=3)
    state = store.get_or_create("session_1", source_input_mode="manual")

    caller = store.append_caller_turn("session_1", "น้ำท่วมอยู่ที่หาดใหญ่")
    assistant = store.append_assistant_turn("session_1", "มีใครบาดเจ็บไหมคะ?")
    same_state = store.get_or_create("session_1")

    assert state is same_state
    assert caller.turn_index == 0
    assert assistant.turn_index == 1
    assert [turn.speaker for turn in same_state.conversation_turns] == ["caller", "assistant"]


def test_session_store_updates_decision_and_final_status() -> None:
    store = IntakeSessionStore(default_max_followups=3)
    store.get_or_create("session_1")
    decision = IntakeDecision(
        action=IntakeAction.ASK_FOLLOWUP,
        response_text="ตอนนี้อยู่จุดไหนคะ?",
        case_group=CaseGroup.UNKNOWN_HUMAN_REVIEW,
        recommended_team="human_review",
        triage_level=TriageLevel.YELLOW,
        confidence=0.5,
        human_review_required=True,
        missing_fields=["location_text"],
        reason="Missing location.",
    )

    state = store.update_state("session_1", decision)
    store.mark_final("session_1", "case_1", IntakeSessionStatus.ESCALATED)

    assert state.triage_level == TriageLevel.YELLOW
    assert state.decision_audit[0]["action"] == "ask_followup"
    assert state.final_case_id == "case_1"
    assert state.status == IntakeSessionStatus.ESCALATED


def test_session_store_clear() -> None:
    store = IntakeSessionStore()
    store.get_or_create("session_1")
    store.clear("session_1")

    assert store.snapshot("session_1") is None

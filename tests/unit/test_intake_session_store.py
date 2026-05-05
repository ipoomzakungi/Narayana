from __future__ import annotations

from datetime import timedelta

from app.models.intake import CaseGroup, ConversationSpeaker, IntakeAction, IntakeDecision, IntakeSessionStatus
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


def test_append_timeline_event_and_list_recent() -> None:
    store = IntakeSessionStore()
    first = store.get_or_create("session_a", call_id="CA_A")
    store.append_timeline_event(
        first.session_id,
        event_type="caller.turn.transcribed",
        speaker=ConversationSpeaker.CALLER,
        text="น้ำท่วม",
        metadata={"sequence": 1},
    )
    second = store.get_or_create("session_b", call_id="CA_B")
    store.mark_final(second.session_id, "case_b", IntakeSessionStatus.CASE_CREATED)
    second.updated_at = first.updated_at + timedelta(seconds=1)

    recent = store.list_recent(limit=2)

    assert [state.session_id for state in recent] == ["session_b", "session_a"]
    assert recent[1].timeline_events[0].type == "caller.turn.transcribed"
    assert recent[1].timeline_events[0].text == "น้ำท่วม"
    assert recent[1].timeline_events[0].metadata["sequence"] == 1


def test_get_by_call_id_returns_snapshot() -> None:
    store = IntakeSessionStore()
    store.get_or_create("twilio_CA123", call_id="CA123")

    found = store.get_by_call_id("CA123")

    assert found is not None
    assert found.session_id == "twilio_CA123"
    found.call_id = "mutated"
    assert store.get_by_call_id("CA123").call_id == "CA123"

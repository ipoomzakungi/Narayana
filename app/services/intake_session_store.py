from __future__ import annotations

from copy import deepcopy

from app.models.intake import (
    ConversationSpeaker,
    ConversationTurn,
    IntakeDecision,
    IntakeSessionState,
    IntakeSessionStatus,
)


class IntakeSessionStore:
    def __init__(self, default_max_followups: int = 3) -> None:
        self.default_max_followups = default_max_followups
        self._sessions: dict[str, IntakeSessionState] = {}

    def get_or_create(
        self,
        session_id: str,
        *,
        call_id: str | None = None,
        source_input_mode: str = "manual",
        max_followups: int | None = None,
    ) -> IntakeSessionState:
        state = self._sessions.get(session_id)
        if state is None:
            state = IntakeSessionState(
                session_id=session_id,
                call_id=call_id,
                source_input_mode=source_input_mode,
                max_followups=max_followups or self.default_max_followups,
            )
            self._sessions[session_id] = state
        else:
            if call_id and not state.call_id:
                state.call_id = call_id
            if source_input_mode:
                state.source_input_mode = source_input_mode
            if max_followups:
                state.max_followups = max_followups
            state.touch()
        return state

    def append_caller_turn(self, session_id: str, text: str) -> ConversationTurn:
        return self._append_turn(session_id, ConversationSpeaker.CALLER, text)

    def append_assistant_turn(self, session_id: str, text: str) -> ConversationTurn:
        return self._append_turn(session_id, ConversationSpeaker.ASSISTANT, text)

    def update_state(self, session_id: str, decision: IntakeDecision) -> IntakeSessionState:
        state = self._sessions[session_id]
        state.triage_level = decision.triage_level
        state.confidence = decision.confidence
        state.human_review_required = decision.human_review_required
        state.case_group = decision.case_group
        state.recommended_team = decision.recommended_team
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, decision.guardrail_warnings)
        state.decision_audit.append(
            {
                "action": decision.action.value,
                "triage_level": decision.triage_level.value,
                "case_group": decision.case_group.value,
                "recommended_team": decision.recommended_team,
                "human_review_required": decision.human_review_required,
                "missing_fields": decision.missing_fields,
                "reason": decision.reason,
                "guardrail_warnings": decision.guardrail_warnings,
            }
        )
        state.touch()
        return state

    def save(self, state: IntakeSessionState) -> IntakeSessionState:
        self._sessions[state.session_id] = state
        state.touch()
        return state

    def clear(self, session_id: str | None = None) -> None:
        if session_id is None:
            self._sessions.clear()
        else:
            self._sessions.pop(session_id, None)

    def snapshot(self, session_id: str) -> IntakeSessionState | None:
        state = self._sessions.get(session_id)
        return deepcopy(state) if state else None

    def mark_final(self, session_id: str, case_id: str, status: IntakeSessionStatus) -> IntakeSessionState:
        state = self._sessions[session_id]
        state.final_case_id = case_id
        state.status = status
        state.touch()
        return state

    def _append_turn(self, session_id: str, speaker: ConversationSpeaker, text: str) -> ConversationTurn:
        state = self._sessions[session_id]
        turn = ConversationTurn(
            speaker=speaker,
            text=text,
            turn_index=len(state.conversation_turns),
        )
        state.conversation_turns.append(turn)
        state.touch()
        return turn


def _merge_unique(current: list[str], new_values: list[str]) -> list[str]:
    result = list(current)
    for value in new_values:
        if value not in result:
            result.append(value)
    return result


_global_store = IntakeSessionStore()


def get_intake_session_store(default_max_followups: int = 3) -> IntakeSessionStore:
    _global_store.default_max_followups = default_max_followups
    return _global_store

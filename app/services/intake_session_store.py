from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from app.models.intake import (
    CallAuditTimelineEvent,
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
        turn = self._append_turn(session_id, ConversationSpeaker.CALLER, text)
        self._sessions[session_id].last_caller_speech_at = turn.created_at
        return turn

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

    def append_timeline_event(
        self,
        session_id: str,
        *,
        event_type: str,
        speaker: ConversationSpeaker | None = None,
        text: str | None = None,
        tts_profile: str | None = None,
        tts_status: str | None = None,
        triage_level=None,
        case_group: str | None = None,
        recommended_team: str | None = None,
        guardrail_warnings: list[str] | None = None,
        metadata: dict | None = None,
        log_transcripts: bool = True,
        max_sessions: int | None = None,
    ) -> CallAuditTimelineEvent:
        state = self._sessions[session_id]
        event = CallAuditTimelineEvent(
            type=event_type,
            speaker=speaker,
            text=text if log_transcripts else None,
            tts_profile=tts_profile,
            tts_status=tts_status,
            triage_level=triage_level,
            case_group=case_group,
            recommended_team=recommended_team,
            guardrail_warnings=guardrail_warnings or [],
            metadata=metadata or {},
        )
        state.timeline_events.append(event)
        state.touch()
        if max_sessions:
            self._trim(max_sessions)
        return event

    def list_recent(self, limit: int = 50) -> list[IntakeSessionState]:
        safe_limit = max(1, limit)
        states = sorted(self._sessions.values(), key=lambda item: item.updated_at, reverse=True)
        return [deepcopy(state) for state in states[:safe_limit]]

    def get_by_call_id(self, call_id: str) -> IntakeSessionState | None:
        for state in self._sessions.values():
            if state.call_id == call_id:
                return deepcopy(state)
        return None

    def mark_greeting_sent(self, session_id: str, when: datetime | None = None) -> IntakeSessionState:
        from app.models.intake import utc_now

        state = self._sessions[session_id]
        state.greeting_sent_at = when or utc_now()
        state.touch()
        return state

    def record_no_reply_prompt(self, session_id: str, text: str) -> IntakeSessionState:
        state = self._sessions[session_id]
        state.no_reply_prompt_count += 1
        state.last_assistant_redirect = text
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, ["call:no_reply_prompt"])
        self.append_assistant_turn(session_id, text)
        state.decision_audit.append(
            {
                "action": "no_reply_prompt",
                "response_text": text,
                "no_reply_prompt_count": state.no_reply_prompt_count,
                "guardrail_warnings": ["call:no_reply_prompt"],
            }
        )
        state.touch()
        return state

    def mark_call_end_recommended(self, session_id: str, reason: str, response_text: str) -> IntakeSessionState:
        state = self._sessions[session_id]
        state.call_end_recommended = True
        state.call_end_reason = reason
        state.last_assistant_redirect = response_text
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, [f"call:end_recommended:{reason}"])
        self.append_assistant_turn(session_id, response_text)
        state.decision_audit.append(
            {
                "action": "call_end_recommended",
                "reason": reason,
                "response_text": response_text,
                "guardrail_warnings": [f"call:end_recommended:{reason}"],
            }
        )
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

    def _trim(self, max_sessions: int) -> None:
        if max_sessions <= 0 or len(self._sessions) <= max_sessions:
            return
        states = sorted(self._sessions.values(), key=lambda item: item.updated_at, reverse=True)
        keep = {state.session_id for state in states[:max_sessions]}
        for session_id in list(self._sessions):
            if session_id not in keep:
                self._sessions.pop(session_id, None)

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

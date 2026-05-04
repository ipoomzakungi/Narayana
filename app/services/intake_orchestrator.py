from __future__ import annotations

from app.core.config import Settings
from app.models.case import CrisisCase
from app.models.intake import (
    CaseGroup,
    IntakeAction,
    IntakeCollectedFields,
    IntakeDecision,
    IntakeRequest,
    IntakeResponse,
    IntakeSessionState,
    IntakeSessionStatus,
)
from app.models.triage import CaseStatus, IncidentType, ProviderMode, TriageLevel
from app.services.azure_openai_intake_provider import AzureOpenAIIntakeProvider
from app.services.case_grouping_service import group_case, group_requires_human_review
from app.services.case_repository import get_case_repository
from app.services.intake_guardrails import evaluate_intake_guardrails, response_mentions_forbidden_dispatch
from app.services.intake_scope_guardrails import classify_scope
from app.services.intake_session_store import IntakeSessionStore, get_intake_session_store
from app.services.safety_rules import apply_safety_rules


class IntakeOrchestrator:
    def __init__(
        self,
        settings: Settings,
        store: IntakeSessionStore | None = None,
        provider: AzureOpenAIIntakeProvider | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or get_intake_session_store(settings.assistant_max_followups)
        self.provider = provider or AzureOpenAIIntakeProvider(settings)

    async def process_transcript(self, request: IntakeRequest) -> IntakeResponse:
        state = self.store.get_or_create(
            request.session_id,
            call_id=request.call_id,
            source_input_mode=request.source_input_mode,
            max_followups=self.settings.assistant_max_followups,
        )
        if request.caller_phone_optional:
            state.collected_fields.caller_phone_optional = request.caller_phone_optional

        self.store.append_caller_turn(request.session_id, request.transcript)
        scope = classify_scope(request.transcript, state, self.settings)
        if scope.is_emergency_signal:
            self._reset_scope_state_for_emergency(state, scope.guardrail_warnings)
        elif scope.is_off_topic:
            return self._off_topic_response(state, scope)

        guardrails = evaluate_intake_guardrails(request.transcript, state)
        decision = await self.provider.decide(state, request.transcript, guardrails)
        decision = self._enforce_decision(decision, state, guardrails)

        state.collected_fields = _merge_collected_fields(state.collected_fields, decision.updated_fields)
        state.collected_fields.missing_fields = decision.missing_fields
        state.triage_level = decision.triage_level
        state.confidence = decision.confidence
        state.human_review_required = decision.human_review_required
        state.case_group = decision.case_group
        state.recommended_team = decision.recommended_team
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, decision.guardrail_warnings)

        created_case = None
        if decision.action == IntakeAction.ASK_FOLLOWUP:
            state.followup_count += 1
            state.status = IntakeSessionStatus.WAITING_FOR_FOLLOWUP
            self.store.append_assistant_turn(request.session_id, decision.response_text)
            self.store.update_state(request.session_id, decision)
            self.store.save(state)
        else:
            self.store.append_assistant_turn(request.session_id, decision.response_text)
            self.store.update_state(request.session_id, decision)
            created_case = await self._create_case(state, decision)
            final_status = (
                IntakeSessionStatus.ESCALATED
                if decision.action == IntakeAction.ESCALATE_HUMAN_REVIEW
                else IntakeSessionStatus.CASE_CREATED
            )
            self.store.mark_final(request.session_id, created_case.case.case_id, final_status)
            state = self.store.get_or_create(
                request.session_id,
                call_id=state.call_id,
                source_input_mode=state.source_input_mode,
            )

        return IntakeResponse(
            session_id=request.session_id,
            action=decision.action,
            response_text=decision.response_text,
            partial_state=state,
            case_group=decision.case_group,
            recommended_team=decision.recommended_team,
            triage_level=decision.triage_level,
            human_review_required=decision.human_review_required,
            missing_fields=decision.missing_fields,
            reason=decision.reason,
            guardrail_warnings=decision.guardrail_warnings,
            off_topic_count=state.off_topic_count,
            redirect_count=state.redirect_count,
            no_reply_prompt_count=state.no_reply_prompt_count,
            call_end_recommended=state.call_end_recommended,
            call_end_reason=state.call_end_reason,
            last_assistant_redirect=state.last_assistant_redirect,
            created_case=created_case,
        )

    def _off_topic_response(self, state: IntakeSessionState, scope) -> IntakeResponse:
        state.off_topic_count += 1
        state.redirect_count += 1
        state.last_off_topic_at = state.updated_at
        state.last_assistant_redirect = scope.response_text
        state.call_end_recommended = scope.call_end_recommended
        state.call_end_reason = "repeated_off_topic" if scope.call_end_recommended else ""
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, scope.guardrail_warnings)
        state.status = IntakeSessionStatus.WAITING_FOR_FOLLOWUP
        self.store.append_assistant_turn(state.session_id, scope.response_text)
        state.decision_audit.append(
            {
                "action": "scope_off_topic",
                "off_topic_count": state.off_topic_count,
                "redirect_count": state.redirect_count,
                "call_end_recommended": state.call_end_recommended,
                "call_end_reason": state.call_end_reason,
                "reason": scope.reason,
                "matched_terms": scope.matched_terms,
                "guardrail_warnings": scope.guardrail_warnings,
            }
        )
        self.store.save(state)
        return IntakeResponse(
            session_id=state.session_id,
            action=IntakeAction.ASK_FOLLOWUP,
            response_text=scope.response_text,
            partial_state=state,
            case_group=CaseGroup.UNKNOWN_HUMAN_REVIEW,
            recommended_team="human_review",
            triage_level=TriageLevel.GREEN,
            human_review_required=False,
            missing_fields=[],
            reason=scope.reason,
            guardrail_warnings=scope.guardrail_warnings,
            off_topic_count=state.off_topic_count,
            redirect_count=state.redirect_count,
            no_reply_prompt_count=state.no_reply_prompt_count,
            call_end_recommended=state.call_end_recommended,
            call_end_reason=state.call_end_reason,
            last_assistant_redirect=state.last_assistant_redirect,
            created_case=None,
        )

    def _reset_scope_state_for_emergency(self, state: IntakeSessionState, warnings: list[str]) -> None:
        if state.off_topic_count or state.call_end_recommended:
            state.decision_audit.append(
                {
                    "action": "scope_emergency_override",
                    "previous_off_topic_count": state.off_topic_count,
                    "previous_call_end_recommended": state.call_end_recommended,
                    "guardrail_warnings": warnings,
                }
            )
        state.off_topic_count = 0
        state.redirect_count = 0
        state.last_off_topic_at = None
        state.last_assistant_redirect = ""
        if state.call_end_reason == "repeated_off_topic":
            state.call_end_recommended = False
            state.call_end_reason = ""
        state.guardrail_warnings = _merge_unique(state.guardrail_warnings, warnings)
        self.store.save(state)

    def _enforce_decision(
        self,
        decision: IntakeDecision,
        state: IntakeSessionState,
        guardrails,
    ) -> IntakeDecision:
        updated = decision.model_copy(deep=True)

        group, team, group_reason = group_case(updated.updated_fields, _session_text(state))
        if group != CaseGroup.UNKNOWN_HUMAN_REVIEW or updated.case_group == CaseGroup.UNKNOWN_HUMAN_REVIEW:
            updated.case_group = group
            updated.recommended_team = team
            if group_reason not in updated.reason:
                updated.reason = f"{updated.reason} {group_reason}".strip()

        if guardrails.recommended_case_group and updated.case_group == CaseGroup.UNKNOWN_HUMAN_REVIEW:
            updated.case_group = guardrails.recommended_case_group
            updated.recommended_team = guardrails.recommended_case_group.value

        if guardrails.forced_triage_level == TriageLevel.RED:
            updated.triage_level = TriageLevel.RED
            updated.action = IntakeAction.ESCALATE_HUMAN_REVIEW
            updated.human_review_required = True

        if state.followup_count >= state.max_followups and updated.action == IntakeAction.ASK_FOLLOWUP:
            updated.action = IntakeAction.ESCALATE_HUMAN_REVIEW
            updated.human_review_required = True
            updated.confidence = min(updated.confidence, 0.45)
            updated.response_text = "รับทราบค่ะ ข้อมูลยังไม่ครบ จะส่งให้เจ้าหน้าที่ตรวจสอบต่อค่ะ"
            updated.reason = f"{updated.reason} Maximum follow-up count reached.".strip()

        if (
            updated.confidence < self.settings.low_confidence_threshold
            or not updated.updated_fields.location_text
            or updated.triage_level == TriageLevel.RED
            or group_requires_human_review(updated.case_group)
            or guardrails.forced_human_review
        ):
            updated.human_review_required = True

        updated.guardrail_warnings = _merge_unique(updated.guardrail_warnings, guardrails.guardrail_reasons)
        if response_mentions_forbidden_dispatch(updated.response_text):
            updated.response_text = "รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบทันที กรุณาอยู่ในที่ปลอดภัยถ้าทำได้"
            updated.guardrail_warnings = _merge_unique(updated.guardrail_warnings, ["response_rewritten:no_dispatch_claim"])

        if updated.action in {IntakeAction.CREATE_CASE, IntakeAction.ESCALATE_HUMAN_REVIEW} and not updated.response_text:
            updated.response_text = "รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบต่อค่ะ"

        return updated

    async def _create_case(self, state: IntakeSessionState, decision: IntakeDecision):
        fields = state.collected_fields
        summary = _conversation_summary(state)
        case = CrisisCase(
            language=fields.language,
            incident_type=fields.incident_type or IncidentType.UNKNOWN,
            triage_level=decision.triage_level,
            confidence=decision.confidence,
            location_text=fields.location_text,
            people_affected=fields.people_affected,
            injuries=fields.injuries,
            immediate_needs=fields.immediate_needs or [decision.case_group.value],
            caller_phone_optional=fields.caller_phone_optional,
            ai_summary=summary or "Crisis intake conversation requires operator review.",
            triage_reason=decision.reason,
            human_review_required=decision.human_review_required,
            missing_fields=decision.missing_fields,
            status=CaseStatus.PENDING,
            case_group=decision.case_group.value,
            recommended_team=decision.recommended_team,
            conversation_summary=summary,
            intake_session_id=state.session_id,
            intake_audit=[
                *state.decision_audit,
                {
                    "action": decision.action.value,
                    "reason": decision.reason,
                    "guardrail_warnings": decision.guardrail_warnings,
                    "missing_fields": decision.missing_fields,
                },
            ],
        )
        safe_case = CrisisCase.model_validate(
            apply_safety_rules(case, self.settings.low_confidence_threshold).model_dump()
        )
        repository = get_case_repository(self.settings)
        return await repository.create(
            case=safe_case,
            session_id=state.session_id,
            source_provider=ProviderMode(self.settings.selected_provider),
            case_group=decision.case_group.value,
            recommended_team=decision.recommended_team,
            conversation_summary=summary,
            intake_session_id=state.session_id,
            intake_audit=safe_case.intake_audit,
        )


def _merge_collected_fields(current: IntakeCollectedFields, new_fields: IntakeCollectedFields) -> IntakeCollectedFields:
    merged = current.model_copy(deep=True)
    merged.language = new_fields.language or merged.language
    if new_fields.incident_type != IncidentType.UNKNOWN:
        merged.incident_type = new_fields.incident_type
    if new_fields.location_text:
        merged.location_text = new_fields.location_text
    if new_fields.people_affected is not None:
        merged.people_affected = new_fields.people_affected
    if new_fields.injuries:
        merged.injuries = new_fields.injuries
    if new_fields.caller_phone_optional:
        merged.caller_phone_optional = new_fields.caller_phone_optional
    merged.immediate_needs = _merge_unique(merged.immediate_needs, new_fields.immediate_needs)
    merged.landmarks = _merge_unique(merged.landmarks, new_fields.landmarks)
    merged.urgency_signals = _merge_unique(merged.urgency_signals, new_fields.urgency_signals)
    merged.missing_fields = new_fields.missing_fields
    return merged


def _merge_unique(current: list[str], new_values: list[str]) -> list[str]:
    result = list(current)
    for value in new_values:
        if value and value not in result:
            result.append(value)
    return result


def _session_text(state: IntakeSessionState) -> str:
    return " ".join(turn.text for turn in state.conversation_turns if turn.speaker.value == "caller")


def _conversation_summary(state: IntakeSessionState) -> str:
    caller_turns = [turn.text for turn in state.conversation_turns if turn.speaker.value == "caller"]
    if not caller_turns:
        return ""
    return " | ".join(caller_turns)[-500:]

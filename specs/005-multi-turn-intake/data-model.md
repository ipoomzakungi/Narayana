# Data Model: Multi-Turn Crisis Conversation Intake

## ConversationSpeaker

Enum values:
- `caller`
- `assistant`
- `system`

Validation:
- Required for every conversation turn.

## IntakeAction

Enum values:
- `ask_followup`
- `create_case`
- `escalate_human_review`

State rules:
- `ask_followup` never creates a final case for that turn.
- `create_case` creates a normal pending case when enough information exists.
- `escalate_human_review` creates a pending case that requires human review due to high risk, low confidence, contradictions, unclear speech, or follow-up limit.

## CaseGroup

Enum values:
- `rescue`
- `medical`
- `fire`
- `flood`
- `police_public_safety`
- `tourist_support`
- `utility_infrastructure`
- `shelter_supplies`
- `mental_health_support`
- `unknown_human_review`

Validation:
- Every created/escalated intake case has exactly one case group.
- `unknown_human_review` implies human review.
- `mental_health_support` implies human review.

## ConversationTurn

Fields:
- `speaker`: ConversationSpeaker.
- `text`: non-empty string after trimming.
- `created_at`: timestamp.
- `turn_index`: zero-based integer within the session.

Validation:
- Turn index is assigned by the session store.
- Turns remain append-only for audit.

## IntakeCollectedFields

Fields:
- `language`: string, default `th`.
- `incident_type`: existing incident enum or unknown.
- `location_text`: string.
- `people_affected`: integer or null.
- `injuries`: string.
- `immediate_needs`: list of strings.
- `caller_phone_optional`: string or null.
- `landmarks`: list of strings.
- `urgency_signals`: list of strings.
- `missing_fields`: list of strings.

Merge rules:
- New non-empty values update the field.
- Empty model values do not erase known values.
- List fields merge uniquely while preserving useful order.
- Contradictions are recorded through audit/guardrail warnings and force human review.

## IntakeSessionState

Fields:
- `session_id`: required string.
- `call_id`: optional string.
- `source_input_mode`: string such as manual, local mic, or Twilio call.
- `conversation_turns`: ordered list of ConversationTurn.
- `collected_fields`: IntakeCollectedFields.
- `triage_level`: RED/YELLOW/GREEN or null.
- `confidence`: number from 0 to 1.
- `human_review_required`: boolean.
- `followup_count`: integer, starts at 0.
- `max_followups`: integer, default 3.
- `case_group`: CaseGroup or null.
- `recommended_team`: string.
- `final_case_id`: optional string.
- `status`: active, case_created, escalated, or closed.
- `guardrail_warnings`: list of strings.
- `decision_audit`: list of model and guardrail decisions.

State transitions:
- New session starts as `active`.
- `ask_followup` increments follow-up count and appends assistant turn.
- `create_case` sets final case ID and status `case_created`.
- `escalate_human_review` sets final case ID and status `escalated`.
- This feature never auto-closes a session.

## IntakeRequest

Fields:
- `session_id`: required string.
- `transcript`: required non-empty caller text.
- `language_hint`: default `th`.
- `source_input_mode`: default manual.
- `call_id`: optional string.
- `caller_phone_optional`: optional string.

Validation:
- Transcript cannot be blank.
- Session ID is used to load/create session state.

## IntakeDecision

Fields:
- `action`: IntakeAction.
- `language`: string.
- `updated_fields`: IntakeCollectedFields partial update.
- `case_group`: CaseGroup.
- `recommended_team`: string.
- `triage_level`: RED/YELLOW/GREEN.
- `confidence`: number from 0 to 1.
- `human_review_required`: boolean.
- `missing_fields`: list of strings.
- `response_text`: Thai response or next question.
- `reason`: human-readable explanation.
- `guardrail_warnings`: list of strings.

Validation:
- `response_text` max defaults to 180 Thai characters.
- Follow-up question max defaults to 120 Thai characters.
- Follow-up action requires a response text.
- Case/escalation action requires a triage level and group.

## IntakeResponse

Fields:
- `session_id`
- `action`
- `response_text`
- `partial_state`
- `case_group`
- `recommended_team`
- `triage_level`
- `human_review_required`
- `missing_fields`
- `reason`
- `guardrail_warnings`
- `created_case`: CaseRepositoryRecord or null

Validation:
- `created_case` is null for `ask_followup`.
- `created_case` is present for `create_case` and `escalate_human_review`.

## Crisis Case Extensions

Backward-compatible optional fields for final case records:
- `case_group`
- `recommended_team`
- `conversation_summary`
- `intake_session_id`
- `intake_audit`

Validation:
- Older records may omit all extension fields.
- Dashboard must treat missing extension fields as unknown/blank.

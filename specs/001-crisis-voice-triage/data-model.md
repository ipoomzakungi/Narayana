# Data Model: Narayana AI Voice Intake

## Enumerations

### TriageLevel

- `RED`: Life-threatening, urgent medical danger, trapped person, breathing difficulty, severe bleeding, fire danger, or drowning risk.
- `YELLOW`: Injured or at risk but not immediately life-threatening from available facts.
- `GREEN`: Caller appears safe and needs information or non-urgent support.

### CaseStatus

- `new`: Case created and not yet acted on by an operator.
- `contacted`: Operator has contacted or acknowledged the caller/case.
- `dispatched`: Operator records that a human response workflow outside the app has been dispatched.
- `resolved`: Operator records that the crisis need has been resolved.
- `closed`: Operator closes the case for the demo workflow.

### VadState

- `silence`
- `speech`
- `listening`
- `thinking`
- `speaking`

### TranscriptSpeaker

- `caller`
- `assistant`
- `operator`
- `system`

## Entity: CrisisCase

Represents the structured emergency-intake record shown on the operator dashboard.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `case_id` | string | yes | Stable unique identifier, generated on create. |
| `language` | string | yes | ISO-like language tag where known, for example `th-TH`; `unknown` allowed when uncertain. |
| `incident_type` | string | yes | Controlled label such as `flood`, `fire`, `medical`, `public_safety`, `other`, or combined labels for mixed incidents. |
| `triage_level` | TriageLevel | yes | Current effective priority, including operator override if present. |
| `ai_triage_level` | TriageLevel | yes | Original AI/rules priority preserved for audit. |
| `confidence` | number | yes | 0.0 to 1.0. Values below 0.70 force human review in V0. |
| `location_text` | string | no | Caller-provided location or landmark text. |
| `people_affected` | string | no | Human-readable count or description, because callers may be imprecise. |
| `injuries` | string | no | Injury or medical-risk description. |
| `immediate_needs` | string[] | yes | Needs such as evacuation, medical help, rescue, information, shelter. |
| `caller_phone_optional` | string | no | Optional because local microphone testing may not have caller phone data. |
| `ai_summary` | string | yes | Short operator-facing crisis summary. |
| `triage_reason` | string | yes | Explanation of why current priority was assigned. |
| `evidence` | EvidenceFact[] | yes | Extracted facts used by triage and summary. |
| `human_review_required` | boolean | yes | True for RED, low confidence, ambiguity, or safety-sensitive cases. |
| `created_at` | datetime | yes | UTC timestamp. |
| `updated_at` | datetime | yes | UTC timestamp updated on case change. |
| `status` | CaseStatus | yes | Initial value `new`. |
| `transcript` | TranscriptTurn[] | yes | Ordered conversation turns. |
| `debug_event_count` | integer | no | Optional denormalized count for dashboard hints. |
| `operator_overrides` | OperatorUpdate[] | yes | Priority and status changes made by an operator. |
| `simulated_outbound_actions` | SimulatedOutboundAction[] | yes | Demo-only SMS/upload-link actions. |

## Entity: TranscriptTurn

Represents a single caller, assistant, operator, or system message.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `turn_id` | string | yes | Unique within a case. |
| `case_id` | string | no | Present once the turn is associated with a case. |
| `speaker` | TranscriptSpeaker | yes | Caller, assistant, operator, or system. |
| `text` | string | yes | Transcript or message content. |
| `language` | string | no | Detected or configured language. |
| `confidence` | number | no | 0.0 to 1.0 if available. |
| `started_at` | datetime | yes | UTC timestamp. |
| `ended_at` | datetime | no | UTC timestamp when turn completes. |
| `duration_ms` | integer | no | Derived timing. |
| `is_final` | boolean | yes | False for partial transcript messages. |

## Entity: EvidenceFact

Represents extracted facts that support the summary and triage decision.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `fact_id` | string | yes | Unique within the case. |
| `field` | string | yes | One of `location`, `incident_type`, `people_affected`, `injuries`, `immediate_needs`, `danger`, or `other`. |
| `value` | string | yes | Extracted text value. |
| `source_turn_id` | string | no | Transcript turn where the fact was found. |
| `confidence` | number | yes | 0.0 to 1.0. |
| `requires_confirmation` | boolean | yes | True until critical fact is confirmed. |

## Entity: TriageAssessment

Represents the AI and rules decision before operator override.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `assessment_id` | string | yes | Unique assessment identifier. |
| `case_id` | string | yes | Associated case. |
| `triage_level` | TriageLevel | yes | AI/rules output. |
| `confidence` | number | yes | 0.0 to 1.0. |
| `triage_reason` | string | yes | Must include evidence-based rationale. |
| `red_flags` | string[] | yes | Matched RED indicators, if any. |
| `human_review_required` | boolean | yes | Must be true for RED or low confidence. |
| `created_at` | datetime | yes | UTC timestamp. |

## Entity: VoiceTimingEvent

Represents debug evidence for microphone, VAD, turn, and playback behavior.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `event_id` | string | yes | Unique event identifier. |
| `session_id` | string | yes | Voice session identifier. |
| `case_id` | string | no | Present after case creation. |
| `event_type` | string | yes | `audio_frame`, `vad_state`, `turn_started`, `turn_ended`, `barge_in`, `ai_request`, `ai_response`, `error`. |
| `state` | VadState | no | Required for state events. |
| `timestamp` | datetime | yes | UTC timestamp. |
| `duration_ms` | integer | no | Optional event duration. |
| `metadata` | object | no | Non-secret diagnostic values only. |

## Entity: OperatorUpdate

Represents human case actions.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `update_id` | string | yes | Unique update identifier. |
| `case_id` | string | yes | Associated case. |
| `operator_id` | string | no | Optional in V0 trusted-demo mode. |
| `update_type` | string | yes | `priority_override`, `status_change`, or `note`. |
| `previous_value` | string | no | Previous priority/status when relevant. |
| `new_value` | string | yes | New priority/status/note value. |
| `reason` | string | no | Required for priority override. |
| `created_at` | datetime | yes | UTC timestamp. |

## Entity: SafeGuidanceScript

Represents approved waiting guidance selected by incident context.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `script_id` | string | yes | Stable script identifier. |
| `incident_type` | string | yes | Incident label or `general`. |
| `triage_level` | TriageLevel | no | Optional priority-specific script. |
| `language` | string | yes | Thai-first for V0. |
| `text` | string | yes | Must not claim dispatch or hotline replacement. |
| `safety_notes` | string[] | yes | Internal notes for why script is safe. |

## Entity: SimulatedOutboundAction

Represents demo-only SMS or upload-link simulation.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `action_id` | string | yes | Unique identifier. |
| `case_id` | string | yes | Associated case. |
| `action_type` | string | yes | `sms_simulation` or `upload_link_simulation`. |
| `target_label` | string | no | Display label only, not a required real phone number. |
| `url` | string | no | Placeholder or local route for upload simulation. |
| `expires_at` | datetime | no | Required for upload-link simulation. |
| `is_simulated` | boolean | yes | Must be true in V0. |
| `created_at` | datetime | yes | UTC timestamp. |

## State Transitions

### Case Status

```text
new -> contacted -> dispatched -> resolved -> closed
new -> resolved -> closed
new -> closed
contacted -> resolved -> closed
contacted -> closed
dispatched -> resolved -> closed
```

Rules:

- The system may create a case with `new` only.
- Only an operator action can set `dispatched`.
- `closed` is terminal for V0 unless a future reopen workflow is explicitly added.

### Triage Override

```text
AI triage assigned -> operator may override current triage_level -> AI triage preserved as ai_triage_level
```

Rules:

- Operator override requires a reason.
- RED and low-confidence cases remain `human_review_required = true` even if an operator later lowers the current priority.
- The case detail view must show both the AI/rules reason and the operator override reason.

# Contract: Dashboard Intake Fields

## Cases Dashboard

The cases dashboard should treat these fields as optional on each case record:

```json
{
  "case_group": "rescue",
  "recommended_team": "rescue",
  "conversation_summary": "Caller reported flood in Hat Yai; elderly person trapped upstairs with breathing difficulty.",
  "intake_session_id": "twilio_CA123"
}
```

Display requirements:
- Show `case_group` when present; otherwise show `-`.
- Show `recommended_team` when present; otherwise show `-`.
- Show `conversation_summary` when present; otherwise continue showing existing AI summary.
- Do not reject or hide older records that omit these fields.

## Voice Debug Console

The debug console should render `intake.followup` payloads and final case payload intake details.

Required visible fields for follow-up:
- Action
- Response text / next question
- Conversation turns
- Partial collected fields
- Case group
- Recommended team
- Missing fields
- Guardrail warnings

Required visible fields for final cases:
- Existing case preview
- Case group
- Recommended team
- Conversation summary when available
- Intake action
- Guardrail warnings

## Frontend API Client

Manual transcript intake client call:

```json
{
  "session_id": "debug-session",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่",
  "language_hint": "th",
  "source_input_mode": "manual"
}
```

The client must keep the existing manual one-shot triage path available for regression and fallback testing.

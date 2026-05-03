# Contract: POST /api/intake/from-transcript

## Purpose

Process a caller transcript as part of a session-scoped crisis conversation. The endpoint updates conversation memory, applies guardrails, chooses the next action, and optionally creates a final crisis case.

## Request

```http
POST /api/intake/from-transcript
Content-Type: application/json
```

```json
{
  "session_id": "debug-session",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่",
  "language_hint": "th",
  "source_input_mode": "manual"
}
```

Optional fields:

```json
{
  "call_id": "CA123",
  "caller_phone_optional": "+66800000000"
}
```

## Response: Follow-Up

```json
{
  "session_id": "debug-session",
  "action": "ask_followup",
  "response_text": "มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?",
  "partial_state": {
    "session_id": "debug-session",
    "conversation_turns": [
      {
        "speaker": "caller",
        "text": "น้ำท่วมอยู่ที่หาดใหญ่",
        "created_at": "2026-05-03T10:00:00Z",
        "turn_index": 0
      },
      {
        "speaker": "assistant",
        "text": "มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?",
        "created_at": "2026-05-03T10:00:01Z",
        "turn_index": 1
      }
    ],
    "collected_fields": {
      "language": "th",
      "incident_type": "flood",
      "location_text": "หาดใหญ่",
      "people_affected": null,
      "injuries": "",
      "immediate_needs": [],
      "caller_phone_optional": null,
      "landmarks": [],
      "urgency_signals": [],
      "missing_fields": ["injuries", "people_affected"]
    },
    "followup_count": 1,
    "max_followups": 3
  },
  "case_group": "flood",
  "recommended_team": "flood_response",
  "triage_level": "YELLOW",
  "human_review_required": true,
  "missing_fields": ["injuries", "people_affected"],
  "reason": "Location and flood are known; injury and people affected details are still missing.",
  "guardrail_warnings": [],
  "created_case": null
}
```

## Response: Created/Escalated Case

```json
{
  "session_id": "debug-session",
  "action": "escalate_human_review",
  "response_text": "รับทราบค่ะ ขอให้เจ้าหน้าที่ตรวจสอบทันที กรุณาอยู่ในที่ปลอดภัยถ้าทำได้",
  "partial_state": {
    "session_id": "debug-session",
    "final_case_id": "case_abc123",
    "case_group": "rescue",
    "recommended_team": "rescue"
  },
  "case_group": "rescue",
  "recommended_team": "rescue",
  "triage_level": "RED",
  "human_review_required": true,
  "missing_fields": ["people_affected"],
  "reason": "Caller reports flood, trapped elderly person, and breathing difficulty.",
  "guardrail_warnings": ["forced_red: breathing difficulty", "forced_red: trapped person"],
  "created_case": {
    "case": {
      "case_id": "case_abc123",
      "language": "th",
      "incident_type": "flood",
      "triage_level": "RED",
      "confidence": 0.85,
      "location_text": "หาดใหญ่",
      "people_affected": null,
      "injuries": "elderly person breathing difficulty",
      "immediate_needs": ["rescue", "medical"],
      "caller_phone_optional": null,
      "ai_summary": "Flood in Hat Yai with a trapped elderly person having breathing difficulty.",
      "triage_reason": "Trapped person and breathing difficulty require immediate human review.",
      "human_review_required": true,
      "missing_fields": ["people_affected"],
      "status": "pending"
    },
    "session_id": "debug-session",
    "source_provider": "mock",
    "debug_event_count": 0,
    "stored_at": "2026-05-03T10:00:02Z",
    "case_group": "rescue",
    "recommended_team": "rescue",
    "conversation_summary": "Caller reported flood in Hat Yai; elderly person trapped upstairs with breathing difficulty."
  }
}
```

## Errors

- `422` for invalid request shape or blank transcript.
- `500` only for unexpected server failures; no external Azure credentials are required for deterministic fallback mode.

## Compatibility

- This endpoint does not replace `POST /api/triage/from-transcript`.
- It must work with mock/fallback mode and without Azure OpenAI credentials.

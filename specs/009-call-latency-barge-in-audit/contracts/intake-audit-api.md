# Contract: Intake Audit API

Base path: `/api/intake`

These endpoints expose recent call/intake sessions for demo debugging. They must not expose secrets or raw audio payloads.

## GET /api/intake/sessions

List recent intake/call sessions.

### Query Parameters

| Name | Type | Default | Validation |
|------|------|---------|------------|
| `limit` | integer | `50` | `1 <= limit <= CALL_AUDIT_MAX_SESSIONS` |

### Response 200

```json
{
  "generated_at": "2026-05-05T10:00:00Z",
  "count": 1,
  "limit": 50,
  "sessions": [
    {
      "session_id": "twilio_CA_TEST",
      "call_id": "CA_TEST",
      "source_input_mode": "twilio_call",
      "conversation_turns": [
        {
          "speaker": "caller",
          "text": "น้ำท่วมอยู่ที่หาดใหญ่",
          "created_at": "2026-05-05T09:59:30Z",
          "turn_index": 0
        }
      ],
      "timeline_events": [
        {
          "event_id": "evt_abc",
          "type": "caller.turn.transcribed",
          "speaker": "caller",
          "text": "น้ำท่วมอยู่ที่หาดใหญ่",
          "guardrail_warnings": [],
          "metadata": {
            "transcript_source": "mock"
          },
          "created_at": "2026-05-05T09:59:31Z"
        }
      ],
      "case_group": "flood",
      "recommended_team": "rescue",
      "triage_level": "YELLOW",
      "guardrail_warnings": [],
      "no_reply_prompt_count": 0,
      "off_topic_count": 0,
      "call_end_reason": "",
      "final_case_id": null,
      "created_at": "2026-05-05T09:59:00Z",
      "updated_at": "2026-05-05T09:59:31Z"
    }
  ]
}
```

### Response 404

Not used for list. Return an empty list when no sessions exist.

## GET /api/intake/sessions/{session_id}

Return one session by session id.

### Response 200

Response body is a `CallAuditSession`.

### Response 404

```json
{
  "detail": "Intake session not found."
}
```

## GET /api/intake/calls/{call_id}

Return one session by Twilio call id.

### Response 200

Response body is a `CallAuditSession`.

### Response 404

```json
{
  "detail": "Intake call session not found."
}
```

## Security and Redaction Rules

- Do not include `AZURE_SPEECH_KEY`, `AZURE_OPENAI_API_KEY`, `TWILIO_AUTH_TOKEN`, or full provider credentials.
- Do not include raw audio payloads or base64 media frames.
- If `CALL_AUDIT_LOG_TRANSCRIPTS=false`, omit or redact timeline `text` fields while retaining event metadata and timestamps.
- Keep `raw_provider_payload` out of audit responses unless it has been explicitly scrubbed.

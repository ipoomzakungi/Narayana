# Contract: Voice WebSocket Intake Payloads

## Scope

Existing WebSocket route paths remain unchanged:

```text
WS /ws/local-audio
WS /ws/telephony/twilio/{call_id}
```

Multi-turn intake is active only when `ENABLE_MULTI_TURN_INTAKE=true`. When disabled, the current `triage.case.created` behavior remains unchanged.

## Follow-Up Payload

When a committed transcript needs more information:

```json
{
  "type": "intake.followup",
  "session_id": "twilio_CA123",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่",
  "action": "ask_followup",
  "response_text": "มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?",
  "partial_state": {
    "collected_fields": {
      "incident_type": "flood",
      "location_text": "หาดใหญ่",
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
  "source_input_mode": "twilio_call",
  "call_metadata": {
    "provider": "twilio",
    "call_id": "CA123"
  }
}
```

Rules:
- No final case is created for this payload.
- `response_text` is text only; no TTS audio is generated.
- The frontend must display this payload in the debug console.

## Case-Created Payload With Intake Fields

Existing `triage.case.created` payload remains the final-case signal. New fields are additive:

```json
{
  "type": "triage.case.created",
  "session_id": "twilio_CA123",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
  "provider_mode": "mock",
  "transcript_source": "mock",
  "audio_ref": ".data/audio/twilio_CA123/turn_1.wav",
  "response_text": "รับทราบค่ะ ขอให้เจ้าหน้าที่ตรวจสอบทันที กรุณาอยู่ในที่ปลอดภัยถ้าทำได้",
  "warnings": [],
  "record": {
    "case": {
      "case_id": "case_abc123",
      "triage_level": "RED",
      "human_review_required": true,
      "status": "pending"
    },
    "session_id": "twilio_CA123",
    "source_provider": "mock",
    "case_group": "rescue",
    "recommended_team": "rescue",
    "conversation_summary": "Caller reported flood in Hat Yai; elderly person trapped upstairs with breathing difficulty."
  },
  "intake": {
    "action": "escalate_human_review",
    "case_group": "rescue",
    "recommended_team": "rescue",
    "missing_fields": ["people_affected"],
    "reason": "Caller reports flood, trapped elderly person, and breathing difficulty.",
    "guardrail_warnings": ["forced_red: breathing difficulty", "forced_red: trapped person"],
    "partial_state": {}
  },
  "source_input_mode": "twilio_call",
  "call_metadata": {
    "provider": "twilio",
    "call_id": "CA123"
  }
}
```

Compatibility:
- Existing frontend code that only reads `record.case` must still work.
- Older records may not contain `case_group`, `recommended_team`, `conversation_summary`, or `intake`.

# Contract: Intake Scope Guardrail Response

## Endpoint

`POST /api/intake/from-transcript`

## First Off-Topic Request

```json
{
  "session_id": "scope-demo",
  "transcript": "เล่าเรื่องตลกให้ฟังหน่อย",
  "language_hint": "th",
  "source_input_mode": "manual"
}
```

## First Off-Topic Response

```json
{
  "session_id": "scope-demo",
  "action": "ask_followup",
  "response_text": "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ",
  "partial_state": {
    "off_topic_count": 1,
    "redirect_count": 1,
    "call_end_recommended": false,
    "call_end_reason": ""
  },
  "human_review_required": false,
  "missing_fields": [],
  "guardrail_warnings": ["scope:off_topic_redirect"],
  "created_case": null
}
```

## Repeated Off-Topic Close Recommendation

After repeated off-topic turns:

```json
{
  "action": "ask_followup",
  "response_text": "ขออภัยค่ะ หากไม่มีเหตุที่ต้องการแจ้ง ระบบจะสิ้นสุดสายนี้นะคะ",
  "partial_state": {
    "off_topic_count": 3,
    "redirect_count": 3,
    "call_end_recommended": true,
    "call_end_reason": "repeated_off_topic"
  },
  "guardrail_warnings": ["scope:repeated_off_topic_close_recommended"],
  "created_case": null
}
```

## Emergency Override

If a later transcript contains emergency content:

```json
{
  "transcript": "ช่วยด้วย น้ำท่วม มีคนแก่หายใจลำบากติดอยู่ชั้นสอง"
}
```

Response must continue normal crisis intake or escalation and must include a warning similar to:

```json
{
  "guardrail_warnings": ["scope:emergency_override"]
}
```

## Rules

- Off-topic responses must not create a case by default.
- Emergency signals reset or bypass off-topic close recommendations.
- Existing response shape remains additive; old clients should tolerate new `partial_state` fields.

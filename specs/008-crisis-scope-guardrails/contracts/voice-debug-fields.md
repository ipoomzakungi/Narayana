# Contract: Voice Debug Scope Fields

## WebSocket Payload Additive Fields

Payloads related to intake or call lifecycle may include:

```json
{
  "off_topic_count": 1,
  "redirect_count": 1,
  "no_reply_prompt_count": 0,
  "call_end_recommended": false,
  "call_end_reason": "",
  "last_assistant_redirect": "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ",
  "guardrail_warnings": ["scope:off_topic_redirect"],
  "response_text": "..."
}
```

## Frontend Display Rules

- Show missing fields as `0`, `false`, or `-` for older records/payloads.
- Do not hide existing transcript, case, VAD, or TTS debug fields.
- Show `call_end_recommended` and `call_end_reason` prominently enough for operator debugging.
- Do not display secrets or raw audio payloads.

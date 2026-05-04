# Contract: Twilio No-Reply WebSocket Handling

## Route

`/ws/telephony/twilio/{call_id}`

Route path remains unchanged.

## No-Reply Prompt Output

After greeting and no caller speech for the configured threshold, the server sends Twilio media chunks through the existing TTS helper and may also emit a debug payload:

```json
{
  "type": "call.no_reply_prompt",
  "session_id": "twilio_CA123",
  "response_text": "ยังอยู่ในสายไหมคะ หากต้องการแจ้งเหตุ กรุณาเล่าสถานการณ์สั้น ๆ ได้เลยค่ะ",
  "no_reply_prompt_count": 1,
  "call_end_recommended": false
}
```

Twilio media event shape remains:

```json
{
  "event": "media",
  "streamSid": "MZ123",
  "media": {
    "payload": "<base64-mulaw-chunk>"
  }
}
```

## Final Close Output

After maximum no-reply prompts:

```json
{
  "type": "call.ending",
  "session_id": "twilio_CA123",
  "response_text": "หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ",
  "no_reply_prompt_count": 2,
  "call_end_recommended": true,
  "call_end_reason": "no_reply"
}
```

Then the WebSocket closes safely when possible.

## Rules

- No-reply lifecycle is active only when call lifecycle audio response is enabled through initial greeting or Twilio TTS response behavior.
- If caller media arrives, update last caller speech time and continue normal media handling.
- If TTS fails for no-reply prompt or final close, log warning and continue safe close behavior where applicable.
- No Twilio REST API hangup is required by default.

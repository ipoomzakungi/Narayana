# Contract: Twilio Speak-Back WebSocket Messages

## Existing Route

The route remains:

```text
WS /ws/telephony/twilio/{call_id}
```

## Input Requirement

The Twilio `start` event must provide or preserve a stream identifier:

```json
{
  "event": "start",
  "start": {
    "streamSid": "MZ123",
    "callSid": "CA123"
  }
}
```

## Normal JSON Payload First

For every processor payload, the backend still sends the existing JSON payload first:

```json
{
  "type": "intake.followup",
  "session_id": "twilio_CA123",
  "response_text": "มีใครบาดเจ็บไหมคะ?"
}
```

or:

```json
{
  "type": "triage.case.created",
  "session_id": "twilio_CA123",
  "response_text": "รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบต่อค่ะ"
}
```

## Outbound Media Event

When speak-back is enabled, configured, and response text is safe/non-empty, backend sends one or more Twilio media events:

```json
{
  "event": "media",
  "streamSid": "MZ123",
  "media": {
    "payload": "<base64-mulaw-8khz-audio>"
  }
}
```

## Outbound Mark Event

After media chunks:

```json
{
  "event": "mark",
  "streamSid": "MZ123",
  "mark": {
    "name": "narayana_tts_20260503T120000Z"
  }
}
```

## Failure Behavior

- If TTS is disabled: send no outbound Twilio media or mark.
- If stream ID is missing: send normal JSON payloads, log warning, skip speak-back.
- If TTS is unconfigured or fails: send normal JSON payloads, log warning, keep call alive.
- Never log the `media.payload` value.

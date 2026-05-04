# Contract: Twilio Initial Greeting WebSocket

## Route

`/ws/telephony/twilio/{call_id}`

Route path remains unchanged.

## Start Event Input

```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "callSid": "CA123",
    "streamSid": "MZ123",
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  }
}
```

## Disabled Greeting Output

When `ENABLE_TWILIO_INITIAL_GREETING=false`, output remains the existing session start payload only:

```json
{
  "type": "session.started",
  "session_id": "twilio_CA123",
  "provider_mode": "mock",
  "state": "listening",
  "source_input_mode": "twilio_call",
  "call_metadata": {}
}
```

No greeting `media` or `mark` event is sent.

## Enabled Greeting Output

When `ENABLE_TWILIO_INITIAL_GREETING=true` and TTS is configured, the WebSocket sends the normal `session.started` payload first, then one or more Twilio media events, then a mark:

```json
{
  "event": "media",
  "streamSid": "MZ123",
  "media": {
    "payload": "<base64-mulaw-chunk>"
  }
}
```

```json
{
  "event": "mark",
  "streamSid": "MZ123",
  "mark": {
    "name": "narayana_initial_greeting"
  }
}
```

## Failure Behavior

- Missing `streamSid`: log `greeting.failed`; send no greeting media; continue listening.
- TTS unconfigured: log `greeting.failed`; send no greeting media; continue listening.
- TTS synthesis failure: log `greeting.failed`; send no greeting media; continue listening.
- WebSocket send failure during greeting: log `greeting.failed` when possible; do not convert the greeting failure into case or intake failure.

## Logging Contract

Expected logs:

- `greeting.started session_id=<id> call_id=<id> streamSid=<id> text_length=<n>`
- `greeting.completed session_id=<id> call_id=<id> streamSid=<id> chunk_count=<n> estimated_duration_ms=<n>`
- `greeting.failed session_id=<id> call_id=<id> streamSid=<id> reason=<reason>`

Logs must not include secrets or raw audio payloads.

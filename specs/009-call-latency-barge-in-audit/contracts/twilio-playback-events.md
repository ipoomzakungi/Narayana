# Contract: Twilio Playback, Mark, and Barge-In Events

The public Twilio route paths remain unchanged:

- `POST /api/telephony/twilio/incoming-call`
- `WS /ws/telephony/twilio/{call_id}`

## Inbound Twilio Events

### start

The route captures `streamSid`, call metadata, and initializes assistant playback state.

```json
{
  "event": "start",
  "streamSid": "MZ123",
  "start": {
    "callSid": "CA_TEST",
    "streamSid": "MZ123",
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    },
    "customParameters": {
      "From": "+66800000000",
      "To": "+16082005400",
      "FromCountry": "TH"
    }
  }
}
```

### media

Inbound media is normalized to `AudioFrame`. While assistant playback is active, `assistant_is_speaking=true` must be passed into the normalizer/turn path so VAD can detect barge-in.

```json
{
  "event": "media",
  "streamSid": "MZ123",
  "sequenceNumber": "42",
  "media": {
    "chunk": "12",
    "timestamp": "240",
    "payload": "<base64-mulaw>"
  }
}
```

### mark

Twilio returns the mark after outbound audio with the same mark name has completed.

```json
{
  "event": "mark",
  "streamSid": "MZ123",
  "mark": {
    "name": "narayana_initial_greeting"
  }
}
```

Expected behavior:

- If the mark matches the active mark, set assistant playback completed.
- Record `tts.completed` or `greeting.completed`.
- Start or resume no-reply timing from completion.
- If mark is unknown or stale, log a warning and do not crash the socket.

## Outbound Twilio Events

### media

Existing outbound media shape remains unchanged.

```json
{
  "event": "media",
  "streamSid": "MZ123",
  "media": {
    "payload": "<base64-mulaw>"
  }
}
```

### mark

Existing outbound mark shape remains unchanged.

```json
{
  "event": "mark",
  "streamSid": "MZ123",
  "mark": {
    "name": "narayana_tts_20260505T100000Z"
  }
}
```

### clear

On barge-in, send Twilio clear for the current stream.

```json
{
  "event": "clear",
  "streamSid": "MZ123"
}
```

Expected behavior:

- Send only when `streamSid` is known and assistant playback is active.
- Log `barge_in.clear_sent` after successful send.
- Mark the current assistant response interrupted.
- Stop remaining unsent TTS chunks when possible.

## Backend Debug Payloads

Existing WebSocket debug payloads may be extended with these fields:

```json
{
  "type": "debug.event",
  "event": {
    "event_type": "barge_in.detected",
    "session_id": "twilio_CA_TEST",
    "metadata": {
      "sequence": 43,
      "active_mark_name": "narayana_tts_20260505T100000Z",
      "clear_sent": true
    }
  }
}
```

```json
{
  "type": "assistant.playback.completed",
  "session_id": "twilio_CA_TEST",
  "call_id": "CA_TEST",
  "stream_sid": "MZ123",
  "mark_name": "narayana_tts_20260505T100000Z",
  "purpose": "tts"
}
```

## No-Reply Interaction

- No-reply timers must not count while assistant playback is active.
- First no-reply wait starts after the initial greeting mark is received.
- Follow-up no-reply waits start after the latest assistant TTS mark is received.
- If marks are missing, use a logged fallback completion timeout instead of sending repeated early prompts.

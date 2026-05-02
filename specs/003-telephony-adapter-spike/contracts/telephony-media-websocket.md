# Contract: Twilio Media WebSocket

## Endpoint

`/ws/telephony/twilio/{call_id}`

Accepts Twilio Media Stream JSON messages, normalizes audio into Narayana `AudioFrame` objects, and sends frames into `AudioSessionProcessor`.

## Client Messages

### Connected

```json
{
  "event": "connected",
  "protocol": "Call",
  "version": "1.0.0"
}
```

Behavior:

- Accept and optionally emit a debug acknowledgement.

### Start

```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "callSid": "CA123",
    "streamSid": "MZ123",
    "accountSid": "AC123",
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    },
    "customParameters": {}
  }
}
```

Behavior:

- Create or enrich `CallMetadata`.
- Emit a `session.started` style payload with `source_input_mode="twilio_call"`.

### Media

```json
{
  "event": "media",
  "sequenceNumber": "2",
  "media": {
    "track": "inbound",
    "chunk": "1",
    "timestamp": "20",
    "payload": "base64-mulaw-audio"
  },
  "streamSid": "MZ123"
}
```

Normalization output:

```json
{
  "type": "audio.frame",
  "session_id": "twilio_CA123",
  "sequence": 2,
  "timestamp_ms": 20,
  "encoding": "pcm16",
  "sample_rate_hz": 8000,
  "channels": 1,
  "duration_ms": 20,
  "audio_base64": "base64-pcm16-audio",
  "assistant_is_speaking": false
}
```

Behavior:

- Decode base64 provider payload.
- Convert G.711 mu-law bytes to PCM16 mono bytes.
- Pass the resulting `AudioFrame` to `AudioSessionProcessor.process_frame(...)`.
- Forward every processor payload back to the WebSocket client.

### Stop

```json
{
  "event": "stop",
  "sequenceNumber": "99",
  "stop": {
    "callSid": "CA123"
  },
  "streamSid": "MZ123"
}
```

Behavior:

- Close the telephony session cleanly.
- Do not create a case unless a turn was already committed by VAD.

## Final Case Payload

Phone-originated final payloads include the existing case-created fields plus:

```json
{
  "source_input_mode": "twilio_call",
  "call_metadata": {
    "provider": "twilio",
    "call_id": "CA123",
    "from_number": "+15551234567",
    "to_number": "+15557654321",
    "country": "US",
    "codec": "mulaw",
    "sample_rate": 8000,
    "started_at": "2026-05-02T00:00:00Z"
  }
}
```

## Error Behavior

- Malformed JSON returns an error payload and keeps the socket open when possible.
- Unsupported codecs return an error payload and skip that frame.
- Missing provider credentials do not prevent simulated WebSocket tests.

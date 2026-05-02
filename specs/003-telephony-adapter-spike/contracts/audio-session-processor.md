# Contract: AudioSessionProcessor

`AudioSessionProcessor` is the internal contract that prevents local microphone, Twilio, and future ACS ingress from creating separate audio pipelines.

## Construction

Inputs:

- `settings`: current `Settings`.
- `session_id`: Narayana session id.
- `provider_mode`: optional requested `ProviderMode`.
- `source_input_mode`: optional source label, default `local_mic`.
- `call_metadata`: optional `CallMetadata` for phone-originated sessions.

Owned services:

- `TurnManager`
- `AudioBufferService`
- `get_voice_provider(settings, provider_mode)`
- `apply_safety_rules(...)`
- `get_case_repository(settings)`

## Methods

### `process_frame(frame: AudioFrame) -> list[dict]`

Processes one normalized PCM16 `AudioFrame`.

Outputs:

- Zero or more `debug.event` payloads.
- On committed turn, one `triage.case.created` payload after provider processing and case persistence.

Failure behavior:

- Validation and buffer errors return an error payload suitable for WebSocket clients.
- Provider failures should rely on provider fallback behavior and safety rules.
- The processor must not close WebSockets directly.

### `assistant_playback_started() -> dict`

Marks the assistant as speaking and returns an `ai.response.started` debug event payload.

### `assistant_playback_completed() -> dict`

Marks the assistant as not speaking and returns an `ai.response.completed` debug event payload.

## Final Case Payload

The `triage.case.created` payload preserves the existing local microphone contract and may add metadata:

```json
{
  "type": "triage.case.created",
  "session_id": "session_123",
  "transcript": "recognized caller transcript",
  "provider_mode": "mock",
  "transcript_source": "mock",
  "audio_ref": ".data/audio/session_123/turn_abc.wav",
  "response_text": "short safe response",
  "warnings": [],
  "record": {},
  "source_input_mode": "twilio_call",
  "call_metadata": {}
}
```

Rules:

- `source_input_mode` and `call_metadata` are optional for local microphone compatibility.
- Phone-originated sessions must include both fields.
- Safety rules are applied before the case is persisted.

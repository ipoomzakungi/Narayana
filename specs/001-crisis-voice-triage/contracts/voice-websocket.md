# Voice WebSocket Contract

## Endpoint

```text
ws://localhost:8000/ws/voice
```

Cloud deployments may expose the same path behind the backend domain.

## Audio Format

- Encoding: PCM signed 16-bit little-endian
- Channels: mono
- Sample rate: 16 kHz for V0 default
- Frame duration: 20 ms
- Frame payload size: 640 bytes before base64 encoding
- Caller audio must pass through backend VAD/turn management before AI interpretation.

## Client Events

### `session.start`

Starts a local microphone intake session.

```json
{
  "type": "session.start",
  "session_id": "voice_123",
  "language_hint": "th-TH",
  "audio": {
    "encoding": "pcm16",
    "sample_rate_hz": 16000,
    "channels": 1,
    "frame_ms": 20
  },
  "use_mock_services": true
}
```

### `audio.frame`

Sends one audio frame. `assistant_is_speaking` lets the server mark barge-in when speech is detected during playback.

```json
{
  "type": "audio.frame",
  "session_id": "voice_123",
  "sequence": 42,
  "timestamp_ms": 840,
  "assistant_is_speaking": false,
  "audio_base64": "..."
}
```

### `audio.end`

Indicates that the browser stopped microphone capture or the demo operator ended input.

```json
{
  "type": "audio.end",
  "session_id": "voice_123"
}
```

### `assistant.playback_started`

Allows backend debug state to reflect assistant audio playback.

```json
{
  "type": "assistant.playback_started",
  "session_id": "voice_123",
  "turn_id": "turn_assistant_1"
}
```

### `assistant.playback_stopped`

Allows backend debug state to return to listening after playback.

```json
{
  "type": "assistant.playback_stopped",
  "session_id": "voice_123",
  "turn_id": "turn_assistant_1",
  "reason": "completed"
}
```

### `session.close`

Closes the session.

```json
{
  "type": "session.close",
  "session_id": "voice_123"
}
```

## Server Events

### `vad.state`

Reports the current debug state.

```json
{
  "type": "vad.state",
  "session_id": "voice_123",
  "state": "speech",
  "timestamp": "2026-05-02T10:00:01Z"
}
```

Allowed state values:

- `silence`
- `speech`
- `listening`
- `thinking`
- `speaking`

### `turn.started`

Emitted when VAD detects the start of caller speech.

```json
{
  "type": "turn.started",
  "session_id": "voice_123",
  "turn_id": "turn_caller_1",
  "pre_speech_padding_ms": 200,
  "timestamp": "2026-05-02T10:00:01Z"
}
```

### `turn.ended`

Emitted after the configured silence threshold completes the caller turn.

```json
{
  "type": "turn.ended",
  "session_id": "voice_123",
  "turn_id": "turn_caller_1",
  "silence_threshold_ms": 750,
  "duration_ms": 3200,
  "timestamp": "2026-05-02T10:00:04Z"
}
```

### `barge_in`

Emitted when caller speech is detected while assistant playback is active.

```json
{
  "type": "barge_in",
  "session_id": "voice_123",
  "interrupted_turn_id": "turn_assistant_1",
  "caller_turn_id": "turn_caller_2",
  "timestamp": "2026-05-02T10:00:05Z"
}
```

### `transcript.partial`

Optional provider-specific partial transcript.

```json
{
  "type": "transcript.partial",
  "session_id": "voice_123",
  "turn_id": "turn_caller_1",
  "text": "น้ำท่วมอยู่ที่หาดใหญ่",
  "language": "th-TH",
  "confidence": 0.82
}
```

### `transcript.final`

Final caller transcript for a completed turn.

```json
{
  "type": "transcript.final",
  "session_id": "voice_123",
  "turn_id": "turn_caller_1",
  "text": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
  "language": "th-TH",
  "confidence": 0.9
}
```

### `triage.result`

Triage extraction result before or after case creation.

```json
{
  "type": "triage.result",
  "session_id": "voice_123",
  "case_id": "case_001",
  "triage_level": "RED",
  "confidence": 0.92,
  "human_review_required": true,
  "triage_reason": "Flood with trapped elderly person and breathing difficulty."
}
```

### `case.created`

Emitted when the backend creates the structured crisis case.

```json
{
  "type": "case.created",
  "session_id": "voice_123",
  "case_id": "case_001"
}
```

### `assistant.text`

Assistant response text for display and optional speech synthesis.

```json
{
  "type": "assistant.text",
  "session_id": "voice_123",
  "turn_id": "turn_assistant_1",
  "text": "รับทราบค่ะ ระบบจะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบ โปรดอยู่ในที่ปลอดภัยถ้าทำได้",
  "script_id": "thai_general_waiting_red"
}
```

### `debug.event`

Timestamped diagnostic event mirrored to the debug console.

```json
{
  "type": "debug.event",
  "session_id": "voice_123",
  "event_type": "ai_request",
  "timestamp": "2026-05-02T10:00:04Z",
  "metadata": {
    "provider": "mock",
    "turn_id": "turn_caller_1"
  }
}
```

### `error`

Recoverable or terminal session error. If provider credentials are missing, the server should report fallback to mock services where possible.

```json
{
  "type": "error",
  "session_id": "voice_123",
  "error": "provider_unavailable",
  "message": "Azure voice provider is unavailable; mock provider is active.",
  "recoverable": true
}
```

## Turn Management Rules

- `session.start` sets state to `listening`.
- Speech energy above threshold sets state to `speech` and starts a caller turn.
- 600-900 ms of silence ends a turn; V0 default is 750 ms.
- After a completed turn, state becomes `thinking` while the voice provider and triage service run.
- Assistant output sets state to `speaking`.
- Caller speech during `speaking` emits `barge_in`, stops or yields assistant playback, and starts a new caller turn.
- Every state change, completed turn, barge-in, provider request, provider response, and error must be logged as a debug event.

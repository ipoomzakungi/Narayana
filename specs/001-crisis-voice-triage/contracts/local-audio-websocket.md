# Local Audio WebSocket Contract

## Endpoint

```text
ws://localhost:8000/ws/local-audio
```

## Audio Contract

- Encoding: PCM16 little-endian
- Channels: mono
- Target sample rate: 16 kHz
- Frame duration: 20 ms
- Frame payload: base64 PCM bytes

## Client Events

### `session.start`

```json
{
  "type": "session.start",
  "session_id": "voice_123",
  "language_hint": "th",
  "provider_mode": "mock",
  "audio": {
    "encoding": "pcm16",
    "sample_rate_hz": 16000,
    "channels": 1,
    "frame_ms": 20
  }
}
```

### `audio.frame`

```json
{
  "type": "audio.frame",
  "session_id": "voice_123",
  "sequence": 12,
  "timestamp_ms": 240,
  "assistant_is_speaking": false,
  "audio_base64": "..."
}
```

### `assistant.playback_started`

```json
{
  "type": "assistant.playback_started",
  "session_id": "voice_123"
}
```

### `assistant.playback_stopped`

```json
{
  "type": "assistant.playback_stopped",
  "session_id": "voice_123",
  "reason": "completed"
}
```

### `session.close`

```json
{
  "type": "session.close",
  "session_id": "voice_123"
}
```

## Server Events

### `audio.frame.received`

```json
{
  "type": "audio.frame.received",
  "session_id": "voice_123",
  "sequence": 12,
  "timestamp": "2026-05-02T10:00:00Z"
}
```

### `vad.speech.start`

```json
{
  "type": "vad.speech.start",
  "session_id": "voice_123",
  "state": "speech",
  "timestamp": "2026-05-02T10:00:01Z"
}
```

### `vad.speech.end`

```json
{
  "type": "vad.speech.end",
  "session_id": "voice_123",
  "state": "silence",
  "silence_ms": 750,
  "timestamp": "2026-05-02T10:00:04Z"
}
```

### `turn.committed`

```json
{
  "type": "turn.committed",
  "session_id": "voice_123",
  "turn_id": "turn_001",
  "duration_ms": 3200,
  "pre_speech_padding_ms": 200,
  "timestamp": "2026-05-02T10:00:04Z"
}
```

### `ai.request.started`

```json
{
  "type": "ai.request.started",
  "session_id": "voice_123",
  "turn_id": "turn_001",
  "provider_mode": "mock",
  "timestamp": "2026-05-02T10:00:04Z"
}
```

### `ai.response.started`

```json
{
  "type": "ai.response.started",
  "session_id": "voice_123",
  "provider_mode": "mock",
  "timestamp": "2026-05-02T10:00:05Z"
}
```

### `ai.response.completed`

```json
{
  "type": "ai.response.completed",
  "session_id": "voice_123",
  "provider_mode": "mock",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
  "timestamp": "2026-05-02T10:00:06Z"
}
```

### `barge_in.detected`

```json
{
  "type": "barge_in.detected",
  "session_id": "voice_123",
  "timestamp": "2026-05-02T10:00:07Z"
}
```

### `triage.case.created`

```json
{
  "type": "triage.case.created",
  "session_id": "voice_123",
  "case": {
    "case_id": "case_001",
    "language": "th",
    "incident_type": "flood",
    "triage_level": "RED",
    "confidence": 0.92,
    "location_text": "หาดใหญ่",
    "people_affected": null,
    "injuries": "elderly person breathing difficulty",
    "immediate_needs": ["rescue", "medical"],
    "caller_phone_optional": null,
    "ai_summary": "Flood in Hat Yai with an elderly person trapped on the second floor and having breathing difficulty.",
    "triage_reason": "Forced RED because caller reports trapped person and breathing difficulty.",
    "human_review_required": true,
    "missing_fields": [],
    "created_at": "2026-05-02T10:00:06Z",
    "updated_at": "2026-05-02T10:00:06Z",
    "status": "pending"
  }
}
```

### `error`

```json
{
  "type": "error",
  "session_id": "voice_123",
  "error": "provider_unavailable",
  "message": "Azure provider unavailable; mock provider fallback is active.",
  "recoverable": true
}
```

## Turn Rules

- `session.start` enters `listening`.
- Speech energy above threshold emits `vad.speech.start`.
- Silence for 600-900 ms emits `vad.speech.end` and `turn.committed`.
- `turn.committed` triggers provider request.
- Provider output is passed through safety rules before `triage.case.created`.
- Speech during assistant playback emits `barge_in.detected`.

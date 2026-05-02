# Contract: Local Audio WebSocket Enhancements

Endpoint remains:

```text
WebSocket /ws/local-audio
```

## Incoming Messages

Existing messages remain valid:

- `session.start`
- `audio.frame`
- `assistant.playback.started`
- `assistant.playback.completed`
- `session.close`

`audio.frame` continues to carry PCM16 mono 20 ms frame data:

```json
{
  "type": "audio.frame",
  "session_id": "session_123",
  "sequence": 12,
  "timestamp_ms": 240,
  "encoding": "pcm16",
  "sample_rate_hz": 16000,
  "channels": 1,
  "duration_ms": 20,
  "audio_base64": "...",
  "assistant_is_speaking": false
}
```

## Debug Events

Existing debug events remain valid. `turn.committed` should include the turn identifier and may include audio artifact metadata once written:

```json
{
  "type": "debug.event",
  "event": {
    "event_type": "turn.committed",
    "state": "thinking",
    "metadata": {
      "turn_id": "turn_abc",
      "audio_ref": ".data/audio/session_123/turn_abc.wav",
      "audio_debug_id": "turn_abc"
    }
  }
}
```

## Case Created Message

`triage.case.created` must include transcript provenance and warning metadata:

```json
{
  "type": "triage.case.created",
  "session_id": "session_123",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
  "provider_mode": "azure_speech_openai",
  "transcript_source": "azure_speech_stt",
  "audio_ref": ".data/audio/session_123/turn_abc.wav",
  "response_text": null,
  "warnings": [],
  "record": {
    "case": {
      "triage_level": "RED",
      "human_review_required": true,
      "status": "pending"
    }
  }
}
```

## Fallback Case Created Message

When speech recognition fails, the message still creates a review-required case and exposes warnings:

```json
{
  "type": "triage.case.created",
  "session_id": "session_123",
  "transcript": "",
  "provider_mode": "azure_speech_openai",
  "transcript_source": "fallback",
  "audio_ref": ".data/audio/session_123/turn_abc.wav",
  "response_text": null,
  "warnings": [
    "Azure Speech did not return a usable transcript."
  ],
  "record": {
    "case": {
      "triage_level": "YELLOW",
      "confidence": 0.35,
      "human_review_required": true,
      "missing_fields": ["transcript", "location_text"],
      "status": "pending"
    }
  }
}
```

## Compatibility

- Existing clients that ignore unknown fields remain compatible.
- Existing mock WebSocket tests should continue to pass.
- No Twilio or ACS WebSocket messages are added for this feature.

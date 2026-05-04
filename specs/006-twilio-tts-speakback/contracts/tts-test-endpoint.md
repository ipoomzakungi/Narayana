# Contract: POST /api/tts/test

## Purpose

Validate Azure Speech TTS readiness without placing a Twilio call and without returning raw audio payloads.

## Request

```http
POST /api/tts/test
Content-Type: application/json
```

```json
{
  "text": "ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?"
}
```

Optional:

```json
{
  "text": "ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?",
  "language": "th",
  "voice": "th-TH-PremwadeeNeural"
}
```

## Response: Configured

```json
{
  "configured": true,
  "voice": "th-TH-PremwadeeNeural",
  "audio_format": "mulaw_8khz",
  "payload_count": 3,
  "total_bytes": 12345,
  "estimated_duration_ms": 1540,
  "warnings": [],
  "missing_variables": []
}
```

## Response: Unconfigured

```json
{
  "configured": false,
  "voice": "th-TH-PremwadeeNeural",
  "audio_format": "mulaw_8khz",
  "payload_count": 0,
  "total_bytes": 0,
  "estimated_duration_ms": 0,
  "warnings": ["Azure Speech TTS is not configured."],
  "missing_variables": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
}
```

## Rules

- Response must not include raw audio payloads by default.
- Unsafe text is sanitized before synthesis.
- Overlong text is shortened or replaced before synthesis.
- Missing credentials return a safe metadata response, not a server crash.

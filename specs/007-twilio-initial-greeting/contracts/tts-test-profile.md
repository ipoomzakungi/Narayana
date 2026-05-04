# Contract: TTS Test Greeting Profile

## Endpoint

`POST /api/tts/test`

## Request

```json
{
  "text": "สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ",
  "profile": "greeting"
}
```

## Successful Configured Response

```json
{
  "configured": true,
  "voice": "th-TH-PremwadeeNeural",
  "audio_format": "mulaw_8khz",
  "profile": "greeting",
  "ssml_enabled": true,
  "payload_count": 12,
  "total_bytes": 1920,
  "estimated_duration_ms": 240,
  "warnings": [],
  "missing_variables": []
}
```

## Unconfigured Response

```json
{
  "configured": false,
  "voice": "th-TH-PremwadeeNeural",
  "audio_format": "mulaw_8khz",
  "profile": "greeting",
  "ssml_enabled": true,
  "payload_count": 0,
  "total_bytes": 0,
  "estimated_duration_ms": 0,
  "warnings": ["Azure Speech TTS is not configured."],
  "missing_variables": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
}
```

## Rules

- `profile="greeting"` must be accepted by request validation.
- The response must not include raw audio payloads.
- Unsafe greeting text must be sanitized before synthesis and may produce warnings.
- Tests must mock configured synthesis and must not require Azure credentials.

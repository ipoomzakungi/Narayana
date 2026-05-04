# Contract: GET /api/health/azure TTS Fields

## Purpose

Expose speak-back readiness alongside existing Azure health information.

## Additive Response Fields

Existing fields stay unchanged. Add:

```json
{
  "twilio_tts_response_enabled": false,
  "azure_speech_tts_configured": false,
  "azure_speech_voice": "th-TH-PremwadeeNeural"
}
```

## Rules

- `twilio_tts_response_enabled` reflects only the speak-back feature flag.
- `azure_speech_tts_configured` is true when Azure Speech key and region are configured.
- `azure_speech_voice` reflects the selected configured voice or default voice.
- Health must remain available when TTS is disabled or unconfigured.

# Contract: Azure Health Greeting Fields

## Endpoint

`GET /api/health/azure`

## Additive Response Fields

```json
{
  "twilio_initial_greeting_enabled": true,
  "twilio_initial_greeting_text_configured": true,
  "twilio_initial_greeting_profile": "greeting"
}
```

## Rules

- Fields are additive and must not remove existing health fields.
- `twilio_initial_greeting_enabled` reports the effective opt-in setting.
- `twilio_initial_greeting_text_configured` is `true` when greeting text is non-blank after trimming.
- `twilio_initial_greeting_profile` reports the selected configured profile string.
- No secret values or greeting audio payloads are returned.

# Quickstart: Call Latency, Barge-In, and Audit Debugging

## Local Gates

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

## Demo Warm Backend

Keep the Azure Container App warm before a live demo:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --min-replicas 1 `
  --max-replicas 1
```

Return to lower-cost mode after the demo:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --min-replicas 0 `
  --max-replicas 1
```

With `min-replicas 0`, the next call after inactivity can experience an Azure Container Apps cold start.

## Demo Latency Environment

Use faster demo turn settings:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --set-env-vars `
    TURN_SILENCE_THRESHOLD_MS=500 `
    TURN_PRE_SPEECH_PADDING_MS=200 `
    VAD_ENERGY_THRESHOLD=0.015 `
    MIN_SPEECH_MS=300 `
    CALL_NO_REPLY_SECONDS=15 `
    CALL_NO_REPLY_PROMPT_SECONDS=15 `
    CALL_MAX_NO_REPLY_PROMPTS=2 `
    CALL_AUDIT_ENABLED=true `
    CALL_AUDIT_LOG_TRANSCRIPTS=true `
    CALL_AUDIT_MAX_SESSIONS=50
```

Keep existing demo safety settings unchanged unless intentionally testing another mode:

```text
USE_MOCK_SERVICES=true
ENABLE_MULTI_TURN_INTAKE=true
ENABLE_TWILIO_TTS_RESPONSE=true
ENABLE_TWILIO_INITIAL_GREETING=true
```

## Barge-In Test

1. Call the configured Twilio number.
2. Wait for the initial greeting to begin.
3. Speak while the greeting is still playing, for example: `น้ำท่วม หาดใหญ่ มีคนติดอยู่`.
4. Verify logs contain:
   - `barge_in.detected`
   - `barge_in.clear_sent`
   - `caller.turn.committed`
   - `caller.turn.transcribed`
5. Verify the call continues and the interrupted assistant response does not produce duplicate answers.

## Mark / No-Reply Test

1. Call the Twilio number and stay silent.
2. Confirm no no-reply prompt plays while the greeting is still playing.
3. Confirm the no-reply prompt starts only after the greeting mark is received or fallback completion is logged.
4. Confirm repeated silence plays the final close message and closes safely.

## Call Audit API Smoke Test

```powershell
$base = "https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io"
Invoke-RestMethod "$base/api/intake/sessions?limit=10"
Invoke-RestMethod "$base/api/intake/sessions/twilio_CA_TEST"
Invoke-RestMethod "$base/api/intake/calls/CA_TEST"
```

## Frontend Audit Page

Static Web Apps dashboard path:

```text
/call-audit
```

Expected view:

- Recent sessions list
- Session detail timeline
- Caller transcripts and assistant response text
- TTS started/completed/interrupted events
- Barge-in and no-reply events
- Guardrail warnings
- Final case id or no-case state

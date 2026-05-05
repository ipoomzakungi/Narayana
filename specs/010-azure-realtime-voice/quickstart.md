# Quickstart: Azure Realtime Voice Provider Spike

## Default Safety Check

Realtime voice is disabled by default.

```powershell
$env:ENABLE_REALTIME_VOICE = "false"
$env:REALTIME_PROVIDER = "none"
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

Expected:

- Backend starts with no Azure realtime credentials.
- Existing Twilio simulated media tests pass.
- Existing local mic/manual transcript behavior remains unchanged.

## Local Mock Realtime Validation

Use mocked provider tests before trying real Azure credentials.

```powershell
pytest tests/unit/test_realtime_provider_selection.py `
  tests/unit/test_realtime_voice_provider.py `
  tests/unit/test_realtime_fallback.py `
  tests/unit/test_telephony_config.py `
  tests/unit/test_twilio_routes.py `
  tests/integration/test_twilio_media_flow.py
```

Expected:

- `REALTIME_PROVIDER=none` selects no realtime provider.
- Missing Azure realtime settings trigger fallback.
- Mocked realtime output emits Twilio-compatible media event shapes.
- Existing Twilio media flow still passes with realtime disabled.

## Manual Azure OpenAI GPT Realtime Setup

Only run this after a supported Azure realtime model deployment exists.

Required environment:

```powershell
$env:ENABLE_REALTIME_VOICE = "true"
$env:REALTIME_PROVIDER = "azure_openai_realtime"
$env:AZURE_REALTIME_ENDPOINT = "https://<resource>.openai.azure.com"
$env:AZURE_REALTIME_API_KEY = "<secret>"
$env:AZURE_REALTIME_DEPLOYMENT = "<gpt-realtime-deployment>"
$env:AZURE_REALTIME_API_VERSION = "2025-04-01-preview"
```

Region warning:

- Microsoft documentation currently describes GPT realtime model availability through supported realtime regions/deployments, with examples that include East US 2 and Sweden Central. Do not assume the existing Narayana Container App region has a realtime deployment.
- The WebSocket endpoint format differs for GA versus preview realtime APIs. Mixing path/query formats can produce 404 responses.

Source:

- [Azure OpenAI GPT Realtime audio overview](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio)
- [Azure OpenAI GPT Realtime via WebSockets](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio-websockets)

## Manual Azure Voice Live Setup

Only run this after an eligible Microsoft Foundry or Speech in Foundry Tools resource is available.

Required environment:

```powershell
$env:ENABLE_REALTIME_VOICE = "true"
$env:REALTIME_PROVIDER = "azure_voice_live"
$env:AZURE_VOICE_LIVE_ENDPOINT = "wss://<resource>.services.ai.azure.com/voice-live/realtime?api-version=2025-10-01"
$env:AZURE_VOICE_LIVE_MODEL = "gpt-realtime"
```

Source:

- [Voice Live API how-to](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)

## Deploy-Time Safety

For the current demo backend, keep realtime disabled until manual tests pass:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --set-env-vars ENABLE_REALTIME_VOICE=false REALTIME_PROVIDER=none
```

When enabling a manual spike, set realtime secrets through Container App secrets, not tracked files.

## Expected Logs

Realtime active path should log:

- `realtime.connected`
- `realtime.audio.input.sent`
- `realtime.audio.output.received`
- `realtime.response.started`
- `realtime.response.completed`

Fallback path should log:

- `realtime.error`
- `realtime.fallback`

Existing logs must remain available for comparison:

- `caller.turn.committed`
- `caller.turn.transcribed`
- `intake.followup`
- `assistant.response`
- `tts.started`
- `tts.completed`

## Manual Twilio Test

1. Keep backend warm if needed:

   ```powershell
   az containerapp update --name narayana-api --resource-group rg-narayana-demo --min-replicas 1 --max-replicas 1
   ```

2. Enable realtime provider only after credentials are configured.
3. Call the Twilio test number.
4. Speak a short Thai crisis phrase.
5. Watch logs for realtime events and `latency_ms`.
6. If realtime fails, verify the current turn-based path still creates/follows up on the case.

## Final Verification Gates

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

No gate should require real Azure realtime credentials.

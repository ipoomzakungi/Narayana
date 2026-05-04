# Quickstart: Twilio Initial Greeting

## Local Test With Mocked Services

1. Keep default settings and run the existing tests:

   ```powershell
   python -m compileall app scripts
   pytest
   cd frontend
   npm test
   npm run build
   ```

2. Verify disabled-by-default behavior in tests:

   ```powershell
   pytest tests\integration\test_twilio_media_flow.py tests\unit\test_twilio_routes.py
   ```

3. Verify the manual TTS test accepts the greeting profile without cloud credentials:

   ```powershell
   Invoke-RestMethod `
     -Method Post `
     -Uri "http://localhost:8000/api/tts/test" `
     -ContentType "application/json" `
     -Body '{"text":"สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ","profile":"greeting"}'
   ```

   Without Azure Speech credentials, the response should report `configured=false` and must not return raw audio payloads.

## Azure Container App Demo Settings

For the first real-call greeting test, keep mock mode and enable only the greeting/TTS behavior:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --set-env-vars `
    USE_MOCK_SERVICES=true `
    ENABLE_MULTI_TURN_INTAKE=true `
    ENABLE_TWILIO_TTS_RESPONSE=true `
    ENABLE_TWILIO_INITIAL_GREETING=true `
    TWILIO_INITIAL_GREETING_TEXT="สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ" `
    TWILIO_INITIAL_GREETING_PROFILE=greeting `
    TTS_RATE_GREETING=-5% `
    TTS_PITCH_GREETING=0%
```

Azure Speech secret settings must already be configured as Container App secrets. Do not print or commit keys.

## Health Check

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/health/azure"
```

Expected greeting-related fields:

- `twilio_initial_greeting_enabled`
- `twilio_initial_greeting_text_configured`
- `twilio_initial_greeting_profile`

## TTS Readiness Check

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ","profile":"greeting"}'
```

Expected when configured:

- `configured=true`
- `profile=greeting`
- `voice=th-TH-PremwadeeNeural`
- `audio_format=mulaw_8khz`
- `payload_count` greater than zero

## Real Twilio Call Check

1. Confirm Twilio webhook still points to:

   ```text
   https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/telephony/twilio/incoming-call
   ```

2. Call the Twilio test number.
3. Confirm the caller hears the greeting once before speaking.
4. Speak a short crisis scenario.
5. Check logs for:

   ```text
   greeting.started
   greeting.completed
   tts.started
   tts.completed
   ```

Logs must not include secrets or raw audio payloads.

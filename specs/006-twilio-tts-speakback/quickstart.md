# Quickstart: Optional Twilio TTS Speak-Back

## 1. Default Regression Mode

Speak-back is disabled by default:

```powershell
$env:ENABLE_TWILIO_TTS_RESPONSE="false"
pytest tests/integration/test_twilio_media_flow.py
pytest tests/integration/test_mock_local_mic_flow.py
```

Expected:
- Existing Twilio simulated flow still emits normal JSON/debug/case payloads.
- No Azure Speech TTS credentials are required.
- No outbound Twilio media events are sent.

## 2. Local Mocked Speak-Back Tests

```powershell
$env:ENABLE_MULTI_TURN_INTAKE="true"
$env:ENABLE_TWILIO_TTS_RESPONSE="true"
pytest tests/unit/test_twilio_audio_service.py
pytest tests/unit/test_azure_speech_tts_service.py
pytest tests/unit/test_tts_routes.py
pytest tests/integration/test_twilio_media_flow.py
```

Expected with mocked TTS:
- JSON `intake.followup` or `triage.case.created` payload is sent first.
- One or more Twilio `media` events follow.
- A Twilio `mark` event follows the media events.
- TTS failure tests keep the call flow alive.

## 3. Manual TTS Readiness Endpoint

Start backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Check unconfigured response:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?"}'
```

Expected without Azure Speech env:
- `configured=false`
- `payload_count=0`
- missing variables include `AZURE_SPEECH_KEY` and/or `AZURE_SPEECH_REGION`
- no raw audio payload is returned

## 4. Real Azure Speech TTS Validation

Set:

```powershell
$env:AZURE_SPEECH_KEY="<secret>"
$env:AZURE_SPEECH_REGION="<region>"
$env:AZURE_SPEECH_VOICE="th-TH-PremwadeeNeural"
$env:TTS_OUTPUT_FORMAT="mulaw_8khz"
$env:TTS_MAX_CHARS="220"
```

Run:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?"}'
```

Expected:
- `configured=true`
- `voice=th-TH-PremwadeeNeural`
- `audio_format=mulaw_8khz`
- `payload_count` greater than zero
- `total_bytes` greater than zero
- no raw audio payload is returned

## 5. Twilio Real-Call Enablement

For first speak-back test, mock intake may remain enabled while Azure Speech TTS is configured:

```powershell
$env:USE_MOCK_SERVICES="true"
$env:ENABLE_MULTI_TURN_INTAKE="true"
$env:ENABLE_TWILIO_TTS_RESPONSE="true"
$env:AZURE_SPEECH_KEY="<secret>"
$env:AZURE_SPEECH_REGION="<region>"
$env:AZURE_SPEECH_VOICE="th-TH-PremwadeeNeural"
```

Health check:

```powershell
Invoke-RestMethod "https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/health/azure"
```

TTS check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?"}'
```

Then place a Twilio test call. Expected:
- Caller hears Narayana response text.
- Logs show `tts.started` and `tts.completed`.
- Logs do not include secrets or audio payloads.

## 6. Full Verification

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

Do not add ACS, SMS, Cosmos DB resources, emergency dispatch, route changes, or default-enabled TTS in this feature.

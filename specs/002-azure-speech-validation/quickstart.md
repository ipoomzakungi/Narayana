# Quickstart: Azure Speech Validation Build

## 1. Keep Mock Mode Working

```powershell
Copy-Item .env.example .env
$env:USE_MOCK_SERVICES="true"
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/voice-debug`, submit:

```text
น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง
```

Expected:

- RED triage
- human review required
- status pending
- source/transcript source shown as mock

## 2. Run Automated Regression Checks

Backend:

```powershell
python -m compileall app
pytest
```

Frontend:

```powershell
cd frontend
npm test
npm run build
```

These checks must not require Azure credentials.

## 3. Configure Real Azure Speech Validation

Set `.env` values:

```dotenv
USE_MOCK_SERVICES=false
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_API_VERSION=...
AUDIO_STORE_PATH=.data/audio
```

Restart the backend after changing `.env`.

## 4. Manual Thai WAV Validation

Prepare a local Thai WAV file that says:

```text
น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง
```

Manual validation path:

1. Set `$env:AZURE_SPEECH_TEST_WAV="C:\path\to\thai-sample.wav"`.
2. Run `pytest tests/integration/test_azure_speech_manual.py`.
3. Confirm `transcript_source=azure_speech_stt`.
4. Confirm the transcript is the Azure Speech result, not a hardcoded crisis sentence.
5. Confirm triage remains pending after safety rules.

The manual test is skipped unless all Azure Speech/OpenAI variables and `AZURE_SPEECH_TEST_WAV` are present.

## 5. Local Microphone Validation

With Azure credentials configured and mock mode disabled:

1. Open `http://localhost:3000/voice-debug`.
2. Start local microphone capture.
3. Speak the Thai flood sample.
4. Stop speaking and wait for the turn to commit.
5. Confirm the debug console shows:
   - provider mode `azure_speech_openai`
   - transcript source `azure_speech_stt` on success or `fallback` on failure
   - audio reference/debug identifier
   - provider warnings if any
   - generated case preview
   - no hardcoded Thai flood transcript on fallback

## 6. Failure Validation

Use silence, noise, or an invalid audio file with mock mode disabled.

Expected:

- No hardcoded Thai flood transcript appears.
- Transcript source is `fallback`.
- Confidence is low.
- Human review is required.
- Provider warnings explain the failure.
- Case status remains pending.

## Out of Scope

- Real phone number setup
- ACS call streaming
- Twilio media streaming
- Real Azure Voice Live streaming
- Production authentication

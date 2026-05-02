# Narayana AI Azure Voice Gateway

Narayana AI is a local-first crisis voice intake and triage assistant for the AI Crisis Management hackathon project. V1 validates local browser microphone intake with committed WAV audio artifacts, Azure Speech transcription, Azure OpenAI triage, and a mock fallback that still works without cloud credentials.

This project is not an official emergency hotline replacement and does not dispatch rescue automatically.

## Architecture

- Backend: FastAPI in `app/`
- Frontend: Next.js debug console in `frontend/`
- V1 input: local browser microphone and manual transcript
- V1 AI path: mock provider by default, Azure Speech + Azure OpenAI when configured
- Audio artifacts: committed local microphone turns are written to `.data/audio/{session_id}/{turn_id}.wav`
- Storage: local JSON by default, Cosmos DB when configured
- Future adapters: Twilio Media Stream and Azure Communication Services interfaces only

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Keep `USE_MOCK_SERVICES=true` for offline demos.

Run the backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Run the frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000/voice-debug`.

## Mock Demo

Manual transcript:

```text
น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง
```

Expected result:

- `incident_type=flood`
- `triage_level=RED`
- `location_text=หาดใหญ่`
- `injuries=elderly person breathing difficulty`
- `immediate_needs=rescue, medical`
- `human_review_required=true`
- `status=pending`

API smoke test:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/triage/from-transcript `
  -ContentType application/json `
  -Body '{"transcript":"น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง","language_hint":"th"}'
```

## Azure Setup

Set these values in `.env` and switch mock mode off:

```dotenv
USE_MOCK_SERVICES=false
AUDIO_STORE_PATH=.data/audio
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_API_VERSION=...
```

The stable V1 provider is `AzureSpeechOpenAIProvider`:

1. The local audio WebSocket writes the committed PCM16 turn to a temporary WAV file.
2. The committed turn carries that WAV path as `CallerTurn.audio_ref`.
3. Azure Speech transcribes the WAV when Speech credentials are configured.
4. Azure OpenAI returns structured triage JSON from the real transcript.
5. Deterministic safety rules run after the model and can force RED or human review.

The debug console shows:

- `provider_mode`: `mock` or `azure_speech_openai`
- `transcript_source`: `mock`, `azure_speech_stt`, or `fallback`
- `audio_ref`: the saved WAV path or `-`
- `provider_warnings`: visible warnings for fallback or provider issues

Expected source behavior:

- Mock transcript and offline local mic demo: `transcript_source=mock`.
- Real Azure Speech success: `transcript_source=azure_speech_stt`.
- Missing credentials, missing audio, empty recognition, or Speech errors: `transcript_source=fallback`, low confidence, `human_review_required=true`, and status remains `pending`.

The Azure provider must not replace a failed Speech result with the Thai flood demo sentence.

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health/azure
```

## Real Azure Speech Validation

Prepare a Thai WAV file containing:

```text
น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง
```

Set the manual test path:

```powershell
$env:AZURE_SPEECH_TEST_WAV="C:\path\to\thai-sample.wav"
```

Run the credential-gated manual test:

```powershell
pytest tests/integration/test_azure_speech_manual.py
```

The test is skipped unless all Azure Speech/OpenAI variables and `AZURE_SPEECH_TEST_WAV` are present. When enabled, it verifies `transcript_source=azure_speech_stt`, the transcript is not the hardcoded demo sentence, and the resulting case stays pending.

For live local microphone validation:

1. Start the backend with `USE_MOCK_SERVICES=false`.
2. Open `http://localhost:3000/voice-debug`.
3. Start local mic capture and speak the Thai sample.
4. Wait for VAD to commit the turn.
5. Confirm the UI shows `azure_speech_openai`, `azure_speech_stt` on success or `fallback` on failure, the saved `audio_ref`, provider warnings if any, and the generated case.

Failure validation:

1. Use silence, noisy audio, or invalid speech input.
2. Confirm no Thai flood demo sentence is silently substituted.
3. Confirm the result is low-confidence, human-review-required, warning-visible, and pending.

## Cosmos DB

Local JSON storage is the default at `.data/cases.json`.

To use Cosmos DB, set:

```dotenv
COSMOS_DB_ENDPOINT=...
COSMOS_DB_KEY=...
COSMOS_DB_DATABASE=...
COSMOS_DB_CONTAINER=...
```

When all Cosmos values exist, the repository selector uses `CosmosCaseRepository`; otherwise it falls back to `LocalCaseRepository`.

## Local Mic Flow

The frontend uses Web Audio API microphone capture, converts audio to 20 ms PCM16 mono frames, and streams JSON frames to:

```text
/ws/local-audio
```

The backend emits debug events:

- `audio.frame.received`
- `vad.speech.start`
- `vad.speech.end`
- `turn.committed`
- `ai.request.started`
- `ai.response.started`
- `ai.response.completed`
- `barge_in.detected`

The UI shows VAD state as `silence`, `speech`, `listening`, `thinking`, or `speaking`.

On each committed local microphone turn, the backend writes a WAV file under `.data/audio/{session_id}/{turn_id}.wav` and includes that path in the WebSocket `triage.case.created` message as `audio_ref`.

## Phone Provider Limitations

Twilio and Azure Communication Services are V1 work. V0 intentionally does not require real phone numbers because Thailand number support, trial-account restrictions, inbound call setup, and compliance requirements must be validated separately.

The code includes disabled adapter placeholders:

- `TwilioMediaStreamAdapter`
- `ACSAudioStreamAdapter`

They are not selected by default and raise `NotImplementedError`.

## Tests

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

Known manual checks:

- Azure Speech Thai audio STT: run only when Speech credentials and a Thai audio file are available.
- Cosmos DB write/read: run only when Cosmos credentials and a container are available.
- Azure Voice Live: optional provider guard only in V0; run manually when the endpoint/model are available.

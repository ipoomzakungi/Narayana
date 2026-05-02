# Narayana AI Azure Voice Gateway

Narayana AI is a local-first crisis voice intake and triage assistant for the AI Crisis Management hackathon project. V0 proves the Azure speech/AI pipeline from a local browser microphone or transcript without depending on Twilio or Azure Communication Services phone-number availability.

This project is not an official emergency hotline replacement and does not dispatch rescue automatically.

## Architecture

- Backend: FastAPI in `app/`
- Frontend: Next.js debug console in `frontend/`
- V0 input: local browser microphone and manual transcript
- V0 AI path: mock provider by default, Azure Speech + Azure OpenAI when configured
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
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_API_VERSION=...
```

The stable V0 provider is `AzureSpeechOpenAIProvider`:

1. Azure Speech transcribes committed Thai audio when an audio reference is provided.
2. Azure OpenAI returns structured triage JSON.
3. Deterministic safety rules run after the model and can force RED or human review.

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health/azure
```

Manual Azure Speech Thai audio smoke test is credential-gated. Provide a local Thai WAV/PCM audio reference to `CallerTurn.audio_ref` in a small script or test harness, then call `AzureSpeechOpenAIProvider.process_turn`. Skip this test when Azure Speech credentials are missing.

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

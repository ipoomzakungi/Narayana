# Quickstart: Narayana AI Voice Intake

This quickstart describes the expected local MVP workflow after implementation tasks scaffold the frontend and backend.

## Prerequisites

- Node.js LTS
- Python 3.11 or newer
- A browser with microphone permission support
- Optional Azure resources for non-mock mode:
  - Azure Speech or Microsoft Foundry resource for Voice Live/Speech
  - Azure OpenAI deployment
  - Azure Cosmos DB for NoSQL
  - Azure SignalR Service
  - Application Insights

## Environment Files

Create environment files from the committed examples:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

Backend `.env.example` must include:

```text
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_VOICE_LIVE_ENDPOINT=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
COSMOS_DB_ENDPOINT=
COSMOS_DB_KEY=
COSMOS_DB_DATABASE=
COSMOS_DB_CONTAINER=
SIGNALR_CONNECTION_STRING=
APPLICATIONINSIGHTS_CONNECTION_STRING=
USE_MOCK_SERVICES=true
```

Frontend `.env.example` must include:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000/ws/voice
NEXT_PUBLIC_CASES_WS_URL=ws://localhost:8000/ws/cases
```

Do not commit `.env` or `.env.local`.

## Run Backend Locally

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:USE_MOCK_SERVICES = "true"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected checks:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## Run Frontend Locally

```powershell
Set-Location frontend
npm install
npm run dev
```

Open:

- `http://localhost:3000/cases` for Live Cases
- `http://localhost:3000/voice-debug` for microphone and VAD testing
- `http://localhost:3000/uploads` for simulated upload-link testing

## Demo Flow With Mock Services

1. Start backend with `USE_MOCK_SERVICES=true`.
2. Start frontend.
3. Open Voice Debug Console.
4. Allow microphone access.
5. Speak or submit the Thai demo transcript:

   ```text
   น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง
   ```

6. Confirm the debug state moves through `listening`, `speech`, `thinking`, and `speaking`.
7. Open Live Cases and verify a new RED case appears without manual refresh.
8. Open the case detail and verify:
   - language is Thai
   - incident includes flood and medical/breathing risk
   - location includes Hat Yai
   - triage is RED
   - human review is required
   - AI summary and triage reason are visible
   - transcript and extracted evidence are visible
9. Change status to `contacted`.
10. Override priority in the UI and confirm the original AI reason remains visible.
11. Generate a simulated upload link and verify it is clearly labeled as simulated.

## Azure Mode Smoke Test

After Azure credentials are configured:

1. Set `USE_MOCK_SERVICES=false`.
2. Configure the preferred voice provider:
   - `AZURE_VOICE_LIVE_ENDPOINT` for Voice Live mode, or
   - `AZURE_SPEECH_*` plus `AZURE_OPENAI_*` for Speech + OpenAI fallback.
3. Configure Cosmos and SignalR values if available.
4. Restart backend.
5. Repeat the Thai demo flow.
6. If any Azure provider fails, the app must show a recoverable provider error and fall back to mock mode when configured to do so.

## Test Commands

Backend:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
pytest
```

Frontend:

```powershell
Set-Location frontend
npm test
npm run lint
```

Browser workflow:

```powershell
Set-Location frontend
npm run test:e2e
```

Required test coverage:

- Unit test triage rules for RED, YELLOW, GREEN, low-confidence, and ambiguous cases.
- Unit test local case repository create, read, update, list, and persistence.
- Unit test VAD state transitions, silence threshold, pre-speech padding, and barge-in flag.
- Integration test local microphone/WebSocket flow with mock provider.
- Integration test structured extraction from the Thai flood and breathing-difficulty transcript.
- Manual demo tests:
  - Thai flood plus elderly breathing difficulty -> RED
  - Minor property damage only -> GREEN
  - Unclear noisy speech -> `human_review_required=true`
  - Operator priority override
  - Dashboard live update

## Deployment Notes

- Frontend target: Azure Static Web Apps.
- Backend target: Azure Container Apps.
- Database target: Azure Cosmos DB.
- Realtime target: Azure SignalR Service with local WebSocket/SSE fallback.
- Monitoring target: Application Insights.
- Future secrets target: Azure Key Vault.
- Telephony remains V1: define `TwilioMediaStreamAdapter` and `ACSCallAutomationAdapter`, but do not require them for V0.

# Quickstart: Narayana AI Azure Voice Gateway

## Prerequisites

- Python 3.11+
- Node.js LTS if running the debug console
- Browser with microphone permission support
- Optional Azure credentials for Speech/OpenAI/Cosmos tests

## Environment

Create local backend environment:

```powershell
Copy-Item .env.example .env
```

Required `.env.example` values:

```text
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=
AZURE_VOICE_LIVE_ENDPOINT=
AZURE_VOICE_LIVE_MODEL=
COSMOS_DB_ENDPOINT=
COSMOS_DB_KEY=
COSMOS_DB_DATABASE=
COSMOS_DB_CONTAINER=
USE_MOCK_SERVICES=true
```

Frontend:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_LOCAL_AUDIO_WS_URL=ws://localhost:8000/ws/local-audio
```

Do not commit `.env` files.

## Run Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:USE_MOCK_SERVICES = "true"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check health:

```powershell
Invoke-RestMethod http://localhost:8000/api/health/azure
```

## Transcript Triage Smoke Test

```powershell
$body = @{
  transcript = "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"
  language_hint = "th"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/triage/from-transcript `
  -ContentType "application/json" `
  -Body $body
```

Expected result:

- `language`: `th`
- `incident_type`: `flood`
- `triage_level`: `RED`
- `location_text`: `Hat Yai` or `หาดใหญ่`
- `injuries`: elderly person breathing difficulty
- `immediate_needs`: includes `rescue` and `medical`
- `human_review_required`: `true`
- `status`: `pending`

## Run Debug Console

```powershell
npm install
npm run dev
```

Open the voice debug console and verify:

- Microphone start/stop works.
- VAD state shows silence, speech, listening, thinking, speaking.
- Debug event timeline receives required event names.
- Transcript panel shows committed turns.
- Triage JSON panel shows structured result.
- Safety panel shows forced RED or review reasons.
- Case preview shows `pending` status.

## Azure Speech/OpenAI Mode

1. Set `USE_MOCK_SERVICES=false`.
2. Configure:
   - `AZURE_SPEECH_KEY`
   - `AZURE_SPEECH_REGION`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_VERSION`
3. Restart backend.
4. Repeat the Thai transcript and local microphone tests.
5. If credentials are incomplete, the system should report missing variables and fall back to mock provider when allowed.

## Optional Azure Voice Live Mode

1. Configure `AZURE_VOICE_LIVE_ENDPOINT` and `AZURE_VOICE_LIVE_MODEL`.
2. Select the Voice Live provider in config or the debug console.
3. Confirm the provider emits transcript or voice events.
4. If Voice Live does not return structured triage directly, verify transcript is passed to Azure OpenAI triage.

## Optional Cosmos Mode

1. Configure all `COSMOS_DB_*` variables.
2. Submit a case through `POST /api/cases`.
3. Confirm the case is written to Cosmos.
4. Remove credentials and confirm local repository fallback still works.

## Required Test Commands

```powershell
pytest tests/unit/test_safety_rules.py
pytest tests/unit/test_triage_schema.py
pytest tests/unit/test_vad_service.py
pytest tests/unit/test_provider_fallback.py
pytest tests/integration/test_thai_transcript_to_red_case.py
pytest tests/integration/test_mock_local_mic_flow.py
```

## Manual Quality Gates

- App runs locally with mock mode.
- App runs locally with Azure Speech/OpenAI credentials.
- Local microphone creates a case.
- RED safety cases are never downgraded.
- Missing or uncertain information requires human review.
- Phone provider integration is isolated behind adapters.

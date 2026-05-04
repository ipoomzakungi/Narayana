# Narayana AI Azure Voice Gateway

Narayana AI is a local-first crisis voice intake and triage assistant for the AI Crisis Management hackathon project. V1 validates local browser microphone intake with committed WAV audio artifacts, Azure Speech transcription, Azure OpenAI triage, and a mock fallback that still works without cloud credentials.

This project is not an official emergency hotline replacement and does not dispatch rescue automatically.

## Architecture

- Backend: FastAPI in `app/`
- Frontend: Next.js debug console in `frontend/`
- V1 input: local browser microphone and manual transcript
- V1 telephony spike: Twilio Media Stream ingress can be simulated locally and tested with a foreign-country test number when available
- V1 AI path: mock provider by default, Azure Speech + Azure OpenAI when configured
- Audio artifacts: committed local microphone turns are written to `.data/audio/{session_id}/{turn_id}.wav`
- Storage: local JSON by default, Cosmos DB when configured
- Future adapter: Azure Communication Services remains a disabled skeleton until explicitly implemented

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

## Multi-Turn Conversation Intake

The multi-turn intake layer is additive. The existing one-shot route remains available:

```text
POST /api/triage/from-transcript
```

The conversation-aware route is:

```text
POST /api/intake/from-transcript
```

It keeps in-memory session state for local V0 demos, stores caller and assistant turns, updates collected fields, asks one concise Thai follow-up question when critical details are missing, and creates or escalates a case immediately when deterministic RED guardrails match.

Example incomplete intake:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/intake/from-transcript `
  -ContentType application/json `
  -Body '{"session_id":"debug-session","transcript":"น้ำท่วมอยู่ที่หาดใหญ่","language_hint":"th","source_input_mode":"manual"}'
```

Expected:

- `action=ask_followup`
- `response_text` contains one short Thai question
- `partial_state.conversation_turns` includes caller and assistant turns
- `created_case=null`

Example RED escalation:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/intake/from-transcript `
  -ContentType application/json `
  -Body '{"session_id":"red-session","transcript":"น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง","language_hint":"th","source_input_mode":"manual"}'
```

Expected:

- `action=escalate_human_review`
- `triage_level=RED`
- `human_review_required=true`
- `case_group=rescue`
- `recommended_team=rescue`
- `created_case` is present

Twilio/local-audio integration is feature-gated and stays disabled by default:

```dotenv
ENABLE_MULTI_TURN_INTAKE=false
ASSISTANT_LANGUAGE=th
ASSISTANT_TONE=calm_concise
ASSISTANT_MAX_FOLLOWUPS=3
ASSISTANT_QUESTION_STYLE=single_short_question
ASSISTANT_NAME=Narayana
ASSISTANT_RESPONSE_MAX_CHARS=180
```

When `ENABLE_MULTI_TURN_INTAKE=true`, committed phone/local audio transcripts are routed through the intake orchestrator. `ask_followup` emits an `intake.followup` WebSocket payload with `response_text`; `create_case` and `escalate_human_review` continue to emit `triage.case.created` with additive intake metadata.

Spoken Twilio playback is a separate optional feature. It stays disabled unless `ENABLE_TWILIO_TTS_RESPONSE=true`.

## Optional Twilio TTS Speak-Back

Twilio speak-back lets Narayana read `response_text` back to a caller over the same Twilio Media Stream. It is for controlled demos only and is disabled by default to avoid surprise Azure Speech usage cost.

Default safe settings:

```dotenv
ENABLE_TWILIO_TTS_RESPONSE=false
ENABLE_TWILIO_INITIAL_GREETING=false
TWILIO_INITIAL_GREETING_TEXT=สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ
TWILIO_INITIAL_GREETING_PROFILE=greeting
TWILIO_INITIAL_GREETING_FALLBACK_SAY=false
AZURE_SPEECH_VOICE=th-TH-PremwadeeNeural
TTS_MAX_CHARS=220
TTS_OUTPUT_FORMAT=mulaw_8khz
TTS_USE_SSML=true
TTS_RATE_NORMAL=0%
TTS_RATE_FOLLOWUP=-5%
TTS_RATE_GREETING=-5%
TTS_RATE_RED=-12%
TTS_RATE_UNCLEAR=-8%
TTS_PITCH_NORMAL=0%
TTS_PITCH_GREETING=0%
TTS_PITCH_RED=-2%
TTS_VOLUME=medium
```

To enable a real-call test, configure Azure Speech and turn on both multi-turn intake and speak-back:

```powershell
$env:USE_MOCK_SERVICES="true"
$env:ENABLE_MULTI_TURN_INTAKE="true"
$env:ENABLE_TWILIO_TTS_RESPONSE="true"
$env:ENABLE_TWILIO_INITIAL_GREETING="true"
$env:TWILIO_INITIAL_GREETING_TEXT="สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ"
$env:TWILIO_INITIAL_GREETING_PROFILE="greeting"
$env:AZURE_SPEECH_KEY="<secret>"
$env:AZURE_SPEECH_REGION="<region>"
$env:AZURE_SPEECH_VOICE="th-TH-PremwadeeNeural"
```

Check readiness without returning raw audio:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?","profile":"followup"}'
```

Check the initial greeting profile the same way:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/tts/test" `
  -ContentType "application/json" `
  -Body '{"text":"สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ","profile":"greeting"}'
```

Expected when configured:

- `configured=true`
- `voice=th-TH-PremwadeeNeural`
- `audio_format=mulaw_8khz`
- `profile=followup`
- `payload_count` greater than zero
- no raw audio payload field

Health includes:

- `twilio_tts_response_enabled`
- `twilio_initial_greeting_enabled`
- `twilio_initial_greeting_text_configured`
- `twilio_initial_greeting_profile`
- `azure_speech_tts_configured`
- `azure_speech_voice`
- `tts_use_ssml`
- `tts_output_format`

During a Twilio call, the backend still sends the normal JSON debug or case payload first. If speak-back is enabled, configured, and the payload has safe `response_text`, the backend sends Twilio `media` chunks followed by a Twilio `mark` event. Logs include `tts.started`, `tts.completed`, or `tts.failed`, chunk count, stream ID, and duration estimate. Logs must not include secrets or raw audio payloads.

Initial greeting speak-back is separate from response speak-back. When `ENABLE_TWILIO_INITIAL_GREETING=true`, Narayana speaks the configured Thai greeting once after the Twilio stream starts, then continues listening. Watch Container App logs for `greeting.started` and `greeting.completed`; if synthesis is unavailable or fails, `greeting.failed` is logged and the call continues.

SSML is enabled by default for Azure Speech TTS. Narayana uses only `prosody` rate, pitch, and volume controls rather than style names, so the voice remains compatible with Thai neural voices. Profiles are selected from the Twilio payload: the initial greeting uses `greeting`, follow-up questions use `followup`, RED or human-escalation responses use `red`, unclear/fallback transcript responses use `unclear`, and sanitized unsafe text uses `safe_fallback`.

Spoken text is sanitized before synthesis. Narayana must not say rescue was dispatched, an ambulance is on the way, give a diagnosis, close/reject an emergency, or provide long unsafe guidance. If synthesis fails, the call continues and case creation or follow-up output is not blocked.

This feature does not add SMS, ACS production behavior, Cosmos DB resources, emergency dispatch, or automatic case closure/rejection.

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

## Twilio Foreign-Number Spike

Local microphone remains the default path. To validate phone ingress with a foreign-country Twilio test number, expose the backend through a public HTTPS tunnel or deployment and set:

```dotenv
VOICE_INPUT_MODE=twilio_call
TELEPHONY_PROVIDER=twilio
PHONE_TEST_COUNTRY=US
PHONE_TEST_NUMBER=+15551234567
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+15557654321
TWILIO_WEBHOOK_PUBLIC_BASE_URL=https://example.ngrok-free.app
```

Configure the Twilio voice webhook for the test number:

```text
POST https://example.ngrok-free.app/api/telephony/twilio/incoming-call
```

When configured, the webhook returns TwiML that connects the call to:

```text
wss://example.ngrok-free.app/ws/telephony/twilio/{call_id}
```

The Twilio media WebSocket decodes base64 G.711 mu-law 8 kHz frames into PCM16 mono `AudioFrame` objects, then reuses the same VAD, `AudioBufferService`, voice provider, safety rules, and case repository used by `/ws/local-audio`.

Offline validation does not require Twilio credentials:

```powershell
pytest tests/unit/test_twilio_audio_service.py tests/unit/test_twilio_routes.py tests/integration/test_twilio_media_flow.py
```

## Azure Container Apps Backend Deployment

Twilio Media Streams must connect to the FastAPI backend because the backend owns `/api/telephony/twilio/incoming-call` and `/ws/telephony/twilio/{call_id}`. Vercel is frontend-only for this project; do not use a frontend-only deployment as the Narayana Twilio webhook target.

The backend container runs:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### GHCR Image Build

This Azure subscription blocks Azure Container Registry Tasks, so the Narayana demo path avoids Azure-side image builds. Do not use `az acr build` or `az containerapp up --source` for this deployment. The backend image is built by GitHub Actions and pushed to GitHub Container Registry instead:

```text
ghcr.io/ipoomzakungi/narayana-backend:latest
```

The workflow is:

```text
.github/workflows/publish-backend-ghcr.yml
```

It runs on every push to `main` and can also be started manually:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Publish backend image to GHCR**.
4. Choose **Run workflow** on `main`.
5. Wait for the image push to complete.

Check the package under GitHub Packages for `ipoomzakungi/Narayana`, or open the personal package list for `ipoomzakungi` and look for `narayana-backend`.

If Azure Container Apps cannot pull the image, make the GHCR package public:

1. Open the `narayana-backend` package page in GitHub.
2. Open **Package settings**.
3. Under visibility, choose **Change visibility**.
4. Select **Public** and confirm.

Alternatively, keep the package private and provide `GHCR_USERNAME` plus `GHCR_PAT` with package read permission when running the deploy script. Do not commit those values.

### Deploy GHCR Image to Azure Container Apps

Deploy in mock Twilio mode after the GHCR image exists:

```powershell
$env:AZURE_RESOURCE_GROUP="rg-narayana-demo"
$env:AZURE_LOCATION="southeastasia"
$env:AZURE_CONTAINER_APP_NAME="narayana-api"
$env:AZURE_CONTAINER_ENV_NAME="narayana-env"
$env:GHCR_IMAGE="ghcr.io/ipoomzakungi/narayana-backend:latest"
$env:USE_MOCK_SERVICES="true"
$env:VOICE_INPUT_MODE="twilio_call"
$env:TELEPHONY_PROVIDER="twilio"
$env:TWILIO_PHONE_NUMBER="+16082005400"
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://placeholder"

.\scripts\azure_container_apps_deploy_ghcr.ps1
```

The script:

- verifies Azure CLI login
- creates or reuses `rg-narayana-demo`
- creates or reuses the `narayana-env` Container Apps environment
- creates or updates `narayana-api`
- uses external ingress on port `8000`
- deploys `ghcr.io/ipoomzakungi/narayana-backend:latest`
- keeps `USE_MOCK_SERVICES=true`
- fetches the real Container App FQDN
- updates `TWILIO_WEBHOOK_PUBLIC_BASE_URL=https://<real-fqdn>`
- prints the final Twilio webhook URL

Expected final webhook format:

```text
https://<real-fqdn>/api/telephony/twilio/incoming-call
```

### Test the Deployed Backend

After deployment, read the FQDN and set local test variables:

```powershell
$fqdn = az containerapp show `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --query properties.configuration.ingress.fqdn `
  -o tsv

$env:AZURE_CONTAINER_APP_URL="https://$fqdn"
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://$fqdn"
```

Health check:

```powershell
Invoke-RestMethod "$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL/api/health/azure"
```

Fake Twilio webhook POST:

```powershell
$response = Invoke-WebRequest `
  -Method Post `
  -Uri "$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL/api/telephony/twilio/incoming-call" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{
    CallSid = "CA_TEST"
    From = "+66800000000"
    To = "+16082005400"
    FromCountry = "TH"
  }

$response.Content
```

Verify the TwiML contains:

```text
wss://
/ws/telephony/twilio/CA_TEST
```

## Cached Cases Dashboard

The backend exposes a low-cost dashboard read endpoint:

```text
GET /api/cases/recent-cached?limit=50
```

It returns an in-process snapshot with a 60 second TTL and response headers:

```text
Cache-Control: public, max-age=60
X-Cache-Source: cache | repository
```

Use this endpoint for dashboards instead of polling fresh repository data. A fresh endpoint also exists for manual inspection:

```text
GET /api/cases/recent?limit=50
```

When hosting the frontend outside localhost, set backend CORS explicitly. Do not use `*` with credentials enabled:

```powershell
$env:CORS_ALLOW_ORIGINS="http://localhost:3000,https://<static-web-app-url>"
.\scripts\azure_container_apps_deploy_ghcr.ps1
```

For the current Azure backend, the dashboard API base URL is:

```text
https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io
```

## Azure Static Web Apps Frontend

Deploy the frontend as a separate static app. The backend remains Azure Container Apps because Twilio Media Streams need the FastAPI WebSocket endpoint.

Azure Static Web Apps settings:

```text
App location: frontend
API location: <empty>
Output location: out
```

The Next.js frontend is configured for static export. Set this build-time environment variable in Azure Static Web Apps:

```text
NEXT_PUBLIC_API_BASE_URL=https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io
```

After deployment:

```text
Dashboard URL: /cases
Debug console URL: /voice-debug
```

## Public Webhook Check

Run a fake Twilio webhook check before using real calls:

```powershell
python scripts/check_public_webhook.py
```

The checker:

- reads `TWILIO_WEBHOOK_PUBLIC_BASE_URL`, falling back to `AZURE_CONTAINER_APP_URL`
- calls `GET /api/health/azure`
- posts fake `CallSid=CA_TEST` to `/api/telephony/twilio/incoming-call`
- verifies TwiML includes `/ws/telephony/twilio/CA_TEST`
- never calls Twilio or Azure management APIs

## Twilio Number Configuration

For the Twilio US voice number `+16082005400`, configure the voice webhook in Twilio:

```text
POST https://<container-app-url>/api/telephony/twilio/incoming-call
```

Inbound call test:

1. Deploy the backend to Azure Container Apps in mock mode.
2. Run `python scripts/check_public_webhook.py`.
3. Call `+16082005400`.
4. Watch Container Apps logs for the Twilio media WebSocket session.
5. Confirm the dashboard/debug output still shows mock-provider triage until Azure credentials are intentionally enabled.

## Twilio Outbound Call Helper

The outbound helper is optional and credential-gated. It creates a Twilio voice call from `+16082005400` to a verified destination and uses the Narayana webhook URL for call handling.

Set:

```powershell
$env:TWILIO_ACCOUNT_SID="AC..."
$env:TWILIO_AUTH_TOKEN="..."
$env:TWILIO_PHONE_NUMBER="+16082005400"
$env:TWILIO_OUTBOUND_TO="+66..."
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://<container-app-url>"
```

Run:

```powershell
python scripts/twilio_outbound_call.py
```

For an outbound call to a verified Thai phone:

- Add the Thai phone as a verified caller ID if the Twilio account is in trial mode.
- Enable Thailand in Twilio Voice Geo Permissions.
- Confirm account balance, destination format, and expected call cost.
- Keep this as a controlled manual test; automated tests do not call Twilio.

## Deployment and Call-Test Limits

- Vercel is frontend-only; Twilio webhook and media stream traffic must target the Azure Container Apps backend.
- No ACS production implementation is included.
- No SMS is sent.
- No emergency dispatch is implemented.
- Real-call tests validate telephony ingress only and do not prove official emergency-service readiness.

## ACS Skeleton

ACS routes are present only as disabled placeholders:

```text
POST /api/telephony/acs/events
WS   /ws/telephony/acs/{call_id}
```

Without ACS implementation/configuration they return a clear not-implemented response and do not create cases or process audio.

## Phone Provider Limitations

The Twilio foreign-number spike validates call ingress only. It does not validate Thailand phone-number availability, Thailand SMS support, local telecom cost, carrier behavior, production authentication, emergency-service compliance, or dispatch readiness.

Narayana remains a crisis intake and triage assistant. It does not send real SMS, does not dispatch rescue automatically, and is not an official emergency hotline replacement.

The code still includes adapter placeholders:

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

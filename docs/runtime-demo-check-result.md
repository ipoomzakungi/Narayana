# Runtime Demo Check Result

Date: 2026-05-16
Tested commit: `f1b4be6f`

## Current Request

Target Foundry realtime endpoint:

`https://realtime-narayana-demo1.services.ai.azure.com`

Target deployment/model:

- Deployment: `gpt-realtime-1.5`
- Model: `gpt-realtime-1.5`
- Model version: `2026-02-23`
- Provisioning state reported by user: `Succeeded`

Security note: the previous realtime key was reported as exposed. The old key was not used. A new regenerated key is required before websocket testing or Container App secret updates.

## Baseline Verification

- `git status`: on `main`, up to date with `origin/main`; dirty files are local report/template/gitignore changes plus `scripts/check_azure_realtime_ws.py`
- `git pull --ff-only`: already up to date
- `python -m compileall app scripts`: passed
- `pytest`: 244 passed, 1 skipped
- `npm test` in `frontend`: 16 passed
- `npm run build` in `frontend`: passed

On the latest run, the working tree had only local report/template/gitignore changes plus the newly added websocket check script.

## Azure Target

- Subscription: `Azure subscription 1` (`adcfa840-4838-4553-9bf8-bf7bb55973fe`)
- Resource group: `rg-narayana-demo`
- Container App: `narayana-api`
- Backend URL: `https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io`
- Image: `ghcr.io/ipoomzakungi/narayana-backend:latest`

## Azure OpenAI Realtime

- Preferred model/deployment: `gpt-realtime-1.5`
- Target endpoint: `https://realtime-narayana-demo1.services.ai.azure.com`
- API version requested first: `v1`
- Expected v1 websocket shape: `wss://realtime-narayana-demo1.services.ai.azure.com/openai/v1/realtime?model=gpt-realtime-1.5`
- Selected realtime deployment/model: `gpt-realtime-1.5`

No realtime key was printed. No realtime deployment value was guessed; the deployment came from the user request.

Added `scripts/check_azure_realtime_ws.py` to probe these endpoint shapes without printing secrets:

- `openai-v1`: `/openai/v1/realtime?model=gpt-realtime-1.5`
- `openai-preview`: `/openai/realtime?api-version=2025-04-01-preview&deployment=gpt-realtime-1.5`
- `voice-live`: `/voice-live/realtime?api-version=2025-10-01&model=gpt-realtime-1.5`

The script was compiled successfully.

The script was executed with only the non-secret endpoint, deployment, and API version set. It stopped before network access with: missing `AZURE_REALTIME_API_KEY`.

The user then ran the script locally with a regenerated key available in their PowerShell process. Result:

- `openai-v1`: connected
- Working URL shape: `wss://realtime-narayana-demo1.services.ai.azure.com/openai/v1/realtime?model=gpt-realtime-1.5`
- First observed event: `session.created`
- Preview websocket needed: no
- Voice Live fallback needed: no

## Deployed Health Result

Earlier `GET /api/health/azure` returned HTTP 200 while the deployed runtime was still on the old mock/Voice Live settings.

After creating the new `azure-realtime-api-key` secret and updating Container App env, `GET /api/health/azure` returns:

- `use_mock_services`: `false`
- `selected_provider`: `azure_voice_live`
- `enable_realtime_voice`: `true`
- `realtime_provider`: `azure_openai_realtime`
- `azure_realtime_configured`: `true`
- `azure_openai_realtime_configured`: `true`
- `azure_voice_live_realtime_configured`: `true`
- `realtime_input_audio_format`: `g711_ulaw`
- `effective_realtime_input_audio_format`: `g711_ulaw`
- `realtime_twilio_audio_passthrough`: `true`
- `realtime_input_audio_passthrough_enabled`: `true`
- `azure_speech_tts_configured`: `true`
- `twilio_tts_response_enabled`: `true`
- `twilio_initial_greeting_enabled`: `true`

The `selected_provider=azure_voice_live` field is the older turn-based provider selector. The realtime provider field is correctly set to `azure_openai_realtime`.

The health endpoint still reports these missing non-realtime Azure OpenAI variables:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`

Active shell secret presence check:

- `AZURE_REALTIME_API_KEY`: missing
- `AZURE_SPEECH_KEY`: missing
- `AZURE_SPEECH_REGION`: missing
- `TWILIO_ACCOUNT_SID`: missing
- `TWILIO_AUTH_TOKEN`: missing

The regenerated key is not available to this Codex process. It was not printed or reused here.

Earlier Container App secrets present were:

- `azure-speech-key`
- `azure-realtime-key`

After the user set the new secret, Container App secrets present are:

- `azure-speech-key`
- `azure-realtime-key`
- `azure-realtime-api-key`

## Twilio Webhook Result

Webhook URL:

`https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io/api/telephony/twilio/incoming-call`

Fake Twilio POST result:

- HTTP status: `200`
- TwiML returned: yes
- Contains `<Connect>`: yes
- Contains `<Stream>`: yes
- Contains `wss://`: yes
- Contains `/ws/telephony/twilio/CA_TEST`: yes

`python scripts/check_public_webhook.py` passed when run with `TWILIO_WEBHOOK_PUBLIC_BASE_URL` set to the backend URL for that command.

After the Container App env update, the fake Twilio POST still passed:

- HTTP status: `200`
- Contains `<Connect>`: yes
- Contains `<Stream>`: yes
- Contains `wss://`: yes
- Contains `/ws/telephony/twilio/CA_TEST`: yes

## Cosmos DB Result

- Cosmos DB account: `narayana-cosmos-demo`
- Database: `narayana`
- Container: `cases`
- Partition key: `/id`
- Container App secret: `COSMOS_DB_KEY=secretref:cosmos-db-key`
- Container App env:
  - `COSMOS_DB_ENDPOINT=https://narayana-cosmos-demo.documents.azure.com:443/`
  - `COSMOS_DB_DATABASE=narayana`
  - `COSMOS_DB_CONTAINER=cases`
- `GET /api/health/azure`: `cosmos_configured=true`

## Dashboard/Data Result

- `GET /api/intake/sessions?limit=10`: HTTP 200, no real-call sessions yet
- `GET /api/cases/recent-cached?limit=10`: HTTP 200, `source=repository`, `count=1`
- Demo verification case created through the public API: `case_f921ddc2c9e4`
- The demo case remains `status=pending`; no dispatch claim was made.

No real call id was available, so `/api/intake/calls/<call_id>` was not checked.

## Frontend Result

- Static Web App: `narayana-dashboard`
- Frontend URL: `https://ambitious-plant-0ad9a3e00.7.azurestaticapps.net`
- Deployment branch: `main`
- Frontend commit deployed: `f1b4be6`
- GitHub Actions run: `25955305034`, completed successfully
- Live HTML includes the new primary nav: `Cases`, `Call Audit`, `Voice Debug`
- Live HTML includes runtime status labels for Azure Container Apps, `gpt-realtime-1.5`, and Cosmos DB.
- Local frontend verification:
  - `npm test`: 16 passed
  - `npm run build`: passed
  - Mobile viewport check showed no horizontal overflow on the cases dashboard.

## Configuration Actions

Container App env was updated to:

- `USE_MOCK_SERVICES=false`
- `ENABLE_MULTI_TURN_INTAKE=true`
- `ENABLE_REALTIME_VOICE=true`
- `REALTIME_PROVIDER=azure_openai_realtime`
- `REALTIME_INPUT_AUDIO_FORMAT=g711_ulaw`
- `REALTIME_TWILIO_AUDIO_PASSTHROUGH=true`
- `AZURE_REALTIME_ENDPOINT=https://realtime-narayana-demo1.services.ai.azure.com`
- `AZURE_REALTIME_DEPLOYMENT=gpt-realtime-1.5`
- `AZURE_REALTIME_API_VERSION=v1`
- `AZURE_REALTIME_API_KEY=secretref:azure-realtime-api-key`
- `AZURE_SPEECH_KEY=secretref:azure-speech-key`
- `AZURE_SPEECH_VOICE=th-TH-PremwadeeNeural`
- `ENABLE_TWILIO_INITIAL_GREETING=true`
- `ENABLE_TWILIO_TTS_RESPONSE=true`
- `TTS_OUTPUT_FORMAT=mulaw_8khz`
- `TTS_USE_SSML=true`
- `VOICE_INPUT_MODE=twilio_call`
- `TELEPHONY_PROVIDER=twilio`
- `TWILIO_WEBHOOK_PUBLIC_BASE_URL=https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io`
- `TWILIO_PHONE_NUMBER=+16082005400`
- `CALL_AUDIT_ENABLED=true`
- `CALL_AUDIT_LOG_TRANSCRIPTS=true`

Container App was warmed for demo:

- `minReplicas=1`
- `maxReplicas=1`

Ignored local env files were checked for key names only. They contain Azure Speech/Voice Live keys but not the missing Twilio credentials, Azure OpenAI resource name, realtime endpoint, realtime deployment, or API version.

The stable fallback path was not disabled.

## Real Call Test

Not performed by Codex.

Expected real-call verification remains pending. The backend runtime is configured and the fake webhook passes.

## Remaining Blockers

- Real call test has not been performed.
- Realtime call-created case has not been verified yet. Current dashboard case is a demo verification case, not a real Twilio call case.
- Twilio account credentials are not available locally, so Twilio API verification/update was not performed. The known console webhook already matches the backend URL.
- Legacy Voice Live env vars remain present, so `selected_provider` reports `azure_voice_live`; realtime routing is controlled by `realtime_provider=azure_openai_realtime`.

## Rollback Command

```powershell
az containerapp update `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --set-env-vars ENABLE_REALTIME_VOICE=false REALTIME_PROVIDER=none
```

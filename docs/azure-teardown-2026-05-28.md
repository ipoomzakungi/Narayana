# Azure Teardown Note - 2026-05-28

The Azure demo stack in resource group `rg-narayana-demo` was intentionally removed on 2026-05-28 to avoid paid Azure usage after free credit expiry risk.

## Deleted Resource Group

- `rg-narayana-demo`

## Resources Present Before Teardown

- `workspace-rgnarayanademot3UB` - Log Analytics workspace - Southeast Asia
- `workspace-rgnarayanademoxrZ4` - Log Analytics workspace - Southeast Asia
- `narayana-api-env` - Azure Container Apps managed environment - Southeast Asia
- `narayana-api` - Azure Container App backend - Southeast Asia
- `caa385d6c083acr` - Azure Container Registry Basic - Southeast Asia
- `narayanaacr001` - Azure Container Registry Basic - Southeast Asia
- `narayana-dashboard` - Azure Static Web App Free - East Asia
- `narayana-cosmos-demo` - Azure Cosmos DB account - Southeast Asia
- `speech-narayana-demo` - Azure Speech Services F0 - Southeast Asia
- `tts-narayana-demo` - Azure AI Services S0 - East US
- `tts-narayana-demo/proj-default` - Foundry project - East US
- `realtime-narayana-demo1` - Azure AI Services S0 - East US 2
- `realtime-narayana-demo1/proj-default` - Foundry project - East US 2

## Public URLs Before Teardown

- Backend: `https://narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io`
- Dashboard: `https://ambitious-plant-0ad9a3e00.7.azurestaticapps.net`

These URLs are expected to stop working after resource group deletion.

## External Resources Not Deleted Here

- Twilio phone number and Twilio account configuration are outside Azure.
- GitHub repository, GitHub Actions, and GHCR images are outside Azure.
- Local `.env*` files are outside Azure and were not changed by this teardown.

If the Twilio number is still active, update or disable the Twilio webhook separately to avoid calls pointing at a deleted backend.

## GitHub Actions After Teardown

- `.github/workflows/azure-static-web-apps-ambitious-plant-0ad9a3e00.yml` was disabled by changing it to a manual placeholder workflow. It no longer deploys on push or pull request.
- `.github/workflows/publish-backend-ghcr.yml` was left enabled. It only builds/pushes the backend image to GitHub Container Registry and does not deploy Azure resources.

## Recreate Checklist

1. Create a new Azure resource group, usually in `southeastasia`.
2. Create Azure Container Apps environment and deploy the FastAPI backend image.
   - Current image source used before teardown: `ghcr.io/ipoomzakungi/narayana-backend:latest`
3. Create or reuse a dashboard host.
   - Previous service: Azure Static Web Apps.
   - Configure `NEXT_PUBLIC_API_BASE_URL` to the new backend URL before building/deploying the frontend.
4. Create Cosmos DB for case storage.
   - Required env names: `COSMOS_DB_ENDPOINT`, `COSMOS_DB_KEY`, `COSMOS_DB_DATABASE`, `COSMOS_DB_CONTAINER`.
5. Create Azure Speech or Azure AI Services for TTS/STT as needed.
   - Required env names: `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_SPEECH_VOICE`.
6. Create Azure OpenAI Realtime deployment.
   - Previous deployment: `gpt-realtime-1.5`.
   - Previous realtime config:
     - `REALTIME_PROVIDER=azure_openai_realtime`
     - `REALTIME_INPUT_AUDIO_FORMAT=g711_ulaw`
     - `REALTIME_TWILIO_AUDIO_PASSTHROUGH=true`
     - `REALTIME_INPUT_TRANSCRIPTION_ENABLED=true`
     - `REALTIME_OUTPUT_VOICE=marin`
   - Required env names: `AZURE_REALTIME_ENDPOINT`, `AZURE_REALTIME_API_KEY`, `AZURE_REALTIME_DEPLOYMENT`, `AZURE_REALTIME_API_VERSION`.
7. Configure Twilio.
   - Point the Twilio voice webhook to the new backend `/api/telephony/twilio/incoming-call`.
   - For backend-driven hangup, configure `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`; these were missing from the live Container App env before teardown.
8. Reapply backend call/runtime env settings:
   - `USE_MOCK_SERVICES=false`
   - `VOICE_INPUT_MODE=twilio_call`
   - `TELEPHONY_PROVIDER=twilio`
   - `TWILIO_PHONE_NUMBER`
   - `TWILIO_WEBHOOK_PUBLIC_BASE_URL`
   - `ENABLE_REALTIME_VOICE=true`
   - `ENABLE_TWILIO_INITIAL_GREETING=false`
   - `ENABLE_TWILIO_TTS_RESPONSE=false`
   - `CALL_NO_REPLY_SECONDS`
   - `CALL_NO_REPLY_PROMPT_SECONDS`
   - `CALL_MAX_NO_REPLY_PROMPTS`
   - `CALL_MAX_OFF_TOPIC_REDIRECTS`
   - `TWILIO_FORCE_HANGUP_ENABLED=true`
   - `TWILIO_DEBUG_PAYLOADS_ENABLED=false`

## Validation After Recreate

- `GET /api/health/azure` should return `enable_realtime_voice: true`, `azure_openai_realtime_configured: true`, `cosmos_configured: true`, and `twilio_force_hangup_enabled: true`.
- Dashboard `/cases` should load from `/api/cases/recent-cached`.
- Dashboard `/call-audit` should load from `/api/intake/sessions`.
- A test call should show `realtime.connected`, `response.output_audio.delta`, and case/audit updates.

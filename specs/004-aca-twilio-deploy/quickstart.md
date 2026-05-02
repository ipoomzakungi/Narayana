# Quickstart: Azure Container Apps Deployment and Twilio Real-Call Test Support

## 1. Local Tooling Validation

Run tests without Azure or Twilio credentials:

```powershell
python -m compileall app scripts
pytest tests/unit/test_twilio_test_helpers.py
pytest tests/integration/test_mock_local_mic_flow.py tests/integration/test_twilio_media_flow.py
```

## 2. Build Backend Container Locally

```powershell
docker build -t narayana-backend:local .
docker run --rm -p 8000:8000 `
  -e USE_MOCK_SERVICES=true `
  -e VOICE_INPUT_MODE=twilio_call `
  -e TELEPHONY_PROVIDER=twilio `
  -e TWILIO_PHONE_NUMBER=+16082005400 `
  -e TWILIO_WEBHOOK_PUBLIC_BASE_URL=http://localhost:8000 `
  narayana-backend:local
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health/azure
```

## 3. Deploy Backend to Azure Container Apps

Set required values:

```powershell
$env:AZURE_RESOURCE_GROUP="rg-narayana-demo"
$env:AZURE_LOCATION="southeastasia"
$env:AZURE_CONTAINER_APP_NAME="narayana-api"
$env:TWILIO_PHONE_NUMBER="+16082005400"
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://<container-app-url>"
```

Run:

```powershell
.\scripts\azure_container_apps_deploy.ps1
```

The script should prefer `az containerapp up` when available or print fallback commands for registry build and Container Apps create/update.

## 4. Verify Public Webhook

```powershell
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://<container-app-url>"
python scripts/check_public_webhook.py
```

Expected checks:

- `GET /api/health/azure` succeeds.
- Fake `POST /api/telephony/twilio/incoming-call` returns TwiML.
- TwiML includes `/ws/telephony/twilio/CA_TEST`.

## 5. Configure Twilio Number

For the Twilio US voice number `+16082005400`, set the voice webhook to:

```text
POST https://<container-app-url>/api/telephony/twilio/incoming-call
```

Then place an inbound call to `+16082005400` and watch backend logs for the Twilio media WebSocket session.

## 6. Optional Outbound Call to Verified Thai Phone

Before calling a Thai destination:

- Add the Thai phone as a verified caller ID if the Twilio account is in trial mode.
- Enable Thailand in Twilio Voice Geographic Permissions.
- Confirm expected call costs and account balance.

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

## Limitations

- Vercel is frontend-only for this project; Twilio webhook and media stream traffic must target the Azure Container Apps backend.
- ACS remains disabled.
- No SMS is sent.
- No emergency dispatch is implemented.
- Real-call tests validate telephony ingress only and do not prove production emergency readiness.

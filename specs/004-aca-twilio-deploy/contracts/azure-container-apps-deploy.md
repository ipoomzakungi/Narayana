# Contract: Azure Container Apps Deployment Script

## File

`scripts/azure_container_apps_deploy.ps1`

## Purpose

Deploy or print deployment commands for the Narayana backend on Azure Container Apps with mock-first Twilio configuration.

## Required Inputs

Environment variables or script parameters should provide:

- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_CONTAINER_APP_NAME`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`

Expected mock-first runtime values:

- `USE_MOCK_SERVICES=true`
- `VOICE_INPUT_MODE=twilio_call`
- `TELEPHONY_PROVIDER=twilio`
- `TWILIO_PHONE_NUMBER=+16082005400`

Conditional fallback inputs:

- `AZURE_REGISTRY_NAME`
- `AZURE_IMAGE_NAME`
- `AZURE_CONTAINER_ENV_NAME`

## Behavior

1. Validate required values and local tools.
2. Prefer `az containerapp up` when available.
3. If `az containerapp up` is unavailable, print clear fallback commands for:
   - resource group creation/check
   - registry build
   - Container Apps environment creation/check
   - Container App create/update
4. Print the expected public backend URL and reminder to set Twilio webhook URL.

## Failure Contract

- Missing values produce one clear error listing all missing values.
- Missing Azure CLI produces a clear install/login instruction.
- The script must not embed secrets into source files.

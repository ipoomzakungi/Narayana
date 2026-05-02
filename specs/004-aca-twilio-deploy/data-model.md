# Data Model: Azure Container Apps Deployment and Twilio Real-Call Test Support

## DeploymentConfiguration

Represents the values needed to deploy the backend container publicly.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `AZURE_RESOURCE_GROUP` | string | Yes | Target resource group for Container Apps resources. |
| `AZURE_LOCATION` | string | Yes | Azure region for resources. |
| `AZURE_CONTAINER_APP_NAME` | string | Yes | Public backend app name. |
| `AZURE_CONTAINER_ENV_NAME` | string | No | Container Apps environment name; script may derive a default. |
| `AZURE_REGISTRY_NAME` | string | Conditional | Required for fallback ACR build path. |
| `AZURE_IMAGE_NAME` | string | No | Container image name/tag; script may derive a default. |
| `USE_MOCK_SERVICES` | boolean string | Yes | First deployment path uses `true`. |
| `VOICE_INPUT_MODE` | string | Yes | Deployment docs use `twilio_call`. |
| `TELEPHONY_PROVIDER` | string | Yes | Deployment docs use `twilio`. |
| `TWILIO_PHONE_NUMBER` | string | Yes | For this feature: `+16082005400`. |
| `TWILIO_WEBHOOK_PUBLIC_BASE_URL` | URL | Yes | Public backend URL. |

Validation rules:

- Required values must be checked before deployment work begins.
- Public base URL must be normalized without a trailing slash.
- Secrets are supplied as environment variables and never committed.

## PublicBackendEndpoint

Represents the deployed backend URL used by Twilio and verification scripts.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `base_url` | URL | Yes | Example: `https://narayana-api.<region>.azurecontainerapps.io`. |
| `health_url` | URL | Derived | `${base_url}/api/health/azure`. |
| `twilio_webhook_url` | URL | Derived | `${base_url}/api/telephony/twilio/incoming-call`. |
| `twilio_media_path` | string | Derived | `/ws/telephony/twilio/{call_id}`. |

Validation rules:

- `base_url` must use `http` or `https` for checker input.
- TwiML verification checks for `/ws/telephony/twilio/CA_TEST`.

## TwilioCallTestConfiguration

Represents the values required to place an outbound Twilio call.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `TWILIO_ACCOUNT_SID` | string | Yes | Twilio account id. |
| `TWILIO_AUTH_TOKEN` | string | Yes | Twilio API secret. |
| `TWILIO_PHONE_NUMBER` | E.164 string | Yes | Source number: `+16082005400`. |
| `TWILIO_OUTBOUND_TO` | E.164 string | Yes | Destination verified test phone. |
| `TWILIO_WEBHOOK_PUBLIC_BASE_URL` | URL | Yes | The Narayana public backend URL. |

Validation rules:

- All missing required values must be reported before any outbound provider request.
- The helper must not call Twilio during automated tests.
- Thai destination testing is manual and requires verified caller ID and Thailand geo permission setup.

## WebhookCheckResult

Represents the public webhook checker outcome.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `health_ok` | boolean | Yes | Whether `/api/health/azure` responded successfully. |
| `twiml_ok` | boolean | Yes | Whether fake webhook returned expected TwiML. |
| `health_status` | int | No | HTTP status for health request. |
| `twiml_status` | int | No | HTTP status for fake webhook request. |
| `messages` | list[string] | Yes | Human-readable success/error details. |

Validation rules:

- Missing URL fails clearly before network calls.
- TwiML parser must reject XML that lacks `/ws/telephony/twilio/CA_TEST`.

## DeploymentLimitation

Represents explicit demo boundaries documented for operators and reviewers.

Required limitation statements:

- Backend must run on Azure Container Apps for Twilio Media Streams; Vercel is frontend-only.
- No ACS production implementation.
- No SMS.
- No emergency dispatch.
- Real-call tests validate telephony ingress only, not official emergency readiness.

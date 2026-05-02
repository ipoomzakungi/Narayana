# Contract: Public Webhook Checker

## File

`scripts/check_public_webhook.py`

## Purpose

Verify that the deployed backend is publicly reachable and returns TwiML for a fake Twilio incoming call.

## Inputs

Environment variable:

- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`

Optional:

- `AZURE_CONTAINER_APP_URL` can be used as a fallback when `TWILIO_WEBHOOK_PUBLIC_BASE_URL` is absent.

## Behavior

1. Normalize the base URL by trimming trailing slash.
2. `GET {base_url}/api/health/azure`.
3. `POST {base_url}/api/telephony/twilio/incoming-call` with fake form data:

```text
CallSid=CA_TEST
From=+15550000000
To=+16082005400
FromCountry=US
```

4. Parse the XML response and verify it includes:

```text
/ws/telephony/twilio/CA_TEST
```

## Output

On success, print health and TwiML pass messages.

On failure, print actionable error text and exit non-zero.

## Test Scope

Unit tests must cover:

- URL construction.
- Missing env validation.
- TwiML parser success/failure.
- Mocked no-network request behavior.

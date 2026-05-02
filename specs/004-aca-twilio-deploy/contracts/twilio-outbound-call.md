# Contract: Twilio Outbound Call Helper

## File

`scripts/twilio_outbound_call.py`

## Purpose

Place a controlled outbound Twilio call from `+16082005400` to a verified test destination, using the Narayana public webhook URL for call handling.

## Inputs

Required environment variables:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_OUTBOUND_TO`
- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`

## Behavior

1. Validate all required values before any provider request.
2. Build webhook URL:

```text
{TWILIO_WEBHOOK_PUBLIC_BASE_URL}/api/telephony/twilio/incoming-call
```

3. POST to Twilio REST API to create a voice call.
4. Print call SID on success.
5. Print troubleshooting tips on Twilio errors.

## Safety and Scope

- Automated tests must not call Twilio.
- Documentation must explain verified caller ID setup for trial accounts.
- Documentation must explain Twilio Geo Permissions for Thailand outbound calling.
- The helper must not send SMS and must not dispatch emergency response.

## Test Scope

Unit tests must cover:

- URL construction.
- Missing env validation.
- Request body construction.
- Mocked Twilio success response parsing.
- Mocked Twilio error response reporting.

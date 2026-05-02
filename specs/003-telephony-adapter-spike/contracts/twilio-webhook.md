# Contract: Twilio Incoming Call Webhook

## Endpoint

`POST /api/telephony/twilio/incoming-call`

Accepts Twilio inbound call webhook form data and returns TwiML that connects the call to a Twilio Media Stream WebSocket when Twilio public callback configuration is present.

## Required Configuration

- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`

Optional metadata configuration:

- `TWILIO_PHONE_NUMBER`
- `PHONE_TEST_COUNTRY`
- `PHONE_TEST_NUMBER`

App startup must not require these values.

## Request

Content type:

- `application/x-www-form-urlencoded`

Relevant Twilio fields:

| Field | Required | Notes |
|-------|----------|-------|
| `CallSid` | Yes | Used as `{call_id}`. |
| `From` | No | Stored in `CallMetadata.from_number`. |
| `To` | No | Stored in `CallMetadata.to_number`. |
| `AccountSid` | No | Debug metadata only. |
| `FromCountry` | No | Preferred country value when present. |

## Successful Response

Status: `200 OK`

Content type: `application/xml`

Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://example.ngrok-free.app/ws/telephony/twilio/CA123">
      <Parameter name="source_input_mode" value="twilio_call" />
    </Stream>
  </Connect>
</Response>
```

Rules:

- The stream URL must use the configured public base URL converted to `wss://` when needed.
- The route must not start triage by itself; media processing happens on the WebSocket.

## Missing Configuration Response

Status: `503 Service Unavailable`

Example:

```json
{
  "detail": "Twilio webhook public base URL is not configured."
}
```

Rules:

- Missing Twilio config must not crash app startup.
- Local microphone and manual transcript routes remain usable.

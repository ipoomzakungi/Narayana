# Quickstart: Telephony Adapter Spike

## 1. Run Local Regression Gates

```powershell
python -m compileall app
pytest
cd frontend
npm test
npm run build
```

These commands must pass without Twilio or ACS credentials.

## 2. Configure Default Local Mode

Use local microphone mode unless actively testing a phone provider:

```powershell
$env:VOICE_INPUT_MODE="local_mic"
$env:TELEPHONY_PROVIDER="none"
$env:USE_MOCK_SERVICES="true"
```

Expected behavior:

- Manual transcript demo works.
- Local microphone WebSocket works.
- Mock mode can still create the deterministic Thai RED demo case.

## 3. Simulate Twilio Media Without Credentials

Run the backend tests that simulate Twilio media stream JSON:

```powershell
pytest tests/unit/test_twilio_audio_service.py tests/integration/test_twilio_media_flow.py
```

Expected behavior:

- Base64 mu-law payloads convert to PCM16 mono frames.
- Simulated media feeds `AudioSessionProcessor`.
- A mock RED case can be created through the same path as local microphone audio.

## 4. Configure Foreign-Number Twilio Test Mode

Set the public base URL from a tunnel such as ngrok or a deployed backend URL:

```powershell
$env:VOICE_INPUT_MODE="twilio_call"
$env:TELEPHONY_PROVIDER="twilio"
$env:PHONE_TEST_COUNTRY="US"
$env:PHONE_TEST_NUMBER="+15551234567"
$env:TWILIO_ACCOUNT_SID="AC..."
$env:TWILIO_AUTH_TOKEN="..."
$env:TWILIO_PHONE_NUMBER="+15557654321"
$env:TWILIO_WEBHOOK_PUBLIC_BASE_URL="https://example.ngrok-free.app"
```

Configure the Twilio voice webhook for the test number:

```text
POST https://example.ngrok-free.app/api/telephony/twilio/incoming-call
```

Expected webhook behavior:

- The incoming-call route returns TwiML with a media stream URL:
  `wss://example.ngrok-free.app/ws/telephony/twilio/{call_id}`
- The media WebSocket decodes inbound Twilio audio and sends normalized frames to the shared Narayana audio pipeline.

## 5. ACS Skeleton Check

Without ACS configuration, these routes should return clear disabled/not-implemented behavior:

```text
POST /api/telephony/acs/events
WS   /ws/telephony/acs/{call_id}
```

No ACS call streaming is required for this spike.

## Limitations

- A foreign-country test number validates call ingress only.
- It does not validate Thailand phone-number availability.
- It does not validate Thailand SMS support.
- It does not validate Thailand telecom cost or carrier behavior.
- It does not validate emergency-service compliance.
- It does not implement production authentication.
- It does not dispatch rescue or replace official emergency services.

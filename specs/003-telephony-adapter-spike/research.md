# Research: Telephony Adapter Spike

## Decision: Use a shared AudioSessionProcessor for all audio ingress

**Rationale**: The existing local microphone WebSocket already contains the correct Narayana flow: VAD, turn commit, WAV persistence, provider selection, Azure/mock processing, deterministic safety rules, and case repository writes. Extracting this into `AudioSessionProcessor` avoids duplicating safety or triage logic in provider routes and satisfies the requirement that telephony is only another `AudioFrame` source.

**Alternatives considered**:

- Build a separate telephony pipeline. Rejected because it would duplicate high-risk safety and case creation logic.
- Keep logic inside `routes_audio.py` and call helper functions from Twilio. Rejected because route-level reuse would make the Twilio WebSocket depend on local microphone protocol details.

## Decision: Implement Twilio first and keep ACS as a disabled skeleton

**Rationale**: Twilio Media Streams have a clear webhook-to-WebSocket flow and are easier to simulate offline. ACS call automation may be valuable later, but phone-number availability and media streaming behavior are still validation risks, so this spike should not block on it.

**Alternatives considered**:

- Implement ACS first. Rejected because the current acceptance criteria prioritize a foreign-country test number and simulated provider media.
- Implement both providers fully. Rejected because the spike should validate ingress architecture, not production phone-provider coverage.

## Decision: Normalize Twilio mu-law audio to PCM16 mono AudioFrame objects

**Rationale**: Narayana's existing audio gateway expects PCM16 mono `AudioFrame` messages. Twilio Media Streams commonly send base64 encoded G.711 mu-law at 8 kHz, so `twilio_audio_service.py` should decode the payload and convert it before invoking the shared processor.

**Alternatives considered**:

- Pass raw Twilio payloads into the turn manager. Rejected because VAD and WAV persistence are built around PCM16.
- Resample every frame to 16 kHz in V1. Rejected for the spike because WAV persistence and Azure Speech can preserve the frame sample rate, and resampling can be added later if quality requires it.

## Decision: Use Python stdlib audioop for Python 3.11, with audioop-lts noted for future Python versions

**Rationale**: The current backend target is Python 3.11, where `audioop.ulaw2lin` is available and sufficient for deterministic unit tests. `audioop` is deprecated and removed in later Python versions, so the implementation notes should allow `audioop-lts` if the runtime changes.

**Alternatives considered**:

- Add a new dependency immediately. Rejected because the current runtime can avoid extra install risk.
- Write a custom mu-law decoder. Rejected because the stdlib conversion is simpler and less error-prone for this spike.

## Decision: Keep Twilio media frames at 8 kHz unless resampling is explicitly added later

**Rationale**: Twilio media arrives at 8 kHz. Producing `AudioFrame(sample_rate_hz=8000, duration_ms=20, channels=1, encoding="pcm16")` makes the source format visible and keeps WAV persistence accurate.

**Alternatives considered**:

- Always upsample to 16 kHz. Rejected for V1 because it adds implementation risk and is not required to validate phone ingress.
- Reject 8 kHz audio. Rejected because it would prevent the intended Twilio spike.

## Decision: Return TwiML only when the public webhook base URL is configured

**Rationale**: Twilio needs a public `wss://` media stream URL. If `TWILIO_WEBHOOK_PUBLIC_BASE_URL` is missing, the route should return a clear configuration error so local startup still works and the failure is actionable.

**Alternatives considered**:

- Guess a public URL from request headers. Rejected because reverse proxies and tunnels make this unreliable.
- Fail application startup when Twilio config is missing. Rejected because local mic and mock mode must remain default.

## Decision: Automated telephony tests use simulated Twilio messages

**Rationale**: The test suite must not require real Twilio or ACS credentials. Simulated `start`, `media`, and `stop` messages can validate JSON parsing, audio normalization, shared processor reuse, and mock case creation.

**Alternatives considered**:

- Mark all telephony tests manual. Rejected because the spike needs regression coverage.
- Use real Twilio credentials in CI. Rejected because credentials and phone-number availability are intentionally out of scope.

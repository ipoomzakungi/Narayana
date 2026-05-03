# Research: Optional Twilio TTS Speak-Back

## Decision: Keep Speak-Back in the Twilio WebSocket Route

**Rationale**: The route already owns the active Twilio WebSocket and can send outbound messages on the same connection after normal processor payloads. This avoids changing the inbound audio pipeline or adding cross-service connection state.

**Alternatives considered**:
- Put outbound audio in `AudioSessionProcessor`: rejected because the processor is shared by local microphone and should not know Twilio WebSocket details.
- Create a separate outbound WebSocket manager: rejected for V0 because Twilio speak-back only needs the current active route session.

## Decision: Make TTS Strictly Feature-Gated and Default Disabled

**Rationale**: Existing Twilio demos and automated tests must keep working without Azure Speech credentials and without unexpected usage cost. `ENABLE_TWILIO_TTS_RESPONSE=false` preserves current behavior.

**Alternatives considered**:
- Enable TTS whenever Azure Speech is configured: rejected because it could surprise operators and add call cost.
- Tie TTS to `ENABLE_MULTI_TURN_INTAKE` only: rejected because multi-turn text decisions and spoken playback need separate rollout controls.

## Decision: Prefer Twilio-Compatible 8 kHz Mu-Law Output

**Rationale**: Twilio Media Streams expect outbound `media.payload` audio compatible with the call stream. Requesting or converting to 8 kHz mu-law keeps chunking and send format simple.

**Alternatives considered**:
- Send PCM directly to Twilio: rejected because outbound Media Stream playback expects encoded payloads compatible with Twilio's media format.
- Use browser playback: rejected because callers need to hear audio inside the phone call.

## Decision: Convert PCM to Mu-Law When Needed

**Rationale**: Azure Speech output format availability can vary. A fallback conversion path using the same audio conversion dependency family as inbound media protects the demo from format limitations.

**Alternatives considered**:
- Require raw mu-law output only: rejected because it makes the real demo brittle if SDK format selection differs.
- Add a heavy audio transcoder dependency now: rejected because 8 kHz mono PCM-to-mu-law conversion is small and testable.

## Decision: Return TTS Test Metadata Only

**Rationale**: The manual readiness endpoint is for configuration and payload shape validation. Returning raw audio payloads would increase response size and risk accidental logging.

**Alternatives considered**:
- Return base64 audio from `/api/tts/test`: rejected by the feature requirements.
- Do not add a readiness endpoint: rejected because real-call troubleshooting needs a low-risk check before placing calls.

## Decision: Sanitize Spoken Text Before Synthesis

**Rationale**: Spoken guidance reaches callers directly and must not include dispatch claims, ambulance-arrival claims, diagnosis language, or overlong instructions. Sanitization is deterministic and runs before any cloud call.

**Alternatives considered**:
- Trust intake response text as already safe: rejected because TTS adds a new caller-facing channel and needs its own final safety gate.
- Fail hard on unsafe text: rejected because replacing with concise safe text keeps calls moving and avoids losing the response.

## Decision: Log Metadata, Never Audio Payload

**Rationale**: Logs are needed for real-call debugging, but audio payloads can be large and sensitive. Start/completion/failure, chunk count, text length, stream ID, and duration estimate are enough for operations.

**Alternatives considered**:
- Log full outbound events: rejected because it would log base64 audio payloads.
- Log nothing: rejected because operators need evidence that synthesis was attempted.

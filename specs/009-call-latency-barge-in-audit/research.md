# Research: Call Latency, Barge-In, and Audit Debugging

## Decision: Tune the existing VAD/turn path instead of changing voice architecture

**Rationale**: The current backend already accepts Twilio media frames, normalizes them to `AudioFrame`, runs `TurnManager`, persists turn WAV, transcribes/intakes, and sends TTS responses. The fastest safe improvement is to make the existing silence threshold, pre-speech padding, energy threshold, and minimum speech duration configurable through `Settings`.

**Alternatives considered**:

- Azure Voice Live: closer to realtime, but explicitly out of scope for this feature and would rewrite the current call path.
- Client-side Twilio-only heuristics: would duplicate the backend VAD path and make local mic behavior diverge from telephony.

## Decision: Add `min_speech_ms` protection to `TurnManager`

**Rationale**: Lowering `TURN_SILENCE_THRESHOLD_MS` and `VAD_ENERGY_THRESHOLD` can improve perceived responsiveness but increases the risk of committing clicks or line noise. A minimum accumulated speech duration lets demo settings be faster without accepting very short noise as a committed caller turn.

**Alternatives considered**:

- Keep old conservative thresholds: safe but does not solve the demo latency complaint.
- Raise energy threshold only: can suppress noise but may miss quiet elderly or panicked callers.

## Decision: Treat assistant playback as explicit Twilio WebSocket state

**Rationale**: No-reply and barge-in both depend on whether assistant audio is currently active. Twilio mark events are the provider signal that buffered media has played, so the route should track current mark name, active response, speaking status, interrupted status, and completion time.

**Alternatives considered**:

- Use only estimated audio duration: useful fallback, but Twilio mark is the stronger completion signal.
- Track playback inside `TurnManager`: mixes audio playback transport state into VAD state and makes local mic behavior harder to reason about.

## Decision: Use Twilio `clear` for barge-in and stop remaining TTS chunks where possible

**Rationale**: Twilio Media Streams supports a `clear` event to clear buffered outbound audio. Narayana should send this as soon as speech is detected while assistant playback is active, mark the current response interrupted, and stop unsent chunks for that response.

**Alternatives considered**:

- Let current TTS finish: easiest but fails the caller interruption requirement.
- Close the call on interruption: unsafe and hostile to urgent crisis callers.

## Decision: Keep TTS send logic reusable and interruptible

**Rationale**: Greeting, follow-up, no-reply, closing, and RED responses all use the same Azure Speech TTS and Twilio media helpers. A reusable sender can report `tts.started`, `tts.completed`, mark names, chunk count, failure warnings, and interrupted status consistently.

**Alternatives considered**:

- Duplicate greeting/follow-up/no-reply send loops: simpler locally but risks inconsistent marks, logs, and interruption handling.
- Return generated audio to the frontend: not needed for Twilio call speak-back.

## Decision: Use the intake session store as the first call-audit session source

**Rationale**: The store already holds session id, call id, conversation turns, collected fields, guardrail warnings, decision audit, final case id, and lifecycle counters. Extending it with recent listing, call-id lookup, and timeline/TTS audit data meets demo debugging needs without adding Cosmos DB or another persistence layer.

**Alternatives considered**:

- Persist audit to Cosmos DB: useful later, but Cosmos is not configured and explicitly not part of this feature.
- Rely on Azure logs only: does not provide a compact caller/assistant timeline for operators.

## Decision: Add safe structured logging through a helper service

**Rationale**: The required event names need consistent fields and secret redaction. A small `call_audit_logger.py` helper can centralize safe event logging and optional timeline writes without changing the intake/voice provider contracts.

**Alternatives considered**:

- Ad hoc `logger.info` calls in every route/service: likely to diverge and accidentally include payloads.
- External logging SDK: unnecessary for this hackathon feature and not required by current deployment.

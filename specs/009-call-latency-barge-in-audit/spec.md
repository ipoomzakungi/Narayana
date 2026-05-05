# Feature Specification: Call Latency, Barge-In, and Audit Debugging

**Feature Branch**: `009-call-latency-barge-in-audit`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "Improve Narayana call latency, barge-in behavior, and call transcript/audit debugging. The demo currently works through Twilio, initial greeting, multi-turn intake, Azure Speech TTS speak-back, and scope guardrails, but conversation feels delayed and call logs do not provide an easy caller/assistant transcript timeline."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faster Demo Call Readiness (Priority: P1)

As a hackathon demo operator, I want clear warm-backend runbook commands and faster turn-timing controls so that calls do not feel stalled by cold starts or overly conservative speech-end detection.

**Why this priority**: The product already demonstrates the full phone-to-intake path, but perceived latency can make the voice demo feel less credible even when the pipeline is functioning.

**Independent Test**: Apply the documented warm mode, start a Twilio demo call, speak one normal Thai crisis sentence, and verify the backend is already available and the caller turn commits promptly using the configured demo timing.

**Acceptance Scenarios**:

1. **Given** the demo operator follows the warm-backend runbook, **When** a call reaches Narayana after a period of inactivity, **Then** the backend is already running with one replica and avoids a cold start.
2. **Given** the demo operator returns the system to low-cost mode, **When** the low-cost command is applied, **Then** the backend can scale down to zero replicas and the documentation warns that future calls may cold start.
3. **Given** demo turn timing is configured for faster detection, **When** a caller stops speaking after a normal sentence, **Then** Narayana commits the turn faster than the previous conservative defaults.
4. **Given** the microphone or phone line contains very short noise, **When** the audio duration is below the configured minimum speech duration, **Then** Narayana does not commit a caller turn from noise alone.

---

### User Story 2 - Caller Can Interrupt Assistant Speech (Priority: P1)

As a crisis caller, I want to interrupt the assistant while it is speaking so that urgent corrections or new details are heard immediately instead of waiting for the whole TTS response to finish.

**Why this priority**: Real callers may speak over the assistant when panicked, correcting a location, adding an injury, or saying someone is trapped. The assistant must stop playback and listen.

**Independent Test**: During a Twilio call, trigger a greeting or follow-up TTS response, speak while the assistant audio is still playing, and verify Narayana sends a Twilio clear event, stops remaining assistant audio when possible, and processes the caller speech.

**Acceptance Scenarios**:

1. **Given** assistant audio is currently being sent or buffered, **When** caller speech is detected, **Then** Narayana treats it as barge-in and sends a clear event for the current stream.
2. **Given** a barge-in has occurred, **When** remaining assistant TTS chunks have not yet been sent, **Then** Narayana stops sending the remaining chunks for that response when possible.
3. **Given** a barge-in interrupts a follow-up question, **When** the caller's new turn is transcribed, **Then** Narayana continues intake from the caller's new content and does not create a duplicate answer from the interrupted assistant audio.
4. **Given** the Twilio clear event cannot be confirmed or the caller disconnects, **When** barge-in is detected, **Then** Narayana logs the failure or disconnect and continues the call flow safely if the socket remains open.

---

### User Story 3 - No-Reply Waits Until Playback Completes (Priority: P1)

As a crisis caller, I want no-reply prompts to start only after the assistant has finished speaking so that I am not treated as silent while I am still hearing the greeting or follow-up.

**Why this priority**: The previous no-reply logic can feel premature if timers start before spoken audio has finished. Twilio mark tracking is needed for natural call pacing.

**Independent Test**: Start a call with initial greeting enabled and keep silent while the greeting plays; verify no no-reply prompt is sent until the greeting mark is received or playback completion is otherwise determined.

**Acceptance Scenarios**:

1. **Given** Narayana sends a greeting mark, **When** Twilio returns that mark, **Then** Narayana records assistant playback as completed and starts the no-reply timer from that point.
2. **Given** Narayana sends follow-up TTS with a mark, **When** Twilio returns the mark, **Then** the no-reply timer starts after that follow-up completes, not when TTS generation begins.
3. **Given** assistant audio is still in progress, **When** the no-reply threshold would otherwise be reached, **Then** Narayana does not send a no-reply prompt while the assistant is still speaking.
4. **Given** Twilio does not return a mark in a reasonable time, **When** the call remains connected, **Then** Narayana uses a safe fallback completion state, records a warning, and avoids repeated premature no-reply prompts.

---

### User Story 4 - Call Transcript and Audit Timeline (Priority: P2)

As a developer or operator, I want a call-audit view showing caller turns, assistant responses, TTS events, guardrail warnings, and case creation so that I can understand exactly what happened after each test call.

**Why this priority**: Azure logs show request and WebSocket lifecycle details, but demo debugging needs a human-readable timeline that ties caller speech, assistant speech, intake decisions, and case creation together.

**Independent Test**: Run a simulated or real Twilio call, then open the call-audit page, select the session, and verify the ordered timeline includes caller and assistant turns, TTS status, guardrail warnings, and whether a case was created.

**Acceptance Scenarios**:

1. **Given** at least one call session has occurred, **When** an operator opens `/call-audit`, **Then** recent sessions are listed with session id, call id when available, latest action, and timestamps.
2. **Given** an operator selects a session, **When** the detail view loads, **Then** it shows an ordered timeline of caller transcripts, assistant response text, TTS events, guardrail warnings, and case outcome.
3. **Given** a session created a case, **When** the audit detail is viewed, **Then** it shows the final case id, triage level, case group, and recommended team.
4. **Given** a session did not create a case, **When** the audit detail is viewed, **Then** it clearly shows the latest partial state, final call reason if any, and that no case was created.

---

### User Story 5 - Structured Troubleshooting Logs (Priority: P2)

As a developer monitoring a live demo, I want consistent structured event names for call, turn, intake, TTS, barge-in, and no-reply behavior so that I can quickly find the relevant lifecycle point in Azure logs.

**Why this priority**: Debugging latency and interrupted speech requires reliable log events without exposing secrets or audio payloads.

**Independent Test**: Run a call that includes greeting, one caller turn, one assistant response, a barge-in, and no-reply handling; verify the logs contain the required event names with call/session identifiers and no secrets or raw audio.

**Acceptance Scenarios**:

1. **Given** a Twilio call starts, **When** the WebSocket stream begins, **Then** Narayana logs `call.started` with safe call/session metadata.
2. **Given** a caller turn is committed and transcribed, **When** processing completes, **Then** Narayana logs `caller.turn.committed` and `caller.turn.transcribed`.
3. **Given** assistant response audio is generated and played, **When** TTS starts and completes, **Then** Narayana logs `tts.started` and `tts.completed`.
4. **Given** barge-in or no-reply occurs, **When** the behavior is triggered, **Then** Narayana logs `barge_in.detected`, `barge_in.clear_sent`, `no_reply.prompt`, or `call.closed` as appropriate.

### Edge Cases

- Caller speaks during the initial greeting before the greeting mark is received.
- Caller barges in repeatedly during several assistant responses.
- Twilio returns a mark late, out of order, or not at all.
- Twilio clear is sent but the caller disconnects immediately afterward.
- Assistant TTS generation succeeds but only part of the audio has been sent when barge-in occurs.
- Very short noise appears after assistant playback completes.
- The caller pauses mid-sentence longer than the faster silence threshold.
- A session ends before any case is created.
- A call creates a case and later receives additional caller speech.
- The backend is in low-cost mode and the first demo call experiences a cold start.
- Audit storage is reset by a backend restart before the operator opens the audit page.
- Multiple active calls generate timeline events at the same time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deployment documentation MUST include a demo warm command: `az containerapp update --name narayana-api --resource-group rg-narayana-demo --min-replicas 1 --max-replicas 1`.
- **FR-002**: The deployment documentation MUST include a low-cost command: `az containerapp update --name narayana-api --resource-group rg-narayana-demo --min-replicas 0 --max-replicas 1`.
- **FR-003**: The deployment documentation MUST explain that `min-replicas 0` can cause cold starts after inactivity.
- **FR-004**: Turn and VAD timing MUST be configurable with `TURN_SILENCE_THRESHOLD_MS`, `TURN_PRE_SPEECH_PADDING_MS`, `VAD_ENERGY_THRESHOLD`, and `MIN_SPEECH_MS`.
- **FR-005**: The default production behavior MAY remain conservative, but the documented demo configuration MUST support faster turn commit with `TURN_SILENCE_THRESHOLD_MS=500`, `TURN_PRE_SPEECH_PADDING_MS=200`, `VAD_ENERGY_THRESHOLD=0.015`, and `MIN_SPEECH_MS=300`.
- **FR-006**: The system MUST avoid committing a turn when detected speech is shorter than the configured minimum speech duration.
- **FR-007**: When caller speech is detected while assistant audio is active, the system MUST record barge-in detection for the current call/session.
- **FR-008**: On barge-in, the system MUST send a Twilio clear event shaped as `{"event":"clear","streamSid":"<streamSid>"}` when a stream id is available.
- **FR-009**: On barge-in, the system MUST stop sending remaining TTS chunks for the interrupted assistant response when possible.
- **FR-010**: Interrupted assistant audio MUST NOT produce a duplicate assistant answer or duplicate case action.
- **FR-011**: When the server sends a TTS mark event, it MUST track the current speaking mark name and associated assistant response.
- **FR-012**: When Twilio returns a mark event, the system MUST mark the corresponding assistant audio as completed.
- **FR-013**: No-reply timers MUST NOT run while assistant playback is active.
- **FR-014**: No-reply timing MUST start after greeting or assistant TTS playback completion, using Twilio mark events when available.
- **FR-015**: No-reply defaults for this feature MUST be `CALL_NO_REPLY_SECONDS=15`, `CALL_NO_REPLY_PROMPT_SECONDS=15`, and `CALL_MAX_NO_REPLY_PROMPTS=2`.
- **FR-016**: The system MUST expose `GET /api/intake/sessions` to list recent intake/call sessions for debugging.
- **FR-017**: The system MUST expose `GET /api/intake/sessions/{session_id}` to retrieve a session timeline by session id.
- **FR-018**: The system MUST expose `GET /api/intake/calls/{call_id}` to retrieve a session timeline by call id.
- **FR-019**: Audit responses MUST include session id, call id when available, conversation turns, caller transcript, assistant response text, TTS profile/status, case group, recommended team, triage level, guardrail warnings, no-reply prompt count, off-topic count, call end reason, final case id, created timestamp, and updated timestamp when available.
- **FR-020**: The frontend MUST provide `/call-audit` with recent session list, selectable session detail, ordered timeline, TTS events, guardrail warnings, and case-created state.
- **FR-021**: Structured logs MUST include clear event names for `call.started`, `greeting.started`, `greeting.completed`, `caller.turn.committed`, `caller.turn.transcribed`, `intake.followup`, `assistant.response`, `tts.started`, `tts.completed`, `barge_in.detected`, `barge_in.clear_sent`, `no_reply.prompt`, and `call.closed`.
- **FR-022**: Logs MUST NOT include secrets, raw audio payloads, full Azure Speech keys, Twilio auth tokens, or other credential material.
- **FR-023**: Existing Twilio route paths, initial greeting behavior, multi-turn intake behavior, Azure Speech TTS speak-back, scope guardrails, and dashboard behavior MUST remain compatible.
- **FR-024**: The feature MUST NOT implement Azure Voice Live, ACS, SMS, rescue dispatch, or new Azure OpenAI enablement.

### Key Entities *(include if feature involves data)*

- **Turn Timing Configuration**: Runtime controls for silence threshold, pre-speech padding, VAD energy threshold, and minimum speech duration.
- **Assistant Playback State**: Per-call state indicating whether assistant audio is active, current mark name, current TTS response id, playback start time, playback completion time, and whether playback was interrupted.
- **Barge-In Event**: A record that caller speech occurred during assistant playback, including call/session identifiers, current mark name, whether a clear event was sent, and whether remaining chunks were stopped.
- **TTS Mark Event**: A record of server-sent and Twilio-returned marks used to determine assistant playback completion.
- **Call Audit Session**: Recent call/intake debug state containing session id, optional call id, source input mode, conversation turns, TTS events, intake decisions, guardrail warnings, case outcome, and lifecycle counters.
- **Timeline Event**: Ordered audit item representing caller turns, assistant turns, TTS start/completion, barge-in, no-reply prompts, intake decisions, guardrail overrides, and case creation.
- **Warm Deployment Mode**: Demo runbook state where the backend is kept at one replica for responsiveness, with a documented low-cost return path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A demo operator can switch the backend to warm mode and back to low-cost mode using documented commands in under 2 minutes.
- **SC-002**: With demo timing configured, a normal Thai caller sentence commits within 1 second after the caller stops speaking in simulated or manual Twilio testing.
- **SC-003**: Speech shorter than `MIN_SPEECH_MS=300` does not create a committed caller turn in VAD state tests.
- **SC-004**: In barge-in tests, 100% of detected caller interruptions during assistant playback send a Twilio clear event when a stream id is available.
- **SC-005**: In barge-in tests, interrupted responses do not send duplicate assistant answers or duplicate case-created events.
- **SC-006**: No-reply tests verify that prompts are not sent while assistant playback is active and start only after playback completion or safe fallback completion.
- **SC-007**: After a simulated Twilio call, `/call-audit` shows caller turns, assistant turns, TTS events, guardrail warnings, and case-created state for the session.
- **SC-008**: Audit endpoints return recent sessions and lookup by session id or call id with the required fields.
- **SC-009**: Structured logs contain the required lifecycle event names and omit secrets and audio payloads.
- **SC-010**: Existing Twilio inbound call, initial greeting, multi-turn intake, TTS speak-back, and scope guardrail regression tests continue to pass.

## Assumptions

- This feature improves responsiveness within the existing Twilio Media Stream plus STT/intake/TTS path; it does not provide true full-duplex Azure Voice Live behavior.
- Barge-in can clear audio buffered by Twilio, but audio already played to the caller cannot be recalled.
- The first implementation may keep audit sessions in a recent in-memory or local debug store suitable for demos; durable long-term audit retention can be planned separately.
- If Twilio mark events are delayed or missing, a conservative fallback playback-complete timeout is acceptable as long as it is logged and does not spam no-reply prompts.
- The same backend and frontend deployments remain in use: Azure Container Apps for FastAPI and Azure Static Web Apps for the frontend.
- Azure OpenAI, Cosmos DB, ACS, SMS, and emergency dispatch integrations remain outside this feature.

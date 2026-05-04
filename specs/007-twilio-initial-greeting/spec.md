# Feature Specification: Twilio Initial Greeting

**Feature Branch**: `007-twilio-initial-greeting`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: User description: "Add first-greeting speak-back to Narayana Twilio calls. When a caller connects to the Twilio Media Stream, Narayana should greet the caller first using Azure Speech TTS, then listen for the caller's emergency/crisis description. Greeting is optional, disabled by default, configurable, safe, and must not change Twilio route paths."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Caller Hears Narayana First (Priority: P1)

As a caller in a Twilio-powered Narayana test call, I want to hear a short Thai greeting immediately after the call connects so that I know I can start describing the emergency situation and location.

**Why this priority**: The current phone flow only speaks after the caller has already said something. A first greeting makes the phone demo feel like a natural crisis intake conversation.

**Independent Test**: Enable the initial greeting for a controlled Twilio call, answer the call, and verify the caller hears one short Thai greeting before giving any emergency description.

**Acceptance Scenarios**:

1. **Given** initial greeting is enabled and speech synthesis is configured, **When** Twilio sends the call start event with a stream identifier, **Then** Narayana speaks the configured Thai greeting once in the same call.
2. **Given** the greeting has completed, **When** the caller speaks their crisis description, **Then** the existing media intake, turn detection, multi-turn intake, and case creation behavior continues normally.
3. **Given** the greeting is enabled for a call, **When** multiple media frames arrive after the start event, **Then** Narayana does not replay the greeting for that call.

---

### User Story 2 - Preserve Current Call Behavior by Default (Priority: P1)

As a demo operator, I want the initial greeting disabled by default so that existing Twilio inbound tests and speak-back behavior stay unchanged unless I explicitly enable the new greeting.

**Why this priority**: The deployed Twilio path is already working. The new greeting must not surprise operators, increase cost by default, or change existing webhook behavior.

**Independent Test**: Run the existing Twilio simulated media flow with default settings and verify no initial greeting audio is attempted while the existing call flow still works.

**Acceptance Scenarios**:

1. **Given** the initial greeting setting is disabled, **When** a Twilio call starts, **Then** no greeting audio is generated or sent.
2. **Given** the initial greeting is disabled, **When** the caller speaks and Narayana later returns response text, **Then** existing optional response speak-back behavior remains unchanged.
3. **Given** the application starts without speech synthesis credentials, **When** initial greeting remains disabled, **Then** startup and Twilio media handling still work.

---

### User Story 3 - Continue Listening When Greeting Fails (Priority: P1)

As a crisis operator, I want the call to continue even if the greeting cannot be spoken so that a greeting failure never blocks emergency intake.

**Why this priority**: Caller intake is more important than spoken greeting. Failures must degrade safely.

**Independent Test**: Enable the initial greeting while speech synthesis is unavailable or forced to fail, start a Twilio call, and verify the call remains connected and caller audio is still processed.

**Acceptance Scenarios**:

1. **Given** initial greeting is enabled but speech synthesis is not configured, **When** a Twilio call starts, **Then** Narayana logs a warning and continues listening without closing the call.
2. **Given** speech synthesis fails while generating the greeting, **When** the failure occurs, **Then** Narayana logs the failure and continues normal media handling.
3. **Given** the greeting cannot be spoken, **When** the caller speaks, **Then** the caller's audio can still produce follow-up prompts or crisis cases.

---

### User Story 4 - Keep Greeting Safe and Configurable (Priority: P2)

As a demo operator, I want the greeting text and speaking profile to be configurable while preserving crisis-safety boundaries so that Narayana sounds calm without making unsafe claims.

**Why this priority**: Different demos may need slightly different wording, but the greeting must remain short and safe for crisis intake.

**Independent Test**: Configure a valid short Thai greeting and verify it is spoken; configure unsafe or overlong greeting text and verify the spoken output is replaced or shortened to safe language.

**Acceptance Scenarios**:

1. **Given** a configured Thai greeting under the spoken length limit, **When** the greeting is played, **Then** the caller hears that greeting using the configured calm speaking behavior.
2. **Given** configured greeting text claims rescue has been dispatched or that this is an official hotline replacement, **When** greeting playback is attempted, **Then** the spoken text is replaced with concise safe intake language.
3. **Given** configured greeting text exceeds the maximum spoken length, **When** greeting playback is attempted, **Then** the greeting is shortened or replaced before synthesis.

---

### User Story 5 - Troubleshoot Greeting Playback (Priority: P3)

As a hackathon developer, I want clear logs and health/debug visibility for greeting playback so that I can confirm whether the first greeting started, completed, failed, or was skipped.

**Why this priority**: Greeting playback happens before caller speech, so logs are the primary way to verify behavior during real Twilio calls.

**Independent Test**: Start a Twilio call with greeting enabled and verify logs contain greeting start and completion events with chunk count and no secrets or raw audio payloads.

**Acceptance Scenarios**:

1. **Given** greeting playback starts, **When** logs are reviewed, **Then** they show a greeting started event with call/session identifiers and no secrets.
2. **Given** greeting playback completes, **When** logs are reviewed, **Then** they show a greeting completed event with media chunk count or duration estimate.
3. **Given** health or debug status is checked, **When** greeting settings are active, **Then** operators can see that initial greeting is enabled and which greeting behavior is selected without seeing secret values.

### Edge Cases

- Twilio start event is missing the stream identifier required for outbound media.
- Initial greeting is enabled but speech synthesis credentials are missing.
- Speech synthesis returns empty audio or no playable chunks.
- Caller starts speaking while greeting audio is being sent.
- Greeting text is blank, too long, or contains unsafe dispatch/official-hotline language.
- Twilio WebSocket disconnects while greeting chunks are being sent.
- Greeting fallback through provider-native voice is requested but disabled.
- Greeting setting is enabled for non-Twilio input modes; no greeting should be attempted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Initial greeting speak-back MUST be disabled by default and require explicit opt-in.
- **FR-002**: The existing Twilio incoming-call webhook path and media WebSocket path MUST remain unchanged.
- **FR-003**: When enabled for a Twilio call, the system MUST speak one greeting after the Twilio start event provides a usable stream identifier.
- **FR-004**: The system MUST send a playback completion marker after greeting audio is sent so the call session can correlate greeting completion.
- **FR-005**: Greeting playback MUST happen at most once per call.
- **FR-006**: After greeting playback is skipped, fails, or completes, the system MUST continue normal caller audio intake.
- **FR-007**: If speech synthesis is not configured, greeting playback MUST log a warning and continue listening without crashing the call.
- **FR-008**: If greeting synthesis or media sending fails, the call MUST remain active when possible and normal media handling MUST continue.
- **FR-009**: Greeting text MUST be configurable and default to a short Thai crisis-intake greeting.
- **FR-010**: Greeting spoken text MUST remain under 220 Thai characters after safety processing.
- **FR-011**: Greeting spoken text MUST NOT claim rescue or medical responders have been dispatched.
- **FR-012**: Greeting spoken text MUST NOT claim Narayana is an official emergency hotline replacement.
- **FR-013**: Greeting playback MUST use the existing speech synthesis safety checks for dispatch claims, diagnostic wording, and overlong content.
- **FR-014**: Greeting playback MUST use calm Thai speech behavior compatible with the existing voice profile controls.
- **FR-015**: Greeting logs MUST include greeting started, completed, and failed outcomes without logging secrets or raw audio payloads.
- **FR-016**: Health or debug output MUST indicate whether initial greeting is enabled and expose no secret values.
- **FR-017**: A provider-native voice fallback before connecting the media stream MAY be supported, but it MUST be disabled by default.
- **FR-018**: Existing optional response speak-back after caller speech MUST continue to work independently from the first greeting.
- **FR-019**: Automated tests MUST validate disabled-by-default behavior, successful greeting payload shape with mocked synthesis, and safe continuation after greeting failure without requiring real cloud credentials.

### Key Entities *(include if feature involves data)*

- **Initial Greeting Configuration**: Operator-controlled settings for whether greeting is enabled, the greeting text, the speaking profile, and optional fallback behavior.
- **Twilio Call Session**: Active call context that includes call identifier, stream identifier, source mode, and whether the initial greeting has already been attempted.
- **Greeting Playback Attempt**: Audit/debug event describing greeting start, completion, failure, chunk count, selected profile, and safety warnings.
- **Spoken Greeting Text**: The caller-facing greeting after safety filtering and length enforcement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With greeting disabled, 100% of existing Twilio simulated media tests pass without sending greeting audio.
- **SC-002**: With greeting enabled and speech synthesis configured, a caller hears the greeting within 5 seconds of Twilio stream start in a controlled real-call demo.
- **SC-003**: Greeting playback occurs no more than once per call across repeated media frames and call messages.
- **SC-004**: In failure tests, 100% of greeting synthesis failures continue to allow caller media processing without closing the call due to the greeting failure.
- **SC-005**: No automated test requires real Twilio or cloud speech credentials to validate greeting behavior.
- **SC-006**: Logs for successful greeting playback include started and completed events, while containing zero secret values and zero raw audio payloads.

## Assumptions

- The first greeting is only for Twilio call sessions in this feature.
- Existing speech synthesis configuration, safety filtering, and voice profile support are reused for greeting playback.
- The default Thai greeting is: "สวัสดีค่ะ นารายานาพร้อมรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ".
- The greeting profile should be calm, clear, and slightly slow; a dedicated greeting profile can map to existing normal or follow-up voice behavior if needed.
- Provider-native voice fallback before connecting the media stream is optional and remains disabled unless explicitly enabled.
- This feature does not add ACS, SMS, Azure OpenAI enablement, dispatch actions, or route path changes.

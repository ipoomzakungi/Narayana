# Feature Specification: Optional Twilio TTS Speak-Back

**Feature Branch**: `006-twilio-tts-speakback`  
**Created**: 2026-05-03  
**Status**: Draft  
**Input**: User description: "Add optional Twilio speak-back using Azure Speech TTS for Narayana. When the intake system returns response_text, optionally synthesize it with Azure Speech TTS and stream it back to the Twilio call as audio, disabled by default."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Caller Hears Follow-Up Question (Priority: P1)

As a caller in a Twilio-powered Narayana test call, I want to hear Narayana's short Thai follow-up question after I speak so that the crisis intake can continue naturally by voice instead of only showing text in the debug console.

**Why this priority**: The current phone path receives caller audio and creates intake decisions, but callers cannot hear the AI response. Spoken follow-up is the core value of this feature.

**Independent Test**: Enable multi-turn intake and Twilio speak-back in a controlled test call, trigger a response text such as "ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?", and verify the caller hears the spoken response while the existing case/debug payloads continue to arrive.

**Acceptance Scenarios**:

1. **Given** Twilio speak-back is enabled and speech synthesis is configured, **When** Narayana returns a non-empty follow-up response for a call, **Then** the caller hears a short Thai spoken response in the same call.
2. **Given** Narayana creates or escalates a case and includes a safe response text, **When** speak-back is enabled and configured, **Then** the response is spoken without blocking case creation.
3. **Given** the caller interrupts or continues speaking after a response is sent, **When** the next caller turn is received, **Then** the system continues to process the call through the existing intake flow.

---

### User Story 2 - Preserve Safe Defaults and Existing Calls (Priority: P1)

As a hackathon operator, I want Twilio speak-back to be disabled by default so that current Twilio webhook tests, WebSocket tests, and mock demonstrations keep working unless I explicitly enable the new audio response.

**Why this priority**: The deployed backend already supports Twilio ingress. Optional output audio must not destabilize the current demo or increase costs unexpectedly.

**Independent Test**: Run the existing simulated Twilio call flow with speak-back disabled and verify no outbound spoken audio is attempted, the same case/debug messages are emitted, and no new cloud credentials are required.

**Acceptance Scenarios**:

1. **Given** Twilio speak-back is disabled, **When** Narayana receives a Twilio call and creates an intake response, **Then** no spoken audio is generated and the existing JSON/debug behavior is unchanged.
2. **Given** speak-back is enabled but speech synthesis is not configured, **When** Narayana returns response text, **Then** the system logs a safe warning and continues the call without crashing or blocking case creation.
3. **Given** speech synthesis fails during a call, **When** the failure occurs, **Then** the caller session remains active and normal debug/case payloads are still sent.

---

### User Story 3 - Validate Speech Synthesis Readiness (Priority: P2)

As a developer preparing a real-call demo, I want a manual TTS readiness check so that I can verify configuration, voice selection, format, and payload counts without returning raw audio in an API response.

**Why this priority**: Real call testing depends on cloud speech synthesis. A small readiness check reduces call-debugging time and avoids exposing audio payloads.

**Independent Test**: Submit a short Thai test phrase to the TTS test endpoint and verify the response reports whether synthesis is configured, the selected voice, audio format, chunk count, and byte count without including the full audio payload.

**Acceptance Scenarios**:

1. **Given** speech synthesis is configured, **When** a short Thai phrase is submitted for testing, **Then** the response reports configured status, selected voice, expected audio format, payload count, and total bytes.
2. **Given** speech synthesis is not configured, **When** a short Thai phrase is submitted for testing, **Then** the response clearly reports unconfigured status without failing the backend.
3. **Given** a test phrase is too long, **When** it is submitted, **Then** the phrase is shortened or replaced with a safe concise response before synthesis.

---

### User Story 4 - Keep Spoken Guidance Safe (Priority: P2)

As a crisis operator, I want Narayana's spoken response to follow the same safety rules as text responses so that callers do not hear claims of official dispatch, unsafe medical diagnosis, or overconfident emergency guidance.

**Why this priority**: Spoken output is more direct to callers than debug text. It must preserve crisis safety boundaries.

**Independent Test**: Submit response texts containing prohibited dispatch claims, ambulance-arrival claims, diagnosis-like phrasing, and overlong guidance; verify the spoken response is replaced or shortened to approved safe language.

**Acceptance Scenarios**:

1. **Given** response text says rescue has been dispatched, **When** speak-back is requested, **Then** the spoken response is replaced with safe review language.
2. **Given** response text says an ambulance is on the way, **When** speak-back is requested, **Then** the spoken response does not include that claim.
3. **Given** response text is longer than the configured speaking limit, **When** speak-back is requested, **Then** the spoken response is shortened or replaced with a concise safe response.

---

### User Story 5 - Operate and Troubleshoot Demo Calls (Priority: P3)

As a hackathon developer, I want clear operational documentation and logs for Twilio speak-back so that I can enable the feature only for real-call demos, monitor synthesis attempts, and understand cost implications.

**Why this priority**: The feature is optional and cloud-backed. Documentation and logs are necessary for demos but do not block the core speak-back behavior.

**Independent Test**: Follow the documented steps to enable speak-back for a test call, check health status, run the manual readiness test, place a call, and confirm logs show synthesis start/completion without secrets or audio payloads.

**Acceptance Scenarios**:

1. **Given** a developer reads the documentation, **When** they enable speak-back, **Then** they can identify all required settings and understand that the feature is disabled by default.
2. **Given** a spoken response is attempted, **When** logs are reviewed, **Then** logs show start/completion status, chunk count, and estimated duration without secrets or audio payloads.
3. **Given** a real-call demo is planned, **When** the operator checks documentation, **Then** it warns about Azure Speech usage cost and confirms that SMS, dispatch, ACS, Cosmos DB changes, and route changes are out of scope.

### Edge Cases

- Speech synthesis is enabled but cloud speech credentials are missing.
- Speech synthesis returns empty audio or an unsupported format.
- Audio conversion succeeds but outbound audio chunking produces zero playable chunks.
- Twilio start metadata does not include a stream identifier needed for outbound media.
- The caller disconnects while spoken response chunks are being sent.
- Response text contains prohibited dispatch, ambulance-arrival, or diagnostic wording.
- Response text exceeds the maximum allowed spoken length.
- Speech synthesis fails after the case has already been created or follow-up payload has already been prepared.
- Speak-back is enabled for non-Twilio input modes; no outbound call audio should be attempted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Twilio speak-back MUST be disabled by default and require explicit opt-in.
- **FR-002**: Existing Twilio incoming-call and media-stream routes MUST remain unchanged.
- **FR-003**: Existing Twilio media intake and simulated Twilio tests MUST continue to work when speak-back is disabled.
- **FR-004**: Speak-back MUST only be attempted for Twilio call sessions when the feature is enabled, response text is non-empty, and speech synthesis is configured.
- **FR-005**: Speak-back MUST use the response text returned by the intake flow, including follow-up questions and safe case/escalation acknowledgements.
- **FR-006**: Spoken output MUST use Thai speech settings by default, including the configured Thai voice when available.
- **FR-007**: Spoken output MUST be compatible with Twilio call playback.
- **FR-008**: The system MUST split synthesized output into caller-playable chunks and send them over the same active Twilio call session.
- **FR-009**: The system MUST send a completion marker after outbound spoken audio so the call session can correlate playback completion.
- **FR-010**: The system MUST retain the Twilio stream identifier from call start metadata for outbound playback.
- **FR-011**: If speech synthesis fails, the system MUST log a warning, continue sending normal debug/case payloads, and keep the call session active when possible.
- **FR-012**: Speech synthesis failures MUST NOT prevent case creation, case escalation, or follow-up debug payload delivery.
- **FR-013**: Health status MUST show whether Twilio speak-back is enabled, whether speech synthesis is configured, and which voice is selected.
- **FR-014**: A manual TTS test MUST accept short text and report configuration status, selected voice, audio format, payload count, and total byte count.
- **FR-015**: The manual TTS test MUST NOT return the full audio payload by default.
- **FR-016**: Spoken response text MUST be checked before synthesis for prohibited dispatch claims, ambulance-arrival claims, diagnostic language, and overlong content.
- **FR-017**: If response text violates spoken safety rules, the system MUST replace it with concise safe review language before synthesis.
- **FR-018**: Logs MUST include synthesis start, completion, chunk count, and duration estimate when available.
- **FR-019**: Logs MUST NOT include secrets or raw audio payloads.
- **FR-020**: Documentation MUST explain how to enable speak-back, required speech configuration, real-call test steps, health checks, logs, cost warning, and default-disabled behavior.
- **FR-021**: This feature MUST NOT implement SMS, official rescue dispatch, Azure Communication Services production behavior, Cosmos DB resources, or route changes.

### Key Entities *(include if feature involves data)*

- **Speak-Back Configuration**: Feature state and voice settings controlling whether Narayana may synthesize response text for Twilio calls.
- **Spoken Response Request**: The response text, language, selected voice, session identifier, and call identifier used to prepare caller audio.
- **Spoken Audio Result**: The caller-playable audio chunks, total bytes, selected format, and estimated duration produced for a response.
- **Twilio Playback Message**: A media or completion marker sent back to the active call session for outbound playback.
- **TTS Health Summary**: Operational status showing whether speech synthesis is configured, enabled, and ready for test calls.
- **TTS Test Result**: A safe readiness response that reports counts and status without exposing raw audio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With speak-back disabled, 100% of existing Twilio simulated call tests continue to pass without new cloud credentials.
- **SC-002**: With speak-back enabled and mocked speech synthesis, a simulated call produces at least one caller-playable outbound audio message and a playback completion marker.
- **SC-003**: In 100% of tested speech synthesis failures, the call flow continues to send normal debug/case output and does not crash because of the synthesis failure.
- **SC-004**: The manual TTS readiness check reports configured/unconfigured status, selected voice, audio format, payload count, and total bytes without returning raw audio payload.
- **SC-005**: In safety tests, 100% of spoken responses avoid dispatch claims, ambulance-arrival claims, automatic closure/rejection language, and diagnosis wording.
- **SC-006**: In a real-call demo with speech credentials configured, the caller can hear Narayana's Thai response within one normal response cycle after the intake decision is produced.
- **SC-007**: Operational logs for spoken responses include start/completion status and chunk count for 100% of attempted syntheses, without secrets or raw audio.

## Assumptions

- Twilio remains the only phone-provider output path for this feature.
- Multi-turn intake is enabled separately when callers should receive follow-up questions.
- The first spoken response is text-to-speech only; the feature does not add speech recognition, triage, or case creation behavior beyond what already exists.
- The default spoken language is Thai.
- Azure Speech credentials used for speech-to-text can also support speech synthesis when configured.
- If the speech service cannot produce a directly compatible call format, conversion to a caller-compatible format is acceptable.
- Speak-back for local microphone, manual transcript, and ACS inputs is out of scope.
- This feature is for hackathon validation and does not make Narayana an official emergency hotline or dispatch system.

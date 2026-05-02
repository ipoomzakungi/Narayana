# Feature Specification: Narayana AI Azure Voice Gateway

**Feature Branch**: `001-crisis-voice-triage`  
**Created**: 2026-05-02  
**Status**: Revised  
**Input**: User description: "Create an optimized Azure Voice Gateway module for the AI Crisis Management hackathon project."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Local Voice Intake Pipeline (Priority: P1)

As a hackathon developer, I want to test crisis voice intake from my local microphone so that I can validate turn detection, speech processing, structured triage extraction, safety rules, and case creation before integrating a real phone provider.

**Why this priority**: This proves the core voice-AI pipeline without blocking on Twilio, Azure Communication Services phone-number availability, Thailand number support, or trial-account restrictions.

**Independent Test**: Start a local microphone intake session, speak the Thai flood scenario, and verify that the module returns a structured crisis case with RED triage and human review required.

**Acceptance Scenarios**:

1. **Given** a local microphone voice session is active, **When** the caller says "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง", **Then** the module returns a case object with language `th`, incident type `flood`, triage level `RED`, location text containing Hat Yai or หาดใหญ่, injuries describing elderly breathing difficulty, immediate needs including rescue and medical help, human review required, status `pending`, and a triage reason explaining trapped person plus breathing difficulty.
2. **Given** cloud speech credentials are unavailable, **When** the developer runs the same local microphone scenario, **Then** the module uses a mock provider and still returns a valid structured case for demo validation.
3. **Given** cloud speech credentials are available, **When** the developer runs the same local microphone scenario, **Then** the module can use the configured Azure provider while preserving the same case JSON contract and safety rules.

---

### User Story 2 - Observe VAD, Turn Detection, and Barge-In (Priority: P1)

As a hackathon developer, I want visible voice gateway state and timing logs so that I can debug whether the system listens, waits, thinks, speaks, and yields correctly during a noisy or interrupted crisis conversation.

**Why this priority**: The demo depends on proving that the assistant does not respond while the caller is still speaking and can flag interruption when caller speech overlaps assistant output.

**Independent Test**: Use a local microphone session with speech, silence, a long pause, and an interruption while assistant speech is marked active; verify state transitions and timing events.

**Acceptance Scenarios**:

1. **Given** a voice session is receiving audio, **When** the caller is silent, speaking, waiting for response, the module is processing, or assistant output is active, **Then** the gateway exposes one of these states: silence, speech, listening, thinking, speaking.
2. **Given** a caller finishes speaking, **When** the configured silence threshold is reached, **Then** the gateway closes the user turn and sends only the completed user turn for speech/AI processing.
3. **Given** assistant output is active, **When** caller speech is detected, **Then** the gateway marks a barge-in event and starts a new caller turn without treating the assistant output as emergency evidence.

---

### User Story 3 - Enforce Crisis Safety Rules After AI Output (Priority: P1)

As a hackathon developer, I want deterministic safety rules applied after AI extraction so that crisis triage is explainable, conservative, and never relies only on model judgment.

**Why this priority**: Crisis triage can affect human response. The module must not dispatch, close, reject, or downgrade emergency cases without human review.

**Independent Test**: Run sample transcripts for breathing difficulty, trapped person, severe bleeding, unconsciousness, drowning risk, active fire danger, missing location, low confidence, and contradictory facts; verify the safety overlay result.

**Acceptance Scenarios**:

1. **Given** AI extraction reports breathing difficulty, trapped person, severe bleeding, unconsciousness, drowning risk, or active fire danger, **When** deterministic safety rules run, **Then** triage is forced to RED and human review is required.
2. **Given** AI extraction has low confidence, missing location, or contradictory facts, **When** deterministic safety rules run, **Then** human review is required and the case is not downgraded automatically.
3. **Given** the module generates guidance, **When** the guidance is returned, **Then** it is short, safe, and frames Narayana AI as an intake and triage assistant, not an official emergency hotline replacement.

---

### User Story 4 - Keep Phone Providers as Future Adapters (Priority: P2)

As a hackathon developer, I want clean adapter interfaces for local microphone, uploaded audio, Twilio Media Streams, and Azure Communication Services so that V0 can demo locally while V1 phone integrations are validated separately.

**Why this priority**: The project needs a credible path to phone intake, but real phone number acquisition and provider restrictions must not block the hackathon MVP.

**Independent Test**: Inspect adapter registration and runtime configuration to verify that local browser microphone is required for V0, uploaded audio is optional, and Twilio/ACS adapters exist only as disabled V1 interfaces.

**Acceptance Scenarios**:

1. **Given** V0 runtime configuration, **When** input adapters are loaded, **Then** local browser microphone is available and Twilio/ACS adapters are not required.
2. **Given** an uploaded audio sample is provided, **When** optional upload processing is enabled, **Then** the gateway processes it through the same turn, extraction, safety, and case-output contract as microphone input.
3. **Given** a developer reviews future phone integration points, **When** they inspect the adapter interfaces, **Then** Twilio Media Stream and Azure Communication Services adapters are clearly marked V1 and not wired into the default V0 demo path.

### Edge Cases

- Caller speech is noisy, panicked, very quiet, clipped, or contains long pauses.
- Caller interrupts assistant output while the system is in speaking state.
- Caller gives no location, ambiguous location, or only a landmark.
- AI output is malformed, incomplete, low-confidence, or contradicts previous extracted facts.
- The caller reports a RED safety indicator but also says they are currently safe.
- Azure credentials are missing, invalid, expired, or configured for a region without the desired voice capability.
- Uploaded audio is too long, corrupt, unsupported, or contains no speech.
- A future telephony adapter is present in code but should remain disabled in V0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST support local browser microphone intake as the required V0 input mode.
- **FR-002**: The module MUST NOT require Twilio, Azure Communication Services, real phone numbers, real SMS sending, or production call setup for V0.
- **FR-003**: The module MUST expose adapter boundaries for local browser microphone, optional uploaded audio sample, Twilio Media Stream V1, and Azure Communication Services V1.
- **FR-004**: V0 runtime MUST load the local microphone input path by default and MUST keep Twilio and Azure Communication Services adapters disabled unless explicitly enabled in a future version.
- **FR-005**: Browser audio MUST be streamed to the backend through a live session connection suitable for incremental audio frames.
- **FR-006**: The backend MUST expose voice gateway state as silence, speech, listening, thinking, or speaking.
- **FR-007**: The backend MUST detect end-of-turn using local voice activity or turn detection plus a silence threshold.
- **FR-008**: The backend MUST avoid sending incomplete caller speech turns for AI interpretation.
- **FR-009**: The backend MUST support a barge-in flag when caller speech is detected while assistant output is active.
- **FR-010**: The module MUST run with a mock AI provider when Azure credentials are missing.
- **FR-011**: The module MUST run with Azure Speech speech-to-text plus Azure OpenAI structured triage extraction when credentials are available.
- **FR-012**: The module SHOULD support Azure Voice Live when configured, without making it the only V0 voice path.
- **FR-013**: The module MUST return structured crisis JSON for each completed crisis intake case.
- **FR-014**: The structured case JSON MUST include language, incident_type, triage_level, location_text, people_affected, injuries, immediate_needs, human_review_required, triage_reason, extracted facts, confidence, and status.
- **FR-015**: For the Thai flood scenario, the case JSON MUST output language `th`, incident_type `flood`, triage_level `RED`, location_text containing Hat Yai or หาดใหญ่, injuries describing elderly breathing difficulty, immediate_needs including rescue and medical help, human_review_required `true`, and status `pending`.
- **FR-016**: The module MUST apply deterministic safety rules after AI output and before emitting or storing a case.
- **FR-017**: Breathing difficulty, trapped person, severe bleeding, unconsciousness, drowning risk, or active fire danger MUST force RED triage and human review.
- **FR-018**: RED, confidence below 0.75, missing-location, or contradictory cases MUST require human review.
- **FR-019**: The module MUST NOT dispatch rescue automatically.
- **FR-020**: The module MUST NOT close, reject, deny, or downgrade emergency cases without human review.
- **FR-021**: AI-generated guidance MUST be short, safe, and must not claim official emergency hotline authority.
- **FR-022**: Every AI decision MUST include extracted facts and an explainable reason.
- **FR-023**: The module MUST store the case object through a repository when storage is configured or emit it through a dashboard integration event when storage is not configured.
- **FR-024**: The module MUST support local development without production authentication or PDPA compliance implementation.

### Key Entities

- **Voice Gateway Session**: A local or future telephony intake session with input mode, current state, timing events, provider mode, and associated case output.
- **Input Adapter**: A source-specific audio adapter for local browser microphone, optional uploaded audio sample, future Twilio Media Streams, or future Azure Communication Services.
- **Caller Turn**: A completed user speech segment created by VAD/turn detection and used as the unit of speech/AI processing.
- **VAD Timing Event**: A timestamped event for silence, speech, listening, thinking, speaking, end-of-turn, or barge-in behavior.
- **Voice Provider Result**: A mock or Azure-derived result containing transcript, language, confidence, optional guidance, and structured crisis extraction.
- **Crisis Case Object**: The emitted or stored case JSON with incident facts, triage, confidence, human-review requirement, reason, and status.
- **Safety Assessment**: Deterministic post-AI evaluation that enforces RED conditions, review requirements, and no-dispatch/no-downgrade constraints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can create a structured crisis case from local microphone input in under 30 seconds after completing the Thai scenario turn.
- **SC-002**: The Thai scenario "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง" produces the required case JSON fields and RED triage in 100% of prepared demo runs with the mock provider.
- **SC-003**: Voice gateway state is visible during local testing and records timing events for speech start, end-of-turn, thinking, speaking, and barge-in.
- **SC-004**: Safety tests force RED for breathing difficulty, trapped person, severe bleeding, unconsciousness, drowning risk, and active fire danger.
- **SC-005**: Low-confidence, missing-location, and contradictory cases require human review in 100% of prepared safety tests.
- **SC-006**: The same case-output contract is used by mock provider mode and Azure provider mode.
- **SC-007**: V0 can start and complete the local microphone demo with no Twilio, Azure Communication Services, phone number, real SMS, or official dispatch integration configured.
- **SC-008**: Adapter interfaces for future Twilio and Azure Communication Services inputs are present and documented, while remaining disabled in the V0 runtime path.

## Assumptions

- Narayana AI V0 is a hackathon prototype module, not an official emergency hotline replacement.
- Local browser microphone is the required V0 input path; uploaded audio is optional.
- Twilio Media Streams and Azure Communication Services are V1 adapter targets because Thailand number support, paid subscription requirements, and trial-account restrictions must be validated separately.
- The initial emitted case status is `pending`.
- Low confidence defaults to below 0.75 on a 0-1 scale.
- Case storage may use a local repository or Cosmos DB, but the voice gateway must still emit a case object when storage is unavailable.
- Production authentication, PDPA compliance implementation, real SMS sending, and official emergency-service integration are out of scope for V0.

# Feature Specification: Azure Speech Validation Build

**Feature Branch**: `002-azure-speech-validation`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "Improve the Narayana Azure Voice Gateway from mock-local demo into a real Azure Speech validation build while preserving mock mode."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Real Thai Audio Intake (Priority: P1)

As a hackathon developer, I want a local microphone or local Thai audio sample to produce a real speech transcript before triage so that the demo proves audio-to-case behavior rather than relying on a canned crisis sentence.

**Why this priority**: This is the core gap in the current MVP. Without real speech recognition validation, the voice gateway cannot prove the most important part of the crisis voice pipeline.

**Independent Test**: Can be tested by submitting a local Thai audio sample containing the phrase "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง" while speech validation credentials are configured, then confirming that the returned transcript is the speech-recognition result used to create the case.

**Acceptance Scenarios**:

1. **Given** speech validation credentials are configured and a Thai audio turn is committed, **When** the gateway processes the turn, **Then** the case is created from the real speech transcript and not from a hardcoded demo transcript.
2. **Given** the real transcript contains flood, trapped-person, and breathing-difficulty evidence, **When** triage is completed, **Then** the case is prioritized RED, requires human review, includes a triage reason, and remains pending.
3. **Given** the operator views the debug console after a real speech validation run, **When** the case preview is displayed, **Then** the console shows the source, transcript source, audio reference identifier, transcript, provider warnings if any, and generated case.

---

### User Story 2 - Preserve Mock Demo Reliability (Priority: P2)

As a developer or reviewer without cloud credentials, I want the existing deterministic mock demo to keep working so that the project remains reviewable offline and during hackathon setup problems.

**Why this priority**: Mock mode is the fallback path for demos, code review, and tests when external credentials or network access are unavailable.

**Independent Test**: Can be tested with mock mode enabled by running the existing Thai transcript flow and synthetic local microphone flow, then confirming both still produce the deterministic RED flood case.

**Acceptance Scenarios**:

1. **Given** mock mode is enabled, **When** the Thai sample transcript is submitted manually, **Then** the result matches the existing deterministic RED flood case behavior.
2. **Given** mock mode is enabled, **When** synthetic local microphone frames commit a turn, **Then** the mock provider may use its deterministic Thai sample and the resulting case remains RED and review-required.
3. **Given** mock mode is enabled, **When** speech validation credentials are missing, **Then** the gateway does not attempt real speech recognition and does not show a credential failure as a user-facing error.

---

### User Story 3 - Surface Speech Failures Safely (Priority: P3)

As a crisis operator or reviewer, I want unclear audio and speech-recognition failures to become visible review-required cases so that the system does not hide uncertainty or create false confidence.

**Why this priority**: Crisis triage must fail toward human review. Silent substitution with a crisis demo sentence could create misleading RED cases or hide audio failures.

**Independent Test**: Can be tested by processing an invalid, silent, or unsupported audio sample with speech validation mode enabled and confirming that the result is low-confidence, human-review-required, and visibly marked as fallback or unclear.

**Acceptance Scenarios**:

1. **Given** speech recognition fails for a committed audio turn, **When** the gateway creates a triage result, **Then** it does not substitute the Thai flood demo sentence.
2. **Given** speech recognition fails or returns no usable text, **When** the case is created, **Then** the case requires human review, has low confidence, exposes the unclear transcript state, and includes provider warnings.
3. **Given** a speech validation run produces provider warnings, **When** the debug console displays the result, **Then** the warnings are visible alongside the case and audio reference.

---

### Edge Cases

- Committed audio contains only silence or background noise.
- The audio turn is too short to produce a reliable transcript.
- Speech validation credentials are missing, invalid, expired, or rate-limited.
- Speech recognition returns no text, partial text, or text in a different language than expected.
- A committed audio file cannot be written, read, or associated with the turn.
- Real speech recognition succeeds but structured triage fails or returns invalid data.
- Mock mode is enabled even though real speech validation credentials exist.
- The operator needs to distinguish between mock transcript, real speech transcript, and fallback transcript.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST preserve the existing mock transcript demo behavior when mock mode is enabled.
- **FR-002**: The system MUST preserve the existing mock local microphone flow behavior when mock mode is enabled.
- **FR-003**: The system MUST persist each committed local audio turn as a replayable audio artifact before real speech validation is attempted.
- **FR-004**: The persisted audio artifact MUST be associated with the committed caller turn through an audio reference or debug identifier.
- **FR-005**: When real speech validation is enabled and credentials are configured, the system MUST use the committed audio artifact as the source for speech-to-text.
- **FR-006**: The system MUST send the real speech transcript to the structured triage flow and then apply deterministic crisis safety rules before case creation.
- **FR-007**: The created case or case event MUST include the transcript returned by real speech validation.
- **FR-008**: The system MUST identify the transcript source as one of: mock, real speech-to-text, or fallback.
- **FR-009**: If speech recognition fails, returns no usable text, or cannot access the audio artifact, the system MUST return a review-required fallback result rather than substituting a hardcoded crisis transcript.
- **FR-010**: Speech failure fallback results MUST have low confidence, require human review, expose the unclear or missing transcript state, and include provider warnings.
- **FR-011**: The operator/debug UI MUST display source, transcript source, audio reference or debug identifier, provider warnings, transcript, structured triage result, safety-rule result, and generated case preview.
- **FR-012**: RED, low-confidence, missing-location, unclear-transcript, or contradictory cases MUST require human review.
- **FR-013**: The system MUST NOT automatically dispatch rescue, close a case, reject a case, or downgrade emergency help without human review.
- **FR-014**: Real phone-number providers MUST remain out of the V1 validation path and must not be required for local speech validation.
- **FR-015**: Optional experimental voice-live behavior MUST remain separate from the required speech validation path and must not block local validation.
- **FR-016**: Documentation MUST include real speech validation steps using a local Thai audio file and clear guidance for mock mode, failure mode, and missing-credential behavior.

### Key Entities *(include if feature involves data)*

- **Audio Turn Artifact**: A replayable recording for one committed caller turn. Key attributes include audio reference or debug identifier, duration, sample rate, channel count, encoding, creation time, and association to a voice session.
- **Transcript Result**: The recognized or fallback text for a caller turn. Key attributes include transcript text, transcript source, confidence if available, language, warnings, and association to an audio turn.
- **Triage Result**: The structured crisis assessment created from a transcript. Key attributes include incident type, triage level, confidence, location, injuries, needs, summary, reason, missing fields, review requirement, and status.
- **Crisis Case**: The operator-facing record created after safety rules are applied. Key attributes include case identifier, transcript, triage result, status, timestamps, source, transcript source, audio reference, and warnings.
- **Provider Warning**: A visible non-fatal warning about speech recognition, triage, configuration, or fallback behavior. Key attributes include warning text, source, timestamp, and related session or case.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer with valid speech validation credentials can process a local Thai audio sample and see the resulting transcript used in a case within 30 seconds.
- **SC-002**: The Thai flood and breathing-difficulty sample creates a RED, pending, human-review-required case in both mock mode and real speech validation mode.
- **SC-003**: 100% of speech-recognition failures in automated tests produce low-confidence, human-review-required fallback results with visible warnings.
- **SC-004**: 0 automated tests in the real speech validation provider rely on a hardcoded Thai crisis transcript as the failure transcript.
- **SC-005**: The debug console shows source, transcript source, audio reference or debug identifier, transcript, and provider warnings for every completed local audio turn.
- **SC-006**: Existing mock transcript and mock local microphone regression tests continue to pass after real speech validation is added.
- **SC-007**: Local validation remains usable without phone-number setup, and no test or demo step requires Twilio or Azure Communication Services.

## Assumptions

- The existing Narayana Azure Voice Gateway MVP remains the baseline and should be changed incrementally.
- Mock mode remains the default for offline review unless explicitly disabled.
- Real speech validation is considered available only when required credentials are configured.
- A local Thai WAV sample is sufficient for validating real speech-to-text before testing live microphone audio.
- Audio artifacts for validation are temporary development/debug artifacts and are not a production retention policy.
- Production authentication, legal compliance, real dispatch integration, phone-number setup, and real phone streaming remain out of scope for this feature.

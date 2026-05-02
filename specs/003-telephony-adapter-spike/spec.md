# Feature Specification: Telephony Adapter Spike

**Feature Branch**: `003-telephony-adapter-spike`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "Add a V1 telephony adapter spike for Narayana that validates a foreign-country test phone number without changing the core Azure Voice Gateway contract."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Phone Call Ingress (Priority: P1)

As a hackathon developer, I want a real phone call from a foreign-country test number to feed call audio into Narayana's existing voice gateway pipeline so that the team can validate phone-provider ingress without changing crisis triage behavior.

**Why this priority**: The current system already proves local microphone and Azure speech validation. The next unknown is whether a provider call stream can be normalized into the same audio-turn pipeline without forking VAD, triage, safety, or case creation logic.

**Independent Test**: Can be tested with a simulated provider media stream and, when credentials are available, a foreign-country test number. The call audio should become normalized audio frames, pass through the existing turn and triage flow, and create the same kind of case as local microphone input.

**Acceptance Scenarios**:

1. **Given** local microphone mode remains the default, **When** the app starts without phone-provider credentials, **Then** local microphone, manual transcript, mock mode, and Azure speech validation still work.
2. **Given** a configured foreign-country phone test number receives a call, **When** the phone provider connects media to the gateway, **Then** normalized call audio enters the same VAD, audio buffering, speech, safety, and case creation flow used by local microphone input.
3. **Given** a simulated phone media stream sends the Thai flood sample audio, **When** the stream completes a turn, **Then** Narayana creates a mock RED pending case through the shared pipeline.

---

### User Story 2 - Preserve Gateway Contract and Safety (Priority: P2)

As a Narayana operator or reviewer, I want phone-originated cases to look like existing cases with extra call metadata so that dashboard/debug workflows remain consistent and safety rules remain explainable.

**Why this priority**: The spike should validate ingress only. It must not create a parallel triage path, bypass human review, or change the existing WebSocket and case semantics beyond adding source metadata.

**Independent Test**: Can be tested by comparing a local microphone case and a simulated phone-provider case. Both should use the same case shape, safety behavior, and debug contract, with the phone case adding source input mode and call metadata.

**Acceptance Scenarios**:

1. **Given** a phone media stream creates a case, **When** the final case payload is emitted, **Then** it includes source input mode, provider, call identifier, caller/called numbers, country, codec, sample rate, and call start time.
2. **Given** phone audio is unclear, incomplete, or fails speech recognition, **When** triage completes, **Then** the case requires human review and no emergency response is automatically dispatched, rejected, closed, or downgraded.
3. **Given** phone-provider credentials are missing, **When** the app starts and health/debug screens are used, **Then** the app remains healthy and reports phone-provider mode as unavailable or not configured.

---

### User Story 3 - Keep ACS Safe and Optional (Priority: P3)

As a developer evaluating phone providers, I want Azure Communication Services call ingress to be represented as a safe disabled skeleton unless test-number support is ready so that future ACS work has a clear seam without blocking the Twilio-first spike.

**Why this priority**: ACS may be useful later, but this spike should not stall on ACS phone-number setup or incomplete event streaming. A safe skeleton documents the future path while preventing accidental runtime failures.

**Independent Test**: Can be tested by calling the ACS event and media entry points without ACS configuration and verifying the system returns a clear not-configured or not-implemented response without crashing.

**Acceptance Scenarios**:

1. **Given** ACS configuration is missing, **When** an ACS event endpoint is called, **Then** Narayana returns a clear disabled/not-configured response.
2. **Given** ACS media streaming is not implemented, **When** an ACS media connection is attempted, **Then** the gateway refuses or closes it safely without affecting local microphone or Twilio test behavior.

---

### Edge Cases

- Phone-provider credentials are absent, invalid, expired, or partially configured.
- A public callback URL is missing or malformed.
- A provider sends malformed webhook payloads, duplicate events, out-of-order media events, or stream stop before speech is complete.
- Provider media uses a codec, sample rate, or payload format that cannot be normalized.
- Caller audio is silent, noisy, too short, or contains no usable speech.
- A phone call disconnects while the system is thinking or speaking.
- A simulated phone stream should create a case without real phone credentials.
- Phone-originated cases must not imply Thailand phone-number availability or emergency-service readiness.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep local microphone mode as the default input mode.
- **FR-002**: The system MUST continue to run without Twilio or ACS credentials.
- **FR-003**: The system MUST support input mode configuration values for local microphone, Twilio call, and ACS call evaluation.
- **FR-004**: The system MUST capture call metadata for phone-originated sessions, including provider, call identifier, caller number, called number, country, codec, sample rate, start time, and optional raw debug payload.
- **FR-005**: Provider-specific call ingress MUST reuse the existing voice gateway pipeline for audio framing, VAD, turn handling, audio buffering, speech processing, safety rules, and case creation.
- **FR-006**: Provider-specific webhook or media routes MUST NOT duplicate triage, safety rules, or case repository logic.
- **FR-007**: Twilio call ingress MUST be available as the first phone-provider spike when Twilio test-number configuration is present.
- **FR-008**: Twilio incoming-call handling MUST return a valid provider response that connects the call to a media stream when configured.
- **FR-009**: Twilio media events MUST normalize provider audio payloads into mono PCM16 audio frames compatible with the existing gateway pipeline.
- **FR-010**: A simulated Twilio media stream MUST be able to create a mock RED pending case through the shared pipeline without real Twilio credentials.
- **FR-011**: Phone-originated final case or debug payloads MUST include `source_input_mode` and `call_metadata`.
- **FR-012**: ACS ingress MUST remain disabled or skeleton-only unless ACS configuration is present and the behavior is explicitly enabled.
- **FR-013**: ACS disabled behavior MUST return clear not-configured or not-implemented feedback without crashing the app.
- **FR-014**: Missing or incomplete phone-provider configuration MUST NOT break app startup, local microphone mode, mock mode, or Azure Speech/OpenAI validation.
- **FR-015**: Documentation MUST explain that a foreign-country test number validates call ingress only and does not validate Thailand number availability, Thailand SMS support, telecom cost, production authentication, emergency-service compliance, or dispatch readiness.
- **FR-016**: Automated tests MUST NOT require real Twilio or ACS credentials.

### Key Entities *(include if feature involves data)*

- **Call Metadata**: Provider-specific details associated with a phone-originated voice session. Key attributes include provider, call identifier, caller number, called number, country, codec, sample rate, start time, and optional raw debug payload.
- **Telephony Session**: A voice session created from a phone-provider call rather than local microphone input. It relates call metadata to the existing turn, audio artifact, transcript, triage, and case records.
- **Normalized Audio Frame**: Provider audio converted into the same frame shape expected by Narayana's existing voice gateway. It carries session identity, sequence, timestamp, encoding, sample rate, channel count, duration, and audio payload.
- **Phone-Originated Case**: A standard Narayana crisis case created from phone-provider audio. It has the same triage, safety, status, and review behavior as local microphone cases, with additional source input mode and call metadata.
- **Provider Configuration State**: The runtime availability state for local microphone, Twilio, and ACS evaluation modes. It determines whether phone-provider routes can accept calls or must return disabled feedback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Local microphone and manual transcript regression checks continue to pass after phone-provider routes are added.
- **SC-002**: App startup succeeds with zero phone-provider credentials configured.
- **SC-003**: 100% of automated telephony tests run without real Twilio or ACS credentials.
- **SC-004**: A simulated Twilio media stream creates a RED pending mock case through the shared voice gateway pipeline.
- **SC-005**: Phone-originated case output includes source input mode and call metadata for every simulated successful phone session.
- **SC-006**: Twilio media normalization tests verify provider audio converts into mono PCM16 frames with the expected sample rate and payload shape.
- **SC-007**: ACS disabled/skeleton paths return clear not-configured or not-implemented responses without app crash.
- **SC-008**: Documentation states at least four explicit limitations: foreign-number ingress only, no Thailand number validation, no Thailand SMS validation, and no emergency-service compliance validation.

## Assumptions

- `local_mic` remains the default and safest demo path.
- Twilio is the first real phone-provider spike when a foreign-country test number and public webhook URL are available.
- ACS is kept as a safe skeleton unless the team has a usable ACS test number and callback setup.
- The spike may use simulated provider media streams for automated tests and reserve real phone calls for manual validation.
- Raw provider payloads are debug-only and should not become the production data retention policy.
- Phone-number availability, SMS support, telecom pricing, production authentication, legal compliance, and official emergency dispatch integration remain out of scope.

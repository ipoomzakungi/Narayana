# Feature Specification: Narayana AI Voice Intake

**Feature Branch**: `001-crisis-voice-triage`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "Build Narayana AI, a local-first AI crisis voice intake and triage prototype for a Microsoft Azure-focused hackathon."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Thai Crisis Intake by Voice (Priority: P1)

A caller speaks naturally in Thai through a local microphone. The assistant listens for complete turns, asks short crisis-intake questions, confirms critical details, and creates a structured crisis case for operator review.

**Why this priority**: This is the core demo value: an overwhelmed crisis team can convert a stressful spoken call into structured, reviewable information without requiring the caller to install an app or use a real phone integration.

**Independent Test**: Can be tested with only a local microphone session by speaking a Thai crisis scenario and verifying that a structured case is created with transcript, extracted fields, triage level, confidence, summary, and human-review flag.

**Acceptance Scenarios**:

1. **Given** a new local microphone intake session, **When** the caller says "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง", **Then** the system records Thai as the language, extracts flood and urgent medical risk, creates a case, assigns RED priority, and marks human review required.
2. **Given** the caller has not provided a location, number of people, injury status, or immediate danger, **When** the assistant needs more information, **Then** it asks one short crisis-intake question at a time and confirms the critical field before relying on it.
3. **Given** the assistant is speaking guidance, **When** the caller starts speaking again, **Then** the assistant supports interruption, stops or yields its speech, and captures the caller's new turn without losing the case context.

---

### User Story 2 - Review Prioritized Cases on a Live Dashboard (Priority: P2)

A crisis operator sees newly created cases appear on a live dashboard, opens the details, understands why the case was prioritized, and updates the case status as human response progresses.

**Why this priority**: Operators need a practical work queue that highlights urgent cases first and keeps the human in charge of review, override, and response status.

**Independent Test**: Can be tested by creating or simulating cases at each priority level and verifying that the dashboard updates without manual refresh, orders cases by urgency, and exposes all case details needed for review.

**Acceptance Scenarios**:

1. **Given** one RED, one YELLOW, and one GREEN case exist, **When** the operator views the dashboard, **Then** cases are shown without manual refresh and RED cases are visually prioritized ahead of lower-priority cases.
2. **Given** an operator opens a case, **When** the case detail view loads, **Then** the operator can see the transcript, AI summary, extracted facts, confidence, triage reason, current status, timestamps, and whether human review is required.
3. **Given** the operator determines that the triage level or status needs correction, **When** they override priority or update status, **Then** the case reflects the new value, preserves the AI-assigned reason, and records the updated time.

---

### User Story 3 - Keep Triage Safe and Human-Centered (Priority: P2)

The assistant gives only safe scripted crisis guidance, never claims to replace emergency responders, never dispatches rescue automatically, and always escalates high-risk or uncertain cases for human review.

**Why this priority**: Crisis intake can affect life safety. The prototype must demonstrate clear guardrails before it can be credible to operators, coordinators, or public-service teams.

**Independent Test**: Can be tested with scripted RED, YELLOW, GREEN, ambiguous, and low-confidence scenarios to verify that the system explains triage, requires review when appropriate, and avoids unsafe claims.

**Acceptance Scenarios**:

1. **Given** a case includes life-threatening danger, severe medical symptoms, trapped people, fire danger, severe bleeding, or drowning risk, **When** triage is assigned, **Then** the case is RED and human review is required.
2. **Given** a case has low confidence or conflicting crisis facts, **When** the case is created or updated, **Then** it requires human review and is not downgraded without operator action.
3. **Given** the assistant gives waiting guidance, **When** guidance is shown or spoken, **Then** it uses predefined safe scripts and clearly frames the product as a crisis intake and triage assistant, not an official emergency hotline replacement.

---

### User Story 4 - Observe Turn Detection and Audio Timing (Priority: P3)

A developer or demo operator can observe the audio interaction state and timing logs while testing noisy or interrupted local microphone conversations.

**Why this priority**: The prototype must prove it can avoid talking over callers and provide enough timing evidence to debug voice behavior during a live hackathon demo.

**Independent Test**: Can be tested by speaking, pausing, staying silent, making noise, and interrupting assistant speech while verifying the debug state and timing log.

**Acceptance Scenarios**:

1. **Given** the caller is silent, speaking, waiting for a response, the system is thinking, or the assistant is speaking, **When** the state changes, **Then** the debug UI shows one of: silence, speech, listening, thinking, or speaking.
2. **Given** a local microphone session contains multiple caller and assistant turns, **When** the session is reviewed, **Then** each relevant audio and turn event has a timestamped timing log.
3. **Given** background noise or partial speech occurs, **When** the system cannot confidently determine a complete caller turn, **Then** it avoids premature response and either waits, asks a clarifying question, or flags the case for human review.

### Edge Cases

- Caller speech is noisy, panicked, very soft, elderly, or interrupted by background sounds.
- Caller pauses mid-sentence long enough to look like a completed turn.
- Caller changes or corrects critical facts after the assistant has summarized them.
- Location is vague, ambiguous, misspelled, or only described by landmark.
- Number of people affected or injury severity is unknown.
- Caller uses mixed Thai and another language, or the language cannot be confidently detected.
- Caller reports danger terms that imply RED priority but also says they are currently safe.
- A case is RED or low-confidence while the operator has not yet opened the case.
- The dashboard temporarily loses its live update connection.
- A simulated SMS or upload-link action is used during the demo and must be clearly marked as simulated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a V0 intake flow that starts from a local microphone and does not require real phone numbers, Twilio call handling, or Azure Communication Services phone number setup.
- **FR-002**: The system MUST support natural Thai voice intake and record the detected language for each case.
- **FR-003**: The system MUST create a structured crisis case from caller conversation turns.
- **FR-004**: The system MUST include local voice activity or turn detection before audio is submitted for crisis interpretation.
- **FR-005**: The system MUST avoid responding while the caller is still speaking.
- **FR-006**: The system MUST support barge-in behavior where caller speech can interrupt assistant speech.
- **FR-007**: The system MUST show the current voice interaction state in a developer/debug UI using these states: silence, speech, listening, thinking, and speaking.
- **FR-008**: The system MUST log timestamped audio, turn, state-change, and barge-in events for debugging.
- **FR-009**: The assistant MUST ask short crisis-intake questions and prioritize missing critical fields: location, people affected, injuries, and immediate danger.
- **FR-010**: The assistant MUST confirm critical fields before treating them as reliable facts.
- **FR-011**: The assistant MUST provide safe scripted guidance while waiting for human review when guidance is appropriate.
- **FR-012**: The assistant MUST NOT claim to replace emergency responders or official emergency hotlines.
- **FR-013**: The assistant MUST NOT dispatch rescue automatically.
- **FR-014**: The assistant MUST NOT deny emergency help or downgrade urgent help needs without human review.
- **FR-015**: Each crisis case MUST include these fields: case_id, language, incident_type, triage_level, confidence, location_text, people_affected, injuries, immediate_needs, caller_phone_optional, ai_summary, triage_reason, human_review_required, created_at, updated_at, and status.
- **FR-016**: The system MUST assign one of three triage levels: RED, YELLOW, or GREEN.
- **FR-017**: RED triage MUST represent life-threatening danger, urgent medical danger, trapped person, breathing difficulty, severe bleeding, fire danger, or drowning risk.
- **FR-018**: YELLOW triage MUST represent injured or at-risk situations that are not immediately life-threatening based on available information.
- **FR-019**: GREEN triage MUST represent callers who appear safe and need information or non-urgent support.
- **FR-020**: RED cases and low-confidence cases MUST require human review.
- **FR-021**: The system MUST show the reason a triage priority was assigned.
- **FR-022**: The live dashboard MUST show newly created or updated cases without requiring manual refresh.
- **FR-023**: The dashboard MUST allow operators to open case details and view transcript, AI summary, extracted facts, confidence, triage reason, human-review requirement, timestamps, and current status.
- **FR-024**: The dashboard MUST allow operators to override triage priority.
- **FR-025**: The dashboard MUST allow operators to update status to contacted, dispatched, resolved, or closed.
- **FR-026**: The system MUST preserve both the AI-assigned triage explanation and the current operator-selected priority when an override occurs.
- **FR-027**: The V0 product MUST clearly describe itself as a crisis intake and triage assistant, not an official emergency hotline replacement.
- **FR-028**: The demo MUST visibly satisfy the Microsoft Azure-focused hackathon requirement without making Azure Communication Services phone numbers or real telephony integrations part of V0 scope.
- **FR-029**: If the demo includes a simulated SMS or upload-link action, the action MUST be labeled as simulated and MUST NOT imply real emergency dispatch.

### Key Entities

- **Crisis Case**: A structured emergency-intake record with case_id, language, incident_type, triage_level, confidence, location_text, people_affected, injuries, immediate_needs, caller_phone_optional, ai_summary, triage_reason, human_review_required, created_at, updated_at, and status.
- **Conversation Transcript**: Ordered caller and assistant turns connected to a crisis case, including text, speaker, language indicator, turn timing, and confidence where available.
- **Triage Assessment**: The priority decision for a case, including RED/YELLOW/GREEN level, confidence, triage reason, human-review requirement, and source facts used for the decision.
- **Operator Update**: A human action on a case, including priority override, status change, update time, and optional operator note.
- **Voice Timing Event**: A debug event for local microphone behavior, including event type, state, timestamp, duration where available, and related turn or case.
- **Safe Guidance Script**: A predefined crisis guidance message selected by incident type or safety condition and constrained to avoid dispatch claims or official-hotline replacement claims.
- **Simulated Outbound Action**: An optional demo-only SMS or upload-link simulation with target label, generated time, case association, and clear simulation status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a local microphone demo, a Thai crisis statement can produce a structured case on the dashboard within 30 seconds after the caller completes the relevant turn.
- **SC-002**: The MVP demo phrase "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง" results in a case that records Thai language, flood incident context, medical breathing risk, trapped-person context, RED priority, human review required, AI summary, and triage reason in 100% of prepared demo runs.
- **SC-003**: Newly created or updated cases appear on the operator dashboard without manual refresh within 5 seconds for at least 95% of demo events.
- **SC-004**: Operators can open a case, understand the priority reason, and update priority or status within 3 interactions from the case list.
- **SC-005**: During voice testing, the debug UI displays the current state and records a timestamped event for every caller turn, assistant turn, state change, and barge-in event.
- **SC-006**: 100% of RED cases and cases with confidence below the V0 low-confidence threshold are marked human_review_required and show an explanation before operator action.
- **SC-007**: Across prepared RED, YELLOW, GREEN, ambiguous, and low-confidence test scripts, the assistant never states that rescue has been automatically dispatched and never denies or downgrades emergency help without human review.
- **SC-008**: A first-time hackathon reviewer can identify within 60 seconds that the product is a Microsoft Azure-focused crisis intake and triage assistant and not an official emergency hotline replacement.

## Assumptions

- V0 is a local-first hackathon prototype tested from a local microphone before any real telephony channel is considered.
- Real Twilio call handling, real Azure Communication Services phone numbers, real emergency dispatch integration, production authentication, full legal compliance implementation, and replacement of official emergency services are out of scope for V0.
- Low confidence for V0 means confidence below 0.70 on a 0-1 scale unless a later planning decision changes the threshold.
- "Dispatched" is an operator-recorded status that indicates a human response workflow outside the prototype; the system itself does not dispatch rescue.
- Caller phone is optional in V0 because local microphone testing may not have a real caller phone number.
- Transcript and case data may be retained for the current demo/testing session; long-term retention and legal compliance policies are deferred beyond V0.
- Operators in V0 are trusted demo users; production identity, access control, and audit policy are deferred beyond V0.
- Microsoft Azure usage evidence is a hackathon demonstration requirement and should not be presented as an official emergency-service endorsement.

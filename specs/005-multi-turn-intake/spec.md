# Feature Specification: Multi-Turn Crisis Conversation Intake

**Feature Branch**: `005-multi-turn-intake`  
**Created**: 2026-05-03  
**Status**: Draft  
**Input**: User description: "Add multi-turn crisis conversation intake to Narayana so each call/session keeps conversation context, asks concise Thai follow-up questions, categorizes cases into operational response groups, and creates or escalates cases only when sufficient information is collected or high-risk conditions appear."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continue a Crisis Intake Conversation (Priority: P1)

As a crisis operator testing Narayana from a manual transcript flow, I want each caller session to remember prior turns and ask only the next critical question so that unclear or incomplete calls can be completed without restarting the intake from scratch.

**Why this priority**: Multi-turn state is the core feature. Without it, Narayana continues to treat every caller utterance as a separate one-shot case and cannot collect missing critical details safely.

**Independent Test**: Start a session with an incomplete Thai transcript such as "น้ำท่วมอยู่ที่หาดใหญ่" and verify the system stores the caller turn, preserves known location and incident details, returns `ask_followup`, and asks one concise Thai question about the next missing critical field.

**Acceptance Scenarios**:

1. **Given** a new intake session with no prior turns, **When** the caller reports a flood location but no injuries or people count, **Then** the system stores the transcript, updates partial collected fields, returns `ask_followup`, and asks one short Thai question about injuries, immediate danger, trapped people, or people affected.
2. **Given** an intake session with a known location, **When** the caller provides injuries in a later turn, **Then** the system updates the same session instead of creating a separate independent case.
3. **Given** a session has asked three follow-up questions, **When** required fields remain missing, **Then** the system creates a human-review case with missing fields recorded rather than asking another question.

---

### User Story 2 - Immediately Escalate High-Risk Cases (Priority: P1)

As a crisis operator, I want Narayana to stop asking follow-ups and create or escalate a case immediately when RED danger appears so that life-threatening situations are not delayed by normal intake completion rules.

**Why this priority**: Safety is more important than completing a form. RED risk must trigger immediate case creation or human review even when some information is missing.

**Independent Test**: Submit the Thai sample "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง" and verify the system returns `create_case` or `escalate_human_review`, assigns RED, requires human review, records the reason, and categorizes the case for rescue/medical response.

**Acceptance Scenarios**:

1. **Given** a caller says someone has breathing difficulty, is trapped, unconscious, drowning, bleeding severely, exposed to active fire, or at self-harm risk, **When** the transcript is processed, **Then** the system creates or escalates a case immediately even if callback number or people count is missing.
2. **Given** high-risk medical language appears, **When** Narayana returns response text, **Then** it uses safe language such as "ขอให้เจ้าหน้าที่ตรวจสอบทันที" and does not diagnose the caller or patient.
3. **Given** self-harm or severe distress appears, **When** Narayana creates or escalates the case, **Then** it uses supportive language, requires human review, and categorizes for mental-health support with human escalation.

---

### User Story 3 - Categorize Cases for the Right Response Group (Priority: P2)

As a rescue coordinator, I want each created case to include an operational group and recommended team so that cases can be routed to the right response function faster.

**Why this priority**: Triage color alone is not enough for operations. Coordinators need to distinguish rescue, medical, fire, flood, police/public safety, tourist support, utilities, shelter supplies, mental health support, and unknown human-review cases.

**Independent Test**: Submit representative transcripts for flood/trapped, breathing difficulty, fire, public danger, tourist trouble, utility damage, shelter supply need, self-harm risk, and unclear speech; verify each case receives the expected operational group and recommended team.

**Acceptance Scenarios**:

1. **Given** a flood call mentions trapped people, **When** a case is created, **Then** the case group is rescue-oriented and the recommended team includes rescue response.
2. **Given** a call mentions breathing difficulty, unconsciousness, severe bleeding, or urgent medical danger, **When** a case is created, **Then** the case group is medical-oriented and human review is required.
3. **Given** the case remains unclear after allowed follow-up attempts, **When** a case is created, **Then** the case group is `unknown_human_review` and the missing/unclear evidence is visible.

---

### User Story 4 - Use Conversation Intake in Phone Calls (Priority: P2)

As a caller using a phone call, I want Narayana to remember what I already said and ask the next short Thai follow-up question without creating a premature final case after every speech turn.

**Why this priority**: Twilio ingress has already been proven; this feature must connect telephony turns to the same conversation-aware intake behavior without changing the public phone webhook paths.

**Independent Test**: Simulate or place a phone call where the first committed turn is incomplete; verify the WebSocket response includes the next Thai question and no final case. Then provide a follow-up turn and verify the same session state is updated.

**Acceptance Scenarios**:

1. **Given** a phone call session is active, **When** a committed caller turn is transcribed, **Then** the transcript is appended to the call's intake session and evaluated with prior turns.
2. **Given** the intake decision is `ask_followup`, **When** the phone WebSocket response is emitted, **Then** it includes `response_text` and does not emit a final case-created payload.
3. **Given** the intake decision is `create_case` or `escalate_human_review`, **When** the phone WebSocket response is emitted, **Then** it includes the created case, conversation context, categorization, triage reason, and human-review status.

---

### User Story 5 - Review Conversation Context on Dashboards (Priority: P3)

As an operator, I want the debug console and cases dashboard to show conversation turns, collected fields, next question, categorization, recommended team, and missing fields so that I can understand what Narayana asked and why a case was or was not created.

**Why this priority**: Operators need explainability and auditability, but dashboard display depends on the intake decisions and case data being available first.

**Independent Test**: Run a multi-turn manual intake session, open the debug console, and verify it shows the conversation timeline, partial fields, action, next question, group, recommended team, missing fields, and guardrail warnings. After case creation, verify the cases dashboard shows group, recommended team, and conversation summary.

**Acceptance Scenarios**:

1. **Given** a session is mid-intake, **When** the debug console receives an `ask_followup` decision, **Then** it shows the response text, action, collected fields, missing fields, case group, recommended team, and conversation turns.
2. **Given** a case is created from a multi-turn conversation, **When** it appears on the cases dashboard, **Then** the dashboard shows the case group, recommended team, and conversation summary when available.

### Edge Cases

- If speech recognition is unclear for a first turn, Narayana asks the caller to repeat once in Thai and records the unclear turn.
- If speech recognition remains unclear after one repeat request, Narayana creates a low-confidence human-review case with missing fields and uncertainty recorded.
- If RED risk appears at any point in the conversation, Narayana stops normal follow-up collection and creates or escalates a human-review case immediately.
- If the caller repeats already-known information, Narayana does not ask redundant follow-up questions for that field.
- If the caller changes or contradicts a critical field such as location or injuries, Narayana preserves the conversation history and marks the case for human review.
- If no callback number is available, Narayana may ask for it only after more urgent fields are addressed and must not block RED case creation on the callback number.
- If case categorization is uncertain, Narayana uses `unknown_human_review` and explains the uncertainty.
- If a caller requests official dispatch confirmation, Narayana must not say rescue has been dispatched and must present itself only as an intake and triage assistant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain an intake session for each distinct manual, local microphone, or phone-call session.
- **FR-002**: Each intake session MUST store ordered conversation turns with speaker, text, creation time, and turn index.
- **FR-003**: Each intake session MUST maintain collected fields for language, incident type, location text, people affected, injuries, immediate needs, optional caller phone, landmarks, urgency signals, and missing fields.
- **FR-004**: The system MUST update collected fields from the full conversation context rather than treating each new caller turn as an unrelated one-shot intake.
- **FR-005**: For each processed caller turn, the system MUST choose exactly one action: `ask_followup`, `create_case`, or `escalate_human_review`.
- **FR-006**: When action is `ask_followup`, the system MUST return one concise Thai follow-up question in `response_text` and MUST NOT create a final crisis case for that turn.
- **FR-007**: Follow-up questions MUST prioritize missing critical fields in this order unless already known or overridden by danger: location, immediate danger, injuries/breathing/unconsciousness, trapped people, number of people affected, callback number.
- **FR-008**: Follow-up questions MUST be short, calm, in Thai by default, ask only one question at a time, and avoid long-form intake wording.
- **FR-009**: The system MUST enforce a configurable maximum follow-up count with a default of three.
- **FR-010**: After the maximum follow-up count is reached, the system MUST create a human-review case with missing fields and uncertainty recorded.
- **FR-011**: The system MUST immediately create or escalate a RED human-review case when breathing difficulty, trapped person, unconsciousness, drowning risk, active fire exposure, severe bleeding, self-harm danger, or comparable life-threatening danger is detected.
- **FR-012**: RED, low-confidence, contradictory, missing-location, self-harm, severe distress, and unclear-after-repeat cases MUST require human review.
- **FR-013**: The system MUST categorize each case into exactly one operational group: rescue, medical, fire, flood, police_public_safety, tourist_support, utility_infrastructure, shelter_supplies, mental_health_support, or unknown_human_review.
- **FR-014**: The system MUST provide a recommended team aligned with the operational group and crisis evidence.
- **FR-015**: Categorization MUST follow the requested mapping defaults: flood plus trapped people to rescue; breathing difficulty, unconsciousness, or severe bleeding to medical; fire/smoke/burning building to fire; crime/violence/public danger to police_public_safety; tourist lost or in trouble to tourist_support; power/water/road issue to utility_infrastructure; food/water/shelter need to shelter_supplies; self-harm, panic, or severe distress to mental_health_support plus human review; unclear cases to unknown_human_review.
- **FR-016**: The system MUST explain why it selected the action, triage level, operational group, recommended team, and any human-review requirement.
- **FR-017**: The system MUST store model decisions, guardrail matches, guardrail overrides, missing fields, and relevant evidence for audit.
- **FR-018**: The system MUST never state that rescue has been dispatched, never close or reject an emergency case automatically, and never downgrade emergency help without human review.
- **FR-019**: The system MUST not diagnose medical or mental-health conditions; for medical risk it MUST use safe review language such as "ขอให้เจ้าหน้าที่ตรวจสอบทันที".
- **FR-020**: For self-harm or severe distress, the system MUST use supportive, calm language and require human escalation.
- **FR-021**: The transcript intake interface MUST support a request containing session ID, transcript, language hint, and source input mode, and return action, response text, partial state, operational group, recommended team, triage level, human-review flag, missing fields, reason, and created case when applicable.
- **FR-022**: Existing one-shot transcript triage MUST continue to work for compatibility.
- **FR-023**: Existing phone webhook and media WebSocket route paths MUST continue to work.
- **FR-024**: Phone-call committed turns MUST be passed through the conversation intake layer after transcription and before final case creation.
- **FR-025**: When phone-call action is `ask_followup`, the system MUST emit the follow-up response text to the WebSocket payload and not emit a final case-created payload for that turn.
- **FR-026**: When phone-call action is `create_case` or `escalate_human_review`, the system MUST create the case, store a conversation summary, and emit a final case-created payload.
- **FR-027**: The debug console MUST show conversation turns, partial collected fields, response text or next question, action, operational group, recommended team, missing fields, and guardrail warnings.
- **FR-028**: The cases dashboard MUST show operational group, recommended team, and conversation summary when available.
- **FR-029**: Assistant behavior MUST be configurable for assistant language, tone, maximum follow-ups, question style, assistant name, and optional future Thai voice selection.
- **FR-030**: This feature MUST return text response only and MUST NOT add spoken text-to-speech audio to phone calls.
- **FR-031**: This feature MUST NOT implement SMS, official dispatch, production ACS behavior, new Cosmos DB resources, or secret storage.

### Key Entities *(include if feature involves data)*

- **Intake Session**: A stateful crisis intake tied to a session or call; includes session ID, optional call ID, source input mode, conversation turns, collected fields, triage state, follow-up count, maximum follow-ups, operational group, recommended team, optional final case ID, and status.
- **Conversation Turn**: A single caller, assistant, or system message with speaker, text, creation time, and turn index.
- **Collected Fields**: The current structured understanding of the crisis, including language, incident type, location, people affected, injuries, immediate needs, optional caller phone, landmarks, urgency signals, and missing fields.
- **Intake Decision**: The outcome after each caller turn: action, response text, partial state, triage level, confidence, human-review requirement, operational group, recommended team, missing fields, reason, audit evidence, and optional created case.
- **Operational Group**: The response category assigned to a case: rescue, medical, fire, flood, police/public safety, tourist support, utility/infrastructure, shelter/supplies, mental health support, or unknown human review.
- **Crisis Case**: The final operator-visible case created when enough information is collected, follow-up limit is reached, or high-risk danger requires immediate escalation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In manual testing, at least 90% of incomplete non-RED Thai intake samples produce exactly one relevant follow-up question instead of creating a premature final case.
- **SC-002**: All test samples containing breathing difficulty, trapped person, unconsciousness, drowning risk, active fire danger, severe bleeding, or self-harm danger create or escalate a human-review case on the same turn.
- **SC-003**: Follow-up sessions never ask more than three follow-up questions before creating a human-review case.
- **SC-004**: At least 90% of representative test samples are categorized into the expected operational group and recommended team.
- **SC-005**: Every final case created from a multi-turn session includes a conversation summary, triage reason, operational group, recommended team, missing fields when applicable, and audit evidence for guardrail decisions.
- **SC-006**: Existing one-shot transcript triage, phone webhook path, and phone media WebSocket path continue passing regression tests.
- **SC-007**: Operator-facing debug views show action, response text, collected fields, missing fields, operational group, recommended team, and conversation turns within one refresh after a test session update.
- **SC-008**: No generated response in safety test cases claims that rescue has been dispatched, diagnoses a medical or mental-health condition, or closes/rejects an emergency case automatically.

## Assumptions

- Thai remains the default assistant language for V1, with future language expansion handled through configuration.
- The first implementation can keep intake session state in the same local-first storage style used by the current demo, while preserving interfaces for future durable storage.
- Phone-call text replies are returned as WebSocket payloads only; spoken TTS back to Twilio is intentionally out of scope for this feature.
- Existing deployed backend and frontend hosting remain in place; this feature extends the application behavior rather than changing the hosting model.
- Existing crisis safety rules remain authoritative and may override AI-suggested triage, categorization, or follow-up decisions.
- Manual transcript intake is the fastest independently testable path and should be implemented before phone-call conversation integration.

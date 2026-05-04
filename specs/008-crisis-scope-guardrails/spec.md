# Feature Specification: Crisis Scope Guardrails

**Feature Branch**: `008-crisis-scope-guardrails`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "Add crisis-intake scope guardrails, configurable system prompt, and no-reply / off-topic call handling to Narayana. The assistant must stay focused on crisis/help intake, politely reject chit-chat, and end calls when caller is silent or repeatedly off-topic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crisis-Focused Assistant Behavior (Priority: P1)

As a crisis caller or operator, I want the assistant to stay focused on emergency and help-intake topics so that it does not behave like a general chatbot during a public-safety call.

**Why this priority**: Narayana is a crisis intake assistant. General chit-chat, unrelated advice, coding help, politics, entertainment, or casual conversation can waste operator capacity and confuse callers.

**Independent Test**: Start an intake session and ask unrelated questions such as jokes, weather, coding, or casual chat; verify the assistant gives a short Thai redirect and does not answer the unrelated request.

**Acceptance Scenarios**:

1. **Given** a caller asks for a joke, weather, coding help, finance, politics, entertainment, or casual conversation, **When** the assistant responds, **Then** it politely redirects the caller to state an emergency situation and location.
2. **Given** a caller asks an unrelated question after the initial greeting, **When** the assistant responds, **Then** it does not provide general knowledge or continue chit-chat.
3. **Given** the caller gives crisis-related information after a redirect, **When** the assistant processes it, **Then** off-topic handling is reset and normal crisis intake continues.

---

### User Story 2 - Configurable Assistant Identity and Prompt Scope (Priority: P1)

As a demo operator, I want the assistant name, greeting, allowed topics, and system prompt behavior to be configurable so that Narayana can use safer neutral wording without hardcoded deity-name phrasing.

**Why this priority**: The deployed call greeting currently includes a fixed Thai name. A safer default display name and configurable prompt scope are required before broader demos.

**Independent Test**: Configure the assistant display name and greeting, run a call or manual intake, and verify the spoken greeting and model instructions use the configured crisis-intake identity and scope.

**Acceptance Scenarios**:

1. **Given** no custom assistant name is configured, **When** the greeting is generated, **Then** it uses the safer default display name "ระบบช่วยรับแจ้งเหตุ".
2. **Given** no custom greeting is configured, **When** the assistant greets a caller, **Then** it says "สวัสดีค่ะ นี่คือระบบช่วยรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ".
3. **Given** the system prompt configuration is active, **When** the assistant evaluates a caller turn, **Then** it is constrained to crisis intake and allowed help topics only.

---

### User Story 3 - Repeated Off-Topic Caller Handling (Priority: P1)

As a crisis operator, I want repeated off-topic calls to be redirected and then politely ended so that non-emergency callers do not occupy the intake channel indefinitely.

**Why this priority**: A single off-topic request may be a confused caller, but repeated off-topic interaction consumes call-center capacity and should be closed safely.

**Independent Test**: In one call/session, send three unrelated caller turns with no emergency signal and verify the first redirect, second final warning, and third close recommendation.

**Acceptance Scenarios**:

1. **Given** a caller is off-topic for the first time, **When** the assistant responds, **Then** it says "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ".
2. **Given** the same caller remains off-topic after the first redirect, **When** the assistant responds again, **Then** it gives a final short warning that the call will end if there is no incident to report.
3. **Given** the same caller remains off-topic after the final warning, **When** the assistant handles the turn, **Then** it recommends ending the call and provides a polite final response.

---

### User Story 4 - No-Reply Caller Handling (Priority: P1)

As a crisis operator, I want silent calls after the greeting to receive short no-reply prompts and then close safely so that abandoned calls do not hold the line open.

**Why this priority**: Twilio calls may connect with no speech, background noise, or a caller who hangs up mentally but not technically. The system needs a safe prompt-and-close path.

**Independent Test**: Start a Twilio call with greeting enabled and send no caller speech; verify the assistant prompts once after the configured waiting period, gives a final no-reply close message after repeated silence, and closes the stream safely.

**Acceptance Scenarios**:

1. **Given** a caller does not speak after the greeting, **When** the no-reply threshold is reached, **Then** the assistant asks "ยังอยู่ในสายไหมคะ หากต้องการแจ้งเหตุ กรุณาเล่าสถานการณ์สั้น ๆ ได้เลยค่ะ".
2. **Given** a caller remains silent after the maximum no-reply prompts, **When** the final threshold is reached, **Then** the assistant says "หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ".
3. **Given** the final no-reply message has been sent, **When** playback completes or close is otherwise safe, **Then** the WebSocket or media stream is closed safely without using dispatch or SMS.

---

### User Story 5 - Emergency Signals Override Scope Guardrails (Priority: P1)

As a vulnerable or panicked caller, I want emergency phrases to be recognized even if my earlier speech was off-topic or unclear so that real incidents are never rejected due to scope handling.

**Why this priority**: Crisis callers may be confused, elderly, panicked, mentally distressed, or initially testing the bot. Emergency content must always take priority over off-topic rules.

**Independent Test**: Send an off-topic turn, then send "ช่วยด้วย", flood/fire/medical danger, self-harm danger, or another high-risk phrase; verify off-topic counters reset and normal crisis intake/escalation continues.

**Acceptance Scenarios**:

1. **Given** the caller previously asked an off-topic question, **When** they then say "ช่วยด้วย" or describe danger, **Then** the assistant treats it as crisis intake, resets off-topic handling, and does not end the call for off-topic behavior.
2. **Given** the caller reports breathing difficulty, trapped people, severe bleeding, drowning, active fire, self-harm danger, or another high-risk signal, **When** the assistant processes the turn, **Then** it escalates immediately according to crisis triage rules.
3. **Given** the caller is confused, panicked, elderly, unclear, or gives a short incomplete emergency phrase, **When** the assistant classifies scope, **Then** it does not falsely mark the caller off-topic.

---

### User Story 6 - Operator Debug and Audit Visibility (Priority: P2)

As a developer or operator monitoring a demo, I want debug and audit visibility into off-topic redirects, no-reply prompts, final close reasons, and guardrail warnings so that call behavior is explainable.

**Why this priority**: Guardrails can end calls. Operators need to see why a redirect, prompt, or close recommendation happened.

**Independent Test**: Trigger off-topic and no-reply flows and verify debug output includes counters, final close recommendation, redirect text, guardrail warnings, and close reason without secrets.

**Acceptance Scenarios**:

1. **Given** a caller is redirected as off-topic, **When** debug output is viewed, **Then** it shows the off-topic count, redirect count, last assistant redirect, and response text.
2. **Given** a silent call receives no-reply prompts, **When** debug output is viewed, **Then** it shows no-reply prompt count and whether call end is recommended.
3. **Given** a case or intake audit is produced, **When** operators inspect it, **Then** it includes off-topic redirects, no-reply prompts, guardrail warnings, and final close reason when relevant.

### Edge Cases

- Caller says only "ช่วยด้วย", a short place name, or a single emergency keyword after earlier off-topic speech.
- Caller is elderly, panicked, confused, crying, or mentally distressed and gives fragmented speech.
- Caller asks a general question that includes emergency terms but no actual incident.
- Caller remains silent after greeting but background noise or VAD false positives occur.
- Caller starts speaking while a no-reply prompt or final close message is playing.
- Speech recognition returns unclear or empty transcript.
- Off-topic handling reaches close threshold but a high-risk signal appears in the same or next turn.
- WebSocket close fails or the caller disconnects before final TTS mark.
- Optional provider-native call completion credentials are absent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The assistant MUST default to the display name "ระบบช่วยรับแจ้งเหตุ".
- **FR-002**: The default Thai greeting MUST be "สวัสดีค่ะ นี่คือระบบช่วยรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ".
- **FR-003**: The greeting and assistant display name MUST be configurable and MUST NOT hardcode "นารายานา" in the default Thai greeting.
- **FR-004**: The assistant system prompt MUST be configurable with a prompt version, crisis-intake-only scope, allowed topic list, and off-topic decline behavior.
- **FR-005**: The assistant MUST use Thai first, calm, concise, operational wording and keep response text within the configured short response limit.
- **FR-006**: The assistant MUST NOT answer unrelated general knowledge, entertainment, coding, finance, politics, weather/news, flirting, or casual chat requests.
- **FR-007**: For first off-topic turns, the assistant MUST respond with the required Thai redirect text and ask the caller to state the situation and location.
- **FR-008**: For repeated off-topic turns, the assistant MUST give a final warning and then recommend ending the call after the configured limit.
- **FR-009**: The system MUST track `off_topic_count`, `redirect_count`, `last_off_topic_at`, and `call_end_recommended` for each session.
- **FR-010**: The system MUST reset off-topic handling when a crisis or high-risk emergency signal appears.
- **FR-011**: The off-topic classifier MUST avoid false positives for confused callers, panic, elderly callers, unclear speech, mental distress, "ช่วยด้วย", or short incomplete emergency phrases.
- **FR-012**: The system MUST track last caller speech time, greeting sent time, and no-reply prompt count for each call/session.
- **FR-013**: If no caller speech occurs after greeting within the configured threshold, the assistant MUST send the required Thai no-reply prompt.
- **FR-014**: If there is still no reply after the maximum no-reply prompts, the assistant MUST send the required Thai final close message.
- **FR-015**: After the final no-reply message, the system MUST close the WebSocket or stream safely when possible without requiring a provider REST API.
- **FR-016**: Closing behavior MUST NOT dispatch rescue, send SMS, or mark a real emergency case closed automatically.
- **FR-017**: High-risk crisis signals MUST continue to escalate immediately and MUST NOT be downgraded or rejected by scope handling.
- **FR-018**: Debug output MUST show off-topic count, no-reply prompt count, call end recommendation, last assistant redirect, guardrail warnings, and response text.
- **FR-019**: Intake/case audit output MUST include off-topic redirects, no-reply prompts, guardrail warnings, and final close reason when they occur.
- **FR-020**: Existing Twilio routes, existing intake endpoints, and existing dashboard behavior MUST continue to pass regression tests.
- **FR-021**: Automated tests MUST NOT require Azure OpenAI secrets, live Twilio calls, ACS, SMS, or dispatch integrations.

### Key Entities *(include if feature involves data)*

- **Assistant Configuration**: Prompt version, display name, greeting text, scope, allowed topics, decline-off-topic flag, response length limits, and no-reply/off-topic thresholds.
- **Scope Guardrail State**: Per-session state containing off-topic count, redirect count, last off-topic timestamp, call end recommendation, last redirect text, and guardrail warnings.
- **No-Reply State**: Per-call state containing greeting sent time, last caller speech time, no-reply prompt count, final close recommendation, and close reason.
- **Scope Decision**: Classification result for a caller turn, including whether the turn is crisis-related, off-topic, unclear, no-reply, high-risk, or safe to continue.
- **Audit Event**: Debug or case/intake audit item recording redirects, no-reply prompts, guardrail overrides, and final close reasons.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tested off-topic first turns receive the required Thai redirect without answering the unrelated request.
- **SC-002**: 100% of tested repeated off-topic sessions recommend call closure by the third off-topic turn.
- **SC-003**: 100% of tested emergency phrases after off-topic speech reset off-topic handling and continue crisis intake.
- **SC-004**: Silent-call tests produce the no-reply prompt after the configured threshold and the final close message after the configured maximum prompts.
- **SC-005**: 100% of tested high-risk signals still create or escalate crisis intake regardless of previous off-topic or no-reply state.
- **SC-006**: Existing Twilio route, intake, and dashboard regression tests continue to pass.
- **SC-007**: Debug output for guardrail flows includes counters, response text, warning/reason, and close recommendation without exposing secrets.

## Assumptions

- The default no-reply thresholds for demos are 10 seconds for first prompt, 15 seconds for follow-up prompt timing, and a maximum of 2 no-reply prompts.
- The default maximum off-topic redirects is 2, with call-end recommendation enabled on repeated off-topic behavior.
- Safe WebSocket/stream close is sufficient for this feature; provider REST API call completion remains optional future work.
- Azure OpenAI can be unavailable in tests; deterministic fallback guardrails must still validate behavior.
- This feature does not add web search, ACS, SMS, rescue dispatch, Azure OpenAI secret enablement, or production emergency-service compliance behavior.

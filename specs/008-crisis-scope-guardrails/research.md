# Research: Crisis Scope Guardrails

## Decision: Deterministic Scope Classifier Before Model

**Rationale**: The system must work in mock mode and tests must not require Azure OpenAI. A deterministic classifier can catch obvious off-topic content and obvious emergency overrides before the model, making behavior consistent and low-cost.

**Alternatives considered**:

- Rely entirely on Azure OpenAI to detect off-topic content. Rejected because credentials are optional and model behavior is less deterministic.
- Treat every short or unclear phrase as off-topic. Rejected because crisis callers may be panicked, elderly, confused, or incomplete.

## Decision: Emergency Signals Reset Off-Topic State

**Rationale**: Real emergencies must always override scope handling. If a caller says "ช่วยด้วย", reports breathing difficulty, trapped people, fire, drowning, severe bleeding, self-harm danger, or similar high-risk content, the system must resume normal intake/escalation.

**Alternatives considered**:

- Keep off-topic count after emergency content. Rejected because it could prematurely close a real emergency call.
- Require location before resetting off-topic state. Rejected because high-risk callers may not provide location in the same turn.

## Decision: In-Memory Session State Extensions

**Rationale**: Off-topic/no-reply counters are session lifecycle state, not durable case facts. Existing `IntakeSessionState` already stores conversation and decision audit data, so additive fields keep implementation localized.

**Alternatives considered**:

- Add a separate database table or repository. Rejected because V0/V1 uses local mock storage by default and no new persistent resource is required.
- Store only in Twilio route local variables. Rejected for manual transcript intake and debug/audit visibility.

## Decision: Timeout-Based WebSocket Receive for No-Reply

**Rationale**: The existing Twilio WebSocket waits for inbound messages. No-reply prompts require actions while waiting, so `asyncio.wait_for` around `receive_json` provides a small additive change without rewriting media handling.

**Alternatives considered**:

- Add a background task per call. Rejected as more complex and easier to leak if calls disconnect.
- Require Twilio REST call status polling. Rejected because no-reply behavior should not require Twilio credentials.

## Decision: Safe Close via WebSocket First

**Rationale**: Closing the media WebSocket after a polite final prompt is sufficient for this feature and avoids Twilio REST credentials. REST call completion remains optional future work and disabled by default.

**Alternatives considered**:

- Always use Twilio REST API to complete the call. Rejected because credentials may be absent and tests must avoid live Twilio.
- Never close silent calls. Rejected because abandoned calls should not hold the line.

## Decision: Configurable Prompt Builder

**Rationale**: The Azure OpenAI prompt needs clear crisis-only behavior and must be auditable/versioned. Building it from settings makes prompt version, display name, allowed topics, and decline behavior visible and testable.

**Alternatives considered**:

- Keep a hardcoded prompt string. Rejected because the feature requires configurable scope and safer display identity.

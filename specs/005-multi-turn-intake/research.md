# Research: Multi-Turn Crisis Conversation Intake

## Decision: Add Conversation Intake as an Incremental Orchestrator

**Rationale**: Existing one-shot triage and voice processing already work. A new `IntakeOrchestrator` can sit between transcript production and final case creation without rewriting the current triage provider or changing Twilio route paths. This keeps risk contained and allows manual transcript intake to ship first.

**Alternatives considered**:
- Replace the existing triage provider directly: rejected because it risks breaking `/api/triage/from-transcript` and current Twilio demo behavior.
- Create a separate telephony-only conversation pipeline: rejected because it would duplicate VAD, transcription, safety, and case repository behavior.

## Decision: Keep V0 Intake Sessions In Memory

**Rationale**: The feature needs fast hackathon iteration and no new database resources. In-memory storage satisfies manual and live-call demo sessions while preserving an interface that can later move to local JSON or Cosmos DB.

**Alternatives considered**:
- Persist all sessions to Cosmos DB now: rejected because Cosmos is not configured and the request explicitly says not to add the resource.
- Store sessions only in case records: rejected because mid-conversation follow-ups need state before a final case exists.

## Decision: Use Deterministic Guardrails Before and After Model Decisions

**Rationale**: Safety requirements must not depend only on AI output. RED risks, human-review conditions, no-dispatch wording, and follow-up limits need deterministic enforcement over both Azure and fallback decisions.

**Alternatives considered**:
- Rely only on Azure OpenAI structured decisions: rejected because model output can miss or under-rank safety signals.
- Use current final-case safety rules only: rejected because follow-up decisions also need safety gating before a case is created.

## Decision: Rule-Based Grouping as Fallback and Corrective Layer

**Rationale**: Operational group mapping is explicitly defined and can be tested with deterministic keyword/rule coverage. Azure OpenAI can enrich grouping when configured, but the fallback must work offline.

**Alternatives considered**:
- Model-only grouping: rejected because tests must pass without Azure credentials.
- Hard-code group only from incident type: rejected because examples need cross-field logic, such as flood plus trapped people becoming rescue.

## Decision: Feature Flag Twilio Intake Integration

**Rationale**: Current Twilio media flow has been proven against Azure Container Apps. `ENABLE_MULTI_TURN_INTAKE=false` by default preserves the existing flow, while enabling controlled rollout of `intake.followup` and conversation-aware case creation.

**Alternatives considered**:
- Enable multi-turn intake immediately for all Twilio calls: rejected because it changes live demo behavior before tests and operator review.
- Manual transcript only forever: rejected because the success criteria require phone-call path integration.

## Decision: Return Text Follow-Up Only, No TTS

**Rationale**: The requested scope explicitly excludes spoken TTS back to Twilio. Returning `response_text` in WebSocket/API payloads supports debug validation and future TTS without adding call audio complexity now.

**Alternatives considered**:
- Add Azure Speech TTS now: rejected as out of scope and unnecessary for validating conversation decisions.

## Decision: Backward-Compatible Optional Case Fields

**Rationale**: Existing case records and dashboards must continue to load. Adding optional group/team/summary/audit fields to case records or case extensions lets newer records show richer intake context without invalidating older records.

**Alternatives considered**:
- Require all case records to include new fields: rejected because existing `.data/cases.json` records and tests would break.

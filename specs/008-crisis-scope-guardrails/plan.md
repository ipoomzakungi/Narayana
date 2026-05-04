# Implementation Plan: Crisis Scope Guardrails

**Branch**: `008-crisis-scope-guardrails` | **Date**: 2026-05-04 | **Spec**: `specs/008-crisis-scope-guardrails/spec.md`
**Input**: Feature specification from `specs/008-crisis-scope-guardrails/spec.md`

## Summary

Add crisis-intake scope guardrails and call lifecycle control as an additive layer over Narayana's existing intake and Twilio audio pipeline. The implementation will add configurable assistant identity/system-prompt settings, deterministic off-topic and emergency-signal classification, per-session off-topic/no-reply state, no-reply prompt/close handling for Twilio calls, and debug/audit visibility. The existing Azure OpenAI intake provider remains in place; its system prompt is refactored into a configurable builder and deterministic guardrails run before/after model decisions.

The independently testable MVP is manual transcript intake with deterministic off-topic handling: first off-topic turn redirects, repeated off-topic turns recommend call close, and an emergency phrase after off-topic speech resets scope handling and continues crisis intake. Twilio no-reply prompt/close is then layered into the existing WebSocket loop with timeout-based receive and existing TTS media sender helpers.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript/React/Next.js frontend for additive debug display.
**Primary Dependencies**: FastAPI WebSocket routes, Pydantic models/settings, existing intake orchestrator/provider/store, existing Twilio TTS media sender helper, pytest, existing Vitest/Next.js regression gates.
**Storage**: In-memory intake session state for scope/no-reply counters; existing local JSON/Cosmos-compatible case repository remains unchanged. No new database resource.
**Testing**: `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`.
**Target Platform**: FastAPI backend on Azure Container Apps for Twilio WebSocket support; frontend remains Azure Static Web Apps.
**Project Type**: Web service backend plus static dashboard/debug frontend.
**Performance Goals**: Off-topic classification is deterministic and immediate per caller turn. No-reply timers use configurable demo thresholds and must not block normal media handling.
**Constraints**: Do not rewrite Twilio audio pipeline; do not remove current intake provider; do not change Twilio route paths; do not enable Azure OpenAI secrets; do not implement ACS, SMS, rescue dispatch, web search, or Twilio REST hangup by default; tests must not require live cloud credentials.
**Scale/Scope**: Settings, two deterministic services, intake model extensions, Azure OpenAI prompt builder, intake orchestrator scope branch, Twilio timeout loop/no-reply prompts, debug type/display updates, docs, and targeted tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and defines no enforceable project-specific gates. This plan applies Narayana's active safety and compatibility constraints:

- Crisis content and high-risk signals always override off-topic handling.
- Scope/no-reply guardrails must be deterministic and testable without Azure OpenAI.
- Existing Twilio route paths and audio frame processing must remain compatible.
- No-reply and repeated off-topic close behavior must be polite and must not dispatch, SMS, or close real emergency cases automatically.
- TTS failures must not crash call handling.
- No secrets may be logged, returned, or committed.

Pre-design status: PASS. No unresolved clarifications.

Post-design status: PASS. Research, model, contracts, and quickstart preserve additive scope, crisis override behavior, and existing pipeline compatibility.

## Project Structure

### Documentation (this feature)

```text
specs/008-crisis-scope-guardrails/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── intake-scope-response.md
│   ├── twilio-no-reply-websocket.md
│   └── voice-debug-fields.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes_twilio.py
├── core/
│   └── config.py
├── models/
│   ├── intake.py
│   └── tts.py
└── services/
    ├── azure_openai_intake_provider.py
    ├── call_lifecycle_service.py
    ├── intake_orchestrator.py
    ├── intake_scope_guardrails.py
    └── intake_session_store.py

frontend/
├── components/voice/VoiceDebugConsole.tsx
└── types/triage.ts

tests/
├── integration/
│   ├── test_intake_api.py
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_call_lifecycle_service.py
    ├── test_intake_scope_guardrails.py
    ├── test_intake_provider.py
    ├── test_intake_orchestrator.py
    └── test_telephony_config.py
```

**Structure Decision**: Keep scope classification and call lifecycle behavior in new service modules. Extend `IntakeSessionState` rather than creating a separate storage layer. Integrate scope handling inside `IntakeOrchestrator` before model decisions. Integrate no-reply timers inside the existing Twilio WebSocket loop using timeout receive and the existing TTS sender.

## Implementation Approach

1. Add settings in `app/core/config.py`:
   - `assistant_display_name`
   - `assistant_system_prompt_version`
   - `assistant_scope`
   - `assistant_allowed_topics`
   - `assistant_decline_off_topic`
   - `call_no_reply_seconds`
   - `call_no_reply_prompt_seconds`
   - `call_max_no_reply_prompts`
   - `call_max_off_topic_redirects`
   - `call_end_on_repeated_off_topic`
   - `call_end_on_no_reply`
   - `twilio_force_hangup_enabled=false`
2. Update default assistant/greeting settings so the default Thai greeting uses "ระบบช่วยรับแจ้งเหตุ" instead of hardcoded "นารายานา".
3. Extend `app/models/intake.py` with off-topic/no-reply/call-close fields and additive response/audit fields where needed.
4. Add `app/services/intake_scope_guardrails.py` with:
   - `OffTopicResult`
   - `classify_scope(transcript, session_state, settings)`
   - `is_emergency_signal(text)`
   - `is_off_topic(text)`
   - deterministic Thai/English examples and emergency override patterns.
5. Add `app/services/call_lifecycle_service.py` with:
   - greeting and last-speech timestamp helpers
   - no-reply prompt/final close text builders
   - `should_prompt_no_reply`
   - `should_close_for_no_reply`
   - `should_close_for_off_topic`
6. Refactor `AzureOpenAIIntakeProvider` system prompt into `build_intake_system_prompt(settings)`, including crisis-only scope, allowed topics, off-topic decline rules, no dispatch, no diagnosis, one question, Thai-first, and JSON-only response instructions.
7. In `IntakeOrchestrator.process_transcript`:
   - update last caller speech time
   - classify scope before model
   - if emergency signal: reset off-topic counters and continue normal intake
   - if off-topic: increment counters, append assistant redirect/final warning, return `ask_followup` with call-end metadata when thresholds are exceeded, and avoid case creation unless explicitly required for human review
   - after model: keep current safety enforcement and attach scope warnings/audit.
8. In `routes_twilio.py`:
   - after start/greeting, track greeting sent time in lifecycle state
   - use timeout-based receive so no-reply prompts can be sent while waiting for media
   - send no-reply prompt via existing TTS helper
   - after max prompts, send final close prompt and close WebSocket safely
   - keep normal media handling unchanged when messages arrive.
9. Add `TTSProfile.CLOSING` if helpful for final close/no-reply text; otherwise use `unclear` or `followup` profile consistently.
10. Update frontend types and voice debug console to show `off_topic_count`, `no_reply_prompt_count`, `call_end_recommended`, `call_end_reason`, last assistant redirect, guardrail warnings, and response text.
11. Update README and `.env.example` with scope prompt, no-reply/off-topic env vars, recommended greeting text, Twilio test guidance, and out-of-scope warnings.
12. Add tests:
   - scope guardrails unit tests
   - lifecycle service unit tests
   - intake API off-topic redirect/repeated close/emergency override
   - Twilio WebSocket no-reply prompt/final close with mocked TTS
   - prompt builder tests for no dispatch/no diagnosis/off-topic rules
   - frontend debug display tests
   - existing regression suites.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

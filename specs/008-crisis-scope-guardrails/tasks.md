# Tasks: Crisis Scope Guardrails

**Input**: Design documents from `specs/008-crisis-scope-guardrails/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Tests**: Required by specification. Test tasks are included before implementation tasks for each behavior.
**Constraints**: No web search, no Azure OpenAI secret enablement, no ACS, no SMS, no dispatch, and no Twilio route path changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on another incomplete task.
- **[Story]**: Maps to user stories from `spec.md`.
- Every task includes files, dependencies, acceptance criteria, and a test command.

## Phase 1: Setup - Config/Env Additions

**Purpose**: Add visible configuration placeholders before behavior changes.

- [X] T001 [P] Add scope/no-reply environment variable entries in `.env.example` (Deps: none; Acceptance: includes `ASSISTANT_DISPLAY_NAME`, `ASSISTANT_SYSTEM_PROMPT_VERSION`, `ASSISTANT_SCOPE`, `ASSISTANT_ALLOWED_TOPICS`, `ASSISTANT_DECLINE_OFF_TOPIC`, `CALL_NO_REPLY_SECONDS`, `CALL_NO_REPLY_PROMPT_SECONDS`, `CALL_MAX_NO_REPLY_PROMPTS`, `CALL_MAX_OFF_TOPIC_REDIRECTS`, `CALL_END_ON_REPEATED_OFF_TOPIC`, `CALL_END_ON_NO_REPLY`, `TWILIO_FORCE_HANGUP_ENABLED`; Test: `Select-String -Path .env.example -Pattern "ASSISTANT_DISPLAY_NAME|CALL_NO_REPLY_SECONDS|TWILIO_FORCE_HANGUP_ENABLED"`)

**Checkpoint**: Environment contract is visible, but runtime behavior is unchanged.

---

## Phase 2: Foundational - Shared Models and TTS Closing Profile

**Purpose**: Add shared model fields and closing voice profile that later stories depend on.

- [X] T002 [P] Add intake state extension validation tests in `tests/unit/test_intake_models.py` (Deps: T001; Acceptance: tests assert default `off_topic_count`, `redirect_count`, `no_reply_prompt_count`, `call_end_recommended`, and `call_end_reason` values; Test: `pytest tests/unit/test_intake_models.py -q`)
- [X] T003 Extend `IntakeSessionState` and response payload models in `app/models/intake.py` (Deps: T002; Acceptance: state includes `off_topic_count`, `redirect_count`, `last_off_topic_at`, `last_assistant_redirect`, `no_reply_prompt_count`, `last_caller_speech_at`, `greeting_sent_at`, `call_end_recommended`, `call_end_reason` with backward-compatible defaults; Test: `pytest tests/unit/test_intake_models.py -q`)
- [X] T004 [P] Add TTS closing profile tests in `tests/unit/test_azure_speech_tts_service.py` and `tests/unit/test_tts_models.py` (Deps: T001; Acceptance: tests verify `closing` profile is accepted, produces calm prosody, and does not allow dispatch phrases; Test: `pytest tests/unit/test_azure_speech_tts_service.py tests/unit/test_tts_models.py -q`)
- [X] T005 Add `TTSProfile.CLOSING` and closing prosody support in `app/models/tts.py` and `app/services/azure_speech_tts_service.py` (Deps: T004; Acceptance: `closing` profile can be used by `/api/tts/test` and Twilio TTS helpers without Azure credentials in tests; Test: `pytest tests/unit/test_azure_speech_tts_service.py tests/unit/test_tts_models.py -q`)

**Checkpoint**: New state and TTS profile are available to services without changing Twilio route behavior.

---

## Phase 3: User Story 2 - Configurable Assistant Identity and Prompt Scope (Priority: P1)

**Goal**: Make assistant identity, greeting, allowed topics, and prompt scope configurable with safe Thai defaults.

**Independent Test**: Configure defaults only and verify the prompt/greeting use `ระบบช่วยรับแจ้งเหตุ` and crisis-intake-only rules.

### Tests for User Story 2

- [X] T006 [P] [US2] Add config default tests in `tests/unit/test_telephony_config.py` (Deps: T001; Acceptance: tests assert neutral display name, default Thai greeting, crisis scope defaults, allowed topics, and off-topic decline default true; Test: `pytest tests/unit/test_telephony_config.py -q`)
- [X] T007 [P] [US2] Add prompt builder tests in `tests/unit/test_intake_provider.py` (Deps: T001; Acceptance: tests assert generated prompt includes Thai-first behavior, crisis-only scope, allowed topics, off-topic decline text, no dispatch, no diagnosis, one-question rule, and response length limit; Test: `pytest tests/unit/test_intake_provider.py -q`)

### Implementation for User Story 2

- [X] T008 [US2] Add assistant scope settings and neutral default greeting in `app/core/config.py` (Deps: T006; Acceptance: settings expose `assistant_display_name`, `assistant_system_prompt_version`, `assistant_scope`, `assistant_allowed_topics`, `assistant_decline_off_topic`, no-reply thresholds, and `twilio_force_hangup_enabled=false`; Test: `pytest tests/unit/test_telephony_config.py -q`)
- [X] T009 [US2] Refactor Azure OpenAI intake prompt into `build_intake_system_prompt(settings)` in `app/services/azure_openai_intake_provider.py` (Deps: T007, T008; Acceptance: provider uses the builder and the prompt includes all scope, redirect, safety, and JSON-only rules without hardcoded unrelated chatbot behavior; Test: `pytest tests/unit/test_intake_provider.py -q`)

**Checkpoint**: User Story 2 is independently testable through config and prompt builder tests.

---

## Phase 4: User Story 1 - Crisis-Focused Assistant Behavior (Priority: P1)

**Goal**: Detect clearly off-topic caller turns and redirect without answering unrelated requests.

**Independent Test**: Submit an off-topic manual transcript and verify the assistant returns the required Thai redirect without creating a case.

### Tests for User Story 1

- [X] T010 [P] [US1] Add deterministic scope guardrail tests in `tests/unit/test_intake_scope_guardrails.py` (Deps: T003, T008; Acceptance: tests classify jokes, weather/news, coding/math, finance, politics, flirting, and casual chat as off-topic while avoiding false positives for unclear or short emergency-like text; Test: `pytest tests/unit/test_intake_scope_guardrails.py -q`)
- [X] T011 [P] [US1] Add first off-topic intake API integration test in `tests/integration/test_intake_api.py` (Deps: T003, T008; Acceptance: first unrelated transcript returns `action=ask_followup`, required Thai redirect, `off_topic_count=1`, `redirect_count=1`, `call_end_recommended=false`, `created_case=null`; Test: `pytest tests/integration/test_intake_api.py -q`)

### Implementation for User Story 1

- [X] T012 [US1] Implement `OffTopicResult`, `is_emergency_signal`, `is_off_topic`, and `classify_scope` in `app/services/intake_scope_guardrails.py` (Deps: T010; Acceptance: deterministic service returns category, confidence, reason, matched terms, response text, and guardrail warnings without calling Azure; Test: `pytest tests/unit/test_intake_scope_guardrails.py -q`)
- [X] T013 [US1] Add first off-topic redirect branch in `app/services/intake_orchestrator.py` and state updates in `app/services/intake_session_store.py` (Deps: T011, T012; Acceptance: orchestrator runs scope guardrails before model, appends assistant redirect, does not create a case for first off-topic turn, and preserves existing in-scope intake behavior; Test: `pytest tests/integration/test_intake_api.py tests/unit/test_intake_orchestrator.py -q`)

**Checkpoint**: User Story 1 is independently testable through `/api/intake/from-transcript`.

---

## Phase 5: User Story 3 - Repeated Off-Topic Caller Handling (Priority: P1)

**Goal**: Warn and recommend ending calls after repeated unrelated turns.

**Independent Test**: Send three unrelated transcripts in one session and verify redirect, final warning, then close recommendation.

### Tests for User Story 3

- [X] T014 [P] [US3] Add repeated off-topic unit tests in `tests/unit/test_intake_orchestrator.py` (Deps: T013; Acceptance: first off-topic redirects, second warns, third sets `call_end_recommended=true` and `call_end_reason=repeated_off_topic`; Test: `pytest tests/unit/test_intake_orchestrator.py -q`)
- [X] T015 [P] [US3] Add repeated off-topic contract integration test in `tests/integration/test_intake_api.py` (Deps: T013; Acceptance: response shape matches `contracts/intake-scope-response.md` for repeated off-topic close recommendation; Test: `pytest tests/integration/test_intake_api.py -q`)

### Implementation for User Story 3

- [X] T016 [US3] Implement repeated off-topic counters and final close recommendation in `app/services/intake_orchestrator.py` (Deps: T014, T015; Acceptance: respects `call_max_off_topic_redirects` and `call_end_on_repeated_off_topic`, increments redirect counters, stores `last_off_topic_at`, and returns final polite Thai close text; Test: `pytest tests/unit/test_intake_orchestrator.py tests/integration/test_intake_api.py -q`)
- [X] T017 [US3] Add off-topic audit entries and warnings in `app/services/intake_orchestrator.py` and `app/services/intake_session_store.py` (Deps: T016; Acceptance: session decision audit records off-topic redirects, final warning, close recommendation, and no emergency case closure/dispatch claims; Test: `pytest tests/unit/test_intake_orchestrator.py -q`)

**Checkpoint**: User Story 3 can be validated without Twilio or Azure credentials.

---

## Phase 6: User Story 5 - Emergency Signals Override Scope Guardrails (Priority: P1)

**Goal**: Ensure high-risk or crisis content always resets/bypasses off-topic handling and continues intake/escalation.

**Independent Test**: Send an off-topic turn followed by "ช่วยด้วย น้ำท่วม มีคนแก่หายใจลำบากติดอยู่ชั้นสอง" and verify crisis intake continues.

### Tests for User Story 5

- [X] T018 [P] [US5] Add emergency override classification tests in `tests/unit/test_intake_scope_guardrails.py` (Deps: T012; Acceptance: `ช่วยด้วย`, breathing difficulty, trapped, severe bleeding, drowning, fire/smoke, self-harm danger, panic, elderly risk, and short emergency phrases are not off-topic; Test: `pytest tests/unit/test_intake_scope_guardrails.py -q`)
- [X] T019 [P] [US5] Add emergency-after-off-topic orchestration tests in `tests/unit/test_intake_orchestrator.py` (Deps: T016; Acceptance: emergency turn resets or stops increasing off-topic counters, adds `scope:emergency_override`, and proceeds to normal intake/escalation; Test: `pytest tests/unit/test_intake_orchestrator.py -q`)
- [X] T020 [P] [US5] Add RED high-risk regression test in `tests/integration/test_intake_api.py` (Deps: T016; Acceptance: breathing difficulty/trapped flood sample still creates or escalates RED/human-review behavior and is never treated as off-topic; Test: `pytest tests/integration/test_intake_api.py -q`)

### Implementation for User Story 5

- [X] T021 [US5] Add emergency override reset logic in `app/services/intake_scope_guardrails.py` and `app/services/intake_orchestrator.py` (Deps: T018, T019, T020; Acceptance: any detected emergency signal bypasses off-topic redirects, clears close recommendation for repeated off-topic when appropriate, and preserves existing safety rules for high-risk RED cases; Test: `pytest tests/unit/test_intake_scope_guardrails.py tests/unit/test_intake_orchestrator.py tests/integration/test_intake_api.py -q`)

**Checkpoint**: Emergency content has priority over scope handling.

---

## Phase 7: User Story 4 - No-Reply Caller Handling (Priority: P1)

**Goal**: Prompt silent callers after greeting, then close safely after repeated silence using existing Twilio/TTS helpers.

**Independent Test**: Run a Twilio WebSocket test with greeting/TTS enabled and no media messages; verify no-reply prompt, final close payload, and safe WebSocket close.

### Tests for User Story 4

- [X] T022 [P] [US4] Add call lifecycle service tests in `tests/unit/test_call_lifecycle_service.py` (Deps: T003, T008; Acceptance: tests cover greeting time tracking, last caller speech tracking, no-reply prompt timing, max prompt threshold, final close prompt, and off-topic close predicate; Test: `pytest tests/unit/test_call_lifecycle_service.py -q`)
- [X] T023 [P] [US4] Add Twilio no-reply WebSocket tests in `tests/integration/test_twilio_media_flow.py` (Deps: T005, T008; Acceptance: mocked TTS sends `call.no_reply_prompt`, then `call.ending`, then closes safely without Twilio REST credentials; Test: `pytest tests/integration/test_twilio_media_flow.py -q`)
- [X] T024 [P] [US4] Add TTS failure no-reply regression test in `tests/integration/test_twilio_media_flow.py` (Deps: T023; Acceptance: TTS failure during no-reply prompt logs or emits failure metadata and does not crash normal WebSocket handling; Test: `pytest tests/integration/test_twilio_media_flow.py -q`)

### Implementation for User Story 4

- [X] T025 [US4] Implement `CallLifecycleState` and no-reply decision helpers in `app/services/call_lifecycle_service.py` (Deps: T022; Acceptance: service builds required Thai no-reply prompt and final close prompt, respects configured thresholds, and has no network or Twilio REST dependency; Test: `pytest tests/unit/test_call_lifecycle_service.py -q`)
- [X] T026 [US4] Add timeout-based receive and no-reply prompt handling in `app/api/routes_twilio.py` (Deps: T023, T025; Acceptance: `/ws/telephony/twilio/{call_id}` route path remains unchanged, normal media handling still works, no-reply prompt uses existing `_send_tts_media`, and lifecycle activates only when initial greeting or Twilio TTS response behavior is enabled; Test: `pytest tests/integration/test_twilio_media_flow.py -q`)
- [X] T027 [US4] Add final no-reply close behavior in `app/api/routes_twilio.py` (Deps: T026; Acceptance: final close payload includes `call_end_recommended=true`, `call_end_reason=no_reply`, sends final TTS when possible, and closes the WebSocket safely without dispatch/SMS/Twilio REST hangup; Test: `pytest tests/integration/test_twilio_media_flow.py -q`)
- [X] T028 [US4] Update session no-reply counters from Twilio lifecycle in `app/services/intake_session_store.py` and `app/services/audio_session_processor.py` (Deps: T025, T027; Acceptance: debug payloads can include `no_reply_prompt_count`, `greeting_sent_at`, `last_caller_speech_at`, and close reason without disrupting current local mic or simulated Twilio media tests; Test: `pytest tests/integration/test_twilio_media_flow.py tests/integration/test_intake_api.py -q`)

**Checkpoint**: Silent-call behavior is independently testable with mocked TTS and no real Twilio credentials.

---

## Phase 8: User Story 6 - Operator Debug and Audit Visibility (Priority: P2)

**Goal**: Surface scope/no-reply counters, close recommendations, redirect text, and guardrail warnings in debug UI and payloads.

**Independent Test**: Trigger off-topic and no-reply flows and verify debug payload/UI display all additive fields while older records remain compatible.

### Tests for User Story 6

- [X] T029 [P] [US6] Add frontend debug rendering tests in `frontend/tests/voice-debug-console.test.tsx` (Deps: T003; Acceptance: tests render `off_topic_count`, `redirect_count`, `no_reply_prompt_count`, `call_end_recommended`, `call_end_reason`, `last_assistant_redirect`, `guardrail_warnings`, and `response_text`; Test: `cd frontend && npm test -- voice-debug-console`)
- [X] T030 [P] [US6] Add backend debug payload tests in `tests/unit/test_intake_orchestrator.py` and `tests/integration/test_twilio_media_flow.py` (Deps: T017, T028; Acceptance: off-topic and no-reply payloads include additive debug fields from `contracts/voice-debug-fields.md`; Test: `pytest tests/unit/test_intake_orchestrator.py tests/integration/test_twilio_media_flow.py -q`)

### Implementation for User Story 6

- [X] T031 [US6] Extend voice debug TypeScript types in `frontend/types/triage.ts` (Deps: T029; Acceptance: frontend accepts optional scope/no-reply fields with backward-compatible optional properties; Test: `cd frontend && npm test -- voice-debug-console`)
- [X] T032 [US6] Update `VoiceDebugConsole` display in `frontend/components/voice/VoiceDebugConsole.tsx` (Deps: T031; Acceptance: debug console shows counters, close recommendation, close reason, last redirect, guardrail warnings, and response text without hiding transcript/VAD/TTS fields; Test: `cd frontend && npm test -- voice-debug-console`)
- [X] T033 [US6] Attach scope/no-reply audit fields to intake and WebSocket payloads in `app/services/intake_orchestrator.py`, `app/services/audio_session_processor.py`, and `app/api/routes_twilio.py` (Deps: T030, T032; Acceptance: backend emits additive debug fields for off-topic redirects, emergency override, no-reply prompts, and final close without raw audio or secrets; Test: `pytest tests/unit/test_intake_orchestrator.py tests/integration/test_twilio_media_flow.py -q`)

**Checkpoint**: Operators can explain why a redirect, prompt, or close recommendation occurred.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression gates, and final secret-safety checks.

- [X] T034 [P] Update scope guardrail and no-reply documentation in `README.md` (Deps: T001, T009, T021, T027; Acceptance: README explains assistant display name, prompt scope vars, off-topic redirect behavior, no-reply thresholds, Twilio test steps, log messages, and explicitly says no ACS/SMS/dispatch; Test: `Select-String -Path README.md -Pattern "ASSISTANT_DISPLAY_NAME|CALL_NO_REPLY_SECONDS|No SMS|dispatch"`)
- [X] T035 [P] Update manual validation steps in `specs/008-crisis-scope-guardrails/quickstart.md` if implementation details differ (Deps: T027, T033; Acceptance: quickstart matches actual env vars, endpoint payloads, expected Thai texts, and test commands; Test: `Select-String -Path specs/008-crisis-scope-guardrails/quickstart.md -Pattern "call.no_reply_prompt|scope.off_topic|pytest"`)
- [X] T036 Run Python compile verification for `app/` and `scripts/` (Deps: T033; Acceptance: compileall completes without syntax errors; Test: `python -m compileall app scripts`)
- [X] T037 Run full backend test suite for `tests/` (Deps: T036; Acceptance: all backend unit/integration tests pass without Azure OpenAI, ACS, SMS, or live Twilio credentials; Test: `pytest`)
- [X] T038 Run frontend unit tests for `frontend/` (Deps: T032, T037; Acceptance: frontend tests pass and existing `/voice-debug` coverage remains green; Test: `cd frontend && npm test`)
- [X] T039 Run frontend production build for `frontend/` (Deps: T038; Acceptance: static/export build completes successfully; Test: `cd frontend && npm run build`)
- [X] T040 Verify git status and secret safety for repository root `.` (Deps: T039; Acceptance: `.env.azure.local` and secrets are not staged, no Azure keys are printed or committed, Twilio route paths remain `/api/telephony/twilio/incoming-call` and `/ws/telephony/twilio/{call_id}`; Test: `git status --short && git check-ignore -v .env.azure.local && Select-String -Path app/api/routes_twilio.py -Pattern "/ws/telephony/twilio|incoming-call"`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on T001 and blocks all user-story implementation.
- **US2 (Phase 3)**: Depends on config visibility and can complete before behavior changes.
- **US1 (Phase 4)**: Depends on state model and config/prompt foundations.
- **US3 (Phase 5)**: Depends on US1 off-topic redirect branch.
- **US5 (Phase 6)**: Depends on US1/US3 scope state and validates emergency override before Twilio lifecycle.
- **US4 (Phase 7)**: Depends on shared models, closing TTS profile, and current Twilio TTS helper.
- **US6 (Phase 8)**: Depends on backend payload fields from US1/US3/US4.
- **Polish (Phase 9)**: Depends on desired stories being complete.

### User Story Dependencies

- **US2 Configurable identity/prompt scope**: Independent after Setup; should be completed early because other behavior reads settings.
- **US1 Crisis-focused behavior**: Depends on US2 settings and model fields.
- **US3 Repeated off-topic handling**: Depends on US1 first redirect behavior.
- **US5 Emergency override**: Depends on US1 scope classifier and US3 counters.
- **US4 No-reply handling**: Independent of US1/US3 business logic after foundational TTS/model work, but should run after Twilio TTS regression tests are in place.
- **US6 Debug/audit visibility**: Depends on emitted backend fields from US1, US3, US4, and US5.

### MVP Scope

The MVP for this feature is:

1. T001-T013: config, prompt builder, scope classifier, and first off-topic redirect.
2. T014-T021: repeated off-topic close recommendation and emergency override.
3. Validate with `pytest tests/unit/test_intake_scope_guardrails.py tests/unit/test_intake_orchestrator.py tests/integration/test_intake_api.py -q`.

Twilio no-reply handling can be layered after the manual intake scope behavior is stable.

---

## Parallel Execution Examples

### Parallel after Setup

```text
Task: T002 intake model tests in tests/unit/test_intake_models.py
Task: T004 TTS closing profile tests in tests/unit/test_azure_speech_tts_service.py and tests/unit/test_tts_models.py
Task: T006 config default tests in tests/unit/test_telephony_config.py
Task: T007 prompt builder tests in tests/unit/test_intake_provider.py
```

### Parallel for Scope Behavior

```text
Task: T010 scope guardrail tests in tests/unit/test_intake_scope_guardrails.py
Task: T011 first off-topic intake API test in tests/integration/test_intake_api.py
```

### Parallel for No-Reply and Debug

```text
Task: T022 call lifecycle service tests in tests/unit/test_call_lifecycle_service.py
Task: T023 Twilio no-reply WebSocket tests in tests/integration/test_twilio_media_flow.py
Task: T029 frontend debug rendering tests in frontend/tests/voice-debug-console.test.tsx
```

---

## Implementation Strategy

### Incremental Delivery

1. Complete Setup and Foundational phases.
2. Deliver US2 and US1 first so manual transcript intake stays crisis-focused.
3. Add US3 and US5 so repeated off-topic behavior cannot block emergency overrides.
4. Add US4 no-reply Twilio lifecycle behavior behind existing TTS/greeting controls.
5. Add US6 debug/audit visibility.
6. Run final gates and verify secrets are not staged.

### Safety Notes

- Keep `ENABLE_MULTI_TURN_INTAKE` behavior compatible with existing defaults.
- Do not change `POST /api/telephony/twilio/incoming-call`.
- Do not change `/ws/telephony/twilio/{call_id}`.
- Do not add ACS, SMS, emergency dispatch, Azure OpenAI secret enablement, or Twilio REST hangup as required behavior.

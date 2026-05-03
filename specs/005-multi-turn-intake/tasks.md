# Tasks: Multi-Turn Crisis Conversation Intake

**Input**: Design documents from `specs/005-multi-turn-intake/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Branch**: `005-multi-turn-intake`

**Tests**: Required by the feature spec. Write or update tests before implementation where practical, keep Azure/Twilio credentials optional, and preserve existing direct triage and Twilio route regressions.

**Organization**: Tasks are grouped by Spec Kit user story while preserving the requested implementation task groups. `ENABLE_MULTI_TURN_INTAKE` must remain `false` by default.

## Phase 1: Setup and Shared Configuration

**Purpose**: Add safe defaults and documentation scaffolding without changing runtime behavior.

- [X] T001 Update assistant and intake environment defaults in `app/core/config.py`
  - Dependencies: none
  - Acceptance criteria: `ENABLE_MULTI_TURN_INTAKE=false`, `ASSISTANT_LANGUAGE=th`, `ASSISTANT_TONE=calm_concise`, `ASSISTANT_MAX_FOLLOWUPS=3`, `ASSISTANT_QUESTION_STYLE=single_short_question`, `ASSISTANT_NAME=Narayana`, and `ASSISTANT_RESPONSE_MAX_CHARS=180` are exposed through settings; existing settings continue to load.
  - Test command: `pytest tests/unit/test_telephony_config.py`

- [X] T002 [P] Add intake environment examples to `.env.example` and `frontend/.env.example`
  - Dependencies: none
  - Acceptance criteria: env files document the new intake variables and state that multi-turn Twilio intake is off by default; no secrets are added.
  - Test command: `rg -n "ENABLE_MULTI_TURN_INTAKE|ASSISTANT_MAX_FOLLOWUPS|ASSISTANT_NAME" .env.example frontend/.env.example`

- [X] T003 [P] Add intake API client test placeholders in `frontend/tests/intake-api-client.test.ts`
  - Dependencies: none
  - Acceptance criteria: test file describes expected `POST /api/intake/from-transcript` request/response behavior and fails until the client exists.
  - Test command: `cd frontend && npm test -- intake-api-client.test.ts`

**Checkpoint**: New settings are documented and default runtime behavior is unchanged.

---

## Phase 2: Foundational Intake Primitives

**Purpose**: Core models and deterministic services required by all user stories.

**Critical**: No user story should depend on Azure credentials, Twilio credentials, SMS, ACS, TTS, or emergency dispatch.

### Intake Models and Enums

- [X] T004 [P] Create intake Pydantic models and enums in `app/models/intake.py`
  - Dependencies: T001
  - Acceptance criteria: defines `ConversationSpeaker`, `IntakeAction`, `CaseGroup`, `ConversationTurn`, `IntakeCollectedFields`, `IntakeSessionState`, `IntakeRequest`, `IntakeDecision`, and `IntakeResponse`; request transcript validation rejects blanks.
  - Test command: `pytest tests/unit/test_intake_models.py`

- [X] T005 [P] Add intake model validation tests in `tests/unit/test_intake_models.py`
  - Dependencies: T004
  - Acceptance criteria: covers enum values, blank transcript rejection, default Thai language, default max followups, and `created_case` null/present expectations by action.
  - Test command: `pytest tests/unit/test_intake_models.py`

### In-Memory Intake Session Store

- [X] T006 [P] Implement in-memory intake session store in `app/services/intake_session_store.py`
  - Dependencies: T004
  - Acceptance criteria: supports get/create, append caller turn, append assistant turn, state update, optional clear/reset; assigns ordered turn indexes and preserves append-only history.
  - Test command: `pytest tests/unit/test_intake_session_store.py`

- [X] T007 [P] Add session store tests in `tests/unit/test_intake_session_store.py`
  - Dependencies: T006
  - Acceptance criteria: verifies state reuse by session ID, caller/assistant turn ordering, followup count update, final case ID update, and clear/reset behavior if implemented.
  - Test command: `pytest tests/unit/test_intake_session_store.py`

### Deterministic Guardrails

- [X] T008 [P] Implement deterministic intake guardrails in `app/services/intake_guardrails.py`
  - Dependencies: T004
  - Acceptance criteria: detects Thai and English RED phrases for breathing difficulty, unconsciousness, severe bleeding, trapped, drowning, active fire/smoke, chest pain/stroke symptoms, self-harm danger, child/elderly vulnerable risk; returns forced triage, human-review flag, reasons, and obvious group.
  - Test command: `pytest tests/unit/test_intake_guardrails.py`

- [X] T009 [P] Add guardrail tests in `tests/unit/test_intake_guardrails.py`
  - Dependencies: T008
  - Acceptance criteria: covers Thai sample `น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง`, active fire, severe bleeding, unconsciousness, drowning, self-harm, unclear safe text, and no-dispatch wording safety expectations.
  - Test command: `pytest tests/unit/test_intake_guardrails.py`

### Case Grouping Service

- [X] T010 [P] Implement rule-based case grouping in `app/services/case_grouping_service.py`
  - Dependencies: T004
  - Acceptance criteria: maps flood/trapped to rescue, medical symptoms to medical, fire to fire, crime/violence to police_public_safety, tourist terms to tourist_support, utility issues to utility_infrastructure, shelter/supplies to shelter_supplies, self-harm/distress to mental_health_support, and unclear cases to unknown_human_review.
  - Test command: `pytest tests/unit/test_case_grouping_service.py`

- [X] T011 [P] Add grouping service tests in `tests/unit/test_case_grouping_service.py`
  - Dependencies: T010
  - Acceptance criteria: covers each operational group and verifies `unknown_human_review` requires human review.
  - Test command: `pytest tests/unit/test_case_grouping_service.py`

**Checkpoint**: Models, session memory, guardrails, and grouping can be tested independently.

---

## Phase 3: User Story 1 - Continue a Crisis Intake Conversation (Priority: P1) MVP

**Goal**: Manual transcript sessions remember context and ask one concise Thai follow-up instead of creating premature cases.

**Independent Test**: Submit `น้ำท่วมอยู่ที่หาดใหญ่` to `POST /api/intake/from-transcript`; verify `ask_followup`, location/incident retained, missing critical fields listed, one Thai question returned, and no case created.

### Tests for User Story 1

- [X] T012 [P] [US1] Add intake route contract tests in `tests/integration/test_intake_api.py`
  - Dependencies: T004, T006
  - Acceptance criteria: test incomplete flood transcript returns `ask_followup`, preserves `หาดใหญ่`, includes missing fields, and returns `created_case=null`.
  - Test command: `pytest tests/integration/test_intake_api.py`

- [X] T013 [P] [US1] Add missing-field orchestration tests in `tests/unit/test_intake_orchestrator.py`
  - Dependencies: T004, T006, T008, T010
  - Acceptance criteria: verifies missing location asks for location, known location asks injury/danger next, and repeated known information does not trigger redundant questions.
  - Test command: `pytest tests/unit/test_intake_orchestrator.py`

### Azure OpenAI Intake Provider With JSON Schema

- [X] T014 [US1] Implement deterministic fallback intake decision logic in `app/services/azure_openai_intake_provider.py`
  - Dependencies: T004, T008, T010
  - Acceptance criteria: works without Azure credentials, merges latest transcript with session state, returns structured `IntakeDecision`, asks one Thai question, and respects response length limits.
  - Test command: `pytest tests/unit/test_intake_orchestrator.py`

- [X] T015 [US1] Add Azure OpenAI structured intake schema support in `app/services/azure_openai_intake_provider.py`
  - Dependencies: T014
  - Acceptance criteria: when Azure OpenAI config exists, sends session state and latest transcript with a JSON schema enforcing action, updated fields, group/team, triage, confidence, missing fields, response text, reason, and warnings; fallback still runs without credentials.
  - Test command: `pytest tests/unit/test_provider_fallback.py tests/unit/test_intake_orchestrator.py`

- [X] T016 [US1] Add provider fallback tests in `tests/unit/test_intake_provider.py`
  - Dependencies: T014, T015
  - Acceptance criteria: verifies no Azure credentials produce deterministic fallback, JSON-like decision shape is validated, and follow-up text is concise Thai.
  - Test command: `pytest tests/unit/test_intake_provider.py`

### Intake Orchestrator and Route

- [X] T017 [US1] Implement intake orchestrator follow-up path in `app/services/intake_orchestrator.py`
  - Dependencies: T006, T008, T010, T014
  - Acceptance criteria: loads session, appends caller turn, runs guardrails/provider, merges collected fields, enforces single-question follow-up, appends assistant turn, updates session state, and returns `IntakeResponse` without creating a case for `ask_followup`.
  - Test command: `pytest tests/unit/test_intake_orchestrator.py`

- [X] T018 [US1] Create intake API route in `app/api/routes_intake.py`
  - Dependencies: T017
  - Acceptance criteria: exposes `POST /api/intake/from-transcript` with the contract response shape; invalid blank transcript returns validation error; endpoint works in mock/default mode.
  - Test command: `pytest tests/integration/test_intake_api.py`

- [X] T019 [US1] Register intake router in `app/main.py`
  - Dependencies: T018
  - Acceptance criteria: FastAPI app includes intake router without removing existing triage, cases, local audio, Twilio, or ACS routes.
  - Test command: `python -m compileall app && pytest tests/integration/test_intake_api.py tests/integration/test_thai_transcript_to_red_case.py`

- [X] T020 [US1] Add frontend intake API client in `frontend/lib/intake-api-client.ts`
  - Dependencies: T018
  - Acceptance criteria: client posts session ID, transcript, language hint, and source input mode to `/api/intake/from-transcript`; parses action, response text, partial state, group/team, missing fields, warnings, and created case.
  - Test command: `cd frontend && npm test -- intake-api-client.test.ts`

**Checkpoint**: US1 is independently demoable through manual transcript API and can be exercised from frontend code.

---

## Phase 4: User Story 2 - Immediately Escalate High-Risk Cases (Priority: P1)

**Goal**: RED risks create or escalate a human-review case on the same turn, even when fields are missing.

**Independent Test**: Submit `น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง`; verify RED, human review, created case, rescue/medical reason, safe response text, and no dispatch claim.

### Tests for User Story 2

- [X] T021 [P] [US2] Add RED escalation integration tests in `tests/integration/test_intake_api.py`
  - Dependencies: T018
  - Acceptance criteria: Thai flood + elderly breathing difficulty + trapped creates or escalates a RED human-review case with group/team and created case included.
  - Test command: `pytest tests/integration/test_intake_api.py`

- [X] T022 [P] [US2] Add max-followup human-review tests in `tests/unit/test_intake_orchestrator.py`
  - Dependencies: T017
  - Acceptance criteria: after three follow-ups with missing fields, orchestrator creates a low-confidence human-review case and does not ask a fourth question.
  - Test command: `pytest tests/unit/test_intake_orchestrator.py`

### Implementation for User Story 2

- [X] T023 [US2] Extend `CrisisCase`/repository record optional intake fields in `app/models/case.py`
  - Dependencies: T004, T017
  - Acceptance criteria: final records can include `case_group`, `recommended_team`, `conversation_summary`, `intake_session_id`, and `intake_audit` without breaking older records or existing tests.
  - Test command: `pytest tests/unit/test_triage_schema.py tests/unit/test_local_case_repository.py`

- [X] T024 [US2] Persist optional intake fields through repositories in `app/services/case_repository.py`, `app/services/local_case_repository.py`, and `app/services/cosmos_case_repository.py`
  - Dependencies: T023
  - Acceptance criteria: local and Cosmos repository interfaces accept optional intake metadata; existing create/get/list_recent behavior remains compatible when fields are absent.
  - Test command: `pytest tests/unit/test_local_case_repository.py tests/unit/test_case_snapshot_cache.py tests/integration/test_cases_api.py`

- [X] T025 [US2] Implement case creation and escalation path in `app/services/intake_orchestrator.py`
  - Dependencies: T017, T023, T024
  - Acceptance criteria: `create_case` and `escalate_human_review` build a `CrisisCase` from session state, apply existing `apply_safety_rules()`, save via existing case repository, set final case ID/status, and return created case in `IntakeResponse`.
  - Test command: `pytest tests/unit/test_intake_orchestrator.py tests/integration/test_intake_api.py`

- [X] T026 [US2] Enforce deterministic guardrail overrides after provider decisions in `app/services/intake_orchestrator.py`
  - Dependencies: T008, T025
  - Acceptance criteria: RED risk cannot be downgraded; low confidence, missing location, self-harm, severe distress, contradictions, and unclear-after-repeat require human review; safe response text never says rescue was dispatched.
  - Test command: `pytest tests/unit/test_intake_guardrails.py tests/unit/test_intake_orchestrator.py`

**Checkpoint**: US2 RED and follow-up-limit escalation works independently and creates operator-visible cases.

---

## Phase 5: User Story 3 - Categorize Cases for the Right Response Group (Priority: P2)

**Goal**: Final cases include one operational group and recommended team with explainable mapping.

**Independent Test**: Submit representative transcripts for each group and verify expected group/team and reason.

### Tests for User Story 3

- [X] T027 [P] [US3] Add operational grouping integration tests in `tests/integration/test_intake_api.py`
  - Dependencies: T018, T025
  - Acceptance criteria: flood/trapped, medical symptom, fire, public danger, tourist trouble, utility damage, shelter need, self-harm, and unclear cases map to expected group/team.
  - Test command: `pytest tests/integration/test_intake_api.py`

### Implementation for User Story 3

- [X] T028 [US3] Apply grouping corrections to provider decisions in `app/services/intake_orchestrator.py`
  - Dependencies: T010, T025
  - Acceptance criteria: rule-based grouping corrects or fills model output, every final case has exactly one group, and unknown cases become `unknown_human_review` with reason.
  - Test command: `pytest tests/unit/test_case_grouping_service.py tests/unit/test_intake_orchestrator.py`

- [X] T029 [US3] Include group/team and conversation summary in cached case output from `app/models/case.py` and `app/services/case_snapshot_cache.py`
  - Dependencies: T023, T024
  - Acceptance criteria: `/api/cases/recent-cached` returns older records unchanged and newer records with optional `case_group`, `recommended_team`, and `conversation_summary`.
  - Test command: `pytest tests/integration/test_cases_api.py tests/unit/test_case_snapshot_cache.py`

**Checkpoint**: US3 cases are routable by operational group without breaking older case records.

---

## Phase 6: User Story 4 - Use Conversation Intake in Phone Calls (Priority: P2)

**Goal**: Twilio/local audio committed transcripts can use the intake orchestrator when explicitly enabled, while existing routes and default behavior remain unchanged.

**Independent Test**: With `ENABLE_MULTI_TURN_INTAKE=false`, simulated Twilio media flow still emits existing `triage.case.created`; with `true`, incomplete transcript emits `intake.followup` and high-risk transcript emits `triage.case.created`.

### Tests for User Story 4

- [X] T030 [P] [US4] Add disabled-flag regression test in `tests/unit/test_audio_session_processor.py`
  - Dependencies: T001
  - Acceptance criteria: with `ENABLE_MULTI_TURN_INTAKE=false`, `AudioSessionProcessor` uses the existing direct provider-to-case path and payload shape.
  - Test command: `pytest tests/unit/test_audio_session_processor.py`

- [X] T031 [P] [US4] Add enabled intake processor tests in `tests/unit/test_audio_session_processor.py`
  - Dependencies: T017, T025
  - Acceptance criteria: enabled path routes transcript through orchestrator, emits `intake.followup` for ask-followup, and emits `triage.case.created` for create/escalate.
  - Test command: `pytest tests/unit/test_audio_session_processor.py`

- [X] T032 [P] [US4] Add simulated Twilio multi-turn integration tests in `tests/integration/test_twilio_media_flow.py`
  - Dependencies: T031
  - Acceptance criteria: route paths remain `/api/telephony/twilio/incoming-call` and `/ws/telephony/twilio/{call_id}`; no Twilio credentials required; follow-up payload includes response text and source/call metadata.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py`

### Implementation for User Story 4

- [X] T033 [US4] Inject intake orchestrator behind feature flag in `app/services/audio_session_processor.py`
  - Dependencies: T017, T025, T030, T031
  - Acceptance criteria: direct triage path remains default; enabled path calls orchestrator after provider transcript; no Twilio route paths change; no TTS audio generated.
  - Test command: `pytest tests/unit/test_audio_session_processor.py tests/integration/test_mock_local_mic_flow.py tests/integration/test_twilio_media_flow.py`

- [X] T034 [US4] Include `intake.followup` payload contract fields in `app/services/audio_session_processor.py`
  - Dependencies: T033
  - Acceptance criteria: follow-up payload includes `type`, `session_id`, `transcript`, `action`, `response_text`, `partial_state`, `case_group`, `recommended_team`, `triage_level`, `human_review_required`, `missing_fields`, `reason`, `guardrail_warnings`, `source_input_mode`, and `call_metadata` when available.
  - Test command: `pytest tests/unit/test_audio_session_processor.py tests/integration/test_twilio_media_flow.py`

**Checkpoint**: US4 can be enabled locally without disturbing the deployed default Twilio behavior.

---

## Phase 7: User Story 5 - Review Conversation Context on Dashboards (Priority: P3)

**Goal**: Operators can see follow-up decisions, collected fields, conversation context, group/team, and conversation summaries in the debug console and cases dashboard.

**Independent Test**: Run a manual intake follow-up and verify `/voice-debug` shows action, response text, partial state, group/team, missing fields, and warnings; create a case and verify `/cases` shows group/team and summary.

### Tests for User Story 5

- [X] T035 [P] [US5] Add voice debug intake rendering tests in `frontend/tests/voice-debug-console.test.tsx`
  - Dependencies: T020, T034
  - Acceptance criteria: test renders `intake.followup`, response text, action, partial collected fields, group/team, missing fields, and guardrail warnings.
  - Test command: `cd frontend && npm test -- voice-debug-console.test.tsx`

- [X] T036 [P] [US5] Add cases dashboard group rendering tests in `frontend/tests/cases-dashboard.test.tsx`
  - Dependencies: T029
  - Acceptance criteria: test renders `case_group`, `recommended_team`, and `conversation_summary`; older records without these fields still render.
  - Test command: `cd frontend && npm test -- cases-dashboard.test.tsx`

### Implementation for User Story 5

- [X] T037 [US5] Extend frontend intake and case types in `frontend/types/triage.ts`
  - Dependencies: T004, T023, T034
  - Acceptance criteria: TypeScript types include `IntakeResponse`, `IntakeDecision` payload fields, `intake.followup`, optional case group/team/summary/audit fields, and remain compatible with existing triage payloads.
  - Test command: `cd frontend && npm test`

- [X] T038 [US5] Update voice debug console for intake events in `frontend/components/voice/VoiceDebugConsole.tsx`
  - Dependencies: T020, T035, T037
  - Acceptance criteria: console shows conversation turns, response text/next question, action, partial fields, case group, recommended team, missing fields, and guardrail warnings; existing `triage.case.created` and manual one-shot triage still work.
  - Test command: `cd frontend && npm test -- voice-debug-console.test.tsx`

- [X] T039 [US5] Update cases dashboard group display in `frontend/components/cases/CasesDashboard.tsx`
  - Dependencies: T029, T036, T037
  - Acceptance criteria: dashboard shows group, recommended team, and conversation summary when present and gracefully renders blanks for older cached records.
  - Test command: `cd frontend && npm test -- cases-dashboard.test.tsx`

**Checkpoint**: US5 operator views explain intake decisions and preserve older dashboard behavior.

---

## Phase 8: Polish and Cross-Cutting Verification

**Purpose**: Documentation, regression, build, and rollout readiness.

- [X] T040 [P] Update README multi-turn intake docs in `README.md`
  - Dependencies: T018, T033, T038, T039
  - Acceptance criteria: documents manual intake endpoint, feature flag, default disabled Twilio behavior, local test steps, no TTS/SMS/ACS/dispatch scope, and Azure rollout command for enabling after review.
  - Test command: `rg -n "multi-turn|ENABLE_MULTI_TURN_INTAKE|/api/intake/from-transcript|TTS|SMS|ACS" README.md`

- [X] T041 [P] Update quickstart with implemented test commands in `specs/005-multi-turn-intake/quickstart.md`
  - Dependencies: T018, T033, T038
  - Acceptance criteria: quickstart commands match final test file names and note that Azure deployment remains disabled until reviewed.
  - Test command: `rg -n "pytest|npm test|ENABLE_MULTI_TURN_INTAKE" specs/005-multi-turn-intake/quickstart.md`

- [X] T042 Run backend compile and full pytest regression for `app/`, `scripts/`, and `tests/`
  - Dependencies: T001-T041
  - Acceptance criteria: backend compiles and full pytest suite passes without Azure/Twilio credentials.
  - Test command: `python -m compileall app scripts; pytest`

- [X] T043 Run frontend test and static build regression for `frontend/`
  - Dependencies: T037-T039
  - Acceptance criteria: frontend unit tests pass and static export build succeeds.
  - Test command: `cd frontend; npm test; npm run build`

- [X] T044 Validate no forbidden scope or route regressions in `app/api/routes_twilio.py`, `app/services/audio_session_processor.py`, and `README.md`
  - Dependencies: T042, T043
  - Acceptance criteria: Twilio route paths unchanged; no TTS audio, SMS, ACS production behavior, emergency dispatch, Azure Speech/OpenAI enabling, Cosmos resource setup, or committed secrets added.
  - Test command: `rg -n "dispatch|SMS|send_sms|TextToSpeech|ACS|AZURE_OPENAI_API_KEY|COSMOS_DB_KEY" app frontend README.md .env.example`

---

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 setup has no dependencies.
- Phase 2 foundational depends on Phase 1 settings and model tasks where noted.
- US1 depends on Phase 2 and is the MVP.
- US2 depends on US1 orchestrator/route and repository-compatible case extensions.
- US3 depends on grouping and case creation from US2.
- US4 depends on US1/US2 orchestrator behavior and is gated by `ENABLE_MULTI_TURN_INTAKE`.
- US5 depends on backend/API payload shape and case snapshot fields.
- Polish depends on selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: starts after foundational tasks; no dependency on other stories.
- **US2 (P1)**: depends on US1 orchestrator and route; can implement RED behavior before frontend.
- **US3 (P2)**: depends on grouping service and final case creation; independently testable through API samples.
- **US4 (P2)**: depends on orchestrator and case creation; route paths must remain unchanged.
- **US5 (P3)**: depends on response/case field contracts from US1-US4.

### Parallel Opportunities

- T002 and T003 can run in parallel with backend settings.
- T004-T011 can be split by file after T001.
- T012 and T013 can be written in parallel before orchestrator implementation.
- T021, T022, and T027 can be written in parallel once the route contract exists.
- T030-T032 can be written in parallel for the audio processor and Twilio regression tests.
- T035 and T036 can be written in parallel before frontend implementation.
- T040 and T041 can be updated in parallel during final documentation.

---

## Parallel Execution Examples

### User Story 1

```text
Task: "Add intake route contract tests in tests/integration/test_intake_api.py"
Task: "Add missing-field orchestration tests in tests/unit/test_intake_orchestrator.py"
Task: "Add provider fallback tests in tests/unit/test_intake_provider.py"
```

### User Story 2

```text
Task: "Add RED escalation integration tests in tests/integration/test_intake_api.py"
Task: "Add max-followup human-review tests in tests/unit/test_intake_orchestrator.py"
```

### User Story 5

```text
Task: "Add voice debug intake rendering tests in frontend/tests/voice-debug-console.test.tsx"
Task: "Add cases dashboard group rendering tests in frontend/tests/cases-dashboard.test.tsx"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 through `POST /api/intake/from-transcript`.
3. Validate manual incomplete flood transcript returns `ask_followup` and no case.
4. Preserve existing `/api/triage/from-transcript` tests before moving on.

### Safety Increment

1. Add US2 RED escalation and max-followup case creation.
2. Confirm high-risk Thai sample creates/escalates RED with human review.
3. Confirm no response claims dispatch, diagnosis, closure, or rejection.

### Telephony and UI Increment

1. Add US4 behind `ENABLE_MULTI_TURN_INTAKE=false` default.
2. Add US5 dashboard/debug display.
3. Run full backend and frontend gates before any Azure rollout.

### Final Gates

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

Do not commit secrets. Do not enable Azure Speech/OpenAI, Cosmos DB, ACS, SMS, TTS audio, or emergency dispatch in this feature.

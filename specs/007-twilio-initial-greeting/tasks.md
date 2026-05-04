# Tasks: Twilio Initial Greeting

**Input**: Design documents from `specs/007-twilio-initial-greeting/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Tests**: Required. Automated tests must not require real Azure Speech or Twilio credentials.

**Organization**: Tasks are ordered by implementation dependency while preserving independent user-story validation. Each task includes dependencies, acceptance criteria, and a test command.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable after dependencies are met
- **[Story]**: Maps to `spec.md` user stories
- **Deps**: Task IDs that must be completed first
- **Acceptance**: Concrete completion criteria
- **Test**: Verification command for the task

---

## Phase 1: Config / Env Settings

**Purpose**: Add opt-in greeting configuration while keeping greeting disabled by default.

- [x] T001 [P] [US2] Add disabled-by-default initial greeting config tests in `tests/unit/test_telephony_config.py` (Deps: none; Acceptance: tests assert `enable_twilio_initial_greeting=false`, default greeting text exists, default profile is `greeting`, fallback say is false, greeting rate/pitch defaults parse; Test: `pytest tests\unit\test_telephony_config.py`)
- [x] T002 [US2] Add initial greeting and greeting prosody settings in `app/core/config.py` and `.env.example` (Deps: T001; Acceptance: env vars `ENABLE_TWILIO_INITIAL_GREETING`, `TWILIO_INITIAL_GREETING_TEXT`, `TWILIO_INITIAL_GREETING_PROFILE`, `TWILIO_INITIAL_GREETING_FALLBACK_SAY`, `TTS_RATE_GREETING`, and `TTS_PITCH_GREETING` are supported with safe defaults and no secret values; Test: `pytest tests\unit\test_telephony_config.py`)

**Checkpoint**: Greeting configuration is available, disabled by default, and testable without Azure credentials.

---

## Phase 2: TTS Greeting Profile

**Purpose**: Extend existing SSML profile handling with a dedicated greeting profile.

- [x] T003 [P] [US4] Add greeting profile model and validation tests in `tests/unit/test_azure_speech_tts_service.py` and `tests/unit/test_tts_models.py` (Deps: T002; Acceptance: tests cover `TTSProfile.GREETING`, greeting SSML rate `-5%`, greeting pitch `0%`, and unsafe greeting sanitization; Test: `pytest tests\unit\test_azure_speech_tts_service.py tests\unit\test_tts_models.py`)
- [x] T004 [US4] Add `TTSProfile.GREETING` in `app/models/tts.py` and greeting prosody mapping in `app/services/azure_speech_tts_service.py` (Deps: T003; Acceptance: `profile="greeting"` builds valid SSML using `TTS_RATE_GREETING`, `TTS_PITCH_GREETING`, and existing `TTS_VOLUME`, while existing profiles remain unchanged; Test: `pytest tests\unit\test_azure_speech_tts_service.py tests\unit\test_tts_models.py`)

**Checkpoint**: Greeting profile works through the existing TTS service and safety pipeline.

---

## Phase 3: Reusable Twilio TTS Media Sender Helper

**Purpose**: Remove duplication risk by routing both response speak-back and initial greeting through one outbound media sender helper.

- [x] T005 [P] [US1] Add reusable TTS media sender helper tests in `tests/unit/test_twilio_routes.py` (Deps: T004; Acceptance: tests cover helper sending Twilio media chunks and mark events, missing `streamSid`, unconfigured TTS, and TTS failure without raising; Test: `pytest tests\unit\test_twilio_routes.py`)
- [x] T006 [US1] Refactor Twilio TTS outbound sending into `_send_tts_media(...)` in `app/api/routes_twilio.py` (Deps: T005; Acceptance: helper accepts `websocket`, `settings`, `stream_sid`, `text`, `profile`, `call_id`, `session_id`, `purpose`, and `mark_name`; existing `_maybe_send_tts_response` uses helper and preserves current response speak-back behavior; Test: `pytest tests\unit\test_twilio_routes.py tests\integration\test_twilio_media_flow.py`)

**Checkpoint**: Existing response speak-back still works through the shared sender.

---

## Phase 4: Twilio WebSocket Start-Event Greeting

**Purpose**: Speak one greeting after Twilio `start` event, then continue normal listening.

- [x] T007 [P] [US1] Add integration test for enabled initial greeting on Twilio start in `tests/integration/test_twilio_media_flow.py` (Deps: T006; Acceptance: mocked TTS receives greeting text/profile, WebSocket sends `session.started`, one or more Twilio `media` events, and a `mark` named `narayana_initial_greeting`; Test: `pytest tests\integration\test_twilio_media_flow.py`)
- [x] T008 [P] [US2] Add integration regression test for greeting disabled start behavior in `tests/integration/test_twilio_media_flow.py` (Deps: T006; Acceptance: default Twilio start emits no initial greeting `media` or `mark` and existing simulated media flow still creates/handles cases as before; Test: `pytest tests\integration\test_twilio_media_flow.py`)
- [x] T009 [P] [US3] Add greeting failure continuation test in `tests/unit/test_twilio_routes.py` or `tests/integration/test_twilio_media_flow.py` (Deps: T006; Acceptance: mocked TTS failure during greeting does not close the WebSocket and caller media after start can still be processed; Test: `pytest tests\unit\test_twilio_routes.py tests\integration\test_twilio_media_flow.py`)
- [x] T010 [US1] Invoke initial greeting once from Twilio `start` handling in `app/api/routes_twilio.py` (Deps: T007, T008, T009; Acceptance: when enabled and `streamSid` exists, greeting sends media chunks and `narayana_initial_greeting` mark exactly once per call after `session.started`; route paths remain unchanged; Test: `pytest tests\integration\test_twilio_media_flow.py`)
- [x] T011 [US3] Add `greeting.started`, `greeting.completed`, and `greeting.failed` logging in `app/api/routes_twilio.py` (Deps: T010; Acceptance: logs include session/call/stream IDs, chunk count, and duration estimate where available, and never include secrets or audio payloads; Test: `pytest tests\unit\test_twilio_routes.py tests\integration\test_twilio_media_flow.py`)

**Checkpoint**: Caller can hear the first greeting when enabled; disabled and failure modes continue listening.

---

## Phase 5: `/api/tts/test` Profile Support

**Purpose**: Let developers validate the greeting profile through the existing TTS readiness endpoint.

- [x] T012 [P] [US5] Add TTS route test for `profile="greeting"` in `tests/unit/test_tts_routes.py` (Deps: T004; Acceptance: route accepts greeting profile, returns profile metadata, and does not return raw payloads; Test: `pytest tests\unit\test_tts_routes.py`)
- [x] T013 [US5] Ensure `/api/tts/test` passes greeting profile through in `app/api/routes_tts.py` (Deps: T012; Acceptance: request body with `profile="greeting"` returns `profile="greeting"` in metadata with configured/unconfigured behavior unchanged; Test: `pytest tests\unit\test_tts_routes.py`)

**Checkpoint**: Greeting profile can be checked manually without placing a Twilio call.

---

## Phase 6: Health Output Update

**Purpose**: Expose greeting readiness without exposing secrets.

- [x] T014 [P] [US5] Add health response tests for greeting fields in `tests/integration/test_gateway_demo_smoke.py` or `tests/unit/test_triage_schema.py` (Deps: T002; Acceptance: tests assert greeting enabled flag, greeting text configured flag, and greeting profile are present and contain no secret values; Test: `pytest tests\integration\test_gateway_demo_smoke.py tests\unit\test_triage_schema.py`)
- [x] T015 [US5] Add greeting health fields to `app/models/triage.py` and `app/api/routes_audio.py` (Deps: T014; Acceptance: `GET /api/health/azure` includes `twilio_initial_greeting_enabled`, `twilio_initial_greeting_text_configured`, and `twilio_initial_greeting_profile`; Test: `pytest tests\integration\test_gateway_demo_smoke.py tests\unit\test_triage_schema.py`)

**Checkpoint**: Operators can verify greeting configuration through health output.

---

## Phase 7: Safety and Regression Tests

**Purpose**: Ensure new greeting behavior does not weaken the existing Twilio and TTS safety contract.

- [x] T016 [P] [US4] Add unsafe/overlong greeting sanitization tests in `tests/unit/test_azure_speech_tts_service.py` (Deps: T004; Acceptance: unsafe dispatch/official-hotline-like greeting text is replaced or shortened before SSML synthesis; Test: `pytest tests\unit\test_azure_speech_tts_service.py`)
- [x] T017 [P] [US2] Run existing Twilio response speak-back regression in `tests/integration/test_twilio_media_flow.py` and adjust only if additive metadata changes are required (Deps: T006, T010; Acceptance: existing response `media` and `mark` tests pass with greeting disabled by default; Test: `pytest tests\integration\test_twilio_media_flow.py`)
- [x] T018 [P] [US3] Add missing `streamSid` greeting skip test in `tests/unit/test_twilio_routes.py` (Deps: T006; Acceptance: missing stream identifier logs/skips greeting and does not send media or raise; Test: `pytest tests\unit\test_twilio_routes.py`)

**Checkpoint**: Greeting safety and failure behavior are covered without real credentials.

---

## Phase 8: README Update

**Purpose**: Document how to enable, test, and troubleshoot first greeting without secrets.

- [x] T019 [P] [US5] Update `.env.example` with greeting env vars and SSML greeting rate/pitch in `.env.example` (Deps: T002; Acceptance: example includes greeting settings, keeps disabled default, and contains no secrets; Test: `git diff -- .env.example`)
- [x] T020 [US5] Update initial greeting documentation in `README.md` (Deps: T013, T015; Acceptance: docs include enablement env vars, recommended Thai greeting, `/api/tts/test` greeting profile example, Twilio call steps, log names `greeting.started` and `greeting.completed`, and restrictions against ACS/SMS/dispatch/Azure OpenAI; Test: `Select-String -Path README.md -Pattern 'ENABLE_TWILIO_INITIAL_GREETING','greeting.started','profile\":\"greeting'`)

**Checkpoint**: Demo operators have a safe enablement and troubleshooting path.

---

## Phase 9: Final Verification

**Purpose**: Validate the complete feature and confirm no secrets are staged.

- [x] T021 [US1] Run Python compile gate for backend and scripts (Deps: T001-T020; Acceptance: compile completes without errors; Test: `python -m compileall app scripts`)
- [x] T022 [US1] Run full backend test suite (Deps: T021; Acceptance: all non-credential tests pass; Azure manual test may remain skipped unless env is explicitly configured; Test: `pytest`)
- [x] T023 [US2] Run frontend tests unchanged (Deps: T021; Acceptance: existing voice debug/dashboard tests pass; Test: `cd frontend && npm test`)
- [x] T024 [US2] Run frontend static build unchanged (Deps: T023; Acceptance: Next.js static export build completes; Test: `cd frontend && npm run build`)
- [x] T025 [US5] Verify git status excludes `.env.azure.local` and no secrets are staged (Deps: T021-T024; Acceptance: `.env.azure.local` is ignored, not staged, and no Azure Speech key appears in tracked diffs; Test: `git status --short; git check-ignore -v .env.azure.local; git diff --cached`)

**Checkpoint**: Feature is ready to commit and deploy through the existing GHCR/Container Apps path.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Config / Env Settings**: No dependencies.
- **Phase 2: TTS Greeting Profile**: Depends on Phase 1.
- **Phase 3: Reusable Twilio TTS Media Sender Helper**: Depends on Phase 2.
- **Phase 4: Twilio WebSocket Start-Event Greeting**: Depends on Phase 3.
- **Phase 5: `/api/tts/test` Profile Support**: Depends on Phase 2 and can run alongside Phase 4 after T004.
- **Phase 6: Health Output Update**: Depends on Phase 1 and can run alongside Phases 4-5.
- **Phase 7: Safety and Regression Tests**: Depends on relevant Phase 2-4 work.
- **Phase 8: README Update**: Depends on implemented env, health, and TTS route behavior.
- **Phase 9: Final Verification**: Depends on all implementation and docs tasks.

### User Story Dependencies

- **US1 Caller Hears Narayana First (P1)**: Requires config, greeting profile, shared media sender, and start-event integration.
- **US2 Preserve Current Call Behavior by Default (P1)**: Can validate immediately after config and start-event integration; must remain true throughout all phases.
- **US3 Continue Listening When Greeting Fails (P1)**: Depends on shared sender and start-event integration.
- **US4 Keep Greeting Safe and Configurable (P2)**: Depends on profile and sanitizer behavior.
- **US5 Troubleshoot Greeting Playback (P3)**: Depends on route/health/doc visibility and logging.

### Parallel Opportunities

- T001 and documentation review can begin immediately.
- T003, T012, and T014 can be developed in parallel after T002.
- T007, T008, and T009 can be written in parallel after T006.
- T016, T017, and T018 can run in parallel after their dependencies are met.
- T019 and T020 can run in parallel with final focused tests once behavior is stable.

---

## Parallel Examples

### After Config Lands

```text
Task: "T003 Add greeting profile model and validation tests"
Task: "T012 Add TTS route test for profile=\"greeting\""
Task: "T014 Add health response tests for greeting fields"
```

### After Shared Sender Lands

```text
Task: "T007 Add integration test for enabled initial greeting"
Task: "T008 Add integration regression test for greeting disabled"
Task: "T009 Add greeting failure continuation test"
```

---

## Implementation Strategy

### MVP First

1. Complete T001-T006 to add config, greeting profile, and shared sender.
2. Complete T007-T010 to speak the greeting once after Twilio `start`.
3. Validate with `pytest tests\integration\test_twilio_media_flow.py tests\unit\test_twilio_routes.py`.
4. Stop and demo with mocked TTS before adding broader docs/health polish.

### Incremental Delivery

1. Add defaults and profile support with focused unit tests.
2. Refactor response speak-back through the shared sender and keep existing tests green.
3. Add initial greeting start-event behavior.
4. Add health/TTS route visibility and README instructions.
5. Run full backend/frontend gates before commit.

### Guardrails

- Do not change Twilio route paths.
- Do not require Azure credentials in tests.
- Do not print or commit secrets.
- Do not commit `.env.azure.local`.
- Keep `ENABLE_TWILIO_INITIAL_GREETING=false` by default.
- Do not enable Azure OpenAI.
- Do not implement ACS, SMS, or emergency dispatch.

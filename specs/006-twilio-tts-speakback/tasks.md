# Tasks: Optional Twilio TTS Speak-Back

**Input**: Design documents from `specs/006-twilio-tts-speakback/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests are required by the feature specification. Unit and integration tests must not require Azure or Twilio credentials.

**Organization**: Tasks are grouped by setup/foundation and then by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: User story label from `spec.md`. Setup, foundational, and polish tasks do not use story labels.
- **File paths**: Every task line includes the exact target file path or paths.

---

## Phase 1: Setup (Shared Configuration)

**Purpose**: Add feature flags and environment examples while preserving default-disabled behavior.

- [X] T001 Add TTS feature settings in `app/core/config.py`
  - Dependencies: None
  - Acceptance criteria: `enable_twilio_tts_response` defaults to `False`; `azure_speech_voice` defaults to `th-TH-PremwadeeNeural`; `tts_max_chars` defaults to `220`; `tts_output_format` defaults to `mulaw_8khz`.
  - Test command: `pytest tests/unit/test_telephony_config.py`

- [X] T002 [P] Add TTS environment examples in `.env.example`
  - Dependencies: None
  - Acceptance criteria: `.env.example` includes `ENABLE_TWILIO_TTS_RESPONSE=false`, `AZURE_SPEECH_VOICE=th-TH-PremwadeeNeural`, `TTS_MAX_CHARS=220`, and `TTS_OUTPUT_FORMAT=mulaw_8khz` without secrets.
  - Test command: `rg -n "ENABLE_TWILIO_TTS_RESPONSE|AZURE_SPEECH_VOICE|TTS_MAX_CHARS|TTS_OUTPUT_FORMAT" .env.example`

- [X] T003 [P] Add frontend TTS display contract types in `frontend/types/triage.ts`
  - Dependencies: None
  - Acceptance criteria: TypeScript types can represent health TTS fields, optional TTS warnings, and Twilio speak-back metadata without breaking older payloads.
  - Test command: `cd frontend && npm test -- voice-debug-console.test.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared models, outbound Twilio audio helpers, and the Azure Speech TTS service before story-specific route integration.

**Critical**: User story work depends on these models and helpers.

- [X] T004 [P] Create TTS Pydantic models in `app/models/tts.py`
  - Dependencies: T001
  - Acceptance criteria: Models cover `TTSRequest`, `TTSResult`, public test response metadata, warnings, missing variables, and exclude raw payloads from public responses.
  - Test command: `pytest tests/unit/test_tts_models.py`

- [X] T005 [P] Add TTS model validation tests in `tests/unit/test_tts_models.py`
  - Dependencies: T004
  - Acceptance criteria: Tests cover blank text rejection, public response without payloads, configured false metadata, and payload count/byte fields.
  - Test command: `pytest tests/unit/test_tts_models.py`

- [X] T006 [P] Add outbound Twilio helper tests in `tests/unit/test_twilio_audio_service.py`
  - Dependencies: None
  - Acceptance criteria: Tests cover PCM16 to mu-law conversion, base64 chunking, media event shape, mark event shape, and duration estimate without changing inbound decode tests.
  - Test command: `pytest tests/unit/test_twilio_audio_service.py`

- [X] T007 Implement outbound Twilio audio helpers in `app/services/twilio_audio_service.py`
  - Dependencies: T006
  - Acceptance criteria: Adds `encode_pcm16_to_mulaw_base64()`, `chunk_mulaw_audio_for_twilio()`, `build_twilio_media_event()`, `build_twilio_mark_event()`, and `estimate_audio_duration_ms()` while preserving existing inbound Twilio decode behavior.
  - Test command: `pytest tests/unit/test_twilio_audio_service.py`

- [X] T008 [P] Add Azure Speech TTS service tests in `tests/unit/test_azure_speech_tts_service.py`
  - Dependencies: T001, T004
  - Acceptance criteria: Tests cover configured/unconfigured status, missing variable reporting, safe text sanitization hook, max character handling, empty audio warnings, and mocked synthesis metadata without Azure credentials.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py`

- [X] T009 Implement Azure Speech TTS service skeleton and configuration checks in `app/services/azure_speech_tts_service.py`
  - Dependencies: T004, T008
  - Acceptance criteria: Service reports health/configured status from existing Azure Speech key/region, returns safe unconfigured results, never logs secrets, and exposes a `synthesize_twilio_mulaw()` method returning `TTSResult`.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py`

- [X] T010 Implement Azure Speech synthesis and PCM-to-mu-law fallback in `app/services/azure_speech_tts_service.py`
  - Dependencies: T007, T009
  - Acceptance criteria: Service requests Azure Speech Thai voice output, prefers raw 8 kHz mu-law when available, falls back to PCM conversion through Twilio helpers, returns chunk payloads, total bytes, duration estimate, and non-secret warnings.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py`

- [X] T011 [P] Add no-payload logging guard test in `tests/unit/test_azure_speech_tts_service.py`
  - Dependencies: T009
  - Acceptance criteria: Tests assert warnings/log metadata do not include raw base64 audio payloads or Azure secrets.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py`

**Checkpoint**: Shared TTS configuration, models, service, and Twilio outbound helpers are ready.

---

## Phase 3: User Story 1 - Caller Hears Follow-Up Question (Priority: P1) MVP

**Goal**: With multi-turn intake and speak-back enabled, a Twilio WebSocket response containing `response_text` sends normal JSON debug output first, then Twilio media chunks, then a mark event.

**Independent Test**: Run the simulated Twilio media flow with mocked TTS enabled and verify the WebSocket emits `intake.followup` or `triage.case.created`, one or more Twilio `media` events, and a final `mark` event.

### Tests for User Story 1

- [X] T012 [P] [US1] Add mocked speak-back integration test in `tests/integration/test_twilio_media_flow.py`
  - Dependencies: T007, T009
  - Acceptance criteria: Test enables `ENABLE_MULTI_TURN_INTAKE=true` and `ENABLE_TWILIO_TTS_RESPONSE=true`, mocks TTS output, sends simulated Twilio media, and asserts JSON payload arrives before Twilio media and mark events.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k speakback`

- [X] T013 [P] [US1] Add Twilio streamSid capture regression test in `tests/integration/test_twilio_media_flow.py`
  - Dependencies: T012
  - Acceptance criteria: Test asserts outbound media uses the `streamSid` from the Twilio `start` event and skips speak-back safely when `streamSid` is missing.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k streamsid`

- [X] T014 [P] [US1] Add TTS failure continuation test in `tests/integration/test_twilio_media_flow.py`
  - Dependencies: T012
  - Acceptance criteria: Test forces TTS service failure and verifies normal JSON debug/case payload is still sent and the WebSocket does not crash.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k tts_failure`

### Implementation for User Story 1

- [X] T015 [US1] Capture Twilio `streamSid` in `app/api/routes_twilio.py`
  - Dependencies: T013
  - Acceptance criteria: WebSocket stores the stream ID from the `start` event for the call session and keeps existing route path `/ws/telephony/twilio/{call_id}` unchanged.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k streamsid`

- [X] T016 [US1] Add speak-back gating and service wiring in `app/api/routes_twilio.py`
  - Dependencies: T010, T015
  - Acceptance criteria: Speak-back is attempted only when enabled, Twilio session has `streamSid`, `response_text` is non-empty, and Azure Speech TTS service is configured; no attempt occurs for disabled/unconfigured cases.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k speakback`

- [X] T017 [US1] Send Twilio media chunks and mark event in `app/api/routes_twilio.py`
  - Dependencies: T016
  - Acceptance criteria: Normal JSON payload is sent first; synthesized chunks are sent as Twilio media events; a mark event follows successful media playback send.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k speakback`

- [X] T018 [US1] Add non-secret TTS operational logs in `app/api/routes_twilio.py`
  - Dependencies: T017
  - Acceptance criteria: Logs include `tts.started`, `tts.completed`, `tts.failed`, stream ID, chunk count, text length, and duration estimate without secrets or audio payloads.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k tts`

**Checkpoint**: User Story 1 is independently functional with mocked TTS and Twilio media output.

---

## Phase 4: User Story 2 - Preserve Safe Defaults and Existing Calls (Priority: P1)

**Goal**: Existing Twilio/local microphone demos and tests keep working with speak-back disabled and no Azure credentials.

**Independent Test**: Run existing Twilio simulated media tests and local mic tests with default settings and verify no outbound Twilio media or Azure TTS call is attempted.

### Tests for User Story 2

- [X] T019 [P] [US2] Add default-disabled config regression test in `tests/unit/test_telephony_config.py`
  - Dependencies: T001
  - Acceptance criteria: Test asserts `ENABLE_TWILIO_TTS_RESPONSE` defaults to false and Azure Speech TTS is not required for settings construction.
  - Test command: `pytest tests/unit/test_telephony_config.py`

- [X] T020 [P] [US2] Add disabled speak-back Twilio regression test in `tests/integration/test_twilio_media_flow.py`
  - Dependencies: T017
  - Acceptance criteria: Test runs simulated Twilio flow with default settings and asserts no Twilio outbound media or mark events are sent.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py -k disabled`

- [X] T021 [P] [US2] Add local mic unaffected regression test in `tests/integration/test_mock_local_mic_flow.py`
  - Dependencies: T017
  - Acceptance criteria: Existing local mic mock flow passes without TTS settings, Twilio stream IDs, or Azure Speech credentials.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py`

### Implementation for User Story 2

- [X] T022 [US2] Harden disabled/unconfigured speak-back skips in `app/api/routes_twilio.py`
  - Dependencies: T019, T020
  - Acceptance criteria: Disabled, unconfigured, empty response text, missing stream ID, and non-Twilio cases continue normal JSON payload delivery without TTS calls.
  - Test command: `pytest tests/integration/test_twilio_media_flow.py tests/integration/test_mock_local_mic_flow.py`

- [X] T023 [US2] Preserve existing Twilio route behavior in `app/api/routes_twilio.py`
  - Dependencies: T022
  - Acceptance criteria: `POST /api/telephony/twilio/incoming-call` and `/ws/telephony/twilio/{call_id}` paths remain unchanged, existing TwiML and inbound media normalization tests still pass.
  - Test command: `pytest tests/unit/test_twilio_routes.py tests/integration/test_twilio_media_flow.py`

**Checkpoint**: User Story 2 confirms safe defaults and no regressions for current demos.

---

## Phase 5: User Story 3 - Validate Speech Synthesis Readiness (Priority: P2)

**Goal**: Developers can verify TTS readiness through `POST /api/tts/test` without placing a call and without receiving raw audio payloads.

**Independent Test**: Call `/api/tts/test` without Azure Speech credentials and receive `configured=false`, missing variables, selected voice, format, zero payload count, and no raw payloads.

### Tests for User Story 3

- [X] T024 [P] [US3] Add TTS route tests in `tests/unit/test_tts_routes.py`
  - Dependencies: T004, T009
  - Acceptance criteria: Tests cover unconfigured response, configured mocked response, blank text validation, no raw audio payloads, and voice override metadata.
  - Test command: `pytest tests/unit/test_tts_routes.py`

- [X] T025 [P] [US3] Add TTS route contract smoke test in `tests/integration/test_gateway_demo_smoke.py`
  - Dependencies: T024
  - Acceptance criteria: FastAPI app responds to `POST /api/tts/test` with contract metadata and no Azure credentials required.
  - Test command: `pytest tests/integration/test_gateway_demo_smoke.py`

### Implementation for User Story 3

- [X] T026 [US3] Implement `POST /api/tts/test` route in `app/api/routes_tts.py`
  - Dependencies: T024, T009
  - Acceptance criteria: Route accepts `TTSRequest`, returns metadata-only `TTSTestResponse`, reports missing Azure Speech variables when unconfigured, and never includes audio payloads.
  - Test command: `pytest tests/unit/test_tts_routes.py`

- [X] T027 [US3] Register TTS router in `app/main.py`
  - Dependencies: T026
  - Acceptance criteria: `/api/tts/test` is available through the FastAPI app without changing existing router registrations.
  - Test command: `pytest tests/unit/test_tts_routes.py tests/integration/test_gateway_demo_smoke.py`

- [X] T028 [US3] Add manual TTS endpoint contract docs in `specs/006-twilio-tts-speakback/contracts/tts-test-endpoint.md`
  - Dependencies: T026
  - Acceptance criteria: Contract remains aligned with implementation fields, unconfigured behavior, and no-payload rule.
  - Test command: `rg -n "payload_count|missing_variables|must not include raw audio" specs/006-twilio-tts-speakback/contracts/tts-test-endpoint.md`

**Checkpoint**: User Story 3 provides a safe readiness endpoint for demos.

---

## Phase 6: User Story 4 - Keep Spoken Guidance Safe (Priority: P2)

**Goal**: Spoken responses are sanitized before synthesis so callers do not hear dispatch claims, ambulance-arrival claims, diagnosis language, closure/rejection language, or overlong guidance.

**Independent Test**: Submit unsafe response text to the TTS service and verify the synthesized text is replaced or shortened before cloud synthesis is attempted.

### Tests for User Story 4

- [X] T029 [P] [US4] Add spoken safety sanitizer tests in `tests/unit/test_azure_speech_tts_service.py`
  - Dependencies: T009
  - Acceptance criteria: Tests cover Thai and English dispatch claims, ambulance-arrival claims, diagnosis wording, automatic closure/rejection wording, and overlong text.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py -k sanitize`

- [X] T030 [P] [US4] Add manual endpoint safety test in `tests/unit/test_tts_routes.py`
  - Dependencies: T024
  - Acceptance criteria: `/api/tts/test` applies spoken safety sanitization and does not echo unsafe text into response warnings.
  - Test command: `pytest tests/unit/test_tts_routes.py -k safety`

### Implementation for User Story 4

- [X] T031 [US4] Implement spoken response sanitization in `app/services/azure_speech_tts_service.py`
  - Dependencies: T029
  - Acceptance criteria: Unsafe dispatch, ambulance-arrival, diagnosis, close/reject, and overlong text is replaced or shortened with concise safe Thai review language before synthesis.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py -k sanitize`

- [X] T032 [US4] Enforce TTS max character behavior in `app/services/azure_speech_tts_service.py`
  - Dependencies: T031
  - Acceptance criteria: Service respects `tts_max_chars`, uses safe replacement when truncation would be unsafe, and records non-secret warning metadata.
  - Test command: `pytest tests/unit/test_azure_speech_tts_service.py`

**Checkpoint**: User Story 4 protects caller-facing spoken guidance.

---

## Phase 7: User Story 5 - Operate and Troubleshoot Demo Calls (Priority: P3)

**Goal**: Developers can see TTS readiness in health, inspect debug status in the frontend, and follow documentation to enable or test Twilio speak-back safely.

**Independent Test**: Run health and frontend tests, then follow README quickstart to verify health, `/api/tts/test`, and Twilio call setup steps.

### Tests for User Story 5

- [X] T033 [P] [US5] Add health field tests in `tests/integration/test_gateway_demo_smoke.py`
  - Dependencies: T001
  - Acceptance criteria: Health response includes `twilio_tts_response_enabled`, `azure_speech_tts_configured`, and `azure_speech_voice` with safe defaults.
  - Test command: `pytest tests/integration/test_gateway_demo_smoke.py -k health`

- [X] T034 [P] [US5] Add voice debug TTS display test in `frontend/tests/voice-debug-console.test.tsx`
  - Dependencies: T003
  - Acceptance criteria: Voice debug console renders response text, TTS enabled/configured status when present, and warnings without requiring browser audio playback.
  - Test command: `cd frontend && npm test -- voice-debug-console.test.tsx`

### Implementation for User Story 5

- [X] T035 [US5] Extend Azure health model in `app/models/triage.py`
  - Dependencies: T001, T033
  - Acceptance criteria: `AzureHealth` includes additive TTS fields while preserving all existing fields and response compatibility.
  - Test command: `pytest tests/integration/test_gateway_demo_smoke.py -k health`

- [X] T036 [US5] Populate TTS health fields in `app/api/routes_audio.py`
  - Dependencies: T035
  - Acceptance criteria: `/api/health/azure` reports speak-back enabled state, Azure Speech TTS configured state from key/region, and selected Azure Speech voice.
  - Test command: `pytest tests/integration/test_gateway_demo_smoke.py -k health`

- [X] T037 [US5] Update voice debug UI for TTS metadata in `frontend/components/voice/VoiceDebugConsole.tsx`
  - Dependencies: T003, T034
  - Acceptance criteria: `/voice-debug` shows response text, TTS warnings, and enabled/configured status when payloads expose them; older payloads render without errors.
  - Test command: `cd frontend && npm test -- voice-debug-console.test.tsx`

- [X] T038 [US5] Update README speak-back setup and troubleshooting in `README.md`
  - Dependencies: T026, T036, T037
  - Acceptance criteria: README explains default disabled behavior, required Azure Speech env vars, Twilio real-call test steps, `/api/health/azure`, `/api/tts/test`, log checks, cost warning, and out-of-scope items.
  - Test command: `rg -n "ENABLE_TWILIO_TTS_RESPONSE|/api/tts/test|cost|Twilio" README.md`

- [X] T039 [US5] Update quickstart validation steps in `specs/006-twilio-tts-speakback/quickstart.md`
  - Dependencies: T038
  - Acceptance criteria: Quickstart reflects final commands for disabled regression, mocked speak-back, manual TTS readiness, and real-call enablement.
  - Test command: `rg -n "ENABLE_TWILIO_TTS_RESPONSE|/api/tts/test|pytest" specs/006-twilio-tts-speakback/quickstart.md`

**Checkpoint**: User Story 5 supports safe operation and troubleshooting.

---

## Phase 8: Polish & Final Verification

**Purpose**: Validate the complete feature and ensure no prohibited scope or secrets were introduced.

- [X] T040 [P] Run backend compile verification for `app/` and `scripts/`
  - Dependencies: T001-T039
  - Acceptance criteria: Python files compile without syntax errors.
  - Test command: `python -m compileall app scripts`

- [X] T041 [P] Run full backend test suite in `tests/`
  - Dependencies: T001-T039
  - Acceptance criteria: All automated tests pass without Azure/Twilio credentials and existing Twilio inbound tests remain green.
  - Test command: `pytest`

- [X] T042 [P] Run frontend test suite in `frontend/`
  - Dependencies: T003, T034, T037
  - Acceptance criteria: Vitest tests pass with the voice debug TTS display update.
  - Test command: `cd frontend && npm test`

- [X] T043 [P] Run frontend static build in `frontend/`
  - Dependencies: T003, T034, T037
  - Acceptance criteria: Next.js static build succeeds for Azure Static Web Apps deployment compatibility.
  - Test command: `cd frontend && npm run build`

- [X] T044 Run final route and scope regression checks across `app/`, `tests/`, `README.md`, and `.env.example`
  - Dependencies: T040, T041, T042, T043
  - Acceptance criteria: Twilio route paths remain unchanged; TTS default remains disabled; no ACS production, SMS, emergency dispatch, Cosmos DB resource, raw audio payload logging, or committed secrets are introduced.
  - Test command: `rg -n "ENABLE_TWILIO_TTS_RESPONSE=false|/api/telephony/twilio/incoming-call|/ws/telephony/twilio" .env.example README.md app tests`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on TTS settings from Phase 1 and blocks user story implementation.
- **Phase 3 US1**: Depends on outbound Twilio helpers and Azure Speech TTS service.
- **Phase 4 US2**: Depends on Twilio route speak-back integration so regressions can verify disabled behavior.
- **Phase 5 US3**: Depends on TTS models and service.
- **Phase 6 US4**: Depends on TTS service and route tests.
- **Phase 7 US5**: Depends on health fields, endpoint behavior, and frontend type additions.
- **Phase 8 Polish**: Depends on all desired user stories.

### User Story Dependencies

- **US1 (P1)**: MVP speak-back path; start after Phase 2.
- **US2 (P1)**: Regression and safe defaults; start after US1 route integration is present.
- **US3 (P2)**: Manual readiness endpoint; can start after Phase 2 and run in parallel with US1 once TTS service exists.
- **US4 (P2)**: Spoken guidance safety; can start after TTS service skeleton exists.
- **US5 (P3)**: Health/UI/docs; can start after health models and endpoint contracts are understood, but README should be finalized after implementation.

### Within Each User Story

- Write tests before implementation tasks when the task group includes tests.
- Add/extend models before services.
- Add service helpers before WebSocket route integration.
- Preserve JSON debug payload behavior before sending outbound Twilio media events.
- Complete and test each story before relying on it in later stories.

---

## Parallel Opportunities

- T002 and T003 can run in parallel after T001 is understood.
- T004, T006, and T008 can be prepared in parallel because they target different model/service test files.
- T012, T013, and T014 can be drafted in parallel after foundational helpers exist.
- US3 route tests and US4 sanitizer tests can run in parallel after the TTS service skeleton exists.
- US5 health tests and frontend display tests can run in parallel.
- T040, T041, T042, and T043 are independent verification commands after implementation is complete.

## Parallel Example: User Story 1

```text
Task: "T012 [P] [US1] Add mocked speak-back integration test in tests/integration/test_twilio_media_flow.py"
Task: "T013 [P] [US1] Add Twilio streamSid capture regression test in tests/integration/test_twilio_media_flow.py"
Task: "T014 [P] [US1] Add TTS failure continuation test in tests/integration/test_twilio_media_flow.py"
```

## Parallel Example: User Story 5

```text
Task: "T033 [P] [US5] Add health field tests in tests/integration/test_gateway_demo_smoke.py"
Task: "T034 [P] [US5] Add voice debug TTS display test in frontend/tests/voice-debug-console.test.tsx"
```

---

## Implementation Strategy

### MVP First (US1 + Required Safety Defaults)

1. Complete Phase 1 and Phase 2.
2. Complete US1 mocked Twilio speak-back.
3. Complete US2 disabled/unconfigured regression checks.
4. Stop and validate `pytest tests/integration/test_twilio_media_flow.py` before adding endpoint/UI/docs work.

### Incremental Delivery

1. Shared TTS settings, models, helpers, and service.
2. Twilio speak-back route integration with mocked TTS.
3. Safe default and failure behavior.
4. Manual `/api/tts/test` readiness endpoint.
5. Spoken text safety hardening.
6. Health, debug UI, documentation.
7. Full final verification.

### Deployment Note

Keep `ENABLE_TWILIO_TTS_RESPONSE=false` by default. Enable real-call speak-back only after tests pass and Azure Speech credentials are configured in the target environment.

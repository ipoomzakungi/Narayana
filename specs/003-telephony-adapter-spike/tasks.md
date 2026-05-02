# Tasks: Telephony Adapter Spike

**Input**: Design documents from `specs/003-telephony-adapter-spike/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Tests**: Required by the feature spec. Tests must not require real Twilio or ACS credentials.

**Organization**: Tasks are grouped by setup/foundation and then by user story so the MVP can validate Twilio ingress through the shared audio pipeline without changing local microphone behavior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on an incomplete task.
- **[Story]**: User story label for implementation phases only.
- Every task includes exact file paths, acceptance criteria, dependencies, and a test command.

## Phase 1: Setup and Test Scaffolding

**Purpose**: Add failing or pending tests first for configuration, audio normalization, simulated telephony stream, and local microphone regression.

- [X] T001 [P] Add telephony configuration tests in `tests/unit/test_telephony_config.py`
- [X] T002 [P] Add Twilio media parsing and mu-law conversion tests in `tests/unit/test_twilio_audio_service.py`
- [X] T003 [P] Add simulated Twilio media stream integration tests in `tests/integration/test_twilio_media_flow.py`
- [X] T004 [P] Add local microphone WebSocket regression assertions in `tests/integration/test_mock_local_mic_flow.py`
- [X] T005 [P] Add frontend metadata display tests in `frontend/tests/voice-debug-console.test.tsx`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T001 | Verifies `VOICE_INPUT_MODE` defaults to `local_mic`, `TELEPHONY_PROVIDER` defaults to `none`, and missing phone-provider credentials do not break settings construction. | None | `pytest tests/unit/test_telephony_config.py` |
| T002 | Verifies Twilio `start` and `media` JSON parsing, base64 decode errors, unsupported codec errors, and G.711 mu-law to PCM16 mono output shape. | None | `pytest tests/unit/test_twilio_audio_service.py` |
| T003 | Verifies simulated Twilio WebSocket messages can create a mock RED pending case without real Twilio credentials. | None | `pytest tests/integration/test_twilio_media_flow.py` |
| T004 | Verifies `/ws/local-audio` still starts as local mic, commits WAV audio, and creates the same mock case payload after refactor. | None | `pytest tests/integration/test_mock_local_mic_flow.py` |
| T005 | Verifies the debug console renders `source_input_mode` and `call_metadata` when present while existing local mic payloads still render. | None | `cd frontend && npm test -- voice-debug-console.test.tsx` |

**Checkpoint**: Test expectations are captured before implementation.

---

## Phase 2: Foundational Shared Pipeline

**Purpose**: Extract the reusable processor and add shared telephony config/model primitives that block provider routes.

- [X] T006 Add telephony environment variables and derived configuration helpers in `app/core/config.py` and `.env.example`
- [X] T007 [P] Add `CallMetadata`, `TelephonyProvider`, and `TelephonyCodec` models in `app/models/telephony.py`
- [X] T008 Extract shared audio turn/provider/case orchestration into `app/services/audio_session_processor.py`
- [X] T009 Refactor local microphone WebSocket to use `AudioSessionProcessor` in `app/api/routes_audio.py`
- [X] T010 Run foundational backend regression checks for `app/services/audio_session_processor.py` and `app/api/routes_audio.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T006 | Settings expose `voice_input_mode`, `telephony_provider`, phone test metadata, Twilio variables, ACS variables, `twilio_configured`, and `acs_configured`; defaults keep `local_mic` and no provider credentials required. | T001 | `pytest tests/unit/test_telephony_config.py` |
| T007 | Pydantic model validation covers provider, call id, caller/called numbers, country, codec, sample rate, start time, and optional compact raw provider payload. | None | `python -m compileall app` |
| T008 | Processor owns `TurnManager`, `AudioBufferService`, provider selection, safety rules, and case repository writes; it emits existing debug events and final `triage.case.created` payloads. | T006, T007 | `pytest tests/unit/test_audio_buffer_service.py tests/unit/test_vad_service.py tests/unit/test_safety_rules.py` |
| T009 | `/ws/local-audio` public message contract remains unchanged while delegating frame, playback, and committed-turn processing to `AudioSessionProcessor`. | T008 | `pytest tests/integration/test_mock_local_mic_flow.py` |
| T010 | Compile and local mic regression pass before adding Twilio routes. | T008, T009 | `python -m compileall app; pytest tests/integration/test_mock_local_mic_flow.py` |

**Checkpoint**: Shared audio session processing is ready and local microphone remains the default working path.

---

## Phase 3: User Story 1 - Validate Phone Call Ingress (Priority: P1)

**Goal**: A Twilio or simulated Twilio call stream is normalized into `AudioFrame` objects and processed through the same Narayana gateway path as local microphone audio.

**Independent Test**: Run the simulated Twilio media stream test with mock services and no Twilio credentials; it should create a RED pending case through `AudioSessionProcessor`.

### Tests for User Story 1

- [X] T011 [P] [US1] Add Twilio webhook TwiML tests in `tests/unit/test_twilio_routes.py`
- [X] T012 [P] [US1] Complete Twilio normalizer failure-mode tests in `tests/unit/test_twilio_audio_service.py`
- [X] T013 [P] [US1] Complete simulated Twilio WebSocket case-creation test in `tests/integration/test_twilio_media_flow.py`

### Implementation for User Story 1

- [X] T014 [US1] Implement Twilio media parsing and mu-law PCM16 normalization in `app/services/twilio_audio_service.py`
- [X] T015 [US1] Implement Twilio incoming-call webhook and TwiML response in `app/api/routes_twilio.py`
- [X] T016 [US1] Implement Twilio media WebSocket forwarding to `AudioSessionProcessor` in `app/api/routes_twilio.py`
- [X] T017 [US1] Register Twilio router in `app/main.py`
- [X] T018 [US1] Validate Twilio ingress MVP through unit and integration tests for `app/services/twilio_audio_service.py` and `app/api/routes_twilio.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T011 | Configured webhook returns XML TwiML with `<Connect><Stream>` targeting `/ws/telephony/twilio/{call_id}`; missing public base URL returns clear 503 without startup failure. | T006 | `pytest tests/unit/test_twilio_routes.py` |
| T012 | Invalid base64, unsupported codec, non-20 ms payload expectations, and sequence/timestamp mapping are covered. | T002 | `pytest tests/unit/test_twilio_audio_service.py` |
| T013 | Simulated `connected`, `start`, `media`, and `stop` messages exercise the WebSocket without real Twilio credentials. | T003, T008 | `pytest tests/integration/test_twilio_media_flow.py` |
| T014 | Twilio media events produce `AudioFrame(encoding="pcm16", sample_rate_hz=8000, channels=1, duration_ms=20)` with base64 PCM16 payload. | T002, T007 | `pytest tests/unit/test_twilio_audio_service.py` |
| T015 | Incoming-call route accepts Twilio form data, derives call id and metadata, returns TwiML only when `TWILIO_WEBHOOK_PUBLIC_BASE_URL` exists, and never starts triage from the webhook. | T006, T011 | `pytest tests/unit/test_twilio_routes.py` |
| T016 | Twilio WebSocket creates/enriches `CallMetadata`, normalizes media frames, calls `AudioSessionProcessor`, forwards processor payloads, handles malformed messages, and stops cleanly. | T008, T014, T015 | `pytest tests/integration/test_twilio_media_flow.py` |
| T017 | FastAPI app includes Twilio routes without requiring Twilio credentials at import or startup. | T015, T016 | `pytest tests/unit/test_telephony_config.py tests/unit/test_twilio_routes.py` |
| T018 | US1 passes independently with mock mode, local JSON storage, no real Twilio credentials, and a RED pending mock case from simulated media. | T014, T015, T016, T017 | `pytest tests/unit/test_twilio_audio_service.py tests/unit/test_twilio_routes.py tests/integration/test_twilio_media_flow.py` |

**Checkpoint**: User Story 1 is independently demoable as the MVP.

---

## Phase 4: User Story 2 - Preserve Gateway Contract and Safety (Priority: P2)

**Goal**: Phone-originated cases preserve existing triage/safety semantics while adding `source_input_mode` and `call_metadata` to debug and dashboard payloads.

**Independent Test**: Compare local microphone and simulated Twilio case payloads. Local mic stays compatible; Twilio payloads include source mode and call metadata; safety still requires review for RED or uncertain cases.

### Tests for User Story 2

- [X] T019 [P] [US2] Add processor metadata payload tests in `tests/unit/test_audio_session_processor.py`
- [X] T020 [P] [US2] Add local mic compatibility assertions in `tests/integration/test_mock_local_mic_flow.py`
- [X] T021 [P] [US2] Add frontend source metadata rendering assertions in `frontend/tests/voice-debug-console.test.tsx`

### Implementation for User Story 2

- [X] T022 [US2] Add optional `source_input_mode` and `call_metadata` output support in `app/services/audio_session_processor.py`
- [X] T023 [US2] Ensure Twilio final case payload includes serialized call metadata in `app/api/routes_twilio.py`
- [X] T024 [US2] Preserve no-dispatch and human-review safety behavior through shared safety rules in `app/services/audio_session_processor.py`
- [X] T025 [US2] Extend debug WebSocket types for source metadata in `frontend/types/triage.ts`
- [X] T026 [US2] Render source input mode and call metadata in `frontend/components/voice/VoiceDebugConsole.tsx`
- [X] T027 [US2] Validate local mic compatibility, Twilio metadata payloads, and frontend rendering in `tests/integration/test_mock_local_mic_flow.py`, `tests/integration/test_twilio_media_flow.py`, and `frontend/tests/voice-debug-console.test.tsx`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T019 | Processor tests cover local payloads without metadata and phone-originated payloads with `source_input_mode` and `call_metadata`. | T008, T007 | `pytest tests/unit/test_audio_session_processor.py` |
| T020 | Regression test confirms `/ws/local-audio` still emits its existing payload shape and does not require phone metadata. | T009 | `pytest tests/integration/test_mock_local_mic_flow.py` |
| T021 | Frontend test covers rendering of provider, call id, caller/called number, country, codec, and sample rate when metadata exists. | T005 | `cd frontend && npm test -- voice-debug-console.test.tsx` |
| T022 | Processor includes source metadata only when configured and keeps safety rules before repository persistence. | T019 | `pytest tests/unit/test_audio_session_processor.py tests/unit/test_safety_rules.py` |
| T023 | Twilio WebSocket final `triage.case.created` payload includes `source_input_mode="twilio_call"` and serialized `CallMetadata`. | T016, T022 | `pytest tests/integration/test_twilio_media_flow.py` |
| T024 | RED, low-confidence, missing-location, and provider fallback cases remain human-review-required and never auto-close or auto-dispatch. | T022 | `pytest tests/unit/test_safety_rules.py tests/integration/test_twilio_media_flow.py` |
| T025 | TypeScript message union accepts optional `source_input_mode` and `call_metadata` without breaking existing messages. | T021 | `cd frontend && npm test -- voice-debug-console.test.tsx` |
| T026 | Debug console displays source metadata compactly and renders `-` or omits the section for local mic payloads without metadata. | T025 | `cd frontend && npm test -- voice-debug-console.test.tsx` |
| T027 | US2 passes across backend and frontend with local mic and simulated Twilio payloads. | T020, T023, T024, T026 | `pytest tests/integration/test_mock_local_mic_flow.py tests/integration/test_twilio_media_flow.py; cd frontend && npm test -- voice-debug-console.test.tsx` |

**Checkpoint**: User Story 2 preserves contract safety and operator/debug visibility.

---

## Phase 5: User Story 3 - Keep ACS Safe and Optional (Priority: P3)

**Goal**: Add ACS placeholder routes that fail safely and document the future adapter point without implementing production ACS media behavior.

**Independent Test**: Call ACS endpoints without ACS configuration and verify clear disabled/not-implemented behavior with no app crash.

### Tests for User Story 3

- [X] T028 [P] [US3] Add ACS disabled endpoint tests in `tests/unit/test_acs_routes.py`

### Implementation for User Story 3

- [X] T029 [US3] Implement ACS disabled event route and media WebSocket skeleton in `app/api/routes_acs.py`
- [X] T030 [US3] Register ACS router safely in `app/main.py`
- [X] T031 [US3] Validate ACS skeleton does not affect local mic or Twilio behavior in `tests/unit/test_acs_routes.py`, `tests/integration/test_mock_local_mic_flow.py`, and `tests/integration/test_twilio_media_flow.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T028 | Tests assert `/api/telephony/acs/events` and `/ws/telephony/acs/{call_id}` return or close with clear disabled/not-implemented behavior without ACS credentials. | T006 | `pytest tests/unit/test_acs_routes.py` |
| T029 | ACS routes exist, do not create cases, do not process media, and return explicit not-configured/not-implemented behavior. | T028 | `pytest tests/unit/test_acs_routes.py` |
| T030 | App includes ACS router without requiring ACS environment variables. | T029 | `pytest tests/unit/test_telephony_config.py tests/unit/test_acs_routes.py` |
| T031 | ACS skeleton has no regression impact on local mic or simulated Twilio tests. | T030 | `pytest tests/integration/test_mock_local_mic_flow.py tests/integration/test_twilio_media_flow.py tests/unit/test_acs_routes.py` |

**Checkpoint**: User Story 3 is independently safe and optional.

---

## Phase 6: Polish, Documentation, and Final Verification

**Purpose**: Update docs, env examples, and run full quality gates.

- [X] T032 [P] Update foreign-number test setup and limitations in `README.md`
- [X] T033 [P] Update implementation quickstart notes in `specs/003-telephony-adapter-spike/quickstart.md`
- [X] T034 [P] Update environment examples for telephony variables in `.env.example` and `frontend/.env.example`
- [X] T035 Run backend compile and full pytest verification for `app/` and `tests/`
- [X] T036 Run frontend test and production build verification in `frontend/`
- [X] T037 Review final diff for no production dispatch, no credential requirement, and local mic default in `app/`, `frontend/`, `tests/`, and `README.md`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T032 | README documents Twilio foreign-number setup, webhook URL examples, simulated stream testing, ACS skeleton status, and limitations: foreign ingress only, no Thailand number validation, no Thailand SMS validation, no emergency-service compliance. | T018, T027, T031 | `rg -n "foreign|Thailand|Twilio|ACS|emergency-service" README.md` |
| T033 | Feature quickstart reflects the implemented commands, URLs, and environment variables. | T032 | `rg -n "VOICE_INPUT_MODE|TWILIO_WEBHOOK_PUBLIC_BASE_URL|ACS" specs/003-telephony-adapter-spike/quickstart.md` |
| T034 | Env examples include telephony variables without secrets and keep mock/local mode as the default. | T006 | `rg -n "VOICE_INPUT_MODE|TELEPHONY_PROVIDER|TWILIO_|ACS_" .env.example frontend/.env.example` |
| T035 | Backend compiles and all automated backend tests pass without real phone provider credentials. | T018, T027, T031 | `python -m compileall app; pytest` |
| T036 | Frontend tests and Next.js build pass with source metadata display support. | T026 | `cd frontend && npm test; npm run build` |
| T037 | Final review confirms no production emergency dispatch, no Twilio/ACS startup dependency, no separate telephony triage pipeline, and `local_mic` remains default. | T035, T036 | `git diff --check; rg -n "dispatch|VOICE_INPUT_MODE|AudioSessionProcessor|local_mic" app frontend tests README.md` |

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 Setup and Test Scaffolding**: No dependencies.
- **Phase 2 Foundational Shared Pipeline**: Depends on Phase 1 tests for expected behavior.
- **Phase 3 User Story 1**: Depends on Phase 2 because Twilio must feed `AudioSessionProcessor`.
- **Phase 4 User Story 2**: Depends on Phase 2 and can run partly in parallel with Phase 3 after `AudioSessionProcessor` exists, but final metadata checks depend on Twilio payloads.
- **Phase 5 User Story 3**: Depends on telephony config from Phase 2; otherwise independent.
- **Phase 6 Polish and Verification**: Depends on completed selected user stories.

### User Story Dependencies

- **US1 Validate Phone Call Ingress**: Requires Phase 2. This is the MVP.
- **US2 Preserve Gateway Contract and Safety**: Requires Phase 2; Twilio-specific metadata assertions depend on US1 route work.
- **US3 Keep ACS Safe and Optional**: Requires Phase 2 config; independent from Twilio implementation except final regression.

### Task Dependency Highlights

- `T008` blocks `T009`, `T016`, `T019`, and `T022`.
- `T014` blocks Twilio media WebSocket implementation in `T016`.
- `T015` and `T016` block route registration validation in `T017`.
- `T022` blocks source metadata display and payload checks in `T023`, `T025`, and `T026`.
- `T029` blocks ACS route registration in `T030`.
- `T035` and `T036` must pass before `T037`.

## Parallel Opportunities

- `T001` through `T005` can be written in parallel.
- `T007` can run in parallel with `T006`; `T008` must wait for both.
- `T011`, `T012`, and `T013` can be written in parallel after Phase 2 starts.
- `T019`, `T020`, and `T021` can be written in parallel after Phase 2.
- `T028` can run in parallel with US1 work after `T006`.
- `T032`, `T033`, and `T034` can run in parallel after implementation behavior is known.

## Parallel Example: User Story 1

```text
Task: "Add Twilio webhook TwiML tests in tests/unit/test_twilio_routes.py"
Task: "Complete Twilio normalizer failure-mode tests in tests/unit/test_twilio_audio_service.py"
Task: "Complete simulated Twilio WebSocket case-creation test in tests/integration/test_twilio_media_flow.py"
```

After tests exist:

```text
Task: "Implement Twilio media parsing and mu-law PCM16 normalization in app/services/twilio_audio_service.py"
Task: "Implement Twilio incoming-call webhook and TwiML response in app/api/routes_twilio.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 test scaffolding.
2. Complete Phase 2 shared processor extraction and local mic regression.
3. Complete Phase 3 Twilio ingress.
4. Stop and validate with:

```powershell
python -m compileall app
pytest tests/unit/test_twilio_audio_service.py tests/unit/test_twilio_routes.py tests/integration/test_twilio_media_flow.py tests/integration/test_mock_local_mic_flow.py
```

### Incremental Delivery

1. Shared processor and local mic regression.
2. Twilio simulated stream to mock RED case.
3. Metadata and frontend display.
4. ACS disabled skeleton.
5. Documentation and full quality gates.

### Guardrails

- Keep `local_mic` as the default input mode.
- Do not require real Twilio or ACS credentials for startup or tests.
- Do not implement production emergency dispatch.
- Do not create a second triage, safety, or case repository pipeline for telephony.

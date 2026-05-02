# Tasks: Narayana AI Azure Voice Gateway

**Input**: Design documents from `/specs/001-crisis-voice-triage/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Goal**: Fastest path to a working hackathon demo: local transcript -> safe RED case -> debug UI -> browser mic -> VAD/WebSocket -> Azure provider adapters -> Cosmos/Voice Live/phone adapter placeholders.

## Phase 1: Backend Skeleton

**Purpose**: Create the FastAPI project shape and configuration foundation.

- [ ] T001 Create FastAPI app skeleton in `app/main.py`
  - Files: `app/main.py`, `app/api/__init__.py`, `app/core/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`
  - Acceptance: `GET /api/health/azure` can be registered later without changing app creation; app imports without side effects.
  - Dependencies: none
  - Test: `python -m compileall app`

- [ ] T002 Add backend dependencies and pytest config in `requirements.txt`
  - Files: `requirements.txt`, `pytest.ini`
  - Acceptance: dependencies include FastAPI, Uvicorn, Pydantic, pytest, pytest-asyncio, httpx, websockets, python-dotenv, Azure Speech SDK, OpenAI client, Azure Cosmos SDK, Azure Identity.
  - Dependencies: T001
  - Test: `pip install -r requirements.txt`

- [ ] T003 Create environment configuration template in `.env.example`
  - Files: `.env.example`
  - Acceptance: includes `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `AZURE_VOICE_LIVE_ENDPOINT`, `AZURE_VOICE_LIVE_MODEL`, `COSMOS_DB_ENDPOINT`, `COSMOS_DB_KEY`, `COSMOS_DB_DATABASE`, `COSMOS_DB_CONTAINER`, and `USE_MOCK_SERVICES=true`.
  - Dependencies: none
  - Test: N/A

- [ ] T004 Implement typed settings and provider-mode helpers in `app/core/config.py`
  - Files: `app/core/config.py`
  - Acceptance: settings load from environment, expose `use_mock_services`, Azure completeness checks, Cosmos completeness check, and selected provider mode without printing secrets.
  - Dependencies: T003
  - Test: `pytest tests/unit/test_provider_fallback.py`

---

## Phase 2: Domain Models

**Purpose**: Define the stable schema that mock, Azure, case storage, and the UI all share.

- [ ] T005 [P] Create audio and debug event models in `app/models/audio.py`
  - Files: `app/models/audio.py`
  - Acceptance: includes `AudioFrame`, `AudioDebugEvent`, `VoiceGatewaySession`, `CallerTurn`, VAD states, input modes, and required debug event names.
  - Dependencies: T001
  - Test: `pytest tests/unit/test_vad_service.py`

- [ ] T006 [P] Create triage schema models in `app/models/triage.py`
  - Files: `app/models/triage.py`
  - Acceptance: includes `TriageResult`, incident enum, triage enum, `SafetyRuleResult`, `missing_fields`, nullable `people_affected`, and status enum values `pending/contacted/dispatched/resolved/closed`.
  - Dependencies: T001
  - Test: `pytest tests/unit/test_triage_schema.py`

- [ ] T007 [P] Create crisis case persistence models in `app/models/case.py`
  - Files: `app/models/case.py`
  - Acceptance: includes `CrisisCase`, `CaseRepositoryRecord`, source provider mode, session ID, debug event count, and timestamps.
  - Dependencies: T006
  - Test: `pytest tests/unit/test_triage_schema.py`

- [ ] T008 Add unit tests for triage schema validation in `tests/unit/test_triage_schema.py`
  - Files: `tests/unit/test_triage_schema.py`
  - Acceptance: validates required fields, enum rejection, `confidence` bounds, nullable `people_affected`, nullable `caller_phone_optional`, and default `pending` status behavior.
  - Dependencies: T006, T007
  - Test: `pytest tests/unit/test_triage_schema.py`

---

## Phase 3: Mock Transcript-To-Case MVP (US1)

**Goal**: A developer can submit the Thai transcript and get a safe structured RED case locally with no Azure credentials.

**Independent Test**: `POST /api/triage/from-transcript` with the Thai sample returns `incident_type=flood`, `triage_level=RED`, `location_text=Hat Yai/หาดใหญ่`, `human_review_required=true`, and `status=pending`.

- [ ] T009 [P] [US1] Define provider interface in `app/services/voice_agent_provider.py`
  - Files: `app/services/voice_agent_provider.py`
  - Acceptance: includes `VoiceAgentProvider`, provider health result, transcript input, `VoiceProviderResult`, and async `process_transcript`/future `process_turn` shape.
  - Dependencies: T005, T006
  - Test: `python -m compileall app/services/voice_agent_provider.py`

- [ ] T010 [US1] Implement deterministic mock provider in `app/services/mock_voice_provider.py`
  - Files: `app/services/mock_voice_provider.py`
  - Acceptance: Thai flood sample maps to flood, RED, Hat Yai/หาดใหญ่, elderly breathing difficulty, rescue/medical needs, high confidence; minor damage and unclear speech fixtures are included.
  - Dependencies: T009
  - Test: `pytest tests/integration/test_thai_transcript_to_red_case.py`

- [ ] T011 [P] [US1] Add safety rule unit tests in `tests/unit/test_safety_rules.py`
  - Files: `tests/unit/test_safety_rules.py`
  - Acceptance: tests force RED for breathing difficulty, unconsciousness, severe bleeding, trapped person, active drowning risk, active fire exposure, chest pain, stroke symptoms, and cannot escape.
  - Dependencies: T006
  - Test: `pytest tests/unit/test_safety_rules.py`

- [ ] T012 [US1] Implement deterministic safety rules in `app/services/safety_rules.py`
  - Files: `app/services/safety_rules.py`
  - Acceptance: forces RED for configured red flags, requires review for confidence below 0.75, missing location, contradictory facts, or unsafe GREEN; never sets `closed` or `dispatched`.
  - Dependencies: T006, T011
  - Test: `pytest tests/unit/test_safety_rules.py`

- [ ] T013 [P] [US1] Add Thai transcript integration test in `tests/integration/test_thai_transcript_to_red_case.py`
  - Files: `tests/integration/test_thai_transcript_to_red_case.py`
  - Acceptance: Thai sample returns required structured JSON with status `pending`, RED triage, review required, and explanation mentioning trapped/breathing difficulty.
  - Dependencies: T010, T012
  - Test: `pytest tests/integration/test_thai_transcript_to_red_case.py`

- [ ] T014 [US1] Implement transcript triage endpoint in `app/api/routes_triage.py`
  - Files: `app/api/routes_triage.py`, `app/main.py`
  - Acceptance: `POST /api/triage/from-transcript` accepts transcript, selects provider, applies safety rules, returns `TriageResult`/case JSON, and validates malformed input.
  - Dependencies: T004, T010, T012, T013
  - Test: `pytest tests/integration/test_thai_transcript_to_red_case.py`

- [ ] T015 [US1] Add provider fallback tests in `tests/unit/test_provider_fallback.py`
  - Files: `tests/unit/test_provider_fallback.py`
  - Acceptance: `USE_MOCK_SERVICES=true` selects mock; missing Azure credentials falls back to mock with warning; no test requires real Azure credentials.
  - Dependencies: T004, T009
  - Test: `pytest tests/unit/test_provider_fallback.py`

---

## Phase 4: Case Repository (US1)

**Goal**: Store or emit the generated case locally for preview and later dashboard integration.

- [ ] T016 [P] [US1] Define case repository interface in `app/services/case_repository.py`
  - Files: `app/services/case_repository.py`
  - Acceptance: exposes async `create` and `get` methods using `CrisisCase`/`CaseRepositoryRecord`; interface does not mention Cosmos-specific types.
  - Dependencies: T007
  - Test: `python -m compileall app/services/case_repository.py`

- [ ] T017 [US1] Implement local JSON case repository in `app/services/local_case_repository.py`
  - Files: `app/services/local_case_repository.py`
  - Acceptance: writes and reads case records from a local JSON file path, creates directories as needed, preserves `pending` status, and handles empty file state.
  - Dependencies: T016
  - Test: `pytest tests/unit/test_local_case_repository.py`

- [ ] T018 [P] [US1] Add local repository tests in `tests/unit/test_local_case_repository.py`
  - Files: `tests/unit/test_local_case_repository.py`
  - Acceptance: tests create, get, missing case, JSON persistence, and no automatic dispatch/close.
  - Dependencies: T016, T017
  - Test: `pytest tests/unit/test_local_case_repository.py`

- [ ] T019 [US1] Implement case creation endpoint in `app/api/routes_cases.py`
  - Files: `app/api/routes_cases.py`, `app/main.py`
  - Acceptance: `POST /api/cases` stores or emits a valid case and returns `CaseRepositoryRecord`; invalid schema returns validation error.
  - Dependencies: T014, T017, T018
  - Test: `pytest tests/integration/test_cases_api.py`

- [ ] T020 [P] [US1] Add cases API tests in `tests/integration/test_cases_api.py`
  - Files: `tests/integration/test_cases_api.py`
  - Acceptance: tests `POST /api/cases` with Thai RED case, validation failure, and local repository record fields.
  - Dependencies: T019
  - Test: `pytest tests/integration/test_cases_api.py`

---

## Phase 5: Debug Console and Manual Transcript UI (US1)

**Goal**: A simple React/Next.js console lets reviewers submit the Thai transcript and inspect transcript, triage JSON, safety result, and case preview.

- [ ] T021 [P] [US1] Create frontend environment and API client in `frontend/lib/triage-api-client.ts`
  - Files: `frontend/.env.example`, `frontend/lib/triage-api-client.ts`, `frontend/types/triage.ts`
  - Acceptance: defines `NEXT_PUBLIC_API_BASE_URL`, request/response types, and client methods for `/api/triage/from-transcript` and `/api/cases`.
  - Dependencies: T014, T019
  - Test: `npm test -- triage-api-client`

- [ ] T022 [US1] Create compact debug console shell in `frontend/app/voice-debug/page.tsx`
  - Files: `frontend/app/voice-debug/page.tsx`, `frontend/components/voice/VoiceDebugConsole.tsx`
  - Acceptance: page shows provider mode, manual transcript textarea, submit button, transcript output, structured JSON, safety result, and case preview.
  - Dependencies: T021
  - Test: `npm test -- VoiceDebugConsole`

- [ ] T023 [P] [US1] Add frontend debug console component tests in `frontend/tests/voice-debug-console.test.tsx`
  - Files: `frontend/tests/voice-debug-console.test.tsx`
  - Acceptance: tests manual transcript submit success, loading state, error state, RED badge rendering, review-required rendering, and case preview status.
  - Dependencies: T022
  - Test: `npm test -- voice-debug-console`

---

## Phase 6: Local Audio WebSocket and VAD (US2)

**Goal**: Browser microphone streams audio to `/ws/local-audio`; backend emits VAD/debug events and commits turns.

**Independent Test**: Synthetic audio frames trigger `audio.frame.received`, `vad.speech.start`, `vad.speech.end`, `turn.committed`, and `barge_in.detected`.

- [ ] T024 [P] [US2] Implement audio frame validation in `app/services/audio_frame_service.py`
  - Files: `app/services/audio_frame_service.py`
  - Acceptance: validates sequence, PCM16 encoding, mono channel, 20 ms frame target, base64 payload, and sample rate metadata.
  - Dependencies: T005
  - Test: `pytest tests/unit/test_audio_frame_service.py`

- [ ] T025 [P] [US2] Add VAD state machine tests in `tests/unit/test_vad_service.py`
  - Files: `tests/unit/test_vad_service.py`
  - Acceptance: tests silence, speech start, speech end, 600-900 ms threshold, 150-250 ms pre-speech buffer, thinking/speaking states, and barge-in.
  - Dependencies: T005
  - Test: `pytest tests/unit/test_vad_service.py`

- [ ] T026 [US2] Implement energy-based VAD in `app/services/vad_service.py`
  - Files: `app/services/vad_service.py`
  - Acceptance: classifies speech/silence from PCM frame energy, exposes threshold config, and supports optional WebRTC VAD hook without requiring it.
  - Dependencies: T024, T025
  - Test: `pytest tests/unit/test_vad_service.py`

- [ ] T027 [US2] Implement turn manager in `app/services/turn_manager.py`
  - Files: `app/services/turn_manager.py`
  - Acceptance: buffers pre-speech audio, commits turns after silence threshold, emits required debug events, tracks `listening/thinking/speaking`, and flags barge-in.
  - Dependencies: T026
  - Test: `pytest tests/unit/test_vad_service.py`

- [ ] T028 [US2] Implement local audio WebSocket route in `app/api/routes_audio.py`
  - Files: `app/api/routes_audio.py`, `app/main.py`
  - Acceptance: `/ws/local-audio` accepts `session.start`, `audio.frame`, assistant playback events, and `session.close`; returns required debug and case events.
  - Dependencies: T010, T012, T027
  - Test: `pytest tests/integration/test_mock_local_mic_flow.py`

- [ ] T029 [P] [US2] Add mock local mic integration test in `tests/integration/test_mock_local_mic_flow.py`
  - Files: `tests/integration/test_mock_local_mic_flow.py`
  - Acceptance: synthetic frames create VAD events, commit a turn, invoke mock provider, apply safety rules, and emit `triage.case.created`.
  - Dependencies: T028
  - Test: `pytest tests/integration/test_mock_local_mic_flow.py`

- [ ] T030 [US2] Add browser microphone capture client in `frontend/lib/audio-client.ts`
  - Files: `frontend/lib/audio-client.ts`, `frontend/lib/voice-ws-client.ts`
  - Acceptance: uses Web Audio API to request microphone, converts/resamples to PCM16 mono frames, batches 20 ms frames, and sends to `/ws/local-audio`.
  - Dependencies: T028
  - Test: `npm test -- audio-client`

- [ ] T031 [US2] Add live VAD state and debug timeline UI in `frontend/components/voice/VoiceDebugConsole.tsx`
  - Files: `frontend/components/voice/VoiceDebugConsole.tsx`, `frontend/app/voice-debug/page.tsx`
  - Acceptance: UI shows silence/speech/listening/thinking/speaking, required debug event timeline, transcript, triage JSON, safety result, and generated case preview from WebSocket events.
  - Dependencies: T030
  - Test: `npm test -- VoiceDebugConsole`

---

## Phase 7: Azure Speech and Azure OpenAI Providers (US1)

**Goal**: When credentials exist, the same transcript/case contract works through Azure Speech STT and Azure OpenAI structured triage.

- [ ] T032 [P] [US1] Implement Azure health endpoint in `app/api/routes_audio.py`
  - Files: `app/api/routes_audio.py`, `app/core/config.py`, `app/main.py`
  - Acceptance: `GET /api/health/azure` returns selected provider, configured booleans, missing variable names, warnings, and no secret values.
  - Dependencies: T004
  - Test: `pytest tests/unit/test_provider_fallback.py`

- [ ] T033 [US1] Implement Azure Speech STT provider in `app/services/azure_speech_provider.py`
  - Files: `app/services/azure_speech_provider.py`
  - Acceptance: accepts committed turn audio or audio reference, uses Azure Speech credentials when configured, returns transcript/language/confidence, and has clear mockable seams for tests.
  - Dependencies: T009, T027, T032
  - Test: manual `pytest tests/unit/test_provider_fallback.py`

- [ ] T034 [US1] Implement Azure OpenAI structured triage provider in `app/services/azure_openai_triage_provider.py`
  - Files: `app/services/azure_openai_triage_provider.py`
  - Acceptance: sends transcript to Azure OpenAI with strict structured schema, validates response into `TriageResult`, handles invalid JSON/schema failure by returning review-required fallback.
  - Dependencies: T006, T012, T032
  - Test: `pytest tests/unit/test_triage_schema.py`

- [ ] T035 [US1] Wire AzureSpeechOpenAIProvider selection in `app/services/voice_agent_provider.py`
  - Files: `app/services/voice_agent_provider.py`, `app/core/config.py`
  - Acceptance: `USE_MOCK_SERVICES=true` selects mock; complete Azure Speech/OpenAI credentials select Azure path when mock disabled; incomplete credentials fall back to mock with warning.
  - Dependencies: T015, T033, T034
  - Test: `pytest tests/unit/test_provider_fallback.py`

- [ ] T036 [US1] Add manual Azure Speech Thai audio test notes in `README.md`
  - Files: `README.md`
  - Acceptance: documents how to run a Thai audio STT smoke test when Azure credentials exist and states the test is skipped when credentials are missing.
  - Dependencies: T033
  - Test: manual Azure Speech STT using Thai audio

---

## Phase 8: Cosmos DB Repository (US1)

**Goal**: Cases can be stored in Cosmos DB when credentials exist, with local JSON fallback remaining default.

- [ ] T037 [P] [US1] Implement Cosmos case repository in `app/services/cosmos_case_repository.py`
  - Files: `app/services/cosmos_case_repository.py`
  - Acceptance: uses Cosmos endpoint/key/database/container config, stores `CrisisCase` JSON, retrieves by case ID, and does not change API response shape.
  - Dependencies: T016, T019
  - Test: manual Cosmos DB write if credentials exist

- [ ] T038 [US1] Add repository selection in `app/services/case_repository.py`
  - Files: `app/services/case_repository.py`, `app/core/config.py`
  - Acceptance: selects Cosmos only when all Cosmos variables exist; otherwise selects local JSON; health endpoint can report Cosmos configured state.
  - Dependencies: T017, T037
  - Test: `pytest tests/unit/test_provider_fallback.py`

---

## Phase 9: Optional Azure Voice Live Provider (US1)

**Goal**: Add Voice Live as an optional provider without making it required for V0.

- [ ] T039 [US1] Implement optional Azure Voice Live provider in `app/services/azure_voice_live_provider.py`
  - Files: `app/services/azure_voice_live_provider.py`
  - Acceptance: connects to configured Voice Live endpoint/model, streams audio frames, receives transcript/audio events, maps recoverable failures to fallback warnings, and passes transcript to Azure OpenAI triage if structured result is unavailable.
  - Dependencies: T027, T034, T035
  - Test: manual Voice Live smoke test when credentials exist

- [ ] T040 [US1] Add Voice Live provider selection guard in `app/services/voice_agent_provider.py`
  - Files: `app/services/voice_agent_provider.py`, `app/core/config.py`
  - Acceptance: Voice Live is selected only when explicitly configured; missing Voice Live variables never blocks mock or Azure Speech/OpenAI flow.
  - Dependencies: T039
  - Test: `pytest tests/unit/test_provider_fallback.py`

---

## Phase 10: Future Phone Adapter Interfaces (US4)

**Goal**: Define Twilio and ACS adapter seams without requiring or enabling them for V0.

- [ ] T041 [P] [US4] Define audio input adapter protocols in `app/services/audio_frame_service.py`
  - Files: `app/services/audio_frame_service.py`
  - Acceptance: includes `AudioInputAdapter`, `LocalMicAdapter` naming, and normalized `AudioFrame` output contract.
  - Dependencies: T024
  - Test: `pytest tests/unit/test_input_adapters.py`

- [ ] T042 [US4] Add Twilio and ACS adapter placeholders in `app/services/audio_frame_service.py`
  - Files: `app/services/audio_frame_service.py`, `tests/unit/test_input_adapters.py`
  - Acceptance: `TwilioMediaStreamAdapter` and `ACSAudioStreamAdapter` exist as disabled V1 placeholders and cannot be selected by default V0 config.
  - Dependencies: T041
  - Test: `pytest tests/unit/test_input_adapters.py`

- [ ] T043 [P] [US4] Add adapter interface documentation in `README.md`
  - Files: `README.md`
  - Acceptance: documents local mic as V0 path, uploaded audio optional, Twilio/ACS as V1 only, and known phone-number limitations.
  - Dependencies: T042
  - Test: N/A

---

## Final Phase: Demo Readiness and Documentation

**Purpose**: Make the hackathon path reproducible for another developer or AI reviewer.

- [ ] T044 Add README local setup, mock demo, and Azure setup in `README.md`
  - Files: `README.md`
  - Acceptance: includes install, `.env`, backend run, frontend run, Thai transcript test, mock local mic test, Azure Speech/OpenAI setup, Cosmos setup, and phone-number limitation notes.
  - Dependencies: T014, T019, T031, T035, T038, T043
  - Test: follow quickstart commands manually

- [ ] T045 [P] Add end-to-end smoke test script in `tests/integration/test_gateway_demo_smoke.py`
  - Files: `tests/integration/test_gateway_demo_smoke.py`
  - Acceptance: exercises health, transcript triage, case creation, and asserts RED/human review/pending for Thai sample.
  - Dependencies: T014, T019, T032
  - Test: `pytest tests/integration/test_gateway_demo_smoke.py`

- [ ] T046 Run full backend test suite and record result in `specs/001-crisis-voice-triage/tasks.md`
  - Files: `specs/001-crisis-voice-triage/tasks.md`
  - Acceptance: records pass/fail and any skipped Azure/Cosmos manual tests under a verification note.
  - Dependencies: T001-T045
  - Test: `pytest`

- [ ] T047 Run frontend test/build checks and record result in `specs/001-crisis-voice-triage/tasks.md`
  - Files: `specs/001-crisis-voice-triage/tasks.md`
  - Acceptance: records pass/fail for frontend unit tests/build or notes if frontend scaffold is not present in target repo yet.
  - Dependencies: T021-T031
  - Test: `npm test && npm run build`

---

## Dependencies and Execution Order

### Fastest Demo Path

1. T001-T004: backend skeleton, config, environment.
2. T005-T008: models and schema validation.
3. T009-T015: mock transcript-to-triage endpoint with safety.
4. T016-T020: local case repository and case creation endpoint.
5. T021-T023: debug UI manual transcript and case preview.
6. T024-T031: microphone capture, `/ws/local-audio`, VAD, and debug events.
7. T032-T036: Azure Speech/OpenAI provider and health check.
8. T037-T040: Cosmos and optional Voice Live.
9. T041-T043: Twilio/ACS interfaces only.
10. T044-T047: README and verification.

### Parallel Opportunities

- T005, T006, and T007 can run in parallel after T001.
- T009, T011, and T013 can be prepared in parallel once models are available.
- T016 and T018 can be prepared alongside T014.
- T021 and T023 can run while backend repository work finishes.
- T024 and T025 can run in parallel.
- T032, T033, and T034 can be split after provider interfaces exist.
- T037 and T039 can run independently after the core provider/repository interfaces are stable.
- T041 and T043 can run in parallel once audio frame contracts exist.

## User Story Coverage

- **US1 Validate Local Voice Intake Pipeline**: T009-T040, T044-T047
- **US2 Observe VAD, Turn Detection, and Barge-In**: T024-T031
- **US3 Enforce Crisis Safety Rules After AI Output**: T011-T012 plus safety assertions in T013, T014, T045
- **US4 Keep Phone Providers as Future Adapters**: T041-T043

## Quality Gates

- App runs locally with mock mode.
- App runs locally with Azure Speech/OpenAI credentials.
- Local microphone creates a case.
- RED safety cases are never downgraded.
- Missing or uncertain information requires human review.
- Phone provider integration is isolated behind adapters and disabled for V0.

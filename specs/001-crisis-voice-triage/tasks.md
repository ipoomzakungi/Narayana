# Tasks: Narayana AI Voice Intake

**Input**: Design documents from `/specs/001-crisis-voice-triage/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are included because the feature explicitly requires triage logic, VAD state transition, local repository, local microphone/mock provider, and Thai extraction tests.

**Organization**: Tasks are grouped by independently testable user-story increments and ordered for a working local demo first:

1. Local transcript-to-case
2. Dashboard
3. Local microphone + VAD debug
4. Azure AI integration
5. Cosmos DB
6. SignalR/live updates
7. Optional upload link
8. Telephony adapter interface only

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: User story label for story phases only.
- Every task includes an exact file path.

## Phase 1: Setup

**Purpose**: Create the two-app project skeleton, local environment examples, and baseline tooling.

- [ ] T001 Create the `backend/` FastAPI directory structure from the plan in `backend/app/main.py`
- [ ] T002 Create backend Python package markers in `backend/app/__init__.py`, `backend/app/api/__init__.py`, `backend/app/core/__init__.py`, `backend/app/models/__init__.py`, `backend/app/repositories/__init__.py`, and `backend/app/services/__init__.py`
- [ ] T003 Create backend dependency list with FastAPI, Uvicorn, Pydantic, pytest, pytest-asyncio, httpx, python-dotenv, azure-cosmos, azure-identity, azure-cognitiveservices-speech, openai, websockets, and Azure Monitor OpenTelemetry in `backend/requirements.txt`
- [ ] T004 Create backend local environment template with all required variables and `USE_MOCK_SERVICES=true` in `backend/.env.example`
- [ ] T005 Create backend pytest configuration and import path settings in `backend/pytest.ini`
- [ ] T006 Scaffold the Next.js TypeScript frontend app with Tailwind CSS under `frontend/package.json`
- [ ] T007 Configure shadcn/ui project metadata and aliases in `frontend/components.json`
- [ ] T008 Create frontend environment template for API and WebSocket URLs in `frontend/.env.example`
- [ ] T009 Create frontend TypeScript, Next.js, Tailwind, and PostCSS configuration in `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/tailwind.config.ts`, and `frontend/postcss.config.mjs`
- [ ] T010 Create shared frontend layout and global stylesheet placeholders in `frontend/app/layout.tsx` and `frontend/app/globals.css`
- [ ] T011 Add local data and secret ignores for backend and frontend environment files in `.gitignore`

**Checkpoint**: Both app skeletons exist and can accept implementation tasks.

---

## Phase 2: Foundational

**Purpose**: Implement shared config, domain models, repository interface, provider interfaces, and API wiring that block user-story work.

**Critical**: No user-story implementation should start until these tasks are complete.

- [ ] T012 Implement typed backend settings, mock-mode detection, and low-confidence threshold defaults in `backend/app/core/config.py`
- [ ] T013 [P] Implement `TriageLevel`, `CaseStatus`, `VadState`, and transcript enums in `backend/app/models/triage.py`
- [ ] T014 [P] Implement Pydantic models for `CrisisCase`, `TranscriptTurn`, `EvidenceFact`, `VoiceTimingEvent`, `OperatorUpdate`, and `SimulatedOutboundAction` in `backend/app/models/case.py`
- [ ] T015 Implement `CaseRepository` protocol with create, list, get, update status, override triage, append debug event, and append simulated action methods in `backend/app/repositories/case_repository.py`
- [ ] T016 Implement local JSON persistence scaffold with atomic read/write helpers in `backend/app/repositories/local_case_repository.py`
- [ ] T017 Implement repository provider selection that defaults to `LocalCaseRepository` when Cosmos settings are missing in `backend/app/repositories/__init__.py`
- [ ] T018 Implement `VoiceAgentProvider`, `VoiceTurnInput`, and `VoiceAgentResult` interfaces in `backend/app/services/azure_voice_service.py`
- [ ] T019 Implement no-op local realtime notifier interface and in-memory connection registry in `backend/app/services/signalr_service.py`
- [ ] T020 Wire FastAPI app creation, CORS for local frontend, health endpoint, dependency injection, and route registration in `backend/app/main.py`
- [ ] T021 [P] Create frontend shared API and domain types matching `contracts/openapi.yaml` in `frontend/types/case.ts`
- [ ] T022 [P] Create frontend API client helpers for case endpoints in `frontend/lib/api-client.ts`
- [ ] T023 [P] Create compact command-center app shell primitives in `frontend/components/app-shell/AppShell.tsx`
- [ ] T024 [P] Create triage badge and VAD state badge primitives in `frontend/components/triage/TriageBadge.tsx` and `frontend/components/voice/VadStateBadge.tsx`

**Checkpoint**: Domain contracts, local storage selection, provider interfaces, and app wiring are ready.

---

## Phase 3: User Story 1 - Local Transcript-to-Case MVP (Priority: P1)

**Goal**: Create a structured crisis case from a Thai transcript without microphone, Azure credentials, Twilio, ACS, or Cosmos.

**Independent Test**: Submit the Thai sample transcript to `POST /api/cases/from-transcript` and verify a stored RED case with Thai language, flood/medical/trapped evidence, confidence, summary, triage reason, and `human_review_required=true`.

### Tests for User Story 1

- [ ] T025 [P] [US1] Add unit tests for RED, YELLOW, GREEN, low-confidence, and ambiguous triage outcomes in `backend/tests/unit/test_triage_service.py`
- [ ] T026 [P] [US1] Add unit tests for local repository create, list, get, status update, triage override, and persistence in `backend/tests/unit/test_local_case_repository.py`
- [ ] T027 [P] [US1] Add integration test for Thai sample transcript extraction to RED case in `backend/tests/integration/test_thai_structured_extraction.py`
- [ ] T028 [P] [US1] Add API contract tests for `POST /api/cases/from-transcript`, `GET /api/cases`, and `GET /api/cases/{case_id}` in `backend/tests/integration/test_cases_api.py`

### Implementation for User Story 1

- [ ] T029 [P] [US1] Implement deterministic RED/YELLOW/GREEN keyword and evidence rules in `backend/app/services/triage_service.py`
- [ ] T030 [US1] Implement Thai sample extraction for location, flood incident, elderly person, breathing difficulty, trapped context, immediate needs, summary, and triage reason in `backend/app/services/triage_service.py`
- [ ] T031 [US1] Implement low-confidence and ambiguity handling that forces `human_review_required=true` in `backend/app/services/triage_service.py`
- [ ] T032 [US1] Implement safe Thai guidance script selection for RED, YELLOW, GREEN, and general waiting guidance in `backend/app/services/triage_service.py`
- [ ] T033 [US1] Complete `LocalCaseRepository` create, list, get, status update, triage override, debug event append, and simulated action append behavior in `backend/app/repositories/local_case_repository.py`
- [ ] T034 [US1] Implement case creation, transcript-to-case request handling, case listing, and case detail endpoints in `backend/app/api/routes_cases.py`
- [ ] T035 [US1] Register case routes and backend dependencies in `backend/app/main.py`
- [ ] T036 [US1] Add manual transcript submission page state and redirect to Live Cases in `frontend/app/page.tsx`
- [ ] T037 [US1] Add client helper for `POST /api/cases/from-transcript` in `frontend/lib/api-client.ts`
- [ ] T038 [US1] Verify Thai sample creates a RED case through backend tests and document the command result in `specs/001-crisis-voice-triage/tasks.md`

**Checkpoint**: Local transcript-to-case MVP works end-to-end and is independently demoable.

---

## Phase 4: User Story 2 - Live Cases Dashboard and Case Detail (Priority: P2)

**Goal**: Operators can scan prioritized cases, open details, understand triage rationale, update status, and override priority.

**Independent Test**: Seed RED, YELLOW, and GREEN cases; open `/cases`; verify RED is prioritized; open a case detail; update status and override priority while preserving AI triage reason.

### Tests for User Story 2

- [ ] T039 [P] [US2] Add backend integration tests for status update and triage override endpoints in `backend/tests/integration/test_operator_case_updates.py`
- [ ] T040 [P] [US2] Add frontend component tests for triage badge, case table row ordering, and status controls in `frontend/tests/cases/components.test.tsx`
- [ ] T041 [P] [US2] Add Playwright workflow test for list, detail, status update, and priority override using mock backend data in `frontend/tests/e2e/operator-dashboard.spec.ts`

### Implementation for User Story 2

- [ ] T042 [US2] Implement `PATCH /api/cases/{case_id}/status` and `PATCH /api/cases/{case_id}/triage` in `backend/app/api/routes_cases.py`
- [ ] T043 [US2] Record operator updates with previous value, new value, reason, and timestamp in `backend/app/repositories/local_case_repository.py`
- [ ] T044 [US2] Add frontend status update and triage override API helpers in `frontend/lib/api-client.ts`
- [ ] T045 [P] [US2] Implement compact Live Cases table with priority ordering, status, confidence, human-review flag, and timestamps in `frontend/components/cases/CaseList.tsx`
- [ ] T046 [P] [US2] Implement case detail summary, transcript, evidence facts, AI reason, confidence, and override history sections in `frontend/components/cases/CaseDetail.tsx`
- [ ] T047 [P] [US2] Implement status update and priority override controls with reason capture in `frontend/components/cases/CaseActions.tsx`
- [ ] T048 [US2] Implement Live Cases route with refresh fallback and manual transcript entry access in `frontend/app/cases/page.tsx`
- [ ] T049 [US2] Implement Case Detail route that loads by case ID and shows operator actions in `frontend/app/cases/[caseId]/page.tsx`
- [ ] T050 [US2] Add command-center navigation for Live Cases, Voice Debug Console, and Upload Evidence in `frontend/components/app-shell/AppShell.tsx`
- [ ] T051 [US2] Apply restrained command-center Tailwind tokens, triage colors, table density, and responsive behavior in `frontend/app/globals.css`
- [ ] T052 [US2] Verify dashboard user flow with seeded RED/YELLOW/GREEN cases and document the command result in `specs/001-crisis-voice-triage/tasks.md`

**Checkpoint**: Operators can use the dashboard and case detail workflow without microphone or Azure services.

---

## Phase 5: User Story 4 - Local Microphone and VAD Debug Console (Priority: P3)

**Goal**: Browser microphone streams PCM frames to FastAPI, backend VAD manages turns, debug UI shows silence/speech/listening/thinking/speaking, and barge-in is logged.

**Independent Test**: Open `/voice-debug`, allow microphone, speak and pause; verify VAD states and timing events appear; trigger assistant-speaking then speak again and verify barge-in.

### Tests for User Story 4

- [ ] T053 [P] [US4] Add VAD state transition unit tests for silence, speech start, end-of-turn silence threshold, thinking, speaking, and barge-in in `backend/tests/unit/test_vad_service.py`
- [ ] T054 [P] [US4] Add WebSocket voice flow integration test with mock audio frames and mock provider in `backend/tests/integration/test_local_voice_flow.py`
- [ ] T055 [P] [US4] Add frontend unit tests for audio client frame sizing, connection lifecycle, and debug event rendering in `frontend/tests/voice/audio-client.test.ts`

### Implementation for User Story 4

- [ ] T056 [US4] Implement 20 ms PCM16 frame state machine, energy threshold, 200 ms pre-speech padding, 750 ms silence threshold, and barge-in detection in `backend/app/services/vad_service.py`
- [ ] T057 [US4] Implement voice session orchestration, provider invocation after completed turns, and debug event creation in `backend/app/services/audio_gateway.py`
- [ ] T058 [US4] Implement `MockVoiceProvider` responses for Thai flood sample, minor property damage, and unclear noisy speech in `backend/app/services/azure_voice_service.py`
- [ ] T059 [US4] Implement `/ws/voice` client/server event handling from `contracts/voice-websocket.md` in `backend/app/api/routes_voice.py`
- [ ] T060 [US4] Implement `GET /api/debug/events` with session and case filters in `backend/app/api/routes_voice.py`
- [ ] T061 [US4] Register voice routes in `backend/app/main.py`
- [ ] T062 [US4] Implement browser microphone capture, downsampling to PCM16 16 kHz mono, 20 ms frame batching, and WebSocket send loop in `frontend/lib/audio-client.ts`
- [ ] T063 [US4] Implement voice WebSocket client with reconnect, event dispatch, and assistant playback state hooks in `frontend/lib/voice-client.ts`
- [ ] T064 [P] [US4] Implement VAD state strip, event timeline, transcript stream, and provider status components in `frontend/components/voice/VoiceDebugPanel.tsx`
- [ ] T065 [US4] Implement Voice Debug Console route with microphone controls, mock-service toggle, Thai sample shortcut, and barge-in test control in `frontend/app/voice-debug/page.tsx`
- [ ] T066 [US4] Verify local microphone flow with mock services and document the command result in `specs/001-crisis-voice-triage/tasks.md`

**Checkpoint**: Local microphone and VAD debug demo works without Azure services.

---

## Phase 6: User Story 3 - Safety Guardrails and Human-Centered Triage (Priority: P2)

**Goal**: The assistant never dispatches automatically, never denies or downgrades emergency help without review, uses safe scripted guidance, and explains every priority.

**Independent Test**: Run RED, YELLOW, GREEN, ambiguous, and low-confidence scripts and verify human-review flags, safe guidance text, preserved AI reason, and no autonomous dispatch claims.

### Tests for User Story 3

- [ ] T067 [P] [US3] Add safety regression tests for no auto-dispatch, no denial, no unsafe downgrade, and official-hotline disclaimer in `backend/tests/unit/test_safety_guardrails.py`
- [ ] T068 [P] [US3] Add Thai safe guidance script tests for RED, YELLOW, GREEN, and ambiguous cases in `backend/tests/unit/test_safe_guidance.py`

### Implementation for User Story 3

- [ ] T069 [US3] Implement immutable safety guardrail constants and forbidden phrase checks in `backend/app/services/triage_service.py`
- [ ] T070 [US3] Enforce RED indicators and confidence below 0.70 as `human_review_required=true` in all create/update paths in `backend/app/services/triage_service.py`
- [ ] T071 [US3] Add safe-script IDs and Thai guidance copy for waiting guidance in `backend/app/services/triage_service.py`
- [ ] T072 [US3] Surface crisis-intake assistant disclaimer in dashboard shell and voice debug console in `frontend/components/app-shell/AppShell.tsx`
- [ ] T073 [US3] Show human-review reason, AI triage reason, and operator override reason together in `frontend/components/cases/CaseDetail.tsx`
- [ ] T074 [US3] Verify RED, low-confidence, and ambiguous safety scenarios and document the command result in `specs/001-crisis-voice-triage/tasks.md`

**Checkpoint**: Safety behavior is test-covered and visible in the operator UI.

---

## Phase 7: Azure AI Provider Integration

**Goal**: Add replaceable Azure Voice Live and Speech + Azure OpenAI providers while keeping mock mode as a reliable fallback.

**Independent Test**: With `USE_MOCK_SERVICES=false` and Azure variables present, the Thai sample can be processed through Azure; with variables missing, provider selection falls back to mock mode and reports a recoverable provider event.

### Tests for Azure AI Integration

- [ ] T075 [P] Add provider selection unit tests for mock mode, Voice Live configured mode, Speech plus OpenAI fallback mode, and missing credentials fallback in `backend/tests/unit/test_voice_provider_selection.py`
- [ ] T076 [P] Add schema validation tests for Azure OpenAI structured triage JSON and invalid JSON fallback in `backend/tests/unit/test_azure_structured_extraction.py`

### Implementation for Azure AI Integration

- [ ] T077 Implement `AzureVoiceLiveProvider` WebSocket session setup, PCM16 audio forwarding, transcript finalization, assistant text handling, and recoverable error mapping in `backend/app/services/azure_voice_service.py`
- [ ] T078 Implement `AzureSpeechOpenAIProvider` speech-to-text, structured triage extraction, safe JSON validation, and optional text-to-speech hook in `backend/app/services/azure_voice_service.py`
- [ ] T079 Implement provider factory that prefers Voice Live, falls back to Speech plus OpenAI, then mock mode based on `backend/app/core/config.py`
- [ ] T080 Add provider status and fallback warnings to voice debug events in `backend/app/services/audio_gateway.py`
- [ ] T081 Add Azure provider status display and fallback notice to `frontend/components/voice/VoiceDebugPanel.tsx`
- [ ] T082 Document Azure AI mode setup, mock fallback behavior, and Thai demo smoke test in `README.md`

**Checkpoint**: Azure AI can be enabled without making the local demo dependent on Azure credentials.

---

## Phase 8: Cosmos DB Repository

**Goal**: Store cases in Azure Cosmos DB when configured while preserving local JSON fallback.

**Independent Test**: With Cosmos variables configured, repository tests create, list, update, and retrieve cases from Cosmos; without variables, the same API uses local JSON.

### Tests for Cosmos DB

- [ ] T083 [P] Add repository contract tests that run against `LocalCaseRepository` and a mocked Cosmos container in `backend/tests/unit/test_case_repository_contract.py`
- [ ] T084 [P] Add Cosmos settings fallback tests in `backend/tests/unit/test_repository_provider.py`

### Implementation for Cosmos DB

- [ ] T085 Implement Cosmos client creation, database/container references, and partition key assumptions in `backend/app/services/cosmos_service.py`
- [ ] T086 Implement `CosmosCaseRepository` methods matching `CaseRepository` in `backend/app/repositories/cosmos_case_repository.py`
- [ ] T087 Wire repository provider to select `CosmosCaseRepository` only when all `COSMOS_DB_*` values are present in `backend/app/repositories/__init__.py`
- [ ] T088 Add Cosmos setup and local fallback documentation to `README.md`

**Checkpoint**: Storage can switch between local JSON and Cosmos without route or frontend changes.

---

## Phase 9: SignalR and Local Realtime Dashboard Updates

**Goal**: Dashboard updates when cases are created or changed, using local WebSocket/SSE first and Azure SignalR when configured.

**Independent Test**: Create a case from transcript or voice; verify `/cases` updates without manual refresh. Then update status and verify connected dashboards receive a `case.updated` event.

### Tests for Realtime Updates

- [ ] T089 [P] Add backend WebSocket/SSE notifier tests for `case.created`, `case.updated`, `debug.event`, reconnect snapshot, and duplicate event IDs in `backend/tests/integration/test_realtime_dashboard.py`
- [ ] T090 [P] Add frontend realtime client tests for event merge, reconnect reload, duplicate suppression, and polling fallback in `frontend/tests/realtime-client.test.ts`

### Implementation for Realtime Updates

- [ ] T091 Implement local WebSocket and SSE case event endpoints from `contracts/realtime-dashboard.md` in `backend/app/api/routes_cases.py`
- [ ] T092 Publish `case.created`, `case.updated`, and `debug.event` events from case and voice services in `backend/app/services/signalr_service.py`
- [ ] T093 Implement Azure SignalR management integration when `SIGNALR_CONNECTION_STRING` is present in `backend/app/services/signalr_service.py`
- [ ] T094 Implement frontend realtime client with WebSocket, SSE or polling fallback, reconnect snapshot, and duplicate event suppression in `frontend/lib/realtime-client.ts`
- [ ] T095 Connect Live Cases page to realtime events and degraded connection indicator in `frontend/app/cases/page.tsx`
- [ ] T096 Connect Voice Debug Console to realtime debug events in `frontend/app/voice-debug/page.tsx`
- [ ] T097 Document local realtime and Azure SignalR mode in `README.md`

**Checkpoint**: Live dashboard updates work locally and have an Azure SignalR adapter path.

---

## Phase 10: Optional Upload Evidence Link Simulation

**Goal**: Provide a clearly simulated upload-link flow and prepare the production Blob SAS path without real upload dependency in V0.

**Independent Test**: Generate a simulated upload link for a case; verify it is stored on the case, appears in the UI, emits `upload.simulated`, and is labeled simulated.

### Tests for Upload Link Simulation

- [ ] T098 [P] Add backend tests for simulated upload-link creation, expiration, case association, and simulation flag in `backend/tests/integration/test_upload_simulation.py`
- [ ] T099 [P] Add frontend tests for upload-link form validation and simulated label rendering in `frontend/tests/uploads/upload-page.test.tsx`

### Implementation for Upload Link Simulation

- [ ] T100 Implement `POST /api/uploads/simulate-link` from `contracts/openapi.yaml` in `backend/app/api/routes_uploads.py`
- [ ] T101 Register upload routes in `backend/app/main.py`
- [ ] T102 Append simulated outbound actions to cases in `backend/app/repositories/local_case_repository.py`
- [ ] T103 Add upload simulation API helper in `frontend/lib/api-client.ts`
- [ ] T104 Implement Upload Evidence page with case selector, simulated link generation, expiration display, and clear simulated labeling in `frontend/app/uploads/page.tsx`
- [ ] T105 Add production Blob SAS notes without implementing real upload in `README.md`

**Checkpoint**: Evidence upload remains optional and visibly simulated in V0.

---

## Phase 11: Telephony Adapter Interface Only

**Goal**: Prepare V1 telephony boundaries without implementing Twilio, Azure Communication Services, real phone numbers, or production call handling.

**Independent Test**: Type checks and documentation show telephony interfaces exist, are not wired into V0 runtime, and local microphone remains the only required V0 audio path.

- [ ] T106 [P] Define `AudioStreamAdapter`, `LocalMicrophoneAdapter`, `TwilioMediaStreamAdapter`, and `ACSCallAutomationAdapter` protocols without production implementations in `backend/app/services/audio_gateway.py`
- [ ] T107 Add tests proving Twilio and ACS adapters are not selected in V0 runtime config in `backend/tests/unit/test_telephony_adapters_disabled.py`
- [ ] T108 Document V1 telephony adapter boundaries and V0 non-goals in `README.md`

**Checkpoint**: Telephony is prepared as an interface only and does not block local demo.

---

## Final Phase: Polish and Cross-Cutting Quality Gates

**Purpose**: Make the local demo reliable, documented, and presentable.

- [ ] T109 [P] Add backend quickstart smoke script for health, transcript-to-case, list cases, status update, and override in `backend/tests/integration/test_quickstart_smoke.py`
- [ ] T110 [P] Add frontend Playwright smoke test for transcript entry, Live Cases, Case Detail, Voice Debug Console, and Upload Evidence navigation in `frontend/tests/e2e/local-demo.spec.ts`
- [ ] T111 Add Application Insights OpenTelemetry initialization guarded by `APPLICATIONINSIGHTS_CONNECTION_STRING` in `backend/app/main.py`
- [ ] T112 Add Dockerfile and container startup command for FastAPI deployment in `backend/Dockerfile`
- [ ] T113 Add Azure Static Web Apps build notes and frontend environment mapping in `infra/static-web-apps/README.md`
- [ ] T114 Add Azure Container Apps deployment notes and backend environment mapping in `infra/container-apps/README.md`
- [ ] T115 Update `README.md` with local setup, mock demo, Azure mode, safety constraints, no-dispatch warning, and troubleshooting steps
- [ ] T116 Run backend test suite and record the result in `specs/001-crisis-voice-triage/tasks.md`
- [ ] T117 Run frontend lint/test/e2e checks and record the result in `specs/001-crisis-voice-triage/tasks.md`
- [ ] T118 Manually execute the five demo scenarios from `quickstart.md` and record the result in `specs/001-crisis-voice-triage/tasks.md`

---

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 Setup has no dependencies.
- Phase 2 Foundational depends on Phase 1 and blocks all user-story work.
- Phase 3 US1 Local Transcript-to-Case depends on Phase 2 and is the MVP target.
- Phase 4 US2 Dashboard depends on Phase 3 because it consumes cases created by the local transcript flow.
- Phase 5 US4 Local Microphone and VAD Debug depends on Phase 3 because completed voice turns create cases through the transcript-to-case path.
- Phase 6 US3 Safety depends on Phase 3 and should be completed before public demo.
- Phase 7 Azure AI depends on Phases 3, 5, and 6.
- Phase 8 Cosmos DB depends on Phase 3.
- Phase 9 SignalR/live updates depends on Phases 4 and 5.
- Phase 10 Upload Link Simulation depends on Phase 4.
- Phase 11 Telephony Adapter Interface depends on Phase 5.
- Final polish depends on the phases selected for the demo.

### User Story Dependencies

- **US1 Capture Thai Crisis Intake by Voice, local transcript slice**: Starts after Foundation; no dependency on dashboard, microphone, Azure, Cosmos, SignalR, upload, or telephony.
- **US2 Review Prioritized Cases on Dashboard**: Starts after US1 local case API exists; independently testable with seeded cases.
- **US4 Observe Turn Detection and Audio Timing**: Starts after US1 local case creation exists; independently testable with mock provider and local WebSocket audio.
- **US3 Keep Triage Safe and Human-Centered**: Starts after US1 triage service exists; independently testable with scripted safety cases.

### Within Each Story

- Tests should be written first and fail before implementation.
- Models and interfaces precede services.
- Services precede endpoints.
- Endpoints precede frontend integration.
- Frontend primitives precede pages.
- Each checkpoint should be validated before starting the next phase when working sequentially.

## Parallel Opportunities

- Setup tasks T003-T011 can be split once T001-T002 establish folders.
- Foundational model, frontend type, API client, and UI primitive tasks T013-T024 can run in parallel after T012.
- US1 test tasks T025-T028 can run in parallel before T029.
- US2 frontend component tasks T045-T047 can run in parallel after API helpers T044.
- US4 test tasks T053-T055 can run in parallel before T056.
- Azure AI provider tasks T077-T081 can be split by provider, factory, backend event, and frontend status display after tests define expected behavior.
- Cosmos, SignalR, upload, and telephony phases can run in parallel after their listed dependencies are complete.

## Parallel Example: User Story 1

```text
Task: "T025 [P] [US1] Add unit tests for RED, YELLOW, GREEN, low-confidence, and ambiguous triage outcomes in backend/tests/unit/test_triage_service.py"
Task: "T026 [P] [US1] Add unit tests for local repository create, list, get, status update, triage override, and persistence in backend/tests/unit/test_local_case_repository.py"
Task: "T027 [P] [US1] Add integration test for Thai sample transcript extraction to RED case in backend/tests/integration/test_thai_structured_extraction.py"
Task: "T028 [P] [US1] Add API contract tests for POST /api/cases/from-transcript, GET /api/cases, and GET /api/cases/{case_id} in backend/tests/integration/test_cases_api.py"
```

## Parallel Example: User Story 2

```text
Task: "T045 [P] [US2] Implement compact Live Cases table with priority ordering, status, confidence, human-review flag, and timestamps in frontend/components/cases/CaseList.tsx"
Task: "T046 [P] [US2] Implement case detail summary, transcript, evidence facts, AI reason, confidence, and override history sections in frontend/components/cases/CaseDetail.tsx"
Task: "T047 [P] [US2] Implement status update and priority override controls with reason capture in frontend/components/cases/CaseActions.tsx"
```

## Parallel Example: User Story 4

```text
Task: "T053 [P] [US4] Add VAD state transition unit tests for silence, speech start, end-of-turn silence threshold, thinking, speaking, and barge-in in backend/tests/unit/test_vad_service.py"
Task: "T054 [P] [US4] Add WebSocket voice flow integration test with mock audio frames and mock provider in backend/tests/integration/test_local_voice_flow.py"
Task: "T055 [P] [US4] Add frontend unit tests for audio client frame sizing, connection lifecycle, and debug event rendering in frontend/tests/voice/audio-client.test.ts"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational.
3. Complete Phase 3 US1 Local Transcript-to-Case.
4. Stop and validate local transcript-to-case with the Thai sample.
5. Add Phase 4 Dashboard for a visual operator demo.
6. Add Phase 5 Local Microphone and VAD Debug for the voice demo.

### Incremental Delivery

1. Local transcript-to-case API and minimal entry page.
2. Dashboard and case detail workflow.
3. Local microphone stream, VAD, debug console, and mock voice provider.
4. Safety hardening and scripted guidance.
5. Azure AI provider integration.
6. Cosmos DB and SignalR cloud adapters.
7. Optional upload link simulation.
8. Telephony adapter interfaces only.

### Quality Gates

- Local app runs without Twilio, ACS, real phone numbers, Cosmos, SignalR, or Azure AI credentials.
- Mock services keep the demo usable offline.
- Thai flood plus elderly breathing difficulty creates RED and requires human review.
- Minor property damage only creates GREEN unless uncertainty requires review.
- Unclear noisy speech sets `human_review_required=true`.
- Operator override preserves original AI triage reason.
- Dashboard updates without manual refresh after Phase 9.
- No system path claims rescue was automatically dispatched.

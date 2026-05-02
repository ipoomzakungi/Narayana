# Tasks: Azure Container Apps Deployment and Twilio Real-Call Test Support

**Input**: Design documents from `specs/004-aca-twilio-deploy/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Tests**: Required for helper functions only. Automated tests must not call Azure or Twilio.

**Organization**: Tasks are grouped by setup/foundation and then user stories so backend packaging can be completed first, then webhook validation, outbound call helper, docs, and final verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: User story label for implementation phases only.
- Every task includes exact file paths, acceptance criteria, dependencies, and a test command.

## Phase 1: Setup and Helper Test Scaffolding

**Purpose**: Create the script/test structure and capture no-network helper expectations before implementation.

- [X] T001 Create deployment scripts directory with placeholder files in `scripts/check_public_webhook.py`, `scripts/twilio_outbound_call.py`, and `scripts/azure_container_apps_deploy.ps1`
- [X] T002 [P] Add no-network helper test skeleton in `tests/unit/test_twilio_test_helpers.py`
- [X] T003 [P] Add Docker packaging contract checks in `tests/unit/test_twilio_test_helpers.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T001 | `scripts/` exists and each requested helper file can be imported or inspected without executing network or Azure commands. | None | `Test-Path scripts/check_public_webhook.py; Test-Path scripts/twilio_outbound_call.py; Test-Path scripts/azure_container_apps_deploy.ps1` |
| T002 | Tests define expected behavior for URL normalization, missing env validation, TwiML parser, and Twilio request construction with mocked network calls only. | None | `pytest tests/unit/test_twilio_test_helpers.py` |
| T003 | Tests define expected Dockerfile command/port and `.dockerignore` exclusions for `.env`, `.data/`, `.git/`, and frontend build artifacts. | None | `pytest tests/unit/test_twilio_test_helpers.py` |

**Checkpoint**: Test expectations exist for tooling before implementation.

---

## Phase 2: Foundational Tooling Utilities

**Purpose**: Implement shared script helpers used by public webhook and outbound-call tooling.

- [X] T004 Implement URL normalization and env validation helpers in `scripts/check_public_webhook.py`
- [X] T005 [P] Implement Twilio webhook URL and required env helpers in `scripts/twilio_outbound_call.py`
- [X] T006 [P] Add `TWILIO_OUTBOUND_TO` and `AZURE_CONTAINER_APP_URL` examples in `.env.example`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T004 | Helper trims trailing slashes, rejects empty/malformed base URLs, constructs health/webhook URLs, and can be imported without network calls. | T002 | `pytest tests/unit/test_twilio_test_helpers.py -k "webhook or url or missing"` |
| T005 | Helper validates `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_OUTBOUND_TO`, and `TWILIO_WEBHOOK_PUBLIC_BASE_URL`; reports all missing values before request construction. | T002 | `pytest tests/unit/test_twilio_test_helpers.py -k "outbound or missing"` |
| T006 | `.env.example` includes `TWILIO_OUTBOUND_TO=` and optional `AZURE_CONTAINER_APP_URL=` without secret values. | None | `rg -n "TWILIO_OUTBOUND_TO|AZURE_CONTAINER_APP_URL" .env.example` |

**Checkpoint**: Shared helper validation is ready and no provider calls occur during tests.

---

## Phase 3: User Story 1 - Deploy Public Voice Backend (Priority: P1)

**Goal**: Provide backend container packaging and Azure Container Apps deployment tooling for a public WebSocket-capable Narayana backend.

**Independent Test**: Inspect and optionally build the backend container; run deployment helper validation without requiring cloud calls.

### Tests for User Story 1

- [X] T007 [P] [US1] Add Dockerfile and `.dockerignore` assertions in `tests/unit/test_twilio_test_helpers.py`
- [X] T008 [P] [US1] Add Azure deploy script validation assertions in `tests/unit/test_twilio_test_helpers.py`

### Implementation for User Story 1

- [X] T009 [US1] Add Python slim backend Dockerfile in `Dockerfile`
- [X] T010 [US1] Add Docker build exclusions in `.dockerignore`
- [X] T011 [US1] Implement Azure Container Apps deployment helper in `scripts/azure_container_apps_deploy.ps1`
- [X] T012 [US1] Validate Docker packaging and deployment helper behavior in `Dockerfile`, `.dockerignore`, and `scripts/azure_container_apps_deploy.ps1`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T007 | Tests assert Dockerfile uses Python slim, exposes `8000`, and runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`. | T003 | `pytest tests/unit/test_twilio_test_helpers.py -k docker` |
| T008 | Tests or static checks assert deployment script names required env vars and includes `az containerapp up` plus fallback command text. | T003 | `pytest tests/unit/test_twilio_test_helpers.py -k deploy` |
| T009 | Dockerfile installs `requirements.txt`, copies backend runtime files, exposes port `8000`, and uses the requested uvicorn command. | T007 | `python -m compileall app` |
| T010 | `.dockerignore` excludes `.env`, `.env.*`, `.data/`, `.git/`, caches, frontend `node_modules/`, and frontend `.next/`. | T007 | `pytest tests/unit/test_twilio_test_helpers.py -k docker` |
| T011 | PowerShell script validates `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_CONTAINER_APP_NAME`, `TWILIO_PHONE_NUMBER`, and `TWILIO_WEBHOOK_PUBLIC_BASE_URL`; prefers `az containerapp up`; prints fallback ACR/Container Apps commands. | T008, T006 | `pytest tests/unit/test_twilio_test_helpers.py -k deploy` |
| T012 | US1 passes through static tests and compile checks without cloud credentials. | T009, T010, T011 | `python -m compileall app scripts; pytest tests/unit/test_twilio_test_helpers.py -k "docker or deploy"` |

**Checkpoint**: Backend can be packaged and the deployment helper documents/validates the Azure Container Apps path.

---

## Phase 4: User Story 2 - Verify Public Twilio Webhook (Priority: P2)

**Goal**: Provide a no-Twilio public checker that verifies health and fake Twilio TwiML response shape against a deployed backend URL.

**Independent Test**: Run unit tests with mocked HTTP openers and no external network calls.

### Tests for User Story 2

- [X] T013 [P] [US2] Add public webhook URL construction tests in `tests/unit/test_twilio_test_helpers.py`
- [X] T014 [P] [US2] Add TwiML response parser tests in `tests/unit/test_twilio_test_helpers.py`
- [X] T015 [P] [US2] Add mocked health and fake webhook request tests in `tests/unit/test_twilio_test_helpers.py`

### Implementation for User Story 2

- [X] T016 [US2] Implement health check, fake Twilio POST, and TwiML validation in `scripts/check_public_webhook.py`
- [X] T017 [US2] Add command-line entry point and clear failure output in `scripts/check_public_webhook.py`
- [X] T018 [US2] Validate public webhook checker without real network calls in `scripts/check_public_webhook.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T013 | Tests cover `TWILIO_WEBHOOK_PUBLIC_BASE_URL`, `AZURE_CONTAINER_APP_URL` fallback, trailing slash normalization, health URL, and fake webhook URL. | T004 | `pytest tests/unit/test_twilio_test_helpers.py -k webhook` |
| T014 | Tests pass for XML containing `/ws/telephony/twilio/CA_TEST` and fail for XML missing the expected media path. | T004 | `pytest tests/unit/test_twilio_test_helpers.py -k twiml` |
| T015 | Tests mock urllib/openers for health GET and fake webhook POST and assert no real network calls are made. | T004 | `pytest tests/unit/test_twilio_test_helpers.py -k "health or fake"` |
| T016 | Script performs `GET /api/health/azure`, posts fake `CallSid=CA_TEST`, and validates returned TwiML includes `/ws/telephony/twilio/CA_TEST`. | T013, T014, T015 | `pytest tests/unit/test_twilio_test_helpers.py -k "webhook or twiml or health"` |
| T017 | Script exits non-zero with actionable messages for missing URL, failed health request, failed fake webhook request, or invalid TwiML; no Twilio API call exists in this script. | T016 | `pytest tests/unit/test_twilio_test_helpers.py -k webhook` |
| T018 | US2 passes with standard-library mocked network behavior only. | T016, T017 | `pytest tests/unit/test_twilio_test_helpers.py -k "webhook or twiml or health"` |

**Checkpoint**: Public webhook checker behavior is independently testable without real provider calls.

---

## Phase 5: User Story 3 - Place Controlled Twilio Test Calls (Priority: P3)

**Goal**: Provide a credential-gated outbound call helper for manual real-call validation from `+16082005400` to a verified destination.

**Independent Test**: Run unit tests for env validation, request construction, and mocked Twilio responses without real credentials.

### Tests for User Story 3

- [X] T019 [P] [US3] Add outbound missing-env validation tests in `tests/unit/test_twilio_test_helpers.py`
- [X] T020 [P] [US3] Add Twilio REST request body construction tests in `tests/unit/test_twilio_test_helpers.py`
- [X] T021 [P] [US3] Add mocked Twilio success and error response tests in `tests/unit/test_twilio_test_helpers.py`

### Implementation for User Story 3

- [X] T022 [US3] Implement Twilio outbound call validation and request construction in `scripts/twilio_outbound_call.py`
- [X] T023 [US3] Implement Twilio REST API POST and success/error output handling in `scripts/twilio_outbound_call.py`
- [X] T024 [US3] Validate outbound helper without real network calls in `scripts/twilio_outbound_call.py`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T019 | Tests assert all missing required values are reported together before request construction. | T005 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |
| T020 | Tests assert request body contains `From`, `To`, and `Url` pointing to `/api/telephony/twilio/incoming-call`, with Basic Auth header construction covered without exposing secrets. | T005 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |
| T021 | Tests mock Twilio success response with a call SID and Twilio error response with troubleshooting output. | T005 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |
| T022 | Helper validates `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_OUTBOUND_TO`, and `TWILIO_WEBHOOK_PUBLIC_BASE_URL` before any Twilio request. | T019, T020 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |
| T023 | Helper posts to Twilio REST API only after validation, prints call SID on success, and prints clear tips for verified caller ID and Thailand Geo Permissions on failure. | T021, T022 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |
| T024 | US3 passes with all Twilio network behavior mocked and no credentials required. | T022, T023 | `pytest tests/unit/test_twilio_test_helpers.py -k outbound` |

**Checkpoint**: Outbound call helper is ready for manual credential-gated testing and automated tests stay offline.

---

## Phase 6: User Story 4 - Document Deployment and Real-Call Limits (Priority: P4)

**Goal**: Document Azure Container Apps backend deployment, Twilio real-call setup, Vercel frontend-only scope, and explicit exclusions.

**Independent Test**: Review README and env example for required setup sections and exclusions.

### Implementation for User Story 4

- [X] T025 [US4] Update Azure Container Apps deployment section in `README.md`
- [X] T026 [US4] Update Twilio webhook, fake webhook test, inbound call, and outbound verified Thai phone instructions in `README.md`
- [X] T027 [US4] Document verified caller ID, Twilio Geo Permissions for Thailand, Vercel frontend-only backend limitation, no ACS production, no SMS, and no emergency dispatch in `README.md`
- [X] T028 [US4] Validate documentation coverage with text checks in `README.md` and `.env.example`

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T025 | README lists Azure Container Apps deployment prerequisites, required environment variables, deployment command, and mock-first runtime settings. | T012 | `rg -n "Azure Container Apps|AZURE_RESOURCE_GROUP|USE_MOCK_SERVICES|VOICE_INPUT_MODE|TWILIO_PHONE_NUMBER" README.md` |
| T026 | README documents Twilio number `+16082005400`, voice webhook URL, fake webhook checker command, inbound call test, and outbound helper command. | T018, T024 | `rg -n "\\+16082005400|check_public_webhook|twilio_outbound_call|incoming-call" README.md` |
| T027 | README explicitly states verified caller ID, Thailand Geo Permissions, Vercel frontend-only, no ACS production implementation, no SMS, and no emergency dispatch. | T026 | `rg -n "verified caller ID|Geo Permissions|Vercel|No SMS|No emergency dispatch|ACS" README.md` |
| T028 | US4 documentation checks pass and no secret values are introduced. | T025, T026, T027 | `rg -n "TWILIO_AUTH_TOKEN=\\.\\.\\.|TWILIO_OUTBOUND_TO|AZURE_CONTAINER_APP_URL|frontend-only" README.md .env.example` |

**Checkpoint**: Teammates can follow deployment and real-call validation steps while seeing clear limits.

---

## Phase 7: Final Verification

**Purpose**: Run complete local quality gates and verify tooling-only scope.

- [X] T029 Run script/backend compile checks for `app/` and `scripts/`
- [X] T030 Run full backend pytest suite in `tests/`
- [X] T031 Run frontend tests and production build in `frontend/`
- [X] T032 Review final diff for no `AudioSessionProcessor`, Twilio media WebSocket, ACS production, SMS, or dispatch behavior changes

| Task | Acceptance Criteria | Dependencies | Test Command |
|------|---------------------|--------------|--------------|
| T029 | Python compile succeeds for backend and scripts. | T024, T028 | `python -m compileall app scripts` |
| T030 | All backend tests pass; helper tests make no real Azure or Twilio calls. | T029 | `pytest` |
| T031 | Frontend tests and build still pass even though the feature is backend/tooling focused. | T030 | `cd frontend && npm test; npm run build` |
| T032 | Diff shows tooling/docs/env/test changes only, with no changes to `app/services/audio_session_processor.py`, `app/api/routes_twilio.py` media WebSocket behavior, ACS production implementation, SMS, or dispatch behavior. | T031 | `git diff --check; git diff -- app/services/audio_session_processor.py app/api/routes_twilio.py app/api/routes_acs.py; rg -n "SMS|dispatch|AudioSessionProcessor|containerapp|twilio_outbound" Dockerfile .dockerignore scripts README.md tests specs/004-aca-twilio-deploy .env.example` |

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational Tooling Utilities**: Depends on Phase 1 tests.
- **US1 Deploy Public Voice Backend**: Depends on Phase 2 for env examples and validation patterns.
- **US2 Verify Public Twilio Webhook**: Depends on Phase 2 URL/env helpers.
- **US3 Place Controlled Twilio Test Calls**: Depends on Phase 2 outbound helper validation.
- **US4 Document Deployment and Real-Call Limits**: Depends on US1, US2, and US3 behavior being defined.
- **Final Verification**: Depends on all selected story phases.

### User Story Dependencies

- **US1 (P1)**: MVP. Can be delivered after Phase 2.
- **US2 (P2)**: Requires base URL helper behavior from Phase 2; independent from real Twilio credentials.
- **US3 (P3)**: Requires outbound helper validation from Phase 2; real-call execution is manual.
- **US4 (P4)**: Documents completed tooling and limitations.

### Task Dependency Highlights

- `T004` blocks public webhook checker tasks `T013` through `T018`.
- `T005` blocks outbound call helper tasks `T019` through `T024`.
- `T007` and `T008` shape implementation for `T009` through `T011`.
- `T025` through `T027` should wait until helper behavior and commands are final.
- `T029` through `T032` are final gates.

## Parallel Opportunities

- `T002` and `T003` can run in parallel after `T001`.
- `T004`, `T005`, and `T006` can run in parallel after test scaffolding.
- `T007` and `T008` can run in parallel.
- `T013`, `T014`, and `T015` can run in parallel.
- `T019`, `T020`, and `T021` can run in parallel.
- `T025`, `T026`, and `T027` can run in parallel after implementation commands stabilize.

## Parallel Example: Helper Tests

```text
Task: "Add public webhook URL construction tests in tests/unit/test_twilio_test_helpers.py"
Task: "Add TwiML response parser tests in tests/unit/test_twilio_test_helpers.py"
Task: "Add outbound missing-env validation tests in tests/unit/test_twilio_test_helpers.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 Docker packaging and Azure Container Apps deployment helper.
3. Validate:

```powershell
python -m compileall app scripts
pytest tests/unit/test_twilio_test_helpers.py -k "docker or deploy"
```

### Incremental Delivery

1. Docker packaging and deployment helper.
2. Public webhook checker.
3. Twilio outbound call helper.
4. README/env updates.
5. Full verification.

### Guardrails

- Do not change `AudioSessionProcessor`.
- Do not change Twilio media WebSocket behavior.
- Do not implement ACS production behavior.
- Do not implement SMS.
- Do not implement emergency dispatch.
- Do not make automated tests call Azure or Twilio.

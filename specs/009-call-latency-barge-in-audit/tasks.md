# Tasks: Call Latency, Barge-In, and Audit Debugging

**Input**: Design documents from `specs/009-call-latency-barge-in-audit/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required by the feature request. Add or update tests before implementation tasks in each story phase.

**Organization**: Tasks are grouped by user story so each increment can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase because it touches different files or independent test files.
- **[Story]**: User story label from [spec.md](./spec.md). Setup, foundational, and polish tasks do not use story labels.
- Each task includes an exact file path.

## Phase 1: Setup

**Purpose**: Add shared settings and environment documentation required by every implementation path.

- [X] T001 Add latency, VAD, no-reply, and call-audit settings fields plus env parsing in `app/core/config.py`
- [X] T002 [P] Add latency, VAD, no-reply, and call-audit variables to `.env.example`
- [X] T003 [P] Add config default and env parsing coverage for the new settings in `tests/unit/test_telephony_config.py`

**Checkpoint**: Settings are available to backend services and documented for local/Azure deployment.

---

## Phase 2: Foundational

**Purpose**: Add shared audit/timeline primitives and safe logging before story-specific route behavior depends on them.

- [X] T004 Add audit timeline fields and response models for call audit sessions in `app/models/intake.py`
- [X] T005 Implement safe structured logging and audit event helpers in `app/services/call_audit_logger.py`
- [X] T006 Extend the intake session store with timeline append/read helpers in `app/services/intake_session_store.py`
- [X] T007 [P] Add call audit logger redaction and event-shape tests in `tests/unit/test_call_audit_logger.py`
- [X] T008 [P] Add intake session timeline helper tests in `tests/unit/test_intake_session_store.py`

**Checkpoint**: Shared audit model, safe logger, and session-store primitives are ready for Twilio, intake, and frontend work.

---

## Phase 3: User Story 1 - Faster Demo Call Readiness (Priority: P1)

**Goal**: Demo operators can keep Azure Container Apps warm and tune VAD/turn thresholds for faster, noise-resistant caller turn commits.

**Independent Test**: Configure demo thresholds, process speech/noise frames, and verify normal speech commits faster while very short noise is ignored.

### Tests for User Story 1

- [X] T009 [P] [US1] Add configurable energy threshold tests in `tests/unit/test_vad_service.py`
- [X] T010 [P] [US1] Add configurable silence, pre-speech padding, and min-speech tests in `tests/unit/test_turn_manager.py`
- [X] T011 [P] [US1] Add AudioSessionProcessor threshold initialization tests in `tests/unit/test_audio_session_processor.py`

### Implementation for User Story 1

- [X] T012 [US1] Update `EnergyVadService` to use the configured energy threshold in `app/services/vad_service.py`
- [X] T013 [US1] Update `TurnManager` to accept configured thresholds and suppress commits below `min_speech_ms` in `app/services/turn_manager.py`
- [X] T014 [US1] Initialize `TurnManager` and `EnergyVadService` from `Settings` in `app/services/audio_session_processor.py`
- [X] T015 [US1] Include effective threshold and min-speech metadata in committed-turn debug payloads in `app/services/audio_session_processor.py`
- [X] T016 [US1] Add Azure Container Apps warm/low-cost commands and low-latency env guidance in `README.md`

**Checkpoint**: User Story 1 is independently testable with `pytest tests/unit/test_vad_service.py tests/unit/test_turn_manager.py tests/unit/test_audio_session_processor.py`.

---

## Phase 4: User Story 2 - Caller Can Interrupt Assistant Speech (Priority: P1)

**Goal**: Caller speech during assistant playback sends Twilio `clear`, stops unsent assistant audio where possible, and continues intake without duplicate responses.

**Independent Test**: Simulate assistant playback, send inbound media with speech, and verify `clear` is sent and the interrupted response is not duplicated.

### Tests for User Story 2

- [X] T017 [P] [US2] Add Twilio clear event builder tests in `tests/unit/test_twilio_audio_service.py`
- [X] T018 [P] [US2] Add barge-in debug payload tests in `tests/unit/test_audio_session_processor.py`
- [X] T019 [US2] Add Twilio WebSocket barge-in clear tests in `tests/unit/test_twilio_routes.py`

### Implementation for User Story 2

- [X] T020 [US2] Add `build_twilio_clear_event(stream_sid)` in `app/services/twilio_audio_service.py`
- [X] T021 [US2] Add per-call assistant playback state for speaking, active mark, interrupted response, and stream id in `app/api/routes_twilio.py`
- [X] T022 [US2] Pass assistant speaking state into Twilio media normalization so inbound frames set `assistant_is_speaking` in `app/api/routes_twilio.py`
- [X] T023 [US2] Emit explicit barge-in payload metadata from committed frames in `app/services/audio_session_processor.py`
- [X] T024 [US2] Send Twilio clear and record `barge_in.clear_sent` when barge-in is detected in `app/api/routes_twilio.py`
- [X] T025 [US2] Stop remaining unsent TTS chunks after the current response is interrupted in `app/api/routes_twilio.py`

**Checkpoint**: User Story 2 is independently testable with `pytest tests/unit/test_twilio_audio_service.py tests/unit/test_audio_session_processor.py tests/unit/test_twilio_routes.py`.

---

## Phase 5: User Story 3 - No-Reply Waits Until Playback Completes (Priority: P1)

**Goal**: No-reply timers do not fire while assistant audio is active and restart only after Twilio mark completion or a safe fallback completion.

**Independent Test**: Simulate greeting/follow-up marks and silence, then verify no-reply prompts wait for playback completion.

### Tests for User Story 3

- [X] T026 [P] [US3] Add assistant playback/no-reply timer tests in `tests/unit/test_call_lifecycle_service.py`
- [X] T027 [US3] Add Twilio mark receive and playback completion tests in `tests/unit/test_twilio_routes.py`
- [X] T028 [US3] Add simulated Twilio no-reply waits-for-mark regression in `tests/integration/test_twilio_media_flow.py`

### Implementation for User Story 3

- [X] T029 [US3] Extend `CallLifecycleState` with assistant playback reference fields in `app/services/call_lifecycle_service.py`
- [X] T030 [US3] Prevent `CallLifecycleService` from prompting or closing while assistant playback is active in `app/services/call_lifecycle_service.py`
- [X] T031 [US3] Track outbound mark names, purpose, and playback start/completion state in `app/api/routes_twilio.py`
- [X] T032 [US3] Handle inbound Twilio `mark` events and mark matching assistant audio completed in `app/api/routes_twilio.py`
- [X] T033 [US3] Start or resume no-reply timing from greeting/follow-up playback completion in `app/api/routes_twilio.py`
- [X] T034 [US3] Add safe fallback completion handling for missing or stale Twilio marks in `app/api/routes_twilio.py`

**Checkpoint**: User Story 3 is independently testable with `pytest tests/unit/test_call_lifecycle_service.py tests/unit/test_twilio_routes.py tests/integration/test_twilio_media_flow.py`.

---

## Phase 6: User Story 4 - Call Transcript and Audit Timeline (Priority: P2)

**Goal**: Developers and operators can open `/call-audit` and inspect recent caller/assistant timelines, TTS status, guardrails, and case outcomes.

**Independent Test**: Create a simulated intake session, call the audit APIs, and render the frontend dashboard with the returned timeline.

### Tests for User Story 4

- [X] T035 [P] [US4] Add intake session list/get store tests in `tests/unit/test_intake_session_store.py`
- [X] T036 [P] [US4] Add intake audit endpoint integration tests in `tests/integration/test_intake_api.py`
- [X] T037 [P] [US4] Add frontend intake session API client tests in `frontend/tests/intake-session-api-client.test.ts`
- [X] T038 [P] [US4] Add call audit dashboard rendering tests in `frontend/tests/call-audit-dashboard.test.tsx`

### Implementation for User Story 4

- [X] T039 [US4] Implement `list_recent(limit)` and `get_by_call_id(call_id)` in `app/services/intake_session_store.py`
- [X] T040 [US4] Append caller transcript, assistant response, TTS, guardrail, no-reply, barge-in, and case-created timeline events in `app/services/audio_session_processor.py`
- [X] T041 [US4] Append Twilio playback, mark, clear, no-reply, and close timeline events in `app/api/routes_twilio.py`
- [X] T042 [US4] Add `GET /api/intake/sessions`, `GET /api/intake/sessions/{session_id}`, and `GET /api/intake/calls/{call_id}` in `app/api/routes_intake.py`
- [X] T043 [US4] Add intake session API client functions in `frontend/lib/intake-session-api-client.ts`
- [X] T044 [US4] Extend frontend types for audit sessions and timeline events in `frontend/types/triage.ts`
- [X] T045 [US4] Add the `/call-audit` route page in `frontend/app/call-audit/page.tsx`
- [X] T046 [US4] Build the recent-session list and timeline detail UI in `frontend/components/call-audit/CallAuditDashboard.tsx`

**Checkpoint**: User Story 4 is independently testable with `pytest tests/unit/test_intake_session_store.py tests/integration/test_intake_api.py` and `cd frontend && npm test -- call-audit-dashboard.test.tsx intake-session-api-client.test.ts`.

---

## Phase 7: User Story 5 - Structured Troubleshooting Logs (Priority: P2)

**Goal**: Azure logs and audit timeline use consistent safe event names for call, greeting, turn, transcript, assistant response, TTS, barge-in, no-reply, and close events.

**Independent Test**: Run unit/integration tests that trigger the lifecycle events and assert safe event names appear without secrets or raw audio payloads.

### Tests for User Story 5

- [X] T047 [P] [US5] Add safe structured lifecycle log tests in `tests/unit/test_call_audit_logger.py`
- [X] T048 [US5] Add Twilio lifecycle structured log assertions in `tests/unit/test_twilio_routes.py`
- [X] T049 [US5] Add caller turn and assistant response log assertions in `tests/unit/test_audio_session_processor.py`

### Implementation for User Story 5

- [X] T050 [US5] Route required call lifecycle events through `call_audit_logger` in `app/api/routes_twilio.py`
- [X] T051 [US5] Log `caller.turn.committed`, `caller.turn.transcribed`, `intake.followup`, and `assistant.response` from `app/services/audio_session_processor.py`
- [X] T052 [US5] Enforce safe metadata redaction for secrets and raw audio payload fields in `app/services/call_audit_logger.py`
- [X] T053 [US5] Ensure Twilio helper metadata never logs outbound or inbound base64 audio payloads in `app/services/twilio_audio_service.py`

**Checkpoint**: User Story 5 is independently testable with `pytest tests/unit/test_call_audit_logger.py tests/unit/test_twilio_routes.py tests/unit/test_audio_session_processor.py`.

---

## Phase 8: Polish and Cross-Cutting Concerns

**Purpose**: Documentation, regression, and final verification after all desired user stories are complete.

- [X] T054 [P] Add barge-in behavior, call audit URL, structured log names, and troubleshooting notes in `README.md`
- [X] T055 [P] Update manual call audit and barge-in verification notes in `specs/009-call-latency-barge-in-audit/quickstart.md`
- [X] T056 Run backend compile gate for `app/` and `scripts/` with `python -m compileall app scripts`
- [X] T057 Run backend test suite for `tests/` with `pytest`
- [X] T058 Run frontend tests for `frontend/` with `cd frontend && npm test`
- [X] T059 Run frontend static build for `frontend/` with `cd frontend && npm run build`
- [X] T060 Review staged/untracked files and verify `.env.azure.local` is not staged in `.gitignore` and git status output

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 settings being available.
- **Phase 3 US1**: Depends on Phase 1; can start after settings tasks are complete.
- **Phase 4 US2**: Depends on Phase 2 audit primitives and Phase 3 turn/VAD metadata for best coverage.
- **Phase 5 US3**: Depends on Phase 4 playback state and TTS sender changes.
- **Phase 6 US4**: Depends on Phase 2 audit primitives; can proceed in parallel with US2/US3 after endpoint models are stable.
- **Phase 7 US5**: Depends on Phase 2 audit logger and benefits from US2/US3/US4 event wiring.
- **Phase 8 Polish**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 Faster Demo Call Readiness**: First MVP increment. No dependency on other user stories after setup.
- **US2 Caller Can Interrupt Assistant Speech**: Depends on playback state and clear helper, but not on `/call-audit` UI.
- **US3 No-Reply Waits Until Playback Completes**: Depends on assistant playback state introduced for US2.
- **US4 Call Transcript and Audit Timeline**: Depends on foundational audit/session store changes; can be delivered after or alongside US2/US3.
- **US5 Structured Troubleshooting Logs**: Cross-cuts all routes/services and should be finalized after core events exist.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001 design is understood.
- T007 and T008 can run in parallel with T004-T006 implementation if tests are written first.
- US1 test tasks T009-T011 can run in parallel.
- US2 test tasks T017-T019 can run in parallel once expected contracts are agreed.
- US4 frontend tasks T043-T046 can run in parallel with backend endpoint tasks T039-T042 after the API contract is stable.
- Polish documentation T054-T055 can run in parallel with final verification gates T056-T059.

---

## Parallel Examples

### User Story 1

```text
Task: "Add configurable energy threshold tests in tests/unit/test_vad_service.py"
Task: "Add configurable silence, pre-speech padding, and min-speech tests in tests/unit/test_turn_manager.py"
Task: "Add AudioSessionProcessor threshold initialization tests in tests/unit/test_audio_session_processor.py"
```

### User Story 4

```text
Task: "Add frontend intake session API client tests in frontend/tests/intake-session-api-client.test.ts"
Task: "Add call audit dashboard rendering tests in frontend/tests/call-audit-dashboard.test.tsx"
Task: "Add intake audit endpoint integration tests in tests/integration/test_intake_api.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) to reduce turn latency and document warm backend commands.
3. Run the US1 checkpoint tests.
4. Demo faster turn commit before adding playback interruption.

### Incremental Delivery

1. Add US1 latency tuning.
2. Add US2 barge-in clear.
3. Add US3 mark-aware no-reply timing.
4. Add US4 call audit API and dashboard.
5. Add US5 final structured logging and redaction sweep.
6. Run all final gates in Phase 8.

### Safety Notes

- Do not add Azure Voice Live.
- Do not change Twilio route paths.
- Do not log raw audio payloads or secrets.
- Preserve TTS speak-back behavior.
- Keep Azure/Twilio credentials optional in automated tests.

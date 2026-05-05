# Tasks: Azure Realtime Voice Provider Spike

**Input**: Design documents from `specs/010-azure-realtime-voice/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase when files do not overlap
- **[US1]**: Preserve current Twilio call flow
- **[US2]**: Manually test Azure realtime voice
- **[US3]**: Fallback safely on realtime failure
- **[US4]**: Compare latency across voice paths

## Phase 1: Setup

**Purpose**: Add default-disabled realtime configuration without changing runtime behavior.

- [X] T001 Add realtime env defaults to `.env.example`
- [X] T002 Add realtime settings fields and env parsing in `app/core/config.py`
- [X] T003 Add realtime configuration health helpers in `app/core/config.py`
- [X] T004 [P] Add realtime provider/status enums and result models in `app/models/realtime.py`
- [X] T005 [P] Add config default tests for `ENABLE_REALTIME_VOICE=false` and `REALTIME_PROVIDER=none` in `tests/unit/test_telephony_config.py`

---

## Phase 2: Foundational

**Purpose**: Create shared realtime provider and latency building blocks before user-story routing.

- [X] T006 Add `RealtimeVoiceProvider` protocol, connection/send/event result dataclasses, and provider selection helper in `app/services/realtime_voice_provider.py`
- [X] T007 Add safe latency stage helper in `app/services/realtime_latency.py`
- [X] T008 Add crisis-intake instruction builder for realtime sessions in `app/services/realtime_voice_provider.py`
- [X] T009 Add realtime health fields to `/api/health/azure` response models in `app/models/triage.py`
- [X] T010 Add realtime health output to `app/api/routes_audio.py`
- [X] T011 [P] Add unit tests for realtime provider selection defaults and missing config in `tests/unit/test_realtime_provider_selection.py`
- [X] T012 [P] Add unit tests for latency helper metadata redaction/no raw audio in `tests/unit/test_realtime_voice_provider.py`

---

## Phase 3: User Story 1 - Preserve Current Twilio Call Flow (Priority: P1)

**Goal**: Realtime disabled mode leaves the current Twilio route and current audio processing behavior unchanged.

**Independent Test**: Run existing simulated Twilio tests with realtime disabled and verify no realtime provider connection is attempted.

- [X] T013 [P] [US1] Add test that Twilio start with realtime disabled does not create realtime provider in `tests/integration/test_twilio_media_flow.py`
- [X] T014 [P] [US1] Add test that existing Twilio media fallback payloads remain unchanged with realtime disabled in `tests/integration/test_twilio_media_flow.py`
- [X] T015 [US1] Add guarded realtime routing decision point to `app/api/routes_twilio.py` without changing current route paths
- [X] T016 [US1] Ensure realtime disabled path uses existing `AudioSessionProcessor` behavior in `app/api/routes_twilio.py`
- [X] T017 [US1] Add safe debug payload for realtime disabled fallback decision in `app/api/routes_twilio.py`

---

## Phase 4: User Story 2 - Manually Test Azure Realtime Voice (Priority: P2)

**Goal**: Enable one experimental Azure realtime provider at a time and stream mocked provider output back to Twilio.

**Independent Test**: Use mocked provider WebSocket events to verify provider connect, input send, output receive, and Twilio media event shape.

- [X] T018 [P] [US2] Add Azure Voice Live realtime provider skeleton in `app/services/azure_voice_live_realtime_provider.py`
- [X] T019 [P] [US2] Add Azure OpenAI GPT Realtime provider skeleton in `app/services/azure_openai_realtime_provider.py`
- [X] T020 [US2] Implement provider WebSocket URI construction and credential redaction helpers in `app/services/realtime_voice_provider.py`
- [X] T021 [US2] Implement provider connection lifecycle skeletons in `app/services/azure_voice_live_realtime_provider.py`
- [X] T022 [US2] Implement provider connection lifecycle skeletons in `app/services/azure_openai_realtime_provider.py`
- [X] T023 [US2] Implement Twilio media frame forwarding to active realtime provider in `app/api/routes_twilio.py`
- [X] T024 [US2] Implement realtime provider output-to-Twilio media event forwarding in `app/api/routes_twilio.py`
- [X] T025 [P] [US2] Add mocked Azure Voice Live provider event tests in `tests/unit/test_realtime_voice_provider.py`
- [X] T026 [P] [US2] Add mocked Azure OpenAI Realtime provider event tests in `tests/unit/test_realtime_voice_provider.py`
- [X] T027 [US2] Add simulated Twilio stream test for mocked realtime audio output in `tests/integration/test_twilio_media_flow.py`

---

## Phase 5: User Story 3 - Fallback Safely on Realtime Failure (Priority: P3)

**Goal**: Any realtime configuration, connection, send, receive, or output failure falls back to the current turn-based path.

**Independent Test**: Enable realtime with missing/failing settings and verify the call still reaches current `AudioSessionProcessor` behavior.

- [X] T028 [P] [US3] Add fallback tests for missing Azure realtime config in `tests/unit/test_realtime_fallback.py`
- [X] T029 [P] [US3] Add fallback tests for provider connect/send/receive failures in `tests/unit/test_realtime_fallback.py`
- [X] T030 [US3] Implement realtime fallback decision object and warnings in `app/services/realtime_voice_provider.py`
- [X] T031 [US3] Route realtime provider configuration failure back to `AudioSessionProcessor` in `app/api/routes_twilio.py`
- [X] T032 [US3] Route realtime provider runtime failure back to `AudioSessionProcessor` in `app/api/routes_twilio.py`
- [X] T033 [US3] Ensure realtime fallback does not duplicate case creation or assistant speak-back in `app/api/routes_twilio.py`
- [X] T034 [US3] Add call audit events for `realtime.error` and `realtime.fallback` in `app/api/routes_twilio.py`

---

## Phase 6: User Story 4 - Compare Latency Across Voice Paths (Priority: P4)

**Goal**: Logs and audit events expose enough safe timing data to compare current pipeline and realtime provider behavior.

**Independent Test**: Run mocked realtime events and verify expected log/audit event names with `latency_ms`.

- [X] T035 [P] [US4] Add latency logging tests for realtime connect/input/output/response/fallback in `tests/unit/test_realtime_voice_provider.py`
- [X] T036 [P] [US4] Add route log tests for `realtime.audio.input.sent` and `realtime.audio.output.received` in `tests/unit/test_twilio_routes.py`
- [X] T037 [US4] Log `realtime.connected` with safe latency metadata in `app/api/routes_twilio.py`
- [X] T038 [US4] Log `realtime.audio.input.sent` with safe latency metadata in `app/api/routes_twilio.py`
- [X] T039 [US4] Log `realtime.audio.output.received` with safe latency metadata in `app/api/routes_twilio.py`
- [X] T040 [US4] Log `realtime.response.started` and `realtime.response.completed` in `app/api/routes_twilio.py`
- [X] T041 [US4] Add realtime latency/audit entries to `app/services/call_audit_logger.py`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, safety review, and final quality gates.

- [X] T042 [P] Update `README.md` with realtime feature flags, Azure OpenAI Realtime region warning, Voice Live setup notes, and manual test steps
- [X] T043 [P] Update `specs/010-azure-realtime-voice/quickstart.md` with any implementation-specific test commands
- [X] T044 [P] Review realtime logs for secret/raw audio redaction in `app/services/realtime_voice_provider.py`
- [X] T045 [P] Review Twilio realtime routing for unchanged route paths and no ACS/SMS/dispatch changes in `app/api/routes_twilio.py`
- [X] T046 Run `python -m compileall app scripts`
- [X] T047 Run `pytest`
- [X] T048 Run `cd frontend && npm test`
- [X] T049 Run `cd frontend && npm run build`
- [X] T050 Review `git status --short` and confirm no secrets or `.env.azure.local` are staged

## Dependencies

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Depends on Foundational and can build after US1 routing guard exists
- **US3 (Phase 5)**: Depends on US2 provider/session skeletons
- **US4 (Phase 6)**: Depends on US2 provider events and US3 fallback events
- **Polish (Phase 7)**: Depends on desired user-story scope

### User Story Dependencies

- **US1** is the MVP and must pass before enabling realtime work.
- **US2** can be implemented after the realtime interface exists but should keep US1 tests passing.
- **US3** depends on provider skeletons from US2.
- **US4** depends on event flow from US2 and fallback flow from US3.

## Parallel Execution Examples

### US1

```text
T013 and T014 can run in parallel because they add independent integration assertions.
```

### US2

```text
T018 and T019 can run in parallel because each provider skeleton owns a different file.
T025 and T026 can run in parallel after the shared realtime provider contract exists.
```

### US3

```text
T028 and T029 can run in parallel because they cover different fallback conditions.
```

### US4

```text
T035 and T036 can run in parallel because service-level and route-level log tests touch different test files.
```

## Implementation Strategy

### MVP First

Complete T001-T017 first. This proves the safest and most important slice: realtime settings exist, are disabled by default, health/debug output is explicit, and the current Twilio path remains unchanged.

### Incremental Delivery

1. Add default-disabled config and provider selection.
2. Add provider skeletons with mocked events only.
3. Add Twilio routing behind `ENABLE_REALTIME_VOICE`.
4. Add fallback behavior for every failure mode.
5. Add latency logs and README manual validation steps.

### Final Verification

Do not enable Azure realtime in automated tests. The final gates remain:

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

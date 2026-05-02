# Tasks: Azure Speech Validation Build

**Input**: Design documents from `/specs/002-azure-speech-validation/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Goal**: Minimal safe enhancement from mock-local demo to real Azure Speech validation: committed local microphone PCM frames are persisted as WAV, passed to the Azure Speech/OpenAI provider through `CallerTurn.audio_ref`, and surfaced in API/UI debug output without breaking mock mode.

**Out of Scope**: Do not implement Twilio, Azure Communication Services, real phone numbers, real Azure Voice Live streaming, or production auth in this task set.

## Phase 1: Setup and Shared Metadata

**Purpose**: Add small shared configuration and provider-result metadata before touching the audio path.

- [X] T001 Add audio artifact storage setting in `app/core/config.py` and `.env.example`
  - Files to modify: `app/core/config.py`, `.env.example`
  - Acceptance criteria: settings expose `audio_store_path` with default `.data/audio`; no secrets are logged or required; existing config behavior remains compatible.
  - Test command: `pytest tests/unit/test_provider_fallback.py`
  - Dependency: none

- [X] T002 Extend provider result metadata in `app/services/voice_agent_provider.py`
  - Files to modify: `app/services/voice_agent_provider.py`
  - Acceptance criteria: `VoiceProviderResult` includes `transcript_source: "mock" | "azure_speech_stt" | "fallback"` and optional `audio_ref`; existing provider protocol remains async-compatible.
  - Test command: `python -m compileall app/services/voice_agent_provider.py`
  - Dependency: T001

- [X] T003 Update mock provider result metadata in `app/services/mock_voice_provider.py`
  - Files to modify: `app/services/mock_voice_provider.py`
  - Acceptance criteria: mock transcript and mock turn flows return `transcript_source="mock"` and keep deterministic Thai RED behavior exactly as before.
  - Test command: `pytest tests/integration/test_thai_transcript_to_red_case.py tests/integration/test_mock_local_mic_flow.py`
  - Dependency: T002

---

## Phase 2: Audio Buffering and WAV Persistence

**Purpose**: Add the temporary WAV artifact path required for real speech validation.

- [X] T004 [P] Add WAV persistence tests in `tests/unit/test_audio_buffer_service.py`
  - Files to modify: `tests/unit/test_audio_buffer_service.py`
  - Acceptance criteria: tests assert committed PCM16 frames are written as a valid WAV file with mono channel, 16-bit sample width, expected sample rate, expected frame count, and path `.data/audio/{session_id}/{turn_id}.wav` under a test store root.
  - Test command: `pytest tests/unit/test_audio_buffer_service.py`
  - Dependency: T002

- [X] T005 Implement audio buffer service in `app/services/audio_buffer_service.py`
  - Files to modify: `app/services/audio_buffer_service.py`
  - Acceptance criteria: service accepts validated `AudioFrame` objects, keeps a pre-speech ring buffer, records active speech frames, writes committed turns to WAV with Python standard library behavior, returns `audio_ref`, and handles empty/no-frame turns with a clear error.
  - Test command: `pytest tests/unit/test_audio_buffer_service.py`
  - Dependency: T004

- [X] T006 Add audio buffer error/debug model support in `app/models/audio.py`
  - Files to modify: `app/models/audio.py`
  - Acceptance criteria: audio debug metadata can carry `audio_ref` and `audio_debug_id` without breaking existing `AudioDebugEvent`/`CallerTurn` validation; `CallerTurn.audio_ref` remains optional.
  - Test command: `pytest tests/unit/test_vad_service.py tests/unit/test_triage_schema.py`
  - Dependency: T005

---

## Phase 3: Turn `audio_ref` Integration

**Purpose**: Wire the new WAV writer into `/ws/local-audio` when VAD commits a turn.

- [X] T007 [P] Add WebSocket audio_ref regression assertions in `tests/integration/test_mock_local_mic_flow.py`
  - Files to modify: `tests/integration/test_mock_local_mic_flow.py`
  - Acceptance criteria: mock local mic flow still creates a RED case and now also asserts `audio_ref` is present in the case-created message and points to a readable WAV file.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py`
  - Dependency: T005

- [X] T008 Wire `AudioBufferService` into local audio WebSocket in `app/api/routes_audio.py`
  - Files to modify: `app/api/routes_audio.py`
  - Acceptance criteria: accepted `audio.frame` messages are passed to the buffer service; when `TurnManager` returns a committed turn, the route writes the WAV and sets `committed_turn.audio_ref` before calling the provider.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py`
  - Dependency: T005, T007

- [X] T009 Add turn committed audio metadata to debug events in `app/api/routes_audio.py`
  - Files to modify: `app/api/routes_audio.py`
  - Acceptance criteria: the `turn.committed` debug event metadata includes `turn_id`, `audio_ref`, and `audio_debug_id` after the WAV is written; existing VAD debug event order remains stable.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py tests/unit/test_vad_service.py`
  - Dependency: T008

---

## Phase 4: AzureSpeechOpenAIProvider Hardening

**Purpose**: Make Azure provider behavior prove real STT on `audio_ref` and fail safely.

- [X] T010 [P] Add Azure provider audio_ref usage tests in `tests/unit/test_azure_speech_provider.py`
  - Files to modify: `tests/unit/test_azure_speech_provider.py`
  - Acceptance criteria: tests monkeypatch the speech-recognition seam and assert `process_turn()` uses `CallerTurn.audio_ref`, returns the recognized transcript, sets `transcript_source="azure_speech_stt"`, and passes the transcript into triage.
  - Test command: `pytest tests/unit/test_azure_speech_provider.py`
  - Dependency: T002

- [X] T011 [P] Add Azure provider safe failure tests in `tests/unit/test_azure_speech_provider.py`
  - Files to modify: `tests/unit/test_azure_speech_provider.py`
  - Acceptance criteria: tests assert missing audio, missing speech credentials in Azure provider mode, recognizer exceptions, and empty recognizer text return `transcript_source="fallback"`, low confidence, `human_review_required=true`, provider warnings, and no hardcoded Thai flood transcript.
  - Test command: `pytest tests/unit/test_azure_speech_provider.py`
  - Dependency: T010

- [X] T012 Refactor Azure Speech recognition seam in `app/services/azure_speech_provider.py`
  - Files to modify: `app/services/azure_speech_provider.py`
  - Acceptance criteria: provider has a mockable method for recognizing `audio_ref` with Azure Speech; successful recognition returns real transcript text; manual credential use is isolated from normal tests.
  - Test command: `pytest tests/unit/test_azure_speech_provider.py`
  - Dependency: T010

- [X] T013 Replace hardcoded Azure failure transcript with controlled fallback in `app/services/azure_speech_provider.py`
  - Files to modify: `app/services/azure_speech_provider.py`
  - Acceptance criteria: Azure provider failure paths never return the deterministic Thai flood sentence; fallback triage is low-confidence, review-required, pending, and includes missing transcript/location fields plus provider warnings.
  - Test command: `pytest tests/unit/test_azure_speech_provider.py tests/unit/test_provider_fallback.py`
  - Dependency: T011, T012

- [X] T014 Update optional Voice Live provider metadata in `app/services/azure_voice_live_provider.py`
  - Files to modify: `app/services/azure_voice_live_provider.py`
  - Acceptance criteria: optional provider returns valid `VoiceProviderResult` with `transcript_source` and `audio_ref` fields when used; Voice Live remains optional and does not block Azure Speech/OpenAI validation.
  - Test command: `python -m compileall app/services/azure_voice_live_provider.py`
  - Dependency: T002

---

## Phase 5: API/WebSocket Response Contract Update

**Purpose**: Expose source metadata and warnings through the local-audio contract.

- [X] T015 [P] Add WebSocket contract assertions in `tests/integration/test_mock_local_mic_flow.py`
  - Files to modify: `tests/integration/test_mock_local_mic_flow.py`
  - Acceptance criteria: `triage.case.created` includes `provider_mode`, `transcript_source`, `audio_ref`, `warnings`, `transcript`, and `record`; mock flow returns `transcript_source="mock"`.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py`
  - Dependency: T009, T013

- [X] T016 Update case-created WebSocket payload in `app/api/routes_audio.py`
  - Files to modify: `app/api/routes_audio.py`
  - Acceptance criteria: response matches `contracts/local-audio-websocket.md`, including `transcript_source`, `audio_ref`, and provider warnings for mock, Azure success, and Azure fallback results.
  - Test command: `pytest tests/integration/test_mock_local_mic_flow.py`
  - Dependency: T015

- [X] T017 Update provider contract documentation in `specs/002-azure-speech-validation/contracts/provider-result.md`
  - Files to modify: `specs/002-azure-speech-validation/contracts/provider-result.md`
  - Acceptance criteria: contract reflects final field names and fallback semantics used by code; no Twilio/ACS implementation contract is added.
  - Test command: N/A
  - Dependency: T016

---

## Phase 6: Frontend Debug UI Update

**Purpose**: Make real-vs-mock transcript provenance visible in the operator/developer console.

- [X] T018 [P] Update frontend WebSocket types in `frontend/types/triage.ts`
  - Files to modify: `frontend/types/triage.ts`
  - Acceptance criteria: `VoiceWsMessage` includes `transcript_source`, `audio_ref`, and `warnings` on `triage.case.created`; transcript source enum matches backend contract.
  - Test command: `cd frontend && npm test`
  - Dependency: T016

- [X] T019 [P] Add frontend tests for source and warnings in `frontend/tests/voice-debug-console.test.tsx`
  - Files to modify: `frontend/tests/voice-debug-console.test.tsx`
  - Acceptance criteria: tests cover display of provider mode, transcript source, audio reference/debug id, and provider warnings for a WebSocket-created case.
  - Test command: `cd frontend && npm test -- voice-debug-console`
  - Dependency: T018

- [X] T020 Update voice debug console UI in `frontend/components/voice/VoiceDebugConsole.tsx`
  - Files to modify: `frontend/components/voice/VoiceDebugConsole.tsx`
  - Acceptance criteria: UI displays source/provider mode, transcript source, audio reference or debug id, provider warnings, transcript, triage JSON, safety result, and case preview without layout overflow.
  - Test command: `cd frontend && npm test -- voice-debug-console`
  - Dependency: T019

- [X] T021 Update frontend API/client tests if needed in `frontend/tests/triage-api-client.test.ts` and `frontend/tests/audio-client.test.ts`
  - Files to modify: `frontend/tests/triage-api-client.test.ts`, `frontend/tests/audio-client.test.ts`
  - Acceptance criteria: existing manual transcript API tests and PCM16 conversion tests continue passing after type/metadata changes.
  - Test command: `cd frontend && npm test`
  - Dependency: T020

---

## Phase 7: Tests and Manual Azure Validation Guard

**Purpose**: Add credential-gated manual validation while keeping normal tests offline-safe.

- [X] T022 [P] Add skipped/manual Azure Speech Thai WAV test in `tests/integration/test_azure_speech_manual.py`
  - Files to modify: `tests/integration/test_azure_speech_manual.py`
  - Acceptance criteria: test is skipped unless Azure Speech/OpenAI env vars and `AZURE_SPEECH_TEST_WAV` are present; when enabled, it verifies `transcript_source="azure_speech_stt"` and transcript is not hardcoded.
  - Test command: `pytest tests/integration/test_azure_speech_manual.py`
  - Dependency: T013

- [X] T023 Run and fix full backend regression suite
  - Files to modify: any backend/test files needed to preserve existing behavior
  - Acceptance criteria: all existing 43 backend tests plus new tests pass without Azure credentials; no Twilio/ACS tests are added.
  - Test command: `pytest`
  - Dependency: T016, T022

- [X] T024 Run and fix full frontend regression suite
  - Files to modify: any frontend files needed to preserve existing behavior
  - Acceptance criteria: Vitest suite passes and no debug UI regressions are introduced.
  - Test command: `cd frontend && npm test`
  - Dependency: T021

---

## Phase 8: README Update

**Purpose**: Document the real Azure Speech validation path and safe failure behavior.

- [X] T025 Update real Azure Speech validation documentation in `README.md`
  - Files to modify: `README.md`
  - Acceptance criteria: README includes mock mode preservation, `.data/audio` WAV artifact behavior, Azure env setup, Thai WAV manual validation, local microphone validation, expected `transcript_source` values, and Azure failure fallback behavior.
  - Test command: N/A
  - Dependency: T022

- [X] T026 Update feature quickstart with final commands in `specs/002-azure-speech-validation/quickstart.md`
  - Files to modify: `specs/002-azure-speech-validation/quickstart.md`
  - Acceptance criteria: quickstart matches final README commands and clearly states Azure credential tests are skipped unless configured.
  - Test command: N/A
  - Dependency: T025

---

## Phase 9: Final Verification

**Purpose**: Prove the enhancement is safe, offline-compatible, and ready for review.

- [X] T027 Run backend compile check
  - Files to modify: none unless compile failures are found
  - Acceptance criteria: backend imports and compiles successfully.
  - Test command: `python -m compileall app`
  - Dependency: T023

- [X] T028 Run full backend test suite
  - Files to modify: none unless test failures are found
  - Acceptance criteria: full backend suite passes without Azure credentials; manual Azure test is skipped unless explicitly configured.
  - Test command: `pytest`
  - Dependency: T027

- [X] T029 Run frontend unit tests and production build
  - Files to modify: none unless test/build failures are found
  - Acceptance criteria: frontend tests and production build pass.
  - Test command: `cd frontend && npm test && npm run build`
  - Dependency: T024

- [X] T030 Record final verification results in `specs/002-azure-speech-validation/tasks.md`
  - Files to modify: `specs/002-azure-speech-validation/tasks.md`
  - Acceptance criteria: tasks file includes final pass/fail results for compile, pytest, frontend tests, frontend build, and notes that real Azure Speech validation is manual/skipped without credentials.
  - Test command: N/A
  - Dependency: T028, T029

---

## Verification Notes

- 2026-05-02: `python -m compileall app` passed.
- 2026-05-02: `pytest` passed with 50 tests and 1 skipped credential-gated Azure Speech manual test.
- 2026-05-02: `cd frontend && npm test` passed with 6 tests.
- 2026-05-02: `cd frontend && npm run build` passed.
- Real Azure Speech validation remains manual/skipped unless Azure Speech/OpenAI credentials and `AZURE_SPEECH_TEST_WAV` are configured.

---

## Dependencies and Execution Order

### Required Group Order

1. Audio buffering and WAV persistence: T004-T006.
2. Turn `audio_ref` integration: T007-T009.
3. AzureSpeechOpenAIProvider hardening: T010-T014.
4. API/WebSocket response contract update: T015-T017.
5. Frontend debug UI update: T018-T021.
6. Tests: T022-T024 plus test-first tasks in earlier phases.
7. README update: T025-T026.
8. Final verification: T027-T030.

### Phase Dependencies

- Phase 1 setup metadata blocks all provider/UI contract work.
- Phase 2 audio buffering blocks WebSocket audio_ref integration.
- Phase 3 turn integration blocks real Azure provider audio_ref validation through WebSocket.
- Phase 4 provider hardening can begin after metadata is available but must finish before response contract completion.
- Phase 5 response contract blocks frontend UI updates.
- Phase 6 frontend UI blocks frontend final verification.
- Phase 7 tests must pass before docs and final verification are considered complete.

### User Story Mapping

- **US1 Validate Real Thai Audio Intake**: T004-T018, T022, T025-T030.
- **US2 Preserve Mock Demo Reliability**: T003, T007-T009, T015-T016, T023-T024.
- **US3 Surface Speech Failures Safely**: T011-T013, T016, T019-T020, T022-T030.

### Parallel Opportunities

- T004 can be written while T003 is completed because it targets new test files.
- T010 and T011 can be prepared in parallel in the same test file before provider implementation.
- T014 can run in parallel with T012/T013 after T002.
- T018 and T019 can run in parallel after T016.
- T022, T025, and T026 can be prepared while frontend verification work proceeds, after provider semantics are stable.

## Implementation Strategy

### MVP First

1. Complete T001-T003 to establish metadata without behavior changes.
2. Complete T004-T009 to prove local committed audio becomes a WAV and reaches `CallerTurn.audio_ref`.
3. Complete T010-T016 to prove Azure provider uses `audio_ref` and fails safely.
4. Stop and validate: `python -m compileall app && pytest`.

### Incremental Completion

1. Add frontend source/warning display after backend payloads are stable.
2. Add manual Azure Speech validation guard and docs.
3. Run full backend/frontend verification.

## Notes

- `[P]` tasks touch separate files or are safe to prepare in parallel after their listed dependencies.
- Tests that require Azure credentials must be skipped unless explicit environment variables are present.
- Do not implement Twilio or ACS in this feature.

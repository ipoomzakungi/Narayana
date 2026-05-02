# Implementation Plan: Azure Speech Validation Build

**Branch**: `002-azure-speech-validation` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/002-azure-speech-validation/spec.md`

## Summary

Enhance the existing Narayana Azure Voice Gateway so the local microphone flow can validate real audio-to-transcript-to-triage through Azure Speech and Azure OpenAI. The implementation keeps mock mode as the default offline path, persists committed PCM16 turns as temporary WAV files, passes the WAV path through `CallerTurn.audio_ref`, removes hardcoded Thai crisis text from Azure failure paths, and exposes transcript source, audio reference, and provider warnings in the WebSocket response and debug UI.

## Technical Context

**Language/Version**: Python 3.11+ backend, TypeScript/React/Next.js frontend  
**Primary Dependencies**: FastAPI, Pydantic, Azure Cognitive Services Speech SDK, OpenAI Azure client, pytest, Next.js, Vitest  
**Storage**: Temporary local audio files under `.data/audio/{session_id}/{turn_id}.wav`; existing local JSON/Cosmos case storage unchanged  
**Testing**: pytest for backend unit/integration tests; Vitest and Next build for frontend checks  
**Target Platform**: Local developer machine for hackathon validation; Azure-ready backend remains container-compatible  
**Project Type**: Web-service backend plus browser debug console  
**Performance Goals**: Committed local audio turns should be persisted and handed to speech recognition within 1 second of turn commit; full manual validation result should appear within 30 seconds with valid credentials  
**Constraints**: No Twilio or ACS dependency; no Azure credentials required for normal automated tests; no automatic dispatch/close/downgrade; speech failures must be visible and human-review-required  
**Scale/Scope**: Single-session/local hackathon demo validation path; temporary audio artifacts for debug only, not production retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The repository constitution still contains template placeholders and no enforceable project-specific rules. This plan applies the active project safety gates from the existing spec and implementation:

- Preserve mock mode and existing tests.
- Require human review for RED, low-confidence, unclear, or missing-location cases.
- Do not dispatch, close, reject, or downgrade emergency help automatically.
- Keep phone-provider integrations as disabled V1 placeholders.
- Keep normal automated tests independent of real Azure credentials.

Gate result: PASS. No constitution violations or unresolved clarifications.

## Project Structure

### Documentation (this feature)

```text
specs/002-azure-speech-validation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── local-audio-websocket.md
│   └── provider-result.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes_audio.py                 # buffer frames, persist committed WAV, return debug metadata
├── models/
│   └── audio.py                        # CallerTurn/audio metadata extensions if needed
└── services/
    ├── audio_buffer_service.py         # new PCM16 frame buffer + WAV writer
    ├── azure_speech_provider.py        # real audio_ref STT + safe fallback
    ├── voice_agent_provider.py         # VoiceProviderResult metadata fields
    └── mock_voice_provider.py          # preserve deterministic mock source metadata

frontend/
├── components/voice/VoiceDebugConsole.tsx
├── types/triage.ts
└── tests/

tests/
├── unit/
│   ├── test_audio_buffer_service.py
│   ├── test_provider_fallback.py
│   └── test_safety_rules.py
└── integration/
    └── test_mock_local_mic_flow.py
```

**Structure Decision**: Use the existing backend/frontend layout and add one focused backend service for audio buffering. Avoid introducing a separate audio persistence subsystem, database table, or phone-provider path for V1.

## Phase 0: Research

Research is captured in [research.md](./research.md). Key decisions:

- Use Python's standard `wave` module to write PCM16 mono WAV files from validated 20 ms audio frames.
- Keep buffering in the WebSocket route through a small `AudioBufferService` rather than moving VAD state management into the provider.
- Extend provider result metadata with `transcript_source` and `audio_ref`.
- Use controlled fallback triage for Azure Speech failures instead of substituting the mock flood transcript.
- Keep Azure-credential tests manual or skipped by explicit environment guards.

## Phase 1: Design & Contracts

Design artifacts:

- [data-model.md](./data-model.md)
- [contracts/local-audio-websocket.md](./contracts/local-audio-websocket.md)
- [contracts/provider-result.md](./contracts/provider-result.md)
- [quickstart.md](./quickstart.md)

## Implementation Approach

1. Add `AudioBufferService` to append validated PCM16 frames by session, include a small pre-speech ring buffer, collect speech frames, and write the committed turn to `.data/audio/{session_id}/{turn_id}.wav`.
2. Wire `routes_audio.py` so every accepted audio frame is offered to the buffer service, and when `TurnManager` emits `committed_turn`, the route writes the WAV and sets `committed_turn.audio_ref`.
3. Extend `VoiceProviderResult` with:
   - `transcript_source`: `mock`, `azure_speech_stt`, or `fallback`
   - `audio_ref`: optional path or debug identifier
4. Update `MockVoiceProvider` to set `transcript_source=mock` and preserve deterministic behavior.
5. Update `AzureSpeechOpenAIProvider`:
   - If Azure Speech is configured and `audio_ref` exists, call Azure Speech STT on that WAV.
   - If Azure Speech is missing in Azure provider mode, return a safe fallback with warnings.
   - If Azure Speech fails or returns no text, return a safe fallback with warnings.
   - Never use the mock flood transcript in Azure provider failure paths.
6. Keep `AzureOpenAITriageProvider` as the structured triage step for successful transcripts and still apply safety rules after model output.
7. Update `/ws/local-audio` case-created response to include `transcript_source`, `audio_ref`, and `provider_warnings`.
8. Update the debug UI and types to show provider mode, transcript source, audio reference/debug ID, and warnings.
9. Add tests for WAV validity, provider failure behavior, mock regression, and WebSocket regression.
10. Update README with real Azure Speech validation steps and manual/skipped test guidance.

## Quality Gates

- `python -m compileall app`
- `pytest`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual Azure Speech validation only when `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, Azure OpenAI settings, and a Thai WAV sample are available.

## Post-Design Constitution Check

Gate result: PASS.

The design keeps the enhancement minimal, preserves offline/mock behavior, adds tests before credential-gated manual validation, and maintains the no-dispatch/no-phone-provider safety boundaries. No complexity exceptions are required.

## Complexity Tracking

No constitution violations or complexity exceptions.

# Implementation Plan: Optional Twilio TTS Speak-Back

**Branch**: `006-twilio-tts-speakback` | **Date**: 2026-05-03 | **Spec**: `specs/006-twilio-tts-speakback/spec.md`  
**Input**: Feature specification from `specs/006-twilio-tts-speakback/spec.md`

## Summary

Add optional Twilio speak-back for Narayana calls. The existing Twilio Media Stream continues to receive caller audio and the existing audio/intake pipeline continues to generate `response_text`. When `ENABLE_TWILIO_TTS_RESPONSE=true`, the Twilio WebSocket will synthesize safe response text through Azure Speech TTS, convert or request Twilio-compatible 8 kHz mu-law audio, send outbound Twilio media events over the same WebSocket, then send a Twilio mark event. The feature is disabled by default and must not change the existing Twilio webhook path, media WebSocket path, inbound audio decode behavior, or case creation behavior.

The independently testable MVP is a mocked-TTS Twilio WebSocket flow: with multi-turn intake and speak-back enabled, an `intake.followup` or `triage.case.created` payload containing `response_text` results in normal JSON debug output plus outbound Twilio `media` and `mark` messages.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript/React/Next.js frontend remains display-only for this feature.  
**Primary Dependencies**: FastAPI WebSocket routes, Pydantic, Azure Cognitive Services Speech SDK, Python `audioop`/`audioop-lts`-compatible conversion path, existing Twilio media normalizer, pytest, Vitest for unchanged UI regression.  
**Storage**: No new persistent storage. TTS results are transient in memory and are not written to case storage by default.  
**Testing**: `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`.  
**Target Platform**: FastAPI backend on Azure Container Apps for Twilio WebSocket support; frontend remains Azure Static Web Apps.  
**Project Type**: Web service backend plus existing static dashboard frontend.  
**Performance Goals**: Speak-back must not block or fail case creation. Outbound chunks should be emitted immediately after synthesis in 20 ms Twilio-compatible chunks. Response text is capped to avoid long call playback.  
**Constraints**: `ENABLE_TWILIO_TTS_RESPONSE=false` by default; do not rewrite inbound audio; do not change `/api/telephony/twilio/incoming-call` or `/ws/telephony/twilio/{call_id}`; do not implement ACS, SMS, Cosmos DB, emergency dispatch, or TTS playback in browser; do not log secrets or raw audio payloads.  
**Scale/Scope**: One TTS service, outbound helper functions in `twilio_audio_service`, one TTS test route, health fields, gated Twilio WebSocket speak-back, docs, and targeted tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and defines no enforceable project-specific gates. This plan applies Narayana's active safety and compatibility constraints:

- Existing inbound Twilio routes and direct simulated Twilio behavior must remain compatible when TTS is disabled.
- TTS must be opt-in and must not require Azure credentials for automated tests.
- Spoken text must pass safety sanitization before synthesis.
- TTS failures must not block call handling, follow-up payloads, case creation, or case escalation.
- No secrets or raw audio payloads may be logged or returned by test endpoints.

Pre-design status: PASS. No unresolved clarifications.

Post-design status: PASS. Research, model, contracts, and quickstart preserve the default-disabled scope and safety constraints.

## Project Structure

### Documentation (this feature)

```text
specs/006-twilio-tts-speakback/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── tts-test-endpoint.md
│   ├── health-fields.md
│   └── twilio-speakback-websocket.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── routes_audio.py
│   ├── routes_tts.py
│   └── routes_twilio.py
├── core/
│   └── config.py
├── main.py
├── models/
│   ├── triage.py
│   └── tts.py
└── services/
    ├── azure_speech_tts_service.py
    └── twilio_audio_service.py

tests/
├── integration/
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_azure_speech_tts_service.py
    ├── test_telephony_config.py
    ├── test_tts_routes.py
    └── test_twilio_audio_service.py

frontend/
├── components/voice/VoiceDebugConsole.tsx
├── tests/voice-debug-console.test.tsx
└── types/triage.ts
```

**Structure Decision**: Use the existing backend module layout. Keep inbound Twilio decode helpers in `twilio_audio_service.py`, add outbound helper functions there, and put Azure Speech synthesis in a separate service. Keep frontend changes minimal: display TTS status/warnings if exposed in payloads; do not add browser audio playback.

## Implementation Approach

1. Add settings in `app/core/config.py`: `enable_twilio_tts_response`, `azure_speech_voice`, `tts_max_chars`, and `tts_output_format`.
2. Extend `AzureHealth` and `/api/health/azure` with `twilio_tts_response_enabled`, `azure_speech_tts_configured`, and `azure_speech_voice`.
3. Add TTS Pydantic models in `app/models/tts.py` for test request/response and internal synthesis result metadata.
4. Add outbound Twilio helpers to `app/services/twilio_audio_service.py`: PCM16-to-mu-law conversion, chunking, media event builder, mark event builder, and duration estimate.
5. Add `AzureSpeechTTSService` with `health/configured`, spoken text sanitization, length enforcement, Azure Speech synthesis, preferred raw 8 kHz mu-law output, fallback PCM-to-mu-law conversion, chunk metadata, warnings, and no secret/audio logging.
6. Add `POST /api/tts/test` in `app/api/routes_tts.py`, returning metadata only and configured/unconfigured status without raw audio.
7. Register the TTS router in `app/main.py`.
8. Modify `app/api/routes_twilio.py` only around outbound response handling: capture `streamSid` from start metadata, send normal JSON payloads first, then if enabled/configured/response_text exists, synthesize and send outbound Twilio media chunks plus mark event. Log `tts.started`, `tts.completed`, and `tts.failed` without payloads.
9. Keep `AudioSessionProcessor` unchanged unless a tiny metadata addition is needed; it should continue returning normal payloads with `response_text`.
10. Add unit and integration tests for config defaults, safety sanitization, event builders, TTS route unconfigured behavior, mocked-TTS outbound send, TTS failure continuation, and existing local mic/Twilio regressions.
11. Update README and `.env.example` with enablement steps, cost warning, health/test endpoints, Twilio call test steps, and deployment env commands.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

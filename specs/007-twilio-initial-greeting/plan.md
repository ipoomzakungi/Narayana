# Implementation Plan: Twilio Initial Greeting

**Branch**: `007-twilio-initial-greeting` | **Date**: 2026-05-04 | **Spec**: `specs/007-twilio-initial-greeting/spec.md`  
**Input**: Feature specification from `specs/007-twilio-initial-greeting/spec.md`

## Summary

Add optional first-greeting speak-back for Narayana Twilio calls as a small extension to the existing optional Twilio TTS pipeline. When `ENABLE_TWILIO_INITIAL_GREETING=true`, the Twilio media WebSocket will play one short, safe Thai greeting after the Twilio `start` event provides `streamSid`, then continue listening through the existing audio session processor. The feature reuses `AzureSpeechTTSService`, existing SSML profile support, and existing Twilio outbound media helpers. Greeting is disabled by default, fails open, and must not change Twilio route paths or duplicate TTS logic.

The independently testable MVP is a mocked-TTS Twilio WebSocket start flow: with greeting enabled, a `start` event emits the normal `session.started` debug payload, then Twilio-compatible `media` events and a `mark` named `narayana_initial_greeting`; with greeting disabled, the start flow is unchanged.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript/React/Next.js frontend remains unchanged except existing debug fields continue to work.  
**Primary Dependencies**: FastAPI WebSocket routes, Pydantic settings/models, existing Azure Cognitive Services Speech SDK wrapper, existing Twilio media event builders, pytest, existing Vitest/Next.js regression gates.  
**Storage**: No new persistent storage. Greeting playback state is per-call in memory and not stored in case records.  
**Testing**: `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`.  
**Target Platform**: FastAPI backend on Azure Container Apps for Twilio WebSocket support; frontend remains Azure Static Web Apps.  
**Project Type**: Web service backend plus existing static dashboard/debug frontend.  
**Performance Goals**: Greeting should be emitted within 5 seconds of Twilio stream start when TTS is configured. Greeting must not block later caller media processing if synthesis fails.  
**Constraints**: `ENABLE_TWILIO_INITIAL_GREETING=false` by default; do not change `/api/telephony/twilio/incoming-call` or `/ws/telephony/twilio/{call_id}`; do not rewrite inbound audio; do not enable Azure OpenAI, ACS, SMS, Cosmos DB, or dispatch; do not log secrets or raw audio payloads; do not require real Azure/Twilio credentials in automated tests.  
**Scale/Scope**: One small config extension, one TTS profile value, one reusable Twilio TTS send helper, one initial-greeting branch in the existing Twilio start handling, health fields, docs, and targeted unit/integration tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and defines no enforceable project-specific gates. This plan applies Narayana's active safety and compatibility constraints:

- Existing Twilio webhook and WebSocket route paths must remain stable.
- Greeting must be opt-in and disabled by default.
- Greeting must reuse the existing TTS service and outbound media helpers.
- Greeting failures must not close calls or block caller media intake.
- Automated tests must use mocked TTS and simulated Twilio events, not real cloud credentials.
- Spoken greeting text must pass the existing safety and length controls.
- No secrets or raw audio payloads may be logged or returned.

Pre-design status: PASS. No unresolved clarifications.

Post-design status: PASS. Research, model, contracts, and quickstart preserve the default-disabled scope, reuse existing TTS, and keep failure behavior safe.

## Project Structure

### Documentation (this feature)

```text
specs/007-twilio-initial-greeting/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── health-fields.md
│   ├── tts-test-profile.md
│   └── twilio-initial-greeting-websocket.md
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
├── models/
│   ├── triage.py
│   └── tts.py
└── services/
    └── azure_speech_tts_service.py

tests/
├── integration/
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_azure_speech_tts_service.py
    ├── test_telephony_config.py
    ├── test_tts_routes.py
    └── test_twilio_routes.py

frontend/
├── components/voice/VoiceDebugConsole.tsx
├── tests/voice-debug-console.test.tsx
└── types/triage.ts
```

**Structure Decision**: Use the existing backend module layout. Keep Azure speech synthesis behavior in `AzureSpeechTTSService`, keep Twilio media message construction in `twilio_audio_service.py`, and keep Twilio call orchestration in `routes_twilio.py`. Frontend changes are not required for the MVP unless a health/debug type must accept new additive fields.

## Implementation Approach

1. Extend `Settings` in `app/core/config.py` with:
   - `enable_twilio_initial_greeting=false`
   - `twilio_initial_greeting_text`
   - `twilio_initial_greeting_profile="greeting"`
   - `twilio_initial_greeting_fallback_say=false`
   - `tts_rate_greeting="-5%"`
   - `tts_pitch_greeting="0%"`
2. Add `TTSProfile.GREETING` to `app/models/tts.py`; `/api/tts/test` should already accept profile values through this model once the enum is extended.
3. Update `AzureSpeechTTSService` profile selection so `greeting` uses `TTS_RATE_GREETING` and `TTS_PITCH_GREETING`, with `TTS_VOLUME` unchanged.
4. Add health fields to `AzureHealth` and `/api/health/azure`:
   - `twilio_initial_greeting_enabled`
   - `twilio_initial_greeting_text_configured`
   - `twilio_initial_greeting_profile`
5. Refactor a shared Twilio helper in `routes_twilio.py`, tentatively `_send_tts_media(...)`, to synthesize safe text and send media/mark events for a named purpose. Use it for both response speak-back and the new initial greeting so TTS logic is not duplicated.
6. On Twilio `start` event, after `streamSid` is captured, metadata/processor are initialized, and `session.started` is sent:
   - if initial greeting is disabled, continue unchanged.
   - if enabled, call the shared helper with `settings.twilio_initial_greeting_text`, `TTSProfile.GREETING`, mark name `narayana_initial_greeting`, and purpose `greeting`.
   - log `greeting.started`, `greeting.completed`, or `greeting.failed` without secrets or audio payloads.
   - never raise greeting failures back into the WebSocket loop.
7. Add `.env.example` and README entries for enablement, default greeting, profile/rate/pitch, health check, `/api/tts/test` profile `"greeting"`, and logs to watch.
8. Add tests:
   - config defaults and env parsing for greeting.
   - SSML for greeting profile.
   - TTS test route accepts `profile="greeting"`.
   - Twilio start with greeting disabled sends no media/mark.
   - Twilio start with greeting enabled and mocked TTS sends session.started, media chunks, and `narayana_initial_greeting` mark.
   - greeting TTS failure logs/continues without closing the call.
   - existing Twilio response speak-back tests still pass.
9. Run final gates: `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

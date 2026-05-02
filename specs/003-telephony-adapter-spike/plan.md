# Implementation Plan: Telephony Adapter Spike

**Branch**: `003-telephony-adapter-spike` | **Date**: 2026-05-02 | **Spec**: `specs/003-telephony-adapter-spike/spec.md`
**Input**: Feature specification from `specs/003-telephony-adapter-spike/spec.md`

## Summary

Add a V1 telephony adapter spike for Narayana that validates foreign-country test phone call ingress without changing the Azure Voice Gateway contract. The implementation must not create a second voice pipeline: Twilio and future ACS input become normalized `AudioFrame` sources that reuse the existing local microphone turn manager, WAV persistence, voice provider selection, safety rules, and case repository behavior.

The fastest demo path is to extract the current `/ws/local-audio` turn/provider/case logic into `AudioSessionProcessor`, refactor local microphone to use it with no public contract change, then add Twilio webhook and media stream routes that decode G.711 mu-law frames into PCM16 mono `AudioFrame` objects. ACS remains a disabled skeleton until explicit provider support is available.

## Technical Context

**Language/Version**: Python 3.11 for FastAPI backend; TypeScript with Next.js for the debug dashboard.  
**Primary Dependencies**: FastAPI, Pydantic, pytest, Azure Speech/OpenAI SDK integrations already present, Next.js, React, Vitest. Twilio media normalization uses Python stdlib `audioop` on Python 3.11; add `audioop-lts` only if the project moves to a Python version where `audioop` is removed.  
**Storage**: Existing local JSON case repository or Cosmos DB repository; existing `.data/audio/{session_id}/{turn_id}.wav` WAV persistence. No new database is required for the spike.  
**Testing**: `python -m compileall app`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`. Manual real-call validation is documented separately and must not be required by automated tests.  
**Target Platform**: Local development on Windows for the hackathon demo, with backend deployable to Azure Container Apps and frontend deployable to Azure Static Web Apps later.  
**Project Type**: Web application with Python API backend and Next.js frontend.  
**Performance Goals**: Preserve 20 ms audio frame handling, avoid blocking WebSocket receive loops with duplicated provider logic, and keep the local mock flow responsive enough for a live demo.  
**Constraints**: `local_mic` remains default; startup must not require Twilio or ACS credentials; no autonomous emergency dispatch; no Thailand number, SMS, or compliance claim; phone-provider tests use simulated media by default.  
**Scale/Scope**: Single backend service, one debug/dashboard frontend, one Twilio spike, one ACS disabled skeleton, and offline tests for simulated telephony media.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The current constitution file still contains placeholders and defines no enforceable project-specific gates. This plan therefore applies the active feature safety and quality gates from the spec:

- Local microphone and mock mode remain default and must keep passing.
- Phone-provider credentials must not be required for startup or automated tests.
- Telephony must reuse the existing audio gateway logic through normalized `AudioFrame` objects.
- Safety rules, human review requirements, and no-dispatch constraints must remain centralized.
- ACS must be disabled or skeleton-only unless explicitly configured.

Pre-design status: PASS. No unresolved clarifications and no justified complexity exceptions.

Post-design status: PASS. Research, data model, contracts, and quickstart preserve the same shared-pipeline architecture and offline test requirement.

## Project Structure

### Documentation (this feature)

```text
specs/003-telephony-adapter-spike/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── acs-skeleton.md
│   ├── audio-session-processor.md
│   ├── telephony-media-websocket.md
│   └── twilio-webhook.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── routes_audio.py          # refactor to use AudioSessionProcessor
│   ├── routes_acs.py            # disabled ACS skeleton
│   ├── routes_cases.py
│   ├── routes_triage.py
│   └── routes_twilio.py         # Twilio webhook and media WebSocket
├── core/
│   └── config.py                # telephony settings
├── models/
│   ├── audio.py                 # existing AudioFrame and turn contracts
│   ├── case.py
│   ├── telephony.py             # CallMetadata and enums
│   └── triage.py
└── services/
    ├── audio_buffer_service.py
    ├── audio_session_processor.py
    ├── azure_speech_provider.py
    ├── case_repository.py
    ├── safety_rules.py
    ├── turn_manager.py
    ├── twilio_audio_service.py
    └── voice_agent_provider.py

frontend/
├── components/
│   └── voice/
│       └── VoiceDebugConsole.tsx # show source_input_mode and call_metadata
└── types/
    └── triage.ts

tests/
├── integration/
│   ├── test_mock_local_mic_flow.py
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_telephony_config.py
    └── test_twilio_audio_service.py
```

**Structure Decision**: Keep the current FastAPI plus Next.js layout. Add telephony as backend API/service/model modules only, with a minimal frontend contract display update.

## Implementation Approach

1. Add telephony settings to `app/core/config.py` with safe defaults: `VOICE_INPUT_MODE=local_mic`, `TELEPHONY_PROVIDER=none`, optional test phone metadata, Twilio variables, and ACS variables.
2. Add `app/models/telephony.py` with `CallMetadata`, `TelephonyProvider`, and codec/input-mode enums used by provider routes and emitted payloads.
3. Create `app/services/audio_session_processor.py` by extracting the shared work from `routes_audio.py`: `TurnManager`, `AudioBufferService`, `get_voice_provider`, `apply_safety_rules`, and `get_case_repository`.
4. Refactor `/ws/local-audio` to instantiate `AudioSessionProcessor`, keep the same client messages and response payloads, and preserve current tests.
5. Add `app/services/twilio_audio_service.py` to parse Twilio media stream JSON, decode base64 mu-law payloads, convert to PCM16 mono, and produce `AudioFrame` instances.
6. Add `app/api/routes_twilio.py` with `POST /api/telephony/twilio/incoming-call` and `/ws/telephony/twilio/{call_id}`. The webhook returns TwiML only when a public base URL is configured; otherwise it returns a clear configuration error.
7. Add `app/api/routes_acs.py` with disabled/skeleton endpoints that return not configured or not implemented without app crashes.
8. Register the new routers in `app/main.py`.
9. Update the frontend debug console types and rendering to display `source_input_mode` and `call_metadata` when present. Do not build call control UI in this spike.
10. Add offline unit and integration tests for Twilio parsing, mu-law conversion, missing config behavior, simulated Twilio media case creation, and local mic regression.
11. Update README with foreign-number setup, Twilio webhook examples, simulated media test steps, ACS skeleton status, and limitations.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

# Implementation Plan: Azure Realtime Voice Provider Spike

**Branch**: `010-azure-realtime-voice` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/010-azure-realtime-voice/spec.md`

## Summary

Add an experimental realtime voice provider layer that can route Twilio media frames to Azure Voice Live or Azure OpenAI GPT Realtime when explicitly enabled. The current Narayana Twilio flow remains the default and fallback: Twilio audio, local VAD/turn manager, Azure Speech STT or mock, intake/model, Azure Speech TTS, and Twilio media speak-back. The spike adds provider selection, skeleton realtime provider implementations, mocked WebSocket tests, safe fallback, latency instrumentation, and README setup guidance without enabling Azure OpenAI secrets or replacing the working pipeline.

## Technical Context

**Language/Version**: Python 3.11-compatible FastAPI backend; TypeScript/Next.js frontend remains unchanged except optional debug display if needed
**Primary Dependencies**: FastAPI, Pydantic v2, `websockets` for provider WebSocket clients, existing Twilio media helpers, existing call audit logger, pytest
**Storage**: No new persistent storage; realtime sessions are per-call runtime objects with audit/log metadata only
**Testing**: `pytest`, FastAPI `TestClient`, mocked realtime WebSocket events; existing frontend tests/build remain part of final gates
**Target Platform**: Backend on Azure Container Apps receiving Twilio Media Streams WebSocket traffic
**Project Type**: Web service plus static dashboard
**Performance Goals**: Capture latency timestamps for realtime connect, input audio sent, first output audio received, response start/completion, fallback, and current-pipeline comparison. Manual validation determines whether realtime reduces perceived call delay.
**Constraints**: `ENABLE_REALTIME_VOICE=false` and `REALTIME_PROVIDER=none` by default; preserve Twilio route paths; do not remove or rewrite current STT/intake/TTS fallback; do not log secrets or raw audio payloads; automated tests must not require Azure/Twilio credentials; no ACS/SMS/dispatch.
**Scale/Scope**: Hackathon spike for one active provider session per Twilio call; no production connection pooling or multi-tenant realtime orchestration in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The repository constitution still contains placeholder principles and no binding technical gates. This plan applies established Narayana quality gates:

- Preserve current local mic, Twilio, mock, intake, TTS, and dashboard behavior by default.
- Keep all realtime functionality behind explicit feature flags.
- Ensure missing Azure realtime credentials never break backend startup.
- Keep tests offline by using mocked provider WebSocket events.
- Do not commit or log secrets, authorization headers, or raw audio payloads.
- Preserve crisis-intake guardrails: no dispatch claims, no diagnosis, crisis-only assistant behavior.

**Gate Result**: PASS. The planned spike is additive and default-disabled.

## Project Structure

### Documentation (this feature)

```text
specs/010-azure-realtime-voice/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── realtime-provider-contract.md
│   └── twilio-realtime-routing-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── routes_audio.py
│   └── routes_twilio.py
├── core/
│   └── config.py
├── models/
│   ├── realtime.py
│   └── triage.py
└── services/
    ├── audio_session_processor.py
    ├── azure_openai_realtime_provider.py
    ├── azure_voice_live_realtime_provider.py
    ├── call_audit_logger.py
    ├── realtime_latency.py
    ├── realtime_voice_provider.py
    ├── twilio_audio_service.py
    └── voice_agent_provider.py

tests/
├── integration/
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_realtime_provider_selection.py
    ├── test_realtime_voice_provider.py
    ├── test_realtime_fallback.py
    └── test_twilio_routes.py

README.md
.env.example
```

**Structure Decision**: Keep realtime providers beside existing voice providers under `app/services/`. Add a separate realtime provider contract rather than changing `VoiceAgentProvider`, because realtime operation is stream/session based while the existing provider processes committed turns. Touch `routes_twilio.py` only at the routing boundary so the current path remains the fallback.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

- Use WebSocket provider skeletons for this spike because Twilio terminates the phone stream at FastAPI and the backend needs server-to-server provider integration.
- Keep Azure OpenAI GPT Realtime and Azure Voice Live as selectable experimental providers; do not pick one as mandatory.
- Treat Azure OpenAI GPT Realtime region/deployment availability as an external manual prerequisite and keep the provider disabled unless configured.
- Use the existing crisis-intake prompt/guardrails as the realtime session instruction source.
- Use existing Twilio media helpers for inbound normalization and outbound media events.

## Phase 1 Design Artifacts

- [data-model.md](./data-model.md): Realtime provider config, session, audio events, latency samples, fallback decisions.
- [contracts/realtime-provider-contract.md](./contracts/realtime-provider-contract.md): Internal async provider interface and event contract.
- [contracts/twilio-realtime-routing-contract.md](./contracts/twilio-realtime-routing-contract.md): Twilio routing, fallback, logging, and debug payload contract.
- [quickstart.md](./quickstart.md): Local mock validation, manual Azure realtime setup checklist, region warnings, and final verification gates.

## Complexity Tracking

No constitution violations. The extra provider interface is justified because realtime streaming has a different lifecycle than the existing turn-based provider contract; forcing it into `VoiceAgentProvider.process_turn()` would either block on committed turns or hide streaming/fallback behavior.

## Post-Design Constitution Check

**Gate Result**: PASS. The design preserves existing route compatibility, keeps realtime disabled by default, avoids new mandatory cloud dependencies, and adds tests for selection, fallback, mocked realtime events, and existing Twilio behavior.

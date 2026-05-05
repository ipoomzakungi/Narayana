# Implementation Plan: Call Latency, Barge-In, and Audit Debugging

**Branch**: `009-call-latency-barge-in-audit` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/009-call-latency-barge-in-audit/spec.md`

## Summary

Improve Narayana's existing Twilio voice demo responsiveness without moving to Azure Voice Live. The implementation keeps the current FastAPI WebSocket route, `AudioSessionProcessor`, local VAD/turn manager, multi-turn intake, and Azure Speech TTS path, then adds configurable VAD/turn thresholds, Twilio barge-in clear handling, Twilio mark-aware no-reply timing, structured call-audit session visibility, and a `/call-audit` frontend page. Documentation adds Azure Container Apps warm/low-cost commands for demo readiness.

## Technical Context

**Language/Version**: Python 3.11-compatible FastAPI backend; TypeScript 5.7 with Next.js 15 / React 19 frontend
**Primary Dependencies**: FastAPI, Pydantic v2, uvicorn, Azure Speech SDK, OpenAI SDK, websockets, Next.js, React, Tailwind CSS, Vitest
**Storage**: Existing in-memory intake session store for audit/debug sessions; existing local JSON case store remains unchanged; no new database resource
**Testing**: `pytest`, `pytest-asyncio`, FastAPI `TestClient`, Vitest + Testing Library
**Target Platform**: Backend on Azure Container Apps with Twilio Media Streams WebSocket; frontend static export on Azure Static Web Apps
**Project Type**: Web service plus static web dashboard
**Performance Goals**: Demo turn commit within 1 second after caller stops speaking when demo thresholds are configured; barge-in clear sent immediately after speech is detected during assistant playback; no-reply timers delayed until assistant playback completes
**Constraints**: Do not change Twilio route paths; do not implement Azure Voice Live, ACS, SMS, dispatch, Cosmos DB setup, or new Azure OpenAI enablement; do not log secrets or raw audio payloads; automated tests must not require Azure/Twilio credentials
**Scale/Scope**: Hackathon demo/debug scope with recent call sessions capped by `CALL_AUDIT_MAX_SESSIONS`; one backend instance is acceptable for audit visibility in V0

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution currently contains placeholder principles and no binding technical gates. This plan applies the established repo quality gates instead:

- Preserve existing Twilio route paths and local/mock behavior.
- Keep Azure/Twilio credentials optional in automated tests.
- Avoid secrets and audio payloads in logs or committed files.
- Add focused unit/integration/frontend tests for new behavior.

**Gate Result**: PASS. No constitution violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/009-call-latency-barge-in-audit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── intake-audit-api.md
│   └── twilio-playback-events.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── routes_intake.py
│   └── routes_twilio.py
├── core/
│   └── config.py
├── models/
│   ├── audio.py
│   └── intake.py
└── services/
    ├── audio_session_processor.py
    ├── call_audit_logger.py
    ├── call_lifecycle_service.py
    ├── intake_session_store.py
    ├── turn_manager.py
    ├── twilio_audio_service.py
    └── vad_service.py

frontend/
├── app/
│   └── call-audit/
│       └── page.tsx
├── components/
│   └── call-audit/
│       └── CallAuditDashboard.tsx
├── lib/
│   └── intake-session-api-client.ts
├── tests/
│   └── call-audit-dashboard.test.tsx
└── types/
    └── triage.ts

tests/
├── integration/
│   ├── test_intake_api.py
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_call_audit_logger.py
    ├── test_call_lifecycle_service.py
    ├── test_intake_session_store.py
    ├── test_turn_manager.py
    ├── test_twilio_audio_service.py
    ├── test_twilio_routes.py
    └── test_vad_service.py
```

**Structure Decision**: Use the existing FastAPI/Next.js layout. Backend changes stay inside the current audio, Twilio, intake, lifecycle, and settings modules. Frontend adds a single dashboard page and API client alongside the existing `cases` and `voice-debug` pages.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

- Keep existing Twilio Media Streams path and tune VAD/turn settings instead of adopting Azure Voice Live.
- Model assistant playback as explicit per-call state and use Twilio mark events for completion.
- Launch/supervise TTS playback as interruptible work so inbound media can trigger barge-in clear.
- Use the intake session store as the first call-audit backing store, capped by configuration.

## Phase 1 Design Artifacts

- [data-model.md](./data-model.md): Turn timing config, assistant playback state, barge-in event, mark event, call audit session, timeline event.
- [contracts/intake-audit-api.md](./contracts/intake-audit-api.md): New intake session audit endpoints and response shapes.
- [contracts/twilio-playback-events.md](./contracts/twilio-playback-events.md): Twilio clear/mark/media handling contracts and debug payloads.
- [quickstart.md](./quickstart.md): Local verification, demo warm commands, Twilio barge-in test, call-audit smoke test.

## Complexity Tracking

No constitution violations or unnecessary new subsystems. The only added service (`call_audit_logger.py`) centralizes safe structured logs and audit timeline writes so Twilio, intake, and lifecycle paths do not duplicate logging/audit formatting.

## Post-Design Constitution Check

**Gate Result**: PASS. The design preserves route compatibility, keeps secrets out of logs, avoids new cloud dependencies, and adds tests for the new latency, barge-in, mark, no-reply, and audit contracts.

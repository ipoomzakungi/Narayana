# Implementation Plan: Narayana AI Voice Intake

**Branch**: `001-crisis-voice-triage` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-crisis-voice-triage/spec.md`

## Summary

Narayana AI is a local-first crisis voice intake and triage MVP for a Microsoft Azure-focused hackathon. The name signals a protective, assistance-focused product identity while keeping the experience clearly framed as a crisis intake and triage assistant. V0 must prove the end-to-end flow from local browser microphone to backend voice turn detection, replaceable Azure/mock voice interpretation, structured crisis extraction, human-review triage, and a live operator dashboard without depending on real phone numbers, Twilio, Azure Communication Services, or autonomous dispatch.

The technical approach uses a Next.js TypeScript frontend for a compact command-center dashboard and microphone/debug UI, plus a Python FastAPI backend with WebSocket audio ingestion, a server-side turn manager, replaceable voice providers, deterministic safety triage rules, repository-backed case storage, and realtime dashboard events. Azure integrations are adapters: Voice Live is the preferred voice path, Speech plus Azure OpenAI structured extraction is the fallback, Cosmos DB and SignalR are cloud persistence/realtime options, and local mock services keep demos running offline.

## Technical Context

**Language/Version**: TypeScript on Node.js LTS for the frontend; Python 3.11+ for the backend  
**Primary Dependencies**: Next.js App Router, Tailwind CSS, shadcn/ui source components, FastAPI, Pydantic, Uvicorn, pytest, Azure Speech SDK, OpenAI Python SDK for Azure OpenAI-compatible calls, Azure Cosmos DB Python SDK, Azure Identity, Azure Monitor OpenTelemetry distro  
**Storage**: Azure Cosmos DB through `CaseRepository`; local JSON-file repository fallback when Cosmos credentials are missing  
**Testing**: pytest, pytest-asyncio, FastAPI TestClient/httpx, Vitest/React Testing Library for frontend units, Playwright for browser workflow verification  
**Target Platform**: Local developer machine first; Azure Static Web Apps for frontend; Azure Container Apps for backend; Azure Cosmos DB and Azure SignalR when configured  
**Project Type**: Web application with separate frontend and backend services  
**Performance Goals**: Local Thai demo statement creates a dashboard case within 30 seconds after turn completion; dashboard updates appear within 5 seconds for 95% of demo events; VAD processes 20 ms PCM frames and ends turns after 600-900 ms of silence  
**Constraints**: Must run without Twilio, Azure Communication Services, real phone numbers, or Azure credentials; must degrade to mock services; must not dispatch rescue automatically; RED and low-confidence cases require human review; secrets stay in local environment files only  
**Scale/Scope**: Hackathon MVP for one local demo station, a small operator dashboard, and dozens of demo cases; architecture leaves adapter points for V1 telephony and production security

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The current constitution file contains template placeholders and no enforceable project-specific gates. This plan therefore treats the feature specification and user-provided quality gates as the controlling constraints.

Pre-design gate results:

- Local-first V0 without Twilio or Azure Communication Services phone numbers: PASS
- Human-centered safety constraints, including no autonomous dispatch and mandatory human review for RED or low-confidence cases: PASS
- Replaceable provider/repository/realtime adapters so missing Azure credentials do not block local demo: PASS
- Test coverage planned for triage rules, VAD state transitions, local repository, mock voice integration, Thai extraction, dashboard live update, and operator override: PASS
- Observability planned for voice state and timing events: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-crisis-voice-triage/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes_voice.py
│   │   ├── routes_cases.py
│   │   └── routes_uploads.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   ├── case.py
│   │   └── triage.py
│   ├── repositories/
│   │   ├── case_repository.py
│   │   ├── cosmos_case_repository.py
│   │   └── local_case_repository.py
│   └── services/
│       ├── audio_gateway.py
│       ├── vad_service.py
│       ├── azure_voice_service.py
│       ├── triage_service.py
│       ├── cosmos_service.py
│       └── signalr_service.py
├── requirements.txt
├── .env.example
└── tests/
    ├── unit/
    │   ├── test_triage_service.py
    │   ├── test_vad_service.py
    │   └── test_local_case_repository.py
    └── integration/
        ├── test_local_voice_flow.py
        └── test_thai_structured_extraction.py

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── cases/
│   │   ├── page.tsx
│   │   └── [caseId]/page.tsx
│   ├── voice-debug/page.tsx
│   └── uploads/page.tsx
├── components/
│   ├── ui/
│   ├── app-shell/
│   ├── cases/
│   ├── triage/
│   └── voice/
├── lib/
│   ├── api-client.ts
│   ├── realtime-client.ts
│   └── audio-client.ts
├── types/
│   └── case.ts
├── public/
├── package.json
├── components.json
└── .env.example

infra/
├── container-apps/
├── static-web-apps/
└── README.md
```

**Structure Decision**: Use a two-app web architecture with `frontend/` and `backend/` at the repository root. The backend follows the requested FastAPI modular layout and adds a small `repositories/` folder to keep Cosmos and local storage interchangeable. The frontend uses Next.js App Router routes for Live Cases, Case Detail, Voice Debug Console, and optional Upload Evidence, with shadcn/ui source components composed into a compact command-center dashboard.

## Phase 0 Research

Research decisions are captured in [research.md](./research.md). All technical unknowns are resolved for V0 without open clarification markers.

## Phase 1 Design Artifacts

- Data model: [data-model.md](./data-model.md)
- REST contract: [contracts/openapi.yaml](./contracts/openapi.yaml)
- Voice WebSocket contract: [contracts/voice-websocket.md](./contracts/voice-websocket.md)
- Dashboard realtime contract: [contracts/realtime-dashboard.md](./contracts/realtime-dashboard.md)
- Quickstart: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- Safety and human-review gates remain satisfied by explicit data fields, status transitions, triage override contract, and triage service rules.
- Local-first gate remains satisfied by `MockVoiceProvider`, `LocalCaseRepository`, and local WebSocket/SSE dashboard fallback.
- Azure-focused demo gate remains satisfied by replaceable Azure provider, Cosmos, SignalR, Static Web Apps, Container Apps, and Application Insights integration points.
- No unresolved clarification markers remain in the plan artifacts.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. Adapter interfaces, repository pattern, and realtime fallback are required by explicit V0 requirements: local offline demo, Azure credential fallback, future telephony preparation, and dashboard live updates.

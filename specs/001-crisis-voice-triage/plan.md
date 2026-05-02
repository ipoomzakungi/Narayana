# Implementation Plan: Narayana AI Azure Voice Gateway

**Branch**: `001-crisis-voice-triage` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)  
**Input**: Revised feature specification plus implementation guidance for `/ws/local-audio`, Azure Speech/OpenAI provider adapters, safety rules, local debug console, and future phone-provider adapter isolation.

## Summary

Implement the Narayana AI Azure Voice Gateway as a local-first, provider-adapter module for the AI Crisis Management hackathon. The module proves the core voice-AI path without requiring working Twilio or Azure Communication Services phone numbers: browser microphone audio streams into FastAPI, local VAD and turn management commit clean user turns, mock or Azure providers produce transcript and structured triage JSON, deterministic safety rules enforce conservative crisis handling, and a case preview can be stored locally, written to Cosmos DB, or sent to dashboard code.

The existing project context is `kullawattana/AI-Crisis-Management` on branch `poc-ms-hackathon`; this Spec Kit workspace is currently on `001-crisis-voice-triage`. The implementation must be designed so it can be ported into the project branch without requiring other Twilio-based work to stop. Twilio and ACS remain valid elsewhere in the broader project, but this module treats them as V1 adapter placeholders.

## Technical Context

**Language/Version**: Python 3.11+ backend; TypeScript frontend with React or Next.js  
**Primary Dependencies**: FastAPI, Pydantic, Uvicorn, pytest, pytest-asyncio, httpx, websockets, Azure Speech SDK, Azure OpenAI client, optional Azure Voice Live WebSocket/SDK, Azure Cosmos DB SDK, Web Audio API, Tailwind CSS, optional shadcn/ui source components  
**Storage**: `LocalCaseRepository` for V0 local persistence; `CosmosCaseRepository` when Cosmos credentials exist; case object emission remains available without storage  
**Testing**: pytest unit/integration tests for backend; frontend unit tests for audio/WebSocket/debug rendering; manual Azure Speech STT and Cosmos write tests when credentials exist  
**Target Platform**: Local developer workstation first; Azure Container Apps-ready backend; optional React/Next.js debug console; Azure Speech/OpenAI/Cosmos only when configured  
**Project Type**: Web-backed voice gateway module with local microphone test harness and provider/input/repository adapters  
**Performance Goals**: Consume 20 ms audio frames; end user turns after 600-900 ms silence; keep 150-250 ms pre-speech buffer; create a Thai sample case within 30 seconds after committed turn; emit debug events in near real time  
**Constraints**: Must run with `USE_MOCK_SERVICES=true`; must not require Twilio, ACS, phone numbers, real SMS, Azure OpenAI Realtime, production auth, or official dispatch integration; must not close or dispatch cases automatically; must require human review for RED, confidence below 0.75, missing location, or contradictory facts  
**Scale/Scope**: Hackathon MVP module for one local demo station, local microphone streaming, manual transcript testing, optional uploaded audio later, Azure Speech/OpenAI provider, optional Azure Voice Live provider, local/Cosmos repository adapters, and disabled Twilio/ACS adapter placeholders

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and no enforceable project-specific rules. This plan uses the revised specification and user-provided quality gates as the controlling constraints.

Pre-design gate results:

- Local microphone path is required and independent of phone numbers: PASS
- Mock mode works when Azure credentials are missing: PASS
- Azure Speech + Azure OpenAI is the primary stable provider path: PASS
- Azure Voice Live is optional and experimental: PASS
- Azure OpenAI Realtime is not required for V0: PASS
- Deterministic safety rules run after AI/provider output: PASS
- RED safety cases are never downgraded automatically: PASS
- Missing/uncertain information requires human review: PASS
- Twilio and ACS are isolated behind adapters and disabled for V0: PASS

## Phase 0 Research

Research decisions are captured in [research.md](./research.md). Key resolved decisions:

- **Primary provider**: `AzureSpeechOpenAIProvider` is the stable Azure path because Azure Speech handles speech-to-text and Azure OpenAI structured outputs can constrain crisis JSON.
- **Experimental provider**: `AzureVoiceLiveProvider` is optional because Voice Live provides realtime WebSocket voice features, PCM16 support, turn detection options, and interruption behavior, but V0 must not depend on it exclusively.
- **Mock provider**: `MockVoiceProvider` is always available for local demos and provider fallback.
- **VAD approach**: start with energy-based VAD for speed and portability; add WebRTC VAD only if dependency installation is reliable.
- **Phone provider scope**: Twilio and ACS adapters are interface-only for V1 because phone number acquisition, Thailand capability, and trial-account restrictions must be validated separately.
- **Frontend approach**: build a compact voice debug console, not a marketing page. If shadcn/ui is initialized in the target project, compose with Button, Badge, Card, Table, Tabs, Alert, Separator, and form components using semantic tokens and `gap-*` spacing.

## Project Structure

### Documentation (this feature)

```text
specs/001-crisis-voice-triage/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   ├── local-audio-websocket.md
│   └── adapter-interfaces.md
└── tasks.md               # Regenerate after this plan revision
```

### Source Code (repository root)

```text
app/
├── main.py
├── core/
│   └── config.py
├── api/
│   ├── routes_audio.py
│   ├── routes_triage.py
│   └── routes_cases.py
├── models/
│   ├── audio.py
│   ├── triage.py
│   └── case.py
└── services/
    ├── audio_frame_service.py
    ├── vad_service.py
    ├── turn_manager.py
    ├── voice_agent_provider.py
    ├── mock_voice_provider.py
    ├── azure_speech_provider.py
    ├── azure_voice_live_provider.py
    ├── azure_openai_triage_provider.py
    ├── safety_rules.py
    ├── case_repository.py
    ├── local_case_repository.py
    └── cosmos_case_repository.py

frontend/ or web/
├── app/ or src/
│   ├── voice-debug/
│   └── components/
├── lib/
│   ├── audio-client.ts
│   ├── voice-ws-client.ts
│   └── triage-api-client.ts
└── types/
    └── triage.ts

tests/
├── unit/
│   ├── test_safety_rules.py
│   ├── test_triage_schema.py
│   ├── test_vad_service.py
│   ├── test_provider_fallback.py
│   └── test_input_adapters.py
└── integration/
    ├── test_thai_transcript_to_red_case.py
    ├── test_mock_local_mic_flow.py
    └── test_cases_api.py
```

**Structure Decision**: Use the requested backend layout directly under `app/` for easier transplant into `kullawattana/AI-Crisis-Management`. Keep frontend naming flexible (`frontend/` or existing project web app) because the target branch may already have a React/Next.js structure. The gateway module owns audio frame processing, VAD, provider adapters, safety rules, and case repository adapters.

## Backend Architecture

### API Routes

- `GET /api/health/azure`: report configured/missing Azure Speech, Azure OpenAI, Azure Voice Live, Cosmos DB, and current provider mode without exposing secrets.
- `POST /api/triage/from-transcript`: test and fallback path that converts transcript text into structured triage JSON through mock or Azure OpenAI provider plus safety rules.
- `POST /api/cases`: store or emit a structured case object through `CaseRepository`.
- `WS /ws/local-audio`: receive browser microphone audio frames, emit VAD/debug/provider/case events, and create case preview after a committed turn.

### Core Services

- `audio_frame_service.py`: validates audio frame metadata, sequence numbers, frame duration, encoding, and optional resampling expectations.
- `vad_service.py`: energy-based VAD first; optional WebRTC VAD adapter later.
- `turn_manager.py`: owns pre-speech buffer, silence threshold, turn commit, current state, and barge-in flag.
- `voice_agent_provider.py`: interface for provider selection and result contract.
- `mock_voice_provider.py`: deterministic provider for Thai flood sample, minor property damage, unclear speech, and safety fixtures.
- `azure_speech_provider.py`: speech-to-text using Azure Speech for committed user turns and optional TTS response text.
- `azure_openai_triage_provider.py`: structured triage extraction using Azure OpenAI and the crisis JSON schema.
- `azure_voice_live_provider.py`: optional Voice Live WebSocket path; if structured output is unavailable, pass transcript to Azure OpenAI triage.
- `safety_rules.py`: deterministic post-AI safety overlay.
- `case_repository.py`: repository interface.
- `local_case_repository.py`: JSON-file repository for local demos.
- `cosmos_case_repository.py`: Cosmos DB repository when credentials exist.

### Provider Selection

1. If `USE_MOCK_SERVICES=true`, use `MockVoiceProvider`.
2. If mock mode is false and Speech/OpenAI credentials are complete, use `AzureSpeechOpenAIProvider`.
3. If Voice Live is explicitly configured and selected, use `AzureVoiceLiveProvider`.
4. If selected Azure provider is unavailable, emit a recoverable provider fallback event and use `MockVoiceProvider`.

Azure OpenAI Realtime is not a V0 dependency.

## Frontend Debug Console Plan

The frontend is a developer/debug console with a compact operational layout:

- Microphone permission and start/stop controls.
- Provider mode indicator: mock, Azure Speech/OpenAI, Azure Voice Live, fallback.
- Live VAD state: silence, speech, listening, thinking, speaking.
- Debug event timeline: `audio.frame.received`, `vad.speech.start`, `vad.speech.end`, `turn.committed`, `ai.request.started`, `ai.response.started`, `ai.response.completed`, `barge_in.detected`.
- Transcript panel with committed turns.
- Structured triage JSON panel.
- Safety-rule result panel showing forced RED/review reasons.
- Generated case preview panel with status and repository result.
- Manual transcript test form that calls `POST /api/triage/from-transcript`.

UI guidance:

- Prefer a dense command-center layout, not a hero or landing page.
- If shadcn/ui is used, initialize it only inside the target frontend project and compose existing source components.
- Use `Badge` variants for provider/VAD/triage states, `Tabs` for transcript vs JSON vs events, `Alert` for safety warnings, and form components for transcript input.
- Use semantic tokens and layout-only `className`; avoid raw color utilities for core component styling.

## Environment Configuration

```text
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=
AZURE_VOICE_LIVE_ENDPOINT=
AZURE_VOICE_LIVE_MODEL=
COSMOS_DB_ENDPOINT=
COSMOS_DB_KEY=
COSMOS_DB_DATABASE=
COSMOS_DB_CONTAINER=
USE_MOCK_SERVICES=true
```

Frontend:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_LOCAL_AUDIO_WS_URL=ws://localhost:8000/ws/local-audio
```

## Structured Triage Schema

The provider output and API response must conform to this schema:

```json
{
  "case_id": "string",
  "language": "string",
  "incident_type": "flood | fire | medical | accident | earthquake | public_safety | unknown",
  "triage_level": "RED | YELLOW | GREEN",
  "confidence": 0.0,
  "location_text": "string",
  "people_affected": null,
  "injuries": "string",
  "immediate_needs": ["string"],
  "caller_phone_optional": null,
  "ai_summary": "string",
  "triage_reason": "string",
  "human_review_required": true,
  "missing_fields": ["string"],
  "created_at": "string",
  "updated_at": "string",
  "status": "pending | contacted | dispatched | resolved | closed"
}
```

Azure OpenAI structured outputs should represent nullable values through supported schema patterns and include every field as required.

## Safety Rules

Run after provider output and before case storage/emission:

- Force RED if breathing difficulty, unconsciousness, severe bleeding, trapped person, active drowning risk, active fire exposure, chest pain, stroke symptoms, or caller says they cannot escape.
- Require human review if confidence is below 0.75.
- Require human review if location is missing.
- Require human review if AI suggests GREEN but injury, trapped condition, elderly risk, child risk, medical risk, fire, flood, or drowning appears.
- Never close a case automatically.
- Never dispatch rescue automatically.
- Preserve AI triage reason plus safety-rule reason.

## Debug Events

The WebSocket and backend logs must use these event names:

- `audio.frame.received`
- `vad.speech.start`
- `vad.speech.end`
- `turn.committed`
- `ai.request.started`
- `ai.response.started`
- `ai.response.completed`
- `barge_in.detected`

## Testing Plan

Automated tests:

- Unit test safety rules.
- Unit test triage schema validation.
- Unit test VAD state machine.
- Unit test provider fallback when Azure credentials are missing.
- Integration test Thai transcript to RED case.
- Integration test mock local mic flow.
- Unit test phone adapter placeholders are not required or selected for V0.

Manual tests:

- Azure Speech STT using Thai audio when credentials exist.
- Cosmos DB write when credentials exist.
- Local microphone creates a case in mock mode.
- Local microphone creates a case in Azure Speech/OpenAI mode.
- RED safety cases are never downgraded.
- Missing/uncertain information requires human review.

## Implementation Phases

1. Backend skeleton, models, config, mock provider, transcript-to-triage endpoint.
2. Frontend voice debug console and manual transcript test UI.
3. Local microphone WebSocket streaming and VAD debug events.
4. Azure Speech STT and Azure OpenAI structured triage.
5. Safety rules and case repository.
6. Cosmos DB integration.
7. Optional Azure Voice Live provider.
8. Twilio and ACS adapter placeholders, disabled for V0.

## Phase 1 Design Artifacts

- Data model: [data-model.md](./data-model.md)
- REST contract: [contracts/openapi.yaml](./contracts/openapi.yaml)
- WebSocket contract: [contracts/local-audio-websocket.md](./contracts/local-audio-websocket.md)
- Adapter contract: [contracts/adapter-interfaces.md](./contracts/adapter-interfaces.md)
- Quickstart: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- App runs locally with mock mode: PASS
- App can run locally with Azure Speech/OpenAI credentials: PASS
- Local microphone creates a case through `/ws/local-audio`: PASS
- RED safety cases are never downgraded by design: PASS
- Missing/uncertain information requires human review: PASS
- Phone provider integration is isolated behind adapters: PASS
- No unresolved clarification markers remain: PASS

## Complexity Tracking

No constitution violations. Provider interfaces, input adapters, and repository abstractions are required because the module must support local-first demos, optional Azure services, future phone providers, and storage fallback without changing the core voice gateway pipeline.

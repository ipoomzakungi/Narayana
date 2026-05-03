# Implementation Plan: Multi-Turn Crisis Conversation Intake

**Branch**: `005-multi-turn-intake` | **Date**: 2026-05-03 | **Spec**: `specs/005-multi-turn-intake/spec.md`
**Input**: Feature specification from `specs/005-multi-turn-intake/spec.md`

## Summary

Add a conversation-aware crisis intake layer over the existing Narayana voice gateway. The feature introduces session-scoped intake state, deterministic safety guardrails, rule-based operational grouping, an Azure OpenAI structured intake provider with deterministic fallback, and a main intake orchestrator. Existing one-shot triage stays available at `/api/triage/from-transcript`; Twilio route paths stay unchanged; phone-call use is gated behind `ENABLE_MULTI_TURN_INTAKE=false` by default.

The first independently testable slice is `POST /api/intake/from-transcript` for manual transcript intake. It stores conversation turns, updates collected fields, returns one concise Thai follow-up when critical fields are missing, and creates/escalates immediately for RED risks. Twilio integration can then route committed transcripts through the same orchestrator when the feature flag is enabled.

## Technical Context

**Language/Version**: Python 3.11 backend; TypeScript/React/Next.js 15 frontend.  
**Primary Dependencies**: FastAPI, Pydantic, existing OpenAI Azure client dependency, existing voice provider abstractions, existing repository/safety-rule services, React 19, Tailwind CSS, Vitest, pytest.  
**Storage**: V0 in-memory intake session store for active sessions; existing local JSON case repository for final cases when Cosmos is not configured. Cosmos-compatible field additions are allowed, but no Cosmos DB resource or migration is required.  
**Testing**: `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, `cd frontend && npm run build`.  
**Target Platform**: Azure Container Apps backend and Azure Static Web Apps frontend; local test mode remains supported.  
**Project Type**: FastAPI backend plus Next.js frontend.  
**Performance Goals**: Manual intake response should return within normal API latency in mock/fallback mode; cached dashboard behavior remains unchanged. Twilio follow-up decisions should not add extra network calls unless Azure OpenAI intake is explicitly configured and enabled.  
**Constraints**: Do not rewrite the existing triage provider; do not remove `/api/triage/from-transcript`; do not change Twilio webhook or WebSocket route paths; do not enable Azure Speech/OpenAI in deployment during this feature; do not add Cosmos DB resource; no ACS, SMS, TTS-to-Twilio, or emergency dispatch.  
**Scale/Scope**: One new backend model module, five intake services, one API route, small gated change in `AudioSessionProcessor`, settings additions, frontend debug/dashboard display updates, and targeted unit/integration tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and defines no enforceable project-specific gates. This plan applies the active Narayana safety and compatibility constraints:

- Safety guardrails must deterministically override model output for RED and human-review conditions.
- The new intake layer must be additive and feature-flagged for Twilio so current voice demo behavior remains stable.
- Existing public routes for triage, Twilio webhook, and Twilio media WebSocket must remain compatible.
- Automated tests must not require Azure Speech/OpenAI, Cosmos DB, Twilio credentials, ACS, SMS, or dispatch services.
- No response may claim rescue has been dispatched, diagnose medical/mental-health conditions, or close/reject a crisis case automatically.

Pre-design status: PASS. No unresolved clarifications.

Post-design status: PASS. Research, data model, contracts, and quickstart preserve additive scope and safety constraints.

## Project Structure

### Documentation (this feature)

```text
specs/005-multi-turn-intake/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── intake-from-transcript.md
│   ├── voice-websocket-intake.md
│   └── dashboard-intake-fields.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes_intake.py
├── core/
│   └── config.py
├── main.py
├── models/
│   ├── case.py
│   └── intake.py
└── services/
    ├── audio_session_processor.py
    ├── azure_openai_intake_provider.py
    ├── case_grouping_service.py
    ├── intake_guardrails.py
    ├── intake_orchestrator.py
    └── intake_session_store.py

frontend/
├── components/
│   ├── cases/CasesDashboard.tsx
│   └── voice/VoiceDebugConsole.tsx
├── lib/
│   ├── intake-api-client.ts
│   └── voice-ws-client.ts
├── tests/
│   ├── cases-dashboard.test.tsx
│   └── voice-debug-console.test.tsx
└── types/
    └── triage.ts

tests/
├── integration/
│   ├── test_intake_api.py
│   ├── test_thai_transcript_to_red_case.py
│   └── test_twilio_media_flow.py
└── unit/
    ├── test_case_grouping_service.py
    ├── test_intake_guardrails.py
    ├── test_intake_models.py
    ├── test_intake_orchestrator.py
    └── test_intake_session_store.py
```

**Structure Decision**: Use the existing FastAPI/Next.js layout. Add intake-specific modules alongside current triage, voice, repository, and dashboard modules. Keep existing voice provider and case repository patterns; do not create a separate telephony pipeline.

## Implementation Approach

1. Add `app/models/intake.py` with enums and Pydantic models for conversation turns, collected fields, session state, request/decision/response, action, and operational group.
2. Add settings for `ENABLE_MULTI_TURN_INTAKE`, assistant behavior, and response length limits with safe defaults.
3. Add an in-memory intake session store keyed by session ID for V0 session continuity and tests.
4. Add deterministic guardrails for RED and human-review risks in Thai and English.
5. Add rule-based case grouping as the deterministic fallback and post-model correction layer.
6. Add `AzureOpenAIIntakeProvider` that returns structured intake decisions when Azure OpenAI is configured, otherwise deterministic fallback decisions using existing triage/provider behavior and rule services.
7. Add `IntakeOrchestrator` to append turns, call guardrails/provider, merge fields, enforce max follow-ups, create final cases through the existing repository, and return `IntakeResponse`.
8. Add `POST /api/intake/from-transcript` and include the router from `app/main.py`.
9. Extend case/record shapes to optionally carry `case_group`, `recommended_team`, conversation summary, and intake audit details while remaining backward-compatible with existing records.
10. Gated Twilio/local mic integration: if `ENABLE_MULTI_TURN_INTAKE=false`, keep current direct case creation; if true, pass provider transcript through `IntakeOrchestrator`, emit `intake.followup` for follow-up decisions, and emit current `triage.case.created` shape for created/escalated cases with added intake fields.
11. Update `/voice-debug` to render `intake.followup`, response text, partial state, action, group/team, missing fields, conversation turns, and guardrail warnings.
12. Update `/cases` to show case group, recommended team, and conversation summary when present without breaking older records.
13. Add backend and frontend tests listed in the user request and preserve existing regression tests.
14. Deployment stays disabled by default; after merge, publish backend image through GHCR and enable `ENABLE_MULTI_TURN_INTAKE=true` only after tests pass and operator review.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

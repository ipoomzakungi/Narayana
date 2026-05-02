# Research: Narayana AI Voice Intake

## Decision 1: Local-first microphone path before telephony

**Decision**: Build V0 around browser microphone capture streamed to FastAPI over WebSocket. Telephony remains adapter-only documentation for V1.

**Rationale**: The feature spec explicitly says V0 must not depend on Twilio, Azure Communication Services phone numbers, or real dispatch integrations. A local browser microphone path lets the team demo Thai crisis intake, VAD state, triage, and dashboard updates without external phone-number provisioning.

**Alternatives considered**:

- Twilio Media Streams first: rejected because phone-number setup is out of scope and would block V0.
- Azure Communication Services Call Automation first: rejected because phone-number availability is out of scope.
- Direct browser-to-Azure voice session: rejected for V0 because backend-side VAD, timing logs, safety rules, and provider fallback need to be controlled in one place.

## Decision 2: Server-side turn manager with local VAD abstraction

**Decision**: Implement `VadService` as a replaceable turn manager that accepts 20 ms PCM16 mono frames, keeps 150-250 ms pre-speech padding, and defaults to a 750 ms end-of-turn silence threshold within the required 600-900 ms range.

**Rationale**: Server-side VAD gives consistent debug state, timing logs, and barge-in detection regardless of browser differences. A simple energy-based VAD should be the default fallback because it has no native build dependency; WebRTC VAD can be plugged in when available.

**Alternatives considered**:

- WebRTC VAD only: rejected because native packaging can slow hackathon development.
- Azure/server semantic VAD only: rejected because local VAD before AI submission is a requirement.
- Browser-only VAD: rejected because backend timing logs and consistent state transitions are required.

## Decision 3: Replaceable voice provider interface

**Decision**: Define `VoiceAgentProvider` with three V0 implementations: `MockVoiceProvider`, `AzureVoiceLiveProvider`, and `AzureSpeechOpenAIProvider`.

**Rationale**: Microsoft documents Voice Live as a WebSocket interface for realtime voice applications and its API reference includes PCM16 audio and built-in turn-detection capabilities. The fallback path uses Azure Speech for realtime recognition, Azure OpenAI structured outputs for triage JSON, and Azure Speech text-to-speech for spoken replies. Mock mode keeps the demo usable when Azure credentials or regional model capacity are missing.

**Alternatives considered**:

- Azure Voice Live only: rejected because credentials, regional availability, or model access may block V0.
- Azure OpenAI Realtime as primary: rejected because the user explicitly asked not to make it the primary dependency.
- Mock only: rejected because the hackathon demo needs a visible Microsoft Azure integration path.

**References**:

- [Voice Live how-to](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)
- [Voice Live API reference](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-api-reference-2025-10-01)
- [Azure Speech realtime recognition](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)
- [Azure Speech text to speech](https://learn.microsoft.com/en-us/azure/ai-services/Speech-Service/text-to-speech)

## Decision 4: Structured triage with deterministic safety overlay

**Decision**: Use a schema-validated triage extraction model and then apply deterministic safety rules in `TriageService`: RED indicators force RED and human review, confidence below 0.70 forces human review, and no rule may auto-dispatch or deny help.

**Rationale**: Azure OpenAI structured outputs are preferred over plain JSON mode because they constrain output to a schema. If structured outputs are unavailable for the selected model, JSON mode may be used only with validation, retry, and a safe fallback case that requires human review.

**Alternatives considered**:

- Prompt-only JSON: rejected because JSON mode can produce valid JSON that still does not match the required schema.
- Rules-only triage: rejected because free-form Thai caller reports need language understanding and summarization.
- AI-only triage: rejected because crisis safety constraints require deterministic enforcement.

**References**:

- [Azure OpenAI structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)
- [Azure OpenAI JSON mode](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/json-mode)

## Decision 5: Cosmos DB repository with local JSON fallback

**Decision**: Define `CaseRepository` and ship `LocalCaseRepository` first using a JSON file under `backend/.data/cases.json`. Add `CosmosCaseRepository` for Azure Cosmos DB when `COSMOS_DB_*` settings are present.

**Rationale**: Repository isolation is necessary because V0 must run locally without Azure credentials but still demonstrate the intended Azure storage path. Cosmos DB stores JSON documents naturally and the Python SDK supports item operations against databases and containers.

**Alternatives considered**:

- Cosmos-only storage: rejected because missing credentials would break offline demos.
- SQLite fallback: deferred because JSON is enough for single-station hackathon data and simpler to inspect.
- In-memory only: rejected because case refresh and restart resilience are useful during demos.

**Reference**:

- [Azure Cosmos DB Python get started](https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-python-get-started)

## Decision 6: Realtime dashboard adapter with local fallback

**Decision**: Use a `RealtimeNotifier` abstraction. In cloud mode, prefer Azure SignalR Service when configured. In local mode, provide FastAPI WebSocket or SSE broadcasts for case and debug events.

**Rationale**: Azure SignalR Service is intended for web apps with realtime features, but local fallback avoids blocking the dashboard when the connection string is missing. SignalR service modes have operational implications, so V0 should keep the notifier isolated and allow a local path.

**Alternatives considered**:

- Polling only: rejected because dashboard updates without manual refresh are required and polling makes the demo less immediate.
- SignalR only: rejected because it would break offline demos.
- Browser-to-backend WebSocket only forever: rejected because the deployment target calls for Azure SignalR polish.

**References**:

- [Azure SignalR Service documentation](https://learn.microsoft.com/en-us/azure/azure-signalr/)
- [Azure SignalR service modes](https://learn.microsoft.com/en-us/azure/azure-signalr/concept-service-mode)

## Decision 7: Compact command-center UI using shadcn/ui composition

**Decision**: Build a compact Next.js command-center interface with routes for Live Cases, Case Detail, Voice Debug Console, and Upload Evidence. Initialize shadcn/ui after the frontend scaffold and compose standard components such as Sidebar, Table, Badge, Card, Tabs, Sheet/Dialog, Tooltip, Separator, and Toast.

**Rationale**: The UI is operational, not marketing-led. A dense but readable command-center layout fits crisis operator workflows better than a landing page or decorative card grid. shadcn/ui keeps components source-controlled and fits the requested Tailwind CSS stack.

**Alternatives considered**:

- Custom-only component system: rejected because shadcn/ui provides accessible primitives and faster dashboard composition.
- Marketing landing page: rejected because the first screen must be the usable operator experience.
- Large illustrative dashboard: rejected because operators need scan speed, clear priority colors, and compact details.

## Decision 8: Evidence upload is simulated in V0, Blob SAS later

**Decision**: Implement only a placeholder upload-link simulation in V0. The production plan uses Azure Blob Storage with short-lived SAS URLs and stores metadata on the case.

**Rationale**: The feature says evidence upload is optional and must not distract from local microphone triage. Azure Storage SAS supports limited access with scoped permissions and expiration; user delegation SAS is preferred where possible.

**Alternatives considered**:

- Real upload in V0: deferred to keep the core voice and dashboard workflow smaller.
- Store binary evidence in Cosmos DB: rejected because Cosmos should only hold metadata.

**Reference**:

- [Azure Blob Storage user delegation SAS](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-user-delegation-sas-create-cli)

## Decision 9: Environment and observability

**Decision**: Use `.env` for local development, commit only `.env.example`, and plan Application Insights through Azure Monitor OpenTelemetry for the backend. Do not log secrets, raw audio bytes, or full sensitive prompts by default.

**Rationale**: The app needs hackathon diagnostics without leaking sensitive caller data. Application Insights supports OpenTelemetry-based telemetry for server applications, while browser telemetry can be handled separately if needed.

**Alternatives considered**:

- Plain console logs only: rejected because Azure-focused demos benefit from Application Insights readiness.
- Capture full prompt/audio logs by default: rejected because crisis data is sensitive.

**Reference**:

- [Application Insights OpenTelemetry overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry)

## Decision 10: Azure deployment targets

**Decision**: Plan deployment as frontend on Azure Static Web Apps and backend on Azure Container Apps, with Cosmos DB, SignalR, and Application Insights added as configured services.

**Rationale**: Static Web Apps supports modern JavaScript frameworks including Next.js and can link to existing backend services. Container Apps is appropriate for the FastAPI service, WebSocket endpoint, and provider adapters.

**Alternatives considered**:

- Single container for frontend and backend: rejected because the requested deployment separates frontend and backend.
- Serverless-only backend: deferred because the local WebSocket audio stream and VAD service are simpler in a long-running FastAPI process.

**Reference**:

- [Azure Static Web Apps overview](https://learn.microsoft.com/en-us/azure/static-web-apps/overview)

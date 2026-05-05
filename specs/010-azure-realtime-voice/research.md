# Research: Azure Realtime Voice Provider Spike

## Decision: Keep Current Pipeline as Default

**Decision**: `ENABLE_REALTIME_VOICE=false` and `REALTIME_PROVIDER=none` remain the default runtime settings.

**Rationale**: The existing Narayana demo path is validated and has deterministic fallback behavior. Realtime models and Voice Live availability can depend on Azure resource type, region, deployment model, and preview/GA endpoint format. The spike should not block Twilio calls, local mic testing, or mock-mode demos.

**Alternatives considered**:

- Make Azure Voice Live primary immediately. Rejected because Voice Live setup requires an eligible Foundry or Speech resource and supported models/regions.
- Make Azure OpenAI GPT Realtime primary immediately. Rejected because realtime model deployments require supported regions and the endpoint/API format can vary by GA versus preview.

## Decision: Add a Separate RealtimeVoiceProvider Interface

**Decision**: Add a streaming-focused provider interface with `connect()`, `send_audio_frame()`, `receive_audio_event()`, and `close()`.

**Rationale**: The existing `VoiceAgentProvider` processes committed turns. Realtime providers maintain a live session and can emit partial/streaming audio before a local VAD turn is complete. A separate interface keeps the current pipeline clean and makes fallback explicit.

**Alternatives considered**:

- Extend `VoiceAgentProvider.process_turn()`. Rejected because it hides the streaming lifecycle and does not represent provider output arriving while caller audio is still flowing.
- Push realtime logic into `routes_twilio.py` directly. Rejected because provider selection, health, safety setup, and event normalization would become hard to test.

## Decision: Implement Skeleton AzureVoiceLiveProvider and AzureOpenAIRealtimeProvider

**Decision**: Add both experimental providers as skeletons that validate configuration, build safe session instructions, connect using WebSocket only when configured, normalize events, and fail safely.

**Rationale**: The team wants to compare Azure Voice Live API and Azure OpenAI GPT Realtime API. A consistent interface allows manual testing of either provider and mocked unit tests without real Azure credentials.

**Alternatives considered**:

- Implement only Azure OpenAI GPT Realtime first. Rejected because Voice Live is explicitly in scope and may be more aligned with Azure speech/voice scenarios.
- Implement fully production-ready provider behavior now. Rejected because this is a spike; production connection recovery, scale-out state, and full media compatibility are out of scope.

## Decision: Use WebSocket for Backend-to-Provider Spike

**Decision**: Use provider WebSocket clients in the FastAPI backend for the spike.

**Rationale**: Twilio Media Streams already terminates phone audio at the backend, so the backend is the natural server-to-server bridge. Microsoft documentation lists WebSocket as a supported Realtime API connection method and describes it as suitable for backend/custom middleware scenarios. Voice Live also exposes a WebSocket endpoint.

**Alternatives considered**:

- WebRTC direct from browser. Rejected because this feature targets Twilio call media already received by FastAPI.
- SIP direct to realtime API. Rejected for this spike because Twilio is already integrated and the goal is to reuse the current webhook/media stream path.

**Sources**:

- Microsoft Learn: [Use the GPT Realtime API for speech and audio](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio)
- Microsoft Learn: [Use the GPT Realtime API via WebSockets](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio-websockets)
- Microsoft Learn: [How to use the Voice Live API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)

## Decision: Treat Azure Realtime Region/Deployment as Manual Prerequisite

**Decision**: The provider must remain disabled unless required realtime settings are present. README and health output must warn that Azure OpenAI realtime models may require supported regions such as East US 2 or Sweden Central and an existing realtime deployment.

**Rationale**: Current Microsoft documentation states GPT realtime models are available through supported regions/deployments and describes WebSocket endpoint differences between GA and preview formats. The app should not assume the existing Southeast Asia Container App region has a matching realtime model deployment.

**Alternatives considered**:

- Auto-create or auto-deploy realtime models. Rejected because model deployment, quota, region choice, and secrets are outside this feature.
- Fail startup when realtime config is missing. Rejected because realtime is an optional spike.

## Decision: Preserve Crisis-Only Safety Prompt and Fallback

**Decision**: Realtime session setup must reuse the existing crisis-intake system prompt or guardrail prompt builder and must enforce fallback to the current path on provider error.

**Rationale**: Realtime output could otherwise bypass prior scope guardrails, no-dispatch claims, and no-diagnosis rules. The realtime provider should be a lower-latency audio transport experiment, not a different assistant personality.

**Alternatives considered**:

- Let provider defaults control behavior. Rejected because Narayana must stay a crisis intake assistant.
- Block all realtime output until model safety is post-processed. Rejected for the spike because it would erase the latency benefit; instead, use safe session instructions plus fallback/error handling and audit logging.

## Decision: Latency Instrumentation Lives at Routing and Provider Boundaries

**Decision**: Record latency samples at Twilio media receipt, provider connect, input audio sent, first output audio received, response started, response completed, and fallback.

**Rationale**: The purpose of the spike is comparing perceived latency. Instrumenting both the routing boundary and provider boundary gives enough signal without logging audio payloads or storing new database records.

**Alternatives considered**:

- Only log total call duration. Rejected because it cannot isolate realtime provider delays.
- Persist all latency metrics in Cosmos DB. Rejected because no new storage resource is in scope.

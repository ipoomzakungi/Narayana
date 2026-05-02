# Research: Narayana AI Azure Voice Gateway

## Decision 1: Use local microphone as the required V0 input

**Decision**: V0 starts with browser microphone capture streamed to FastAPI over `/ws/local-audio`.

**Rationale**: The hackathon goal is to validate VAD, Azure speech processing, triage extraction, and case creation before phone-provider integration. This avoids dependency on Twilio or ACS phone-number availability.

**Alternatives considered**:

- Twilio first: rejected because V0 must not depend on working phone numbers.
- ACS inbound calling first: rejected because phone acquisition and Thailand capabilities need separate validation.
- Uploaded audio first: kept optional, but not sufficient to prove microphone turn-taking.

## Decision 2: Energy-based VAD first, optional WebRTC VAD later

**Decision**: Implement energy-based VAD first using 20 ms PCM frames, 600-900 ms end-of-turn silence, and 150-250 ms pre-speech buffer. Add WebRTC VAD only if the dependency is reliable in the target environment.

**Rationale**: Energy-based VAD is fast to build, dependency-light, and adequate for proving state transitions, debug events, and turn commits during a hackathon demo.

**Alternatives considered**:

- WebRTC VAD only: rejected because native dependency issues could block V0.
- Provider-only VAD: rejected because V0 requires visible local VAD state before provider submission.

## Decision 3: Make Azure Speech + Azure OpenAI the stable provider

**Decision**: Implement `AzureSpeechOpenAIProvider` as the primary stable Azure provider: Azure Speech STT converts committed turns to text, then Azure OpenAI structured outputs produce crisis JSON.

**Rationale**: Azure Speech supports real-time transcription from microphone/file/custom streams. Azure OpenAI structured outputs support schema-constrained JSON, which is better for the crisis case contract than prompt-only parsing.

**Alternatives considered**:

- Azure Voice Live only: rejected as a sole dependency because V0 needs a stable fallback.
- Azure OpenAI Realtime: not required for V0 because realtime model region availability may be limited.
- Mock only: rejected because the hackathon needs a credible Azure path.

**References**:

- [Azure Speech to text](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-to-text)
- [Azure Speech SDK audio module](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.audio)
- [Azure OpenAI structured outputs](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs)

## Decision 4: Keep Azure Voice Live experimental and optional

**Decision**: Implement `AzureVoiceLiveProvider` as an optional provider when `AZURE_VOICE_LIVE_ENDPOINT` and `AZURE_VOICE_LIVE_MODEL` are configured.

**Rationale**: Voice Live supports WebSocket realtime voice applications, PCM16 audio, turn detection options, and interruptible conversations. It is useful for a polished Azure demo, but it must not replace the stable Speech + OpenAI path.

**Alternatives considered**:

- Remove Voice Live: rejected because the module should optimize the Azure voice/AI pipeline and show a forward-looking provider.
- Make Voice Live mandatory: rejected because V0 must degrade gracefully.

**References**:

- [Voice Live API reference](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-api-reference)
- [Voice Live how-to](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)
- [Azure AI VoiceLive Python client](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-voicelive-readme)

## Decision 5: Apply deterministic safety rules after provider output

**Decision**: Provider output is never final. `safety_rules.py` validates and adjusts triage/review flags before the case is stored or emitted.

**Rationale**: Crisis safety rules must be consistent and auditable. RED must be forced for explicit high-risk indicators, and low-confidence or missing-location cases must require human review.

**Alternatives considered**:

- AI-only triage: rejected because it can downgrade or miss critical safety constraints.
- Rules-only triage: rejected because Thai natural-language extraction still benefits from speech and language models.

## Decision 6: Keep Twilio and ACS as V1 adapters only

**Decision**: Define `TwilioMediaStreamAdapter` and `ACSAudioStreamAdapter` as placeholder interfaces but do not wire them into V0 runtime.

**Rationale**: Azure Communication Services phone-number purchasing requires paid subscription eligibility and region/country capability checks. Thailand number support and Twilio trial restrictions also need separate validation. V0 should prove the voice gateway without those blockers.

**Alternatives considered**:

- Remove telephony abstractions: rejected because V1 needs a clean integration seam.
- Enable telephony adapters in V0: rejected because phone providers are explicitly out of scope.

**Reference**:

- [Azure Communication Services phone number planning](https://learn.microsoft.com/en-us/azure/communication-services/concepts/telephony/plan-solution)

## Decision 7: Use repository adapter for local and Cosmos case storage

**Decision**: Use `CaseRepository` with `LocalCaseRepository` as default and `CosmosCaseRepository` when Cosmos variables are present.

**Rationale**: The gateway must emit a case even without storage, but the hackathon demo benefits from local persistence and an Azure storage story.

**Alternatives considered**:

- Cosmos-only: rejected because local mock mode must work offline.
- In-memory only: rejected because demo refresh/restart behavior benefits from local persistence.

## Decision 8: Build a compact debug console

**Decision**: The frontend is a compact developer console showing microphone controls, VAD state, debug events, transcript, structured JSON, safety result, and case preview.

**Rationale**: This module is an engineering proof point, not a marketing surface. A command-center UI helps reviewers see the pipeline stages directly.

**Alternatives considered**:

- Full operator dashboard first: deferred because the module’s immediate goal is gateway validation.
- Landing page: rejected because it does not prove the audio/AI pipeline.

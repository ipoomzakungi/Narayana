# Adapter Interface Contracts

## AudioInputAdapter

All audio inputs normalize into the same gateway frame contract.

```python
class AudioInputAdapter(Protocol):
    name: str
    enabled: bool

    async def start(self, session_id: str) -> None: ...
    async def receive_frame(self) -> AudioFrame: ...
    async def stop(self, session_id: str) -> None: ...
```

### `LocalMicAdapter`

- Required for V0.
- Receives browser WebSocket `audio.frame` messages.
- Produces PCM16 mono 20 ms frames.

### `TwilioMediaStreamAdapter`

- V1 interface only.
- Must not be selected when `USE_MOCK_SERVICES=true` or in default V0 configuration.
- Exists only to document future mapping from Twilio media stream events to `AudioFrame`.

### `ACSAudioStreamAdapter`

- V1 interface only.
- Must not be selected in default V0 configuration.
- Exists only to document future mapping from ACS call audio to `AudioFrame`.

## VoiceAgentProvider

```python
class VoiceAgentProvider(Protocol):
    mode: ProviderMode

    async def process_turn(self, turn: CallerTurn) -> VoiceProviderResult: ...
    async def health(self) -> ProviderHealth: ...
```

### `MockVoiceProvider`

- Always available.
- Returns deterministic outputs for Thai flood sample, minor property damage, unclear/noisy speech, and safety fixtures.

### `AzureSpeechOpenAIProvider`

- Primary stable Azure provider.
- Uses Azure Speech for STT.
- Uses Azure OpenAI structured outputs for `TriageCase`.
- May optionally produce short safe response text and Azure Speech TTS later.

### `AzureVoiceLiveProvider`

- Optional experimental provider.
- Connects to Azure Voice Live over WebSocket when configured.
- If it cannot produce structured crisis JSON directly, passes transcript to Azure OpenAI triage.

## CaseRepository

```python
class CaseRepository(Protocol):
    async def create(self, case: TriageCase, session_id: str | None, source_provider: ProviderMode) -> CaseRepositoryRecord: ...
    async def get(self, case_id: str) -> CaseRepositoryRecord | None: ...
```

### `LocalCaseRepository`

- Default V0 repository.
- Stores JSON locally or keeps in-memory state if file storage is disabled.

### `CosmosCaseRepository`

- Enabled only when all Cosmos variables exist.
- Stores the same `TriageCase` JSON without changing API responses.

## Runtime Selection Rules

- Local mic adapter is enabled by default.
- Twilio and ACS adapters are disabled by default.
- Mock provider is selected when `USE_MOCK_SERVICES=true`.
- Azure Speech/OpenAI provider is selected when mock mode is false and required Azure variables exist.
- Azure Voice Live provider is selected only when explicitly configured.
- Repository falls back to local when Cosmos variables are incomplete.

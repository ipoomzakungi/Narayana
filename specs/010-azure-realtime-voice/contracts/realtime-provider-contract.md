# Contract: Realtime Voice Provider

This is an internal backend contract for experimental realtime voice providers. It is intentionally separate from the current turn-based `VoiceAgentProvider` contract.

## Provider Selection

```text
REALTIME_PROVIDER=none | azure_voice_live | azure_openai_realtime
ENABLE_REALTIME_VOICE=false | true
```

Selection rules:

- If `ENABLE_REALTIME_VOICE=false`, return a disabled/noop realtime provider decision.
- If `REALTIME_PROVIDER=none`, return a disabled/noop realtime provider decision.
- If provider-specific configuration is incomplete, return a not-configured decision with warnings.
- If configured, construct the selected provider session for the Twilio call.

## Interface

```python
class RealtimeVoiceProvider(Protocol):
    mode: RealtimeProviderMode

    async def connect(self, *, session_id: str, call_id: str | None, instructions: str) -> RealtimeConnectionResult:
        ...

    async def send_audio_frame(self, frame: AudioFrame) -> RealtimeSendResult:
        ...

    async def receive_audio_event(self) -> RealtimeAudioEvent | None:
        ...

    async def close(self) -> None:
        ...
```

## RealtimeConnectionResult

```json
{
  "connected": true,
  "provider": "azure_openai_realtime",
  "warnings": [],
  "latency_ms": 138
}
```

Failure shape:

```json
{
  "connected": false,
  "provider": "azure_openai_realtime",
  "warnings": ["Azure realtime deployment is not configured."],
  "fallback_reason": "not_configured",
  "latency_ms": 0
}
```

## RealtimeAudioEvent

Provider output events must normalize into one of these types:

```json
{
  "event_type": "audio.output.received",
  "audio_format": "mulaw_8khz",
  "audio_base64": "<not logged>",
  "latency_ms": 212,
  "metadata": {
    "provider_event_type": "response.audio.delta"
  }
}
```

```json
{
  "event_type": "response.started",
  "latency_ms": 180,
  "metadata": {
    "provider_event_type": "response.created"
  }
}
```

```json
{
  "event_type": "error",
  "fallback_reason": "provider_error",
  "warnings": ["Realtime provider returned an error."]
}
```

## Safety Contract

- The `instructions` passed to `connect()` must be derived from Narayana's crisis-intake system prompt.
- Provider output must not be allowed to claim rescue dispatch, diagnose, or become a general chatbot.
- If provider output cannot be safely interpreted or normalized, the caller must be routed back to the current turn-based path.

## Logging Contract

Allowed event names:

- `realtime.connected`
- `realtime.audio.input.sent`
- `realtime.audio.output.received`
- `realtime.response.started`
- `realtime.response.completed`
- `realtime.error`
- `realtime.fallback`

Required metadata:

- `session_id`
- `call_id` when available
- `provider`
- `latency_ms` when measurable
- safe warning/fallback reason when relevant

Forbidden metadata:

- API keys
- authorization headers
- raw input audio payloads
- raw output audio payloads

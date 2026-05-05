# Data Model: Azure Realtime Voice Provider Spike

## RealtimeProviderConfig

Represents the selected optional realtime voice provider and whether it is usable.

**Fields**

- `enabled`: boolean from `ENABLE_REALTIME_VOICE`, default `false`
- `provider`: enum `none | azure_voice_live | azure_openai_realtime`, default `none`
- `azure_realtime_endpoint`: optional endpoint for Azure OpenAI GPT Realtime
- `azure_realtime_api_key_present`: boolean only, never the key value
- `azure_realtime_deployment`: optional deployment/model name
- `azure_realtime_api_version`: optional API version
- `azure_voice_live_endpoint`: optional Voice Live endpoint
- `azure_voice_live_model`: optional Voice Live model name
- `configured`: boolean derived from provider-specific required fields
- `warnings`: list of safe configuration warnings

**Validation rules**

- `enabled=false` always makes the realtime route inactive even if provider settings exist.
- `provider=none` always makes the realtime route inactive.
- Missing required fields must produce warnings and fallback, not backend startup failure.
- Health/debug output must never expose API keys.

## RealtimeVoiceSession

Tracks one experimental realtime provider connection for a Twilio call.

**Fields**

- `session_id`: Narayana session identifier, usually `twilio_{call_id}`
- `call_id`: Twilio CallSid
- `stream_sid`: Twilio stream identifier when available
- `provider`: selected realtime provider
- `status`: `disabled | connecting | connected | streaming | fallback | closed | error`
- `connected_at`: optional timestamp
- `closed_at`: optional timestamp
- `fallback_reason`: optional safe reason string
- `latency_samples`: list of `RealtimeLatencySample`

**State transitions**

```text
disabled -> fallback
connecting -> connected -> streaming -> closed
connecting -> fallback
connected -> fallback
streaming -> fallback
streaming -> closed
```

**Validation rules**

- A session must close the provider connection when the Twilio WebSocket ends.
- A provider error must move the session to `fallback` and allow the current turn-based pipeline to continue.

## RealtimeAudioEvent

Normalized event exchanged between Twilio routing and a realtime provider.

**Fields**

- `event_type`: `connected | input_audio_sent | output_audio_received | response_started | response_completed | error | fallback`
- `session_id`: Narayana session identifier
- `call_id`: optional Twilio call identifier
- `sequence`: optional Twilio audio sequence number
- `audio_base64`: optional provider/Twilio-compatible audio payload for outbound media only; never logged
- `audio_format`: optional format label such as `mulaw_8khz` or provider-native format
- `text`: optional text delta/transcript if provider emits one
- `metadata`: safe structured metadata
- `created_at`: timestamp

**Validation rules**

- Logs and audit records must redact or omit `audio_base64`.
- Outbound audio to Twilio must be Twilio-compatible before sending as media events.
- Provider text must be subject to crisis-intake safety constraints before being shown or stored as assistant output.

## RealtimeLatencySample

Measures one stage in the realtime or fallback voice path.

**Fields**

- `stage`: `connect | input_audio_sent | first_output_audio | response_started | response_completed | fallback | current_pipeline_turn`
- `started_at`: timestamp
- `completed_at`: optional timestamp
- `latency_ms`: optional non-negative integer
- `provider`: selected provider
- `session_id`: Narayana session identifier
- `metadata`: safe structured metadata

**Validation rules**

- Latency values must be non-negative.
- Missing completion timestamps are allowed for failed or interrupted stages.
- Metadata must never contain secrets or raw audio.

## RealtimeFallbackDecision

Records why Narayana chose the current turn-based path instead of realtime.

**Fields**

- `session_id`: Narayana session identifier
- `call_id`: optional Twilio call identifier
- `provider`: selected realtime provider
- `reason`: safe enum/string, such as `disabled`, `not_configured`, `connect_failed`, `stream_failed`, `provider_error`, `provider_closed`, `unsafe_output`
- `occurred_at`: timestamp
- `latency_ms_before_fallback`: optional integer
- `warnings`: safe warning list

**Validation rules**

- Fallback must never close an otherwise usable Twilio call by itself.
- Fallback must not create duplicate cases or duplicate assistant replies for the same caller audio segment.

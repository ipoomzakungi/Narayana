# Data Model: Telephony Adapter Spike

## CallMetadata

Represents provider metadata attached to a phone-originated voice session.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `provider` | `TelephonyProvider` | Yes | `twilio`, `acs`, or `none` for non-telephony contexts. |
| `call_id` | `string` | Yes | Provider call identifier, such as Twilio `CallSid`. |
| `from_number` | `string | null` | No | Caller number if provided by the provider. |
| `to_number` | `string | null` | No | Narayana test number if provided by the provider. |
| `country` | `string | null` | No | Configured test country or provider-supplied country value. |
| `codec` | `TelephonyCodec` | Yes | Expected first spike value is `mulaw`. |
| `sample_rate` | `int` | Yes | Twilio media stream expected value is `8000`. |
| `started_at` | `datetime` | Yes | UTC timestamp for the phone session start. |
| `raw_provider_payload` | `dict | null` | No | Debug only; not intended as production retention policy. |

Validation rules:

- `call_id` must be present for phone-originated sessions.
- `sample_rate` must be positive.
- `raw_provider_payload` should only include compact debug metadata, not unbounded media payloads.

## TelephonyProvider

Enum for configured phone-provider state.

Values:

- `none`
- `twilio`
- `acs`

Validation rules:

- App startup must allow `none`.
- Twilio routes may be registered even when provider is `none`, but must return clear not-configured behavior for real call setup.

## TelephonyCodec

Enum for provider audio codec values.

Values:

- `mulaw`
- `pcm16`
- `unknown`

Validation rules:

- Twilio media normalization supports `mulaw` to `pcm16` conversion for V1.
- Unsupported codecs should produce a recoverable WebSocket error, not crash the app.

## TelephonySession

Runtime association between call metadata and the shared audio session.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `session_id` | `string` | Yes | Internal Narayana session id, typically derived from the call id. |
| `source_input_mode` | `string` | Yes | `twilio_call` or future `acs_call`. |
| `call_metadata` | `CallMetadata` | Yes | Phone-provider metadata. |
| `provider_mode` | `ProviderMode` | No | Mock or Azure provider mode requested for processing. |
| `created_at` | `datetime` | Yes | UTC timestamp. |
| `closed_at` | `datetime | null` | No | Set when provider sends stop or socket disconnects. |

Relationships:

- A `TelephonySession` owns many normalized `AudioFrame` values.
- A committed turn from the session writes one WAV artifact through `AudioBufferService`.
- A session may create zero or more `CrisisCase` records, matching the local microphone behavior.

## Normalized Audio Frame

Provider audio converted into the existing `AudioFrame` model.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `session_id` | `string` | Yes | Shared with `TelephonySession`. |
| `sequence` | `int` | Yes | Derived from provider sequence or incremented locally. |
| `timestamp_ms` | `int` | Yes | Derived from provider timestamp if present. |
| `encoding` | `string` | Yes | Must be `pcm16` after normalization. |
| `sample_rate_hz` | `int` | Yes | `8000` for Twilio unless resampling is added. |
| `channels` | `int` | Yes | Must be `1`. |
| `duration_ms` | `int` | Yes | Must be `20`. |
| `audio_base64` | `string` | Yes | Base64 encoded PCM16 bytes. |
| `assistant_is_speaking` | `bool` | No | Used for existing barge-in handling. |

Validation rules:

- Converted PCM16 payload must contain an even number of bytes.
- Frame duration must remain 20 ms for the existing VAD and turn manager.

## Phone-Originated Case Payload

The final WebSocket payload for a phone-created case extends the existing `triage.case.created` payload with source metadata.

Additional fields:

- `source_input_mode`: `twilio_call` or future `acs_call`.
- `call_metadata`: serialized `CallMetadata`.

Validation rules:

- Existing case schema and safety behavior remain unchanged.
- Phone-originated cases must never auto-dispatch, auto-close, or bypass human review rules.

## Provider Configuration State

Represents whether phone-provider routes can accept real calls.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `voice_input_mode` | `string` | Yes | Defaults to `local_mic`. |
| `telephony_provider` | `TelephonyProvider` | Yes | Defaults to `none`. |
| `phone_test_country` | `string` | No | Documentation/debug only. |
| `phone_test_number` | `string` | No | Documentation/debug only. |
| `twilio_configured` | `bool` | Derived | True only when required Twilio vars are present. |
| `acs_configured` | `bool` | Derived | True only when required ACS vars are present. |

Validation rules:

- Missing Twilio or ACS values must not prevent app startup.
- Health/debug output should surface unavailable provider state clearly.

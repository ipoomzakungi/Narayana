# Data Model: Narayana AI Azure Voice Gateway

## Enumerations

### InputMode

- `local_mic`
- `uploaded_audio`
- `twilio_media_stream`
- `acs_audio_stream`

### VadState

- `silence`
- `speech`
- `listening`
- `thinking`
- `speaking`

### ProviderMode

- `mock`
- `azure_speech_openai`
- `azure_voice_live`

### IncidentType

- `flood`
- `fire`
- `medical`
- `accident`
- `earthquake`
- `public_safety`
- `unknown`

### TriageLevel

- `RED`
- `YELLOW`
- `GREEN`

### CaseStatus

- `pending`
- `contacted`
- `dispatched`
- `resolved`
- `closed`

## Entity: VoiceGatewaySession

Tracks one local microphone, uploaded audio, or future phone-provider session.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `session_id` | string | yes | Unique session identifier. |
| `input_mode` | InputMode | yes | V0 default is `local_mic`; Twilio/ACS modes are disabled by default. |
| `provider_mode` | ProviderMode | yes | Selected provider after config resolution. |
| `current_state` | VadState | yes | Current visible gateway state. |
| `sample_rate_hz` | integer | yes | V0 target is 16000 Hz. |
| `frame_ms` | integer | yes | V0 target is 20 ms. |
| `created_at` | datetime | yes | UTC timestamp. |
| `updated_at` | datetime | yes | UTC timestamp. |
| `case_id` | string | no | Set after case creation. |

## Entity: AudioFrame

Represents one browser-sent audio frame.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `session_id` | string | yes | Associated session. |
| `sequence` | integer | yes | Monotonic per session. |
| `timestamp_ms` | integer | yes | Client-side stream timestamp. |
| `encoding` | string | yes | `pcm16` for V0. |
| `sample_rate_hz` | integer | yes | Should match session target. |
| `channels` | integer | yes | Mono for V0. |
| `duration_ms` | integer | yes | 20 ms target. |
| `audio_base64` | string | yes | Encoded PCM payload. |
| `assistant_is_speaking` | boolean | yes | Used for barge-in detection. |

## Entity: DebugEvent

Represents VAD, turn, provider, or barge-in telemetry.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `event_id` | string | yes | Unique event ID. |
| `session_id` | string | yes | Associated session. |
| `case_id` | string | no | Present after case creation. |
| `event_type` | string | yes | One of required debug event names. |
| `state` | VadState | no | Present for state events. |
| `timestamp` | datetime | yes | UTC timestamp. |
| `duration_ms` | integer | no | Optional event duration. |
| `metadata` | object | no | Non-secret diagnostics only. |

Required event names:

- `audio.frame.received`
- `vad.speech.start`
- `vad.speech.end`
- `turn.committed`
- `ai.request.started`
- `ai.response.started`
- `ai.response.completed`
- `barge_in.detected`

## Entity: CallerTurn

Completed user speech segment after VAD and turn management.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `turn_id` | string | yes | Unique per session. |
| `session_id` | string | yes | Associated session. |
| `started_at` | datetime | yes | UTC timestamp. |
| `ended_at` | datetime | yes | UTC timestamp. |
| `duration_ms` | integer | yes | Turn duration. |
| `pre_speech_padding_ms` | integer | yes | 150-250 ms target. |
| `silence_threshold_ms` | integer | yes | 600-900 ms target. |
| `audio_ref` | string | no | Internal reference, not raw audio in logs. |
| `barge_in` | boolean | yes | True if caller interrupted assistant output. |

## Entity: VoiceProviderResult

Common provider output before safety rules.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `provider_mode` | ProviderMode | yes | Provider that produced the result. |
| `transcript` | string | yes | Final transcript for committed turn. |
| `language` | string | yes | Expected `th` for Thai demo. |
| `confidence` | number | yes | 0.0 to 1.0. |
| `triage` | TriageCase | yes | Structured provider triage JSON. |
| `response_text` | string | no | Optional short safe guidance. |
| `provider_warnings` | string[] | yes | Fallbacks or recoverable issues. |

## Entity: TriageCase

The structured crisis JSON produced by provider plus safety rules.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `case_id` | string | yes | Generated if provider omits it. |
| `language` | string | yes | `th`, `en`, or detected language code. |
| `incident_type` | IncidentType | yes | Controlled enum. |
| `triage_level` | TriageLevel | yes | Safety rules may force RED. |
| `confidence` | number | yes | 0.0 to 1.0. |
| `location_text` | string | yes | Empty string means missing location. |
| `people_affected` | integer/null | yes | Null when unknown. |
| `injuries` | string | yes | Empty string allowed if none mentioned. |
| `immediate_needs` | string[] | yes | Rescue, medical, evacuation, information, etc. |
| `caller_phone_optional` | string/null | yes | Null for local microphone V0. |
| `ai_summary` | string | yes | Short operator/developer summary. |
| `triage_reason` | string | yes | Must include extracted evidence and safety reason. |
| `human_review_required` | boolean | yes | True for RED, confidence < 0.75, missing location, or contradictions. |
| `missing_fields` | string[] | yes | Includes `location_text` when missing. |
| `created_at` | datetime | yes | UTC timestamp. |
| `updated_at` | datetime | yes | UTC timestamp. |
| `status` | CaseStatus | yes | Initial value `pending`. |

## Entity: SafetyRuleResult

Deterministic post-AI rule output.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `forced_triage_level` | TriageLevel/null | yes | RED when a RED trigger is present. |
| `human_review_required` | boolean | yes | Final review decision. |
| `matched_rules` | string[] | yes | Rule IDs, for example `red.breathing_difficulty`. |
| `reason` | string | yes | Explainable safety overlay reason. |

## Entity: CaseRepositoryRecord

Persistence wrapper for local or Cosmos case storage.

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `case` | TriageCase | yes | Stored case payload. |
| `session_id` | string | no | Source session. |
| `source_provider` | ProviderMode | yes | Provider used. |
| `debug_event_count` | integer | yes | Number of associated debug events. |
| `stored_at` | datetime | yes | UTC timestamp. |

## State Transitions

### VAD State

```text
listening -> silence -> speech -> thinking -> speaking -> listening
speech -> speech -> silence -> turn.committed -> thinking
speaking -> barge_in.detected -> speech
```

### Case Status

```text
pending -> contacted -> dispatched -> resolved -> closed
pending -> resolved -> closed
pending -> closed
```

Rules:

- The gateway creates cases with `pending` only.
- The gateway never sets `dispatched`, `resolved`, or `closed` automatically.
- Human/operator workflow owns later status transitions.

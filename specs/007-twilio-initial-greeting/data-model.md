# Data Model: Twilio Initial Greeting

## InitialGreetingSettings

Operator-controlled runtime configuration for first-greeting speak-back.

| Field | Type | Validation / Default |
|-------|------|----------------------|
| `enable_twilio_initial_greeting` | boolean | Default `false`; must be explicitly enabled for greeting playback |
| `twilio_initial_greeting_text` | string | Defaults to the approved short Thai greeting; blank values are treated as unconfigured/unsafe and replaced by safe spoken text |
| `twilio_initial_greeting_profile` | string | Default `greeting`; must resolve to a supported TTS profile |
| `twilio_initial_greeting_fallback_say` | boolean | Default `false`; reserved for optional provider-native fallback |
| `tts_rate_greeting` | string | Default `-5%`; used by SSML prosody for greeting |
| `tts_pitch_greeting` | string | Default `0%`; used by SSML prosody for greeting |

## TTSProfile

Supported spoken-output profile enum.

| Value | Purpose |
|-------|---------|
| `normal` | Standard response text |
| `followup` | Short follow-up questions |
| `red` | RED/high-risk escalation acknowledgement |
| `unclear` | Unclear or fallback transcript response |
| `safe_fallback` | Sanitized replacement response |
| `greeting` | Initial call greeting; calm and slightly slow |

## TwilioGreetingSessionState

In-memory state held for one active Twilio WebSocket session.

| Field | Type | Validation / Notes |
|-------|------|--------------------|
| `session_id` | string | Existing `twilio_{call_id}` value |
| `call_id` | string | Existing Twilio call identifier |
| `stream_sid` | string or null | Required before sending outbound greeting media |
| `initial_greeting_attempted` | boolean | Starts `false`; set `true` before or when greeting send is attempted to prevent replay |

## GreetingPlaybackAttempt

Operational log/debug concept for one greeting attempt.

| Field | Type | Validation / Notes |
|-------|------|--------------------|
| `purpose` | string | `greeting` |
| `profile` | string | `greeting` unless config overrides to another valid profile |
| `mark_name` | string | `narayana_initial_greeting` |
| `chunk_count` | integer | Number of outbound Twilio media chunks sent; zero on failure |
| `estimated_duration_ms` | integer | Estimate based on encoded audio bytes |
| `warnings` | string list | Sanitization or synthesis warnings, no secrets or audio payloads |
| `outcome` | string | `started`, `completed`, `failed`, or `skipped` |

## Validation Rules

- Greeting must be attempted at most once per Twilio call.
- Greeting text must pass spoken-text sanitization before synthesis.
- Greeting text must not exceed the configured TTS maximum after sanitization.
- Missing stream identifier skips/fails greeting without closing the call.
- TTS failures must not mutate case state or prevent later caller audio processing.

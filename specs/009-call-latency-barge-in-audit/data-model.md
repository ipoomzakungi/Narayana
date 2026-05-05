# Data Model: Call Latency, Barge-In, and Audit Debugging

## TurnTimingConfiguration

Runtime configuration read from environment through `Settings`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `turn_silence_threshold_ms` | int | `>= 100` | Demo target `500`; current safe default may remain higher if chosen during implementation. |
| `turn_pre_speech_padding_ms` | int | `>= 0` | Demo target `200`. |
| `vad_energy_threshold` | float | `0.0 < value < 1.0` | Demo target `0.015`. |
| `min_speech_ms` | int | `>= 0` | Demo target `300`; speech shorter than this is ignored as noise. |

## AssistantPlaybackState

Per Twilio WebSocket/call state that determines whether no-reply timers are allowed and whether barge-in should send `clear`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `session_id` | string | non-empty | Existing `twilio_{call_id}` format. |
| `call_id` | string | non-empty | Twilio CallSid. |
| `stream_sid` | string? | optional until start event | Required for media, mark, and clear events. |
| `assistant_speaking` | bool | default false | True while outbound audio is active or assumed buffered. |
| `active_mark_name` | string? | optional | Last mark sent for current TTS response. |
| `active_response_id` | string? | optional | Internal id for greeting/follow-up/no-reply/closing response. |
| `active_purpose` | string? | optional | `greeting`, `tts`, `call.no_reply_prompt`, `call.no_reply_close`, etc. |
| `playback_started_at` | datetime? | optional | Set when sending media begins. |
| `playback_completed_at` | datetime? | optional | Set when Twilio mark returns or fallback completion occurs. |
| `interrupted` | bool | default false | Set after barge-in for current response. |
| `clear_sent_at` | datetime? | optional | Set when clear event is sent. |

### State Transitions

```text
idle -> speaking: outbound TTS media starts
speaking -> completed: matching Twilio mark received
speaking -> interrupted: caller speech detected and clear sent
interrupted -> idle: sender stops remaining chunks and playback state resets
completed -> idle: no-reply timer may use playback completion as reference
```

## BargeInEvent

Audit/log record created when caller speech is detected during assistant playback.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `event_type` | string | `barge_in.detected` or `barge_in.clear_sent` | Required structured log names. |
| `session_id` | string | non-empty | Links to audit session. |
| `call_id` | string? | optional | Twilio CallSid. |
| `stream_sid` | string? | optional | Present when clear can be sent. |
| `active_mark_name` | string? | optional | Mark interrupted by caller. |
| `audio_sequence` | int? | optional | Inbound media sequence that detected speech. |
| `clear_sent` | bool | required | False when stream id unavailable or socket send fails. |
| `remaining_chunks_stopped` | bool | required | Indicates whether sender stopped unsent audio. |
| `created_at` | datetime | required | UTC timestamp. |

## TTSMarkEvent

Audit/log record for outbound Twilio mark tracking.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `mark_name` | string | non-empty | Existing mark names are retained. |
| `purpose` | string | non-empty | Greeting, follow-up, no-reply, closing, etc. |
| `status` | string | `sent`, `received`, `fallback_completed`, `interrupted` | Drives no-reply timer behavior. |
| `session_id` | string | non-empty | Links to audit session. |
| `call_id` | string? | optional | Twilio CallSid. |
| `stream_sid` | string? | optional | Twilio stream id. |
| `sent_at` | datetime? | optional | Set when mark is sent. |
| `received_at` | datetime? | optional | Set when Twilio returns mark. |
| `estimated_duration_ms` | int? | optional | Useful when mark is missing. |
| `warnings` | string[] | default empty | Missing mark/fallback warnings. |

## CallAuditTimelineEvent

Display-ready item for `/call-audit`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `event_id` | string | non-empty | May reuse debug event id or generated id. |
| `type` | string | non-empty | Examples: `caller.turn.transcribed`, `assistant.response`, `tts.started`, `tts.completed`, `barge_in.detected`. |
| `speaker` | string? | `caller`, `assistant`, `system` | Optional for non-conversation events. |
| `text` | string? | optional | Transcript or assistant response text when logging is enabled. |
| `tts_profile` | string? | optional | TTS profile used for assistant response. |
| `tts_status` | string? | optional | Started/completed/interrupted/failed. |
| `triage_level` | string? | optional | RED/YELLOW/GREEN when available. |
| `case_group` | string? | optional | Operational group when available. |
| `recommended_team` | string? | optional | Recommended team when available. |
| `guardrail_warnings` | string[] | default empty | Scope/safety warnings. |
| `metadata` | object | safe values only | Must not include secrets or audio payloads. |
| `created_at` | datetime | required | UTC timestamp. |

## CallAuditSession

Session payload returned by intake audit endpoints and rendered by `/call-audit`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `session_id` | string | non-empty | Primary lookup id. |
| `call_id` | string? | optional | Twilio CallSid lookup id. |
| `source_input_mode` | string | non-empty | `twilio_call`, `local_mic`, or manual. |
| `conversation_turns` | ConversationTurn[] | existing model | Caller/assistant/system turns. |
| `timeline_events` | CallAuditTimelineEvent[] | ordered by created_at | Includes TTS and lifecycle events. |
| `case_group` | string? | optional | Current or final group. |
| `recommended_team` | string | optional | Current or final team. |
| `triage_level` | string? | optional | Current or final triage. |
| `guardrail_warnings` | string[] | default empty | Existing intake warnings plus lifecycle warnings. |
| `no_reply_prompt_count` | int | `>= 0` | Existing lifecycle count. |
| `off_topic_count` | int | `>= 0` | Existing scope count. |
| `call_end_reason` | string | optional | `no_reply`, `off_topic`, disconnect, etc. |
| `final_case_id` | string? | optional | Set after case creation. |
| `created_at` | datetime | required | Existing session creation time. |
| `updated_at` | datetime | required | Updated after timeline changes. |

## IntakeSessionListResponse

Wrapper for recent audit sessions.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `generated_at` | datetime | required | UTC response time. |
| `count` | int | `>= 0` | Number of sessions returned. |
| `limit` | int | `1..CALL_AUDIT_MAX_SESSIONS` | Applied limit. |
| `sessions` | CallAuditSession[] | newest first | Summary payloads may omit long transcript text when disabled. |

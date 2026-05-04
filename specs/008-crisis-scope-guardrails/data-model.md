# Data Model: Crisis Scope Guardrails

## AssistantRuntimeConfig

Runtime configuration for assistant identity, prompt scope, and call lifecycle thresholds.

| Field | Type | Default / Rules |
|-------|------|-----------------|
| `assistant_display_name` | string | `ระบบช่วยรับแจ้งเหตุ` |
| `assistant_system_prompt_version` | string | `v1` |
| `assistant_scope` | string | `crisis_intake_only` |
| `assistant_allowed_topics` | string list | emergency, medical, flood, fire, accident, public safety, tourist support, mental health crisis, utility infrastructure, shelter supplies |
| `assistant_decline_off_topic` | boolean | `true` |
| `call_no_reply_seconds` | integer | `10`, positive |
| `call_no_reply_prompt_seconds` | integer | `15`, positive |
| `call_max_no_reply_prompts` | integer | `2`, non-negative |
| `call_max_off_topic_redirects` | integer | `2`, non-negative |
| `call_end_on_repeated_off_topic` | boolean | `true` |
| `call_end_on_no_reply` | boolean | `true` |
| `twilio_force_hangup_enabled` | boolean | `false` |

## IntakeSessionState Extensions

Additive fields on the existing per-session intake state.

| Field | Type | Rules |
|-------|------|-------|
| `off_topic_count` | integer | Incremented for off-topic caller turns without emergency signal |
| `redirect_count` | integer | Incremented when the assistant sends an off-topic redirect/final warning |
| `last_off_topic_at` | datetime or null | Set on latest off-topic turn |
| `last_assistant_redirect` | string | Latest off-topic/no-reply redirect text |
| `no_reply_prompt_count` | integer | Incremented for no-reply prompts |
| `last_caller_speech_at` | datetime or null | Updated on every accepted caller transcript |
| `greeting_sent_at` | datetime or null | Set when initial greeting is sent or considered sent |
| `call_end_recommended` | boolean | Set when repeated off-topic or no-reply thresholds are exceeded |
| `call_end_reason` | string | `repeated_off_topic`, `no_reply`, or empty |

## OffTopicResult

Deterministic scope-classification result.

| Field | Type | Rules |
|-------|------|-------|
| `is_off_topic` | boolean | True only for clearly unrelated content |
| `is_emergency_signal` | boolean | True for crisis or high-risk terms; overrides off-topic |
| `category` | string | `off_topic`, `emergency`, `unclear`, or `in_scope` |
| `confidence` | number | Deterministic confidence score |
| `reason` | string | Human-readable reason for debug/audit |
| `matched_terms` | string list | Matched off-topic or emergency patterns |
| `response_text` | string | Redirect/final warning when applicable |
| `call_end_recommended` | boolean | True after threshold |
| `guardrail_warnings` | string list | Scope-related audit warnings |

## CallLifecycleState

Per-call runtime state used by the Twilio WebSocket loop.

| Field | Type | Rules |
|-------|------|-------|
| `session_id` | string | Existing Twilio session id |
| `call_id` | string | Twilio call id |
| `greeting_sent_at` | datetime or null | Set after start/greeting |
| `last_caller_speech_at` | datetime or null | Set when a caller media turn produces transcript |
| `no_reply_prompt_count` | integer | Incremented by no-reply prompts |
| `call_end_recommended` | boolean | True after final no-reply |
| `call_end_reason` | string | `no_reply` when silence close is recommended |

## State Transitions

### Off-Topic Flow

1. `off_topic_count=0`
2. First off-topic: increment count, send redirect, keep call active.
3. Second off-topic: increment count, send final warning, keep call active.
4. Third off-topic: set `call_end_recommended=true`, final close response.
5. Any emergency signal: reset off-topic count/redirect state and continue normal intake.

### No-Reply Flow

1. Greeting sent and `last_caller_speech_at` is empty.
2. First timeout: send no-reply prompt, increment prompt count.
3. Subsequent timeout before max: repeat/continue prompt behavior.
4. Max exceeded: send final close prompt, set `call_end_recommended=true`, close WebSocket safely.

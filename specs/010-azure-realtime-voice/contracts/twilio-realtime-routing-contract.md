# Contract: Twilio Realtime Routing

This contract describes how the existing Twilio media WebSocket uses the experimental realtime provider when explicitly enabled.

## Existing Routes Preserved

```text
POST /api/telephony/twilio/incoming-call
GET  /ws/telephony/twilio/{call_id}
```

No route path changes are allowed for this feature.

## Routing Decision

On Twilio `start` event:

1. Capture `streamSid` and call metadata as today.
2. Evaluate realtime settings.
3. If realtime is disabled or not configured, log `realtime.fallback` and continue current path.
4. If realtime is configured, connect provider with crisis-intake instructions.
5. If connect succeeds, mark the call session as realtime active.
6. If connect fails, log `realtime.error` then continue current path.

## Media Event Handling

When realtime is inactive:

- Preserve current behavior: normalize Twilio media to `AudioFrame`, route through `AudioSessionProcessor`, then optionally send Azure Speech TTS speak-back.

When realtime is active:

- Normalize Twilio media to `AudioFrame`.
- Send the frame to the active realtime provider.
- Log `realtime.audio.input.sent` with safe metadata.
- Concurrently receive provider events.
- For provider audio output, send Twilio media event:

```json
{
  "event": "media",
  "streamSid": "<twilio-streamSid>",
  "media": {
    "payload": "<base64 mulaw audio>"
  }
}
```

- For provider response boundaries, send existing debug/audit payloads where useful:

```json
{
  "type": "realtime.response.started",
  "session_id": "twilio_CA123",
  "call_id": "CA123",
  "provider": "azure_openai_realtime",
  "latency_ms": 180
}
```

```json
{
  "type": "realtime.response.completed",
  "session_id": "twilio_CA123",
  "call_id": "CA123",
  "provider": "azure_openai_realtime",
  "latency_ms": 900
}
```

## Fallback Behavior

Fallback must occur when:

- Provider is disabled.
- Provider is selected but not configured.
- Provider connection fails.
- Provider send or receive fails.
- Provider closes unexpectedly.
- Provider output cannot be normalized into safe Twilio media.

Fallback payload:

```json
{
  "type": "realtime.fallback",
  "session_id": "twilio_CA123",
  "call_id": "CA123",
  "provider": "azure_voice_live",
  "reason": "connect_failed",
  "warnings": ["Realtime provider connection failed; current pipeline remains active."]
}
```

## Barge-In and Clear Behavior

- Existing Twilio `clear` support remains available.
- If realtime output is streaming and caller media arrives, send Twilio `clear` when the route determines assistant audio should be interrupted.
- Log `barge_in.detected` and `barge_in.clear_sent` using existing log names plus realtime provider metadata.

## Health/Debug Output

Existing health/debug output should add:

```json
{
  "enable_realtime_voice": false,
  "realtime_provider": "none",
  "azure_realtime_configured": false,
  "azure_voice_live_realtime_configured": false,
  "realtime_warnings": []
}
```

## Automated Test Contract

- Tests must not open real Azure or Twilio network connections.
- Provider selection tests use settings objects only.
- Realtime WebSocket tests use mocked provider events.
- Existing simulated Twilio tests must pass with realtime disabled.

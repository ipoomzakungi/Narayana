# Realtime Dashboard Contract

## Local Development Transport

Use one of these local transports:

- WebSocket: `ws://localhost:8000/ws/cases`
- SSE fallback: `GET http://localhost:8000/api/events`

The frontend should prefer WebSocket locally and fall back to SSE or short polling only if WebSocket is unavailable.

## Cloud Transport

When `SIGNALR_CONNECTION_STRING` is configured, `RealtimeNotifier` may publish equivalent events through Azure SignalR Service. Event payloads must stay compatible with the local contract so the frontend does not depend on a specific transport.

## Event Envelope

All dashboard events use this envelope:

```json
{
  "type": "case.created",
  "event_id": "evt_123",
  "timestamp": "2026-05-02T10:00:05Z",
  "payload": {}
}
```

## Events

### `case.created`

Sent when a new crisis case is created.

```json
{
  "type": "case.created",
  "event_id": "evt_case_created_001",
  "timestamp": "2026-05-02T10:00:05Z",
  "payload": {
    "case_id": "case_001",
    "triage_level": "RED",
    "status": "new",
    "human_review_required": true,
    "ai_summary": "Flood in Hat Yai with an elderly person trapped on the second floor and breathing difficulty.",
    "created_at": "2026-05-02T10:00:05Z"
  }
}
```

### `case.updated`

Sent when status, current priority, summary, or human-review data changes.

```json
{
  "type": "case.updated",
  "event_id": "evt_case_updated_001",
  "timestamp": "2026-05-02T10:01:00Z",
  "payload": {
    "case_id": "case_001",
    "triage_level": "RED",
    "status": "contacted",
    "updated_at": "2026-05-02T10:01:00Z",
    "changed_fields": ["status"]
  }
}
```

### `debug.event`

Sent to the Voice Debug Console when a voice timing event is recorded.

```json
{
  "type": "debug.event",
  "event_id": "evt_debug_001",
  "timestamp": "2026-05-02T10:00:04Z",
  "payload": {
    "session_id": "voice_123",
    "case_id": "case_001",
    "event_type": "turn_ended",
    "state": "thinking",
    "duration_ms": 3200
  }
}
```

### `upload.simulated`

Sent when a demo upload or SMS link simulation is generated.

```json
{
  "type": "upload.simulated",
  "event_id": "evt_upload_001",
  "timestamp": "2026-05-02T10:02:00Z",
  "payload": {
    "case_id": "case_001",
    "action_id": "action_001",
    "is_simulated": true,
    "expires_at": "2026-05-02T10:17:00Z"
  }
}
```

## Ordering and Reconnect Rules

- Events are timestamped by the backend.
- The dashboard should update optimistically only after the backend returns success for operator changes.
- On reconnect, the dashboard must call `GET /api/cases` and replace stale local state.
- Duplicate `event_id` values must be ignored by the frontend.
- If realtime transport fails, the UI should show a degraded connection indicator and poll `GET /api/cases` every 10 seconds until realtime reconnects.

# Contract: ACS Skeleton

ACS support is a safe placeholder for this spike. It must not be required for startup or automated tests.

## Event Endpoint

`POST /api/telephony/acs/events`

Behavior when ACS is not configured:

Status: `501 Not Implemented` or `503 Service Unavailable`

```json
{
  "detail": "ACS telephony ingress is not implemented for V1 spike or is not configured."
}
```

Rules:

- The endpoint must not crash when `ACS_CONNECTION_STRING`, `ACS_PHONE_NUMBER`, or `ACS_CALLBACK_PUBLIC_BASE_URL` are missing.
- The endpoint must not create cases.

## Media WebSocket

`/ws/telephony/acs/{call_id}`

Behavior:

- Accept only if explicitly configured and implemented later.
- For this spike, close safely with a clear not-implemented reason.

Rules:

- No production ACS media behavior is required.
- The skeleton exists to document the future adapter point.

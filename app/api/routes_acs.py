from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket

router = APIRouter(tags=["telephony-acs"])


@router.post("/api/telephony/acs/events")
async def acs_events() -> dict:
    raise HTTPException(
        status_code=501,
        detail="ACS telephony ingress is not implemented for V1 spike or is not configured.",
    )


@router.websocket("/ws/telephony/acs/{call_id}")
async def acs_media_ws(websocket: WebSocket, call_id: str) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "error",
            "detail": "ACS telephony ingress is not implemented for V1 spike or is not configured.",
            "call_id": call_id,
        }
    )
    await websocket.close(code=1008)

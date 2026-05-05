from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.models.intake import IntakeRequest, IntakeResponse, IntakeSessionListResponse, IntakeSessionState
from app.services.intake_orchestrator import IntakeOrchestrator
from app.services.intake_session_store import get_intake_session_store

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.post("/from-transcript", response_model=IntakeResponse)
async def intake_from_transcript(
    request: IntakeRequest,
    settings: Settings = Depends(get_settings),
) -> IntakeResponse:
    orchestrator = IntakeOrchestrator(settings)
    return await orchestrator.process_transcript(request)


@router.get("/sessions", response_model=IntakeSessionListResponse)
async def list_intake_sessions(
    limit: int = Query(default=50, ge=1),
    settings: Settings = Depends(get_settings),
) -> IntakeSessionListResponse:
    applied_limit = min(limit, settings.call_audit_max_sessions)
    store = get_intake_session_store(settings.assistant_max_followups)
    sessions = store.list_recent(applied_limit)
    return IntakeSessionListResponse(count=len(sessions), limit=applied_limit, sessions=sessions)


@router.get("/calls/{call_id}", response_model=IntakeSessionState)
async def get_intake_session_by_call_id(
    call_id: str,
    settings: Settings = Depends(get_settings),
) -> IntakeSessionState:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.get_by_call_id(call_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Intake call session not found.")
    return state


@router.get("/sessions/{session_id}", response_model=IntakeSessionState)
async def get_intake_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> IntakeSessionState:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.snapshot(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Intake session not found.")
    return state

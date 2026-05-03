from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.intake import IntakeRequest, IntakeResponse
from app.services.intake_orchestrator import IntakeOrchestrator

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.post("/from-transcript", response_model=IntakeResponse)
async def intake_from_transcript(
    request: IntakeRequest,
    settings: Settings = Depends(get_settings),
) -> IntakeResponse:
    orchestrator = IntakeOrchestrator(settings)
    return await orchestrator.process_transcript(request)

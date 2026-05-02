from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.models.case import CaseRepositoryRecord, CreateCaseRequest
from app.services.case_repository import get_case_repository
from app.services.safety_rules import apply_safety_rules

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseRepositoryRecord)
async def create_case(
    request: CreateCaseRequest,
    settings: Settings = Depends(get_settings),
) -> CaseRepositoryRecord:
    repository = get_case_repository(settings)
    safe_case = apply_safety_rules(request.case, settings.low_confidence_threshold)
    return await repository.create(
        case=safe_case,
        session_id=request.session_id,
        source_provider=request.source_provider,
    )


@router.get("/{case_id}", response_model=CaseRepositoryRecord)
async def get_case(case_id: str, settings: Settings = Depends(get_settings)) -> CaseRepositoryRecord:
    repository = get_case_repository(settings)
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return record

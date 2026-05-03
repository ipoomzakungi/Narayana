from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.config import Settings, get_settings
from app.models.case import CaseRepositoryRecord, CaseSnapshotResponse, CreateCaseRequest
from app.services.case_repository import get_case_repository
from app.services.case_snapshot_cache import CaseSnapshotCache
from app.services.safety_rules import apply_safety_rules

router = APIRouter(prefix="/api/cases", tags=["cases"])
_case_snapshot_cache = CaseSnapshotCache(ttl_seconds=60)


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
        case_group=request.case_group,
        recommended_team=request.recommended_team,
        conversation_summary=request.conversation_summary,
        intake_session_id=request.intake_session_id,
        intake_audit=request.intake_audit,
    )


@router.get("/recent-cached", response_model=CaseSnapshotResponse)
async def list_recent_cases_cached(
    response: Response,
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> CaseSnapshotResponse:
    repository = get_case_repository(settings)
    snapshot = await _case_snapshot_cache.get_recent_cases(repository, limit)
    response.headers["Cache-Control"] = f"public, max-age={snapshot.ttl_seconds}"
    response.headers["X-Cache-Source"] = snapshot.source
    return snapshot


@router.get("/recent", response_model=list[CaseRepositoryRecord])
async def list_recent_cases(
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> list[CaseRepositoryRecord]:
    repository = get_case_repository(settings)
    return await repository.list_recent(limit)


@router.get("/{case_id}", response_model=CaseRepositoryRecord)
async def get_case(case_id: str, settings: Settings = Depends(get_settings)) -> CaseRepositoryRecord:
    repository = get_case_repository(settings)
    record = await repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return record

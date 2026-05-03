from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.api import routes_cases
from app.main import create_app
from app.models.case import CrisisCase
from app.models.triage import IncidentType, TriageLevel


def case_payload() -> dict:
    case = CrisisCase(
        language="th",
        incident_type=IncidentType.FLOOD,
        triage_level=TriageLevel.RED,
        confidence=0.93,
        location_text="หาดใหญ่",
        injuries="elderly person breathing difficulty",
        immediate_needs=["rescue", "medical"],
        ai_summary="Flood with trapped elderly person.",
        triage_reason="Trapped person and breathing difficulty.",
        human_review_required=True,
    )
    return {"case": case.model_dump(mode="json"), "session_id": "session_1", "source_provider": "mock"}


@pytest.mark.asyncio
async def test_create_case_with_local_repository(tmp_path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(case_store_path=str(tmp_path / "cases.json"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/cases", json=case_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["triage_level"] == "RED"
    assert payload["case"]["status"] == "pending"
    assert payload["source_provider"] == "mock"
    assert payload["session_id"] == "session_1"


@pytest.mark.asyncio
async def test_create_case_validation_failure(tmp_path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(case_store_path=str(tmp_path / "cases.json"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/cases", json={"case": {"triage_level": "BLUE"}})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recent_cached_cases_returns_snapshot_with_cache_headers(tmp_path) -> None:
    routes_cases._case_snapshot_cache.clear()
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(case_store_path=str(tmp_path / "cases.json"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post("/api/cases", json=case_payload())
        response = await client.get("/api/cases/recent-cached?limit=50")
        cached_response = await client.get("/api/cases/recent-cached?limit=50")

    assert create_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "repository"
    assert payload["ttl_seconds"] == 60
    assert payload["count"] == 1
    assert payload["cases"][0]["case"]["triage_level"] == "RED"
    assert response.headers["Cache-Control"] == "public, max-age=60"
    assert response.headers["X-Cache-Source"] == "repository"
    assert cached_response.json()["source"] == "cache"
    assert cached_response.headers["X-Cache-Source"] == "cache"

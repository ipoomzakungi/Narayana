from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.mock_voice_provider import THAI_SAMPLE


@pytest.mark.asyncio
async def test_thai_transcript_to_red_case(tmp_path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        use_mock_services=True,
        case_store_path=str(tmp_path / "cases.json"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/triage/from-transcript",
            json={"transcript": THAI_SAMPLE, "language_hint": "th"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "th"
    assert payload["incident_type"] == "flood"
    assert payload["triage_level"] == "RED"
    assert payload["status"] == "pending"
    assert payload["human_review_required"] is True
    assert payload["location_text"] in {"Hat Yai", "หาดใหญ่"}
    assert "breathing" in payload["injuries"].lower()
    assert "trapped" in payload["triage_reason"].lower()

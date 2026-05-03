from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.intake_session_store import get_intake_session_store


@pytest.fixture()
def app_with_tmp_store(tmp_path):
    get_intake_session_store().clear()
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        use_mock_services=True,
        case_store_path=str(tmp_path / "cases.json"),
        audio_store_path=str(tmp_path / "audio"),
    )
    yield app
    app.dependency_overrides.clear()
    get_intake_session_store().clear()


@pytest.mark.asyncio
async def test_intake_from_transcript_asks_followup_for_incomplete_flood(app_with_tmp_store) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_tmp_store), base_url="http://test") as client:
        response = await client.post(
            "/api/intake/from-transcript",
            json={
                "session_id": "debug-session",
                "transcript": "น้ำท่วมอยู่ที่หาดใหญ่",
                "language_hint": "th",
                "source_input_mode": "manual",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "ask_followup"
    assert payload["created_case"] is None
    assert payload["partial_state"]["collected_fields"]["location_text"] == "หาดใหญ่"
    assert "injuries" in payload["missing_fields"]
    assert payload["response_text"]


@pytest.mark.asyncio
async def test_intake_from_transcript_creates_red_case_for_thai_sample(app_with_tmp_store) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_tmp_store), base_url="http://test") as client:
        response = await client.post(
            "/api/intake/from-transcript",
            json={
                "session_id": "red-session",
                "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
                "language_hint": "th",
                "source_input_mode": "manual",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "escalate_human_review"
    assert payload["triage_level"] == "RED"
    assert payload["human_review_required"] is True
    assert payload["case_group"] == "rescue"
    assert payload["recommended_team"] == "rescue"
    assert payload["created_case"]["case"]["triage_level"] == "RED"
    assert payload["created_case"]["case_group"] == "rescue"


@pytest.mark.asyncio
async def test_intake_grouping_samples(app_with_tmp_store) -> None:
    samples = [
        ("fire", "ไฟไหม้อาคารที่กรุงเทพ มีควันเยอะ", "fire"),
        ("tourist", "นักท่องเที่ยวหลงทางที่กรุงเทพ", "tourist_support"),
        ("utility", "ถนนขาดที่หาดใหญ่", "utility_infrastructure"),
        ("shelter", "ต้องการอาหาร น้ำดื่ม และที่พักที่หาดใหญ่", "shelter_supplies"),
        ("mental", "อยู่ที่กรุงเทพ อยากทำร้ายตัวเอง", "mental_health_support"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app_with_tmp_store), base_url="http://test") as client:
        for session_id, transcript, expected_group in samples:
            response = await client.post(
                "/api/intake/from-transcript",
                json={
                    "session_id": f"group-{session_id}",
                    "transcript": transcript,
                    "language_hint": "th",
                    "source_input_mode": "manual",
                },
            )
            payload = response.json()

            assert response.status_code == 200
            assert payload["case_group"] == expected_group


@pytest.mark.asyncio
async def test_existing_triage_route_still_works(app_with_tmp_store) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_tmp_store), base_url="http://test") as client:
        response = await client.post(
            "/api/triage/from-transcript",
            json={"transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง", "language_hint": "th"},
        )

    assert response.status_code == 200
    assert response.json()["triage_level"] == "RED"

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.mock_voice_provider import THAI_SAMPLE


@pytest.mark.asyncio
async def test_gateway_demo_smoke(tmp_path) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        use_mock_services=True,
        case_store_path=str(tmp_path / "cases.json"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/api/health/azure")
        tts = await client.post("/api/tts/test", json={"text": "ตอนนี้อยู่จุดไหนคะ?"})
        triage = await client.post("/api/triage/from-transcript", json={"transcript": THAI_SAMPLE})
        case = await client.post(
            "/api/cases",
            json={"case": triage.json(), "session_id": "session_smoke", "source_provider": "mock"},
        )

    assert health.status_code == 200
    assert health.json()["selected_provider"] == "mock"
    assert health.json()["twilio_tts_response_enabled"] is False
    assert health.json()["azure_speech_tts_configured"] is False
    assert health.json()["azure_speech_voice"] == "th-TH-PremwadeeNeural"
    assert tts.status_code == 200
    assert tts.json()["configured"] is False
    assert "payloads" not in tts.json()
    assert triage.status_code == 200
    assert triage.json()["triage_level"] == "RED"
    assert triage.json()["human_review_required"] is True
    assert case.status_code == 200
    assert case.json()["case"]["status"] == "pending"

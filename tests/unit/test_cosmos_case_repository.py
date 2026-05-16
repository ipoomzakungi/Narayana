from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.models.case import CrisisCase
from app.models.triage import IncidentType, ProviderMode, TriageLevel
from app.services.cosmos_case_repository import CosmosCaseRepository


def make_case() -> CrisisCase:
    created = datetime(2026, 5, 2, tzinfo=timezone.utc)
    return CrisisCase(
        case_id="case_cosmos_realtime",
        language="th",
        incident_type=IncidentType.FIRE,
        triage_level=TriageLevel.RED,
        confidence=0.91,
        location_text="หาดใหญ่",
        injuries="smoke inhalation",
        immediate_needs=["fire", "medical"],
        ai_summary="Fire with smoke inhalation.",
        triage_reason="Active fire requires review.",
        human_review_required=True,
        created_at=created,
        updated_at=created,
        realtime_provider="azure_openai_realtime",
        realtime_model_or_deployment="gpt-realtime",
        realtime_transcript_turns=[{"speaker": "caller", "text": "ไฟไหม้ที่หาดใหญ่"}],
        caller_tone="urgent",
        recommended_operator_action="immediate_human_review",
        fallback_reason="provider_error",
    )


class FakeContainer:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def upsert_item(self, payload: dict) -> None:
        self.payloads.append(payload)


@pytest.mark.asyncio
async def test_cosmos_case_repository_persists_realtime_metadata_in_payload(monkeypatch) -> None:
    container = FakeContainer()
    repository = CosmosCaseRepository(
        Settings(
            cosmos_db_endpoint="https://cosmos.example",
            cosmos_db_key="key",
            cosmos_db_database="db",
            cosmos_db_container="cases",
        )
    )
    monkeypatch.setattr(repository, "_container", lambda: container)

    record = await repository.create(
        make_case(),
        session_id="twilio_CA123",
        source_provider=ProviderMode.AZURE_OPENAI_REALTIME,
    )

    assert record.realtime_provider == "azure_openai_realtime"
    payload = container.payloads[0]
    assert payload["id"] == "case_cosmos_realtime"
    assert payload["case"]["realtime_provider"] == "azure_openai_realtime"
    assert payload["case"]["realtime_model_or_deployment"] == "gpt-realtime"
    assert payload["case"]["realtime_transcript_turns"] == [{"speaker": "caller", "text": "ไฟไหม้ที่หาดใหญ่"}]
    assert payload["realtime_provider"] == "azure_openai_realtime"
    assert payload["recommended_operator_action"] == "immediate_human_review"
    assert payload["fallback_reason"] == "provider_error"

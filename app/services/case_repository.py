from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.models.case import CaseRepositoryRecord, CrisisCase
from app.models.triage import ProviderMode


class CaseRepository(Protocol):
    async def create(
        self,
        case: CrisisCase,
        session_id: str | None,
        source_provider: ProviderMode,
        debug_event_count: int = 0,
        case_group: str | None = None,
        recommended_team: str | None = None,
        conversation_summary: str | None = None,
        intake_session_id: str | None = None,
        intake_audit: list[dict] | None = None,
    ) -> CaseRepositoryRecord:
        ...

    async def get(self, case_id: str) -> CaseRepositoryRecord | None:
        ...

    async def list_recent(self, limit: int = 50) -> list[CaseRepositoryRecord]:
        ...


def get_case_repository(settings: Settings) -> CaseRepository:
    if settings.cosmos_configured:
        from app.services.cosmos_case_repository import CosmosCaseRepository

        return CosmosCaseRepository(settings)

    from app.services.local_case_repository import LocalCaseRepository

    return LocalCaseRepository(settings.case_store_path)

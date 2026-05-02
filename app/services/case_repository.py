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
    ) -> CaseRepositoryRecord:
        ...

    async def get(self, case_id: str) -> CaseRepositoryRecord | None:
        ...


def get_case_repository(settings: Settings) -> CaseRepository:
    if settings.cosmos_configured:
        from app.services.cosmos_case_repository import CosmosCaseRepository

        return CosmosCaseRepository(settings)

    from app.services.local_case_repository import LocalCaseRepository

    return LocalCaseRepository(settings.case_store_path)

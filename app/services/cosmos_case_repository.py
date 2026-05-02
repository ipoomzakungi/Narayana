from __future__ import annotations

from app.core.config import Settings
from app.models.case import CaseRepositoryRecord, CrisisCase
from app.models.triage import ProviderMode


class CosmosCaseRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _container(self):
        from azure.cosmos import CosmosClient

        client = CosmosClient(self.settings.cosmos_db_endpoint, credential=self.settings.cosmos_db_key)
        database = client.get_database_client(self.settings.cosmos_db_database)
        return database.get_container_client(self.settings.cosmos_db_container)

    async def create(
        self,
        case: CrisisCase,
        session_id: str | None,
        source_provider: ProviderMode,
        debug_event_count: int = 0,
    ) -> CaseRepositoryRecord:
        record = CaseRepositoryRecord(
            case=case,
            session_id=session_id,
            source_provider=source_provider,
            debug_event_count=debug_event_count,
        )
        payload = record.model_dump(mode="json")
        payload["id"] = case.case_id
        self._container().upsert_item(payload)
        return record

    async def get(self, case_id: str) -> CaseRepositoryRecord | None:
        try:
            raw = self._container().read_item(case_id, partition_key=case_id)
        except Exception:
            return None
        raw.pop("id", None)
        return CaseRepositoryRecord.model_validate(raw)

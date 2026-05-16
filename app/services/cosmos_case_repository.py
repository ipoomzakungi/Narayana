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
        case_group: str | None = None,
        recommended_team: str | None = None,
        conversation_summary: str | None = None,
        intake_session_id: str | None = None,
        intake_audit: list[dict] | None = None,
    ) -> CaseRepositoryRecord:
        record = CaseRepositoryRecord(
            case=case,
            session_id=session_id,
            source_provider=source_provider,
            debug_event_count=debug_event_count,
            case_group=case_group or case.case_group,
            recommended_team=recommended_team or case.recommended_team,
            conversation_summary=conversation_summary or case.conversation_summary,
            intake_session_id=intake_session_id or case.intake_session_id,
            intake_audit=intake_audit or case.intake_audit,
            realtime_provider=case.realtime_provider,
            realtime_model_or_deployment=case.realtime_model_or_deployment,
            realtime_transcript_turns=case.realtime_transcript_turns,
            full_transcript=case.full_transcript,
            final_structured_fields=case.final_structured_fields,
            caller_tone=case.caller_tone,
            missing_fields=case.missing_fields,
            recommended_operator_action=case.recommended_operator_action,
            call_started_at=case.call_started_at,
            call_ended_at=case.call_ended_at,
            fallback_reason=case.fallback_reason,
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

    async def list_recent(self, limit: int = 50) -> list[CaseRepositoryRecord]:
        if limit <= 0:
            return []

        container = self._container()
        parameters = [{"name": "@limit", "value": limit}]
        queries = [
            "SELECT * FROM c ORDER BY c.case.created_at DESC OFFSET 0 LIMIT @limit",
            "SELECT * FROM c OFFSET 0 LIMIT @limit",
        ]
        for query in queries:
            try:
                items = list(
                    container.query_items(
                        query=query,
                        parameters=parameters,
                        enable_cross_partition_query=True,
                    )
                )
                records = []
                for raw in items:
                    raw.pop("id", None)
                    records.append(CaseRepositoryRecord.model_validate(raw))
                records.sort(key=lambda record: record.case.created_at or record.stored_at, reverse=True)
                return records[:limit]
            except Exception:
                continue
        return []

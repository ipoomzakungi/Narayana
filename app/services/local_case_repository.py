from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.case import CaseRepositoryRecord, CrisisCase
from app.models.triage import ProviderMode


class LocalCaseRepository:
    def __init__(self, path: str = ".data/cases.json") -> None:
        self.path = Path(path)

    def _read(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        if not self.path.read_text(encoding="utf-8").strip():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

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
        data = self._read()
        data[case.case_id] = record.model_dump(mode="json")
        self._write(data)
        return record

    async def get(self, case_id: str) -> CaseRepositoryRecord | None:
        data = self._read()
        raw = data.get(case_id)
        if not raw:
            return None
        return CaseRepositoryRecord.model_validate(raw)

    async def list_recent(self, limit: int = 50) -> list[CaseRepositoryRecord]:
        if limit <= 0:
            return []
        records: list[CaseRepositoryRecord] = []
        for raw in self._read().values():
            try:
                records.append(CaseRepositoryRecord.model_validate(raw))
            except Exception:
                continue
        records.sort(key=_record_created_at, reverse=True)
        return records[:limit]


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _record_created_at(record: CaseRepositoryRecord) -> datetime:
    return _aware_datetime(record.case.created_at or record.stored_at)

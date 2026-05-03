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
    ) -> CaseRepositoryRecord:
        record = CaseRepositoryRecord(
            case=case,
            session_id=session_id,
            source_provider=source_provider,
            debug_event_count=debug_event_count,
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

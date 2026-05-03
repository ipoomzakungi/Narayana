from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from app.models.case import CaseSnapshotResponse
from app.services.case_repository import CaseRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseSnapshotCache:
    def __init__(self, ttl_seconds: int = 60, now_provider: Callable[[], datetime] = utc_now) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        self.ttl_seconds = ttl_seconds
        self.now_provider = now_provider
        self._snapshots: dict[str, CaseSnapshotResponse] = {}

    async def get_recent_cases(self, repository: CaseRepository, limit: int = 50) -> CaseSnapshotResponse:
        cache_key = f"recent_cases:{limit}"
        now = self._aware_now()
        cached = self._snapshots.get(cache_key)
        if cached is not None and cached.expires_at > now:
            return cached.model_copy(update={"source": "cache"})

        records = await repository.list_recent(limit)
        generated_at = now
        snapshot = CaseSnapshotResponse(
            generated_at=generated_at,
            expires_at=generated_at + timedelta(seconds=self.ttl_seconds),
            ttl_seconds=self.ttl_seconds,
            count=len(records),
            source="repository",
            cases=records,
        )
        self._snapshots[cache_key] = snapshot
        return snapshot

    def clear(self) -> None:
        self._snapshots.clear()

    def _aware_now(self) -> datetime:
        now = self.now_provider()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now

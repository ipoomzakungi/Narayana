from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.models.realtime import RealtimeLatencySample, RealtimeProviderMode
from app.services.call_audit_logger import safe_metadata


@dataclass
class RealtimeLatencyTracker:
    provider: RealtimeProviderMode
    session_id: str
    call_id: str | None = None
    _stage_starts: dict[str, float] = field(default_factory=dict)

    def start(self, stage: str) -> None:
        self._stage_starts[stage] = perf_counter()

    def sample(self, stage: str, *, metadata: dict[str, Any] | None = None) -> RealtimeLatencySample:
        now = perf_counter()
        started = self._stage_starts.pop(stage, now)
        return RealtimeLatencySample(
            stage=stage,
            provider=self.provider,
            session_id=self.session_id,
            call_id=self.call_id,
            latency_ms=max(0, int((now - started) * 1000)),
            metadata=safe_metadata(metadata),
        )

    def instant(self, stage: str, *, metadata: dict[str, Any] | None = None) -> RealtimeLatencySample:
        return RealtimeLatencySample(
            stage=stage,
            provider=self.provider,
            session_id=self.session_id,
            call_id=self.call_id,
            latency_ms=0,
            metadata=safe_metadata(metadata),
        )

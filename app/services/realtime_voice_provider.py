from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol
from urllib.parse import urlencode, urlparse

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.realtime import (
    RealtimeAudioEvent,
    RealtimeAudioEventType,
    RealtimeAudioFormat,
    RealtimeConnectionResult,
    RealtimeProviderMode,
    RealtimeSendResult,
)
from app.services.azure_openai_intake_provider import build_intake_system_prompt
from app.services.call_audit_logger import safe_metadata
from app.services.realtime_latency import RealtimeLatencyTracker

WebSocketFactory = Callable[..., Any | Awaitable[Any]]


class RealtimeVoiceProvider(Protocol):
    mode: RealtimeProviderMode

    async def connect(self, *, session_id: str, call_id: str | None, instructions: str) -> RealtimeConnectionResult:
        ...

    async def send_audio_frame(self, frame: AudioFrame) -> RealtimeSendResult:
        ...

    async def receive_audio_event(self) -> RealtimeAudioEvent | None:
        ...

    async def close(self) -> None:
        ...


@dataclass
class RealtimeProviderSelection:
    enabled: bool
    provider_mode: RealtimeProviderMode
    provider: RealtimeVoiceProvider | None = None
    configured: bool = False
    warnings: list[str] = field(default_factory=list)
    fallback_reason: str | None = None

    @property
    def active_candidate(self) -> bool:
        return self.enabled and self.configured and self.provider is not None

    def debug_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider_mode.value,
            "configured": self.configured,
            "active_candidate": self.active_candidate,
            "fallback_reason": self.fallback_reason,
            "warnings": list(self.warnings),
        }


class BaseRealtimeProvider:
    mode: RealtimeProviderMode = RealtimeProviderMode.NONE

    def __init__(self, settings: Settings, websocket_factory: WebSocketFactory | None = None) -> None:
        self.settings = settings
        self.websocket_factory = websocket_factory
        self.websocket: Any | None = None
        self.session_id: str | None = None
        self.call_id: str | None = None
        self.latency: RealtimeLatencyTracker | None = None

    async def _open_websocket(self, uri: str, headers: dict[str, str]) -> Any:
        factory = self.websocket_factory
        if factory is None:
            import websockets

            factory = websockets.connect
        try:
            result = factory(uri, additional_headers=headers)
        except TypeError:
            result = factory(uri, extra_headers=headers)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _send_json(self, payload: dict[str, Any]) -> None:
        if self.websocket is None:
            raise RuntimeError("Realtime provider is not connected.")
        if hasattr(self.websocket, "send"):
            await self.websocket.send(json.dumps(payload, ensure_ascii=False))
            return
        if hasattr(self.websocket, "send_json"):
            await self.websocket.send_json(payload)
            return
        raise RuntimeError("Realtime websocket object does not support send.")

    async def _recv_json(self) -> dict[str, Any]:
        if self.websocket is None:
            raise RuntimeError("Realtime provider is not connected.")
        if hasattr(self.websocket, "recv"):
            raw = await self.websocket.recv()
        elif hasattr(self.websocket, "receive_json"):
            return await self.websocket.receive_json()
        else:
            raise RuntimeError("Realtime websocket object does not support receive.")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def close(self) -> None:
        if self.websocket is None:
            return
        websocket = self.websocket
        self.websocket = None
        close = getattr(websocket, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    def _tracker(self, session_id: str, call_id: str | None) -> RealtimeLatencyTracker:
        if self.latency is None or self.session_id != session_id or self.call_id != call_id:
            self.latency = RealtimeLatencyTracker(provider=self.mode, session_id=session_id, call_id=call_id)
        return self.latency

    def _event(
        self,
        event_type: RealtimeAudioEventType,
        *,
        audio_base64: str | None = None,
        audio_format: RealtimeAudioFormat = RealtimeAudioFormat.UNKNOWN,
        text: str | None = None,
        latency_ms: int | None = None,
        warnings: list[str] | None = None,
        fallback_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RealtimeAudioEvent:
        return RealtimeAudioEvent(
            event_type=event_type,
            provider=self.mode,
            session_id=self.session_id,
            call_id=self.call_id,
            audio_base64=audio_base64,
            audio_format=audio_format,
            text=text,
            latency_ms=latency_ms,
            warnings=warnings or [],
            fallback_reason=fallback_reason,
            metadata=safe_metadata(metadata),
        )


def build_realtime_instructions(settings: Settings) -> str:
    prompt = build_intake_system_prompt(settings)
    return (
        f"{prompt}\n"
        "Realtime voice mode: respond with short Thai crisis-intake speech only. "
        "Do not claim rescue has been dispatched. Do not diagnose. "
        "If uncertain or provider context is insufficient, ask one concise follow-up question or allow fallback."
    )


def get_realtime_provider(
    settings: Settings,
    websocket_factory: WebSocketFactory | None = None,
) -> RealtimeProviderSelection:
    try:
        provider_mode = RealtimeProviderMode(settings.normalized_realtime_provider)
    except ValueError:
        provider_mode = RealtimeProviderMode.NONE
    warnings = settings.realtime_warnings()

    if not settings.enable_realtime_voice:
        return RealtimeProviderSelection(
            enabled=False,
            provider_mode=provider_mode,
            configured=False,
            warnings=warnings,
            fallback_reason="disabled",
        )
    if provider_mode == RealtimeProviderMode.NONE:
        return RealtimeProviderSelection(
            enabled=True,
            provider_mode=provider_mode,
            configured=False,
            warnings=warnings or ["REALTIME_PROVIDER is none."],
            fallback_reason="disabled",
        )
    if not settings.realtime_configured:
        return RealtimeProviderSelection(
            enabled=True,
            provider_mode=provider_mode,
            configured=False,
            warnings=warnings or ["Realtime provider is not configured."],
            fallback_reason="not_configured",
        )

    if provider_mode == RealtimeProviderMode.AZURE_VOICE_LIVE:
        from app.services.azure_voice_live_realtime_provider import AzureVoiceLiveRealtimeProvider

        provider: RealtimeVoiceProvider = AzureVoiceLiveRealtimeProvider(settings, websocket_factory=websocket_factory)
    else:
        from app.services.azure_openai_realtime_provider import AzureOpenAIRealtimeProvider

        provider = AzureOpenAIRealtimeProvider(settings, websocket_factory=websocket_factory)

    return RealtimeProviderSelection(
        enabled=True,
        provider_mode=provider_mode,
        provider=provider,
        configured=True,
        warnings=warnings,
    )


def build_openai_realtime_uri(settings: Settings) -> str:
    endpoint = settings.azure_realtime_endpoint.rstrip("/")
    parsed = urlparse(endpoint)
    host = parsed.netloc or parsed.path
    scheme = "wss"
    path = "/openai/realtime"
    query = urlencode(
        {
            "api-version": settings.azure_realtime_api_version,
            "deployment": settings.azure_realtime_deployment,
        }
    )
    return f"{scheme}://{host}{path}?{query}"


def build_voice_live_uri(settings: Settings) -> str:
    base = settings.azure_voice_live_endpoint.strip()
    if not base:
        return ""
    separator = "&" if "?" in base else "?"
    model_query = urlencode({"model": settings.azure_voice_live_model})
    if "model=" in base:
        return base
    return f"{base}{separator}{model_query}"


def auth_headers(settings: Settings) -> dict[str, str]:
    return {"api-key": settings.azure_realtime_api_key} if settings.azure_realtime_api_key else {}

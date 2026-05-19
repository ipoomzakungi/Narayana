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

    async def send_tool_result(self, *, tool_call_id: str | None, result: dict[str, Any]) -> RealtimeSendResult:
        ...

    async def commit_audio_buffer(self) -> RealtimeSendResult:
        ...

    async def create_response(self, *, instructions: str | None = None) -> RealtimeSendResult:
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
        provider_settings = getattr(self.provider, "settings", None)
        return {
            "enabled": self.enabled,
            "provider": self.provider_mode.value,
            "configured": self.configured,
            "active_candidate": self.active_candidate,
            "input_audio_format": getattr(provider_settings, "effective_realtime_input_audio_format", None),
            "twilio_audio_passthrough": getattr(provider_settings, "realtime_input_audio_passthrough_enabled", False),
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

    async def send_tool_result(self, *, tool_call_id: str | None, result: dict[str, Any]) -> RealtimeSendResult:
        tracker = self._tracker(self.session_id or "", self.call_id)
        tracker.start("tool_result_sent")
        try:
            item: dict[str, Any] = {
                "type": "function_call_output",
                "output": json.dumps(result, ensure_ascii=False),
            }
            if tool_call_id:
                item["call_id"] = tool_call_id
            await self._send_json({"type": "conversation.item.create", "item": item})
            await self._send_response_create()
        except Exception as exc:
            sample = tracker.sample("tool_result_sent", metadata={"reason": "tool_result_failed"})
            return RealtimeSendResult(
                sent=False,
                provider=self.mode,
                fallback_reason="tool_result_failed",
                warnings=[f"Realtime tool result send failed: {exc}"],
                latency_ms=sample.latency_ms or 0,
            )
        sample = tracker.sample("tool_result_sent", metadata={"tool_call_id": tool_call_id})
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=sample.latency_ms or 0)

    async def commit_audio_buffer(self) -> RealtimeSendResult:
        tracker = self._tracker(self.session_id or "", self.call_id)
        tracker.start("audio_buffer_commit_sent")
        try:
            await self._send_json({"type": "input_audio_buffer.commit"})
        except Exception as exc:
            sample = tracker.sample("audio_buffer_commit_sent", metadata={"reason": "commit_failed"})
            return RealtimeSendResult(
                sent=False,
                provider=self.mode,
                fallback_reason="commit_failed",
                warnings=[f"Realtime audio buffer commit failed: {exc}"],
                latency_ms=sample.latency_ms or 0,
            )
        sample = tracker.sample("audio_buffer_commit_sent")
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=sample.latency_ms or 0)

    async def create_response(self, *, instructions: str | None = None) -> RealtimeSendResult:
        tracker = self._tracker(self.session_id or "", self.call_id)
        tracker.start("response_create_sent")
        try:
            await self._send_response_create(instructions=instructions)
        except Exception as exc:
            sample = tracker.sample("response_create_sent", metadata={"reason": "response_create_failed"})
            return RealtimeSendResult(
                sent=False,
                provider=self.mode,
                fallback_reason="response_create_failed",
                warnings=[f"Realtime response create failed: {exc}"],
                latency_ms=sample.latency_ms or 0,
            )
        sample = tracker.sample("response_create_sent")
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=sample.latency_ms or 0)

    async def _send_response_create(self, *, instructions: str | None = None) -> None:
        payload: dict[str, Any] = {"type": "response.create"}
        if instructions:
            payload["response"] = {"instructions": instructions}
        await self._send_json(payload)

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
        "Realtime voice mode: Thai first. Speak calmly, slowly, concisely, and empathetically. "
        "Ask exactly one crisis-intake question at a time. Do not chit-chat or answer off-topic questions. "
        "Never say rescue has been dispatched. Never say an ambulance is on the way. "
        "Never reveal RED, YELLOW, or GREEN triage labels to the caller. Do not diagnose. "
        "Escalate human review immediately for breathing difficulty, unconsciousness, severe bleeding, "
        "trapped people, active drowning, active fire or smoke, self-harm danger, child risk, "
        "or elderly vulnerable risk. Caller tone is metadata only, not the main triage signal. "
        "Use the crisis_intake_update tool whenever facts are collected or materially changed."
    )


def build_realtime_intake_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "crisis_intake_update",
        "description": "Record structured facts from the crisis call for human review and case creation.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "situation": {"type": "string", "description": "Brief situation summary."},
                "incident_type": {
                    "type": "string",
                    "enum": ["flood", "fire", "medical", "accident", "earthquake", "public_safety", "unknown"],
                },
                "location": {"type": "string"},
                "people_affected": {"type": ["integer", "null"], "minimum": 0},
                "injuries": {"type": "string"},
                "immediate_needs": {"type": "array", "items": {"type": "string"}},
                "caller_phone": {"type": ["string", "null"]},
                "language": {"type": "string"},
                "missing_fields": {"type": "array", "items": {"type": "string"}},
                "caller_tone": {"type": "string"},
                "recommended_operator_action": {"type": "string"},
            },
            "required": [
                "situation",
                "incident_type",
                "location",
                "people_affected",
                "injuries",
                "immediate_needs",
                "caller_phone",
                "language",
                "missing_fields",
                "caller_tone",
                "recommended_operator_action",
            ],
        },
    }


def build_openai_realtime_session_update(
    settings: Settings,
    instructions: str,
    *,
    input_transcription_enabled: bool | None = None,
) -> dict[str, Any]:
    transcription_enabled = (
        settings.realtime_input_transcription_enabled
        if input_transcription_enabled is None
        else input_transcription_enabled
    )
    if settings.azure_realtime_api_version.strip().lower() in {"v1", "ga"}:
        session = _build_openai_realtime_v1_session(
            settings,
            instructions,
            input_transcription_enabled=transcription_enabled,
        )
        return {
            "type": "session.update",
            "session": session,
        }

    session: dict[str, Any] = {
        "type": "realtime",
        "instructions": instructions,
        "input_audio_format": settings.effective_realtime_input_audio_format,
        "output_audio_format": "g711_ulaw",
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
            "create_response": True,
            "interrupt_response": True,
        },
        "tools": [build_realtime_intake_tool()],
        "tool_choice": "auto",
    }
    if transcription_enabled:
        session["input_audio_transcription"] = {"model": "whisper-1"}
    return {
        "type": "session.update",
        "session": session,
    }


def _build_openai_realtime_v1_session(
    settings: Settings,
    instructions: str,
    *,
    input_transcription_enabled: bool,
) -> dict[str, Any]:
    input_format = (
        {"type": "audio/pcmu"}
        if settings.effective_realtime_input_audio_format == "g711_ulaw"
        else {"type": "audio/pcm", "rate": 24000}
    )
    audio_input: dict[str, Any] = {
        "format": input_format,
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
            "create_response": True,
            "interrupt_response": True,
        },
    }
    if input_transcription_enabled:
        audio_input["transcription"] = {"model": "whisper-1"}
    return {
        "type": "realtime",
        "instructions": instructions,
        "output_modalities": ["audio"],
        "audio": {
            "input": audio_input,
            "output": {
                "format": {"type": "audio/pcmu"},
                "voice": settings.normalized_realtime_output_voice,
            },
        },
        "tools": [build_realtime_intake_tool()],
        "tool_choice": "auto",
    }


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
    api_version = settings.azure_realtime_api_version.strip().lower()
    if api_version in {"v1", "ga"}:
        path = "/openai/v1/realtime"
        query = urlencode({"model": settings.azure_realtime_deployment})
    else:
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

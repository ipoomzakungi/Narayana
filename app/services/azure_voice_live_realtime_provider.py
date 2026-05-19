from __future__ import annotations

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
from app.services.azure_openai_realtime_provider import _parse_tool_arguments
from app.services.realtime_voice_provider import (
    BaseRealtimeProvider,
    WebSocketFactory,
    auth_headers,
    build_voice_live_uri,
)


class AzureVoiceLiveRealtimeProvider(BaseRealtimeProvider):
    mode = RealtimeProviderMode.AZURE_VOICE_LIVE

    def __init__(self, settings: Settings, websocket_factory: WebSocketFactory | None = None) -> None:
        super().__init__(settings, websocket_factory)

    async def connect(self, *, session_id: str, call_id: str | None, instructions: str) -> RealtimeConnectionResult:
        self.session_id = session_id
        self.call_id = call_id
        tracker = self._tracker(session_id, call_id)
        tracker.start("connect")
        try:
            self.websocket = await self._open_websocket(build_voice_live_uri(self.settings), auth_headers(self.settings))
            await self._send_json(
                {
                    "type": "session.update",
                    "session": {
                        "instructions": instructions,
                        "turn_detection": {"type": "azure_semantic_vad", "silence_duration_ms": 500},
                        "input_audio_format": self.settings.effective_realtime_input_audio_format,
                        "output_audio_format": "g711_ulaw",
                        "voice": {"name": self.settings.azure_speech_voice, "type": "azure-standard"},
                    },
                }
            )
        except Exception as exc:
            await self.close()
            sample = tracker.sample("connect", metadata={"reason": "connect_failed"})
            return RealtimeConnectionResult(
                connected=False,
                provider=self.mode,
                fallback_reason="connect_failed",
                warnings=[f"Azure Voice Live connection failed: {exc}"],
                latency_ms=sample.latency_ms or 0,
            )
        sample = tracker.sample("connect")
        return RealtimeConnectionResult(connected=True, provider=self.mode, latency_ms=sample.latency_ms or 0)

    async def send_audio_frame(self, frame: AudioFrame) -> RealtimeSendResult:
        tracker = self._tracker(frame.session_id, self.call_id)
        tracker.start("input_audio_sent")
        try:
            await self._send_json({"type": "input_audio_buffer.append", "audio": frame.audio_base64})
        except Exception as exc:
            sample = tracker.sample("input_audio_sent", metadata={"sequence": frame.sequence, "reason": "stream_failed"})
            return RealtimeSendResult(
                sent=False,
                provider=self.mode,
                fallback_reason="stream_failed",
                warnings=[f"Azure Voice Live audio send failed: {exc}"],
                latency_ms=sample.latency_ms or 0,
            )
        sample = tracker.sample("input_audio_sent", metadata={"sequence": frame.sequence})
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=sample.latency_ms or 0)

    async def receive_audio_event(self) -> RealtimeAudioEvent | None:
        try:
            message = await self._recv_json()
        except Exception as exc:
            return self._event(
                RealtimeAudioEventType.ERROR,
                fallback_reason="provider_error",
                warnings=[f"Azure Voice Live receive failed: {exc}"],
            )
        return self._normalize_message(message)

    def _normalize_message(self, message: dict) -> RealtimeAudioEvent | None:
        event_type = str(message.get("type") or "")
        if event_type in {"response.created", "response.started"}:
            return self._event(RealtimeAudioEventType.RESPONSE_STARTED, metadata={"provider_event_type": event_type})
        if event_type in {"response.done", "response.completed"}:
            return self._event(RealtimeAudioEventType.RESPONSE_COMPLETED, metadata={"provider_event_type": event_type})
        if event_type in {"response.audio.delta", "response.output_audio.delta"}:
            audio = message.get("delta") or message.get("audio")
            if not isinstance(audio, str) or not audio:
                return self._event(
                    RealtimeAudioEventType.ERROR,
                    fallback_reason="provider_error",
                    warnings=["Azure Voice Live audio delta was empty."],
                    metadata={"provider_event_type": event_type},
                )
            return self._event(
                RealtimeAudioEventType.OUTPUT_AUDIO_RECEIVED,
                audio_base64=audio,
                audio_format=RealtimeAudioFormat.MULAW_8KHZ,
                metadata={"provider_event_type": event_type},
            )
        if event_type in {
            "conversation.item.input_audio_transcription.delta",
            "input_audio_buffer.transcription.delta",
            "input_audio_transcription.delta",
        }:
            return self._transcript_event(
                RealtimeAudioEventType.CALLER_TRANSCRIPT_DELTA,
                message,
                provider_event_type=event_type,
            )
        if event_type in {
            "conversation.item.input_audio_transcription.completed",
            "input_audio_buffer.transcription.completed",
            "input_audio_transcription.completed",
        }:
            return self._transcript_event(
                RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
                message,
                provider_event_type=event_type,
            )
        if event_type in {
            "conversation.item.input_audio_transcription.failed",
            "input_audio_buffer.transcription.failed",
            "input_audio_transcription.failed",
        }:
            error = message.get("error") if isinstance(message.get("error"), dict) else {}
            warning = str(error.get("message") or "Azure Voice Live caller transcription failed.")
            return self._event(
                RealtimeAudioEventType.CALLER_TRANSCRIPTION_FAILED,
                warnings=[warning],
                metadata={
                    "provider_event_type": event_type,
                    "item_id": message.get("item_id"),
                    "error": error,
                },
            )
        if event_type in {"response.audio_transcript.delta", "response.output_audio_transcript.delta", "response.text.delta"}:
            return self._transcript_event(
                RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA,
                message,
                provider_event_type=event_type,
            )
        if event_type in {
            "response.audio_transcript.done",
            "response.output_audio_transcript.done",
            "response.text.done",
            "response.audio_transcript.completed",
        }:
            return self._transcript_event(
                RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_COMPLETED,
                message,
                provider_event_type=event_type,
            )
        if event_type in {"response.function_call_arguments.done", "response.output_item.done"}:
            tool_event = self._tool_event(message, event_type=event_type)
            if tool_event is not None:
                return tool_event
        if event_type == "error":
            error = message.get("error") if isinstance(message.get("error"), dict) else {}
            return self._event(
                RealtimeAudioEventType.ERROR,
                fallback_reason="provider_error",
                warnings=[str(error.get("message") or "Azure Voice Live returned an error.")],
                metadata={"provider_event_type": event_type},
            )
        return self._event(
            RealtimeAudioEventType.UNKNOWN_PROVIDER_EVENT,
            metadata={"provider_event_type": event_type or "missing"},
        )

    def _transcript_event(
        self,
        normalized_type: RealtimeAudioEventType,
        message: dict,
        *,
        provider_event_type: str,
    ) -> RealtimeAudioEvent | None:
        text = message.get("transcript") or message.get("delta") or message.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        return self._event(
            normalized_type,
            text=text,
            metadata={"provider_event_type": provider_event_type, "item_id": message.get("item_id")},
        )

    def _tool_event(self, message: dict, *, event_type: str) -> RealtimeAudioEvent | None:
        item = message.get("item") if isinstance(message.get("item"), dict) else {}
        tool_name = message.get("name") or item.get("name")
        if tool_name != "crisis_intake_update":
            return None
        raw_arguments = message.get("arguments") or item.get("arguments") or "{}"
        tool_call_id = message.get("call_id") or item.get("call_id") or message.get("item_id") or item.get("id")
        return self._event(
            RealtimeAudioEventType.STRUCTURED_EXTRACTION,
            metadata={
                "provider_event_type": event_type,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "tool_arguments": _parse_tool_arguments(raw_arguments),
            },
        )

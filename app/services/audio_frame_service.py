from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

from app.models.audio import AudioFrame, InputMode


class AudioFrameError(ValueError):
    pass


def decode_pcm16(frame: AudioFrame) -> bytes:
    validate_audio_frame(frame)
    return base64.b64decode(frame.audio_base64)


def validate_audio_frame(frame: AudioFrame) -> None:
    if frame.encoding.lower() != "pcm16":
        raise AudioFrameError("Only pcm16 audio is supported for V0.")
    if frame.channels != 1:
        raise AudioFrameError("Only mono audio is supported for V0.")
    if frame.duration_ms != 20:
        raise AudioFrameError("Audio frames must be 20 ms.")
    if frame.sample_rate_hz <= 0:
        raise AudioFrameError("sample_rate_hz must be positive.")
    try:
        payload = base64.b64decode(frame.audio_base64, validate=True)
    except Exception as exc:
        raise AudioFrameError("audio_base64 is not valid base64.") from exc
    if len(payload) % 2 != 0:
        raise AudioFrameError("pcm16 payload must contain an even number of bytes.")


def pcm16_samples(payload: bytes) -> list[int]:
    return [int.from_bytes(payload[index : index + 2], "little", signed=True) for index in range(0, len(payload), 2)]


class AudioInputAdapter(Protocol):
    name: str
    enabled: bool
    input_mode: InputMode

    async def frames(self) -> AsyncIterator[AudioFrame]:
        ...


@dataclass
class LocalMicAdapter:
    name: str = "local_mic"
    enabled: bool = True
    input_mode: InputMode = InputMode.LOCAL_MIC

    async def frames(self) -> AsyncIterator[AudioFrame]:
        if False:
            yield  # pragma: no cover
        raise NotImplementedError("LocalMicAdapter frames are supplied by the FastAPI WebSocket route.")


@dataclass
class TwilioMediaStreamAdapter:
    name: str = "twilio_media_stream"
    enabled: bool = False
    input_mode: InputMode = InputMode.TWILIO_MEDIA_STREAM

    async def frames(self) -> AsyncIterator[AudioFrame]:
        if False:
            yield  # pragma: no cover
        raise NotImplementedError("Twilio Media Streams are V1 only and disabled for V0.")


@dataclass
class ACSAudioStreamAdapter:
    name: str = "acs_audio_stream"
    enabled: bool = False
    input_mode: InputMode = InputMode.ACS_AUDIO_STREAM

    async def frames(self) -> AsyncIterator[AudioFrame]:
        if False:
            yield  # pragma: no cover
        raise NotImplementedError("Azure Communication Services audio is V1 only and disabled for V0.")

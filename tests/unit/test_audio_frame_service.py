from __future__ import annotations

import base64

import pytest

from app.models.audio import AudioFrame
from app.services.audio_frame_service import AudioFrameError, decode_pcm16, validate_audio_frame


def frame(**overrides) -> AudioFrame:
    payload = base64.b64encode((0).to_bytes(2, "little", signed=True) * 320).decode("ascii")
    data = dict(
        session_id="session_1",
        sequence=1,
        timestamp_ms=20,
        audio_base64=payload,
    )
    data.update(overrides)
    return AudioFrame(**data)


def test_valid_pcm16_frame_decodes() -> None:
    audio_frame = frame()

    validate_audio_frame(audio_frame)

    assert len(decode_pcm16(audio_frame)) == 640


@pytest.mark.parametrize(
    "overrides",
    [
        {"encoding": "mulaw"},
        {"channels": 2},
        {"duration_ms": 40},
        {"sample_rate_hz": 0},
        {"audio_base64": "not-base64"},
    ],
)
def test_invalid_frame_metadata_raises(overrides) -> None:
    with pytest.raises(AudioFrameError):
        validate_audio_frame(frame(**overrides))

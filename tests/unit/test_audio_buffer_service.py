from __future__ import annotations

import base64
from pathlib import Path
import wave

import pytest

from app.models.audio import AudioFrame, CallerTurn
from app.services.audio_buffer_service import AudioBufferError, AudioBufferService


def pcm_frame(sequence: int, amplitude: int = 12000, session_id: str = "session_1") -> AudioFrame:
    payload = b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(320))
    return AudioFrame(
        session_id=session_id,
        sequence=sequence,
        timestamp_ms=sequence * 20,
        sample_rate_hz=16000,
        duration_ms=20,
        audio_base64=base64.b64encode(payload).decode("ascii"),
    )


def caller_turn(session_id: str = "session_1", turn_id: str = "turn_1") -> CallerTurn:
    return CallerTurn(
        session_id=session_id,
        turn_id=turn_id,
        duration_ms=60,
        pre_speech_padding_ms=40,
        silence_threshold_ms=600,
    )


def test_audio_buffer_service_writes_valid_wav_with_expected_path(tmp_path) -> None:
    service = AudioBufferService(root_path=str(tmp_path / ".data" / "audio"), pre_speech_padding_ms=40)

    service.observe_frame(pcm_frame(1, amplitude=0))
    service.observe_frame(pcm_frame(2, amplitude=2000))
    service.observe_frame(pcm_frame(3, amplitude=16000), speech_started=True)
    service.observe_frame(pcm_frame(4, amplitude=16000))
    service.observe_frame(pcm_frame(5, amplitude=0))

    result = service.write_committed_turn(caller_turn())

    assert Path(result.audio_ref).parts[-2:] == ("session_1", "turn_1.wav")
    assert result.audio_debug_id == "turn_1"
    assert result.frame_count == 5

    with wave.open(result.audio_ref, "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() == 320 * 5


def test_audio_buffer_service_rejects_empty_committed_turn(tmp_path) -> None:
    service = AudioBufferService(root_path=str(tmp_path / ".data" / "audio"))

    with pytest.raises(AudioBufferError, match="No audio frames"):
        service.write_committed_turn(caller_turn())

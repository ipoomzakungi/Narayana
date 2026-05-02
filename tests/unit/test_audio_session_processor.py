from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.telephony import CallMetadata, TelephonyCodec, TelephonyProvider, VoiceInputMode
from app.services.audio_session_processor import AudioSessionProcessor


def pcm_payload(amplitude: int) -> str:
    payload = b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(320))
    return base64.b64encode(payload).decode("ascii")


def frame(sequence: int, amplitude: int, session_id: str = "session_processor") -> AudioFrame:
    return AudioFrame(
        session_id=session_id,
        sequence=sequence,
        timestamp_ms=sequence * 20,
        encoding="pcm16",
        sample_rate_hz=16000,
        channels=1,
        duration_ms=20,
        audio_base64=pcm_payload(amplitude),
    )


async def drain_case_payload(processor: AudioSessionProcessor, session_id: str = "session_processor") -> dict:
    payloads: list[dict] = []
    payloads.extend(await processor.process_frame(frame(1, 24000, session_id=session_id)))
    for sequence in range(2, 41):
        payloads.extend(await processor.process_frame(frame(sequence, 0, session_id=session_id)))
    return [payload for payload in payloads if payload["type"] == "triage.case.created"][0]


@pytest.mark.asyncio
async def test_processor_local_payload_omits_telephony_metadata(tmp_path) -> None:
    processor = AudioSessionProcessor(
        settings=Settings(use_mock_services=True, case_store_path=str(tmp_path / "cases.json"), audio_store_path=str(tmp_path / "audio")),
        session_id="session_processor",
    )

    payload = await drain_case_payload(processor)

    assert payload["provider_mode"] == "mock"
    assert payload["record"]["case"]["triage_level"] == "RED"
    assert "source_input_mode" not in payload
    assert "call_metadata" not in payload
    assert Path(payload["audio_ref"]).exists()


@pytest.mark.asyncio
async def test_processor_phone_payload_includes_source_metadata(tmp_path) -> None:
    metadata = CallMetadata(
        provider=TelephonyProvider.TWILIO,
        call_id="CA123",
        from_number="+15550001111",
        to_number="+15552223333",
        country="US",
        codec=TelephonyCodec.MULAW,
        sample_rate=8000,
    )
    processor = AudioSessionProcessor(
        settings=Settings(use_mock_services=True, case_store_path=str(tmp_path / "cases.json"), audio_store_path=str(tmp_path / "audio")),
        session_id="session_processor",
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        call_metadata=metadata,
    )

    payload = await drain_case_payload(processor)

    assert payload["source_input_mode"] == "twilio_call"
    assert payload["call_metadata"]["provider"] == "twilio"
    assert payload["call_metadata"]["call_id"] == "CA123"
    assert payload["call_metadata"]["sample_rate"] == 8000

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.telephony import CallMetadata, TelephonyCodec, TelephonyProvider, VoiceInputMode
from app.models.triage import IncidentType, ProviderMode, TriageLevel, TriageResult
from app.services.audio_session_processor import AudioSessionProcessor
from app.services.voice_agent_provider import TranscriptInput, VoiceProviderResult


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


async def drain_payloads(processor: AudioSessionProcessor, session_id: str = "session_processor") -> list[dict]:
    payloads: list[dict] = []
    payloads.extend(await processor.process_frame(frame(1, 24000, session_id=session_id)))
    for sequence in range(2, 41):
        payloads.extend(await processor.process_frame(frame(sequence, 0, session_id=session_id)))
    return payloads


class StaticTranscriptProvider:
    mode = ProviderMode.MOCK

    def __init__(self, transcript: str) -> None:
        self.transcript = transcript

    async def process_turn(self, turn) -> VoiceProviderResult:
        triage = TriageResult(
            language="th",
            incident_type=IncidentType.UNKNOWN,
            triage_level=TriageLevel.YELLOW,
            confidence=0.8,
            location_text="",
            ai_summary="Static transcript.",
            triage_reason="Static test provider.",
        )
        return VoiceProviderResult(
            provider_mode=ProviderMode.MOCK,
            transcript=self.transcript,
            transcript_source="mock",
            language="th",
            confidence=0.8,
            triage=triage,
            audio_ref=turn.audio_ref,
        )

    async def process_transcript(self, transcript_input: TranscriptInput) -> VoiceProviderResult:
        raise NotImplementedError

    async def health(self):
        raise NotImplementedError


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


@pytest.mark.asyncio
async def test_processor_multi_turn_disabled_keeps_direct_case_payload(tmp_path) -> None:
    processor = AudioSessionProcessor(
        settings=Settings(
            use_mock_services=True,
            enable_multi_turn_intake=False,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
        ),
        session_id="session_processor",
    )

    payload = await drain_case_payload(processor)

    assert payload["type"] == "triage.case.created"
    assert "intake" not in payload


@pytest.mark.asyncio
async def test_processor_multi_turn_enabled_emits_followup(tmp_path, monkeypatch) -> None:
    import app.services.audio_session_processor as processor_module

    monkeypatch.setattr(processor_module, "get_voice_provider", lambda settings, requested_mode=None: StaticTranscriptProvider("น้ำท่วมอยู่ที่หาดใหญ่"))
    processor = AudioSessionProcessor(
        settings=Settings(
            use_mock_services=True,
            enable_multi_turn_intake=True,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
        ),
        session_id="session_followup",
    )

    payloads = await drain_payloads(processor, session_id="session_followup")
    followups = [payload for payload in payloads if payload["type"] == "intake.followup"]

    assert followups
    assert followups[0]["action"] == "ask_followup"
    assert followups[0]["response_text"]
    assert followups[0]["case_group"] == "flood"
    assert "injuries" in followups[0]["missing_fields"]


@pytest.mark.asyncio
async def test_processor_multi_turn_enabled_creates_case(tmp_path, monkeypatch) -> None:
    import app.services.audio_session_processor as processor_module

    monkeypatch.setattr(
        processor_module,
        "get_voice_provider",
        lambda settings, requested_mode=None: StaticTranscriptProvider("น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"),
    )
    processor = AudioSessionProcessor(
        settings=Settings(
            use_mock_services=True,
            enable_multi_turn_intake=True,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
        ),
        session_id="session_red",
    )

    payloads = await drain_payloads(processor, session_id="session_red")
    cases = [payload for payload in payloads if payload["type"] == "triage.case.created"]

    assert cases
    assert cases[0]["intake"]["action"] == "escalate_human_review"
    assert cases[0]["record"]["case"]["triage_level"] == "RED"
    assert cases[0]["record"]["case_group"] == "rescue"

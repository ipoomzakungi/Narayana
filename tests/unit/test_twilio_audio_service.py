from __future__ import annotations

import base64

import pytest

from app.core.config import Settings
from app.models.telephony import TelephonyCodec, TelephonyProvider
from app.services.audio_frame_service import decode_pcm16
from app.services.twilio_audio_service import (
    TwilioMediaError,
    build_twilio_mark_event,
    build_twilio_media_event,
    chunk_mulaw_audio_for_twilio,
    decode_mulaw_to_pcm16,
    encode_pcm16_to_mulaw,
    encode_pcm16_to_mulaw_base64,
    estimate_audio_duration_ms,
    normalize_twilio_media_message,
    twilio_call_metadata,
)

audioop = pytest.importorskip("audioop")


def pcm16_payload(amplitude: int, sample_count: int = 160) -> bytes:
    return b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(sample_count))


def mulaw_base64(amplitude: int, sample_count: int = 160) -> str:
    return base64.b64encode(audioop.lin2ulaw(pcm16_payload(amplitude, sample_count), 2)).decode("ascii")


def media_message(payload: str | None = None, sequence: str = "2") -> dict:
    return {
        "event": "media",
        "sequenceNumber": sequence,
        "media": {
            "track": "inbound",
            "chunk": "1",
            "timestamp": "20",
            "payload": payload if payload is not None else mulaw_base64(12000),
        },
        "streamSid": "MZ123",
    }


def test_twilio_start_message_creates_call_metadata() -> None:
    metadata = twilio_call_metadata(
        {
            "event": "start",
            "start": {
                "callSid": "CA123",
                "streamSid": "MZ123",
                "accountSid": "AC123",
                "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                "customParameters": {"From": "+15550001111", "To": "+15552223333", "FromCountry": "US"},
            },
        },
        "CAfallback",
        Settings(phone_test_country="TH"),
    )

    assert metadata.provider == TelephonyProvider.TWILIO
    assert metadata.call_id == "CA123"
    assert metadata.from_number == "+15550001111"
    assert metadata.to_number == "+15552223333"
    assert metadata.country == "US"
    assert metadata.codec == TelephonyCodec.MULAW
    assert metadata.sample_rate == 8000
    assert metadata.raw_provider_payload


def test_mulaw_payload_converts_to_pcm16() -> None:
    pcm16 = decode_mulaw_to_pcm16(mulaw_base64(12000))

    assert len(pcm16) == 320
    assert len(pcm16) % 2 == 0


def test_media_message_normalizes_to_audio_frame() -> None:
    frame = normalize_twilio_media_message(media_message(), session_id="twilio_CA123")

    assert frame.session_id == "twilio_CA123"
    assert frame.sequence == 2
    assert frame.timestamp_ms == 20
    assert frame.encoding == "pcm16"
    assert frame.sample_rate_hz == 8000
    assert frame.channels == 1
    assert frame.duration_ms == 20
    assert len(decode_pcm16(frame)) == 320


def test_invalid_base64_payload_raises_clear_error() -> None:
    with pytest.raises(TwilioMediaError, match="not valid base64"):
        normalize_twilio_media_message(media_message("not base64!!!"), session_id="twilio_CA123")


def test_unsupported_codec_raises_clear_error() -> None:
    with pytest.raises(TwilioMediaError, match="Unsupported Twilio media codec"):
        normalize_twilio_media_message(
            media_message(),
            session_id="twilio_CA123",
            codec=TelephonyCodec.PCM16,
        )


def test_non_20_ms_payload_raises_clear_error() -> None:
    with pytest.raises(TwilioMediaError, match="20 ms"):
        normalize_twilio_media_message(media_message(mulaw_base64(12000, sample_count=80)), session_id="twilio_CA123")


def test_pcm16_encodes_to_mulaw_for_outbound_twilio_audio() -> None:
    pcm16 = pcm16_payload(12000)
    mulaw = encode_pcm16_to_mulaw(pcm16)
    payload = encode_pcm16_to_mulaw_base64(pcm16)

    assert len(mulaw) == 160
    assert base64.b64decode(payload) == mulaw


def test_outbound_mulaw_chunks_are_base64_20_ms_payloads() -> None:
    chunks = chunk_mulaw_audio_for_twilio(b"\xff" * 320)

    assert len(chunks) == 2
    assert all(len(base64.b64decode(chunk)) == 160 for chunk in chunks)


def test_twilio_outbound_media_and_mark_event_shapes() -> None:
    media_event = build_twilio_media_event("MZ123", "abcd")
    mark_event = build_twilio_mark_event("MZ123", "narayana_tts_test")

    assert media_event == {
        "event": "media",
        "streamSid": "MZ123",
        "media": {"payload": "abcd"},
    }
    assert mark_event == {
        "event": "mark",
        "streamSid": "MZ123",
        "mark": {"name": "narayana_tts_test"},
    }


def test_estimate_audio_duration_for_mulaw_bytes() -> None:
    assert estimate_audio_duration_ms(160) == 20
    assert estimate_audio_duration_ms(0) == 0

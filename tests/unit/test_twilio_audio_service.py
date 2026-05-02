from __future__ import annotations

import base64

import pytest

from app.core.config import Settings
from app.models.telephony import TelephonyCodec, TelephonyProvider
from app.services.audio_frame_service import decode_pcm16
from app.services.twilio_audio_service import (
    TwilioMediaError,
    decode_mulaw_to_pcm16,
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

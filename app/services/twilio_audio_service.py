from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any

try:
    import audioop
except ImportError:  # pragma: no cover - Python 3.13+ can use audioop-lts
    audioop = None  # type: ignore[assignment]

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.telephony import CallMetadata, TelephonyCodec, TelephonyProvider


class TwilioMediaError(ValueError):
    pass


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _codec_from_encoding(encoding: str | None) -> TelephonyCodec:
    if not encoding:
        return TelephonyCodec.MULAW
    normalized = encoding.lower()
    if "mulaw" in normalized or "mu-law" in normalized or "ulaw" in normalized:
        return TelephonyCodec.MULAW
    if "pcm" in normalized:
        return TelephonyCodec.PCM16
    return TelephonyCodec.UNKNOWN


def twilio_call_metadata(message: dict[str, Any], call_id: str, settings: Settings) -> CallMetadata:
    start = message.get("start") if isinstance(message.get("start"), dict) else {}
    media_format = start.get("mediaFormat") if isinstance(start.get("mediaFormat"), dict) else {}
    custom = start.get("customParameters") if isinstance(start.get("customParameters"), dict) else {}
    return CallMetadata(
        provider=TelephonyProvider.TWILIO,
        call_id=str(start.get("callSid") or call_id),
        from_number=start.get("from") or custom.get("From") or settings.phone_test_number or None,
        to_number=start.get("to") or custom.get("To") or settings.twilio_phone_number or None,
        country=start.get("fromCountry") or custom.get("FromCountry") or settings.phone_test_country or None,
        codec=_codec_from_encoding(media_format.get("encoding")),
        sample_rate=_to_int(media_format.get("sampleRate"), 8000),
        started_at=datetime.now(timezone.utc),
        raw_provider_payload={
            "streamSid": start.get("streamSid"),
            "accountSid": start.get("accountSid"),
            "mediaFormat": media_format,
        },
    )


def decode_mulaw_to_pcm16(payload_base64: str) -> bytes:
    try:
        mulaw = base64.b64decode(payload_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TwilioMediaError("Twilio media payload is not valid base64.") from exc
    if not mulaw:
        raise TwilioMediaError("Twilio media payload is empty.")
    if audioop is None:
        raise TwilioMediaError("audioop is unavailable; install audioop-lts for mu-law conversion.")
    return audioop.ulaw2lin(mulaw, 2)


def encode_pcm16_to_mulaw(pcm16: bytes) -> bytes:
    if not pcm16:
        return b""
    if audioop is None:
        raise TwilioMediaError("audioop is unavailable; install audioop-lts for mu-law conversion.")
    if len(pcm16) % 2 != 0:
        raise TwilioMediaError("PCM16 audio must contain whole 16-bit samples.")
    return audioop.lin2ulaw(pcm16, 2)


def encode_pcm16_to_mulaw_base64(pcm16: bytes) -> str:
    return base64.b64encode(encode_pcm16_to_mulaw(pcm16)).decode("ascii")


def chunk_mulaw_bytes(mulaw: bytes, *, sample_rate_hz: int = 8000, chunk_ms: int = 20) -> list[bytes]:
    if not mulaw:
        return []
    if sample_rate_hz <= 0 or chunk_ms <= 0:
        raise TwilioMediaError("sample_rate_hz and chunk_ms must be positive.")
    chunk_size = max(1, sample_rate_hz * chunk_ms // 1000)
    return [mulaw[index : index + chunk_size] for index in range(0, len(mulaw), chunk_size)]


def chunk_mulaw_audio_for_twilio(mulaw: bytes, *, sample_rate_hz: int = 8000, chunk_ms: int = 20) -> list[str]:
    return [base64.b64encode(chunk).decode("ascii") for chunk in chunk_mulaw_bytes(mulaw, sample_rate_hz=sample_rate_hz, chunk_ms=chunk_ms)]


def build_twilio_media_event(stream_sid: str, payload_base64: str) -> dict[str, Any]:
    if not stream_sid:
        raise TwilioMediaError("Twilio streamSid is required for outbound media.")
    if not payload_base64:
        raise TwilioMediaError("Twilio outbound media payload is empty.")
    return {
        "event": "media",
        "streamSid": stream_sid,
        "media": {"payload": payload_base64},
    }


def build_twilio_mark_event(stream_sid: str, name: str) -> dict[str, Any]:
    if not stream_sid:
        raise TwilioMediaError("Twilio streamSid is required for outbound mark.")
    if not name:
        raise TwilioMediaError("Twilio mark name is required.")
    return {
        "event": "mark",
        "streamSid": stream_sid,
        "mark": {"name": name},
    }


def build_twilio_clear_event(stream_sid: str) -> dict[str, Any]:
    if not stream_sid:
        raise TwilioMediaError("Twilio streamSid is required for clear.")
    return {
        "event": "clear",
        "streamSid": stream_sid,
    }


def estimate_audio_duration_ms(byte_count: int, *, sample_rate_hz: int = 8000) -> int:
    if byte_count <= 0 or sample_rate_hz <= 0:
        return 0
    return round(byte_count * 1000 / sample_rate_hz)


def normalize_twilio_media_message(
    message: dict[str, Any],
    *,
    session_id: str,
    sample_rate_hz: int = 8000,
    codec: TelephonyCodec = TelephonyCodec.MULAW,
    assistant_is_speaking: bool = False,
) -> AudioFrame:
    if message.get("event") != "media":
        raise TwilioMediaError("Twilio message is not a media event.")
    if codec != TelephonyCodec.MULAW:
        raise TwilioMediaError(f"Unsupported Twilio media codec: {codec}.")
    media = message.get("media")
    if not isinstance(media, dict):
        raise TwilioMediaError("Twilio media event is missing media details.")
    payload_base64 = media.get("payload")
    if not isinstance(payload_base64, str):
        raise TwilioMediaError("Twilio media event is missing payload.")

    pcm16 = decode_mulaw_to_pcm16(payload_base64)
    expected_samples = sample_rate_hz * 20 // 1000
    if len(pcm16) != expected_samples * 2:
        actual_ms = round((len(pcm16) / 2) * 1000 / sample_rate_hz) if sample_rate_hz else 0
        raise TwilioMediaError(f"Twilio media frame must be 20 ms; received about {actual_ms} ms.")

    return AudioFrame(
        session_id=session_id,
        sequence=_to_int(message.get("sequenceNumber"), _to_int(media.get("chunk"), 0)),
        timestamp_ms=_to_int(media.get("timestamp"), 0),
        encoding="pcm16",
        sample_rate_hz=sample_rate_hz,
        channels=1,
        duration_ms=20,
        audio_base64=base64.b64encode(pcm16).decode("ascii"),
        assistant_is_speaking=assistant_is_speaking,
    )

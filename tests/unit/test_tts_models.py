from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.tts import TTSTestResponse, TTSProfile, TTSRequest, TTSResult


def test_tts_request_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        TTSRequest(text="   ")


def test_tts_request_accepts_greeting_profile() -> None:
    request = TTSRequest(text="สวัสดีค่ะ", profile="greeting")

    assert request.profile == TTSProfile.GREETING


def test_tts_request_accepts_closing_profile() -> None:
    request = TTSRequest(text="หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ", profile="closing")

    assert request.profile == TTSProfile.CLOSING


def test_tts_result_keeps_payloads_out_of_public_dump() -> None:
    result = TTSResult(configured=True, voice="th-TH-PremwadeeNeural").with_payloads(["abcd"])

    assert result.payloads == ["abcd"]
    assert result.payload_count == 1
    assert "payloads" not in result.model_dump()


def test_tts_test_response_has_metadata_only() -> None:
    response = TTSTestResponse(
        configured=False,
        voice="th-TH-PremwadeeNeural",
        warnings=["Azure Speech TTS is not configured."],
        missing_variables=["AZURE_SPEECH_KEY"],
    )

    payload = response.model_dump()

    assert payload["configured"] is False
    assert payload["payload_count"] == 0
    assert payload["total_bytes"] == 0
    assert "payloads" not in payload

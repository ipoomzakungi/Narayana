from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.triage import IncidentType, ProviderMode, TriageLevel, TriageResult
from app.services.voice_agent_provider import VoiceProviderResult

audioop = pytest.importorskip("audioop")


def mulaw_payload(amplitude: int, sample_count: int = 160) -> str:
    pcm16 = b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(sample_count))
    return base64.b64encode(audioop.lin2ulaw(pcm16, 2)).decode("ascii")


def media(sequence: int, amplitude: int) -> dict:
    return {
        "event": "media",
        "sequenceNumber": str(sequence),
        "media": {
            "track": "inbound",
            "chunk": str(sequence),
            "timestamp": str(sequence * 20),
            "payload": mulaw_payload(amplitude),
        },
        "streamSid": "MZ123",
    }


def test_simulated_twilio_media_stream_creates_mock_red_case(tmp_path, monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    monkeypatch.setattr(
        routes_twilio,
        "get_settings",
        lambda: Settings(
            use_mock_services=True,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
            phone_test_country="US",
            phone_test_number="+15550001111",
            twilio_phone_number="+15552223333",
        ),
    )
    client = TestClient(create_app())

    with client.websocket_connect("/ws/telephony/twilio/CA123") as websocket:
        websocket.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
        websocket.send_json(
            {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": "CA123",
                    "streamSid": "MZ123",
                    "accountSid": "AC123",
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                    "customParameters": {"From": "+15550001111", "To": "+15552223333", "FromCountry": "US"},
                },
            }
        )
        start_message = websocket.receive_json()
        assert start_message["type"] == "session.started"
        assert start_message["source_input_mode"] == "twilio_call"

        websocket.send_json(media(2, 24000))
        for sequence in range(3, 42):
            websocket.send_json(media(sequence, 0))

        messages = []
        for _ in range(100):
            message = websocket.receive_json()
            messages.append(message)
            if message["type"] == "triage.case.created":
                break

    case_messages = [message for message in messages if message["type"] == "triage.case.created"]
    assert case_messages
    case_message = case_messages[0]
    assert case_message["provider_mode"] == "mock"
    assert case_message["source_input_mode"] == "twilio_call"
    assert case_message["call_metadata"]["provider"] == "twilio"
    assert case_message["call_metadata"]["call_id"] == "CA123"
    assert case_message["call_metadata"]["from_number"] == "+15550001111"
    assert case_message["call_metadata"]["to_number"] == "+15552223333"
    assert case_message["call_metadata"]["country"] == "US"
    assert case_message["call_metadata"]["codec"] == "mulaw"
    assert case_message["call_metadata"]["sample_rate"] == 8000
    assert case_message["record"]["case"]["triage_level"] == "RED"
    assert case_message["record"]["case"]["human_review_required"] is True
    assert case_message["audio_ref"]


def test_simulated_twilio_media_stream_can_emit_intake_followup(tmp_path, monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio
    import app.services.audio_session_processor as processor_module

    class FollowupProvider:
        async def process_turn(self, turn):
            triage = TriageResult(
                language="th",
                incident_type=IncidentType.FLOOD,
                triage_level=TriageLevel.YELLOW,
                confidence=0.8,
                location_text="หาดใหญ่",
                ai_summary="Flood in Hat Yai.",
                triage_reason="Needs more information.",
            )
            return VoiceProviderResult(
                provider_mode=ProviderMode.MOCK,
                transcript="น้ำท่วมอยู่ที่หาดใหญ่",
                transcript_source="mock",
                language="th",
                confidence=0.8,
                triage=triage,
                audio_ref=turn.audio_ref,
            )

    monkeypatch.setattr(
        routes_twilio,
        "get_settings",
        lambda: Settings(
            use_mock_services=True,
            enable_multi_turn_intake=True,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
            phone_test_country="US",
            phone_test_number="+15550001111",
            twilio_phone_number="+15552223333",
        ),
    )
    monkeypatch.setattr(processor_module, "get_voice_provider", lambda settings, requested_mode=None: FollowupProvider())
    client = TestClient(create_app())

    with client.websocket_connect("/ws/telephony/twilio/CA123") as websocket:
        websocket.send_json(
            {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": "CA123",
                    "streamSid": "MZ123",
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                    "customParameters": {"From": "+15550001111", "To": "+15552223333", "FromCountry": "US"},
                },
            }
        )
        assert websocket.receive_json()["type"] == "session.started"
        websocket.send_json(media(2, 24000))
        for sequence in range(3, 42):
            websocket.send_json(media(sequence, 0))

        messages = []
        for _ in range(100):
            message = websocket.receive_json()
            messages.append(message)
            if message["type"] == "intake.followup":
                break

    followups = [message for message in messages if message["type"] == "intake.followup"]
    assert followups
    followup = followups[0]
    assert followup["source_input_mode"] == "twilio_call"
    assert followup["call_metadata"]["call_id"] == "CA123"
    assert followup["response_text"]
    assert followup["case_group"] == "flood"


def test_twilio_media_stream_reports_malformed_media_without_credentials(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    monkeypatch.setattr(routes_twilio, "get_settings", lambda: Settings(use_mock_services=True))
    client = TestClient(create_app())

    with client.websocket_connect("/ws/telephony/twilio/CA123") as websocket:
        websocket.send_json({"event": "media", "sequenceNumber": "1", "media": {"payload": "bad!"}})
        message = websocket.receive_json()

    assert message["type"] == "error"
    assert "base64" in message["detail"]

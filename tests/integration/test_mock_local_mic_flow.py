from __future__ import annotations

import base64
from pathlib import Path
import wave

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def pcm_payload(amplitude: int) -> str:
    payload = b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(320))
    return base64.b64encode(payload).decode("ascii")


def frame(sequence: int, amplitude: int) -> dict:
    return {
        "type": "audio.frame",
        "session_id": "session_ws",
        "sequence": sequence,
        "timestamp_ms": sequence * 20,
        "encoding": "pcm16",
        "sample_rate_hz": 16000,
        "channels": 1,
        "duration_ms": 20,
        "audio_base64": pcm_payload(amplitude),
    }


def test_mock_local_mic_flow_creates_case(tmp_path, monkeypatch) -> None:
    import app.api.routes_audio as routes_audio

    monkeypatch.setattr(
        routes_audio,
        "get_settings",
        lambda: Settings(
            use_mock_services=True,
            case_store_path=str(tmp_path / "cases.json"),
            audio_store_path=str(tmp_path / "audio"),
        ),
    )
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/local-audio") as websocket:
        websocket.send_json({"type": "session.start", "session_id": "session_ws"})
        start_message = websocket.receive_json()
        assert start_message["type"] == "session.started"
        assert start_message["provider_mode"] == "mock"
        assert "source_input_mode" not in start_message

        websocket.send_json(frame(1, 24000))
        for sequence in range(2, 41):
            websocket.send_json(frame(sequence, 0))

        messages = []
        for _ in range(80):
            message = websocket.receive_json()
            messages.append(message)
            if message["type"] == "triage.case.created":
                break

    event_types = [
        message["event"]["event_type"]
        for message in messages
        if message["type"] == "debug.event"
    ]
    case_messages = [message for message in messages if message["type"] == "triage.case.created"]
    turn_events = [
        message["event"]
        for message in messages
        if message["type"] == "debug.event" and message["event"]["event_type"] == "turn.committed"
    ]

    assert "audio.frame.received" in event_types
    assert "vad.speech.start" in event_types
    assert "vad.speech.end" in event_types
    assert "turn.committed" in event_types
    assert "ai.request.started" in event_types
    assert case_messages
    case_message = case_messages[0]
    assert case_message["provider_mode"] == "mock"
    assert case_message["transcript_source"] == "mock"
    assert "source_input_mode" not in case_message
    assert "call_metadata" not in case_message
    assert case_message["warnings"] == []
    assert case_message["transcript"]
    assert case_message["record"]["case"]["triage_level"] == "RED"
    assert case_message["audio_ref"]
    assert Path(case_message["audio_ref"]).exists()
    assert turn_events
    assert turn_events[0]["metadata"]["audio_ref"] == case_message["audio_ref"]
    assert turn_events[0]["metadata"]["audio_debug_id"]

    with wave.open(case_message["audio_ref"], "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() > 0

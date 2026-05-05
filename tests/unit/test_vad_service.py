from __future__ import annotations

import base64

from app.models.audio import AudioDebugEventType, AudioFrame, VadState
from app.services.turn_manager import TurnManager
from app.services.vad_service import EnergyVadService


def pcm_frame(sequence: int, amplitude: int, assistant_is_speaking: bool = False) -> AudioFrame:
    payload = b"".join(int(amplitude).to_bytes(2, "little", signed=True) for _ in range(320))
    return AudioFrame(
        session_id="session_1",
        sequence=sequence,
        timestamp_ms=sequence * 20,
        audio_base64=base64.b64encode(payload).decode("ascii"),
        assistant_is_speaking=assistant_is_speaking,
    )


def test_energy_vad_classifies_silence_and_speech() -> None:
    vad = EnergyVadService(threshold=0.02)

    assert vad.is_speech(pcm_frame(1, 0)) is False
    assert vad.is_speech(pcm_frame(2, 24000)) is True


def test_energy_vad_uses_configurable_threshold() -> None:
    frame = pcm_frame(1, 600)

    assert EnergyVadService(threshold=0.01).is_speech(frame) is True
    assert EnergyVadService(threshold=0.03).is_speech(frame) is False


def test_turn_manager_emits_speech_start_and_commit_after_threshold() -> None:
    manager = TurnManager(vad=EnergyVadService(threshold=0.02), silence_threshold_ms=600, pre_speech_padding_ms=200)
    events = []

    events.extend(manager.process_frame(pcm_frame(1, 24000)).events)
    committed = None
    for sequence in range(2, 32):
        result = manager.process_frame(pcm_frame(sequence, 0))
        events.extend(result.events)
        committed = result.committed_turn or committed

    event_types = [event.event_type for event in events]

    assert AudioDebugEventType.VAD_SPEECH_START in event_types
    assert AudioDebugEventType.VAD_SPEECH_END in event_types
    assert AudioDebugEventType.TURN_COMMITTED in event_types
    assert committed is not None
    assert committed.silence_threshold_ms == 600
    assert committed.pre_speech_padding_ms == 200
    assert manager.state == VadState.THINKING


def test_turn_manager_discards_short_speech_below_minimum() -> None:
    manager = TurnManager(
        vad=EnergyVadService(threshold=0.02),
        silence_threshold_ms=60,
        pre_speech_padding_ms=200,
        min_speech_ms=300,
    )

    manager.process_frame(pcm_frame(1, 24000))
    committed = None
    events = []
    for sequence in range(2, 6):
        result = manager.process_frame(pcm_frame(sequence, 0))
        events.extend(result.events)
        committed = committed or result.committed_turn

    assert committed is None
    assert any(event.metadata.get("discarded_short_speech") for event in events)
    assert manager.state == VadState.SILENCE


def test_barge_in_detected_while_assistant_is_speaking() -> None:
    manager = TurnManager(vad=EnergyVadService(threshold=0.02))
    manager.set_speaking(True)

    result = manager.process_frame(pcm_frame(1, 25000, assistant_is_speaking=True))

    assert AudioDebugEventType.BARGE_IN_DETECTED in [event.event_type for event in result.events]

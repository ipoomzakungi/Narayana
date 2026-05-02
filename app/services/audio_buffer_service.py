from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import wave

from app.models.audio import AudioFrame, CallerTurn
from app.services.audio_frame_service import decode_pcm16


class AudioBufferError(RuntimeError):
    pass


@dataclass(frozen=True)
class BufferedAudioFrame:
    payload: bytes
    sample_rate_hz: int
    channels: int
    duration_ms: int
    sequence: int


@dataclass
class SessionAudioBuffer:
    pre_frames: deque[BufferedAudioFrame]
    active_frames: list[BufferedAudioFrame] = field(default_factory=list)
    active: bool = False


@dataclass(frozen=True)
class AudioWriteResult:
    audio_ref: str
    audio_debug_id: str
    frame_count: int
    sample_rate_hz: int
    duration_ms: int


class AudioBufferService:
    def __init__(self, root_path: str = ".data/audio", pre_speech_padding_ms: int = 200, frame_ms: int = 20) -> None:
        self.root_path = Path(root_path)
        self.pre_speech_padding_ms = pre_speech_padding_ms
        self.frame_ms = frame_ms
        self._pre_frame_limit = max(1, pre_speech_padding_ms // frame_ms)
        self._sessions: dict[str, SessionAudioBuffer] = {}

    def observe_frame(self, frame: AudioFrame, speech_started: bool = False) -> None:
        buffered = BufferedAudioFrame(
            payload=decode_pcm16(frame),
            sample_rate_hz=frame.sample_rate_hz,
            channels=frame.channels,
            duration_ms=frame.duration_ms,
            sequence=frame.sequence,
        )
        session = self._session(frame.session_id)

        if speech_started and not session.active:
            session.active = True
            session.active_frames = list(session.pre_frames)
            session.pre_frames.clear()

        if session.active:
            session.active_frames.append(buffered)
            return

        session.pre_frames.append(buffered)

    def write_committed_turn(self, turn: CallerTurn) -> AudioWriteResult:
        session = self._session(turn.session_id)
        if not session.active_frames:
            raise AudioBufferError(f"No audio frames buffered for committed turn {turn.turn_id}.")

        frames = list(session.active_frames)
        self._validate_frames(frames)
        sample_rate_hz = frames[0].sample_rate_hz
        output_path = self.root_path / turn.session_id / f"{turn.turn_id}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate_hz)
            wav_file.writeframes(b"".join(frame.payload for frame in frames))

        duration_ms = sum(frame.duration_ms for frame in frames)
        session.active = False
        session.active_frames = []
        session.pre_frames.clear()
        return AudioWriteResult(
            audio_ref=str(output_path),
            audio_debug_id=turn.turn_id,
            frame_count=len(frames),
            sample_rate_hz=sample_rate_hz,
            duration_ms=duration_ms,
        )

    def _session(self, session_id: str) -> SessionAudioBuffer:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionAudioBuffer(pre_frames=deque(maxlen=self._pre_frame_limit))
        return self._sessions[session_id]

    @staticmethod
    def _validate_frames(frames: list[BufferedAudioFrame]) -> None:
        sample_rate_hz = frames[0].sample_rate_hz
        for frame in frames:
            if frame.channels != 1:
                raise AudioBufferError("Only mono PCM16 frames can be written to V1 WAV artifacts.")
            if frame.sample_rate_hz != sample_rate_hz:
                raise AudioBufferError("Cannot write a WAV artifact from mixed sample rates.")
            if len(frame.payload) % 2 != 0:
                raise AudioBufferError("PCM16 frame payload must contain an even number of bytes.")

from __future__ import annotations

import math

from app.models.audio import AudioFrame
from app.services.audio_frame_service import decode_pcm16, pcm16_samples


class EnergyVadService:
    def __init__(self, threshold: float = 0.02) -> None:
        self.threshold = threshold

    def score(self, frame: AudioFrame) -> float:
        payload = decode_pcm16(frame)
        samples = pcm16_samples(payload)
        if not samples:
            return 0.0
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        return rms / 32768.0

    def is_speech(self, frame: AudioFrame) -> bool:
        return self.score(frame) >= self.threshold

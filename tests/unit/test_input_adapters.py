from __future__ import annotations

import pytest

from app.models.audio import InputMode
from app.services.audio_frame_service import ACSAudioStreamAdapter, LocalMicAdapter, TwilioMediaStreamAdapter


def test_local_mic_adapter_is_enabled_v0_path() -> None:
    adapter = LocalMicAdapter()

    assert adapter.enabled is True
    assert adapter.input_mode == InputMode.LOCAL_MIC


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter", [TwilioMediaStreamAdapter(), ACSAudioStreamAdapter()])
async def test_phone_adapters_are_disabled_placeholders(adapter) -> None:
    assert adapter.enabled is False

    with pytest.raises(NotImplementedError):
        async for _ in adapter.frames():
            pass

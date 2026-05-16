from __future__ import annotations

import asyncio
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any

import websockets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=False)

from app.core.config import Settings
from app.services.realtime_voice_provider import (
    auth_headers,
    build_openai_realtime_session_update,
    build_openai_realtime_uri,
    build_voice_live_uri,
)


INSTRUCTIONS = "Say one short Thai greeting for a crisis intake test."
PREVIEW_API_VERSION = "2025-04-01-preview"
VOICE_LIVE_API_VERSION = "2025-10-01"


class CheckError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise CheckError(f"Missing required environment variable: {name}")
    return value


def _base_settings(*, api_version: str | None = None) -> Settings:
    return Settings(
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_endpoint=_required_env("AZURE_REALTIME_ENDPOINT"),
        azure_realtime_api_key=_required_env("AZURE_REALTIME_API_KEY"),
        azure_realtime_deployment=_required_env("AZURE_REALTIME_DEPLOYMENT"),
        azure_realtime_api_version=api_version or _required_env("AZURE_REALTIME_API_VERSION"),
        realtime_input_audio_format="g711_ulaw",
        realtime_twilio_audio_passthrough=True,
        azure_speech_voice=os.getenv("AZURE_SPEECH_VOICE", "th-TH-PremwadeeNeural"),
    )


def _voice_live_settings() -> Settings:
    endpoint = _required_env("AZURE_REALTIME_ENDPOINT").rstrip("/")
    return Settings(
        enable_realtime_voice=True,
        realtime_provider="azure_voice_live",
        azure_realtime_api_key=_required_env("AZURE_REALTIME_API_KEY"),
        azure_voice_live_endpoint=f"{endpoint}/voice-live/realtime?api-version={VOICE_LIVE_API_VERSION}",
        azure_voice_live_model=_required_env("AZURE_REALTIME_DEPLOYMENT"),
        realtime_input_audio_format="g711_ulaw",
        realtime_twilio_audio_passthrough=True,
        azure_speech_voice=os.getenv("AZURE_SPEECH_VOICE", "th-TH-PremwadeeNeural"),
    )


def _status_code(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None) or getattr(response, "status", None)
    return int(status) if isinstance(status, int) else None


def _safe_error(exc: BaseException) -> str:
    status = _status_code(exc)
    name = type(exc).__name__
    if status:
        return f"{name} HTTP {status}"
    return name


async def _try_connect(label: str, uri: str, settings: Settings, payload: dict[str, Any]) -> tuple[bool, int | None]:
    print(f"Trying {label}: {uri}")
    header_arg = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
    try:
        async with websockets.connect(
            uri,
            **{header_arg: auth_headers(settings)},
            open_timeout=10,
            close_timeout=5,
            max_size=2**20,
        ) as websocket:
            await websocket.send(json.dumps(payload))
            event_types: list[str] = []
            deadline = asyncio.get_running_loop().time() + 6
            while asyncio.get_running_loop().time() < deadline:
                timeout = max(0.1, deadline - asyncio.get_running_loop().time())
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    event_types.append("non_json")
                    continue
                event_type = str(message.get("type") or "missing_type")
                event_types.append(event_type)
                if event_type in {"session.created", "session.updated", "response.created", "error"}:
                    break
            print(f"SUCCESS {label}: connected; events={event_types or ['none_before_timeout']}")
            return True, None
    except Exception as exc:
        status = _status_code(exc)
        print(f"FAILED {label}: {_safe_error(exc)}")
        return False, status


async def main() -> int:
    try:
        settings = _base_settings()
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    payload = build_openai_realtime_session_update(settings, INSTRUCTIONS)
    ok, status = await _try_connect("openai-v1", build_openai_realtime_uri(settings), settings, payload)
    if ok:
        return 0
    if status == 401:
        print("Authentication failed with 401. Rotate/regenerate the key and retry.", file=sys.stderr)
        return 1
    if status and status != 404:
        return 1

    preview = _base_settings(api_version=PREVIEW_API_VERSION)
    preview_payload = build_openai_realtime_session_update(preview, INSTRUCTIONS)
    ok, status = await _try_connect("openai-preview", build_openai_realtime_uri(preview), preview, preview_payload)
    if ok:
        return 0
    if status == 401:
        print("Authentication failed with 401. Rotate/regenerate the key and retry.", file=sys.stderr)
        return 1
    if status and status != 404:
        return 1

    voice_live = _voice_live_settings()
    voice_payload = {
        "type": "session.update",
        "session": {
            "instructions": INSTRUCTIONS,
            "turn_detection": {"type": "azure_semantic_vad", "silence_duration_ms": 500},
            "input_audio_format": voice_live.effective_realtime_input_audio_format,
            "output_audio_format": "g711_ulaw",
            "voice": {"name": voice_live.azure_speech_voice, "type": "azure-standard"},
        },
    }
    ok, _ = await _try_connect("voice-live", build_voice_live_uri(voice_live), voice_live, voice_payload)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

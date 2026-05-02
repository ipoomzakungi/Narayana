from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import os
import sys
from typing import Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError

try:
    from scripts.check_public_webhook import ToolingError, normalize_base_url
except ImportError:  # pragma: no cover - direct script execution from scripts/
    from check_public_webhook import ToolingError, normalize_base_url


REQUIRED_ENV = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "TWILIO_OUTBOUND_TO",
    "TWILIO_WEBHOOK_PUBLIC_BASE_URL",
)


@dataclass(frozen=True)
class TwilioCallConfig:
    account_sid: str
    auth_token: str
    from_number: str
    to_number: str
    webhook_base_url: str


def config_from_env(env: Mapping[str, str] | None = None) -> TwilioCallConfig:
    values = env or os.environ
    missing = [name for name in REQUIRED_ENV if not values.get(name, "").strip()]
    if missing:
        raise ToolingError("Missing required Twilio call values: " + ", ".join(missing))
    return TwilioCallConfig(
        account_sid=values["TWILIO_ACCOUNT_SID"].strip(),
        auth_token=values["TWILIO_AUTH_TOKEN"].strip(),
        from_number=values["TWILIO_PHONE_NUMBER"].strip(),
        to_number=values["TWILIO_OUTBOUND_TO"].strip(),
        webhook_base_url=normalize_base_url(values["TWILIO_WEBHOOK_PUBLIC_BASE_URL"]),
    )


def build_webhook_url(base_url: str) -> str:
    return f"{normalize_base_url(base_url)}/api/telephony/twilio/incoming-call"


def build_twilio_call_request(config: TwilioCallConfig) -> request.Request:
    api_url = f"https://api.twilio.com/2010-04-01/Accounts/{parse.quote(config.account_sid)}/Calls.json"
    body = parse.urlencode(
        {
            "From": config.from_number,
            "To": config.to_number,
            "Url": build_webhook_url(config.webhook_base_url),
        }
    ).encode("utf-8")
    token = base64.b64encode(f"{config.account_sid}:{config.auth_token}".encode("utf-8")).decode("ascii")
    return request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )


def create_outbound_call(config: TwilioCallConfig, opener=request.urlopen) -> str:
    twilio_request = build_twilio_call_request(config)
    try:
        with opener(twilio_request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ToolingError(
            "Twilio call request failed. Check verified caller ID for trial accounts, "
            f"Thailand Voice Geo Permissions, balance, and destination format. Response: {body}"
        ) from exc
    except URLError as exc:
        raise ToolingError(f"Could not reach Twilio REST API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ToolingError("Twilio response was not valid JSON.") from exc

    sid = payload.get("sid")
    if not sid:
        raise ToolingError(f"Twilio response did not include a call SID: {payload}")
    return str(sid)


def main() -> int:
    try:
        config = config_from_env()
        call_sid = create_outbound_call(config)
    except ToolingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Twilio outbound call created: {call_sid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

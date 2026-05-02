from __future__ import annotations

from dataclasses import dataclass, field
import os
import sys
from typing import Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET


FAKE_CALL_SID = "CA_TEST"
TWILIO_TEST_NUMBER = "+16082005400"


class ToolingError(RuntimeError):
    pass


@dataclass(frozen=True)
class EndpointUrls:
    base_url: str
    health_url: str
    twilio_webhook_url: str


@dataclass
class WebhookCheckResult:
    health_ok: bool = False
    twiml_ok: bool = False
    health_status: int | None = None
    twiml_status: int | None = None
    messages: list[str] = field(default_factory=list)


def normalize_base_url(value: str | None, name: str = "TWILIO_WEBHOOK_PUBLIC_BASE_URL") -> str:
    cleaned = (value or "").strip().rstrip("/")
    if not cleaned:
        raise ToolingError(f"Missing required public backend URL: {name}.")
    parsed = parse.urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ToolingError(f"{name} must be an http(s) URL, for example https://narayana-api.example.com.")
    return cleaned


def base_url_from_env(env: Mapping[str, str] | None = None) -> str:
    values = env or os.environ
    value = values.get("TWILIO_WEBHOOK_PUBLIC_BASE_URL") or values.get("AZURE_CONTAINER_APP_URL")
    name = "TWILIO_WEBHOOK_PUBLIC_BASE_URL or AZURE_CONTAINER_APP_URL"
    return normalize_base_url(value, name)


def endpoint_urls(base_url: str) -> EndpointUrls:
    normalized = normalize_base_url(base_url)
    return EndpointUrls(
        base_url=normalized,
        health_url=f"{normalized}/api/health/azure",
        twilio_webhook_url=f"{normalized}/api/telephony/twilio/incoming-call",
    )


def fake_twilio_payload() -> bytes:
    return parse.urlencode(
        {
            "CallSid": FAKE_CALL_SID,
            "From": "+15550000000",
            "To": TWILIO_TEST_NUMBER,
            "FromCountry": "US",
        }
    ).encode("utf-8")


def twiml_has_media_stream(xml_text: str, call_sid: str = FAKE_CALL_SID) -> bool:
    expected_path = f"/ws/telephony/twilio/{call_sid}"
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return False
    for element in root.iter():
        if element.tag.endswith("Stream") and expected_path in element.attrib.get("url", ""):
            return True
    return False


def _read_text(target: request.Request, opener=request.urlopen, timeout: int = 10) -> tuple[int, str]:
    try:
        with opener(target, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            return int(status), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ToolingError(f"HTTP {exc.code} from {target.full_url}: {body}") from exc
    except URLError as exc:
        raise ToolingError(f"Could not reach {target.full_url}: {exc.reason}") from exc


def run_check(env: Mapping[str, str] | None = None, opener=request.urlopen) -> WebhookCheckResult:
    urls = endpoint_urls(base_url_from_env(env))
    result = WebhookCheckResult()

    health_request = request.Request(urls.health_url, method="GET")
    result.health_status, health_body = _read_text(health_request, opener=opener)
    result.health_ok = 200 <= result.health_status < 300
    if not result.health_ok:
        raise ToolingError(f"Health check failed with HTTP {result.health_status}: {health_body}")
    result.messages.append(f"Health OK: {urls.health_url}")

    twilio_request = request.Request(
        urls.twilio_webhook_url,
        data=fake_twilio_payload(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    result.twiml_status, twiml_body = _read_text(twilio_request, opener=opener)
    result.twiml_ok = 200 <= result.twiml_status < 300 and twiml_has_media_stream(twiml_body)
    if not result.twiml_ok:
        raise ToolingError(
            "Fake Twilio webhook did not return TwiML containing "
            f"/ws/telephony/twilio/{FAKE_CALL_SID}."
        )
    result.messages.append(f"TwiML OK: {urls.twilio_webhook_url}")
    return result


def main() -> int:
    try:
        result = run_check()
    except ToolingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for message in result.messages:
        print(message)
    print("Public webhook check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

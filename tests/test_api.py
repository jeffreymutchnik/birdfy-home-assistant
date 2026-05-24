"""Tests for the standalone Birdfy API client."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest

import pybirdfy.client as birdfy_client_module
from pybirdfy.client import (
    API2_BASE_URL,
    EVENT_BIRD,
    EVENT_CLIP_READY,
    EVENT_MOTION,
    EVENT_SPECIES,
    BirdfyAuthError,
    BirdfyClient,
    BirdfyDevice,
    BirdfyEvent,
    BirdfyRateLimitError,
    BirdfyTokens,
    _signature,
    redact_data,
)

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    """Minimal aiohttp-like response."""

    def __init__(self, payload, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    async def text(self):
        return json.dumps(self.payload)

    async def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode()


class FakeSession:
    """Route requests to fixture responses."""

    def __init__(self) -> None:
        self.calls = []
        self.refresh_count = 0

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("users/login/v2"):
            return FakeResponse(_fixture("login.json"))
        if url.endswith("auth/refreshtoken"):
            self.refresh_count += 1
            return FakeResponse({"token": "new-token", "refreshToken": "new-refresh"})
        if url.endswith("devices/v3"):
            if self.refresh_count == 0 and len([call for call in self.calls if call[1].endswith("devices/v3")]) == 1:
                return FakeResponse({"ret": 10005, "msg": "expired"})
            return FakeResponse(_fixture("devices.json"))
        if url.endswith("/services"):
            return FakeResponse({"sdCard": True})
        if url.endswith("/play"):
            return FakeResponse({"streamUrl": "rtsp://example.invalid/live"})
        if url.endswith("events"):
            return FakeResponse(_fixture("events.json"))
        if url.endswith(".jpg"):
            return FakeResponse(b"image")
        return FakeResponse({"ret": 404, "msg": "not found"}, status=404)


class ServiceFailureSession(FakeSession):
    """Fixture session that fails optional service metadata calls."""

    def request(self, method, url, **kwargs):
        if url.endswith("/services"):
            self.calls.append((method, url, kwargs))
            return FakeResponse({"ret": 500, "msg": "boom"}, status=500)
        return super().request(method, url, **kwargs)


class WebRtcOnlyStreamSession(FakeSession):
    """Fixture session that returns stream metadata without a direct media URL."""

    def request(self, method, url, **kwargs):
        if url.endswith("/play"):
            self.calls.append((method, url, kwargs))
            return FakeResponse({"kinesis": {"channelARN": "arn:aws:kinesisvideo:example"}})
        return super().request(method, url, **kwargs)


class RateLimitSession(FakeSession):
    """Fixture session that returns a rate limit response."""

    def request(self, method, url, **kwargs):
        if url.endswith("devices/v3"):
            self.calls.append((method, url, kwargs))
            return FakeResponse({"ret": 0, "msg": "too many requests"}, status=429)
        return super().request(method, url, **kwargs)


class RetryOnceSession(FakeSession):
    """Fixture session that has a transient transport failure."""

    def __init__(self) -> None:
        super().__init__()
        self.failures = 0

    def request(self, method, url, **kwargs):
        if url.endswith("devices/v3") and self.failures == 0:
            self.failures += 1
            self.calls.append((method, url, kwargs))
            raise OSError("temporary network failure")
        return super().request(method, url, **kwargs)


def _fixture(filename: str):
    return json.loads((FIXTURES / filename).read_text())


def test_home_assistant_runtime_client_is_synced() -> None:
    """HACS installs custom_components only, so keep the vendored client synced."""
    root = FIXTURES.parents[1]
    assert (root / "custom_components" / "birdfy" / "api.py").read_text() == (
        root / "pybirdfy" / "client.py"
    ).read_text()


def test_login_hashes_password_and_stores_tokens() -> None:
    asyncio.run(_test_login_hashes_password_and_stores_tokens())


async def _test_login_hashes_password_and_stores_tokens() -> None:
    session = FakeSession()
    client = BirdfyClient(session, base_url="http://127.0.0.1/v1/", request_interval=0)

    tokens = await client.login("fixture-user@example.invalid", "test-password")

    assert tokens.user_id == "123456"
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "http://127.0.0.1/v1/users/login/v2"
    assert kwargs["json"]["password"] != "test-password"
    assert len(kwargs["json"]["password"]) == 32


def test_list_devices_refreshes_expired_token() -> None:
    asyncio.run(_test_list_devices_refreshes_expired_token())


async def _test_list_devices_refreshes_expired_token() -> None:
    session = FakeSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(
            token="old-token",
            refresh_token="old-refresh",
            user_id="123456",
            username="fixture-user@example.invalid",
        ),
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
    )

    devices = await client.list_devices(include_services=True)

    assert session.refresh_count == 1
    assert client.tokens.token == "new-token"
    assert devices[0].name == "Backyard Birdfy"
    assert devices[0].battery_level == 87
    assert devices[0].capabilities.supports_snapshot is True
    assert devices[0].services["sdCard"] is True


def test_token_update_callback_runs_after_login_and_refresh() -> None:
    asyncio.run(_test_token_update_callback_runs_after_login_and_refresh())


async def _test_token_update_callback_runs_after_login_and_refresh() -> None:
    seen: list[str] = []

    async def store_tokens(tokens: BirdfyTokens) -> None:
        seen.append(tokens.token)

    session = FakeSession()
    client = BirdfyClient(
        session,
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
        token_update_callback=store_tokens,
    )

    await client.login("fixture-user@example.invalid", "test-password")
    await client.refresh_tokens()

    assert seen == ["REDACTED_TEST_ACCESS_VALUE", "new-token"]


def test_stream_source_returns_direct_urls_only() -> None:
    asyncio.run(_test_stream_source_returns_direct_urls_only())


async def _test_stream_source_returns_direct_urls_only() -> None:
    session = FakeSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456", region="us"),
        base_url="http://127.0.0.1/v1/",
        api2_base_url=API2_BASE_URL,
        request_interval=0,
    )
    device = (await client.list_devices())[0]

    stream = await client.get_stream_source(device)

    assert stream == "rtsp://example.invalid/live"


def test_stream_source_ignores_webrtc_only_payloads() -> None:
    asyncio.run(_test_stream_source_ignores_webrtc_only_payloads())


async def _test_stream_source_ignores_webrtc_only_payloads() -> None:
    session = WebRtcOnlyStreamSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456", region="us"),
        base_url="http://127.0.0.1/v1/",
        api2_base_url=API2_BASE_URL,
        request_interval=0,
    )
    device = (await client.list_devices())[0]

    assert await client.get_stream_source(device) is None


def test_rate_limit_error_is_explicit() -> None:
    asyncio.run(_test_rate_limit_error_is_explicit())


async def _test_rate_limit_error_is_explicit() -> None:
    client = BirdfyClient(
        RateLimitSession(),
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456"),
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
    )

    with pytest.raises(BirdfyRateLimitError):
        await client.list_devices()


def test_transient_connection_errors_are_retried(monkeypatch) -> None:
    asyncio.run(_test_transient_connection_errors_are_retried(monkeypatch))


async def _test_transient_connection_errors_are_retried(monkeypatch) -> None:
    async def fast_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(birdfy_client_module.asyncio, "sleep", fast_sleep)
    session = RetryOnceSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456"),
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
    )

    devices = await client.list_devices()

    assert session.failures == 1
    assert devices[0].identifier == "SIMULATED_DEVICE_001"


def test_service_metadata_errors_do_not_log_serials(caplog) -> None:
    asyncio.run(_test_service_metadata_errors_do_not_log_serials(caplog))


async def _test_service_metadata_errors_do_not_log_serials(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="pybirdfy.client")
    session = ServiceFailureSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456"),
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
    )

    devices = await client.list_devices(include_services=True)

    assert devices[0].services == {}
    assert "Unable to load service metadata" in caplog.text
    assert "SIMULATED_DEVICE_001" not in caplog.text


def test_simulator_events_are_parsed() -> None:
    asyncio.run(_test_simulator_events_are_parsed())


async def _test_simulator_events_are_parsed() -> None:
    session = FakeSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456"),
        base_url="http://127.0.0.1/v1/",
        request_interval=0,
    )

    events = await client.list_events()

    assert events[0].species == "Northern Cardinal"
    assert events[0].event_type == "species_recognized"


def test_remote_cloud_events_are_disabled_until_validated() -> None:
    asyncio.run(_test_remote_cloud_events_are_disabled_until_validated())


async def _test_remote_cloud_events_are_disabled_until_validated() -> None:
    session = FakeSession()
    client = BirdfyClient(
        session,
        tokens=BirdfyTokens(token="token", refresh_token="refresh", user_id="123456"),
        base_url="https://localweb.nvts.co/v1/",
        request_interval=0,
    )

    assert await client.list_events() == []
    assert session.calls == []


def test_signature_is_stable() -> None:
    assert _signature("token", "ucid", "udid", "123", "456") == (
        "c71c095d2698dda72ce55fed903bd63d9bacb89fcccbb76b48fdaff83a046b56"
    )


def test_redact_data_removes_sensitive_values() -> None:
    redacted = redact_data(
        {
            "token": "secret",
            "devices": [{"serial_number": "SIMULATED_DEVICE_001", "name": "Backyard"}],
            "nested": {"image_url": "https://example.invalid/image.jpg"},
        }
    )

    assert redacted["token"] == "**REDACTED**"
    assert redacted["devices"][0]["serial_number"] == "**REDACTED**"
    assert redacted["devices"][0]["name"] == "Backyard"
    assert redacted["nested"]["image_url"] == "**REDACTED**"


def test_redact_data_handles_camel_case_sensitive_keys() -> None:
    redacted = redact_data(
        {
            "refreshToken": "secret-refresh",
            "serialNumber": "SIMULATED_DEVICE_001",
            "snapshotUrl": "https://example.invalid/snapshot.jpg",
            "clipUrl": "https://example.invalid/clip.mp4",
            "userID": "123456",
            "displayName": "Backyard",
        }
    )

    assert redacted == {
        "refreshToken": "**REDACTED**",
        "serialNumber": "**REDACTED**",
        "snapshotUrl": "**REDACTED**",
        "clipUrl": "**REDACTED**",
        "userID": "**REDACTED**",
        "displayName": "Backyard",
    }


def test_device_parser_accepts_percentage_strings() -> None:
    device = BirdfyDevice.from_api(
        {
            "serialNumber": "SIMULATED_DEVICE_001",
            "modelName": "Birdfy",
            "onlineStatus": "online",
            "batteryPercent": "87%",
            "wifiSignal": "71 %",
        }
    )

    assert device.online is True
    assert device.battery_level == 87
    assert device.signal_level == 71


def test_event_parser_normalizes_common_event_aliases() -> None:
    assert BirdfyEvent.from_api({"eventType": "motion"}).event_type == EVENT_MOTION
    assert BirdfyEvent.from_api({"eventType": "bird"}).event_type == EVENT_BIRD
    assert BirdfyEvent.from_api({"eventType": "recognition"}).event_type == EVENT_SPECIES
    assert BirdfyEvent.from_api({"eventType": "clip"}).event_type == EVENT_CLIP_READY
    assert BirdfyEvent.from_api({"birdName": "Blue Jay"}).event_type == EVENT_SPECIES
    assert (
        BirdfyEvent.from_api({"videoUrl": "https://example.invalid/clip.mp4"}).event_type
        == EVENT_CLIP_READY
    )


def test_auth_error_without_tokens() -> None:
    asyncio.run(_test_auth_error_without_tokens())


async def _test_auth_error_without_tokens() -> None:
    client = BirdfyClient(FakeSession(), request_interval=0)

    try:
        await client.list_devices()
    except BirdfyAuthError:
        return
    raise AssertionError("Expected BirdfyAuthError")

"""Async Birdfy / Netvue web API client.

This module intentionally has no Home Assistant imports. The API surface is based
on the public Netvue web application and should be treated as unofficial.
"""

from __future__ import annotations

import asyncio
import hmac
import inspect
import json
import logging
import re
import secrets
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import md5
from typing import Any
from urllib.parse import urljoin

LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://localweb.nvts.co/v1/"
API2_BASE_URL = "https://api2.nvts.co/"
CAPI2_BASE_URL = "https://capi2.nvts.co/"
CAPIV3_BASE_URL = "https://capiv3.nvts.co/"

DEFAULT_UCID = "41f33045b1"
SIGNATURE_VERSION = '{"signature":2}'

EVENT_MOTION = "motion_detected"
EVENT_BIRD = "bird_detected"
EVENT_SPECIES = "species_recognized"
EVENT_CLIP_READY = "clip_ready"

EVENT_TYPE_ALIASES = {
    "ai": EVENT_SPECIES,
    "aispecies": EVENT_SPECIES,
    "bird": EVENT_BIRD,
    "birddetected": EVENT_BIRD,
    "birdrecognition": EVENT_SPECIES,
    "clip": EVENT_CLIP_READY,
    "clipready": EVENT_CLIP_READY,
    "media": EVENT_CLIP_READY,
    "md": EVENT_MOTION,
    "motion": EVENT_MOTION,
    "motiondetected": EVENT_MOTION,
    "moment": EVENT_CLIP_READY,
    "pir": EVENT_MOTION,
    "recognition": EVENT_SPECIES,
    "species": EVENT_SPECIES,
    "speciesrecognized": EVENT_SPECIES,
    "video": EVENT_CLIP_READY,
}

AUTH_RET_CODES = {
    10005,  # token expired, observed in Netvue web client enum handling
    10006,  # refresh token expired
    10007,  # refresh token mismatch
    10008,  # signature invalid
}

SENSITIVE_KEYS = {
    "access_key",
    "access_key_id",
    "authorization",
    "device_id",
    "email",
    "image_url",
    "local_endpoint",
    "password",
    "refresh_token",
    "secret",
    "secret_access_key",
    "serial",
    "serial_number",
    "session_token",
    "snapshot",
    "snapshot_url",
    "stream",
    "stream_url",
    "token",
    "url",
    "user_id",
    "username",
}

SENSITIVE_KEYS_NORMALIZED = {
    *(key.replace("_", "").replace("-", "").lower() for key in SENSITIVE_KEYS),
    "accesstoken",
    "apikey",
    "clipurl",
    "deviceid",
    "imageurl",
    "mediaurl",
    "refreshtoken",
    "serialnumber",
    "streamurl",
    "snapshoturl",
    "userid",
    "videourl",
}


class BirdfyError(Exception):
    """Base exception for Birdfy API failures."""


class BirdfyAuthError(BirdfyError):
    """Authentication failed or credentials expired."""


class BirdfyRateLimitError(BirdfyError):
    """The remote API rejected the request due to rate limiting."""


class BirdfyUnsupportedError(BirdfyError):
    """The requested feature is not exposed by the currently supported API."""


class BirdfyConnectionError(BirdfyError):
    """The remote API could not be reached."""


class BirdfyApiError(BirdfyError):
    """The remote API returned an error response."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: int | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.operation = operation


@dataclass(slots=True)
class BirdfyTokens:
    """Account tokens returned by Netvue/Birdfy."""

    token: str
    refresh_token: str
    user_id: str
    username: str | None = None
    region: str | None = None
    local_endpoint: str | None = None
    icon_bucket: str | None = None
    icon: str | None = None
    nickname: str | None = None

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> BirdfyTokens:
        """Build tokens from a login/refresh payload."""
        token = _as_str(_first(payload, "token", "accessToken"))
        refresh = _as_str(_first(payload, "refreshToken", "refresh_token"))
        user_id = _as_str(_first(payload, "userID", "userId", "user_id", "id"))
        if not token or not refresh or not user_id:
            raise BirdfyAuthError("Login response did not include the expected token fields")
        return cls(
            token=token,
            refresh_token=refresh,
            user_id=user_id,
            username=_as_str(_first(payload, "userName", "username", "email")),
            region=_as_str(_first(payload, "region")),
            local_endpoint=_as_str(_first(payload, "localEndpoint")),
            icon_bucket=_as_str(_first(payload, "iconBucket")),
            icon=_as_str(_first(payload, "icon")),
            nickname=_as_str(_first(payload, "nickName", "nickname")),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BirdfyTokens:
        """Build tokens from stored config entry data."""
        return cls(
            token=str(payload["token"]),
            refresh_token=str(payload["refresh_token"]),
            user_id=str(payload["user_id"]),
            username=_as_str(payload.get("username")),
            region=_as_str(payload.get("region")),
            local_endpoint=_as_str(payload.get("local_endpoint")),
            icon_bucket=_as_str(payload.get("icon_bucket")),
            icon=_as_str(payload.get("icon")),
            nickname=_as_str(payload.get("nickname")),
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return JSON-serializable token data."""
        return {
            "token": self.token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "username": self.username,
            "region": self.region,
            "local_endpoint": self.local_endpoint,
            "icon_bucket": self.icon_bucket,
            "icon": self.icon,
            "nickname": self.nickname,
        }


@dataclass(frozen=True, slots=True)
class BirdfyCapabilities:
    """Device capability flags decoded from Netvue ability bitfields."""

    supports_video: bool = False
    supports_audio: bool = False
    supports_talk: bool = False
    supports_snapshot: bool = False
    supports_wifi: bool = False
    supports_night_light: bool = False
    supports_motion_detection: bool = False
    supports_local_storage: bool = False
    supports_two_way_audio: bool = False
    supports_motion_sensitivity: bool = False
    supports_motion_zone: bool = False
    supports_night_vision: bool = False
    supports_status_light: bool = False
    supports_motion_video: bool = False
    supports_cloud_human_detection: bool = False
    supports_rtsa_channel: bool = False
    supports_h264: bool = False
    supports_h265: bool = False
    supports_kvs_webrtc: bool = False
    supports_dual_sensor: bool = False
    raw_ability: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> BirdfyCapabilities:
        """Decode capability bit fields from a device payload."""
        raw = _parse_ability(payload.get("ability"))
        cn = _as_int(raw.get("CN")) or 0
        cn2 = _as_int(raw.get("CN2")) or 0
        vi = _as_int(raw.get("VI")) or 0
        return cls(
            supports_video=_has_bit(cn, 1),
            supports_audio=_has_bit(cn, 2),
            supports_talk=_has_bit(cn, 4),
            supports_snapshot=_has_bit(cn, 8),
            supports_wifi=_has_bit(cn, 32),
            supports_night_light=_has_bit(cn, 1024),
            supports_motion_detection=_has_bit(cn, 16384),
            supports_local_storage=_has_bit(cn, 1048576),
            supports_two_way_audio=_has_bit(cn, 16777216),
            supports_motion_sensitivity=_has_bit(cn2, 8),
            supports_motion_zone=_has_bit(cn2, 16),
            supports_night_vision=_has_bit(cn2, 8192),
            supports_status_light=_has_bit(cn2, 32768),
            supports_motion_video=_has_bit(cn2, 131072),
            supports_cloud_human_detection=_has_bit(cn2, 8388608),
            supports_rtsa_channel=_has_bit(cn2, 16777216),
            supports_h264=_has_bit(cn2, 67108864),
            supports_h265=_has_bit(cn2, 134217728),
            supports_kvs_webrtc=_has_bit(cn2, 268435456),
            supports_dual_sensor=_has_bit(vi, 2048),
            raw_ability=raw,
        )


@dataclass(frozen=True, slots=True)
class BirdfyDevice:
    """A Birdfy/Netvue device."""

    identifier: str
    serial_number: str
    name: str
    model: str | None
    manufacturer: str
    firmware: str | None
    online: bool | None
    battery_level: int | None
    signal_level: int | None
    snapshot_url: str | None
    region: str | None
    capabilities: BirdfyCapabilities
    raw: Mapping[str, Any]
    services: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(
        cls,
        payload: Mapping[str, Any],
        *,
        services: Mapping[str, Any] | None = None,
    ) -> BirdfyDevice:
        """Build a device model from the web API payload."""
        serial = _as_str(
            _first(payload, "serialNumber", "serial_number", "deviceSerial", "sn", "deviceId", "id")
        )
        if not serial:
            raise BirdfyApiError("Device payload did not include a serial number")
        model = _as_str(_first(payload, "modelName", "model", "modelKey", "productType", "deviceModel"))
        name = _as_str(_first(payload, "deviceName", "name", "nickName", "displayName")) or model or "Birdfy"
        manufacturer = _as_str(_first(payload, "manufacturer", "menufacturer", "brand")) or (
            "Birdfy" if "birdfy" in (model or "").lower() else "Netvue"
        )
        snapshot_url = _find_url(
            payload,
            (
                "snapshotUrl",
                "snapshotURL",
                "snapshot",
                "cover",
                "coverUrl",
                "image",
                "imageUrl",
                "thumbnail",
                "thumbnailUrl",
                "iconUrl",
                "avatarUrl",
            ),
        )
        return cls(
            identifier=serial,
            serial_number=serial,
            name=name,
            model=model,
            manufacturer=manufacturer,
            firmware=_as_str(_first(payload, "firmware", "firmwareVersion", "swVersion", "version")),
            online=_as_bool(_first(payload, "online", "isOnline", "onlineStatus", "status")),
            battery_level=_coerce_percent(_first(payload, "battery", "batteryLevel", "batteryPercent", "power")),
            signal_level=_coerce_percent(_first(payload, "wifi", "wifiSignal", "signal", "rssi", "signalLevel")),
            snapshot_url=snapshot_url,
            region=_as_str(_first(payload, "region")),
            capabilities=BirdfyCapabilities.from_payload(payload),
            raw=dict(payload),
            services=services or {},
        )

    def with_services(self, services: Mapping[str, Any]) -> BirdfyDevice:
        """Return the same device with service metadata attached."""
        return BirdfyDevice(
            identifier=self.identifier,
            serial_number=self.serial_number,
            name=self.name,
            model=self.model,
            manufacturer=self.manufacturer,
            firmware=self.firmware,
            online=self.online,
            battery_level=self.battery_level,
            signal_level=self.signal_level,
            snapshot_url=self.snapshot_url,
            region=self.region,
            capabilities=self.capabilities,
            raw=self.raw,
            services=services,
        )


@dataclass(frozen=True, slots=True)
class BirdfyEvent:
    """A motion/bird/media event."""

    event_id: str
    device_id: str
    event_type: str
    occurred_at: datetime | None = None
    species: str | None = None
    image_url: str | None = None
    clip_url: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> BirdfyEvent:
        """Build an event model from fixture or future API payloads."""
        event_id = _as_str(_first(payload, "eventId", "id", "uuid")) or secrets.token_hex(8)
        device_id = _as_str(_first(payload, "deviceId", "serialNumber", "serial_number", "sn")) or ""
        raw_event_type = _as_str(_first(payload, "eventType", "type", "kind"))
        species = _as_str(_first(payload, "species", "birdName", "bird_name", "aiName"))
        image_url = _find_url(payload, ("imageUrl", "image", "snapshotUrl", "thumbnailUrl"))
        clip_url = _find_url(payload, ("clipUrl", "videoUrl", "video", "mediaUrl"))
        return cls(
            event_id=event_id,
            device_id=device_id,
            event_type=_normalize_event_type(raw_event_type, species=species, clip_url=clip_url),
            occurred_at=_parse_datetime(_first(payload, "time", "timestamp", "createdAt", "created_at")),
            species=species,
            image_url=image_url,
            clip_url=clip_url,
            raw=dict(payload),
        )


TokenUpdateCallback = Callable[[BirdfyTokens], Awaitable[None] | None]


class BirdfyClient:
    """Async client for the public Netvue web API used by Birdfy."""

    def __init__(
        self,
        session: Any,
        *,
        tokens: BirdfyTokens | None = None,
        base_url: str = DEFAULT_BASE_URL,
        api2_base_url: str = API2_BASE_URL,
        capi2_base_url: str = CAPI2_BASE_URL,
        capiv3_base_url: str = CAPIV3_BASE_URL,
        ucid: str = DEFAULT_UCID,
        udid: str | None = None,
        request_interval: float = 0.25,
        timeout: int = 30,
        token_update_callback: TokenUpdateCallback | None = None,
    ) -> None:
        self._session = session
        self.tokens = tokens
        self.base_url = _ensure_slash(base_url)
        self.api2_base_url = _ensure_slash(api2_base_url)
        self.capi2_base_url = _ensure_slash(capi2_base_url)
        self.capiv3_base_url = _ensure_slash(capiv3_base_url)
        self.ucid = ucid
        self.udid = udid or secrets.token_hex(16)
        self.timeout = timeout
        self.token_update_callback = token_update_callback
        self._request_interval = request_interval
        self._last_request = 0.0
        self._rate_lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()

    @property
    def authenticated(self) -> bool:
        """Return whether a token is available."""
        return self.tokens is not None

    async def login(self, username: str, password: str, *, locale: str = "en") -> BirdfyTokens:
        """Authenticate with a Birdfy/Netvue account."""
        payload = await self._request(
            "post",
            self.base_url,
            "users/login/v2",
            data={
                "username": username.strip(),
                "password": md5(password.encode()).hexdigest(),
                "locale": locale,
                "platform": 0,
            },
            signed=False,
            operation="login",
        )
        if not isinstance(payload, Mapping):
            raise BirdfyAuthError("Unexpected login response")
        self.tokens = BirdfyTokens.from_api(payload)
        await self._notify_token_update()
        return self.tokens

    async def refresh_tokens(self) -> BirdfyTokens:
        """Refresh access tokens."""
        if self.tokens is None:
            raise BirdfyAuthError("Cannot refresh before login")
        async with self._refresh_lock:
            payload = await self._request(
                "post",
                self.base_url,
                "auth/refreshtoken",
                data={"token": self.tokens.token, "refreshToken": self.tokens.refresh_token},
                signed=True,
                allow_refresh=False,
                operation="token refresh",
            )
            if not isinstance(payload, Mapping):
                raise BirdfyAuthError("Unexpected token refresh response")
            refreshed = dict(self.tokens.as_dict())
            refreshed.update(payload)
            refreshed["refresh_token"] = payload.get("refreshToken", self.tokens.refresh_token)
            refreshed["user_id"] = self.tokens.user_id
            refreshed["username"] = self.tokens.username
            self.tokens = BirdfyTokens.from_dict(refreshed)
            await self._notify_token_update()
            return self.tokens

    async def list_devices(self, *, include_services: bool = False) -> list[BirdfyDevice]:
        """Return devices visible to the account."""
        payload = await self._request(
            "get",
            self.base_url,
            "devices/v3",
            signed=True,
            operation="device list",
        )
        devices_payload = _collection_payload(payload, "devices", "deviceList", "items", "list")
        if not isinstance(devices_payload, list):
            raise BirdfyApiError(
                f"Unexpected devices response for device list ({_payload_shape(payload)})",
                operation="device list",
            )

        devices = [BirdfyDevice.from_api(item) for item in devices_payload if isinstance(item, Mapping)]
        if not include_services:
            return devices

        enriched: list[BirdfyDevice] = []
        for device in devices:
            try:
                services = await self.get_device_services(device.serial_number)
            except BirdfyError as err:
                LOGGER.debug("Unable to load service metadata for a Birdfy device: %s", err)
                services = {}
            enriched.append(device.with_services(services))
        return enriched

    async def get_device_services(self, serial_number: str) -> Mapping[str, Any]:
        """Return cloud service/subscription metadata for a device."""
        payload = await self._request(
            "get",
            self.capi2_base_url,
            f"devices/{serial_number}/services",
            signed=True,
            operation="device services",
        )
        return payload if isinstance(payload, Mapping) else {"services": payload}

    async def get_stream_source(self, device: BirdfyDevice) -> str | None:
        """Return a direct stream URL if the web API exposes one.

        Netvue's web app can request a play session, but some models use AWS
        Kinesis WebRTC data rather than a direct ffmpeg-compatible URL. We only
        return URLs that Home Assistant can pass to ffmpeg directly.
        """
        payload = await self._request(
            "post",
            self._regional_api2_base_url(device.region),
            f"devices/{device.serial_number}/play",
            data={"serialNumber": device.serial_number, "deviceSerial": device.serial_number},
            signed=True,
            operation="stream source",
        )
        if not isinstance(payload, Mapping):
            return None
        return _find_url(
            payload,
            (
                "streamUrl",
                "streamURL",
                "rtsp",
                "rtspUrl",
                "hls",
                "hlsUrl",
                "playUrl",
                "url",
            ),
            allowed_schemes=("rtsp://", "rtsps://", "http://", "https://"),
        )

    async def get_public_stream(self, serial_number: str) -> Mapping[str, Any]:
        """Return raw pubstream payload for diagnostics/hardware validation."""
        payload = await self._request(
            "post",
            self.capiv3_base_url,
            "pubstream",
            params={"serialNumber": serial_number},
            signed=True,
            operation="public stream",
        )
        return payload if isinstance(payload, Mapping) else {"stream": payload}

    async def fetch_image(self, url: str) -> bytes | None:
        """Fetch image bytes from a URL returned by the API."""
        if not url:
            return None
        payload = await self._request_raw("get", url, signed=False)
        return payload

    async def list_events(self, *, since: datetime | None = None) -> list[BirdfyEvent]:
        """Return account events when running against a simulator.

        The public Netvue web client currently renders the device-events page as
        "stay tuned" and does not expose a documented event history endpoint.
        Production cloud calls therefore return an empty list; the simulator
        implements this endpoint so entity behavior can be tested without
        inventing vendor capabilities.
        """
        if "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            return []
        params: dict[str, str] = {}
        if since:
            params["since"] = since.isoformat()
        payload = await self._request(
            "get",
            self.base_url,
            "events",
            params=params,
            signed=True,
            operation="events",
        )
        events_payload = _collection_payload(payload, "events", "items", "list")
        if not isinstance(events_payload, list):
            return []
        return [BirdfyEvent.from_api(item) for item in events_payload if isinstance(item, Mapping)]

    def _regional_api2_base_url(self, region: str | None) -> str:
        if not region:
            region = self.tokens.region if self.tokens else None
        if not region:
            return self.api2_base_url
        return self.api2_base_url.replace("://", f"://{region}-")

    async def _request(
        self,
        method: str,
        base_url: str,
        path: str,
        *,
        data: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        signed: bool,
        allow_refresh: bool = True,
        operation: str | None = None,
    ) -> Any:
        url = path if path.startswith(("http://", "https://")) else urljoin(_ensure_slash(base_url), path)
        headers = self._headers(signed=signed)
        for attempt in range(3):
            await self._throttle()
            try:
                async with self._session.request(
                    method.upper(),
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    payload = await _read_response(response)
            except BirdfyError:
                raise
            except (TimeoutError, OSError) as err:
                if attempt == 2:
                    raise BirdfyConnectionError("Unable to reach Birdfy cloud API") from err
                await asyncio.sleep(0.5 * (2**attempt))
                continue

            status = getattr(response, "status", None)
            if status == 429:
                raise BirdfyRateLimitError(
                    f"Birdfy cloud API rate limit exceeded for {_operation_label(operation, path)}"
                )
            if status in (401, 403):
                if signed and allow_refresh:
                    await self.refresh_tokens()
                    headers = self._headers(signed=signed)
                    continue
                raise BirdfyAuthError(
                    f"Birdfy rejected the account credentials for {_operation_label(operation, path)}"
                )
            if status and status >= 400:
                raise BirdfyApiError(
                    "Birdfy cloud API request failed for "
                    f"{_operation_label(operation, path)} (HTTP {status})",
                    status=status,
                    operation=operation,
                )
            if isinstance(payload, Mapping):
                code = _as_int(payload.get("ret"))
                if code and code != 0:
                    if code in AUTH_RET_CODES and signed and allow_refresh:
                        await self.refresh_tokens()
                        headers = self._headers(signed=signed)
                        continue
                    raise BirdfyApiError(
                        "Birdfy cloud API returned an error for "
                        f"{_operation_label(operation, path)} (code {code})",
                        status=status,
                        code=code,
                        operation=operation,
                    )
            return _unwrap_payload(payload)
        raise BirdfyConnectionError("Birdfy cloud API request failed after retries")

    async def _request_raw(self, method: str, url: str, *, signed: bool) -> bytes:
        headers = self._headers(signed=signed)
        await self._throttle()
        try:
            async with self._session.request(
                method.upper(),
                url,
                headers=headers,
                timeout=self.timeout,
            ) as response:
                status = getattr(response, "status", None)
                if status and status >= 400:
                    raise BirdfyApiError("Unable to fetch Birdfy media", status=status)
                return await response.read()
        except BirdfyError:
            raise
        except (TimeoutError, OSError) as err:
            raise BirdfyConnectionError("Unable to fetch Birdfy media") from err

    def _headers(self, *, signed: bool) -> dict[str, str]:
        headers = {
            "accept-language": "en",
            "x-nvs-ucid": self.ucid,
            "x-nvs-udid": self.udid,
        }
        if not signed:
            return headers
        if self.tokens is None:
            raise BirdfyAuthError("A signed request requires authenticated tokens")
        timestamp = str(int(time.time() * 1000))
        headers.update(
            {
                "x-nvs-version": SIGNATURE_VERSION,
                "x-nvs-userid": self.tokens.user_id,
                "x-nvs-time": timestamp,
                "x-nvs-signature": _signature(
                    self.tokens.token,
                    self.ucid,
                    self.udid,
                    self.tokens.user_id,
                    timestamp,
                ),
            }
        )
        return headers

    async def _throttle(self) -> None:
        async with self._rate_lock:
            now = time.monotonic()
            wait_time = self._request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()

    async def _notify_token_update(self) -> None:
        if self.tokens is None or self.token_update_callback is None:
            return
        result = self.token_update_callback(self.tokens)
        if inspect.isawaitable(result):
            await result


async def _read_response(response: Any) -> Any:
    try:
        return await response.json(content_type=None)
    except TypeError:
        return await response.json()
    except Exception:
        text = await response.text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


def _signature(token: str, ucid: str, udid: str, user_id: str, timestamp: str) -> str:
    """Return the Netvue web signature for signed API calls."""

    def digest(key: str, value: str) -> str:
        return hmac.new(key.encode(), value.encode(), "sha256").hexdigest()

    key1 = digest(f"nvs1{token}", ucid)
    key2 = digest(key1, udid)
    key3 = digest(key2, user_id)
    key4 = digest(key3, timestamp)
    return digest(key4, "nvs1_request")


def redact_data(value: Any) -> Any:
    """Recursively redact secrets and user/device identifiers."""
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[str(key)] = "**REDACTED**"
            else:
                redacted[str(key)] = redact_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    return value


def _first(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _unwrap_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping) and "data" in payload and payload["data"] not in (None, ""):
        return payload["data"]
    return payload


def _collection_payload(payload: Any, *keys: str) -> Any:
    payload = _unwrap_payload(payload)
    if isinstance(payload, Mapping):
        return _first(payload, *keys) or payload
    return payload


def _payload_shape(payload: Any) -> str:
    if isinstance(payload, Mapping):
        keys = ", ".join(sorted(str(key) for key in payload)[:10])
        return f"mapping keys: {keys}" if keys else "empty mapping"
    return f"type: {type(payload).__name__}"


def _operation_label(operation: str | None, path: str) -> str:
    if operation:
        return operation
    if path.startswith(("http://", "https://")):
        return "remote request"
    return path


def _parse_ability(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _has_bit(value: int, bit: int) -> bool:
    return (value & bit) == bit


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if not match:
            return None
        value = match.group(0)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "online", "on", "connected"}:
            return True
        if normalized in {"0", "false", "offline", "off", "disconnected"}:
            return False
    return None


def _coerce_percent(value: Any) -> int | None:
    result = _as_int(value)
    if result is None:
        return None
    return max(0, min(100, result))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("_", "").replace("-", "").lower()
    return (
        normalized in SENSITIVE_KEYS_NORMALIZED
        or normalized.endswith("token")
        or normalized.endswith("password")
        or normalized.endswith("secret")
    )


def _normalize_event_type(value: str | None, *, species: str | None, clip_url: str | None) -> str:
    if value:
        normalized = re.sub(r"[^a-z0-9]", "", value.lower())
        if normalized in EVENT_TYPE_ALIASES:
            return EVENT_TYPE_ALIASES[normalized]
    if species:
        return EVENT_SPECIES
    if clip_url:
        return EVENT_CLIP_READY
    return EVENT_MOTION


def _find_url(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    allowed_schemes: tuple[str, ...] = ("http://", "https://", "rtsp://", "rtsps://"),
) -> str | None:
    for key in keys:
        value = _first(payload, key)
        if isinstance(value, str) and value.startswith(allowed_schemes):
            return value
    for value in payload.values():
        if isinstance(value, Mapping):
            found = _find_url(value, keys, allowed_schemes=allowed_schemes)
            if found:
                return found
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    found = _find_url(item, keys, allowed_schemes=allowed_schemes)
                    if found:
                        return found
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        timestamp = float(value) / 1000 if value > 10_000_000_000 else float(value)
        return datetime.fromtimestamp(timestamp, UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _ensure_slash(value: str) -> str:
    return value if value.endswith("/") else f"{value}/"

"""Data coordinators for Birdfy."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    BirdfyAuthError,
    BirdfyClient,
    BirdfyConnectionError,
    BirdfyDevice,
    BirdfyError,
    BirdfyEvent,
    redact_data,
)
from .const import DEFAULT_EVENT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, SIGNAL_EVENT

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BirdfyData:
    """Latest account data."""

    devices: dict[str, BirdfyDevice]
    events: dict[str, BirdfyEvent]


@dataclass(slots=True)
class BirdfyRuntimeData:
    """Runtime objects for a config entry."""

    client: BirdfyClient
    coordinator: BirdfyCoordinator
    event_coordinator: BirdfyEventCoordinator


class BirdfyCoordinator(DataUpdateCoordinator[BirdfyData]):
    """Poll account devices and basic metadata."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: BirdfyClient) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self.client = client
        self._events: dict[str, BirdfyEvent] = {}

    async def _async_update_data(self) -> BirdfyData:
        try:
            devices = await self.client.list_devices(include_services=True)
        except BirdfyAuthError as err:
            raise ConfigEntryAuthFailed(str(err) or "Birdfy authentication expired") from err
        except BirdfyConnectionError as err:
            raise UpdateFailed(f"Unable to reach Birdfy cloud API: {err}") from err
        except BirdfyError as err:
            raise UpdateFailed(f"Unable to update Birdfy devices: {err}") from err

        existing_events = self.data.events if self.data else self._events
        return BirdfyData(devices={device.identifier: device for device in devices}, events=existing_events)

    @callback
    def async_set_events(self, events: dict[str, BirdfyEvent]) -> None:
        """Merge event data into coordinator data."""
        self._events = events
        if self.data:
            self.async_set_updated_data(BirdfyData(devices=self.data.devices, events=events))


class BirdfyEventCoordinator(DataUpdateCoordinator[dict[str, BirdfyEvent]]):
    """Poll event metadata when a supported source exists."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BirdfyClient,
        device_coordinator: BirdfyCoordinator,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}-{entry.entry_id}-events",
            update_interval=DEFAULT_EVENT_SCAN_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.device_coordinator = device_coordinator
        self._last_event_time: datetime | None = None

    async def _async_update_data(self) -> dict[str, BirdfyEvent]:
        try:
            events = await self.client.list_events(since=self._last_event_time)
        except BirdfyAuthError as err:
            raise ConfigEntryAuthFailed(str(err) or "Birdfy authentication expired") from err
        except BirdfyError as err:
            raise UpdateFailed(f"Unable to update Birdfy events: {err}") from err

        existing = dict(self.data or {})
        newest = self._last_event_time
        for event in events:
            if event.event_id in existing:
                continue
            existing[event.event_id] = event
            async_dispatcher_send(self.hass, f"{SIGNAL_EVENT}_{self.config_entry.entry_id}", event)
            if event.occurred_at and (newest is None or event.occurred_at > newest):
                newest = event.occurred_at
        self._last_event_time = newest or datetime.now(UTC)
        self.device_coordinator.async_set_events(existing)
        return existing

    @callback
    def latest_event_for_device(self, device_id: str) -> BirdfyEvent | None:
        """Return the newest known event for a device."""
        events = [event for event in (self.data or {}).values() if event.device_id == device_id]
        if not events:
            return None
        return max(events, key=lambda event: event.occurred_at or datetime.min.replace(tzinfo=UTC))


@callback
def device_from_coordinator(coordinator: BirdfyCoordinator, device_id: str) -> BirdfyDevice | None:
    """Return a device by ID from coordinator data."""
    if not coordinator.data:
        return None
    return coordinator.data.devices.get(device_id)


def redacted_device_payload(device: BirdfyDevice) -> dict[str, Any]:
    """Return safe diagnostic metadata for a device."""
    return {
        "has_name": bool(device.name),
        "manufacturer": device.manufacturer,
        "model": device.model,
        "firmware": device.firmware,
        "online": device.online,
        "has_snapshot_url": bool(device.snapshot_url),
        "capabilities": {
            "supports_video": device.capabilities.supports_video,
            "supports_snapshot": device.capabilities.supports_snapshot,
            "supports_motion_detection": device.capabilities.supports_motion_detection,
            "supports_local_storage": device.capabilities.supports_local_storage,
            "supports_kvs_webrtc": device.capabilities.supports_kvs_webrtc,
        },
        "services_present": bool(device.services),
        "raw_payload_shape": _raw_payload_shape(device.raw),
    }


DIAGNOSTIC_VALUE_KEYS = {
    "active",
    "battery",
    "batteryCapacity",
    "batteryLevel",
    "batteryPercent",
    "batteryPercentage",
    "connected",
    "connectionStatus",
    "connectStatus",
    "deviceModel",
    "deviceOnline",
    "deviceStatus",
    "electricity",
    "firmware",
    "firmwareVersion",
    "fwVersion",
    "isActive",
    "isConnected",
    "isOnline",
    "model",
    "modelKey",
    "modelName",
    "netStatus",
    "networkSignal",
    "networkStatus",
    "online",
    "onlineStatus",
    "power",
    "powerPercent",
    "productType",
    "rssi",
    "rssiLevel",
    "signal",
    "signalLevel",
    "signalStrength",
    "softVersion",
    "softwareVersion",
    "status",
    "swVersion",
    "version",
    "versionName",
    "wifi",
    "wifiQuality",
    "wifiSignal",
    "wifiStrength",
}


def _raw_payload_shape(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return enough raw payload shape to map real devices without private values."""
    candidate_values = {
        str(key): value
        for key, value in payload.items()
        if str(key) in DIAGNOSTIC_VALUE_KEYS and not isinstance(value, (dict, list))
    }
    return {
        "top_level_keys": sorted(str(key) for key in payload),
        "candidate_values": redact_data(candidate_values),
    }

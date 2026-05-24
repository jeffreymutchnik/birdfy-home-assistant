"""Binary sensor entities for Birdfy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .api import BirdfyDevice
from .const import EVENT_BIRD, EVENT_MOTION, EVENT_SPECIES
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity


@dataclass(frozen=True, kw_only=True)
class BirdfyBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Birdfy binary sensor."""

    value_fn: Callable[[BirdfyDevice, BirdfyCoordinator], bool | None]


RECENT_EVENT_WINDOW = timedelta(minutes=3)


BINARY_SENSOR_DESCRIPTIONS: tuple[BirdfyBinarySensorDescription, ...] = (
    BirdfyBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device, coordinator: device.online,
    ),
    BirdfyBinarySensorDescription(
        key="motion",
        translation_key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
        value_fn=lambda device, coordinator: _has_recent_event(coordinator, device.identifier, {EVENT_MOTION}),
    ),
    BirdfyBinarySensorDescription(
        key="bird_detected",
        translation_key="bird_detected",
        icon="mdi:bird",
        value_fn=lambda device, coordinator: _has_recent_event(
            coordinator, device.identifier, {EVENT_BIRD, EVENT_SPECIES}
        ),
    ),
    BirdfyBinarySensorDescription(
        key="sd_card",
        translation_key="sd_card",
        device_class=BinarySensorDeviceClass.PLUG,
        entity_registry_enabled_default=False,
        value_fn=lambda device, coordinator: _service_bool(device, ("sdCard", "sd_card", "tfCard", "localStorage")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BirdfyBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class BirdfyBinarySensor(BirdfyEntity, BinarySensorEntity):
    """Birdfy binary sensor."""

    entity_description: BirdfyBinarySensorDescription

    def __init__(
        self,
        coordinator: BirdfyCoordinator,
        device_id: str,
        description: BirdfyBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return binary sensor state."""
        device = self.device
        if device is None:
            return None
        return self.entity_description.value_fn(device, self.coordinator)


def _has_recent_event(coordinator: BirdfyCoordinator, device_id: str, event_types: set[str]) -> bool:
    if not coordinator.data:
        return False
    now = datetime.now(UTC)
    for event in coordinator.data.events.values():
        if event.device_id != device_id or event.event_type not in event_types or not event.occurred_at:
            continue
        if now - event.occurred_at <= RECENT_EVENT_WINDOW:
            return True
    return False


def _service_bool(device: BirdfyDevice, keys: tuple[str, ...]) -> bool | None:
    for key in keys:
        value = device.services.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            for nested_value in value.values():
                if isinstance(nested_value, bool):
                    return nested_value
    return None

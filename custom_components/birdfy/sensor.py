"""Sensor entities for Birdfy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .api import BirdfyDevice
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity


@dataclass(frozen=True, kw_only=True)
class BirdfySensorDescription(SensorEntityDescription):
    """Describe a Birdfy sensor."""

    value_fn: Callable[[BirdfyDevice], Any]
    available_fn: Callable[[BirdfyDevice], bool] = lambda device: True


SENSOR_DESCRIPTIONS: tuple[BirdfySensorDescription, ...] = (
    BirdfySensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.battery_level,
        available_fn=lambda device: device.battery_level is not None,
    ),
    BirdfySensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.signal_level,
        available_fn=lambda device: device.signal_level is not None,
    ),
    BirdfySensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.firmware,
        available_fn=lambda device: bool(device.firmware),
    ),
    BirdfySensorDescription(
        key="last_species",
        translation_key="last_species",
        icon="mdi:bird",
        value_fn=lambda device: None,
    ),
    BirdfySensorDescription(
        key="last_event_time",
        translation_key="last_event_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BirdfySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in SENSOR_DESCRIPTIONS
        if description.available_fn(coordinator.data.devices[device_id])
    )


class BirdfySensor(BirdfyEntity, SensorEntity):
    """Birdfy sensor."""

    entity_description: BirdfySensorDescription

    def __init__(
        self,
        coordinator: BirdfyCoordinator,
        device_id: str,
        description: BirdfySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        device = self.device
        if device is None:
            return None
        if self.entity_description.key == "last_species":
            event = self.coordinator.data and self.coordinator.data.events
            if not event:
                return None
            latest = _latest_device_event(list(event.values()), self.device_id)
            return latest.species if latest else None
        if self.entity_description.key == "last_event_time":
            event = self.coordinator.data and self.coordinator.data.events
            if not event:
                return None
            latest = _latest_device_event(list(event.values()), self.device_id)
            return latest.occurred_at if latest else None
        return self.entity_description.value_fn(device)


def _latest_device_event(events, device_id):
    device_events = [event for event in events if event.device_id == device_id]
    if not device_events:
        return None
    return max(device_events, key=lambda event: event.occurred_at or datetime.min.replace(tzinfo=UTC))

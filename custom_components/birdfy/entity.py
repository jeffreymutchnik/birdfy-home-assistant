"""Shared entity helpers for Birdfy."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BirdfyCoordinator, device_from_coordinator


class BirdfyEntity(CoordinatorEntity[BirdfyCoordinator]):
    """Base Birdfy entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BirdfyCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self.entity_key = key
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def device(self):
        """Return the backing device."""
        return device_from_coordinator(self.coordinator, self.device_id)

    @property
    def available(self) -> bool:
        """Return whether entity data is available."""
        device = self.device
        return super().available and device is not None and device.online is not False

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device registry info."""
        device = self.device
        if device is None:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, device.identifier)},
            manufacturer=device.manufacturer,
            model=device.model,
            name=device.name,
            serial_number=device.serial_number,
            sw_version=device.firmware,
        )

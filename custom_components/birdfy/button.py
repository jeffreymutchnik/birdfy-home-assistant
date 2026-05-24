"""Button entities for Birdfy."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity


@dataclass(frozen=True, kw_only=True)
class BirdfyButtonDescription(ButtonEntityDescription):
    """Describe a Birdfy button."""

    press_fn: Callable[[BirdfyCoordinator, str], Awaitable[None]]


async def _async_refresh(coordinator: BirdfyCoordinator, device_id: str) -> None:
    await coordinator.async_request_refresh()


async def _async_sync_events(coordinator: BirdfyCoordinator, device_id: str) -> None:
    await coordinator.config_entry.runtime_data.event_coordinator.async_request_refresh()


BUTTON_DESCRIPTIONS: tuple[BirdfyButtonDescription, ...] = (
    BirdfyButtonDescription(key="refresh", translation_key="refresh", press_fn=_async_refresh),
    BirdfyButtonDescription(key="sync_events", translation_key="sync_events", press_fn=_async_sync_events),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy buttons."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BirdfyButton(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BUTTON_DESCRIPTIONS
    )


class BirdfyButton(BirdfyEntity, ButtonEntity):
    """Birdfy button."""

    entity_description: BirdfyButtonDescription

    def __init__(
        self,
        coordinator: BirdfyCoordinator,
        device_id: str,
        description: BirdfyButtonDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator, self.device_id)

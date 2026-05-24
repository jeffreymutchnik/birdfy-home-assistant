"""Constants for the Birdfy integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "birdfy"
NAME: Final = "Birdfy"

CONF_BASE_URL: Final = "base_url"
CONF_API2_BASE_URL: Final = "api2_base_url"
CONF_CAPI2_BASE_URL: Final = "capi2_base_url"
CONF_CAPIV3_BASE_URL: Final = "capiv3_base_url"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)
DEFAULT_EVENT_SCAN_INTERVAL: Final = timedelta(minutes=1)

PLATFORMS: Final = [
    "binary_sensor",
    "button",
    "camera",
    "event",
    "image",
    "sensor",
    "switch",
]

STARTUP_MESSAGE: Final = (
    "Birdfy uses an unofficial Netvue/Birdfy web API surface. Only read-only "
    "features with public evidence are enabled by default."
)

CONF_TOKEN_DATA: Final = "token_data"
CONF_USERNAME: Final = "username"
CONF_UDID: Final = "udid"

ATTR_SERIAL_NUMBER: Final = "serial_number"
ATTR_MODEL: Final = "model"
ATTR_FEATURE_SOURCE: Final = "feature_source"

EVENT_MOTION: Final = "motion_detected"
EVENT_BIRD: Final = "bird_detected"
EVENT_SPECIES: Final = "species_recognized"
EVENT_CLIP_READY: Final = "clip_ready"

EVENT_TYPES: Final = [EVENT_MOTION, EVENT_BIRD, EVENT_SPECIES, EVENT_CLIP_READY]

SIGNAL_EVENT: Final = "birdfy_event"

# Birdfy

Unofficial Home Assistant integration for Birdfy / Netvue smart bird feeders and cameras.

Current support is intentionally conservative:

- Account login and device discovery through the public Netvue web API surface.
- Read-only device metadata where available.
- Snapshot camera support when the API exposes a still image URL.
- Optional direct stream support only when the API returns an ffmpeg-compatible URL.
- Simulator-backed event/image entities for development.

No siren, spotlight, talk, privacy, notification, or sensitivity controls are exposed until stable and safe API support is verified.

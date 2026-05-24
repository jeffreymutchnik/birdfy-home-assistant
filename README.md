# Birdfy Home Assistant Custom Integration

`birdfy` is an unofficial Home Assistant integration for Birdfy / Netvue smart bird feeders and cameras. It is designed to be HACS-ready, async-first, and conservative about features: if Birdfy does not expose a stable, lawful API path for something, the integration documents the limitation instead of pretending it works.

## Status

This is an early production scaffold. It includes:

- UI config flow with Birdfy/Netvue account login.
- Token refresh and secret redaction.
- Device discovery through the public Netvue web API surface.
- Camera still image support when the device payload exposes a snapshot URL.
- Direct stream support only when the API returns an ffmpeg-compatible URL.
- Read-only sensors for battery, Wi-Fi signal, firmware, latest species, and latest event time when data is present.
- Binary sensors for online state plus recent motion/bird events from supported event sources.
- Event/image entities backed by simulator fixtures today.
- Fixture simulator for development without physical hardware.

Hardware validation is still required before a tagged public release.
See [docs/HARDWARE_VALIDATION.md](docs/HARDWARE_VALIDATION.md) for the next real-device test checklist.
Use [docs/HARDWARE_TEST_RESULTS_TEMPLATE.md](docs/HARDWARE_TEST_RESULTS_TEMPLATE.md) to record sanitized results.

## Known Limitations

Birdfy/Netvue does not publish an official Home Assistant or developer API. This integration is based on public web-client behavior and may break if the vendor changes endpoints or auth semantics.

Write controls are intentionally not exposed yet. That includes siren, spotlight, microphone/speaker/talk, privacy/sleep mode, notification toggles, detection sensitivity, and detection zones. These features exist in the app, but the integration will not expose them until a stable and safe API path is verified with hardware.

Birdfy live video may use AWS Kinesis/WebRTC data rather than a direct RTSP/HLS URL. Home Assistant camera streaming is enabled only when the API returns a direct stream URL that ffmpeg can consume.

## Installation

### HACS

1. Add this repository as a HACS custom repository of type `Integration`.
2. Install `Birdfy`.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration > Birdfy**.

### Manual

Copy `custom_components/birdfy` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Setup

Enter your Birdfy or Netvue account email and password in the UI config flow. Tokens are stored by Home Assistant in the config entry store. The password is used only during the initial login/reauth flow and is not kept in the config entry.

For local development, run:

```bash
python tools/birdfy_simulator.py
```

Then configure Birdfy with API base URL:

```text
http://127.0.0.1:8765/v1/
```

The simulator covers login, token refresh, device discovery, service metadata, snapshot bytes, fixture events, and placeholder HLS URLs. The HLS data is for URL plumbing only; it is not a real camera video feed.

## Feature Matrix

| Feature | Status | Notes |
|---|---|---|
| Account login | Probably supported | Based on the public Netvue web client. Requires user-authorized credentials. |
| Device discovery | Probably supported | Uses `devices/v3` from the public web API surface. |
| Battery/Wi-Fi/firmware | Requires hardware validation | Exposed only if returned by the device payload. |
| Camera snapshot | Probably supported | Works when the payload includes a snapshot/cover URL. |
| Live stream | Requires hardware validation | Enabled only for direct RTSP/HLS/HTTP stream URLs. Kinesis/WebRTC is documented but not implemented. |
| Motion/bird/species events | Requires hardware validation | Fixture-backed now; no official event history endpoint is documented. |
| Highlight/Recap share links | Confirmed low-risk future path | Public community integrations show this can support read-only AI summaries without account control APIs. |
| Siren/light/talk/privacy/settings | Unsafe/unsupported | App controls exist, but no stable public write API has been verified. |

## Privacy And Security

- No credentials, tokens, device IDs, media URLs, snapshots, clips, or user data should be committed.
- Diagnostics redact account tokens, refresh tokens, usernames, device IDs, serials, media URLs, and related sensitive fields.
- Logs avoid request payloads and secrets.
- The integration uses cloud APIs only after the user configures account access.
- Media URLs are treated as bearer secrets, even when they are temporary or signed.
- Camera snapshots, clips, thumbnails, and live stream segments are not persisted by default.
- Do not expose Home Assistant directly to the public internet; prefer Home Assistant Cloud, a VPN, or a carefully configured HTTPS reverse proxy.

See [SECURITY.md](SECURITY.md) for reporting instructions and maintainer release checks.

## Development

```bash
python -m pytest
python tools/check_no_private_artifacts.py
python -m compileall pybirdfy custom_components tests tools
```

Optional Home Assistant validation:

```bash
pytest -o asyncio_mode=auto tests/test_config_flow_ha.py
python -m script.hassfest --integration-path custom_components/birdfy
hacs validate
```

Before tagging a release, follow [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).
The release-only metadata gate is:

```bash
python tools/check_release_ready.py
```

## Sources And Evidence

- Home Assistant developer docs: [manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/), [config flow](https://developers.home-assistant.io/docs/core/integration/config_flow/), [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/), [camera](https://developers.home-assistant.io/docs/core/entity/camera/), [image](https://developers.home-assistant.io/docs/core/entity/image/), [event](https://developers.home-assistant.io/docs/core/entity/event/), [diagnostics](https://developers.home-assistant.io/docs/core/integration/diagnostics/), [repairs](https://developers.home-assistant.io/docs/core/platform/repairs/), and [quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/).
- Birdfy support docs: [Birdfy app](https://support.birdfy.com/help/birdfy-app/), [web client](https://support.birdfy.com/help/birdfy-app/Web%20Client/), and [cloud service](https://support.birdfy.com/help/cloud-service/).
- Community references: [Home Assistant community thread](https://community.home-assistant.io/t/birdfy-feeder-with-solar-panel/754121), [dakahler/homeassistant-birdfy](https://github.com/dakahler/homeassistant-birdfy), [sebsst/birdfy-integration](https://github.com/sebsst/birdfy-integration), and [sebsst/birdfy-rtsp](https://github.com/sebsst/birdfy-rtsp).

## Contributing

Please include sanitized fixtures and avoid uploading real snapshots, videos, serial numbers, tokens, or account data. Hardware validation reports should describe model, firmware, observed entities, and API behavior without exposing private identifiers.

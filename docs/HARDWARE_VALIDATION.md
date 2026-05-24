# Hardware Validation Checklist

Use this checklist when a real Birdfy / Netvue account and feeder are available. Keep all credentials, tokens, serial numbers, device IDs, media URLs, snapshots, and videos private.

## Before Testing

1. Pull the latest branch and install the integration in a Home Assistant test instance.
2. Run the offline checks:

   ```bash
   python3 -m pytest -q
   python3 -m compileall -q pybirdfy custom_components tests tools
   ```

3. Confirm the simulator still works without hardware:

   ```bash
   python3 tools/birdfy_simulator.py
   ```

   Configure the integration with base URL `http://127.0.0.1:8765/v1/` and the fixture account credentials from `tests/fixtures/login.json`.

## Account And Discovery

Record only yes/no results and sanitized notes.

- Add the integration from the Home Assistant UI with a real Birdfy/Netvue account.
- Confirm invalid credentials produce a clear auth error.
- Confirm a successful login creates one config entry.
- Confirm reauth works after changing the account password or invalidating tokens, if practical.
- Confirm duplicate account/device setup is blocked or merged cleanly.
- Confirm every discovered feeder/camera has a device registry entry.
- Record sanitized model names, firmware versions, and which fields appear in the device payload.

## Entity Validation

For each device, check whether the entity exists, updates, and becomes unavailable/offline gracefully.

| Entity area | Expected behavior |
|---|---|
| `sensor.battery` | Shows a percentage only when the API returns battery data. |
| `sensor.signal` | Shows Wi-Fi/signal level only when exposed. |
| `sensor.firmware` | Shows firmware only when exposed. |
| `sensor.latest_species` | Updates only after a recognized bird event. |
| `sensor.latest_event_time` | Updates after a motion/bird/media event. |
| `binary_sensor.online` | Tracks online/offline status. |
| `binary_sensor.motion` | Turns on briefly after recent motion event data. |
| `binary_sensor.bird` | Turns on briefly after recent bird/species event data. |
| `camera` | Shows a still image when a snapshot URL is present. |
| `camera.stream_source` | Works only if a direct RTSP/HLS/HTTP stream URL is returned. |
| `image.latest_event` | Shows the latest event image only when an image URL is present. |
| `event` | Fires `motion_detected`, `bird_detected`, `species_recognized`, or `clip_ready` only from real event data. |

Do not enable siren, spotlight, talk, microphone, privacy mode, notification toggles, sensitivity, or zones unless a stable lawful API path has been verified.

## Camera And Media

- Open the camera entity in Home Assistant.
- Confirm snapshot image loading works without exposing the URL in logs.
- If live stream is available, confirm Home Assistant can play it through the camera card.
- If live stream fails, record the sanitized response shape only. Do not paste full media URLs.
- Trigger or wait for a bird/motion event and confirm the latest event image updates.
- If cloud clips are exposed, record whether the URL is direct, signed, expiring, WebRTC/Kinesis, or app-only.

## Events

- Trigger motion in front of the camera.
- Confirm event polling updates within the configured interval.
- Capture the sanitized shape of any event payload:

  ```json
  {
    "eventType": "species_recognized",
    "timestamp": "2026-05-14T12:00:00+00:00",
    "species": "Northern Cardinal",
    "imageUrl": "**REDACTED**",
    "clipUrl": "**REDACTED**",
    "serialNumber": "**REDACTED**"
  }
  ```

- Note aliases used by the vendor for event types, such as `motion`, `bird`, `recognition`, `video`, or `clip`.

## Diagnostics And Logs

- Download diagnostics from Home Assistant and confirm these are redacted:
  - access tokens
  - refresh tokens
  - usernames and emails
  - serial numbers and device IDs
  - snapshot, stream, image, clip, and media URLs
- Review debug logs for useful but secret-free messages.
- Confirm offline devices do not cause traceback loops.
- Confirm expired tokens refresh without logging token values.

## Release Decision

Mark a feature as supported only after it has passed hardware validation. If an API response exists but behavior is inconsistent, keep the entity disabled or document it as experimental. If a feature requires app-only controls, protected mobile traffic, reverse engineering around protections, or terms-of-service risk, leave it unsupported and document the blocker in an ADR.

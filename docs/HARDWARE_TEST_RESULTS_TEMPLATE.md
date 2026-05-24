# Hardware Test Results Template

Copy this file for each hardware validation run. Keep the copy sanitized. Do not include credentials, account names, serial numbers, device IDs, snapshots, clips, media URLs, or raw signed URLs.

## Test Metadata

- Date:
- Tester:
- Home Assistant version:
- Integration commit/version:
- Birdfy/Netvue app version, if relevant:
- Network conditions:

## Device

- Model:
- Manufacturer shown by API:
- Firmware:
- Power mode:
- Storage configuration:
- Cloud subscription status, if relevant:
- Notes:

## Account And Setup

| Check | Result | Sanitized notes |
|---|---|---|
| UI config flow succeeds | Untested | |
| Invalid credentials return `invalid_auth` | Untested | |
| Token refresh works | Untested | |
| Duplicate setup is blocked | Untested | |
| Reauth works | Untested | |

## Device Discovery

| Field | Present? | Sanitized value/shape |
|---|---|---|
| Device name | Untested | Do not paste exact private names unless generic. |
| Model | Untested | |
| Firmware | Untested | |
| Online status | Untested | |
| Battery | Untested | |
| Wi-Fi/signal | Untested | |
| Snapshot URL | Untested | Record only `present`, `absent`, or `signed/expiring`. |
| Capability/ability payload | Untested | Paste sanitized key names and boolean/bitfield shape only. |
| Services payload | Untested | Paste sanitized key names only. |

## Entities

| Entity area | Result | Notes |
|---|---|---|
| Device registry | Untested | |
| Battery sensor | Untested | |
| Signal sensor | Untested | |
| Firmware sensor | Untested | |
| Online binary sensor | Untested | |
| Motion binary sensor | Untested | |
| Bird binary sensor | Untested | |
| Latest species sensor | Untested | |
| Latest event time sensor | Untested | |
| Camera still image | Untested | |
| Camera stream | Untested | |
| Latest event image | Untested | |
| Event entity | Untested | |
| Refresh button | Untested | |
| Sync events button | Untested | |

## Camera And Media

- Snapshot response shape:
- Snapshot refresh behavior:
- Stream endpoint response shape:
- Stream type: direct RTSP / direct HLS / direct HTTP / WebRTC / Kinesis / app-only / unknown
- Home Assistant playback result:
- Clip/media response shape:
- Any media URL expiration observed:

## Events

| Event | Trigger method | Result | Sanitized payload shape |
|---|---|---|---|
| Motion | | Untested | |
| Bird detected | | Untested | |
| Species recognized | | Untested | |
| Clip ready | | Untested | |

## Diagnostics And Logs

| Check | Result | Notes |
|---|---|---|
| Diagnostics redact tokens | Untested | |
| Diagnostics redact serial/device IDs | Untested | |
| Diagnostics redact media URLs | Untested | |
| Logs omit request payloads | Untested | |
| Logs omit media URLs | Untested | |
| Offline device does not loop tracebacks | Untested | |

## Unsupported Or Blocked Features

List any feature visible in the Birdfy app but not safely exposed by the current API evidence.

- Siren:
- Spotlight:
- Talk/microphone/speaker:
- Privacy/sleep mode:
- Notifications:
- Detection sensitivity:
- Detection zones:
- Storage settings:

## Release Decision

- Recommended support level: unsupported / experimental / beta / supported
- Features safe to enable:
- Features that need another validation run:
- New ADR needed:
- Follow-up issues:

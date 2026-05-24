# Local Firmware / Hardware Bring-Up Checklist

This checklist is for owned hardware only. Keep all credentials, tokens, device IDs, serials, flash dumps, media URLs, snapshots, and videos private.

## Ground Rules

- Work on a device you can afford to recover, reflash, or replace.
- Keep the device on an isolated test network during experiments.
- Do not bypass app protections, certificate pinning, DRM, encryption, or authentication.
- Do not publish flash dumps or logs containing private keys, Wi-Fi credentials, account identifiers, serials, or media URLs.
- Make a recovery plan before writing to flash.

## Non-Invasive Inventory

Record sanitized facts:

```text
Model:
FCC ID:
Firmware version:
App shows Live Stream option: yes/no
SD card slot present: yes/no
Battery/solar details:
Observed LAN services:
```

For repeatable single-device LAN checks, use
[LOCAL_DEVICE_DISCOVERY.md](LOCAL_DEVICE_DISCOVERY.md). Do not use subnet scans
or publish raw discovery output that contains real network identifiers.

Use public filings before opening the enclosure:

- FCC ID pages for external/internal photos, manuals, and test reports.
- Birdfy/Netvue support pages for model-specific livestream and storage support.
- Community reports only as hints, not proof for your exact revision.

See [HARDWARE_EVIDENCE.md](HARDWARE_EVIDENCE.md) for the current public
model-family map.

## Physical Inspection

Photograph:

- full enclosure before opening;
- cable routing and gasket positions;
- both sides of each PCB;
- every readable IC marking;
- camera sensor board and ribbon connectors;
- antenna, PIR sensor, microphone, speaker, LEDs, and battery/solar wiring.

Create a table:

| Part | Marking | Suspected role | Notes |
|---|---|---|---|
| Main SoC | TBD | video/control | |
| Wi-Fi module | TBD | network | |
| Flash | TBD | firmware storage | |
| Camera sensor | TBD | video input | |
| PMIC/charger | TBD | battery/solar | |

## UART Logging

Safe UART work is passive observation first:

1. Identify likely UART pads by labels, test pads, or FCC internal photos.
2. Measure voltage levels before connecting a USB-TTL adapter.
3. Connect ground and RX first; avoid driving TX until voltage and pinout are known.
4. Record boot logs.
5. Redact secrets before sharing logs.

Do not attempt credential guessing, bootloader password bypasses, or vendor-key extraction.

## Firmware Backup

Before changing firmware:

1. Identify flash chip package and voltage.
2. Prefer documented backup/recovery mechanisms.
3. If using an external programmer, keep dumps private and encrypted.
4. Hash backups and record chip orientation.
5. Verify that a backup can be read consistently at least twice.

Never commit firmware dumps to this repository.

## Decision Tree

```text
Does the Birdfy app expose Live Stream?
  yes -> test local RTMP with MediaMTX first.
  no  -> continue.

Does the device expose direct RTSP/HLS/snapshot/ONVIF locally?
  yes -> add manual local media URL in Home Assistant.
  no  -> continue.

Is the camera SoC supported by a maintained open firmware project?
  yes -> evaluate open firmware with full backup/recovery.
  no  -> continue.

Can the enclosure/power/PIR be reused with a local camera board?
  yes -> build a transplant prototype.
  no  -> keep current cloud integration for discovery/events and document unsupported local video.
```

## Candidate Local Architectures

### MediaMTX Bridge

Use when Birdfy app-initiated RTMP is available. See [LOCAL_RTMP_MEDIAMTX.md](LOCAL_RTMP_MEDIAMTX.md).

### Open Firmware

Use only when the SoC, sensor, boot flow, and recovery path are understood. Good signs include public SoC support, documented flashing tools, known sensor drivers, and an unlocked or documented bootloader.

### Hardware Transplant

Use when original firmware is closed or app-only. Candidate modules:

- Raspberry Pi Zero / camera module for strongest Linux and AI compatibility.
- ESP32-S3 camera board for lower power and simpler firmware.
- Existing local-first IP camera module if it supports RTSP/HLS.

Home Assistant-facing outputs should be RTSP/HLS for video and MQTT/Home Assistant events for detections.

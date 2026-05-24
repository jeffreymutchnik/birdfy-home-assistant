# ADR 0002: Prefer Open Local Control Over App Bypass

## Status

Proposed

## Context

The owner wants a local-first Birdfy system that can work without depending on the Birdfy mobile app or paid cloud AI. Local network testing against the owned device found the feeder online, but no reachable RTSP, ONVIF, HTTP snapshot, HLS, or common camera service ports were exposed while idle.

Public evidence suggests several Birdfy/Netvue hardware variants exist. FCC filings publish model families, manuals, and internal/external exhibits for some devices. Community hardware work also suggests at least some Netvue/Birdfy camera boards expose UART logs and may use HiSilicon-family SDK components or an RTOS-like firmware layout, but that evidence is not enough to assume a universal firmware path across models.

## Decision

The project will support owner-controlled local operation through lawful and reversible paths:

- App-initiated RTMP to a local MediaMTX server when the Birdfy app exposes **Live Stream** for the model.
- Direct local RTSP/HLS/snapshot/ONVIF only when the device exposes those services without bypassing protections.
- Vendor-provided firmware, documented recovery modes, unlocked bootloaders, or open firmware ports where available.
- Clean hardware transplant or companion-camera builds when the original board is closed, app-only, or impractical to replace safely.

The project will not document or implement:

- Certificate pinning bypasses, mobile app patching, DRM/encryption bypasses, or protected-traffic interception.
- Credential extraction, desKey/device-key reuse, or publishing private device secrets.
- Exploit chains or authentication bypasses for the original firmware.
- Destructive flash writes without a verified backup and recovery path.

## Hardware Bring-Up Plan

1. Record the exact model, FCC ID, firmware version, and sanitized device capabilities.
2. Photograph both sides of each PCB and identify the SoC, camera sensor, flash chip, power rails, PIR sensor, microphone/speaker path, LED/IR/spotlight control, and battery/solar charging components.
3. Use public FCC exhibits and vendor manuals to cross-check model families before opening the device further.
4. Locate UART pads and observe boot logs with a logic analyzer or USB-TTL adapter at the correct voltage. Passive boot logging is allowed; do not attempt login bypasses.
5. Identify flash type and package. If reading flash, keep backups private and redact Wi-Fi credentials, cloud tokens, device IDs, keys, serials, and media URLs.
6. Look for documented update or recovery mechanisms, including SD-card updates if vendor support provides them.
7. Decide between:
   - native open firmware, if the SoC and sensor are supported by a maintained project;
   - a companion local stream bridge, if the vendor firmware can publish RTMP;
   - a hardware transplant, if the original board is closed or too brittle.

## Replacement Architecture

The preferred Home Assistant-native replacement stack is:

- camera source: RTSP/HLS from MediaMTX, OpenIPC, ESP32 camera firmware, Raspberry Pi camera, or another local source;
- event bus: MQTT or Home Assistant events;
- motion detection: PIR, frame differencing, Frigate, or another local detector;
- species detection: local inference service or model adapter;
- storage: optional local clips/snapshots with explicit retention settings;
- integration: Birdfy custom integration exposes camera, image, sensors, binary sensors, and events without depending on Birdfy cloud features.

## Consequences

This keeps the project aligned with owner control and privacy without making fragile or unsafe assumptions about Birdfy's proprietary app and cloud stack. It also gives the owner two practical paths: reuse the original camera board if it is open enough, or replace the board while keeping the enclosure, power system, PIR placement, and bird-facing mechanical design.

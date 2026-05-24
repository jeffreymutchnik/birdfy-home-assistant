# Changelog

## Unreleased

- Added a local RTMP/MediaMTX bridge guide for Birdfy models that support app-initiated livestreaming but do not expose direct LAN RTSP/ONVIF/snapshot endpoints.
- Added a local firmware/hardware bring-up checklist and ADR for pursuing owner-controlled operation without app-protection bypasses or credential extraction.
- Added a public hardware evidence matrix for known Birdfy/Netvue model families, FCC IDs, and open-firmware research clues.
- Added an owned-device hypothesis note that keeps private app device IDs out of hardware mapping while tracking the likely Birdfy Smart Feeder family.

## 0.1.5

- Added optional manual local stream and snapshot URL overrides for user-authorized camera media sources.
- Camera entities now prefer manual local media URLs before falling back to Birdfy/Netvue cloud-discovered media.
- Documented the local-video-first path for replacing Birdfy AI with a future private detection pipeline.

## 0.1.4

- Broadened real-device parsing aliases for online, firmware, battery, and Wi-Fi signal fields.
- Added redacted raw payload-shape diagnostics so hardware testers can share field names and safe status candidates without leaking identifiers or media URLs.

## 0.1.3

- Persist the Netvue web client identifier created during login and reuse it during Home Assistant setup, token refresh, and signed API requests.
- Added safe auth error metadata so reauth loops show which cloud operation/code failed without exposing tokens or device identifiers.
- Redact Netvue client identifiers from diagnostics and test fixtures.

## 0.1.2

- Matched token-refresh handling to the current public Netvue web client error codes.
- Trigger Home Assistant reauthentication when the cloud rejects a refresh token instead of retrying setup forever.
- Added clock-skew correction for signed API requests when Netvue returns an invalid-time response.
- Added regression tests for current token-expired codes, refresh-token rejection, and clock-skew retry behavior.

## 0.1.1

- Added support for wrapped Birdfy API responses that use `data` and `deviceList`.
- Improved setup failure messages with safe request context such as `device list (HTTP 503)`.
- Kept diagnostics and logs free of tokens, device IDs, and media URLs.

## 0.1.0

- Initial HACS-ready scaffold.
- Added standalone async `pybirdfy` client.
- Added Home Assistant config flow, reauth flow, coordinator, diagnostics, and read-only entities.
- Added camera snapshot/direct-stream fallback behavior.
- Added simulator, mocked fixtures, pytest coverage, and CI skeleton.
- Documented unsupported controls and hardware validation requirements.

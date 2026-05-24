# Changelog

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

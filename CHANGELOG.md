# Changelog

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

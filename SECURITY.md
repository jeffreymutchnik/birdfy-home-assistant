# Security Policy

Birdfy camera streams, snapshots, clips, event images, account tokens, device identifiers, and serial numbers are sensitive. Treat them as private home surveillance data.

## Supported Versions

This project is pre-release. Security fixes apply to the current `main` branch until a tagged release line exists.

## Reporting A Vulnerability

Do not open a public issue that includes credentials, tokens, serial numbers, device IDs, stream URLs, snapshots, videos, or private API responses.

If this repository has private security advisories enabled, report vulnerabilities there. Otherwise, contact the maintainers privately before posting details. Include:

- Integration version or commit.
- Home Assistant version.
- A short description of the risk.
- Minimal reproduction steps using redacted data.
- Whether the issue can expose live video, snapshots, clips, tokens, account details, or device identifiers.

## Security Boundaries

This project will not:

- Bypass encryption, DRM, certificate pinning, mobile app protections, or terms of service.
- Store account passwords after login.
- Persist snapshots, clips, thumbnails, or live video segments by default.
- Commit real credentials, tokens, serials, device IDs, snapshots, videos, stream URLs, or cloud media URLs.
- Expose siren, spotlight, microphone, speaker, privacy mode, detection settings, or other write controls without stable lawful API evidence and hardware validation.

## Implementation Requirements

- Use Home Assistant config entries and token refresh; do not support YAML-first password storage.
- Redact tokens, account names, serials, device IDs, snapshot URLs, stream URLs, image URLs, clip URLs, media URLs, and authorization headers in diagnostics and logs.
- Treat any media URL as a bearer secret, even if it looks temporary or signed.
- Do not include raw API payloads in logs. Log concise error categories instead.
- Use request throttling, timeouts, retries, and explicit rate-limit handling.
- Return unavailable or `None` for camera/media failures instead of surfacing raw responses.
- Prefer read-only entities unless a feature has passed hardware validation.

## User Hardening Guidance

- Do not expose Home Assistant directly to the public internet.
- Prefer Home Assistant Cloud, a VPN, or a carefully configured HTTPS reverse proxy.
- Enable account MFA in Birdfy/Netvue if available.
- Review diagnostics before sharing them.
- Avoid posting screenshots that show private camera views, exact location details, or identifiable people.

## Maintainer Checklist

Before release:

- Run unit tests, lint, typing, hassfest, HACS validation, secret scanning, dependency audit, and private artifact scanning.
- Confirm diagnostics redaction with real hardware data.
- Confirm logs do not include stream/snapshot/clip URLs.
- Confirm no hardware fixtures contain real user data.
- Document every unsupported feature honestly.

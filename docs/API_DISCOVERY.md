# Birdfy / Netvue API Discovery

Research date: 2026-05-14

## Summary

No official Birdfy/Netvue developer API documentation was found. Birdfy documents the mobile app, web client, cloud service, live viewing, AI recognition, and account-linked integrations with Alexa/Google, but not a public automation API.

The public Netvue web client at `my.netvue.com` exposes JavaScript references to:

- `users/login/v2`
- `auth/refreshtoken`
- `devices/v3`
- `devices/{serial}/services`
- `devices/{serial}/play`
- `pubstream`
- `sts/client`

These endpoints are treated as an undocumented cloud API surface. They are used only with credentials provided by the Home Assistant user.

## Safety Boundaries

This project does not:

- Bypass encryption, certificate pinning, app protections, DRM, or terms of service.
- Inspect private traffic captures.
- Commit credentials, device IDs, media URLs, snapshots, videos, or real account data.
- Expose write controls without stable lawful evidence and hardware validation.

## Feasibility Matrix

| Feature area | Status | Evidence | Implementation stance |
|---|---|---|---|
| Official API | Not exposed by API | Vendor docs and HA forum discussion show app/web usage but no developer API. | Document limitation. |
| Account auth | Probably supported | Netvue web client references login and refresh endpoints. | Implement user-authorized login and refresh. |
| Device list/status | Probably supported | Netvue web client references `devices/v3`; app docs show device list/status. | Implement read-only discovery. |
| Snapshot/thumbnail | Probably supported | App/web docs support screenshots; device payloads may expose image URLs. | Expose only when URL is present. |
| Live stream | Requires hardware validation | App/web support live view; web client references `play` and `pubstream`; community RTSP bridge exists. | Return direct URLs only; WebRTC/Kinesis unimplemented. |
| Motion/bird/species events | Requires hardware validation | Birdfy cloud/AI docs and community integrations show moments/highlights, but public web event page is not documented as a stable API. | Simulator-backed; poll real events only after endpoint validation. |
| Highlight/Recap share UUID | Confirmed supported externally | Community `homeassistant-birdfy` uses share links for read-only AI summaries. | Recommended future low-risk feature. |
| Battery/Wi-Fi/firmware/storage | Requires hardware validation | App settings display these; web payload likely includes some fields. | Expose only when present. |
| Siren/light/talk/privacy/settings | Unsafe/unsupported | App controls exist, but no stable public write endpoints were validated. | Do not expose in HA. |

## Vendor API Access Request

Hello Birdfy/Netvue team,

I am building a Home Assistant integration for Birdfy smart bird feeders and cameras. The goal is to let users access their own devices securely and privately from their local smart home system. Could you provide documentation or a developer API for:

- OAuth or token-based account authorization
- Device list and device status
- Snapshot and live stream URLs
- Motion/bird/species recognition events
- Battery, Wi-Fi, firmware, and storage metadata
- Supported read/write controls per model
- Rate limits, data retention, and privacy requirements

The integration will not bypass app protections or use unauthorized access. Official guidance would let the project avoid fragile undocumented behavior and provide users with safer controls.

Thank you.

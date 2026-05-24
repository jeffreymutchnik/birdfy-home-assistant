# ADR 0001: Use Unofficial Web API Conservatively

## Status

Accepted

## Context

Birdfy/Netvue does not publish an official Home Assistant or developer API. Public evidence confirms account-based app/web access, device lists, live view, snapshots, cloud moments, and AI recognition, but write-control endpoints are not documented.

The Netvue web client references account, device, service, and play endpoints. Community integrations also demonstrate read-only Birdfy data paths. These sources are useful but are not a contractual API.

## Decision

The integration uses a standalone async `pybirdfy` client for user-authorized web API access and exposes only conservative read-only Home Assistant entities by default.

Write controls are not exposed until they have:

- A stable lawful endpoint.
- Clear per-model capability evidence.
- Hardware validation.
- Safe failure behavior.

## Consequences

Users get account setup, device discovery, and read-only entities where data is available. Some app features remain unavailable in Home Assistant. The integration can be tested without hardware through fixtures and a simulator, and future hardware validation can add entities incrementally.

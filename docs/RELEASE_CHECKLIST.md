# Release Checklist

Use this before tagging any public HACS release. Do not release hardware-facing features that have not passed real-device validation.

## Version And Metadata

- [ ] Replace placeholder `documentation` and `issue_tracker` URLs in `custom_components/birdfy/manifest.json`.
- [ ] Confirm `manifest.json` version matches `pyproject.toml`, `CHANGELOG.md`, and the release tag.
- [ ] Confirm `hacs.json` metadata is valid.
- [ ] Confirm `README.md`, `info.md`, and `CHANGELOG.md` describe the same support level.
- [ ] Mark the release as beta if any camera/event behavior is validated on only one account/device.

## Security And Privacy

- [ ] Run Gitleaks or equivalent secret scanning.
- [ ] Run `python3 tools/check_no_private_artifacts.py`.
- [ ] Run `pip-audit --skip-editable --progress-spinner off`.
- [ ] Confirm no real snapshots, clips, stream URLs, serial numbers, device IDs, tokens, or account names are committed.
- [ ] Confirm diagnostics redact account, device, and media fields from real hardware data.
- [ ] Confirm debug logs do not contain raw request payloads or media URLs.

## Automated Checks

Run:

```bash
python3 -m pytest -q
python3 tools/check_no_private_artifacts.py
python3 tools/check_release_ready.py
python3 -m compileall -q pybirdfy custom_components tests tools
ruff check .
mypy pybirdfy custom_components/birdfy --ignore-missing-imports
pip-audit --skip-editable --progress-spinner off
```

When Home Assistant test dependencies are installed:

```bash
pytest -o asyncio_mode=auto tests/test_config_flow_ha.py
```

When Home Assistant validation tooling is available:

```bash
python -m script.hassfest --integration-path custom_components/birdfy
hacs validate
```

## Hardware Validation

- [ ] Complete `docs/HARDWARE_VALIDATION.md`.
- [ ] Save sanitized results using `docs/HARDWARE_TEST_RESULTS_TEMPLATE.md`.
- [ ] Confirm account login and token refresh.
- [ ] Confirm device discovery and device registry fields.
- [ ] Confirm offline device behavior.
- [ ] Confirm snapshot behavior.
- [ ] Confirm live stream response shape and whether it is direct RTSP/HLS/HTTP or WebRTC/Kinesis.
- [ ] Confirm event behavior for motion, bird, species recognition, and clip readiness.
- [ ] Confirm unsupported write controls remain hidden.

## Release Notes

- [ ] List confirmed supported models.
- [ ] List confirmed entities.
- [ ] List unverified and unsupported features.
- [ ] Include known limitations for unofficial API usage.
- [ ] Include privacy notes for camera/live video content.
- [ ] Include troubleshooting steps for auth, no devices, no snapshot, and no stream.

## Final Gate

Do not release if:

- [ ] Any scanner reports real private data.
- [ ] A write-control endpoint is unvalidated or app-only.
- [ ] Diagnostics leak tokens, serials, device IDs, or media URLs.
- [ ] Camera/media errors raise raw exceptions into Home Assistant.
- [ ] The README overstates support beyond validated API behavior.

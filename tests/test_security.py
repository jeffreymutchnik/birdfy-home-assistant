"""Security regression tests for camera/media privacy."""

from __future__ import annotations

import json
from importlib import util
from pathlib import Path

from pybirdfy.client import redact_data

TOOLS_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "check_no_private_artifacts.py"
TOOLS_SPEC = util.spec_from_file_location("check_no_private_artifacts", TOOLS_MODULE_PATH)
assert TOOLS_SPEC is not None
check_no_private_artifacts = util.module_from_spec(TOOLS_SPEC)
assert TOOLS_SPEC.loader is not None
TOOLS_SPEC.loader.exec_module(check_no_private_artifacts)
_find_private_media_urls = check_no_private_artifacts._find_private_media_urls

RELEASE_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "check_release_ready.py"
RELEASE_SPEC = util.spec_from_file_location("check_release_ready", RELEASE_MODULE_PATH)
assert RELEASE_SPEC is not None
check_release_ready = util.module_from_spec(RELEASE_SPEC)
assert RELEASE_SPEC.loader is not None
RELEASE_SPEC.loader.exec_module(check_release_ready)


def test_redaction_removes_camera_and_account_secrets() -> None:
    signed_host = "signed" + ".example.test"
    camera_host = "camera" + ".example.test"
    storage_host = "storage" + ".example.test"
    payload = {
        "authorization": "Bearer real-token-value",
        "refreshToken": "real-refresh-value",
        "serialNumber": "REAL_SERIAL",
        "deviceId": "REAL_DEVICE_ID",
        "userID": "REAL_USER_ID",
        "snapshotUrl": "https://" + signed_host + "/snapshot" + ".jpg?token=secret",
        "streamUrl": "rtsps://" + camera_host + "/live/secret",
        "clipUrl": "https://" + storage_host + "/clip" + ".mp4?signature=secret",
        "mediaUrl": "https://" + storage_host + "/media/event" + ".jpg",
        "nested": [{"imageUrl": "https://" + storage_host + "/image" + ".jpg"}],
        "safe": "keep-me",
    }

    encoded = json.dumps(redact_data(payload), sort_keys=True)

    assert "keep-me" in encoded
    for secret in (
        "real-token-value",
        "real-refresh-value",
        "REAL_SERIAL",
        "REAL_DEVICE_ID",
        "REAL_USER_ID",
        "signed.example.test",
        "camera.example.test",
        "storage.example.test",
        "signature=secret",
    ):
        assert secret not in encoded


def test_private_media_url_scanner_allows_documented_hosts() -> None:
    text = "\n".join(
        (
            "http://127.0.0.1:8765/media/snapshot.jpg",
            "rtsp://example.invalid/live",
            "https://support.birdfy.com/help/birdfy-app/Web%20Client/",
        )
    )

    assert _find_private_media_urls(Path("README.md"), text) == []


def test_private_media_url_scanner_flags_unknown_media_hosts() -> None:
    host = "real-camera" + ".example.test"
    url = "https://" + host + "/media/live" + ".m3u8?token=secret"
    findings = _find_private_media_urls(
        Path("debug.txt"),
        f"streamUrl={url}",
    )

    assert findings == [f"debug.txt:1: private-looking media URL {url!r}"]


def test_release_checker_flags_placeholder_urls() -> None:
    manifest = {
        "domain": "birdfy",
        "config_flow": True,
        "dependencies": ["stream"],
        "codeowners": ["@Jeff"],
        "documentation": "https://github.com/example/birdfy-home-assistant",
        "issue_tracker": "https://github.com/example/birdfy-home-assistant/issues",
    }

    findings = check_release_ready._check_manifest(manifest)

    assert "manifest.json 'documentation' still uses the example GitHub URL" in findings
    assert "manifest.json 'issue_tracker' still uses the example GitHub URL" in findings

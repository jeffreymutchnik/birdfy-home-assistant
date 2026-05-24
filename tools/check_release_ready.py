"""Release-only metadata checks for the Birdfy integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "birdfy" / "manifest.json"
HACS = ROOT / "hacs.json"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"


def main() -> int:
    findings: list[str] = []
    manifest = json.loads(MANIFEST.read_text())
    hacs = json.loads(HACS.read_text())
    version = manifest.get("version")

    findings.extend(_check_manifest(manifest))
    findings.extend(_check_hacs(hacs))
    findings.extend(_check_version(version))

    if findings:
        sys.stderr.write("Release readiness check failed:\n")
        for finding in findings:
            sys.stderr.write(f"- {finding}\n")
        return 1
    sys.stdout.write("Release metadata is ready.\n")
    return 0


def _check_manifest(manifest: dict[str, object]) -> list[str]:
    findings: list[str] = []
    for key in ("documentation", "issue_tracker"):
        value = str(manifest.get(key, ""))
        if not value.startswith("https://github.com/"):
            findings.append(f"manifest.json {key!r} must be a GitHub HTTPS URL")
        if "github.com/example/" in value:
            findings.append(f"manifest.json {key!r} still uses the example GitHub URL")
    if manifest.get("domain") != "birdfy":
        findings.append("manifest.json domain must be 'birdfy'")
    if manifest.get("config_flow") is not True:
        findings.append("manifest.json must declare config_flow true")
    dependencies = manifest.get("dependencies", [])
    if not isinstance(dependencies, list) or "stream" not in dependencies:
        findings.append("manifest.json must keep stream dependency for camera playback")
    if not manifest.get("codeowners"):
        findings.append("manifest.json must include at least one code owner")
    return findings


def _check_hacs(hacs: dict[str, object]) -> list[str]:
    findings: list[str] = []
    allowed_keys = {"content_in_root", "homeassistant", "name", "render_readme"}
    extra_keys = set(hacs) - allowed_keys
    if extra_keys:
        findings.append(f"hacs.json has keys rejected by HACS action: {', '.join(sorted(extra_keys))}")
    if hacs.get("name") != "Birdfy":
        findings.append("hacs.json name should be Birdfy")
    if hacs.get("content_in_root") is not False:
        findings.append("hacs.json content_in_root should be false")
    if not isinstance(hacs.get("homeassistant"), str):
        findings.append("hacs.json homeassistant should be a version string")
    return findings


def _check_version(version: object) -> list[str]:
    findings: list[str] = []
    if not isinstance(version, str) or not version:
        return ["manifest.json version must be a non-empty string"]
    pyproject_text = PYPROJECT.read_text()
    changelog_text = CHANGELOG.read_text()
    if f'version = "{version}"' not in pyproject_text:
        findings.append("manifest.json version does not match pyproject.toml")
    if version not in changelog_text:
        findings.append("manifest.json version is not mentioned in CHANGELOG.md")
    return findings


if __name__ == "__main__":
    raise SystemExit(main())

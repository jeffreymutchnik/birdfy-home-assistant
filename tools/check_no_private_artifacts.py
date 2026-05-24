"""Fail if private Birdfy camera artifacts are committed.

This check is intentionally conservative for a camera integration. It rejects
raw media files and non-approved media-like URLs so real snapshots, clips, and
signed stream links do not slip into fixtures, docs, or crash reproductions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "pybirdfy.egg-info",
}

DENIED_MEDIA_SUFFIXES = {
    ".3gp",
    ".avi",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".m3u8",
    ".m4v",
    ".mov",
    ".mp4",
    ".png",
    ".ts",
    ".webm",
}

APPROVED_URL_HOSTS = {
    "127.0.0.1",
    "localhost",
    "example.invalid",
    "localweb.nvts.co",
    "api2.nvts.co",
    "capi2.nvts.co",
    "capiv3.nvts.co",
    "developers.home-assistant.io",
    "support.birdfy.com",
    "community.home-assistant.io",
    "github.com",
    "owasp.org",
}

MEDIA_URL_HINTS = ("snapshot", "stream", "clip", "media", "video", "live", ".m3u8", ".mp4", ".jpg")
URL_RE = re.compile(r"""(?P<url>(?:https?|rtsp|rtsps)://[^\s"'<>),]+)""")


def main() -> int:
    findings: list[str] = []
    for path in _iter_files(ROOT):
        rel = path.relative_to(ROOT)
        if path.suffix.lower() in DENIED_MEDIA_SUFFIXES:
            findings.append(f"{rel}: raw media artifacts are not allowed")
            continue
        if _looks_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(_find_private_media_urls(rel, text))

    if findings:
        sys.stderr.write("Private Birdfy artifact scan failed:\n")
        for finding in findings:
            sys.stderr.write(f"- {finding}\n")
        return 1
    sys.stdout.write("No private Birdfy media artifacts found.\n")
    return 0


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _looks_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in chunk


def _find_private_media_urls(rel_path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for match in URL_RE.finditer(line):
            url = match.group("url")
            parsed = urlparse(url)
            host = parsed.hostname or ""
            url_lower = url.lower()
            if host in APPROVED_URL_HOSTS:
                continue
            if any(hint in url_lower for hint in MEDIA_URL_HINTS):
                findings.append(f"{rel_path}:{index}: private-looking media URL {url!r}")
    return findings


if __name__ == "__main__":
    raise SystemExit(main())

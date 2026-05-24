"""Safely collect a small, sanitized local-device connectivity snapshot.

The utility intentionally accepts one target IP address at a time. It does not
perform subnet discovery or credentialed requests.
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_PORTS = (80, 443, 554, 8554, 1935, 8000, 8080)
HTTP_PORTS = {80, 8000, 8080, 8888}
HTTPS_PORTS = {443, 8443}
RTSP_PORTS = {554, 8554}
MAX_PORTS = 32
CONNECT_TIMEOUT_SECONDS = 1.5
HTTP_TIMEOUT_SECONDS = 2.0
FFPROBE_TIMEOUT_SECONDS = 5.0

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authenticate",
    "proxy-authorization",
    "set-cookie",
    "www-authenticate",
    "x-api-key",
    "x-auth-token",
}

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")
LONG_ID_RE = re.compile(r"\b[A-Za-z0-9_-]{16,}\b")


@dataclass(frozen=True)
class PortCheck:
    port: int
    open: bool
    elapsed_ms: int
    error: str | None = None


def main() -> int:
    args = _parse_args()
    try:
        target = _parse_target(args.target)
        ports = _parse_ports(args.ports)
    except ValueError as err:
        sys.stderr.write(f"discover_local_device: {err}\n")
        return 2

    started = time.monotonic()
    checks = [_check_port(str(target), port, args.timeout) for port in ports]
    http_results = [
        _probe_http(str(target), check.port, check.port in HTTPS_PORTS)
        for check in checks
        if check.open and (check.port in HTTP_PORTS or check.port in HTTPS_PORTS)
    ]
    rtsp_results = []
    if args.rtsp:
        rtsp_results = [
            _probe_rtsp(str(target), check.port, args.rtsp_path)
            for check in checks
            if check.open and check.port in RTSP_PORTS
        ]

    result = {
        "target": "<redacted-ip>",
        "scope": "single-target",
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "ports": [check.__dict__ for check in checks],
        "http": http_results,
        "rtsp": rtsp_results,
        "notes": [
            "No subnet scan was performed.",
            "No credentials were sent.",
            "Target IP, MAC-like values, and long identifier-like values are redacted.",
        ],
    }

    if args.format == "json":
        sys.stdout.write(f"{json.dumps(result, indent=2, sort_keys=True)}\n")
    else:
        _print_text(result)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe one local device IP and print a sanitized connectivity snapshot."
    )
    parser.add_argument("target", help="single IPv4 or IPv6 address to check")
    parser.add_argument(
        "--ports",
        default=",".join(str(port) for port in DEFAULT_PORTS),
        help="comma-separated TCP ports to check; defaults to a small camera-oriented set",
    )
    parser.add_argument(
        "--timeout",
        default=CONNECT_TIMEOUT_SECONDS,
        type=float,
        help="TCP connect timeout in seconds",
    )
    parser.add_argument(
        "--rtsp",
        action="store_true",
        help="optionally run ffprobe against open RTSP ports when ffprobe is installed",
    )
    parser.add_argument(
        "--rtsp-path",
        default="/",
        help="RTSP path to probe when --rtsp is enabled; credentials are not supported",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="output format",
    )
    return parser.parse_args()


def _parse_target(raw_target: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        target = ipaddress.ip_address(raw_target)
    except ValueError as err:
        raise ValueError("target must be one IP address, not a hostname or subnet") from err

    if target.is_multicast or target.is_unspecified:
        raise ValueError("target must be a usable unicast IP address")
    return target


def _parse_ports(raw_ports: str) -> list[int]:
    ports: list[int] = []
    for raw_port in raw_ports.split(","):
        raw_port = raw_port.strip()
        if not raw_port:
            continue
        try:
            port = int(raw_port)
        except ValueError as err:
            raise ValueError(f"invalid port {raw_port!r}") from err
        if not 1 <= port <= 65535:
            raise ValueError(f"port {port} is outside 1-65535")
        if port not in ports:
            ports.append(port)

    if not ports:
        raise ValueError("at least one port is required")
    if len(ports) > MAX_PORTS:
        raise ValueError(f"refusing to check more than {MAX_PORTS} ports")
    return ports


def _check_port(target: str, port: int, timeout: float) -> PortCheck:
    started = time.monotonic()
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return PortCheck(port=port, open=True, elapsed_ms=_elapsed_ms(started))
    except OSError as err:
        return PortCheck(
            port=port,
            open=False,
            elapsed_ms=_elapsed_ms(started),
            error=type(err).__name__,
        )


def _probe_http(target: str, port: int, use_https: bool) -> dict[str, Any]:
    connection_class = http.client.HTTPSConnection if use_https else http.client.HTTPConnection
    scheme = "https" if use_https else "http"
    result: dict[str, Any] = {"url": f"{scheme}://<redacted-ip>:{port}/", "port": port}
    try:
        conn = connection_class(target, port=port, timeout=HTTP_TIMEOUT_SECONDS)
        conn.request("HEAD", "/", headers={"User-Agent": "birdfy-local-discovery/1"})
        response = conn.getresponse()
        response.read()
        result["status"] = response.status
        result["reason"] = _sanitize_value(response.reason)
        result["headers"] = _sanitize_headers(response.getheaders())
    except Exception as err:  # noqa: BLE001 - diagnostics should record broad probe failures.
        result["error"] = type(err).__name__
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return result


def _probe_rtsp(target: str, port: int, path: str) -> dict[str, Any]:
    result: dict[str, Any] = {"url": f"rtsp://<redacted-ip>:{port}{path}", "port": port}
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        result["skipped"] = "ffprobe not found"
        return result

    safe_path = path if path.startswith("/") else f"/{path}"
    command = [
        ffprobe,
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-show_entries",
        "stream=codec_type,codec_name,width,height",
        "-of",
        "json",
        f"rtsp://{target}:{port}{safe_path}",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        result["error"] = "TimeoutExpired"
        return result

    result["returncode"] = completed.returncode
    if completed.stdout.strip():
        result["stdout"] = _sanitize_value(completed.stdout.strip())
    if completed.stderr.strip():
        result["stderr"] = _sanitize_value(completed.stderr.strip())
    return result


def _sanitize_headers(headers: list[tuple[str, str]]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for name, value in headers:
        if name.lower() in SENSITIVE_HEADERS:
            sanitized[name] = "<redacted>"
        else:
            sanitized[name] = _sanitize_value(value)
    return sanitized


def _sanitize_value(value: str) -> str:
    value = IP_RE.sub("<redacted-ip>", value)
    value = MAC_RE.sub("<redacted-mac>", value)
    return LONG_ID_RE.sub("<redacted-id>", value)


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _print_text(result: dict[str, Any]) -> None:
    lines = [
        "Birdfy local device discovery",
        f"Target: {result['target']}",
        f"Scope: {result['scope']}",
        "",
        "Ports:",
    ]
    for check in result["ports"]:
        state = "open" if check["open"] else f"closed ({check['error']})"
        lines.append(f"- {check['port']}: {state}, {check['elapsed_ms']} ms")
    if result["http"]:
        lines.extend(["", "HTTP:"])
        for probe in result["http"]:
            status = probe.get("status", probe.get("error", "unknown"))
            lines.append(f"- {probe['url']}: {status}")
            for name, value in probe.get("headers", {}).items():
                lines.append(f"  {name}: {value}")
    if result["rtsp"]:
        lines.extend(["", "RTSP:"])
        for probe in result["rtsp"]:
            status = probe.get("returncode", probe.get("error", probe.get("skipped", "unknown")))
            lines.append(f"- {probe['url']}: {status}")
    lines.append("")
    for note in result["notes"]:
        lines.append(f"Note: {note}")
    sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

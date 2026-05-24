from __future__ import annotations

import pytest

from tools import discover_local_device


def test_parse_target_rejects_subnets_and_hostnames() -> None:
    with pytest.raises(ValueError, match="one IP address"):
        discover_local_device._parse_target("192.0.2.0/24")

    with pytest.raises(ValueError, match="one IP address"):
        discover_local_device._parse_target("camera.local")


def test_parse_ports_deduplicates_and_caps_scope() -> None:
    assert discover_local_device._parse_ports("80, 443,80") == [80, 443]

    too_many_ports = ",".join(str(port) for port in range(1, discover_local_device.MAX_PORTS + 2))
    with pytest.raises(ValueError, match="refusing"):
        discover_local_device._parse_ports(too_many_ports)


def test_sanitize_value_redacts_ip_mac_and_long_ids() -> None:
    value = (
        "device 192.0.2.10 mac aa:bb:cc:dd:ee:ff "
        "serial ABCDEFGHIJKLMNOPQRST stream ready"
    )

    assert discover_local_device._sanitize_value(value) == (
        "device <redacted-ip> mac <redacted-mac> serial <redacted-id> stream ready"
    )


def test_sanitize_headers_redacts_sensitive_headers() -> None:
    headers = [
        ("Server", "camera/1.0 192.0.2.20"),
        ("Set-Cookie", "session=secret"),
        ("WWW-Authenticate", "Basic realm=private"),
    ]

    assert discover_local_device._sanitize_headers(headers) == {
        "Server": "camera/1.0 <redacted-ip>",
        "Set-Cookie": "<redacted>",
        "WWW-Authenticate": "<redacted>",
    }

"""Small fixture server for Birdfy integration development.

Run with:
    python tools/birdfy_simulator.py
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00" + bytes([8] * 64) + b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\"\x00\x02\x11\x01\x03\x11\x01"
    b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07"
    b"\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xbf\x80\xff\xd9"
)
HLS_PLAYLIST = b"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:1
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:1.0,
segment0.ts
#EXT-X-ENDLIST
"""
TS_BYTES = b"SIMULATED_BIRDFY_TRANSPORT_STREAM_SEGMENT"


class BirdfySimulatorHandler(BaseHTTPRequestHandler):
    """Serve minimal Birdfy-like API responses."""

    server_version = "BirdfySimulator/0.1"

    def do_GET(self) -> None:
        if self.path.startswith("/v1/devices/v3"):
            self._json_fixture("devices.json")
        elif self.path.startswith("/v1/events"):
            self._json_fixture("events.json")
        elif self.path.startswith("/v1/devices/") and self.path.endswith("/services"):
            self._json({"cloud_storage": {"enabled": True}, "sdCard": True})
        elif self.path.startswith("/media/") and self.path.endswith(".jpg"):
            self._bytes(JPEG_BYTES, "image/jpeg")
        elif self.path.startswith("/media/") and self.path.endswith(".m3u8"):
            self._bytes(HLS_PLAYLIST, "application/vnd.apple.mpegurl")
        elif self.path.startswith("/media/") and self.path.endswith(".ts"):
            self._bytes(TS_BYTES, "video/mp2t")
        else:
            self._json({"ret": 404, "msg": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path.startswith("/v1/users/login/v2"):
            self._json_fixture("login.json")
        elif self.path.startswith("/v1/auth/refreshtoken"):
            self._json({"token": "REDACTED_TEST_ACCESS_REFRESHED", "refreshToken": "REDACTED_TEST_REFRESH_REFRESHED"})
        elif self.path.startswith("/v1/devices/") and self.path.endswith("/play"):
            self._json({"streamUrl": "http://127.0.0.1:8765/media/live.m3u8"})
        else:
            self._json({"ret": 404, "msg": "not found"}, status=404)

    def _json_fixture(self, filename: str) -> None:
        self._json(json.loads((FIXTURES / filename).read_text()))

    def _json(self, payload: object, status: int = 200) -> None:
        self._bytes(json.dumps(payload).encode(), "application/json", status=status)

    def _bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), BirdfySimulatorHandler)
    sys.stdout.write("Birdfy simulator listening on http://127.0.0.1:8765/v1/\n")
    server.serve_forever()


if __name__ == "__main__":
    main()

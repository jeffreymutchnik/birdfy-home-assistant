# Local Device Discovery Utility

Use `tools/discover_local_device.py` for repeatable, low-noise checks against a
single owned Birdfy or camera device on your local network. The tool is designed
for ad hoc hardware notes without committing private addresses, identifiers, or
credentials.

## Safety Defaults

- Requires one literal IP address. Hostnames and CIDR ranges are rejected.
- Checks only a small default TCP port set: `80,443,554,8554,1935,8000,8080`.
- Refuses custom lists larger than 32 ports.
- Sends no credentials, cookies, tokens, or authenticated URLs.
- Redacts the target IP, MAC-like values, and long identifier-like values in
  output.
- Runs RTSP probing only when `--rtsp` is supplied and `ffprobe` is installed.

## Examples

Write sanitized JSON:

```bash
python tools/discover_local_device.py 192.0.2.10 > local-discovery.json
```

Print a text summary:

```bash
python tools/discover_local_device.py 192.0.2.10 --format text
```

Check a narrow custom port list:

```bash
python tools/discover_local_device.py 192.0.2.10 --ports 80,554,8554
```

Optionally probe an open RTSP port with `ffprobe`:

```bash
python tools/discover_local_device.py 192.0.2.10 --rtsp --rtsp-path /
```

Use documentation-only example addresses such as `192.0.2.10` when sharing
results. Do not paste real IPs, MAC addresses, device IDs, media URLs, serials,
or account identifiers into issues, fixtures, docs, or commits.

## Output Shape

JSON output includes:

- `target`: always `<redacted-ip>`.
- `scope`: always `single-target`.
- `ports`: TCP connect results and elapsed milliseconds.
- `http`: unauthenticated `HEAD /` status and sanitized headers for open HTTP
  ports.
- `rtsp`: optional `ffprobe` metadata or sanitized probe errors for open RTSP
  ports.

The output is meant for local notes and issue triage. Treat it as a starting
point, not proof that a device supports local streaming.

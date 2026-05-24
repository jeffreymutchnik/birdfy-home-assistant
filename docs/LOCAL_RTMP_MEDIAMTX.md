# Local RTMP / MediaMTX Test Guide

This guide is for owned Birdfy devices where the Birdfy app exposes a **Live Stream** or RTMP feature. It does not require intercepting protected app traffic, bypassing DRM, disabling certificate checks, or guessing device credentials.

## Why This Path

Some Birdfy hardware does not expose RTSP, ONVIF, HTTP snapshot, or HLS directly on the LAN. Battery-powered cameras may answer ping while refusing every common media port. In that case, the safest local-video path is:

1. Run a local RTMP server you control.
2. Tell the Birdfy app to stream to that server, if the app and model support it.
3. Read the resulting stream from Home Assistant through RTSP or HLS.
4. Feed frames from Home Assistant or the stream URL into a future local bird-detection pipeline.

Netvue documents Birdfy RTMP/live streaming for selected models. The Birdfy app documentation says compatible devices show a **Live Stream** option in device settings. If the option is not present for a model/firmware/account, this project should treat app-initiated RTMP as unsupported for that device.

## Start MediaMTX

On a machine reachable from the Birdfy camera and Home Assistant:

```bash
docker run --rm -it \
  -p 1935:1935 \
  -p 8554:8554 \
  -p 8888:8888 \
  bluenviron/mediamtx:latest
```

Useful local URLs, replacing `HOST_IP` with the machine running MediaMTX:

```text
Birdfy app RTMP target: rtmp://HOST_IP:1935/birdfy
Home Assistant stream URL: rtsp://HOST_IP:8554/birdfy
Browser/HLS test URL: http://HOST_IP:8888/birdfy/
```

MediaMTX logs should show an RTMP publisher after the Birdfy app starts streaming. If nothing appears in the logs, the camera did not connect to the RTMP server.

## Configure Birdfy

In the Birdfy app:

1. Open the device.
2. Open device settings.
3. Look for **Live Stream**.
4. Enter the local RTMP URL.
5. Start the livestream from the Birdfy app.

Do not use public YouTube/Facebook stream keys for local testing. Do not paste real stream keys, media URLs, serial numbers, or MAC addresses into issues or diagnostics.

## Configure Home Assistant

After MediaMTX shows the stream is publishing:

1. Open **Settings > Devices & services > Birdfy > Configure > Options**.
2. Set **Manual local stream URL** to:

   ```text
   rtsp://HOST_IP:8554/birdfy
   ```

3. Submit options and reload the integration if Home Assistant does not refresh the camera immediately.
4. Open the Birdfy camera entity.

The custom integration redacts manual local stream and snapshot URLs from diagnostics because stream URLs can act like bearer secrets.

## Quick Verification

From a terminal on the same LAN:

```bash
ffprobe -v error -show_streams rtsp://HOST_IP:8554/birdfy
curl -I http://HOST_IP:8888/birdfy/
```

Expected result:

- `ffprobe` prints at least one video stream.
- MediaMTX logs show an active reader when Home Assistant or `ffprobe` connects.

## Troubleshooting

| Symptom | Likely cause | Next step |
|---|---|---|
| Birdfy app has no **Live Stream** option | Model, firmware, region, or account does not support RTMP | Treat RTMP as unavailable and continue with cloud event/snapshot validation. |
| MediaMTX logs show no RTMP publisher | Camera cannot reach the server or app did not start streaming | Confirm both devices are on the same LAN and the server firewall allows TCP `1935`. |
| MediaMTX receives RTMP but Home Assistant camera is gray | Home Assistant cannot reach RTSP or cannot decode the stream | Test `ffprobe rtsp://HOST_IP:8554/birdfy` from the Home Assistant host. |
| Stream works but has high delay | RTMP/HLS buffering and camera upload behavior | Prefer RTSP from MediaMTX into Home Assistant; use HLS only for browser checks. |
| Stream stops after a while | Vendor session limit, battery saving, or app-side livestream timeout | Record the duration and whether the app needs manual restart. |

## Security Notes

- Keep MediaMTX bound to your private LAN only.
- Do not port-forward RTMP, RTSP, HLS, or Home Assistant unless you have a deliberate security design.
- Use a unique path name instead of `birdfy` if the stream is on a shared LAN.
- Avoid recording unless explicitly needed for testing.
- Delete any captured frames or clips after debugging.

## Evidence

- Netvue support documents RTMP/live streaming and says compatible Birdfy devices are required.
- Birdfy app documentation says selected devices show **Live Stream** in device settings.
- MediaMTX supports publishing and republishing streams across RTMP, RTSP, HLS, WebRTC, and related protocols.

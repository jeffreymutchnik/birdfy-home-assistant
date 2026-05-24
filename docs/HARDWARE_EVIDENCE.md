# Birdfy / Netvue Hardware Evidence

This page collects public, non-secret evidence for Birdfy/Netvue hardware families. It is a map for owner-controlled local work, not proof that every unit in a model family can run open firmware.

## Model Families

| Family | Public IDs | Evidence | Local-control notes |
|---|---|---|---|
| Original Birdfy Camera | FCC `2AO8RNI-8202W`; model `NI-8202W`; variants `NI-8200` through `NI-8209` | FCC listing says `BIRDFY CAMERA NI-8202W` and publishes internal photos, manuals, block diagram, and reports. | Candidate for label/FCC cross-check. Exact SoC still must be confirmed from PCB photos. |
| Birdfy Smart Feeder | FCC examples include `2AO8RNI-8102W`, `2AO8RNI-8101`, and `2AO8RNI-8141A`; models include `NI-8100` through `NI-8109` in one filing | FCC/model-difference letters and manuals identify `BIRDFY SMART FEEDER` / `Birdfy Feeder` variants. | Most likely family when the app name is simply `Birdfy Feeder`, but the exact label/FCC ID is still required. |
| Birdfy Smart Nest | FCC `2AO8RNI-8301W`; models `NI-8300` through `NI-8309` | FCC reports identify `BIRDFY SMART NEST`; community notes mention board marking `MAT40N` for a related Nest device. | A plausible open-firmware research target if PCB photos confirm an Ingenic camera SoC and supported sensor. |
| Birdfy Feeder Bamboo | FCC examples include `2AO8RNI-8401` and `2BC96NI-8408`; models `NI-8400` through `NI-8409` in one similarity declaration | FCC/company listings show this as a separate feeder family. | Treat as separate hardware until PCB confirms otherwise. |
| Birdfy Nest Duo | FCC `2BC96NI-8321`; model `NI-8321` | Public FCC/device reports include internal-photo filing; a community teardown reports an Ingenic T40 processing board. | Promising for open-firmware research, but dual-camera and power-management details may complicate replacement. |
| Birdfy Cam 2 | FCC `2BC96NI-8601`; model `NI-8601`; manuals reference Feeder 2 model `NI-8602` sharing the camera family | Public device reports and manuals identify the Cam 2 generation. | Netvue documents RTMP livestream support for Birdfy Feeder 2 Series, so app-initiated RTMP should be checked before opening. |
| Birdfy Cam 2 Pro | FCC `2BC96NI-8611`; model `NI-8611` | Public device report identifies the Pro generation. | Check app **Live Stream** first; otherwise collect PCB evidence. |
| Birdfy Cam BA-series | FCC examples `2BC96NB-CMA01`, `2BC96NB-CMA04-0`; model examples `NB-CMA01`, `NB-CMA04-0` | Birdfy manuals identify `Birdfy Cam BA3A` as `NB-CMA01`; device reports list multiple BA camera modules. | Newer modular camera path. Treat each module as its own board family. |

## Public SoC Clues

Community hardware reports point in two different directions:

- Some Birdfy/Netvue logs identify a `Hi3861` Wi-Fi/RTOS component. This may be a low-power network/housekeeping side, not the main image processor.
- A later discussion and teardown notes point to an Ingenic `T40`/`MAT40N` processing board on at least one Nest-family device.

That means a UART log from one connector may describe only the Wi-Fi module. A separate UART, flash chip, or SoC marking may be needed to identify the real camera processor.

## Current Owned-Device Hypothesis

The owned device is reported in the app as **Birdfy Feeder**. The private app
device ID is not useful for public hardware mapping and should stay out of docs,
issues, and commits.

Based on the generic app name, the leading hypothesis is the Birdfy Smart Feeder
family. Public manuals/FCC records show several nearby feeder identifiers,
including `NI-8102W`, `NI-8101`, and newer `NI-8141A` manuals. Confirm the
physical label before assuming board compatibility.

The latest sanitized local discovery result for the owned feeder found no open
TCP service on `80`, `443`, `554`, `8554`, `1935`, `8000`, or `8080`; no
credentials were sent. This reinforces the current assumption that this unit
does not expose direct pull-based LAN RTSP/ONVIF/snapshot media while idle.

## Open Firmware Outlook

OpenIPC supports many IP camera SoC families, including Ingenic T20/T21/T30/T31/T40 and multiple HiSilicon generations. That is encouraging but not sufficient. A working port still depends on:

- exact SoC variant;
- camera sensor model and driver support;
- flash type and partition layout;
- bootloader access or safe flashing path;
- Wi-Fi and power-management architecture;
- recovery path if flashing fails.

No confirmed public OpenIPC or Thingino port for a Birdfy model has been found yet.

## Next Evidence To Collect

For the owned unit, collect and store privately:

- exact model and FCC ID from the label;
- app camera name and firmware version;
- whether the Birdfy app shows **Live Stream**;
- high-resolution PCB photos;
- readable SoC, Wi-Fi module, flash, PMIC/charger, and image-sensor markings;
- passive UART boot logs with SSID, password, device ID, keys, serials, and account identifiers redacted.

After that, compare the SoC and sensor against OpenIPC/Thingino support before deciding whether firmware replacement or a camera-module transplant is more realistic.

## Sources

- FCC ID `2AO8RNI-8202W` listing for `BIRDFY CAMERA NI-8202W`: <https://fccid.io/2AO8RNI-8202W>
- FCC model-difference letter for `2AO8RNI-8102W`: <https://fcc.report/FCC-ID/2AO8RNI-8102W/6787888.pdf>
- FCC ID `2AO8RNI-8102W` listing for `BIRDFY SMART FEEDER NI-8102W`: <https://fccid.io/2AO8RNI-8102W>
- Birdfy Feeder manual with `FCC ID: 2AO8RNI-8141A`: <https://support.birdfy.com/img/products/birdfy-feeder-manual.pdf>
- FCC / company listing for Netvue device families: <https://www.fccinsights.com/netvue-technologies-co-ltd>
- Birdfy Cam BA-series device reports: <https://device.report/birdfy/cam>
- Birdfy Feeder Metal S manual identifying `NB-CMA01`: <https://support.birdfy.com/img/products/product-manual/birdfy-feeder-metal-s-manual.pdf>
- Netvue RTMP livestream support article: <https://support.netvue.com/hc/en-us/articles/41039979574553-How-to-Live-Stream-Your-Birdfy-Camera-on-YouTube>
- Community Birdfy UART report: <https://www.reddit.com/r/hardwarehacking/comments/1jg4e5l/netview_camera_uart_question/>
- OpenIPC SoC support overview: <https://deepwiki.com/OpenIPC/firmware/5-soc-support>
- OpenIPC supported hardware list: <https://openipc.org/supported-hardware/full-list>

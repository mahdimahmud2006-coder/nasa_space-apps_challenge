# Offline demo runbook

1. From this folder, run `make demo` (or `OFFLINE=1 python3 -m src.api.app` with the included compact public assets). Open `http://127.0.0.1:8000/`.
2. The default comparison is **August 19 → September 12, 2026**. Show Before, After and Swipe; drag the slider.
3. Press **SCAN REGION**. The sweep reveals saved deterministic evidence; it does not run science in the browser. Read **0.7949 km²** and **30** nominal candidate regions.
4. Inspect a region: nominal area, median signed ΔdB, peak absolute change, robust area, descriptive temporal class and **UNVERIFIED** validation status. The top ten ranked regions have individual UNOSAT source review notes. Click a map polygon or a region button, then center on the region.
5. Turn on **Show robust candidate core**. Read **0.4174 km²**, retained within **14 nominal regions** as **20 connected strict components**. Toggle back to nominal. The threshold sensitivity rows show −10%, nominal and +10% areas; these are not confidence intervals.
6. Select August 19 → August 31: **0.0195 km²**, one region. Select August 31 → September 12: **0.0000 km²**, zero nominal retained regions. Explain that the −10% cutoff retains **0.0111 km²**, and a zero nominal result does not establish no physical change.
7. Open **Methodology** for source granule IDs, HH measurement, dates, grid, cutoff, cleanup and limitations. Download the pair-specific evidence JSON if asked. The validation source link is optional and requires internet; the demo itself does not.

For the required **physical disconnected rehearsal**, the user must close the app, disable Wi-Fi and any Ethernet connection, then start `make demo` and repeat steps 1–7. In developer tools, verify that no required external page assets fail. Record date, machine, browser, result and `wifi_physically_disabled: true` in `docs/QA.json` **only after actually performing it**. The implementation cannot verify the machine's physical network state from the local app; current QA leaves this false.

If raw data changes, run `make inspect`, `make test`, `make process`, and `make validate`. Keep raw HDF5s out of the browser and public repository. The candidate radar change must never be described as a confirmed disaster.

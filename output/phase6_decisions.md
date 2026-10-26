# Phase 6 decisions log

Decisions made while working overnight without the user (per the Phase 6 prompt). **Q** marks a call I would normally have asked about.

## Before Phase 6
1. **Branch:** the Phase 5 stress test was committed on `main` (as asked, "commit"); everything after that, including the three Phase 5 fixes, is on the `phase6` branch.
2. **Phase 5 fixes 1–3 done, plus fix 4** (sold listing wording, ~5 lines) because Phase 6 makes "sold" real. Re-run: `stress_phase5.py` 9/9, `test_two_sided.py` 17/17, MCP smoke 89/89.
3. **The first race test case was wrong, not the app:** Tidewater already had need #20 that the new impeller kit also fills (family match), so it was alerted through #20. The pre-filter shows each buyer's most urgent fitting need, so a second need of the same buyer adds no new alert pair. The race case now uses a buyer whose only fitting need is the new one (Riverbend DI cards vs a new DI listing). **Q:** should a buyer with two fitting needs get one alert per need? I kept one per listing (less noise).

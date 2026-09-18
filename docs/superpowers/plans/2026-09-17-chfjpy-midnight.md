# CHFJPY midnight entry design and implementation

Deployment note (2026-09-19): the user confirmed keeping the current 01:00
MT5-time entry for main. This plan records the earlier midnight experiment;
opening-entry mode remains available for research and is not selected live.

User explicitly requested entry at the start of the 00:00 candle and a new backtest.

Design: retain the completed-candle interface for ATR and legacy research. Add an
explicit opening-entry option to the selected CHFJPY configuration. Use the fresh
quote's hourly boundary for the session clock, including weekend gaps; do not read
forming candle OHLC. Use the actual entry date for daily rails and duplicate checks.
Keep the existing 60-second freshness window, sizing, demo-only guard, and 12-hour
position-age exit. Polling implies first available poll, not guaranteed zero latency.

- [x] Verify configured strategy and local process status.
- [x] Add failing midnight-boundary and configuration tests, then implement.
- [x] Add failing opening replay tests: entry-candle stop and noon exit before low.
- [x] Add failing weekend tests, then use current entry clock with prior history.
- [x] Verify midnight sizing/date handling with ordinary and weekend history.
- [x] Replay old and new timing with identical costs and research risk rules over
  2016–2025, September 2025–August 2026, and July–August 2026, with 2.5/5-pip spreads.
- [x] Save ledgers, monthly results, source hashes and limitations.

Verification commands: `.venv/Scripts/python -m pytest -q` and
`.venv/Scripts/python -m research.chfjpy_midnight_recheck`.
No process startup, account connection or orders are part of this change.

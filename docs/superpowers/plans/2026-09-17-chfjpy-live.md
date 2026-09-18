# CHFJPY live strategy implementation plan

**Goal:** Make the approved CHFJPY H1 session strategy the sole selection in the demo-only live runner.

**Architecture:** Restore a pure session signal in the existing registry. Add MT5-specific entry sizing and session eligibility checks, and poll position opening timestamps for 12-hour exits. Keep BOS available for historical research. Work on the existing dirty workspace without reverting its changes; do not start a trading process.

**Tech stack:** Python, pandas, MetaTrader5, pytest.

Approved behavior: long after the broker-labelled hour-0 H1 candle closes, simple ATR14 times two stop, no take-profit, 12 elapsed hours from actual entry, 1% equity risk, maximum one position and one lot, fixed $10,000 baseline with existing 3% daily / 6% total entry halts. Broker timezone labels retain research semantics; market-session/UTC mapping is not independently established.

- [x] Restore session signal and test hour selection, warmup, true range, invalid input, and no TP (`trader/strategies/session.py`, `trader/config.py`, registry, `tests/test_session.py`).
- [x] Test then implement MT5 sizing from executable ask/bid and `order_calc_profit`, broker volume constraints, failure-closed calculations, fresh-entry window and history-based duplicate prevention (`trader/broker_mt5.py`, `trader/engine.py`, `tests/test_chfjpy_live.py`).
- [x] Test then implement poll-time exits using recovered broker timestamps; ensure exits run while entry risk is halted and before new signals (`trader/live.py`, `tests/test_chfjpy_live.py`).
- [x] Select only CHFJPY in `run_live.py`; preserve explicit GOLD research config compatibility, update README and registry assertions. Test runner selection without connecting to MT5.
- [x] Run `.venv/Scripts/python -m pytest tests -q`, independent review, and inspect final diff. No account orders or process restart during verification.

Sizing reference: https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py (returns account-currency profit). Preserve current entry-halt rail semantics; this change does not claim parity with research liquidation guards or fees.

Verification: 191 tests passed on 2026-09-17; git diff --check passed (line-ending warnings only). Independent review identified fractional ATR stop prices; corrected by rounding to broker tick size before sizing and verified through a captured order request. Changes remain uncommitted on codex/chfjpy-live; no trading process was launched or restarted.

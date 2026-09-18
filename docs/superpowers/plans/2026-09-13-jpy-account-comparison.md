# JPY account-size comparison implementation plan

User-authorized scope: CHFJPY and EURJPY, exact existing hour-0/12-hour long signal, 1% target risk, separate $10,000 and $50,000 accounts, Jan-Dec 2016-2025 and continuous Sep2025-Aug2026 monthly results. Offline research only.

Architecture: preserve earlier simulator/results. Add `research/jpy_guarded_session.py` for the revised balance-parametric replay and `research/jpy_account_comparison.py` for data loading, runs, ledgers and reporting. Use existing `signal_inputs` unchanged.

- [x] Test sizing/cost conversion at both balances, no-lookahead timing, floating threshold liquidation, daily reset, pre-entry drawdown headroom, and gap handling in `tests/test_jpy_guarded_session.py`.
- [x] Implement replay with 1% balance risk, 0.01 lots, scaled historical caps (1 lot/$10k), 2.5-pip baseline and 5-pip sensitivity, 0.1-pip slippage per fill, $14/lot total commission. USDJPY previous close for intrabar conversion and contemporaneous close for timed exits. Include liquidation-cost reserve in floating equity.
- [x] Use $300/$600 and $1,500/$3,000 daily/static internal allowances. Reject full-risk entries that do not fit remaining drawdown headroom; monitor open/low/close conservatively, liquidate at internal guard if above SL, gap at executable open. Record all threshold breaches and blocked-entry counts. Day anchor is realized balance at dataset midnight. These are modeled guardrails, not certified FundedNext compliance.
- [x] Run both pairs, two balances, eleven windows, two spread profiles; keep annual fresh starts distinct from a continuous latest year. Do not scale $10k outcomes algebraically.
- [x] Reconcile every saved ledger, four annual means, monthly totals and account balances; inspect gaps and rule events. Compare old simulator control under old $7 assumptions against saved screen for data parity.
- [x] Write `docs/2026-09-13-jpy-account-comparison.md` with complete tables, costs, limitations and reasons earlier results differ. Include that $50k FundedNext automation is prohibited by current published policy; actual quotes/timezone/news/swaps remain unverified.

Validation commands: `.venv\Scripts\python.exe -m pytest tests/test_jpy_guarded_session.py tests/test_jpy_session_recheck.py tests/test_risk.py -q`; `.venv\Scripts\python.exe -m research.jpy_account_comparison`.

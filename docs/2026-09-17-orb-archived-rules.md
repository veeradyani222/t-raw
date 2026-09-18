# Archived gold ORB rules and comparison context

Read-only source investigation on 17 September 2026. No terminal connection or live change. Git object notation below is an exact local citation, inspectable with `git show COMMIT:path`.

## Which version

The last pre-BOS deployment tree is `6b0d185179702e7f85ef43becddd189c4570300a` (`c5290c7^`). Its `run_live.py`, `trader/config.py`, `trader/strategies/orb.py`, `trader/engine.py`, and `trader/sim.py` are unchanged from `665430a295ecfffb8baecd91c7e0eab48cc33a4d`, verified with `git diff 665430a c5290c7^ -- ...`. `f81bf7b8b5d55ba99929824b1f761a87ed402916` also contains the same gold rules. BOS replaced ORB in `c5290c7:run_live.py`.

## Exact gold configuration

Source: `6b0d185:run_live.py` GOLD and RAILS; inherited defaults from `6b0d185:trader/config.py`.

| Parameter | Value |
|---|---|
| Symbol / timeframe | XAUUSD / H1 |
| Session start / box | hour 1 in candle timestamps / first 3 available candles |
| Structure confirmation | enabled; fractal window 2 each side |
| Volume confirmation | disabled; inherited multiplier 1.2, lookback 20 |
| Target | structure, minimum distance 1R, fallback 3R |
| Pip size / value / modeled spread | 0.1 / $10 per pip per lot / 3 pips ($0.30) |
| Risk / position cap | 1% equity / one gold position |
| Sizing | floor to 0.01 lot; minimum 0.01, maximum 1 lot |
| Rails | fixed $10,000 baseline; $300 daily; $600 permanent static loss; trailing halt disabled |

The deployed launcher also traded USDJPY and shared account equity/rails. A gold-only replay isolates ORB and is not a replay of the full deployed portfolio. (`6b0d185:run_live.py`, `6b0d185:trader/live.py`.)

## Signal and exit semantics

Source: `6b0d185:trader/strategies/orb.py`.

- H1 lookback is **86 completed bars**: `3 * ((26*60)//60) + 3 + 5`. Do not silently replace 26 with 24.
- Box uses max high/min low of the first three available candles starting at the latest date with an hour-1 candle. Regular labels are 01:00, 02:00, 03:00; first candidate is the completed 04:00 candle, ordinarily acted on around 05:00. Missing bars are not synthesized, and no requirement checks that the chosen session belongs to the latest candle's date.
- Long: latest close strictly exceeds both its open and box high, with no earlier post-box close above the box. Short mirrors this. A prior crossing close consumes that side even if its candle direction was wrong, confirmation vetoed it, or risk/position rules skipped entry. There is no retry on a later breakout bar.
- Confirmed swing highs/lows must strictly dominate two bars on each side. Long requires last two swing lows rising; short requires last two swing highs falling. Fewer than two relevant swings passes. The latest candidate candle can confirm a swing two bars earlier; future bars are never used.
- SL is the opposite box boundary. R is measured from signal close to SL. Structure TP searches confirmed swings in reverse chronological order for the first level at least 1R beyond entry. This is the most recent qualifying level, not the closest level. If none qualifies, use 3R. Structure targets can exceed 3R.
- No ORB scheduled exit, midnight flatten, trailing stop, breakeven rule, or partial profit. Positions can cross days/weekends. An opposite **qualified** signal closes the held position before checking permission to open its replacement; blocked signals do not close it. A same-side held position prevents another entry. (`6b0d185:trader/engine.py`, `6b0d185:trader/live.py`.)

## Execution parity pitfalls

The archive simulator enters at signal close plus spread for longs, minus spread for shorts; exits at signal close on reversal, exact SL/TP on subsequent candles, and stop wins ambiguous bars. Final positions are marked at final close. It charges no commission, swap, slippage, or gap penalty. It sizes from signal close, before the adverse entry spread, so stopped loss can exceed the nominal 1%. It checks closed balance, while live polls floating equity every ten seconds. The archive's guards prevent new entries; they do not automatically liquidate ORB holdings. Engine reversal captures equity before closing the old position and does not rerun the guard after that close. These quirks belong in an exact reproduction, with any improved execution model separately labeled. (`6b0d185:trader/sim.py`, `6b0d185:trader/engine.py`, `6b0d185:trader/risk.py`, `6b0d185:trader/live.py`.)

Historical simulator max-drawdown calculation does not prepend starting equity to the cumulative trade equity series. Recompute drawdown including initial capital for reporting, while preserving trade execution. Warmup must feed indicators without placing orders before the intended fresh-start boundary. (`6b0d185:trader/sim.py`.)

Archived tests cover first-breakout-only, mirrored long/short box stops, structure and volume vetoes, structure TP/fallback, and metadata propagation: `6b0d185:tests/test_strategies.py`, `6b0d185:tests/test_orb_v2.py`. This inspection did not execute those archived tests.

## Existing comparison evidence

- BOS calendar 2026 continuous account, started Jan 1 with $10,000, no withdrawals: July **+$211.99**, 31 trades; August **-$183.73**, 18 trades; Sep 1-11 **-$359.16**, 13 trades. These are monthly slices of an already-running account, not fresh $10,000 starts. Source: [2026 monthly ledger](../logs/bos-calendar-years-20260913/2026/none-monthly.csv), [method](2026-09-13-bos-calendar-year-results.md).
- Different BOS rolling window Aug 12-Sep 11, fresh $10,000: **-$466.60**, 28 trades, nine wins; preceding Jul 12-Aug 11 fresh window **+$113.65**, 27 trades. Do not label these as calendar August/July. [Diagnosis](2026-09-12-bos-monthly-loss-diagnosis.md).
- BOS 2019-2025 independent calendar starts without withdrawals: **one profitable year out of seven**, six internally halted, mean **-$123.25/year**. Current settings were historically selected; these are conditional historical outcomes, not forecast probabilities. [Calendar results](2026-09-13-bos-calendar-year-results.md).
- The more complete CHFJPY account model ($14/lot round-trip commission, headroom checks and floating liquidation approximation) shows **four profitable years out of ten** for independent 2016-2025 $10,000 starts; the other six years lost and encountered static-guard/headroom constraints. Mean **+$157.05/year**. The latest Sep 2025-Aug 2026 continuous run earned **+$5,294.44**, including July **+$175.56**, August **+$523.00** and March **-$807.64**. At 5-pip spread, latest-year net falls to **+$3,429.57**. These are different costs and capital paths from BOS/archived ORB. [Account comparison](2026-09-13-jpy-account-comparison.md).
- Earlier, simpler CHFJPY pair screen: six of ten years permanently halted at base costs, eight of ten at wide spread, annual wide-spread mean **-$352.06**. Those halt counts belong to its older balance-only/$7-commission model and must not be mixed with the later model's headroom stops. [Pair screen](2026-09-13-jpy-pair-screen.md).

The historical record supports describing both as regime-sensitive. Choosing CHFJPY because it recently won while BOS lost is retrospective selection; it does not itself demonstrate a durable improvement. No investment recommendation or claim about future success is established by these archived tests.

## Independent audit of the September 17 replay

Inspected [replay source](../research/orb_recent_recheck.py) and [saved results](../logs/orb-recent-recheck-20260917/results.json). All 26 relevant configuration values independently matched literal archived Config defaults plus archived RAILS/GOLD overrides. The replay currently derives non-ORB defaults/rails from current GOLD; these match the archive today, but changing current GOLD could alter a later reproduction. Archived ORB source is loaded with only its relative strategy-type import rewritten.

Current `trader/sim.py` and `trader/risk.py` match `665430a` executable AST exactly. Current engine changes add session-only branches; ORB/BOS avoid these. To independently verify that reasoning, loaded the actual archived engine and reran all six ORB windows/profiles: **all 82 saved ORB trade rows matched in every column**. Every ORB trade's signed price change times 100 ounces times lots matched profit, with cumulative balance reconciled.

All 18 run summaries and **466 trade rows** independently reconciled profit arithmetic, win counts, final balances, cumulative balances and closed drawdown including initial capital. CHFJPY checks independently included JPY/USD conversion and $14-per-lot fees. All six continuous July-August runs reconcile exactly to their two monthly slices. Fresh monthly runs must not be added to reproduce continuous returns: they reset capital/positions, and the July fresh run marks remaining exposure at July-end while continuous runs carry it.

Fresh runs create an empty broker and new guard, only loop within the requested interval, and expose preceding historical candles solely for signal warmup. No entry precedes the interval; final marks occur before its exclusive end. The engine strategy lookup is patched within a context manager and restored on exit; the production strategy registry is never modified. Input helpers read cached CSV files; the replay does not call the MT5 connection or live loop.

Continuous base July-August nets: ORB **+$24.92**, BOS **-$132.76**, CHFJPY **+$473.34**. Fresh August: ORB **-$193.55**, BOS **-$233.04**, CHFJPY **+$351.10**. These demonstrate the saved historical outcomes, not an execution-normalized ranking: gold retains archived close/spread-only execution and balance entry halts, while CHFJPY includes commission/slippage, FX conversion, gap pricing, entry headroom checks and floating-equity guard exits. CHFJPY research guard liquidation also differs from the deployed live entry-halt policy. A headline that CHFJPY is proven superior or safer would therefore overstate this comparison. July-August are the last two *complete calendar months*, not the latest trailing two months through September 17.

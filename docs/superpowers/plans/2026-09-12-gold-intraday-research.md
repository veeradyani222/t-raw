# Gold intraday research plan

**Goal:** Screen a few fixed gold intraday strategies for recent-month and year profitability under user-confirmed 4% daily / 8% total external limits and 3% / 6% internal buffers. Research only; production stays BOS-only.

**Data:** MT5 bid OHLC with tick_volume and spread in points; point=0.01, contract=100 oz, lot step/min=0.01. M5: 2025-04-07 onward; M15: 2024-02-20 onward; M1: 2026-05-28 onward. A full-year M1 result is unavailable. Study dates 2025-09-12 through 2026-09-11; recent month 2026-08-12 through 2026-09-11. Indicators use prior context; trading starts flat at each evaluation start.

**Fixed candidates before viewing results:** channel breakout20 + MA200 (both directions and long-only); EMA20 pullback in EMA50/200 trend; Bollinger20 re-entry in ADX14<20 range; 20-bar liquidity sweep/reclaim with MA200; compression/channel expansion; existing BOS+CMF20+MA200 baseline. Same rules on M1/M5/M15. No parameter grid or repeated tuning to the report month.

**Screenshot addition before screening:** LuxAlgo Trendlines with Breaks, length14 / multiplier1 / ATR, with and without EMA200 direction filter. Confirm pivots after14 bars; first closing-price break of the current projected boundary; no backpainted entries. Added trading wrapper: 1.5 ATR stop, 2R target, 180-minute maximum holding period. No RSI/TRAMA filter. Indicator parity against TradingView has not been certified.

**Execution:** Signal on completed candle; fill at next bar open. One position. Stops/targets, adverse-first intrabar approximation, adverse gap fills, floating-equity tracking. Cost floor $0.30 gold-price spread or observed bar spread if larger; $7/lot round-trip commission and $0.03/oz adverse slippage per market fill are assumptions. Stress floor $0.60, $10/lot commission, $0.10 slippage. No opening when observed spread exceeds $0.60. All positions are intraday, entries 07:00-18:59 and forced close at 20:00 in dataset timestamps; no planned rollover exposure. Reset day at 00:00 in dataset timestamps, matching current code; exact firm timezone/news rules remain unverified.

**Risk:** Start $10,000. 0.25% per trade primary; test 0.5% only after identifying stronger candidates. 3% daily loss measured from day-start equity, static 6% floor off starting baseline; separately count 4%/8% breaches. Size includes spread, slippage and fees, capped at 1 lot and remaining loss headroom. Internal limits block entries; existing stops still apply. Report conservative floating drawdowns and daily losses. OHLC cannot certify real tick-level or firm compliance.

**Validation:** Simulator tests for no same-bar signal fill, bid/ask costs, gap stops, stop-first ties, intrabar loss limit, day reset, permanent halt, risk sizing and end accounting. Candidate tests for causal signals and body-based entry confirmations. Freeze first-11-month ranking before inspecting final month; publish all attempts. For leaders: higher-cost and risk-size stress, fresh monthly-start sensitivity. Month overlaps year and is not independent evidence; source notes discuss selection bias.

- [x] Implement/test isolated research simulator.
- [x] Implement/test fixed candidate signals and study runner.
- [x] Run all candidate/timeframe windows; audit leaders under stress and new starts.
- [x] Independently review simulator and report accounting, data coverage, all outcomes and limitations.

**Outcome:** 147 simulations reconciled; 112 repository tests passed. No first-11-month candidate qualified. M15 EMA pullback's small positive year reversed under cost stress. M5 trendlines had a positive fresh recent month but stalled near the loss buffer during the year. See [complete results](../../2026-09-12-gold-intraday-results.md). Historical gaps and unverified firm-specific terms limit the conclusions.

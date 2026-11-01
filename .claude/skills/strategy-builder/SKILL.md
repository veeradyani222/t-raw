---
name: strategy-builder
description: How strategies are built, judged and admitted to a mix in mt5-trader (prop-firm rules, honest out-of-sample judging, what has already failed). Use before designing, testing or sizing any trading strategy or mix in this repo.
---

# Strategy builder

The judge is `research/search5/core5.py` (full-history 1% sims, dev / unseen periods, $5K and $10K replays
with the live daily stop and the challenge counter). The rule engine is `research/search6/engine.py`.
Everything tested so far is on the scoreboard: `docs/board/scoreboard.csv`. Check it before testing an idea again.

## Non-negotiables
1. **Pick on dev, report on unseen.** dev = 2015-01-01..2023-10-20. Any selection, parameter choice or size is
   decided on dev only. Report unseen yr (Oct 2023..Oct 2024), last 2y (Oct 2024..Oct 2026) and Sep+Oct 2026
   separately, and say when a number comes from a window the strategy was picked on. The round-3 pool and
   the live 66/24 were picked on the last 2 years: that column is a fit period for them.
2. **Costs always on.** Spread floor or the bar's spread, slippage, $14/lot round trip on FX and metals.
   Price-action grids that looked fine before costs died after them (round 4).
3. **One source, one market.** A strategy from a gold video runs on XAUUSD at the video's timeframe. Never
   spray one rule across every pair; the test count explodes and false positives with it.
4. **Plateau, not peak.** A parameter only counts if its neighbours also work. 40,020 hour-pair tests gave a
   best t-stat of 3.2, which is what noise produces at that count.
5. **Enough history.** Markets with bars only from 2022 (EURUSD, USTEC) or 2025 (exotics, AUS200, SOL, XRP)
   cannot be judged honestly; say so instead of reporting their 2-year numbers.
6. **Runs live or it does not count.** Own symbol's bars only; no second-market inputs (Brent/WTI, gold/silver
   ratio fail live); every entry has a stop; no martingale, grid or scaling in.

## Admission to a mix (what "steady" means)
- 4+ dev years, at least half of them green, dev $/month > 0, 60+ dev trades: the relaxed rule.
- 5+ dev years and 80% green: strict.
- Size equal across strategies, chosen on dev: largest level that keeps the $5K dev lowest balance >= $4,750
  and <= 12 stop days a year. Per-strategy optimised sizes are fitting.
- $5K facts: risk per trade is ~$15 at 0.30%; daily-timeframe FX/index strategies cannot fund one minimum
  lot at that size and silently trade nothing. The $125 daily close-all dominates everything: adding
  strategies adds stop days before it adds profit.

## Already dead (do not re-test without a new angle)
- Volatility-regime gates on existing strategies (gold gate 2026-10-30; 52-strategy ATR filter 2026-11-01).
- Time-of-day holds per market (round 5).
- Equity regime switch (half size in drawdown): costs profit, saves nothing for the live 23.
- Re-mining the 66/74/51/146 pool: 3 steady strategies in it, all tiny.
- Re-optimising on the last two years: every mix built that way made ~$100/month once the window moved.

## What a result must say
A table with $/month per period, failed challenge starts (fresh $5K every 14 days, fail = -$400 before +$400),
lowest balance and stop days, for $5K and $10K. Plain language. Veer decides what goes live.

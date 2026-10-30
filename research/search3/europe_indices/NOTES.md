# Round 3 search: European indices (UK100, F40/FRA40, IT40, DE40, +ESP35)

Judge: `research/prop/harness.py`, `PROP_OOS=1`, scoring window 2024-10-20..data end,
fixed-dollar risk on a $10k FundedNext account, best_risk = highest risk with worst
day > -3% and max DD > -6%. No statistical gates (owner's call); what stays is the
look-ahead check (section 6) and the 300/800 rule.

## 1. Data and data quality

Files: `data/search/<sym>-<tf>.csv`, server time EET (Xetra/Euronext cash 10:00-18:30,
US cash open 16:30, index CFDs trade to 23:00).

| group symbol | file used | note |
|---|---|---|
| UK100 | uk100-* | **sparse feed**: only 48 daily bars / 1,879 M30 bars in the scoring window (file ends 2026-05-15 and has large holes). Scored, but every UK100 number rests on ~2 months of bars. Not tradeable from this evidence. |
| F40 | fra40-* | IC Markets name is FRA40. `vol_min = 1.0` lot at 1 EUR/point: at 0.25-0.5% risk ($25-50) only trades with a stop under ~25-45 points can be sized; the harness skips the rest. Real constraint for a $10k account; FRA40 trade counts are therefore small and biased to tight-stop setups. |
| STOXX50 | none | no data file in the broker export (not in `symbol_specs.json` either). Re-checked during the run; never appeared. |
| SWI20 | none | same as STOXX50. |
| IT40 | it40-* | ok, 2015+ on D1, M30 from 2024-05. |
| DE40 | de40-* | ok, also has M15 (used for the Kagels 09:15-candle rule). Data ends 2026-10-19. |
| ESP35 | esp35-* | added as a cross-check (same session structure). `vol_min = 1.0` like FRA40. |

Quality filter (`common.quality_mask`): drop zero-volume bars, zero-range bars, and
whole days that look like a stale feed: day range under 25% of the median daily range
OR more than 30% of the day's bars have zero range (price stuck while ticks arrive). The
second rule was added after the first sweep produced a fake +$4,522 DE40 trade held
across 2024-11-28..12-03, where the feed was stuck at 19,313.7 / 19,410.8 / 19,898.6
for whole days but day ranges of 40-100 points slipped under the original 5% threshold.
That first sweep (220 runs, `results_oldmask.jsonl`) was discarded; everything below
uses the new mask.

Bars dropped / bars in the scoring window:

| symbol | M30 | H1 | H4 | D1 | stale days dropped (whole file) |
|---|---|---|---|---|---|
| UK100 | 0 / 1,879 | 0 / 940 | 0 / 283 | 0 / 48 | 0-8 |
| FRA40 | 19 / 23,369 | 11 / 11,695 | 0 / 3,060 | 0 / 516 | 0-18 |
| IT40 | 846 / 11,937 | 428 / 5,978 | 118 / 1,849 | 29 / 469 | 37-47 |
| DE40 | 1,745 / 20,215 | 863 / 10,119 | 233 / 2,792 | 31 / 472 | 40-53 |
| ESP35 | 649 / 11,383 | 300 / 5,716 | 81 / 1,804 | 17 / 457 | 24-27 |

Gaps over 72h (holiday weekends + feed holes, M30): UK100 4, FRA40 4, IT40 9, DE40 6,
ESP35 21. Zero-volume bars: none in any file. Side effect of dropping whole days: a
position whose `exit_hour` bar falls on a dropped day exits on the next available bar
with that hour (one day later); rare after the fix, noted for honesty.

Cost model (monkeypatched in `common.py`): spread floors in price units UK100 2.0,
FRA40/F40 1.5, STOXX50 1.5, SWI20 3.0, IT40 10.0, ESP35 5.0, DE40 1.5 (harness
default); all added to `H.INDICES` (no commission, pip = 1 point). Contract sizes from
`data/search/symbol_specs.json`: DE40 1 EUR/pt, 0.1 lot min; FRA40 1 EUR/pt, 1.0 lot
min; IT40 1 EUR/pt, 0.1 min; UK100 10 GBP/pt, 0.1 min; ESP35 1 EUR/pt, 1.0 min.

## 2. Market study (H1 bars, 2024-10-20 onward, after cleaning; `study.py` -> `study_out.txt`)

Volatility by hour (mean H1 range in bps of price): the 10:00 bar is the widest of
the day everywhere (DE40 52, FRA40 55, IT40 64, ESP35 60, UK100 52), 11:00 second
(40-44), then a lunch trough 12:00-15:00 (30-34), a second bump at 16:00-17:00 for
the US open (38-41), and a quiet evening 19:00-22:00 (22-26). Overnight 01:00-08:00
bars range 15-25 bps.

Drift by session leg (sum of H1 log returns per day, bps):

| leg | DE40 | FRA40 | IT40 | ESP35 | UK100 (48 d) |
|---|---|---|---|---|---|
| overnight 23-09 | +1.1 | -1.8 | +2.5 | -1.1 | -0.5 |
| open 10-11 | -0.8 | +0.6 | -0.4 | +5.5 | -1.0 |
| mid 12-15 | +2.0 | +0.7 | +1.9 | +3.2 | +7.8 |
| US 16-18 | -0.3 | -1.9 | 0.0 | +0.8 | -2.8 |
| late 19-22 | **+4.7** | **+4.9** | **+5.0** | +0.2 | -0.4 |

The one drift that is consistent across the three liquid continental indices is the
late session (19:00-22:00, after the cash close, during the US afternoon): about +5
bps/day, with the 20:00 bar alone +3.2 to +3.6 bps. That is the `time_window` idea.

Gap at the cash open (10:00 open vs previous 18:00 close): std 79-95 bps, half of
all days gap more than 30 bps. corr(gap, open-to-close session return) is clearly
negative on DE40 (-0.21), FRA40 (-0.24), IT40 (-0.24) and about 0 on ESP35/UK100:
gaps partly fill. Mean session return in the gap direction after a gap over 20 bps:
-9 bps (DE40), -8.5 (FRA40), -6 (IT40). Supports gap-fade, but the edge is small
against a ~100 bp session std.

Persistence: H1 lag-1 autocorrelation is about 0 at almost every hour (|r| under 0.1
for the 10:00-18:00 bars). corr(10:00 bar, rest of session) is +0.05..+0.10 (tiny
continuation, no 10-11 reversal). corr(16:00 bar, 17-18 bars) is -0.05 on DE40,
-0.02 FRA40, -0.04 IT40 (+0.23 on the thin UK100 sample): no reliable US-open
continuation. Daily lag-1 autocorr: DE40 -0.02, FRA40 -0.14, IT40 +0.01, ESP35 -0.03.
Weekly: nothing (|r| under 0.07 except ESP35 -0.2 on 90 weeks).

Weekday: Monday is the best cash day on DE40/IT40/UK100 (+1.4/+2.4/+4.2 bps per H1
bar), Thursday/Friday the worst; small.

## 3. Practitioner research (what people actually trade on these markets)

- Kagels Trading, "Einfache DAX Breakout-Strategie im Test" (2026): FDAX 15-min, the
  09:15 CET candle high/low become buy/sell stops, TP 10/20 points, no new orders
  after 13:00, re-entries. Their 2020-2025 Python backtest: ~75-83% win rate but only
  slightly profitable after costs, long side better, killed by chop days. Tested here
  as `kagels_915` (bar-close entry, stop at the opposite side of the candle or its
  midpoint, TP in points or R, flat 18:00) on DE40 M15 and as a 10:00-10:30 M30
  proxy on all symbols. https://www.kagels-trading.de/dax-open-range-strategie/
- Benzinga / PyQuant "DAX opening range breakout" (2025-01): first hour as the range,
  entries at ref +/- multiplier x range, optimised multipliers. Tested as `fh_mult`.
  https://www.benzinga.com/markets/eurozone/25/01/42902291/dax-trading-exploring-an-opening-range-breakout-strategy-code-and-optimizations
- STOXX, "When do returns come from? The overnight effect" (2025): Euro Stoxx 50
  2013-2025, nearly all of the ~3 bp/day comes from previous close to the 09:00 CET
  open; iShares EUE ETF 2016-2025 overnight +12.9%/yr vs intraday -4.3%/yr. Tested
  as `overnight` (18:30 to 10:00) and `close_to_open` (18:00 to 10:00 with day filters).
  https://stoxx.com/when-do-returns-come-from-an-analysis-of-the-overnight-effect-in-equities-trading/
- Gao, Han, Li, Zhou (JFE 2018) "Market intraday momentum": the first half-hour
  return predicts the last half-hour return; holds in FTSE 100 and Euro Stoxx 50
  futures. Tested as `intraday_mom` (10:00-10:30 bar sign, trade 18:00-18:30).
  https://www3.nd.edu/~zda/intramom.pdf ; Baltussen, Da, Lammers, Martens
  (hedging-demand paper): predictability sits mostly in the last half hour.
- Seasonax / Crossing Wall Street: DAX turn-of-the-month effect (1970-2018, most
  gains around month end/start). Tested as `calendar kind=tom`.
- Edgeful / LuxAlgo gap-fill reports: fill rates depend on the definition; half-gap
  targets fill far more often than full fills. Tested as `gap` with `tp=fill` and
  `tp=r`.
- TradingView / ProRealCode DAX scripts (08:30-09:00 box, first-10-minutes high/low,
  morning breakout with size increase): all opening-range-breakout variants, covered
  by `orb`, `or_fail`, `fh_retest`.
- Searches for a published 10:00-11:00 reversal or US-open continuation statistic
  on European indices found nothing credible; both were tested directly (`or_fail`,
  `us_open_fade`, `late_momentum`).
- No video or podcast rule set specific to these indices was found that was more
  concrete than the Kagels write-up, so no transcript was used.

## 4. Ideas tested (24 builders in `strategies.py`, all `build_<name>(df, **params)`)

1. `gap` cash-open gap fade / continuation (gap in daily-ATR units, TP fill or R)
2. `us_open_fade` 16:30 bar shock fade / continuation
3. `close_fade` fade (or follow) the cash-session drift into the 18:30 close
4. `overnight` long 18:30 to 10:00 (STOXX overnight effect) with day filters
5. `orb` opening range breakout (10:00-10:30 / 11:00), SL far/mid, TP in R
6. `or_fail` opening-range failure (the 10-11 reversal)
7. `pdhl` prior-day high/low rejection or break
8. `round` round-number break (100/50/250 pt steps); 9. `round_fade` round-number rejection
10. `late_momentum` 19:00/20:00 bar follow / fade
11. `time_window` pure session drift (19:00-22:00 long etc.)
12. `lunch_break` lunch range (12:30-15:30) break into the US open
13. `pullback` H1/H4 EMA trend + RSI(3) pullback
14. `d1_meanrev` D1 consecutive-down / RSI2 mean reversion above the 200-day MA
15. `prev_week` previous-week high/low break with ATR trail
16. `calendar` turn-of-month / weekday sessions
17. `compression_break` NR4 / NR7 / inside-day break
18. `big_day` D1 move over k ATR: fade / follow
19. `fh_retest` first-hour break then retest entry
20. `donchian` H4/D1 channel trend
21. `kagels_915` Kagels 09:15-candle breakout (DE40 M15 + M30 proxy)
22. `fh_mult` first-hour range multiplier breakout (Benzinga rules)
23. `close_to_open` 18:00 to 10:00 overnight with cash-session filters
24. `intraday_mom` Gao et al. first-half-hour predicts last-half-hour

## 5. Results

Status: the sweep (`run.py`, 1,410 planned runs over 5 symbols x M30/H1/H4/D1/M15) was interrupted by the harness deadline at **812 scored runs**; 291 are safe and positive. `run.py all 2` is resumable (done keys are skipped) and `run.py imom 2` adds the intraday-momentum batch. Batches fully scored so far: all DE40 and ESP35 jobs plus most FRA40; IT40 and UK100 were still queued.

Candidates (best run per idea x market, max 2 per idea, 3 per market, >= 20 trades, UK100 excluded; all pass the look-ahead check):

| builder | symbol | tf | params | best_risk | avg_month $ | net $ | max_dd $ | worst_day $ | trades | green |
|---|---|---|---|---|---|---|---|---|---|---|
| calendar | DE40 | M30 | `{"kind": "weekday", "wd": 0, "side": "long"}` | 2.00% | 92 | 2217 | -507 | -187 | 84 | 54% |
| fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": null}` | 0.50% | 89 | 2126 | -558 | -50 | 357 | 62% |
| prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.25% | 84 | 2021 | -447 | -41 | 46 | 54% |
| time_window | ESP35 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long", "wds": [0]}` | 1.50% | 71 | 1763 | -568 | -142 | 71 | 40% |
| or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "mid", "trend": "with"}` | 2.00% | 52 | 1310 | -491 | -199 | 30 | 48% |
| gap | ESP35 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 1.25% | 43 | 1076 | -475 | -124 | 67 | 48% |
| orb | ESP35 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": null}` | 1.00% | 38 | 946 | -411 | -99 | 80 | 56% |
| us_open_fade | FRA40 | M30 | `{"k": 1.0, "sides": "short"}` | 0.75% | 36 | 908 | -473 | -75 | 53 | 48% |

Reading: the 'ideas' that reach $70-90/month on a $10k account are (a) a Monday-only
long cash session on DE40, (b) the first-hour multiplier breakout on DE40 (357 trades,
the only candidate with real volume), (c) a long-only previous-week-high break with
a trailing stop on DE40, (d) Monday long on ESP35. Gap fade, opening-range breakout
and failure, and the US-open fade show up only on one market each at $35-50/month,
consistent with the weak correlations in the market study. Overnight (STOXX effect),
intraday momentum, late-session drift on DE40/FRA40, round numbers, prior-day
levels, lunch breaks, pullbacks, Donchian and D1 mean reversion were net negative or
unsafe on every market tried so far. All candidates sit near the DD limit at their
best_risk ($410-570 of the $600 buffer), none clears 4 green months in 7 on all
markets; nothing here is strong enough to trade alone.

## 6. Look-ahead check

`causal_check.py`: build(df) vs build(df.iloc[:k]) with attrs re-attached, 5 random k
in [n/3, n), every Entry at index < k compared on side/sl/tp/max_hold/exit_hour/
manage-presence. All 24 builders with default params on DE40 M30/D1: 0 mismatches.
All 8 candidates with their exact params: 0 mismatches.

## 7. Every scored run

816 scored runs; 291 safe and positive

| # | builder | symbol | tf | params | best_risk | avg_month $ | net $ | max_dd $ | worst_day $ | trades | green | win% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | calendar | DE40 | M30 | `{"kind": "weekday", "wd": 0, "side": "long"}` | 2.00% | 92 | 2217 | -507 | -187 | 84 | 54% | 60% |
| 2 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": null}` | 0.50% | 89 | 2126 | -558 | -50 | 357 | 62% | 46% |
| 3 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.25% | 84 | 2021 | -447 | -41 | 46 | 54% | 43% |
| 4 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.25% | 83 | 2003 | -447 | -41 | 62 | 58% | 40% |
| 5 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | 76 | 1813 | -447 | -90 | 62 | 50% | 29% |
| 6 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [0, 1, 2, 3], "hold_days": 1}` | 1.00% | 72 | 1725 | -589 | -221 | 54 | 62% | 52% |
| 7 | fh_mult | DE40 | M30 | `{"mult": 0.25, "sl": "ref", "tp_r": null}` | 0.25% | 72 | 1722 | -589 | -25 | 403 | 58% | 31% |
| 8 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "sides": "short"}` | 0.75% | 72 | 1718 | -503 | -75 | 173 | 67% | 45% |
| 9 | time_window | ESP35 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long", "wds": [0]}` | 1.50% | 71 | 1763 | -568 | -142 | 71 | 40% | 56% |
| 10 | time_window | DE40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long", "wds": [0]}` | 1.25% | 70 | 1678 | -527 | -124 | 84 | 54% | 58% |
| 11 | fh_mult | DE40 | M30 | `{"mult": 1.0, "sl": "ref", "tp_r": null}` | 0.50% | 69 | 1644 | -596 | -50 | 203 | 62% | 48% |
| 12 | time_window | DE40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "short", "wds": [4]}` | 1.25% | 68 | 1635 | -580 | -125 | 85 | 67% | 48% |
| 13 | prev_week | DE40 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | 1.00% | 60 | 1433 | -543 | -185 | 76 | 54% | 43% |
| 14 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "ref", "tp_r": null}` | 0.25% | 56 | 1352 | -490 | -25 | 355 | 54% | 38% |
| 15 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": 2.0}` | 0.50% | 56 | 1342 | -476 | -50 | 357 | 67% | 46% |
| 16 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "trend": null}` | 0.75% | 55 | 1313 | -484 | -75 | 119 | 67% | 64% |
| 17 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "te": 13.0}` | 0.75% | 55 | 1308 | -529 | -75 | 162 | 58% | 62% |
| 18 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "sides": "short"}` | 1.00% | 54 | 1300 | -590 | -100 | 65 | 67% | 66% |
| 19 | orb | DE40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": null}` | 0.50% | 53 | 1279 | -486 | -50 | 285 | 58% | 49% |
| 20 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "mid", "trend": "with"}` | 2.00% | 52 | 1310 | -491 | -199 | 30 | 48% | 80% |
| 21 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1}` | 0.75% | 52 | 1256 | -424 | -208 | 56 | 67% | 50% |
| 22 | prev_week | DE40 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 0.25% | 51 | 1220 | -303 | -25 | 60 | 54% | 43% |
| 23 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "sl_datr": 1.5}` | 1.50% | 50 | 1190 | -537 | -240 | 49 | 62% | 55% |
| 24 | time_window | DE40 | M30 | `{"entry_hm": 18.5, "exit_hour": 22, "side": "long"}` | 0.50% | 48 | 1159 | -553 | -121 | 368 | 67% | 52% |
| 25 | fh_mult | DE40 | M30 | `{"mult": 1.0, "sl": "opp", "tp_r": null}` | 0.50% | 48 | 1158 | -533 | -50 | 193 | 62% | 52% |
| 26 | prev_week | DE40 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | 48 | 1155 | -303 | -54 | 60 | 42% | 35% |
| 27 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "trend": "with", "te": 14.0}` | 0.50% | 47 | 1125 | -558 | -50 | 135 | 58% | 45% |
| 28 | time_window | FRA40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "short", "wds": [4]}` | 1.25% | 46 | 1149 | -478 | -119 | 99 | 48% | 51% |
| 29 | fh_mult | DE40 | M30 | `{"mult": 0.25, "sl": "opp", "tp_r": null}` | 0.25% | 44 | 1051 | -541 | -25 | 404 | 62% | 41% |
| 30 | time_window | DE40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long"}` | 0.50% | 43 | 1036 | -520 | -118 | 368 | 62% | 50% |
| 31 | gap | ESP35 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 1.25% | 43 | 1076 | -475 | -124 | 67 | 48% | 63% |
| 32 | time_window | DE40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "sl_datr": 0.3}` | 0.25% | 42 | 1015 | -397 | -89 | 373 | 54% | 48% |
| 33 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "trend": "with", "te": 16.0}` | 0.50% | 42 | 1012 | -558 | -50 | 165 | 50% | 44% |
| 34 | time_window | FRA40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_down"}` | 1.50% | 42 | 1048 | -511 | -137 | 240 | 60% | 48% |
| 35 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "sides": "long"}` | 0.50% | 42 | 1005 | -558 | -50 | 185 | 42% | 46% |
| 36 | time_window | ESP35 | M30 | `{"entry_hm": 16.0, "exit_hour": 18, "side": "long"}` | 1.25% | 41 | 1036 | -426 | -123 | 241 | 48% | 54% |
| 37 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | 0.50% | 40 | 969 | -386 | -154 | 75 | 46% | 35% |
| 38 | calendar | DE40 | M30 | `{"kind": "weekday", "wd": 4, "side": "short"}` | 1.50% | 40 | 961 | -561 | -148 | 85 | 67% | 48% |
| 39 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "te": 14.0}` | 0.75% | 40 | 949 | -578 | -75 | 200 | 50% | 60% |
| 40 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": null}` | 1.00% | 38 | 946 | -411 | -99 | 80 | 56% | 52% |
| 41 | orb | DE40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": null}` | 0.25% | 37 | 894 | -397 | -25 | 280 | 58% | 40% |
| 42 | time_window | DE40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_down"}` | 0.50% | 37 | 889 | -461 | -124 | 198 | 67% | 51% |
| 43 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "sides": "short"}` | 0.75% | 36 | 908 | -473 | -75 | 53 | 48% | 47% |
| 44 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 2.00% | 36 | 892 | -346 | -181 | 42 | 36% | 52% |
| 45 | gap | FRA40 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 1.50% | 35 | 879 | -433 | -148 | 137 | 56% | 57% |
| 46 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 2.00% | 34 | 858 | -398 | -181 | 43 | 36% | 51% |
| 47 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 11.0}` | 1.25% | 33 | 828 | -575 | -124 | 64 | 48% | 59% |
| 48 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | 0.75% | 33 | 816 | -489 | -109 | 38 | 40% | 42% |
| 49 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 10.5}` | 1.25% | 31 | 782 | -535 | -124 | 65 | 52% | 62% |
| 50 | late_momentum | ESP35 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "follow"}` | 0.50% | 31 | 774 | -261 | -93 | 13 | 24% | 54% |
| 51 | donchian | FRA40 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": null}` | 0.75% | 31 | 768 | -215 | -120 | 2 | 12% | 50% |
| 52 | fh_mult | DE40 | M30 | `{"mult": 1.0, "sl": "ref", "tp_r": 2.0}` | 0.50% | 30 | 731 | -539 | -50 | 203 | 58% | 48% |
| 53 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "mid", "trend": null}` | 1.25% | 30 | 743 | -485 | -123 | 73 | 48% | 73% |
| 54 | time_window | DE40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_up"}` | 0.50% | 29 | 706 | -394 | -127 | 196 | 54% | 51% |
| 55 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "sides": "short", "te": 14.0}` | 0.50% | 28 | 677 | -481 | -50 | 163 | 58% | 48% |
| 56 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 2.00% | 28 | 704 | -361 | -181 | 39 | 40% | 56% |
| 57 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "mid", "trend": null}` | 1.00% | 27 | 651 | -595 | -100 | 98 | 54% | 79% |
| 58 | compression_break | DE40 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": null}` | 1.50% | 27 | 649 | -593 | -150 | 27 | 50% | 63% |
| 59 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 2.00% | 27 | 669 | -413 | -181 | 40 | 40% | 55% |
| 60 | overnight | DE40 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 0.75}` | 1.25% | 27 | 641 | -595 | -255 | 164 | 50% | 53% |
| 61 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.5}` | 1.50% | 26 | 662 | -43 | -18 | 5 | 8% | 80% |
| 62 | pdhl | ESP35 | M30 | `{"mode": "break", "trend": "with"}` | 0.75% | 26 | 661 | -430 | -73 | 99 | 48% | 54% |
| 63 | orb | DE40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": "with"}` | 0.50% | 26 | 630 | -495 | -50 | 147 | 46% | 49% |
| 64 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | 0.75% | 26 | 617 | -587 | -231 | 31 | 25% | 26% |
| 65 | overnight | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.5}` | 1.50% | 26 | 616 | -554 | -252 | 336 | 58% | 53% |
| 66 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.50% | 24 | 587 | -401 | -175 | 60 | 46% | 40% |
| 67 | orb | DE40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.25% | 24 | 574 | -321 | -25 | 144 | 50% | 40% |
| 68 | compression_break | DE40 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": 2.0}` | 1.50% | 22 | 534 | -593 | -150 | 27 | 50% | 63% |
| 69 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [-1, 0], "hold_days": 2}` | 1.00% | 22 | 530 | -471 | -295 | 28 | 54% | 50% |
| 70 | close_to_open | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.5}` | 1.50% | 22 | 528 | -534 | -252 | 337 | 58% | 53% |
| 71 | overnight | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 18.0}` | 0.75% | 22 | 528 | -423 | -181 | 399 | 50% | 54% |
| 72 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "sides": "long"}` | 1.00% | 22 | 527 | -586 | -99 | 54 | 50% | 61% |
| 73 | close_fade | DE40 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 1.50% | 22 | 526 | -569 | -149 | 269 | 54% | 50% |
| 74 | orb | DE40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": null}` | 0.50% | 22 | 522 | -435 | -50 | 285 | 54% | 49% |
| 75 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "r", "trend": null}` | 0.75% | 22 | 520 | -574 | -75 | 119 | 42% | 46% |
| 76 | calendar | ESP35 | M30 | `{"kind": "weekday", "wd": 0, "side": "long"}` | 2.00% | 22 | 539 | -452 | -183 | 60 | 40% | 60% |
| 77 | close_to_open | DE40 | M30 | `{"side": "long", "wds": [0, 1, 2, 3, 4]}` | 0.75% | 22 | 518 | -423 | -181 | 400 | 50% | 54% |
| 78 | fh_mult | DE40 | M30 | `{"mult": 1.0, "sl": "opp", "tp_r": 2.0}` | 0.50% | 21 | 511 | -386 | -50 | 193 | 62% | 52% |
| 79 | overnight | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 18.0}` | 1.00% | 21 | 531 | -43 | -18 | 4 | 8% | 75% |
| 80 | close_to_open | ESP35 | M30 | `{"side": "long", "wds": [0, 1, 2, 3, 4]}` | 1.00% | 21 | 531 | -43 | -18 | 4 | 8% | 75% |
| 81 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 11.0}` | 1.25% | 21 | 526 | -569 | -123 | 149 | 52% | 54% |
| 82 | overnight | DE40 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 1.5}` | 2.00% | 21 | 503 | -460 | -255 | 164 | 54% | 53% |
| 83 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "short"}` | 1.25% | 21 | 519 | -291 | -122 | 33 | 36% | 55% |
| 84 | time_window | FRA40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long", "wds": [0]}` | 1.25% | 21 | 518 | -582 | -121 | 101 | 52% | 50% |
| 85 | lunch_break | DE40 | M30 | `{"sl": "far", "tp_r": null, "trend": "with"}` | 0.75% | 21 | 497 | -493 | -74 | 135 | 54% | 50% |
| 86 | gap | DE40 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 1.5}` | 0.50% | 20 | 483 | -550 | -50 | 158 | 54% | 53% |
| 87 | prev_week | DE40 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 20 | 482 | -468 | -175 | 60 | 46% | 45% |
| 88 | donchian | DE40 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": null}` | 1.00% | 20 | 474 | -574 | -129 | 55 | 50% | 40% |
| 89 | lunch_break | DE40 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": "with"}` | 0.75% | 20 | 473 | -493 | -74 | 135 | 54% | 50% |
| 90 | close_to_open | DE40 | M30 | `{"side": "long", "entry_hm": 17.5, "exit_hm": 10.0}` | 1.00% | 19 | 467 | -533 | -252 | 337 | 54% | 52% |
| 91 | gap | DE40 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 1.5}` | 1.00% | 19 | 466 | -596 | -100 | 78 | 42% | 59% |
| 92 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.50% | 19 | 464 | -406 | -97 | 45 | 38% | 40% |
| 93 | overnight | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "trend": "with"}` | 1.25% | 19 | 462 | -542 | -288 | 259 | 50% | 53% |
| 94 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "far", "trend": "with"}` | 0.25% | 19 | 452 | -545 | -177 | 209 | 67% | 35% |
| 95 | close_to_open | ESP35 | M30 | `{"side": "long", "exit_hm": 11.0}` | 1.00% | 19 | 470 | -97 | -72 | 4 | 8% | 75% |
| 96 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "far", "trend": "with"}` | 1.25% | 19 | 467 | -583 | -123 | 35 | 44% | 54% |
| 97 | orb | DE40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": null}` | 0.25% | 19 | 446 | -568 | -177 | 344 | 54% | 35% |
| 98 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": "with"}` | 1.25% | 19 | 463 | -598 | -119 | 68 | 40% | 56% |
| 99 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": null}` | 0.75% | 18 | 458 | -398 | -74 | 54 | 40% | 56% |
| 100 | close_fade | DE40 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 1.50% | 18 | 436 | -451 | -134 | 151 | 54% | 48% |
| 101 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "down_cash", "sl_datr": 1.5}` | 2.00% | 18 | 430 | -537 | -235 | 158 | 58% | 54% |
| 102 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "trend": "with", "te": 14.0}` | 1.00% | 18 | 441 | -578 | -100 | 72 | 36% | 51% |
| 103 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "entry_hm": 18.0}` | 0.50% | 17 | 420 | -437 | -144 | 81 | 54% | 54% |
| 104 | overnight | DE40 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 1.5}` | 2.00% | 17 | 418 | -520 | -255 | 159 | 54% | 52% |
| 105 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.75% | 17 | 435 | -490 | -125 | 40 | 28% | 28% |
| 106 | d1_meanrev | DE40 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200, "use_trend": false}` | 2.00% | 17 | 416 | -392 | -159 | 29 | 54% | 62% |
| 107 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | 0.50% | 17 | 422 | -559 | -96 | 70 | 40% | 33% |
| 108 | donchian | FRA40 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": null}` | 0.75% | 17 | 421 | -188 | -115 | 3 | 8% | 33% |
| 109 | fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "ref", "tp_r": 2.0}` | 0.25% | 17 | 404 | -307 | -25 | 355 | 54% | 41% |
| 110 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 1.25% | 17 | 419 | -598 | -119 | 68 | 40% | 56% |
| 111 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "down_cash", "sl_datr": 0.75}` | 1.50% | 17 | 419 | -447 | -179 | 33 | 28% | 64% |
| 112 | us_open_fade | DE40 | M30 | `{"k": 1.0, "sides": "short"}` | 0.75% | 17 | 402 | -577 | -75 | 41 | 42% | 39% |
| 113 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "sides": "short", "te": 14.0}` | 0.75% | 17 | 418 | -396 | -73 | 28 | 36% | 57% |
| 114 | overnight | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 19.0}` | 0.75% | 17 | 397 | -471 | -181 | 399 | 50% | 52% |
| 115 | close_to_open | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 0.75}` | 0.75% | 16 | 394 | -503 | -252 | 337 | 46% | 53% |
| 116 | donchian | FRA40 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": null}` | 0.75% | 16 | 405 | -188 | -115 | 3 | 8% | 33% |
| 117 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "up_cash", "sl_datr": 1.5}` | 1.50% | 16 | 404 | -30 | -15 | 2 | 4% | 50% |
| 118 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "sl_datr": 1.5}` | 1.50% | 16 | 399 | -112 | -5 | 1 | 4% | 100% |
| 119 | overnight | DE40 | M30 | `{"side": "long", "cond": null, "sl_datr": 0.75}` | 0.75% | 16 | 379 | -503 | -252 | 336 | 54% | 53% |
| 120 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "te": 14.0}` | 0.75% | 16 | 390 | -434 | -74 | 60 | 40% | 52% |
| 121 | lunch_break | DE40 | M30 | `{"sl": "mid", "tp_r": null, "trend": "with"}` | 0.50% | 16 | 374 | -474 | -50 | 135 | 54% | 47% |
| 122 | gap | DE40 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 2.5}` | 0.75% | 15 | 367 | -442 | -74 | 76 | 54% | 59% |
| 123 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": null}` | 0.75% | 15 | 382 | -456 | -74 | 54 | 36% | 52% |
| 124 | close_to_open | DE40 | M30 | `{"side": "long", "exit_hm": 11.0}` | 0.75% | 15 | 364 | -541 | -180 | 319 | 67% | 51% |
| 125 | us_open_fade | DE40 | M30 | `{"k": 1.0, "trend": "with"}` | 0.50% | 15 | 361 | -437 | -50 | 44 | 33% | 39% |
| 126 | prev_week | FRA40 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | 0.75% | 15 | 374 | -528 | -87 | 60 | 44% | 37% |
| 127 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | 0.50% | 15 | 366 | -536 | -90 | 73 | 40% | 33% |
| 128 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "far", "te": 14.0}` | 0.75% | 15 | 366 | -386 | -74 | 60 | 40% | 57% |
| 129 | prev_week | FRA40 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | 0.50% | 15 | 366 | -389 | -50 | 55 | 44% | 44% |
| 130 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "up_cash", "sl_datr": 0.75}` | 1.00% | 14 | 346 | -568 | -123 | 178 | 46% | 53% |
| 131 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "up_cash", "sl_datr": 1.5}` | 1.50% | 14 | 334 | -397 | -111 | 175 | 58% | 53% |
| 132 | lunch_break | DE40 | M30 | `{"sl": "far", "tp_r": null, "trend": null}` | 0.50% | 14 | 332 | -461 | -49 | 279 | 46% | 45% |
| 133 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "against"}` | 1.00% | 14 | 328 | -564 | -100 | 86 | 46% | 51% |
| 134 | late_momentum | DE40 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "fade"}` | 1.50% | 14 | 325 | -569 | -150 | 83 | 46% | 49% |
| 135 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "down_cash", "sl_datr": 1.5}` | 2.00% | 13 | 337 | -91 | -46 | 8 | 12% | 88% |
| 136 | overnight | DE40 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 1.5}` | 1.50% | 13 | 323 | -432 | -115 | 174 | 54% | 54% |
| 137 | big_day | DE40 | D1 | `{"k": 1.5, "mode": "follow"}` | 2.00% | 13 | 317 | -344 | -161 | 15 | 25% | 53% |
| 138 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "short"}` | 1.00% | 13 | 330 | -446 | -100 | 67 | 40% | 54% |
| 139 | overnight | DE40 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 0.75}` | 0.75% | 13 | 303 | -339 | -170 | 159 | 46% | 52% |
| 140 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 1.50% | 12 | 312 | -566 | -147 | 84 | 52% | 49% |
| 141 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 1.50% | 12 | 312 | -566 | -147 | 84 | 52% | 49% |
| 142 | gap | FRA40 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 1.00% | 12 | 303 | -541 | -100 | 137 | 48% | 52% |
| 143 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "down_cash", "sl_datr": 0.75}` | 1.00% | 12 | 285 | -598 | -235 | 158 | 42% | 54% |
| 144 | overnight | DE40 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 0.75}` | 0.75% | 12 | 284 | -469 | -105 | 174 | 50% | 54% |
| 145 | overnight | FRA40 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 0.75}` | 1.25% | 12 | 292 | -521 | -112 | 167 | 52% | 53% |
| 146 | pullback | ESP35 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | 0.25% | 12 | 291 | -278 | -247 | 4 | 8% | 25% |
| 147 | orb | ESP35 | M30 | `{"re": 10.5, "te": 14.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 1.00% | 11 | 287 | -516 | -100 | 72 | 36% | 51% |
| 148 | lunch_break | DE40 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": null}` | 0.50% | 11 | 272 | -461 | -49 | 279 | 46% | 45% |
| 149 | gap | FRA40 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 2.5}` | 1.00% | 11 | 281 | -519 | -95 | 41 | 40% | 46% |
| 150 | d1_meanrev | DE40 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200}` | 1.50% | 11 | 268 | -325 | -108 | 25 | 54% | 56% |
| 151 | late_momentum | DE40 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "follow"}` | 2.00% | 11 | 267 | -373 | -192 | 28 | 33% | 54% |
| 152 | overnight | ESP35 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 1.5}` | 2.00% | 11 | 276 | -101 | -51 | 10 | 8% | 80% |
| 153 | prev_week | ESP35 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | 1.00% | 11 | 276 | -296 | -165 | 5 | 8% | 40% |
| 154 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1}` | 0.75% | 11 | 274 | -210 | -105 | 9 | 24% | 56% |
| 155 | prev_week | DE40 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | 0.25% | 11 | 261 | -274 | -46 | 59 | 38% | 32% |
| 156 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [0, 1, 2, 3], "hold_days": 1}` | 1.00% | 11 | 268 | -443 | -167 | 39 | 48% | 51% |
| 157 | donchian | DE40 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 11 | 253 | -559 | -95 | 60 | 62% | 37% |
| 158 | lunch_break | DE40 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": "with"}` | 0.50% | 10 | 252 | -430 | -50 | 135 | 54% | 47% |
| 159 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": "with"}` | 1.00% | 10 | 261 | -586 | -100 | 65 | 36% | 51% |
| 160 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "far", "wds": [1, 2, 3]}` | 0.25% | 10 | 249 | -545 | -177 | 245 | 42% | 35% |
| 161 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "below_pdc", "sl_datr": 1.5}` | 1.50% | 10 | 258 | -39 | -17 | 3 | 4% | 100% |
| 162 | calendar | DE40 | M30 | `{"kind": "tom", "tom_days": [-1], "hold_days": 4}` | 1.00% | 10 | 246 | -510 | -296 | 18 | 38% | 33% |
| 163 | orb | DE40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.50% | 10 | 244 | -538 | -50 | 147 | 42% | 49% |
| 164 | overnight | FRA40 | M30 | `{"side": "short", "cond": null, "sl_datr": 1.0}` | 1.00% | 10 | 253 | -243 | -79 | 40 | 20% | 55% |
| 165 | prev_week | ESP35 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | 1.00% | 10 | 252 | -345 | -165 | 5 | 8% | 40% |
| 166 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | 0.25% | 10 | 235 | -512 | -77 | 73 | 38% | 26% |
| 167 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [-1], "hold_days": 4}` | 1.25% | 10 | 244 | -456 | -286 | 22 | 40% | 45% |
| 168 | overnight | ESP35 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 0.75}` | 1.25% | 10 | 244 | -144 | -128 | 14 | 12% | 71% |
| 169 | close_fade | DE40 | M30 | `{"k": 0.3, "mode": "fade", "from_hm": 16.5, "entry_hm": 17.5}` | 2.00% | 10 | 233 | -522 | -192 | 69 | 46% | 55% |
| 170 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "mid", "trend": null}` | 1.00% | 10 | 240 | -464 | -100 | 121 | 52% | 73% |
| 171 | donchian | FRA40 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": null}` | 1.00% | 9 | 237 | -491 | -118 | 17 | 28% | 41% |
| 172 | gap | DE40 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 2.5}` | 0.50% | 9 | 227 | -558 | -50 | 158 | 46% | 51% |
| 173 | overnight | FRA40 | M30 | `{"side": "short", "cond": "up_day", "sl_datr": 1.0}` | 1.00% | 9 | 236 | -100 | -50 | 14 | 16% | 71% |
| 174 | overnight | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 0.75}` | 1.25% | 9 | 232 | -373 | -293 | 42 | 12% | 55% |
| 175 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "sl_datr": 1.5}` | 1.50% | 9 | 225 | -227 | -129 | 7 | 24% | 57% |
| 176 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 9 | 223 | -554 | -125 | 43 | 28% | 26% |
| 177 | overnight | FRA40 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 0.75}` | 1.25% | 9 | 219 | -536 | -113 | 184 | 52% | 52% |
| 178 | orb | DE40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.25% | 9 | 209 | -468 | -177 | 174 | 46% | 33% |
| 179 | donchian | FRA40 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": null}` | 1.00% | 8 | 208 | -362 | -118 | 10 | 24% | 50% |
| 180 | donchian | FRA40 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": "with"}` | 1.00% | 8 | 208 | -362 | -118 | 10 | 24% | 50% |
| 181 | pullback | ESP35 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | 0.25% | 8 | 206 | -374 | -247 | 5 | 8% | 20% |
| 182 | time_window | DE40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "trend": "with"}` | 0.25% | 8 | 194 | -291 | -59 | 254 | 42% | 49% |
| 183 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "mid", "trend": "with"}` | 1.00% | 8 | 198 | -488 | -100 | 57 | 52% | 74% |
| 184 | big_day | FRA40 | D1 | `{"k": 1.5, "mode": "fade"}` | 2.00% | 8 | 194 | -194 | -180 | 6 | 16% | 67% |
| 185 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "entry_hm": 18.0}` | 0.75% | 8 | 194 | -186 | -73 | 10 | 16% | 50% |
| 186 | fh_retest | DE40 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": null}` | 0.75% | 7 | 180 | -478 | -74 | 189 | 38% | 50% |
| 187 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.25% | 7 | 186 | -140 | -43 | 10 | 12% | 30% |
| 188 | time_window | DE40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long"}` | 0.25% | 7 | 175 | -321 | -44 | 351 | 54% | 50% |
| 189 | compression_break | ESP35 | M30 | `{"kind": "nr7", "sl": "mid"}` | 1.25% | 7 | 180 | -402 | -125 | 27 | 32% | 48% |
| 190 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "against"}` | 1.50% | 7 | 178 | -520 | -146 | 43 | 40% | 51% |
| 191 | compression_break | ESP35 | M30 | `{"kind": "nr4", "sl": "mid"}` | 1.25% | 7 | 172 | -501 | -125 | 49 | 40% | 49% |
| 192 | pdhl | ESP35 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 2.0}` | 0.75% | 7 | 171 | -241 | -75 | 24 | 20% | 50% |
| 193 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | 7 | 168 | -280 | -60 | 33 | 16% | 55% |
| 194 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | 7 | 168 | -280 | -60 | 33 | 16% | 55% |
| 195 | prev_week | FRA40 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | 0.50% | 7 | 166 | -521 | -66 | 55 | 48% | 33% |
| 196 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.50% | 7 | 164 | -353 | -90 | 41 | 40% | 27% |
| 197 | close_fade | ESP35 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 1.00% | 6 | 162 | -164 | -62 | 80 | 24% | 48% |
| 198 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "te": 14.0}` | 0.25% | 6 | 155 | -471 | -89 | 340 | 54% | 44% |
| 199 | big_day | FRA40 | D1 | `{"k": 2.0, "mode": "fade"}` | 2.00% | 6 | 161 | 0 | 0 | 1 | 4% | 100% |
| 200 | overnight | ESP35 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 0.75}` | 1.50% | 6 | 160 | -462 | -158 | 64 | 20% | 50% |
| 201 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.75% | 6 | 158 | -387 | -172 | 11 | 12% | 27% |
| 202 | round_fade | ESP35 | M30 | `{"step": 100.0, "touch_atr": 0.25, "tp": "step"}` | 0.25% | 6 | 151 | -29 | -21 | 4 | 12% | 100% |
| 203 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "below_pdc", "sl_datr": 1.5}` | 1.50% | 6 | 144 | -331 | -252 | 157 | 46% | 56% |
| 204 | compression_break | ESP35 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": null}` | 1.50% | 6 | 147 | -332 | -144 | 23 | 24% | 52% |
| 205 | calendar | FRA40 | M30 | `{"kind": "weekday", "wd": 4, "side": "short"}` | 1.50% | 6 | 142 | -587 | -151 | 94 | 36% | 50% |
| 206 | compression_break | FRA40 | M30 | `{"kind": "inside", "sl": "mid"}` | 0.75% | 6 | 141 | -387 | -68 | 32 | 44% | 47% |
| 207 | fh_mult | DE40 | M30 | `{"mult": 0.25, "sl": "opp", "tp_r": 2.0}` | 0.25% | 6 | 135 | -358 | -25 | 404 | 42% | 42% |
| 208 | compression_break | ESP35 | M30 | `{"kind": "nr7", "sl": "far"}` | 2.00% | 6 | 139 | -443 | -167 | 28 | 32% | 46% |
| 209 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 10.5}` | 0.75% | 6 | 138 | -475 | -73 | 116 | 56% | 48% |
| 210 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "ref", "tp_r": 2.0}` | 0.50% | 5 | 136 | -330 | -49 | 67 | 32% | 43% |
| 211 | round_fade | ESP35 | M30 | `{"step": 100.0, "touch_atr": 0.1, "tp": "step"}` | 0.25% | 5 | 136 | -29 | -25 | 6 | 12% | 67% |
| 212 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "r", "trend": "with"}` | 1.00% | 5 | 136 | -540 | -100 | 35 | 44% | 49% |
| 213 | close_fade | DE40 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 1.50% | 5 | 130 | -521 | -132 | 271 | 50% | 46% |
| 214 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.25% | 5 | 135 | -176 | -25 | 46 | 36% | 46% |
| 215 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "r", "trend": "with"}` | 1.50% | 5 | 134 | -556 | -150 | 46 | 36% | 52% |
| 216 | prev_week | DE40 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | 5 | 124 | -268 | -61 | 49 | 38% | 33% |
| 217 | time_window | ESP35 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "short", "wds": [4]}` | 1.00% | 5 | 126 | -373 | -99 | 18 | 20% | 50% |
| 218 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | 0.75% | 5 | 125 | -597 | -165 | 10 | 8% | 20% |
| 219 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.25% | 5 | 123 | -232 | -25 | 46 | 32% | 39% |
| 220 | prev_week | ESP35 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 1.00% | 5 | 122 | -294 | -86 | 3 | 4% | 33% |
| 221 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.50% | 5 | 114 | -529 | -132 | 215 | 50% | 44% |
| 222 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | 0.25% | 5 | 114 | -145 | -66 | 9 | 12% | 33% |
| 223 | compression_break | ESP35 | M30 | `{"kind": "inside", "sl": "far"}` | 2.00% | 5 | 113 | -447 | -199 | 21 | 24% | 48% |
| 224 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 1.50% | 4 | 108 | -432 | -147 | 83 | 52% | 51% |
| 225 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 1.50% | 4 | 108 | -432 | -147 | 83 | 52% | 51% |
| 226 | big_day | ESP35 | D1 | `{"k": 1.5, "mode": "follow"}` | 2.00% | 4 | 107 | -293 | -179 | 3 | 4% | 67% |
| 227 | us_open_fade | DE40 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "retrace"}` | 0.50% | 4 | 99 | -517 | -50 | 61 | 46% | 38% |
| 228 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 1.25% | 4 | 103 | -488 | -124 | 38 | 28% | 47% |
| 229 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 1.25% | 4 | 103 | -488 | -124 | 38 | 28% | 47% |
| 230 | us_open_fade | DE40 | M30 | `{"k": 1.2, "tp": "retrace", "sl_mult": 1.0}` | 0.50% | 4 | 97 | -536 | -50 | 56 | 33% | 34% |
| 231 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.50% | 4 | 97 | -529 | -132 | 201 | 50% | 44% |
| 232 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "below_pdc", "sl_datr": 0.75}` | 0.75% | 4 | 101 | -17 | -17 | 1 | 4% | 100% |
| 233 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "r", "trend": null}` | 0.75% | 4 | 99 | -506 | -74 | 84 | 56% | 49% |
| 234 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 0.75}` | 0.75% | 4 | 98 | -43 | -18 | 2 | 4% | 50% |
| 235 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "sides": "long"}` | 1.50% | 4 | 98 | -541 | -150 | 44 | 44% | 57% |
| 236 | overnight | FRA40 | M30 | `{"side": "long", "cond": null, "sl_datr": 0.75}` | 1.00% | 4 | 95 | -594 | -138 | 267 | 48% | 52% |
| 237 | prev_week | FRA40 | H1 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 0.50% | 4 | 94 | -377 | -55 | 31 | 28% | 29% |
| 238 | overnight | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 19.0}` | 1.50% | 4 | 92 | -418 | -293 | 32 | 12% | 44% |
| 239 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | 4 | 87 | -393 | -121 | 59 | 29% | 29% |
| 240 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "mid", "trend": null}` | 1.00% | 4 | 89 | -438 | -95 | 47 | 44% | 68% |
| 241 | prev_week | DE40 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | 0.25% | 4 | 85 | -356 | -286 | 70 | 42% | 36% |
| 242 | donchian | ESP35 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": null}` | 1.50% | 3 | 87 | -232 | -165 | 2 | 4% | 50% |
| 243 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.75% | 3 | 84 | -168 | -56 | 8 | 8% | 50% |
| 244 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.75% | 3 | 84 | -168 | -56 | 8 | 8% | 50% |
| 245 | prev_week | FRA40 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | 3 | 80 | -140 | -66 | 10 | 12% | 30% |
| 246 | donchian | ESP35 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": null}` | 1.50% | 3 | 78 | -398 | -293 | 3 | 4% | 33% |
| 247 | us_open_fade | FRA40 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "retrace"}` | 0.25% | 3 | 76 | -281 | -24 | 68 | 44% | 41% |
| 248 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.75% | 3 | 75 | -321 | -134 | 10 | 8% | 40% |
| 249 | donchian | DE40 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 3 | 68 | -501 | -95 | 51 | 42% | 33% |
| 250 | orb | DE40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": null}` | 0.25% | 3 | 68 | -456 | -89 | 318 | 50% | 43% |
| 251 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 3 | 70 | -326 | -134 | 11 | 8% | 36% |
| 252 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "sides": "long"}` | 1.00% | 3 | 69 | -545 | -99 | 76 | 44% | 57% |
| 253 | donchian | DE40 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": "with"}` | 0.25% | 3 | 65 | -111 | -43 | 9 | 21% | 44% |
| 254 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "far", "trend": "with"}` | 1.00% | 3 | 67 | -300 | -93 | 22 | 32% | 45% |
| 255 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 1.25% | 3 | 67 | -467 | -124 | 35 | 32% | 46% |
| 256 | overnight | ESP35 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 0.75}` | 1.25% | 3 | 63 | -306 | -293 | 10 | 12% | 80% |
| 257 | donchian | DE40 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": null}` | 0.75% | 2 | 59 | -531 | -79 | 39 | 46% | 36% |
| 258 | donchian | DE40 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": "with"}` | 0.75% | 2 | 59 | -531 | -79 | 39 | 46% | 36% |
| 259 | late_momentum | ESP35 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "follow"}` | 2.00% | 2 | 61 | -438 | -199 | 20 | 24% | 50% |
| 260 | gap | DE40 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 0.50% | 2 | 58 | -510 | -50 | 154 | 38% | 49% |
| 261 | close_to_open | DE40 | M30 | `{"side": "long", "cond": "below_pdc", "sl_datr": 0.75}` | 0.75% | 2 | 57 | -358 | -252 | 157 | 54% | 56% |
| 262 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": null}` | 0.25% | 2 | 58 | -283 | -25 | 89 | 52% | 42% |
| 263 | pdhl | FRA40 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 2.0}` | 0.25% | 2 | 57 | -84 | -25 | 12 | 16% | 33% |
| 264 | gap | FRA40 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 1.5}` | 1.00% | 2 | 56 | -519 | -95 | 41 | 36% | 46% |
| 265 | close_to_open | ESP35 | M30 | `{"side": "long", "entry_hm": 17.5, "exit_hm": 10.0}` | 1.50% | 2 | 56 | -321 | -293 | 26 | 8% | 54% |
| 266 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [-1, 0], "hold_days": 2}` | 1.25% | 2 | 55 | -414 | -166 | 5 | 4% | 20% |
| 267 | fh_retest | ESP35 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": null}` | 1.00% | 2 | 49 | -567 | -99 | 70 | 32% | 53% |
| 268 | pdhl | ESP35 | H1 | `{"mode": "break", "sl_atr": 1.0}` | 0.50% | 2 | 48 | -62 | -43 | 8 | 8% | 50% |
| 269 | compression_break | ESP35 | M30 | `{"kind": "inside", "sl": "mid"}` | 1.50% | 2 | 46 | -546 | -142 | 28 | 28% | 43% |
| 270 | compression_break | ESP35 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": 2.0}` | 1.50% | 2 | 44 | -332 | -144 | 23 | 24% | 52% |
| 271 | gap | FRA40 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 0.50% | 2 | 44 | -108 | -49 | 7 | 12% | 57% |
| 272 | round_fade | ESP35 | M30 | `{"step": 100.0, "touch_atr": 0.25, "tp": "r"}` | 0.25% | 2 | 43 | -19 | -18 | 4 | 12% | 100% |
| 273 | pdhl | ESP35 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 2.0}` | 0.75% | 2 | 39 | -230 | -75 | 24 | 12% | 50% |
| 274 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 0.75% | 2 | 39 | -381 | -72 | 122 | 44% | 61% |
| 275 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 0.75% | 2 | 39 | -381 | -72 | 122 | 44% | 61% |
| 276 | orb | DE40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.25% | 1 | 31 | -300 | -25 | 144 | 46% | 41% |
| 277 | prev_week | ESP35 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 1.00% | 1 | 31 | -385 | -96 | 3 | 4% | 33% |
| 278 | fh_retest | ESP35 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": "with"}` | 1.00% | 1 | 28 | -532 | -99 | 40 | 40% | 57% |
| 279 | prev_week | FRA40 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 0.50% | 1 | 26 | -392 | -50 | 54 | 48% | 37% |
| 280 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": null}` | 0.25% | 1 | 23 | -61 | -22 | 4 | 4% | 25% |
| 281 | donchian | FRA40 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": "with"}` | 1.00% | 1 | 19 | -529 | -118 | 17 | 28% | 35% |
| 282 | big_day | ESP35 | D1 | `{"k": 2.0, "mode": "fade"}` | 2.00% | 1 | 17 | -97 | -97 | 1 | 4% | 100% |
| 283 | pullback | ESP35 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | 0.25% | 1 | 17 | -22 | -22 | 5 | 8% | 60% |
| 284 | lunch_break | ESP35 | M30 | `{"sl": "far", "tp_r": null, "trend": null}` | 0.75% | 1 | 15 | -336 | -67 | 60 | 32% | 42% |
| 285 | late_momentum | ESP35 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "fade"}` | 0.75% | 1 | 14 | -220 | -220 | 15 | 28% | 60% |
| 286 | overnight | ESP35 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 1.5}` | 2.00% | 0 | 12 | -293 | -112 | 13 | 4% | 38% |
| 287 | pdhl | FRA40 | M30 | `{"mode": "reject", "trend": "with"}` | 0.25% | 0 | 11 | -302 | -32 | 54 | 32% | 39% |
| 288 | round | DE40 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.0}` | 0.25% | 0 | 8 | -396 | -149 | 398 | 50% | 54% |
| 289 | round_fade | ESP35 | M30 | `{"step": 100.0, "touch_atr": 0.1, "tp": "r"}` | 0.25% | 0 | 5 | -30 | -25 | 6 | 8% | 67% |
| 290 | lunch_break | ESP35 | M30 | `{"sl": "far", "tp_r": null, "trend": "with"}` | 1.25% | 0 | 3 | -518 | -125 | 117 | 44% | 50% |
| 291 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "mid", "te": 14.0}` | 0.25% | 0 | 2 | -83 | -22 | 5 | 4% | 20% |
| 292 | d1_meanrev | ESP35 | D1 | `{"n_down": 2, "ma": 100, "side": "long"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 293 | d1_meanrev | ESP35 | D1 | `{"n_down": 2, "ma": 200, "side": "long"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 294 | d1_meanrev | ESP35 | D1 | `{"n_down": 3, "ma": 100, "side": "long"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 295 | d1_meanrev | ESP35 | D1 | `{"n_down": 3, "ma": 200, "side": "long"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 296 | d1_meanrev | ESP35 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 297 | d1_meanrev | ESP35 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200, "use_trend": false}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 298 | d1_meanrev | ESP35 | D1 | `{"n_down": 3, "ma": 200, "side": "short"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 299 | d1_meanrev | ESP35 | D1 | `{"n_down": 2, "ma": 200, "exit": "hold", "max_hold": 3}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 300 | big_day | ESP35 | D1 | `{"k": 1.5, "mode": "fade"}` | 1.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 301 | donchian | ESP35 | D1 | `{"n_ch": 20, "trail_atr": 3.0}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 302 | donchian | ESP35 | D1 | `{"n_ch": 55, "trail_atr": 3.0}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 303 | donchian | ESP35 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": null}` | 1.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 304 | donchian | ESP35 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": "with"}` | 1.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 305 | donchian | ESP35 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": null}` | 1.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 306 | donchian | ESP35 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": "with"}` | 1.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 307 | overnight | ESP35 | M30 | `{"side": "short", "cond": null, "sl_datr": 1.0}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 308 | overnight | ESP35 | M30 | `{"side": "short", "cond": "up_day", "sl_datr": 1.0}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 309 | round | ESP35 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.0}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 310 | round | ESP35 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.0}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 311 | round | ESP35 | M30 | `{"step": 100.0, "trend": "with"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 312 | time_window | ESP35 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 313 | time_window | ESP35 | M30 | `{"entry_hm": 18.5, "exit_hour": 22, "side": "long"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 314 | time_window | ESP35 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_up"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 315 | time_window | ESP35 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_down"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 316 | time_window | ESP35 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "trend": "with"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 317 | time_window | ESP35 | M30 | `{"entry_hm": 12.0, "exit_hour": 16, "side": "long"}` | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 318 | time_window | ESP35 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "sl_datr": 0.3}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 319 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 320 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [0, 1, 2, 3], "hold_days": 1}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 321 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [-1], "hold_days": 4}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 322 | calendar | ESP35 | M30 | `{"kind": "tom", "tom_days": [-1, 0, 1, 2], "hold_days": 1, "entry_hm": 18.0}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 323 | close_to_open | ESP35 | M30 | `{"side": "short", "cond": "up_cash"}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 324 | d1_meanrev | FRA40 | D1 | `{"n_down": 3, "ma": 200, "side": "short"}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 325 | donchian | FRA40 | D1 | `{"n_ch": 20, "trail_atr": 3.0}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 326 | donchian | FRA40 | D1 | `{"n_ch": 55, "trail_atr": 3.0}` | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 327 | donchian | FRA40 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": null}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 328 | donchian | FRA40 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": "with"}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 329 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 330 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 331 | overnight | FRA40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 18.0}` | 0.75% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 332 | round | FRA40 | M30 | `{"step": 50.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.0}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 333 | round | FRA40 | M30 | `{"step": 50.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.3}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 334 | round | FRA40 | M30 | `{"step": 50.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.0}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 335 | round | FRA40 | M30 | `{"step": 50.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.3}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 336 | round | FRA40 | M30 | `{"step": 50.0, "trend": "with"}` | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | 0% |
| 337 | big_day | DE40 | D1 | `{"k": 2.0, "mode": "follow"}` | 2.00% | -0 | -1 | -225 | -134 | 4 | 8% | 50% |
| 338 | pdhl | FRA40 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 2.0}` | 0.25% | -0 | -2 | -67 | -25 | 12 | 12% | 42% |
| 339 | calendar | ESP35 | M30 | `{"kind": "weekday", "wd": 0, "side": "long", "entry_hm": 18.0, "exit_hour": 10}` | 0.75% | -0 | -2 | -26 | -15 | 1 | 0% | 0% |
| 340 | close_to_open | ESP35 | M30 | `{"side": "long", "cond": "up_cash", "sl_datr": 0.75}` | 0.75% | -0 | -2 | -26 | -15 | 1 | 0% | 0% |
| 341 | kagels_915 | FRA40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "far", "te": 14.0}` | 0.25% | -0 | -3 | -51 | -25 | 11 | 24% | 55% |
| 342 | us_open_fade | DE40 | M30 | `{"k": 0.8, "tp": "retrace", "sl_mult": 1.0}` | 0.25% | -0 | -3 | -423 | -25 | 110 | 42% | 36% |
| 343 | overnight | FRA40 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 0.75}` | 0.75% | -0 | -4 | -240 | -54 | 23 | 16% | 43% |
| 344 | donchian | DE40 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": null}` | 0.50% | -0 | -6 | -533 | -206 | 42 | 42% | 33% |
| 345 | donchian | DE40 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": "with"}` | 0.50% | -0 | -7 | -342 | -119 | 30 | 46% | 30% |
| 346 | donchian | DE40 | H4 | `{"n_ch": 80, "trail_atr": 5.0, "trend": null}` | 0.50% | -0 | -7 | -342 | -119 | 30 | 46% | 30% |
| 347 | donchian | DE40 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": null}` | 0.25% | -0 | -7 | -111 | -52 | 14 | 21% | 36% |
| 348 | close_fade | ESP35 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 1.00% | -0 | -8 | -193 | -44 | 80 | 28% | 49% |
| 349 | time_window | DE40 | M30 | `{"entry_hm": 12.0, "exit_hour": 16, "side": "long"}` | 0.25% | -0 | -8 | -353 | -24 | 351 | 46% | 52% |
| 350 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with", "exit_hour": 22}` | 0.25% | -0 | -10 | -53 | -24 | 4 | 8% | 50% |
| 351 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": "with"}` | 0.25% | -0 | -10 | -53 | -24 | 4 | 8% | 50% |
| 352 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -0 | -10 | -53 | -24 | 4 | 8% | 50% |
| 353 | orb | FRA40 | M30 | `{"re": 10.5, "te": 14.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -0 | -10 | -53 | -24 | 4 | 8% | 50% |
| 354 | orb | FRA40 | M30 | `{"re": 10.5, "te": 16.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -0 | -10 | -53 | -24 | 4 | 8% | 50% |
| 355 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": null}` | 0.25% | -0 | -11 | -442 | -25 | 89 | 44% | 35% |
| 356 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": null}` | 0.25% | -0 | -11 | -20 | -20 | 2 | 4% | 50% |
| 357 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": "with"}` | 0.25% | -0 | -11 | -20 | -20 | 2 | 4% | 50% |
| 358 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": null}` | 0.25% | -0 | -11 | -20 | -20 | 2 | 4% | 50% |
| 359 | orb | FRA40 | M30 | `{"re": 11.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -0 | -11 | -20 | -20 | 2 | 4% | 50% |
| 360 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.50% | -1 | -14 | -214 | -49 | 25 | 28% | 40% |
| 361 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": null}` | 0.25% | -1 | -14 | -87 | -25 | 10 | 20% | 50% |
| 362 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "mid", "trend": "with"}` | 1.25% | -1 | -14 | -533 | -125 | 51 | 50% | 71% |
| 363 | fh_retest | ESP35 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": "with"}` | 1.00% | -1 | -15 | -326 | -100 | 25 | 28% | 56% |
| 364 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "trend": "with"}` | 0.75% | -1 | -17 | -488 | -75 | 43 | 44% | 40% |
| 365 | time_window | FRA40 | M30 | `{"entry_hm": 12.0, "exit_hour": 16, "side": "long"}` | 0.50% | -1 | -18 | -244 | -90 | 43 | 16% | 58% |
| 366 | round | DE40 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.3}` | 0.25% | -1 | -19 | -369 | -149 | 378 | 54% | 58% |
| 367 | fh_mult | ESP35 | M30 | `{"mult": 0.25, "sl": "opp", "tp_r": 2.0}` | 0.50% | -1 | -21 | -276 | -50 | 61 | 36% | 43% |
| 368 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "trend": "with"}` | 0.50% | -1 | -22 | -467 | -47 | 64 | 40% | 52% |
| 369 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "r", "trend": "with"}` | 1.00% | -1 | -24 | -338 | -93 | 22 | 28% | 41% |
| 370 | or_fail | FRA40 | M30 | `{"re": 11.0, "tp": "far", "trend": null}` | 0.75% | -1 | -28 | -558 | -74 | 84 | 44% | 54% |
| 371 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "sides": "long", "te": 14.0}` | 0.75% | -1 | -28 | -507 | -74 | 32 | 28% | 47% |
| 372 | overnight | ESP35 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 1.5}` | 2.00% | -1 | -29 | -306 | -293 | 8 | 8% | 75% |
| 373 | round | ESP35 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 1.0, "min_body": 0.3}` | 0.75% | -1 | -29 | -345 | -75 | 19 | 12% | 37% |
| 374 | big_day | ESP35 | D1 | `{"k": 2.0, "mode": "follow"}` | 2.00% | -1 | -29 | -179 | -179 | 1 | 0% | 0% |
| 375 | lunch_break | DE40 | M30 | `{"sl": "mid", "tp_r": null, "trend": null}` | 0.25% | -1 | -28 | -384 | -25 | 275 | 42% | 41% |
| 376 | us_open_fade | FRA40 | M30 | `{"k": 1.2, "tp": "retrace", "sl_mult": 1.0}` | 0.50% | -1 | -29 | -506 | -49 | 57 | 44% | 39% |
| 377 | pdhl | DE40 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 2.0}` | 0.25% | -1 | -29 | -346 | -25 | 202 | 38% | 39% |
| 378 | close_fade | FRA40 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 0.50% | -1 | -32 | -94 | -45 | 36 | 20% | 56% |
| 379 | lunch_break | ESP35 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": "with"}` | 1.25% | -1 | -32 | -518 | -125 | 117 | 44% | 50% |
| 380 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "with"}` | 0.50% | -1 | -33 | -256 | -58 | 27 | 24% | 52% |
| 381 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "r", "trend": null}` | 0.50% | -1 | -31 | -432 | -50 | 76 | 42% | 43% |
| 382 | pdhl | ESP35 | M30 | `{"mode": "reject", "trend": "with"}` | 0.75% | -1 | -33 | -321 | -74 | 38 | 36% | 45% |
| 383 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "far", "trend": null}` | 0.50% | -1 | -33 | -518 | -50 | 76 | 42% | 51% |
| 384 | compression_break | DE40 | M30 | `{"kind": "nr7", "sl": "far"}` | 2.00% | -1 | -35 | -592 | -191 | 50 | 42% | 50% |
| 385 | time_window | DE40 | M30 | `{"entry_hm": 16.0, "exit_hour": 18, "side": "long"}` | 0.25% | -2 | -36 | -247 | -24 | 353 | 50% | 50% |
| 386 | donchian | ESP35 | H4 | `{"n_ch": 40, "trail_atr": 3.0, "trend": "with"}` | 1.50% | -2 | -41 | -231 | -164 | 2 | 4% | 50% |
| 387 | donchian | ESP35 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": null}` | 1.50% | -2 | -41 | -231 | -164 | 2 | 4% | 50% |
| 388 | donchian | ESP35 | H4 | `{"n_ch": 80, "trail_atr": 3.0, "trend": "with"}` | 1.50% | -2 | -41 | -231 | -164 | 2 | 4% | 50% |
| 389 | lunch_break | FRA40 | M30 | `{"sl": "mid", "tp_r": null, "trend": null}` | 0.25% | -2 | -41 | -252 | -24 | 120 | 32% | 39% |
| 390 | fh_retest | ESP35 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": "with"}` | 1.00% | -2 | -44 | -520 | -99 | 40 | 40% | 57% |
| 391 | us_open_fade | FRA40 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "retrace"}` | 0.25% | -2 | -45 | -328 | -25 | 165 | 44% | 42% |
| 392 | d1_meanrev | DE40 | D1 | `{"n_down": 3, "ma": 100, "side": "long"}` | 2.00% | -2 | -44 | -459 | -154 | 19 | 38% | 63% |
| 393 | d1_meanrev | DE40 | D1 | `{"n_down": 2, "ma": 200, "exit": "hold", "max_hold": 3}` | 2.00% | -2 | -46 | -554 | -198 | 53 | 46% | 55% |
| 394 | time_window | FRA40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "cond": "session_up"}` | 0.50% | -2 | -49 | -129 | -50 | 18 | 12% | 50% |
| 395 | donchian | ESP35 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": "with"}` | 1.50% | -2 | -50 | -398 | -293 | 3 | 4% | 33% |
| 396 | overnight | FRA40 | M30 | `{"side": "long", "cond": "down_vs_pdc", "sl_datr": 1.5}` | 1.50% | -2 | -51 | -269 | -124 | 24 | 16% | 42% |
| 397 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.75% | -2 | -51 | -452 | -72 | 72 | 44% | 42% |
| 398 | d1_meanrev | FRA40 | D1 | `{"n_down": 2, "ma": 200, "side": "long"}` | 2.00% | -2 | -52 | -252 | -95 | 5 | 12% | 60% |
| 399 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "far", "trend": "with"}` | 0.75% | -2 | -51 | -543 | -75 | 60 | 38% | 53% |
| 400 | overnight | FRA40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "trend": "with"}` | 1.25% | -2 | -58 | -522 | -136 | 144 | 32% | 50% |
| 401 | big_day | DE40 | D1 | `{"k": 2.0, "mode": "fade"}` | 2.00% | -2 | -56 | -178 | -174 | 4 | 4% | 50% |
| 402 | pdhl | FRA40 | M30 | `{"mode": "reject", "ts": 16.0, "te": 18.0, "tp": "mid"}` | 0.50% | -2 | -58 | -441 | -50 | 157 | 44% | 42% |
| 403 | fh_retest | ESP35 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": "with"}` | 1.00% | -2 | -59 | -315 | -100 | 25 | 28% | 56% |
| 404 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "sides": "long", "te": 14.0}` | 0.25% | -2 | -59 | -370 | -89 | 194 | 42% | 43% |
| 405 | calendar | FRA40 | M30 | `{"kind": "weekday", "wd": 3, "side": "short"}` | 1.25% | -3 | -63 | -598 | -118 | 87 | 44% | 49% |
| 406 | close_fade | FRA40 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 0.50% | -3 | -63 | -126 | -43 | 36 | 8% | 47% |
| 407 | gap | ESP35 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 2.5}` | 0.75% | -3 | -65 | -379 | -203 | 26 | 16% | 46% |
| 408 | overnight | FRA40 | M30 | `{"side": "long", "cond": "down_day", "sl_datr": 1.5}` | 1.50% | -3 | -65 | -268 | -124 | 26 | 16% | 42% |
| 409 | fh_mult | ESP35 | M30 | `{"mult": 1.0, "sl": "ref", "tp_r": 2.0}` | 0.50% | -3 | -65 | -206 | -164 | 5 | 12% | 60% |
| 410 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "mid", "te": 14.0}` | 0.25% | -3 | -66 | -83 | -22 | 5 | 0% | 20% |
| 411 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with", "exit_hour": 22}` | 0.50% | -3 | -67 | -94 | -49 | 4 | 4% | 25% |
| 412 | d1_meanrev | FRA40 | D1 | `{"n_down": 2, "ma": 100, "side": "long"}` | 2.00% | -3 | -67 | -202 | -95 | 4 | 8% | 50% |
| 413 | orb | DE40 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": null}` | 0.25% | -3 | -66 | -357 | -25 | 280 | 46% | 41% |
| 414 | lunch_break | ESP35 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": null}` | 0.75% | -3 | -72 | -336 | -67 | 60 | 32% | 42% |
| 415 | donchian | FRA40 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": "with"}` | 0.75% | -3 | -73 | -73 | -64 | 1 | 0% | 0% |
| 416 | donchian | FRA40 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": "with"}` | 0.75% | -3 | -73 | -73 | -64 | 1 | 0% | 0% |
| 417 | donchian | FRA40 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": "with"}` | 0.75% | -3 | -73 | -73 | -64 | 1 | 0% | 0% |
| 418 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 11.0}` | 0.50% | -3 | -73 | -392 | -49 | 142 | 42% | 50% |
| 419 | lunch_break | DE40 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": null}` | 0.25% | -3 | -75 | -322 | -25 | 275 | 46% | 43% |
| 420 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": null}` | 0.25% | -3 | -78 | -120 | -25 | 10 | 12% | 40% |
| 421 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "trend": "against"}` | 0.50% | -3 | -79 | -590 | -49 | 52 | 40% | 37% |
| 422 | fh_retest | ESP35 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": null}` | 1.00% | -3 | -79 | -496 | -100 | 44 | 28% | 50% |
| 423 | pdhl | FRA40 | M30 | `{"mode": "break", "trend": "with"}` | 0.25% | -3 | -83 | -172 | -25 | 68 | 40% | 43% |
| 424 | close_fade | FRA40 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 0.50% | -3 | -84 | -198 | -44 | 36 | 12% | 47% |
| 425 | time_window | FRA40 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long"}` | 0.50% | -3 | -87 | -382 | -105 | 43 | 16% | 44% |
| 426 | gap | FRA40 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 1.5}` | 0.50% | -4 | -90 | -357 | -51 | 61 | 32% | 44% |
| 427 | fh_mult | ESP35 | M30 | `{"mult": 1.0, "sl": "ref", "tp_r": null}` | 0.50% | -4 | -91 | -206 | -164 | 5 | 12% | 60% |
| 428 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | 0.50% | -4 | -94 | -470 | -49 | 37 | 28% | 24% |
| 429 | donchian | DE40 | D1 | `{"n_ch": 20, "trail_atr": 3.0}` | 1.00% | -4 | -90 | -524 | -79 | 7 | 25% | 43% |
| 430 | close_fade | ESP35 | M30 | `{"k": 0.3, "mode": "fade", "sides": "long"}` | 1.50% | -4 | -95 | -282 | -81 | 63 | 24% | 48% |
| 431 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | 0.50% | -4 | -96 | -141 | -48 | 3 | 0% | 0% |
| 432 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.50% | -4 | -98 | -124 | -45 | 7 | 4% | 29% |
| 433 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.50% | -4 | -98 | -124 | -45 | 7 | 4% | 29% |
| 434 | overnight | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.5}` | 2.00% | -4 | -100 | -383 | -293 | 24 | 8% | 50% |
| 435 | late_momentum | DE40 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "follow"}` | 0.75% | -4 | -97 | -470 | -74 | 44 | 29% | 50% |
| 436 | close_fade | DE40 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 2.00% | -4 | -103 | -584 | -197 | 167 | 42% | 44% |
| 437 | compression_break | FRA40 | M30 | `{"kind": "inside", "sl": "far"}` | 1.50% | -4 | -108 | -389 | -150 | 39 | 40% | 44% |
| 438 | prev_week | ESP35 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 0.75% | -4 | -108 | -341 | -102 | 7 | 4% | 29% |
| 439 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | 0.50% | -4 | -109 | -268 | -165 | 3 | 0% | 0% |
| 440 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | 0.50% | -4 | -109 | -268 | -165 | 3 | 0% | 0% |
| 441 | prev_week | ESP35 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": "with"}` | 0.75% | -4 | -110 | -269 | -60 | 7 | 4% | 29% |
| 442 | us_open_fade | FRA40 | M30 | `{"k": 0.8, "tp": "retrace", "sl_mult": 1.0}` | 0.25% | -4 | -112 | -379 | -25 | 146 | 40% | 39% |
| 443 | gap | DE40 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 0.50% | -4 | -108 | -368 | -50 | 134 | 42% | 51% |
| 444 | pullback | ESP35 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | 0.50% | -4 | -112 | -432 | -247 | 40 | 28% | 45% |
| 445 | fh_mult | ESP35 | M30 | `{"mult": 1.0, "sl": "opp", "tp_r": 2.0}` | 0.75% | -5 | -113 | -367 | -164 | 8 | 12% | 38% |
| 446 | prev_week | FRA40 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | -5 | -113 | -113 | -25 | 5 | 0% | 0% |
| 447 | close_fade | FRA40 | M30 | `{"k": 0.3, "mode": "fade", "sides": "short"}` | 1.00% | -5 | -113 | -368 | -44 | 116 | 40% | 44% |
| 448 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -5 | -114 | -149 | -45 | 5 | 0% | 20% |
| 449 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -5 | -114 | -149 | -45 | 5 | 0% | 20% |
| 450 | donchian | DE40 | H4 | `{"n_ch": 20, "trail_atr": 3.0, "trend": null}` | 0.50% | -5 | -109 | -540 | -136 | 66 | 54% | 39% |
| 451 | us_open_fade | ESP35 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "retrace"}` | 0.75% | -5 | -115 | -574 | -73 | 38 | 28% | 39% |
| 452 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "trend": "with"}` | 1.50% | -5 | -120 | -541 | -150 | 45 | 36% | 56% |
| 453 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.50% | -5 | -120 | -305 | -102 | 9 | 4% | 22% |
| 454 | donchian | DE40 | H4 | `{"n_ch": 40, "trail_atr": 5.0, "trend": "with"}` | 0.50% | -5 | -116 | -532 | -206 | 40 | 42% | 30% |
| 455 | kagels_915 | ESP35 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "trend": "with", "te": 12.0}` | 0.75% | -5 | -123 | -507 | -74 | 27 | 28% | 44% |
| 456 | pdhl | ESP35 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 2.0}` | 0.75% | -5 | -123 | -327 | -75 | 64 | 32% | 39% |
| 457 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "trend": "with", "te": 14.0}` | 0.25% | -5 | -119 | -432 | -89 | 171 | 38% | 42% |
| 458 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "mid", "trend": "with"}` | 1.50% | -5 | -125 | -470 | -150 | 35 | 36% | 74% |
| 459 | fh_mult | ESP35 | M30 | `{"mult": 0.25, "sl": "ref", "tp_r": null}` | 0.25% | -5 | -127 | -393 | -164 | 25 | 12% | 16% |
| 460 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "r", "trend": "with"}` | 0.25% | -5 | -122 | -285 | -25 | 41 | 33% | 39% |
| 461 | d1_meanrev | DE40 | D1 | `{"n_down": 3, "ma": 200, "side": "short"}` | 2.00% | -5 | -122 | -173 | -124 | 2 | 4% | 50% |
| 462 | time_window | FRA40 | M30 | `{"entry_hm": 18.5, "exit_hour": 22, "side": "long"}` | 0.75% | -5 | -128 | -458 | -79 | 387 | 40% | 51% |
| 463 | fh_mult | ESP35 | M30 | `{"mult": 0.25, "sl": "ref", "tp_r": 2.0}` | 0.25% | -5 | -129 | -183 | -25 | 25 | 16% | 36% |
| 464 | donchian | ESP35 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": null}` | 1.25% | -5 | -132 | -351 | -293 | 1 | 0% | 0% |
| 465 | donchian | ESP35 | H4 | `{"n_ch": 20, "trail_atr": 5.0, "trend": "with"}` | 1.25% | -5 | -132 | -351 | -293 | 1 | 0% | 0% |
| 466 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "long"}` | 1.50% | -5 | -136 | -589 | -140 | 39 | 44% | 51% |
| 467 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "sides": "short"}` | 0.50% | -5 | -137 | -452 | -50 | 70 | 44% | 53% |
| 468 | fh_retest | FRA40 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": null}` | 0.50% | -5 | -137 | -377 | -50 | 87 | 48% | 48% |
| 469 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "ref", "tp_r": null}` | 0.25% | -6 | -140 | -199 | -164 | 4 | 4% | 25% |
| 470 | lunch_break | FRA40 | M30 | `{"sl": "mid", "tp_r": null, "trend": "with"}` | 0.50% | -6 | -141 | -381 | -50 | 170 | 48% | 46% |
| 471 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "r", "trend": "with"}` | 0.25% | -6 | -141 | -181 | -24 | 26 | 24% | 31% |
| 472 | pdhl | FRA40 | H1 | `{"mode": "reject", "sl_atr": 1.0}` | 0.25% | -6 | -141 | -292 | -34 | 69 | 36% | 39% |
| 473 | gap | FRA40 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 2.5}` | 0.50% | -6 | -143 | -360 | -51 | 61 | 28% | 44% |
| 474 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.25% | -6 | -140 | -266 | -44 | 77 | 29% | 40% |
| 475 | late_momentum | ESP35 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "follow"}` | 1.00% | -6 | -148 | -552 | -185 | 22 | 20% | 32% |
| 476 | close_fade | ESP35 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 0.75% | -6 | -149 | -149 | -39 | 11 | 0% | 18% |
| 477 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "mid", "trend": "with"}` | 1.25% | -6 | -149 | -564 | -121 | 22 | 32% | 68% |
| 478 | orb | DE40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": null, "trend": "with"}` | 0.25% | -6 | -143 | -434 | -89 | 162 | 38% | 41% |
| 479 | pdhl | DE40 | H1 | `{"mode": "reject", "sl_atr": 1.0}` | 0.25% | -6 | -143 | -369 | -44 | 218 | 29% | 45% |
| 480 | compression_break | FRA40 | M30 | `{"kind": "nr4", "sl": "mid"}` | 0.50% | -6 | -150 | -243 | -51 | 33 | 32% | 36% |
| 481 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | 0.25% | -6 | -152 | -439 | -25 | 31 | 20% | 26% |
| 482 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.25% | -6 | -146 | -266 | -44 | 75 | 29% | 40% |
| 483 | us_open_fade | FRA40 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "r"}` | 0.50% | -6 | -152 | -438 | -50 | 74 | 44% | 54% |
| 484 | pdhl | FRA40 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 2.0}` | 0.25% | -6 | -153 | -316 | -35 | 47 | 28% | 38% |
| 485 | time_window | FRA40 | M30 | `{"entry_hm": 16.0, "exit_hour": 18, "side": "long"}` | 0.50% | -6 | -153 | -277 | -50 | 43 | 12% | 51% |
| 486 | prev_week | ESP35 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | 0.75% | -6 | -154 | -419 | -238 | 9 | 4% | 22% |
| 487 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 0.75% | -6 | -157 | -192 | -56 | 5 | 0% | 20% |
| 488 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 0.75% | -6 | -157 | -192 | -56 | 5 | 0% | 20% |
| 489 | gap | FRA40 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 0.50% | -6 | -158 | -297 | -49 | 61 | 28% | 36% |
| 490 | prev_week | ESP35 | H1 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | 0.75% | -6 | -158 | -317 | -165 | 3 | 0% | 0% |
| 491 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 1.50% | -6 | -160 | -584 | -145 | 46 | 36% | 46% |
| 492 | close_fade | FRA40 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 1.25% | -6 | -160 | -495 | -113 | 182 | 36% | 52% |
| 493 | fh_mult | ESP35 | M30 | `{"mult": 0.25, "sl": "opp", "tp_r": null}` | 0.25% | -6 | -160 | -233 | -164 | 4 | 4% | 25% |
| 494 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "far", "tp_r": null, "trend": null}` | 0.25% | -6 | -161 | -184 | -164 | 1 | 0% | 0% |
| 495 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": 2.0}` | 0.25% | -6 | -161 | -184 | -164 | 1 | 0% | 0% |
| 496 | close_fade | ESP35 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 1.50% | -6 | -161 | -523 | -141 | 138 | 36% | 46% |
| 497 | calendar | DE40 | M30 | `{"kind": "weekday", "wd": 0, "side": "long", "entry_hm": 18.0, "exit_hour": 10}` | 0.75% | -6 | -156 | -423 | -93 | 84 | 46% | 45% |
| 498 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "short"}` | 0.75% | -7 | -156 | -467 | -74 | 83 | 33% | 47% |
| 499 | close_fade | ESP35 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 0.75% | -7 | -164 | -206 | -52 | 11 | 4% | 36% |
| 500 | big_day | FRA40 | D1 | `{"k": 2.0, "mode": "follow"}` | 2.00% | -7 | -165 | -165 | -165 | 1 | 0% | 0% |
| 501 | fh_retest | FRA40 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": null}` | 0.50% | -7 | -166 | -402 | -50 | 115 | 44% | 45% |
| 502 | gap | ESP35 | M30 | `{"mode": "cont", "gmin": 0.3, "gmax": 2.0, "tp_r": 1.5}` | 0.75% | -7 | -168 | -351 | -203 | 26 | 16% | 50% |
| 503 | calendar | FRA40 | M30 | `{"kind": "weekday", "wd": 0, "side": "long"}` | 1.25% | -7 | -170 | -526 | -106 | 90 | 40% | 50% |
| 504 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "far", "te": 14.0}` | 0.25% | -7 | -165 | -348 | -89 | 340 | 50% | 46% |
| 505 | d1_meanrev | DE40 | D1 | `{"n_down": 3, "ma": 200, "side": "long"}` | 1.50% | -7 | -166 | -463 | -116 | 25 | 42% | 60% |
| 506 | d1_meanrev | FRA40 | D1 | `{"n_down": 3, "ma": 200, "side": "long"}` | 2.00% | -7 | -174 | -238 | -95 | 2 | 4% | 50% |
| 507 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "far", "trend": null}` | 0.50% | -7 | -175 | -419 | -69 | 18 | 16% | 28% |
| 508 | compression_break | ESP35 | M30 | `{"kind": "nr4", "sl": "far"}` | 1.50% | -7 | -175 | -376 | -135 | 20 | 16% | 45% |
| 509 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "far", "trend": "with"}` | 0.25% | -7 | -168 | -304 | -25 | 41 | 38% | 39% |
| 510 | close_fade | DE40 | M30 | `{"k": 0.3, "mode": "fade", "sides": "short"}` | 1.50% | -7 | -169 | -596 | -89 | 114 | 42% | 46% |
| 511 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 0.25% | -7 | -171 | -194 | -44 | 101 | 46% | 56% |
| 512 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 0.25% | -7 | -171 | -194 | -44 | 101 | 46% | 56% |
| 513 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "sides": "short"}` | 0.25% | -7 | -179 | -306 | -164 | 2 | 0% | 0% |
| 514 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": "with"}` | 0.25% | -7 | -180 | -316 | -25 | 33 | 20% | 24% |
| 515 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -7 | -181 | -444 | -58 | 117 | 40% | 54% |
| 516 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -7 | -181 | -444 | -58 | 117 | 40% | 54% |
| 517 | pdhl | FRA40 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 2.0}` | 0.25% | -7 | -181 | -385 | -26 | 47 | 20% | 32% |
| 518 | prev_week | FRA40 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | 0.50% | -7 | -182 | -553 | -107 | 30 | 28% | 37% |
| 519 | fh_retest | ESP35 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": null}` | 1.00% | -7 | -182 | -473 | -100 | 44 | 32% | 52% |
| 520 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "mid", "te": 14.0}` | 0.25% | -7 | -175 | -568 | -177 | 363 | 46% | 43% |
| 521 | fh_retest | ESP35 | M30 | `{"fh_end": 11.0, "mm": 1.5, "sl": "mid"}` | 0.50% | -7 | -182 | -231 | -50 | 38 | 20% | 42% |
| 522 | late_momentum | FRA40 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "follow"}` | 0.25% | -7 | -184 | -184 | -24 | 37 | 8% | 30% |
| 523 | fh_mult | ESP35 | M30 | `{"mult": 1.0, "sl": "opp", "tp_r": null}` | 0.75% | -7 | -184 | -367 | -164 | 8 | 12% | 38% |
| 524 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "te": 13.0}` | 0.50% | -7 | -186 | -401 | -49 | 29 | 24% | 38% |
| 525 | pdhl | ESP35 | M30 | `{"mode": "reject", "ts": 16.0, "te": 18.0, "tp": "mid"}` | 0.50% | -8 | -188 | -239 | -49 | 26 | 16% | 35% |
| 526 | fh_retest | FRA40 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": "with"}` | 0.50% | -8 | -189 | -320 | -47 | 47 | 40% | 49% |
| 527 | calendar | FRA40 | M30 | `{"kind": "weekday", "wd": 0, "side": "long", "entry_hm": 18.0, "exit_hour": 10}` | 1.25% | -8 | -189 | -510 | -109 | 90 | 56% | 46% |
| 528 | close_fade | ESP35 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 0.75% | -8 | -190 | -281 | -57 | 20 | 8% | 35% |
| 529 | fh_retest | FRA40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": null}` | 0.50% | -8 | -191 | -370 | -50 | 115 | 40% | 49% |
| 530 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | 0.25% | -8 | -192 | -439 | -70 | 31 | 20% | 26% |
| 531 | d1_meanrev | FRA40 | D1 | `{"n_down": 3, "ma": 100, "side": "long"}` | 2.00% | -8 | -193 | -193 | -95 | 1 | 0% | 0% |
| 532 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "mid", "trend": null}` | 1.00% | -8 | -193 | -549 | -99 | 65 | 40% | 71% |
| 533 | fh_retest | FRA40 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": "with"}` | 0.50% | -8 | -194 | -359 | -47 | 47 | 44% | 47% |
| 534 | late_momentum | FRA40 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "fade"}` | 1.25% | -8 | -194 | -575 | -116 | 49 | 40% | 45% |
| 535 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "trend": null}` | 0.50% | -8 | -194 | -494 | -50 | 136 | 40% | 53% |
| 536 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": 2.0, "trend": null}` | 0.50% | -8 | -196 | -254 | -50 | 42 | 32% | 40% |
| 537 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 1.00% | -8 | -197 | -414 | -116 | 83 | 44% | 48% |
| 538 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 1.00% | -8 | -197 | -414 | -116 | 83 | 44% | 48% |
| 539 | gap | ESP35 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "with"}` | 0.75% | -8 | -198 | -315 | -70 | 11 | 12% | 36% |
| 540 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "mid", "trend": null}` | 0.50% | -8 | -190 | -400 | -50 | 64 | 42% | 67% |
| 541 | late_momentum | FRA40 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "fade"}` | 1.50% | -8 | -199 | -502 | -146 | 44 | 44% | 48% |
| 542 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "long"}` | 0.75% | -8 | -201 | -587 | -74 | 52 | 24% | 35% |
| 543 | round | DE40 | M30 | `{"step": 100.0, "trend": "with"}` | 0.25% | -8 | -194 | -440 | -149 | 195 | 33% | 52% |
| 544 | us_open_fade | ESP35 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "r"}` | 0.75% | -8 | -202 | -410 | -73 | 37 | 24% | 51% |
| 545 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 2.0}` | 0.25% | -8 | -203 | -203 | -24 | 13 | 4% | 15% |
| 546 | calendar | FRA40 | M30 | `{"kind": "tom", "tom_days": [-1, 0], "hold_days": 2}` | 1.25% | -8 | -203 | -475 | -286 | 29 | 40% | 38% |
| 547 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | 0.50% | -8 | -203 | -363 | -102 | 11 | 4% | 18% |
| 548 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | 0.50% | -8 | -203 | -290 | -48 | 11 | 4% | 18% |
| 549 | prev_week | ESP35 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | 0.50% | -8 | -203 | -290 | -48 | 11 | 4% | 18% |
| 550 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "far", "trend": "with", "te": 12.0}` | 0.25% | -8 | -196 | -482 | -89 | 153 | 38% | 40% |
| 551 | round | ESP35 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.3}` | 0.75% | -8 | -205 | -322 | -75 | 19 | 12% | 47% |
| 552 | gap | DE40 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 0.75% | -8 | -201 | -495 | -133 | 145 | 42% | 56% |
| 553 | late_momentum | DE40 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "fade"}` | 1.50% | -8 | -201 | -454 | -150 | 28 | 33% | 43% |
| 554 | or_fail | ESP35 | M30 | `{"re": 11.0, "tp": "r", "trend": null}` | 0.50% | -8 | -210 | -345 | -47 | 18 | 20% | 33% |
| 555 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.75% | -8 | -210 | -367 | -65 | 64 | 36% | 44% |
| 556 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "r", "tp_r": 1.5}` | 0.75% | -8 | -210 | -367 | -65 | 64 | 36% | 44% |
| 557 | prev_week | ESP35 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | 0.75% | -8 | -210 | -550 | -238 | 9 | 4% | 22% |
| 558 | round_fade | FRA40 | M30 | `{"step": 50.0, "trend": "with"}` | 0.25% | -8 | -212 | -373 | -25 | 102 | 40% | 41% |
| 559 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 1.0}` | 0.25% | -8 | -212 | -212 | -24 | 12 | 0% | 17% |
| 560 | orb | DE40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": null}` | 0.25% | -8 | -204 | -525 | -177 | 344 | 58% | 39% |
| 561 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": "with"}` | 0.25% | -9 | -213 | -404 | -41 | 33 | 20% | 18% |
| 562 | donchian | DE40 | D1 | `{"n_ch": 55, "trail_atr": 3.0}` | 1.25% | -9 | -208 | -529 | -86 | 7 | 25% | 14% |
| 563 | d1_meanrev | FRA40 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200, "use_trend": false}` | 2.00% | -9 | -217 | -368 | -191 | 3 | 4% | 33% |
| 564 | big_day | FRA40 | D1 | `{"k": 1.5, "mode": "follow"}` | 2.00% | -9 | -218 | -391 | -189 | 6 | 8% | 33% |
| 565 | round | DE40 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.0}` | 0.25% | -9 | -210 | -347 | -25 | 322 | 46% | 67% |
| 566 | or_fail | DE40 | M30 | `{"re": 10.5, "tp": "r", "trend": "with"}` | 0.50% | -9 | -210 | -518 | -50 | 59 | 33% | 42% |
| 567 | us_open_fade | DE40 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "retrace"}` | 0.25% | -9 | -210 | -481 | -25 | 144 | 42% | 38% |
| 568 | compression_break | DE40 | M30 | `{"kind": "nr7", "sl": "mid"}` | 0.75% | -9 | -211 | -483 | -75 | 50 | 38% | 48% |
| 569 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "trend": "with", "te": 14.0}` | 0.25% | -9 | -221 | -221 | -203 | 1 | 0% | 0% |
| 570 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "trend": "with", "te": 16.0}` | 0.25% | -9 | -221 | -221 | -203 | 1 | 0% | 0% |
| 571 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "sides": "long"}` | 0.25% | -9 | -221 | -221 | -203 | 1 | 0% | 0% |
| 572 | fh_mult | DE40 | M30 | `{"mult": 0.25, "sl": "ref", "tp_r": 2.0}` | 0.25% | -9 | -214 | -499 | -25 | 403 | 46% | 36% |
| 573 | orb | DE40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.25% | -9 | -214 | -444 | -177 | 174 | 42% | 37% |
| 574 | orb | ESP35 | M30 | `{"re": 11.0, "sl": "mid", "tp_r": null, "trend": null}` | 0.25% | -9 | -223 | -247 | -164 | 4 | 0% | 0% |
| 575 | lunch_break | FRA40 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": null}` | 0.25% | -9 | -228 | -303 | -24 | 120 | 28% | 40% |
| 576 | d1_meanrev | FRA40 | D1 | `{"n_down": 0, "rsi2_max": 10, "ma": 200}` | 2.00% | -9 | -230 | -295 | -191 | 2 | 4% | 0% |
| 577 | fh_retest | DE40 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": null}` | 0.75% | -9 | -222 | -520 | -74 | 189 | 38% | 50% |
| 578 | gap | ESP35 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 2.5}` | 1.50% | -9 | -232 | -590 | -144 | 20 | 16% | 35% |
| 579 | late_momentum | FRA40 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "fade"}` | 1.00% | -9 | -233 | -543 | -98 | 106 | 44% | 47% |
| 580 | us_open_fade | FRA40 | M30 | `{"k": 1.2, "tp": "r", "sl_mult": 1.0}` | 0.50% | -9 | -234 | -424 | -49 | 57 | 48% | 53% |
| 581 | us_open_fade | ESP35 | M30 | `{"k": 0.8, "tp": "r", "sl_mult": 1.0}` | 0.50% | -9 | -235 | -424 | -49 | 100 | 44% | 58% |
| 582 | us_open_fade | DE40 | H1 | `{"k": 1.2, "bar_hm": 16.0, "tp": "r"}` | 0.50% | -9 | -226 | -521 | -50 | 61 | 46% | 48% |
| 583 | fh_retest | DE40 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": null}` | 0.50% | -9 | -226 | -484 | -50 | 226 | 29% | 49% |
| 584 | pdhl | ESP35 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 1.0}` | 0.50% | -10 | -238 | -564 | -50 | 43 | 24% | 35% |
| 585 | time_window | FRA40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "trend": "with"}` | 0.75% | -10 | -239 | -466 | -75 | 244 | 36% | 52% |
| 586 | late_momentum | DE40 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "follow"}` | 0.50% | -10 | -230 | -491 | -50 | 103 | 42% | 48% |
| 587 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "sides": "long"}` | 0.50% | -10 | -240 | -338 | -49 | 31 | 24% | 39% |
| 588 | close_fade | ESP35 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 0.75% | -10 | -245 | -245 | -40 | 20 | 0% | 20% |
| 589 | fh_retest | DE40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "sl": "mid"}` | 0.25% | -10 | -236 | -437 | -25 | 224 | 38% | 41% |
| 590 | close_fade | FRA40 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 1.00% | -10 | -246 | -433 | -90 | 182 | 28% | 44% |
| 591 | overnight | DE40 | M30 | `{"side": "short", "cond": null, "sl_datr": 1.0}` | 0.50% | -10 | -241 | -351 | -83 | 281 | 50% | 46% |
| 592 | late_momentum | ESP35 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "follow"}` | 1.00% | -10 | -253 | -381 | -99 | 71 | 32% | 42% |
| 593 | prev_week | FRA40 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | 0.25% | -10 | -253 | -543 | -55 | 31 | 20% | 16% |
| 594 | us_open_fade | DE40 | M30 | `{"k": 1.2, "tp": "r", "sl_mult": 1.0}` | 0.50% | -10 | -243 | -472 | -50 | 56 | 38% | 48% |
| 595 | fh_retest | FRA40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "sl": "mid"}` | 0.25% | -10 | -254 | -387 | -25 | 71 | 40% | 35% |
| 596 | us_open_fade | DE40 | M30 | `{"k": 0.8, "tp": "r", "sl_mult": 1.0}` | 0.25% | -10 | -244 | -338 | -25 | 110 | 33% | 47% |
| 597 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "te": 14.0}` | 0.50% | -10 | -256 | -397 | -49 | 36 | 28% | 36% |
| 598 | us_open_fade | DE40 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 1.0}` | 0.25% | -10 | -246 | -408 | -25 | 79 | 29% | 44% |
| 599 | or_fail | DE40 | M30 | `{"re": 11.0, "tp": "mid", "trend": "with"}` | 0.75% | -10 | -246 | -487 | -74 | 36 | 38% | 64% |
| 600 | late_momentum | FRA40 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "follow"}` | 1.00% | -10 | -258 | -572 | -98 | 49 | 32% | 51% |
| 601 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "with"}` | 0.25% | -10 | -248 | -316 | -44 | 53 | 33% | 43% |
| 602 | lunch_break | ESP35 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": "with"}` | 0.50% | -10 | -259 | -375 | -49 | 49 | 20% | 39% |
| 603 | big_day | DE40 | D1 | `{"k": 1.5, "mode": "fade"}` | 1.50% | -10 | -250 | -424 | -157 | 15 | 12% | 40% |
| 604 | time_window | ESP35 | M30 | `{"entry_hm": 10.0, "exit_hour": 18, "side": "long"}` | 0.75% | -10 | -262 | -551 | -239 | 29 | 8% | 45% |
| 605 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 2.0}` | 0.25% | -10 | -262 | -302 | -25 | 91 | 32% | 37% |
| 606 | pdhl | DE40 | M30 | `{"mode": "reject", "ts": 16.0, "te": 18.0, "tp": "mid"}` | 0.50% | -11 | -252 | -550 | -50 | 131 | 29% | 43% |
| 607 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.25% | -11 | -264 | -523 | -25 | 87 | 44% | 34% |
| 608 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "sides": "short"}` | 0.50% | -11 | -266 | -385 | -49 | 12 | 8% | 17% |
| 609 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "r", "trend": null}` | 0.25% | -11 | -266 | -307 | -25 | 54 | 32% | 31% |
| 610 | prev_week | FRA40 | H1 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": "with"}` | 0.50% | -11 | -271 | -545 | -107 | 31 | 28% | 32% |
| 611 | lunch_break | ESP35 | M30 | `{"sl": "mid", "tp_r": null, "trend": "with"}` | 0.75% | -11 | -273 | -558 | -74 | 107 | 32% | 44% |
| 612 | gap | ESP35 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 1.00% | -11 | -273 | -306 | -98 | 16 | 12% | 38% |
| 613 | fh_retest | FRA40 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": null}` | 0.50% | -11 | -276 | -517 | -50 | 87 | 40% | 45% |
| 614 | close_fade | FRA40 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 0.75% | -11 | -280 | -373 | -73 | 153 | 32% | 44% |
| 615 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.75% | -11 | -281 | -507 | -74 | 29 | 28% | 45% |
| 616 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.25% | -11 | -286 | -459 | -25 | 87 | 36% | 23% |
| 617 | d1_meanrev | FRA40 | D1 | `{"n_down": 2, "ma": 200, "exit": "hold", "max_hold": 3}` | 2.00% | -11 | -286 | -451 | -191 | 6 | 8% | 33% |
| 618 | compression_break | FRA40 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": null}` | 1.00% | -11 | -287 | -575 | -100 | 26 | 12% | 35% |
| 619 | calendar | ESP35 | M30 | `{"kind": "weekday", "wd": 4, "side": "short"}` | 1.50% | -11 | -287 | -550 | -151 | 24 | 16% | 46% |
| 620 | close_fade | DE40 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 1.00% | -12 | -277 | -490 | -94 | 167 | 42% | 45% |
| 621 | late_momentum | DE40 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "fade"}` | 1.00% | -12 | -278 | -536 | -99 | 44 | 42% | 45% |
| 622 | pdhl | ESP35 | H1 | `{"mode": "reject", "sl_atr": 1.0}` | 0.50% | -12 | -291 | -302 | -48 | 16 | 8% | 25% |
| 623 | lunch_break | ESP35 | M30 | `{"sl": "mid", "tp_r": null, "trend": null}` | 0.50% | -12 | -292 | -576 | -50 | 77 | 20% | 35% |
| 624 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "sides": "short"}` | 0.50% | -12 | -292 | -481 | -48 | 30 | 24% | 33% |
| 625 | us_open_fade | ESP35 | M30 | `{"k": 1.2, "tp": "r", "sl_mult": 1.0}` | 0.50% | -12 | -293 | -377 | -49 | 40 | 32% | 50% |
| 626 | close_fade | ESP35 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 1.25% | -12 | -298 | -383 | -115 | 112 | 24% | 46% |
| 627 | us_open_fade | ESP35 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "r"}` | 0.50% | -12 | -300 | -398 | -49 | 80 | 32% | 51% |
| 628 | orb | DE40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": null}` | 0.25% | -12 | -288 | -475 | -89 | 318 | 50% | 43% |
| 629 | round_fade | ESP35 | M30 | `{"step": 100.0, "trend": "with"}` | 0.50% | -12 | -301 | -554 | -50 | 70 | 36% | 43% |
| 630 | fh_retest | DE40 | M30 | `{"fh_end": 11.5, "mm": 2.5, "trend": "with"}` | 0.75% | -12 | -290 | -479 | -74 | 94 | 38% | 44% |
| 631 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -12 | -290 | -571 | -132 | 204 | 42% | 50% |
| 632 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "te": 13.0}` | 0.25% | -12 | -303 | -356 | -25 | 69 | 28% | 33% |
| 633 | lunch_break | FRA40 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": "with"}` | 0.75% | -12 | -303 | -488 | -72 | 168 | 36% | 48% |
| 634 | us_open_fade | FRA40 | M30 | `{"k": 0.8, "tp": "r", "sl_mult": 1.0}` | 0.25% | -12 | -304 | -434 | -25 | 146 | 44% | 50% |
| 635 | late_momentum | DE40 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "fade"}` | 1.00% | -12 | -292 | -510 | -99 | 103 | 29% | 46% |
| 636 | close_fade | FRA40 | M30 | `{"k": 0.3, "mode": "fade", "sides": "long"}` | 1.00% | -12 | -304 | -378 | -90 | 114 | 32% | 42% |
| 637 | lunch_break | ESP35 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": null}` | 0.50% | -12 | -306 | -426 | -50 | 77 | 28% | 38% |
| 638 | pdhl | ESP35 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 1.0}` | 0.50% | -12 | -307 | -438 | -50 | 41 | 28% | 32% |
| 639 | us_open_fade | ESP35 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "retrace"}` | 0.50% | -12 | -308 | -533 | -49 | 81 | 40% | 36% |
| 640 | orb | ESP35 | M30 | `{"re": 10.5, "te": 16.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.75% | -12 | -308 | -546 | -75 | 34 | 28% | 44% |
| 641 | pdhl | DE40 | M30 | `{"mode": "break", "trend": "with"}` | 0.50% | -12 | -297 | -571 | -50 | 118 | 38% | 43% |
| 642 | pdhl | FRA40 | H1 | `{"mode": "break", "sl_atr": 1.0}` | 0.25% | -13 | -313 | -512 | -25 | 63 | 20% | 35% |
| 643 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "long"}` | 0.50% | -13 | -303 | -462 | -132 | 72 | 42% | 53% |
| 644 | late_momentum | DE40 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "follow"}` | 0.75% | -13 | -306 | -461 | -72 | 83 | 29% | 45% |
| 645 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | -13 | -306 | -431 | -88 | 92 | 33% | 39% |
| 646 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -13 | -306 | -571 | -132 | 190 | 42% | 50% |
| 647 | gap | ESP35 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.5}` | 1.00% | -13 | -319 | -456 | -247 | 19 | 8% | 47% |
| 648 | fh_retest | ESP35 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": null}` | 1.00% | -13 | -320 | -592 | -99 | 69 | 24% | 52% |
| 649 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "sides": "long"}` | 0.25% | -13 | -327 | -423 | -25 | 42 | 24% | 26% |
| 650 | compression_break | DE40 | M30 | `{"kind": "nr4", "sl": "far"}` | 1.50% | -13 | -314 | -499 | -148 | 78 | 42% | 47% |
| 651 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "far", "trend": null}` | 0.50% | -13 | -327 | -420 | -49 | 19 | 12% | 26% |
| 652 | lunch_break | FRA40 | M30 | `{"sl": "mid", "tp_r": 1.5, "trend": "with"}` | 0.50% | -13 | -328 | -445 | -50 | 170 | 40% | 47% |
| 653 | close_fade | FRA40 | M30 | `{"k": 0.3, "mode": "fade", "from_hm": 16.5, "entry_hm": 17.5}` | 1.50% | -13 | -329 | -474 | -135 | 78 | 32% | 40% |
| 654 | pdhl | ESP35 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 1.0}` | 0.50% | -13 | -331 | -499 | -50 | 41 | 24% | 34% |
| 655 | close_fade | DE40 | M30 | `{"k": 0.4, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 0.50% | -13 | -318 | -397 | -47 | 151 | 38% | 42% |
| 656 | pdhl | FRA40 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 1.0}` | 0.25% | -13 | -335 | -508 | -25 | 118 | 48% | 39% |
| 657 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 2.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | -13 | -322 | -557 | -88 | 193 | 38% | 44% |
| 658 | or_fail | FRA40 | M30 | `{"re": 10.5, "tp": "far", "te": 14.0}` | 0.25% | -13 | -336 | -389 | -25 | 76 | 24% | 33% |
| 659 | kagels_915 | DE40 | M15 | `{"tp_pts": 20, "sl": "far"}` | 0.25% | -13 | -323 | -583 | -177 | 407 | 50% | 77% |
| 660 | compression_break | FRA40 | M30 | `{"kind": "nr7", "sl": "far"}` | 1.25% | -13 | -337 | -426 | -120 | 45 | 36% | 44% |
| 661 | overnight | FRA40 | M30 | `{"side": "long", "cond": "up_day", "sl_datr": 1.5}` | 1.50% | -13 | -337 | -359 | -108 | 16 | 0% | 25% |
| 662 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "trend": "against"}` | 1.00% | -14 | -339 | -491 | -100 | 72 | 44% | 47% |
| 663 | fh_retest | FRA40 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": "with"}` | 0.50% | -14 | -340 | -556 | -50 | 64 | 36% | 45% |
| 664 | or_fail | ESP35 | M30 | `{"re": 10.5, "tp": "r", "trend": null}` | 0.50% | -14 | -341 | -431 | -49 | 19 | 8% | 26% |
| 665 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | -14 | -327 | -431 | -88 | 88 | 29% | 39% |
| 666 | orb | DE40 | M30 | `{"re": 10.5, "te": 16.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -14 | -329 | -516 | -89 | 179 | 33% | 42% |
| 667 | late_momentum | FRA40 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "fade"}` | 0.75% | -14 | -345 | -467 | -73 | 147 | 44% | 48% |
| 668 | round_fade | DE40 | M30 | `{"step": 100.0, "touch_atr": 0.25, "tp": "r"}` | 0.25% | -14 | -332 | -539 | -110 | 421 | 33% | 49% |
| 669 | compression_break | FRA40 | M30 | `{"kind": "nr4", "sl": "far"}` | 1.00% | -14 | -348 | -557 | -81 | 46 | 32% | 39% |
| 670 | overnight | FRA40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "skip_wd": [], "entry_hm": 19.0}` | 1.00% | -14 | -348 | -548 | -103 | 51 | 16% | 37% |
| 671 | round_fade | DE40 | M30 | `{"step": 100.0, "trend": "with"}` | 0.25% | -14 | -336 | -551 | -25 | 142 | 33% | 55% |
| 672 | gap | DE40 | H1 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 0.50% | -14 | -337 | -503 | -133 | 145 | 46% | 50% |
| 673 | compression_break | DE40 | M30 | `{"kind": "inside", "sl": "mid"}` | 0.75% | -14 | -341 | -492 | -70 | 34 | 29% | 38% |
| 674 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.2, "gmax": 1.0, "sl_mult": 1.5, "tp": "r", "tp_r": 1.5}` | 0.50% | -14 | -343 | -557 | -88 | 189 | 38% | 43% |
| 675 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "trend": "with"}` | 1.00% | -14 | -358 | -553 | -98 | 34 | 24% | 41% |
| 676 | gap | ESP35 | H1 | `{"mode": "cont", "gmin": 0.3, "gmax": 1.5, "sl_mult": 1.0}` | 0.75% | -15 | -363 | -487 | -247 | 26 | 12% | 42% |
| 677 | lunch_break | FRA40 | M30 | `{"sl": "far", "tp_r": null, "trend": "with"}` | 0.75% | -15 | -365 | -496 | -72 | 168 | 36% | 48% |
| 678 | orb | DE40 | M30 | `{"re": 10.5, "te": 14.0, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -15 | -353 | -510 | -89 | 171 | 33% | 42% |
| 679 | compression_break | FRA40 | M30 | `{"kind": "nr7", "sl": "mid", "trend": "with", "tp_r": 2.0}` | 1.00% | -15 | -368 | -575 | -100 | 26 | 12% | 35% |
| 680 | us_open_fade | DE40 | M30 | `{"k": 1.0, "sides": "long"}` | 0.50% | -15 | -356 | -479 | -50 | 38 | 25% | 26% |
| 681 | us_open_fade | FRA40 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 1.0}` | 0.25% | -15 | -373 | -426 | -25 | 91 | 36% | 45% |
| 682 | late_momentum | ESP35 | H1 | `{"bar_hm": 19.0, "k": 0.8, "mode": "fade"}` | 1.50% | -15 | -378 | -426 | -112 | 20 | 20% | 30% |
| 683 | fh_retest | FRA40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": "with"}` | 0.50% | -15 | -379 | -503 | -50 | 64 | 36% | 47% |
| 684 | lunch_break | FRA40 | M30 | `{"sl": "far", "tp_r": null, "trend": null}` | 0.50% | -15 | -382 | -440 | -50 | 203 | 44% | 44% |
| 685 | close_fade | FRA40 | M30 | `{"k": 0.4, "mode": "follow", "entry_hm": 17.0, "hold": 2}` | 0.75% | -15 | -384 | -447 | -73 | 148 | 36% | 45% |
| 686 | close_fade | DE40 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.0, "hold": 2}` | 0.50% | -16 | -376 | -462 | -47 | 269 | 38% | 44% |
| 687 | orb | DE40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with"}` | 0.25% | -16 | -377 | -528 | -89 | 162 | 33% | 41% |
| 688 | overnight | ESP35 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.0, "trend": "with"}` | 1.50% | -16 | -393 | -582 | -293 | 24 | 4% | 50% |
| 689 | d1_meanrev | DE40 | D1 | `{"n_down": 2, "ma": 200, "side": "long"}` | 1.50% | -16 | -378 | -587 | -116 | 45 | 42% | 62% |
| 690 | round | DE40 | M30 | `{"step": 100.0, "sl_frac": 0.5, "tp_frac": 0.5, "min_body": 0.3}` | 0.75% | -16 | -381 | -538 | -75 | 279 | 50% | 76% |
| 691 | late_momentum | FRA40 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "follow"}` | 0.50% | -16 | -400 | -412 | -48 | 98 | 28% | 42% |
| 692 | fh_mult | ESP35 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": null}` | 0.25% | -16 | -401 | -528 | -203 | 3 | 0% | 0% |
| 693 | pdhl | DE40 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 1.0}` | 0.25% | -16 | -386 | -549 | -25 | 216 | 33% | 30% |
| 694 | overnight | FRA40 | M30 | `{"side": "long", "cond": null, "sl_datr": 1.5}` | 1.50% | -16 | -402 | -548 | -124 | 42 | 12% | 36% |
| 695 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.5, "tp": "fill"}` | 0.50% | -16 | -387 | -452 | -88 | 92 | 33% | 47% |
| 696 | fh_retest | DE40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": null}` | 0.25% | -16 | -388 | -402 | -25 | 201 | 29% | 49% |
| 697 | time_window | FRA40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long", "sl_datr": 0.3}` | 0.50% | -16 | -405 | -457 | -52 | 433 | 48% | 48% |
| 698 | compression_break | DE40 | M30 | `{"kind": "nr4", "sl": "mid"}` | 0.75% | -16 | -389 | -564 | -75 | 78 | 33% | 46% |
| 699 | late_momentum | FRA40 | H1 | `{"bar_hm": 20.0, "k": 0.8, "mode": "follow"}` | 1.00% | -16 | -406 | -557 | -97 | 43 | 32% | 40% |
| 700 | overnight | DE40 | M30 | `{"side": "short", "cond": "up_day", "sl_datr": 1.0}` | 0.75% | -16 | -391 | -504 | -111 | 166 | 29% | 45% |
| 701 | fh_retest | DE40 | M30 | `{"fh_end": 11.0, "mm": 2.5, "trend": "with"}` | 0.25% | -16 | -395 | -460 | -25 | 106 | 25% | 42% |
| 702 | us_open_fade | DE40 | M30 | `{"k": 1.0, "mode": "cont", "tp_r": 2.0}` | 0.25% | -16 | -395 | -520 | -25 | 79 | 29% | 29% |
| 703 | orb | DE40 | M30 | `{"re": 10.5, "sl": "far", "tp_r": 2.0, "trend": "with", "exit_hour": 22}` | 0.25% | -17 | -397 | -536 | -89 | 158 | 38% | 38% |
| 704 | lunch_break | FRA40 | M30 | `{"sl": "far", "tp_r": 1.5, "trend": null}` | 0.50% | -17 | -413 | -451 | -50 | 203 | 44% | 44% |
| 705 | close_to_open | DE40 | M30 | `{"side": "short", "cond": "up_cash"}` | 1.00% | -17 | -397 | -587 | -166 | 175 | 38% | 46% |
| 706 | d1_meanrev | DE40 | D1 | `{"n_down": 2, "ma": 100, "side": "long"}` | 1.50% | -17 | -397 | -480 | -116 | 37 | 42% | 65% |
| 707 | us_open_fade | FRA40 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "r"}` | 0.25% | -17 | -414 | -533 | -25 | 165 | 24% | 49% |
| 708 | compression_break | FRA40 | M30 | `{"kind": "nr7", "sl": "mid"}` | 0.75% | -17 | -415 | -562 | -74 | 44 | 24% | 36% |
| 709 | us_open_fade | ESP35 | M30 | `{"k": 0.8, "tp": "retrace", "sl_mult": 1.0}` | 0.50% | -17 | -415 | -530 | -49 | 101 | 40% | 43% |
| 710 | us_open_fade | ESP35 | M30 | `{"k": 1.0, "trend": "against"}` | 0.50% | -17 | -416 | -519 | -48 | 31 | 20% | 29% |
| 711 | close_fade | DE40 | M30 | `{"k": 0.3, "mode": "fade", "sides": "long"}` | 1.50% | -17 | -406 | -543 | -149 | 102 | 50% | 43% |
| 712 | close_fade | FRA40 | M30 | `{"k": 0.2, "mode": "follow", "entry_hm": 17.5, "hold": 1}` | 0.75% | -17 | -424 | -542 | -73 | 256 | 28% | 44% |
| 713 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.5, "tp": "fill"}` | 0.50% | -17 | -409 | -464 | -88 | 88 | 29% | 47% |
| 714 | time_window | FRA40 | M30 | `{"entry_hm": 19.0, "exit_hour": 22, "side": "long"}` | 0.75% | -17 | -426 | -478 | -75 | 387 | 48% | 48% |
| 715 | compression_break | DE40 | M30 | `{"kind": "inside", "sl": "far"}` | 1.25% | -17 | -410 | -531 | -123 | 34 | 29% | 38% |
| 716 | calendar | ESP35 | M30 | `{"kind": "weekday", "wd": 3, "side": "short"}` | 1.25% | -17 | -431 | -431 | -123 | 7 | 0% | 14% |
| 717 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": null}` | 0.50% | -18 | -441 | -584 | -50 | 69 | 28% | 36% |
| 718 | gap | FRA40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "sides": "long"}` | 0.75% | -18 | -441 | -533 | -73 | 63 | 28% | 44% |
| 719 | close_fade | DE40 | M30 | `{"k": 0.2, "mode": "fade", "entry_hm": 17.5, "hold": 1}` | 0.75% | -18 | -430 | -538 | -64 | 271 | 33% | 44% |
| 720 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.3, "gmax": 1.5, "entry_hm": 10.5}` | 0.50% | -18 | -432 | -515 | -133 | 145 | 42% | 48% |
| 721 | pullback | ESP35 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | 0.25% | -18 | -462 | -464 | -85 | 64 | 24% | 34% |
| 722 | us_open_fade | ESP35 | M30 | `{"k": 1.2, "tp": "retrace", "sl_mult": 1.0}` | 0.50% | -19 | -476 | -594 | -49 | 41 | 24% | 32% |
| 723 | us_open_fade | DE40 | M30 | `{"k": 1.0, "trend": "against"}` | 0.50% | -20 | -470 | -590 | -50 | 35 | 29% | 26% |
| 724 | calendar | DE40 | M30 | `{"kind": "weekday", "wd": 3, "side": "short"}` | 1.25% | -20 | -473 | -530 | -125 | 82 | 42% | 41% |
| 725 | pdhl | DE40 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 2.0}` | 0.25% | -20 | -476 | -536 | -25 | 202 | 29% | 40% |
| 726 | late_momentum | ESP35 | H1 | `{"bar_hm": 19.0, "k": 0.5, "mode": "fade"}` | 0.75% | -20 | -497 | -542 | -58 | 50 | 20% | 24% |
| 727 | pdhl | ESP35 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 2.0}` | 0.75% | -20 | -506 | -554 | -75 | 63 | 28% | 41% |
| 728 | fh_retest | DE40 | M30 | `{"fh_end": 11.0, "mm": 1.5, "trend": "with"}` | 0.25% | -20 | -486 | -522 | -25 | 106 | 17% | 43% |
| 729 | fh_retest | DE40 | M30 | `{"fh_end": 11.5, "mm": 1.5, "trend": "with"}` | 0.75% | -20 | -488 | -580 | -74 | 94 | 29% | 44% |
| 730 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": "with"}` | 0.50% | -20 | -511 | -529 | -48 | 35 | 16% | 29% |
| 731 | close_fade | ESP35 | M30 | `{"k": 0.3, "mode": "fade", "from_hm": 16.5, "entry_hm": 17.5}` | 1.50% | -21 | -516 | -586 | -105 | 63 | 24% | 41% |
| 732 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 2.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -22 | -517 | -595 | -132 | 114 | 25% | 46% |
| 733 | orb | ESP35 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": "with"}` | 0.50% | -22 | -543 | -546 | -48 | 35 | 16% | 26% |
| 734 | pdhl | ESP35 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 1.0}` | 0.50% | -22 | -547 | -599 | -50 | 43 | 20% | 35% |
| 735 | gap | ESP35 | M30 | `{"mode": "cont", "gmin": 0.5, "gmax": 2.0, "tp_r": 1.5}` | 1.25% | -22 | -555 | -581 | -124 | 12 | 4% | 17% |
| 736 | gap | DE40 | M30 | `{"mode": "fade", "gmin": 0.4, "gmax": 1.0, "sl_mult": 1.0, "tp": "fill"}` | 0.50% | -22 | -533 | -597 | -132 | 100 | 21% | 46% |
| 737 | close_fade | ESP35 | M30 | `{"k": 0.3, "mode": "fade", "sides": "short"}` | 1.00% | -24 | -592 | -592 | -58 | 42 | 4% | 26% |
| 738 | us_open_fade | DE40 | H1 | `{"k": 0.8, "bar_hm": 16.0, "tp": "r"}` | none | -23 | -562 | -697 | -25 | 144 | 38% | 42% |
| 739 | pdhl | DE40 | H1 | `{"mode": "break", "sl_atr": 1.0}` | none | -34 | -825 | -865 | -25 | 201 | 25% | 33% |
| 740 | pullback | DE40 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | none | -124 | -2977 | -3125 | -577 | 425 | 29% | 31% |
| 741 | pullback | DE40 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -246 | -5908 | -6062 | -1042 | 802 | 25% | 30% |
| 742 | pullback | DE40 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | none | -88 | -2101 | -2826 | -577 | 385 | 29% | 14% |
| 743 | pullback | DE40 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -180 | -4319 | -5467 | -1042 | 737 | 33% | 14% |
| 744 | pullback | DE40 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | none | -144 | -3460 | -3606 | -577 | 671 | 21% | 32% |
| 745 | pullback | DE40 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -273 | -6564 | -6762 | -1042 | 1276 | 17% | 32% |
| 746 | pullback | DE40 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | none | -95 | -2284 | -2488 | -577 | 528 | 33% | 15% |
| 747 | pullback | DE40 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -233 | -5592 | -6483 | -1042 | 999 | 29% | 15% |
| 748 | pullback | DE40 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | none | -44 | -1051 | -1051 | -432 | 125 | 25% | 29% |
| 749 | pullback | DE40 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -77 | -1846 | -1972 | -671 | 218 | 33% | 31% |
| 750 | pullback | DE40 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | none | -59 | -1416 | -1543 | -480 | 107 | 25% | 14% |
| 751 | pullback | DE40 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -105 | -2525 | -2826 | -671 | 193 | 29% | 16% |
| 752 | pullback | DE40 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | none | -40 | -954 | -1006 | -432 | 196 | 46% | 34% |
| 753 | pullback | DE40 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -84 | -2014 | -2169 | -671 | 358 | 46% | 34% |
| 754 | pullback | DE40 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | none | -19 | -447 | -1076 | -480 | 145 | 50% | 18% |
| 755 | pullback | DE40 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -61 | -1476 | -1901 | -671 | 269 | 50% | 21% |
| 756 | kagels_915 | DE40 | M15 | `{"tp_r": 1.5, "sl": "far", "te": 14.0}` | none | 4 | 101 | -670 | -177 | 407 | 50% | 44% |
| 757 | kagels_915 | DE40 | M15 | `{"tp_r": 1.5, "sl": "mid", "te": 14.0}` | none | 14 | 325 | -946 | -310 | 402 | 58% | 45% |
| 758 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "far", "te": 14.0}` | none | 37 | 896 | -689 | -177 | 407 | 67% | 37% |
| 759 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "mid", "te": 14.0}` | none | 57 | 1359 | -1037 | -310 | 402 | 71% | 29% |
| 760 | kagels_915 | DE40 | M15 | `{"tp_pts": 40, "sl": "far"}` | none | -4 | -97 | -743 | -177 | 407 | 46% | 65% |
| 761 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "far", "sides": "long"}` | none | 2 | 47 | -621 | -177 | 233 | 54% | 33% |
| 762 | kagels_915 | DE40 | M15 | `{"tp_r": null, "sl": "far", "te": 12.0}` | none | 35 | 833 | -701 | -177 | 393 | 71% | 36% |
| 763 | pdhl | DE40 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 1.0}` | none | -25 | -612 | -920 | -89 | 239 | 25% | 38% |
| 764 | pdhl | DE40 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 2.0}` | none | -19 | -447 | -619 | -89 | 231 | 33% | 43% |
| 765 | pdhl | DE40 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 1.0}` | none | -33 | -801 | -1035 | -89 | 241 | 38% | 34% |
| 766 | pdhl | DE40 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 2.0}` | none | -21 | -514 | -633 | -89 | 233 | 33% | 39% |
| 767 | pdhl | DE40 | M30 | `{"mode": "break", "tp_r": 1.5, "sl_atr": 1.0}` | none | -30 | -720 | -798 | -25 | 216 | 21% | 37% |
| 768 | pdhl | DE40 | M30 | `{"mode": "reject", "trend": "with"}` | none | -36 | -858 | -941 | -89 | 102 | 12% | 30% |
| 769 | round_fade | DE40 | M30 | `{"step": 100.0, "touch_atr": 0.1, "tp": "step"}` | none | -15 | -351 | -640 | -25 | 311 | 42% | 61% |
| 770 | round_fade | DE40 | M30 | `{"step": 100.0, "touch_atr": 0.1, "tp": "r"}` | none | -21 | -498 | -739 | -110 | 416 | 38% | 48% |
| 771 | round_fade | DE40 | M30 | `{"step": 100.0, "touch_atr": 0.25, "tp": "step"}` | none | -16 | -396 | -690 | -25 | 318 | 29% | 62% |
| 772 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "trend": null}` | none | 91 | 2189 | -568 | -524 | 78 | 42% | 37% |
| 773 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 6.0, "trend": null}` | none | 81 | 1946 | -568 | -524 | 78 | 46% | 27% |
| 774 | prev_week | DE40 | M30 | `{"sl_atr": 2.5, "trail_atr": 3.0, "trend": null}` | none | 52 | 1251 | -376 | -341 | 74 | 46% | 45% |
| 775 | prev_week | DE40 | M30 | `{"sl_atr": 2.5, "trail_atr": 6.0, "trend": null}` | none | 46 | 1115 | -378 | -341 | 74 | 50% | 34% |
| 776 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "sides": "short"}` | none | 7 | 168 | -551 | -524 | 32 | 25% | 28% |
| 777 | prev_week | DE40 | M30 | `{"sl_atr": 1.5, "trail_atr": 3.0, "friday_flat": false}` | none | 40 | 963 | -624 | -623 | 77 | 46% | 36% |
| 778 | kagels_915 | DE40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": null, "sl": "mid", "te": 14.0}` | none | 22 | 520 | -603 | -177 | 363 | 50% | 36% |
| 779 | late_momentum | ESP35 | H1 | `{"bar_hm": 20.0, "k": 0.5, "mode": "fade"}` | none | -13 | -333 | -333 | -333 | 1 | 0% | 0% |
| 780 | pullback | ESP35 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -33 | -815 | -815 | -85 | 94 | 16% | 31% |
| 781 | pullback | ESP35 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | none | -38 | -944 | -1034 | -342 | 62 | 4% | 10% |
| 782 | pullback | ESP35 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -35 | -865 | -1311 | -342 | 92 | 20% | 13% |
| 783 | pullback | ESP35 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | none | -46 | -1153 | -1153 | -292 | 99 | 16% | 32% |
| 784 | pullback | ESP35 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -66 | -1649 | -1649 | -292 | 152 | 12% | 31% |
| 785 | pullback | ESP35 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | none | -73 | -1813 | -1844 | -342 | 93 | 4% | 8% |
| 786 | pullback | ESP35 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -80 | -1992 | -2249 | -342 | 145 | 16% | 11% |
| 787 | pullback | ESP35 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -14 | -359 | -402 | -333 | 8 | 8% | 38% |
| 788 | pullback | ESP35 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -4 | -94 | -662 | -333 | 8 | 8% | 12% |
| 789 | pullback | ESP35 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -14 | -345 | -402 | -333 | 9 | 8% | 44% |
| 790 | pullback | ESP35 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -7 | -179 | -759 | -333 | 9 | 8% | 11% |
| 791 | pullback | FRA40 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | none | -127 | -3180 | -3212 | -118 | 499 | 8% | 31% |
| 792 | pullback | FRA40 | H1 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -206 | -5160 | -5204 | -152 | 940 | 4% | 33% |
| 793 | pullback | FRA40 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | none | -82 | -2052 | -2127 | -271 | 454 | 32% | 13% |
| 794 | pullback | FRA40 | H1 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -196 | -4908 | -4920 | -339 | 871 | 16% | 13% |
| 795 | pullback | FRA40 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | none | -199 | -4966 | -5020 | -142 | 774 | 0% | 31% |
| 796 | pullback | FRA40 | H1 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -335 | -8387 | -8487 | -152 | 1490 | 0% | 33% |
| 797 | pullback | FRA40 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | none | -102 | -2543 | -2658 | -271 | 622 | 28% | 14% |
| 798 | pullback | FRA40 | H1 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -247 | -6187 | -6302 | -339 | 1217 | 24% | 14% |
| 799 | pullback | FRA40 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "long", "rsi_sell": 80}` | none | -28 | -688 | -738 | -144 | 80 | 24% | 31% |
| 800 | pullback | FRA40 | H4 | `{"rsi_buy": 20, "tp_r": 2.0, "sides": "both", "rsi_sell": 80}` | none | -42 | -1045 | -1187 | -144 | 142 | 32% | 30% |
| 801 | pullback | FRA40 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "long", "rsi_sell": 80, "trail_atr": 3.0}` | none | -43 | -1065 | -1175 | -144 | 72 | 20% | 8% |
| 802 | pullback | FRA40 | H4 | `{"rsi_buy": 20, "tp_r": null, "sides": "both", "rsi_sell": 80, "trail_atr": 3.0}` | none | -58 | -1449 | -1772 | -144 | 129 | 28% | 9% |
| 803 | pullback | FRA40 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "long", "rsi_sell": 70}` | none | -31 | -767 | -807 | -144 | 120 | 24% | 32% |
| 804 | pullback | FRA40 | H4 | `{"rsi_buy": 30, "tp_r": 2.0, "sides": "both", "rsi_sell": 70}` | none | -58 | -1451 | -1506 | -144 | 224 | 20% | 30% |
| 805 | pullback | FRA40 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "long", "rsi_sell": 70, "trail_atr": 3.0}` | none | -39 | -972 | -1368 | -144 | 103 | 16% | 10% |
| 806 | pullback | FRA40 | H4 | `{"rsi_buy": 30, "tp_r": null, "sides": "both", "rsi_sell": 70, "trail_atr": 3.0}` | none | -73 | -1821 | -2091 | -144 | 191 | 28% | 10% |
| 807 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": 2.0, "trend": null}` | none | -18 | -443 | -779 | -25 | 153 | 40% | 35% |
| 808 | orb | FRA40 | M30 | `{"re": 10.5, "sl": "mid", "tp_r": null, "trend": null}` | none | -27 | -676 | -951 | -49 | 153 | 32% | 25% |
| 809 | pdhl | FRA40 | M30 | `{"mode": "reject", "tp": "mid", "sl_atr": 1.0}` | none | -11 | -263 | -612 | -32 | 115 | 36% | 35% |
| 810 | pdhl | FRA40 | M30 | `{"mode": "reject", "tp": "far", "sl_atr": 1.0}` | none | -12 | -298 | -731 | -26 | 115 | 28% | 30% |
| 811 | pdhl | FRA40 | M30 | `{"mode": "break", "tp_r": null, "sl_atr": 1.0}` | none | -14 | -342 | -667 | -25 | 118 | 28% | 29% |
| 812 | round_fade | FRA40 | M30 | `{"step": 50.0, "touch_atr": 0.1, "tp": "step"}` | none | -33 | -829 | -956 | -25 | 251 | 36% | 39% |
| 813 | round_fade | FRA40 | M30 | `{"step": 50.0, "touch_atr": 0.1, "tp": "r"}` | none | -32 | -805 | -883 | -25 | 251 | 28% | 47% |
| 814 | round_fade | FRA40 | M30 | `{"step": 50.0, "touch_atr": 0.25, "tp": "step"}` | none | -30 | -740 | -825 | -25 | 247 | 28% | 41% |
| 815 | round_fade | FRA40 | M30 | `{"step": 50.0, "touch_atr": 0.25, "tp": "r"}` | none | -30 | -751 | -816 | -25 | 247 | 20% | 47% |
| 816 | kagels_915 | FRA40 | M30 | `{"bar_hm": 10.0, "bar_len": 0.5, "tp_r": 1.5, "sl": "mid", "te": 14.0}` | none | -23 | -586 | -778 | -25 | 171 | 36% | 38% |

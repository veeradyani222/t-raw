# jpy_crosses (round 3): notes

Judge: `research/prop/harness.py` (`H.score`) with `PROP_OOS=1`, `split="oos"`: warmup kept, scoring
counts from 2024-10-20 to 2026-10-20 (last bar in the files). Fixed-dollar risk, FundedNext $10k rules
(worst day > -3%, max DD > -6% at `best_risk`). Costs: the harness's own JPY floors
(`H.SPREAD_FLOOR`: USDJPY 0.012, EURJPY 0.020, GBPJPY 0.030, AUDJPY 0.020, CHFJPY 0.025, NZDJPY 0.025,
CADJPY 0.025, or the bar's recorded spread if wider), $14/lot round-trip commission, 0.1 pip slippage
per fill, JPY P&L converted with USDJPY. Nothing was monkeypatched: all seven symbols were already
in the cost tables and `data/search/symbol_specs.json`.

Files: `strategies.py` (25 builders), `run.py` (batches, Pool(2), look-ahead check on every run),
`study.py` + `study_out.txt` (market study and data-quality check), `report.py` (tables),
`results.jsonl` (every scored run).

## Data quality

Files checked: 7 symbols x m30/h1/h4/d1 (28 files). H1/H4/D1 start 2015-01, M30 2018-10; all end
2026-10-20 00:00. Zero-volume bars: 0 in every file. Duplicated timestamps: none after `H.load`.
Flat/stale days (daily range < 5% of the rolling 60-day median): only market holidays:
2025-01-01 (USDJPY, EURJPY), 2024-12-25 (CADJPY, CHFJPY), 2023-12-25 (CHFJPY). Long gaps (> weekend
+ 2 bars) are the Christmas / New-Year closures every year plus the M30 files' 2 day 1:30 h weekend
gaps around US/EU DST switches (36-37 per M30 file, all weekends). Handling: every builder refuses to
open a trade on Dec 24-26, Dec 31 and Jan 1-2 (`_holiday_mask`), so the flat days and the thin
holiday sessions never produce entries; no bars were deleted (deleting would break the
`exit_hour` / `max_hold` clocks).

Contract note: `symbol_specs.json` gives NZDJPY `vol_min` = 0.10 lots (all other pairs 0.01). The
harness therefore skips any NZDJPY entry whose stop would lose more than the risk budget at 0.1 lot
(at 0.25% risk, $25, that is every stop wider than ~4 pips), so NZDJPY rows show few or zero trades
for tight-stop ideas and only wide-stop / higher-risk settings fill. That is the broker's rule, not a
bug, and it is kept as is.

## Market study (scoring window 2024-10-20.., H1 unless stated; full print in `study_out.txt`)

Server clock EET: Tokyo 00:00-09:00, Tokyo fix 02:55, London 09:00-16:00, NY 16:00-23:00.

- **Daily-scale mean reversion everywhere.** Variance ratio VR(5) on D1 returns: USDJPY 0.91,
  EURJPY 0.92, GBPJPY 0.90, AUDJPY 0.85, CADJPY 0.82, CHFJPY 0.93, NZDJPY 0.89 (all < 1), lag-1
  autocorrelation -0.01..-0.08. H1 ~random (VR 0.94-1.04), H4 random-to-slightly-mean-reverting
  except USDJPY (VR 1.06). So the window favours fading multi-day stretches, not following them.
- **Weekday drift** (sum of H1 returns): Monday strongly positive on all pairs (+410..+1866 bp),
  Thursday negative on 6/7 (-396..-1087 bp). Round 1 already monetised Monday; not re-used here.
- **Session drift**: Tokyo 00-09 positive on the carry crosses (AUDJPY +0.44, CADJPY +0.26,
  CHFJPY +0.49, NZDJPY +0.68 bp/bar), NY 16-23 positive on USDJPY/GBPJPY/CADJPY (+0.35..+0.43 bp/bar),
  London flat to negative. Tokyo direction tells nothing about the rest of the day (sign agreement
  0.46-0.54, corr -0.05..+0.05); London tells nothing about NY (corr -0.14..+0.06).
- **Hour effects**: hour 01 (01:00-02:00, Tokyo pre-open) +1.5..+6.2 bp on every pair, hour 23
  -1.5..-7.0 bp. The M15 check (`study_out` section + this file's rollover note) shows the 23:45-00:15
  drop and the 01:00 rebound coincide exactly with the recorded spread jumping from 20-40 to 110-160
  points (GBPJPY/CHFJPY) and back: it is the bid being pushed down by the rollover spread, not a
  tradable move. Over 23:00-01:15 the net bid move is -1 bp. **Any strategy whose exit or entry sits
  inside 00:00-01:00 is treated as an artefact** (see "rollover" rows below).
- **Monday gap**: mean |gap| 14-25 bp, same-day move against the gap +4..+16 bp (GBPJPY +16 of 19,
  AUDJPY +13 of 25): gaps half-fill on average. Tested as `gap_fade`.
- **Prior-day extremes**: prior-day high touched on ~50% of days, closed above on 21-28%; low
  touched 41-48%, closed below 19-24%; both extremes taken 9-13%; inside days 15-18%. So a touch
  closes beyond the level ~half the time: no free fade and no free break at the level itself.
- **Tokyo fix / gotobi** (days 5/10/15/20/25/30): pre-fix 00-03 drift on gotobi days is NOT more
  positive than other days (USDJPY -0.40 vs +0.28 bp/bar), post-fix 03-06 is more negative on gotobi
  days on every pair (-0.8..-1.5 vs -0.0..-0.3 bp/bar). Only the post-fix short had a chance.
- **Risk-on/off**: same-day correlation with US500 daily returns AUDJPY +0.51, NZDJPY +0.43,
  GBPJPY +0.25, CADJPY +0.22, USDJPY +0.10, CHFJPY -0.01; lag-1 (US500 yesterday -> pair today)
  -0.13..+0.03: no lead-lag to trade, so co-movement was used as a basket signal (`yen_basket`)
  instead of an equity lead.
- **Vol regime**: D1 ATR14 median 70-93 bp of price, p10 48-73, p90 93-126.

## Sources (practitioner rules looked up; what was tested)

- EBC "Gotobi strategy explained" and the MQL5 Gotobi/Tokyo-fix marker manual: fix 09:55 JST
  (= 02:55 server), gotobi dates 5/10/15/20/25/30 with the prior business day when on a weekend;
  claim: USDJPY bid up into the fix, weakens after. Tested as `tokyo_fix` (long 00:00->03:00) and
  `post_fix_short` (short 03:00->06:00), gotobi-only and all days.
  https://www.ebc.com/forex/gotobi-strategy , https://www.mql5.com/en/blogs/post/777569
- Generic London / Asian-range breakout write-ups (babypips London breakout thread, RoboForex
  GBPJPY range article, backtrex GBPUSD London-breakout backtest reporting a loss with a 20/40 pip
  bracket): rules = mark the Tokyo high/low, trade the London break, SL at the other side.
  Round 2 already showed the plain break loses on JPY crosses; here the *failed* break is tested
  (`tokyo_sweep`: London takes the Tokyo high and closes back inside -> fade) plus the prior-day
  version (`pdh_sweep`, `pdh_break`) and NR7/inside-day gated breaks (`nr_break`).
  https://forums.babypips.com/t/london-breakout/412449 ,
  https://backtrex.com/en/backtests/london-breakout-gbp-usd
- Nomura (via FXStreet 2018) and poundsterlinglive: USDJPY tends to rise during Tokyo hours on
  Japanese outflows, reversing NY moves. Tested indirectly through `yen_basket`, `carry_dip` and the
  day-open / big-day fades.
  https://www.fxstreet.com/news/jpy-caught-up-in-regime-change-nomura-201802220544
- Intervention behaviour (HSBC FX viewpoint, Continuum Economics, Benzinga "1 week after"):
  intervention knocks USDJPY 4-5 figures in hours and the move fades within days to weeks unless
  backed by policy. Tested as `shock_day` (range >= 2.0-2.2 x ATR, fade vs follow, 3-day hold).
  https://www.hsbc.com.hk/wealth/insights/fx-insights/fx-viewpoint/jpy-fx-intervention/ ,
  https://continuumeconomics.com/a/79e6ff69/bojs-intervention-and-its-impact
- Connors RSI(2) pullback and Bollinger-stretch fades (PineForge USDJPY RSI / Bollinger pages,
  generic rules RSI(2) < 10 above the 200 SMA, exit above the 5 SMA): `rsi2`, `band_fade`.
  https://getpineforge.com/strategies/usdjpy-rsi-mean-reversion
- Added after the first batches (b5): consecutive-close streak fade (`streak_fade`, a pure structure
  version of the D1 mean reversion seen in the study), close-vs-SMA z-score fade (`zfade`), the
  "London open fakeout" rule traders describe for GBPJPY (first London H1 bar runs >= 0.35 ATR and
  closes at its extreme -> fade back to its open; `london_fakeout`), the Tokyo-range break taken
  only with the D1 trend (prior close vs SMA20/50 of daily closes; `tokyo_break_trend`) and the NY
  continuation / fade of the day's move at 16:00 (`ny_follow`). Sweeps around the first-batch
  leaders (gap fade, RSI(2) counter-trend on D1, big-day fade at the London open) are batch b6.
- Bug found by the runner (not look-ahead): `shock_day` crashed on D1 frames (bars-per-day from the
  hour step is undefined when every bar is at 00:00); fixed to 1 bar/day before b2 was resumed.
- No credible JPY-specific video/podcast rule set was found; nothing was transcribed.

## Look-ahead check

`run.causal_check`: for every scored run, `build(df)` is compared with `build(df.iloc[:k])`
(attrs re-attached) for 5 random k in [40% of the frame, len-2]; every Entry at index < k must match
on side / sl / tp / max_hold / exit_hour / has-manage / meta. Result column `causal` in the tables.
Daily and weekly levels come from `shift(1)` of completed days/weeks, session levels are running
cummax/cummin, the yen basket uses the last completed day strictly before the bar's day.

## What came out (read before the tables)

- **Rollover family excluded.** `rollover_short` (short at the 22:00 close, cover at the close of the
  00:00 bar) scores +$79/month on GBPJPY with 508 trades, but the market study showed the 23:00-01:00
  bid dip is the rollover spread widening (20-40 -> 110-160 points) and the net bid move over
  23:00-01:15 is -1 bp. The harness charges spread only at entry, so covering a short at the
  depressed 01:00 bid is free in the backtest and costs ~1.4 pips live (~$2.6 of the $3.9 average
  trade at 0.28 lots). All 42 rollover / pre-open rows are kept in the table but none is a candidate.
- **The window rewards daily-scale mean reversion**, exactly what the study's variance ratios said:
  RSI(2) counter-trend on D1 (100 of 126 runs positive, every pair), consecutive-close streak fades,
  z-score fades, Monday gap fades and the trend-side Bollinger fade. Breakouts (Tokyo range, prior-day
  high, NR4/NR7, Donchian), pullbacks in H4 trends, round numbers, Tokyo-fix/gotobi, London fakeout and
  NY continuation all lose or barely break even on these pairs in 2024-10..2026-10.
- **Thin rows**: `band_fade_h4_trend` CHFJPY (17 trades), `zfade_d1_n20` CADJPY (12 trades),
  `shock_*` (7-12 trades). Reported as found; the owner asked for no statistical gates.

### Candidates returned (distinct ideas or markets, ranked by avg $/month at best_risk)

| # | builder | symbol | tf | params | best risk | avg/mo | net | maxDD | worst day | trades | green | exit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | build_rsi2 | USDJPY | D1 | counter=True, exit_n=10 | 2.00% | 98.3 | 2458 | -424 | -227 | 60 | 60% | manage (close crosses SMA10) or 10 bars; SL 2 ATR |
| 2 | build_rsi2 | GBPJPY | D1 | counter=True, exit_n=10 | 2.00% | 78.4 | 1960 | -596 | -203 | 59 | 72% | same |
| 3 | build_gap_fade | EURJPY | H1 | defaults (min_gap 0.15 ATR, tp=fill, 24 bars) | 2.00% | 70.5 | 1763 | -338 | -200 | 46 | 76% | TP = Friday close, SL = gap size beyond the open, 24 bars |
| 4 | build_band_fade | CHFJPY | H4 | trend_n=200 | 2.00% | 63.5 | 1588 | -523 | -273 | 17 | 40% | manage (mid band) / 24 bars; SL 1.2 ATR |
| 5 | build_streak_fade | GBPJPY | D1 | n=4, max_hold=4 | 1.50% | 62.1 | 1552 | -564 | -218 | 26 | 48% | time (4 bars); SL 1.2 ATR |
| 6 | build_streak_fade | CADJPY | D1 | min_move=1.5, max_hold=3 | 2.00% | 57.3 | 1432 | -433 | -198 | 30 | 44% | time (3 bars); SL 1.2 ATR |
| 7 | build_carry_dip | EURJPY | D1 | trend_n=200, dip_n=3 | 1.50% | 37.3 | 933 | -518 | -214 | 61 | 68% | TP prior 20-day high/low or 10 bars; SL 1.5 ATR |
| 8 | build_pwh_sweep | GBPJPY | H4 | tp=wc | 0.75% | 36.2 | 906 | -568 | -149 | 69 | 76% | TP last week's close, SL beyond sweep bar, 30 bars |

All eight pass the look-ahead check (as does every one of the 830 runs).

<!-- RESULTS START -->
## Results

Scored runs: **830** (25 builders / ideas, 7 symbols, timeframes D1, H1, H4, M30). Candidates (best_risk set and avg_month > 0): **269**. Look-ahead check failures: **0**.

### Ideas ranked by their best run (avg $/month at best_risk)

| idea | runs | mean avg/mo | best avg/mo | candidates |
|---|---|---|---|---|
| rsi2 | 126.0 | 20.5 | 98.3 | 100 |
| rollover | 42.0 | -16.4 | 78.9 | 10 |
| gap_fade | 98.0 | 1.0 | 70.5 | 36 |
| band_fade | 21.0 | -10.9 | 63.5 | 4 |
| streak_fade | 42.0 | 2.1 | 62.1 | 22 |
| zfade | 28.0 | 9.4 | 50.9 | 18 |
| carry_dip | 21.0 | 13.6 | 37.3 | 16 |
| bigday_fade | 63.0 | -5.0 | 36.8 | 18 |
| pwh_sweep | 21.0 | -4.0 | 36.2 | 6 |
| london_fade | 21.0 | -6.8 | 34.6 | 3 |
| nr_break | 28.0 | -1.0 | 34.3 | 10 |
| shock_day | 32.0 | -7.1 | 15.2 | 9 |
| donchian | 28.0 | -9.5 | 15.0 | 3 |
| week_open_fade | 14.0 | -9.2 | 11.4 | 3 |
| day_open_fade | 14.0 | -7.5 | 10.2 | 2 |
| yen_basket | 21.0 | -9.0 | 8.8 | 3 |
| tokyo_break_trend | 28.0 | -12.8 | 8.3 | 3 |
| ny_follow | 21.0 | -12.9 | 2.4 | 1 |
| london_fakeout | 21.0 | -11.6 | 1.1 | 2 |
| pdh_break | 14.0 | -13.6 | 0.0 | 0 |
| tokyo_fix | 35.0 | -17.5 | -1.5 | 0 |
| ema_pullback | 21.0 | -32.0 | -2.1 | 0 |
| pdh_sweep | 28.0 | -32.3 | -7.4 | 0 |
| round_number | 21.0 | -91.7 | -14.0 | 0 |
| tokyo_sweep | 21.0 | -50.2 | -20.4 | 0 |

### Top 40 candidate runs

| # | batch | name | symbol | tf | params | best risk | net | avg/mo | green | maxDD | worst day | trades | win | causal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | b6 | rsi2c_d1_ex10 | USDJPY | D1 | counter=True, exit_n=10 | 2.00% | 2458 | 98.3 | 60% | -424 | -227 | 60 | 0.70 | ok |
| 2 | b4 | rollover_short | GBPJPY | H1 | - | 0.50% | 1971 | 78.9 | 76% | -237 | -237 | 508 | 0.67 | ok |
| 3 | b6 | rsi2c_d1_ex10 | GBPJPY | D1 | counter=True, exit_n=10 | 2.00% | 1960 | 78.4 | 72% | -596 | -203 | 59 | 0.75 | ok |
| 4 | b6 | rsi2c_d1_sl1.0 | USDJPY | D1 | counter=True, sl_atr=1.0 | 1.25% | 1836 | 73.5 | 60% | -558 | -160 | 79 | 0.59 | ok |
| 5 | b1 | gap_fade_fill | EURJPY | H1 | - | 2.00% | 1763 | 70.5 | 76% | -338 | -200 | 46 | 0.80 | ok |
| 6 | b6 | gap_fade_sl1.5 | EURJPY | H1 | sl_mult=1.5 | 2.00% | 1589 | 63.6 | 80% | -308 | -200 | 46 | 0.83 | ok |
| 7 | b2 | band_fade_h4_trend | CHFJPY | H4 | trend_n=200 | 2.00% | 1588 | 63.5 | 40% | -523 | -273 | 17 | 0.71 | ok |
| 8 | b5 | streak4_fade_d1 | GBPJPY | D1 | n=4, max_hold=4 | 1.50% | 1552 | 62.1 | 48% | -564 | -218 | 26 | 0.62 | ok |
| 9 | b6 | gap_fade_g0.2_h48 | EURJPY | H1 | min_gap=0.2, max_hold=48 | 2.00% | 1530 | 61.2 | 68% | -405 | -200 | 37 | 0.86 | ok |
| 10 | b6 | gap_fade_m30 | EURJPY | M30 | max_hold=48 | 2.00% | 1511 | 60.5 | 72% | -424 | -199 | 47 | 0.85 | ok |
| 11 | b4 | rollover_short | CHFJPY | H1 | - | 0.50% | 1511 | 60.4 | 64% | -515 | -257 | 508 | 0.67 | ok |
| 12 | b2 | rsi2_d1_counter | EURJPY | D1 | counter=True | 2.00% | 1489 | 59.6 | 64% | -578 | -214 | 60 | 0.67 | ok |
| 13 | b2 | rsi2_d1_counter | USDJPY | D1 | counter=True | 2.00% | 1464 | 58.6 | 56% | -527 | -193 | 62 | 0.69 | ok |
| 14 | b6 | rsi2c_d1_hold5 | EURJPY | D1 | counter=True, max_hold=5 | 2.00% | 1464 | 58.5 | 60% | -580 | -214 | 63 | 0.68 | ok |
| 15 | b5 | streak3_fade_d1_big | CADJPY | D1 | min_move=1.5, max_hold=3 | 2.00% | 1432 | 57.3 | 44% | -433 | -198 | 30 | 0.53 | ok |
| 16 | b5 | streak4_fade_d1 | USDJPY | D1 | n=4, max_hold=4 | 1.25% | 1419 | 56.8 | 40% | -520 | -143 | 31 | 0.58 | ok |
| 17 | b6 | rsi2c_d1_hold5 | USDJPY | D1 | counter=True, max_hold=5 | 2.00% | 1393 | 55.7 | 56% | -541 | -193 | 64 | 0.66 | ok |
| 18 | b6 | rsi2c_d1_15_85 | EURJPY | D1 | counter=True, lo=15, hi=85 | 1.50% | 1381 | 55.2 | 64% | -574 | -148 | 85 | 0.72 | ok |
| 19 | b6 | rsi2c_d1_ex10 | EURJPY | D1 | counter=True, exit_n=10 | 1.50% | 1359 | 54.4 | 72% | -463 | -148 | 59 | 0.71 | ok |
| 20 | b6 | rsi2c_d1_15_85 | CADJPY | D1 | counter=True, lo=15, hi=85 | 2.00% | 1337 | 53.5 | 64% | -581 | -198 | 88 | 0.72 | ok |
| 21 | b6 | rsi2c_d1_5_95 | EURJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 1330 | 53.2 | 52% | -386 | -189 | 33 | 0.67 | ok |
| 22 | b6 | rsi2c_d1_ex3 | EURJPY | D1 | counter=True, exit_n=3 | 2.00% | 1320 | 52.8 | 64% | -469 | -193 | 66 | 0.68 | ok |
| 23 | b6 | rsi2c_d1_sl1.0 | GBPJPY | D1 | counter=True, sl_atr=1.0 | 1.25% | 1316 | 52.6 | 68% | -549 | -180 | 80 | 0.60 | ok |
| 24 | b6 | gap_fade_g0.3_h48 | EURJPY | H1 | min_gap=0.3, max_hold=48 | 2.00% | 1306 | 52.2 | 56% | -338 | -198 | 24 | 0.88 | ok |
| 25 | b6 | rsi2c_d1_15_85 | USDJPY | D1 | counter=True, lo=15, hi=85 | 1.50% | 1298 | 51.9 | 64% | -460 | -149 | 84 | 0.70 | ok |
| 26 | b5 | zfade_d1_n20 | CADJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 1273 | 50.9 | 28% | -323 | -195 | 12 | 0.67 | ok |
| 27 | b6 | gap_fade_g0.2_h24 | EURJPY | H1 | min_gap=0.2, max_hold=24 | 2.00% | 1241 | 49.6 | 64% | -407 | -200 | 37 | 0.81 | ok |
| 28 | b5 | zfade_d1_n20 | AUDJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 1239 | 49.5 | 36% | -593 | -209 | 19 | 0.58 | ok |
| 29 | b6 | rsi2c_d1_short | EURJPY | D1 | counter=True, side=short | 2.00% | 1233 | 49.3 | 60% | -310 | -126 | 35 | 0.66 | ok |
| 30 | b5 | streak4_fade_d1 | CHFJPY | D1 | n=4, max_hold=4 | 1.50% | 1216 | 48.7 | 36% | -576 | -151 | 27 | 0.59 | ok |
| 31 | b6 | rsi2c_d1_5_95 | USDJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 1211 | 48.4 | 68% | -403 | -193 | 34 | 0.74 | ok |
| 32 | b4 | rollover_short | AUDJPY | H1 | - | 0.75% | 1187 | 47.5 | 60% | -575 | -290 | 508 | 0.58 | ok |
| 33 | b2 | rsi2_d1_counter | GBPJPY | D1 | counter=True | 2.00% | 1186 | 47.4 | 68% | -466 | -203 | 64 | 0.72 | ok |
| 34 | b6 | gap_fade_g0.1_h48 | EURJPY | H1 | min_gap=0.1, max_hold=48 | 1.50% | 1134 | 45.4 | 76% | -501 | -150 | 51 | 0.80 | ok |
| 35 | b6 | rsi3c_d1 | GBPJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1115 | 44.6 | 68% | -520 | -203 | 47 | 0.77 | ok |
| 36 | b6 | rsi2c_d1_short | USDJPY | D1 | counter=True, side=short | 2.00% | 1104 | 44.2 | 60% | -382 | -147 | 38 | 0.68 | ok |
| 37 | b5 | streak3_fade_d1 | USDJPY | D1 | - | 1.00% | 1083 | 43.3 | 60% | -535 | -126 | 77 | 0.51 | ok |
| 38 | b6 | rsi3c_d1 | CADJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1077 | 43.1 | 60% | -410 | -189 | 38 | 0.79 | ok |
| 39 | b6 | rsi2c_d1_short | GBPJPY | D1 | counter=True, side=short | 2.00% | 1070 | 42.8 | 60% | -274 | -141 | 39 | 0.74 | ok |
| 40 | b6 | rsi3c_d1 | USDJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1067 | 42.7 | 60% | -403 | -193 | 46 | 0.67 | ok |

### Every scored run

| # | batch | name | symbol | tf | params | best risk | net | avg/mo | green | maxDD | worst day | trades | win | causal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | b1 | day_open_fade | AUDJPY | H1 | - | 1.00% | 120 | 4.8 | 48% | -488 | -116 | 109 | 0.51 | ok |
| 2 | b1 | day_open_fade | CADJPY | H1 | - | 0.50% | -305 | -12.2 | 44% | -496 | -50 | 103 | 0.47 | ok |
| 3 | b1 | day_open_fade | CHFJPY | H1 | - | 0.25% | -276 | -11.0 | 32% | -290 | -25 | 117 | 0.42 | ok |
| 4 | b1 | day_open_fade | EURJPY | H1 | - | 0.25% | -222 | -8.9 | 36% | -310 | -25 | 105 | 0.45 | ok |
| 5 | b1 | day_open_fade | GBPJPY | H1 | - | 1.00% | -136 | -5.4 | 56% | -585 | -100 | 108 | 0.56 | ok |
| 6 | b1 | day_open_fade | NZDJPY | H1 | - | 0.25% | -143 | -5.7 | 4% | -154 | -25 | 10 | 0.20 | ok |
| 7 | b1 | day_open_fade | USDJPY | H1 | - | 0.50% | -353 | -14.1 | 44% | -570 | -50 | 111 | 0.48 | ok |
| 8 | b1 | day_open_fade_k1 | AUDJPY | H1 | k=1.0, tp_frac=0.5 | 1.25% | 254 | 10.2 | 44% | -590 | -124 | 55 | 0.53 | ok |
| 9 | b1 | day_open_fade_k1 | CADJPY | H1 | k=1.0, tp_frac=0.5 | 0.50% | -231 | -9.2 | 40% | -414 | -49 | 57 | 0.51 | ok |
| 10 | b1 | day_open_fade_k1 | CHFJPY | H1 | k=1.0, tp_frac=0.5 | 0.50% | -305 | -12.2 | 32% | -466 | -49 | 63 | 0.44 | ok |
| 11 | b1 | day_open_fade_k1 | EURJPY | H1 | k=1.0, tp_frac=0.5 | 0.50% | -338 | -13.5 | 32% | -537 | -49 | 52 | 0.35 | ok |
| 12 | b1 | day_open_fade_k1 | GBPJPY | H1 | k=1.0, tp_frac=0.5 | 0.75% | -245 | -9.8 | 28% | -466 | -74 | 61 | 0.44 | ok |
| 13 | b1 | day_open_fade_k1 | NZDJPY | H1 | k=1.0, tp_frac=0.5 | 0.50% | -232 | -9.3 | 40% | -460 | -63 | 53 | 0.45 | ok |
| 14 | b1 | day_open_fade_k1 | USDJPY | H1 | k=1.0, tp_frac=0.5 | 0.50% | -203 | -8.1 | 44% | -458 | -50 | 63 | 0.44 | ok |
| 15 | b1 | gap_fade_fill | AUDJPY | H1 | - | 1.50% | 162 | 6.5 | 56% | -568 | -149 | 43 | 0.70 | ok |
| 16 | b1 | gap_fade_fill | CADJPY | H1 | - | 1.00% | -422 | -16.9 | 36% | -581 | -100 | 41 | 0.61 | ok |
| 17 | b1 | gap_fade_fill | CHFJPY | H1 | - | 0.75% | -296 | -11.8 | 48% | -565 | -74 | 31 | 0.68 | ok |
| 18 | b1 | gap_fade_fill | EURJPY | H1 | - | 2.00% | 1763 | 70.5 | 76% | -338 | -200 | 46 | 0.80 | ok |
| 19 | b1 | gap_fade_fill | GBPJPY | H1 | - | 1.25% | 130 | 5.2 | 56% | -509 | -126 | 45 | 0.73 | ok |
| 20 | b1 | gap_fade_fill | NZDJPY | H1 | - | 0.75% | -343 | -13.7 | 36% | -566 | -74 | 36 | 0.47 | ok |
| 21 | b1 | gap_fade_fill | USDJPY | H1 | - | 0.50% | -322 | -12.9 | 40% | -552 | -50 | 35 | 0.51 | ok |
| 22 | b1 | gap_fade_half | AUDJPY | H1 | tp=half, min_gap=0.1 | 1.00% | -337 | -13.5 | 40% | -494 | -99 | 31 | 0.61 | ok |
| 23 | b1 | gap_fade_half | CADJPY | H1 | tp=half, min_gap=0.1 | 2.00% | -14 | -0.6 | 40% | -407 | -199 | 24 | 0.58 | ok |
| 24 | b1 | gap_fade_half | CHFJPY | H1 | tp=half, min_gap=0.1 | 1.00% | -340 | -13.6 | 44% | -523 | -99 | 21 | 0.71 | ok |
| 25 | b1 | gap_fade_half | EURJPY | H1 | tp=half, min_gap=0.1 | 1.00% | -225 | -9.0 | 56% | -547 | -100 | 33 | 0.67 | ok |
| 26 | b1 | gap_fade_half | GBPJPY | H1 | tp=half, min_gap=0.1 | 2.00% | 365 | 14.6 | 60% | -248 | -198 | 27 | 0.78 | ok |
| 27 | b1 | gap_fade_half | NZDJPY | H1 | tp=half, min_gap=0.1 | 1.00% | -510 | -20.4 | 28% | -596 | -100 | 29 | 0.52 | ok |
| 28 | b1 | gap_fade_half | USDJPY | H1 | tp=half, min_gap=0.1 | 0.75% | -242 | -9.7 | 44% | -480 | -75 | 33 | 0.58 | ok |
| 29 | b1 | pdh_sweep_mid | AUDJPY | H1 | tp=mid | none safe | -991 | -39.6 | 20% | -1065 | -27 | 264 | 0.44 | ok |
| 30 | b1 | pdh_sweep_mid | AUDJPY | M30 | tp=mid | none safe | -1260 | -50.4 | 8% | -1350 | -29 | 282 | 0.41 | ok |
| 31 | b1 | pdh_sweep_mid | CADJPY | H1 | tp=mid | none safe | -1405 | -56.2 | 8% | -1474 | -42 | 281 | 0.43 | ok |
| 32 | b1 | pdh_sweep_mid | CADJPY | M30 | tp=mid | none safe | -1535 | -61.4 | 20% | -1580 | -48 | 302 | 0.39 | ok |
| 33 | b1 | pdh_sweep_mid | CHFJPY | H1 | tp=mid | none safe | -1264 | -50.6 | 20% | -1316 | -58 | 274 | 0.42 | ok |
| 34 | b1 | pdh_sweep_mid | CHFJPY | M30 | tp=mid | none safe | -1733 | -69.3 | 20% | -1771 | -39 | 301 | 0.40 | ok |
| 35 | b1 | pdh_sweep_mid | EURJPY | H1 | tp=mid | none safe | -764 | -30.6 | 24% | -969 | -25 | 295 | 0.48 | ok |
| 36 | b1 | pdh_sweep_mid | EURJPY | M30 | tp=mid | none safe | -706 | -28.3 | 28% | -970 | -25 | 311 | 0.48 | ok |
| 37 | b1 | pdh_sweep_mid | GBPJPY | H1 | tp=mid | none safe | -827 | -33.1 | 36% | -965 | -25 | 289 | 0.47 | ok |
| 38 | b1 | pdh_sweep_mid | GBPJPY | M30 | tp=mid | none safe | -1101 | -44.0 | 28% | -1197 | -47 | 323 | 0.45 | ok |
| 39 | b1 | pdh_sweep_mid | NZDJPY | H1 | tp=mid | none safe | -729 | -29.2 | 24% | -750 | -25 | 176 | 0.44 | ok |
| 40 | b1 | pdh_sweep_mid | NZDJPY | M30 | tp=mid | none safe | -958 | -38.3 | 24% | -1080 | -25 | 231 | 0.41 | ok |
| 41 | b1 | pdh_sweep_mid | USDJPY | H1 | tp=mid | none safe | -746 | -29.9 | 32% | -905 | -43 | 260 | 0.43 | ok |
| 42 | b1 | pdh_sweep_mid | USDJPY | M30 | tp=mid | none safe | -1096 | -43.8 | 32% | -1144 | -47 | 280 | 0.42 | ok |
| 43 | b1 | pdh_sweep_p1 | AUDJPY | H1 | pierce=0.1, tp=mid | 0.25% | -383 | -15.3 | 28% | -486 | -25 | 116 | 0.42 | ok |
| 44 | b1 | pdh_sweep_p1 | CADJPY | H1 | pierce=0.1, tp=mid | 0.25% | -299 | -12.0 | 52% | -463 | -25 | 141 | 0.50 | ok |
| 45 | b1 | pdh_sweep_p1 | CHFJPY | H1 | pierce=0.1, tp=mid | 0.25% | -220 | -8.8 | 32% | -320 | -25 | 137 | 0.52 | ok |
| 46 | b1 | pdh_sweep_p1 | EURJPY | H1 | pierce=0.1, tp=mid | 0.25% | -186 | -7.4 | 40% | -425 | -41 | 125 | 0.46 | ok |
| 47 | b1 | pdh_sweep_p1 | GBPJPY | H1 | pierce=0.1, tp=mid | 0.25% | -324 | -12.9 | 40% | -408 | -25 | 135 | 0.47 | ok |
| 48 | b1 | pdh_sweep_p1 | NZDJPY | H1 | pierce=0.1, tp=mid | 0.25% | -191 | -7.7 | 32% | -268 | -25 | 51 | 0.49 | ok |
| 49 | b1 | pdh_sweep_p1 | USDJPY | H1 | pierce=0.1, tp=mid | 0.25% | -293 | -11.7 | 44% | -373 | -28 | 133 | 0.46 | ok |
| 50 | b1 | pdh_sweep_pdc | AUDJPY | H1 | tp=pdc | 0.25% | -413 | -16.5 | 28% | -496 | -29 | 228 | 0.50 | ok |
| 51 | b1 | pdh_sweep_pdc | CADJPY | H1 | tp=pdc | none safe | -1009 | -40.4 | 12% | -1082 | -42 | 239 | 0.49 | ok |
| 52 | b1 | pdh_sweep_pdc | CHFJPY | H1 | tp=pdc | none safe | -1178 | -47.1 | 12% | -1188 | -58 | 230 | 0.47 | ok |
| 53 | b1 | pdh_sweep_pdc | EURJPY | H1 | tp=pdc | none safe | -946 | -37.8 | 20% | -1083 | -35 | 260 | 0.53 | ok |
| 54 | b1 | pdh_sweep_pdc | GBPJPY | H1 | tp=pdc | none safe | -854 | -34.2 | 24% | -888 | -25 | 260 | 0.48 | ok |
| 55 | b1 | pdh_sweep_pdc | NZDJPY | H1 | tp=pdc | none safe | -594 | -23.8 | 24% | -610 | -25 | 163 | 0.50 | ok |
| 56 | b1 | pdh_sweep_pdc | USDJPY | H1 | tp=pdc | none safe | -637 | -25.5 | 32% | -731 | -43 | 234 | 0.54 | ok |
| 57 | b1 | tokyo_sweep_mid | AUDJPY | H1 | tp=mid | none safe | -978 | -39.1 | 28% | -1255 | -25 | 229 | 0.52 | ok |
| 58 | b1 | tokyo_sweep_mid | CADJPY | H1 | tp=mid | none safe | -1461 | -58.4 | 12% | -1493 | -25 | 269 | 0.52 | ok |
| 59 | b1 | tokyo_sweep_mid | CHFJPY | H1 | tp=mid | none safe | -1645 | -65.8 | 16% | -1672 | -25 | 287 | 0.51 | ok |
| 60 | b1 | tokyo_sweep_mid | EURJPY | H1 | tp=mid | none safe | -1238 | -49.5 | 20% | -1434 | -25 | 278 | 0.54 | ok |
| 61 | b1 | tokyo_sweep_mid | GBPJPY | H1 | tp=mid | none safe | -919 | -36.7 | 36% | -1064 | -25 | 280 | 0.57 | ok |
| 62 | b1 | tokyo_sweep_mid | NZDJPY | H1 | tp=mid | none safe | -1118 | -44.7 | 24% | -1259 | -25 | 211 | 0.47 | ok |
| 63 | b1 | tokyo_sweep_mid | USDJPY | H1 | tp=mid | none safe | -1062 | -42.5 | 24% | -1113 | -30 | 263 | 0.51 | ok |
| 64 | b1 | tokyo_sweep_rng | AUDJPY | H1 | tp=range | none safe | -844 | -33.8 | 20% | -1017 | -25 | 242 | 0.41 | ok |
| 65 | b1 | tokyo_sweep_rng | AUDJPY | M30 | tp=range | none safe | -1083 | -43.3 | 24% | -1201 | -25 | 263 | 0.37 | ok |
| 66 | b1 | tokyo_sweep_rng | CADJPY | H1 | tp=range | none safe | -1734 | -69.4 | 16% | -1820 | -25 | 284 | 0.36 | ok |
| 67 | b1 | tokyo_sweep_rng | CADJPY | M30 | tp=range | none safe | -1906 | -76.2 | 20% | -1974 | -25 | 314 | 0.34 | ok |
| 68 | b1 | tokyo_sweep_rng | CHFJPY | H1 | tp=range | none safe | -1586 | -63.5 | 16% | -1614 | -50 | 309 | 0.39 | ok |
| 69 | b1 | tokyo_sweep_rng | CHFJPY | M30 | tp=range | none safe | -2048 | -81.9 | 20% | -2065 | -82 | 338 | 0.36 | ok |
| 70 | b1 | tokyo_sweep_rng | EURJPY | H1 | tp=range | none safe | -739 | -29.5 | 40% | -1040 | -25 | 293 | 0.45 | ok |
| 71 | b1 | tokyo_sweep_rng | EURJPY | M30 | tp=range | none safe | -510 | -20.4 | 36% | -992 | -25 | 317 | 0.43 | ok |
| 72 | b1 | tokyo_sweep_rng | GBPJPY | H1 | tp=range | none safe | -934 | -37.4 | 28% | -1075 | -25 | 303 | 0.43 | ok |
| 73 | b1 | tokyo_sweep_rng | GBPJPY | M30 | tp=range | none safe | -1090 | -43.6 | 24% | -1168 | -25 | 326 | 0.40 | ok |
| 74 | b1 | tokyo_sweep_rng | NZDJPY | H1 | tp=range | none safe | -1038 | -41.5 | 40% | -1333 | -31 | 213 | 0.39 | ok |
| 75 | b1 | tokyo_sweep_rng | NZDJPY | M30 | tp=range | none safe | -1410 | -56.4 | 32% | -1624 | -31 | 251 | 0.35 | ok |
| 76 | b1 | tokyo_sweep_rng | USDJPY | H1 | tp=range | none safe | -1527 | -61.1 | 28% | -1596 | -30 | 275 | 0.35 | ok |
| 77 | b1 | tokyo_sweep_rng | USDJPY | M30 | tp=range | none safe | -1461 | -58.4 | 32% | -1532 | -51 | 304 | 0.36 | ok |
| 78 | b1 | week_open_fade | AUDJPY | H1 | - | 1.00% | 286 | 11.4 | 44% | -539 | -129 | 46 | 0.46 | ok |
| 79 | b1 | week_open_fade | CADJPY | H1 | - | 0.75% | 158 | 6.3 | 56% | -532 | -115 | 45 | 0.53 | ok |
| 80 | b1 | week_open_fade | CHFJPY | H1 | - | 0.25% | -245 | -9.8 | 32% | -285 | -38 | 35 | 0.31 | ok |
| 81 | b1 | week_open_fade | EURJPY | H1 | - | 0.50% | -425 | -17.0 | 32% | -456 | -73 | 40 | 0.35 | ok |
| 82 | b1 | week_open_fade | GBPJPY | H1 | - | 0.75% | -265 | -10.6 | 32% | -586 | -109 | 39 | 0.41 | ok |
| 83 | b1 | week_open_fade | NZDJPY | H1 | - | 0.50% | -466 | -18.6 | 12% | -488 | -71 | 34 | 0.32 | ok |
| 84 | b1 | week_open_fade | USDJPY | H1 | - | 0.50% | -411 | -16.4 | 44% | -588 | -61 | 47 | 0.40 | ok |
| 85 | b1 | week_open_fade_k2 | AUDJPY | H1 | k=2.0 | 1.25% | -293 | -11.7 | 24% | -552 | -137 | 20 | 0.40 | ok |
| 86 | b1 | week_open_fade_k2 | CADJPY | H1 | k=2.0 | 0.75% | -285 | -11.4 | 12% | -482 | -75 | 20 | 0.35 | ok |
| 87 | b1 | week_open_fade_k2 | CHFJPY | H1 | k=2.0 | 0.50% | -464 | -18.5 | 12% | -529 | -81 | 23 | 0.30 | ok |
| 88 | b1 | week_open_fade_k2 | EURJPY | H1 | k=2.0 | 0.50% | -308 | -12.3 | 20% | -407 | -73 | 21 | 0.33 | ok |
| 89 | b1 | week_open_fade_k2 | GBPJPY | H1 | k=2.0 | 1.00% | 20 | 0.8 | 28% | -518 | -148 | 21 | 0.52 | ok |
| 90 | b1 | week_open_fade_k2 | NZDJPY | H1 | k=2.0 | 1.50% | -300 | -12.0 | 20% | -543 | -172 | 21 | 0.38 | ok |
| 91 | b1 | week_open_fade_k2 | USDJPY | H1 | k=2.0 | 0.75% | -232 | -9.3 | 24% | -453 | -98 | 25 | 0.44 | ok |
| 92 | b2 | band_fade_h1_k3 | AUDJPY | H1 | k=3.0, n=24 | none safe | -784 | -31.4 | 20% | -802 | -72 | 115 | 0.29 | ok |
| 93 | b2 | band_fade_h1_k3 | CADJPY | H1 | k=3.0, n=24 | none safe | -1197 | -47.9 | 20% | -1264 | -71 | 135 | 0.25 | ok |
| 94 | b2 | band_fade_h1_k3 | CHFJPY | H1 | k=3.0, n=24 | none safe | -1017 | -40.7 | 24% | -1094 | -74 | 108 | 0.25 | ok |
| 95 | b2 | band_fade_h1_k3 | EURJPY | H1 | k=3.0, n=24 | none safe | -1191 | -47.6 | 20% | -1191 | -84 | 139 | 0.27 | ok |
| 96 | b2 | band_fade_h1_k3 | GBPJPY | H1 | k=3.0, n=24 | 0.25% | -208 | -8.3 | 44% | -559 | -73 | 133 | 0.34 | ok |
| 97 | b2 | band_fade_h1_k3 | NZDJPY | H1 | k=3.0, n=24 | none safe | -1003 | -40.1 | 24% | -1003 | -75 | 109 | 0.26 | ok |
| 98 | b2 | band_fade_h1_k3 | USDJPY | H1 | k=3.0, n=24 | none safe | -1011 | -40.4 | 28% | -1226 | -95 | 140 | 0.25 | ok |
| 99 | b2 | band_fade_h4 | AUDJPY | H4 | - | 0.25% | -372 | -14.9 | 40% | -489 | -64 | 74 | 0.30 | ok |
| 100 | b2 | band_fade_h4 | CADJPY | H4 | - | 0.25% | -491 | -19.7 | 28% | -549 | -77 | 76 | 0.26 | ok |
| 101 | b2 | band_fade_h4 | CHFJPY | H4 | - | 0.50% | -273 | -10.9 | 48% | -582 | -123 | 72 | 0.40 | ok |
| 102 | b2 | band_fade_h4 | EURJPY | H4 | - | 0.25% | -538 | -21.5 | 32% | -555 | -76 | 76 | 0.28 | ok |
| 103 | b2 | band_fade_h4 | GBPJPY | H4 | - | 0.25% | 292 | 11.7 | 56% | -300 | -70 | 74 | 0.45 | ok |
| 104 | b2 | band_fade_h4 | NZDJPY | H4 | - | 0.25% | -173 | -6.9 | 8% | -222 | -46 | 14 | 0.21 | ok |
| 105 | b2 | band_fade_h4 | USDJPY | H4 | - | 0.25% | -313 | -12.5 | 44% | -508 | -75 | 88 | 0.31 | ok |
| 106 | b2 | band_fade_h4_trend | AUDJPY | H4 | trend_n=200 | 0.50% | -174 | -7.0 | 20% | -435 | -99 | 19 | 0.32 | ok |
| 107 | b2 | band_fade_h4_trend | CADJPY | H4 | trend_n=200 | 0.75% | -48 | -1.9 | 20% | -569 | -145 | 16 | 0.38 | ok |
| 108 | b2 | band_fade_h4_trend | CHFJPY | H4 | trend_n=200 | 2.00% | 1588 | 63.5 | 40% | -523 | -273 | 17 | 0.71 | ok |
| 109 | b2 | band_fade_h4_trend | EURJPY | H4 | trend_n=200 | 1.00% | -405 | -16.2 | 16% | -595 | -207 | 23 | 0.39 | ok |
| 110 | b2 | band_fade_h4_trend | GBPJPY | H4 | trend_n=200 | 1.25% | 916 | 36.6 | 40% | -558 | -249 | 22 | 0.50 | ok |
| 111 | b2 | band_fade_h4_trend | NZDJPY | H4 | trend_n=200 | 0.25% | -138 | -5.5 | 8% | -146 | -34 | 8 | 0.12 | ok |
| 112 | b2 | band_fade_h4_trend | USDJPY | H4 | trend_n=200 | 1.25% | 834 | 33.4 | 32% | -591 | -190 | 19 | 0.47 | ok |
| 113 | b2 | bigday_fade_k1.0 | AUDJPY | H1 | k=1.0 | 0.75% | -253 | -10.1 | 32% | -531 | -74 | 42 | 0.48 | ok |
| 114 | b2 | bigday_fade_k1.0 | CADJPY | H1 | k=1.0 | 0.75% | -273 | -10.9 | 32% | -567 | -75 | 45 | 0.47 | ok |
| 115 | b2 | bigday_fade_k1.0 | CHFJPY | H1 | k=1.0 | 0.25% | -406 | -16.2 | 32% | -446 | -24 | 54 | 0.30 | ok |
| 116 | b2 | bigday_fade_k1.0 | EURJPY | H1 | k=1.0 | 0.25% | -233 | -9.3 | 40% | -299 | -25 | 51 | 0.47 | ok |
| 117 | b2 | bigday_fade_k1.0 | GBPJPY | H1 | k=1.0 | 0.25% | -181 | -7.3 | 40% | -278 | -24 | 46 | 0.41 | ok |
| 118 | b2 | bigday_fade_k1.0 | NZDJPY | H1 | k=1.0 | 1.00% | -114 | -4.5 | 44% | -562 | -101 | 44 | 0.57 | ok |
| 119 | b2 | bigday_fade_k1.0 | USDJPY | H1 | k=1.0 | 0.75% | -1 | -0.0 | 36% | -467 | -75 | 58 | 0.52 | ok |
| 120 | b2 | bigday_fade_k1.3 | AUDJPY | H1 | k=1.3 | 1.50% | -221 | -8.8 | 24% | -590 | -149 | 18 | 0.44 | ok |
| 121 | b2 | bigday_fade_k1.3 | CADJPY | H1 | k=1.3 | 1.00% | -231 | -9.2 | 20% | -494 | -99 | 15 | 0.33 | ok |
| 122 | b2 | bigday_fade_k1.3 | CHFJPY | H1 | k=1.3 | 0.50% | -329 | -13.2 | 20% | -381 | -50 | 21 | 0.33 | ok |
| 123 | b2 | bigday_fade_k1.3 | EURJPY | H1 | k=1.3 | 0.50% | -391 | -15.6 | 16% | -444 | -50 | 17 | 0.29 | ok |
| 124 | b2 | bigday_fade_k1.3 | GBPJPY | H1 | k=1.3 | 0.50% | -346 | -13.8 | 16% | -455 | -49 | 21 | 0.29 | ok |
| 125 | b2 | bigday_fade_k1.3 | NZDJPY | H1 | k=1.3 | 1.00% | -200 | -8.0 | 16% | -523 | -101 | 18 | 0.50 | ok |
| 126 | b2 | bigday_fade_k1.3 | USDJPY | H1 | k=1.3 | 1.00% | -15 | -0.6 | 28% | -542 | -100 | 21 | 0.52 | ok |
| 127 | b2 | bigday_fade_k1.6 | AUDJPY | H1 | k=1.6 | 2.00% | 261 | 10.5 | 12% | -279 | -194 | 6 | 0.67 | ok |
| 128 | b2 | bigday_fade_k1.6 | CADJPY | H1 | k=1.6 | 1.25% | -413 | -16.5 | 8% | -580 | -124 | 9 | 0.22 | ok |
| 129 | b2 | bigday_fade_k1.6 | CHFJPY | H1 | k=1.6 | 1.00% | -393 | -15.7 | 8% | -502 | -100 | 9 | 0.22 | ok |
| 130 | b2 | bigday_fade_k1.6 | EURJPY | H1 | k=1.6 | 1.00% | -526 | -21.1 | 0% | -567 | -100 | 7 | 0.00 | ok |
| 131 | b2 | bigday_fade_k1.6 | GBPJPY | H1 | k=1.6 | 1.25% | -414 | -16.6 | 8% | -514 | -125 | 8 | 0.25 | ok |
| 132 | b2 | bigday_fade_k1.6 | NZDJPY | H1 | k=1.6 | 2.00% | 324 | 13.0 | 20% | -257 | -199 | 8 | 0.62 | ok |
| 133 | b2 | bigday_fade_k1.6 | USDJPY | H1 | k=1.6 | 1.00% | -193 | -7.7 | 20% | -550 | -100 | 12 | 0.42 | ok |
| 134 | b2 | bigday_fade_ldn | AUDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.50% | -95 | -3.8 | 24% | -529 | -150 | 22 | 0.41 | ok |
| 135 | b2 | bigday_fade_ldn | CADJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.50% | 233 | 9.3 | 24% | -533 | -150 | 25 | 0.48 | ok |
| 136 | b2 | bigday_fade_ldn | CHFJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.25% | -302 | -12.1 | 32% | -590 | -125 | 28 | 0.50 | ok |
| 137 | b2 | bigday_fade_ldn | EURJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.00% | -47 | -1.9 | 36% | -484 | -100 | 27 | 0.52 | ok |
| 138 | b2 | bigday_fade_ldn | GBPJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 0.75% | -333 | -13.3 | 20% | -473 | -74 | 27 | 0.44 | ok |
| 139 | b2 | bigday_fade_ldn | NZDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.50% | 383 | 15.3 | 32% | -450 | -150 | 23 | 0.61 | ok |
| 140 | b2 | bigday_fade_ldn | USDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14 | 1.50% | 17 | 0.7 | 28% | -478 | -150 | 29 | 0.52 | ok |
| 141 | b2 | bigday_follow_k1.3 | AUDJPY | H1 | k=1.3, mode=follow | 1.00% | -489 | -19.6 | 20% | -533 | -100 | 18 | 0.39 | ok |
| 142 | b2 | bigday_follow_k1.3 | CADJPY | H1 | k=1.3, mode=follow | 0.75% | -353 | -14.1 | 16% | -568 | -74 | 15 | 0.40 | ok |
| 143 | b2 | bigday_follow_k1.3 | CHFJPY | H1 | k=1.3, mode=follow | 0.75% | 11 | 0.4 | 24% | -507 | -75 | 21 | 0.57 | ok |
| 144 | b2 | bigday_follow_k1.3 | EURJPY | H1 | k=1.3, mode=follow | 1.50% | 10 | 0.4 | 28% | -565 | -149 | 17 | 0.53 | ok |
| 145 | b2 | bigday_follow_k1.3 | GBPJPY | H1 | k=1.3, mode=follow | 1.50% | -325 | -13.0 | 32% | -586 | -147 | 21 | 0.43 | ok |
| 146 | b2 | bigday_follow_k1.3 | NZDJPY | H1 | k=1.3, mode=follow | 1.25% | -273 | -10.9 | 12% | -566 | -124 | 18 | 0.50 | ok |
| 147 | b2 | bigday_follow_k1.3 | USDJPY | H1 | k=1.3, mode=follow | 0.50% | -459 | -18.4 | 12% | -496 | -50 | 21 | 0.24 | ok |
| 148 | b2 | rsi2_d1_counter | AUDJPY | D1 | counter=True | 1.00% | 105 | 4.2 | 64% | -525 | -100 | 67 | 0.63 | ok |
| 149 | b2 | rsi2_d1_counter | CADJPY | D1 | counter=True | 1.50% | 616 | 24.6 | 72% | -529 | -151 | 56 | 0.70 | ok |
| 150 | b2 | rsi2_d1_counter | CHFJPY | D1 | counter=True | 1.50% | 333 | 13.3 | 68% | -491 | -169 | 62 | 0.71 | ok |
| 151 | b2 | rsi2_d1_counter | EURJPY | D1 | counter=True | 2.00% | 1489 | 59.6 | 64% | -578 | -214 | 60 | 0.67 | ok |
| 152 | b2 | rsi2_d1_counter | GBPJPY | D1 | counter=True | 2.00% | 1186 | 47.4 | 68% | -466 | -203 | 64 | 0.72 | ok |
| 153 | b2 | rsi2_d1_counter | NZDJPY | D1 | counter=True | 1.25% | -84 | -3.3 | 44% | -546 | -122 | 50 | 0.58 | ok |
| 154 | b2 | rsi2_d1_counter | USDJPY | D1 | counter=True | 2.00% | 1464 | 58.6 | 56% | -527 | -193 | 62 | 0.69 | ok |
| 155 | b2 | rsi2_d1_trend | AUDJPY | D1 | - | 1.25% | 258 | 10.3 | 64% | -552 | -125 | 26 | 0.65 | ok |
| 156 | b2 | rsi2_d1_trend | CADJPY | D1 | - | 2.00% | 887 | 35.5 | 56% | -381 | -198 | 19 | 0.79 | ok |
| 157 | b2 | rsi2_d1_trend | CHFJPY | D1 | - | 2.00% | 630 | 25.2 | 56% | -285 | -219 | 21 | 0.76 | ok |
| 158 | b2 | rsi2_d1_trend | EURJPY | D1 | - | 2.00% | 1046 | 41.8 | 44% | -214 | -214 | 17 | 0.82 | ok |
| 159 | b2 | rsi2_d1_trend | GBPJPY | D1 | - | 2.00% | 811 | 32.4 | 60% | -203 | -203 | 23 | 0.87 | ok |
| 160 | b2 | rsi2_d1_trend | NZDJPY | D1 | - | 2.00% | 277 | 11.1 | 64% | -577 | -193 | 28 | 0.64 | ok |
| 161 | b2 | rsi2_d1_trend | USDJPY | D1 | - | 2.00% | -268 | -10.7 | 32% | -530 | -193 | 19 | 0.63 | ok |
| 162 | b2 | rsi2_h4_counter | AUDJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.25% | -270 | -10.8 | 48% | -468 | -45 | 226 | 0.60 | ok |
| 163 | b2 | rsi2_h4_counter | CADJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.75% | 81 | 3.2 | 44% | -484 | -145 | 229 | 0.62 | ok |
| 164 | b2 | rsi2_h4_counter | CHFJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.50% | -364 | -14.6 | 40% | -444 | -112 | 219 | 0.62 | ok |
| 165 | b2 | rsi2_h4_counter | EURJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.25% | -259 | -10.4 | 48% | -381 | -68 | 214 | 0.59 | ok |
| 166 | b2 | rsi2_h4_counter | GBPJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.25% | -389 | -15.6 | 36% | -470 | -55 | 234 | 0.60 | ok |
| 167 | b2 | rsi2_h4_counter | NZDJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.75% | 49 | 1.9 | 48% | -396 | -132 | 211 | 0.68 | ok |
| 168 | b2 | rsi2_h4_counter | USDJPY | H4 | counter=True, lo=5, hi=95, max_hold=30 | 0.50% | -262 | -10.5 | 44% | -551 | -143 | 257 | 0.60 | ok |
| 169 | b2 | rsi2_h4_trend | AUDJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.25% | -259 | -10.4 | 36% | -308 | -37 | 139 | 0.55 | ok |
| 170 | b2 | rsi2_h4_trend | CADJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.25% | -225 | -9.0 | 36% | -311 | -47 | 147 | 0.54 | ok |
| 171 | b2 | rsi2_h4_trend | CHFJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.50% | -481 | -19.3 | 40% | -540 | -94 | 148 | 0.56 | ok |
| 172 | b2 | rsi2_h4_trend | EURJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.25% | -254 | -10.2 | 36% | -305 | -34 | 139 | 0.63 | ok |
| 173 | b2 | rsi2_h4_trend | GBPJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.25% | -331 | -13.2 | 28% | -355 | -38 | 150 | 0.57 | ok |
| 174 | b2 | rsi2_h4_trend | NZDJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.50% | -378 | -15.1 | 44% | -548 | -104 | 94 | 0.57 | ok |
| 175 | b2 | rsi2_h4_trend | USDJPY | H4 | trend_n=200, exit_n=5, max_hold=30 | 0.25% | -207 | -8.3 | 40% | -384 | -47 | 167 | 0.58 | ok |
| 176 | b2 | shock_fade | AUDJPY | H1 | - | 1.50% | -383 | -15.3 | 12% | -596 | -227 | 10 | 0.50 | ok |
| 177 | b2 | shock_fade | AUDJPY | H1 | - | 1.50% | -383 | -15.3 | 12% | -596 | -227 | 10 | 0.50 | ok |
| 178 | b2 | shock_fade | CADJPY | H1 | - | 1.00% | -407 | -16.3 | 8% | -480 | -100 | 8 | 0.25 | ok |
| 179 | b2 | shock_fade | CADJPY | H1 | - | 1.00% | -407 | -16.3 | 8% | -480 | -100 | 8 | 0.25 | ok |
| 180 | b2 | shock_fade | CHFJPY | H1 | - | 1.50% | -19 | -0.8 | 16% | -563 | -149 | 8 | 0.50 | ok |
| 181 | b2 | shock_fade | CHFJPY | H1 | - | 1.50% | -19 | -0.8 | 16% | -563 | -149 | 8 | 0.50 | ok |
| 182 | b2 | shock_fade | EURJPY | H1 | - | 1.25% | -327 | -13.1 | 8% | -590 | -146 | 8 | 0.38 | ok |
| 183 | b2 | shock_fade | GBPJPY | H1 | - | 1.25% | -388 | -15.5 | 8% | -579 | -143 | 8 | 0.25 | ok |
| 184 | b2 | shock_fade | GBPJPY | H1 | - | 1.25% | -388 | -15.5 | 8% | -579 | -143 | 8 | 0.25 | ok |
| 185 | b2 | shock_fade | NZDJPY | H1 | - | 1.50% | -437 | -17.5 | 8% | -581 | -147 | 7 | 0.29 | ok |
| 186 | b2 | shock_fade | NZDJPY | H1 | - | 1.50% | -437 | -17.5 | 8% | -581 | -147 | 7 | 0.29 | ok |
| 187 | b2 | shock_fade | USDJPY | H1 | - | 1.50% | -209 | -8.3 | 16% | -598 | -194 | 8 | 0.50 | ok |
| 188 | b2 | shock_fade_d1 | AUDJPY | D1 | k=2.0, hold_days=3 | 1.25% | -365 | -14.6 | 12% | -495 | -125 | 11 | 0.36 | ok |
| 189 | b2 | shock_fade_d1 | CADJPY | D1 | k=2.0, hold_days=3 | 2.00% | -259 | -10.4 | 20% | -515 | -200 | 13 | 0.46 | ok |
| 190 | b2 | shock_fade_d1 | CHFJPY | D1 | k=2.0, hold_days=3 | 1.50% | -258 | -10.3 | 12% | -547 | -221 | 9 | 0.44 | ok |
| 191 | b2 | shock_fade_d1 | EURJPY | D1 | k=2.0, hold_days=3 | 2.00% | -528 | -21.1 | 12% | -544 | -264 | 10 | 0.40 | ok |
| 192 | b2 | shock_fade_d1 | GBPJPY | D1 | k=2.0, hold_days=3 | 2.00% | -345 | -13.8 | 16% | -527 | -276 | 12 | 0.50 | ok |
| 193 | b2 | shock_fade_d1 | NZDJPY | D1 | k=2.0, hold_days=3 | 1.25% | -525 | -21.0 | 8% | -530 | -149 | 12 | 0.33 | ok |
| 194 | b2 | shock_fade_d1 | USDJPY | D1 | k=2.0, hold_days=3 | 2.00% | -252 | -10.1 | 16% | -599 | -283 | 15 | 0.47 | ok |
| 195 | b2 | shock_follow | AUDJPY | H1 | mode=follow | 0.75% | -342 | -13.7 | 8% | -482 | -83 | 10 | 0.20 | ok |
| 196 | b2 | shock_follow | AUDJPY | H1 | mode=follow | 0.75% | -342 | -13.7 | 8% | -482 | -83 | 10 | 0.20 | ok |
| 197 | b2 | shock_follow | CADJPY | H1 | mode=follow | 1.50% | 131 | 5.3 | 8% | -531 | -216 | 7 | 0.29 | ok |
| 198 | b2 | shock_follow | CADJPY | H1 | mode=follow | 1.50% | 131 | 5.3 | 8% | -531 | -216 | 7 | 0.29 | ok |
| 199 | b2 | shock_follow | CHFJPY | H1 | mode=follow | 1.25% | 117 | 4.7 | 12% | -571 | -121 | 7 | 0.29 | ok |
| 200 | b2 | shock_follow | CHFJPY | H1 | mode=follow | 1.25% | 117 | 4.7 | 12% | -571 | -121 | 7 | 0.29 | ok |
| 201 | b2 | shock_follow | EURJPY | H1 | mode=follow | 1.25% | 103 | 4.1 | 8% | -554 | -128 | 7 | 0.29 | ok |
| 202 | b2 | shock_follow | EURJPY | H1 | mode=follow | 1.25% | 103 | 4.1 | 8% | -554 | -128 | 7 | 0.29 | ok |
| 203 | b2 | shock_follow | GBPJPY | H1 | mode=follow | 2.00% | 282 | 11.3 | 12% | -599 | -196 | 7 | 0.43 | ok |
| 204 | b2 | shock_follow | GBPJPY | H1 | mode=follow | 2.00% | 282 | 11.3 | 12% | -599 | -196 | 7 | 0.43 | ok |
| 205 | b2 | shock_follow | NZDJPY | H1 | mode=follow | 2.00% | 380 | 15.2 | 12% | -537 | -190 | 7 | 0.57 | ok |
| 206 | b2 | shock_follow | USDJPY | H1 | mode=follow | 1.00% | -165 | -6.6 | 8% | -481 | -161 | 8 | 0.25 | ok |
| 207 | b2 | shock_follow | USDJPY | H1 | mode=follow | 1.00% | -165 | -6.6 | 8% | -481 | -161 | 8 | 0.25 | ok |
| 208 | b2 | yen_basket_fade | AUDJPY | H1 | - | 0.50% | -461 | -18.4 | 28% | -557 | -50 | 49 | 0.41 | ok |
| 209 | b2 | yen_basket_fade | CADJPY | H1 | - | 0.25% | -143 | -5.7 | 28% | -297 | -25 | 49 | 0.35 | ok |
| 210 | b2 | yen_basket_fade | CHFJPY | H1 | - | 0.50% | -419 | -16.8 | 36% | -465 | -50 | 49 | 0.41 | ok |
| 211 | b2 | yen_basket_fade | EURJPY | H1 | - | 0.50% | -405 | -16.2 | 32% | -494 | -50 | 49 | 0.35 | ok |
| 212 | b2 | yen_basket_fade | GBPJPY | H1 | - | 0.50% | -461 | -18.4 | 16% | -546 | -50 | 49 | 0.39 | ok |
| 213 | b2 | yen_basket_fade | NZDJPY | H1 | - | 0.50% | -174 | -6.9 | 8% | -247 | -50 | 21 | 0.43 | ok |
| 214 | b2 | yen_basket_fade | USDJPY | H1 | - | 0.50% | -4 | -0.2 | 44% | -523 | -50 | 49 | 0.49 | ok |
| 215 | b2 | yen_basket_fade_z2 | AUDJPY | H1 | z=2.0, max_hold=48 | 0.50% | -478 | -19.1 | 16% | -599 | -71 | 20 | 0.20 | ok |
| 216 | b2 | yen_basket_fade_z2 | CADJPY | H1 | z=2.0, max_hold=48 | 0.50% | -267 | -10.7 | 28% | -480 | -61 | 20 | 0.40 | ok |
| 217 | b2 | yen_basket_fade_z2 | CHFJPY | H1 | z=2.0, max_hold=48 | 0.50% | -384 | -15.4 | 12% | -438 | -62 | 20 | 0.25 | ok |
| 218 | b2 | yen_basket_fade_z2 | EURJPY | H1 | z=2.0, max_hold=48 | 0.50% | -462 | -18.5 | 20% | -504 | -88 | 20 | 0.35 | ok |
| 219 | b2 | yen_basket_fade_z2 | GBPJPY | H1 | z=2.0, max_hold=48 | 0.50% | -293 | -11.7 | 24% | -440 | -65 | 20 | 0.35 | ok |
| 220 | b2 | yen_basket_fade_z2 | NZDJPY | H1 | z=2.0, max_hold=48 | 0.50% | -514 | -20.6 | 0% | -526 | -78 | 12 | 0.08 | ok |
| 221 | b2 | yen_basket_fade_z2 | USDJPY | H1 | z=2.0, max_hold=48 | 0.50% | -112 | -4.5 | 24% | -418 | -66 | 20 | 0.35 | ok |
| 222 | b2 | yen_basket_follow | AUDJPY | H1 | mode=follow | 0.50% | -70 | -2.8 | 36% | -473 | -50 | 49 | 0.43 | ok |
| 223 | b2 | yen_basket_follow | CADJPY | H1 | mode=follow | 0.75% | -195 | -7.8 | 24% | -528 | -75 | 49 | 0.39 | ok |
| 224 | b2 | yen_basket_follow | CHFJPY | H1 | mode=follow | 0.75% | -148 | -5.9 | 36% | -521 | -73 | 49 | 0.49 | ok |
| 225 | b2 | yen_basket_follow | EURJPY | H1 | mode=follow | 1.00% | 221 | 8.8 | 36% | -550 | -100 | 49 | 0.47 | ok |
| 226 | b2 | yen_basket_follow | GBPJPY | H1 | mode=follow | 0.75% | 110 | 4.4 | 44% | -444 | -75 | 49 | 0.47 | ok |
| 227 | b2 | yen_basket_follow | NZDJPY | H1 | mode=follow | 0.75% | 98 | 3.9 | 36% | -462 | -74 | 45 | 0.44 | ok |
| 228 | b2 | yen_basket_follow | USDJPY | H1 | mode=follow | 0.25% | -154 | -6.2 | 24% | -285 | -25 | 49 | 0.37 | ok |
| 229 | b3 | carry_dip | AUDJPY | D1 | - | 1.00% | 765 | 30.6 | 60% | -539 | -128 | 39 | 0.59 | ok |
| 230 | b3 | carry_dip | CADJPY | D1 | - | 1.25% | 351 | 14.1 | 60% | -597 | -161 | 43 | 0.51 | ok |
| 231 | b3 | carry_dip | CHFJPY | D1 | - | 1.00% | 833 | 33.3 | 44% | -507 | -117 | 41 | 0.56 | ok |
| 232 | b3 | carry_dip | EURJPY | D1 | - | 0.75% | 434 | 17.3 | 56% | -413 | -93 | 42 | 0.55 | ok |
| 233 | b3 | carry_dip | GBPJPY | D1 | - | 0.75% | 188 | 7.5 | 40% | -443 | -96 | 47 | 0.51 | ok |
| 234 | b3 | carry_dip | NZDJPY | D1 | - | 0.75% | -285 | -11.4 | 12% | -331 | -115 | 11 | 0.27 | ok |
| 235 | b3 | carry_dip | USDJPY | D1 | - | 1.50% | 708 | 28.3 | 52% | -558 | -175 | 41 | 0.51 | ok |
| 236 | b3 | carry_dip_200 | AUDJPY | D1 | trend_n=200, dip_n=3 | 1.00% | 450 | 18.0 | 60% | -562 | -140 | 62 | 0.55 | ok |
| 237 | b3 | carry_dip_200 | CADJPY | D1 | trend_n=200, dip_n=3 | 1.25% | 339 | 13.6 | 52% | -598 | -176 | 58 | 0.55 | ok |
| 238 | b3 | carry_dip_200 | CHFJPY | D1 | trend_n=200, dip_n=3 | 1.00% | 638 | 25.5 | 60% | -584 | -129 | 57 | 0.56 | ok |
| 239 | b3 | carry_dip_200 | EURJPY | D1 | trend_n=200, dip_n=3 | 1.50% | 933 | 37.3 | 68% | -518 | -214 | 61 | 0.62 | ok |
| 240 | b3 | carry_dip_200 | GBPJPY | D1 | trend_n=200, dip_n=3 | 1.00% | 524 | 21.0 | 52% | -550 | -129 | 63 | 0.59 | ok |
| 241 | b3 | carry_dip_200 | NZDJPY | D1 | trend_n=200, dip_n=3 | 0.75% | -184 | -7.4 | 24% | -407 | -115 | 14 | 0.43 | ok |
| 242 | b3 | carry_dip_200 | USDJPY | D1 | trend_n=200, dip_n=3 | 1.00% | -99 | -4.0 | 48% | -567 | -146 | 64 | 0.55 | ok |
| 243 | b3 | carry_dip_trail | AUDJPY | D1 | tp=None, trail=3.0, max_hold=20 | 0.75% | 478 | 19.1 | 52% | -476 | -146 | 27 | 0.48 | ok |
| 244 | b3 | carry_dip_trail | CADJPY | D1 | tp=None, trail=3.0, max_hold=20 | 1.25% | 198 | 7.9 | 44% | -591 | -174 | 27 | 0.37 | ok |
| 245 | b3 | carry_dip_trail | CHFJPY | D1 | tp=None, trail=3.0, max_hold=20 | 0.75% | 701 | 28.0 | 52% | -449 | -89 | 28 | 0.54 | ok |
| 246 | b3 | carry_dip_trail | EURJPY | D1 | tp=None, trail=3.0, max_hold=20 | 0.75% | 179 | 7.2 | 52% | -469 | -107 | 27 | 0.37 | ok |
| 247 | b3 | carry_dip_trail | GBPJPY | D1 | tp=None, trail=3.0, max_hold=20 | 0.75% | -163 | -6.5 | 44% | -575 | -121 | 33 | 0.36 | ok |
| 248 | b3 | carry_dip_trail | NZDJPY | D1 | tp=None, trail=3.0, max_hold=20 | 0.75% | -342 | -13.7 | 12% | -433 | -115 | 9 | 0.22 | ok |
| 249 | b3 | carry_dip_trail | USDJPY | D1 | tp=None, trail=3.0, max_hold=20 | 1.25% | 515 | 20.6 | 44% | -566 | -197 | 28 | 0.39 | ok |
| 250 | b3 | donchian10_h4_long | AUDJPY | H4 | n=10, trail=2.5, side=long | 0.50% | 78 | 3.1 | 44% | -415 | -73 | 69 | 0.42 | ok |
| 251 | b3 | donchian10_h4_long | CADJPY | H4 | n=10, trail=2.5, side=long | 0.25% | -248 | -9.9 | 36% | -384 | -25 | 77 | 0.32 | ok |
| 252 | b3 | donchian10_h4_long | CHFJPY | H4 | n=10, trail=2.5, side=long | 0.25% | -31 | -1.2 | 56% | -301 | -29 | 73 | 0.38 | ok |
| 253 | b3 | donchian10_h4_long | EURJPY | H4 | n=10, trail=2.5, side=long | 0.50% | -129 | -5.2 | 52% | -427 | -64 | 77 | 0.39 | ok |
| 254 | b3 | donchian10_h4_long | GBPJPY | H4 | n=10, trail=2.5, side=long | 0.50% | -393 | -15.7 | 36% | -531 | -72 | 80 | 0.36 | ok |
| 255 | b3 | donchian10_h4_long | NZDJPY | H4 | n=10, trail=2.5, side=long | 0.50% | -451 | -18.0 | 20% | -579 | -60 | 50 | 0.36 | ok |
| 256 | b3 | donchian10_h4_long | USDJPY | H4 | n=10, trail=2.5, side=long | 0.50% | 107 | 4.3 | 52% | -592 | -72 | 79 | 0.42 | ok |
| 257 | b3 | donchian20_d1 | AUDJPY | D1 | n=20, trail=3.0 | 0.50% | -30 | -1.2 | 48% | -442 | -88 | 13 | 0.38 | ok |
| 258 | b3 | donchian20_d1 | CADJPY | D1 | n=20, trail=3.0 | 0.50% | -436 | -17.5 | 28% | -551 | -63 | 17 | 0.12 | ok |
| 259 | b3 | donchian20_d1 | CHFJPY | D1 | n=20, trail=3.0 | 1.00% | 374 | 15.0 | 52% | -513 | -83 | 10 | 0.40 | ok |
| 260 | b3 | donchian20_d1 | EURJPY | D1 | n=20, trail=3.0 | 0.75% | -248 | -9.9 | 32% | -517 | -102 | 16 | 0.19 | ok |
| 261 | b3 | donchian20_d1 | GBPJPY | D1 | n=20, trail=3.0 | 0.75% | -532 | -21.3 | 32% | -600 | -80 | 18 | 0.11 | ok |
| 262 | b3 | donchian20_d1 | NZDJPY | D1 | n=20, trail=3.0 | 1.00% | -236 | -9.4 | 12% | -304 | -106 | 5 | 0.20 | ok |
| 263 | b3 | donchian20_d1 | USDJPY | D1 | n=20, trail=3.0 | 0.75% | -89 | -3.6 | 40% | -501 | -92 | 14 | 0.29 | ok |
| 264 | b3 | donchian20_h4 | AUDJPY | H4 | - | none safe | -348 | -13.9 | 28% | -727 | -53 | 97 | 0.30 | ok |
| 265 | b3 | donchian20_h4 | CADJPY | H4 | - | none safe | -794 | -31.7 | 16% | -1019 | -59 | 101 | 0.24 | ok |
| 266 | b3 | donchian20_h4 | CHFJPY | H4 | - | none safe | -440 | -17.6 | 32% | -818 | -69 | 102 | 0.30 | ok |
| 267 | b3 | donchian20_h4 | EURJPY | H4 | - | none safe | -339 | -13.5 | 32% | -642 | -80 | 90 | 0.34 | ok |
| 268 | b3 | donchian20_h4 | GBPJPY | H4 | - | none safe | -530 | -21.2 | 36% | -760 | -61 | 101 | 0.28 | ok |
| 269 | b3 | donchian20_h4 | NZDJPY | H4 | - | 0.25% | 0 | 0.0 | 0% | 0 | 0 | 0 | 0.00 | ok |
| 270 | b3 | donchian20_h4 | USDJPY | H4 | - | 0.25% | -80 | -3.2 | 48% | -505 | -69 | 98 | 0.33 | ok |
| 271 | b3 | donchian55_h4 | AUDJPY | H4 | n=55, trail=4.0 | 0.25% | -464 | -18.6 | 28% | -464 | -58 | 54 | 0.28 | ok |
| 272 | b3 | donchian55_h4 | CADJPY | H4 | n=55, trail=4.0 | none safe | -702 | -28.1 | 28% | -814 | -69 | 57 | 0.21 | ok |
| 273 | b3 | donchian55_h4 | CHFJPY | H4 | n=55, trail=4.0 | 0.25% | -136 | -5.4 | 32% | -438 | -68 | 48 | 0.25 | ok |
| 274 | b3 | donchian55_h4 | EURJPY | H4 | n=55, trail=4.0 | 0.25% | -64 | -2.5 | 52% | -343 | -66 | 45 | 0.31 | ok |
| 275 | b3 | donchian55_h4 | GBPJPY | H4 | n=55, trail=4.0 | 0.25% | -274 | -11.0 | 36% | -501 | -61 | 47 | 0.28 | ok |
| 276 | b3 | donchian55_h4 | NZDJPY | H4 | n=55, trail=4.0 | 0.25% | 0 | 0.0 | 0% | 0 | 0 | 0 | 0.00 | ok |
| 277 | b3 | donchian55_h4 | USDJPY | H4 | n=55, trail=4.0 | 0.25% | -199 | -8.0 | 48% | -386 | -42 | 53 | 0.30 | ok |
| 278 | b3 | ema_pb_h1 | AUDJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -1779 | -71.1 | 16% | -1856 | -99 | 358 | 0.35 | ok |
| 279 | b3 | ema_pb_h1 | CADJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -2090 | -83.6 | 24% | -2171 | -74 | 360 | 0.33 | ok |
| 280 | b3 | ema_pb_h1 | CHFJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -1758 | -70.3 | 24% | -1920 | -96 | 357 | 0.34 | ok |
| 281 | b3 | ema_pb_h1 | EURJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -1577 | -63.1 | 28% | -1615 | -78 | 335 | 0.34 | ok |
| 282 | b3 | ema_pb_h1 | GBPJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -1944 | -77.8 | 24% | -2230 | -95 | 374 | 0.33 | ok |
| 283 | b3 | ema_pb_h1 | NZDJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -1425 | -57.0 | 28% | -1461 | -91 | 209 | 0.32 | ok |
| 284 | b3 | ema_pb_h1 | USDJPY | H1 | fast=20, slow=100, max_hold=48 | none safe | -279 | -11.2 | 44% | -705 | -103 | 306 | 0.39 | ok |
| 285 | b3 | ema_pb_h4 | AUDJPY | H4 | - | none safe | -738 | -29.5 | 28% | -738 | -78 | 115 | 0.29 | ok |
| 286 | b3 | ema_pb_h4 | CADJPY | H4 | - | none safe | -468 | -18.7 | 24% | -722 | -38 | 121 | 0.35 | ok |
| 287 | b3 | ema_pb_h4 | CHFJPY | H4 | - | 0.25% | -308 | -12.3 | 40% | -498 | -45 | 112 | 0.34 | ok |
| 288 | b3 | ema_pb_h4 | EURJPY | H4 | - | none safe | -284 | -11.4 | 40% | -663 | -69 | 119 | 0.34 | ok |
| 289 | b3 | ema_pb_h4 | GBPJPY | H4 | - | none safe | -829 | -33.2 | 28% | -897 | -58 | 119 | 0.27 | ok |
| 290 | b3 | ema_pb_h4 | NZDJPY | H4 | - | 0.25% | -305 | -12.2 | 32% | -362 | -49 | 48 | 0.29 | ok |
| 291 | b3 | ema_pb_h4 | USDJPY | H4 | - | 0.25% | -241 | -9.6 | 40% | -443 | -92 | 116 | 0.34 | ok |
| 292 | b3 | ema_pb_h4_r3 | AUDJPY | H4 | tp_r=3.0 | none safe | -637 | -25.5 | 28% | -639 | -78 | 104 | 0.24 | ok |
| 293 | b3 | ema_pb_h4_r3 | CADJPY | H4 | tp_r=3.0 | none safe | -269 | -10.8 | 36% | -601 | -65 | 108 | 0.30 | ok |
| 294 | b3 | ema_pb_h4_r3 | CHFJPY | H4 | tp_r=3.0 | 0.25% | -233 | -9.3 | 48% | -390 | -46 | 104 | 0.28 | ok |
| 295 | b3 | ema_pb_h4_r3 | EURJPY | H4 | tp_r=3.0 | none safe | -546 | -21.9 | 32% | -888 | -71 | 108 | 0.25 | ok |
| 296 | b3 | ema_pb_h4_r3 | GBPJPY | H4 | tp_r=3.0 | none safe | -794 | -31.8 | 32% | -850 | -64 | 109 | 0.23 | ok |
| 297 | b3 | ema_pb_h4_r3 | NZDJPY | H4 | tp_r=3.0 | 0.25% | -269 | -10.8 | 28% | -346 | -66 | 48 | 0.23 | ok |
| 298 | b3 | ema_pb_h4_r3 | USDJPY | H4 | tp_r=3.0 | 0.25% | -53 | -2.1 | 44% | -316 | -92 | 107 | 0.31 | ok |
| 299 | b3 | inside_break | AUDJPY | H1 | inside=True | 1.50% | 410 | 16.4 | 64% | -486 | -148 | 54 | 0.63 | ok |
| 300 | b3 | inside_break | CADJPY | H1 | inside=True | 0.75% | -454 | -18.2 | 28% | -528 | -75 | 48 | 0.50 | ok |
| 301 | b3 | inside_break | CHFJPY | H1 | inside=True | 2.00% | 89 | 3.6 | 32% | -551 | -198 | 44 | 0.45 | ok |
| 302 | b3 | inside_break | EURJPY | H1 | inside=True | 1.50% | -34 | -1.4 | 44% | -543 | -148 | 46 | 0.59 | ok |
| 303 | b3 | inside_break | GBPJPY | H1 | inside=True | 0.50% | -397 | -15.9 | 16% | -422 | -49 | 53 | 0.34 | ok |
| 304 | b3 | inside_break | NZDJPY | H1 | inside=True | 2.00% | 193 | 7.7 | 32% | -548 | -191 | 37 | 0.57 | ok |
| 305 | b3 | inside_break | USDJPY | H1 | inside=True | 2.00% | 236 | 9.4 | 40% | -577 | -200 | 53 | 0.62 | ok |
| 306 | b3 | nr4_break | AUDJPY | H1 | n=4 | 0.75% | -261 | -10.5 | 36% | -458 | -74 | 71 | 0.51 | ok |
| 307 | b3 | nr4_break | CADJPY | H1 | n=4 | 1.00% | -133 | -5.3 | 44% | -581 | -99 | 92 | 0.51 | ok |
| 308 | b3 | nr4_break | CHFJPY | H1 | n=4 | 1.50% | -214 | -8.6 | 44% | -450 | -149 | 78 | 0.47 | ok |
| 309 | b3 | nr4_break | EURJPY | H1 | n=4 | 1.00% | -37 | -1.5 | 40% | -541 | -99 | 88 | 0.58 | ok |
| 310 | b3 | nr4_break | GBPJPY | H1 | n=4 | 0.50% | -257 | -10.3 | 40% | -493 | -49 | 87 | 0.47 | ok |
| 311 | b3 | nr4_break | NZDJPY | H1 | n=4 | 1.50% | 635 | 25.4 | 52% | -462 | -127 | 64 | 0.59 | ok |
| 312 | b3 | nr4_break | USDJPY | H1 | n=4 | 2.00% | 859 | 34.3 | 52% | -552 | -198 | 82 | 0.65 | ok |
| 313 | b3 | nr7_break | AUDJPY | H1 | - | 1.25% | -290 | -11.6 | 32% | -528 | -125 | 44 | 0.52 | ok |
| 314 | b3 | nr7_break | CADJPY | H1 | - | 1.00% | -337 | -13.5 | 44% | -519 | -99 | 53 | 0.45 | ok |
| 315 | b3 | nr7_break | CHFJPY | H1 | - | 1.50% | -344 | -13.8 | 28% | -552 | -149 | 43 | 0.40 | ok |
| 316 | b3 | nr7_break | EURJPY | H1 | - | 1.50% | -77 | -3.1 | 44% | -559 | -148 | 54 | 0.59 | ok |
| 317 | b3 | nr7_break | GBPJPY | H1 | - | 0.75% | -351 | -14.0 | 40% | -591 | -74 | 54 | 0.44 | ok |
| 318 | b3 | nr7_break | NZDJPY | H1 | - | 2.00% | 397 | 15.9 | 52% | -544 | -139 | 38 | 0.63 | ok |
| 319 | b3 | nr7_break | USDJPY | H1 | - | 2.00% | 329 | 13.1 | 44% | -384 | -198 | 49 | 0.65 | ok |
| 320 | b3 | nr7_break_mid | AUDJPY | H1 | sl=mid, tp_mult=1.5 | 0.75% | -96 | -3.8 | 40% | -518 | -75 | 48 | 0.50 | ok |
| 321 | b3 | nr7_break_mid | CADJPY | H1 | sl=mid, tp_mult=1.5 | 0.50% | -353 | -14.1 | 40% | -561 | -50 | 53 | 0.38 | ok |
| 322 | b3 | nr7_break_mid | CHFJPY | H1 | sl=mid, tp_mult=1.5 | 0.75% | -43 | -1.7 | 32% | -450 | -76 | 45 | 0.42 | ok |
| 323 | b3 | nr7_break_mid | EURJPY | H1 | sl=mid, tp_mult=1.5 | 0.75% | -416 | -16.6 | 32% | -582 | -75 | 57 | 0.54 | ok |
| 324 | b3 | nr7_break_mid | GBPJPY | H1 | sl=mid, tp_mult=1.5 | 0.25% | -256 | -10.3 | 28% | -412 | -25 | 55 | 0.40 | ok |
| 325 | b3 | nr7_break_mid | NZDJPY | H1 | sl=mid, tp_mult=1.5 | 1.00% | 329 | 13.2 | 52% | -532 | -100 | 41 | 0.59 | ok |
| 326 | b3 | nr7_break_mid | USDJPY | H1 | sl=mid, tp_mult=1.5 | 0.75% | 140 | 5.6 | 48% | -459 | -121 | 53 | 0.58 | ok |
| 327 | b3 | pdh_break | AUDJPY | H1 | - | none safe | -380 | -15.2 | 48% | -694 | -25 | 244 | 0.47 | ok |
| 328 | b3 | pdh_break | CADJPY | H1 | - | none safe | -600 | -24.0 | 40% | -708 | -25 | 256 | 0.42 | ok |
| 329 | b3 | pdh_break | CHFJPY | H1 | - | none safe | -466 | -18.6 | 36% | -668 | -25 | 249 | 0.43 | ok |
| 330 | b3 | pdh_break | EURJPY | H1 | - | 0.50% | -395 | -15.8 | 44% | -594 | -87 | 253 | 0.49 | ok |
| 331 | b3 | pdh_break | GBPJPY | H1 | - | 0.25% | -309 | -12.4 | 52% | -532 | -34 | 260 | 0.43 | ok |
| 332 | b3 | pdh_break | NZDJPY | H1 | - | 0.25% | -28 | -1.1 | 8% | -62 | -25 | 13 | 0.38 | ok |
| 333 | b3 | pdh_break | USDJPY | H1 | - | 0.50% | -289 | -11.6 | 56% | -457 | -103 | 262 | 0.51 | ok |
| 334 | b3 | pdh_break_tp1.5 | AUDJPY | H1 | tp_atr=1.5, sl_atr=0.5 | none safe | -406 | -16.2 | 36% | -627 | -24 | 244 | 0.46 | ok |
| 335 | b3 | pdh_break_tp1.5 | CADJPY | H1 | tp_atr=1.5, sl_atr=0.5 | none safe | -514 | -20.6 | 32% | -637 | -25 | 254 | 0.42 | ok |
| 336 | b3 | pdh_break_tp1.5 | CHFJPY | H1 | tp_atr=1.5, sl_atr=0.5 | 0.25% | -357 | -14.3 | 44% | -508 | -25 | 248 | 0.44 | ok |
| 337 | b3 | pdh_break_tp1.5 | EURJPY | H1 | tp_atr=1.5, sl_atr=0.5 | 0.50% | -557 | -22.3 | 40% | -593 | -73 | 253 | 0.49 | ok |
| 338 | b3 | pdh_break_tp1.5 | GBPJPY | H1 | tp_atr=1.5, sl_atr=0.5 | 0.25% | -232 | -9.3 | 52% | -429 | -35 | 259 | 0.43 | ok |
| 339 | b3 | pdh_break_tp1.5 | NZDJPY | H1 | tp_atr=1.5, sl_atr=0.5 | 0.25% | 0 | 0.0 | 0% | 0 | 0 | 0 | 0.00 | ok |
| 340 | b3 | pdh_break_tp1.5 | USDJPY | H1 | tp_atr=1.5, sl_atr=0.5 | 0.50% | -221 | -8.8 | 52% | -437 | -87 | 262 | 0.51 | ok |
| 341 | b4 | london_fade | AUDJPY | H1 | - | 1.50% | -99 | -4.0 | 32% | -518 | -150 | 31 | 0.55 | ok |
| 342 | b4 | london_fade | CADJPY | H1 | - | 0.50% | -289 | -11.5 | 32% | -469 | -49 | 40 | 0.45 | ok |
| 343 | b4 | london_fade | CHFJPY | H1 | - | 0.50% | -483 | -19.3 | 24% | -561 | -50 | 57 | 0.42 | ok |
| 344 | b4 | london_fade | EURJPY | H1 | - | 1.00% | -47 | -1.9 | 44% | -593 | -101 | 46 | 0.57 | ok |
| 345 | b4 | london_fade | GBPJPY | H1 | - | 1.00% | 59 | 2.3 | 32% | -526 | -99 | 52 | 0.52 | ok |
| 346 | b4 | london_fade | NZDJPY | H1 | - | 0.75% | -218 | -8.7 | 32% | -527 | -76 | 25 | 0.52 | ok |
| 347 | b4 | london_fade | USDJPY | H1 | - | 0.25% | -160 | -6.4 | 36% | -306 | -25 | 46 | 0.48 | ok |
| 348 | b4 | london_fade_k0.8 | AUDJPY | H1 | k=0.8, sl_atr=0.4 | 2.00% | 454 | 18.2 | 28% | -522 | -200 | 14 | 0.57 | ok |
| 349 | b4 | london_fade_k0.8 | CADJPY | H1 | k=0.8, sl_atr=0.4 | 0.50% | -459 | -18.4 | 12% | -579 | -51 | 19 | 0.26 | ok |
| 350 | b4 | london_fade_k0.8 | CHFJPY | H1 | k=0.8, sl_atr=0.4 | 0.75% | -343 | -13.7 | 20% | -463 | -74 | 22 | 0.36 | ok |
| 351 | b4 | london_fade_k0.8 | EURJPY | H1 | k=0.8, sl_atr=0.4 | 2.00% | 864 | 34.6 | 32% | -500 | -198 | 20 | 0.65 | ok |
| 352 | b4 | london_fade_k0.8 | GBPJPY | H1 | k=0.8, sl_atr=0.4 | 0.75% | -84 | -3.3 | 28% | -457 | -75 | 23 | 0.43 | ok |
| 353 | b4 | london_fade_k0.8 | NZDJPY | H1 | k=0.8, sl_atr=0.4 | 1.50% | -2 | -0.1 | 16% | -502 | -148 | 9 | 0.56 | ok |
| 354 | b4 | london_fade_k0.8 | USDJPY | H1 | k=0.8, sl_atr=0.4 | 0.50% | -329 | -13.2 | 24% | -549 | -50 | 23 | 0.35 | ok |
| 355 | b4 | london_follow | AUDJPY | H1 | mode=follow | 1.00% | -428 | -17.1 | 40% | -506 | -99 | 31 | 0.48 | ok |
| 356 | b4 | london_follow | CADJPY | H1 | mode=follow | 0.75% | -461 | -18.4 | 24% | -495 | -75 | 40 | 0.40 | ok |
| 357 | b4 | london_follow | CHFJPY | H1 | mode=follow | 0.75% | -326 | -13.0 | 40% | -455 | -74 | 57 | 0.42 | ok |
| 358 | b4 | london_follow | EURJPY | H1 | mode=follow | 0.50% | -414 | -16.6 | 32% | -435 | -50 | 46 | 0.37 | ok |
| 359 | b4 | london_follow | GBPJPY | H1 | mode=follow | 0.50% | -384 | -15.3 | 48% | -431 | -50 | 52 | 0.40 | ok |
| 360 | b4 | london_follow | NZDJPY | H1 | mode=follow | 0.75% | -414 | -16.5 | 28% | -454 | -75 | 25 | 0.48 | ok |
| 361 | b4 | london_follow | USDJPY | H1 | mode=follow | 0.75% | -23 | -0.9 | 36% | -561 | -74 | 46 | 0.54 | ok |
| 362 | b4 | post_fix_short | AUDJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.25% | -227 | -9.1 | 40% | -380 | -25 | 139 | 0.45 | ok |
| 363 | b4 | post_fix_short | CADJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.25% | -284 | -11.3 | 32% | -418 | -25 | 139 | 0.37 | ok |
| 364 | b4 | post_fix_short | CHFJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.50% | -253 | -10.1 | 44% | -530 | -50 | 139 | 0.42 | ok |
| 365 | b4 | post_fix_short | EURJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.50% | -38 | -1.5 | 60% | -577 | -49 | 139 | 0.42 | ok |
| 366 | b4 | post_fix_short | GBPJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.50% | -54 | -2.1 | 48% | -514 | -50 | 139 | 0.42 | ok |
| 367 | b4 | post_fix_short | NZDJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.25% | -254 | -10.2 | 16% | -305 | -25 | 63 | 0.30 | ok |
| 368 | b4 | post_fix_short | USDJPY | H1 | entry_h=2.0, exit_h=5, side=short | 0.25% | -147 | -5.9 | 36% | -364 | -25 | 139 | 0.41 | ok |
| 369 | b4 | post_fix_short_all | AUDJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -1270 | -50.8 | 16% | -1307 | -25 | 506 | 0.41 | ok |
| 370 | b4 | post_fix_short_all | CADJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -1413 | -56.5 | 8% | -1429 | -25 | 506 | 0.37 | ok |
| 371 | b4 | post_fix_short_all | CHFJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -1060 | -42.4 | 20% | -1083 | -25 | 506 | 0.39 | ok |
| 372 | b4 | post_fix_short_all | EURJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -857 | -34.3 | 40% | -974 | -25 | 506 | 0.39 | ok |
| 373 | b4 | post_fix_short_all | GBPJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -786 | -31.5 | 28% | -841 | -25 | 506 | 0.40 | ok |
| 374 | b4 | post_fix_short_all | NZDJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -810 | -32.4 | 12% | -880 | -25 | 217 | 0.34 | ok |
| 375 | b4 | post_fix_short_all | USDJPY | H1 | entry_h=2.0, exit_h=5, side=short, gotobi_only=False | none safe | -776 | -31.0 | 32% | -945 | -25 | 506 | 0.42 | ok |
| 376 | b4 | post_fix_short_m30 | AUDJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.25% | -179 | -7.2 | 40% | -331 | -25 | 139 | 0.39 | ok |
| 377 | b4 | post_fix_short_m30 | CADJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.25% | -285 | -11.4 | 32% | -397 | -25 | 139 | 0.38 | ok |
| 378 | b4 | post_fix_short_m30 | CHFJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.50% | -319 | -12.8 | 28% | -546 | -50 | 139 | 0.42 | ok |
| 379 | b4 | post_fix_short_m30 | EURJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.50% | -44 | -1.7 | 56% | -509 | -49 | 139 | 0.42 | ok |
| 380 | b4 | post_fix_short_m30 | GBPJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.50% | -38 | -1.5 | 60% | -459 | -50 | 139 | 0.41 | ok |
| 381 | b4 | post_fix_short_m30 | NZDJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.25% | -208 | -8.3 | 20% | -311 | -25 | 70 | 0.30 | ok |
| 382 | b4 | post_fix_short_m30 | USDJPY | M30 | entry_h=2.5, exit_h=5, side=short | 0.25% | -124 | -4.9 | 44% | -308 | -25 | 139 | 0.42 | ok |
| 383 | b4 | preopen_long | AUDJPY | H1 | entry_h=0.0, exit_h=1, side=long | none safe | -660 | -26.4 | 24% | -686 | -25 | 509 | 0.35 | ok |
| 384 | b4 | preopen_long | CADJPY | H1 | entry_h=0.0, exit_h=1, side=long | none safe | -952 | -38.1 | 8% | -952 | -25 | 509 | 0.29 | ok |
| 385 | b4 | preopen_long | CHFJPY | H1 | entry_h=0.0, exit_h=1, side=long | 0.25% | -475 | -19.0 | 40% | -570 | -20 | 509 | 0.44 | ok |
| 386 | b4 | preopen_long | EURJPY | H1 | entry_h=0.0, exit_h=1, side=long | 0.25% | -534 | -21.4 | 32% | -563 | -24 | 509 | 0.38 | ok |
| 387 | b4 | preopen_long | GBPJPY | H1 | entry_h=0.0, exit_h=1, side=long | 0.25% | -457 | -18.3 | 32% | -517 | -25 | 509 | 0.38 | ok |
| 388 | b4 | preopen_long | NZDJPY | H1 | entry_h=0.0, exit_h=1, side=long | 0.25% | -187 | -7.5 | 16% | -270 | -23 | 138 | 0.35 | ok |
| 389 | b4 | preopen_long | USDJPY | H1 | entry_h=0.0, exit_h=1, side=long | 0.25% | -410 | -16.4 | 24% | -410 | -23 | 509 | 0.43 | ok |
| 390 | b4 | preopen_long_m30 | AUDJPY | M30 | entry_h=0.5, exit_h=1, side=long | none safe | -1062 | -42.5 | 8% | -1065 | -23 | 509 | 0.25 | ok |
| 391 | b4 | preopen_long_m30 | CADJPY | M30 | entry_h=0.5, exit_h=1, side=long | none safe | -1267 | -50.7 | 0% | -1268 | -23 | 509 | 0.25 | ok |
| 392 | b4 | preopen_long_m30 | CHFJPY | M30 | entry_h=0.5, exit_h=1, side=long | none safe | -1333 | -53.3 | 4% | -1334 | -15 | 495 | 0.21 | ok |
| 393 | b4 | preopen_long_m30 | EURJPY | M30 | entry_h=0.5, exit_h=1, side=long | none safe | -589 | -23.6 | 8% | -602 | -24 | 509 | 0.31 | ok |
| 394 | b4 | preopen_long_m30 | GBPJPY | M30 | entry_h=0.5, exit_h=1, side=long | none safe | -715 | -28.6 | 16% | -732 | -25 | 509 | 0.28 | ok |
| 395 | b4 | preopen_long_m30 | NZDJPY | M30 | entry_h=0.5, exit_h=1, side=long | 0.25% | -297 | -11.9 | 8% | -297 | -12 | 145 | 0.27 | ok |
| 396 | b4 | preopen_long_m30 | USDJPY | M30 | entry_h=0.5, exit_h=1, side=long | 0.25% | -268 | -10.7 | 32% | -296 | -23 | 508 | 0.41 | ok |
| 397 | b4 | preopen_long_m30b | AUDJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1500 | -60.0 | 0% | -1500 | -25 | 508 | 0.16 | ok |
| 398 | b4 | preopen_long_m30b | CADJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1734 | -69.4 | 0% | -1734 | -24 | 508 | 0.12 | ok |
| 399 | b4 | preopen_long_m30b | CHFJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1532 | -61.3 | 0% | -1532 | -22 | 508 | 0.13 | ok |
| 400 | b4 | preopen_long_m30b | EURJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1172 | -46.9 | 0% | -1172 | -24 | 508 | 0.18 | ok |
| 401 | b4 | preopen_long_m30b | GBPJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1076 | -43.0 | 0% | -1076 | -21 | 508 | 0.20 | ok |
| 402 | b4 | preopen_long_m30b | NZDJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -775 | -31.0 | 4% | -775 | -24 | 241 | 0.11 | ok |
| 403 | b4 | preopen_long_m30b | USDJPY | M30 | entry_h=1.0, exit_h=1, side=long | none safe | -1014 | -40.6 | 0% | -1014 | -25 | 508 | 0.24 | ok |
| 404 | b4 | pwh_sweep_h1 | AUDJPY | H1 | max_hold=48 | none safe | -693 | -27.7 | 24% | -764 | -40 | 93 | 0.31 | ok |
| 405 | b4 | pwh_sweep_h1 | CADJPY | H1 | max_hold=48 | 0.25% | -282 | -11.3 | 44% | -413 | -56 | 89 | 0.39 | ok |
| 406 | b4 | pwh_sweep_h1 | CHFJPY | H1 | max_hold=48 | 0.50% | -117 | -4.7 | 40% | -552 | -77 | 87 | 0.41 | ok |
| 407 | b4 | pwh_sweep_h1 | EURJPY | H1 | max_hold=48 | 0.25% | -227 | -9.1 | 44% | -539 | -52 | 90 | 0.36 | ok |
| 408 | b4 | pwh_sweep_h1 | GBPJPY | H1 | max_hold=48 | 0.25% | -143 | -5.7 | 44% | -370 | -51 | 85 | 0.41 | ok |
| 409 | b4 | pwh_sweep_h1 | NZDJPY | H1 | max_hold=48 | 0.25% | -310 | -12.4 | 8% | -336 | -54 | 29 | 0.24 | ok |
| 410 | b4 | pwh_sweep_h1 | USDJPY | H1 | max_hold=48 | 0.50% | 179 | 7.1 | 48% | -441 | -83 | 87 | 0.41 | ok |
| 411 | b4 | pwh_sweep_h4 | AUDJPY | H4 | - | none safe | -544 | -21.8 | 28% | -671 | -42 | 88 | 0.32 | ok |
| 412 | b4 | pwh_sweep_h4 | CADJPY | H4 | - | 0.25% | -52 | -2.1 | 64% | -293 | -56 | 82 | 0.45 | ok |
| 413 | b4 | pwh_sweep_h4 | CHFJPY | H4 | - | 0.25% | -189 | -7.6 | 44% | -381 | -39 | 80 | 0.39 | ok |
| 414 | b4 | pwh_sweep_h4 | EURJPY | H4 | - | 0.50% | -120 | -4.8 | 44% | -593 | -100 | 83 | 0.42 | ok |
| 415 | b4 | pwh_sweep_h4 | GBPJPY | H4 | - | 0.50% | 233 | 9.3 | 52% | -472 | -109 | 79 | 0.46 | ok |
| 416 | b4 | pwh_sweep_h4 | NZDJPY | H4 | - | 0.25% | 99 | 4.0 | 24% | -97 | -50 | 15 | 0.53 | ok |
| 417 | b4 | pwh_sweep_h4 | USDJPY | H4 | - | 0.75% | 477 | 19.1 | 56% | -578 | -169 | 82 | 0.45 | ok |
| 418 | b4 | pwh_sweep_h4_wc | AUDJPY | H4 | tp=wc | none safe | -543 | -21.7 | 32% | -668 | -42 | 76 | 0.36 | ok |
| 419 | b4 | pwh_sweep_h4_wc | CADJPY | H4 | tp=wc | 0.25% | -199 | -8.0 | 32% | -300 | -56 | 72 | 0.46 | ok |
| 420 | b4 | pwh_sweep_h4_wc | CHFJPY | H4 | tp=wc | 0.25% | -210 | -8.4 | 44% | -401 | -45 | 69 | 0.48 | ok |
| 421 | b4 | pwh_sweep_h4_wc | EURJPY | H4 | tp=wc | 0.25% | -173 | -6.9 | 40% | -347 | -44 | 75 | 0.52 | ok |
| 422 | b4 | pwh_sweep_h4_wc | GBPJPY | H4 | tp=wc | 0.75% | 906 | 36.2 | 76% | -568 | -149 | 69 | 0.67 | ok |
| 423 | b4 | pwh_sweep_h4_wc | NZDJPY | H4 | tp=wc | 0.25% | 30 | 1.2 | 28% | -100 | -27 | 15 | 0.67 | ok |
| 424 | b4 | pwh_sweep_h4_wc | USDJPY | H4 | tp=wc | 0.50% | -199 | -8.0 | 44% | -424 | -74 | 75 | 0.52 | ok |
| 425 | b4 | rollover_short | AUDJPY | H1 | - | 0.75% | 1187 | 47.5 | 60% | -575 | -290 | 508 | 0.58 | ok |
| 426 | b4 | rollover_short | CADJPY | H1 | - | 0.50% | 171 | 6.8 | 60% | -367 | -222 | 508 | 0.52 | ok |
| 427 | b4 | rollover_short | CHFJPY | H1 | - | 0.50% | 1511 | 60.4 | 64% | -515 | -257 | 508 | 0.67 | ok |
| 428 | b4 | rollover_short | EURJPY | H1 | - | 0.50% | 264 | 10.6 | 56% | -574 | -264 | 508 | 0.54 | ok |
| 429 | b4 | rollover_short | GBPJPY | H1 | - | 0.50% | 1971 | 78.9 | 76% | -237 | -237 | 508 | 0.67 | ok |
| 430 | b4 | rollover_short | NZDJPY | H1 | - | 0.50% | -226 | -9.0 | 60% | -583 | -175 | 480 | 0.49 | ok |
| 431 | b4 | rollover_short | USDJPY | H1 | - | 0.50% | -49 | -2.0 | 44% | -465 | -208 | 508 | 0.51 | ok |
| 432 | b4 | rollover_short_23 | AUDJPY | H1 | entry_h=23.0, exit_h=0 | none safe | -942 | -37.7 | 20% | -961 | -89 | 500 | 0.33 | ok |
| 433 | b4 | rollover_short_23 | CADJPY | H1 | entry_h=23.0, exit_h=0 | none safe | -1160 | -46.4 | 20% | -1161 | -104 | 500 | 0.25 | ok |
| 434 | b4 | rollover_short_23 | CHFJPY | H1 | entry_h=23.0, exit_h=0 | none safe | -759 | -30.4 | 40% | -927 | -116 | 500 | 0.47 | ok |
| 435 | b4 | rollover_short_23 | EURJPY | H1 | entry_h=23.0, exit_h=0 | 0.25% | -415 | -16.6 | 36% | -512 | -127 | 500 | 0.41 | ok |
| 436 | b4 | rollover_short_23 | GBPJPY | H1 | entry_h=23.0, exit_h=0 | 0.50% | 519 | 20.8 | 60% | -424 | -225 | 500 | 0.56 | ok |
| 437 | b4 | rollover_short_23 | NZDJPY | H1 | entry_h=23.0, exit_h=0 | none safe | -1192 | -47.7 | 0% | -1197 | -83 | 214 | 0.13 | ok |
| 438 | b4 | rollover_short_23 | USDJPY | H1 | entry_h=23.0, exit_h=0 | 0.25% | -537 | -21.5 | 24% | -537 | -94 | 500 | 0.36 | ok |
| 439 | b4 | rollover_short_m30 | AUDJPY | M30 | entry_h=23.0, exit_h=0 | 0.25% | 129 | 5.2 | 52% | -349 | -94 | 500 | 0.53 | ok |
| 440 | b4 | rollover_short_m30 | CADJPY | M30 | entry_h=23.0, exit_h=0 | 0.25% | -324 | -13.0 | 48% | -499 | -112 | 500 | 0.44 | ok |
| 441 | b4 | rollover_short_m30 | CHFJPY | M30 | entry_h=23.0, exit_h=0 | 0.25% | 328 | 13.1 | 52% | -549 | -122 | 500 | 0.58 | ok |
| 442 | b4 | rollover_short_m30 | EURJPY | M30 | entry_h=23.0, exit_h=0 | 0.25% | -26 | -1.0 | 56% | -470 | -120 | 500 | 0.48 | ok |
| 443 | b4 | rollover_short_m30 | GBPJPY | M30 | entry_h=23.0, exit_h=0 | 0.25% | 500 | 20.0 | 60% | -312 | -113 | 500 | 0.60 | ok |
| 444 | b4 | rollover_short_m30 | NZDJPY | M30 | entry_h=23.0, exit_h=0 | 0.50% | 36 | 1.5 | 64% | -457 | -175 | 498 | 0.47 | ok |
| 445 | b4 | rollover_short_m30 | USDJPY | M30 | entry_h=23.0, exit_h=0 | 0.50% | -232 | -9.3 | 40% | -517 | -208 | 500 | 0.46 | ok |
| 446 | b4 | round_number_05 | AUDJPY | H1 | step=0.5 | none safe | -3303 | -132.1 | 8% | -3399 | -105 | 754 | 0.36 | ok |
| 447 | b4 | round_number_05 | CADJPY | H1 | step=0.5 | none safe | -3154 | -126.1 | 16% | -3348 | -82 | 756 | 0.38 | ok |
| 448 | b4 | round_number_05 | CHFJPY | H1 | step=0.5 | none safe | -3142 | -125.7 | 20% | -3507 | -99 | 1075 | 0.42 | ok |
| 449 | b4 | round_number_05 | EURJPY | H1 | step=0.5 | none safe | -1107 | -44.3 | 36% | -1288 | -78 | 981 | 0.45 | ok |
| 450 | b4 | round_number_05 | GBPJPY | H1 | step=0.5 | none safe | -1841 | -73.6 | 24% | -2109 | -77 | 1226 | 0.44 | ok |
| 451 | b4 | round_number_05 | NZDJPY | H1 | step=0.5 | none safe | -1286 | -51.5 | 12% | -1360 | -122 | 369 | 0.36 | ok |
| 452 | b4 | round_number_05 | USDJPY | H1 | step=0.5 | none safe | -2152 | -86.1 | 36% | -2649 | -87 | 935 | 0.41 | ok |
| 453 | b4 | round_number_1 | AUDJPY | H1 | - | none safe | -1911 | -76.4 | 4% | -1957 | -90 | 371 | 0.34 | ok |
| 454 | b4 | round_number_1 | CADJPY | H1 | - | none safe | -1469 | -58.8 | 28% | -1562 | -64 | 401 | 0.39 | ok |
| 455 | b4 | round_number_1 | CHFJPY | H1 | - | none safe | -1301 | -52.1 | 44% | -1635 | -86 | 551 | 0.40 | ok |
| 456 | b4 | round_number_1 | EURJPY | H1 | - | none safe | -649 | -25.9 | 36% | -907 | -59 | 491 | 0.43 | ok |
| 457 | b4 | round_number_1 | GBPJPY | H1 | - | none safe | -1605 | -64.2 | 16% | -1822 | -81 | 653 | 0.40 | ok |
| 458 | b4 | round_number_1 | NZDJPY | H1 | - | 0.25% | -350 | -14.0 | 36% | -475 | -91 | 181 | 0.39 | ok |
| 459 | b4 | round_number_1 | USDJPY | H1 | - | none safe | -1362 | -54.5 | 28% | -1554 | -68 | 491 | 0.37 | ok |
| 460 | b4 | round_number_m30 | AUDJPY | M30 | step=0.5, max_hold=16 | none safe | -4415 | -176.6 | 0% | -4456 | -96 | 1009 | 0.32 | ok |
| 461 | b4 | round_number_m30 | CADJPY | M30 | step=0.5, max_hold=16 | none safe | -3647 | -145.9 | 20% | -3917 | -94 | 955 | 0.36 | ok |
| 462 | b4 | round_number_m30 | CHFJPY | M30 | step=0.5, max_hold=16 | none safe | -4383 | -175.3 | 4% | -4433 | -94 | 1393 | 0.37 | ok |
| 463 | b4 | round_number_m30 | EURJPY | M30 | step=0.5, max_hold=16 | none safe | -2245 | -89.8 | 20% | -2314 | -129 | 1282 | 0.39 | ok |
| 464 | b4 | round_number_m30 | GBPJPY | M30 | step=0.5, max_hold=16 | none safe | -2975 | -119.0 | 12% | -3176 | -133 | 1637 | 0.41 | ok |
| 465 | b4 | round_number_m30 | NZDJPY | M30 | step=0.5, max_hold=16 | none safe | -2885 | -115.4 | 4% | -2930 | -134 | 588 | 0.30 | ok |
| 466 | b4 | round_number_m30 | USDJPY | M30 | step=0.5, max_hold=16 | none safe | -2945 | -117.8 | 20% | -3115 | -132 | 1167 | 0.38 | ok |
| 467 | b4 | tokyo_fix_long | AUDJPY | H1 | - | 0.50% | -467 | -18.7 | 28% | -568 | -48 | 140 | 0.41 | ok |
| 468 | b4 | tokyo_fix_long | CADJPY | H1 | - | 0.25% | -275 | -11.0 | 32% | -304 | -24 | 140 | 0.33 | ok |
| 469 | b4 | tokyo_fix_long | CHFJPY | H1 | - | 0.75% | -337 | -13.5 | 36% | -579 | -73 | 140 | 0.43 | ok |
| 470 | b4 | tokyo_fix_long | EURJPY | H1 | - | 0.50% | -380 | -15.2 | 40% | -509 | -50 | 140 | 0.37 | ok |
| 471 | b4 | tokyo_fix_long | GBPJPY | H1 | - | 0.50% | -282 | -11.3 | 56% | -464 | -48 | 140 | 0.45 | ok |
| 472 | b4 | tokyo_fix_long | NZDJPY | H1 | - | 0.50% | -542 | -21.7 | 24% | -586 | -48 | 131 | 0.36 | ok |
| 473 | b4 | tokyo_fix_long | USDJPY | H1 | - | 0.50% | -322 | -12.9 | 40% | -418 | -49 | 140 | 0.44 | ok |
| 474 | b4 | tokyo_fix_long_all | AUDJPY | H1 | gotobi_only=False | none safe | -710 | -28.4 | 24% | -728 | -25 | 509 | 0.42 | ok |
| 475 | b4 | tokyo_fix_long_all | CADJPY | H1 | gotobi_only=False | none safe | -899 | -36.0 | 16% | -960 | -25 | 509 | 0.35 | ok |
| 476 | b4 | tokyo_fix_long_all | CHFJPY | H1 | gotobi_only=False | 0.25% | -235 | -9.4 | 40% | -491 | -24 | 509 | 0.47 | ok |
| 477 | b4 | tokyo_fix_long_all | EURJPY | H1 | gotobi_only=False | none safe | -500 | -20.0 | 36% | -613 | -25 | 509 | 0.44 | ok |
| 478 | b4 | tokyo_fix_long_all | GBPJPY | H1 | gotobi_only=False | 0.25% | -339 | -13.6 | 40% | -518 | -25 | 509 | 0.45 | ok |
| 479 | b4 | tokyo_fix_long_all | NZDJPY | H1 | gotobi_only=False | 0.25% | -179 | -7.1 | 16% | -299 | -23 | 138 | 0.43 | ok |
| 480 | b4 | tokyo_fix_long_all | USDJPY | H1 | gotobi_only=False | 0.25% | -434 | -17.4 | 40% | -553 | -25 | 509 | 0.47 | ok |
| 481 | b5 | london_fakeout | AUDJPY | H1 | - | 0.75% | 26 | 1.1 | 24% | -478 | -75 | 22 | 0.41 | ok |
| 482 | b5 | london_fakeout | CADJPY | H1 | - | 1.25% | -230 | -9.2 | 28% | -533 | -125 | 22 | 0.41 | ok |
| 483 | b5 | london_fakeout | CHFJPY | H1 | - | 0.25% | -146 | -5.8 | 32% | -325 | -25 | 35 | 0.37 | ok |
| 484 | b5 | london_fakeout | EURJPY | H1 | - | 0.25% | -267 | -10.7 | 28% | -343 | -30 | 39 | 0.31 | ok |
| 485 | b5 | london_fakeout | GBPJPY | H1 | - | 1.00% | -259 | -10.4 | 36% | -486 | -100 | 44 | 0.39 | ok |
| 486 | b5 | london_fakeout | NZDJPY | H1 | - | 0.50% | -393 | -15.7 | 20% | -468 | -50 | 19 | 0.32 | ok |
| 487 | b5 | london_fakeout | USDJPY | H1 | - | 0.50% | -372 | -14.9 | 20% | -599 | -50 | 27 | 0.37 | ok |
| 488 | b5 | london_fakeout_m30 | AUDJPY | M30 | k=0.25, exit_h=14 | 0.50% | -446 | -17.8 | 12% | -464 | -50 | 18 | 0.22 | ok |
| 489 | b5 | london_fakeout_m30 | CADJPY | M30 | k=0.25, exit_h=14 | 0.50% | -368 | -14.7 | 32% | -464 | -50 | 29 | 0.41 | ok |
| 490 | b5 | london_fakeout_m30 | CHFJPY | M30 | k=0.25, exit_h=14 | 2.00% | 8 | 0.3 | 24% | -576 | -200 | 20 | 0.50 | ok |
| 491 | b5 | london_fakeout_m30 | EURJPY | M30 | k=0.25, exit_h=14 | 0.50% | -474 | -18.9 | 28% | -476 | -50 | 35 | 0.34 | ok |
| 492 | b5 | london_fakeout_m30 | GBPJPY | M30 | k=0.25, exit_h=14 | 0.50% | -370 | -14.8 | 48% | -456 | -50 | 46 | 0.41 | ok |
| 493 | b5 | london_fakeout_m30 | NZDJPY | M30 | k=0.25, exit_h=14 | 0.50% | -388 | -15.5 | 20% | -459 | -50 | 20 | 0.30 | ok |
| 494 | b5 | london_fakeout_m30 | USDJPY | M30 | k=0.25, exit_h=14 | 1.25% | -25 | -1.0 | 36% | -573 | -125 | 25 | 0.52 | ok |
| 495 | b5 | london_fakeout_tokyo | AUDJPY | H1 | tp=tokyo, k=0.3 | 0.50% | -500 | -20.0 | 24% | -527 | -50 | 34 | 0.32 | ok |
| 496 | b5 | london_fakeout_tokyo | CADJPY | H1 | tp=tokyo, k=0.3 | 0.50% | -327 | -13.1 | 24% | -398 | -50 | 34 | 0.38 | ok |
| 497 | b5 | london_fakeout_tokyo | CHFJPY | H1 | tp=tokyo, k=0.3 | 0.50% | -111 | -4.4 | 40% | -426 | -50 | 45 | 0.47 | ok |
| 498 | b5 | london_fakeout_tokyo | EURJPY | H1 | tp=tokyo, k=0.3 | 0.25% | -374 | -15.0 | 16% | -377 | -30 | 49 | 0.31 | ok |
| 499 | b5 | london_fakeout_tokyo | GBPJPY | H1 | tp=tokyo, k=0.3 | 0.50% | -355 | -14.2 | 36% | -419 | -50 | 54 | 0.39 | ok |
| 500 | b5 | london_fakeout_tokyo | NZDJPY | H1 | tp=tokyo, k=0.3 | 0.75% | -480 | -19.2 | 32% | -531 | -75 | 27 | 0.37 | ok |
| 501 | b5 | london_fakeout_tokyo | USDJPY | H1 | tp=tokyo, k=0.3 | 0.50% | -264 | -10.5 | 28% | -432 | -50 | 38 | 0.39 | ok |
| 502 | b5 | ny_fade | AUDJPY | H1 | mode=fade | 0.25% | -211 | -8.4 | 40% | -330 | -25 | 170 | 0.49 | ok |
| 503 | b5 | ny_fade | CADJPY | H1 | mode=fade | 0.25% | -278 | -11.1 | 24% | -382 | -25 | 162 | 0.48 | ok |
| 504 | b5 | ny_fade | CHFJPY | H1 | mode=fade | 0.25% | -423 | -16.9 | 28% | -433 | -25 | 175 | 0.39 | ok |
| 505 | b5 | ny_fade | EURJPY | H1 | mode=fade | 0.25% | -309 | -12.4 | 36% | -351 | -25 | 170 | 0.45 | ok |
| 506 | b5 | ny_fade | GBPJPY | H1 | mode=fade | 0.50% | -364 | -14.6 | 44% | -545 | -50 | 168 | 0.50 | ok |
| 507 | b5 | ny_fade | NZDJPY | H1 | mode=fade | 0.25% | -147 | -5.9 | 4% | -159 | -25 | 14 | 0.21 | ok |
| 508 | b5 | ny_fade | USDJPY | H1 | mode=fade | 0.25% | -170 | -6.8 | 28% | -298 | -25 | 165 | 0.48 | ok |
| 509 | b5 | ny_follow | AUDJPY | H1 | - | 0.25% | -543 | -21.7 | 28% | -568 | -25 | 170 | 0.38 | ok |
| 510 | b5 | ny_follow | CADJPY | H1 | - | 0.25% | -527 | -21.1 | 20% | -562 | -25 | 162 | 0.33 | ok |
| 511 | b5 | ny_follow | CHFJPY | H1 | - | 0.25% | -293 | -11.7 | 28% | -516 | -28 | 175 | 0.50 | ok |
| 512 | b5 | ny_follow | EURJPY | H1 | - | 0.25% | -222 | -8.9 | 32% | -331 | -25 | 170 | 0.45 | ok |
| 513 | b5 | ny_follow | GBPJPY | H1 | - | 0.25% | -356 | -14.2 | 32% | -373 | -25 | 168 | 0.41 | ok |
| 514 | b5 | ny_follow | NZDJPY | H1 | - | 0.25% | 60 | 2.4 | 16% | -39 | -22 | 14 | 0.64 | ok |
| 515 | b5 | ny_follow | USDJPY | H1 | - | 0.50% | -544 | -21.8 | 28% | -581 | -87 | 165 | 0.44 | ok |
| 516 | b5 | ny_follow_k0.8 | AUDJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.25% | -323 | -12.9 | 32% | -349 | -25 | 63 | 0.40 | ok |
| 517 | b5 | ny_follow_k0.8 | CADJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.25% | -360 | -14.4 | 24% | -374 | -24 | 65 | 0.34 | ok |
| 518 | b5 | ny_follow_k0.8 | CHFJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.50% | -303 | -12.1 | 48% | -505 | -50 | 74 | 0.49 | ok |
| 519 | b5 | ny_follow_k0.8 | EURJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.75% | -21 | -0.8 | 44% | -467 | -75 | 66 | 0.50 | ok |
| 520 | b5 | ny_follow_k0.8 | GBPJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.75% | -552 | -22.1 | 32% | -576 | -80 | 70 | 0.44 | ok |
| 521 | b5 | ny_follow_k0.8 | NZDJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.75% | -542 | -21.7 | 36% | -597 | -75 | 59 | 0.42 | ok |
| 522 | b5 | ny_follow_k0.8 | USDJPY | H1 | k=0.8, tp_atr=0.4, sl_atr=0.4 | 0.50% | -346 | -13.8 | 44% | -515 | -50 | 69 | 0.48 | ok |
| 523 | b5 | streak3_fade_d1 | AUDJPY | D1 | - | 0.25% | -182 | -7.3 | 52% | -275 | -25 | 84 | 0.48 | ok |
| 524 | b5 | streak3_fade_d1 | CADJPY | D1 | - | 0.75% | 77 | 3.1 | 48% | -459 | -85 | 67 | 0.46 | ok |
| 525 | b5 | streak3_fade_d1 | CHFJPY | D1 | - | 1.00% | 460 | 18.4 | 56% | -525 | -151 | 66 | 0.55 | ok |
| 526 | b5 | streak3_fade_d1 | EURJPY | D1 | - | 0.75% | 168 | 6.7 | 40% | -566 | -82 | 80 | 0.54 | ok |
| 527 | b5 | streak3_fade_d1 | GBPJPY | D1 | - | 0.75% | 679 | 27.2 | 56% | -510 | -95 | 72 | 0.58 | ok |
| 528 | b5 | streak3_fade_d1 | NZDJPY | D1 | - | 1.00% | 95 | 3.8 | 56% | -539 | -162 | 75 | 0.52 | ok |
| 529 | b5 | streak3_fade_d1 | USDJPY | D1 | - | 1.00% | 1083 | 43.3 | 60% | -535 | -126 | 77 | 0.51 | ok |
| 530 | b5 | streak3_fade_d1_big | AUDJPY | D1 | min_move=1.5, max_hold=3 | 0.75% | -508 | -20.3 | 32% | -590 | -84 | 31 | 0.42 | ok |
| 531 | b5 | streak3_fade_d1_big | CADJPY | D1 | min_move=1.5, max_hold=3 | 2.00% | 1432 | 57.3 | 44% | -433 | -198 | 30 | 0.53 | ok |
| 532 | b5 | streak3_fade_d1_big | CHFJPY | D1 | min_move=1.5, max_hold=3 | 1.50% | 806 | 32.2 | 48% | -538 | -234 | 33 | 0.58 | ok |
| 533 | b5 | streak3_fade_d1_big | EURJPY | D1 | min_move=1.5, max_hold=3 | 1.50% | 936 | 37.5 | 40% | -479 | -163 | 30 | 0.57 | ok |
| 534 | b5 | streak3_fade_d1_big | GBPJPY | D1 | min_move=1.5, max_hold=3 | 1.50% | 816 | 32.6 | 32% | -564 | -141 | 26 | 0.65 | ok |
| 535 | b5 | streak3_fade_d1_big | NZDJPY | D1 | min_move=1.5, max_hold=3 | 1.50% | -43 | -1.7 | 32% | -565 | -161 | 29 | 0.45 | ok |
| 536 | b5 | streak3_fade_d1_big | USDJPY | D1 | min_move=1.5, max_hold=3 | 1.50% | 501 | 20.0 | 32% | -467 | -170 | 32 | 0.53 | ok |
| 537 | b5 | streak3_follow_d1 | AUDJPY | D1 | mode=follow | 0.50% | -194 | -7.8 | 32% | -488 | -68 | 74 | 0.42 | ok |
| 538 | b5 | streak3_follow_d1 | CADJPY | D1 | mode=follow | 0.25% | -255 | -10.2 | 40% | -321 | -32 | 64 | 0.42 | ok |
| 539 | b5 | streak3_follow_d1 | CHFJPY | D1 | mode=follow | 0.25% | -252 | -10.1 | 28% | -273 | -26 | 60 | 0.38 | ok |
| 540 | b5 | streak3_follow_d1 | EURJPY | D1 | mode=follow | 0.25% | -228 | -9.1 | 40% | -362 | -41 | 76 | 0.39 | ok |
| 541 | b5 | streak3_follow_d1 | GBPJPY | D1 | mode=follow | 0.25% | -282 | -11.3 | 36% | -381 | -30 | 66 | 0.36 | ok |
| 542 | b5 | streak3_follow_d1 | NZDJPY | D1 | mode=follow | 0.50% | 9 | 0.3 | 8% | -36 | -31 | 1 | 1.00 | ok |
| 543 | b5 | streak3_follow_d1 | USDJPY | D1 | mode=follow | 0.25% | -132 | -5.3 | 36% | -254 | -31 | 71 | 0.42 | ok |
| 544 | b5 | streak4_fade_d1 | AUDJPY | D1 | n=4, max_hold=4 | 1.00% | 2 | 0.1 | 44% | -483 | -170 | 43 | 0.53 | ok |
| 545 | b5 | streak4_fade_d1 | CADJPY | D1 | n=4, max_hold=4 | 1.00% | 325 | 13.0 | 36% | -595 | -118 | 27 | 0.48 | ok |
| 546 | b5 | streak4_fade_d1 | CHFJPY | D1 | n=4, max_hold=4 | 1.50% | 1216 | 48.7 | 36% | -576 | -151 | 27 | 0.59 | ok |
| 547 | b5 | streak4_fade_d1 | EURJPY | D1 | n=4, max_hold=4 | 1.00% | 157 | 6.3 | 44% | -519 | -107 | 30 | 0.57 | ok |
| 548 | b5 | streak4_fade_d1 | GBPJPY | D1 | n=4, max_hold=4 | 1.50% | 1552 | 62.1 | 48% | -564 | -218 | 26 | 0.62 | ok |
| 549 | b5 | streak4_fade_d1 | NZDJPY | D1 | n=4, max_hold=4 | 1.00% | 127 | 5.1 | 44% | -480 | -110 | 37 | 0.46 | ok |
| 550 | b5 | streak4_fade_d1 | USDJPY | D1 | n=4, max_hold=4 | 1.25% | 1419 | 56.8 | 40% | -520 | -143 | 31 | 0.58 | ok |
| 551 | b5 | streak5_fade_h4 | AUDJPY | H4 | n=5, max_hold=8 | 0.50% | -7 | -0.3 | 44% | -564 | -114 | 103 | 0.45 | ok |
| 552 | b5 | streak5_fade_h4 | CADJPY | H4 | n=5, max_hold=8 | 0.25% | 60 | 2.4 | 44% | -308 | -75 | 104 | 0.39 | ok |
| 553 | b5 | streak5_fade_h4 | CHFJPY | H4 | n=5, max_hold=8 | 0.25% | -229 | -9.2 | 32% | -352 | -45 | 96 | 0.38 | ok |
| 554 | b5 | streak5_fade_h4 | EURJPY | H4 | n=5, max_hold=8 | 0.50% | 105 | 4.2 | 56% | -529 | -112 | 85 | 0.49 | ok |
| 555 | b5 | streak5_fade_h4 | GBPJPY | H4 | n=5, max_hold=8 | none safe | -348 | -13.9 | 36% | -617 | -57 | 113 | 0.35 | ok |
| 556 | b5 | streak5_fade_h4 | NZDJPY | H4 | n=5, max_hold=8 | 0.25% | -256 | -10.3 | 16% | -403 | -53 | 40 | 0.35 | ok |
| 557 | b5 | streak5_fade_h4 | USDJPY | H4 | n=5, max_hold=8 | 0.25% | 86 | 3.4 | 48% | -358 | -55 | 118 | 0.41 | ok |
| 558 | b5 | streak6_fade_h1 | AUDJPY | H1 | n=6, max_hold=12 | none safe | -979 | -39.2 | 32% | -1083 | -74 | 193 | 0.32 | ok |
| 559 | b5 | streak6_fade_h1 | CADJPY | H1 | n=6, max_hold=12 | none safe | -910 | -36.4 | 32% | -928 | -119 | 179 | 0.32 | ok |
| 560 | b5 | streak6_fade_h1 | CHFJPY | H1 | n=6, max_hold=12 | none safe | -1246 | -49.8 | 24% | -1470 | -139 | 194 | 0.32 | ok |
| 561 | b5 | streak6_fade_h1 | EURJPY | H1 | n=6, max_hold=12 | none safe | -869 | -34.8 | 28% | -1172 | -134 | 158 | 0.35 | ok |
| 562 | b5 | streak6_fade_h1 | GBPJPY | H1 | n=6, max_hold=12 | none safe | -707 | -28.3 | 36% | -865 | -103 | 190 | 0.34 | ok |
| 563 | b5 | streak6_fade_h1 | NZDJPY | H1 | n=6, max_hold=12 | none safe | -1494 | -59.8 | 32% | -1757 | -105 | 178 | 0.28 | ok |
| 564 | b5 | streak6_fade_h1 | USDJPY | H1 | n=6, max_hold=12 | none safe | -733 | -29.3 | 36% | -1076 | -155 | 223 | 0.35 | ok |
| 565 | b5 | tokyo_break_m30 | AUDJPY | M30 | trend_n=20 | 0.25% | -387 | -15.5 | 28% | -402 | -25 | 115 | 0.43 | ok |
| 566 | b5 | tokyo_break_m30 | CADJPY | M30 | trend_n=20 | 0.25% | -202 | -8.1 | 48% | -310 | -25 | 136 | 0.49 | ok |
| 567 | b5 | tokyo_break_m30 | CHFJPY | M30 | trend_n=20 | 0.25% | -491 | -19.6 | 40% | -586 | -25 | 155 | 0.43 | ok |
| 568 | b5 | tokyo_break_m30 | EURJPY | M30 | trend_n=20 | 0.25% | -398 | -15.9 | 36% | -527 | -25 | 153 | 0.46 | ok |
| 569 | b5 | tokyo_break_m30 | GBPJPY | M30 | trend_n=20 | 0.25% | -347 | -13.9 | 32% | -428 | -27 | 160 | 0.47 | ok |
| 570 | b5 | tokyo_break_m30 | NZDJPY | M30 | trend_n=20 | 0.50% | -436 | -17.4 | 36% | -525 | -50 | 96 | 0.47 | ok |
| 571 | b5 | tokyo_break_m30 | USDJPY | M30 | trend_n=20 | 0.25% | -132 | -5.3 | 56% | -357 | -26 | 140 | 0.51 | ok |
| 572 | b5 | tokyo_break_trail | AUDJPY | H1 | trail=2.0, sl=mid | none safe | -622 | -24.9 | 16% | -668 | -25 | 101 | 0.35 | ok |
| 573 | b5 | tokyo_break_trail | CADJPY | H1 | trail=2.0, sl=mid | 0.25% | -98 | -3.9 | 44% | -330 | -25 | 120 | 0.41 | ok |
| 574 | b5 | tokyo_break_trail | CHFJPY | H1 | trail=2.0, sl=mid | none safe | -906 | -36.3 | 20% | -963 | -27 | 135 | 0.28 | ok |
| 575 | b5 | tokyo_break_trail | EURJPY | H1 | trail=2.0, sl=mid | none safe | -428 | -17.1 | 36% | -605 | -25 | 137 | 0.36 | ok |
| 576 | b5 | tokyo_break_trail | GBPJPY | H1 | trail=2.0, sl=mid | none safe | -735 | -29.4 | 24% | -775 | -25 | 145 | 0.32 | ok |
| 577 | b5 | tokyo_break_trail | NZDJPY | H1 | trail=2.0, sl=mid | 0.25% | -81 | -3.2 | 48% | -209 | -25 | 70 | 0.36 | ok |
| 578 | b5 | tokyo_break_trail | USDJPY | H1 | trail=2.0, sl=mid | 0.50% | 198 | 7.9 | 56% | -492 | -50 | 124 | 0.37 | ok |
| 579 | b5 | tokyo_break_trend | AUDJPY | H1 | - | 0.25% | -414 | -16.6 | 24% | -417 | -25 | 101 | 0.43 | ok |
| 580 | b5 | tokyo_break_trend | CADJPY | H1 | - | 0.50% | -181 | -7.2 | 64% | -505 | -50 | 120 | 0.51 | ok |
| 581 | b5 | tokyo_break_trend | CHFJPY | H1 | - | 0.25% | -524 | -21.0 | 32% | -563 | -25 | 135 | 0.42 | ok |
| 582 | b5 | tokyo_break_trend | EURJPY | H1 | - | 0.25% | -279 | -11.2 | 36% | -373 | -25 | 137 | 0.50 | ok |
| 583 | b5 | tokyo_break_trend | GBPJPY | H1 | - | 0.25% | -369 | -14.8 | 36% | -433 | -27 | 145 | 0.46 | ok |
| 584 | b5 | tokyo_break_trend | NZDJPY | H1 | - | 0.50% | -470 | -18.8 | 28% | -508 | -50 | 82 | 0.44 | ok |
| 585 | b5 | tokyo_break_trend | USDJPY | H1 | - | 0.75% | 100 | 4.0 | 56% | -540 | -84 | 124 | 0.52 | ok |
| 586 | b5 | tokyo_break_trend50 | AUDJPY | H1 | trend_n=50, tp_mult=1.5 | 0.50% | -347 | -13.9 | 36% | -536 | -50 | 112 | 0.47 | ok |
| 587 | b5 | tokyo_break_trend50 | CADJPY | H1 | trend_n=50, tp_mult=1.5 | 0.25% | -222 | -8.9 | 48% | -328 | -25 | 132 | 0.46 | ok |
| 588 | b5 | tokyo_break_trend50 | CHFJPY | H1 | trend_n=50, tp_mult=1.5 | none safe | -498 | -19.9 | 24% | -605 | -25 | 149 | 0.39 | ok |
| 589 | b5 | tokyo_break_trend50 | EURJPY | H1 | trend_n=50, tp_mult=1.5 | 0.25% | -333 | -13.3 | 32% | -399 | -25 | 133 | 0.46 | ok |
| 590 | b5 | tokyo_break_trend50 | GBPJPY | H1 | trend_n=50, tp_mult=1.5 | 0.50% | -528 | -21.1 | 44% | -572 | -54 | 146 | 0.45 | ok |
| 591 | b5 | tokyo_break_trend50 | NZDJPY | H1 | trend_n=50, tp_mult=1.5 | 0.25% | -24 | -0.9 | 12% | -54 | -25 | 9 | 0.56 | ok |
| 592 | b5 | tokyo_break_trend50 | USDJPY | H1 | trend_n=50, tp_mult=1.5 | 0.75% | 207 | 8.3 | 60% | -541 | -84 | 127 | 0.46 | ok |
| 593 | b5 | zfade_d1 | AUDJPY | D1 | - | 1.50% | 104 | 4.2 | 24% | -553 | -155 | 19 | 0.58 | ok |
| 594 | b5 | zfade_d1 | CADJPY | D1 | - | 2.00% | 565 | 22.6 | 24% | -479 | -199 | 15 | 0.53 | ok |
| 595 | b5 | zfade_d1 | CHFJPY | D1 | - | 1.50% | 216 | 8.6 | 36% | -519 | -146 | 24 | 0.54 | ok |
| 596 | b5 | zfade_d1 | EURJPY | D1 | - | 2.00% | 708 | 28.3 | 40% | -551 | -280 | 22 | 0.55 | ok |
| 597 | b5 | zfade_d1 | GBPJPY | D1 | - | 2.00% | 626 | 25.0 | 44% | -406 | -233 | 22 | 0.68 | ok |
| 598 | b5 | zfade_d1 | NZDJPY | D1 | - | 2.00% | 248 | 9.9 | 32% | -496 | -193 | 18 | 0.61 | ok |
| 599 | b5 | zfade_d1 | USDJPY | D1 | - | 1.50% | 792 | 31.7 | 32% | -429 | -237 | 22 | 0.55 | ok |
| 600 | b5 | zfade_d1_n20 | AUDJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 1239 | 49.5 | 36% | -593 | -209 | 19 | 0.58 | ok |
| 601 | b5 | zfade_d1_n20 | CADJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 1273 | 50.9 | 28% | -323 | -195 | 12 | 0.67 | ok |
| 602 | b5 | zfade_d1_n20 | CHFJPY | D1 | n=20, z=2.0, max_hold=8 | 1.25% | 192 | 7.7 | 32% | -515 | -118 | 19 | 0.53 | ok |
| 603 | b5 | zfade_d1_n20 | EURJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 417 | 16.7 | 32% | -538 | -280 | 15 | 0.60 | ok |
| 604 | b5 | zfade_d1_n20 | GBPJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 572 | 22.9 | 28% | -401 | -233 | 16 | 0.50 | ok |
| 605 | b5 | zfade_d1_n20 | NZDJPY | D1 | n=20, z=2.0, max_hold=8 | 1.50% | -322 | -12.9 | 16% | -530 | -141 | 11 | 0.27 | ok |
| 606 | b5 | zfade_d1_n20 | USDJPY | D1 | n=20, z=2.0, max_hold=8 | 2.00% | 853 | 34.1 | 28% | -479 | -242 | 13 | 0.54 | ok |
| 607 | b5 | zfade_h1 | AUDJPY | H1 | n=48, z=2.5, max_hold=48 | none safe | -214 | -8.6 | 36% | -742 | -119 | 123 | 0.33 | ok |
| 608 | b5 | zfade_h1 | CADJPY | H1 | n=48, z=2.5, max_hold=48 | none safe | -179 | -7.2 | 48% | -613 | -150 | 104 | 0.38 | ok |
| 609 | b5 | zfade_h1 | CHFJPY | H1 | n=48, z=2.5, max_hold=48 | 0.25% | -354 | -14.2 | 32% | -449 | -151 | 126 | 0.33 | ok |
| 610 | b5 | zfade_h1 | EURJPY | H1 | n=48, z=2.5, max_hold=48 | 0.25% | -166 | -6.6 | 52% | -416 | -168 | 126 | 0.36 | ok |
| 611 | b5 | zfade_h1 | GBPJPY | H1 | n=48, z=2.5, max_hold=48 | none safe | -250 | -10.0 | 48% | -707 | -193 | 108 | 0.34 | ok |
| 612 | b5 | zfade_h1 | NZDJPY | H1 | n=48, z=2.5, max_hold=48 | 0.25% | -177 | -7.1 | 32% | -501 | -106 | 84 | 0.33 | ok |
| 613 | b5 | zfade_h1 | USDJPY | H1 | n=48, z=2.5, max_hold=48 | 0.25% | -356 | -14.2 | 36% | -566 | -155 | 118 | 0.31 | ok |
| 614 | b5 | zfade_h4 | AUDJPY | H4 | n=20, z=2.2, max_hold=18 | 0.25% | -139 | -5.6 | 48% | -392 | -62 | 60 | 0.42 | ok |
| 615 | b5 | zfade_h4 | CADJPY | H4 | n=20, z=2.2, max_hold=18 | 0.50% | 528 | 21.1 | 60% | -407 | -115 | 61 | 0.52 | ok |
| 616 | b5 | zfade_h4 | CHFJPY | H4 | n=20, z=2.2, max_hold=18 | 0.50% | -420 | -16.8 | 44% | -563 | -168 | 73 | 0.45 | ok |
| 617 | b5 | zfade_h4 | EURJPY | H4 | n=20, z=2.2, max_hold=18 | 0.75% | 394 | 15.8 | 56% | -586 | -226 | 65 | 0.46 | ok |
| 618 | b5 | zfade_h4 | GBPJPY | H4 | n=20, z=2.2, max_hold=18 | 0.50% | 180 | 7.2 | 64% | -410 | -134 | 65 | 0.51 | ok |
| 619 | b5 | zfade_h4 | NZDJPY | H4 | n=20, z=2.2, max_hold=18 | 0.50% | 251 | 10.0 | 60% | -521 | -107 | 55 | 0.51 | ok |
| 620 | b5 | zfade_h4 | USDJPY | H4 | n=20, z=2.2, max_hold=18 | 0.75% | 4 | 0.2 | 48% | -598 | -224 | 59 | 0.41 | ok |
| 621 | b6 | bigday_ldn_k1.0 | AUDJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 0.75% | -18 | -0.7 | 44% | -465 | -75 | 42 | 0.43 | ok |
| 622 | b6 | bigday_ldn_k1.0 | CADJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 1.25% | -92 | -3.7 | 32% | -499 | -125 | 44 | 0.48 | ok |
| 623 | b6 | bigday_ldn_k1.0 | CHFJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 0.50% | -480 | -19.2 | 40% | -542 | -49 | 54 | 0.46 | ok |
| 624 | b6 | bigday_ldn_k1.0 | EURJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 1.25% | -88 | -3.5 | 56% | -521 | -126 | 51 | 0.51 | ok |
| 625 | b6 | bigday_ldn_k1.0 | GBPJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 0.75% | -234 | -9.4 | 32% | -450 | -74 | 45 | 0.51 | ok |
| 626 | b6 | bigday_ldn_k1.0 | NZDJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 1.00% | 57 | 2.3 | 36% | -540 | -101 | 44 | 0.57 | ok |
| 627 | b6 | bigday_ldn_k1.0 | USDJPY | H1 | k=1.0, entry_h=9.0, max_hold=14 | 1.00% | 13 | 0.5 | 44% | -481 | -100 | 58 | 0.50 | ok |
| 628 | b6 | bigday_ldn_k1.5 | AUDJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 1.50% | 102 | 4.1 | 20% | -467 | -150 | 11 | 0.55 | ok |
| 629 | b6 | bigday_ldn_k1.5 | CADJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 2.00% | 196 | 7.8 | 28% | -349 | -200 | 12 | 0.58 | ok |
| 630 | b6 | bigday_ldn_k1.5 | CHFJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 2.00% | -511 | -20.4 | 16% | -575 | -199 | 12 | 0.42 | ok |
| 631 | b6 | bigday_ldn_k1.5 | EURJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 1.25% | -296 | -11.8 | 12% | -514 | -126 | 9 | 0.33 | ok |
| 632 | b6 | bigday_ldn_k1.5 | GBPJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 1.50% | -320 | -12.8 | 12% | -534 | -150 | 10 | 0.40 | ok |
| 633 | b6 | bigday_ldn_k1.5 | NZDJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 2.00% | 226 | 9.1 | 12% | -300 | -202 | 9 | 0.56 | ok |
| 634 | b6 | bigday_ldn_k1.5 | USDJPY | H1 | k=1.5, entry_h=9.0, max_hold=14 | 2.00% | 116 | 4.6 | 24% | -504 | -199 | 13 | 0.54 | ok |
| 635 | b6 | bigday_ldn_tp0.3 | AUDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.50% | -345 | -13.8 | 24% | -562 | -149 | 22 | 0.41 | ok |
| 636 | b6 | bigday_ldn_tp0.3 | CADJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.25% | -85 | -3.4 | 28% | -579 | -125 | 25 | 0.52 | ok |
| 637 | b6 | bigday_ldn_tp0.3 | CHFJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.25% | -142 | -5.7 | 36% | -539 | -125 | 28 | 0.54 | ok |
| 638 | b6 | bigday_ldn_tp0.3 | EURJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.00% | -305 | -12.2 | 32% | -526 | -100 | 27 | 0.48 | ok |
| 639 | b6 | bigday_ldn_tp0.3 | GBPJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.00% | -327 | -13.1 | 24% | -553 | -101 | 27 | 0.48 | ok |
| 640 | b6 | bigday_ldn_tp0.3 | NZDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.50% | 181 | 7.2 | 28% | -594 | -150 | 23 | 0.57 | ok |
| 641 | b6 | bigday_ldn_tp0.3 | USDJPY | H1 | k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5 | 1.25% | 134 | 5.4 | 32% | -543 | -125 | 29 | 0.52 | ok |
| 642 | b6 | bigday_ny_k1.2 | AUDJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 1.25% | -385 | -15.4 | 20% | -577 | -125 | 22 | 0.36 | ok |
| 643 | b6 | bigday_ny_k1.2 | CADJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 2.00% | 364 | 14.6 | 40% | -412 | -200 | 25 | 0.68 | ok |
| 644 | b6 | bigday_ny_k1.2 | CHFJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 1.50% | -224 | -8.9 | 28% | -521 | -146 | 28 | 0.43 | ok |
| 645 | b6 | bigday_ny_k1.2 | EURJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 2.00% | 699 | 27.9 | 32% | -429 | -198 | 27 | 0.59 | ok |
| 646 | b6 | bigday_ny_k1.2 | GBPJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 0.75% | -320 | -12.8 | 24% | -466 | -73 | 28 | 0.46 | ok |
| 647 | b6 | bigday_ny_k1.2 | NZDJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 2.00% | -128 | -5.1 | 28% | -545 | -194 | 23 | 0.43 | ok |
| 648 | b6 | bigday_ny_k1.2 | USDJPY | H1 | k=1.2, entry_h=16.0, max_hold=7 | 2.00% | 920 | 36.8 | 40% | -358 | -198 | 29 | 0.62 | ok |
| 649 | b6 | gap_fade_g0.1_h12 | AUDJPY | H1 | min_gap=0.1, max_hold=12 | 1.25% | -326 | -13.0 | 44% | -571 | -124 | 50 | 0.62 | ok |
| 650 | b6 | gap_fade_g0.1_h12 | CADJPY | H1 | min_gap=0.1, max_hold=12 | 0.50% | -301 | -12.1 | 44% | -412 | -50 | 47 | 0.57 | ok |
| 651 | b6 | gap_fade_g0.1_h12 | CHFJPY | H1 | min_gap=0.1, max_hold=12 | 0.75% | -135 | -5.4 | 56% | -486 | -74 | 41 | 0.71 | ok |
| 652 | b6 | gap_fade_g0.1_h12 | EURJPY | H1 | min_gap=0.1, max_hold=12 | 1.25% | 613 | 24.5 | 76% | -513 | -124 | 51 | 0.76 | ok |
| 653 | b6 | gap_fade_g0.1_h12 | GBPJPY | H1 | min_gap=0.1, max_hold=12 | 1.00% | 26 | 1.0 | 60% | -504 | -100 | 48 | 0.71 | ok |
| 654 | b6 | gap_fade_g0.1_h12 | NZDJPY | H1 | min_gap=0.1, max_hold=12 | 0.75% | -528 | -21.1 | 32% | -585 | -75 | 42 | 0.50 | ok |
| 655 | b6 | gap_fade_g0.1_h12 | USDJPY | H1 | min_gap=0.1, max_hold=12 | 0.50% | -434 | -17.3 | 48% | -596 | -50 | 47 | 0.57 | ok |
| 656 | b6 | gap_fade_g0.1_h24 | AUDJPY | H1 | min_gap=0.1, max_hold=24 | 1.50% | -208 | -8.3 | 48% | -568 | -149 | 50 | 0.66 | ok |
| 657 | b6 | gap_fade_g0.1_h24 | CADJPY | H1 | min_gap=0.1, max_hold=24 | 0.75% | -440 | -17.6 | 36% | -588 | -75 | 47 | 0.57 | ok |
| 658 | b6 | gap_fade_g0.1_h24 | CHFJPY | H1 | min_gap=0.1, max_hold=24 | 0.75% | -131 | -5.2 | 60% | -482 | -74 | 41 | 0.73 | ok |
| 659 | b6 | gap_fade_g0.1_h24 | EURJPY | H1 | min_gap=0.1, max_hold=24 | 1.50% | 916 | 36.7 | 72% | -503 | -150 | 51 | 0.76 | ok |
| 660 | b6 | gap_fade_g0.1_h24 | GBPJPY | H1 | min_gap=0.1, max_hold=24 | 1.25% | 148 | 5.9 | 60% | -564 | -126 | 48 | 0.73 | ok |
| 661 | b6 | gap_fade_g0.1_h24 | NZDJPY | H1 | min_gap=0.1, max_hold=24 | 0.50% | -344 | -13.8 | 28% | -384 | -50 | 35 | 0.46 | ok |
| 662 | b6 | gap_fade_g0.1_h24 | USDJPY | H1 | min_gap=0.1, max_hold=24 | 0.50% | -338 | -13.5 | 48% | -578 | -50 | 47 | 0.60 | ok |
| 663 | b6 | gap_fade_g0.1_h48 | AUDJPY | H1 | min_gap=0.1, max_hold=48 | 2.00% | 324 | 12.9 | 48% | -494 | -200 | 50 | 0.72 | ok |
| 664 | b6 | gap_fade_g0.1_h48 | CADJPY | H1 | min_gap=0.1, max_hold=48 | 0.75% | -367 | -14.7 | 44% | -549 | -75 | 47 | 0.62 | ok |
| 665 | b6 | gap_fade_g0.1_h48 | CHFJPY | H1 | min_gap=0.1, max_hold=48 | 1.00% | -106 | -4.2 | 64% | -572 | -99 | 41 | 0.76 | ok |
| 666 | b6 | gap_fade_g0.1_h48 | EURJPY | H1 | min_gap=0.1, max_hold=48 | 1.50% | 1134 | 45.4 | 76% | -501 | -150 | 51 | 0.80 | ok |
| 667 | b6 | gap_fade_g0.1_h48 | GBPJPY | H1 | min_gap=0.1, max_hold=48 | 1.00% | 95 | 3.8 | 60% | -518 | -100 | 48 | 0.75 | ok |
| 668 | b6 | gap_fade_g0.1_h48 | NZDJPY | H1 | min_gap=0.1, max_hold=48 | 0.50% | -261 | -10.5 | 36% | -328 | -50 | 35 | 0.51 | ok |
| 669 | b6 | gap_fade_g0.1_h48 | USDJPY | H1 | min_gap=0.1, max_hold=48 | 0.25% | -160 | -6.4 | 48% | -294 | -25 | 47 | 0.62 | ok |
| 670 | b6 | gap_fade_g0.2_h12 | AUDJPY | H1 | min_gap=0.2, max_hold=12 | 1.50% | 31 | 1.3 | 56% | -591 | -149 | 39 | 0.64 | ok |
| 671 | b6 | gap_fade_g0.2_h12 | CADJPY | H1 | min_gap=0.2, max_hold=12 | 0.75% | -364 | -14.6 | 40% | -499 | -75 | 34 | 0.59 | ok |
| 672 | b6 | gap_fade_g0.2_h12 | CHFJPY | H1 | min_gap=0.2, max_hold=12 | 2.00% | 230 | 9.2 | 48% | -413 | -197 | 22 | 0.77 | ok |
| 673 | b6 | gap_fade_g0.2_h12 | EURJPY | H1 | min_gap=0.2, max_hold=12 | 2.00% | 978 | 39.1 | 68% | -517 | -200 | 37 | 0.81 | ok |
| 674 | b6 | gap_fade_g0.2_h12 | GBPJPY | H1 | min_gap=0.2, max_hold=12 | 1.25% | -205 | -8.2 | 56% | -599 | -126 | 36 | 0.67 | ok |
| 675 | b6 | gap_fade_g0.2_h12 | NZDJPY | H1 | min_gap=0.2, max_hold=12 | 1.00% | -319 | -12.8 | 40% | -564 | -100 | 33 | 0.52 | ok |
| 676 | b6 | gap_fade_g0.2_h12 | USDJPY | H1 | min_gap=0.2, max_hold=12 | 0.50% | -423 | -16.9 | 36% | -490 | -50 | 29 | 0.45 | ok |
| 677 | b6 | gap_fade_g0.2_h24 | AUDJPY | H1 | min_gap=0.2, max_hold=24 | 1.50% | 236 | 9.4 | 56% | -568 | -149 | 39 | 0.69 | ok |
| 678 | b6 | gap_fade_g0.2_h24 | CADJPY | H1 | min_gap=0.2, max_hold=24 | 1.00% | -380 | -15.2 | 32% | -532 | -100 | 34 | 0.59 | ok |
| 679 | b6 | gap_fade_g0.2_h24 | CHFJPY | H1 | min_gap=0.2, max_hold=24 | 2.00% | 241 | 9.6 | 52% | -453 | -197 | 22 | 0.82 | ok |
| 680 | b6 | gap_fade_g0.2_h24 | EURJPY | H1 | min_gap=0.2, max_hold=24 | 2.00% | 1241 | 49.6 | 64% | -407 | -200 | 37 | 0.81 | ok |
| 681 | b6 | gap_fade_g0.2_h24 | GBPJPY | H1 | min_gap=0.2, max_hold=24 | 1.25% | -115 | -4.6 | 56% | -541 | -126 | 36 | 0.67 | ok |
| 682 | b6 | gap_fade_g0.2_h24 | NZDJPY | H1 | min_gap=0.2, max_hold=24 | 1.00% | -209 | -8.4 | 40% | -482 | -100 | 33 | 0.48 | ok |
| 683 | b6 | gap_fade_g0.2_h24 | USDJPY | H1 | min_gap=0.2, max_hold=24 | 0.50% | -328 | -13.1 | 40% | -472 | -50 | 29 | 0.48 | ok |
| 684 | b6 | gap_fade_g0.2_h48 | AUDJPY | H1 | min_gap=0.2, max_hold=48 | 2.00% | 916 | 36.6 | 56% | -494 | -200 | 39 | 0.77 | ok |
| 685 | b6 | gap_fade_g0.2_h48 | CADJPY | H1 | min_gap=0.2, max_hold=48 | 1.00% | -281 | -11.2 | 40% | -478 | -100 | 34 | 0.65 | ok |
| 686 | b6 | gap_fade_g0.2_h48 | CHFJPY | H1 | min_gap=0.2, max_hold=48 | 2.00% | 416 | 16.6 | 56% | -420 | -197 | 22 | 0.86 | ok |
| 687 | b6 | gap_fade_g0.2_h48 | EURJPY | H1 | min_gap=0.2, max_hold=48 | 2.00% | 1530 | 61.2 | 68% | -405 | -200 | 37 | 0.86 | ok |
| 688 | b6 | gap_fade_g0.2_h48 | GBPJPY | H1 | min_gap=0.2, max_hold=48 | 1.25% | -126 | -5.1 | 56% | -553 | -126 | 36 | 0.69 | ok |
| 689 | b6 | gap_fade_g0.2_h48 | NZDJPY | H1 | min_gap=0.2, max_hold=48 | 1.25% | 22 | 0.9 | 48% | -513 | -124 | 33 | 0.58 | ok |
| 690 | b6 | gap_fade_g0.2_h48 | USDJPY | H1 | min_gap=0.2, max_hold=48 | 0.50% | -342 | -13.7 | 40% | -523 | -50 | 29 | 0.52 | ok |
| 691 | b6 | gap_fade_g0.3_h12 | AUDJPY | H1 | min_gap=0.3, max_hold=12 | 1.25% | 8 | 0.3 | 48% | -500 | -124 | 26 | 0.65 | ok |
| 692 | b6 | gap_fade_g0.3_h12 | CADJPY | H1 | min_gap=0.3, max_hold=12 | 0.75% | -421 | -16.8 | 32% | -483 | -74 | 24 | 0.50 | ok |
| 693 | b6 | gap_fade_g0.3_h12 | CHFJPY | H1 | min_gap=0.3, max_hold=12 | 1.50% | -152 | -6.1 | 24% | -467 | -147 | 13 | 0.62 | ok |
| 694 | b6 | gap_fade_g0.3_h12 | EURJPY | H1 | min_gap=0.3, max_hold=12 | 2.00% | 754 | 30.1 | 52% | -338 | -198 | 24 | 0.79 | ok |
| 695 | b6 | gap_fade_g0.3_h12 | GBPJPY | H1 | min_gap=0.3, max_hold=12 | 1.25% | -240 | -9.6 | 44% | -580 | -126 | 29 | 0.62 | ok |
| 696 | b6 | gap_fade_g0.3_h12 | NZDJPY | H1 | min_gap=0.3, max_hold=12 | 1.50% | -194 | -7.8 | 32% | -591 | -149 | 22 | 0.59 | ok |
| 697 | b6 | gap_fade_g0.3_h12 | USDJPY | H1 | min_gap=0.3, max_hold=12 | 0.75% | -548 | -21.9 | 16% | -582 | -75 | 15 | 0.27 | ok |
| 698 | b6 | gap_fade_g0.3_h24 | AUDJPY | H1 | min_gap=0.3, max_hold=24 | 1.50% | 168 | 6.7 | 48% | -518 | -149 | 26 | 0.69 | ok |
| 699 | b6 | gap_fade_g0.3_h24 | CADJPY | H1 | min_gap=0.3, max_hold=24 | 1.00% | -457 | -18.3 | 32% | -512 | -99 | 24 | 0.50 | ok |
| 700 | b6 | gap_fade_g0.3_h24 | CHFJPY | H1 | min_gap=0.3, max_hold=24 | 1.50% | -148 | -5.9 | 28% | -462 | -147 | 13 | 0.69 | ok |
| 701 | b6 | gap_fade_g0.3_h24 | EURJPY | H1 | min_gap=0.3, max_hold=24 | 2.00% | 1017 | 40.7 | 48% | -338 | -198 | 24 | 0.79 | ok |
| 702 | b6 | gap_fade_g0.3_h24 | GBPJPY | H1 | min_gap=0.3, max_hold=24 | 1.25% | -150 | -6.0 | 44% | -522 | -126 | 29 | 0.62 | ok |
| 703 | b6 | gap_fade_g0.3_h24 | NZDJPY | H1 | min_gap=0.3, max_hold=24 | 1.50% | -57 | -2.3 | 32% | -483 | -149 | 22 | 0.55 | ok |
| 704 | b6 | gap_fade_g0.3_h24 | USDJPY | H1 | min_gap=0.3, max_hold=24 | 0.75% | -407 | -16.3 | 20% | -523 | -75 | 15 | 0.33 | ok |
| 705 | b6 | gap_fade_g0.3_h48 | AUDJPY | H1 | min_gap=0.3, max_hold=48 | 2.00% | 737 | 29.5 | 48% | -561 | -200 | 26 | 0.81 | ok |
| 706 | b6 | gap_fade_g0.3_h48 | CADJPY | H1 | min_gap=0.3, max_hold=48 | 1.25% | -472 | -18.9 | 36% | -587 | -125 | 24 | 0.58 | ok |
| 707 | b6 | gap_fade_g0.3_h48 | CHFJPY | H1 | min_gap=0.3, max_hold=48 | 2.00% | -36 | -1.4 | 32% | -568 | -197 | 13 | 0.77 | ok |
| 708 | b6 | gap_fade_g0.3_h48 | EURJPY | H1 | min_gap=0.3, max_hold=48 | 2.00% | 1306 | 52.2 | 56% | -338 | -198 | 24 | 0.88 | ok |
| 709 | b6 | gap_fade_g0.3_h48 | GBPJPY | H1 | min_gap=0.3, max_hold=48 | 1.25% | -162 | -6.5 | 48% | -533 | -126 | 29 | 0.66 | ok |
| 710 | b6 | gap_fade_g0.3_h48 | NZDJPY | H1 | min_gap=0.3, max_hold=48 | 1.50% | 188 | 7.5 | 36% | -472 | -149 | 22 | 0.64 | ok |
| 711 | b6 | gap_fade_g0.3_h48 | USDJPY | H1 | min_gap=0.3, max_hold=48 | 0.75% | -423 | -16.9 | 24% | -596 | -75 | 15 | 0.40 | ok |
| 712 | b6 | gap_fade_m30 | AUDJPY | M30 | max_hold=48 | 1.00% | 116 | 4.6 | 48% | -474 | -100 | 43 | 0.67 | ok |
| 713 | b6 | gap_fade_m30 | CADJPY | M30 | max_hold=48 | 1.00% | -413 | -16.5 | 32% | -597 | -100 | 37 | 0.54 | ok |
| 714 | b6 | gap_fade_m30 | CHFJPY | M30 | max_hold=48 | 0.50% | -228 | -9.1 | 48% | -447 | -49 | 34 | 0.65 | ok |
| 715 | b6 | gap_fade_m30 | EURJPY | M30 | max_hold=48 | 2.00% | 1511 | 60.5 | 72% | -424 | -199 | 47 | 0.85 | ok |
| 716 | b6 | gap_fade_m30 | GBPJPY | M30 | max_hold=48 | 1.25% | 124 | 5.0 | 60% | -532 | -124 | 48 | 0.79 | ok |
| 717 | b6 | gap_fade_m30 | NZDJPY | M30 | max_hold=48 | 0.75% | -350 | -14.0 | 52% | -599 | -75 | 37 | 0.59 | ok |
| 718 | b6 | gap_fade_m30 | USDJPY | M30 | max_hold=48 | 0.50% | -424 | -17.0 | 36% | -554 | -50 | 34 | 0.47 | ok |
| 719 | b6 | gap_fade_sl0.7 | AUDJPY | H1 | sl_mult=0.7, min_sl=0.2 | 0.75% | -132 | -5.3 | 40% | -479 | -74 | 43 | 0.63 | ok |
| 720 | b6 | gap_fade_sl0.7 | CADJPY | H1 | sl_mult=0.7, min_sl=0.2 | 0.50% | -356 | -14.2 | 36% | -455 | -50 | 41 | 0.56 | ok |
| 721 | b6 | gap_fade_sl0.7 | CHFJPY | H1 | sl_mult=0.7, min_sl=0.2 | 0.50% | -292 | -11.7 | 40% | -520 | -50 | 31 | 0.61 | ok |
| 722 | b6 | gap_fade_sl0.7 | EURJPY | H1 | sl_mult=0.7, min_sl=0.2 | 1.25% | 1017 | 40.7 | 60% | -547 | -124 | 46 | 0.74 | ok |
| 723 | b6 | gap_fade_sl0.7 | GBPJPY | H1 | sl_mult=0.7, min_sl=0.2 | 1.25% | 290 | 11.6 | 56% | -557 | -125 | 45 | 0.71 | ok |
| 724 | b6 | gap_fade_sl0.7 | NZDJPY | H1 | sl_mult=0.7, min_sl=0.2 | 0.50% | -277 | -11.1 | 32% | -360 | -50 | 32 | 0.44 | ok |
| 725 | b6 | gap_fade_sl0.7 | USDJPY | H1 | sl_mult=0.7, min_sl=0.2 | 0.50% | -393 | -15.7 | 32% | -566 | -50 | 35 | 0.46 | ok |
| 726 | b6 | gap_fade_sl1.5 | AUDJPY | H1 | sl_mult=1.5 | 1.50% | 142 | 5.7 | 56% | -477 | -150 | 43 | 0.72 | ok |
| 727 | b6 | gap_fade_sl1.5 | CADJPY | H1 | sl_mult=1.5 | 1.00% | -349 | -14.0 | 40% | -478 | -100 | 41 | 0.61 | ok |
| 728 | b6 | gap_fade_sl1.5 | CHFJPY | H1 | sl_mult=1.5 | 0.75% | -260 | -10.4 | 48% | -487 | -74 | 31 | 0.68 | ok |
| 729 | b6 | gap_fade_sl1.5 | EURJPY | H1 | sl_mult=1.5 | 2.00% | 1589 | 63.6 | 80% | -308 | -200 | 46 | 0.83 | ok |
| 730 | b6 | gap_fade_sl1.5 | GBPJPY | H1 | sl_mult=1.5 | 1.50% | 15 | 0.6 | 60% | -578 | -150 | 45 | 0.73 | ok |
| 731 | b6 | gap_fade_sl1.5 | NZDJPY | H1 | sl_mult=1.5 | 0.75% | -249 | -9.9 | 36% | -400 | -74 | 30 | 0.50 | ok |
| 732 | b6 | gap_fade_sl1.5 | USDJPY | H1 | sl_mult=1.5 | 0.75% | -303 | -12.1 | 44% | -588 | -75 | 35 | 0.54 | ok |
| 733 | b6 | rsi2c_d1_15_85 | AUDJPY | D1 | counter=True, lo=15, hi=85 | 0.75% | 80 | 3.2 | 56% | -478 | -73 | 88 | 0.67 | ok |
| 734 | b6 | rsi2c_d1_15_85 | CADJPY | D1 | counter=True, lo=15, hi=85 | 2.00% | 1337 | 53.5 | 64% | -581 | -198 | 88 | 0.72 | ok |
| 735 | b6 | rsi2c_d1_15_85 | CHFJPY | D1 | counter=True, lo=15, hi=85 | 1.00% | 190 | 7.6 | 56% | -484 | -97 | 83 | 0.69 | ok |
| 736 | b6 | rsi2c_d1_15_85 | EURJPY | D1 | counter=True, lo=15, hi=85 | 1.50% | 1381 | 55.2 | 64% | -574 | -148 | 85 | 0.72 | ok |
| 737 | b6 | rsi2c_d1_15_85 | GBPJPY | D1 | counter=True, lo=15, hi=85 | 1.25% | 346 | 13.8 | 64% | -489 | -125 | 84 | 0.65 | ok |
| 738 | b6 | rsi2c_d1_15_85 | NZDJPY | D1 | counter=True, lo=15, hi=85 | 1.00% | -29 | -1.2 | 16% | -232 | -96 | 21 | 0.62 | ok |
| 739 | b6 | rsi2c_d1_15_85 | USDJPY | D1 | counter=True, lo=15, hi=85 | 1.50% | 1298 | 51.9 | 64% | -460 | -149 | 84 | 0.70 | ok |
| 740 | b6 | rsi2c_d1_20_80 | AUDJPY | D1 | counter=True, lo=20, hi=80 | 0.75% | -117 | -4.7 | 48% | -594 | -73 | 101 | 0.66 | ok |
| 741 | b6 | rsi2c_d1_20_80 | CADJPY | D1 | counter=True, lo=20, hi=80 | 1.50% | 900 | 36.0 | 68% | -547 | -151 | 107 | 0.70 | ok |
| 742 | b6 | rsi2c_d1_20_80 | CHFJPY | D1 | counter=True, lo=20, hi=80 | 1.00% | 261 | 10.4 | 52% | -484 | -99 | 107 | 0.69 | ok |
| 743 | b6 | rsi2c_d1_20_80 | EURJPY | D1 | counter=True, lo=20, hi=80 | 1.25% | 868 | 34.7 | 60% | -537 | -132 | 102 | 0.69 | ok |
| 744 | b6 | rsi2c_d1_20_80 | GBPJPY | D1 | counter=True, lo=20, hi=80 | 1.25% | 1001 | 40.0 | 72% | -490 | -125 | 103 | 0.69 | ok |
| 745 | b6 | rsi2c_d1_20_80 | NZDJPY | D1 | counter=True, lo=20, hi=80 | 1.00% | -42 | -1.7 | 20% | -221 | -96 | 23 | 0.61 | ok |
| 746 | b6 | rsi2c_d1_20_80 | USDJPY | D1 | counter=True, lo=20, hi=80 | 1.25% | 765 | 30.6 | 68% | -558 | -126 | 105 | 0.64 | ok |
| 747 | b6 | rsi2c_d1_5_95 | AUDJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 509 | 20.4 | 64% | -477 | -198 | 37 | 0.65 | ok |
| 748 | b6 | rsi2c_d1_5_95 | CADJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 692 | 27.7 | 56% | -423 | -178 | 27 | 0.74 | ok |
| 749 | b6 | rsi2c_d1_5_95 | CHFJPY | D1 | counter=True, lo=5, hi=95 | 1.50% | -10 | -0.4 | 52% | -577 | -169 | 33 | 0.64 | ok |
| 750 | b6 | rsi2c_d1_5_95 | EURJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 1330 | 53.2 | 52% | -386 | -189 | 33 | 0.67 | ok |
| 751 | b6 | rsi2c_d1_5_95 | GBPJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 964 | 38.6 | 68% | -496 | -203 | 38 | 0.79 | ok |
| 752 | b6 | rsi2c_d1_5_95 | NZDJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 126 | 5.0 | 56% | -513 | -197 | 34 | 0.65 | ok |
| 753 | b6 | rsi2c_d1_5_95 | USDJPY | D1 | counter=True, lo=5, hi=95 | 2.00% | 1211 | 48.4 | 68% | -403 | -193 | 34 | 0.74 | ok |
| 754 | b6 | rsi2c_d1_ex10 | AUDJPY | D1 | counter=True, exit_n=10 | 1.00% | 298 | 11.9 | 68% | -497 | -100 | 64 | 0.64 | ok |
| 755 | b6 | rsi2c_d1_ex10 | CADJPY | D1 | counter=True, exit_n=10 | 2.00% | 951 | 38.1 | 68% | -598 | -198 | 53 | 0.68 | ok |
| 756 | b6 | rsi2c_d1_ex10 | CHFJPY | D1 | counter=True, exit_n=10 | 1.25% | 346 | 13.9 | 60% | -534 | -135 | 58 | 0.67 | ok |
| 757 | b6 | rsi2c_d1_ex10 | EURJPY | D1 | counter=True, exit_n=10 | 1.50% | 1359 | 54.4 | 72% | -463 | -148 | 59 | 0.71 | ok |
| 758 | b6 | rsi2c_d1_ex10 | GBPJPY | D1 | counter=True, exit_n=10 | 2.00% | 1960 | 78.4 | 72% | -596 | -203 | 59 | 0.75 | ok |
| 759 | b6 | rsi2c_d1_ex10 | NZDJPY | D1 | counter=True, exit_n=10 | 1.25% | 247 | 9.9 | 40% | -532 | -122 | 47 | 0.64 | ok |
| 760 | b6 | rsi2c_d1_ex10 | USDJPY | D1 | counter=True, exit_n=10 | 2.00% | 2458 | 98.3 | 60% | -424 | -227 | 60 | 0.70 | ok |
| 761 | b6 | rsi2c_d1_ex3 | AUDJPY | D1 | counter=True, exit_n=3 | 0.75% | -334 | -13.4 | 56% | -556 | -71 | 70 | 0.59 | ok |
| 762 | b6 | rsi2c_d1_ex3 | CADJPY | D1 | counter=True, exit_n=3 | 1.50% | 374 | 15.0 | 56% | -571 | -151 | 59 | 0.66 | ok |
| 763 | b6 | rsi2c_d1_ex3 | CHFJPY | D1 | counter=True, exit_n=3 | 2.00% | 95 | 3.8 | 64% | -592 | -219 | 64 | 0.66 | ok |
| 764 | b6 | rsi2c_d1_ex3 | EURJPY | D1 | counter=True, exit_n=3 | 2.00% | 1320 | 52.8 | 64% | -469 | -193 | 66 | 0.68 | ok |
| 765 | b6 | rsi2c_d1_ex3 | GBPJPY | D1 | counter=True, exit_n=3 | 2.00% | 1012 | 40.5 | 64% | -458 | -203 | 66 | 0.71 | ok |
| 766 | b6 | rsi2c_d1_ex3 | NZDJPY | D1 | counter=True, exit_n=3 | 1.50% | 90 | 3.6 | 64% | -530 | -142 | 66 | 0.67 | ok |
| 767 | b6 | rsi2c_d1_ex3 | USDJPY | D1 | counter=True, exit_n=3 | 2.00% | 1053 | 42.1 | 60% | -461 | -193 | 66 | 0.67 | ok |
| 768 | b6 | rsi2c_d1_hold5 | AUDJPY | D1 | counter=True, max_hold=5 | 1.00% | 105 | 4.2 | 64% | -516 | -100 | 71 | 0.65 | ok |
| 769 | b6 | rsi2c_d1_hold5 | CADJPY | D1 | counter=True, max_hold=5 | 1.50% | 782 | 31.3 | 76% | -528 | -151 | 59 | 0.71 | ok |
| 770 | b6 | rsi2c_d1_hold5 | CHFJPY | D1 | counter=True, max_hold=5 | 1.50% | 299 | 11.9 | 64% | -469 | -169 | 63 | 0.68 | ok |
| 771 | b6 | rsi2c_d1_hold5 | EURJPY | D1 | counter=True, max_hold=5 | 2.00% | 1464 | 58.5 | 60% | -580 | -214 | 63 | 0.68 | ok |
| 772 | b6 | rsi2c_d1_hold5 | GBPJPY | D1 | counter=True, max_hold=5 | 2.00% | 960 | 38.4 | 64% | -510 | -203 | 65 | 0.69 | ok |
| 773 | b6 | rsi2c_d1_hold5 | NZDJPY | D1 | counter=True, max_hold=5 | 1.25% | -8 | -0.3 | 48% | -528 | -122 | 53 | 0.60 | ok |
| 774 | b6 | rsi2c_d1_hold5 | USDJPY | D1 | counter=True, max_hold=5 | 2.00% | 1393 | 55.7 | 56% | -541 | -193 | 64 | 0.66 | ok |
| 775 | b6 | rsi2c_d1_long | AUDJPY | D1 | counter=True, side=long | 1.00% | -78 | -3.1 | 56% | -480 | -100 | 31 | 0.58 | ok |
| 776 | b6 | rsi2c_d1_long | CADJPY | D1 | counter=True, side=long | 1.50% | 147 | 5.9 | 60% | -504 | -151 | 25 | 0.68 | ok |
| 777 | b6 | rsi2c_d1_long | CHFJPY | D1 | counter=True, side=long | 1.50% | 189 | 7.6 | 52% | -436 | -169 | 23 | 0.65 | ok |
| 778 | b6 | rsi2c_d1_long | EURJPY | D1 | counter=True, side=long | 2.00% | 256 | 10.2 | 48% | -552 | -214 | 25 | 0.68 | ok |
| 779 | b6 | rsi2c_d1_long | GBPJPY | D1 | counter=True, side=long | 2.00% | 116 | 4.6 | 48% | -549 | -203 | 25 | 0.68 | ok |
| 780 | b6 | rsi2c_d1_long | NZDJPY | D1 | counter=True, side=long | 1.50% | -453 | -18.1 | 52% | -589 | -142 | 27 | 0.59 | ok |
| 781 | b6 | rsi2c_d1_long | USDJPY | D1 | counter=True, side=long | 2.00% | 360 | 14.4 | 44% | -521 | -193 | 24 | 0.71 | ok |
| 782 | b6 | rsi2c_d1_short | AUDJPY | D1 | counter=True, side=short | 2.00% | 417 | 16.7 | 60% | -533 | -168 | 36 | 0.67 | ok |
| 783 | b6 | rsi2c_d1_short | CADJPY | D1 | counter=True, side=short | 2.00% | 638 | 25.5 | 52% | -347 | -143 | 31 | 0.71 | ok |
| 784 | b6 | rsi2c_d1_short | CHFJPY | D1 | counter=True, side=short | 1.50% | 144 | 5.8 | 68% | -597 | -109 | 39 | 0.74 | ok |
| 785 | b6 | rsi2c_d1_short | EURJPY | D1 | counter=True, side=short | 2.00% | 1233 | 49.3 | 60% | -310 | -126 | 35 | 0.66 | ok |
| 786 | b6 | rsi2c_d1_short | GBPJPY | D1 | counter=True, side=short | 2.00% | 1070 | 42.8 | 60% | -274 | -141 | 39 | 0.74 | ok |
| 787 | b6 | rsi2c_d1_short | NZDJPY | D1 | counter=True, side=short | 2.00% | 881 | 35.3 | 56% | -372 | -164 | 36 | 0.67 | ok |
| 788 | b6 | rsi2c_d1_short | USDJPY | D1 | counter=True, side=short | 2.00% | 1104 | 44.2 | 60% | -382 | -147 | 38 | 0.68 | ok |
| 789 | b6 | rsi2c_d1_sl1.0 | AUDJPY | D1 | counter=True, sl_atr=1.0 | 0.75% | 460 | 18.4 | 56% | -584 | -98 | 86 | 0.58 | ok |
| 790 | b6 | rsi2c_d1_sl1.0 | CADJPY | D1 | counter=True, sl_atr=1.0 | 0.75% | 50 | 2.0 | 60% | -567 | -106 | 69 | 0.49 | ok |
| 791 | b6 | rsi2c_d1_sl1.0 | CHFJPY | D1 | counter=True, sl_atr=1.0 | 0.75% | 181 | 7.2 | 60% | -461 | -92 | 81 | 0.62 | ok |
| 792 | b6 | rsi2c_d1_sl1.0 | EURJPY | D1 | counter=True, sl_atr=1.0 | 1.00% | 680 | 27.2 | 60% | -582 | -156 | 82 | 0.55 | ok |
| 793 | b6 | rsi2c_d1_sl1.0 | GBPJPY | D1 | counter=True, sl_atr=1.0 | 1.25% | 1316 | 52.6 | 68% | -549 | -180 | 80 | 0.60 | ok |
| 794 | b6 | rsi2c_d1_sl1.0 | NZDJPY | D1 | counter=True, sl_atr=1.0 | 0.50% | -170 | -6.8 | 4% | -208 | -48 | 13 | 0.46 | ok |
| 795 | b6 | rsi2c_d1_sl1.0 | USDJPY | D1 | counter=True, sl_atr=1.0 | 1.25% | 1836 | 73.5 | 60% | -558 | -160 | 79 | 0.59 | ok |
| 796 | b6 | rsi2c_d1_sl1.5 | AUDJPY | D1 | counter=True, sl_atr=1.5 | 0.75% | 398 | 15.9 | 64% | -482 | -76 | 74 | 0.65 | ok |
| 797 | b6 | rsi2c_d1_sl1.5 | CADJPY | D1 | counter=True, sl_atr=1.5 | 1.25% | 729 | 29.1 | 64% | -558 | -125 | 59 | 0.64 | ok |
| 798 | b6 | rsi2c_d1_sl1.5 | CHFJPY | D1 | counter=True, sl_atr=1.5 | 1.00% | 203 | 8.1 | 64% | -487 | -105 | 70 | 0.69 | ok |
| 799 | b6 | rsi2c_d1_sl1.5 | EURJPY | D1 | counter=True, sl_atr=1.5 | 1.25% | 844 | 33.8 | 60% | -503 | -165 | 68 | 0.62 | ok |
| 800 | b6 | rsi2c_d1_sl1.5 | GBPJPY | D1 | counter=True, sl_atr=1.5 | 1.50% | 1054 | 42.2 | 68% | -574 | -184 | 68 | 0.66 | ok |
| 801 | b6 | rsi2c_d1_sl1.5 | NZDJPY | D1 | counter=True, sl_atr=1.5 | 0.75% | 135 | 5.4 | 24% | -156 | -71 | 18 | 0.67 | ok |
| 802 | b6 | rsi2c_d1_sl1.5 | USDJPY | D1 | counter=True, sl_atr=1.5 | 1.25% | 977 | 39.1 | 60% | -515 | -143 | 70 | 0.66 | ok |
| 803 | b6 | rsi2c_d1_sl3.0 | AUDJPY | D1 | counter=True, sl_atr=3.0 | 1.50% | 451 | 18.0 | 68% | -529 | -146 | 64 | 0.67 | ok |
| 804 | b6 | rsi2c_d1_sl3.0 | CADJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | 618 | 24.7 | 76% | -536 | -186 | 51 | 0.69 | ok |
| 805 | b6 | rsi2c_d1_sl3.0 | CHFJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | 238 | 9.5 | 76% | -403 | -195 | 59 | 0.71 | ok |
| 806 | b6 | rsi2c_d1_sl3.0 | EURJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | 725 | 29.0 | 60% | -464 | -198 | 57 | 0.67 | ok |
| 807 | b6 | rsi2c_d1_sl3.0 | GBPJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | 939 | 37.6 | 72% | -352 | -186 | 58 | 0.72 | ok |
| 808 | b6 | rsi2c_d1_sl3.0 | NZDJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | -38 | -1.5 | 60% | -552 | -132 | 49 | 0.59 | ok |
| 809 | b6 | rsi2c_d1_sl3.0 | USDJPY | D1 | counter=True, sl_atr=3.0 | 2.00% | 953 | 38.1 | 60% | -311 | -147 | 56 | 0.68 | ok |
| 810 | b6 | rsi2t_d1_sma100 | AUDJPY | D1 | trend_n=100 | 2.00% | 679 | 27.2 | 56% | -537 | -200 | 21 | 0.71 | ok |
| 811 | b6 | rsi2t_d1_sma100 | CADJPY | D1 | trend_n=100 | 2.00% | 630 | 25.2 | 48% | -230 | -143 | 17 | 0.76 | ok |
| 812 | b6 | rsi2t_d1_sma100 | CHFJPY | D1 | trend_n=100 | 2.00% | 340 | 13.6 | 48% | -285 | -219 | 18 | 0.78 | ok |
| 813 | b6 | rsi2t_d1_sma100 | EURJPY | D1 | trend_n=100 | 2.00% | 714 | 28.6 | 36% | -227 | -143 | 16 | 0.69 | ok |
| 814 | b6 | rsi2t_d1_sma100 | GBPJPY | D1 | trend_n=100 | 2.00% | 928 | 37.1 | 52% | -191 | -191 | 17 | 0.94 | ok |
| 815 | b6 | rsi2t_d1_sma100 | NZDJPY | D1 | trend_n=100 | 2.00% | 173 | 6.9 | 44% | -454 | -148 | 20 | 0.65 | ok |
| 816 | b6 | rsi2t_d1_sma100 | USDJPY | D1 | trend_n=100 | 2.00% | 664 | 26.5 | 40% | -362 | -193 | 18 | 0.83 | ok |
| 817 | b6 | rsi2t_d1_sma50 | AUDJPY | D1 | trend_n=50 | 2.00% | 708 | 28.3 | 60% | -485 | -200 | 20 | 0.75 | ok |
| 818 | b6 | rsi2t_d1_sma50 | CADJPY | D1 | trend_n=50 | 2.00% | 13 | 0.5 | 24% | -375 | -198 | 14 | 0.57 | ok |
| 819 | b6 | rsi2t_d1_sma50 | CHFJPY | D1 | trend_n=50 | 2.00% | 615 | 24.6 | 56% | -312 | -219 | 17 | 0.88 | ok |
| 820 | b6 | rsi2t_d1_sma50 | EURJPY | D1 | trend_n=50 | 2.00% | 770 | 30.8 | 36% | -165 | -143 | 13 | 0.77 | ok |
| 821 | b6 | rsi2t_d1_sma50 | GBPJPY | D1 | trend_n=50 | 2.00% | 390 | 15.6 | 36% | -227 | -191 | 13 | 0.77 | ok |
| 822 | b6 | rsi2t_d1_sma50 | NZDJPY | D1 | trend_n=50 | 2.00% | 177 | 7.1 | 32% | -440 | -148 | 13 | 0.69 | ok |
| 823 | b6 | rsi2t_d1_sma50 | USDJPY | D1 | trend_n=50 | 2.00% | 43 | 1.7 | 28% | -250 | -177 | 12 | 0.67 | ok |
| 824 | b6 | rsi3c_d1 | AUDJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 572 | 22.9 | 56% | -508 | -198 | 45 | 0.62 | ok |
| 825 | b6 | rsi3c_d1 | CADJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1077 | 43.1 | 60% | -410 | -189 | 38 | 0.79 | ok |
| 826 | b6 | rsi3c_d1 | CHFJPY | D1 | counter=True, n=3, lo=15, hi=85 | 1.25% | -59 | -2.3 | 60% | -526 | -135 | 43 | 0.65 | ok |
| 827 | b6 | rsi3c_d1 | EURJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 963 | 38.5 | 56% | -579 | -214 | 42 | 0.60 | ok |
| 828 | b6 | rsi3c_d1 | GBPJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1115 | 44.6 | 68% | -520 | -203 | 47 | 0.77 | ok |
| 829 | b6 | rsi3c_d1 | NZDJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | -56 | -2.3 | 56% | -538 | -193 | 41 | 0.61 | ok |
| 830 | b6 | rsi3c_d1 | USDJPY | D1 | counter=True, n=3, lo=15, hi=85 | 2.00% | 1067 | 42.7 | 60% | -403 | -193 | 46 | 0.67 | ok |
<!-- RESULTS END -->

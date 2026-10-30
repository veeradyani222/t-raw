# search3 / metals (round 3, 2026-10-30)

Group: XAUUSD XAGUSD XPTUSD XPDUSD on M30 / H1 / H4 / D1. Judge: `research/prop/harness.py`,
`PROP_OOS=1`, scoring window 2024-10-20..last bar. No statistical gates; look-ahead check +
300/800 rule only. Scripts in this folder:

| file | what |
|---|---|
| `study.py` / `study.log` | market study + data-quality report (all four metals) |
| `strategies.py` | every `build_<name>(df, **params)` (17 ideas, see docstring) |
| `grids.py` | parameter grids per idea (17 batches) |
| `runner.py` | scorer (serial / Pool(2)), cost patches, bad-tick cleaner, appends `results.jsonl` |
| `report.py` | `top` summary, `md` full table (`all_runs.md`), `idea <name>` drill-down |
| `causal_check.py` | mandatory look-ahead check + re-score of the shortlisted candidates |
| `smoke.py` | builder smoke test + 3-cut causality check |
| `candidates.json` / `candidates_checked.json` | the shortlist in / out of the look-ahead check |

## Costs used (NOTES on monkeypatching)

Harness already has XAUUSD (spread floor 0.30, pip 0.1) and XAGUSD (0.03, pip 0.01), both with the
$14/lot round-trip commission. XPTUSD / XPDUSD are missing, so `runner.py` patches:

* `H.SPREAD_FLOOR["XPTUSD"] = 2.0`, `["XPDUSD"] = 3.0` (median bar spread in the window: XPT 2220 pts =
  $2.22 = 0.14% of price, XPD 3011 pts = $3.01 = 0.25%; harness takes max(floor, bar spread), so the
  wide 00:00-02:00 spreads are still charged in full).
* `H._pip` -> 0.1 for both (slippage unit, same as gold).
* Both added to `H.INDICES` (no commission). Reason: `symbol_specs.json` has contract = 1 oz for
  XPT/XPD (vol_step 0.1), so the $14/100-oz-lot metal commission would become $14/oz (absurd);
  the true ~$0.14/oz is ~0.01% and is dwarfed by the 0.14-0.25% spread.
* Bad ticks: XPTUSD/XPDUSD 2026-10-27 19:00-21:00 have lows of 0.001/0.003 and (XPD) a high of
  48307.9. The patched `H.load` clamps any wick more than 10% beyond the bar body to the body.
  These are the only clamps triggered (reported by `runner.BAD` in `smoke.py`).

Contract sizes (data/search/symbol_specs.json): XAU 100 oz, XAG 5000 oz, XPT 1 oz, XPD 1 oz.

## Data quality (scoring window)

| symbol | D1 bars | flat days (<5% median range) | H1 gaps >3h (weekend ~99 expected) | gaps >60h | zero-volume bars | last bar |
|---|---|---|---|---|---|---|
| XAUUSD | 515 | 0 | 121 | 2 (Christmas / New Year) | 0 | 2026-10-19 22:00 |
| XAGUSD | 516 | 1 (2026-01-01, holiday) | 117 | 2 | 0 | 2026-10-19 22:00 |
| XPTUSD | 525 | 0 | 114 | 2 | 0 | 2026-10-29 22:00 |
| XPDUSD | 525 | 1 (2025-01-23) | 117 | 2 | 0 | 2026-10-29 22:00 |

Extra gaps beyond weekends are the daily 23:00-01:00 CFD close (metals trade 01:00-23:59 server
on this feed; hour-0 and hour-23 bars exist only on part of the days). The two flat days carry no
trades (holiday bars are inside a normal day range of neighbours; no strategy fires on a zero-range
day because every builder needs ATR / a range > 0). The XPT/XPD bad ticks (3 bars) are clamped, not
dropped, so day codes stay intact. XAU/XAG files end 10 days earlier than XPT/XPD (fetch window);
scoring uses what is there.

## Market study (from `study.log`, server = EET, bar-open hours)

Session clock (server): Asia 01-09, London 10-15 (AM fix at 12:30), NY 16:30 open, PM fix 17:00,
CME close 23:00.

**Hour-of-day drift.** All four metals rise in Asia and give it back in NY:
mean session log-return (bp/day) Asia / London / NY = gold +11 / +5 / -3, silver +15 / +6 / -6,
platinum +60 / +5 / -8, palladium +86 / +5 / -31. In XPT/XPD most of the Asia number sits in the
01:00 bar (+54 / +72 bp) and is the mirror of a negative overnight gap (-48 / -60 bp mean) -> it
is the bid/ask discontinuity at the 01:00 reopen with a 3-10x spread, not a tradable edge
(gap -> day corr -0.29 / -0.36, i.e. the gap closes). This matches the CBS "hat-shaped"
intraday seasonality in gold (rises in eastern hours, falls in western hours), whose authors also
report the edge mostly disappears after transaction costs.

**Volatility clock.** Range peaks 15:00-17:00 server (NY open + PM fix): gold 56-61 bp/h vs 28-38 in
Asia; silver 107-125 vs 56-99; PGMs 112-139 vs 55-105. 23:00 and 00:00 bars are thin.

**Weekday.** Silver and the PGMs earn most of their drift on Monday (silver Mon +6175 bp total vs
Thu -2276; palladium Mon 14043 vs Fri 2315). Palladium Tuesday range is distorted by one bad tick
(961 bp/h) -> clamped.

**Persistence.** Autocorrelation of bar returns is negative everywhere except gold H4 (ac1 +0.003,
VR5 1.08 = mild trending): gold H1 ac1 -0.017, D1 -0.008 / VR5 0.91; silver H4 ac1 -0.075; platinum
D1 ac1 -0.079 / VR5 0.87; palladium D1 ac1 -0.096 / VR5 0.81. The PGMs are mean-reverting on every
timeframe, which argues against breakout logic and for fades / reversals there.

**Prior-day levels.** PDH is touched on 51-53% of days (gold 53%, silver 51%, platinum 53%,
palladium 48%), PDL on 43-51%, both on 10-15%; the close ends outside the prior-day range on
48-49% (gold, silver) and 39-40% (PGMs) of days.

**Fix behaviour.** AM fix: the 11:00-12:30 move is reversed after the fix (corr -0.09 silver,
-0.18 platinum, -0.14 palladium; gold +0.005). PM fix: pre-fix (15:30-17:00) slightly negative,
post-fix (17:00-18:30) positive in the PGMs (+8.6 / +10.6 bp) and flat in gold / silver. The old
"PM fix sells off" finding (Abrantes-Metz & Metz 2014) is not visible in 2024-26 data.

**Asian range.** Asia (01-09) range is 55-64% of the day range; the day breaks the Asian high on
63-70% of days and the Asian low on 49-55%; both sides are taken on 22-26% of days. On one-sided
break days, the close stays outside the broken side 59-70% of the time -> a structural reason the
Asian-range breakout works on gold.

**Cross-metal.** Gold/silver ratio and Pt/Pd ratio were tested as z-score reversions (idea
`ratio_z`) and as leader-lag catch-up / fade (`lag_catchup`).

## Sources (practitioner rules tested)

* mql5 blog 777540 "London Breakout on Gold: 3.7 years of backtests" (03:00-08:00 server range,
  OCO stops, SL opposite side capped 0.6%, TP 2.5R, BE at 1.5R, range filter 0.30-1.60%, flat
  21:00, one trade/day; PF 1.37-1.38, 715 trades, DD 17-19% at 1% risk) -> `build_asia_break`,
  window "mql" with its exact rules plus structure-target variants.
  https://www.mql5.com/en/blogs/post/777540
* Unger Academy "Bias pattern on platinum" (short at 04:00, cover at 09:00 exchange time =
  12/13-17/18 server; optional filter: prior session close < the one before) -> `build_session_hold`
  with `prev_day="down"`, batch `unger_pt`. https://ungeracademy.com/blog/bias-pattern-in-platinum-how-to-exploit-it-with-a-2-line-script-backtest-and-optimization
* Unger Academy platinum H1 channel breakout (6-bar long / 2-bar short) -> `build_channel_pt`.
* Donati & Jung (CBS) "Gold price dynamics around the clock": hat-shaped intraday seasonality,
  Sharpe up to 1.61 before costs, under-performs after costs -> `build_session_hold` long Asia /
  short West. https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/
* Abrantes-Metz & Metz 2014 (Bloomberg / LBMA Alchemist rebuttal): PM-fix downward spikes ->
  `build_fix_fade` (fade / follow the pre-fix run after 12:30 and 17:00).
  https://www.lbma.org.uk/alchemist/issue-73/has-there-been-a-decade-of-london-pm-gold-fixing-manipulation
* QuantConnect / TradingView gold-silver ratio scripts (60-day z, enter +-2, exit +-0.5; 90/10
  percentile bands) -> `build_ratio_z` (z_n 100/200, z_in 2.0/2.5, z_out 0.5).
* Unger-style false-break of prior-day / prior-week high-low -> `build_pd_sweep`; NR4/NR7 and
  inside-day contraction (Crabel) -> `build_nr_break`; round-number break / fade ->
  `build_round_level`.

## Results

### Volume

2392 scored runs, 0 errors, 455 runs with best_risk set and avg_month > 0, 17 ideas,
4 symbols x M30/H1/H4/D1 (grid per idea in `grids.py`). Full table of every run: `all_runs.md`.

### Idea summary (runs, candidates, mean / median / best avg_month $)

| idea | runs | cands | mean_am | med_am | best |
|---|---|---|---|---|---|
| nr_break | 72 | 32 | 6.8 | -6.8 | 107.8 |
| session_hold | 448 | 99 | -21.8 | -15.0 | 106.9 |
| channel_pt | 208 | 33 | -64.5 | -44.6 | 101.2 |
| wopen_retest | 64 | 15 | -5.6 | -10.1 | 83.1 |
| ratio_z | 112 | 45 | 0.5 | -4.0 | 80.3 |
| asia_break | 384 | 49 | -72.0 | -62.7 | 75.9 |
| pd_break | 144 | 51 | -26.9 | -30.2 | 69.3 |
| d1_reversal | 160 | 55 | -4.5 | -6.5 | 52.5 |
| lag_catchup | 80 | 19 | -6.2 | -10.2 | 47.0 |
| round_level | 128 | 5 | -474.0 | -437.4 | 41.7 |
| asia_dip | 144 | 28 | -6.5 | -11.1 | 37.5 |
| gap_fade | 96 | 11 | -18.7 | -13.8 | 26.5 |
| fix_fade | 128 | 6 | -54.9 | -48.2 | 25.4 |
| late_day | 96 | 7 | -7.7 | 0.0 | 22.8 |
| asia_fade | 48 | 0 | -84.1 | -84.2 | 8.8 |
| pd_sweep | 80 | 0 | -38.9 | -32.7 | -3.5 |

### Per symbol

| symbol | runs | cands | best | mean |
|---|---|---|---|---|
| XAGUSD | 594 | 119 | 107.8 | -39.8 |
| XAUUSD | 594 | 292 | 106.9 | 2.2 |
| XPDUSD | 610 | 22 | 34.8 | -99.2 |
| XPTUSD | 594 | 22 | 28.0 | -86.3 |

The PGMs are nearly dead after costs: the 0.14-0.25% spread (3-10x wider at the 01:00 reopen) eats
every intraday idea; only the overnight hold (23->09, prior-day-up filter), the Pt/Pd ratio
z-score on H4 and D1 big-day fades reach positive avg_month, all with low trade counts. The Unger
platinum morning short (12/13->17/18 server) is negative on this feed in every variant
(`unger_pt` batch), with or without the prior-day-down filter.

### Top 40 runs by avg_month (candidates only)

| batch | name | symbol | tf | best_risk | avg_month | net | green | max_dd | worst_day | trades | win |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nr_break | nr_7_mid_r:2 | XAGUSD | H1 | 0.0125 | 107.8 | 2694.6 | 0.68 | -418.4 | -122.9 | 55 | 0.6 |
| session_hold | sh_long_23-9_s3.0_d(0, 1) | XAUUSD | H1 | 0.02 | 106.9 | 2672.5 | 0.52 | -575.2 | -197.5 | 128 | 0.594 |
| session_hold | sh_long_23-9_s1.5_d(0, 1) | XAUUSD | H1 | 0.01 | 103.3 | 2581.5 | 0.48 | -525.8 | -99.8 | 128 | 0.578 |
| nr_break | nr_4_mid_r:2 | XAGUSD | H1 | 0.0125 | 101.3 | 2531.8 | 0.72 | -529.5 | -137.8 | 89 | 0.573 |
| channel | ch_24-24_s1.5_tp2.5_long | XAUUSD | H1 | 0.005 | 101.2 | 2529.8 | 0.64 | -522.5 | -121.2 | 257 | 0.385 |
| nr_break | nr_7_mid_range | XAGUSD | H1 | 0.0125 | 100.9 | 2523.0 | 0.68 | -418.4 | -122.9 | 55 | 0.618 |
| session_hold | sh_long_21-3_s3.0_dNone | XAUUSD | H1 | 0.01 | 96.9 | 2422.6 | 0.68 | -578.3 | -154.3 | 485 | 0.573 |
| session_hold | sh_long_21-3_s3.0_d(0, 1) | XAUUSD | H1 | 0.015 | 94.1 | 2351.5 | 0.68 | -564.2 | -167.3 | 203 | 0.635 |
| nr_break | nr_4_mid_range | XAGUSD | H1 | 0.0125 | 94.0 | 2350.5 | 0.68 | -533.1 | -137.8 | 89 | 0.584 |
| unger_pt | up_long_23-9_s3.0_pdup | XAUUSD | H1 | 0.0125 | 89.0 | 2224.8 | 0.52 | -594.1 | -126.8 | 187 | 0.578 |
| channel | ch_12-4_s2.5_tp2.5_long | XAUUSD | H1 | 0.005 | 87.9 | 2197.4 | 0.56 | -409.1 | -83.8 | 243 | 0.502 |
| wopen | wo_d1.0_t0.2_r:2 | XAUUSD | H4 | 0.0125 | 83.1 | 2077.0 | 0.64 | -525.6 | -169.4 | 38 | 0.526 |
| ratio_z | rz_XPTUSD_n200_z2.5_zout0.5 | XAUUSD | H4 | 0.015 | 80.3 | 2008.5 | 0.32 | -517.6 | -163.5 | 19 | 0.526 |
| asia_break | ab_mql_range_mid_mr0.3 | XAUUSD | M30 | 0.005 | 75.9 | 1896.5 | 0.72 | -442.7 | -49.8 | 356 | 0.489 |
| session_hold | sh_long_2-15_s3.0_d(0,) | XAUUSD | H1 | 0.0125 | 75.6 | 1890.2 | 0.64 | -596.9 | -121.9 | 102 | 0.578 |
| nr_break | nr_inside_atr:1.0_r:2 | XAUUSD | H1 | 0.01 | 72.9 | 1822.3 | 0.64 | -577.7 | -99.3 | 56 | 0.482 |
| nr_break | nr_7_other_range | XAGUSD | H1 | 0.02 | 72.3 | 1808.2 | 0.72 | -529.6 | -197.9 | 55 | 0.636 |
| channel | ch_24-24_s1.5_tp1.5_long | XAUUSD | H1 | 0.005 | 71.6 | 1791.1 | 0.56 | -561.2 | -92.4 | 325 | 0.471 |
| asia_break | ab_mql_range_mid_mr0.0 | XAUUSD | M30 | 0.005 | 71.2 | 1780.8 | 0.68 | -541.8 | -49.8 | 382 | 0.487 |
| session_hold | sh_long_2-9_s3.0_d(0, 1, 2) | XAUUSD | H1 | 0.01 | 71.2 | 1779.7 | 0.56 | -531.1 | -98.8 | 297 | 0.515 |
| session_hold | sh_long_21-3_s3.0_d(0, 1, 2) | XAUUSD | H1 | 0.01 | 70.0 | 1751.2 | 0.64 | -469.2 | -154.3 | 297 | 0.616 |
| pd_break | pb_atr:1.0_range_be1.0 | XAUUSD | H1 | 0.005 | 69.3 | 1731.5 | 0.64 | -474.1 | -49.9 | 216 | 0.361 |
| asia_break | ab_mql_range_range_mr0.3 | XAUUSD | M30 | 0.005 | 68.9 | 1721.9 | 0.72 | -433.4 | -49.9 | 356 | 0.531 |
| session_hold | sh_long_2-9_s3.0_d(0,) | XAUUSD | H1 | 0.015 | 67.3 | 1681.3 | 0.68 | -506.8 | -149.6 | 103 | 0.524 |
| ratio_z | rz_XAGUSD_n200_z2.5_zout0.5 | XAUUSD | H1 | 0.0075 | 67.2 | 1680.0 | 0.52 | -514.7 | -149.4 | 70 | 0.443 |
| session_hold | sh_long_23-9_s3.0_dNone | XAUUSD | H1 | 0.0075 | 66.6 | 1664.9 | 0.6 | -358.2 | -73.0 | 289 | 0.55 |
| nr_break | nr_7_other_r:2 | XAGUSD | H1 | 0.02 | 66.2 | 1654.1 | 0.64 | -552.8 | -197.9 | 55 | 0.582 |
| ratio_z | rz_XAGUSD_n100_z2.0 | XAUUSD | H4 | 0.0125 | 63.8 | 1596.2 | 0.48 | -557.8 | -181.0 | 54 | 0.5 |
| session_hold | sh_long_21-3_s3.0_d(0,) | XAUUSD | H1 | 0.02 | 63.5 | 1587.7 | 0.68 | -484.3 | -170.9 | 103 | 0.641 |
| session_hold | sh_long_2-15_s3.0_d(0,) | XAGUSD | H1 | 0.015 | 62.5 | 1561.6 | 0.6 | -470.2 | -142.2 | 91 | 0.626 |
| pd_break | pb_atr:1.0_r:3_be1.0 | XAUUSD | H1 | 0.005 | 61.5 | 1537.4 | 0.64 | -475.2 | -49.9 | 216 | 0.366 |
| channel | ch_12-4_s2.5_tp1.5_long | XAUUSD | H1 | 0.005 | 61.3 | 1531.3 | 0.56 | -481.2 | -83.8 | 282 | 0.507 |
| channel | ch_24-24_s2.5_tp2.5_long | XAUUSD | H1 | 0.005 | 61.3 | 1531.9 | 0.48 | -543.3 | -83.8 | 177 | 0.492 |
| ratio_z | rz_XAGUSD_n200_z2.5_zout0.5 | XAUUSD | H4 | 0.015 | 60.1 | 1502.2 | 0.36 | -573.7 | -240.2 | 23 | 0.391 |
| session_hold | sh_long_23-9_s1.5_d(0, 1, 2) | XAUUSD | H1 | 0.0075 | 59.6 | 1490.2 | 0.44 | -516.3 | -75.0 | 189 | 0.529 |
| pd_break | pb_atr:1.0_range_beNone | XAUUSD | H1 | 0.005 | 58.0 | 1450.2 | 0.68 | -481.9 | -49.9 | 216 | 0.389 |
| session_hold | sh_long_2-15_s3.0_dNone | XAUUSD | H1 | 0.005 | 54.5 | 1363.7 | 0.56 | -309.7 | -50.0 | 306 | 0.578 |
| nr_break | nr_inside_atr:1.0_range | XAUUSD | H1 | 0.005 | 53.5 | 1336.9 | 0.68 | -374.4 | -49.6 | 56 | 0.411 |
| session_hold | sh_long_2-15_s1.5_dNone | XAUUSD | H1 | 0.0025 | 53.0 | 1326.1 | 0.6 | -367.6 | -24.9 | 304 | 0.474 |
| d1_reversal | dr_k0.8_follow_h12_s2.5 | XAUUSD | H4 | 0.01 | 52.5 | 1313.7 | 0.56 | -533.8 | -197.3 | 235 | 0.443 |

### Returned candidates (8, distinct ideas / markets) and the look-ahead check

Look-ahead check: `build(df)` vs `build(df.iloc[:k])` (attrs re-attached) at 5 random k, every
Entry at index < k compared on side/sl/tp/max_hold/exit_hour/manage; all 8 pass with 0 differences.
Every entry has a stop and a defined exit.

| name | symbol | tf | idea | best_risk | avg_month | net | max_dd | worst_day | trades | green | causal_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nr_7_mid_r2_XAGUSD_H1 | XAGUSD | H1 | nr_break | 1.25% | 107.8 | 2694.6 | -418.4 | -122.9 | 55 | 0.68 | True |
| sh_long_21-3_s3.0_dNone_XAUUSD_H1 | XAUUSD | H1 | session_hold | 1.00% | 96.9 | 2422.6 | -578.3 | -154.3 | 485 | 0.68 | True |
| ch_24-24_s1.5_tp2.5_long_XAUUSD_H1 | XAUUSD | H1 | channel_pt | 0.50% | 101.2 | 2529.8 | -522.5 | -121.2 | 257 | 0.64 | True |
| wo_d1.0_t0.2_r2_XAUUSD_H4 | XAUUSD | H4 | wopen_retest | 1.25% | 83.1 | 2077.0 | -525.6 | -169.4 | 38 | 0.64 | True |
| ab_mql_range_mid_mr0.3_XAUUSD_M30 | XAUUSD | M30 | asia_break | 0.50% | 75.9 | 1896.5 | -442.7 | -49.8 | 356 | 0.72 | True |
| pb_atr1.0_range_be1.0_XAUUSD_H1 | XAUUSD | H1 | pd_break | 0.50% | 69.3 | 1731.5 | -474.1 | -49.9 | 216 | 0.64 | True |
| rz_XAGUSD_n200_z2.5_zout0.5_XAUUSD_H1 | XAUUSD | H1 | ratio_z | 0.75% | 67.2 | 1680.0 | -514.7 | -149.4 | 70 | 0.52 | True |
| up_long_23-9_s3.0_pdup_XPDUSD_H1 | XPDUSD | H1 | session_hold | 1.50% | 33.1 | 828.0 | -580.2 | -149.3 | 168 | 0.36 | True |

What each one is:

1. **nr_7_mid_r2 XAGUSD H1** - yesterday was the narrowest of the last 7 days (NR7); first H1 close
   outside yesterday's range between 02:00 and 18:00 goes with the break, stop at the range mid,
   TP 2R, flat 22:00. Silver's compression -> expansion days.
2. **sh_long_21-3_s3.0 XAUUSD H1** - clock drift: buy at the 21:00 bar close, sell at the 03:00
   close (Asia drift, every weekday), ATR(14) x3 stop. 485 trades, 57% win.
3. **ch_24-24_s1.5_tp2.5_long XAUUSD H1** - long-only 24-bar channel breakout (close above the
   prior 24 H1 highs), 1.5 ATR stop, 2.5R target, 24-bar time exit. Gold's H4 trending (VR5 1.08).
4. **wo_d1.0_t0.2_r2 XAUUSD H4** - weekly-open retest: once price is >= 1 ATR from the week open,
   a Tue-Thu bar touching back within 0.2 ATR of the open enters in the week's direction, 1 ATR stop,
   2R target, 12-bar time exit. 38 trades only.
5. **ab_mql_range_mid_mr0.3 XAUUSD M30** - the mql5 London-breakout rule set (03-08 range, break by
   14:00, range filter 0.3-1.6%, flat 21:00) with stop at the range midpoint and a 1x-range
   projection target instead of 2.5R. 356 trades, worst day -$50 at 0.5%.
6. **pb_atr1.0_range_be1.0 XAUUSD H1** - first H1 close of the day beyond PDH/PDL (09:00-18:00),
   1 ATR stop, prior-day-range measured move target, BE at 1R, flat 22:00.
7. **rz_XAGUSD_n200_z2.5_zout0.5 XAUUSD H1** - gold/silver ratio z-score (200 bars): z > 2.5 shorts
   gold, z < -2.5 buys gold; exits when |z| < 0.5, 3R target, 2 ATR stop, 60-bar time stop.
8. **up_long_23-9_s3.0_pdup XPDUSD H1** - palladium overnight hold: buy at 23:00 close when the
   prior day closed above the day before, sell at 09:00, 3 ATR stop. The only palladium idea with
   168 trades and a positive month average; green months just 36%, so the weakest of the eight.

Notes for the owner: the three highest avg_month runs that were NOT returned (sh_long_23-9 d(0,1)
XAUUSD at 2% risk, nr_4 XAGUSD, ch_12-4 XAUUSD) are parameter neighbours of candidates 2, 1 and 3.
Everything here is scored on one window with no out-of-sample split, as instructed.

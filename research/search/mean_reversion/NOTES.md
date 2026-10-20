# mean_reversion family: notes (in-sample 2015-01 .. 2023-12 only)

## Short version
Mean reversion with a stop and a time exit **does not work on FX or metals at H1/H4** once
costs are included. Across 17 FX pairs the median trade loses 0.04-0.10 R. It **does work,
weakly but consistently, when buying dips in stock indices (US30, US500, DE40) on D1 and H4**.
The edge is small. The best robust configs make **$15-40 a month at the highest safe risk**
on a $10k account. That is far below what a fast prop pass needs: the median time to clear
phase 1 + phase 2 is 600 to 2,200 days, although no challenge window ever breached.
OOS was never touched.

## Method
1. `screen.py` is a fast re-implementation of the harness fill rules in R units. It covers
   one position, the stop-first rule and gap fills, and leaves out the daily block and lot
   rounding. It was checked against `harness.simulate`: gold H4 stoch gave 123 vs 127 trades
   and 4.0R vs 3.8R; EURUSD H1 rsi2 gave 2521 vs 2595 trades and -104.5R vs -108.1R.
   It ranks variants roughly 100x faster.
2. Broad screen (`sweep.py` -> `screen.csv`): 9 builders x ~90 variants x 23 symbols x
   H1/H4/D1 = 54,648 variants.
3. Fine screens of long-only dips on indices: `sweep_fine.py` -> `fine_idx.csv` (55k),
   `sweep_combo.py` -> `combo_idx.csv`, daily-trend + intraday RSI2 (`htf_idx.csv`),
   exit variants (`combo_exits.csv`) and the classic IBS (`ibs_d1.csv`).
   Configs were ranked by the WORST of US30/US500/DE40, not the best.
4. Every candidate and its neighbours were scored with the judge `research.prop.harness`
   (`run.py` -> `results.csv`; 170 runs). `results_g1_partial.csv` has 98 more baseline
   runs from the first grid. That grid died when the shared machine ran out of RAM; its
   `r_at_025` column is meaningless because D1 trades at 0.25% risk round to 0 lots.
   Total: 268 harness-scored runs, 236 of them with a safe risk level.

Note: USTEC data starts 2022-07, so it has only 18 in-sample months. USTEC results look large
(zscore H4 $88/mo, dip_combo D1 $52/mo) but rest on 12-52 trades, so they are ignored.

## What failed and why
- **FX H1/H4 (all 17 pairs, including the "range" crosses EURGBP/EURCHF/AUDCAD/GBPCHF):** the
  median avgR per builder is -0.04 to -0.14 R. The gross reversion edge is about zero, and the
  spread plus commission (~0.05-0.1 R at a 2-3.5 ATR stop) makes it negative. The ADX/session
  ideas were never worth pursuing on top of a negative base.
- **FX D1:** RSI(2)/RSI(3) "both sides with a 200-MA filter" is positive on 14-15 of 17 pairs
  (the most consistent FX finding), but at ~0.03 R/trade and ~6 trades/yr that is only
  $1-3/month. Not a candidate.
- **Session-VWAP fades (H1):** negative on FX. On indices the long side is weak. DE40 short
  fades looked good (6.4 R/DD) but only on one symbol and one setting.
- **Gold/silver:** they trend, so fading works only on the long side at D1 (stoch(30) < 20).
  Best harness result: XAUUSD D1 stoch $9/mo, XAGUSD $8/mo. Neighbours range from $4-9 and
  one silver variant is negative. Too weak to recommend; gold belongs to the trend/breakout
  families.
- **Index H1** (RSI2, %R, IBS, VWAP, RSI2 + daily trend): about zero after costs. Intraday
  noise is too large compared with the dip edge.
- **Classic IBS (D1, hold 1-5 days):** gone after CFD costs (US500 +5R in 9 years, US30 ~0,
  DE40 ~0, XAG strongly negative).
- **Single-symbol "winners"** do not carry over to other indices. Example: US500 H4 %R(10) < -85
  gives 51R, but the same rule on DE40 is negative at every neighbour. Not a candidate.
- **More trades (dip_combo need=1):** frequency doubles, the edge per trade falls to zero, and
  avg_month drops to $1-8.

## What worked (and how robust it is)
- **dip_combo D1** (build_dip_combo): at least 2 of 3 oversold votes [%R(10) < -90, close at a
  5-day low, IBS < 0.2], above the 200-day SMA, 3-ATR stop. Positive on US30, US500 and DE40 for
  every neighbour tested: %R length 7/10/14, threshold -80/-90, IBS 0.1-0.3, stop 2-4.5 ATR,
  hold 5-16, exits prev-high/%R/MA10/time, trend 100/200. Two weak spots: need=3 (too few
  trades) and trend=0. With a time-only exit (hold 8) it makes $17-33/mo, versus $14-20 with
  the prev-high exit. Holding longer captures index drift, so part of this is long beta, not
  pure reversion. The best risk is usually the 2% cap, so the strategy is limited by trade
  count (~9/yr), not by drawdown.
- **nlow US30 H4**: close at a 10-bar low above the 200-bar SMA, stop 3.5 ATR, hold 24. $40/mo,
  with neighbours on US30 at $27-40. It is positive on US500 ($5-20) and flat on DE40. 2022-23
  were flat or negative, so watch for decay.
- **zscore H4** z(20) < -2, exit z > -0.5, no trend filter, stop 3 ATR: $13-15/mo on all three
  indices, green months 56-63%. The z thresholds 1.5 and 2.5 and length 30 are weaker but mostly
  positive.

## Lessons
1. The cost line decides MR. Any H1 FX fade needs > 0.1 R of gross edge per trade and none has
   it. Only the low-cost, upward-drifting index CFDs (no commission) clear it.
2. Long-only on indices: the short side of index MR loses everywhere (median -0.03 to -0.10 R).
3. Rank by the worst symbol in a group; the best symbol is mostly noise.
4. At D1 frequency the 2% harness risk cap binds before the 6% DD cap. A pure MR system cannot
   reach phase-1 +8% quickly. It is better used as a low-correlation sleeve next to the trend /
   breakout strategies.

## Files
strategies.py (builders), screen.py (fast pre-screen), sweep*.py, run.py (harness runner),
grids.py, analyze.py/_rob.py (ranking), *.csv (all raw results), jobs_b*.json (harness batches).

## Every harness-scored run
| grid | name | symbol | tf | params | best_risk | avg_month | max_dd | worst_day | trades |
|---|---|---|---|---|---|---|---|---|---|
| b1_broadtop | stoch | USTEC | H4 | n=14, lo=20, hi=80, trend=0, sides=long, stop_atr=3.5, max_hold=12 | 1.25% | 58.8 | -401.0 | -122.0 | 77 |
| b1_broadtop | nlow | US30 | H4 | n=10, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.50% | 39.7 | -492.0 | -240.0 | 414 |
| b1_broadtop | vwap | DE40 | H1 | dev_atr=2.0, sides=short, stop_atr=2.0, max_hold=24, trend=200 | 1.25% | 26.0 | -501.0 | -152.0 | 133 |
| b1_broadtop | zscore | EURGBP | H4 | n=100, z_in=2.5, trend=0, sides=short, stop_atr=3.5, max_hold=12 | 2.00% | 26.0 | -441.0 | -287.0 | 84 |
| b1_broadtop | bb_fade | DE40 | D1 | n=20, k=2.0, trend=0, sides=long, stop_atr=2.0, max_hold=16 | 1.50% | 25.3 | -470.0 | -203.0 | 67 |
| b1_broadtop | bb_fade | EURUSD | H1 | n=50, k=2.5, trend=200, sides=long, stop_atr=2.0, max_hold=24 | 1.25% | 25.3 | -523.0 | -200.0 | 78 |
| b1_broadtop | wpr | US500 | H4 | n=10, lo=-85, hi=-15, trend=0, sides=long, stop_atr=2.0, max_hold=24 | 0.50% | 23.4 | -565.0 | -149.0 | 619 |
| b1_broadtop | zscore | DE40 | H4 | n=100, z_in=1.5, trend=0, sides=both, stop_atr=3.5, max_hold=24 | 0.75% | 22.1 | -525.0 | -184.0 | 358 |
| b1_broadtop | ibs | USDCAD | D1 | lo=0.1, hi=0.9, trend=0, sides=long, stop_atr=2.0, max_hold=16 | 1.50% | 22.0 | -574.0 | -182.0 | 226 |
| b1_broadtop | wpr | EURCHF | H4 | n=30, lo=-95, hi=-5, trend=200, sides=both, stop_atr=3.5, max_hold=12 | 2.00% | 19.3 | -508.0 | -199.0 | 84 |
| b1_broadtop | stoch | GBPCHF | D1 | n=30, lo=20, hi=80, trend=0, sides=short, stop_atr=2.0, max_hold=16 | 1.25% | 17.5 | -576.0 | -146.0 | 69 |
| b1_broadtop | ibs | US500 | D1 | lo=0.2, hi=0.8, trend=0, sides=long, stop_atr=3.5, max_hold=16 | 1.50% | 16.4 | -469.0 | -148.0 | 295 |
| b1_broadtop | wpr | AUDUSD | D1 | n=10, lo=-95, hi=-5, trend=0, sides=short, stop_atr=2.0, max_hold=8 | 1.50% | 16.3 | -488.0 | -170.0 | 76 |
| b1_broadtop | ibs | EURCHF | D1 | lo=0.2, hi=0.8, trend=0, sides=short, stop_atr=3.5, max_hold=8 | 2.00% | 16.0 | -388.0 | -182.0 | 248 |
| b1_broadtop | ibs | AUDCAD | D1 | lo=0.1, hi=0.9, trend=0, sides=short, stop_atr=3.5, max_hold=16 | 2.00% | 14.0 | -289.0 | -103.0 | 99 |
| b1_broadtop | nlow | EURGBP | D1 | n=20, trend=0, sides=long, stop_atr=3.5, max_hold=16 | 2.00% | 13.7 | -337.0 | -139.0 | 104 |
| b1_broadtop | rsi2 | GBPUSD | D1 | n=3, lo=15, hi=85, exit_ma=5, trend=200, sides=both, stop_atr=3.5, max_hold=8 | 2.00% | 12.3 | -266.0 | -92.0 | 69 |
| b1_broadtop | stoch | USDCHF | D1 | n=30, lo=20, hi=80, trend=0, sides=both, stop_atr=3.5, max_hold=16 | 1.25% | 11.8 | -572.0 | -86.0 | 125 |
| b1_broadtop | rsi2 | USDJPY | D1 | n=2, lo=15, hi=85, exit_ma=5, trend=200, sides=short, stop_atr=2.0, max_hold=8 | 2.00% | 11.6 | -465.0 | -211.0 | 74 |
| b1_broadtop | wpr | EURJPY | D1 | n=30, lo=-85, hi=-15, trend=0, sides=both, stop_atr=2.0, max_hold=8 | 1.00% | 11.5 | -477.0 | -119.0 | 195 |
| b1_broadtop | nlow | US30 | D1 | n=10, trend=200, sides=long, stop_atr=2.0, max_hold=8 | 1.50% | 10.9 | -597.0 | -148.0 | 92 |
| b1_broadtop | stoch | CADJPY | D1 | n=14, lo=20, hi=80, trend=200, sides=both, stop_atr=3.5, max_hold=8 | 2.00% | 10.8 | -330.0 | -118.0 | 71 |
| b1_broadtop | rsi2 | EURUSD | H4 | n=3, lo=5, hi=95, exit_ma=0, trend=200, sides=both, stop_atr=3.5, max_hold=12 | 2.00% | 9.8 | -354.0 | -198.0 | 72 |
| b1_broadtop | rsi2 | NZDUSD | D1 | n=2, lo=5, hi=95, exit_ma=5, trend=0, sides=short, stop_atr=3.5, max_hold=8 | 2.00% | 9.3 | -188.0 | -94.0 | 70 |
| b2_index | zscore | USTEC | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 1.50% | 87.8 | -503.0 | -169.0 | 52 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=wpr, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 24.4 | -443.0 | -196.0 | 86 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 23.4 | -566.0 | -196.0 | 98 |
| b2_index | rsi2 | USTEC | D1 | n=3, lo=30, hi=70, exit_ma=3, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 23.3 | -106.0 | -72.0 | 17 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=2.0, max_hold=8 | 2.00% | 23.1 | -567.0 | -232.0 | 102 |
| b2_index | zscore | US500 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=200, stop_atr=3.0, max_hold=12 | 1.50% | 21.9 | -511.0 | -296.0 | 137 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=16 | 2.00% | 19.9 | -576.0 | -196.0 | 89 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 19.5 | -566.0 | -196.0 | 90 |
| b2_index | dip_combo | US500 | D1 | wpr_n=7, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 19.5 | -566.0 | -196.0 | 90 |
| b2_index | dip_combo | US500 | D1 | wpr_n=14, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 19.5 | -566.0 | -196.0 | 90 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 19.5 | -351.0 | -192.0 | 114 |
| b2_index | zscore | US30 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=4.5, max_hold=12 | 1.50% | 19.2 | -490.0 | -265.0 | 280 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=2.0, max_hold=8 | 1.50% | 19.1 | -580.0 | -159.0 | 94 |
| b2_index | wpr | USTEC | D1 | n=10, lo=-75, hi=-25, exit_lvl=-30, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 18.2 | -172.0 | -75.0 | 9 |
| b2_index | zscore | US30 | H4 | n=30, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 1.25% | 18.1 | -565.0 | -250.0 | 243 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=wpr, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 17.6 | -386.0 | -185.0 | 95 |
| b2_index | zscore | DE40 | H4 | n=20, z_in=2.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 1.00% | 17.4 | -519.0 | -240.0 | 166 |
| b2_index | dip_combo | US30 | D1 | wpr_n=7, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 17.0 | -302.0 | -185.0 | 97 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 16.9 | -302.0 | -185.0 | 97 |
| b2_index | dip_combo | US30 | D1 | wpr_n=14, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 16.9 | -302.0 | -185.0 | 97 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.1, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 16.7 | -435.0 | -191.0 | 68 |
| b2_index | rsi2 | DE40 | D1 | n=3, lo=30, hi=70, exit_ma=3, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 16.2 | -381.0 | -173.0 | 113 |
| b2_index | wpr | DE40 | D1 | n=10, lo=-75, hi=-25, exit_lvl=-30, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 15.7 | -394.0 | -162.0 | 57 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.3, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 15.6 | -324.0 | -185.0 | 115 |
| b2_index | wpr | US500 | D1 | n=10, lo=-75, hi=-25, exit_lvl=-30, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 15.6 | -460.0 | -142.0 | 69 |
| b2_index | zscore | US30 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 1.00% | 15.3 | -583.0 | -221.0 | 306 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=100, stop_atr=3.0, max_hold=8 | 2.00% | 14.9 | -531.0 | -196.0 | 79 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=16 | 2.00% | 14.8 | -342.0 | -164.0 | 71 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=100, stop_atr=3.0, max_hold=8 | 2.00% | 14.5 | -358.0 | -164.0 | 74 |
| b2_index | zscore | DE40 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 1.00% | 14.5 | -587.0 | -240.0 | 303 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=7, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 14.2 | -342.0 | -164.0 | 72 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=16 | 2.00% | 14.2 | -398.0 | -185.0 | 95 |
| b2_index | zscore | US500 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=4.5, max_hold=12 | 1.00% | 13.9 | -499.0 | -142.0 | 271 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 13.8 | -342.0 | -164.0 | 72 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=14, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 13.8 | -342.0 | -164.0 | 72 |
| b2_index | zscore | US30 | H4 | n=20, z_in=1.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.75% | 13.8 | -540.0 | -203.0 | 409 |
| b2_index | rsi2 | US500 | D1 | n=3, lo=30, hi=70, exit_ma=3, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 13.4 | -567.0 | -192.0 | 126 |
| b2_index | zscore | US500 | H4 | n=20, z_in=1.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.50% | 13.2 | -439.0 | -123.0 | 453 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.1, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 13.1 | -342.0 | -161.0 | 53 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=wpr, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 13.1 | -338.0 | -162.0 | 68 |
| b2_index | zscore | US500 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.75% | 12.8 | -518.0 | -199.0 | 290 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 12.3 | -386.0 | -173.0 | 83 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.3, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 12.3 | -559.0 | -149.0 | 108 |
| b2_index | zscore | DE40 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=4.5, max_hold=12 | 1.25% | 11.9 | -495.0 | -195.0 | 279 |
| b2_index | zscore | US30 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=200, stop_atr=3.0, max_hold=12 | 1.25% | 11.2 | -580.0 | -191.0 | 139 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=10, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 10.3 | -342.0 | -161.0 | 45 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=0, stop_atr=3.0, max_hold=8 | 1.00% | 10.3 | -476.0 | -95.0 | 143 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=10, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 10.2 | -444.0 | -142.0 | 63 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.3, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 10.2 | -585.0 | -173.0 | 95 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=2.0, max_hold=8 | 1.50% | 9.9 | -528.0 | -201.0 | 77 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=4.5, max_hold=8 | 2.00% | 9.7 | -370.0 | -163.0 | 85 |
| b2_index | rsi2 | US30 | D1 | n=3, lo=30, hi=70, exit_ma=3, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 9.7 | -419.0 | -174.0 | 131 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=100, stop_atr=3.0, max_hold=8 | 2.00% | 9.5 | -416.0 | -185.0 | 75 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=4.5, max_hold=8 | 2.00% | 9.2 | -221.0 | -126.0 | 73 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=3, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 9.0 | -342.0 | -161.0 | 35 |
| b2_index | zscore | DE40 | H4 | n=20, z_in=2.0, z_out=0.5, sides=long, trend=200, stop_atr=3.0, max_hold=12 | 1.25% | 8.5 | -590.0 | -187.0 | 117 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=1, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 1.25% | 8.4 | -564.0 | -130.0 | 214 |
| b2_index | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=3, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 8.3 | -447.0 | -192.0 | 40 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=0, stop_atr=3.0, max_hold=8 | 1.50% | 8.0 | -399.0 | -148.0 | 116 |
| b2_index | dip_combo | USTEC | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 7.1 | -247.0 | -72.0 | 13 |
| b2_index | wpr | US30 | D1 | n=10, lo=-75, hi=-25, exit_lvl=-30, sides=long, trend=200, stop_atr=3.0, max_hold=8 | 1.25% | 7.1 | -358.0 | -99.0 | 58 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=10, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 6.7 | -355.0 | -174.0 | 56 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=0, stop_atr=3.0, max_hold=8 | 1.25% | 5.7 | -428.0 | -98.0 | 143 |
| b2_index | zscore | US500 | H4 | n=20, z_in=2.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.75% | 5.7 | -530.0 | -148.0 | 142 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=prev_high, trend=200, stop_atr=4.5, max_hold=8 | 2.00% | 4.8 | -417.0 | -121.0 | 71 |
| b2_index | zscore | DE40 | H4 | n=20, z_in=1.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.50% | 4.8 | -353.0 | -93.0 | 435 |
| b2_index | zscore | US500 | H4 | n=30, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.50% | 4.8 | -597.0 | -123.0 | 240 |
| b2_index | zscore | DE40 | H4 | n=30, z_in=2.0, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.50% | 4.8 | -390.0 | -93.0 | 229 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.1, need=2, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 3.2 | -395.0 | -172.0 | 66 |
| b2_index | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=1, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 1.25% | 1.5 | -599.0 | -98.0 | 169 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=3, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 1.4 | -540.0 | -174.0 | 39 |
| b2_index | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=1, exit_mode=prev_high, trend=200, stop_atr=3.0, max_hold=8 | 1.25% | 0.7 | -542.0 | -111.0 | 156 |
| b2_index | zscore | US30 | H4 | n=20, z_in=2.5, z_out=0.5, sides=long, trend=0, stop_atr=3.0, max_hold=12 | 0.75% | -0.6 | -519.0 | -145.0 | 126 |
| b3_neighbours | dip_combo | USTEC | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 52.5 | -295.0 | -106.0 | 12 |
| b3_neighbours | nlow | US30 | H4 | n=10, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.50% | 39.7 | -492.0 | -240.0 | 414 |
| b3_neighbours | nlow | US30 | H4 | n=10, trend=200, sides=long, stop_atr=5.0, max_hold=24 | 2.00% | 35.7 | -532.0 | -197.0 | 405 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 32.8 | -575.0 | -296.0 | 84 |
| b3_neighbours | nlow | US30 | H4 | n=10, trend=100, sides=long, stop_atr=3.5, max_hold=24 | 1.50% | 29.1 | -564.0 | -170.0 | 349 |
| b3_neighbours | nlow | US30 | H4 | n=15, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.50% | 27.5 | -558.0 | -240.0 | 296 |
| b3_neighbours | nlow | US30 | H4 | n=7, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.25% | 26.9 | -515.0 | -218.0 | 567 |
| b3_neighbours | nlow | US30 | H4 | n=10, trend=200, sides=long, stop_atr=2.5, max_hold=24 | 1.00% | 26.7 | -580.0 | -202.0 | 441 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=ma10, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 25.2 | -421.0 | -196.0 | 91 |
| b3_neighbours | wpr | US500 | H4 | n=14, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.50% | 25.2 | -554.0 | -167.0 | 505 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=2.0, max_hold=8 | 1.50% | 23.9 | -523.0 | -288.0 | 92 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=12 | 1.50% | 23.8 | -542.0 | -265.0 | 72 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 23.7 | -511.0 | -250.0 | 81 |
| b3_neighbours | wpr | US500 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.50% | 23.4 | -565.0 | -149.0 | 619 |
| b3_neighbours | wpr | US500 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=12 | 0.50% | 22.7 | -565.0 | -149.0 | 619 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 21.2 | -409.0 | -260.0 | 89 |
| b3_neighbours | nlow | US500 | H4 | n=10, trend=100, sides=long, stop_atr=3.5, max_hold=24 | 1.25% | 20.4 | -570.0 | -239.0 | 377 |
| b3_neighbours | wpr | US500 | H4 | n=10, lo=-90, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.50% | 19.8 | -565.0 | -148.0 | 479 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=2.0, max_hold=8 | 1.00% | 18.8 | -568.0 | -201.0 | 87 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 18.3 | -400.0 | -164.0 | 65 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=ma10, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 17.4 | -246.0 | -185.0 | 98 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=2.0, max_hold=8 | 1.50% | 17.3 | -519.0 | -201.0 | 70 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 1.50% | 16.9 | -409.0 | -260.0 | 77 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=4.5, max_hold=8 | 2.00% | 16.5 | -312.0 | -174.0 | 66 |
| b3_neighbours | wpr | US500 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=3.0, max_hold=24 | 0.50% | 16.4 | -428.0 | -98.0 | 547 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=5 | 1.50% | 15.9 | -398.0 | -250.0 | 91 |
| b3_neighbours | wpr | US500 | H4 | n=7, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.50% | 15.8 | -439.0 | -149.0 | 703 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=5 | 2.00% | 15.6 | -562.0 | -225.0 | 99 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=ma10, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 14.0 | -346.0 | -161.0 | 72 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=5 | 2.00% | 13.5 | -523.0 | -164.0 | 73 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=12 | 2.00% | 13.5 | -497.0 | -164.0 | 56 |
| b3_neighbours | dip_combo | US500 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=4.5, max_hold=8 | 1.50% | 13.5 | -493.0 | -172.0 | 77 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-80, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=8 | 2.00% | 12.9 | -551.0 | -164.0 | 69 |
| b3_neighbours | nlow | US500 | H4 | n=10, trend=200, sides=long, stop_atr=5.0, max_hold=24 | 1.00% | 10.7 | -513.0 | -134.0 | 419 |
| b3_neighbours | wpr | US500 | H4 | n=10, lo=-80, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 10.3 | -279.0 | -80.0 | 704 |
| b3_neighbours | wpr | US30 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=3.0, max_hold=24 | 0.75% | 9.9 | -594.0 | -141.0 | 473 |
| b3_neighbours | nlow | US500 | H4 | n=10, trend=200, sides=long, stop_atr=2.5, max_hold=24 | 0.50% | 9.2 | -469.0 | -121.0 | 461 |
| b3_neighbours | stoch | XAUUSD | D1 | n=30, lo=15, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.25% | 8.9 | -597.0 | -99.0 | 51 |
| b3_neighbours | dip_combo | US30 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=3.0, max_hold=12 | 1.50% | 8.2 | -560.0 | -260.0 | 64 |
| b3_neighbours | stoch | XAGUSD | D1 | n=30, lo=25, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 8.0 | -397.0 | -97.0 | 79 |
| b3_neighbours | nlow | US500 | H4 | n=10, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 0.50% | 7.3 | -399.0 | -94.0 | 433 |
| b3_neighbours | dip_combo | DE40 | D1 | wpr_n=10, wpr_lo=-90, nlow_n=5, ibs_lo=0.2, need=2, exit_mode=time, trend=200, stop_atr=4.5, max_hold=8 | 2.00% | 7.2 | -526.0 | -125.0 | 63 |
| b3_neighbours | stoch | XAUUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 6.4 | -514.0 | -100.0 | 66 |
| b3_neighbours | stoch | XAGUSD | D1 | n=30, lo=15, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.25% | 6.2 | -480.0 | -122.0 | 59 |
| b3_neighbours | nlow | DE40 | H4 | n=15, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.50% | 6.1 | -567.0 | -169.0 | 270 |
| b3_neighbours | stoch | XAUUSD | D1 | n=30, lo=25, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 5.8 | -529.0 | -81.0 | 74 |
| b3_neighbours | stoch | XAUUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=3.0, max_hold=16 | 1.50% | 5.3 | -486.0 | -149.0 | 58 |
| b3_neighbours | stoch | XAUUSD | D1 | n=20, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 5.2 | -494.0 | -100.0 | 72 |
| b3_neighbours | nlow | US500 | H4 | n=15, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 0.75% | 5.1 | -542.0 | -145.0 | 305 |
| b3_neighbours | stoch | XAGUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 5.0 | -379.0 | -93.0 | 71 |
| b3_neighbours | wpr | US30 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=12 | 0.25% | 4.8 | -205.0 | -67.0 | 261 |
| b3_neighbours | wpr | US30 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 4.7 | -205.0 | -67.0 | 260 |
| b3_neighbours | wpr | US30 | H4 | n=10, lo=-80, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 4.7 | -175.0 | -59.0 | 315 |
| b3_neighbours | nlow | US500 | H4 | n=7, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 0.50% | 4.7 | -502.0 | -99.0 | 595 |
| b3_neighbours | stoch | XAUUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=8 | 1.00% | 4.3 | -482.0 | -100.0 | 89 |
| b3_neighbours | wpr | US30 | H4 | n=7, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.50% | 4.1 | -551.0 | -145.0 | 612 |
| b3_neighbours | wpr | US30 | H4 | n=10, lo=-90, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 3.8 | -200.0 | -67.0 | 188 |
| b3_neighbours | stoch | XAGUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=3.0, max_hold=16 | 1.50% | 3.6 | -440.0 | -124.0 | 65 |
| b3_neighbours | nlow | DE40 | H4 | n=10, trend=200, sides=long, stop_atr=5.0, max_hold=24 | 1.25% | 3.2 | -507.0 | -117.0 | 371 |
| b3_neighbours | wpr | DE40 | H4 | n=14, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 2.7 | -337.0 | -59.0 | 448 |
| b3_neighbours | stoch | XAGUSD | D1 | n=20, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=16 | 1.00% | 2.1 | -560.0 | -93.0 | 76 |
| b3_neighbours | wpr | US30 | H4 | n=14, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | 1.8 | -215.0 | -67.0 | 213 |
| b3_neighbours | nlow | DE40 | H4 | n=10, trend=200, sides=long, stop_atr=2.5, max_hold=24 | 0.50% | 0.9 | -414.0 | -89.0 | 410 |
| b3_neighbours | nlow | DE40 | H4 | n=10, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 1.00% | 0.8 | -558.0 | -161.0 | 380 |
| b3_neighbours | nlow | DE40 | H4 | n=10, trend=100, sides=long, stop_atr=3.5, max_hold=24 | 0.75% | 0.4 | -542.0 | -78.0 | 320 |
| b3_neighbours | stoch | XAGUSD | D1 | n=30, lo=20, hi=80, sides=long, trend=0, stop_atr=2.0, max_hold=8 | 1.00% | -0.5 | -444.0 | -93.0 | 95 |
| b3_neighbours | wpr | DE40 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=12 | 0.25% | -1.0 | -427.0 | -69.0 | 520 |
| b3_neighbours | wpr | DE40 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=3.0, max_hold=24 | 0.25% | -1.1 | -267.0 | -38.0 | 289 |
| b3_neighbours | wpr | DE40 | H4 | n=10, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | -1.2 | -446.0 | -69.0 | 518 |
| b3_neighbours | wpr | DE40 | H4 | n=10, lo=-80, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | -1.2 | -454.0 | -69.0 | 611 |
| b3_neighbours | nlow | DE40 | H4 | n=7, trend=200, sides=long, stop_atr=3.5, max_hold=24 | 0.50% | -2.5 | -502.0 | -70.0 | 466 |
| b3_neighbours | wpr | DE40 | H4 | n=10, lo=-90, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | -2.9 | -453.0 | -67.0 | 391 |
| b3_neighbours | wpr | DE40 | H4 | n=7, lo=-85, hi=-15, sides=long, trend=0, stop_atr=2.0, max_hold=24 | 0.25% | -3.0 | -591.0 | -69.0 | 585 |
| g1_partial | stoch | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | 5.4 | -261.0 | -103.0 | 29 |
| g1_partial | ibs | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 1.50% | 4.2 | -599.0 | -107.0 | 171 |
| g1_partial | stoch | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 1.00% | 3.6 | -475.0 | -171.0 | 126 |
| g1_partial | bb_fade | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | 2.3 | -254.0 | -112.0 | 16 |
| g1_partial | stoch | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | 1.5 | -271.0 | -97.0 | 23 |
| g1_partial | wpr | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | 1.2 | -461.0 | -105.0 | 32 |
| g1_partial | bb_fade | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 2.00% | 0.9 | -465.0 | -112.0 | 25 |
| g1_partial | wpr | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | 0.6 | -526.0 | -97.0 | 25 |
| g1_partial | zscore | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 1.50% | 0.2 | -576.0 | -203.0 | 33 |
| g1_partial | wpr | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.75% | 0.2 | -539.0 | -111.0 | 151 |
| g1_partial | zscore | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.50% | 0.1 | -469.0 | -58.0 | 70 |
| g1_partial | zscore | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 1.25% | 0.1 | -507.0 | -145.0 | 34 |
| g1_partial | bb_fade | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -0.1 | -235.0 | -119.0 | 14 |
| g1_partial | crsi | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -0.3 | -145.0 | -84.0 | 19 |
| g1_partial | zscore | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -0.4 | -163.0 | -75.0 | 6 |
| g1_partial | zscore | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -0.6 | -137.0 | -99.0 | 5 |
| g1_partial | crsi | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 2.00% | -0.7 | -266.0 | -119.0 | 22 |
| g1_partial | wpr | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -0.9 | -265.0 | -25.0 | 172 |
| g1_partial | crsi | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -1.2 | -241.0 | -119.0 | 11 |
| g1_partial | zscore | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.50% | -1.4 | -432.0 | -64.0 | 79 |
| g1_partial | ibs | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.25% | -1.5 | -265.0 | -35.0 | 588 |
| g1_partial | stoch | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 2.00% | -1.5 | -596.0 | -120.0 | 52 |
| g1_partial | crsi | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -1.6 | -209.0 | -29.0 | 154 |
| g1_partial | wpr | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -1.6 | -239.0 | -27.0 | 244 |
| g1_partial | crsi | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 2.00% | -1.6 | -256.0 | -148.0 | 27 |
| g1_partial | bb_fade | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.50% | -1.7 | -379.0 | -81.0 | 87 |
| g1_partial | bb_fade | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -2.0 | -332.0 | -34.0 | 114 |
| g1_partial | rsi2 | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 1.50% | -2.0 | -322.0 | -110.0 | 41 |
| g1_partial | bb_fade | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.50% | -2.1 | -518.0 | -94.0 | 30 |
| g1_partial | ibs | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.00% | -2.2 | -574.0 | -76.0 | 237 |
| g1_partial | crsi | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | 0.25% | -2.3 | -358.0 | -44.0 | 352 |
| g1_partial | crsi | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -2.3 | -252.0 | -23.0 | 101 |
| g1_partial | zscore | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | 0.25% | -2.4 | -433.0 | -44.0 | 158 |
| g1_partial | nlow | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.25% | -2.4 | -350.0 | -32.0 | 293 |
| g1_partial | nlow | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 2.00% | -2.4 | -588.0 | -119.0 | 55 |
| g1_partial | stoch | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.75% | -2.5 | -538.0 | -114.0 | 252 |
| g1_partial | nlow | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 0.50% | -2.5 | -401.0 | -40.0 | 47 |
| g1_partial | ibs | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -2.6 | -495.0 | -35.0 | 1248 |
| g1_partial | rsi2 | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 0.75% | -2.6 | -400.0 | -55.0 | 48 |
| g1_partial | stoch | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.50% | -2.6 | -512.0 | -94.0 | 47 |
| g1_partial | ibs | XAGUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 0.75% | -2.8 | -303.0 | -51.0 | 60 |
| g1_partial | rsi2 | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 1.00% | -2.9 | -443.0 | -62.0 | 45 |
| g1_partial | stoch | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.50% | -2.9 | -399.0 | -83.0 | 214 |
| g1_partial | zscore | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | 0.25% | -3.0 | -576.0 | -60.0 | 282 |
| g1_partial | zscore | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 2.00% | -3.0 | -445.0 | -114.0 | 14 |
| g1_partial | stoch | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -3.1 | -716.0 | -56.0 | 862 |
| g1_partial | crsi | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.50% | -3.1 | -450.0 | -58.0 | 77 |
| g1_partial | stoch | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.75% | -3.1 | -533.0 | -84.0 | 91 |
| g1_partial | wpr | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | 0.25% | -3.2 | -548.0 | -69.0 | 541 |
| g1_partial | wpr | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.75% | -3.2 | -577.0 | -84.0 | 119 |
| g1_partial | zscore | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.50% | -3.4 | -487.0 | -94.0 | 11 |
| g1_partial | stoch | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | 0.25% | -3.6 | -594.0 | -56.0 | 409 |
| g1_partial | wpr | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.00% | -3.7 | -582.0 | -70.0 | 55 |
| g1_partial | zscore | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | 0.25% | -3.7 | -453.0 | -43.0 | 117 |
| g1_partial | nlow | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.25% | -3.7 | -531.0 | -79.0 | 114 |
| g1_partial | bb_fade | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -3.8 | -439.0 | -32.0 | 145 |
| g1_partial | nlow | XAUUSD | D1 | sides=long, max_hold=8, stop_atr=3.0 | 1.25% | -3.9 | -587.0 | -120.0 | 65 |
| g1_partial | crsi | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.50% | -4.0 | -550.0 | -92.0 | 105 |
| g1_partial | bb_fade | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -4.2 | -670.0 | -54.0 | 433 |
| g1_partial | rsi2 | XAUUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 0.75% | -4.2 | -486.0 | -56.0 | 59 |
| g1_partial | crsi | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | 0.25% | -4.3 | -510.0 | -44.0 | 661 |
| g1_partial | rsi2 | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.25% | -4.3 | -488.0 | -34.0 | 158 |
| g1_partial | bb_fade | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.50% | -4.5 | -543.0 | -83.0 | 95 |
| g1_partial | nlow | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | 0.25% | -4.5 | -559.0 | -38.0 | 600 |
| g1_partial | nlow | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.25% | -4.5 | -530.0 | -34.0 | 173 |
| g1_partial | ibs | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 0.75% | -4.5 | -584.0 | -51.0 | 117 |
| g1_partial | rsi2 | XAUUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | 0.25% | -4.7 | -554.0 | -33.0 | 256 |
| g1_partial | wpr | XAGUSD | D1 | sides=both, max_hold=8, stop_atr=3.0 | 1.25% | -4.9 | -580.0 | -65.0 | 51 |
| g1_partial | rsi2 | XAUUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | NONE | -5.0 | -627.0 | -38.0 | 514 |
| g1_partial | bb_fade | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -5.8 | -967.0 | -54.0 | 829 |
| g1_partial | crsi | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -7.1 | -792.0 | -42.0 | 295 |
| g1_partial | zscore | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -7.1 | -869.0 | -43.0 | 241 |
| g1_partial | ibs | XAGUSD | H4 | sides=long, max_hold=12, stop_atr=2.5 | NONE | -7.3 | -842.0 | -26.0 | 397 |
| g1_partial | rsi2 | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -8.0 | -1021.0 | -66.0 | 1313 |
| g1_partial | wpr | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -8.7 | -1218.0 | -69.0 | 1090 |
| g1_partial | stoch | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -8.8 | -1119.0 | -66.0 | 381 |
| g1_partial | rsi2 | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | NONE | -9.0 | -987.0 | -34.0 | 382 |
| g1_partial | nlow | XAGUSD | H4 | sides=both, max_hold=12, stop_atr=2.5 | NONE | -9.5 | -1058.0 | -34.0 | 428 |
| g1_partial | bb_fade | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -9.6 | -1109.0 | -56.0 | 365 |
| g1_partial | nlow | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -11.3 | -1457.0 | -66.0 | 1584 |
| g1_partial | wpr | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -13.4 | -1524.0 | -63.0 | 481 |
| g1_partial | vwap | XAUUSD | H1 | sides=long, max_hold=12, stop_atr=2.5 | NONE | -14.4 | -1844.0 | -66.0 | 1602 |
| g1_partial | crsi | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -14.9 | -1622.0 | -42.0 | 565 |
| g1_partial | stoch | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -17.1 | -1984.0 | -66.0 | 790 |
| g1_partial | rsi2 | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -19.0 | -2294.0 | -66.0 | 2454 |
| g1_partial | bb_fade | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -20.6 | -2242.0 | -56.0 | 740 |
| g1_partial | ibs | XAUUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -24.3 | -2732.0 | -65.0 | 3396 |
| g1_partial | nlow | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -25.4 | -3078.0 | -72.0 | 2915 |
| g1_partial | wpr | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -28.8 | -3127.0 | -63.0 | 1007 |
| g1_partial | rsi2 | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -32.2 | -3500.0 | -64.0 | 1139 |
| g1_partial | vwap | XAUUSD | H1 | sides=both, max_hold=12, stop_atr=2.5 | NONE | -37.0 | -4198.0 | -90.0 | 3294 |
| g1_partial | nlow | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -39.4 | -4259.0 | -63.0 | 1398 |
| g1_partial | vwap | XAGUSD | H1 | sides=long, max_hold=12, stop_atr=2.5 | NONE | -41.4 | -4505.0 | -64.0 | 1469 |
| g1_partial | ibs | XAUUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -46.0 | -5053.0 | -65.0 | 6431 |
| g1_partial | rsi2 | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -62.9 | -6811.0 | -64.0 | 2181 |
| g1_partial | nlow | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -78.1 | -8447.0 | -63.0 | 2762 |
| g1_partial | ibs | XAGUSD | H1 | sides=long, max_hold=24, stop_atr=2.5 | NONE | -84.8 | -9164.0 | -61.0 | 3082 |
| g1_partial | ibs | XAGUSD | H1 | sides=both, max_hold=24, stop_atr=2.5 | NONE | -162.6 | -17570.0 | -69.0 | 6065 |
# gold_fix — in-sample research notes (2015-01 .. 2023-12 only)

Judge: `research/prop/harness.py` (fixed-dollar risk on $10k, safe = worst day > -3% and
max DD > -6%, best_risk = highest safe level in 0.25..2%). M30 data starts 2018-04, so
M30 results cover ~5.7 years; H1/H4/D1 cover 9 years. No 2024+ data was read.
Every scored run is in `results.jsonl` (249 unique runs; table at the bottom).

## 1. Diagnosis of the live BOS + CMF strategy (XAUUSD M30)

`check_parity.py`: our vectorised `build_bos` reproduces `bos_backtest.make_bos_signal`
(trend_ma=200) on all 3,271 in-sample signals (0 mismatches).

Baseline on the judge: **-$2,595 net, no safe risk level**, -0.079 R per trade over 1,514
trades. Every in-sample year lost (2018..2023, -0.0 to -0.17 R/trade). `diagnose.py`:

| Where it fails | Evidence (sum of R, 0.5% risk) |
|---|---|
| **Structure target too close** | 1,130 of 1,514 trades had a target <= 1.2R: -125R. Targets 2-3R: +49R. With ~44% wins and costs, a ~1R target cannot pay. |
| **Low volatility regime** | ATR percentile (2000 bars) 0-60%: -121R; 80-100%: +17R. Breakouts in calm M30 conditions are fakeouts. |
| **Opposite-signal flips** | 221 flip exits, -102R (7% win). |
| **Asian / rollover hours** | server hours 22-05: about -75R; 06-09 and 17 positive. |
| **Shorts** | shorts -91R vs longs -29R (gold drifted up in-sample). |
| **Tight structural stops** | stop < 1.5 ATR: -40R. |
| **Month end** | day 26-31: -45R (weak, not acted on). |
| Not the problem | NFP Fridays (+1.7R), ADX bucket (no monotone pattern), CMF strength (no pattern). |

Fixes tested one at a time (all on the judge): fixed 2R/3R targets, tp_min_r 2/3, no-flip,
London+NY hours only, daily-EMA trend gate, trailing exits, breakeven, other TFs. Alone,
none made BOS profitable except the **volatility-regime filter** (ATR pct >= 0.6), which
was positive for every threshold 0.4..0.8 once combined with tp_min_r=2 (+$5..+$23/mo).
Adding a daily EMA100 trend gate helped (+$18/mo @0.25%); EMA20/50 and H4-EMA50 gates
were also positive (+$13..16/mo) so it is not a single-setting artefact. Long-only version
+$34/mo @0.5%. BOS still fails on H1, H4, M15 and on XAGUSD, and breakeven / trailing
exits hurt (they cut the long-hold winners that carry the strategy).

## 2. Other gold ideas

* **Donchian trend following** (H4): plain 20/10 is weakly positive in 8/9 years
  (+0.12 R/trade) but DD limits it to 0.25% risk (~$8/mo). Diagnosis (`diag_any.py`):
  ADX < 20 entries lose, and entries in the HIGH half of the ATR range lose. Breakouts out
  of calm, already-trending conditions carry the edge (same idea as the squeeze below).
  **Low-vol + ADX>=20 filter + trailing exit** gives the best family: all 48 grid cells
  (n_entry 15/20 x n_exit 5/7/10 x trail none/4/5/6 x stop 2/2.5) are safe and positive,
  $16..$46/mo. Neighbours: ATR-pct cap 0.3..0.7 all positive, ADX 15..25 all positive,
  4h-equivalent on 2h/6h/8h/12h bars all positive (weaker at 12h), 2x spread still
  +$29..33/mo, both sides positive (long $36/mo, short $7/mo). Removing either filter
  drops it to ~$10-12/mo.
  It does NOT transfer: XAGUSD, USDJPY, EURUSD, GBPUSD, AUDUSD H4 are flat-to-negative.
  It is a gold-specific result; treat as such.
* **Bollinger squeeze breakout** (H4): +$10..12/mo at 0.25% for squeeze pct 0.1..0.3;
  with ADX>=20 +$20/mo @0.5%. Fails on H1/M30 (costs) and XAGUSD.
* **Asia-range session breakout** (H1/M30, several windows, range/mid/ATR stops, 2R
  targets): all lose or are flat; with an ATR-pct >= 0.5 filter barely positive (+$6-7/mo).
* **RSI(2) pullback in EMA50/200 trend** (H1/H4): loses everywhere, including long-only
  and with regime filters.
* **Time-of-day drift**: gold H1 hours 01-02 server time are positive in both halves of
  in-sample (t ~ 3.7 / 2.0), silver hour 13 is strongly negative, but the moves are
  ~0.03-0.05 ATR per bar, far below spread + commission. Hold strategies lost ~$2k.
* **Session-to-session momentum** (`segment_study.py`): correlations < 0.06; prev-day ->
  London momentum ~ +0.025 daily ATR, consistent but too small to trade.
* **Combos** (one position, M30, H4-Donchian placed via `build_mtf` + BOS-fixed): no
  better than the parts (one-position interaction eats the diversification).

## 3. What I learned

1. On gold the judge's binding constraint is max DD (6%), not the daily limit. Return/DD
   ratio decides the safe risk level; lot rounding (0.01 lot min) makes 0.25% risk trade
   well below 0.25% on wide gold stops, so 0.25%-results understate.
2. Gold's tradeable edge in this data is slow trend (H4, multi-day holds); everything
   intraday (M30/H1 breakouts, pullbacks, hour effects) is eaten by $0.30 spread + $14/lot.
3. The live BOS's core flaw is targeting the nearest swing (~1R); its second flaw is
   trading calm markets. Even fixed, it is a modest strategy (~$18-34/mo in-sample).
4. Challenge stats: even the best candidate reaches +8% then +4% in a median of 600-1,200
   days; most rolling attempts are "unfinished", not failed. None of these pass a
   FundedNext challenge quickly at safe risk. They are safe, slow earners.
5. Biggest caveat: in-sample gold rose ~75% and long trades dominate. The long-only
   variants partly harvest gold beta. Out-of-sample must judge.

## Candidates (in-sample, best safe risk)

| builder (strategies.py) | tf | risk | avg/mo | max DD | worst day | trades |
|---|---|---|---|---|---|---|
| build_gold_lowvol_donchian | H4 | 0.50% | $37 | -$408 | -$96 | 204 |
| build_gold_lowvol_donchian_fast | H4 | 0.75% | $45 | -$580 | -$140 | 221 |
| build_bos_fixed_long | M30 | 0.50% | $34 | -$467 | -$106 | 161 |
| build_gold_squeeze_adx | H4 | 0.50% | $20 | -$581 | -$94 | 148 |
| build_bos_fixed | M30 | 0.25% | $18 | -$386 | -$64 | 273 |

Files: `lib.py` (causal indicators, HTF alignment), `strategies.py` (BOS + candidates),
`ideas.py` (Donchian, session, pullback, hour, squeeze, regime wrapper, MTF, combo),
`runner.py` + `batch*.py` (every scored run), `check_parity.py`, `causal_check.py`,
`mtf_check.py` (truncation tests: 0 mismatches), `diagnose.py`, `diag_any.py`,
`hour_profile.py`, `segment_study.py`, `final_check.py`.

## All scored runs

| name | symbol | tf | best_risk | avg_month | max_dd | worst_day | trades |
|---|---|---|---|---|---|---|---|
| bos_base_M30 | XAUUSD | M30 | none | -38 | -3040 | -101 | 1556 |
| bos_noflip_M30 | XAUUSD | M30 | none | -20 | -1788 | -108 | 1184 |
| bos_tpmin2.0_M30 | XAUUSD | M30 | none | -26 | -2179 | -97 | 1227 |
| bos_tpmin3.0_M30 | XAUUSD | M30 | none | -36 | -2643 | -97 | 1104 |
| bos_fixR2.0_M30 | XAUUSD | M30 | none | -35 | -2761 | -97 | 1303 |
| bos_fixR3.0_M30 | XAUUSD | M30 | none | -29 | -2228 | -97 | 1126 |
| bos_atrp0.6_M30 | XAUUSD | M30 | 0.25% | 1 | -552 | -66 | 657 |
| bos_base_H1 | XAUUSD | H1 | none | -7 | -1218 | -81 | 1225 |
| bos_tpmin2_atrp0.6_M30 | XAUUSD | M30 | 0.25% | 10 | -545 | -66 | 569 |
| bos_noflip_H1 | XAUUSD | H1 | none | -4 | -909 | -65 | 1001 |
| bos_tpmin2.0_H1 | XAUUSD | H1 | none | -1 | -1196 | -81 | 966 |
| bos_tpmin3.0_H1 | XAUUSD | H1 | none | -6 | -1606 | -81 | 869 |
| bos_fixR2.0_H1 | XAUUSD | H1 | none | -2 | -1157 | -81 | 1024 |
| bos_atrp0.6_H1 | XAUUSD | H1 | none | -5 | -831 | -54 | 529 |
| bos_fixR3.0_H1 | XAUUSD | H1 | none | -8 | -1481 | -81 | 869 |
| bos_tpmin2_atrp0.6_H1 | XAUUSD | H1 | none | -1 | -684 | -54 | 443 |
| bos_base_H4 | XAUUSD | H4 | 0.25% | -1 | -457 | -36 | 306 |
| bos_noflip_H4 | XAUUSD | H4 | 0.25% | -2 | -506 | -36 | 289 |
| bos_tpmin2.0_H4 | XAUUSD | H4 | none | -6 | -861 | -48 | 251 |
| bos_tpmin3.0_H4 | XAUUSD | H4 | none | -7 | -918 | -53 | 235 |
| bos_fixR2.0_H4 | XAUUSD | H4 | none | -6 | -851 | -48 | 258 |
| bos_fixR3.0_H4 | XAUUSD | H4 | none | -5 | -810 | -48 | 240 |
| bos_atrp0.6_H4 | XAUUSD | H4 | 0.25% | -1 | -300 | -30 | 99 |
| bos_tpmin2_atrp0.6_H4 | XAUUSD | H4 | 0.25% | -3 | -420 | -48 | 85 |
| donch20_10_H4 | XAUUSD | H4 | 0.25% | 9 | -463 | -121 | 387 |
| donch55_20_H4 | XAUUSD | H4 | 0.25% | 8 | -345 | -142 | 206 |
| donch10_5_H4 | XAUUSD | H4 | 0.25% | 1 | -532 | -71 | 681 |
| donch20_trail3_H4 | XAUUSD | H4 | 0.25% | 6 | -385 | -42 | 424 |
| donch20_10_long_H4 | XAUUSD | H4 | 0.25% | 6 | -377 | -121 | 213 |
| donch20_10_D1 | XAUUSD | D1 | 0.50% | -0 | -526 | -126 | 62 |
| donch55_20_D1 | XAUUSD | D1 | 0.75% | 3 | -524 | -163 | 34 |
| donch10_5_D1 | XAUUSD | D1 | 0.75% | 1 | -598 | -147 | 121 |
| donch20_trail3_D1 | XAUUSD | D1 | 0.75% | 3 | -421 | -74 | 79 |
| donch20_10_long_D1 | XAUUSD | D1 | 0.75% | 6 | -464 | -163 | 37 |
| donch55_20_H1 | XAUUSD | H1 | none | 5 | -1111 | -112 | 829 |
| donch100_50_H1 | XAUUSD | H1 | none | 5 | -605 | -99 | 427 |
| sess0-8_range_H1 | XAUUSD | H1 | none | 0 | -831 | -90 | 1906 |
| sess0-8_mid_H1 | XAUUSD | H1 | none | -7 | -1386 | -116 | 1942 |
| sess0-8_range_tp2_H1 | XAUUSD | H1 | none | -13 | -1871 | -90 | 1924 |
| sess0-10_range_H1 | XAUUSD | H1 | none | -7 | -1429 | -61 | 1838 |
| sess0-15_NY_H1 | XAUUSD | H1 | none | -13 | -1572 | -61 | 1349 |
| sess0-8_range_M30 | XAUUSD | M30 | none | -14 | -1237 | -77 | 1262 |
| sess0-8_mid_M30 | XAUUSD | M30 | none | -20 | -2134 | -116 | 1298 |
| sess0-8_range_tp2_M30 | XAUUSD | M30 | none | -20 | -1622 | -37 | 1274 |
| sess0-10_range_M30 | XAUUSD | M30 | none | -14 | -1255 | -39 | 1213 |
| sess0-15_NY_M30 | XAUUSD | M30 | none | -17 | -1338 | -52 | 906 |
| pull_rsi2_H1 | XAUUSD | H1 | none | -24 | -2811 | -71 | 2213 |
| pull_rsi2_long_H1 | XAUUSD | H1 | none | -13 | -1479 | -71 | 1225 |
| pull_rsi2_H4 | XAUUSD | H4 | none | -4 | -698 | -40 | 536 |
| pull_rsi2_long_H4 | XAUUSD | H4 | 0.25% | -2 | -350 | -40 | 277 |
| hour1_long_hold3_H1 | XAUUSD | H1 | none | -19 | -2184 | -25 | 2296 |
| hour1_long_hold4_H1 | XAUUSD | H1 | 2.00% | 4 | -456 | -196 | 50 |
| hour1_long_hold3_ma200_H1 | XAUUSD | H1 | none | -12 | -1459 | -25 | 1227 |
| bos_LN_M30 | XAUUSD | M30 | none | -19 | -1807 | -76 | 1283 |
| bos_LN_tpmin2_M30 | XAUUSD | M30 | none | -10 | -1385 | -77 | 1033 |
| bos_htfD50_M30 | XAUUSD | M30 | none | -12 | -1251 | -63 | 863 |
| bos_htfD50_tpmin2_M30 | XAUUSD | M30 | none | -8 | -1161 | -64 | 653 |
| bos_trail3_M30 | XAUUSD | M30 | none | -35 | -2973 | -94 | 1791 |
| bos_trail3_htfD50_M30 | XAUUSD | M30 | none | -20 | -1808 | -69 | 1073 |
| bos_tpmin2_noflip_M30 | XAUUSD | M30 | none | -7 | -1114 | -73 | 848 |
| bos_LN_H1 | XAUUSD | H1 | none | -4 | -719 | -81 | 1102 |
| bos_LN_tpmin2_H1 | XAUUSD | H1 | none | 1 | -964 | -81 | 872 |
| bos_htfD50_H1 | XAUUSD | H1 | none | -3 | -680 | -65 | 774 |
| bos_htfD50_tpmin2_H1 | XAUUSD | H1 | none | -0 | -697 | -54 | 582 |
| bos_trail3_H1 | XAUUSD | H1 | none | 1 | -1210 | -77 | 1394 |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | none | 0 | -698 | -65 | 933 |
| bos_tpmin2_noflip_H1 | XAUUSD | H1 | none | 3 | -958 | -61 | 690 |
| bos_tpmin2_atrp0.4_M30 | XAUUSD | M30 | 0.25% | 8 | -495 | -73 | 768 |
| bos_tpmin2_atrp0.5_M30 | XAUUSD | M30 | 0.25% | 11 | -550 | -66 | 683 |
| bos_tpmin2_atrp0.7_M30 | XAUUSD | M30 | 0.25% | 5 | -423 | -59 | 467 |
| bos_tpmin2_atrp0.8_M30 | XAUUSD | M30 | 0.50% | 23 | -584 | -165 | 324 |
| bos_tpmin1.5_atrp0.6_M30 | XAUUSD | M30 | 0.25% | 4 | -556 | -66 | 592 |
| bos_tpmin2.5_atrp0.6_M30 | XAUUSD | M30 | 0.25% | 3 | -503 | -66 | 544 |
| bos_tpmin2_atrp0.6_LN_M30 | XAUUSD | M30 | 0.25% | 10 | -525 | -69 | 498 |
| bos_tpmin2_atrp0.6_htf_M30 | XAUUSD | M30 | 0.25% | 14 | -506 | -64 | 289 |
| bos_tpmin2_atrp0.6_noflip_M30 | XAUUSD | M30 | 0.25% | 14 | -375 | -64 | 454 |
| bos_tpmin2_atrp0.6_M30_XAG | XAGUSD | M30 | none | -22 | -1672 | -54 | 538 |
| donch15_10_H4 | XAUUSD | H4 | 0.25% | 8 | -428 | -121 | 451 |
| donch15_15_H4 | XAUUSD | H4 | 0.25% | 8 | -438 | -121 | 404 |
| donch30_10_H4 | XAUUSD | H4 | 0.25% | 9 | -449 | -121 | 318 |
| donch30_15_H4 | XAUUSD | H4 | 0.25% | 7 | -547 | -121 | 290 |
| donch40_10_H4 | XAUUSD | H4 | 0.25% | 8 | -376 | -121 | 283 |
| donch40_15_H4 | XAUUSD | H4 | 0.25% | 6 | -367 | -121 | 259 |
| donch20_15_H4 | XAUUSD | H4 | 0.25% | 7 | -486 | -121 | 351 |
| donch20_5_H4 | XAUUSD | H4 | 0.25% | 5 | -497 | -77 | 470 |
| donch20_10_adx18_H4 | XAUUSD | H4 | 0.25% | 13 | -421 | -121 | 322 |
| donch20_10_adx20_H4 | XAUUSD | H4 | 0.25% | 12 | -374 | -136 | 291 |
| donch20_10_adx22_H4 | XAUUSD | H4 | 0.25% | 10 | -279 | -136 | 267 |
| donch20_10_adx25_H4 | XAUUSD | H4 | 0.25% | 6 | -318 | -129 | 228 |
| donch20_10_stop1.5_H4 | XAUUSD | H4 | 0.25% | 8 | -513 | -226 | 436 |
| donch20_10_stop3.0_H4 | XAUUSD | H4 | 0.25% | 7 | -238 | -74 | 256 |
| donch20_10_ma200_H4 | XAUUSD | H4 | 0.25% | 4 | -428 | -121 | 326 |
| donch80_40_H1 | XAUUSD | H1 | none | 2 | -1018 | -164 | 605 |
| donch80_40_adx20_H1 | XAUUSD | H1 | none | 1 | -1162 | -164 | 559 |
| donch20_10_adx20_D1 | XAUUSD | D1 | 0.75% | 0 | -544 | -163 | 52 |
| donch20_10_H4_XAG | XAGUSD | H4 | none | -1 | -764 | -113 | 318 |
| donch20_10_adx20_H4_XAG | XAGUSD | H4 | none | -2 | -768 | -113 | 243 |
| donch55_20_H4_XAG | XAGUSD | H4 | 0.25% | 3 | -553 | -127 | 176 |
| bos_hv_htf_noflip_M30 | XAUUSD | M30 | 0.25% | 14 | -506 | -64 | 289 |
| bos_hv_htf_LN_M30 | XAUUSD | M30 | 0.25% | 12 | -421 | -63 | 262 |
| bos_hv_htfD20_M30 | XAUUSD | M30 | 0.25% | 13 | -534 | -64 | 323 |
| bos_hv_htfD100_M30 | XAUUSD | M30 | 0.25% | 18 | -386 | -64 | 273 |
| bos_hv_htfH4_50_M30 | XAUUSD | M30 | 0.25% | 16 | -510 | -58 | 420 |
| bos_hv_be1_M30 | XAUUSD | M30 | none | 2 | -651 | -66 | 605 |
| bos_hv_nocmf_M30 | XAUUSD | M30 | 0.25% | 11 | -530 | -78 | 664 |
| bos_hv_noma_M30 | XAUUSD | M30 | none | -3 | -973 | -76 | 973 |
| bos_hv_sw3_M30 | XAUUSD | M30 | 0.25% | 10 | -411 | -67 | 474 |
| bos_hv_fixR2_M30 | XAUUSD | M30 | none | 3 | -655 | -66 | 615 |
| bos_hv_M15 | XAUUSD | M15 | 0.25% | -15 | -430 | -76 | 271 |
| bos_hv_htf_H1 | XAUUSD | H1 | 0.50% | 0 | -581 | -101 | 259 |
| donch20_10_adx20_stop3_H4 | XAUUSD | H4 | 0.50% | 15 | -591 | -227 | 295 |
| donch20_10_adx20_trail4_H4 | XAUUSD | H4 | 0.25% | 11 | -358 | -42 | 305 |
| donch20_10_adx20_long_H4 | XAUUSD | H4 | 0.25% | 9 | -260 | -136 | 156 |
| donch30_10_adx20_H4 | XAUUSD | H4 | 0.25% | 11 | -312 | -136 | 249 |
| donch15_10_adx20_H4 | XAUUSD | H4 | 0.25% | 14 | -350 | -136 | 332 |
| donch20_15_adx20_H4 | XAUUSD | H4 | 0.25% | 11 | -389 | -136 | 268 |
| sess0-8_range_atrp0.5_H1 | XAUUSD | H1 | 0.25% | 7 | -344 | -77 | 630 |
| sess0-8_range_atrp0.5_M30 | XAUUSD | M30 | 0.25% | 6 | -352 | -83 | 327 |
| sess0-8_range_atrp0.7_H1 | XAUUSD | H1 | none | -0 | -619 | -83 | 339 |
| sess0-8_range_atrp0.7_M30 | XAUUSD | M30 | 0.50% | 0 | -479 | -155 | 172 |
| sess0-8_range_tp2_atrp0.6_H1 | XAUUSD | H1 | 0.25% | -1 | -577 | -38 | 487 |
| donch20_10_atrp0.5_H4 | XAUUSD | H4 | 0.25% | 2 | -369 | -80 | 238 |
| donch20_10_atrpmax0.5_H4 | XAUUSD | H4 | 0.50% | 27 | -591 | -242 | 230 |
| squeeze_H4 | XAUUSD | H4 | 0.25% | 12 | -284 | -77 | 246 |
| squeeze_trail3_H4 | XAUUSD | H4 | 0.25% | 9 | -485 | -33 | 269 |
| squeeze_sq0.1_H4 | XAUUSD | H4 | 0.25% | 7 | -264 | -74 | 178 |
| squeeze_sq0.3_H4 | XAUUSD | H4 | 0.25% | 11 | -292 | -141 | 291 |
| squeeze_H1 | XAUUSD | H1 | none | 4 | -1016 | -112 | 1168 |
| squeeze_trail3_H1 | XAUUSD | H1 | none | 2 | -825 | -69 | 1228 |
| squeeze_sq0.1_H1 | XAUUSD | H1 | none | 4 | -970 | -112 | 816 |
| squeeze_sq0.3_H1 | XAUUSD | H1 | none | 2 | -1207 | -112 | 1399 |
| squeeze_M30 | XAUUSD | M30 | none | -53 | -4219 | -83 | 1411 |
| squeeze_H4_XAG | XAGUSD | H4 | 0.25% | -3 | -462 | -113 | 220 |
| pull_rsi2_atrp0.6_H1 | XAUUSD | H1 | none | -7 | -841 | -57 | 851 |
| pull_rsi2_adxmax20_H1 | XAUUSD | H1 | none | -13 | -1467 | -48 | 766 |
| donch20_10_atrpmax0.3_H4 | XAUUSD | H4 | 0.25% | 9 | -319 | -121 | 171 |
| donch20_10_atrpmax0.4_H4 | XAUUSD | H4 | 0.25% | 11 | -269 | -121 | 210 |
| donch20_10_atrpmax0.6_H4 | XAUUSD | H4 | 0.25% | 11 | -339 | -121 | 268 |
| donch20_10_atrpmax0.7_H4 | XAUUSD | H4 | 0.25% | 7 | -480 | -121 | 314 |
| donch20_10_atrpmax0.5_w250_H4 | XAUUSD | H4 | 0.25% | 10 | -397 | -121 | 250 |
| donch20_10_atrpmax0.5_w1000_H4 | XAUUSD | H4 | 0.25% | 13 | -380 | -121 | 238 |
| donch20_10_atrpmax0.5_w2000_H4 | XAUUSD | H4 | 0.25% | 13 | -310 | -121 | 213 |
| donch15_10_atrpmax0.5_H4 | XAUUSD | H4 | 0.25% | 13 | -260 | -121 | 271 |
| donch30_10_atrpmax0.5_H4 | XAUUSD | H4 | 0.25% | 13 | -327 | -121 | 191 |
| donch20_15_atrpmax0.5_H4 | XAUUSD | H4 | 0.25% | 11 | -301 | -121 | 211 |
| donch40_15_atrpmax0.5_H4 | XAUUSD | H4 | 0.25% | 8 | -397 | -121 | 157 |
| donch55_20_atrpmax0.5_H4 | XAUUSD | H4 | 0.25% | 7 | -311 | -142 | 131 |
| donch20_10_atrpmax0.5_adx20_H4 | XAUUSD | H4 | 0.25% | 16 | -255 | -136 | 165 |
| donch20_10_atrpmax0.5_stop3_H4 | XAUUSD | H4 | 0.50% | 17 | -400 | -182 | 217 |
| donch20_10_atrpmax0.5_H4_XAG | XAGUSD | H4 | 0.25% | -1 | -549 | -113 | 214 |
| donch55_20_atrpmax0.5_H4_XAG | XAGUSD | H4 | 0.25% | 2 | -377 | -127 | 114 |
| donch80_40_atrpmax0.5_H1 | XAUUSD | H1 | 0.25% | 3 | -506 | -82 | 278 |
| donch20_10_atrpmax0.5_D1 | XAUUSD | D1 | 0.50% | 3 | -499 | -126 | 44 |
| combo_donLV_bos_M30 | XAUUSD | M30 | 0.25% | 17 | -303 | -136 | 289 |
| combo_bos_donLV_M30 | XAUUSD | M30 | 0.25% | 17 | -303 | -136 | 289 |
| combo_donLV_bos50_M30 | XAUUSD | M30 | 0.25% | 15 | -571 | -136 | 286 |
| combo_donADX_bos_M30 | XAUUSD | M30 | 0.25% | 13 | -334 | -136 | 319 |
| combo_donLV_sqz_bos_M30 | XAUUSD | M30 | 0.25% | 18 | -374 | -136 | 320 |
| combo_donLV_bos_M30_noflip | XAUUSD | M30 | 0.25% | 20 | -303 | -136 | 283 |
| combo_donLV_sqz_H1 | XAUUSD | H1 | 0.25% | 14 | -291 | -136 | 292 |
| donLV_adx20_stop2.5_H4 | XAUUSD | H4 | 0.50% | 25 | -530 | -281 | 165 |
| donLV_adx20_stop3.0_H4 | XAUUSD | H4 | 0.50% | 21 | -412 | -218 | 161 |
| donLV_adx20_stop4.0_H4 | XAUUSD | H4 | 0.50% | 14 | -347 | -121 | 160 |
| donLV_adx20_x7_H4 | XAUUSD | H4 | 0.50% | 32 | -402 | -168 | 178 |
| donLV_adx20_x12_H4 | XAUUSD | H4 | 0.25% | 15 | -274 | -136 | 159 |
| donLV_adx20_trail5_H4 | XAUUSD | H4 | 0.50% | 34 | -437 | -108 | 169 |
| donLV_adx15_H4 | XAUUSD | H4 | 0.25% | 15 | -269 | -121 | 206 |
| donLV_adx25_H4 | XAUUSD | H4 | 0.25% | 10 | -302 | -129 | 126 |
| donLV15_adx20_H4 | XAUUSD | H4 | 0.25% | 18 | -237 | -136 | 190 |
| donLV30_adx20_H4 | XAUUSD | H4 | 0.25% | 14 | -309 | -136 | 146 |
| donLV_adx20_mtf2h_H1 | XAUUSD | H1 | 0.25% | 12 | -476 | -98 | 362 |
| donLV_adx20_mtf6h_H1 | XAUUSD | H1 | 0.50% | 20 | -442 | -182 | 119 |
| donLV_adx20_mtf8h_H1 | XAUUSD | H1 | 0.50% | 10 | -529 | -148 | 98 |
| donLV_adx20_mtf12h_H1 | XAUUSD | H1 | 0.50% | 4 | -336 | -149 | 59 |
| donLV_adx20_H4_XAG | XAGUSD | H4 | 0.25% | -0 | -449 | -113 | 151 |
| donLV_adx20_stop3_H4_XAG | XAGUSD | H4 | 0.25% | -0 | -310 | -25 | 82 |
| grid_donLV15_x5_trNone_st2.0_H4 | XAUUSD | H4 | 0.75% | 46 | -586 | -235 | 221 |
| grid_donLV15_x5_trNone_st2.5_H4 | XAUUSD | H4 | 0.75% | 35 | -533 | -244 | 218 |
| grid_donLV15_x5_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.75% | 45 | -580 | -140 | 221 |
| grid_donLV15_x5_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 35 | -505 | -120 | 218 |
| grid_donLV15_x5_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.75% | 42 | -586 | -160 | 221 |
| grid_donLV15_x5_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 32 | -533 | -138 | 218 |
| grid_donLV15_x5_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.75% | 46 | -586 | -192 | 221 |
| grid_donLV15_x5_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 35 | -533 | -174 | 218 |
| grid_donLV15_x7_trNone_st2.0_H4 | XAUUSD | H4 | 0.50% | 38 | -408 | -168 | 203 |
| grid_donLV15_x7_trNone_st2.5_H4 | XAUUSD | H4 | 0.75% | 44 | -579 | -244 | 199 |
| grid_donLV15_x7_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 37 | -403 | -91 | 204 |
| grid_donLV15_x7_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 44 | -555 | -129 | 200 |
| grid_donLV15_x7_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 37 | -408 | -96 | 204 |
| grid_donLV15_x7_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 43 | -579 | -138 | 200 |
| grid_donLV15_x7_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 39 | -408 | -116 | 203 |
| grid_donLV15_x7_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 46 | -579 | -174 | 199 |
| grid_donLV15_x10_trNone_st2.0_H4 | XAUUSD | H4 | 0.25% | 18 | -237 | -136 | 190 |
| grid_donLV15_x10_trNone_st2.5_H4 | XAUUSD | H4 | 0.50% | 28 | -491 | -281 | 188 |
| grid_donLV15_x10_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 36 | -437 | -91 | 199 |
| grid_donLV15_x10_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 26 | -392 | -82 | 195 |
| grid_donLV15_x10_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 40 | -443 | -108 | 194 |
| grid_donLV15_x10_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 28 | -411 | -92 | 191 |
| grid_donLV15_x10_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 42 | -443 | -117 | 191 |
| grid_donLV15_x10_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 30 | -411 | -116 | 188 |
| grid_donLV20_x5_trNone_st2.0_H4 | XAUUSD | H4 | 0.50% | 26 | -387 | -168 | 193 |
| grid_donLV20_x5_trNone_st2.5_H4 | XAUUSD | H4 | 0.75% | 29 | -577 | -229 | 193 |
| grid_donLV20_x5_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.75% | 40 | -583 | -137 | 193 |
| grid_donLV20_x5_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 29 | -558 | -110 | 193 |
| grid_donLV20_x5_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 24 | -387 | -96 | 193 |
| grid_donLV20_x5_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 26 | -577 | -138 | 193 |
| grid_donLV20_x5_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 26 | -387 | -116 | 193 |
| grid_donLV20_x5_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.75% | 29 | -577 | -174 | 193 |
| grid_donLV20_x7_trNone_st2.0_H4 | XAUUSD | H4 | 0.50% | 32 | -402 | -168 | 178 |
| grid_donLV20_x7_trNone_st2.5_H4 | XAUUSD | H4 | 0.50% | 24 | -393 | -153 | 176 |
| grid_donLV20_x7_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 32 | -383 | -86 | 179 |
| grid_donLV20_x7_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 24 | -367 | -82 | 177 |
| grid_donLV20_x7_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 31 | -402 | -96 | 179 |
| grid_donLV20_x7_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 24 | -393 | -92 | 177 |
| grid_donLV20_x7_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 33 | -402 | -116 | 178 |
| grid_donLV20_x7_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 25 | -393 | -116 | 176 |
| grid_donLV20_x10_trNone_st2.0_H4 | XAUUSD | H4 | 0.25% | 16 | -255 | -136 | 165 |
| grid_donLV20_x10_trNone_st2.5_H4 | XAUUSD | H4 | 0.50% | 25 | -530 | -281 | 165 |
| grid_donLV20_x10_tr4.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 31 | -394 | -86 | 174 |
| grid_donLV20_x10_tr4.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 23 | -382 | -82 | 172 |
| grid_donLV20_x10_tr5.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 34 | -437 | -108 | 169 |
| grid_donLV20_x10_tr5.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 25 | -428 | -92 | 168 |
| grid_donLV20_x10_tr6.0_st2.0_H4 | XAUUSD | H4 | 0.50% | 37 | -437 | -117 | 166 |
| grid_donLV20_x10_tr6.0_st2.5_H4 | XAUUSD | H4 | 0.50% | 27 | -428 | -116 | 165 |
| donLV20_x7_tr5_H4_USDJPY | USDJPY | H4 | 0.25% | 1 | -593 | -61 | 192 |
| donLV20_x7_tr5_H4_EURUSD | EURUSD | H4 | 0.25% | -0 | -517 | -52 | 218 |
| donLV20_x7_tr5_H4_GBPUSD | GBPUSD | H4 | none | -5 | -834 | -47 | 206 |
| donLV20_x7_tr5_H4_AUDUSD | AUDUSD | H4 | none | -5 | -727 | -44 | 198 |
| donLV20_x7_tr5_H4_spread2x | XAUUSD | H4 | 0.50% | 29 | -441 | -96 | 179 |
| donLV15_x7_tr5_H4_spread2x | XAUUSD | H4 | 0.50% | 33 | -422 | -96 | 204 |
| donLV20_x7_tr5_H4_noflip | XAUUSD | H4 | 0.50% | 31 | -402 | -96 | 179 |
| donLV20_x7_tr5_long_H4 | XAUUSD | H4 | 0.75% | 36 | -465 | -184 | 97 |
| donLV20_x7_tr5_short_H4 | XAUUSD | H4 | 0.50% | 7 | -448 | -60 | 82 |
| donLV20_x7_tr5_noadx_H4 | XAUUSD | H4 | 0.25% | 12 | -309 | -64 | 246 |
| donLV20_x7_tr5_noatrp_H4 | XAUUSD | H4 | 0.25% | 10 | -337 | -46 | 319 |
| donLV20_x7_tr5_H4_XAG | XAGUSD | H4 | 0.25% | -3 | -505 | -62 | 158 |
| bos_hvD100_trail3_M30 | XAUUSD | M30 | 0.25% | 1 | -448 | -53 | 451 |
| bos_hvD100_trail5_M30 | XAUUSD | M30 | 0.25% | 11 | -368 | -62 | 345 |
| bos_hvD100_long_M30 | XAUUSD | M30 | 0.50% | 34 | -467 | -106 | 161 |
| bos_hvD100_stopatr1.5_M30 | XAUUSD | M30 | 0.25% | 21 | -320 | -64 | 259 |
| bos_hvD100_atrp0.5_M30 | XAUUSD | M30 | 0.25% | 20 | -448 | -64 | 328 |
| bos_hvD100_atrp0.7_M30 | XAUUSD | M30 | 0.25% | 11 | -333 | -58 | 238 |
| bos_hvD100_noflip_M30 | XAUUSD | M30 | 0.25% | 18 | -386 | -64 | 273 |
| bos_hvD100_spread2x_M30 | XAUUSD | M30 | 0.25% | 16 | -401 | -60 | 274 |
| bos_hvD100_M30_XAG | XAGUSD | M30 | none | -12 | -1071 | -52 | 269 |
| squeeze_x7_tr5_H4 | XAUUSD | H4 | 0.25% | 10 | -482 | -77 | 263 |
| squeeze_x7_H4 | XAUUSD | H4 | 0.25% | 10 | -525 | -77 | 263 |
| squeeze_adx_x7_tr5_H4 | XAUUSD | H4 | 0.50% | 20 | -581 | -94 | 148 |
| squeeze_x7_tr5_H4_XAG | XAGUSD | H4 | 0.25% | -4 | -488 | -80 | 230 |

(avg_month/max_dd/worst_day are at best_risk, or at 0.25% when none is safe.)

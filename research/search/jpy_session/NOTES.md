# jpy_session family: notes (in-sample 2015-2023 only)

Every number here comes from `research/prop/harness.py` (`H.score`) or from the fast R-multiple
prescreen (`prescreen.py`, which uses the same fills and costs, checked against a loop version
on CHFJPY: -161.1R vs -161.4R). No 2024+ data was read. PROP_OOS was never set.

Files:
- `strategies.py`: every builder. Candidates are `build_index_turn_of_month`, `build_gold_turn_of_month`,
  `build_jpy_week_cycle` and `build_monday_long`. The generic builders are `build_session`,
  `build_multi_session`, `build_turn_of_month`, `build_intraday_momentum` and `build_session_breakout`.
- `data.py`: loader. It uses `H.load(split="is")`. When this family started, the JPY crosses were not in data/search
  yet, so the first 6 scored runs (rows 1-6) used the older exports in data/ (same broker feed, identical USDJPY
  closes on every overlapping bar). Once the background job wrote data/search, all later runs used it. It pickles
  in-sample frames to `_cache/`, because the machine was so short of memory that CSV parsing kept failing.
- `prescreen.py`: vectorised R-multiple grid tool. It is not the judge.
- `exp01..exp22_*.py`: every experiment. `results.jsonl` logs each harness run, and `grid_*.csv` holds the prescreen grids.

## 1. The live CHFJPY "session" rule fails in-sample

Re-implemented exactly (`build_chfjpy_live`: long after the broker hour-0 bar closes, stop 2 x simple ATR14, 12-bar hold).

| pair | net @0.25% | avg/mo | max DD | safe? |
|---|---|---|---|---|
| CHFJPY | -3,793 | -35 | -4,470 | no |
| EURJPY | -3,060 | -28 | -3,385 | no |
| GBPJPY | -2,798 | -26 | -3,185 | no |
| AUDJPY | -2,316 | -21 | -2,588 | no |
| NZDJPY | -789 | -7 | -1,372 | no (vol_min 0.1 skips most trades) |
| CADJPY | -4,976 | -46 | -4,994 | no |
| USDJPY | -4,273 | -39 | -4,385 | no |

Why it loses (exp21_live_diag, exp03, exp08, exp10):
- **The gross edge is real but small, and costs are larger.** Before costs the hour-0 long makes +0.06 to +0.09 R a
  trade (all 7 pairs). The harness costs (spread floor, which is 2.5 pips on CHFJPY and 2.0 on EURJPY, the wide rollover
  bar spread, plus $14/lot commission) take 0.10-0.20 R a trade. Net is -0.05 to -0.09 R a trade. CHFJPY made money net
  in only 1 of 9 years (2022), and only barely.
- **Almost all of that gross edge comes in the first hour after entry (01:00-02:00 broker time).** The weekday x hour return
  map shows the bar into rollover (hour 23) and the rollover bar (hour 0) falling, and hour 1 rising, on every weekday.
  That matches bid prices dipping while the spread widens and recovering when it narrows. It is mostly a quoting effect of
  rollover, not a flow you can trade. Entering at hour 1 instead removes it, and that variant is even worse
  (CHFJPY -6,217, EURJPY -5,550).
- **What is left is mostly long beta.** The correlation between monthly net R and the pair's monthly return is 0.54-0.62.
  The months that lost are the months the cross fell: the bottom third of months averages -4.3R, the top third +1.2R.
  Gross was positive only in the JPY-weakening years 2021-2023, which is why it looks good recently and fails in 2015-2020.
- No filter fixed it. Tried: D1 SMA 20/50/100/200, D1 momentum 20/60, H1 SMA 200/500, ATR-ratio high/low, each weekday,
  no-Monday. Every one stayed net negative averaged over the 7 pairs (-0.05 to -0.12 R a trade, exp03 table).
  The short mirror is worse at every hour.
- Full hour (0-23) x hold (2-23) x side grid on 7 JPY pairs (exp02): no cell has positive average net R. The best
  average cell is -0.053 R. There is no plateau to find. The gross map shows the long-at-hour-0 ridge (+0.04..+0.08)
  and nothing else.
- Gotobi / Tokyo-fix days (exp08) add about 0.02-0.04 R gross to the hour-0 long. Net is still negative on all 5 pairs tested.

## 2. Weekly pattern in JPY crosses (weak, small)

The weekday x hour map (exp10) shows JPY crosses rising on Monday (about +0.4 ATR(H1) over the day) and falling
Thursday-Friday (Friday -0.37 ATR). That gives:
- Monday long (hour 0-8, hold 23-47 bars): +0.03..+0.08 R net, positive on 5-6 of 7 pairs. The plateau runs across entry
  hours 0 and 3-8 and holds 30-47 (exp04/exp05). Harness: EURJPY hold47 +$16/mo, AUDJPY +$20/mo, both only safe at 0.25%.
  CHFJPY, GBPJPY and CADJPY are not safe. Positive in only 4 of 9 years (2016, 2020, 2022, 2023 carry it).
- Friday short (hour 1, hold 22) only when the D1 close is below its 200-day SMA: +$5-14/mo on 5 of 7 pairs.
- Combining them (`build_jpy_week_cycle`): EURJPY +$21/mo at 0.25% (d1 100: +$19, mon_hold 47: +$22). CADJPY, CHFJPY
  and USDJPY are not safe. WEAK. t-stat is about 1 per pair, so this is close to noise.
- "Monday after a down week" (prior 120 bars down): AUDJPY +$32-37/mo, but EURJPY only +$10, CADJPY 0, CHFJPY +2,
  NZDJPY 0. This is a one-pair result, so it is REJECTED under the anti-overfit rule.

## 3. Non-JPY FX, metals and indices, same time-of-day idea

- FX majors and crosses (EURUSD GBPUSD AUDUSD NZDUSD USDCAD USDCHF EURGBP EURCHF GBPCHF AUDCAD), full hour x hold grid
  (exp02 fx): the best cell is GBPUSD short hour 6 hold 18 at +0.010 R. That is GBP's downtrend, not a session effect.
  Nothing usable.
- Gold and silver hour x hold grid: nothing positive after costs. The XAUUSD hour-0 cell is only 50 bars. Silver costs
  (0.03 floor) are about 0.15-0.2 R a trade.
- Indices: long US30/US500/DE40 entered at hour 15-20 with a 1-day hold is +0.05..+0.09 R net. That is just equity
  drift (beta). Max DD is 30-40R, so it is mostly not safe (US30 h20 hold18 +$15/mo at 0.25%). A D1 trend filter did not help.
- Intraday momentum / reversal (sign of the move since hour X, traded at hour Y): grid of 23 x 12 window pairs x hold x
  follow/fade on US500 US30 DE40 XAUUSD (exp09). The best average cell is +0.027 R, and nothing holds across symbols.
- Asian-range breakout (range hours 0-6, entries until 14, exit 21): every one of 6 symbols negative (GBPJPY -$35/mo,
  EURUSD -$37/mo, XAUUSD about 0). TP 2R, a D1 filter and a half-range stop also failed.

## 4. What does work: turn-of-month (calendar timing)

Rule: enter on the last weekday of the month (k=0 business days left, which is pure calendar, so known in advance) at a
fixed broker hour. Stop 3 x ATR14(H1), exit after N H1 bars. The prescreen (exp14/exp17) shows broad plateaus:
- Indices (US500, US30, DE40): long k=0 at hour 20 or 22, hold 24-96: +0.18..+0.43 R a trade on all three indices.
  k=1 and k=2 are about 0 or negative, so the effect sits on the last day, as in the published turn-of-month anomaly
  (Ariel 1987; Lakonishok-Smidt 1988; McConnell-Xu 2008). Short is negative everywhere.
- Gold (XAUUSD): long k=0 at every entry hour from 2 to 22 and every hold from 48 to 120 is positive (+0.1..+0.6 R),
  with 5-8 of 9 years positive. k=1 at hour 14 or later is also positive. Silver is positive gross at k=0, hours 10 and
  later, but costs eat it. JPY crosses show no consistent TOM effect (signs flip across hours, exp20). That contrast
  suggests the gold and index plateau is not a general artefact.

Harness results (all SAFE, all positive):

| strategy | symbol | best_risk | avg/mo | max DD | worst day | trades |
|---|---|---|---|---|---|---|
| index TOM h22 hold24 sl3 | US500 | 1.25% | +27 | -554 | -183 | 89 |
| index TOM h22 hold48 | US500 | 1.00% | +24 | -585 | -239 | 89 |
| index TOM h22 hold72 / sl5 / h20 / hold96 | US500 | 0.5-0.75% | +8..+13 | | | |
| index TOM h22 hold72 | DE40 | 1.00% | +28 | -588 | -247 | 83 |
| index TOM h22 hold24/48/96, h20, sl5 | DE40 | 0.75-1% | +15..+25 | | | |
| index TOM h22 hold24 / hold72 sl5 / hold48 | US30 | 0.75-1% | +13..+16 | | | |
| gold TOM h14 hold96 sl3 | XAUUSD | 0.50% | +26 | -461 | -174 | 107 |
| gold TOM h16 / h12 / hold120 / hold48 / sl4 | XAUUSD | 0.50% | +17..+22 | | | |
| gold TOM h10 / h20 / h4 / sl2 / tp2 / d1ma50 | XAUUSD | 0.25-0.5% | +7..+14 | | | |

The limits: only about 1 trade a month, so dollars are small ($15-28/mo, which is 0.15-0.28% a month). On those numbers
alone a Stellar Lite phase-1 +8% would take years. The daily limit is binding: overnight and weekend gaps through a
3 x H1-ATR stop make the worst day about 1.5-3.5R. These are best used as a low-correlation add-on, not a primary
strategy. USTEC has only 18 in-sample trades (data from 2022-07), so it is not judged.

## 5. Lessons

1. With the harness cost model (conservative spread floors plus $14/lot), intraday time-of-day trades on FX need at
   least 0.15 R of gross edge a trade just to break even with 2 x ATR(H1) stops. The famous session effects are about
   0.05-0.09 R. Holding longer does not help much: the gross R barely grows with the hold.
2. The hour-0 / rollover effect is mostly a quoting artefact around the daily rollover. Do not build on it.
3. The live CHFJPY rule's recent profit is consistent with JPY-weakness beta (2021-2023 gross positive, 2015-2020
   negative). It should be treated as regime exposure, with a trend/regime kill switch, not as a session edge.
4. The calendar effect (turn-of-month) survives costs because one trade covers a multi-day move. It is robust across
   neighbouring hours and holds and across 3 indices plus gold. It is small because it trades once a month.
5. The harness rule "best_risk = highest safe risk in 0.25% steps" makes low-trade-count results jumpy. For example,
   AUDJPY Monday-downweek moves from $17 to $37 just by changing the hold from 36 to 47. Compare plateaus, not single runs.

## 6. Every scored harness run

Rows 1-6 used the older data/ exports for the JPY crosses, before data/search had them. Rows 7 onward all use data/search.

| # | name | fn | symbol | tf | best_risk | avg_month $ | net $ | max_dd $ | worst_day $ | trades | green |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | live_h0_hold12_CHFJPY | chfjpy_live | CHFJPY | H1 | none safe | -40 | -3924 | -4064 | -25 | 2087 | 30% |
| 2 | live_h0_hold12_EURJPY | chfjpy_live | EURJPY | H1 | none safe | -26 | -2568 | -2902 | -25 | 2089 | 36% |
| 3 | live_h0_hold12_GBPJPY | chfjpy_live | GBPJPY | H1 | none safe | -27 | -2633 | -2990 | -25 | 2086 | 30% |
| 4 | live_h0_hold12_AUDJPY | chfjpy_live | AUDJPY | H1 | none safe | -16 | -1512 | -2225 | -25 | 2089 | 43% |
| 5 | live_h0_hold12_NZDJPY | chfjpy_live | NZDJPY | H1 | none safe | -8 | -808 | -1372 | -25 | 514 | 38% |
| 6 | live_h0_hold12_USDJPY | chfjpy_live | USDJPY | H1 | none safe | -39 | -4273 | -4385 | -25 | 2326 | 27% |
| 7 | mon_long_h0_sl2_hold36 | session | CHFJPY | H1 | none safe | -1 | -103 | -763 | -73 | 461 | 43% |
| 8 | mon_long_h0_sl2_hold36 | session | EURJPY | H1 | 0.25% | 14 | 1579 | -500 | -52 | 463 | 50% |
| 9 | mon_long_h0_sl2_hold36 | session | GBPJPY | H1 | none safe | 4 | 429 | -717 | -49 | 462 | 48% |
| 10 | mon_long_h0_sl2_hold36 | session | AUDJPY | H1 | 0.25% | 16 | 1773 | -595 | -70 | 461 | 52% |
| 11 | mon_long_h0_sl2_hold36 | session | NZDJPY | H1 | 0.25% | 1 | 162 | -295 | -36 | 66 | 14% |
| 12 | mon_long_h0_sl2_hold36 | session | CADJPY | H1 | none safe | 4 | 399 | -812 | -53 | 464 | 52% |
| 13 | mon_long_h0_sl2_hold36 | session | USDJPY | H1 | 0.25% | 8 | 876 | -573 | -57 | 464 | 49% |
| 14 | fri_short_h1_sl2_hold22_d1ma200 | session | CHFJPY | H1 | 0.25% | 0 | 44 | -383 | -25 | 146 | 19% |
| 15 | fri_short_h1_sl2_hold22_d1ma200 | session | EURJPY | H1 | 0.50% | 14 | 1486 | -470 | -50 | 180 | 25% |
| 16 | fri_short_h1_sl2_hold22_d1ma200 | session | GBPJPY | H1 | 0.50% | 9 | 970 | -551 | -50 | 175 | 22% |
| 17 | fri_short_h1_sl2_hold22_d1ma200 | session | AUDJPY | H1 | 0.25% | 5 | 524 | -355 | -50 | 216 | 28% |
| 18 | fri_short_h1_sl2_hold22_d1ma200 | session | NZDJPY | H1 | 0.50% | 8 | 863 | -547 | -50 | 176 | 28% |
| 19 | fri_short_h1_sl2_hold22_d1ma200 | session | CADJPY | H1 | 0.25% | 5 | 500 | -334 | -64 | 194 | 30% |
| 20 | fri_short_h1_sl2_hold22_d1ma200 | session | USDJPY | H1 | 0.25% | -3 | -282 | -511 | -50 | 190 | 22% |
| 21 | idx_long_h15_hold23 | session | US30 | H1 | none safe | 35 | 3831 | -1053 | -93 | 1897 | 48% |
| 22 | idx_long_h14_hold23 | session | US30 | H1 | none safe | 16 | 1689 | -1139 | -182 | 1904 | 45% |
| 23 | idx_long_h16_hold23 | session | US30 | H1 | none safe | 26 | 2777 | -741 | -87 | 1855 | 47% |
| 24 | idx_long_h17_hold23 | session | US30 | H1 | none safe | 23 | 2495 | -715 | -136 | 1808 | 49% |
| 25 | idx_long_h15_hold18 | session | US30 | H1 | none safe | 28 | 3006 | -943 | -93 | 1941 | 44% |
| 26 | idx_long_h20_hold18 | session | US30 | H1 | 0.25% | 15 | 1600 | -476 | -94 | 1716 | 50% |
| 27 | idx_long_h20_hold23 | session | US30 | H1 | none safe | 20 | 2170 | -832 | -94 | 1683 | 48% |
| 28 | idx_long_h15_hold23 | session | US500 | H1 | none safe | 32 | 3508 | -1259 | -157 | 1998 | 53% |
| 29 | idx_long_h20_hold23 | session | US500 | H1 | 0.25% | 20 | 2117 | -547 | -131 | 1945 | 48% |
| 30 | idx_long_h15_hold23 | session | DE40 | H1 | none safe | 18 | 1922 | -1000 | -103 | 1761 | 52% |
| 31 | idx_long_h15_hold18 | session | DE40 | H1 | 0.25% | 20 | 2200 | -590 | -103 | 1985 | 52% |
| 32 | live_h0_hold12 | chfjpy_live | CHFJPY | H1 | none safe | -35 | -3793 | -4470 | -25 | 2322 | 31% |
| 33 | live_h0_hold12 | chfjpy_live | EURJPY | H1 | none safe | -28 | -3060 | -3385 | -25 | 2325 | 34% |
| 34 | live_h0_hold12 | chfjpy_live | GBPJPY | H1 | none safe | -26 | -2798 | -3185 | -25 | 2323 | 30% |
| 35 | live_h0_hold12 | chfjpy_live | AUDJPY | H1 | none safe | -21 | -2316 | -2588 | -25 | 2314 | 40% |
| 36 | live_h0_hold12 | chfjpy_live | NZDJPY | H1 | none safe | -7 | -789 | -1372 | -25 | 521 | 36% |
| 37 | live_h0_hold12 | chfjpy_live | CADJPY | H1 | none safe | -46 | -4976 | -4994 | -25 | 2326 | 23% |
| 38 | live_h0_hold12 | chfjpy_live | USDJPY | H1 | none safe | -39 | -4273 | -4385 | -25 | 2326 | 27% |
| 39 | h1_long_hold12 | session | CHFJPY | H1 | none safe | -57 | -6217 | -7052 | -26 | 2324 | 27% |
| 40 | h1_long_hold12 | session | EURJPY | H1 | none safe | -51 | -5550 | -5575 | -25 | 2325 | 29% |
| 41 | mon_long_h0_hold47 | session | EURJPY | H1 | 0.25% | 16 | 1712 | -409 | -59 | 463 | 50% |
| 42 | mon_long_h0_hold36_downweek | session | EURJPY | H1 | 0.25% | 10 | 1098 | -297 | -51 | 240 | 54% |
| 43 | mon_long_h0_hold47 | session | AUDJPY | H1 | 0.25% | 20 | 2155 | -585 | -70 | 461 | 58% |
| 44 | mon_long_h0_hold36_downweek | session | AUDJPY | H1 | 0.50% | 32 | 3487 | -556 | -98 | 215 | 57% |
| 45 | mon_long_h0_hold47 | session | USDJPY | H1 | none safe | 9 | 992 | -655 | -93 | 464 | 50% |
| 46 | mon_long_h0_hold36_downweek | session | USDJPY | H1 | 0.25% | 3 | 276 | -326 | -57 | 209 | 50% |
| 47 | mon_long_h0_hold47 | session | GBPJPY | H1 | none safe | 5 | 534 | -670 | -61 | 462 | 49% |
| 48 | mon_long_h0_hold36_downweek | session | GBPJPY | H1 | 0.25% | 6 | 673 | -390 | -40 | 217 | 51% |
| 49 | mon_long_h0_hold23 | session | EURJPY | H1 | 0.25% | 7 | 712 | -576 | -25 | 463 | 46% |
| 50 | mon_long_h4_hold36 | session | EURJPY | H1 | 0.25% | 15 | 1684 | -388 | -59 | 463 | 51% |
| 51 | mon_long_h0_hold36_sl3 | session | EURJPY | H1 | 0.25% | 11 | 1165 | -298 | -44 | 462 | 50% |
| 52 | mon_long_h0_hold23 | session | AUDJPY | H1 | 0.25% | 9 | 1002 | -524 | -25 | 461 | 53% |
| 53 | mon_long_h4_hold36 | session | AUDJPY | H1 | none safe | 9 | 988 | -715 | -55 | 461 | 46% |
| 54 | mon_long_h0_hold36_sl3 | session | AUDJPY | H1 | 0.25% | 11 | 1186 | -372 | -46 | 461 | 61% |
| 55 | week_monlong_frishort | multi_session | EURJPY | H1 | 0.25% | 21 | 2251 | -476 | -52 | 643 | 57% |
| 56 | week_monlong_frishort | multi_session | GBPJPY | H1 | none safe | 8 | 840 | -702 | -49 | 636 | 46% |
| 57 | week_monlong_frishort | multi_session | AUDJPY | H1 | none safe | 21 | 2297 | -814 | -70 | 677 | 56% |
| 58 | week_monlong_frishort | multi_session | NZDJPY | H1 | 0.25% | 1 | 150 | -400 | -36 | 109 | 17% |
| 59 | idx_long_h20_hold18_d1ma200 | session | US30 | H1 | none safe | 9 | 984 | -713 | -94 | 1493 | 42% |
| 60 | idx_long_h15_hold23_d1ma50 | session | US30 | H1 | none safe | 25 | 2746 | -885 | -93 | 1375 | 37% |
| 61 | idx_long_h20_hold18_d1ma200 | session | US500 | H1 | none safe | -8 | -818 | -1428 | -131 | 1579 | 34% |
| 62 | idx_long_h15_hold23_d1ma50 | session | US500 | H1 | none safe | 18 | 1961 | -1268 | -157 | 1411 | 43% |
| 63 | idx_long_h20_hold18_d1ma200 | session | DE40 | H1 | 0.25% | 3 | 296 | -591 | -98 | 1308 | 32% |
| 64 | idx_long_h15_hold23_d1ma50 | session | DE40 | H1 | 0.25% | 15 | 1628 | -565 | -94 | 1108 | 43% |
| 65 | tom_k0_h22_hold72_sl3 | turn_of_month | US500 | H1 | 0.50% | 12 | 1338 | -377 | -217 | 89 | 41% |
| 66 | tom_k0_h20_hold72_sl3 | turn_of_month | US500 | H1 | 0.50% | 8 | 917 | -547 | -186 | 94 | 39% |
| 67 | tom_k0_h22_hold48_sl3 | turn_of_month | US500 | H1 | 1.00% | 24 | 2577 | -585 | -239 | 89 | 45% |
| 68 | tom_k0_h22_hold96_sl3 | turn_of_month | US500 | H1 | 0.50% | 13 | 1397 | -536 | -217 | 89 | 37% |
| 69 | tom_k0_h22_hold72_sl5 | turn_of_month | US500 | H1 | 0.75% | 13 | 1354 | -362 | -224 | 89 | 47% |
| 70 | tom_k0_h22_hold24_sl3 | turn_of_month | US500 | H1 | 1.25% | 27 | 2969 | -554 | -183 | 89 | 53% |
| 71 | tom_k0_h22_hold72_sl3 | turn_of_month | US30 | H1 | 0.50% | 8 | 914 | -357 | -180 | 78 | 37% |
| 72 | tom_k0_h20_hold72_sl3 | turn_of_month | US30 | H1 | 0.50% | 6 | 667 | -496 | -166 | 87 | 35% |
| 73 | tom_k0_h22_hold48_sl3 | turn_of_month | US30 | H1 | 0.75% | 13 | 1429 | -490 | -150 | 88 | 44% |
| 74 | tom_k0_h22_hold96_sl3 | turn_of_month | US30 | H1 | 0.50% | 11 | 1161 | -407 | -180 | 78 | 36% |
| 75 | tom_k0_h22_hold72_sl5 | turn_of_month | US30 | H1 | 1.00% | 16 | 1740 | -346 | -203 | 86 | 47% |
| 76 | tom_k0_h22_hold24_sl3 | turn_of_month | US30 | H1 | 1.00% | 14 | 1548 | -480 | -146 | 88 | 48% |
| 77 | tom_k0_h22_hold72_sl3 | turn_of_month | DE40 | H1 | 1.00% | 28 | 3038 | -588 | -247 | 83 | 40% |
| 78 | tom_k0_h20_hold72_sl3 | turn_of_month | DE40 | H1 | 0.75% | 24 | 2577 | -595 | -197 | 91 | 44% |
| 79 | tom_k0_h22_hold48_sl3 | turn_of_month | DE40 | H1 | 1.00% | 25 | 2701 | -579 | -231 | 83 | 42% |
| 80 | tom_k0_h22_hold96_sl3 | turn_of_month | DE40 | H1 | 0.75% | 23 | 2537 | -511 | -173 | 83 | 35% |
| 81 | tom_k0_h22_hold72_sl5 | turn_of_month | DE40 | H1 | 1.00% | 15 | 1662 | -581 | -148 | 83 | 44% |
| 82 | tom_k0_h22_hold24_sl3 | turn_of_month | DE40 | H1 | 1.00% | 19 | 2047 | -520 | -152 | 83 | 47% |
| 83 | gold_tom_k0_h14_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 26 | 2828 | -461 | -174 | 107 | 52% |
| 84 | gold_tom_k0_h12_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 19 | 2011 | -532 | -174 | 107 | 49% |
| 85 | gold_tom_k0_h16_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 22 | 2373 | -455 | -148 | 107 | 50% |
| 86 | gold_tom_k0_h10_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.25% | 7 | 788 | -295 | -87 | 105 | 51% |
| 87 | gold_tom_k0_h20_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 10 | 1123 | -551 | -154 | 105 | 41% |
| 88 | gold_tom_k0_h14_hold72_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 15 | 1627 | -400 | -174 | 107 | 52% |
| 89 | gold_tom_k0_h14_hold120_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 20 | 2197 | -580 | -203 | 107 | 49% |
| 90 | gold_tom_k0_h14_hold48_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 17 | 1794 | -481 | -147 | 107 | 56% |
| 91 | gold_tom_k0_h14_hold96_sl2 | turn_of_month | XAUUSD | H1 | 0.25% | 11 | 1170 | -380 | -118 | 107 | 48% |
| 92 | gold_tom_k0_h14_hold96_sl4 | turn_of_month | XAUUSD | H1 | 0.50% | 18 | 1963 | -538 | -141 | 107 | 52% |
| 93 | gold_tom_k0_h4_hold96_sl3 | turn_of_month | XAUUSD | H1 | 0.50% | 11 | 1194 | -461 | -148 | 107 | 46% |
| 94 | silver_tom_k0_h14_hold96_sl3 | turn_of_month | XAGUSD | H1 | 0.25% | 2 | 183 | -414 | -82 | 99 | 41% |
| 95 | silver_tom_k0_h16_hold96_sl3 | turn_of_month | XAGUSD | H1 | 0.25% | 2 | 198 | -279 | -56 | 99 | 40% |
| 96 | asia_bo_0-6_to14_x21 | session_breakout | GBPJPY | H1 | none safe | -35 | -3761 | -3998 | -29 | 2029 | 33% |
| 97 | asia_bo_0-6_to14_x21 | session_breakout | EURJPY | H1 | none safe | -16 | -1726 | -2368 | -51 | 1902 | 45% |
| 98 | asia_bo_0-6_to14_x21 | session_breakout | USDJPY | H1 | none safe | -18 | -1971 | -2230 | -48 | 1712 | 40% |
| 99 | asia_bo_0-6_to14_x21 | session_breakout | XAUUSD | H1 | none safe | 0 | 53 | -1069 | -111 | 1888 | 46% |
| 100 | asia_bo_0-6_to14_x21 | session_breakout | GBPUSD | H1 | none safe | -40 | -4316 | -4740 | -28 | 2182 | 34% |
| 101 | asia_bo_0-6_to14_x21 | session_breakout | EURUSD | H1 | none safe | -37 | -4076 | -4917 | -51 | 2148 | 37% |
| 102 | asia_bo_0-6_to14_x21_tp2 | session_breakout | GBPJPY | H1 | none safe | -36 | -3957 | -4111 | -29 | 2029 | 39% |
| 103 | asia_bo_0-6_to14_x21_d1ma50 | session_breakout | GBPJPY | H1 | none safe | -20 | -2141 | -2375 | -26 | 1149 | 40% |
| 104 | asia_bo_0-8_to16_x22_half | session_breakout | GBPJPY | H1 | none safe | -40 | -4326 | -4802 | -33 | 2037 | 29% |
| 105 | asia_bo_0-6_to14_x21_tp2 | session_breakout | XAUUSD | H1 | none safe | -7 | -753 | -1383 | -111 | 1889 | 49% |
| 106 | asia_bo_0-6_to14_x21_d1ma50 | session_breakout | XAUUSD | H1 | none safe | -0 | -36 | -985 | -56 | 992 | 44% |
| 107 | asia_bo_0-8_to16_x22_half | session_breakout | XAUUSD | H1 | none safe | -12 | -1296 | -1946 | -59 | 1975 | 44% |
| 108 | gold_tom_k0_h14_hold96_tp2 | turn_of_month | XAUUSD | H1 | 0.50% | 10 | 1087 | -518 | -115 | 107 | 57% |
| 109 | gold_tom_k0_h14_hold96_d1ma50 | turn_of_month | XAUUSD | H1 | 0.50% | 14 | 1491 | -389 | -174 | 57 | 30% |
| 110 | gold_tom_k01_h16_hold96 | turn_of_month | XAUUSD | H1 | 0.50% | 13 | 1375 | -527 | -197 | 145 | 48% |
| 111 | gold_tom_wrapper_default | gold_turn_of_month | XAUUSD | H1 | 0.50% | 26 | 2828 | -461 | -174 | 107 | 52% |
| 112 | idx_tom_wrapper_default | index_turn_of_month | US500 | H1 | 1.25% | 27 | 2969 | -554 | -183 | 89 | 53% |
| 113 | idx_tom_wrapper_default | index_turn_of_month | DE40 | H1 | 1.00% | 19 | 2047 | -520 | -152 | 83 | 47% |
| 114 | idx_tom_wrapper_default | index_turn_of_month | US30 | H1 | 1.00% | 14 | 1548 | -480 | -146 | 88 | 48% |
| 115 | idx_tom_wrapper_default | index_turn_of_month | USTEC | H1 | 2.00% | 19 | 339 | -586 | -206 | 18 | 44% |
| 116 | idx_tom_h22_hold48 | index_turn_of_month | USTEC | H1 | 1.00% | -11 | -193 | -520 | -157 | 18 | 22% |
| 117 | jpy_week_cycle | jpy_week_cycle | EURJPY | H1 | 0.25% | 21 | 2251 | -476 | -52 | 643 | 57% |
| 118 | jpy_week_cycle | jpy_week_cycle | CADJPY | H1 | none safe | 8 | 899 | -1016 | -70 | 658 | 51% |
| 119 | jpy_week_cycle | jpy_week_cycle | CHFJPY | H1 | none safe | -1 | -59 | -942 | -73 | 607 | 42% |
| 120 | jpy_week_cycle | jpy_week_cycle | USDJPY | H1 | none safe | 5 | 594 | -707 | -57 | 654 | 49% |
| 121 | jpy_week_cycle_mon47 | jpy_week_cycle | EURJPY | H1 | 0.25% | 22 | 2384 | -468 | -59 | 643 | 56% |
| 122 | jpy_week_cycle_d1ma100 | jpy_week_cycle | EURJPY | H1 | 0.25% | 19 | 2091 | -527 | -52 | 670 | 57% |
| 123 | monday_long_downweek | monday_long | EURJPY | H1 | 0.25% | 10 | 1098 | -297 | -51 | 240 | 54% |
| 124 | monday_long_downweek | monday_long | CADJPY | H1 | 0.25% | 0 | 51 | -553 | -53 | 224 | 45% |
| 125 | monday_long_downweek | monday_long | NZDJPY | H1 | 0.25% | -0 | -8 | -237 | -29 | 28 | 7% |
| 126 | monday_long_downweek | monday_long | CHFJPY | H1 | 0.25% | 2 | 226 | -380 | -73 | 223 | 40% |
| 127 | monday_long_downweek_n72 | monday_long | AUDJPY | H1 | 0.25% | 17 | 1850 | -412 | -47 | 255 | 56% |
| 128 | monday_long_downweek_n240 | monday_long | AUDJPY | H1 | 0.25% | 9 | 941 | -396 | -65 | 222 | 48% |
| 129 | monday_long_downweek_hold47 | monday_long | AUDJPY | H1 | 0.50% | 37 | 4083 | -557 | -110 | 215 | 55% |
| 130 | monday_long_downweek_hold23 | monday_long | AUDJPY | H1 | 0.25% | 8 | 912 | -312 | -25 | 214 | 54% |
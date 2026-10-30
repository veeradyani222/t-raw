# Strategy search, round 3 results (2026-10-30)

Written for Veer. Plain language. Round 3 was a from-scratch, per-market search (ten market groups,
80 candidates returned) with no loyalty to the 66 strategies running live and no statistical gates
other than the look-ahead check and the 300/800 rule. This document is the PORTFOLIO stage: the full
pool (80 new + 66 live = 146 strategies) was rebuilt into three mixes, one sized on the last 2 years,
one on 3 years and one on 5 years, and all four mixes (the live 66 included) were then tested on every
window and every calendar year.

Rules the mixes had to keep at every hour: combined floating loss on the server day never worse than
-$300 (the firm's limit is -$400), combined equity never below $9,200 from a fresh $10k start. In the
tables below every cell is **net / worst day / lowest equity / stop fires** after replaying the account
with the live close-all stop at -$300 (slip $25). Each window or year starts fresh at $10,000.

## The short version

**Run Mix-5y.** It is the only mix of the four that never breaks the account on any window it was tested on:
5 years $50,873 with worst day -$300, lowest equity $9,323 and zero close-all fires, and it is profitable in every
calendar year including 2022 (+$2,408) and 2023 (+$23), the two years that sink everything else. On the last
2 years it makes $38,283 (about $1,600 a month) against $50,588 for Mix-2y, so it gives up a quarter of the
recent profit to buy survival in bad years. Mix-2y would have lost the account in 2022 (-$12,260) and 2023
(-$16,282); Mix-3y also fails 2022; the current live 66 fails both. One honest caveat for a brand-new account:
a 2023-style year starting from a fresh $10k would still have taken Mix-5y down to $7,807, below the floor, so
no mix here is bust-proof in the worst year; Mix-5y is the one with by far the best odds.

## Cross-evaluation: every mix on every window

Each cell: net profit / worst server day / lowest equity / number of close-all stop fires. Fresh $10k
start at the beginning of each window. Risk is fixed-dollar per trade (not compounding), as live.

| Mix | 2 years (2024-10-20..) | 3 years (2023-10-20..) | 5 years (2021-10-20..) | last 12 months |
|---|---|---|---|---|
| **Current 66 (live)** | $21,667 / -$325 / $9,575 / 42 | $26,967 / -$325 / $6,820 / 76 | $26,014 / -$325 / -$1,169 / 109 | $13,028 / -$325 / $9,776 / 8 |
| **Mix-2y** | $50,588 / -$325 / $9,761 / 13 | $43,077 / -$325 / $7,386 / 56 | $25,474 / -$325 / -$21,095 / 99 | $22,409 / -$325 / $9,990 / 9 |
| **Mix-3y** | $43,967 / -$325 / $9,782 / 11 | $48,539 / -$325 / $9,516 / 22 | $47,459 / -$325 / $325 / 41 | $18,633 / -$325 / $9,990 / 13 |
| **Mix-5y** | $38,283 / -$325 / $9,828 / 9 | $43,429 / -$325 / $9,502 / 15 | $50,873 / -$300 / $9,323 / 0 | $16,831 / -$325 / $9,988 / 7 |

## Calendar years, each a fresh $10k start

| Mix | 2022 | 2023 | 2024 | 2025 | 2026 (to 10-30) |
|---|---|---|---|---|---|
| **Current 66 (live)** | -$2,362 / -$325 / $5,853 / 37 | -$933 / -$325 / $5,312 / 57 | $640 / -$325 / $5,309 / 34 | $19,922 / -$325 / $9,850 / 8 | $7,754 / -$325 / $9,784 / 8 |
| **Mix-2y** | -$12,260 / -$325 / -$2,260 / 35 | -$16,282 / -$325 / -$7,887 / 57 | $4,505 / -$325 / $5,979 / 23 | $24,636 / -$325 / $9,919 / 16 | $15,773 / -$325 / $9,818 / 6 |
| **Mix-3y** | -$5,281 / -$325 / $4,321 / 22 | -$1,177 / -$325 / $4,784 / 23 | $6,442 / -$325 / $8,301 / 21 | $24,190 / -$325 / $9,915 / 7 | $16,299 / -$325 / $9,759 / 2 |
| **Mix-5y** | $2,408 / -$325 / $9,670 / 1 | $23 / -$325 / $7,807 / 16 | $7,177 / -$325 / $9,099 / 13 | $19,615 / -$325 / $9,953 / 5 | $13,045 / -$325 / $9,895 / 5 |

## Mix statistics

| Mix | strategies (new) | window built on | avg/month (own window) | green months | max $ at risk at once | challenges passed / failed (own window) | avg/month 5y | green months 5y | challenges 5y |
|---|---|---|---|---|---|---|---|---|---|
| **Current 66 (live)** | 66 (0) | 2y | $867 | 76% | $1,800 | 35 / 14 | $426 | 59% | 51 / 76 |
| **Mix-2y** | 51 (32) | 2y | $2,024 | 100% | $1,350 | 45 / 3 | $418 | 59% | 46 / 81 |
| **Mix-3y** | 62 (35) | 3y | $1,312 | 86% | $1,250 | 59 / 16 | $778 | 69% | 68 / 59 |
| **Mix-5y** | 57 (31) | 5y | $834 | 82% | $1,200 | 90 / 37 | $834 | 82% | 90 / 37 |

## Where the profit comes from (by market group, 2 years / 5 years)

| Market group | Current 66 (live) 2y / 5y | Mix-2y 2y / 5y | Mix-3y 2y / 5y | Mix-5y 2y / 5y |
|---|---|---|---|---|
| Metals | $13,402 / $13,889 | $12,506 / $6,650 | $8,347 / $6,154 | $5,313 / $6,558 |
| Europe indices | $3,033 / $5,048 | $4,570 / $7,129 | $4,069 / $6,213 | $7,643 / $11,575 |
| Majors | $5,855 / $6,239 | $7,339 / $6,381 | $7,540 / $7,453 | $6,279 / $7,543 |
| US indices | $3,838 / $2,768 | $4,279 / $4,367 | $8,894 / $9,861 | $7,689 / $9,065 |
| JPY crosses | $8,771 / $12,523 | $3,423 / $4,154 | $4,413 / $5,764 | $2,984 / $3,608 |
| Crypto | $0 / $0 | $7,386 / $8,004 | $6,221 / $7,827 | $4,902 / $5,868 |
| Exotic FX | $0 / $0 | $1,106 / $1,106 | $2,700 / $2,700 | $4,757 / $4,757 |
| Oil & gas | $0 / $0 | $8,087 / $2,479 | $2,294 / $648 | $769 / $434 |
| Commodity FX | $1,484 / $697 | $1,635 / $937 | $1,332 / $1,016 | $769 / $441 |
| Asia indices | $0 / $0 | $3,380 / -$12,261 | $3,603 / $2,575 | $1,021 / $1,021 |

## Mix-2y (sized on 2024-10-20..now)

New strategies in: wd_MW_Th_a15 (BTCUSD D1, 1.00%), pw_h4_sfp_trail2 (SOLUSD H4, 0.75%), squeeze_h4_a25_kc2 (ETHUSD H4, 0.25%), pdm_t10_h24 (ETHUSD H1, 0.25%), inside_h4_trail (XRPUSD H4, 0.50%), brent_wti_spread_z (XTIUSD H4, 0.50%), donchian160_h4 (XTIUSD H4, 1.00%), eia_fade_m30 (XTIUSD M30, 0.75%), inside_bar_h4 (XTIUSD H4, 0.50%), gas_rsi14_h4 (XNGUSD H4, 0.25%), rsi2_mr_aus200_h4 (AUS200 H4, 0.75%), rsi2_mr_jpn225_h1 (JPN225 H1, 1.25%), gap_fill_aus200_h1 (AUS200 H1, 0.50%), monday_cash_long_de40 (DE40 M30, 0.25%), first_hour_mult_break_de40 (DE40 M30, 0.25%), prev_week_high_long_de40 (DE40 M30, 0.50%), or_fail_fra40 (FRA40 M30, 1.00%), rsi2_thresh10_sma5 (US500 D1, 1.25%), weekday_fri_to_mon (USTEC D1, 0.75%), overnight_trend (US500 M30, 0.50%), round_big_bounce (USTEC M30, 0.75%), nr_7_mid_r2 (XAGUSD H1, 1.25%), sh_long_21-3_s3.0 (XAUUSD H1, 0.50%), wo_d1.0_t0.2_r2 (XAUUSD H4, 0.25%), ab_mql_range_mid_mr0.3 (XAUUSD M30, 0.50%), up_long_23-9_s3.0_pdup (XPDUSD H1, 0.25%), zmean_n100_adx25 (NZDUSD H4, 0.50%), exo_eurnok_inside_day (EURNOK D1, 0.50%), exo_eurnok_rsi2_h4 (EURNOK H4, 0.50%), monday_gap_fade_gbpusd (GBPUSD H1, 2.50%), inside_day_break_usdchf (USDCHF H4, 1.00%), friday_week_fade_eurusd (EURUSD H1, 2.00%)

Live strategies dropped: tom_k0_h20_hold72_sl3 (DE40 H1), ema_x (US500 D1), htf_bo50_n24 (XAUUSD H1), rsi_rev+trend (CADJPY H4), connors_rsi2_D1_rsi_n3 (US500 D1), rsi_rev+trend (GBPJPY H4), asia0-9_te14_tp1.0 (XAUUSD H1), bb_fade (EURUSD H1), dip_combo (US500 D1), connors_rsi2_D1_ (EURJPY D1), bb_rev+trend (GBPUSD H4), bos_trail3_htfD50_M30 (XAUUSD M30), zscore (US500 H4), crabel_k0.5_None (DE40 M30), inside_far_tp2 (XAUUSD H1), de_orb2.0_trNone_tp2.0_ex18 (DE40 H1), stoch_rev+trend (GBPUSD H4), aroon_x+trend (XAUUSD H1), mfi_rev+trend (EURUSD D1), rsi_rev+trend (GBPJPY D1), kelt_rev+trend (GBPJPY D1), mfi_rev+trend (USDJPY D1), rsi_rev+trend (GBPUSD D1), kelt_rev+trend (GBPUSD D1), mfi_rev (GBPCHF H4), mfi_rev+trend (EURJPY D1), rsi_rev (US30 H1), connors_rsi2_D1_ (CADJPY D1), bb_breakout_M30_dev2.5 (XAUUSD M30), free_robot_H4_patternsoldiers_osccci (USDJPY H4), free_robot_H1_patternsoldiers_oscmfi (XAUUSD H1), mon_long_h0_hold23 (EURJPY H1), day1-14_te20_tp1.5 (DE40 H1), free_robot_H4_patternhammer_oscrsi (USDJPY H4), connors_rsi2_D1_rsi_n3 (GBPUSD D1), inside_tp3 (EURUSD H1), bos_hv_be1_M30 (XAUUSD M30), rsi_rev+trend (EURCHF H4), mfi_rev+trend (USDCHF D1), dmi_x (US30 H1), tsmom50 (DE40 H4), mfi_rev+trend (GBPCHF H4), squeeze_brk (EURUSD D1), nr7_far_tp2 (EURUSD H1), rsi_rev+trend (XAUUSD H1), crabel_k1.0_nr4 (EURUSD H1), macd_zero (USTEC H1)

Live strategies kept at a different risk: bb_breakout_H1_period250_dev2.75 (XAUUSD: 0.50% -> 0.25%), imom_nyclose_h1 (XAUUSD: 0.25% -> 1.00%), rsi_rev (AUDCAD: 0.75% -> 0.50%), connors_rsi2_D1_ (USDCHF: 0.25% -> 1.25%), monday_long_downweek (EURJPY: 0.50% -> 0.75%), persistent_anti_D1_ (USDJPY: 1.25% -> 0.75%), connors_rsi2_D1_ (EURCHF: 1.25% -> 3.00%), prefomc_16to20 (EURUSD: 2.00% -> 3.00%), vwap (DE40: 0.50% -> 0.75%)

Things that look like data artefacts or thin edges:
- pweek_sl1_trail8 DE40 H1 @0.25%: one trade is 65% of its profit ($60)
- tom_short_1_4 USDJPY H1 @0.75%: one trade is 45% of its profit ($193)
- connors_rsi2_D1_ USDCHF D1 @1.25%: only 12 trades in the window
- connors_rsi2_D1_ EURCHF D1 @3.00%: only 12 trades in the window
- prefomc_16to20 EURUSD H1 @3.00%: one trade is 75% of its profit ($150)
- free_robot_H1_patternengulfing_oscrsi XAUUSD H1 @0.25%: one trade is 79% of its profit ($24)
- vwap DE40 H1 @0.75%: one trade is 249% of its profit ($512)
- prefomc_short EURUSD H1 @0.75%: one trade is 246% of its profit ($69)
- free_robot_H1_patternharami_oscmfi XAUUSD H1 @0.25%: one trade is 48% of its profit ($25)
- pw_h4_sfp_trail2 SOLUSD H4 @0.75%: one trade is 51% of its profit ($1744)
- pw_h4_sfp_trail2 SOLUSD H4 @0.75%: max lots 29.00
- squeeze_h4_a25_kc2 ETHUSD H4 @0.25%: one trade is 39% of its profit ($237)
- inside_h4_trail XRPUSD H4 @0.50%: one trade is 81% of its profit ($561)
- inside_h4_trail XRPUSD H4 @0.50%: max lots 2213.36
- donchian160_h4 XTIUSD H4 @1.00%: one trade is 61% of its profit ($1901)
- gas_rsi14_h4 XNGUSD H4 @0.25%: one trade is 38% of its profit ($25)
- gap_fill_aus200_h1 AUS200 H1 @0.50%: max lots 5.40
- monday_cash_long_de40 DE40 M30 @0.25%: one trade is 38% of its profit ($25)
- or_fail_fra40 FRA40 M30 @1.00%: max lots 9.00
- overnight_trend US500 M30 @0.50%: one trade is 43% of its profit ($155)
- up_long_23-9_s3.0_pdup XPDUSD H1 @0.25%: one trade is 89% of its profit ($127)
- exo_eurnok_inside_day EURNOK D1 @0.50%: only 14 trades in the window

| Strategy | Market | TF | Risk | Net (window) | Trades | Biggest trade | Max lots | New? |
|---|---|---|---|---|---|---|---|---|
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 1.00% | $5,950 | 192 | $664 (11%) | 0.14 | live |
| pw_h4_sfp_trail2 | SOLUSD | H4 | 0.75% | $3,435 | 71 | $1,744 (51%) | 29.00 | new |
| donchian160_h4 | XTIUSD | H4 | 1.00% | $3,128 | 22 | $1,901 (61%) | 0.99 | new |
| nr_7_mid_r2 | XAGUSD | H1 | 1.25% | $2,695 | 55 | $231 (9%) | 0.11 | new |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.50% | $2,577 | 26 | $396 (15%) | 3.33 | new |
| wd_MW_Th_a15 | BTCUSD | D1 | 1.00% | $2,101 | 318 | $226 (11%) | 0.05 | new |
| rsi2_mr_jpn225_h1 | JPN225 | H1 | 1.25% | $2,061 | 81 | $380 (18%) | 1.00 | new |
| eia_fade_m30 | XTIUSD | M30 | 0.75% | $1,944 | 77 | $522 (27%) | 3.64 | new |
| ab_mql_range_mid_mr0.3 | XAUUSD | M30 | 0.50% | $1,896 | 356 | $86 (5%) | 0.10 | new |
| friday_week_fade_eurusd | EURUSD | H1 | 2.00% | $1,776 | 18 | $617 (35%) | 0.67 | new |
| brent_wti_spread_z | XTIUSD | H4 | 0.50% | $1,657 | 39 | $501 (30%) | 0.60 | new |
| rsi2_thresh10_sma5 | US500 | D1 | 1.25% | $1,554 | 25 | $326 (21%) | 1.90 | new |
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | $1,449 | 46 | $412 (28%) | 4.70 | new |
| round_big_bounce | USTEC | M30 | 0.75% | $1,418 | 105 | $246 (17%) | 0.80 | new |
| inside_day_break_usdchf | USDCHF | H4 | 1.00% | $1,281 | 57 | $195 (15%) | 1.64 | new |
| inside_bar_h4 | XTIUSD | H4 | 0.50% | $1,266 | 122 | $132 (10%) | 0.80 | new |
| monday_long_downweek | EURJPY | H1 | 0.75% | $1,230 | 43 | $330 (27%) | 0.36 | live |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.75% | $1,156 | 191 | $105 (9%) | 2.70 | new |
| connors_rsi2_D1_ | EURCHF | D1 | 3.00% | $1,036 | 12 | $249 (24%) | 0.29 | live |
| rsi_rev | AUDCAD | H4 | 0.50% | $981 | 49 | $71 (7%) | 0.17 | live |
| first_hour_mult_break_de40 | DE40 | M30 | 0.25% | $973 | 317 | $260 (27%) | 2.20 | new |
| sh_long_21-3_s3.0 | XAUUSD | H1 | 0.50% | $743 | 305 | $74 (10%) | 0.03 | new |
| rsi_rev+trend | CADJPY | H1 | 0.75% | $736 | 40 | $97 (13%) | 0.51 | live |
| weekday_fri_to_mon | USTEC | D1 | 0.75% | $727 | 52 | $129 (18%) | 0.30 | new |
| inside_h4_trail | XRPUSD | H4 | 0.50% | $693 | 48 | $561 (81%) | 2213.36 | new |
| zmean_n100_adx25 | NZDUSD | H4 | 0.50% | $654 | 23 | $153 (23%) | 0.13 | new |
| exo_eurnok_rsi2_h4 | EURNOK | H4 | 0.50% | $628 | 57 | $65 (10%) | 0.09 | new |
| or_fail_fra40 | FRA40 | M30 | 1.00% | $612 | 30 | $128 (21%) | 9.00 | new |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 0.25% | $607 | 45 | $237 (39%) | 0.35 | new |
| pdm_t10_h24 | ETHUSD | H1 | 0.25% | $550 | 93 | $128 (23%) | 0.66 | new |
| exo_eurnok_inside_day | EURNOK | D1 | 0.50% | $478 | 14 | $63 (13%) | 0.06 | new |
| connors_rsi2_D1_ | USDCHF | D1 | 1.25% | $463 | 12 | $101 (22%) | 0.10 | live |
| imom_nyclose_h1 | XAUUSD | H1 | 1.00% | $447 | 491 | $123 (28%) | 0.06 | live |
| tom_short_1_4 | USDJPY | H1 | 0.75% | $426 | 23 | $193 (45%) | 0.09 | live |
| overnight_trend | US500 | M30 | 0.50% | $361 | 295 | $155 (43%) | 1.40 | new |
| persistent_anti_D1_ | USDJPY | D1 | 0.75% | $360 | 98 | $68 (19%) | 0.09 | live |
| kelt_rev+trend | GBPJPY | H4 | 0.50% | $359 | 21 | $69 (19%) | 0.08 | live |
| aroon_x+trend | AUDJPY | H4 | 0.25% | $339 | 58 | $34 (10%) | 0.07 | live |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 0.25% | $231 | 22 | $59 (26%) | 0.02 | live |
| rsi_rev+trend | US30 | H1 | 0.50% | $224 | 42 | $73 (33%) | 1.30 | live |
| wo_d1.0_t0.2_r2 | XAUUSD | H4 | 0.25% | $209 | 17 | $45 (21%) | 0.02 | new |
| vwap | DE40 | H1 | 0.75% | $206 | 28 | $512 (249%) | 4.00 | live |
| prefomc_16to20 | EURUSD | H1 | 3.00% | $200 | 16 | $150 (75%) | 0.42 | live |
| gap_fill_aus200_h1 | AUS200 | H1 | 0.50% | $163 | 114 | $50 (30%) | 5.40 | new |
| up_long_23-9_s3.0_pdup | XPDUSD | H1 | 0.25% | $143 | 168 | $127 (89%) | 3.90 | new |
| pweek_sl1_trail8 | DE40 | H1 | 0.25% | $92 | 18 | $60 (65%) | 0.10 | live |
| monday_cash_long_de40 | DE40 | M30 | 0.25% | $66 | 25 | $25 (38%) | 0.20 | new |
| gas_rsi14_h4 | XNGUSD | H4 | 0.25% | $65 | 27 | $25 (38%) | 0.02 | new |
| free_robot_H1_patternharami_oscmfi | XAUUSD | H1 | 0.25% | $52 | 63 | $25 (48%) | 0.03 | live |
| free_robot_H1_patternengulfing_oscrsi | XAUUSD | H1 | 0.25% | $30 | 26 | $24 (79%) | 0.02 | live |
| prefomc_short | EURUSD | H1 | 0.75% | $28 | 16 | $69 (246%) | 0.10 | live |

## Mix-3y (sized on 2023-10-20..now)

New strategies in: wd_MW_Th_a15 (BTCUSD D1, 1.25%), pw_h4_sfp_trail2 (SOLUSD H4, 0.25%), squeeze_h4_a25_kc2 (ETHUSD H4, 0.25%), spike_follow (BTCUSD H1, 0.50%), inside_h4_trail (XRPUSD H4, 0.25%), donchian160_h4 (XTIUSD H4, 0.50%), eia_fade_m30 (XTIUSD M30, 0.25%), gas_rsi14_h4 (XNGUSD H4, 0.25%), daily_mr_china50_d1 (CHINA50 D1, 1.25%), rsi2_mr_aus200_h4 (AUS200 H4, 0.50%), gap_go_jpn225_m30 (JPN225 M30, 1.25%), rsi2_mr_china50_d1 (CHINA50 D1, 0.25%), daily_mr_aus200_d1 (AUS200 D1, 0.25%), gap_fill_aus200_h1 (AUS200 H1, 1.25%), first_hour_mult_break_de40 (DE40 M30, 0.25%), prev_week_high_long_de40 (DE40 M30, 0.50%), or_fail_fra40 (FRA40 M30, 0.75%), ibs_lo0.2_hi0.8 (US30 D1, 1.00%), rsi2_thresh10_sma5 (US500 D1, 1.50%), weekday_fri_to_mon (USTEC D1, 1.50%), prev_week_break_long (USTEC H1, 1.00%), round_big_bounce (USTEC M30, 1.25%), nr_7_mid_r2 (XAGUSD H1, 1.25%), sh_long_21-3_s3.0 (XAUUSD H1, 0.50%), rz_XAGUSD_n200_z2.5 (XAUUSD H1, 0.25%), band_fade_h4_trend (CHFJPY H4, 0.25%), zmean_n100_adx25 (NZDUSD H4, 1.00%), exo_eurnok_pwhl_break (EURNOK D1, 0.50%), exo_eurnok_inside_day (EURNOK D1, 1.25%), exo_eurnok_rsi2_h4 (EURNOK H4, 0.50%), exo_usdcnh_3bar_pullback (USDCNH D1, 0.25%), monday_gap_fade_gbpusd (GBPUSD H1, 2.00%), inside_day_break_usdchf (USDCHF H4, 0.75%), friday_week_fade_eurusd (EURUSD H1, 1.50%), friday_week_fade_usdchf (USDCHF H1, 0.50%)

Live strategies dropped: tom_k0_h20_hold72_sl3 (DE40 H1), ema_x (US500 D1), pweek_sl1_trail8 (DE40 H1), imom_nyclose_h1 (XAUUSD H1), rsi_rev (AUDCAD H4), rsi_rev+trend (CADJPY H4), connors_rsi2_D1_rsi_n3 (US500 D1), asia0-9_te14_tp1.0 (XAUUSD H1), connors_rsi2_D1_ (EURJPY D1), zscore (US500 H4), crabel_k0.5_None (DE40 M30), de_orb2.0_trNone_tp2.0_ex18 (DE40 H1), stoch_rev+trend (GBPUSD H4), mfi_rev+trend (EURUSD D1), rsi_rev+trend (GBPJPY D1), kelt_rev+trend (GBPJPY D1), mfi_rev+trend (USDJPY D1), rsi_rev+trend (GBPUSD D1), kelt_rev+trend (GBPUSD D1), mfi_rev (GBPCHF H4), mfi_rev+trend (EURJPY D1), rsi_rev (US30 H1), bb_breakout_M30_dev2.5 (XAUUSD M30), free_robot_H4_patternsoldiers_osccci (USDJPY H4), free_robot_H1_patternsoldiers_oscmfi (XAUUSD H1), mon_long_h0_hold23 (EURJPY H1), day1-14_te20_tp1.5 (DE40 H1), connors_rsi2_D1_rsi_n3 (GBPUSD D1), bos_hv_be1_M30 (XAUUSD M30), rsi_rev+trend (EURCHF H4), mfi_rev+trend (USDCHF D1), dmi_x (US30 H1), tsmom50 (DE40 H4), prefomc_short (EURUSD H1), mfi_rev+trend (GBPCHF H4), squeeze_brk (EURUSD D1), rsi_rev+trend (XAUUSD H1), crabel_k1.0_nr4 (EURUSD H1), macd_zero (USTEC H1)

Live strategies kept at a different risk: bos_trail3_htfD50_H1 (XAUUSD: 1.00% -> 0.25%), bb_breakout_H1_period250_dev2.75 (XAUUSD: 0.50% -> 0.75%), htf_bo50_n24 (XAUUSD: 0.50% -> 0.25%), tom_short_1_4 (USDJPY: 0.75% -> 1.25%), connors_rsi2_D1_ (USDCHF: 0.25% -> 1.50%), bb_fade (EURUSD: 1.25% -> 0.75%), monday_long_downweek (EURJPY: 0.50% -> 0.75%), dip_combo (US500: 0.25% -> 0.50%), connors_rsi2_D1_ (EURCHF: 1.25% -> 1.50%), rsi_rev+trend (CADJPY: 0.75% -> 0.25%), aroon_x+trend (XAUUSD: 0.50% -> 0.25%), kelt_rev+trend (GBPJPY: 0.50% -> 0.25%), connors_rsi2_D1_ (CADJPY: 3.00% -> 2.50%), free_robot_H4_patternhammer_oscrsi (USDJPY: 0.25% -> 1.00%), prefomc_16to20 (EURUSD: 2.00% -> 3.00%), free_robot_H1_patternengulfing_oscrsi (XAUUSD: 0.25% -> 0.75%), vwap (DE40: 0.50% -> 0.25%)

Things that look like data artefacts or thin edges:
- tom_short_1_4 USDJPY H1 @1.25%: one trade is 54% of its profit ($330)
- rsi_rev+trend GBPJPY H4 @1.00%: only 14 trades in the window
- connors_rsi2_D1_ EURCHF D1 @1.50%: one trade is 65% of its profit ($152)
- connors_rsi2_D1_ CADJPY D1 @2.50%: only 12 trades in the window
- prefomc_16to20 EURUSD H1 @3.00%: one trade is 143% of its profit ($150)
- inside_tp3 EURUSD H1 @0.25%: one trade is 36% of its profit ($67)
- nr7_far_tp2 EURUSD H1 @0.25%: one trade is 84% of its profit ($47)
- free_robot_H1_patternharami_oscmfi XAUUSD H1 @0.25%: one trade is 133% of its profit ($25)
- pw_h4_sfp_trail2 SOLUSD H4 @0.25%: one trade is 50% of its profit ($531)
- pw_h4_sfp_trail2 SOLUSD H4 @0.25%: max lots 9.00
- squeeze_h4_a25_kc2 ETHUSD H4 @0.25%: one trade is 36% of its profit ($237)
- inside_h4_trail XRPUSD H4 @0.25%: one trade is 81% of its profit ($281)
- inside_h4_trail XRPUSD H4 @0.25%: max lots 1106.68
- donchian160_h4 XTIUSD H4 @0.50%: one trade is 70% of its profit ($951)
- rsi2_mr_china50_d1 CHINA50 D1 @0.25%: only 0 trades in the window
- gap_fill_aus200_h1 AUS200 H1 @1.25%: max lots 13.60
- prev_week_high_long_de40 DE40 M30 @0.50%: max lots 8.30
- or_fail_fra40 FRA40 M30 @0.75%: one trade is 89% of its profit ($109)
- or_fail_fra40 FRA40 M30 @0.75%: max lots 9.00
- rz_XAGUSD_n200_z2.5 XAUUSD H1 @0.25%: one trade is 40% of its profit ($73)
- band_fade_h4_trend CHFJPY H4 @0.25%: one trade is 50% of its profit ($50)
- exo_eurnok_inside_day EURNOK D1 @1.25%: only 14 trades in the window
- friday_week_fade_eurusd EURUSD H1 @1.50%: one trade is 47% of its profit ($463)
- friday_week_fade_usdchf USDCHF H1 @0.50%: one trade is 41% of its profit ($147)

| Strategy | Market | TF | Risk | Net (window) | Trades | Biggest trade | Max lots | New? |
|---|---|---|---|---|---|---|---|---|
| wd_MW_Th_a15 | BTCUSD | D1 | 1.25% | $3,938 | 474 | $271 (7%) | 0.09 | new |
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | $3,568 | 77 | $829 (23%) | 8.30 | new |
| spike_follow | BTCUSD | H1 | 0.50% | $2,547 | 324 | $96 (4%) | 0.27 | new |
| round_big_bounce | USTEC | M30 | 1.25% | $2,495 | 145 | $430 (17%) | 1.60 | new |
| first_hour_mult_break_de40 | DE40 | M30 | 0.25% | $2,350 | 530 | $570 (24%) | 2.30 | new |
| rsi2_thresh10_sma5 | US500 | D1 | 1.50% | $2,332 | 34 | $395 (17%) | 2.30 | new |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.00% | $2,145 | 31 | $320 (15%) | 2.66 | new |
| nr_7_mid_r2 | XAGUSD | H1 | 1.25% | $2,065 | 85 | $231 (11%) | 0.16 | new |
| monday_long_downweek | EURJPY | H1 | 0.75% | $2,040 | 65 | $372 (18%) | 0.36 | live |
| weekday_fri_to_mon | USTEC | D1 | 1.50% | $2,010 | 103 | $258 (13%) | 0.60 | new |
| prev_week_break_long | USTEC | H1 | 1.00% | $1,637 | 73 | $448 (27%) | 0.70 | new |
| ibs_lo0.2_hi0.8 | US30 | D1 | 1.00% | $1,514 | 76 | $214 (14%) | 0.30 | new |
| inside_day_break_usdchf | USDCHF | H4 | 0.75% | $1,375 | 83 | $140 (10%) | 1.23 | new |
| donchian160_h4 | XTIUSD | H4 | 0.50% | $1,365 | 39 | $951 (70%) | 0.49 | new |
| exo_eurnok_inside_day | EURNOK | D1 | 1.25% | $1,291 | 14 | $160 (12%) | 0.16 | new |
| gap_go_jpn225_m30 | JPN225 | M30 | 1.25% | $1,249 | 28 | $410 (33%) | 2.00 | new |
| connors_rsi2_D1_ | CADJPY | D1 | 2.50% | $1,150 | 12 | $221 (19%) | 0.34 | live |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 0.25% | $1,073 | 196 | $180 (17%) | 0.05 | live |
| pw_h4_sfp_trail2 | SOLUSD | H4 | 0.25% | $1,065 | 70 | $531 (50%) | 9.00 | new |
| sh_long_21-3_s3.0 | XAUUSD | H1 | 0.50% | $1,053 | 562 | $74 (7%) | 0.05 | new |
| zmean_n100_adx25 | NZDUSD | H4 | 1.00% | $1,035 | 38 | $307 (30%) | 0.29 | new |
| daily_mr_china50_d1 | CHINA50 | D1 | 1.25% | $1,017 | 40 | $187 (18%) | 0.40 | new |
| friday_week_fade_eurusd | EURUSD | H1 | 1.50% | $978 | 23 | $463 (47%) | 0.50 | new |
| persistent_anti_D1_ | USDJPY | D1 | 1.25% | $878 | 151 | $202 (23%) | 0.15 | live |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 0.75% | $844 | 67 | $178 (21%) | 0.11 | live |
| bb_rev+trend | GBPUSD | H4 | 0.50% | $803 | 77 | $70 (9%) | 0.11 | live |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.50% | $768 | 191 | $67 (9%) | 1.80 | new |
| bb_fade | EURUSD | H1 | 0.75% | $732 | 24 | $141 (19%) | 0.43 | live |
| htf_bo50_n24 | XAUUSD | H1 | 0.25% | $698 | 190 | $109 (16%) | 0.04 | live |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 0.25% | $666 | 68 | $237 (36%) | 0.39 | new |
| eia_fade_m30 | XTIUSD | M30 | 0.25% | $634 | 124 | $174 (27%) | 1.21 | new |
| exo_eurnok_rsi2_h4 | EURNOK | H4 | 0.50% | $628 | 57 | $65 (10%) | 0.09 | new |
| tom_short_1_4 | USDJPY | H1 | 1.25% | $613 | 35 | $330 (54%) | 0.16 | live |
| bos_trail3_htfD50_M30 | XAUUSD | M30 | 0.25% | $594 | 460 | $158 (27%) | 0.08 | live |
| connors_rsi2_D1_ | USDCHF | D1 | 1.50% | $588 | 18 | $142 (24%) | 0.12 | live |
| aroon_x+trend | XAUUSD | H1 | 0.25% | $578 | 198 | $36 (6%) | 0.04 | live |
| inside_far_tp2 | XAUUSD | H1 | 0.50% | $536 | 55 | $94 (18%) | 0.04 | live |
| rsi_rev+trend | US30 | H1 | 0.50% | $513 | 70 | $73 (14%) | 1.30 | live |
| rsi_rev+trend | GBPJPY | H4 | 1.00% | $503 | 14 | $140 (28%) | 0.21 | live |
| exo_eurnok_pwhl_break | EURNOK | D1 | 0.50% | $491 | 17 | $91 (18%) | 0.04 | new |
| dip_combo | US500 | D1 | 0.50% | $474 | 41 | $58 (12%) | 0.40 | live |
| gap_fill_aus200_h1 | AUS200 | H1 | 1.25% | $426 | 114 | $125 (29%) | 13.60 | new |
| friday_week_fade_usdchf | USDCHF | H1 | 0.50% | $357 | 29 | $147 (41%) | 0.14 | new |
| inside_h4_trail | XRPUSD | H4 | 0.25% | $347 | 48 | $281 (81%) | 1106.68 | new |
| free_robot_H4_patternhammer_oscrsi | USDJPY | H4 | 1.00% | $297 | 16 | $100 (34%) | 0.60 | live |
| exo_usdcnh_3bar_pullback | USDCNH | D1 | 0.25% | $290 | 21 | $46 (16%) | 0.10 | new |
| aroon_x+trend | AUDJPY | H4 | 0.25% | $258 | 85 | $34 (13%) | 0.07 | live |
| free_robot_H1_patternengulfing_oscrsi | XAUUSD | H1 | 0.75% | $248 | 54 | $75 (30%) | 0.11 | live |
| connors_rsi2_D1_ | EURCHF | D1 | 1.50% | $234 | 21 | $152 (65%) | 0.14 | live |
| rsi_rev+trend | CADJPY | H1 | 0.25% | $216 | 59 | $32 (15%) | 0.17 | live |
| inside_tp3 | EURUSD | H1 | 0.25% | $186 | 91 | $67 (36%) | 0.23 | live |
| rz_XAGUSD_n200_z2.5 | XAUUSD | H1 | 0.25% | $185 | 69 | $73 (40%) | 0.03 | new |
| kelt_rev+trend | GBPJPY | H4 | 0.25% | $141 | 37 | $35 (25%) | 0.04 | live |
| or_fail_fra40 | FRA40 | M30 | 0.75% | $123 | 47 | $109 (89%) | 9.00 | new |
| daily_mr_aus200_d1 | AUS200 | D1 | 0.25% | $107 | 78 | $32 (30%) | 0.10 | new |
| prefomc_16to20 | EURUSD | H1 | 3.00% | $104 | 24 | $150 (143%) | 0.44 | live |
| band_fade_h4_trend | CHFJPY | H4 | 0.25% | $99 | 28 | $50 (50%) | 0.07 | new |
| nr7_far_tp2 | EURUSD | H1 | 0.25% | $57 | 94 | $47 (84%) | 0.23 | live |
| free_robot_H1_patternharami_oscmfi | XAUUSD | H1 | 0.25% | $19 | 117 | $25 (133%) | 0.04 | live |
| rsi2_mr_china50_d1 | CHINA50 | D1 | 0.25% | $0 | 0 | $0 (0%) | 0.00 | new |
| vwap | DE40 | H1 | 0.25% | -$14 | 34 | $160 (1111%) | 1.30 | live |
| gas_rsi14_h4 | XNGUSD | H4 | 0.25% | -$99 | 53 | $29 (29%) | 0.02 | new |

## Mix-5y (sized on 2021-10-20..now)

New strategies in: wd_MW_Th_a15 (BTCUSD D1, 0.50%), pw_h4_sfp_trail2 (SOLUSD H4, 0.25%), squeeze_h4_a25_kc2 (ETHUSD H4, 0.50%), pdm_t10_h24 (ETHUSD H1, 0.25%), spike_follow (BTCUSD H1, 0.25%), inside_h4_trail (XRPUSD H4, 0.50%), donchian160_h4 (XTIUSD H4, 0.25%), daily_mr_china50_d1 (CHINA50 D1, 0.25%), rsi2_mr_aus200_h4 (AUS200 H4, 0.50%), rsi2_mr_china50_d1 (CHINA50 D1, 0.25%), gap_fill_aus200_h1 (AUS200 H1, 0.75%), monday_cash_long_de40 (DE40 M30, 1.25%), first_hour_mult_break_de40 (DE40 M30, 0.50%), prev_week_high_long_de40 (DE40 M30, 0.50%), or_fail_fra40 (FRA40 M30, 0.75%), ibs_lo0.2_hi0.8 (US30 D1, 0.50%), rsi2_thresh10_sma5 (US500 D1, 1.50%), weekday_fri_to_mon (USTEC D1, 1.50%), turtle_soup_n20_long (US30 D1, 0.75%), prev_week_break_long (USTEC H1, 0.50%), round_big_bounce (USTEC M30, 0.75%), sh_long_21-3_s3.0 (XAUUSD H1, 0.75%), rz_XAGUSD_n200_z2.5 (XAUUSD H1, 0.50%), zmean_n100_adx25 (NZDUSD H4, 0.25%), exo_eurnok_inside_day (EURNOK D1, 2.00%), exo_eurnok_rsi2_h4 (EURNOK H4, 0.75%), exo_usdcnh_3bar_pullback (USDCNH D1, 1.25%), exo_usdmxn_ema_pullback (USDMXN D1, 0.25%), monday_gap_fade_gbpusd (GBPUSD H1, 2.00%), friday_week_fade_eurusd (EURUSD H1, 1.50%), friday_week_fade_usdchf (USDCHF H1, 0.25%)

Live strategies dropped: tom_k0_h20_hold72_sl3 (DE40 H1), ema_x (US500 D1), imom_nyclose_h1 (XAUUSD H1), rsi_rev+trend (CADJPY H4), connors_rsi2_D1_rsi_n3 (US500 D1), asia0-9_te14_tp1.0 (XAUUSD H1), connors_rsi2_D1_ (EURJPY D1), bos_trail3_htfD50_M30 (XAUUSD M30), crabel_k0.5_None (DE40 M30), de_orb2.0_trNone_tp2.0_ex18 (DE40 H1), aroon_x+trend (XAUUSD H1), mfi_rev+trend (EURUSD D1), rsi_rev+trend (GBPJPY D1), kelt_rev+trend (GBPJPY D1), mfi_rev+trend (USDJPY D1), rsi_rev+trend (GBPUSD D1), kelt_rev+trend (GBPUSD D1), mfi_rev (GBPCHF H4), mfi_rev+trend (EURJPY D1), rsi_rev (US30 H1), bb_breakout_M30_dev2.5 (XAUUSD M30), free_robot_H4_patternsoldiers_osccci (USDJPY H4), free_robot_H1_patternsoldiers_oscmfi (XAUUSD H1), mon_long_h0_hold23 (EURJPY H1), day1-14_te20_tp1.5 (DE40 H1), free_robot_H4_patternhammer_oscrsi (USDJPY H4), prefomc_16to20 (EURUSD H1), connors_rsi2_D1_rsi_n3 (GBPUSD D1), inside_tp3 (EURUSD H1), bos_hv_be1_M30 (XAUUSD M30), rsi_rev+trend (EURCHF H4), mfi_rev+trend (USDCHF D1), dmi_x (US30 H1), tsmom50 (DE40 H4), prefomc_short (EURUSD H1), mfi_rev+trend (GBPCHF H4), squeeze_brk (EURUSD D1), nr7_far_tp2 (EURUSD H1), crabel_k1.0_nr4 (EURUSD H1), rsi_rev+trend (US30 H1)

Live strategies kept at a different risk: bos_trail3_htfD50_H1 (XAUUSD: 1.00% -> 0.25%), bb_breakout_H1_period250_dev2.75 (XAUUSD: 0.50% -> 0.25%), htf_bo50_n24 (XAUUSD: 0.50% -> 0.25%), tom_short_1_4 (USDJPY: 0.75% -> 0.25%), rsi_rev (AUDCAD: 0.75% -> 0.25%), rsi_rev+trend (GBPJPY: 1.00% -> 0.25%), connors_rsi2_D1_ (USDCHF: 0.25% -> 1.00%), bb_fade (EURUSD: 1.25% -> 1.00%), dip_combo (US500: 0.25% -> 0.75%), bb_rev+trend (GBPUSD: 0.50% -> 0.25%), aroon_x+trend (AUDJPY: 0.25% -> 0.50%), zscore (US500: 0.25% -> 0.50%), connors_rsi2_D1_ (EURCHF: 1.25% -> 0.75%), rsi_rev+trend (CADJPY: 0.75% -> 0.50%), inside_far_tp2 (XAUUSD: 0.50% -> 0.75%), kelt_rev+trend (GBPJPY: 0.50% -> 0.25%), connors_rsi2_D1_ (CADJPY: 3.00% -> 0.50%), free_robot_H1_patternengulfing_oscrsi (XAUUSD: 0.25% -> 0.50%), vwap (DE40: 0.50% -> 0.75%), rsi_rev+trend (XAUUSD: 0.50% -> 0.25%)

Things that look like data artefacts or thin edges:
- pweek_sl1_trail8 DE40 H1 @0.25%: one trade is 39% of its profit ($60)
- htf_bo50_n24 XAUUSD H1 @0.25%: one trade is 39% of its profit ($164)
- tom_short_1_4 USDJPY H1 @0.25%: one trade is 162% of its profit ($66)
- connors_rsi2_D1_ EURCHF D1 @0.75%: one trade is 51% of its profit ($76)
- kelt_rev+trend GBPJPY H4 @0.25%: one trade is 60% of its profit ($35)
- vwap DE40 H1 @0.75%: one trade is 75% of its profit ($512)
- pw_h4_sfp_trail2 SOLUSD H4 @0.25%: one trade is 50% of its profit ($531)
- pw_h4_sfp_trail2 SOLUSD H4 @0.25%: max lots 9.00
- squeeze_h4_a25_kc2 ETHUSD H4 @0.50%: one trade is 36% of its profit ($474)
- inside_h4_trail XRPUSD H4 @0.50%: one trade is 81% of its profit ($561)
- inside_h4_trail XRPUSD H4 @0.50%: max lots 2213.36
- donchian160_h4 XTIUSD H4 @0.25%: one trade is 110% of its profit ($475)
- daily_mr_china50_d1 CHINA50 D1 @0.25%: only 0 trades in the window
- rsi2_mr_china50_d1 CHINA50 D1 @0.25%: only 0 trades in the window
- gap_fill_aus200_h1 AUS200 H1 @0.75%: max lots 8.10
- prev_week_high_long_de40 DE40 M30 @0.50%: max lots 8.30
- or_fail_fra40 FRA40 M30 @0.75%: one trade is 269% of its profit ($109)
- or_fail_fra40 FRA40 M30 @0.75%: max lots 9.00
- ibs_lo0.2_hi0.8 US30 D1 @0.50%: one trade is 167% of its profit ($58)
- turtle_soup_n20_long US30 D1 @0.75%: one trade is 127% of its profit ($300)
- prev_week_break_long USTEC H1 @0.50%: one trade is 54% of its profit ($224)
- exo_eurnok_inside_day EURNOK D1 @2.00%: only 14 trades in the window
- exo_usdmxn_ema_pullback USDMXN D1 @0.25%: one trade is 36% of its profit ($73)
- exo_usdmxn_ema_pullback USDMXN D1 @0.25%: only 10 trades in the window
- friday_week_fade_eurusd EURUSD H1 @1.50%: one trade is 37% of its profit ($463)
- friday_week_fade_usdchf USDCHF H1 @0.25%: one trade is 43% of its profit ($74)

| Strategy | Market | TF | Risk | Net (window) | Trades | Biggest trade | Max lots | New? |
|---|---|---|---|---|---|---|---|---|
| first_hour_mult_break_de40 | DE40 | M30 | 0.50% | $5,695 | 999 | $1,140 (20%) | 4.60 | new |
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | $3,373 | 130 | $829 (25%) | 8.30 | new |
| rz_XAGUSD_n200_z2.5 | XAUUSD | H1 | 0.50% | $2,192 | 181 | $143 (7%) | 0.10 | new |
| rsi2_thresh10_sma5 | US500 | D1 | 1.50% | $2,121 | 49 | $395 (19%) | 2.30 | new |
| exo_eurnok_inside_day | EURNOK | D1 | 2.00% | $2,092 | 14 | $259 (12%) | 0.27 | new |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.00% | $2,078 | 48 | $320 (15%) | 2.66 | new |
| weekday_fri_to_mon | USTEC | D1 | 1.50% | $2,053 | 142 | $258 (13%) | 0.60 | new |
| bb_fade | EURUSD | H1 | 1.00% | $1,895 | 37 | $386 (20%) | 0.58 | live |
| sh_long_21-3_s3.0 | XAUUSD | H1 | 0.75% | $1,747 | 1226 | $124 (7%) | 0.11 | new |
| monday_long_downweek | EURJPY | H1 | 0.50% | $1,746 | 115 | $243 (14%) | 0.24 | live |
| monday_cash_long_de40 | DE40 | M30 | 1.25% | $1,633 | 231 | $244 (15%) | 1.30 | new |
| exo_usdcnh_3bar_pullback | USDCNH | D1 | 1.25% | $1,530 | 21 | $239 (16%) | 0.54 | new |
| round_big_bounce | USTEC | M30 | 0.75% | $1,374 | 201 | $246 (18%) | 0.90 | new |
| stoch_rev+trend | GBPUSD | H4 | 0.50% | $1,365 | 153 | $71 (5%) | 0.11 | live |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 0.50% | $1,324 | 119 | $474 (36%) | 1.57 | new |
| inside_far_tp2 | XAUUSD | H1 | 0.75% | $1,260 | 127 | $139 (11%) | 0.09 | live |
| friday_week_fade_eurusd | EURUSD | H1 | 1.50% | $1,246 | 39 | $463 (37%) | 0.50 | new |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 0.25% | $1,098 | 423 | $180 (16%) | 0.07 | live |
| pw_h4_sfp_trail2 | SOLUSD | H4 | 0.25% | $1,065 | 70 | $531 (50%) | 9.00 | new |
| spike_follow | BTCUSD | H1 | 0.25% | $1,063 | 612 | $48 (5%) | 0.19 | new |
| zscore | US500 | H4 | 0.50% | $1,055 | 175 | $108 (10%) | 2.40 | live |
| macd_zero | USTEC | H1 | 0.25% | $1,000 | 703 | $195 (19%) | 2.30 | live |
| wd_MW_Th_a15 | BTCUSD | D1 | 0.50% | $966 | 658 | $90 (9%) | 0.11 | new |
| exo_eurnok_rsi2_h4 | EURNOK | H4 | 0.75% | $934 | 57 | $94 (10%) | 0.13 | new |
| dip_combo | US500 | D1 | 0.75% | $772 | 58 | $93 (12%) | 0.70 | live |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.50% | $768 | 191 | $67 (9%) | 1.80 | new |
| pdm_t10_h24 | ETHUSD | H1 | 0.25% | $757 | 226 | $128 (17%) | 1.40 | new |
| inside_h4_trail | XRPUSD | H4 | 0.50% | $693 | 48 | $561 (81%) | 2213.36 | new |
| vwap | DE40 | H1 | 0.75% | $679 | 69 | $512 (75%) | 4.00 | live |
| persistent_anti_D1_ | USDJPY | D1 | 1.25% | $615 | 271 | $202 (33%) | 0.15 | live |
| aroon_x+trend | AUDJPY | H4 | 0.50% | $468 | 151 | $70 (15%) | 0.15 | live |
| donchian160_h4 | XTIUSD | H4 | 0.25% | $434 | 74 | $475 (110%) | 0.24 | new |
| prev_week_break_long | USTEC | H1 | 0.50% | $419 | 86 | $224 (54%) | 0.30 | new |
| htf_bo50_n24 | XAUUSD | H1 | 0.25% | $418 | 399 | $164 (39%) | 0.05 | live |
| connors_rsi2_D1_ | USDCHF | D1 | 1.00% | $320 | 31 | $95 (30%) | 0.08 | live |
| bb_rev+trend | GBPUSD | H4 | 0.25% | $320 | 128 | $34 (11%) | 0.05 | live |
| rsi_rev+trend | CADJPY | H1 | 0.50% | $298 | 102 | $65 (22%) | 0.34 | live |
| gap_fill_aus200_h1 | AUS200 | H1 | 0.75% | $253 | 114 | $75 (29%) | 8.10 | new |
| connors_rsi2_D1_ | CADJPY | D1 | 0.50% | $248 | 29 | $54 (22%) | 0.06 | live |
| turtle_soup_n20_long | US30 | D1 | 0.75% | $236 | 38 | $300 (127%) | 0.20 | new |
| zmean_n100_adx25 | NZDUSD | H4 | 0.25% | $235 | 76 | $70 (30%) | 0.07 | new |
| rsi_rev | AUDCAD | H4 | 0.25% | $206 | 123 | $35 (17%) | 0.09 | live |
| exo_usdmxn_ema_pullback | USDMXN | D1 | 0.25% | $201 | 10 | $73 (36%) | 0.03 | new |
| friday_week_fade_usdchf | USDCHF | H1 | 0.25% | $171 | 49 | $74 (43%) | 0.07 | new |
| pweek_sl1_trail8 | DE40 | H1 | 0.25% | $154 | 107 | $60 (39%) | 0.10 | live |
| connors_rsi2_D1_ | EURCHF | D1 | 0.75% | $148 | 34 | $76 (51%) | 0.07 | live |
| rsi_rev+trend | GBPJPY | H4 | 0.25% | $134 | 28 | $35 (26%) | 0.05 | live |
| rsi_rev+trend | XAUUSD | H1 | 0.25% | $106 | 64 | $35 (33%) | 0.04 | live |
| kelt_rev+trend | GBPJPY | H4 | 0.25% | $58 | 66 | $35 (60%) | 0.04 | live |
| tom_short_1_4 | USDJPY | H1 | 0.25% | $41 | 52 | $66 (162%) | 0.03 | live |
| or_fail_fra40 | FRA40 | M30 | 0.75% | $41 | 83 | $109 (269%) | 9.00 | new |
| ibs_lo0.2_hi0.8 | US30 | D1 | 0.50% | $35 | 27 | $58 (167%) | 0.10 | new |
| daily_mr_china50_d1 | CHINA50 | D1 | 0.25% | $0 | 0 | $0 (0%) | 0.00 | new |
| rsi2_mr_china50_d1 | CHINA50 | D1 | 0.25% | $0 | 0 | $0 (0%) | 0.00 | new |
| free_robot_H1_patternengulfing_oscrsi | XAUUSD | H1 | 0.50% | -$81 | 88 | $50 (61%) | 0.13 | live |
| free_robot_H1_patternharami_oscmfi | XAUUSD | H1 | 0.25% | -$88 | 226 | $38 (43%) | 0.07 | live |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 0.25% | -$94 | 97 | $59 (63%) | 0.05 | live |

## Ranked table of all 80 round-3 candidates

"Group score" is what the market group reported on the 2-year window at its best risk. "Solo 1% net" is
the exact portfolio-stage simulation at 1% risk from a fresh start on each window (a strategy whose data
begins later is simply flat until then). The last column says which mixes picked it and at what risk.

| # | Candidate | Market | TF | Group | Group score avg/mo | Solo 1% net 2y / 3y / 5y | Trades 2y / 5y | In mix 2y / 3y / 5y (risk) |
|---|---|---|---|---|---|---|---|---|
| 1 | first_hour_mult_break_de40 | DE40 | M30 | europe_indices | $89 | $7,553 / $9,778 / $11,645 | 362 / 1001 | 0.25% / 0.25% / 0.50% |
| 2 | weekday_MW_Th | ETHUSD | H1 | crypto | $148 | $7,416 / $7,364 / $1,578 | 318 / 787 | - / - / - |
| 3 | ch_24-24_s1.5_tp2.5_long | XAUUSD | H1 | metals | $101 | $5,068 / $6,122 / $3,528 | 264 / 664 | - / - / - |
| 4 | ab_mql_range_mid_mr0.3 | XAUUSD | M30 | metals | $76 | $4,648 / $5,495 / $1,176 | 356 / 827 | 0.50% / - / - |
| 5 | pw_h4_sfp_trail2 | SOLUSD | H4 | crypto | $101 | $4,592 / $4,592 / $4,592 | 71 / 71 | 0.75% / 0.25% / 0.25% |
| 6 | pb_atr1.0_range_be1.0 | XAUUSD | H1 | metals | $69 | $3,769 / $2,733 / -$1,366 | 220 / 650 | - / - / - |
| 7 | prev_week_high_long_de40 | DE40 | M30 | europe_indices | $84 | $3,566 / $7,203 / $6,835 | 46 / 130 | 0.50% / 0.50% / 0.50% |
| 8 | brent_wti_spread_z | XTIUSD | H4 | oil_gas | $100 | $3,367 / $3,348 / $2,895 | 39 / 87 | 0.50% / - / - |
| 9 | donchian160_h4 | XTIUSD | H4 | oil_gas | $94 | $3,128 / $2,743 / $1,716 | 22 / 74 | 1.00% / 0.50% / 0.25% |
| 10 | spike_follow | BTCUSD | H1 | crypto | $81 | $2,779 / $5,376 / $5,233 | 207 / 613 | - / 0.50% / 0.25% |
| 11 | rz_XAGUSD_n200_z2.5 | XAUUSD | H1 | metals | $67 | $2,654 / $3,503 / $5,162 | 71 / 187 | - / 0.25% / 0.50% |
| 12 | eia_fade_m30 | XTIUSD | M30 | oil_gas | $78 | $2,589 / $2,537 / -$642 | 77 / 211 | 0.75% / 0.25% / - |
| 13 | inside_bar_h4 | XTIUSD | H4 | oil_gas | $51 | $2,550 / $1,764 / -$261 | 122 / 298 | 0.50% / - / - |
| 14 | squeeze_h4_a25_kc2 | ETHUSD | H4 | crypto | $98 | $2,449 / $2,693 / $2,657 | 45 / 119 | 0.25% / 0.25% / 0.50% |
| 15 | sh_long_21-3_s3.0 | XAUUSD | H1 | metals | $97 | $2,423 / $3,076 / $2,905 | 485 / 1255 | 0.50% / 0.50% / 0.75% |
| 16 | pdm_t10_h24 | ETHUSD | H1 | crypto | $90 | $2,241 / $2,134 / $3,087 | 93 / 226 | 0.25% / - / 0.25% |
| 17 | wd_MW_Th_a15 | BTCUSD | D1 | crypto | $195 | $2,101 / $2,917 / $2,463 | 318 / 787 | 1.00% / 1.25% / 0.50% |
| 18 | d1_reversal_gbpusd | GBPUSD | D1 | majors | $119 | $1,936 / $2,065 / $2,022 | 56 / 143 | - / - / - |
| 19 | thursday_effect_h1 | XBRUSD | H1 | oil_gas | $38 | $1,921 / $2,564 / $116 | 104 / 261 | - / - / - |
| 20 | round_big_bounce | USTEC | M30 | us_indices | $59 | $1,870 / $1,876 / $1,842 | 105 / 201 | 0.75% / 1.25% / 0.75% |
| 21 | wo_d1.0_t0.2_r2 | XAUUSD | H4 | metals | $83 | $1,616 / $989 / -$2,182 | 37 / 108 | 0.25% / - / - |
| 22 | nr_7_mid_r2 | XAGUSD | H1 | metals | $108 | $1,572 / $1,065 / $196 | 53 / 146 | 1.25% / 1.25% / - |
| 23 | down_streak_k2_trend | US500 | D1 | us_indices | $134 | $1,566 / $2,314 / $2,226 | 52 / 104 | - / - / - |
| 24 | rsi2_mr_aus200_h4 | AUS200 | H4 | asia_indices | $88 | $1,556 / $1,556 / $1,556 | 191 / 191 | 0.75% / 0.50% / 0.50% |
| 25 | trend_pullback_h4_10_30_100 | USDCAD | H4 | commodity_fx | $46 | $1,544 / $1,041 / $473 | 96 / 235 | - / - / - |
| 26 | exo_usdcnh_tsmom60 | USDCNH | D1 | exotics | $137 | $1,489 / $1,489 / $1,489 | 8 / 8 | - / - / - |
| 27 | inside_h4_trail | XRPUSD | H4 | crypto | $47 | $1,386 / $1,386 / $1,386 | 48 / 48 | 0.50% / 0.25% / 0.50% |
| 28 | zmean_n100_adx25 | NZDUSD | H4 | commodity_fx | $66 | $1,332 / $1,035 / $1,016 | 23 / 76 | 0.50% / 1.00% / 0.25% |
| 29 | exo_eurnok_rsi2_h4 | EURNOK | H4 | exotics | $141 | $1,320 / $1,320 / $1,320 | 57 / 57 | 0.50% / 0.50% / 0.75% |
| 30 | us_open_fade_short_fra40 | FRA40 | M30 | europe_indices | $36 | $1,278 / $1,214 / $414 | 53 / 114 | - / - / - |
| 31 | d1_reversal_gbpchf | GBPCHF | D1 | majors | $78 | $1,273 / $1,633 / $942 | 57 / 142 | - / - / - |
| 32 | inside_day_break_usdchf | USDCHF | H4 | majors | $76 | $1,259 / $1,872 / $1,409 | 57 / 137 | 1.00% / 0.75% / - |
| 33 | pwh_sweep_h4_wc | GBPJPY | H4 | jpy_crosses | $36 | $1,245 / $742 / $190 | 69 / 173 | - / - / - |
| 34 | rsi2_thresh10_sma5 | US500 | D1 | us_indices | $106 | $1,229 / $1,438 / $1,399 | 25 / 49 | 1.25% / 1.50% / 1.50% |
| 35 | rsi2c_d1_ex10_usdjpy | USDJPY | D1 | jpy_crosses | $98 | $1,221 / $1,099 / $200 | 60 / 154 | - / - / - |
| 36 | exo_usdcnh_3bar_pullback | USDCNH | D1 | exotics | $112 | $1,216 / $1,216 / $1,216 | 21 / 21 | - / 0.25% / 1.25% |
| 37 | turtle_soup_n20_long | US30 | D1 | us_indices | $76 | $1,204 / $923 / $582 | 17 / 45 | - / - / 0.75% |
| 38 | prev_week_break_long | USTEC | H1 | us_indices | $76 | $1,188 / $1,637 / $1,460 | 44 / 113 | - / 1.00% / 0.50% |
| 39 | bb_reentry_r_sl0.8 | EURNZD | H4 | commodity_fx | $69 | $1,129 / $499 / $544 | 56 / 146 | - / - / - |
| 40 | tsmom_d1_lb40_a2 | BTCUSD | D1 | crypto | $80 | $1,121 / $1,558 / $2,727 | 82 / 199 | - / - / - |
| 41 | gas_ma15_140_h1 | XNGUSD | H1 | oil_gas | $38 | $1,118 / -$111 / -$93 | 121 / 317 | - / - / - |
| 42 | exo_eurnok_pwhl_break | EURNOK | D1 | exotics | $166 | $1,112 / $1,112 / $1,112 | 17 / 17 | - / 0.50% / - |
| 43 | exo_usdsek_weekly_fade | USDSEK | D1 | exotics | $73 | $1,072 / $1,072 / $1,072 | 92 / 92 | - / - / - |
| 44 | ibs_lo0.2_hi0.8 | US30 | D1 | us_indices | $107 | $1,068 / $1,514 / $1,127 | 49 / 116 | - / 1.00% / 0.50% |
| 45 | monday_gap_fade_gbpusd | GBPUSD | H1 | majors | $82 | $1,014 / $1,058 / $1,021 | 26 / 48 | 2.50% / 2.00% / 2.00% |
| 46 | exo_eurnok_inside_day | EURNOK | D1 | exotics | $149 | $1,013 / $1,013 / $1,013 | 14 / 14 | 0.50% / 1.25% / 2.00% |
| 47 | streak4_fade_d1 | GBPJPY | D1 | jpy_crosses | $62 | $1,006 / $136 / $787 | 26 / 87 | - / - / - |
| 48 | orb_11_esp35 | ESP35 | M30 | europe_indices | $38 | $946 / $1,585 / $19 | 80 / 471 | - / - / - |
| 49 | exo_usdmxn_ema_pullback | USDMXN | D1 | exotics | $88 | $943 / $943 / $943 | 10 / 10 | - / - / 0.25% |
| 50 | rsi2c_d1_ex10_gbpjpy | GBPJPY | D1 | jpy_crosses | $78 | $942 / $717 / $174 | 59 / 159 | - / - / - |
| 51 | monday_cash_long_de40 | DE40 | M30 | europe_indices | $92 | $918 / $1,165 / $1,105 | 84 / 231 | 0.25% / - / 1.25% |
| 52 | weekday_fri_to_mon | USTEC | D1 | us_indices | $96 | $903 / $1,106 / $1,123 | 58 / 136 | 0.75% / 1.50% / 1.50% |
| 53 | friday_week_fade_eurusd | EURUSD | H1 | majors | $71 | $887 / $663 / $838 | 18 / 39 | 2.00% / 1.50% / 1.50% |
| 54 | gap_go_jpn225_m30 | JPN225 | M30 | asia_indices | $79 | $874 / $382 / -$441 | 7 / 43 | - / 1.25% / - |
| 55 | gap_fade_fill | EURJPY | H1 | jpy_crosses | $70 | $867 / $843 / $650 | 46 / 74 | - / - / - |
| 56 | d1_reversal_eurchf | EURCHF | D1 | majors | $70 | $844 / $476 / $475 | 42 / 130 | - / - / - |
| 57 | d1_meanrev_z1_streak3 | GBPAUD | D1 | commodity_fx | $48 | $804 / $908 / $1,271 | 42 / 83 | - / - / - |
| 58 | overnight_trend | US500 | M30 | us_indices | $67 | $794 / $1,017 / $366 | 295 / 695 | 0.50% / - / - |
| 59 | tsmom20_highvol | XBRUSD | D1 | oil_gas | $49 | $778 / $384 / $630 | 57 / 124 | - / - / - |
| 60 | band_fade_h4_trend | CHFJPY | H4 | jpy_crosses | $64 | $778 / $423 / $49 | 17 / 46 | - / 0.25% / - |
| 61 | friday_week_fade_usdchf | USDCHF | H1 | majors | $62 | $770 / $744 / $765 | 18 / 49 | - / 0.50% / 0.25% |
| 62 | gold_div_follow | NZDUSD | D1 | commodity_fx | $39 | $741 / $333 / -$453 | 71 / 179 | - / - / - |
| 63 | friday_week_fade_gbpusd | GBPUSD | H1 | majors | $57 | $708 / $117 / $223 | 50 / 128 | - / - / - |
| 64 | squeeze_pct60_tp2 | USDCAD | D1 | commodity_fx | $58 | $706 / $447 / $148 | 7 / 21 | - / - / - |
| 65 | streak3_fade_d1_big | CADJPY | D1 | jpy_crosses | $57 | $705 / $398 / $742 | 30 / 101 | - / - / - |
| 66 | daily_mr_aus200_d1 | AUS200 | D1 | asia_indices | $63 | $690 / $690 / $690 | 102 / 102 | - / 0.25% / - |
| 67 | donchian_20_10 | USDCAD | D1 | commodity_fx | $40 | $672 / $401 / -$255 | 15 / 51 | - / - / - |
| 68 | gas_rsi14_h4 | XNGUSD | H4 | oil_gas | $44 | $669 / -$238 / $59 | 35 / 114 | 0.25% / 0.25% / - |
| 69 | trend_pullback_d1_trail3 | AUDNZD | D1 | commodity_fx | $52 | $645 / $422 / $144 | 11 / 31 | - / - / - |
| 70 | daily_mr_china50_d1 | CHINA50 | D1 | asia_indices | $112 | $615 / $615 / $615 | 40 / 40 | - / 1.25% / 0.25% |
| 71 | or_fail_fra40 | FRA40 | M30 | europe_indices | $52 | $612 / $244 / $185 | 30 / 83 | 1.00% / 0.75% / 0.75% |
| 72 | carry_dip_200 | EURJPY | D1 | jpy_crosses | $37 | $587 / $421 / -$14 | 61 / 154 | - / - / - |
| 73 | up_long_23-9_s3.0_pdup | XPDUSD | H1 | metals | $33 | $539 / -$298 / -$1,051 | 168 / 514 | 0.25% / - / - |
| 74 | daily_mr_hk50_d1 | HK50 | D1 | asia_indices | $42 | $513 / $98 / $351 | 19 / 50 | - / - / - |
| 75 | rsi2_mr_china50_d1 | CHINA50 | D1 | asia_indices | $82 | $489 / $489 / $489 | 71 / 71 | - / 0.25% / 0.25% |
| 76 | exo_usdzar_rsi2_d1 | USDZAR | D1 | exotics | $39 | $419 / $419 / $419 | 27 / 27 | - / - / - |
| 77 | gap_fill_aus200_h1 | AUS200 | H1 | asia_indices | $23 | $331 / $331 / $331 | 114 / 114 | 0.50% / 1.25% / 0.75% |
| 78 | monday_cash_long_esp35 | ESP35 | M30 | europe_indices | $70 | $280 / $440 / -$285 | 27 / 162 | - / - / - |
| 79 | rsi2_mr_jpn225_h1 | JPN225 | H1 | asia_indices | $82 | $181 / -$91 / -$4,592 | 11 / 428 | 1.25% / - / - |
| 80 | gap_fade_esp35_h1 | ESP35 | H1 | europe_indices | $43 | -$34 / -$872 / -$2,579 | 42 / 224 | - / - / - |

## Data notes

- Strategies whose data begins after a window start are flat until their data begins:
- Current 66 (live): flat at the start of the 5-year window (data begins later): EURCHF D1, EURJPY D1, EURUSD D1, EURUSD H1, GBPJPY D1, GBPUSD D1, US500 D1, USDCHF D1, USDJPY D1, USDJPY H4, USTEC H1, XAUUSD H1
- Mix-2y: flat at the start of the 5-year window (data begins later): AUS200 H1, AUS200 H4, EURCHF D1, EURNOK D1, EURNOK H4, SOLUSD H4, USTEC D1, USTEC M30, XNGUSD H4, XRPUSD H4
- Mix-3y: flat at the start of the 5-year window (data begins later): AUS200 D1, AUS200 H1, AUS200 H4, CHFJPY H4, CHINA50 D1, EURCHF D1, EURNOK D1, EURNOK H4, EURUSD H1, SOLUSD H4, USDCNH D1, USDJPY H4, USTEC D1, USTEC H1, USTEC M30, XNGUSD H4, XRPUSD H4
- Mix-5y: flat at the start of the 5-year window (data begins later): AUS200 H1, AUS200 H4, EURCHF D1, EURNOK D1, EURNOK H4, EURUSD H1, SOLUSD H4, USDCNH D1, USDMXN D1, USTEC D1, USTEC H1, USTEC M30, XRPUSD H4
- Windows are slices of one five-year simulation per strategy (fixed-dollar risk makes P&L path-independent); a
  position open across a window boundary is counted in the curve but not in the window's trade list. Not material.
- Costs: each market group's own cost patch (spread floors, no commission on indices/crypto, pip sizes, quote
  conversions) and data cleaner (flat/stale days, zero-volume bars, the DE40 stale week of 2024-11-28..12-05)
  were applied exactly as in the group scoring, see research/search3/portfolio/core3.py.
- Files: docs/board/portfolio-round3-2y.json, portfolio-round3-3y.json, portfolio-round3-5y.json (same format
  as portfolio-lp300-66.json plus the cross-evaluation); raw numbers in research/search3/portfolio/out/round3w_results.json.

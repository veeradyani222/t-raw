# Round-5 strategy screen (1% of $10K per trade; halve for $5K)

dev = 2015..2023-10-20 (pick period). unseen yr = Oct 2023..Oct 2024. last 2y = Oct 2024..Oct 2026 = the window the round-3 pool and the 66 were SEARCHED on, so it is a fit period for every strategy here. Sep+Oct = 2026-09-01..10-31.

### The live 24 on long history (24 rows)

| strategy | market | tf | live risk | data from | dev years | green years | dev $/mo | unseen yr $/mo | last 2y $/mo (fit) | Sep+Oct $/mo | worst day 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | 2018-03-12 | 5 | 3 | -12 | 174 | 72 | 27 | -171 |
| monday_long_downweek | EURJPY | H1 | 0.75% | 2018-10-08 | 5 | 3 | 31 | 87 | 62 | -142 | -213 |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 1.00% | 2015-03-16 | 8 | 5 | 6 | 86 | 241 | -231 | -210 |
| ab_mql_range_mid_mr0.3 | XAUUSD | M30 | 0.50% | 2018-04-25 | 5 | 0 | -132 | 71 | 188 | 124 | -114 |
| wd_MW_Th_a15 | BTCUSD | D1 | 1.00% | 2016-06-22 | 7 | 4 | -19 | 68 | 86 | 81 | -99 |
| sh_long_21-3_s3.0 | XAUUSD | H1 | 1.00% | 2015-01-05 | 9 | 2 | -32 | 54 | 96 | -29 | -147 |
| inside_day_break_usdchf | USDCHF | H4 | 1.00% | 2015-01-07 | 9 | 2 | -12 | 51 | 48 | -149 | -138 |
| zscore | US500 | H4 | 0.75% | 2015-03-10 | 8 | 5 | 19 | 29 | 55 | -51 | -183 |
| rsi2_thresh10_sma5 | US500 | D1 | 1.25% | 2015-11-09 | 8 | 5 | 6 | 17 | 47 | 29 | -74 |
| weekday_fri_to_mon | USTEC | D1 | 2.50% | 2022-08-12 | 1 | 1 | 1 | 17 | 37 | 30 | -83 |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.50% | 2015-02-02 | 9 | 4 | -11 | 4 | 42 | 27 | -100 |
| bb_fade | EURUSD | H1 | 1.25% | 2022-08-12 | 1 | 1 | 47 | 3 | 39 | 0 | -188 |
| round_big_bounce | USTEC | M30 | 0.75% | 2022-07-19 | 1 | 0 | -2 | 1 | 76 | -51 | -99 |
| brent_wti_spread_z | XTIUSD | H4 | 0.50% | 2021-01-05 | 3 | 0 | -5 | -2 | 138 | -40 | -203 |
| eia_fade_m30 | XTIUSD | M30 | 0.75% | 2018-05-16 | 5 | 0 | -91 | -4 | 106 | -7 | -167 |
| us_open_fade_short_fra40 | FRA40 | M30 | 1.50% | 2019-05-16 | 4 | 2 | -17 | -5 | 53 | -5 | -99 |
| connors_rsi2_D1_ | EURCHF | D1 | 2.75% | 2015-11-04 | 8 | 5 | 2 | -6 | 13 | 12 | -77 |
| friday_week_fade_eurusd | EURUSD | H1 | 2.00% | 2022-08-19 | 1 | 1 | -0 | -19 | 27 | 59 | -99 |
| rsi2_mr_jpn225_h1 | JPN225 | H1 | 1.25% | 2019-04-29 | 4 | 0 | -181 | -23 | 7 | 0 | -206 |
| donchian160_h4 | XTIUSD | H4 | 1.00% | 2016-08-17 | 7 | 3 | 0 | -32 | 128 | 93 | -228 |
| nr_7_mid_r2 | XAGUSD | H1 | 1.25% | 2015-01-13 | 9 | 0 | -47 | -42 | 63 | -90 | -99 |
| inside_bar_h4 | XTIUSD | H4 | 0.50% | 2016-07-04 | 7 | 1 | -69 | -65 | 105 | 118 | -267 |
| pw_h4_sfp_trail2 | SOLUSD | H4 | 0.75% | 2025-01-06 | 0 | 0 | - | - | 211 | -218 | -271 |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.75% | 2025-02-19 | 0 | 0 | - | - | 77 | 98 | -197 |

Sum of the 24 at 1% each (no account stop): dev $-518/mo, unseen yr $463/mo, last 2y $2,018/mo, Sep+Oct $-315/mo

### Not in the 24, judged on dev data, ranked by dev $/month (109 rows with >= 3 dev years)

| strategy | market | tf | in mixes | data from | dev years | green years | dev $/mo | unseen yr $/mo | last 2y $/mo (fit) | Sep+Oct $/mo | worst day 3y | trades 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tsmom_d1_lb40_a2 | BTCUSD | D1 | - | 2017-03-24 | 6 | 5 | 76 | 36 | 46 | -20 | -100 | 132 |
| mon_long_h0_hold23 | EURJPY | H1 | 66 | 2018-10-01 | 5 | 4 | 56 | 98 | 76 | -81 | -100 | 156 |
| pa_bos_BTCUSD_D1 | BTCUSD | D1 | - | 2016-12-21 | 7 | 6 | 53 | 33 | 11 | -32 | -212 | 18 |
| first_hour_mult_break_de40 | DE40 | M30 | 51,62,57 | 2018-03-13 | 5 | 2 | 43 | 213 | 146 | 356 | -100 | 666 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | - | 2017-03-24 | 6 | 5 | 38 | -47 | -70 | -135 | -159 | 65 |
| pa_engulf_UK100_H4 | UK100 | H4 | - | 2015-11-16 | 8 | 6 | 34 | 29 | -22 | 48 | -155 | 59 |
| pa_pin_AUDUSD_D1 | AUDUSD | D1 | - | 2015-03-24 | 8 | 5 | 32 | 93 | -10 | 129 | -142 | 21 |
| tom_k0_h20_hold72_sl3 | DE40 | H1 | 66 | 2016-01-29 | 8 | 5 | 30 | 14 | 2 | -88 | -238 | 32 |
| pa_double_USDCAD_H1 | USDCAD | H1 | - | 2015-01-19 | 9 | 9 | 29 | -24 | 13 | 78 | -159 | 37 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | - | 2017-05-15 | 6 | 5 | 28 | 159 | 80 | -207 | -306 | 137 |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 66,74,51,62,57 | 2015-02-06 | 9 | 7 | 26 | -87 | 79 | 54 | -182 | 71 |
| pa_double_USDJPY_H1 | USDJPY | H1 | - | 2015-02-26 | 8 | 6 | 25 | -9 | 13 | 0 | -128 | 34 |
| vwap | DE40 | H1 | 66,74,51,62,57 | 2016-01-26 | 8 | 6 | 24 | -20 | -22 | -66 | -196 | 56 |
| pa_pin_DE40_D1 | DE40 | D1 | - | 2015-03-06 | 8 | 7 | 23 | -2 | 30 | 30 | -123 | 24 |
| pdm_t10_h24 | ETHUSD | H1 | 74,51,57 | 2020-03-09 | 3 | 2 | 23 | -9 | 94 | -66 | -100 | 136 |
| pa_engulf_USDCAD_D1 | USDCAD | D1 | - | 2015-03-18 | 8 | 7 | 22 | -4 | 0 | -48 | -145 | 9 |
| pa_pin_USDCHF_D1 | USDCHF | D1 | - | 2015-07-28 | 8 | 5 | 21 | -57 | 4 | 0 | -114 | 13 |
| pa_bos_LTCUSD_D1 | LTCUSD | D1 | - | 2015-06-16 | 8 | 3 | 20 | -37 | -45 | 84 | -260 | 51 |
| pa_hikkake_ETHUSD_D1 | ETHUSD | D1 | - | 2017-07-18 | 6 | 6 | 19 | -44 | 10 | -150 | -142 | 18 |
| pa_inside_EURJPY_D1 | EURJPY | D1 | - | 2019-01-14 | 5 | 3 | 16 | -46 | -54 | -112 | -102 | 65 |
| tsmom20_highvol | XBRUSD | D1 | - | 2017-05-16 | 6 | 4 | 14 | -33 | 32 | 0 | -156 | 83 |
| pa_hikkake_BTCUSD_D1 | BTCUSD | D1 | - | 2016-06-21 | 7 | 5 | 13 | 27 | -30 | -184 | -227 | 22 |
| dip_combo | US500 | D1 | 66,62,57 | 2015-11-11 | 8 | 5 | 13 | 20 | 31 | -24 | -83 | 41 |
| rsi_rev+trend | EURCHF | H4 | 66 | 2015-04-23 | 8 | 6 | 13 | -54 | -8 | 66 | -125 | 18 |
| pa_bos_GBPAUD_D1 | GBPAUD | D1 | - | 2015-01-23 | 9 | 7 | 12 | -36 | -0 | -19 | -72 | 33 |
| pa_bos_GBPJPY_D1 | GBPJPY | D1 | - | 2015-02-05 | 9 | 6 | 12 | 3 | -13 | 62 | -118 | 26 |
| bos_hv_be1_M30 | XAUUSD | M30 | 66 | 2018-05-23 | 5 | 4 | 11 | 92 | 164 | -210 | -273 | 338 |
| pweek_sl1_trail8 | DE40 | H1 | 66,74,51,57 | 2015-01-06 | 9 | 7 | 11 | 95 | 34 | -75 | -167 | 138 |
| crabel_k0.5_None | DE40 | M30 | 66 | 2018-03-20 | 5 | 3 | 10 | 113 | 125 | -288 | -108 | 749 |
| zmean_n100_adx25 | NZDUSD | H4 | 74,51,62,57 | 2015-05-07 | 8 | 6 | 10 | -25 | 51 | -49 | -197 | 39 |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 74,51,62,57 | 2017-08-09 | 6 | 4 | 10 | 20 | 101 | 9 | -155 | 68 |
| squeeze_pct60_tp2 | USDCAD | D1 | - | 2015-05-22 | 8 | 4 | 8 | -21 | 29 | 91 | -169 | 11 |
| mfi_rev+trend | USDJPY | D1 | 66 | 2018-08-23 | 5 | 3 | 8 | 0 | 5 | 0 | -30 | 1 |
| ibs_lo0.2_hi0.8 | US30 | D1 | 74,62,57 | 2015-10-30 | 8 | 5 | 6 | 37 | 46 | 46 | -91 | 77 |
| spike_follow | BTCUSD | H1 | 74,62,57 | 2017-05-05 | 6 | 3 | 6 | 216 | 121 | 6 | -291 | 324 |
| down_streak_k2_trend | US500 | D1 | - | 2015-11-05 | 8 | 4 | 5 | 62 | 64 | -14 | -116 | 72 |
| inside_far_tp2 | XAUUSD | H1 | 66,74,62,57 | 2015-01-08 | 9 | 6 | 4 | 18 | 70 | -55 | -175 | 90 |
| turtle_soup_n20_long | US30 | D1 | 74,57 | 2015-02-02 | 9 | 3 | 4 | -23 | 49 | 111 | -113 | 20 |
| htf_bo50_n24 | XAUUSD | H1 | 66,62,57 | 2015-03-17 | 8 | 4 | 4 | 27 | 234 | -53 | -210 | 282 |
| rz_XAGUSD_n200_z2.5 | XAUUSD | H1 | 62,57 | 2015-01-16 | 9 | 4 | 3 | 71 | 117 | 126 | -243 | 112 |
| de_orb2.0_trNone_tp2.0_ex18 | DE40 | H1 | 66,74 | 2016-01-26 | 8 | 4 | 3 | 163 | 62 | 167 | -100 | 328 |
| d1_meanrev_z1_streak3 | GBPAUD | D1 | - | 2015-01-29 | 9 | 4 | 3 | 9 | 33 | 42 | -128 | 56 |
| rsi_rev+trend | GBPJPY | H4 | 66,62,57 | 2015-03-05 | 8 | 5 | 3 | -1 | 21 | 71 | -101 | 14 |
| connors_rsi2_D1_ | EURJPY | D1 | 66 | 2019-10-11 | 4 | 2 | 2 | -7 | 10 | 0 | -90 | 14 |
| kelt_rev+trend | GBPJPY | D1 | 66 | 2016-11-28 | 7 | 4 | 2 | 3 | 5 | 0 | -53 | 3 |
| rsi_rev+trend | GBPUSD | D1 | 66 | 2020-06-11 | 3 | 1 | 2 | 0 | 5 | 0 | -19 | 1 |
| or_fail_fra40 | FRA40 | M30 | 74,51,62,57 | 2019-05-08 | 4 | 2 | 1 | -31 | 25 | -44 | -100 | 47 |
| connors_rsi2_D1_rsi_n3 | GBPUSD | D1 | 66 | 2018-05-01 | 5 | 2 | 1 | 0 | 2 | 0 | -31 | 2 |
| kelt_rev+trend | GBPUSD | D1 | 66 | 2016-06-24 | 7 | 3 | 1 | -7 | 5 | 0 | -33 | 2 |
| free_robot_H4_patternsoldiers_osccci | USDJPY | H4 | 66 | 2016-05-03 | 7 | 2 | 0 | -8 | 4 | 0 | -65 | 2 |
| rsi_rev+trend | XAUUSD | H1 | 66,74,57 | 2015-01-26 | 9 | 5 | 0 | 20 | 17 | 88 | -217 | 60 |
| connors_rsi2_D1_rsi_n3 | US500 | D1 | 66 | 2016-11-01 | 7 | 1 | -0 | 0 | 12 | 0 | -51 | 2 |
| tsmom50 | DE40 | H4 | 66 | 2016-01-06 | 8 | 2 | -1 | -53 | 44 | 4 | -99 | 275 |
| daily_mr_hk50_d1 | HK50 | D1 | - | 2015-03-10 | 8 | 3 | -1 | -34 | 21 | 9 | -160 | 32 |
| free_robot_H4_patternhammer_oscrsi | USDJPY | H4 | 66,62 | 2015-01-13 | 9 | 5 | -1 | 8 | 8 | 0 | -100 | 16 |
| bb_breakout_M30_dev2.5 | XAUUSD | M30 | 66,74 | 2018-04-30 | 5 | 3 | -2 | 40 | 125 | -201 | -358 | 250 |
| connors_rsi2_D1_ | USDCHF | D1 | 66,74,51,62,57 | 2015-12-03 | 8 | 3 | -2 | 2 | 15 | 0 | -72 | 18 |
| tom_short_1_4 | USDJPY | H1 | 66,74,51,62,57 | 2015-01-29 | 9 | 2 | -2 | -6 | 25 | 118 | -94 | 36 |
| day1-14_te20_tp1.5 | DE40 | H1 | 66 | 2016-01-25 | 8 | 4 | -2 | 29 | -16 | -46 | -192 | 468 |
| rsi2c_d1_ex10_usdjpy | USDJPY | D1 | - | 2015-01-05 | 9 | 5 | -2 | -10 | 53 | 26 | -101 | 93 |
| ema_x | US500 | D1 | 66 | 2015-01-05 | 9 | 4 | -2 | 24 | 20 | 0 | -5 | 7 |
| gap_go_jpn225_m30 | JPN225 | M30 | 62 | 2019-05-20 | 4 | 2 | -3 | -41 | 36 | 0 | -99 | 15 |
| rsi_rev+trend | GBPJPY | D1 | 66 | 2016-11-11 | 7 | 1 | -3 | -8 | 5 | 0 | -57 | 2 |
| mfi_rev+trend | EURJPY | D1 | 66 | 2019-10-25 | 4 | 0 | -4 | 4 | 0 | 0 | -48 | 2 |
| mfi_rev+trend | USDCHF | D1 | 66 | 2016-02-16 | 7 | 0 | -4 | 0 | 6 | 0 | -72 | 1 |
| gas_rsi14_h4 | XNGUSD | H4 | 74,51,62 | 2016-09-12 | 7 | 3 | -4 | -75 | 27 | -56 | -162 | 62 |
| free_robot_H1_patternsoldiers_oscmfi | XAUUSD | H1 | 66 | 2015-02-10 | 9 | 4 | -5 | -15 | 6 | 0 | -113 | 12 |
| friday_week_fade_usdchf | USDCHF | H1 | 74,62,57 | 2015-01-30 | 9 | 4 | -6 | -2 | 32 | 48 | -100 | 29 |
| streak4_fade_d1 | GBPJPY | D1 | 74 | 2015-01-14 | 9 | 5 | -6 | -72 | 41 | -1 | -151 | 53 |
| donchian_20_10 | USDCAD | D1 | - | 2015-01-30 | 9 | 5 | -7 | -23 | 28 | 49 | -94 | 26 |
| gold_div_follow | NZDUSD | D1 | - | 2015-07-01 | 8 | 3 | -7 | -34 | 34 | -40 | -143 | 109 |
| monday_cash_long_de40 | DE40 | M30 | 74,51,57 | 2018-03-19 | 5 | 3 | -9 | 19 | 32 | -0 | -100 | 152 |
| gap_fade_fill | EURJPY | H1 | - | 2018-10-01 | 5 | 1 | -10 | 8 | 20 | 72 | -100 | 56 |
| rsi_rev+trend | US30 | H1 | 66,74,51,62 | 2016-02-01 | 8 | 3 | -11 | 45 | 17 | 172 | -311 | 72 |
| d1_reversal_eurchf | EURCHF | D1 | - | 2015-03-13 | 8 | 1 | -12 | -32 | 1 | -112 | -143 | 85 |
| overnight_trend | US500 | M30 | 51 | 2018-04-18 | 5 | 2 | -12 | 19 | 33 | 8 | -95 | 428 |
| d1_reversal_gbpusd | GBPUSD | D1 | - | 2015-02-05 | 9 | 3 | -12 | 11 | 83 | 39 | -343 | 86 |
| band_fade_h4_trend | CHFJPY | H4 | 62 | 2015-03-18 | 8 | 3 | -13 | -30 | 32 | -49 | -143 | 28 |
| kelt_rev+trend | GBPJPY | H4 | 66,74,51,62,57 | 2015-03-05 | 8 | 3 | -15 | 8 | 29 | 49 | -169 | 39 |
| trend_pullback_d1_trail3 | AUDNZD | D1 | - | 2015-12-01 | 8 | 2 | -15 | -19 | 26 | 29 | -98 | 17 |
| bb_rev+trend | GBPUSD | H4 | 66,74,62,57 | 2015-03-19 | 8 | 3 | -16 | 24 | 47 | -23 | -218 | 78 |
| friday_week_fade_gbpusd | GBPUSD | H1 | - | 2015-01-23 | 9 | 2 | -18 | -49 | 31 | 82 | -99 | 77 |
| free_robot_H1_patternengulfing_oscrsi | XAUUSD | H1 | 66,74,51,62,57 | 2015-01-12 | 9 | 0 | -22 | 8 | 3 | -17 | -173 | 55 |
| rsi2c_d1_ex10_gbpjpy | GBPJPY | D1 | - | 2015-01-05 | 9 | 2 | -23 | -19 | 41 | -55 | -99 | 97 |
| carry_dip_200 | EURJPY | D1 | - | 2019-10-09 | 4 | 1 | -23 | -12 | 29 | 33 | -148 | 94 |
| persistent_anti_D1_ | USDJPY | D1 | 66,74,51,62,57 | 2015-01-29 | 9 | 1 | -23 | 21 | 19 | 1 | -90 | 153 |
| ch_24-24_s1.5_tp2.5_long | XAUUSD | H1 | - | 2015-01-06 | 9 | 4 | -24 | 88 | 210 | -289 | -236 | 412 |
| stoch_rev+trend | GBPUSD | H4 | 66,57 | 2015-02-27 | 8 | 3 | -24 | -3 | 64 | -15 | -150 | 96 |
| trend_pullback_h4_10_30_100 | USDCAD | H4 | - | 2015-01-26 | 9 | 2 | -25 | -42 | 63 | 52 | -176 | 144 |
| bb_reentry_r_sl0.8 | EURNZD | H4 | 74 | 2015-01-16 | 9 | 3 | -30 | -52 | 46 | -5 | -202 | 86 |
| free_robot_H1_patternharami_oscmfi | XAUUSD | H1 | 66,74,51,62,57 | 2015-01-06 | 9 | 1 | -31 | -4 | -19 | 84 | -225 | 152 |
| thursday_effect_h1 | XBRUSD | H1 | 74 | 2016-08-31 | 7 | 2 | -32 | 53 | 79 | 273 | -278 | 156 |
| dmi_x | US30 | H1 | 66,74 | 2015-01-05 | 9 | 2 | -35 | -108 | 40 | -146 | -430 | 550 |
| monday_cash_long_esp35 | ESP35 | M30 | - | 2019-05-13 | 4 | 0 | -36 | 13 | 11 | 0 | -99 | 75 |
| wo_d1.0_t0.2_r2 | XAUUSD | H4 | 74,51 | 2015-02-03 | 9 | 2 | -37 | -52 | 73 | 196 | -181 | 58 |
| aroon_x+trend | XAUUSD | H1 | 66,62 | 2015-01-22 | 9 | 3 | -38 | 103 | 122 | 71 | -230 | 322 |
| pwh_sweep_h4_wc | GBPJPY | H4 | - | 2015-01-12 | 9 | 2 | -47 | -42 | 47 | 141 | -207 | 107 |
| rsi_rev | US30 | H1 | 66 | 2015-01-29 | 9 | 3 | -48 | -115 | 79 | -21 | -311 | 447 |
| pb_atr1.0_range_be1.0 | XAUUSD | H1 | - | 2015-01-05 | 9 | 2 | -50 | -86 | 166 | -131 | -105 | 366 |
| tod_long_0-8 | EURCHF | H1 | - | 2015-01-20 | 9 | 2 | -55 | -190 | -155 | -145 | -99 | 784 |
| gas_ma15_140_h1 | XNGUSD | H1 | - | 2016-09-01 | 7 | 2 | -71 | -102 | 46 | 11 | -437 | 181 |
| gap_fade_esp35_h1 | ESP35 | H1 | 74 | 2019-05-09 | 4 | 0 | -74 | -70 | -1 | 86 | -99 | 97 |
| asia0-9_te14_tp1.0 | XAUUSD | H1 | 66 | 2015-01-06 | 9 | 1 | -81 | -25 | 72 | -70 | -140 | 439 |
| up_long_23-9_s3.0_pdup | XPDUSD | H1 | 74,51 | 2015-09-09 | 8 | 1 | -94 | -70 | 22 | 0 | -100 | 282 |
| tod_long_6-12 | FRA40 | H1 | - | 2019-05-21 | 4 | 0 | -101 | -117 | -107 | -321 | -100 | 671 |
| imom_nyclose_h1 | XAUUSD | H1 | 66,74,51 | 2015-01-26 | 9 | 0 | -107 | -22 | 17 | 48 | -94 | 757 |
| bos_trail3_htfD50_M30 | XAUUSD | M30 | 66,74,62 | 2018-06-29 | 5 | 2 | -109 | 42 | 225 | -64 | -217 | 601 |
| weekday_MW_Th | ETHUSD | H1 | - | 2020-03-03 | 3 | 0 | -154 | -4 | 305 | -90 | -100 | 474 |
| orb_11_esp35 | ESP35 | M30 | 74 | 2019-05-07 | 4 | 1 | -155 | 53 | 39 | 0 | -100 | 200 |

### Steady screen: >= 5 dev years, >= 80% green, dev $/month > 0 (10 rows)

| strategy | market | tf | in mixes | data from | dev years | green years | dev $/mo | unseen yr $/mo | last 2y $/mo (fit) | Sep+Oct $/mo | worst day 3y | trades 3y |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tsmom_d1_lb40_a2 | BTCUSD | D1 | - | 2017-03-24 | 6 | 5 | 76 | 36 | 46 | -20 | -100 | 132 |
| mon_long_h0_hold23 | EURJPY | H1 | 66 | 2018-10-01 | 5 | 4 | 56 | 98 | 76 | -81 | -100 | 156 |
| pa_bos_BTCUSD_D1 | BTCUSD | D1 | - | 2016-12-21 | 7 | 6 | 53 | 33 | 11 | -32 | -212 | 18 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | - | 2017-03-24 | 6 | 5 | 38 | -47 | -70 | -135 | -159 | 65 |
| pa_double_USDCAD_H1 | USDCAD | H1 | - | 2015-01-19 | 9 | 9 | 29 | -24 | 13 | 78 | -159 | 37 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | - | 2017-05-15 | 6 | 5 | 28 | 159 | 80 | -207 | -306 | 137 |
| pa_pin_DE40_D1 | DE40 | D1 | - | 2015-03-06 | 8 | 7 | 23 | -2 | 30 | 30 | -123 | 24 |
| pa_engulf_USDCAD_D1 | USDCAD | D1 | - | 2015-03-18 | 8 | 7 | 22 | -4 | 0 | -48 | -145 | 9 |
| pa_hikkake_ETHUSD_D1 | ETHUSD | D1 | - | 2017-07-18 | 6 | 6 | 19 | -44 | 10 | -150 | -142 | 18 |
| bos_hv_be1_M30 | XAUUSD | M30 | 66 | 2018-05-23 | 5 | 4 | 11 | 92 | 164 | -210 | -273 | 338 |

steady & not in 24: 10 strategies; sum $/mo at 1% each: dev $357, unseen yr $298, last 2y $361, Sep+Oct $-775; green in unseen yr 5/10


36 strategies cannot be judged on long history (data starts after 2020): AUDCAD, AUDJPY, AUS200, CADJPY, CHINA50, EURNOK, EURUSD, GBPCHF, USDCNH, USDMXN, USDSEK, USDZAR, USTEC, XRPUSD

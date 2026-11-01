
### Mixes on the $5K (x0.5, stop -$125) account (exact replay with the live daily stop)

| mix | strategies | dev 2015-23 (fast model) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|
| live23 | 23 | $-212/mo, low $-17,897, stops 229 in 8.8y | $124/mo, fail 9/24, low $4,601, stops 15 | $696/mo, fail 0/51, low $4,807, stops 21 | $153/mo, fail 0/3, low $4,967, stops 2 | $507/mo, fail 10/77, low $4,601, stops 36 |
| live23+adds | 52 | $-520/mo, low $-49,968, stops 765 in 8.8y | $103/mo, fail 8/24, low $4,486, stops 51 | $610/mo, fail 9/51, low $4,899, stops 70 | $-162/mo, fail 1/3, low $4,331, stops 6 | $442/mo, fail 18/77, low $4,486, stops 121 |
| honest | 33 | $68/mo, low $4,762, stops 11 in 8.8y | $133/mo, fail 0/24, low $4,798, stops 0 | $119/mo, fail 5/51, low $4,952, stops 0 | $-173/mo, fail 1/3, low $4,556, stops 0 | $124/mo, fail 4/77, low $4,798, stops 0 |
| strict | 10 | $60/mo, low $4,899, stops 66 in 8.8y | $113/mo, fail 7/24, low $4,944, stops 3 | $98/mo, fail 6/51, low $4,940, stops 5 | $-235/mo, fail 1/3, low $4,452, stops 0 | $103/mo, fail 13/77, low $4,944, stops 8 |
| pruned+adds | 46 | $-219/mo, low $-18,595, stops 524 in 8.8y | $117/mo, fail 10/24, low $4,500, stops 39 | $561/mo, fail 6/51, low $4,882, stops 49 | $-229/mo, fail 2/3, low $4,180, stops 5 | $414/mo, fail 18/77, low $4,500, stops 88 |

Same mixes with the equity regime switch (half size while the mix's 20-day mean equity is under its 60-day mean), $5K (x0.5, stop -$125):

| mix | half-size share of days | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|
| live23 | 11% | $93/mo, fail 8/24, low $4,601, stops 10 | $696/mo, fail 0/51, low $4,807, stops 21 | $153/mo, fail 0/3, low $4,967, stops 2 | $497/mo, fail 9/77, low $4,601, stops 31 |
| live23+adds | 22% | $123/mo, fail 7/24, low $4,486, stops 34 | $591/mo, fail 5/51, low $4,950, stops 57 | $-81/mo, fail 0/3, low $4,665, stops 0 | $437/mo, fail 16/77, low $4,486, stops 91 |
| honest | 14% | $121/mo, fail 0/24, low $4,798, stops 0 | $117/mo, fail 0/51, low $4,952, stops 0 | $-117/mo, fail 0/3, low $4,717, stops 0 | $118/mo, fail 0/77, low $4,798, stops 0 |
| strict | 30% | $104/mo, fail 2/24, low $4,944, stops 3 | $84/mo, fail 1/51, low $4,970, stops 5 | $-170/mo, fail 0/3, low $4,623, stops 0 | $91/mo, fail 3/77, low $4,944, stops 8 |
| pruned+adds | 18% | $81/mo, fail 13/24, low $4,500, stops 28 | $537/mo, fail 5/51, low $4,882, stops 46 | $-214/mo, fail 1/3, low $4,394, stops 2 | $386/mo, fail 20/77, low $4,500, stops 74 |

### Mixes on the $10K (x1.0, stop -$300) account (exact replay with the live daily stop)

| mix | strategies | dev 2015-23 (fast model) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|
| live23 | 23 | $-399/mo, low $-33,216, stops 142 in 8.8y | $106/mo, fail 10/24, low $8,535, stops 17 | $1,747/mo, fail 0/51, low $9,829, stops 11 | $190/mo, fail 0/3, low $9,878, stops 1 | $1,204/mo, fail 11/77, low $8,535, stops 28 |
| live23+adds | 52 | $-792/mo, low $-74,344, stops 527 in 8.8y | $283/mo, fail 8/24, low $8,813, stops 45 | $1,711/mo, fail 7/51, low $9,723, stops 60 | $-315/mo, fail 3/3, low $8,334, stops 5 | $1,239/mo, fail 15/77, low $8,813, stops 105 |
| honest | 33 | $147/mo, low $9,524, stops 1 in 8.8y | $306/mo, fail 0/24, low $9,526, stops 0 | $403/mo, fail 2/51, low $9,889, stops 0 | $-218/mo, fail 1/3, low $9,132, stops 0 | $371/mo, fail 2/77, low $9,526, stops 0 |
| strict | 10 | $164/mo, low $9,798, stops 29 in 8.8y | $185/mo, fail 10/24, low $9,849, stops 2 | $255/mo, fail 8/51, low $9,845, stops 3 | $-597/mo, fail 3/3, low $8,663, stops 0 | $232/mo, fail 18/77, low $9,849, stops 5 |
| pruned+adds | 46 | $-262/mo, low $-18,834, stops 341 in 8.8y | $480/mo, fail 8/24, low $8,927, stops 26 | $1,460/mo, fail 5/51, low $9,724, stops 41 | $-333/mo, fail 2/3, low $8,537, stops 4 | $1,136/mo, fail 15/77, low $8,927, stops 67 |

Same mixes with the equity regime switch (half size while the mix's 20-day mean equity is under its 60-day mean), $10K (x1.0, stop -$300):

| mix | half-size share of days | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|
| live23 | 13% | $53/mo, fail 10/24, low $9,169, stops 13 | $1,740/mo, fail 0/51, low $9,829, stops 11 | $113/mo, fail 0/3, low $9,878, stops 1 | $1,183/mo, fail 11/77, low $9,169, stops 24 |
| live23+adds | 15% | $296/mo, fail 7/24, low $8,813, stops 32 | $1,705/mo, fail 6/51, low $9,821, stops 55 | $-343/mo, fail 1/3, low $8,801, stops 1 | $1,239/mo, fail 15/77, low $8,813, stops 87 |
| honest | 16% | $262/mo, fail 0/24, low $9,526, stops 0 | $384/mo, fail 0/51, low $9,888, stops 0 | $-137/mo, fail 0/3, low $9,510, stops 0 | $343/mo, fail 0/77, low $9,526, stops 0 |
| strict | 29% | $164/mo, fail 5/24, low $9,849, stops 2 | $222/mo, fail 10/51, low $9,923, stops 3 | $-400/mo, fail 1/3, low $9,130, stops 0 | $203/mo, fail 13/77, low $9,849, stops 5 |
| pruned+adds | 15% | $380/mo, fail 11/24, low $8,927, stops 19 | $1,384/mo, fail 4/51, low $9,724, stops 37 | $-260/mo, fail 2/3, low $9,085, stops 1 | $1,052/mo, fail 17/77, low $8,927, stops 56 |

### Per-strategy profit inside 'live23', $5K account, exact replay

| strategy | market | tf | risk ($10K fraction) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|---|
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 1.00% | $348 | $2,022 | $-159 | $2,371 |
| bb_fade | EURUSD | H1 | 1.25% | $25 | $594 | $0 | $620 |
| monday_long_downweek | EURJPY | H1 | 0.75% | $380 | $543 | $-98 | $923 |
| zscore | US500 | H4 | 0.75% | $109 | $479 | $-39 | $589 |
| connors_rsi2_D1_ | EURCHF | D1 | 2.75% | $-95 | $428 | $32 | $333 |
| wd_MW_Th_a15 | BTCUSD | D1 | 1.00% | $383 | $777 | $50 | $1,161 |
| brent_wti_spread_z | XTIUSD | H4 | 0.50% | $50 | $804 | $7 | $854 |
| donchian160_h4 | XTIUSD | H4 | 1.00% | $-190 | $1,555 | $87 | $1,365 |
| eia_fade_m30 | XTIUSD | M30 | 0.75% | $-20 | $969 | $-5 | $950 |
| inside_bar_h4 | XTIUSD | H4 | 0.50% | $-191 | $644 | $-1 | $453 |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.75% | $0 | $556 | $79 | $556 |
| rsi2_mr_jpn225_h1 | JPN225 | H1 | 1.25% | $0 | $0 | $0 | $0 |
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | $493 | $385 | $18 | $877 |
| us_open_fade_short_fra40 | FRA40 | M30 | 1.50% | $-45 | $908 | $-6 | $863 |
| rsi2_thresh10_sma5 | US500 | D1 | 1.25% | $179 | $676 | $29 | $855 |
| weekday_fri_to_mon | USTEC | D1 | 2.50% | $216 | $1,284 | $148 | $1,499 |
| round_big_bounce | USTEC | M30 | 0.75% | $-39 | $646 | $-9 | $607 |
| nr_7_mid_r2 | XAGUSD | H1 | 1.25% | $-320 | $1,090 | $-89 | $770 |
| sh_long_21-3_s3.0 | XAUUSD | H1 | 1.00% | $310 | $708 | $34 | $1,018 |
| ab_mql_range_mid_mr0.3 | XAUUSD | M30 | 0.50% | $214 | $568 | $78 | $782 |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.50% | $55 | $1,278 | $67 | $1,333 |
| inside_day_break_usdchf | USDCHF | H4 | 1.00% | $277 | $555 | $-180 | $832 |
| friday_week_fade_eurusd | EURUSD | H1 | 2.00% | $-230 | $661 | $116 | $432 |

### Per-strategy profit inside 'honest', $5K account, exact replay

| strategy | market | tf | risk ($10K fraction) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|---|
| tom_k0_h20_hold72_sl3 | DE40 | H1 | 0.30% | $23 | $-14 | $0 | $9 |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 0.30% | $101 | $233 | $-12 | $333 |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 0.30% | $-87 | $133 | $0 | $46 |
| pweek_sl1_trail8 | DE40 | H1 | 0.30% | $0 | $0 | $0 | $0 |
| htf_bo50_n24 | XAUUSD | H1 | 0.30% | $89 | $255 | $0 | $344 |
| monday_long_downweek | EURJPY | H1 | 0.30% | $160 | $190 | $-39 | $350 |
| dip_combo | US500 | D1 | 0.30% | $27 | $42 | $0 | $69 |
| zscore | US500 | H4 | 0.30% | $43 | $162 | $-19 | $205 |
| crabel_k0.5_None | DE40 | M30 | 0.30% | $186 | $-43 | $-151 | $144 |
| inside_far_tp2 | XAUUSD | H1 | 0.30% | $33 | $2 | $0 | $35 |
| de_orb2.0_trNone_tp2.0_ex18 | DE40 | H1 | 0.30% | $216 | $190 | $59 | $406 |
| mon_long_h0_hold23 | EURJPY | H1 | 0.30% | $168 | $237 | $-22 | $405 |
| bos_hv_be1_M30 | XAUUSD | M30 | 0.30% | $245 | $207 | $-10 | $452 |
| vwap | DE40 | H1 | 0.30% | $-32 | $-7 | $-12 | $-39 |
| rsi_rev+trend | XAUUSD | H1 | 0.30% | $-1 | $63 | $0 | $62 |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 0.30% | $34 | $358 | $3 | $392 |
| spike_follow | BTCUSD | H1 | 0.30% | $269 | $391 | $-5 | $660 |
| tsmom_d1_lb40_a2 | BTCUSD | D1 | 0.30% | $0 | $0 | $0 | $0 |
| tsmom20_highvol | XBRUSD | D1 | 0.30% | $-35 | $105 | $0 | $70 |
| or_fail_fra40 | FRA40 | M30 | 0.30% | $-6 | $-15 | $-14 | $-20 |
| down_streak_k2_trend | US500 | D1 | 0.30% | $76 | $118 | $-27 | $193 |
| ibs_lo0.2_hi0.8 | US30 | D1 | 0.30% | $0 | $0 | $0 | $0 |
| rsi2_thresh10_sma5 | US500 | D1 | 0.30% | $26 | $90 | $5 | $116 |
| zmean_n100_adx25 | NZDUSD | H4 | 0.30% | $-44 | $169 | $-14 | $124 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | 0.30% | $-83 | $-238 | $-39 | $-322 |
| pa_engulf_UK100_H4 | UK100 | H4 | 0.30% | $39 | $-27 | $9 | $12 |
| pa_double_USDCAD_H1 | USDCAD | H1 | 0.30% | $-43 | $48 | $23 | $6 |
| pa_pin_DE40_D1 | DE40 | D1 | 0.30% | $-28 | $10 | $0 | $-17 |
| pa_bos_GBPJPY_D1 | GBPJPY | D1 | 0.30% | $28 | $30 | $0 | $57 |
| pa_inside_EURJPY_D1 | EURJPY | D1 | 0.30% | $-52 | $-222 | $-44 | $-274 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | 0.30% | $299 | $284 | $-61 | $583 |
| pa_bos_GBPAUD_D1 | GBPAUD | D1 | 0.30% | $5 | $48 | $0 | $53 |
| pa_double_USDJPY_H1 | USDJPY | H1 | 0.30% | $8 | $28 | $0 | $36 |

### Per-strategy profit inside 'strict', $5K account, exact replay

| strategy | market | tf | risk ($10K fraction) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|---|
| mon_long_h0_hold23 | EURJPY | H1 | 0.75% | $434 | $667 | $-55 | $1,101 |
| bos_hv_be1_M30 | XAUUSD | M30 | 0.75% | $437 | $1,218 | $-54 | $1,655 |
| tsmom_d1_lb40_a2 | BTCUSD | D1 | 0.75% | $283 | $67 | $0 | $350 |
| pa_bos_BTCUSD_D1 | BTCUSD | D1 | 0.75% | $-14 | $0 | $0 | $-14 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | 0.75% | $-202 | $-624 | $-100 | $-827 |
| pa_engulf_USDCAD_D1 | USDCAD | D1 | 0.75% | $-7 | $2 | $-34 | $-5 |
| pa_hikkake_ETHUSD_D1 | ETHUSD | D1 | 0.75% | $-199 | $95 | $-110 | $-104 |
| pa_double_USDCAD_H1 | USDCAD | H1 | 0.75% | $-100 | $112 | $57 | $12 |
| pa_pin_DE40_D1 | DE40 | D1 | 0.75% | $14 | $247 | $8 | $261 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | 0.75% | $758 | $723 | $-152 | $1,480 |

### Per-strategy profit inside 'pruned+adds', $5K account, exact replay

| strategy | market | tf | risk ($10K fraction) | unseen yr Oct23-Oct24 | last 2y Oct24-Oct26 (fit) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|---|
| bos_trail3_htfD50_H1 | XAUUSD | H1 | 1.00% | $348 | $2,022 | $-159 | $2,371 |
| bb_fade | EURUSD | H1 | 1.25% | $25 | $594 | $0 | $620 |
| monday_long_downweek | EURJPY | H1 | 0.75% | $380 | $543 | $-98 | $923 |
| zscore | US500 | H4 | 0.75% | $109 | $479 | $-39 | $589 |
| connors_rsi2_D1_ | EURCHF | D1 | 2.75% | $-95 | $428 | $32 | $333 |
| wd_MW_Th_a15 | BTCUSD | D1 | 1.00% | $383 | $777 | $50 | $1,161 |
| brent_wti_spread_z | XTIUSD | H4 | 0.50% | $50 | $804 | $7 | $854 |
| donchian160_h4 | XTIUSD | H4 | 1.00% | $-190 | $1,555 | $87 | $1,365 |
| rsi2_mr_aus200_h4 | AUS200 | H4 | 0.75% | $0 | $556 | $79 | $556 |
| prev_week_high_long_de40 | DE40 | M30 | 0.50% | $493 | $385 | $18 | $877 |
| us_open_fade_short_fra40 | FRA40 | M30 | 1.50% | $-45 | $908 | $-6 | $863 |
| rsi2_thresh10_sma5 | US500 | D1 | 1.25% | $179 | $676 | $29 | $855 |
| weekday_fri_to_mon | USTEC | D1 | 2.50% | $216 | $1,284 | $148 | $1,499 |
| round_big_bounce | USTEC | M30 | 0.75% | $-39 | $646 | $-9 | $607 |
| monday_gap_fade_gbpusd | GBPUSD | H1 | 2.50% | $55 | $1,278 | $67 | $1,333 |
| inside_day_break_usdchf | USDCHF | H4 | 1.00% | $277 | $555 | $-180 | $832 |
| friday_week_fade_eurusd | EURUSD | H1 | 2.00% | $-230 | $661 | $116 | $432 |
| tom_k0_h20_hold72_sl3 | DE40 | H1 | 0.50% | $31 | $-47 | $0 | $-17 |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | 0.50% | $-194 | $208 | $-23 | $14 |
| pweek_sl1_trail8 | DE40 | H1 | 0.50% | $106 | $19 | $0 | $125 |
| htf_bo50_n24 | XAUUSD | H1 | 0.50% | $50 | $636 | $-12 | $686 |
| dip_combo | US500 | D1 | 0.50% | $37 | $112 | $-12 | $149 |
| crabel_k0.5_None | DE40 | M30 | 0.50% | $276 | $650 | $-95 | $925 |
| inside_far_tp2 | XAUUSD | H1 | 0.50% | $14 | $109 | $0 | $123 |
| de_orb2.0_trNone_tp2.0_ex18 | DE40 | H1 | 0.50% | $458 | $186 | $72 | $645 |
| mon_long_h0_hold23 | EURJPY | H1 | 0.50% | $283 | $445 | $-38 | $729 |
| bos_hv_be1_M30 | XAUUSD | M30 | 0.50% | $313 | $556 | $-21 | $870 |
| vwap | DE40 | H1 | 0.50% | $-58 | $-88 | $-30 | $-146 |
| rsi_rev+trend | XAUUSD | H1 | 0.50% | $22 | $96 | $35 | $118 |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | 0.50% | $59 | $607 | $4 | $666 |
| spike_follow | BTCUSD | H1 | 0.50% | $539 | $631 | $-20 | $1,170 |
| tsmom_d1_lb40_a2 | BTCUSD | D1 | 0.50% | $115 | $-14 | $0 | $102 |
| tsmom20_highvol | XBRUSD | D1 | 0.50% | $-60 | $164 | $0 | $104 |
| or_fail_fra40 | FRA40 | M30 | 0.50% | $-107 | $75 | $-30 | $-32 |
| down_streak_k2_trend | US500 | D1 | 0.50% | $153 | $301 | $-12 | $454 |
| ibs_lo0.2_hi0.8 | US30 | D1 | 0.50% | $0 | $0 | $0 | $0 |
| zmean_n100_adx25 | NZDUSD | H4 | 0.50% | $-64 | $286 | $-22 | $222 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | 0.50% | $-136 | $-413 | $-66 | $-550 |
| pa_engulf_UK100_H4 | UK100 | H4 | 0.50% | $59 | $-170 | $17 | $-111 |
| pa_double_USDCAD_H1 | USDCAD | H1 | 0.50% | $-70 | $78 | $37 | $7 |
| pa_pin_DE40_D1 | DE40 | D1 | 0.50% | $-27 | $58 | $0 | $31 |
| pa_bos_GBPJPY_D1 | GBPJPY | D1 | 0.50% | $-1 | $-23 | $23 | $-25 |
| pa_inside_EURJPY_D1 | EURJPY | D1 | 0.50% | $-75 | $-218 | $-81 | $-293 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | 0.50% | $501 | $481 | $-101 | $982 |
| pa_bos_GBPAUD_D1 | GBPAUD | D1 | 0.50% | $-91 | $-9 | $-22 | $-100 |
| pa_double_USDJPY_H1 | USDJPY | H1 | 0.50% | $21 | $28 | $0 | $49 |
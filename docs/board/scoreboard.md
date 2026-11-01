# Scoreboard: every strategy judged on long history

349 strategies. dev = 2015..2023-10-20 (pick period), unseen yr = Oct 2023..Oct 2024, last 2y = Oct 2024..Oct 2026 (fit period for the round-3 pool and the live mixes), Sep+Oct = 2026. All $/month at 1% of $10K per trade; halve for $5K.

Pass the relaxed dev rule (4+ years, half green, dev > 0, 60+ trades): **43**. Strict (5+ years, 80% green): **12**.

| source | tested | relaxed | strict | profitable in unseen yr |
|---|---|---|---|---|
| round-3 pool | 80 | 9 | 1 | 26 |
| round-4 price action | 16 | 9 | 7 | 6 |
| round-5 time-of-day | 2 | 0 | 0 | 0 |
| round-6 YouTube | 114 | 5 | 2 | 23 |
| round-6 written | 71 | 5 | 0 | 21 |
| round1-2 live 66 | 66 | 15 | 2 | 30 |

## Relaxed-rule passers, ranked by dev $/month

| strategy | market | tf | source | dev yrs | green | dev $/mo | unseen yr | last 2y (fit?) | Sep+Oct | worst day 3y |
|---|---|---|---|---|---|---|---|---|---|---|
| tsmom_d1_lb40_a2 | BTCUSD | D1 | round-3 pool | 6 | 5.0 | 76 | 36 | 46 | -20 | -100 |
| mon_long_h0_hold23 | EURJPY | H1 | round1-2 live 66 | 5 | 4.0 | 56 | 98 | 76 | -81 | -100 |
| pa_inside_ETHUSD_D1 | ETHUSD | D1 | round-4 price action | 6 | 5.0 | 38 | -47 | -70 | -135 | -159 |
| yt76_us30_orb_demand_engulfing | US30 | M30 | round-6 YouTube | 5 | 3.0 | 36 | -41 | -7 | -187 | -221 |
| pa_engulf_UK100_H4 | UK100 | H4 | round-4 price action | 8 | 6.0 | 34 | 29 | -22 | 48 | -155 |
| monday_long_downweek | EURJPY | H1 | round1-2 live 66 | 5 | 3.0 | 31 | 87 | 62 | -142 | -213 |
| tom_k0_h20_hold72_sl3 | DE40 | H1 | round1-2 live 66 | 8 | 5.0 | 30 | 14 | 2 | -88 | -238 |
| pa_double_USDCAD_H1 | USDCAD | H1 | round-4 price action | 9 | 9.0 | 29 | -24 | 13 | 78 | -159 |
| pa_pin_ETHUSD_H4 | ETHUSD | H4 | round-4 price action | 6 | 5.0 | 28 | 159 | 80 | -207 | -306 |
| bb_breakout_H1_period250_dev2.75 | XAUUSD | H1 | round1-2 live 66 | 9 | 7.0 | 26 | -87 | 79 | 54 | -182 |
| pa_double_USDJPY_H1 | USDJPY | H1 | round-4 price action | 8 | 6.0 | 25 | -9 | 13 | 0 | -128 |
| vwap | DE40 | H1 | round1-2 live 66 | 8 | 6.0 | 24 | -20 | -22 | -66 | -196 |
| pa_pin_DE40_D1 | DE40 | D1 | round-4 price action | 8 | 7.0 | 23 | -2 | 30 | 30 | -123 |
| zscore | US500 | H4 | round1-2 live 66 | 8 | 5.0 | 19 | 29 | 55 | -51 | -183 |
| pa_inside_EURJPY_D1 | EURJPY | D1 | round-4 price action | 5 | 3.0 | 16 | -46 | -54 | -112 | -102 |
| tsmom20_highvol | XBRUSD | D1 | round-3 pool | 6 | 4.0 | 14 | -33 | 32 | 0 | -156 |
| dip_combo | US500 | D1 | round1-2 live 66 | 8 | 5.0 | 13 | 20 | 31 | -24 | -83 |
| yt80_us500_daily_dip_buy_marubozu | US500 | D1 | round-6 YouTube | 8 | 7.0 | 12 | 13 | -6 | 16 | -114 |
| pa_bos_GBPAUD_D1 | GBPAUD | D1 | round-4 price action | 9 | 7.0 | 12 | -36 | -0 | -19 | -72 |
| pa_bos_GBPJPY_D1 | GBPJPY | D1 | round-4 price action | 9 | 6.0 | 12 | 3 | -13 | 62 | -118 |
| yt56_gbpjpy_sr_engulfing_ema50_confluence | GBPJPY | H4 | round-6 YouTube | 8 | 7.0 | 12 | -2 | -3 | -48 | -146 |
| bos_hv_be1_M30 | XAUUSD | M30 | round1-2 live 66 | 5 | 4.0 | 11 | 92 | 164 | -210 | -273 |
| yt69_nzdusd_h4_structure_mirror_bars | NZDUSD | H4 | round-6 YouTube | 9 | 6.0 | 11 | 36 | -38 | -63 | -151 |
| pweek_sl1_trail8 | DE40 | H1 | round1-2 live 66 | 9 | 7.0 | 11 | 95 | 34 | -75 | -167 |
| crabel_k0.5_None | DE40 | M30 | round1-2 live 66 | 5 | 3.0 | 10 | 113 | 125 | -288 | -108 |
| zmean_n100_adx25 | NZDUSD | H4 | round-3 pool | 8 | 6.0 | 10 | -25 | 51 | -49 | -197 |
| squeeze_h4_a25_kc2 | ETHUSD | H4 | round-3 pool | 6 | 4.0 | 10 | 20 | 101 | 9 | -155 |
| yt130_tsg_bb_bounce_rsi_gbpusd_h4 | GBPUSD | H4 | round-6 written | 8 | 5.0 | 9 | 6 | -6 | -33 | -243 |
| rsi2_thresh10_sma5 | US500 | D1 | round-3 pool | 8 | 5.0 | 6 | 17 | 47 | 29 | -74 |
| bos_trail3_htfD50_H1 | XAUUSD | H1 | round1-2 live 66 | 8 | 5.0 | 6 | 86 | 241 | -231 | -210 |
| yt178_pin_bar_h4_xauusd | XAUUSD | H4 | round-6 written | 9 | 5.0 | 6 | -7 | 38 | 271 | -157 |
| ibs_lo0.2_hi0.8 | US30 | D1 | round-3 pool | 8 | 5.0 | 6 | 37 | 46 | 46 | -91 |
| spike_follow | BTCUSD | H1 | round-3 pool | 6 | 3.0 | 6 | 216 | 121 | 6 | -291 |
| down_streak_k2_trend | US500 | D1 | round-3 pool | 8 | 4.0 | 5 | 62 | 64 | -14 | -116 |
| yt141_earnforex_spike_trader_usdcad_d1 | USDCAD | D1 | round-6 written | 8 | 5.0 | 4 | 27 | -22 | -15 | -118 |
| inside_far_tp2 | XAUUSD | H1 | round1-2 live 66 | 9 | 6.0 | 4 | 18 | 70 | -55 | -175 |
| htf_bo50_n24 | XAUUSD | H1 | round1-2 live 66 | 8 | 4.0 | 4 | 27 | 234 | -53 | -210 |
| de_orb2.0_trNone_tp2.0_ex18 | DE40 | H1 | round1-2 live 66 | 8 | 4.0 | 3 | 163 | 62 | 167 | -100 |
| yt122_rsi2_strict_5_short_90 | US500 | D1 | round-6 written | 8 | 5.0 | 1 | 14 | 22 | 7 | -60 |
| yt113_gold_swing_resistance_break_h1 | XAUUSD | H1 | round-6 YouTube | 8 | 4.0 | 1 | 181 | 104 | -94 | -182 |
| or_fail_fra40 | FRA40 | M30 | round-3 pool | 4 | 2.0 | 1 | -31 | 25 | -44 | -100 |
| yt120_connors_rsi2_5_95_sp500 | US500 | D1 | round-6 written | 8 | 5.0 | 0 | 12 | 5 | 3 | -40 |
| rsi_rev+trend | XAUUSD | H1 | round1-2 live 66 | 9 | 5.0 | 0 | 20 | 17 | 88 | -217 |

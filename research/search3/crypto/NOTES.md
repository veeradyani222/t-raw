# Round 3 crypto group: BTCUSD ETHUSD XRPUSD LTCUSD SOLUSD ADAUSD BNBUSD DOTUSD (H1/H4/D1)

Judge: `research/prop/harness.py`, `PROP_OOS=1`, `H.load(sym, tf, split="oos")`, scoring 2024-10-20..2026-10-30
(XRPUSD / SOLUSD files start 2025-01-01, so they score on 22 months). best_risk = highest risk level with
worst day > -3% and max DD > -6%; a candidate = best_risk set and avg_month > 0; ranked by avg_month.

Files: `strategies.py` (27 build_* ideas), `batches.py` (config grids: screen / rerun / refine), `run.py` (Pool(2) scorer,
appends `results.jsonl`), `costs.py` (cost patches), `causal_check.py` + `causal.log` (look-ahead check),
`study.py` + `study.log` (market study + data quality), `report.py` -> `runs_table.md` (every scored run).

## Cost model used (costs.py)

Harness has no crypto entries, so `costs.apply()` monkeypatches before every score:

| symbol | spread floor (price units) | ~% of price | slippage pip (0.1 x pip per fill) |
|---|---|---|---|
| BTCUSD | 25 | 0.02% | 2.5 |
| ETHUSD | 2.0 | 0.05% | 0.2 |
| XRPUSD | 0.0045 | 0.3% | 0.00045 |
| LTCUSD | 0.25 | 0.3% | 0.025 |
| SOLUSD | 0.5 | 0.3% | 0.05 |
| ADAUSD | 0.002 | 0.3% | 0.0002 |
| BNBUSD | 2.0 | 0.3% | 0.2 |
| DOTUSD | 0.015 | 0.3% | 0.0015 |

All eight added to `H.INDICES` (no $14/lot commission). `simulate(max_lots)` lifted to 1e9 because XRPUSD's
vol_min (100 lots) is above the default cap; risk sizing still caps lots by the stop distance. Every entry's stop is
pushed to at least 4 x the spread floor (`MIN_STOP_SPREADS`), and in practice stops are 1-4 ATR (BTC H1 ATR ~ $400-900,
i.e. 15-35 spreads).

## Data quality (study.log, 2024-01-01..2026-10-30)

| symbol | H1 bars | H1 gaps >3 bars | zero-vol bars | flat days (range < 5% of median) | first bar |
|---|---|---|---|---|---|
| BTCUSD | 24742 | 6 | 0 | 0 | 2024-01-01 |
| ETHUSD | 24740 | 6 | 0 | 0 | 2024-01-01 |
| XRPUSD | 15967 | 5 | 0 | 0 | 2025-01-01 |
| LTCUSD | 24718 | 6 | 0 | 0 | 2024-01-01 |
| SOLUSD | 15962 | 6 | 0 | 0 | 2025-01-01 |
| ADAUSD | 24712 | 10 | 0 | 1 | 2024-01-01 |
| BNBUSD | 24686 | 11 | 0 | 0 | 2024-01-01 |
| DOTUSD | 24035 | 94 | 0 | 0 | 2024-01-01 |

H4/D1: no gaps except ADAUSD H4 (1), BNBUSD H4 (2), DOTUSD H4 (2); no zero-volume bars anywhere; one flat day
(ADAUSD). `run.clean()` drops all bars of any flat server day before scoring (1 day on ADAUSD, 0 elsewhere).
The H1 gaps are a handful of missing hours (IC Markets maintenance / feed hiccups); DOTUSD has ~700 missing H1 bars
spread over 94 gaps, which is why its intraday results should be read with caution. Server time is EET
(UTC+2/+3); hours below are server hours.

## Market study (study.log; scoring window 2024-10-20..2026-10-30, H1)

Hour of day (BTC, bp/hour mean, hourly vol): volatility is strongly US-session: 16:00-18:00 EET (= 13:00-15:00 UTC,
NYSE open) carries 71-76 bp hourly sd vs 33-36 bp at 12:00-14:00 and 36 bp at 07:00. ETH/SOL/XRP show the same shape
(ETH 93-107 bp at 16-18h vs 51-58 bp midday). Mean hourly returns are tiny relative to vol (BTC best hours 00:00 +4.4 bp,
23:00 +3.1 bp, 11:00 +3.3 bp; worst 21:00 -2.7 bp, 16:00 -2.0 bp), i.e. no hour-of-day drift worth trading on its own;
the hour-slice grid in `refine` confirms this.

Day of week (daily close-to-close, bp): BTC Mon +43 / Tue -18 / Wed +54 / Thu -63 / Fri +10 / Sat -10 / Sun -3;
ETH Mon +37 / Tue -32 / Wed +83 / Thu -90 / Fri +20 / Sat +7 / Sun -24; XRP Mon +58 / Tue -53 / Wed +34 / Thu -82 /
Fri +43. Thursday is negative on every one of the eight symbols except LTC (-25 bp) being the mildest; Monday and
Wednesday positive on BTC/ETH/XRP/SOL. This is the source of the `weekday` idea (long Mon+Wed, short Thu). Weekend
hourly vol is 55-60% of weekday vol on BTC/ETH (31 vs 53 bp BTC) and weekend drift is slightly negative.

Trend persistence vs mean reversion: return autocorrelation(1) is ~0 at H1/H4/D1 for BTC (-0.011 / -0.003 / +0.016)
and slightly positive at weekly (+0.088 BTC, +0.068 ETH); LTC/XRP are mildly mean-reverting at every horizon (LTC
-0.03..-0.06, XRP D1 -0.054). After an up day the next day is flat (BTC -0 bp, ETH +4 bp); after a down day
BTC +4 bp, LTC +13 bp. 20-day breakouts: BTC up-breakout -> 5d forward -29 bp (n=44), breakdown -112 bp (n=31);
ETH +27 / -164; XRP +200 / +54 (n=20/29); so breakouts have had follow-through only on the downside for BTC/ETH in
this window, which is why pure Donchian/TSMOM scored modestly and only at long lookbacks (40d).

Volatility regimes: after 5d/20d range compression < 0.7 the next 5-day absolute move is 322 bp (BTC) vs 432 bp after
expansion > 1.3; ETH 615 vs 468; LTC 506 vs 607. Compression does not reliably precede expansion on BTC in this window;
it does on ETH. Squeeze (BB inside Keltner) fared best on BTC H4 all the same because the ATR trail captured the Oct-24
to Jan-25 and Apr-25 to Jul-25 legs.

Session follow-through: corr(16-18h return, 19-23h return) = +0.04 BTC, +0.15 ETH, +0.09 XRP: a small positive
intraday momentum from the US open into the US afternoon (ETH strongest). Asia (02-09h) vs London (10-15h) correlation
is slightly negative (-0.01 .. -0.13), i.e. Asian range tends to be faded in London.

BTC-ETH lead/lag: contemporaneous H1 corr 0.82, BTC(t-1)->ETH(t) +0.006, ETH(t-1)->BTC(t) -0.004; ETH/BTC 5-day
relative strength vs next-24h ETH return -0.006. There is no exploitable hourly lead/lag, which the `relstr` and `lead`
grids confirm (best alt-vs-BTC run +1.9/mo).

## Practitioner / literature sources (web search 2026-10-30)

- Day-of-week: Korkmaz Kahraman & Kok 2024 (BTC/ETH: Thursday weak on ETH, highest vol Mondays); Yaya 2024 (no
  significant DoW effect in BTC returns); Sahu et al. 2024 (DoW effects appear post-2020). Mixed literature; our own
  window shows a clear Mon/Wed-up, Thu-down pattern so we tested it directly.
  https://doaj.org/article/a41888b96a204ce1a616f70491d8ac6c , https://mpra.ub.uni-muenchen.de/122529/1/MPRA_paper_122529.pdf ,
  https://ideas.repec.org/a/gam/jjrfmx/v17y2024i8p351-d1454951.html
- Weekend / overnight: Quantpedia "How to profitably trade Bitcoin's overnight sessions" and "Are there seasonal intraday
  or overnight anomalies in Bitcoin?" (overnight component carries the return on normal days; weekend effect exists but
  is time-varying). https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/ ,
  https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/
- US-session dominance: Kraken study via CryptoSlate (US hours 13:00-21:59 UTC = 50.6% of daily realized variance
  2022-2025; peak hour moves with NYSE clock). https://cryptoslate.com/crypto-never-closes-but-bitcoin-ethereum-xrp-and-solana-now-move-on-wall-street-time/
- Time-series momentum: Borgards 2021 "Dynamic time series momentum of cryptocurrencies" (momentum periods last longer
  than in US equities). https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000590
- Funding-rate cycle (perps settle 00/08/16 UTC) and Asian-range / prior-day-level / SFP rules are standard discretionary
  crypto-desk practice (ICT-style liquidity sweeps, Asia-range breakouts); coded as `funding_cycle`, `session_bo`,
  `pd_break`, `pw_sfp`.

## Ideas tested (27 build_* functions, see strategies.py docstring)

tsmom, donchian, compress_bo, weekend_bo, session_bo (Asian range), us_open_mom, weekday, overnight, pd_break (break /
SFP of prior-day levels), pw_sfp (prior-week sweep / break), pdc_revert, rsi2_mr, ema_pullback, squeeze, round_bounce,
weekly_open, rel_strength, vol_spike, day_orb, inside_day, supertrend, hour_slice, funding_cycle, btc_lead, nday_bo,
weekend_mr, pd_mom.

## Look-ahead check (causal.log)

`causal_check.py`: for every build_* (defaults) on ETHUSD H1 and BTCUSD D1, build(df) vs build(df.iloc[:k]) with attrs
re-attached, 5 random k in [n/3, n-10]; all Entries at index < k compared on side/sl/tp/max_hold/exit_hour.
Result: 0 mismatches for all 27 builds (54 checks). Builds that read the BTC csv (`rel_strength`, `btc_lead`) use
`merge_asof(direction="backward")`, so truncating the alt df cannot pull later BTC bars.

## Scoring summary

Batches: `screen` (700 configs, 21 ideas x 8 symbols), `rerun` (33 configs that had died with a pandas out-of-memory while
reading the csv during `screen`; all re-scored cleanly), `refine` (805 configs: weekday sweep of every single day long/short,
hour-slice grid, funding cycle, BTC-lead, n-day breakout, weekend MR, prior-day momentum, plus parameter refinements of the
screen winners). 1,503 distinct (name, symbol, tf) runs scored, 0 still errored, 388 qualify (best_risk set and avg_month > 0).

What the search says about this market, in plain words:
- The calendar is the strongest thing in crypto right now. Long Monday and Wednesday, short Thursday (full server day,
  2 x ATR stop) is the top idea on BTC, ETH and XRP on both D1 and H1; the single-day sweep confirms Thursday-short and
  Wednesday-long are the live legs on every major, Tuesday-short is positive but weaker, Sunday-long and Saturday-anything are
  flat or negative. Entering at 23:00 or 00:00 makes no difference; 12:00 entry is worse.
- Structure trades that work: prior-week high/low sweep-and-reclaim (SFP) with an ATR trail on SOL H4 (and positive on
  XRP/ETH), the squeeze (BB inside Keltner) on H4 for BTC/ETH/SOL/ADA, inside-day break with a trail on XRP H4, and
  following (not fading) a 3-ATR range bar on BTC H1 for 12 hours.
- Daily follow-through: at 23:00 if the day moved > 1 day-ATR from the prior close, hold that direction 24h (ETH +90/mo);
  the fade version loses. Multi-day breakouts (Donchian 55/20, n-day) are positive but with 10-17 trades in two years.
- Long-lookback TSMOM (40d) works on BTC/ETH/SOL D1; 10-20d does not, and H4 TSMOM is marginal.
- Things that do not work here: Asian-range breakout (negative on all 8), server-day ORB (flat), round-number fades,
  RSI(2) mean reversion, prior-day-close reversion, alt-vs-BTC relative strength and BTC-lead (no exploitable lead/lag),
  funding-cycle momentum (flat/negative), hour-of-day slices (best +13/mo), weekend range breakout (+16/mo at best),
  weekend fade (4 trades), supertrend flips (negative at every setting), US-open momentum (small, +44/mo at 0.25% risk).

## Candidates returned (8, distinct ideas or markets)

| # | name | symbol | tf | build_fn | params | best_risk | avg/mo | net | max DD | worst day | trades | exit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | wd_MW_Th_a15 | BTCUSD | D1 | build_weekday | {"atr_mult": 1.5} | 2.0% | 195.4 | 4885 | -585 | -198 | 318 | 1.5 ATR stop, time exit 1 day |
| 2 | weekday_MW_Th | ETHUSD | H1 | build_weekday | {} | 0.5% | 147.9 | 3698 | -498 | -50 | 318 | 2 ATR stop, time exit 24 bars |
| 3 | pw_h4_sfp_trail2 | SOLUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.5% | 101.1 | 2224 | -473 | -132 | 71 | stop under sweep low, 2 ATR chandelier trail |
| 4 | squeeze_h4_a25_kc2 | ETHUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 1.0% | 98.0 | 2449 | -522 | -156 | 45 | 2.5 ATR stop + chandelier trail |
| 5 | pdm_t10_h24 | ETHUSD | H1 | build_pd_mom | {"thresh": 1.0} | 1.0% | 89.7 | 2241 | -511 | -100 | 93 | 2 ATR stop, time exit 24 bars |
| 6 | spike_follow | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | 0.75% | 81.3 | 2032 | -572 | -137 | 207 | 1.5 ATR stop, 2R target, 12-bar time exit |
| 7 | tsmom_d1_lb40_a2 | BTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 1.5% | 80.4 | 2009 | -577 | -165 | 82 | 2 ATR chandelier trail, flips on sign change |
| 8 | inside_h4_trail | XRPUSD | H4 | build_inside_day | {"trail": true} | 0.75% | 47.3 | 1040 | -457 | -79 | 48 | 1 ATR stop + chandelier trail |

Notes on the picks: #1 at 2 x ATR (`weekday_d1_MW_Th`, same params minus atr_mult) makes 155/mo with a shallower -379 DD and
80% green months; the 1.5 ATR version ranks higher on avg_month but spends more of the DD budget. #2 is the same calendar
idea on ETH intraday (kept because the owner asked for distinct ideas OR markets; it is the only pick that is worst-day
-50 at its best risk). `overnight_thu00_S24` ETHUSD (+96/mo) is the Thursday-short leg alone and is subsumed by #1/#2.
`squeeze_h4` BTCUSD (+95/mo at 1.25%) and `pw_h4_sfp_trail15` SOLUSD (+89/mo) are parameter neighbours of #4 and #3.
XRPUSD and SOLUSD score on 22 months (data from 2025-01-01).

Best-risk caveat: best_risk is the highest risk level with worst day > -3% and max DD > -6% in this single two-year run;
max DD on most picks sits at -450..-585, i.e. close to the -600 ceiling, so these are sized at the edge of the rule and a
live book should run them a notch below best_risk (the `net_025` column in results.jsonl gives every run at 0.25%).

## Every scored run (from runs_table.md; regenerate with python -m research.search3.crypto.report)


| batch | name | symbol | tf | fn | params | best_risk | avg_month | net | max_dd | worst_day | trades | win | green |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rerun | asia_noTP_x23 | ADAUSD | H1 | build_session_bo | {"rr": null} | nan | -163.8 | -4094.3 | -4120.0 | -25.0 | 597.0 | 0.273 | 0.12 |
| rerun | asia_noTP_x23 | BNBUSD | H1 | build_session_bo | {"rr": null} | nan | -137.6 | -3440.3 | -3440.3 | -25.0 | 610.0 | 0.302 | 0.08 |
| screen | asia_noTP_x23 | DOTUSD | H1 | build_session_bo | {"rr": null} | nan | -232.3 | -5806.7 | -5867.8 | -76.7 | 586.0 | 0.183 | 0.04 |
| rerun | asia_noTP_x23 | LTCUSD | H1 | build_session_bo | {"rr": null} | nan | -317.7 | -7941.9 | -7963.3 | -25.0 | 607.0 | 0.158 | 0.0 |
| rerun | asia_noTP_x23 | SOLUSD | H1 | build_session_bo | {"rr": null} | nan | -137.1 | -3017.3 | -3145.2 | -25.0 | 553.0 | 0.3 | 0.136 |
| rerun | asia_noTP_x23 | XRPUSD | H1 | build_session_bo | {"rr": null} | nan | -119.9 | -2637.2 | -2789.0 | -25.0 | 566.0 | 0.297 | 0.273 |
| screen | asia_range_rr2 | ADAUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -73.5 | -1837.2 | -1976.1 | -30.4 | 412.0 | 0.33 | 0.2 |
| screen | asia_range_rr2 | BNBUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -97.1 | -2427.8 | -2488.3 | -25.0 | 610.0 | 0.346 | 0.08 |
| screen | asia_range_rr2 | BTCUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | 0.0025 | -12.6 | -314.7 | -545.9 | -24.9 | 528.0 | 0.432 | 0.36 |
| screen | asia_range_rr2 | DOTUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -128.3 | -3206.6 | -3229.7 | -44.9 | 438.0 | 0.269 | 0.16 |
| screen | asia_range_rr2 | ETHUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | 0.0025 | -4.4 | -110.4 | -342.7 | -25.0 | 598.0 | 0.428 | 0.56 |
| screen | asia_range_rr2 | LTCUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -237.9 | -5947.9 | -5980.6 | -33.3 | 586.0 | 0.189 | 0.0 |
| screen | asia_range_rr2 | SOLUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -86.6 | -1904.8 | -1941.1 | -25.0 | 550.0 | 0.375 | 0.136 |
| screen | asia_range_rr2 | XRPUSD | H1 | build_session_bo | {"stop": "range", "rr": 2.0} | nan | -77.9 | -1714.1 | -1771.7 | -25.0 | 557.0 | 0.393 | 0.136 |
| screen | asia_rr15 | ADAUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -145.2 | -3630.1 | -3640.5 | -25.0 | 526.0 | 0.409 | 0.04 |
| screen | asia_rr15 | BNBUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -150.6 | -3763.9 | -3763.9 | -25.0 | 603.0 | 0.459 | 0.0 |
| rerun | asia_rr15 | BTCUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -31.5 | -786.3 | -900.6 | -25.0 | 620.0 | 0.39 | 0.32 |
| rerun | asia_rr15 | DOTUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -75.2 | -1879.4 | -1903.6 | -69.4 | 317.0 | 0.429 | 0.08 |
| rerun | asia_rr15 | ETHUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -72.4 | -1811.2 | -2041.4 | -25.0 | 598.0 | 0.395 | 0.28 |
| rerun | asia_rr15 | LTCUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -151.2 | -3780.1 | -3784.7 | -25.0 | 316.0 | 0.348 | 0.0 |
| screen | asia_rr15 | SOLUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -138.5 | -3047.6 | -3091.2 | -25.0 | 545.0 | 0.431 | 0.136 |
| rerun | asia_rr15 | XRPUSD | H1 | build_session_bo | {"rr": 1.5} | nan | -150.3 | -3307.1 | -3353.9 | -25.0 | 566.0 | 0.417 | 0.045 |
| screen | asia_wk_rr15 | ADAUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -102.5 | -2563.2 | -2572.7 | -25.0 | 382.0 | 0.419 | 0.08 |
| screen | asia_wk_rr15 | BNBUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -127.9 | -3197.9 | -3197.9 | -25.0 | 434.0 | 0.424 | 0.04 |
| screen | asia_wk_rr15 | BTCUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -15.7 | -393.6 | -758.7 | -25.0 | 459.0 | 0.399 | 0.48 |
| screen | asia_wk_rr15 | DOTUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -61.5 | -1536.7 | -1544.6 | -25.0 | 231.0 | 0.411 | 0.08 |
| screen | asia_wk_rr15 | ETHUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -50.5 | -1262.7 | -1555.6 | -25.0 | 436.0 | 0.397 | 0.28 |
| screen | asia_wk_rr15 | LTCUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -115.8 | -2893.8 | -2898.4 | -25.0 | 242.0 | 0.355 | 0.0 |
| screen | asia_wk_rr15 | SOLUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -95.3 | -2096.5 | -2163.0 | -25.0 | 402.0 | 0.448 | 0.136 |
| screen | asia_wk_rr15 | XRPUSD | H1 | build_session_bo | {"rr": 1.5, "weekdays_only": true} | nan | -111.3 | -2448.6 | -2510.4 | -25.0 | 417.0 | 0.42 | 0.091 |
| screen | compress_d1_r07_rr2 | ADAUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.005 | -11.7 | -292.6 | -404.4 | -50.0 | 11.0 | 0.182 | 0.16 |
| screen | compress_d1_r07_rr2 | BNBUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0125 | 29.0 | 725.4 | -522.0 | -124.6 | 14.0 | 0.5 | 0.36 |
| screen | compress_d1_r07_rr2 | BTCUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.01 | -16.1 | -403.2 | -451.9 | -93.3 | 15.0 | 0.2 | 0.12 |
| screen | compress_d1_r07_rr2 | DOTUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0075 | -13.3 | -332.4 | -506.9 | -119.4 | 17.0 | 0.294 | 0.28 |
| screen | compress_d1_r07_rr2 | ETHUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0075 | -3.2 | -79.0 | -534.8 | -144.5 | 19.0 | 0.316 | 0.24 |
| screen | compress_d1_r07_rr2 | LTCUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.005 | -23.8 | -594.3 | -594.3 | -51.6 | 18.0 | 0.111 | 0.12 |
| screen | compress_d1_r07_rr2 | SOLUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.01 | 22.6 | 496.7 | -564.8 | -92.6 | 15.0 | 0.467 | 0.364 |
| screen | compress_d1_r07_rr2 | XRPUSD | D1 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.005 | -10.6 | -233.8 | -527.3 | -59.9 | 25.0 | 0.28 | 0.455 |
| screen | compress_h4_r07_rr2 | ADAUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | -10.8 | -269.6 | -554.2 | -43.0 | 64.0 | 0.359 | 0.4 |
| screen | compress_h4_r07_rr2 | BNBUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | -12.4 | -308.9 | -332.3 | -55.0 | 103.0 | 0.35 | 0.44 |
| screen | compress_h4_r07_rr2 | BTCUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | 10.0 | 250.8 | -295.5 | -54.0 | 125.0 | 0.36 | 0.56 |
| screen | compress_h4_r07_rr2 | DOTUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | -15.9 | -396.6 | -577.5 | -42.1 | 74.0 | 0.351 | 0.24 |
| screen | compress_h4_r07_rr2 | ETHUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | -14.9 | -371.8 | -527.0 | -54.0 | 100.0 | 0.3 | 0.32 |
| screen | compress_h4_r07_rr2 | LTCUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | nan | -36.7 | -917.2 | -992.3 | -41.5 | 92.0 | 0.293 | 0.24 |
| screen | compress_h4_r07_rr2 | SOLUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.0025 | 2.1 | 46.1 | -300.6 | -42.9 | 94.0 | 0.404 | 0.455 |
| screen | compress_h4_r07_rr2 | XRPUSD | H4 | build_compress_bo | {"ratio": 0.7, "rr": 2.0} | 0.005 | 30.4 | 668.5 | -579.7 | -104.9 | 96.0 | 0.438 | 0.682 |
| screen | compress_h4_r07_trail | ADAUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.0025 | -4.1 | -102.1 | -336.5 | -37.7 | 65.0 | 0.262 | 0.28 |
| screen | compress_h4_r07_trail | BNBUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.005 | -16.7 | -416.5 | -555.9 | -108.1 | 99.0 | 0.343 | 0.48 |
| screen | compress_h4_r07_trail | BTCUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.0025 | 20.9 | 522.7 | -301.1 | -54.5 | 122.0 | 0.336 | 0.64 |
| screen | compress_h4_r07_trail | DOTUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | nan | -23.5 | -587.8 | -732.5 | -38.2 | 80.0 | 0.237 | 0.16 |
| screen | compress_h4_r07_trail | ETHUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.0025 | -7.3 | -183.4 | -343.9 | -48.1 | 99.0 | 0.313 | 0.44 |
| screen | compress_h4_r07_trail | LTCUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | nan | -38.2 | -955.0 | -1064.6 | -41.5 | 95.0 | 0.158 | 0.16 |
| screen | compress_h4_r07_trail | SOLUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.005 | 22.7 | 500.5 | -405.5 | -90.4 | 93.0 | 0.344 | 0.364 |
| screen | compress_h4_r07_trail | XRPUSD | H4 | build_compress_bo | {"ratio": 0.7, "trail": true} | 0.0025 | 12.1 | 265.6 | -361.0 | -48.8 | 94.0 | 0.394 | 0.591 |
| screen | donch_d1_20_10 | ADAUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.005 | 21.8 | 543.9 | -425.2 | -195.8 | 12.0 | 0.333 | 0.16 |
| screen | donch_d1_20_10 | BNBUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.005 | -1.2 | -28.8 | -402.4 | -120.0 | 25.0 | 0.28 | 0.32 |
| rerun | donch_d1_20_10 | BTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.0075 | 9.1 | 226.8 | -461.8 | -83.0 | 23.0 | 0.348 | 0.44 |
| screen | donch_d1_20_10 | DOTUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.005 | -17.0 | -424.5 | -466.1 | -53.7 | 20.0 | 0.2 | 0.2 |
| rerun | donch_d1_20_10 | ETHUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.0075 | 6.4 | 160.9 | -511.2 | -138.1 | 28.0 | 0.357 | 0.44 |
| rerun | donch_d1_20_10 | LTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.0025 | -6.3 | -156.9 | -348.1 | -112.2 | 28.0 | 0.25 | 0.32 |
| screen | donch_d1_20_10 | SOLUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.01 | -2.9 | -64.8 | -530.1 | -118.8 | 23.0 | 0.391 | 0.409 |
| rerun | donch_d1_20_10 | XRPUSD | D1 | build_donchian | {"n": 20, "exit_n": 10} | 0.01 | -12.4 | -272.3 | -574.1 | -228.2 | 23.0 | 0.261 | 0.364 |
| screen | donch_d1_20_10_L | ADAUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.0075 | 33.3 | 831.8 | -549.0 | -293.7 | 8.0 | 0.25 | 0.08 |
| screen | donch_d1_20_10_L | BNBUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.0075 | 7.7 | 192.3 | -502.2 | -180.7 | 13.0 | 0.308 | 0.2 |
| screen | donch_d1_20_10_L | BTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.01 | 23.5 | 587.5 | -480.6 | -147.8 | 13.0 | 0.308 | 0.32 |
| screen | donch_d1_20_10_L | DOTUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.005 | -11.8 | -293.9 | -353.4 | -53.7 | 9.0 | 0.111 | 0.04 |
| screen | donch_d1_20_10_L | ETHUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.0075 | 0.1 | 2.9 | -523.5 | -138.1 | 15.0 | 0.333 | 0.16 |
| screen | donch_d1_20_10_L | LTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.005 | -1.0 | -24.9 | -437.8 | -224.4 | 12.0 | 0.333 | 0.2 |
| screen | donch_d1_20_10_L | SOLUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.01 | 4.4 | 96.8 | -504.2 | -118.8 | 11.0 | 0.455 | 0.227 |
| screen | donch_d1_20_10_L | XRPUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "long_only": true} | 0.01 | 4.3 | 95.5 | -578.6 | -228.2 | 9.0 | 0.222 | 0.091 |
| screen | donch_d1_20_10_a0 | ADAUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.01 | 24.1 | 603.0 | -523.2 | -208.2 | 15.0 | 0.333 | 0.16 |
| rerun | donch_d1_20_10_a0 | BNBUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.0075 | 1.4 | 35.7 | -463.0 | -144.0 | 24.0 | 0.292 | 0.32 |
| rerun | donch_d1_20_10_a0 | BTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.015 | 8.9 | 221.4 | -556.1 | -106.4 | 23.0 | 0.391 | 0.48 |
| screen | donch_d1_20_10_a0 | DOTUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.0075 | -16.4 | -410.8 | -490.5 | -74.3 | 19.0 | 0.263 | 0.16 |
| rerun | donch_d1_20_10_a0 | ETHUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.0125 | 1.0 | 24.5 | -519.5 | -113.4 | 28.0 | 0.357 | 0.44 |
| rerun | donch_d1_20_10_a0 | LTCUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.005 | -11.3 | -281.8 | -467.9 | -136.5 | 28.0 | 0.25 | 0.32 |
| screen | donch_d1_20_10_a0 | SOLUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.02 | 3.3 | 73.5 | -580.4 | -197.9 | 22.0 | 0.409 | 0.5 |
| screen | donch_d1_20_10_a0 | XRPUSD | D1 | build_donchian | {"n": 20, "exit_n": 10, "atr_mult": 0} | 0.0125 | -11.8 | -259.1 | -561.4 | -232.4 | 22.0 | 0.318 | 0.364 |
| refine | donch_d1_40_20 | ADAUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.005 | -5.6 | -140.0 | -259.8 | -47.8 | 8.0 | 0.25 | 0.04 |
| refine | donch_d1_40_20 | BNBUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.005 | 30.3 | 758.3 | -584.1 | -287.9 | 12.0 | 0.5 | 0.44 |
| refine | donch_d1_40_20 | BTCUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.0125 | 29.4 | 736.0 | -546.7 | -165.9 | 16.0 | 0.5 | 0.44 |
| refine | donch_d1_40_20 | DOTUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.005 | -10.6 | -264.1 | -326.2 | -39.5 | 12.0 | 0.167 | 0.2 |
| refine | donch_d1_40_20 | ETHUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.0125 | 62.5 | 1563.1 | -569.8 | -246.0 | 14.0 | 0.571 | 0.52 |
| refine | donch_d1_40_20 | LTCUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.005 | -10.4 | -258.8 | -586.8 | -218.4 | 16.0 | 0.25 | 0.28 |
| refine | donch_d1_40_20 | SOLUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.0075 | -0.6 | -14.0 | -442.4 | -136.5 | 14.0 | 0.357 | 0.364 |
| refine | donch_d1_40_20 | XRPUSD | D1 | build_donchian | {"n": 40, "exit_n": 20} | 0.0125 | 18.2 | 401.0 | -516.3 | -285.3 | 10.0 | 0.5 | 0.318 |
| rerun | donch_d1_55_20 | ADAUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.005 | -5.2 | -129.1 | -250.1 | -47.3 | 6.0 | 0.333 | 0.04 |
| rerun | donch_d1_55_20 | BNBUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.005 | 21.3 | 533.1 | -532.0 | -241.5 | 11.0 | 0.273 | 0.4 |
| screen | donch_d1_55_20 | BTCUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.015 | 49.9 | 1247.2 | -554.7 | -221.6 | 11.0 | 0.636 | 0.44 |
| rerun | donch_d1_55_20 | DOTUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.005 | -9.7 | -242.4 | -257.6 | -39.5 | 9.0 | 0.111 | 0.16 |
| rerun | donch_d1_55_20 | ETHUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.015 | 75.5 | 1886.9 | -527.4 | -298.4 | 11.0 | 0.727 | 0.48 |
| rerun | donch_d1_55_20 | LTCUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.0025 | -5.1 | -128.5 | -309.6 | -109.2 | 12.0 | 0.25 | 0.2 |
| screen | donch_d1_55_20 | SOLUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.01 | -5.0 | -110.3 | -528.9 | -178.5 | 11.0 | 0.273 | 0.182 |
| screen | donch_d1_55_20 | XRPUSD | D1 | build_donchian | {"n": 55, "exit_n": 20} | 0.0125 | 30.1 | 661.4 | -509.1 | -281.1 | 7.0 | 0.714 | 0.318 |
| refine | donch_d1_55_20_a3 | ADAUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.0075 | 20.2 | 505.8 | -383.4 | -273.5 | 5.0 | 0.8 | 0.12 |
| refine | donch_d1_55_20_a3 | BNBUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.0075 | 18.8 | 471.0 | -581.2 | -246.3 | 11.0 | 0.273 | 0.4 |
| refine | donch_d1_55_20_a3 | BTCUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.02 | 42.1 | 1051.5 | -352.6 | -165.9 | 10.0 | 0.7 | 0.4 |
| refine | donch_d1_55_20_a3 | DOTUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.0075 | -5.7 | -142.0 | -273.6 | -61.8 | 8.0 | 0.25 | 0.2 |
| refine | donch_d1_55_20_a3 | ETHUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.02 | 74.0 | 1850.5 | -492.9 | -266.9 | 10.0 | 0.8 | 0.48 |
| refine | donch_d1_55_20_a3 | LTCUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.0075 | -9.7 | -241.6 | -578.8 | -228.5 | 11.0 | 0.273 | 0.24 |
| refine | donch_d1_55_20_a3 | SOLUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.0125 | -2.4 | -53.1 | -489.9 | -157.5 | 10.0 | 0.3 | 0.182 |
| refine | donch_d1_55_20_a3 | XRPUSD | D1 | build_donchian | {"n": 55, "exit_n": 20, "atr_mult": 3.0} | 0.015 | 22.0 | 484.8 | -410.3 | -226.5 | 7.0 | 0.714 | 0.318 |
| screen | donch_h4_30_15 | ADAUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | 2.6 | 64.4 | -567.6 | -69.0 | 57.0 | 0.263 | 0.16 |
| screen | donch_h4_30_15 | BNBUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | -17.2 | -429.5 | -541.7 | -87.8 | 112.0 | 0.259 | 0.4 |
| screen | donch_h4_30_15 | BTCUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | 12.8 | 320.4 | -371.5 | -83.0 | 78.0 | 0.295 | 0.44 |
| screen | donch_h4_30_15 | DOTUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | nan | -21.4 | -534.4 | -681.6 | -41.7 | 85.0 | 0.282 | 0.24 |
| screen | donch_h4_30_15 | ETHUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | 23.3 | 583.4 | -380.9 | -70.8 | 99.0 | 0.343 | 0.56 |
| screen | donch_h4_30_15 | LTCUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | nan | -44.0 | -1100.8 | -1190.8 | -112.9 | 114.0 | 0.193 | 0.28 |
| screen | donch_h4_30_15 | SOLUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | 5.1 | 111.1 | -391.0 | -59.4 | 100.0 | 0.31 | 0.5 |
| screen | donch_h4_30_15 | XRPUSD | H4 | build_donchian | {"n": 30, "exit_n": 15} | 0.0025 | 10.7 | 234.9 | -500.4 | -117.6 | 93.0 | 0.28 | 0.364 |
| screen | donch_h4_60_15 | ADAUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.0025 | 2.4 | 59.2 | -450.4 | -69.0 | 43.0 | 0.279 | 0.12 |
| screen | donch_h4_60_15 | BNBUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | nan | -21.3 | -532.2 | -616.8 | -85.6 | 80.0 | 0.175 | 0.32 |
| screen | donch_h4_60_15 | BTCUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.0025 | 12.9 | 323.1 | -267.6 | -83.0 | 54.0 | 0.333 | 0.48 |
| screen | donch_h4_60_15 | DOTUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.0025 | -16.4 | -410.2 | -490.7 | -42.2 | 62.0 | 0.306 | 0.24 |
| screen | donch_h4_60_15 | ETHUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.005 | 31.4 | 784.8 | -555.3 | -102.0 | 68.0 | 0.353 | 0.52 |
| screen | donch_h4_60_15 | LTCUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | nan | -36.8 | -919.5 | -1037.9 | -112.9 | 83.0 | 0.181 | 0.24 |
| screen | donch_h4_60_15 | SOLUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.005 | 11.8 | 259.4 | -500.9 | -125.4 | 69.0 | 0.319 | 0.455 |
| screen | donch_h4_60_15 | XRPUSD | H4 | build_donchian | {"n": 60, "exit_n": 15} | 0.0025 | 9.6 | 212.0 | -322.4 | -117.6 | 66.0 | 0.318 | 0.364 |
| screen | emapb_d1_rr2 | ADAUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.01 | 6.7 | 167.9 | -451.8 | -135.4 | 30.0 | 0.4 | 0.48 |
| screen | emapb_d1_rr2 | BNBUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.01 | 43.9 | 1096.5 | -574.2 | -137.4 | 37.0 | 0.432 | 0.64 |
| screen | emapb_d1_rr2 | BTCUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.0075 | -5.5 | -137.9 | -545.2 | -73.9 | 34.0 | 0.294 | 0.4 |
| screen | emapb_d1_rr2 | DOTUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.0025 | -2.4 | -60.4 | -77.8 | -31.9 | 13.0 | 0.385 | 0.24 |
| screen | emapb_d1_rr2 | ETHUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.01 | 27.1 | 677.1 | -492.7 | -157.0 | 30.0 | 0.433 | 0.56 |
| screen | emapb_d1_rr2 | LTCUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.0075 | -5.7 | -142.8 | -522.5 | -118.7 | 36.0 | 0.361 | 0.44 |
| screen | emapb_d1_rr2 | SOLUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.015 | 13.4 | 295.4 | -577.1 | -169.6 | 25.0 | 0.36 | 0.591 |
| screen | emapb_d1_rr2 | XRPUSD | D1 | build_ema_pullback | {"fast": 10, "slow": 20, "trend": 50} | 0.0025 | -8.8 | -193.5 | -281.1 | -37.1 | 24.0 | 0.25 | 0.273 |
| screen | emapb_h4_rr2 | ADAUSD | H4 | build_ema_pullback | {} | 0.0025 | -12.8 | -319.6 | -414.4 | -50.1 | 93.0 | 0.387 | 0.28 |
| screen | emapb_h4_rr2 | BNBUSD | H4 | build_ema_pullback | {} | 0.0025 | -21.0 | -525.8 | -546.4 | -49.0 | 161.0 | 0.329 | 0.32 |
| screen | emapb_h4_rr2 | BTCUSD | H4 | build_ema_pullback | {} | 0.0025 | -12.7 | -318.2 | -571.5 | -50.1 | 127.0 | 0.307 | 0.52 |
| screen | emapb_h4_rr2 | DOTUSD | H4 | build_ema_pullback | {} | nan | -37.4 | -934.8 | -1076.5 | -51.0 | 115.0 | 0.33 | 0.32 |
| screen | emapb_h4_rr2 | ETHUSD | H4 | build_ema_pullback | {} | 0.0025 | 5.0 | 124.5 | -332.3 | -52.5 | 121.0 | 0.355 | 0.56 |
| screen | emapb_h4_rr2 | LTCUSD | H4 | build_ema_pullback | {} | nan | -63.5 | -1587.3 | -1616.2 | -66.0 | 146.0 | 0.281 | 0.12 |
| screen | emapb_h4_rr2 | SOLUSD | H4 | build_ema_pullback | {} | nan | -31.4 | -690.4 | -757.5 | -46.5 | 131.0 | 0.282 | 0.409 |
| screen | emapb_h4_rr2 | XRPUSD | H4 | build_ema_pullback | {} | 0.0025 | -0.4 | -8.9 | -417.6 | -62.2 | 127.0 | 0.37 | 0.591 |
| screen | emapb_h4_trail | ADAUSD | H4 | build_ema_pullback | {"trail": true} | 0.0025 | -13.4 | -336.1 | -462.4 | -45.3 | 134.0 | 0.291 | 0.24 |
| screen | emapb_h4_trail | BNBUSD | H4 | build_ema_pullback | {"trail": true} | nan | -24.4 | -610.6 | -777.6 | -49.0 | 240.0 | 0.292 | 0.4 |
| screen | emapb_h4_trail | BTCUSD | H4 | build_ema_pullback | {"trail": true} | 0.0025 | -1.5 | -38.0 | -351.7 | -37.3 | 181.0 | 0.309 | 0.36 |
| screen | emapb_h4_trail | DOTUSD | H4 | build_ema_pullback | {"trail": true} | nan | -46.8 | -1171.2 | -1299.2 | -45.0 | 169.0 | 0.225 | 0.24 |
| screen | emapb_h4_trail | ETHUSD | H4 | build_ema_pullback | {"trail": true} | 0.0025 | 25.6 | 641.2 | -312.9 | -48.4 | 219.0 | 0.315 | 0.48 |
| screen | emapb_h4_trail | LTCUSD | H4 | build_ema_pullback | {"trail": true} | nan | -84.0 | -2100.3 | -2100.3 | -50.0 | 237.0 | 0.228 | 0.12 |
| screen | emapb_h4_trail | SOLUSD | H4 | build_ema_pullback | {"trail": true} | nan | -17.2 | -377.8 | -715.0 | -45.4 | 202.0 | 0.292 | 0.455 |
| screen | emapb_h4_trail | XRPUSD | H4 | build_ema_pullback | {"trail": true} | 0.0025 | 2.5 | 54.8 | -303.6 | -45.1 | 174.0 | 0.368 | 0.455 |
| refine | fund_t05_h4_a1 | ADAUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -328.9 | -8222.6 | -8224.6 | -75.0 | 1582.0 | 0.268 | 0.08 |
| refine | fund_t05_h4_a1 | BNBUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -361.4 | -9034.9 | -9066.3 | -74.9 | 1731.0 | 0.298 | 0.0 |
| refine | fund_t05_h4_a1 | BTCUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -88.2 | -2204.2 | -3088.7 | -71.6 | 1652.0 | 0.41 | 0.36 |
| refine | fund_t05_h4_a1 | DOTUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -513.7 | -12842.1 | -12843.6 | -74.9 | 1596.0 | 0.197 | 0.08 |
| refine | fund_t05_h4_a1 | ETHUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -135.3 | -3381.8 | -3565.0 | -74.9 | 1597.0 | 0.397 | 0.24 |
| refine | fund_t05_h4_a1 | LTCUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -788.3 | -19708.2 | -19708.2 | -75.0 | 1689.0 | 0.127 | 0.0 |
| refine | fund_t05_h4_a1 | SOLUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -311.1 | -6844.8 | -7098.3 | -70.0 | 1554.0 | 0.301 | 0.091 |
| refine | fund_t05_h4_a1 | XRPUSD | H1 | build_funding_cycle | {"hold": 4, "atr_mult": 1.0} | nan | -355.1 | -7812.5 | -7812.8 | -75.0 | 1498.0 | 0.327 | 0.045 |
| refine | fund_t05_h8 | ADAUSD | H1 | build_funding_cycle | {} | nan | -288.6 | -7215.8 | -7227.3 | -93.7 | 1439.0 | 0.297 | 0.08 |
| refine | fund_t05_h8 | BNBUSD | H1 | build_funding_cycle | {} | nan | -324.3 | -8107.0 | -8123.8 | -87.6 | 1730.0 | 0.349 | 0.0 |
| refine | fund_t05_h8 | BTCUSD | H1 | build_funding_cycle | {} | nan | -60.3 | -1507.5 | -2094.3 | -100.2 | 1647.0 | 0.4 | 0.4 |
| refine | fund_t05_h8 | DOTUSD | H1 | build_funding_cycle | {} | nan | -488.1 | -12203.4 | -12265.8 | -88.5 | 1541.0 | 0.215 | 0.12 |
| refine | fund_t05_h8 | ETHUSD | H1 | build_funding_cycle | {} | nan | -97.0 | -2424.2 | -2749.5 | -95.5 | 1595.0 | 0.4 | 0.36 |
| refine | fund_t05_h8 | LTCUSD | H1 | build_funding_cycle | {} | nan | -738.3 | -18457.7 | -18457.7 | -86.8 | 1687.0 | 0.186 | 0.0 |
| refine | fund_t05_h8 | SOLUSD | H1 | build_funding_cycle | {} | nan | -277.3 | -6101.4 | -6385.3 | -88.8 | 1553.0 | 0.352 | 0.091 |
| refine | fund_t05_h8 | XRPUSD | H1 | build_funding_cycle | {} | nan | -272.7 | -5999.1 | -5999.1 | -98.8 | 1494.0 | 0.362 | 0.182 |
| refine | fund_t05_h8_fade | ADAUSD | H1 | build_funding_cycle | {"fade": true} | nan | -290.1 | -7251.3 | -7317.7 | -80.9 | 1439.0 | 0.319 | 0.08 |
| refine | fund_t05_h8_fade | BNBUSD | H1 | build_funding_cycle | {"fade": true} | nan | -374.4 | -9359.9 | -9375.7 | -109.9 | 1731.0 | 0.355 | 0.0 |
| refine | fund_t05_h8_fade | BTCUSD | H1 | build_funding_cycle | {"fade": true} | nan | -40.3 | -1008.6 | -1326.2 | -91.2 | 1647.0 | 0.445 | 0.32 |
| refine | fund_t05_h8_fade | DOTUSD | H1 | build_funding_cycle | {"fade": true} | nan | -496.7 | -12418.6 | -12439.9 | -119.4 | 1547.0 | 0.211 | 0.04 |
| refine | fund_t05_h8_fade | ETHUSD | H1 | build_funding_cycle | {"fade": true} | nan | -206.8 | -5169.0 | -5410.7 | -128.4 | 1597.0 | 0.412 | 0.2 |
| refine | fund_t05_h8_fade | LTCUSD | H1 | build_funding_cycle | {"fade": true} | nan | -732.5 | -18311.9 | -18384.0 | -123.1 | 1688.0 | 0.185 | 0.0 |
| refine | fund_t05_h8_fade | SOLUSD | H1 | build_funding_cycle | {"fade": true} | nan | -263.3 | -5792.4 | -5908.6 | -91.3 | 1554.0 | 0.383 | 0.091 |
| refine | fund_t05_h8_fade | XRPUSD | H1 | build_funding_cycle | {"fade": true} | nan | -286.4 | -6301.9 | -6545.8 | -95.4 | 1496.0 | 0.397 | 0.045 |
| refine | fund_t10_h8 | ADAUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -198.9 | -4971.5 | -5167.2 | -81.8 | 1028.0 | 0.293 | 0.16 |
| refine | fund_t10_h8 | BNBUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -258.6 | -6465.3 | -6472.9 | -83.3 | 1261.0 | 0.337 | 0.0 |
| refine | fund_t10_h8 | BTCUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -40.6 | -1014.8 | -1423.9 | -74.0 | 1165.0 | 0.397 | 0.44 |
| refine | fund_t10_h8 | DOTUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -331.2 | -8278.8 | -8311.4 | -84.3 | 1093.0 | 0.23 | 0.12 |
| refine | fund_t10_h8 | ETHUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -65.9 | -1646.5 | -2235.6 | -95.5 | 1103.0 | 0.396 | 0.36 |
| refine | fund_t10_h8 | LTCUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -540.2 | -13505.1 | -13505.1 | -85.7 | 1196.0 | 0.176 | 0.0 |
| refine | fund_t10_h8 | SOLUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -197.0 | -4335.0 | -4538.9 | -87.3 | 1101.0 | 0.351 | 0.045 |
| refine | fund_t10_h8 | XRPUSD | H1 | build_funding_cycle | {"thresh": 1.0} | nan | -176.6 | -3885.8 | -3885.8 | -96.3 | 1068.0 | 0.362 | 0.182 |
| refine | fund_t10_h8_fade | ADAUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -215.5 | -5388.0 | -5450.1 | -80.9 | 1028.0 | 0.315 | 0.04 |
| refine | fund_t10_h8_fade | BNBUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -277.5 | -6936.5 | -6998.3 | -109.9 | 1262.0 | 0.355 | 0.04 |
| refine | fund_t10_h8_fade | BTCUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -39.1 | -978.2 | -1560.6 | -86.3 | 1165.0 | 0.438 | 0.28 |
| refine | fund_t10_h8_fade | DOTUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -358.5 | -8962.8 | -8984.1 | -81.1 | 1098.0 | 0.209 | 0.08 |
| refine | fund_t10_h8_fade | ETHUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -150.3 | -3756.7 | -4012.3 | -94.0 | 1104.0 | 0.416 | 0.16 |
| refine | fund_t10_h8_fade | LTCUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -495.4 | -12385.5 | -12452.8 | -98.1 | 1196.0 | 0.2 | 0.0 |
| refine | fund_t10_h8_fade | SOLUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -200.3 | -4406.3 | -4522.6 | -82.1 | 1101.0 | 0.376 | 0.045 |
| refine | fund_t10_h8_fade | XRPUSD | H1 | build_funding_cycle | {"thresh": 1.0, "fade": true} | nan | -240.6 | -5292.4 | -5482.4 | -87.4 | 1070.0 | 0.393 | 0.0 |
| refine | hs_L0_h12_we | ADAUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -46.5 | -1162.4 | -1261.1 | -25.0 | 167.0 | 0.251 | 0.08 |
| refine | hs_L0_h12_we | BNBUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -20.6 | -514.0 | -651.8 | -25.7 | 204.0 | 0.407 | 0.4 |
| refine | hs_L0_h12_we | BTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | 0.0025 | -5.8 | -144.6 | -291.6 | -25.0 | 203.0 | 0.488 | 0.48 |
| refine | hs_L0_h12_we | DOTUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -60.2 | -1504.2 | -1609.2 | -25.0 | 146.0 | 0.103 | 0.08 |
| refine | hs_L0_h12_we | ETHUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -23.7 | -593.5 | -646.3 | -25.0 | 206.0 | 0.417 | 0.4 |
| refine | hs_L0_h12_we | LTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -81.3 | -2032.7 | -2042.5 | -25.0 | 193.0 | 0.15 | 0.0 |
| refine | hs_L0_h12_we | SOLUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | nan | -31.3 | -688.1 | -717.8 | -24.9 | 181.0 | 0.359 | 0.182 |
| refine | hs_L0_h12_we | XRPUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 12, "days": [5, 6]} | 0.0025 | -18.8 | -412.9 | -424.2 | -25.0 | 183.0 | 0.421 | 0.318 |
| refine | hs_L0_h24 | ADAUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -127.2 | -3180.5 | -3409.9 | -46.3 | 569.0 | 0.309 | 0.12 |
| refine | hs_L0_h24 | BNBUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -106.4 | -2661.1 | -2696.9 | -38.3 | 728.0 | 0.375 | 0.2 |
| refine | hs_L0_h24 | BTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | 13.2 | 330.1 | -795.8 | -35.9 | 709.0 | 0.413 | 0.6 |
| refine | hs_L0_h24 | DOTUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -216.0 | -5399.2 | -5613.4 | -41.7 | 624.0 | 0.223 | 0.08 |
| refine | hs_L0_h24 | ETHUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | 12.7 | 317.0 | -908.8 | -51.9 | 730.0 | 0.414 | 0.48 |
| refine | hs_L0_h24 | LTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -294.3 | -7357.5 | -7358.0 | -209.1 | 718.0 | 0.237 | 0.04 |
| refine | hs_L0_h24 | SOLUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -105.1 | -2312.7 | -2461.5 | -45.4 | 653.0 | 0.355 | 0.227 |
| refine | hs_L0_h24 | XRPUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 24} | nan | -122.9 | -2703.0 | -2820.5 | -43.6 | 653.0 | 0.354 | 0.227 |
| refine | hs_L0_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 8} | nan | -15.2 | -379.0 | -638.0 | -25.0 | 714.0 | 0.459 | 0.32 |
| refine | hs_L0_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 0, "side": "long", "hold": 8} | nan | -42.7 | -1067.3 | -1235.8 | -25.0 | 735.0 | 0.448 | 0.28 |
| refine | hs_L10_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 10, "side": "long", "hold": 8} | nan | -1.7 | -41.5 | -788.4 | -25.0 | 726.0 | 0.45 | 0.48 |
| refine | hs_L10_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 10, "side": "long", "hold": 8} | nan | -55.6 | -1390.0 | -1516.3 | -25.0 | 738.0 | 0.424 | 0.24 |
| refine | hs_L14_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 14, "side": "long", "hold": 8} | nan | -25.8 | -645.0 | -998.0 | -25.0 | 730.0 | 0.441 | 0.44 |
| refine | hs_L14_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 14, "side": "long", "hold": 8} | nan | -55.2 | -1380.1 | -1553.2 | -28.5 | 739.0 | 0.424 | 0.32 |
| refine | hs_L16_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8} | 0.0025 | 4.1 | 102.9 | -499.8 | -51.5 | 726.0 | 0.492 | 0.44 |
| refine | hs_L16_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8} | nan | -10.2 | -255.3 | -601.0 | -49.8 | 738.0 | 0.472 | 0.44 |
| refine | hs_L16_h8_wk | ADAUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -77.5 | -1936.5 | -2023.3 | -56.2 | 408.0 | 0.348 | 0.12 |
| refine | hs_L16_h8_wk | BNBUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -74.6 | -1864.3 | -1875.3 | -38.5 | 529.0 | 0.425 | 0.12 |
| refine | hs_L16_h8_wk | BTCUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | 0.0025 | 3.2 | 79.0 | -435.1 | -37.7 | 517.0 | 0.487 | 0.52 |
| refine | hs_L16_h8_wk | DOTUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -153.6 | -3840.2 | -3840.2 | -37.8 | 489.0 | 0.217 | 0.12 |
| refine | hs_L16_h8_wk | ETHUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -14.0 | -351.2 | -616.3 | -45.6 | 529.0 | 0.456 | 0.4 |
| refine | hs_L16_h8_wk | LTCUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -194.1 | -4851.8 | -4855.0 | -39.0 | 529.0 | 0.238 | 0.0 |
| refine | hs_L16_h8_wk | SOLUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -73.7 | -1622.4 | -1639.4 | -41.1 | 477.0 | 0.384 | 0.136 |
| refine | hs_L16_h8_wk | XRPUSD | H1 | build_hour_slice | {"hour": 16, "side": "long", "hold": 8, "days": [0, 1, 2, 3, 4]} | nan | -77.4 | -1703.4 | -1828.1 | -45.2 | 476.0 | 0.384 | 0.227 |
| refine | hs_L18_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 18, "side": "long", "hold": 8} | nan | -19.0 | -474.7 | -645.0 | -50.0 | 718.0 | 0.471 | 0.28 |
| refine | hs_L18_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 18, "side": "long", "hold": 8} | nan | -47.4 | -1183.9 | -1237.0 | -61.7 | 737.0 | 0.448 | 0.32 |
| refine | hs_L20_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 20, "side": "long", "hold": 8} | 0.0025 | -11.7 | -292.5 | -431.4 | -58.1 | 718.0 | 0.46 | 0.36 |
| refine | hs_L20_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 20, "side": "long", "hold": 8} | nan | -45.7 | -1141.4 | -1175.9 | -65.5 | 738.0 | 0.443 | 0.28 |
| refine | hs_L22_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 22, "side": "long", "hold": 8} | 0.0025 | 0.5 | 13.4 | -448.4 | -54.7 | 716.0 | 0.461 | 0.52 |
| refine | hs_L22_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 22, "side": "long", "hold": 8} | nan | -28.7 | -717.7 | -1020.7 | -58.9 | 739.0 | 0.453 | 0.32 |
| refine | hs_L2_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 2, "side": "long", "hold": 8} | 0.0025 | -12.6 | -315.9 | -505.8 | -24.9 | 718.0 | 0.485 | 0.36 |
| refine | hs_L2_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 2, "side": "long", "hold": 8} | nan | -49.2 | -1230.5 | -1336.3 | -25.0 | 739.0 | 0.471 | 0.28 |
| refine | hs_L8_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 8, "side": "long", "hold": 8} | nan | -21.4 | -533.9 | -815.5 | -25.0 | 725.0 | 0.461 | 0.32 |
| refine | hs_L8_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 8, "side": "long", "hold": 8} | nan | -74.5 | -1861.9 | -1942.3 | -30.7 | 739.0 | 0.414 | 0.2 |
| refine | hs_S0_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 0, "side": "short", "hold": 8} | 0.0025 | -5.9 | -148.0 | -427.7 | -25.0 | 714.0 | 0.458 | 0.4 |
| refine | hs_S0_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 0, "side": "short", "hold": 8} | nan | -36.3 | -908.2 | -1117.8 | -25.0 | 735.0 | 0.437 | 0.32 |
| refine | hs_S10_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 10, "side": "short", "hold": 8} | 0.0025 | -20.1 | -503.0 | -594.8 | -25.0 | 726.0 | 0.437 | 0.32 |
| refine | hs_S10_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 10, "side": "short", "hold": 8} | nan | -38.6 | -965.6 | -1228.4 | -25.0 | 738.0 | 0.447 | 0.36 |
| refine | hs_S14_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 14, "side": "short", "hold": 8} | 0.0025 | 13.5 | 337.6 | -502.4 | -25.0 | 730.0 | 0.425 | 0.56 |
| refine | hs_S14_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 14, "side": "short", "hold": 8} | nan | -2.8 | -69.9 | -873.9 | -59.4 | 739.0 | 0.447 | 0.56 |
| refine | hs_S16_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 16, "side": "short", "hold": 8} | nan | -42.2 | -1054.2 | -1152.7 | -62.9 | 726.0 | 0.434 | 0.4 |
| refine | hs_S16_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 16, "side": "short", "hold": 8} | nan | -51.6 | -1290.9 | -1562.7 | -44.2 | 738.0 | 0.402 | 0.28 |
| refine | hs_S18_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 18, "side": "short", "hold": 8} | nan | -30.2 | -756.0 | -829.7 | -72.8 | 718.0 | 0.428 | 0.32 |
| refine | hs_S18_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 18, "side": "short", "hold": 8} | nan | -56.6 | -1413.8 | -1546.8 | -72.5 | 737.0 | 0.403 | 0.2 |
| refine | hs_S20_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 20, "side": "short", "hold": 8} | nan | -21.0 | -524.4 | -608.9 | -61.8 | 718.0 | 0.448 | 0.36 |
| refine | hs_S20_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 20, "side": "short", "hold": 8} | nan | -47.7 | -1192.5 | -1253.8 | -61.4 | 738.0 | 0.419 | 0.28 |
| refine | hs_S22_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 22, "side": "short", "hold": 8} | 0.0025 | -16.7 | -418.2 | -599.2 | -52.6 | 716.0 | 0.447 | 0.44 |
| refine | hs_S22_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 22, "side": "short", "hold": 8} | nan | -64.7 | -1617.7 | -1754.4 | -58.9 | 739.0 | 0.41 | 0.32 |
| refine | hs_S2_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 2, "side": "short", "hold": 8} | 0.0025 | -8.8 | -219.2 | -372.1 | -24.9 | 718.0 | 0.451 | 0.32 |
| refine | hs_S2_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 2, "side": "short", "hold": 8} | nan | -55.3 | -1382.4 | -1514.6 | -25.0 | 739.0 | 0.399 | 0.24 |
| refine | hs_S8_h8 | BTCUSD | H1 | build_hour_slice | {"hour": 8, "side": "short", "hold": 8} | 0.0025 | -1.2 | -28.8 | -325.2 | -25.0 | 725.0 | 0.479 | 0.44 |
| refine | hs_S8_h8 | ETHUSD | H1 | build_hour_slice | {"hour": 8, "side": "short", "hold": 8} | nan | -30.5 | -763.2 | -921.8 | -25.0 | 739.0 | 0.457 | 0.4 |
| screen | inside_d1_trail | ADAUSD | D1 | build_inside_day | {"trail": true} | 0.01 | 5.1 | 127.9 | -582.8 | -150.1 | 30.0 | 0.333 | 0.36 |
| screen | inside_d1_trail | BNBUSD | D1 | build_inside_day | {"trail": true} | 0.0075 | 26.9 | 672.0 | -528.5 | -102.3 | 32.0 | 0.469 | 0.4 |
| screen | inside_d1_trail | BTCUSD | D1 | build_inside_day | {"trail": true} | 0.01 | 13.3 | 333.0 | -562.4 | -87.3 | 31.0 | 0.226 | 0.32 |
| screen | inside_d1_trail | DOTUSD | D1 | build_inside_day | {"trail": true} | 0.005 | -12.1 | -303.2 | -422.3 | -46.6 | 23.0 | 0.304 | 0.28 |
| screen | inside_d1_trail | ETHUSD | D1 | build_inside_day | {"trail": true} | 0.005 | 1.0 | 24.9 | -477.4 | -52.2 | 36.0 | 0.333 | 0.28 |
| screen | inside_d1_trail | LTCUSD | D1 | build_inside_day | {"trail": true} | 0.005 | -18.0 | -450.9 | -538.5 | -60.8 | 33.0 | 0.242 | 0.32 |
| screen | inside_d1_trail | SOLUSD | D1 | build_inside_day | {"trail": true} | 0.0075 | 0.4 | 8.3 | -470.9 | -74.3 | 24.0 | 0.333 | 0.364 |
| screen | inside_d1_trail | XRPUSD | D1 | build_inside_day | {"trail": true} | 0.0075 | 34.0 | 748.3 | -456.0 | -126.9 | 29.0 | 0.448 | 0.545 |
| screen | inside_h1_rr2 | ADAUSD | H1 | build_inside_day | {} | 0.0025 | -14.6 | -366.1 | -484.0 | -41.7 | 55.0 | 0.364 | 0.24 |
| screen | inside_h1_rr2 | BNBUSD | H1 | build_inside_day | {} | 0.005 | -7.3 | -182.5 | -469.7 | -95.1 | 68.0 | 0.412 | 0.44 |
| screen | inside_h1_rr2 | BTCUSD | H1 | build_inside_day | {} | 0.005 | -0.0 | -0.9 | -577.4 | -82.2 | 59.0 | 0.339 | 0.48 |
| screen | inside_h1_rr2 | DOTUSD | H1 | build_inside_day | {} | 0.0025 | -1.8 | -44.3 | -325.2 | -40.1 | 42.0 | 0.5 | 0.28 |
| screen | inside_h1_rr2 | ETHUSD | H1 | build_inside_day | {} | 0.0025 | -12.0 | -300.9 | -463.7 | -55.7 | 65.0 | 0.292 | 0.2 |
| screen | inside_h1_rr2 | LTCUSD | H1 | build_inside_day | {} | nan | -25.4 | -635.4 | -678.3 | -34.0 | 55.0 | 0.327 | 0.16 |
| screen | inside_h1_rr2 | SOLUSD | H1 | build_inside_day | {} | 0.0025 | -10.5 | -232.0 | -477.5 | -38.0 | 50.0 | 0.34 | 0.318 |
| screen | inside_h1_rr2 | XRPUSD | H1 | build_inside_day | {} | 0.005 | -3.9 | -86.8 | -458.7 | -68.0 | 59.0 | 0.407 | 0.409 |
| screen | inside_h4_rr2 | ADAUSD | H4 | build_inside_day | {} | 0.0025 | -3.3 | -83.0 | -230.6 | -37.1 | 22.0 | 0.364 | 0.2 |
| screen | inside_h4_rr2 | BNBUSD | H4 | build_inside_day | {} | 0.0075 | 6.3 | 156.6 | -496.5 | -169.9 | 57.0 | 0.386 | 0.48 |
| screen | inside_h4_rr2 | BTCUSD | H4 | build_inside_day | {} | 0.005 | -15.5 | -387.5 | -522.7 | -88.6 | 53.0 | 0.283 | 0.36 |
| screen | inside_h4_rr2 | DOTUSD | H4 | build_inside_day | {} | 0.0025 | -13.8 | -344.9 | -419.7 | -42.2 | 32.0 | 0.281 | 0.28 |
| screen | inside_h4_rr2 | ETHUSD | H4 | build_inside_day | {} | 0.0025 | -11.8 | -295.1 | -358.3 | -42.1 | 56.0 | 0.268 | 0.28 |
| screen | inside_h4_rr2 | LTCUSD | H4 | build_inside_day | {} | 0.0025 | -11.6 | -290.1 | -374.6 | -36.4 | 44.0 | 0.318 | 0.32 |
| screen | inside_h4_rr2 | SOLUSD | H4 | build_inside_day | {} | 0.0025 | -12.3 | -271.6 | -422.2 | -37.9 | 44.0 | 0.273 | 0.273 |
| screen | inside_h4_rr2 | XRPUSD | H4 | build_inside_day | {} | 0.005 | 2.1 | 46.2 | -455.7 | -113.4 | 45.0 | 0.4 | 0.545 |
| refine | inside_h4_rr3 | ADAUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -2.5 | -61.4 | -207.8 | -35.0 | 20.0 | 0.3 | 0.2 |
| refine | inside_h4_rr3 | BNBUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0075 | 12.2 | 304.2 | -525.7 | -169.9 | 52.0 | 0.327 | 0.56 |
| refine | inside_h4_rr3 | BTCUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -11.0 | -275.6 | -368.5 | -44.3 | 38.0 | 0.211 | 0.2 |
| refine | inside_h4_rr3 | DOTUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -10.3 | -257.0 | -309.5 | -42.2 | 32.0 | 0.25 | 0.28 |
| refine | inside_h4_rr3 | ETHUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -7.9 | -197.4 | -304.1 | -42.1 | 54.0 | 0.241 | 0.36 |
| refine | inside_h4_rr3 | LTCUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -6.6 | -164.9 | -397.2 | -41.6 | 40.0 | 0.275 | 0.28 |
| refine | inside_h4_rr3 | SOLUSD | H4 | build_inside_day | {"rr": 3.0} | 0.0025 | -11.5 | -253.5 | -384.1 | -37.9 | 43.0 | 0.233 | 0.318 |
| refine | inside_h4_rr3 | XRPUSD | H4 | build_inside_day | {"rr": 3.0} | 0.005 | -3.3 | -72.4 | -487.7 | -113.4 | 44.0 | 0.318 | 0.455 |
| screen | inside_h4_trail | ADAUSD | H4 | build_inside_day | {"trail": true} | 0.0025 | 3.6 | 89.4 | -149.8 | -25.6 | 31.0 | 0.29 | 0.32 |
| screen | inside_h4_trail | BNBUSD | H4 | build_inside_day | {"trail": true} | 0.0075 | 2.1 | 52.0 | -559.6 | -78.7 | 60.0 | 0.383 | 0.4 |
| screen | inside_h4_trail | BTCUSD | H4 | build_inside_day | {"trail": true} | 0.005 | -10.8 | -270.0 | -455.3 | -47.7 | 54.0 | 0.333 | 0.48 |
| screen | inside_h4_trail | DOTUSD | H4 | build_inside_day | {"trail": true} | 0.0025 | -12.2 | -304.5 | -433.4 | -25.9 | 41.0 | 0.22 | 0.2 |
| screen | inside_h4_trail | ETHUSD | H4 | build_inside_day | {"trail": true} | 0.0025 | -6.0 | -150.4 | -394.9 | -27.2 | 57.0 | 0.298 | 0.2 |
| screen | inside_h4_trail | LTCUSD | H4 | build_inside_day | {"trail": true} | 0.0025 | -12.8 | -319.6 | -436.3 | -25.0 | 49.0 | 0.245 | 0.24 |
| screen | inside_h4_trail | SOLUSD | H4 | build_inside_day | {"trail": true} | 0.0025 | -8.8 | -193.4 | -469.9 | -26.5 | 46.0 | 0.217 | 0.227 |
| screen | inside_h4_trail | XRPUSD | H4 | build_inside_day | {"trail": true} | 0.0075 | 47.3 | 1039.6 | -457.4 | -78.5 | 48.0 | 0.396 | 0.5 |
| refine | inside_h4_trail_a15 | ADAUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.005 | -5.8 | -144.5 | -552.1 | -52.1 | 43.0 | 0.372 | 0.28 |
| refine | inside_h4_trail_a15 | BNBUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.0075 | -9.9 | -247.1 | -533.0 | -117.8 | 57.0 | 0.333 | 0.44 |
| refine | inside_h4_trail_a15 | BTCUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.01 | 25.7 | 643.6 | -570.1 | -111.9 | 50.0 | 0.36 | 0.44 |
| refine | inside_h4_trail_a15 | DOTUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.005 | -11.4 | -286.2 | -544.4 | -53.0 | 41.0 | 0.268 | 0.24 |
| refine | inside_h4_trail_a15 | ETHUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.0025 | -13.9 | -348.0 | -477.7 | -39.9 | 57.0 | 0.193 | 0.24 |
| refine | inside_h4_trail_a15 | LTCUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.0025 | -14.6 | -363.8 | -490.6 | -42.8 | 47.0 | 0.17 | 0.2 |
| refine | inside_h4_trail_a15 | SOLUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.0025 | -11.2 | -246.7 | -412.3 | -27.7 | 45.0 | 0.244 | 0.182 |
| refine | inside_h4_trail_a15 | XRPUSD | H4 | build_inside_day | {"trail": true, "atr_mult": 1.5} | 0.005 | 27.3 | 601.0 | -407.3 | -62.1 | 46.0 | 0.37 | 0.5 |
| refine | lead_h4_lb2_h6 | ADAUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | 0.0025 | -6.2 | -154.6 | -292.7 | -31.5 | 65.0 | 0.385 | 0.4 |
| refine | lead_h4_lb2_h6 | BNBUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | 0.0025 | -9.5 | -237.6 | -298.9 | -40.2 | 142.0 | 0.408 | 0.4 |
| refine | lead_h4_lb2_h6 | DOTUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | nan | -41.2 | -1030.7 | -1121.3 | -38.5 | 153.0 | 0.261 | 0.2 |
| refine | lead_h4_lb2_h6 | ETHUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | 0.005 | 27.9 | 698.2 | -410.1 | -79.4 | 91.0 | 0.484 | 0.52 |
| refine | lead_h4_lb2_h6 | LTCUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | nan | -36.0 | -899.5 | -924.1 | -50.0 | 157.0 | 0.299 | 0.12 |
| refine | lead_h4_lb2_h6 | SOLUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | 0.005 | -9.4 | -207.7 | -453.5 | -64.6 | 82.0 | 0.427 | 0.364 |
| refine | lead_h4_lb2_h6 | XRPUSD | H4 | build_btc_lead | {"lb": 2, "hold": 6} | 0.0075 | 16.6 | 366.0 | -557.6 | -114.3 | 94.0 | 0.457 | 0.455 |
| refine | lead_h4_lb4_h12 | ADAUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | nan | -29.5 | -737.7 | -811.3 | -72.4 | 101.0 | 0.307 | 0.32 |
| refine | lead_h4_lb4_h12 | BNBUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | 0.0025 | -9.6 | -239.9 | -518.1 | -89.9 | 195.0 | 0.385 | 0.44 |
| refine | lead_h4_lb4_h12 | DOTUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | nan | -47.3 | -1182.4 | -1491.6 | -45.7 | 182.0 | 0.291 | 0.28 |
| refine | lead_h4_lb4_h12 | ETHUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | 0.005 | 8.1 | 202.6 | -576.5 | -116.3 | 145.0 | 0.379 | 0.48 |
| refine | lead_h4_lb4_h12 | LTCUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | nan | -77.4 | -1936.1 | -1939.8 | -50.4 | 220.0 | 0.245 | 0.12 |
| refine | lead_h4_lb4_h12 | SOLUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | nan | -22.2 | -488.9 | -637.2 | -54.1 | 126.0 | 0.365 | 0.273 |
| refine | lead_h4_lb4_h12 | XRPUSD | H4 | build_btc_lead | {"lb": 4, "hold": 12} | 0.0025 | 24.2 | 532.7 | -315.0 | -72.3 | 141.0 | 0.447 | 0.545 |
| refine | lead_lb2_t08_h6 | ADAUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -131.4 | -3284.1 | -3470.6 | -87.8 | 774.0 | 0.315 | 0.2 |
| refine | lead_lb2_t08_h6 | BNBUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -200.2 | -5004.7 | -5018.6 | -80.7 | 927.0 | 0.326 | 0.04 |
| refine | lead_lb2_t08_h6 | DOTUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -351.9 | -8798.5 | -8811.0 | -85.8 | 1028.0 | 0.192 | 0.04 |
| refine | lead_lb2_t08_h6 | ETHUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -76.9 | -1923.0 | -2064.3 | -78.4 | 760.0 | 0.396 | 0.28 |
| refine | lead_lb2_t08_h6 | LTCUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -471.6 | -11789.0 | -11789.0 | -105.7 | 1109.0 | 0.176 | 0.0 |
| refine | lead_lb2_t08_h6 | SOLUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -115.6 | -2544.0 | -2571.6 | -85.0 | 709.0 | 0.368 | 0.091 |
| refine | lead_lb2_t08_h6 | XRPUSD | H1 | build_btc_lead | {"lb": 2, "btc_thresh": 0.8, "hold": 6} | nan | -162.2 | -3568.8 | -3829.3 | -124.7 | 807.0 | 0.333 | 0.091 |
| refine | lead_lb4_h12 | ADAUSD | H1 | build_btc_lead | {} | nan | -136.0 | -3401.0 | -3445.0 | -86.7 | 591.0 | 0.308 | 0.12 |
| refine | lead_lb4_h12 | BNBUSD | H1 | build_btc_lead | {} | nan | -126.2 | -3155.0 | -3194.0 | -67.9 | 697.0 | 0.363 | 0.12 |
| refine | lead_lb4_h12 | DOTUSD | H1 | build_btc_lead | {} | nan | -257.8 | -6446.0 | -6446.0 | -101.8 | 773.0 | 0.201 | 0.04 |
| refine | lead_lb4_h12 | ETHUSD | H1 | build_btc_lead | {} | nan | -40.9 | -1023.3 | -1142.9 | -96.4 | 563.0 | 0.384 | 0.24 |
| refine | lead_lb4_h12 | LTCUSD | H1 | build_btc_lead | {} | nan | -373.6 | -9341.1 | -9345.9 | -89.2 | 848.0 | 0.199 | 0.0 |
| refine | lead_lb4_h12 | SOLUSD | H1 | build_btc_lead | {} | nan | -117.5 | -2584.5 | -2667.3 | -71.6 | 541.0 | 0.329 | 0.091 |
| refine | lead_lb4_h12 | XRPUSD | H1 | build_btc_lead | {} | nan | -92.9 | -2044.3 | -2180.9 | -99.7 | 595.0 | 0.355 | 0.182 |
| refine | lead_lb4_h12_rr2 | ADAUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -138.8 | -3469.3 | -3499.9 | -86.7 | 595.0 | 0.334 | 0.08 |
| refine | lead_lb4_h12_rr2 | BNBUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -134.6 | -3364.6 | -3428.5 | -65.6 | 710.0 | 0.366 | 0.12 |
| refine | lead_lb4_h12_rr2 | DOTUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -152.2 | -3805.3 | -3811.8 | -101.8 | 543.0 | 0.298 | 0.0 |
| refine | lead_lb4_h12_rr2 | ETHUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -47.8 | -1194.9 | -1293.1 | -96.4 | 571.0 | 0.403 | 0.32 |
| refine | lead_lb4_h12_rr2 | LTCUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -317.1 | -7928.6 | -7933.5 | -89.2 | 741.0 | 0.242 | 0.0 |
| refine | lead_lb4_h12_rr2 | SOLUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -118.6 | -2609.6 | -2698.3 | -71.6 | 550.0 | 0.353 | 0.045 |
| refine | lead_lb4_h12_rr2 | XRPUSD | H1 | build_btc_lead | {"rr": 2.0} | nan | -105.7 | -2324.9 | -2369.6 | -99.7 | 602.0 | 0.37 | 0.227 |
| refine | lead_lb4_h24 | ADAUSD | H1 | build_btc_lead | {"hold": 24} | nan | -107.2 | -2679.6 | -2757.2 | -86.7 | 533.0 | 0.3 | 0.28 |
| refine | lead_lb4_h24 | BNBUSD | H1 | build_btc_lead | {"hold": 24} | nan | -104.9 | -2621.9 | -2668.7 | -123.3 | 638.0 | 0.342 | 0.24 |
| refine | lead_lb4_h24 | DOTUSD | H1 | build_btc_lead | {"hold": 24} | nan | -214.5 | -5361.9 | -5361.9 | -97.8 | 689.0 | 0.216 | 0.04 |
| refine | lead_lb4_h24 | ETHUSD | H1 | build_btc_lead | {"hold": 24} | nan | -17.1 | -426.5 | -687.8 | -134.7 | 513.0 | 0.368 | 0.44 |
| refine | lead_lb4_h24 | LTCUSD | H1 | build_btc_lead | {"hold": 24} | nan | -332.7 | -8318.0 | -8325.6 | -92.2 | 763.0 | 0.214 | 0.04 |
| refine | lead_lb4_h24 | SOLUSD | H1 | build_btc_lead | {"hold": 24} | nan | -103.2 | -2270.5 | -2454.3 | -71.6 | 497.0 | 0.304 | 0.182 |
| refine | lead_lb4_h24 | XRPUSD | H1 | build_btc_lead | {"hold": 24} | nan | -59.0 | -1297.4 | -1540.1 | -127.0 | 541.0 | 0.364 | 0.364 |
| refine | lead_lb8_t15_h12 | ADAUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -68.4 | -1709.2 | -1807.0 | -125.0 | 336.0 | 0.315 | 0.16 |
| refine | lead_lb8_t15_h12 | BNBUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -61.4 | -1535.2 | -1726.0 | -89.7 | 386.0 | 0.373 | 0.28 |
| refine | lead_lb8_t15_h12 | DOTUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -125.7 | -3142.7 | -3150.3 | -72.1 | 449.0 | 0.216 | 0.12 |
| refine | lead_lb8_t15_h12 | ETHUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | 0.0025 | 14.3 | 356.8 | -447.3 | -72.6 | 270.0 | 0.448 | 0.6 |
| refine | lead_lb8_t15_h12 | LTCUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -206.1 | -5153.0 | -5188.1 | -74.7 | 480.0 | 0.19 | 0.04 |
| refine | lead_lb8_t15_h12 | SOLUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -19.8 | -435.9 | -682.5 | -74.8 | 272.0 | 0.382 | 0.318 |
| refine | lead_lb8_t15_h12 | XRPUSD | H1 | build_btc_lead | {"lb": 8, "btc_thresh": 1.5} | nan | -22.3 | -489.5 | -1035.7 | -80.8 | 303.0 | 0.383 | 0.455 |
| refine | nbo_d1_10_h5 | ADAUSD | D1 | build_nday_bo | {} | 0.0075 | -1.1 | -27.7 | -369.6 | -59.3 | 20.0 | 0.4 | 0.16 |
| refine | nbo_d1_10_h5 | BNBUSD | D1 | build_nday_bo | {} | 0.015 | -16.6 | -413.9 | -565.2 | -149.7 | 26.0 | 0.423 | 0.16 |
| refine | nbo_d1_10_h5 | BTCUSD | D1 | build_nday_bo | {} | 0.01 | -18.6 | -464.7 | -479.6 | -81.6 | 33.0 | 0.424 | 0.32 |
| refine | nbo_d1_10_h5 | DOTUSD | D1 | build_nday_bo | {} | 0.01 | -10.4 | -258.9 | -535.3 | -87.6 | 25.0 | 0.52 | 0.28 |
| refine | nbo_d1_10_h5 | ETHUSD | D1 | build_nday_bo | {} | 0.0075 | -16.9 | -423.2 | -591.9 | -85.9 | 33.0 | 0.364 | 0.28 |
| refine | nbo_d1_10_h5 | LTCUSD | D1 | build_nday_bo | {} | 0.005 | -16.0 | -400.6 | -481.8 | -46.6 | 29.0 | 0.31 | 0.16 |
| refine | nbo_d1_10_h5 | SOLUSD | D1 | build_nday_bo | {} | 0.015 | -7.0 | -153.0 | -459.8 | -106.4 | 28.0 | 0.429 | 0.364 |
| refine | nbo_d1_10_h5 | XRPUSD | D1 | build_nday_bo | {} | 0.0075 | -1.8 | -38.5 | -476.1 | -75.0 | 34.0 | 0.382 | 0.273 |
| refine | nbo_d1_10_h5_L | ADAUSD | D1 | build_nday_bo | {"long_only": true} | 0.015 | 14.8 | 370.6 | -481.5 | -118.5 | 16.0 | 0.438 | 0.24 |
| refine | nbo_d1_10_h5_L | BNBUSD | D1 | build_nday_bo | {"long_only": true} | 0.02 | -9.3 | -233.2 | -557.4 | -199.9 | 13.0 | 0.385 | 0.2 |
| refine | nbo_d1_10_h5_L | BTCUSD | D1 | build_nday_bo | {"long_only": true} | 0.015 | -15.9 | -398.2 | -504.6 | -114.2 | 16.0 | 0.375 | 0.24 |
| refine | nbo_d1_10_h5_L | DOTUSD | D1 | build_nday_bo | {"long_only": true} | 0.015 | -6.0 | -150.1 | -507.5 | -131.4 | 15.0 | 0.467 | 0.28 |
| refine | nbo_d1_10_h5_L | ETHUSD | D1 | build_nday_bo | {"long_only": true} | 0.015 | 0.8 | 19.5 | -518.3 | -126.0 | 16.0 | 0.438 | 0.24 |
| refine | nbo_d1_10_h5_L | LTCUSD | D1 | build_nday_bo | {"long_only": true} | 0.0075 | -12.0 | -299.8 | -481.3 | -54.2 | 14.0 | 0.214 | 0.12 |
| refine | nbo_d1_10_h5_L | SOLUSD | D1 | build_nday_bo | {"long_only": true} | 0.02 | -11.7 | -257.4 | -521.9 | -127.7 | 14.0 | 0.429 | 0.227 |
| refine | nbo_d1_10_h5_L | XRPUSD | D1 | build_nday_bo | {"long_only": true} | 0.01 | -1.6 | -36.1 | -599.2 | -100.0 | 17.0 | 0.176 | 0.136 |
| refine | nbo_d1_20_h10 | ADAUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.015 | 1.2 | 29.7 | -525.3 | -105.6 | 11.0 | 0.455 | 0.2 |
| refine | nbo_d1_20_h10 | BNBUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.02 | 27.7 | 691.5 | -556.4 | -252.2 | 15.0 | 0.533 | 0.32 |
| refine | nbo_d1_20_h10 | BTCUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.015 | 16.3 | 408.5 | -524.4 | -163.9 | 16.0 | 0.438 | 0.4 |
| refine | nbo_d1_20_h10 | DOTUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.015 | 6.5 | 163.7 | -573.4 | -139.6 | 16.0 | 0.438 | 0.32 |
| refine | nbo_d1_20_h10 | ETHUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.015 | 22.5 | 562.3 | -530.5 | -115.3 | 15.0 | 0.467 | 0.28 |
| refine | nbo_d1_20_h10 | LTCUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.0125 | -11.4 | -284.2 | -559.3 | -142.8 | 17.0 | 0.353 | 0.24 |
| refine | nbo_d1_20_h10 | SOLUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.02 | 54.5 | 1199.8 | -443.6 | -244.2 | 13.0 | 0.615 | 0.364 |
| refine | nbo_d1_20_h10 | XRPUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10} | 0.02 | 53.2 | 1170.1 | -501.0 | -269.2 | 14.0 | 0.429 | 0.318 |
| refine | nbo_d1_20_h10_trail | ADAUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.015 | 1.2 | 29.7 | -525.3 | -105.6 | 11.0 | 0.455 | 0.2 |
| refine | nbo_d1_20_h10_trail | BNBUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.02 | 31.5 | 787.6 | -460.3 | -193.3 | 15.0 | 0.467 | 0.28 |
| refine | nbo_d1_20_h10_trail | BTCUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.015 | 4.5 | 113.7 | -483.2 | -122.3 | 16.0 | 0.312 | 0.36 |
| refine | nbo_d1_20_h10_trail | DOTUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.015 | 9.9 | 247.1 | -549.2 | -139.6 | 16.0 | 0.438 | 0.32 |
| refine | nbo_d1_20_h10_trail | ETHUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.02 | 35.4 | 884.2 | -562.4 | -153.8 | 15.0 | 0.467 | 0.28 |
| refine | nbo_d1_20_h10_trail | LTCUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.0125 | -16.1 | -403.7 | -590.9 | -139.2 | 17.0 | 0.353 | 0.2 |
| refine | nbo_d1_20_h10_trail | SOLUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.02 | 54.5 | 1199.8 | -443.6 | -244.2 | 13.0 | 0.615 | 0.364 |
| refine | nbo_d1_20_h10_trail | XRPUSD | D1 | build_nday_bo | {"n": 20, "hold_days": 10, "trail": true} | 0.015 | 35.9 | 790.7 | -454.6 | -201.9 | 14.0 | 0.429 | 0.318 |
| refine | nbo_d1_30_h15_a3 | ADAUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.02 | 0.9 | 21.9 | -428.2 | -142.1 | 7.0 | 0.714 | 0.2 |
| refine | nbo_d1_30_h15_a3 | BNBUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.02 | 0.1 | 3.0 | -487.9 | -169.7 | 11.0 | 0.455 | 0.2 |
| refine | nbo_d1_30_h15_a3 | BTCUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.02 | 4.9 | 122.4 | -399.8 | -165.9 | 13.0 | 0.462 | 0.4 |
| refine | nbo_d1_30_h15_a3 | DOTUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.02 | 18.5 | 461.3 | -463.9 | -140.3 | 11.0 | 0.545 | 0.32 |
| refine | nbo_d1_30_h15_a3 | ETHUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.02 | 20.4 | 510.8 | -509.5 | -117.2 | 12.0 | 0.583 | 0.28 |
| refine | nbo_d1_30_h15_a3 | LTCUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.015 | -11.5 | -288.1 | -581.9 | -96.8 | 11.0 | 0.364 | 0.2 |
| refine | nbo_d1_30_h15_a3 | SOLUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.015 | -1.2 | -25.4 | -567.8 | -125.4 | 13.0 | 0.462 | 0.364 |
| refine | nbo_d1_30_h15_a3 | XRPUSD | D1 | build_nday_bo | {"n": 30, "hold_days": 15, "atr_mult": 3.0} | 0.015 | 24.1 | 529.3 | -290.7 | -229.9 | 8.0 | 0.625 | 0.273 |
| refine | nbo_d1_5_h3 | ADAUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.015 | 13.1 | 327.8 | -580.1 | -156.2 | 45.0 | 0.444 | 0.36 |
| refine | nbo_d1_5_h3 | BNBUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.0075 | -17.8 | -443.9 | -492.5 | -73.9 | 47.0 | 0.34 | 0.32 |
| refine | nbo_d1_5_h3 | BTCUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.015 | 26.5 | 661.5 | -418.6 | -114.2 | 51.0 | 0.471 | 0.6 |
| refine | nbo_d1_5_h3 | DOTUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.005 | -6.7 | -168.2 | -431.6 | -50.0 | 36.0 | 0.361 | 0.36 |
| refine | nbo_d1_5_h3 | ETHUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.01 | -6.9 | -173.6 | -571.9 | -110.3 | 47.0 | 0.447 | 0.44 |
| refine | nbo_d1_5_h3 | LTCUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.005 | -19.5 | -486.9 | -502.5 | -43.7 | 47.0 | 0.298 | 0.2 |
| refine | nbo_d1_5_h3 | SOLUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.015 | -1.2 | -27.3 | -536.3 | -134.0 | 36.0 | 0.472 | 0.5 |
| refine | nbo_d1_5_h3 | XRPUSD | D1 | build_nday_bo | {"n": 5, "hold_days": 3} | 0.0125 | 0.6 | 14.3 | -523.0 | -125.0 | 48.0 | 0.312 | 0.273 |
| refine | nbo_h4_120_h10_trail | ADAUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.0025 | 3.2 | 81.1 | -259.1 | -25.0 | 14.0 | 0.214 | 0.12 |
| refine | nbo_h4_120_h10_trail | BNBUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.0075 | -14.7 | -366.6 | -470.4 | -101.6 | 17.0 | 0.235 | 0.16 |
| refine | nbo_h4_120_h10_trail | BTCUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.0075 | -19.0 | -474.0 | -513.9 | -74.3 | 16.0 | 0.188 | 0.08 |
| refine | nbo_h4_120_h10_trail | DOTUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.02 | 57.2 | 1430.4 | -585.3 | -234.9 | 17.0 | 0.529 | 0.36 |
| refine | nbo_h4_120_h10_trail | ETHUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.015 | 4.6 | 115.5 | -491.4 | -192.9 | 15.0 | 0.333 | 0.16 |
| refine | nbo_h4_120_h10_trail | LTCUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.0025 | -13.9 | -346.9 | -367.4 | -32.9 | 23.0 | 0.13 | 0.08 |
| refine | nbo_h4_120_h10_trail | SOLUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.0075 | -11.7 | -258.3 | -579.7 | -88.8 | 15.0 | 0.133 | 0.045 |
| refine | nbo_h4_120_h10_trail | XRPUSD | H4 | build_nday_bo | {"n": 120, "hold_days": 10, "trail": true} | 0.01 | 34.1 | 749.6 | -493.4 | -175.1 | 17.0 | 0.294 | 0.182 |
| refine | nbo_h4_60_h5 | ADAUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.005 | 20.3 | 506.4 | -469.0 | -96.8 | 36.0 | 0.472 | 0.44 |
| refine | nbo_h4_60_h5 | BNBUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.0025 | -21.2 | -529.4 | -546.6 | -35.7 | 30.0 | 0.133 | 0.08 |
| refine | nbo_h4_60_h5 | BTCUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.0075 | -1.1 | -26.7 | -529.4 | -171.6 | 37.0 | 0.324 | 0.32 |
| refine | nbo_h4_60_h5 | DOTUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.005 | -4.0 | -98.8 | -434.6 | -134.7 | 37.0 | 0.405 | 0.28 |
| refine | nbo_h4_60_h5 | ETHUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.005 | 5.7 | 142.0 | -450.0 | -102.0 | 37.0 | 0.324 | 0.32 |
| refine | nbo_h4_60_h5 | LTCUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.0025 | -19.0 | -476.2 | -573.8 | -36.5 | 35.0 | 0.2 | 0.2 |
| refine | nbo_h4_60_h5 | SOLUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.0075 | -7.1 | -156.0 | -537.8 | -141.9 | 35.0 | 0.457 | 0.455 |
| refine | nbo_h4_60_h5 | XRPUSD | H4 | build_nday_bo | {"n": 60, "hold_days": 5} | 0.0025 | 0.8 | 17.6 | -387.3 | -60.9 | 44.0 | 0.273 | 0.318 |
| screen | orb_n2_rr2 | ADAUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -129.7 | -3242.6 | -3261.3 | -26.6 | 617.0 | 0.366 | 0.12 |
| screen | orb_n2_rr2 | BNBUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -161.2 | -4031.2 | -4066.9 | -25.3 | 732.0 | 0.387 | 0.12 |
| screen | orb_n2_rr2 | BTCUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | 7.0 | 175.5 | -843.3 | -25.0 | 703.0 | 0.403 | 0.6 |
| screen | orb_n2_rr2 | DOTUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -128.6 | -3216.0 | -3222.5 | -63.8 | 471.0 | 0.321 | 0.16 |
| screen | orb_n2_rr2 | ETHUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -55.0 | -1374.9 | -1536.6 | -26.2 | 731.0 | 0.382 | 0.32 |
| screen | orb_n2_rr2 | LTCUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -259.2 | -6478.9 | -6519.7 | -25.0 | 621.0 | 0.285 | 0.0 |
| screen | orb_n2_rr2 | SOLUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -110.2 | -2425.1 | -2604.3 | -25.0 | 659.0 | 0.392 | 0.227 |
| screen | orb_n2_rr2 | XRPUSD | H1 | build_day_orb | {"n_hours": 2, "rr": 2.0} | nan | -111.5 | -2453.8 | -2539.3 | -28.0 | 660.0 | 0.394 | 0.273 |
| screen | orb_n4_noTP | ADAUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -151.8 | -3794.7 | -3973.8 | -43.9 | 680.0 | 0.285 | 0.12 |
| screen | orb_n4_noTP | BNBUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -141.9 | -3546.9 | -3547.4 | -26.8 | 717.0 | 0.317 | 0.12 |
| screen | orb_n4_noTP | BTCUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | 33.4 | 834.4 | -881.7 | -32.5 | 705.0 | 0.301 | 0.44 |
| screen | orb_n4_noTP | DOTUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -231.4 | -5783.9 | -5860.1 | -79.9 | 693.0 | 0.199 | 0.0 |
| screen | orb_n4_noTP | ETHUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -9.0 | -224.4 | -1233.9 | -25.0 | 706.0 | 0.286 | 0.56 |
| screen | orb_n4_noTP | LTCUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -330.6 | -8265.9 | -8318.1 | -25.0 | 702.0 | 0.205 | 0.0 |
| screen | orb_n4_noTP | SOLUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -89.3 | -1964.8 | -2408.1 | -25.0 | 638.0 | 0.32 | 0.182 |
| screen | orb_n4_noTP | XRPUSD | H1 | build_day_orb | {"n_hours": 4, "rr": null, "stop": "atr"} | nan | -129.6 | -2850.8 | -2850.8 | -87.8 | 642.0 | 0.301 | 0.273 |
| screen | orb_n4_rr2 | ADAUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -121.5 | -3036.6 | -3036.6 | -26.2 | 534.0 | 0.346 | 0.2 |
| screen | orb_n4_rr2 | BNBUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -114.1 | -2853.4 | -2932.8 | -41.5 | 717.0 | 0.368 | 0.12 |
| screen | orb_n4_rr2 | BTCUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | 0.0025 | 17.3 | 431.4 | -410.0 | -25.0 | 640.0 | 0.439 | 0.6 |
| screen | orb_n4_rr2 | DOTUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -127.2 | -3179.6 | -3214.4 | -46.8 | 481.0 | 0.312 | 0.08 |
| screen | orb_n4_rr2 | ETHUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -22.8 | -569.4 | -937.8 | -43.1 | 706.0 | 0.414 | 0.36 |
| screen | orb_n4_rr2 | LTCUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -263.9 | -6597.1 | -6635.9 | -25.0 | 648.0 | 0.256 | 0.0 |
| screen | orb_n4_rr2 | SOLUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -84.3 | -1855.0 | -1989.2 | -37.2 | 635.0 | 0.381 | 0.182 |
| screen | orb_n4_rr2 | XRPUSD | H1 | build_day_orb | {"n_hours": 4, "rr": 2.0} | nan | -92.4 | -2033.2 | -2134.9 | -27.1 | 637.0 | 0.386 | 0.273 |
| screen | orb_n6_rr15 | ADAUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -101.6 | -2541.1 | -2548.6 | -25.0 | 453.0 | 0.342 | 0.04 |
| screen | orb_n6_rr15 | BNBUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -97.7 | -2443.6 | -2493.1 | -25.0 | 687.0 | 0.364 | 0.08 |
| screen | orb_n6_rr15 | BTCUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | 0.0025 | -2.2 | -54.1 | -563.2 | -24.9 | 578.0 | 0.457 | 0.4 |
| screen | orb_n6_rr15 | DOTUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -107.0 | -2675.4 | -2697.4 | -46.6 | 425.0 | 0.339 | 0.16 |
| screen | orb_n6_rr15 | ETHUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | 0.0025 | 7.2 | 179.4 | -439.9 | -25.0 | 657.0 | 0.441 | 0.56 |
| screen | orb_n6_rr15 | LTCUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -219.2 | -5481.0 | -5515.6 | -34.6 | 594.0 | 0.264 | 0.0 |
| screen | orb_n6_rr15 | SOLUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -89.4 | -1967.1 | -2033.6 | -25.0 | 596.0 | 0.389 | 0.091 |
| screen | orb_n6_rr15 | XRPUSD | H1 | build_day_orb | {"n_hours": 6, "rr": 1.5} | nan | -69.2 | -1522.3 | -1551.5 | -25.0 | 599.0 | 0.411 | 0.182 |
| screen | overnight_fri20_S48 | ADAUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | 0.0025 | -4.5 | -111.8 | -276.2 | -48.8 | 75.0 | 0.427 | 0.32 |
| screen | overnight_fri20_S48 | BNBUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | nan | -18.0 | -450.2 | -694.5 | -96.0 | 105.0 | 0.305 | 0.36 |
| screen | overnight_fri20_S48 | BTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | 0.0025 | -9.4 | -234.7 | -404.6 | -50.0 | 100.0 | 0.36 | 0.36 |
| screen | overnight_fri20_S48 | DOTUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | nan | -7.5 | -188.3 | -710.3 | -58.1 | 96.0 | 0.312 | 0.28 |
| screen | overnight_fri20_S48 | ETHUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | nan | -14.6 | -364.5 | -646.1 | -110.1 | 105.0 | 0.333 | 0.32 |
| screen | overnight_fri20_S48 | LTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | nan | -48.4 | -1211.1 | -1277.4 | -37.3 | 105.0 | 0.219 | 0.12 |
| screen | overnight_fri20_S48 | SOLUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | 0.0025 | -10.9 | -238.7 | -506.4 | -60.7 | 95.0 | 0.368 | 0.409 |
| screen | overnight_fri20_S48 | XRPUSD | H1 | build_overnight | {"side": "short", "entry_wd": 4, "entry_hour": 20, "hold": 48} | 0.0025 | -7.0 | -153.7 | -507.8 | -81.0 | 95.0 | 0.411 | 0.364 |
| refine | overnight_mon00_L12 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.0025 | -11.2 | -279.8 | -360.8 | -25.0 | 85.0 | 0.412 | 0.32 |
| refine | overnight_mon00_L12 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.0025 | -14.5 | -362.1 | -424.3 | -25.0 | 106.0 | 0.415 | 0.44 |
| refine | overnight_mon00_L12 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.005 | 21.1 | 526.3 | -399.3 | -49.6 | 106.0 | 0.425 | 0.68 |
| refine | overnight_mon00_L12 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | nan | -29.8 | -743.9 | -815.5 | -25.0 | 96.0 | 0.208 | 0.16 |
| refine | overnight_mon00_L12 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.0075 | 27.9 | 698.2 | -541.0 | -75.0 | 106.0 | 0.491 | 0.6 |
| refine | overnight_mon00_L12 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | nan | -45.9 | -1147.1 | -1164.3 | -25.0 | 106.0 | 0.245 | 0.0 |
| refine | overnight_mon00_L12 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.0025 | -12.7 | -279.9 | -355.0 | -25.0 | 95.0 | 0.432 | 0.318 |
| refine | overnight_mon00_L12 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 12} | 0.0025 | -12.9 | -284.1 | -329.2 | -25.0 | 95.0 | 0.4 | 0.409 |
| screen | overnight_mon00_L24 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.0025 | -11.9 | -296.5 | -338.1 | -25.0 | 85.0 | 0.376 | 0.28 |
| screen | overnight_mon00_L24 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.0025 | -13.2 | -329.0 | -431.8 | -25.0 | 106.0 | 0.406 | 0.44 |
| screen | overnight_mon00_L24 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.005 | 58.5 | 1463.5 | -414.1 | -49.6 | 106.0 | 0.377 | 0.6 |
| screen | overnight_mon00_L24 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | nan | -37.1 | -928.6 | -970.5 | -25.0 | 96.0 | 0.198 | 0.12 |
| screen | overnight_mon00_L24 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.005 | 36.0 | 899.0 | -461.6 | -50.0 | 106.0 | 0.443 | 0.52 |
| screen | overnight_mon00_L24 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | nan | -51.1 | -1277.7 | -1285.2 | -25.0 | 106.0 | 0.217 | 0.08 |
| screen | overnight_mon00_L24 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.0025 | -8.4 | -184.9 | -300.8 | -25.0 | 95.0 | 0.389 | 0.364 |
| screen | overnight_mon00_L24 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24} | 0.005 | 6.2 | 137.3 | -554.9 | -50.0 | 95.0 | 0.389 | 0.5 |
| refine | overnight_mon00_L24_a3 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.0025 | -8.7 | -216.8 | -254.0 | -25.0 | 70.0 | 0.429 | 0.28 |
| refine | overnight_mon00_L24_a3 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.005 | -15.4 | -385.5 | -572.4 | -50.0 | 106.0 | 0.472 | 0.44 |
| refine | overnight_mon00_L24_a3 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.0075 | 40.9 | 1023.3 | -591.2 | -74.5 | 106.0 | 0.434 | 0.56 |
| refine | overnight_mon00_L24_a3 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | nan | -34.9 | -873.4 | -874.9 | -25.0 | 91.0 | 0.198 | 0.12 |
| refine | overnight_mon00_L24_a3 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.0075 | 39.0 | 974.8 | -452.6 | -75.0 | 106.0 | 0.509 | 0.52 |
| refine | overnight_mon00_L24_a3 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | nan | -41.2 | -1031.2 | -1038.1 | -25.0 | 106.0 | 0.264 | 0.12 |
| refine | overnight_mon00_L24_a3 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.005 | -12.3 | -270.4 | -496.0 | -49.6 | 95.0 | 0.432 | 0.364 |
| refine | overnight_mon00_L24_a3 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 24, "atr_mult": 3.0} | 0.005 | 0.2 | 3.3 | -516.1 | -50.0 | 95.0 | 0.442 | 0.364 |
| refine | overnight_mon00_L48 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | nan | -22.3 | -557.1 | -614.5 | -77.5 | 85.0 | 0.247 | 0.24 |
| refine | overnight_mon00_L48 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | nan | -28.1 | -702.5 | -812.4 | -103.3 | 106.0 | 0.292 | 0.4 |
| refine | overnight_mon00_L48 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | 0.0025 | 15.0 | 375.2 | -351.8 | -144.2 | 106.0 | 0.236 | 0.4 |
| refine | overnight_mon00_L48 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | nan | -48.3 | -1208.5 | -1245.7 | -89.0 | 96.0 | 0.188 | 0.08 |
| refine | overnight_mon00_L48 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | 0.0025 | -6.3 | -158.6 | -407.1 | -114.6 | 106.0 | 0.302 | 0.4 |
| refine | overnight_mon00_L48 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | nan | -59.3 | -1483.4 | -1508.8 | -49.0 | 106.0 | 0.179 | 0.08 |
| refine | overnight_mon00_L48 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | nan | -24.7 | -543.9 | -642.6 | -64.0 | 95.0 | 0.263 | 0.364 |
| refine | overnight_mon00_L48 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 0, "entry_hour": 0, "hold": 48} | 0.0025 | -11.0 | -242.6 | -415.6 | -118.7 | 95.0 | 0.326 | 0.318 |
| screen | overnight_sat00_S48 | ADAUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | 0.0025 | 2.3 | 56.7 | -303.0 | -51.3 | 79.0 | 0.443 | 0.44 |
| screen | overnight_sat00_S48 | BNBUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | nan | -21.6 | -540.4 | -723.6 | -46.1 | 101.0 | 0.317 | 0.28 |
| screen | overnight_sat00_S48 | BTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | 0.0025 | -8.1 | -202.9 | -374.2 | -52.0 | 98.0 | 0.367 | 0.4 |
| screen | overnight_sat00_S48 | DOTUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | 0.0025 | -18.2 | -454.5 | -480.3 | -32.9 | 49.0 | 0.184 | 0.04 |
| screen | overnight_sat00_S48 | ETHUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | nan | -13.6 | -341.1 | -600.0 | -66.4 | 101.0 | 0.337 | 0.36 |
| screen | overnight_sat00_S48 | LTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | nan | -37.4 | -933.8 | -999.5 | -35.6 | 88.0 | 0.261 | 0.12 |
| screen | overnight_sat00_S48 | SOLUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | 0.0025 | -9.8 | -214.5 | -428.7 | -45.7 | 87.0 | 0.425 | 0.273 |
| screen | overnight_sat00_S48 | XRPUSD | H1 | build_overnight | {"side": "short", "entry_wd": 5, "entry_hour": 0, "hold": 48} | 0.0025 | -11.5 | -252.5 | -534.5 | -49.9 | 89.0 | 0.382 | 0.364 |
| screen | overnight_sun20_L12 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | 0.0025 | -18.7 | -468.7 | -526.9 | -41.2 | 88.0 | 0.33 | 0.28 |
| screen | overnight_sun20_L12 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | 0.0025 | -19.7 | -493.4 | -553.8 | -30.1 | 106.0 | 0.387 | 0.36 |
| screen | overnight_sun20_L12 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | 0.005 | 9.7 | 241.9 | -470.2 | -73.4 | 106.0 | 0.349 | 0.56 |
| screen | overnight_sun20_L12 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | nan | -27.4 | -684.0 | -766.5 | -27.7 | 97.0 | 0.268 | 0.2 |
| screen | overnight_sun20_L12 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | 0.0025 | -11.8 | -293.8 | -385.3 | -37.1 | 106.0 | 0.387 | 0.4 |
| screen | overnight_sun20_L12 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | nan | -54.5 | -1363.7 | -1445.7 | -25.9 | 106.0 | 0.198 | 0.08 |
| screen | overnight_sun20_L12 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | nan | -29.4 | -645.9 | -687.4 | -29.7 | 95.0 | 0.284 | 0.227 |
| screen | overnight_sun20_L12 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 20, "hold": 12} | 0.0025 | -23.1 | -508.0 | -548.8 | -35.7 | 95.0 | 0.326 | 0.273 |
| refine | overnight_sun23_L24 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.0025 | -3.9 | -98.4 | -226.1 | -25.0 | 86.0 | 0.43 | 0.44 |
| refine | overnight_sun23_L24 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.0025 | -8.8 | -219.2 | -428.8 | -25.0 | 106.0 | 0.443 | 0.4 |
| refine | overnight_sun23_L24 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.005 | 34.9 | 873.6 | -509.6 | -49.9 | 106.0 | 0.34 | 0.56 |
| refine | overnight_sun23_L24 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | nan | -38.1 | -952.2 | -965.6 | -35.0 | 97.0 | 0.216 | 0.12 |
| refine | overnight_sun23_L24 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.005 | 23.4 | 585.4 | -537.9 | -50.0 | 106.0 | 0.396 | 0.52 |
| refine | overnight_sun23_L24 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | nan | -51.4 | -1284.6 | -1325.3 | -32.5 | 106.0 | 0.217 | 0.08 |
| refine | overnight_sun23_L24 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.005 | -12.1 | -265.7 | -555.7 | -49.9 | 95.0 | 0.368 | 0.409 |
| refine | overnight_sun23_L24 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 6, "entry_hour": 23, "hold": 24} | 0.005 | 7.8 | 171.9 | -520.9 | -50.0 | 95.0 | 0.358 | 0.455 |
| refine | overnight_thu00_S24 | ADAUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0025 | 1.8 | 44.8 | -274.1 | -25.0 | 79.0 | 0.456 | 0.44 |
| refine | overnight_thu00_S24 | BNBUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0025 | 3.4 | 85.0 | -398.5 | -25.0 | 106.0 | 0.462 | 0.52 |
| refine | overnight_thu00_S24 | BTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.005 | 28.4 | 711.2 | -541.9 | -52.3 | 106.0 | 0.481 | 0.56 |
| refine | overnight_thu00_S24 | DOTUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0025 | -15.7 | -392.7 | -501.8 | -25.0 | 97.0 | 0.32 | 0.28 |
| refine | overnight_thu00_S24 | ETHUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0075 | 96.0 | 2400.7 | -521.4 | -75.0 | 106.0 | 0.547 | 0.72 |
| refine | overnight_thu00_S24 | LTCUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | nan | -29.8 | -745.2 | -822.2 | -25.0 | 106.0 | 0.311 | 0.24 |
| refine | overnight_thu00_S24 | SOLUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0075 | 22.6 | 496.3 | -599.7 | -74.5 | 96.0 | 0.49 | 0.545 |
| refine | overnight_thu00_S24 | XRPUSD | H1 | build_overnight | {"side": "short", "entry_wd": 3, "entry_hour": 0, "hold": 24} | 0.0075 | 75.2 | 1654.2 | -550.1 | -77.3 | 96.0 | 0.562 | 0.545 |
| refine | overnight_wed00_L24 | ADAUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | 0.0025 | -10.9 | -272.9 | -434.9 | -25.0 | 79.0 | 0.354 | 0.28 |
| refine | overnight_wed00_L24 | BNBUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | 0.005 | -6.8 | -169.9 | -527.0 | -50.0 | 105.0 | 0.457 | 0.52 |
| refine | overnight_wed00_L24 | BTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | 0.0025 | 11.3 | 282.6 | -322.7 | -24.8 | 100.0 | 0.5 | 0.56 |
| refine | overnight_wed00_L24 | DOTUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | nan | -15.2 | -380.3 | -617.6 | -25.0 | 95.0 | 0.326 | 0.32 |
| refine | overnight_wed00_L24 | ETHUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | 0.005 | 78.1 | 1952.8 | -487.5 | -50.0 | 105.0 | 0.476 | 0.6 |
| refine | overnight_wed00_L24 | LTCUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | nan | -33.9 | -847.3 | -946.9 | -25.0 | 105.0 | 0.286 | 0.2 |
| refine | overnight_wed00_L24 | SOLUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | 0.005 | 1.4 | 31.1 | -595.9 | -49.9 | 94.0 | 0.415 | 0.364 |
| refine | overnight_wed00_L24 | XRPUSD | H1 | build_overnight | {"side": "long", "entry_wd": 2, "entry_hour": 0, "hold": 24} | nan | -18.1 | -397.4 | -611.2 | -25.0 | 94.0 | 0.351 | 0.273 |
| screen | pd_break_rr2 | ADAUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -91.6 | -2290.7 | -2348.0 | -83.0 | 486.0 | 0.469 | 0.2 |
| screen | pd_break_rr2 | BNBUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -105.9 | -2646.8 | -2646.8 | -52.8 | 530.0 | 0.487 | 0.12 |
| screen | pd_break_rr2 | BTCUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -25.8 | -646.0 | -1025.8 | -63.9 | 563.0 | 0.332 | 0.4 |
| screen | pd_break_rr2 | DOTUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -49.4 | -1235.0 | -1240.8 | -74.1 | 319.0 | 0.417 | 0.12 |
| screen | pd_break_rr2 | ETHUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -33.1 | -826.9 | -1003.6 | -83.0 | 524.0 | 0.353 | 0.4 |
| screen | pd_break_rr2 | LTCUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -193.5 | -4837.3 | -4841.8 | -50.0 | 377.0 | 0.318 | 0.0 |
| screen | pd_break_rr2 | SOLUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -133.7 | -2940.9 | -3061.8 | -54.8 | 511.0 | 0.425 | 0.091 |
| screen | pd_break_rr2 | XRPUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0} | nan | -116.6 | -2564.3 | -2624.3 | -70.3 | 465.0 | 0.389 | 0.182 |
| screen | pd_break_rr2_x23 | ADAUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -99.4 | -2484.2 | -2517.0 | -50.0 | 527.0 | 0.397 | 0.08 |
| screen | pd_break_rr2_x23 | BNBUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -108.2 | -2705.0 | -2705.0 | -50.0 | 561.0 | 0.431 | 0.12 |
| screen | pd_break_rr2_x23 | BTCUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -28.8 | -719.9 | -1092.7 | -63.9 | 575.0 | 0.35 | 0.36 |
| screen | pd_break_rr2_x23 | DOTUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -59.0 | -1475.8 | -1475.8 | -50.0 | 332.0 | 0.392 | 0.04 |
| screen | pd_break_rr2_x23 | ETHUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -31.8 | -794.5 | -956.0 | -49.9 | 535.0 | 0.372 | 0.4 |
| screen | pd_break_rr2_x23 | LTCUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -190.0 | -4751.0 | -4751.0 | -50.0 | 386.0 | 0.29 | 0.0 |
| screen | pd_break_rr2_x23 | SOLUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -136.0 | -2991.5 | -3095.2 | -49.6 | 534.0 | 0.38 | 0.045 |
| screen | pd_break_rr2_x23 | XRPUSD | H1 | build_pd_break | {"mode": "break", "rr": 2.0, "exit_hour": 23} | nan | -122.6 | -2697.8 | -2777.2 | -52.5 | 488.0 | 0.369 | 0.091 |
| screen | pd_h4_sfp_rr2 | ADAUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -70.2 | -1756.2 | -1820.4 | -53.6 | 361.0 | 0.429 | 0.16 |
| screen | pd_h4_sfp_rr2 | BNBUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -135.1 | -3378.4 | -3382.2 | -108.7 | 472.0 | 0.398 | 0.08 |
| screen | pd_h4_sfp_rr2 | BTCUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -52.5 | -1312.9 | -1312.9 | -69.1 | 448.0 | 0.359 | 0.28 |
| screen | pd_h4_sfp_rr2 | DOTUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -84.7 | -2116.9 | -2131.6 | -56.1 | 310.0 | 0.358 | 0.12 |
| screen | pd_h4_sfp_rr2 | ETHUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -81.0 | -2025.9 | -2159.2 | -66.9 | 447.0 | 0.362 | 0.32 |
| screen | pd_h4_sfp_rr2 | LTCUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -162.3 | -4056.8 | -4098.9 | -50.7 | 396.0 | 0.313 | 0.0 |
| screen | pd_h4_sfp_rr2 | SOLUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -90.3 | -1985.9 | -2180.0 | -51.6 | 430.0 | 0.423 | 0.182 |
| screen | pd_h4_sfp_rr2 | XRPUSD | H4 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -78.5 | -1726.3 | -1930.1 | -63.3 | 391.0 | 0.427 | 0.273 |
| screen | pd_sfp_lvl | ADAUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -99.3 | -2482.4 | -2552.5 | -112.2 | 457.0 | 0.357 | 0.24 |
| screen | pd_sfp_lvl | BNBUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -128.1 | -3202.7 | -3234.9 | -68.5 | 504.0 | 0.355 | 0.12 |
| screen | pd_sfp_lvl | BTCUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -31.6 | -789.1 | -1806.6 | -165.5 | 540.0 | 0.269 | 0.36 |
| screen | pd_sfp_lvl | DOTUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -92.3 | -2306.9 | -2521.2 | -87.0 | 385.0 | 0.275 | 0.2 |
| screen | pd_sfp_lvl | ETHUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -97.6 | -2440.4 | -3137.9 | -328.3 | 522.0 | 0.257 | 0.44 |
| screen | pd_sfp_lvl | LTCUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -235.7 | -5892.4 | -5906.7 | -72.5 | 484.0 | 0.264 | 0.0 |
| screen | pd_sfp_lvl | SOLUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -119.5 | -2628.1 | -2657.2 | -77.0 | 479.0 | 0.324 | 0.182 |
| screen | pd_sfp_lvl | XRPUSD | H1 | build_pd_break | {"mode": "sfp", "tp_level": true} | nan | -144.1 | -3170.2 | -3260.0 | -98.4 | 455.0 | 0.295 | 0.091 |
| screen | pd_sfp_rr2 | ADAUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -88.6 | -2214.3 | -2356.7 | -55.5 | 446.0 | 0.484 | 0.2 |
| screen | pd_sfp_rr2 | BNBUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -122.7 | -3068.6 | -3111.2 | -55.9 | 516.0 | 0.5 | 0.04 |
| screen | pd_sfp_rr2 | BTCUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -37.2 | -928.8 | -1565.8 | -68.5 | 548.0 | 0.356 | 0.36 |
| screen | pd_sfp_rr2 | DOTUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -47.8 | -1195.1 | -1476.9 | -62.0 | 313.0 | 0.457 | 0.24 |
| screen | pd_sfp_rr2 | ETHUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -70.0 | -1750.8 | -1922.3 | -73.9 | 530.0 | 0.357 | 0.44 |
| screen | pd_sfp_rr2 | LTCUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -134.4 | -3359.8 | -3385.4 | -53.9 | 341.0 | 0.381 | 0.0 |
| screen | pd_sfp_rr2 | SOLUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -110.8 | -2438.2 | -2454.5 | -47.5 | 476.0 | 0.458 | 0.136 |
| screen | pd_sfp_rr2 | XRPUSD | H1 | build_pd_break | {"mode": "sfp", "rr": 2.0} | nan | -142.7 | -3140.2 | -3142.5 | -67.6 | 462.0 | 0.413 | 0.091 |
| screen | pdc_z15 | ADAUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.0025 | -9.1 | -226.7 | -248.4 | -39.0 | 22.0 | 0.364 | 0.12 |
| screen | pdc_z15 | BNBUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.0025 | -7.8 | -195.8 | -310.6 | -49.4 | 58.0 | 0.431 | 0.36 |
| screen | pdc_z15 | BTCUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.01 | -18.8 | -470.2 | -581.1 | -134.4 | 42.0 | 0.548 | 0.52 |
| screen | pdc_z15 | DOTUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.005 | -20.6 | -514.9 | -581.8 | -79.8 | 31.0 | 0.323 | 0.16 |
| screen | pdc_z15 | ETHUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.005 | -14.9 | -373.3 | -527.7 | -49.8 | 53.0 | 0.434 | 0.44 |
| screen | pdc_z15 | LTCUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.0025 | -16.0 | -399.3 | -421.4 | -46.5 | 46.0 | 0.326 | 0.08 |
| screen | pdc_z15 | SOLUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.005 | -23.8 | -523.2 | -586.7 | -51.2 | 33.0 | 0.303 | 0.182 |
| screen | pdc_z15 | XRPUSD | H1 | build_pdc_revert | {"z": 1.5} | 0.005 | -15.8 | -347.9 | -434.0 | -105.6 | 42.0 | 0.452 | 0.409 |
| screen | pdc_z15_h24 | ADAUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.0075 | -21.5 | -536.6 | -591.7 | -131.0 | 34.0 | 0.412 | 0.28 |
| screen | pdc_z15_h24 | BNBUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.005 | -12.6 | -314.0 | -554.8 | -98.0 | 58.0 | 0.5 | 0.48 |
| screen | pdc_z15_h24 | BTCUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.01 | -11.1 | -277.2 | -479.7 | -164.1 | 42.0 | 0.524 | 0.52 |
| screen | pdc_z15_h24 | DOTUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.005 | -14.4 | -359.5 | -377.6 | -57.4 | 27.0 | 0.333 | 0.16 |
| screen | pdc_z15_h24 | ETHUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.01 | -13.7 | -342.1 | -521.8 | -110.9 | 53.0 | 0.472 | 0.4 |
| screen | pdc_z15_h24 | LTCUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.005 | -19.4 | -484.9 | -537.2 | -79.9 | 46.0 | 0.37 | 0.2 |
| screen | pdc_z15_h24 | SOLUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.005 | -20.1 | -442.5 | -489.2 | -106.0 | 33.0 | 0.303 | 0.182 |
| screen | pdc_z15_h24 | XRPUSD | H1 | build_pdc_revert | {"z": 1.5, "hold": 24, "atr_mult": 1.5} | 0.005 | -15.2 | -333.6 | -423.0 | -103.8 | 42.0 | 0.429 | 0.364 |
| screen | pdc_z20 | ADAUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.0075 | -17.9 | -447.7 | -511.2 | -110.8 | 15.0 | 0.267 | 0.12 |
| screen | pdc_z20 | BNBUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.0075 | 5.9 | 148.6 | -452.3 | -118.8 | 22.0 | 0.591 | 0.32 |
| screen | pdc_z20 | BTCUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.0075 | -18.2 | -454.5 | -533.9 | -123.7 | 15.0 | 0.2 | 0.12 |
| screen | pdc_z20 | DOTUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.0075 | -14.1 | -353.2 | -387.9 | -97.3 | 14.0 | 0.214 | 0.08 |
| screen | pdc_z20 | ETHUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.01 | -22.5 | -561.4 | -572.3 | -104.1 | 15.0 | 0.2 | 0.08 |
| screen | pdc_z20 | LTCUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.02 | -0.2 | -5.8 | -583.7 | -277.0 | 20.0 | 0.6 | 0.16 |
| screen | pdc_z20 | SOLUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.02 | -0.8 | -18.3 | -573.1 | -198.5 | 13.0 | 0.538 | 0.273 |
| screen | pdc_z20 | XRPUSD | H1 | build_pdc_revert | {"z": 2.0} | 0.01 | -20.3 | -445.9 | -541.0 | -100.0 | 19.0 | 0.316 | 0.182 |
| refine | pdm_h12_t05_h12 | ADAUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | 0.0025 | -11.9 | -298.2 | -435.4 | -39.4 | 108.0 | 0.398 | 0.36 |
| refine | pdm_h12_t05_h12 | BNBUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | nan | -28.0 | -700.7 | -885.9 | -32.2 | 144.0 | 0.354 | 0.36 |
| refine | pdm_h12_t05_h12 | BTCUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | 0.0025 | 4.4 | 109.2 | -270.4 | -24.6 | 134.0 | 0.433 | 0.44 |
| refine | pdm_h12_t05_h12 | DOTUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | nan | -31.4 | -785.4 | -875.9 | -35.9 | 130.0 | 0.269 | 0.28 |
| refine | pdm_h12_t05_h12 | ETHUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | 0.005 | 19.6 | 489.1 | -427.2 | -56.7 | 133.0 | 0.391 | 0.52 |
| refine | pdm_h12_t05_h12 | LTCUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | nan | -48.3 | -1208.5 | -1208.5 | -47.4 | 147.0 | 0.306 | 0.24 |
| refine | pdm_h12_t05_h12 | SOLUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | 0.0025 | -8.9 | -195.4 | -317.7 | -24.8 | 132.0 | 0.439 | 0.409 |
| refine | pdm_h12_t05_h12 | XRPUSD | H1 | build_pd_mom | {"hour": 12, "hold": 12} | 0.005 | -12.5 | -275.5 | -594.2 | -93.1 | 121.0 | 0.405 | 0.5 |
| refine | pdm_h16_t05_h8 | ADAUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.0025 | -14.1 | -351.5 | -573.2 | -31.3 | 146.0 | 0.363 | 0.4 |
| refine | pdm_h16_t05_h8 | BNBUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.0025 | -18.0 | -451.2 | -558.7 | -31.6 | 191.0 | 0.414 | 0.4 |
| refine | pdm_h16_t05_h8 | BTCUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.005 | 10.4 | 259.2 | -595.0 | -72.5 | 208.0 | 0.495 | 0.48 |
| refine | pdm_h16_t05_h8 | DOTUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | nan | -55.7 | -1391.4 | -1452.9 | -49.8 | 183.0 | 0.219 | 0.08 |
| refine | pdm_h16_t05_h8 | ETHUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.0025 | 6.7 | 167.7 | -435.9 | -49.5 | 198.0 | 0.429 | 0.48 |
| refine | pdm_h16_t05_h8 | LTCUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | nan | -66.4 | -1660.6 | -1668.7 | -33.0 | 196.0 | 0.26 | 0.16 |
| refine | pdm_h16_t05_h8 | SOLUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.0025 | -9.7 | -213.0 | -335.5 | -30.2 | 183.0 | 0.464 | 0.364 |
| refine | pdm_h16_t05_h8 | XRPUSD | H1 | build_pd_mom | {"hour": 16, "hold": 8} | 0.0025 | -7.7 | -169.4 | -420.0 | -39.9 | 173.0 | 0.405 | 0.318 |
| refine | pdm_t05_h24 | ADAUSD | H1 | build_pd_mom | {} | 0.0025 | -9.0 | -224.6 | -512.5 | -25.0 | 192.0 | 0.406 | 0.36 |
| refine | pdm_t05_h24 | BNBUSD | H1 | build_pd_mom | {} | nan | -49.3 | -1233.4 | -1255.9 | -79.8 | 259.0 | 0.363 | 0.28 |
| refine | pdm_t05_h24 | BTCUSD | H1 | build_pd_mom | {} | 0.005 | 50.4 | 1259.7 | -512.8 | -100.1 | 274.0 | 0.427 | 0.6 |
| refine | pdm_t05_h24 | DOTUSD | H1 | build_pd_mom | {} | nan | -50.5 | -1261.5 | -1461.6 | -29.1 | 219.0 | 0.26 | 0.24 |
| refine | pdm_t05_h24 | ETHUSD | H1 | build_pd_mom | {} | 0.0025 | 3.4 | 86.2 | -436.7 | -38.6 | 280.0 | 0.4 | 0.52 |
| refine | pdm_t05_h24 | LTCUSD | H1 | build_pd_mom | {} | nan | -98.5 | -2463.7 | -2468.3 | -106.2 | 250.0 | 0.24 | 0.12 |
| refine | pdm_t05_h24 | SOLUSD | H1 | build_pd_mom | {} | nan | -28.1 | -618.2 | -757.7 | -36.5 | 241.0 | 0.373 | 0.364 |
| refine | pdm_t05_h24 | XRPUSD | H1 | build_pd_mom | {} | 0.0025 | 9.7 | 213.0 | -376.6 | -25.0 | 234.0 | 0.393 | 0.455 |
| refine | pdm_t05_h24_fade | ADAUSD | H1 | build_pd_mom | {"fade": true} | nan | -56.2 | -1403.8 | -1413.5 | -145.3 | 194.0 | 0.304 | 0.16 |
| refine | pdm_t05_h24_fade | BNBUSD | H1 | build_pd_mom | {"fade": true} | nan | -68.1 | -1702.9 | -1790.5 | -74.0 | 260.0 | 0.373 | 0.12 |
| refine | pdm_t05_h24_fade | BTCUSD | H1 | build_pd_mom | {"fade": true} | nan | -17.5 | -437.6 | -679.1 | -39.6 | 262.0 | 0.393 | 0.32 |
| refine | pdm_t05_h24_fade | DOTUSD | H1 | build_pd_mom | {"fade": true} | nan | -102.5 | -2563.1 | -2587.0 | -539.2 | 220.0 | 0.223 | 0.08 |
| refine | pdm_t05_h24_fade | ETHUSD | H1 | build_pd_mom | {"fade": true} | nan | -19.9 | -496.8 | -704.1 | -26.7 | 281.0 | 0.423 | 0.48 |
| refine | pdm_t05_h24_fade | LTCUSD | H1 | build_pd_mom | {"fade": true} | nan | -97.2 | -2430.7 | -2478.5 | -35.1 | 252.0 | 0.266 | 0.08 |
| refine | pdm_t05_h24_fade | SOLUSD | H1 | build_pd_mom | {"fade": true} | nan | -33.5 | -736.5 | -832.1 | -36.9 | 244.0 | 0.41 | 0.227 |
| refine | pdm_t05_h24_fade | XRPUSD | H1 | build_pd_mom | {"fade": true} | nan | -38.3 | -842.5 | -1032.3 | -117.8 | 236.0 | 0.39 | 0.318 |
| refine | pdm_t10_h24 | ADAUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.0025 | 12.4 | 309.2 | -185.4 | -25.0 | 61.0 | 0.508 | 0.44 |
| refine | pdm_t10_h24 | BNBUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.0025 | -1.9 | -46.8 | -398.8 | -25.0 | 75.0 | 0.4 | 0.36 |
| refine | pdm_t10_h24 | BTCUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.0075 | 48.8 | 1219.0 | -462.5 | -75.0 | 94.0 | 0.436 | 0.56 |
| refine | pdm_t10_h24 | DOTUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.0025 | -14.5 | -361.3 | -527.1 | -25.0 | 60.0 | 0.267 | 0.24 |
| refine | pdm_t10_h24 | ETHUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.01 | 89.7 | 2241.4 | -511.4 | -100.0 | 93.0 | 0.495 | 0.64 |
| refine | pdm_t10_h24 | LTCUSD | H1 | build_pd_mom | {"thresh": 1.0} | nan | -29.9 | -746.3 | -801.4 | -106.2 | 87.0 | 0.287 | 0.16 |
| refine | pdm_t10_h24 | SOLUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.005 | -2.6 | -57.0 | -529.7 | -49.9 | 76.0 | 0.395 | 0.591 |
| refine | pdm_t10_h24 | XRPUSD | H1 | build_pd_mom | {"thresh": 1.0} | 0.005 | 7.2 | 159.4 | -466.1 | -50.0 | 78.0 | 0.333 | 0.364 |
| refine | pdm_t10_h24_fade | ADAUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | nan | -24.8 | -620.6 | -633.3 | -145.3 | 61.0 | 0.262 | 0.16 |
| refine | pdm_t10_h24_fade | BNBUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.0025 | -19.2 | -481.1 | -586.1 | -25.0 | 75.0 | 0.347 | 0.32 |
| refine | pdm_t10_h24_fade | BTCUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.0075 | 5.0 | 126.2 | -541.1 | -118.8 | 94.0 | 0.436 | 0.44 |
| refine | pdm_t10_h24_fade | DOTUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.0025 | -17.3 | -432.5 | -526.9 | -25.0 | 60.0 | 0.25 | 0.2 |
| refine | pdm_t10_h24_fade | ETHUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.0025 | -9.3 | -233.2 | -318.3 | -26.7 | 93.0 | 0.376 | 0.36 |
| refine | pdm_t10_h24_fade | LTCUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | nan | -29.3 | -733.4 | -740.5 | -25.0 | 87.0 | 0.264 | 0.16 |
| refine | pdm_t10_h24_fade | SOLUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.0025 | -5.0 | -109.9 | -291.0 | -36.9 | 76.0 | 0.461 | 0.409 |
| refine | pdm_t10_h24_fade | XRPUSD | H1 | build_pd_mom | {"thresh": 1.0, "fade": true} | 0.005 | 25.7 | 565.2 | -429.4 | -235.6 | 79.0 | 0.506 | 0.409 |
| refine | pw_d1_break_trail2 | ADAUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.0025 | -6.6 | -163.9 | -291.3 | -23.4 | 15.0 | 0.133 | 0.12 |
| refine | pw_d1_break_trail2 | BNBUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | 7.2 | 179.7 | -445.7 | -99.4 | 39.0 | 0.308 | 0.4 |
| refine | pw_d1_break_trail2 | BTCUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | 14.8 | 371.0 | -236.0 | -82.7 | 30.0 | 0.4 | 0.52 |
| refine | pw_d1_break_trail2 | DOTUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.0025 | -11.3 | -283.4 | -321.4 | -25.7 | 23.0 | 0.261 | 0.08 |
| refine | pw_d1_break_trail2 | ETHUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.0075 | -2.4 | -60.4 | -579.1 | -102.1 | 46.0 | 0.304 | 0.48 |
| refine | pw_d1_break_trail2 | LTCUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | nan | -21.8 | -545.1 | -628.8 | -83.9 | 48.0 | 0.271 | 0.36 |
| refine | pw_d1_break_trail2 | SOLUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.0075 | 9.6 | 210.9 | -534.7 | -118.8 | 36.0 | 0.361 | 0.5 |
| refine | pw_d1_break_trail2 | XRPUSD | D1 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | -18.7 | -410.3 | -521.7 | -112.8 | 43.0 | 0.209 | 0.318 |
| refine | pw_d1_sfp_trail2 | ADAUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.005 | 26.5 | 662.8 | -556.4 | -156.7 | 60.0 | 0.4 | 0.4 |
| refine | pw_d1_sfp_trail2 | BNBUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 5.6 | 140.8 | -308.2 | -51.3 | 78.0 | 0.423 | 0.36 |
| refine | pw_d1_sfp_trail2 | BTCUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 2.5 | 61.6 | -329.1 | -55.5 | 41.0 | 0.244 | 0.32 |
| refine | pw_d1_sfp_trail2 | DOTUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.005 | 11.7 | 292.2 | -575.4 | -186.6 | 64.0 | 0.359 | 0.32 |
| refine | pw_d1_sfp_trail2 | ETHUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 9.9 | 248.1 | -378.7 | -79.2 | 77.0 | 0.351 | 0.52 |
| refine | pw_d1_sfp_trail2 | LTCUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | -0.6 | -15.5 | -428.5 | -67.4 | 70.0 | 0.4 | 0.44 |
| refine | pw_d1_sfp_trail2 | SOLUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 10.2 | 223.9 | -358.5 | -119.4 | 60.0 | 0.333 | 0.455 |
| refine | pw_d1_sfp_trail2 | XRPUSD | D1 | build_pw_sfp | {"trail_mult": 2.0} | 0.005 | 3.6 | 78.1 | -559.3 | -167.0 | 58.0 | 0.397 | 0.409 |
| refine | pw_h1_sfp_trail2 | ADAUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | nan | -29.8 | -745.0 | -839.0 | -32.7 | 86.0 | 0.198 | 0.2 |
| refine | pw_h1_sfp_trail2 | BNBUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | nan | -27.1 | -676.4 | -822.2 | -28.2 | 95.0 | 0.284 | 0.2 |
| refine | pw_h1_sfp_trail2 | BTCUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | -4.2 | -105.8 | -416.2 | -102.5 | 92.0 | 0.207 | 0.32 |
| refine | pw_h1_sfp_trail2 | DOTUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | nan | -24.4 | -610.1 | -751.5 | -26.5 | 88.0 | 0.193 | 0.16 |
| refine | pw_h1_sfp_trail2 | ETHUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 38.6 | 965.1 | -386.3 | -116.5 | 87.0 | 0.368 | 0.52 |
| refine | pw_h1_sfp_trail2 | LTCUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | nan | -41.6 | -1040.8 | -1040.8 | -91.5 | 93.0 | 0.194 | 0.2 |
| refine | pw_h1_sfp_trail2 | SOLUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | 0.005 | 18.2 | 401.0 | -466.1 | -58.1 | 75.0 | 0.36 | 0.409 |
| refine | pw_h1_sfp_trail2 | XRPUSD | H1 | build_pw_sfp | {"trail_mult": 2.0} | nan | -23.5 | -517.7 | -649.2 | -45.1 | 75.0 | 0.24 | 0.227 |
| refine | pw_h1_sfp_trail3 | ADAUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | nan | -26.5 | -661.6 | -851.5 | -40.6 | 86.0 | 0.233 | 0.24 |
| refine | pw_h1_sfp_trail3 | BNBUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | nan | -30.1 | -753.3 | -974.3 | -46.8 | 94.0 | 0.234 | 0.24 |
| refine | pw_h1_sfp_trail3 | BTCUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | -5.3 | -133.4 | -556.3 | -102.5 | 92.0 | 0.239 | 0.36 |
| refine | pw_h1_sfp_trail3 | DOTUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | nan | -18.4 | -460.7 | -616.6 | -38.0 | 87.0 | 0.253 | 0.2 |
| refine | pw_h1_sfp_trail3 | ETHUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | 33.5 | 836.7 | -356.5 | -194.1 | 87.0 | 0.368 | 0.48 |
| refine | pw_h1_sfp_trail3 | LTCUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | nan | -45.3 | -1132.2 | -1132.2 | -91.5 | 93.0 | 0.172 | 0.2 |
| refine | pw_h1_sfp_trail3 | SOLUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | 0.005 | 21.3 | 468.6 | -488.7 | -88.7 | 75.0 | 0.32 | 0.364 |
| refine | pw_h1_sfp_trail3 | XRPUSD | H1 | build_pw_sfp | {"trail_mult": 3.0} | nan | -29.2 | -641.7 | -702.1 | -65.8 | 75.0 | 0.227 | 0.318 |
| screen | pw_h4_break_rr2 | ADAUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.005 | 12.2 | 303.9 | -437.8 | -88.0 | 73.0 | 0.452 | 0.52 |
| screen | pw_h4_break_rr2 | BNBUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | nan | -31.6 | -789.3 | -797.8 | -55.0 | 83.0 | 0.241 | 0.24 |
| screen | pw_h4_break_rr2 | BTCUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.005 | 10.3 | 257.1 | -416.6 | -65.3 | 80.0 | 0.362 | 0.6 |
| screen | pw_h4_break_rr2 | DOTUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.0025 | -20.1 | -502.5 | -587.8 | -37.2 | 66.0 | 0.333 | 0.28 |
| screen | pw_h4_break_rr2 | ETHUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.0025 | -9.8 | -245.2 | -461.1 | -58.6 | 80.0 | 0.3 | 0.4 |
| screen | pw_h4_break_rr2 | LTCUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | nan | -33.9 | -847.8 | -853.8 | -35.7 | 80.0 | 0.275 | 0.12 |
| screen | pw_h4_break_rr2 | SOLUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.0025 | -0.1 | -2.1 | -390.9 | -42.5 | 71.0 | 0.38 | 0.5 |
| screen | pw_h4_break_rr2 | XRPUSD | H4 | build_pw_sfp | {"mode": "break", "rr": 2.0} | 0.005 | 10.5 | 231.2 | -537.0 | -77.0 | 71.0 | 0.394 | 0.5 |
| screen | pw_h4_break_trail2 | ADAUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.0025 | 7.4 | 184.0 | -360.9 | -43.9 | 52.0 | 0.308 | 0.32 |
| screen | pw_h4_break_trail2 | BNBUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | nan | -29.7 | -742.3 | -750.8 | -49.6 | 81.0 | 0.148 | 0.16 |
| screen | pw_h4_break_trail2 | BTCUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | 24.1 | 601.4 | -404.2 | -81.7 | 75.0 | 0.333 | 0.48 |
| screen | pw_h4_break_trail2 | DOTUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | nan | -20.6 | -514.9 | -604.7 | -44.2 | 71.0 | 0.239 | 0.2 |
| screen | pw_h4_break_trail2 | ETHUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | 10.3 | 258.4 | -594.9 | -97.5 | 77.0 | 0.273 | 0.52 |
| screen | pw_h4_break_trail2 | LTCUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | nan | -43.7 | -1092.4 | -1092.4 | -41.9 | 79.0 | 0.127 | 0.16 |
| screen | pw_h4_break_trail2 | SOLUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | -1.1 | -23.2 | -546.1 | -84.7 | 70.0 | 0.329 | 0.409 |
| screen | pw_h4_break_trail2 | XRPUSD | H4 | build_pw_sfp | {"mode": "break", "trail_mult": 2.0} | 0.005 | 32.7 | 720.2 | -587.3 | -125.0 | 68.0 | 0.309 | 0.455 |
| refine | pw_h4_sfp_rr3 | ADAUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.0025 | -12.7 | -318.4 | -446.5 | -59.3 | 72.0 | 0.389 | 0.24 |
| refine | pw_h4_sfp_rr3 | BNBUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.005 | -7.7 | -193.7 | -516.7 | -97.5 | 89.0 | 0.371 | 0.52 |
| refine | pw_h4_sfp_rr3 | BTCUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.0025 | -7.7 | -192.1 | -338.4 | -53.1 | 77.0 | 0.234 | 0.52 |
| refine | pw_h4_sfp_rr3 | DOTUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.005 | -9.5 | -237.6 | -583.9 | -113.8 | 72.0 | 0.375 | 0.36 |
| refine | pw_h4_sfp_rr3 | ETHUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.0025 | 11.5 | 288.7 | -318.5 | -78.9 | 85.0 | 0.329 | 0.64 |
| refine | pw_h4_sfp_rr3 | LTCUSD | H4 | build_pw_sfp | {"rr": 3.0} | nan | -27.2 | -680.8 | -687.5 | -90.0 | 87.0 | 0.333 | 0.32 |
| refine | pw_h4_sfp_rr3 | SOLUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.0025 | 10.4 | 228.4 | -339.2 | -57.4 | 71.0 | 0.394 | 0.5 |
| refine | pw_h4_sfp_rr3 | XRPUSD | H4 | build_pw_sfp | {"rr": 3.0} | 0.0025 | -15.7 | -345.1 | -505.5 | -66.9 | 70.0 | 0.243 | 0.409 |
| refine | pw_h4_sfp_trail15 | ADAUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.0025 | -6.2 | -154.8 | -393.6 | -65.5 | 72.0 | 0.292 | 0.28 |
| refine | pw_h4_sfp_trail15 | BNBUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.0025 | -3.3 | -81.3 | -406.5 | -45.4 | 89.0 | 0.36 | 0.44 |
| refine | pw_h4_sfp_trail15 | BTCUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.0025 | -9.3 | -232.5 | -571.1 | -80.2 | 77.0 | 0.299 | 0.36 |
| refine | pw_h4_sfp_trail15 | DOTUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.0025 | -8.7 | -217.1 | -392.8 | -41.5 | 81.0 | 0.296 | 0.36 |
| refine | pw_h4_sfp_trail15 | ETHUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.0025 | 15.8 | 395.7 | -403.9 | -69.5 | 87.0 | 0.356 | 0.48 |
| refine | pw_h4_sfp_trail15 | LTCUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | nan | -44.0 | -1100.7 | -1100.7 | -90.0 | 90.0 | 0.2 | 0.12 |
| refine | pw_h4_sfp_trail15 | SOLUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | 0.005 | 89.2 | 1963.0 | -452.3 | -96.5 | 71.0 | 0.408 | 0.5 |
| refine | pw_h4_sfp_trail15 | XRPUSD | H4 | build_pw_sfp | {"trail_mult": 1.5} | nan | -25.7 | -564.8 | -620.0 | -49.7 | 72.0 | 0.264 | 0.227 |
| screen | pw_h4_sfp_trail2 | ADAUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | -7.5 | -188.2 | -351.4 | -65.5 | 72.0 | 0.306 | 0.36 |
| screen | pw_h4_sfp_trail2 | BNBUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 2.5 | 62.6 | -385.9 | -49.0 | 89.0 | 0.348 | 0.32 |
| screen | pw_h4_sfp_trail2 | BTCUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 4.8 | 119.3 | -453.9 | -224.4 | 77.0 | 0.273 | 0.32 |
| screen | pw_h4_sfp_trail2 | DOTUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | -10.4 | -259.6 | -451.9 | -55.4 | 81.0 | 0.296 | 0.32 |
| screen | pw_h4_sfp_trail2 | ETHUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.0025 | 9.8 | 245.9 | -578.6 | -111.0 | 87.0 | 0.264 | 0.48 |
| screen | pw_h4_sfp_trail2 | LTCUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | nan | -37.3 | -932.9 | -985.1 | -90.0 | 90.0 | 0.222 | 0.12 |
| screen | pw_h4_sfp_trail2 | SOLUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | 0.005 | 101.1 | 2223.7 | -473.2 | -131.9 | 71.0 | 0.366 | 0.591 |
| screen | pw_h4_sfp_trail2 | XRPUSD | H4 | build_pw_sfp | {"trail_mult": 2.0} | nan | -28.3 | -621.9 | -652.0 | -63.8 | 72.0 | 0.236 | 0.182 |
| refine | pw_h4_sfp_trail2_h60 | ADAUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.0025 | -7.5 | -188.2 | -351.4 | -65.5 | 72.0 | 0.306 | 0.36 |
| refine | pw_h4_sfp_trail2_h60 | BNBUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.0025 | 2.5 | 62.6 | -385.9 | -49.0 | 89.0 | 0.348 | 0.32 |
| refine | pw_h4_sfp_trail2_h60 | BTCUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.0025 | 4.8 | 119.3 | -453.9 | -224.4 | 77.0 | 0.273 | 0.32 |
| refine | pw_h4_sfp_trail2_h60 | DOTUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.0025 | -10.4 | -259.6 | -451.9 | -55.4 | 81.0 | 0.296 | 0.32 |
| refine | pw_h4_sfp_trail2_h60 | ETHUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.0025 | 9.8 | 245.9 | -578.6 | -111.0 | 87.0 | 0.264 | 0.48 |
| refine | pw_h4_sfp_trail2_h60 | LTCUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | nan | -37.3 | -932.9 | -985.1 | -90.0 | 90.0 | 0.222 | 0.12 |
| refine | pw_h4_sfp_trail2_h60 | SOLUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | 0.005 | 101.1 | 2223.7 | -473.2 | -131.9 | 71.0 | 0.366 | 0.591 |
| refine | pw_h4_sfp_trail2_h60 | XRPUSD | H4 | build_pw_sfp | {"trail_mult": 2.0, "max_hold": 60} | nan | -28.3 | -621.9 | -652.0 | -63.8 | 72.0 | 0.236 | 0.182 |
| refine | pw_h4_sfp_trail3 | ADAUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | -3.6 | -90.7 | -404.2 | -65.5 | 72.0 | 0.319 | 0.4 |
| refine | pw_h4_sfp_trail3 | BNBUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | 3.4 | 86.2 | -390.6 | -55.2 | 89.0 | 0.315 | 0.36 |
| refine | pw_h4_sfp_trail3 | BTCUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | 17.7 | 443.0 | -497.5 | -261.6 | 77.0 | 0.156 | 0.36 |
| refine | pw_h4_sfp_trail3 | DOTUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | -7.2 | -179.1 | -359.6 | -82.9 | 80.0 | 0.312 | 0.36 |
| refine | pw_h4_sfp_trail3 | ETHUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | nan | -3.2 | -80.5 | -814.6 | -186.6 | 86.0 | 0.267 | 0.48 |
| refine | pw_h4_sfp_trail3 | LTCUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | nan | -26.8 | -669.0 | -721.8 | -90.1 | 90.0 | 0.244 | 0.24 |
| refine | pw_h4_sfp_trail3 | SOLUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | 35.5 | 781.3 | -366.8 | -96.6 | 70.0 | 0.3 | 0.5 |
| refine | pw_h4_sfp_trail3 | XRPUSD | H4 | build_pw_sfp | {"trail_mult": 3.0} | 0.0025 | -14.8 | -325.8 | -525.2 | -66.1 | 72.0 | 0.222 | 0.409 |
| screen | pw_sfp_rr2 | ADAUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | -16.8 | -419.6 | -505.1 | -25.2 | 81.0 | 0.469 | 0.36 |
| screen | pw_sfp_rr2 | BNBUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | -20.4 | -510.0 | -569.0 | -49.1 | 92.0 | 0.478 | 0.32 |
| screen | pw_sfp_rr2 | BTCUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | -15.4 | -384.7 | -497.2 | -54.7 | 92.0 | 0.283 | 0.44 |
| screen | pw_sfp_rr2 | DOTUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | -7.8 | -195.3 | -219.2 | -40.9 | 58.0 | 0.483 | 0.4 |
| screen | pw_sfp_rr2 | ETHUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | 2.1 | 53.6 | -308.2 | -78.3 | 87.0 | 0.391 | 0.48 |
| screen | pw_sfp_rr2 | LTCUSD | H1 | build_pw_sfp | {"rr": 2.0} | nan | -34.6 | -866.1 | -866.1 | -91.5 | 69.0 | 0.348 | 0.24 |
| screen | pw_sfp_rr2 | SOLUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0075 | -5.9 | -130.2 | -599.6 | -123.1 | 75.0 | 0.493 | 0.455 |
| screen | pw_sfp_rr2 | XRPUSD | H1 | build_pw_sfp | {"rr": 2.0} | 0.0025 | -22.6 | -496.4 | -551.2 | -46.4 | 74.0 | 0.365 | 0.227 |
| screen | relstr_h4_lb30_h6 | ADAUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | nan | -25.5 | -637.4 | -644.6 | -47.5 | 150.0 | 0.307 | 0.2 |
| screen | relstr_h4_lb30_h6 | BNBUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | nan | -32.7 | -817.0 | -930.0 | -49.8 | 292.0 | 0.387 | 0.28 |
| screen | relstr_h4_lb30_h6 | DOTUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | nan | -68.1 | -1702.1 | -1749.5 | -62.7 | 234.0 | 0.218 | 0.24 |
| screen | relstr_h4_lb30_h6 | ETHUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | 0.0025 | -15.1 | -376.8 | -491.9 | -57.9 | 327.0 | 0.41 | 0.36 |
| screen | relstr_h4_lb30_h6 | LTCUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | nan | -108.2 | -2705.6 | -2705.6 | -57.4 | 342.0 | 0.219 | 0.0 |
| screen | relstr_h4_lb30_h6 | SOLUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | nan | -21.0 | -462.4 | -616.9 | -46.8 | 282.0 | 0.422 | 0.591 |
| screen | relstr_h4_lb30_h6 | XRPUSD | H4 | build_rel_strength | {"lb": 30, "hold": 6} | 0.0025 | 1.9 | 41.7 | -300.7 | -50.0 | 285.0 | 0.411 | 0.545 |
| screen | relstr_lb120_h24 | ADAUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -36.0 | -899.9 | -1425.7 | -89.0 | 347.0 | 0.343 | 0.36 |
| screen | relstr_lb120_h24 | BNBUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -81.7 | -2043.6 | -2043.6 | -80.7 | 407.0 | 0.319 | 0.24 |
| screen | relstr_lb120_h24 | DOTUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -94.0 | -2350.0 | -2454.0 | -80.2 | 391.0 | 0.23 | 0.2 |
| screen | relstr_lb120_h24 | ETHUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -60.9 | -1521.9 | -1769.0 | -98.0 | 488.0 | 0.311 | 0.32 |
| screen | relstr_lb120_h24 | LTCUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -210.3 | -5258.4 | -5263.0 | -94.1 | 480.0 | 0.194 | 0.0 |
| screen | relstr_lb120_h24 | SOLUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -67.5 | -1485.3 | -1742.1 | -68.8 | 413.0 | 0.329 | 0.273 |
| screen | relstr_lb120_h24 | XRPUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24} | nan | -15.0 | -330.8 | -695.6 | -92.6 | 405.0 | 0.368 | 0.5 |
| screen | relstr_lb120_nobtc | ADAUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -70.8 | -1771.2 | -2182.9 | -120.7 | 543.0 | 0.239 | 0.24 |
| screen | relstr_lb120_nobtc | BNBUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -92.4 | -2309.7 | -2309.7 | -103.4 | 800.0 | 0.299 | 0.2 |
| screen | relstr_lb120_nobtc | DOTUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -169.2 | -4230.0 | -4539.2 | -136.7 | 638.0 | 0.163 | 0.2 |
| screen | relstr_lb120_nobtc | ETHUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -17.1 | -427.3 | -982.4 | -89.9 | 784.0 | 0.362 | 0.52 |
| screen | relstr_lb120_nobtc | LTCUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -385.7 | -9641.3 | -9641.3 | -155.3 | 910.0 | 0.113 | 0.04 |
| screen | relstr_lb120_nobtc | SOLUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -96.3 | -2119.2 | -2338.1 | -123.9 | 690.0 | 0.243 | 0.136 |
| screen | relstr_lb120_nobtc | XRPUSD | H1 | build_rel_strength | {"lb": 120, "hold": 24, "need_btc": false} | nan | -75.9 | -1669.2 | -2031.9 | -128.9 | 704.0 | 0.266 | 0.227 |
| screen | relstr_lb48_h12 | ADAUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -69.2 | -1730.7 | -1873.6 | -104.8 | 595.0 | 0.351 | 0.24 |
| screen | relstr_lb48_h12 | BNBUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -163.1 | -4077.3 | -4077.3 | -96.2 | 749.0 | 0.306 | 0.04 |
| screen | relstr_lb48_h12 | DOTUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -198.2 | -4955.0 | -5150.7 | -81.0 | 677.0 | 0.216 | 0.16 |
| screen | relstr_lb48_h12 | ETHUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -46.5 | -1162.7 | -1343.8 | -98.1 | 809.0 | 0.366 | 0.36 |
| screen | relstr_lb48_h12 | LTCUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -291.5 | -7287.6 | -7304.4 | -77.2 | 769.0 | 0.228 | 0.0 |
| screen | relstr_lb48_h12 | SOLUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -95.8 | -2108.3 | -2192.6 | -72.9 | 708.0 | 0.353 | 0.273 |
| screen | relstr_lb48_h12 | XRPUSD | H1 | build_rel_strength | {"lb": 48, "hold": 12} | nan | -68.5 | -1507.6 | -1642.2 | -87.2 | 687.0 | 0.361 | 0.318 |
| screen | round_h1 | ADAUSD | H1 | build_round_bounce | {} | nan | -84.1 | -2102.5 | -2141.4 | -67.0 | 296.0 | 0.314 | 0.16 |
| screen | round_h1 | BNBUSD | H1 | build_round_bounce | {} | nan | -58.5 | -1463.7 | -1593.9 | -68.3 | 317.0 | 0.407 | 0.28 |
| screen | round_h1 | BTCUSD | H1 | build_round_bounce | {} | nan | -79.9 | -1998.6 | -2058.8 | -90.0 | 1390.0 | 0.363 | 0.32 |
| screen | round_h1 | DOTUSD | H1 | build_round_bounce | {} | nan | -35.4 | -884.6 | -1272.9 | -104.9 | 195.0 | 0.364 | 0.16 |
| screen | round_h1 | ETHUSD | H1 | build_round_bounce | {} | nan | -108.0 | -2699.8 | -3130.6 | -86.0 | 739.0 | 0.35 | 0.24 |
| screen | round_h1 | LTCUSD | H1 | build_round_bounce | {} | nan | -131.4 | -3284.5 | -3306.7 | -91.7 | 464.0 | 0.377 | 0.12 |
| screen | round_h1 | SOLUSD | H1 | build_round_bounce | {} | nan | -40.5 | -890.6 | -1034.9 | -72.8 | 343.0 | 0.399 | 0.318 |
| screen | round_h1 | XRPUSD | H1 | build_round_bounce | {} | nan | -88.7 | -1951.6 | -1991.8 | -93.9 | 523.0 | 0.377 | 0.227 |
| screen | round_h1_rr15 | ADAUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -100.3 | -2507.5 | -2547.4 | -76.1 | 393.0 | 0.369 | 0.08 |
| screen | round_h1_rr15 | BNBUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -78.3 | -1958.7 | -2066.3 | -72.6 | 420.0 | 0.452 | 0.16 |
| screen | round_h1_rr15 | BTCUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -92.7 | -2316.7 | -2434.4 | -99.0 | 1982.0 | 0.395 | 0.32 |
| screen | round_h1_rr15 | DOTUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -28.2 | -705.3 | -1120.9 | -104.9 | 243.0 | 0.444 | 0.16 |
| screen | round_h1_rr15 | ETHUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -109.7 | -2741.3 | -3058.8 | -109.2 | 1010.0 | 0.405 | 0.28 |
| screen | round_h1_rr15 | LTCUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -187.7 | -4692.6 | -4714.3 | -102.5 | 619.0 | 0.404 | 0.08 |
| screen | round_h1_rr15 | SOLUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -81.7 | -1796.4 | -1800.0 | -89.4 | 492.0 | 0.421 | 0.364 |
| screen | round_h1_rr15 | XRPUSD | H1 | build_round_bounce | {"rr": 1.5, "tol": 0.3} | nan | -118.1 | -2597.5 | -2623.6 | -117.6 | 744.0 | 0.423 | 0.227 |
| screen | round_h4 | ADAUSD | H4 | build_round_bounce | {} | 0.0025 | -4.0 | -100.7 | -276.8 | -48.4 | 71.0 | 0.408 | 0.4 |
| screen | round_h4 | BNBUSD | H4 | build_round_bounce | {} | 0.0025 | -6.7 | -167.4 | -393.7 | -49.8 | 132.0 | 0.394 | 0.32 |
| screen | round_h4 | BTCUSD | H4 | build_round_bounce | {} | nan | -37.1 | -928.1 | -1213.7 | -46.4 | 611.0 | 0.334 | 0.28 |
| screen | round_h4 | DOTUSD | H4 | build_round_bounce | {} | 0.0025 | -17.1 | -428.3 | -544.1 | -51.5 | 83.0 | 0.361 | 0.2 |
| screen | round_h4 | ETHUSD | H4 | build_round_bounce | {} | 0.0025 | 12.4 | 310.8 | -466.4 | -66.3 | 338.0 | 0.411 | 0.48 |
| screen | round_h4 | LTCUSD | H4 | build_round_bounce | {} | nan | -86.4 | -2160.9 | -2241.4 | -68.5 | 270.0 | 0.315 | 0.12 |
| screen | round_h4 | SOLUSD | H4 | build_round_bounce | {} | nan | -25.5 | -561.7 | -702.7 | -49.3 | 190.0 | 0.347 | 0.273 |
| screen | round_h4 | XRPUSD | H4 | build_round_bounce | {} | nan | -40.1 | -881.4 | -1036.6 | -72.9 | 252.0 | 0.349 | 0.364 |
| screen | rsi2_h4_notrend | ADAUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -64.5 | -1612.0 | -1635.5 | -65.4 | 284.0 | 0.366 | 0.12 |
| screen | rsi2_h4_notrend | BNBUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -74.5 | -1862.3 | -1926.6 | -93.8 | 590.0 | 0.539 | 0.12 |
| screen | rsi2_h4_notrend | BTCUSD | H4 | build_rsi2_mr | {"use_trend": false} | 0.0025 | -12.7 | -318.0 | -399.5 | -53.7 | 387.0 | 0.62 | 0.32 |
| screen | rsi2_h4_notrend | DOTUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -137.6 | -3441.2 | -3441.2 | -73.9 | 431.0 | 0.246 | 0.04 |
| screen | rsi2_h4_notrend | ETHUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -28.7 | -717.7 | -803.5 | -73.3 | 614.0 | 0.632 | 0.36 |
| screen | rsi2_h4_notrend | LTCUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -164.4 | -4109.2 | -4119.7 | -66.9 | 587.0 | 0.31 | 0.0 |
| screen | rsi2_h4_notrend | SOLUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -57.3 | -1261.5 | -1304.4 | -60.9 | 524.0 | 0.584 | 0.091 |
| screen | rsi2_h4_notrend | XRPUSD | H4 | build_rsi2_mr | {"use_trend": false} | nan | -74.5 | -1638.1 | -1706.6 | -113.2 | 529.0 | 0.543 | 0.091 |
| screen | rsi2_h4_trend | ADAUSD | H4 | build_rsi2_mr | {} | nan | -23.6 | -589.0 | -630.0 | -40.6 | 102.0 | 0.304 | 0.2 |
| screen | rsi2_h4_trend | BNBUSD | H4 | build_rsi2_mr | {} | nan | -22.3 | -557.5 | -653.5 | -40.7 | 208.0 | 0.553 | 0.24 |
| screen | rsi2_h4_trend | BTCUSD | H4 | build_rsi2_mr | {} | 0.0125 | 16.7 | 417.2 | -577.9 | -231.7 | 220.0 | 0.668 | 0.64 |
| screen | rsi2_h4_trend | DOTUSD | H4 | build_rsi2_mr | {} | nan | -47.0 | -1174.0 | -1180.1 | -58.0 | 157.0 | 0.255 | 0.08 |
| screen | rsi2_h4_trend | ETHUSD | H4 | build_rsi2_mr | {} | 0.0075 | -3.5 | -88.3 | -543.2 | -154.3 | 226.0 | 0.668 | 0.48 |
| screen | rsi2_h4_trend | LTCUSD | H4 | build_rsi2_mr | {} | nan | -56.9 | -1422.8 | -1430.1 | -47.3 | 219.0 | 0.306 | 0.04 |
| screen | rsi2_h4_trend | SOLUSD | H4 | build_rsi2_mr | {} | 0.0025 | -15.2 | -335.1 | -412.3 | -60.9 | 193.0 | 0.591 | 0.273 |
| screen | rsi2_h4_trend | XRPUSD | H4 | build_rsi2_mr | {} | 0.0025 | -24.6 | -541.4 | -588.1 | -50.0 | 188.0 | 0.548 | 0.091 |
| screen | rsi2_notrend | ADAUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -334.2 | -8355.4 | -8366.0 | -153.6 | 1717.0 | 0.316 | 0.08 |
| screen | rsi2_notrend | BNBUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -380.3 | -9508.0 | -9543.8 | -137.1 | 2247.0 | 0.395 | 0.0 |
| screen | rsi2_notrend | BTCUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -43.7 | -1093.2 | -1457.1 | -89.5 | 2259.0 | 0.628 | 0.32 |
| screen | rsi2_notrend | DOTUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -577.9 | -14446.8 | -14449.7 | -567.0 | 1943.0 | 0.265 | 0.04 |
| screen | rsi2_notrend | ETHUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -176.3 | -4408.6 | -4448.6 | -135.0 | 2283.0 | 0.583 | 0.04 |
| screen | rsi2_notrend | LTCUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -813.8 | -20344.2 | -20351.2 | -141.9 | 2152.0 | 0.135 | 0.0 |
| screen | rsi2_notrend | SOLUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -300.2 | -6604.1 | -6635.8 | -117.0 | 2015.0 | 0.426 | 0.0 |
| screen | rsi2_notrend | XRPUSD | H1 | build_rsi2_mr | {"use_trend": false} | nan | -315.0 | -6931.1 | -6942.4 | -136.3 | 1979.0 | 0.459 | 0.0 |
| screen | rsi2_trend | ADAUSD | H1 | build_rsi2_mr | {} | nan | -121.3 | -3031.8 | -3043.9 | -75.0 | 643.0 | 0.302 | 0.12 |
| screen | rsi2_trend | BNBUSD | H1 | build_rsi2_mr | {} | nan | -125.6 | -3138.8 | -3161.3 | -75.7 | 849.0 | 0.379 | 0.04 |
| screen | rsi2_trend | BTCUSD | H1 | build_rsi2_mr | {} | 0.0025 | -16.7 | -418.0 | -499.4 | -55.0 | 812.0 | 0.608 | 0.48 |
| screen | rsi2_trend | DOTUSD | H1 | build_rsi2_mr | {} | nan | -218.0 | -5451.0 | -5453.8 | -73.1 | 755.0 | 0.242 | 0.04 |
| screen | rsi2_trend | ETHUSD | H1 | build_rsi2_mr | {} | nan | -54.6 | -1365.4 | -1378.7 | -61.8 | 819.0 | 0.582 | 0.16 |
| screen | rsi2_trend | LTCUSD | H1 | build_rsi2_mr | {} | nan | -298.9 | -7471.3 | -7475.5 | -114.7 | 784.0 | 0.098 | 0.0 |
| screen | rsi2_trend | SOLUSD | H1 | build_rsi2_mr | {} | nan | -116.5 | -2563.3 | -2602.2 | -72.0 | 735.0 | 0.389 | 0.045 |
| screen | rsi2_trend | XRPUSD | H1 | build_rsi2_mr | {} | nan | -104.5 | -2298.7 | -2314.9 | -61.0 | 726.0 | 0.46 | 0.091 |
| screen | spike_fade | ADAUSD | H1 | build_vol_spike | {} | nan | -24.5 | -612.7 | -632.2 | -100.0 | 124.0 | 0.46 | 0.32 |
| screen | spike_fade | BNBUSD | H1 | build_vol_spike | {} | nan | -51.2 | -1280.2 | -1349.5 | -50.0 | 175.0 | 0.406 | 0.16 |
| screen | spike_fade | BTCUSD | H1 | build_vol_spike | {} | 0.0025 | -18.0 | -449.7 | -592.3 | -68.6 | 213.0 | 0.484 | 0.44 |
| screen | spike_fade | DOTUSD | H1 | build_vol_spike | {} | 0.005 | -15.7 | -392.9 | -505.2 | -80.7 | 63.0 | 0.476 | 0.2 |
| screen | spike_fade | ETHUSD | H1 | build_vol_spike | {} | nan | -26.0 | -648.9 | -731.9 | -49.7 | 197.0 | 0.467 | 0.36 |
| screen | spike_fade | LTCUSD | H1 | build_vol_spike | {} | nan | -32.3 | -807.1 | -855.3 | -70.8 | 85.0 | 0.365 | 0.08 |
| screen | spike_fade | SOLUSD | H1 | build_vol_spike | {} | nan | -25.4 | -559.6 | -621.0 | -47.8 | 146.0 | 0.445 | 0.273 |
| screen | spike_fade | XRPUSD | H1 | build_vol_spike | {} | nan | -24.9 | -547.7 | -613.4 | -75.0 | 148.0 | 0.486 | 0.318 |
| screen | spike_follow | ADAUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | nan | -17.5 | -438.0 | -694.5 | -50.0 | 139.0 | 0.381 | 0.32 |
| screen | spike_follow | BNBUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | nan | -29.8 | -745.9 | -768.3 | -74.5 | 172.0 | 0.378 | 0.24 |
| screen | spike_follow | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | 0.0075 | 81.3 | 2031.7 | -571.5 | -137.2 | 207.0 | 0.464 | 0.56 |
| screen | spike_follow | DOTUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | nan | -23.1 | -576.9 | -719.4 | -112.4 | 92.0 | 0.38 | 0.32 |
| screen | spike_follow | ETHUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | 0.0025 | -0.5 | -13.6 | -310.5 | -60.4 | 195.0 | 0.4 | 0.52 |
| screen | spike_follow | LTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | nan | -49.1 | -1227.8 | -1233.2 | -61.2 | 122.0 | 0.295 | 0.12 |
| screen | spike_follow | SOLUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | 0.0025 | -8.9 | -195.8 | -360.7 | -40.7 | 147.0 | 0.415 | 0.409 |
| screen | spike_follow | XRPUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 2.0, "hold": 12} | 0.0025 | -18.4 | -404.2 | -475.5 | -66.6 | 147.0 | 0.395 | 0.455 |
| refine | spike_follow_k25_h12 | ADAUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -22.1 | -553.0 | -874.4 | -66.1 | 249.0 | 0.406 | 0.44 |
| refine | spike_follow_k25_h12 | BNBUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -34.6 | -865.3 | -1025.7 | -74.5 | 310.0 | 0.406 | 0.36 |
| refine | spike_follow_k25_h12 | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | 0.0025 | 18.3 | 456.9 | -261.5 | -79.9 | 379.0 | 0.427 | 0.52 |
| refine | spike_follow_k25_h12 | DOTUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -32.5 | -812.0 | -1067.6 | -112.4 | 165.0 | 0.394 | 0.4 |
| refine | spike_follow_k25_h12 | ETHUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | 0.0025 | 8.6 | 214.8 | -322.7 | -85.0 | 355.0 | 0.408 | 0.6 |
| refine | spike_follow_k25_h12 | LTCUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -110.1 | -2752.6 | -2758.0 | -75.0 | 253.0 | 0.269 | 0.12 |
| refine | spike_follow_k25_h12 | SOLUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -28.3 | -623.6 | -857.1 | -63.3 | 280.0 | 0.393 | 0.409 |
| refine | spike_follow_k25_h12 | XRPUSD | H1 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 12} | nan | -52.6 | -1157.9 | -1240.6 | -102.7 | 298.0 | 0.376 | 0.273 |
| refine | spike_follow_k35_h12 | ADAUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.0025 | -3.2 | -79.8 | -303.4 | -36.5 | 69.0 | 0.391 | 0.36 |
| refine | spike_follow_k35_h12 | BNBUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.0025 | -19.8 | -495.8 | -502.7 | -49.9 | 83.0 | 0.349 | 0.36 |
| refine | spike_follow_k35_h12 | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.01 | 54.8 | 1370.1 | -571.6 | -191.4 | 121.0 | 0.446 | 0.56 |
| refine | spike_follow_k35_h12 | DOTUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.0025 | -9.7 | -241.8 | -389.6 | -99.7 | 53.0 | 0.377 | 0.24 |
| refine | spike_follow_k35_h12 | ETHUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.005 | 17.3 | 431.5 | -421.5 | -95.0 | 123.0 | 0.439 | 0.56 |
| refine | spike_follow_k35_h12 | LTCUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | nan | -27.8 | -696.2 | -701.7 | -49.9 | 68.0 | 0.294 | 0.2 |
| refine | spike_follow_k35_h12 | SOLUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.0075 | 3.8 | 82.5 | -551.3 | -134.0 | 90.0 | 0.467 | 0.591 |
| refine | spike_follow_k35_h12 | XRPUSD | H1 | build_vol_spike | {"mode": "follow", "k": 3.5, "rr": 2.0, "hold": 12} | 0.005 | -18.4 | -405.3 | -486.1 | -100.0 | 92.0 | 0.391 | 0.318 |
| refine | spike_follow_k3_h24 | ADAUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | nan | -20.9 | -521.9 | -975.3 | -50.0 | 135.0 | 0.311 | 0.24 |
| refine | spike_follow_k3_h24 | BNBUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | nan | -32.0 | -799.4 | -822.7 | -74.5 | 164.0 | 0.329 | 0.32 |
| refine | spike_follow_k3_h24 | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | 0.0025 | 29.5 | 737.4 | -294.0 | -63.2 | 200.0 | 0.385 | 0.52 |
| refine | spike_follow_k3_h24 | DOTUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | nan | -26.4 | -660.5 | -903.6 | -112.4 | 110.0 | 0.309 | 0.28 |
| refine | spike_follow_k3_h24 | ETHUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | 0.0025 | 10.8 | 269.6 | -336.8 | -81.7 | 188.0 | 0.335 | 0.56 |
| refine | spike_follow_k3_h24 | LTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | nan | -49.7 | -1241.9 | -1247.3 | -61.2 | 133.0 | 0.286 | 0.16 |
| refine | spike_follow_k3_h24 | SOLUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | 0.0025 | -12.2 | -268.0 | -421.7 | -40.7 | 141.0 | 0.355 | 0.409 |
| refine | spike_follow_k3_h24 | XRPUSD | H1 | build_vol_spike | {"mode": "follow", "rr": 3.0, "hold": 24} | 0.0025 | -14.9 | -327.9 | -500.9 | -66.6 | 139.0 | 0.324 | 0.545 |
| refine | spike_follow_k3_noTP_h24 | ADAUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | nan | -15.9 | -398.6 | -1003.2 | -50.0 | 130.0 | 0.285 | 0.28 |
| refine | spike_follow_k3_noTP_h24 | BNBUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | nan | -42.1 | -1052.4 | -1086.1 | -74.5 | 157.0 | 0.299 | 0.28 |
| refine | spike_follow_k3_noTP_h24 | BTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | 0.0025 | 30.8 | 768.9 | -335.6 | -117.5 | 191.0 | 0.372 | 0.56 |
| refine | spike_follow_k3_noTP_h24 | DOTUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | nan | -16.8 | -419.4 | -1018.7 | -112.4 | 115.0 | 0.243 | 0.44 |
| refine | spike_follow_k3_noTP_h24 | ETHUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | 0.0025 | 16.7 | 418.4 | -399.9 | -81.7 | 178.0 | 0.315 | 0.52 |
| refine | spike_follow_k3_noTP_h24 | LTCUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | nan | -55.0 | -1374.3 | -1379.7 | -61.2 | 130.0 | 0.254 | 0.04 |
| refine | spike_follow_k3_noTP_h24 | SOLUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | 0.0025 | -19.2 | -422.0 | -573.5 | -86.0 | 135.0 | 0.333 | 0.318 |
| refine | spike_follow_k3_noTP_h24 | XRPUSD | H1 | build_vol_spike | {"mode": "follow", "rr": null, "hold": 24} | nan | -28.8 | -634.4 | -858.4 | -93.4 | 132.0 | 0.273 | 0.455 |
| screen | spike_h4_fade | ADAUSD | H4 | build_vol_spike | {"k": 2.5} | 0.0025 | -13.0 | -324.5 | -347.0 | -55.9 | 58.0 | 0.448 | 0.16 |
| screen | spike_h4_fade | BNBUSD | H4 | build_vol_spike | {"k": 2.5} | 0.005 | -13.1 | -327.4 | -506.0 | -99.8 | 84.0 | 0.524 | 0.44 |
| screen | spike_h4_fade | BTCUSD | H4 | build_vol_spike | {"k": 2.5} | 0.005 | 3.2 | 81.2 | -383.4 | -72.5 | 126.0 | 0.524 | 0.52 |
| screen | spike_h4_fade | DOTUSD | H4 | build_vol_spike | {"k": 2.5} | 0.0025 | -12.4 | -310.2 | -312.9 | -49.9 | 41.0 | 0.366 | 0.16 |
| screen | spike_h4_fade | ETHUSD | H4 | build_vol_spike | {"k": 2.5} | 0.0025 | -11.1 | -276.5 | -407.3 | -51.9 | 105.0 | 0.495 | 0.36 |
| screen | spike_h4_fade | LTCUSD | H4 | build_vol_spike | {"k": 2.5} | nan | -24.6 | -615.8 | -661.8 | -116.7 | 79.0 | 0.468 | 0.24 |
| screen | spike_h4_fade | SOLUSD | H4 | build_vol_spike | {"k": 2.5} | 0.0025 | -13.2 | -290.6 | -342.1 | -41.7 | 77.0 | 0.429 | 0.364 |
| screen | spike_h4_fade | XRPUSD | H4 | build_vol_spike | {"k": 2.5} | 0.0075 | -14.5 | -318.7 | -569.4 | -225.0 | 93.0 | 0.538 | 0.455 |
| refine | spike_h4_follow_k25_h6 | ADAUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.0025 | -14.4 | -359.3 | -478.5 | -44.0 | 56.0 | 0.339 | 0.28 |
| refine | spike_h4_follow_k25_h6 | BNBUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.0025 | -10.4 | -259.5 | -475.7 | -41.7 | 84.0 | 0.369 | 0.4 |
| refine | spike_h4_follow_k25_h6 | BTCUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.005 | -1.5 | -38.3 | -582.1 | -90.1 | 121.0 | 0.421 | 0.44 |
| refine | spike_h4_follow_k25_h6 | DOTUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | nan | -22.8 | -569.4 | -630.7 | -47.9 | 62.0 | 0.242 | 0.16 |
| refine | spike_h4_follow_k25_h6 | ETHUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.0025 | 9.4 | 235.1 | -414.1 | -43.0 | 103.0 | 0.437 | 0.56 |
| refine | spike_h4_follow_k25_h6 | LTCUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | nan | -24.2 | -604.5 | -694.1 | -33.9 | 86.0 | 0.326 | 0.24 |
| refine | spike_h4_follow_k25_h6 | SOLUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.005 | -10.2 | -223.3 | -522.0 | -82.7 | 76.0 | 0.395 | 0.455 |
| refine | spike_h4_follow_k25_h6 | XRPUSD | H4 | build_vol_spike | {"mode": "follow", "k": 2.5, "rr": 2.0, "hold": 6} | 0.0025 | -13.2 | -289.4 | -365.3 | -48.9 | 88.0 | 0.364 | 0.318 |
| screen | squeeze_d1 | ADAUSD | D1 | build_squeeze | {"min_bars": 4} | 0.0125 | 17.6 | 440.1 | -578.8 | -190.5 | 8.0 | 0.25 | 0.08 |
| screen | squeeze_d1 | BNBUSD | D1 | build_squeeze | {"min_bars": 4} | 0.0125 | -19.5 | -486.5 | -589.9 | -142.1 | 10.0 | 0.2 | 0.08 |
| screen | squeeze_d1 | BTCUSD | D1 | build_squeeze | {"min_bars": 4} | 0.01 | 6.1 | 151.3 | -351.6 | -127.1 | 8.0 | 0.375 | 0.2 |
| screen | squeeze_d1 | DOTUSD | D1 | build_squeeze | {"min_bars": 4} | 0.0125 | -17.1 | -428.5 | -501.4 | -124.9 | 6.0 | 0.167 | 0.04 |
| screen | squeeze_d1 | ETHUSD | D1 | build_squeeze | {"min_bars": 4} | 0.01 | -3.9 | -98.5 | -534.4 | -103.3 | 10.0 | 0.3 | 0.16 |
| screen | squeeze_d1 | LTCUSD | D1 | build_squeeze | {"min_bars": 4} | 0.0125 | -4.8 | -119.2 | -544.5 | -145.6 | 11.0 | 0.273 | 0.16 |
| screen | squeeze_d1 | SOLUSD | D1 | build_squeeze | {"min_bars": 4} | 0.02 | 20.5 | 451.5 | -551.5 | -283.9 | 6.0 | 0.333 | 0.091 |
| screen | squeeze_d1 | XRPUSD | D1 | build_squeeze | {"min_bars": 4} | 0.015 | -23.3 | -513.2 | -542.9 | -140.3 | 6.0 | 0.167 | 0.045 |
| screen | squeeze_h1 | ADAUSD | H1 | build_squeeze | {} | nan | -18.3 | -456.8 | -780.6 | -39.4 | 155.0 | 0.239 | 0.28 |
| screen | squeeze_h1 | BNBUSD | H1 | build_squeeze | {} | 0.0025 | -10.7 | -267.9 | -523.8 | -47.5 | 143.0 | 0.308 | 0.36 |
| screen | squeeze_h1 | BTCUSD | H1 | build_squeeze | {} | 0.0025 | 5.0 | 124.5 | -279.8 | -28.2 | 187.0 | 0.342 | 0.6 |
| screen | squeeze_h1 | DOTUSD | H1 | build_squeeze | {} | nan | -43.1 | -1077.9 | -1255.4 | -40.9 | 167.0 | 0.21 | 0.16 |
| screen | squeeze_h1 | ETHUSD | H1 | build_squeeze | {} | 0.0025 | -8.4 | -209.3 | -502.4 | -48.4 | 207.0 | 0.357 | 0.28 |
| screen | squeeze_h1 | LTCUSD | H1 | build_squeeze | {} | nan | -71.5 | -1786.5 | -1829.3 | -29.8 | 164.0 | 0.165 | 0.08 |
| screen | squeeze_h1 | SOLUSD | H1 | build_squeeze | {} | 0.0025 | -8.7 | -190.6 | -488.2 | -28.6 | 147.0 | 0.306 | 0.455 |
| screen | squeeze_h1 | XRPUSD | H1 | build_squeeze | {} | 0.0025 | -21.2 | -467.5 | -534.7 | -27.5 | 169.0 | 0.308 | 0.364 |
| screen | squeeze_h4 | ADAUSD | H4 | build_squeeze | {} | 0.0075 | 36.6 | 915.0 | -462.4 | -93.0 | 46.0 | 0.5 | 0.48 |
| screen | squeeze_h4 | BNBUSD | H4 | build_squeeze | {} | 0.0025 | -13.6 | -341.2 | -365.2 | -31.9 | 37.0 | 0.216 | 0.24 |
| screen | squeeze_h4 | BTCUSD | H4 | build_squeeze | {} | 0.0125 | 94.9 | 2373.6 | -542.6 | -176.6 | 42.0 | 0.452 | 0.44 |
| screen | squeeze_h4 | DOTUSD | H4 | build_squeeze | {} | 0.0025 | 1.0 | 24.4 | -358.5 | -28.4 | 39.0 | 0.231 | 0.24 |
| screen | squeeze_h4 | ETHUSD | H4 | build_squeeze | {} | 0.0075 | 37.9 | 946.4 | -540.6 | -110.3 | 39.0 | 0.462 | 0.4 |
| screen | squeeze_h4 | LTCUSD | H4 | build_squeeze | {} | 0.0025 | -22.8 | -568.8 | -598.2 | -25.0 | 46.0 | 0.174 | 0.16 |
| screen | squeeze_h4 | SOLUSD | H4 | build_squeeze | {} | 0.005 | 0.2 | 4.2 | -539.9 | -50.0 | 38.0 | 0.316 | 0.318 |
| screen | squeeze_h4 | XRPUSD | H4 | build_squeeze | {} | 0.0075 | 22.8 | 502.3 | -559.4 | -93.0 | 47.0 | 0.34 | 0.364 |
| refine | squeeze_h4_a2 | ADAUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.0075 | 28.2 | 706.2 | -588.3 | -95.1 | 44.0 | 0.386 | 0.4 |
| refine | squeeze_h4_a2 | BNBUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.0025 | -16.5 | -412.5 | -430.8 | -32.7 | 37.0 | 0.162 | 0.2 |
| refine | squeeze_h4_a2 | BTCUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.01 | 83.7 | 2091.3 | -555.1 | -134.8 | 42.0 | 0.381 | 0.4 |
| refine | squeeze_h4_a2 | DOTUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.005 | 4.2 | 105.6 | -569.1 | -59.1 | 40.0 | 0.3 | 0.36 |
| refine | squeeze_h4_a2 | ETHUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.0075 | 15.9 | 396.9 | -578.2 | -109.8 | 39.0 | 0.308 | 0.36 |
| refine | squeeze_h4_a2 | LTCUSD | H4 | build_squeeze | {"atr_mult": 2.0} | nan | -21.8 | -545.0 | -608.6 | -26.5 | 44.0 | 0.205 | 0.16 |
| refine | squeeze_h4_a2 | SOLUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.005 | 11.3 | 248.9 | -404.5 | -57.7 | 37.0 | 0.351 | 0.409 |
| refine | squeeze_h4_a2 | XRPUSD | H4 | build_squeeze | {"atr_mult": 2.0} | 0.005 | 7.3 | 161.4 | -475.0 | -72.9 | 46.0 | 0.348 | 0.318 |
| refine | squeeze_h4_a25_kc2 | ADAUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.005 | -11.1 | -277.9 | -487.3 | -51.4 | 45.0 | 0.222 | 0.32 |
| refine | squeeze_h4_a25_kc2 | BNBUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.0025 | -10.0 | -249.8 | -416.1 | -27.3 | 49.0 | 0.245 | 0.24 |
| refine | squeeze_h4_a25_kc2 | BTCUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.0075 | 33.1 | 827.5 | -471.9 | -105.7 | 48.0 | 0.229 | 0.36 |
| refine | squeeze_h4_a25_kc2 | DOTUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.005 | 6.5 | 162.7 | -475.0 | -52.1 | 39.0 | 0.41 | 0.36 |
| refine | squeeze_h4_a25_kc2 | ETHUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.01 | 98.0 | 2448.8 | -522.3 | -155.5 | 45.0 | 0.422 | 0.52 |
| refine | squeeze_h4_a25_kc2 | LTCUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.0025 | -14.9 | -372.4 | -396.0 | -30.0 | 44.0 | 0.227 | 0.32 |
| refine | squeeze_h4_a25_kc2 | SOLUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.015 | 84.2 | 1852.1 | -579.0 | -174.5 | 37.0 | 0.514 | 0.591 |
| refine | squeeze_h4_a25_kc2 | XRPUSD | H4 | build_squeeze | {"atr_mult": 2.5, "kc_mult": 2.0} | 0.005 | 12.6 | 276.3 | -474.6 | -75.6 | 49.0 | 0.245 | 0.318 |
| refine | squeeze_h4_kc1 | ADAUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.02 | 74.9 | 1871.7 | -452.2 | -200.0 | 11.0 | 0.455 | 0.2 |
| refine | squeeze_h4_kc1 | BNBUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.0125 | -13.6 | -339.1 | -543.8 | -125.0 | 6.0 | 0.167 | 0.04 |
| refine | squeeze_h4_kc1 | BTCUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.0125 | 39.8 | 995.4 | -573.1 | -176.6 | 12.0 | 0.333 | 0.16 |
| refine | squeeze_h4_kc1 | DOTUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.0125 | -21.2 | -530.8 | -595.2 | -124.8 | 8.0 | 0.125 | 0.04 |
| refine | squeeze_h4_kc1 | ETHUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.0125 | 14.8 | 369.7 | -599.4 | -147.7 | 16.0 | 0.312 | 0.2 |
| refine | squeeze_h4_kc1 | LTCUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.01 | -17.8 | -444.6 | -483.8 | -96.1 | 7.0 | 0.143 | 0.08 |
| refine | squeeze_h4_kc1 | SOLUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.015 | -3.4 | -74.1 | -454.2 | -148.1 | 5.0 | 0.4 | 0.091 |
| refine | squeeze_h4_kc1 | XRPUSD | H4 | build_squeeze | {"kc_mult": 1.0} | 0.01 | 64.2 | 1412.1 | -558.2 | -107.2 | 11.0 | 0.636 | 0.318 |
| refine | squeeze_h4_mb4 | ADAUSD | H4 | build_squeeze | {"min_bars": 4} | 0.005 | 10.6 | 264.6 | -457.9 | -62.0 | 48.0 | 0.417 | 0.44 |
| refine | squeeze_h4_mb4 | BNBUSD | H4 | build_squeeze | {"min_bars": 4} | 0.0025 | -9.3 | -233.1 | -335.9 | -31.9 | 45.0 | 0.222 | 0.32 |
| refine | squeeze_h4_mb4 | BTCUSD | H4 | build_squeeze | {"min_bars": 4} | 0.0075 | 32.1 | 801.9 | -486.3 | -96.3 | 60.0 | 0.383 | 0.4 |
| refine | squeeze_h4_mb4 | DOTUSD | H4 | build_squeeze | {"min_bars": 4} | 0.0025 | 0.5 | 11.4 | -338.5 | -28.4 | 44.0 | 0.25 | 0.28 |
| refine | squeeze_h4_mb4 | ETHUSD | H4 | build_squeeze | {"min_bars": 4} | 0.005 | 14.5 | 361.3 | -506.4 | -73.5 | 52.0 | 0.404 | 0.44 |
| refine | squeeze_h4_mb4 | LTCUSD | H4 | build_squeeze | {"min_bars": 4} | nan | -22.4 | -559.5 | -617.7 | -25.0 | 52.0 | 0.173 | 0.2 |
| refine | squeeze_h4_mb4 | SOLUSD | H4 | build_squeeze | {"min_bars": 4} | 0.005 | -4.4 | -97.1 | -584.9 | -50.0 | 42.0 | 0.31 | 0.318 |
| refine | squeeze_h4_mb4 | XRPUSD | H4 | build_squeeze | {"min_bars": 4} | 0.005 | 16.7 | 367.3 | -468.6 | -62.0 | 56.0 | 0.321 | 0.409 |
| refine | squeeze_h4_mb8 | ADAUSD | H4 | build_squeeze | {"min_bars": 8} | 0.0125 | 62.5 | 1562.0 | -583.2 | -125.0 | 38.0 | 0.5 | 0.44 |
| refine | squeeze_h4_mb8 | BNBUSD | H4 | build_squeeze | {"min_bars": 8} | 0.005 | -19.0 | -474.9 | -522.9 | -64.1 | 28.0 | 0.25 | 0.2 |
| refine | squeeze_h4_mb8 | BTCUSD | H4 | build_squeeze | {"min_bars": 8} | 0.01 | 69.1 | 1726.3 | -504.2 | -128.4 | 33.0 | 0.424 | 0.48 |
| refine | squeeze_h4_mb8 | DOTUSD | H4 | build_squeeze | {"min_bars": 8} | 0.005 | -6.4 | -158.9 | -579.6 | -57.0 | 36.0 | 0.222 | 0.24 |
| refine | squeeze_h4_mb8 | ETHUSD | H4 | build_squeeze | {"min_bars": 8} | 0.015 | 91.1 | 2277.3 | -569.9 | -220.6 | 29.0 | 0.552 | 0.36 |
| refine | squeeze_h4_mb8 | LTCUSD | H4 | build_squeeze | {"min_bars": 8} | 0.0025 | -18.2 | -454.9 | -509.3 | -25.0 | 39.0 | 0.179 | 0.16 |
| refine | squeeze_h4_mb8 | SOLUSD | H4 | build_squeeze | {"min_bars": 8} | 0.005 | 3.9 | 86.2 | -429.0 | -50.0 | 32.0 | 0.312 | 0.273 |
| refine | squeeze_h4_mb8 | XRPUSD | H4 | build_squeeze | {"min_bars": 8} | 0.0075 | 16.4 | 360.5 | -514.6 | -93.0 | 37.0 | 0.351 | 0.364 |
| screen | squeeze_h4_rr2 | ADAUSD | H4 | build_squeeze | {"trail": false} | 0.01 | 27.0 | 674.1 | -578.0 | -125.9 | 46.0 | 0.457 | 0.48 |
| screen | squeeze_h4_rr2 | BNBUSD | H4 | build_squeeze | {"trail": false} | 0.0025 | -16.7 | -418.0 | -483.6 | -38.3 | 37.0 | 0.216 | 0.24 |
| screen | squeeze_h4_rr2 | BTCUSD | H4 | build_squeeze | {"trail": false} | 0.01 | 46.3 | 1158.7 | -577.0 | -160.3 | 42.0 | 0.429 | 0.52 |
| screen | squeeze_h4_rr2 | DOTUSD | H4 | build_squeeze | {"trail": false} | 0.0025 | -6.6 | -164.4 | -331.3 | -42.0 | 35.0 | 0.371 | 0.28 |
| screen | squeeze_h4_rr2 | ETHUSD | H4 | build_squeeze | {"trail": false} | 0.005 | 7.8 | 195.0 | -486.3 | -94.7 | 39.0 | 0.385 | 0.4 |
| screen | squeeze_h4_rr2 | LTCUSD | H4 | build_squeeze | {"trail": false} | 0.0025 | -15.3 | -382.7 | -504.0 | -25.0 | 45.0 | 0.311 | 0.28 |
| screen | squeeze_h4_rr2 | SOLUSD | H4 | build_squeeze | {"trail": false} | 0.0025 | -1.4 | -31.9 | -294.2 | -44.9 | 38.0 | 0.368 | 0.409 |
| screen | squeeze_h4_rr2 | XRPUSD | H4 | build_squeeze | {"trail": false} | 0.005 | 2.6 | 57.4 | -488.7 | -112.3 | 47.0 | 0.383 | 0.455 |
| screen | stt_d1_10_3 | ADAUSD | D1 | build_supertrend | {} | 0.0025 | -13.5 | -338.4 | -408.6 | -82.6 | 30.0 | 0.133 | 0.24 |
| screen | stt_d1_10_3 | BNBUSD | D1 | build_supertrend | {} | nan | -8.0 | -200.2 | -755.8 | -307.4 | 44.0 | 0.205 | 0.44 |
| screen | stt_d1_10_3 | BTCUSD | D1 | build_supertrend | {} | nan | -5.4 | -135.3 | -633.6 | -137.6 | 31.0 | 0.065 | 0.16 |
| screen | stt_d1_10_3 | DOTUSD | D1 | build_supertrend | {} | nan | -20.2 | -504.5 | -642.6 | -75.0 | 32.0 | 0.125 | 0.24 |
| screen | stt_d1_10_3 | ETHUSD | D1 | build_supertrend | {} | 0.0025 | -9.6 | -240.4 | -355.6 | -111.1 | 37.0 | 0.297 | 0.56 |
| screen | stt_d1_10_3 | LTCUSD | D1 | build_supertrend | {} | 0.0025 | -15.6 | -389.7 | -447.8 | -70.8 | 33.0 | 0.212 | 0.32 |
| screen | stt_d1_10_3 | SOLUSD | D1 | build_supertrend | {} | 0.0025 | 26.5 | 583.7 | -408.3 | -212.9 | 37.0 | 0.216 | 0.455 |
| screen | stt_d1_10_3 | XRPUSD | D1 | build_supertrend | {} | 0.0025 | -0.0 | -0.7 | -368.0 | -100.3 | 32.0 | 0.281 | 0.455 |
| screen | stt_d1_10_3_L | ADAUSD | D1 | build_supertrend | {"long_only": true} | 0.0025 | -8.3 | -206.9 | -271.8 | -70.8 | 16.0 | 0.062 | 0.08 |
| screen | stt_d1_10_3_L | BNBUSD | D1 | build_supertrend | {"long_only": true} | nan | 1.4 | 35.5 | -681.8 | -307.4 | 22.0 | 0.182 | 0.32 |
| screen | stt_d1_10_3_L | BTCUSD | D1 | build_supertrend | {"long_only": true} | 0.0025 | 2.6 | 63.9 | -434.4 | -73.9 | 21.0 | 0.095 | 0.12 |
| screen | stt_d1_10_3_L | DOTUSD | D1 | build_supertrend | {"long_only": true} | 0.0025 | -11.1 | -277.4 | -299.6 | -32.2 | 15.0 | 0.067 | 0.04 |
| screen | stt_d1_10_3_L | ETHUSD | D1 | build_supertrend | {"long_only": true} | 0.0025 | -6.2 | -154.4 | -302.0 | -111.1 | 22.0 | 0.227 | 0.28 |
| screen | stt_d1_10_3_L | LTCUSD | D1 | build_supertrend | {"long_only": true} | 0.0025 | -11.4 | -283.9 | -321.8 | -70.8 | 16.0 | 0.188 | 0.24 |
| screen | stt_d1_10_3_L | SOLUSD | D1 | build_supertrend | {"long_only": true} | 0.0075 | -17.5 | -384.4 | -517.3 | -89.1 | 14.0 | 0.286 | 0.273 |
| screen | stt_d1_10_3_L | XRPUSD | D1 | build_supertrend | {"long_only": true} | 0.005 | -23.9 | -525.5 | -545.0 | -120.9 | 18.0 | 0.167 | 0.182 |
| screen | stt_h4_10_3 | ADAUSD | H4 | build_supertrend | {} | nan | -6.4 | -160.9 | -1526.8 | -264.5 | 189.0 | 0.201 | 0.36 |
| screen | stt_h4_10_3 | BNBUSD | H4 | build_supertrend | {} | nan | -48.6 | -1214.1 | -1240.4 | -139.5 | 215.0 | 0.223 | 0.32 |
| screen | stt_h4_10_3 | BTCUSD | H4 | build_supertrend | {} | nan | -66.0 | -1650.9 | -1865.9 | -331.3 | 255.0 | 0.173 | 0.4 |
| screen | stt_h4_10_3 | DOTUSD | H4 | build_supertrend | {} | nan | -59.0 | -1475.0 | -2200.4 | -134.1 | 202.0 | 0.158 | 0.32 |
| screen | stt_h4_10_3 | ETHUSD | H4 | build_supertrend | {} | nan | -26.5 | -661.4 | -1391.1 | -290.9 | 233.0 | 0.227 | 0.48 |
| screen | stt_h4_10_3 | LTCUSD | H4 | build_supertrend | {} | nan | -127.2 | -3181.2 | -3181.2 | -336.0 | 241.0 | 0.12 | 0.04 |
| screen | stt_h4_10_3 | SOLUSD | H4 | build_supertrend | {} | nan | -28.7 | -631.8 | -989.1 | -127.2 | 202.0 | 0.228 | 0.455 |
| screen | stt_h4_10_3 | XRPUSD | H4 | build_supertrend | {} | nan | 23.3 | 512.1 | -664.3 | -195.3 | 185.0 | 0.27 | 0.409 |
| screen | stt_h4_14_2 | ADAUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -23.4 | -586.0 | -937.0 | -206.4 | 351.0 | 0.217 | 0.4 |
| screen | stt_h4_14_2 | BNBUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -50.4 | -1260.4 | -1317.1 | -69.2 | 361.0 | 0.255 | 0.28 |
| screen | stt_h4_14_2 | BTCUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -7.5 | -186.4 | -1689.1 | -319.4 | 417.0 | 0.223 | 0.44 |
| screen | stt_h4_14_2 | DOTUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -102.0 | -2550.2 | -3133.6 | -241.0 | 370.0 | 0.157 | 0.2 |
| screen | stt_h4_14_2 | ETHUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | 112.2 | 2805.1 | -1043.5 | -408.6 | 375.0 | 0.232 | 0.52 |
| screen | stt_h4_14_2 | LTCUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -151.9 | -3798.5 | -3830.5 | -363.3 | 382.0 | 0.173 | 0.12 |
| screen | stt_h4_14_2 | SOLUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -26.7 | -587.6 | -1117.4 | -142.3 | 332.0 | 0.232 | 0.5 |
| screen | stt_h4_14_2 | XRPUSD | H4 | build_supertrend | {"n": 14, "mult": 2.0} | nan | -29.2 | -643.0 | -1372.7 | -218.9 | 373.0 | 0.236 | 0.409 |
| screen | tsmom_d1_lb10_a2 | ADAUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0025 | -3.5 | -87.5 | -161.1 | -20.3 | 19.0 | 0.158 | 0.04 |
| screen | tsmom_d1_lb10_a2 | BNBUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0075 | -4.2 | -104.9 | -454.6 | -111.1 | 123.0 | 0.374 | 0.4 |
| screen | tsmom_d1_lb10_a2 | BTCUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0075 | 12.1 | 303.7 | -393.1 | -82.7 | 104.0 | 0.298 | 0.6 |
| screen | tsmom_d1_lb10_a2 | DOTUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0025 | -11.7 | -293.2 | -322.1 | -24.8 | 38.0 | 0.184 | 0.08 |
| screen | tsmom_d1_lb10_a2 | ETHUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0025 | -4.8 | -120.5 | -299.5 | -25.8 | 138.0 | 0.348 | 0.52 |
| screen | tsmom_d1_lb10_a2 | LTCUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.0025 | -19.8 | -493.8 | -597.0 | -64.8 | 125.0 | 0.256 | 0.4 |
| screen | tsmom_d1_lb10_a2 | SOLUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.005 | -10.0 | -220.6 | -429.5 | -59.4 | 108.0 | 0.306 | 0.364 |
| screen | tsmom_d1_lb10_a2 | XRPUSD | D1 | build_tsmom | {"lb": 10, "atr_mult": 2.0} | 0.005 | -12.0 | -264.7 | -447.8 | -84.1 | 112.0 | 0.304 | 0.455 |
| screen | tsmom_d1_lb20_a2 | ADAUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.0075 | 8.0 | 199.6 | -450.9 | -111.0 | 52.0 | 0.346 | 0.32 |
| screen | tsmom_d1_lb20_a2 | BNBUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.005 | -9.8 | -243.9 | -554.7 | -76.6 | 98.0 | 0.265 | 0.4 |
| screen | tsmom_d1_lb20_a2 | BTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.01 | 46.3 | 1156.7 | -532.8 | -165.4 | 104.0 | 0.385 | 0.6 |
| screen | tsmom_d1_lb20_a2 | DOTUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.005 | -20.6 | -514.4 | -575.7 | -53.2 | 64.0 | 0.281 | 0.32 |
| screen | tsmom_d1_lb20_a2 | ETHUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.01 | 55.4 | 1384.5 | -520.6 | -197.4 | 106.0 | 0.377 | 0.52 |
| screen | tsmom_d1_lb20_a2 | LTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.0025 | -13.5 | -336.5 | -458.5 | -64.8 | 106.0 | 0.264 | 0.4 |
| screen | tsmom_d1_lb20_a2 | SOLUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.0075 | 20.3 | 446.8 | -539.5 | -105.6 | 80.0 | 0.362 | 0.591 |
| screen | tsmom_d1_lb20_a2 | XRPUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 2.0} | 0.0025 | 3.9 | 86.3 | -191.1 | -44.8 | 60.0 | 0.35 | 0.364 |
| screen | tsmom_d1_lb20_a3 | ADAUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.005 | -0.3 | -8.7 | -126.1 | -39.1 | 23.0 | 0.261 | 0.16 |
| screen | tsmom_d1_lb20_a3 | BNBUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.0075 | -9.7 | -241.8 | -534.6 | -105.2 | 80.0 | 0.25 | 0.4 |
| screen | tsmom_d1_lb20_a3 | BTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.015 | 50.3 | 1257.7 | -483.0 | -165.9 | 87.0 | 0.368 | 0.52 |
| screen | tsmom_d1_lb20_a3 | DOTUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.005 | -8.9 | -223.3 | -267.8 | -46.3 | 33.0 | 0.242 | 0.12 |
| screen | tsmom_d1_lb20_a3 | ETHUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.0125 | 47.8 | 1196.2 | -541.9 | -178.8 | 90.0 | 0.333 | 0.56 |
| screen | tsmom_d1_lb20_a3 | LTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.0025 | -8.3 | -206.5 | -342.9 | -51.5 | 92.0 | 0.239 | 0.44 |
| screen | tsmom_d1_lb20_a3 | SOLUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.01 | 13.0 | 286.8 | -471.4 | -125.2 | 71.0 | 0.324 | 0.545 |
| screen | tsmom_d1_lb20_a3 | XRPUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0} | 0.005 | -3.2 | -70.4 | -382.2 | -77.0 | 69.0 | 0.29 | 0.364 |
| screen | tsmom_d1_lb20_a3_L | ADAUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.005 | -1.9 | -46.3 | -134.4 | -37.9 | 5.0 | 0.4 | 0.12 |
| screen | tsmom_d1_lb20_a3_L | BNBUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.01 | 2.2 | 54.9 | -555.2 | -145.2 | 19.0 | 0.316 | 0.44 |
| screen | tsmom_d1_lb20_a3_L | BTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.0125 | 7.9 | 197.5 | -485.9 | -73.9 | 15.0 | 0.333 | 0.4 |
| screen | tsmom_d1_lb20_a3_L | DOTUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.005 | -7.9 | -197.0 | -236.7 | -46.3 | 8.0 | 0.125 | 0.04 |
| screen | tsmom_d1_lb20_a3_L | ETHUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.01 | 17.6 | 440.4 | -536.4 | -141.3 | 14.0 | 0.357 | 0.44 |
| screen | tsmom_d1_lb20_a3_L | LTCUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.0075 | 3.3 | 81.8 | -505.4 | -163.7 | 16.0 | 0.375 | 0.48 |
| screen | tsmom_d1_lb20_a3_L | SOLUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.01 | -5.2 | -113.4 | -526.4 | -71.1 | 14.0 | 0.286 | 0.364 |
| screen | tsmom_d1_lb20_a3_L | XRPUSD | D1 | build_tsmom | {"lb": 20, "atr_mult": 3.0, "long_only": true} | 0.005 | -10.3 | -226.8 | -445.7 | -99.8 | 16.0 | 0.25 | 0.136 |
| refine | tsmom_d1_lb30_a25 | ADAUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.005 | -8.0 | -199.4 | -319.7 | -46.4 | 35.0 | 0.286 | 0.12 |
| refine | tsmom_d1_lb30_a25 | BNBUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0075 | 16.1 | 403.0 | -512.7 | -124.0 | 79.0 | 0.342 | 0.48 |
| refine | tsmom_d1_lb30_a25 | BTCUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.01 | 38.4 | 959.8 | -374.4 | -114.1 | 75.0 | 0.387 | 0.6 |
| refine | tsmom_d1_lb30_a25 | DOTUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.005 | -16.7 | -417.2 | -568.7 | -45.2 | 39.0 | 0.154 | 0.24 |
| refine | tsmom_d1_lb30_a25 | ETHUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0125 | 85.3 | 2132.8 | -515.5 | -202.3 | 69.0 | 0.391 | 0.56 |
| refine | tsmom_d1_lb30_a25 | LTCUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0025 | -14.5 | -363.1 | -472.3 | -58.0 | 101.0 | 0.218 | 0.32 |
| refine | tsmom_d1_lb30_a25 | SOLUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.01 | 3.2 | 70.0 | -587.7 | -112.2 | 59.0 | 0.356 | 0.455 |
| refine | tsmom_d1_lb30_a25 | XRPUSD | D1 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.005 | -13.9 | -306.3 | -435.6 | -85.5 | 72.0 | 0.292 | 0.5 |
| screen | tsmom_d1_lb40_a2 | ADAUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.0075 | 13.1 | 326.3 | -312.0 | -92.8 | 51.0 | 0.392 | 0.4 |
| screen | tsmom_d1_lb40_a2 | BNBUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.005 | 9.8 | 245.4 | -420.4 | -76.6 | 88.0 | 0.364 | 0.56 |
| screen | tsmom_d1_lb40_a2 | BTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.015 | 80.4 | 2009.1 | -576.5 | -165.4 | 82.0 | 0.366 | 0.6 |
| screen | tsmom_d1_lb40_a2 | DOTUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.0025 | -11.0 | -274.7 | -295.3 | -24.9 | 29.0 | 0.138 | 0.16 |
| screen | tsmom_d1_lb40_a2 | ETHUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.015 | 71.4 | 1784.2 | -564.6 | -177.6 | 65.0 | 0.415 | 0.6 |
| screen | tsmom_d1_lb40_a2 | LTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.0025 | -12.5 | -312.6 | -416.7 | -61.4 | 86.0 | 0.233 | 0.48 |
| screen | tsmom_d1_lb40_a2 | SOLUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.015 | 31.2 | 686.7 | -593.5 | -178.2 | 68.0 | 0.397 | 0.682 |
| screen | tsmom_d1_lb40_a2 | XRPUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0} | 0.0075 | -12.1 | -266.5 | -475.8 | -134.4 | 85.0 | 0.365 | 0.455 |
| refine | tsmom_d1_lb40_a2_notrail | ADAUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0025 | 2.5 | 63.4 | -60.2 | -26.1 | 12.0 | 0.417 | 0.08 |
| refine | tsmom_d1_lb40_a2_notrail | BNBUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0025 | 10.8 | 269.8 | -373.8 | -144.0 | 61.0 | 0.344 | 0.48 |
| refine | tsmom_d1_lb40_a2_notrail | BTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.01 | 39.5 | 986.7 | -535.6 | -147.8 | 60.0 | 0.367 | 0.56 |
| refine | tsmom_d1_lb40_a2_notrail | DOTUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0025 | -9.3 | -231.3 | -251.9 | -31.8 | 22.0 | 0.136 | 0.16 |
| refine | tsmom_d1_lb40_a2_notrail | ETHUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.015 | 89.5 | 2238.2 | -569.9 | -298.4 | 42.0 | 0.476 | 0.68 |
| refine | tsmom_d1_lb40_a2_notrail | LTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0025 | -8.6 | -214.1 | -440.0 | -114.6 | 59.0 | 0.22 | 0.44 |
| refine | tsmom_d1_lb40_a2_notrail | SOLUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0125 | 18.5 | 407.1 | -543.5 | -241.5 | 44.0 | 0.386 | 0.636 |
| refine | tsmom_d1_lb40_a2_notrail | XRPUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 2.0, "trail": false} | 0.0075 | -15.1 | -331.8 | -498.3 | -171.9 | 67.0 | 0.299 | 0.409 |
| screen | tsmom_d1_lb40_a3 | ADAUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.005 | 2.7 | 68.5 | -108.6 | -39.1 | 24.0 | 0.375 | 0.16 |
| screen | tsmom_d1_lb40_a3 | BNBUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.01 | 15.6 | 390.4 | -509.1 | -140.6 | 71.0 | 0.38 | 0.48 |
| screen | tsmom_d1_lb40_a3 | BTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.015 | 43.2 | 1080.4 | -526.3 | -147.8 | 66.0 | 0.379 | 0.6 |
| screen | tsmom_d1_lb40_a3 | DOTUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.005 | -18.0 | -451.1 | -470.9 | -40.3 | 36.0 | 0.167 | 0.2 |
| screen | tsmom_d1_lb40_a3 | ETHUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.02 | 70.9 | 1771.9 | -536.8 | -266.9 | 48.0 | 0.5 | 0.68 |
| screen | tsmom_d1_lb40_a3 | LTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.005 | -12.5 | -311.9 | -589.8 | -105.4 | 67.0 | 0.254 | 0.4 |
| screen | tsmom_d1_lb40_a3 | SOLUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.02 | 28.8 | 633.2 | -593.0 | -225.9 | 52.0 | 0.404 | 0.682 |
| screen | tsmom_d1_lb40_a3 | XRPUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 3.0} | 0.0075 | -14.7 | -323.3 | -459.1 | -115.5 | 73.0 | 0.315 | 0.364 |
| refine | tsmom_d1_lb40_a4 | ADAUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.0075 | -0.7 | -16.5 | -198.6 | -44.7 | 33.0 | 0.394 | 0.12 |
| refine | tsmom_d1_lb40_a4 | BNBUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.0075 | 22.6 | 566.2 | -475.1 | -174.1 | 61.0 | 0.344 | 0.52 |
| refine | tsmom_d1_lb40_a4 | BTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.02 | 42.6 | 1066.1 | -535.6 | -147.8 | 60.0 | 0.383 | 0.56 |
| refine | tsmom_d1_lb40_a4 | DOTUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.0075 | -19.1 | -477.2 | -513.8 | -50.3 | 34.0 | 0.235 | 0.24 |
| refine | tsmom_d1_lb40_a4 | ETHUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.02 | 59.9 | 1497.0 | -411.5 | -198.9 | 40.0 | 0.45 | 0.68 |
| refine | tsmom_d1_lb40_a4 | LTCUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.005 | -9.3 | -233.5 | -495.8 | -114.8 | 59.0 | 0.22 | 0.4 |
| refine | tsmom_d1_lb40_a4 | SOLUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.02 | 17.2 | 377.8 | -507.6 | -199.5 | 48.0 | 0.417 | 0.682 |
| refine | tsmom_d1_lb40_a4 | XRPUSD | D1 | build_tsmom | {"lb": 40, "atr_mult": 4.0} | 0.015 | -16.3 | -358.1 | -525.3 | -173.9 | 66.0 | 0.318 | 0.409 |
| refine | tsmom_d1_lb60_a3 | ADAUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.005 | 2.6 | 64.2 | -114.5 | -37.9 | 17.0 | 0.412 | 0.12 |
| refine | tsmom_d1_lb60_a3 | BNBUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.0075 | 6.1 | 152.6 | -527.2 | -119.8 | 59.0 | 0.322 | 0.48 |
| refine | tsmom_d1_lb60_a3 | BTCUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.02 | 58.1 | 1452.2 | -564.0 | -221.6 | 41.0 | 0.415 | 0.6 |
| refine | tsmom_d1_lb60_a3 | DOTUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.005 | -7.7 | -192.4 | -276.1 | -40.3 | 22.0 | 0.182 | 0.2 |
| refine | tsmom_d1_lb60_a3 | ETHUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.015 | 62.1 | 1551.4 | -492.3 | -240.8 | 45.0 | 0.422 | 0.6 |
| refine | tsmom_d1_lb60_a3 | LTCUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.005 | -5.1 | -126.6 | -497.8 | -109.4 | 52.0 | 0.288 | 0.44 |
| refine | tsmom_d1_lb60_a3 | SOLUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.0125 | 0.4 | 9.1 | -551.8 | -126.5 | 49.0 | 0.347 | 0.455 |
| refine | tsmom_d1_lb60_a3 | XRPUSD | D1 | build_tsmom | {"lb": 60, "atr_mult": 3.0} | 0.0125 | 11.6 | 255.6 | -562.6 | -188.8 | 54.0 | 0.463 | 0.364 |
| screen | tsmom_h4_lb120 | ADAUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | 0.0025 | -4.0 | -99.1 | -480.7 | -47.1 | 142.0 | 0.275 | 0.24 |
| rerun | tsmom_h4_lb120 | BNBUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | nan | -6.3 | -158.1 | -713.4 | -61.1 | 333.0 | 0.324 | 0.48 |
| screen | tsmom_h4_lb120 | BTCUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | 0.005 | 43.7 | 1092.2 | -500.1 | -87.6 | 326.0 | 0.374 | 0.72 |
| rerun | tsmom_h4_lb120 | DOTUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | nan | -44.5 | -1111.7 | -1290.6 | -51.7 | 186.0 | 0.167 | 0.28 |
| screen | tsmom_h4_lb120 | ETHUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | 0.005 | 60.1 | 1502.4 | -598.7 | -97.5 | 330.0 | 0.336 | 0.44 |
| screen | tsmom_h4_lb120 | LTCUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | nan | -91.4 | -2283.9 | -2327.5 | -75.2 | 354.0 | 0.186 | 0.24 |
| screen | tsmom_h4_lb120 | SOLUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | 0.0025 | -7.7 | -168.8 | -473.5 | -48.2 | 293.0 | 0.294 | 0.5 |
| screen | tsmom_h4_lb120 | XRPUSD | H4 | build_tsmom | {"lb": 120, "atr_mult": 2.5} | 0.0025 | -4.7 | -104.1 | -473.0 | -74.8 | 281.0 | 0.313 | 0.409 |
| screen | tsmom_h4_lb30 | ADAUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0025 | -16.0 | -399.5 | -581.7 | -51.9 | 199.0 | 0.241 | 0.2 |
| screen | tsmom_h4_lb30 | BNBUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | nan | -48.7 | -1216.7 | -1237.3 | -61.1 | 540.0 | 0.27 | 0.32 |
| screen | tsmom_h4_lb30 | BTCUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.005 | 2.4 | 60.0 | -568.3 | -98.1 | 547.0 | 0.322 | 0.48 |
| screen | tsmom_h4_lb30 | DOTUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | nan | -79.0 | -1974.1 | -2195.8 | -75.3 | 309.0 | 0.162 | 0.28 |
| screen | tsmom_h4_lb30 | ETHUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0025 | 4.9 | 122.2 | -385.1 | -51.4 | 513.0 | 0.312 | 0.48 |
| screen | tsmom_h4_lb30 | LTCUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | nan | -140.4 | -3511.2 | -3511.2 | -80.1 | 513.0 | 0.166 | 0.0 |
| screen | tsmom_h4_lb30 | SOLUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0025 | -15.6 | -343.2 | -564.8 | -65.5 | 425.0 | 0.308 | 0.409 |
| screen | tsmom_h4_lb30 | XRPUSD | H4 | build_tsmom | {"lb": 30, "atr_mult": 2.5} | 0.0025 | 7.4 | 163.7 | -389.3 | -77.0 | 420.0 | 0.312 | 0.545 |
| screen | tsmom_h4_lb60 | ADAUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -34.8 | -869.6 | -1315.5 | -63.6 | 204.0 | 0.167 | 0.16 |
| screen | tsmom_h4_lb60 | BNBUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -24.7 | -616.8 | -680.5 | -63.0 | 420.0 | 0.286 | 0.4 |
| screen | tsmom_h4_lb60 | BTCUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | 0.0025 | 22.2 | 554.2 | -286.7 | -57.8 | 218.0 | 0.367 | 0.56 |
| screen | tsmom_h4_lb60 | DOTUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -78.2 | -1955.6 | -2263.8 | -72.9 | 259.0 | 0.17 | 0.28 |
| screen | tsmom_h4_lb60 | ETHUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | 0.0025 | 15.9 | 396.4 | -511.9 | -58.9 | 425.0 | 0.346 | 0.56 |
| screen | tsmom_h4_lb60 | LTCUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -91.9 | -2297.8 | -2373.6 | -75.2 | 365.0 | 0.214 | 0.2 |
| screen | tsmom_h4_lb60 | SOLUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -8.8 | -193.9 | -608.8 | -39.3 | 331.0 | 0.284 | 0.455 |
| screen | tsmom_h4_lb60 | XRPUSD | H4 | build_tsmom | {"lb": 60, "atr_mult": 2.5} | nan | -12.9 | -283.5 | -733.9 | -74.8 | 340.0 | 0.306 | 0.409 |
| refine | usopen_day_0_15_t10 | ADAUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | -70.1 | -1753.4 | -1860.0 | -35.4 | 430.0 | 0.328 | 0.24 |
| refine | usopen_day_0_15_t10 | BNBUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | -38.1 | -953.7 | -993.1 | -39.0 | 501.0 | 0.387 | 0.28 |
| refine | usopen_day_0_15_t10 | BTCUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | 20.1 | 502.3 | -721.0 | -25.0 | 475.0 | 0.417 | 0.48 |
| refine | usopen_day_0_15_t10 | DOTUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | -165.7 | -4142.4 | -4173.5 | -36.1 | 469.0 | 0.198 | 0.08 |
| refine | usopen_day_0_15_t10 | ETHUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | 0.0025 | 44.3 | 1108.2 | -483.3 | -25.0 | 480.0 | 0.427 | 0.6 |
| refine | usopen_day_0_15_t10 | LTCUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | -207.7 | -5193.6 | -5252.4 | -25.3 | 483.0 | 0.199 | 0.0 |
| refine | usopen_day_0_15_t10 | SOLUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | nan | -67.6 | -1487.1 | -1567.2 | -25.0 | 459.0 | 0.359 | 0.273 |
| refine | usopen_day_0_15_t10 | XRPUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0} | 0.0025 | 10.4 | 228.8 | -519.6 | -25.0 | 434.0 | 0.412 | 0.409 |
| refine | usopen_day_0_15_t10_fade | ADAUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -61.3 | -1531.8 | -2116.3 | -25.0 | 430.0 | 0.302 | 0.28 |
| refine | usopen_day_0_15_t10_fade | BNBUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -130.7 | -3267.6 | -3285.9 | -25.0 | 501.0 | 0.343 | 0.08 |
| refine | usopen_day_0_15_t10_fade | BTCUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -38.8 | -969.4 | -1132.6 | -25.0 | 475.0 | 0.379 | 0.32 |
| refine | usopen_day_0_15_t10_fade | DOTUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -141.5 | -3537.0 | -3547.9 | -25.0 | 469.0 | 0.209 | 0.16 |
| refine | usopen_day_0_15_t10_fade | ETHUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -88.6 | -2215.5 | -2256.7 | -25.6 | 480.0 | 0.365 | 0.24 |
| refine | usopen_day_0_15_t10_fade | LTCUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -194.1 | -4853.0 | -4853.0 | -25.0 | 483.0 | 0.201 | 0.04 |
| refine | usopen_day_0_15_t10_fade | SOLUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -78.8 | -1733.5 | -1850.6 | -25.0 | 459.0 | 0.366 | 0.227 |
| refine | usopen_day_0_15_t10_fade | XRPUSD | H1 | build_us_open_mom | {"t0": 0, "t1": 15, "thresh": 1.0, "fade": true} | nan | -103.8 | -2283.4 | -2401.9 | -25.0 | 434.0 | 0.378 | 0.182 |
| screen | usopen_fade_t10 | ADAUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -59.9 | -1497.9 | -1539.1 | -25.0 | 285.0 | 0.281 | 0.08 |
| screen | usopen_fade_t10 | BNBUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -74.1 | -1853.0 | -2023.0 | -25.0 | 359.0 | 0.331 | 0.12 |
| screen | usopen_fade_t10 | BTCUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -18.2 | -454.2 | -660.8 | -24.9 | 354.0 | 0.489 | 0.36 |
| screen | usopen_fade_t10 | DOTUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -97.7 | -2443.7 | -2468.1 | -25.0 | 271.0 | 0.181 | 0.04 |
| screen | usopen_fade_t10 | ETHUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -56.7 | -1416.8 | -1562.9 | -25.0 | 321.0 | 0.408 | 0.28 |
| screen | usopen_fade_t10 | LTCUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -144.5 | -3613.2 | -3613.2 | -25.0 | 321.0 | 0.131 | 0.0 |
| screen | usopen_fade_t10 | SOLUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -76.5 | -1682.9 | -1794.9 | -24.9 | 313.0 | 0.31 | 0.045 |
| screen | usopen_fade_t10 | XRPUSD | H1 | build_us_open_mom | {"thresh": 1.0, "fade": true} | nan | -74.2 | -1633.3 | -1740.1 | -25.0 | 311.0 | 0.379 | 0.091 |
| refine | usopen_ldn_10_15_t075 | ADAUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -55.3 | -1382.9 | -1388.9 | -25.0 | 388.0 | 0.345 | 0.2 |
| refine | usopen_ldn_10_15_t075 | BNBUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -62.2 | -1554.5 | -1560.2 | -25.4 | 449.0 | 0.354 | 0.28 |
| refine | usopen_ldn_10_15_t075 | BTCUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | 0.0025 | 1.9 | 47.6 | -586.4 | -25.0 | 413.0 | 0.395 | 0.6 |
| refine | usopen_ldn_10_15_t075 | DOTUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -131.4 | -3284.6 | -3284.6 | -56.0 | 408.0 | 0.223 | 0.16 |
| refine | usopen_ldn_10_15_t075 | ETHUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -7.9 | -196.5 | -757.4 | -25.0 | 394.0 | 0.383 | 0.48 |
| refine | usopen_ldn_10_15_t075 | LTCUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -193.9 | -4847.2 | -4857.7 | -25.0 | 422.0 | 0.194 | 0.0 |
| refine | usopen_ldn_10_15_t075 | SOLUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -54.9 | -1207.5 | -1340.4 | -25.0 | 393.0 | 0.372 | 0.318 |
| refine | usopen_ldn_10_15_t075 | XRPUSD | H1 | build_us_open_mom | {"t0": 10, "t1": 15, "thresh": 0.75} | nan | -36.0 | -792.0 | -968.3 | -25.0 | 389.0 | 0.396 | 0.318 |
| screen | usopen_t075 | ADAUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -75.1 | -1877.6 | -1914.6 | -25.0 | 350.0 | 0.254 | 0.16 |
| screen | usopen_t075 | BNBUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -81.2 | -2029.8 | -2029.8 | -25.0 | 433.0 | 0.279 | 0.12 |
| screen | usopen_t075 | BTCUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -33.8 | -845.5 | -874.5 | -25.0 | 434.0 | 0.406 | 0.24 |
| screen | usopen_t075 | DOTUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -103.7 | -2593.1 | -2715.1 | -25.0 | 357.0 | 0.216 | 0.08 |
| screen | usopen_t075 | ETHUSD | H1 | build_us_open_mom | {"thresh": 0.75} | 0.0025 | 3.4 | 85.2 | -591.3 | -25.0 | 397.0 | 0.423 | 0.48 |
| screen | usopen_t075 | LTCUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -179.2 | -4480.4 | -4480.4 | -25.0 | 416.0 | 0.139 | 0.04 |
| screen | usopen_t075 | SOLUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -46.2 | -1016.2 | -1231.9 | -25.0 | 389.0 | 0.36 | 0.136 |
| screen | usopen_t075 | XRPUSD | H1 | build_us_open_mom | {"thresh": 0.75} | nan | -64.1 | -1410.2 | -1416.7 | -25.0 | 381.0 | 0.357 | 0.227 |
| screen | usopen_t075_rr15 | ADAUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -74.6 | -1866.1 | -1866.2 | -25.0 | 346.0 | 0.289 | 0.16 |
| screen | usopen_t075_rr15 | BNBUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -81.5 | -2037.7 | -2037.7 | -25.0 | 433.0 | 0.305 | 0.12 |
| screen | usopen_t075_rr15 | BTCUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -24.0 | -599.7 | -676.4 | -25.0 | 434.0 | 0.422 | 0.36 |
| screen | usopen_t075_rr15 | DOTUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -39.1 | -978.2 | -994.2 | -25.0 | 212.0 | 0.358 | 0.08 |
| screen | usopen_t075_rr15 | ETHUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | 0.0025 | -8.5 | -213.4 | -502.7 | -25.0 | 397.0 | 0.428 | 0.48 |
| screen | usopen_t075_rr15 | LTCUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -126.6 | -3165.5 | -3169.4 | -25.0 | 314.0 | 0.204 | 0.0 |
| screen | usopen_t075_rr15 | SOLUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -43.2 | -949.9 | -1117.2 | -25.0 | 388.0 | 0.376 | 0.318 |
| screen | usopen_t075_rr15 | XRPUSD | H1 | build_us_open_mom | {"thresh": 0.75, "rr": 1.5} | nan | -58.8 | -1294.3 | -1294.3 | -25.0 | 381.0 | 0.383 | 0.182 |
| screen | usopen_t10 | ADAUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -62.0 | -1550.6 | -1599.6 | -25.0 | 285.0 | 0.249 | 0.16 |
| screen | usopen_t10 | BNBUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -67.9 | -1698.3 | -1698.3 | -25.0 | 359.0 | 0.273 | 0.16 |
| screen | usopen_t10 | BTCUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -24.9 | -622.2 | -631.9 | -25.0 | 354.0 | 0.41 | 0.28 |
| screen | usopen_t10 | DOTUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -84.5 | -2112.4 | -2192.3 | -25.0 | 271.0 | 0.203 | 0.12 |
| screen | usopen_t10 | ETHUSD | H1 | build_us_open_mom | {"thresh": 1.0} | 0.0025 | 19.1 | 476.3 | -342.6 | -25.0 | 321.0 | 0.455 | 0.52 |
| screen | usopen_t10 | LTCUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -139.3 | -3483.2 | -3495.6 | -25.0 | 321.0 | 0.146 | 0.04 |
| screen | usopen_t10 | SOLUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -34.4 | -757.2 | -876.7 | -25.0 | 313.0 | 0.364 | 0.182 |
| screen | usopen_t10 | XRPUSD | H1 | build_us_open_mom | {"thresh": 1.0} | nan | -51.4 | -1131.9 | -1197.7 | -25.0 | 311.0 | 0.354 | 0.273 |
| refine | usopen_t10_rr2 | ADAUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -58.6 | -1466.1 | -1501.8 | -25.0 | 285.0 | 0.27 | 0.16 |
| refine | usopen_t10_rr2 | BNBUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -65.2 | -1630.8 | -1630.8 | -25.0 | 359.0 | 0.284 | 0.2 |
| refine | usopen_t10_rr2 | BTCUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | 0.0025 | -19.7 | -492.7 | -502.4 | -25.0 | 354.0 | 0.415 | 0.36 |
| refine | usopen_t10_rr2 | DOTUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -43.9 | -1096.5 | -1195.5 | -25.0 | 185.0 | 0.292 | 0.16 |
| refine | usopen_t10_rr2 | ETHUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | 0.005 | 31.0 | 776.0 | -451.4 | -50.0 | 321.0 | 0.461 | 0.52 |
| refine | usopen_t10_rr2 | LTCUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -114.4 | -2859.6 | -2883.2 | -25.0 | 275.0 | 0.185 | 0.08 |
| refine | usopen_t10_rr2 | SOLUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -33.3 | -733.5 | -847.5 | -25.0 | 313.0 | 0.371 | 0.227 |
| refine | usopen_t10_rr2 | XRPUSD | H1 | build_us_open_mom | {"thresh": 1.0, "rr": 2.0} | nan | -46.4 | -1020.9 | -1103.1 | -25.0 | 311.0 | 0.367 | 0.318 |
| refine | wd_L0 | ADAUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.0125 | -17.6 | -440.9 | -545.8 | -125.0 | 85.0 | 0.506 | 0.28 |
| refine | wd_L0 | BNBUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.01 | -15.6 | -388.8 | -505.5 | -99.9 | 106.0 | 0.538 | 0.48 |
| refine | wd_L0 | BTCUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.02 | 43.4 | 1084.6 | -365.9 | -172.2 | 106.0 | 0.575 | 0.56 |
| refine | wd_L0 | DOTUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.0025 | -9.1 | -227.6 | -233.9 | -15.9 | 34.0 | 0.118 | 0.04 |
| refine | wd_L0 | ETHUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.0125 | 2.2 | 55.8 | -577.1 | -124.5 | 106.0 | 0.575 | 0.4 |
| refine | wd_L0 | LTCUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.0025 | -19.0 | -475.8 | -475.8 | -25.0 | 106.0 | 0.274 | 0.12 |
| refine | wd_L0 | SOLUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.015 | -10.6 | -234.3 | -591.1 | -138.8 | 93.0 | 0.495 | 0.273 |
| refine | wd_L0 | XRPUSD | D1 | build_weekday | {"long_days": [0], "short_days": []} | 0.01 | -5.8 | -128.2 | -511.5 | -100.0 | 93.0 | 0.484 | 0.5 |
| refine | wd_L0_h1 | BTCUSD | H1 | build_weekday | {"long_days": [0], "short_days": []} | 0.005 | 34.9 | 873.6 | -509.6 | -49.9 | 106.0 | 0.34 | 0.56 |
| refine | wd_L0_h1 | ETHUSD | H1 | build_weekday | {"long_days": [0], "short_days": []} | 0.005 | 23.4 | 585.4 | -537.9 | -50.0 | 106.0 | 0.396 | 0.52 |
| refine | wd_L0_h1 | SOLUSD | H1 | build_weekday | {"long_days": [0], "short_days": []} | 0.005 | -12.1 | -265.7 | -555.7 | -49.9 | 95.0 | 0.368 | 0.409 |
| refine | wd_L0_h1 | XRPUSD | H1 | build_weekday | {"long_days": [0], "short_days": []} | 0.005 | 7.8 | 171.9 | -520.9 | -50.0 | 95.0 | 0.358 | 0.455 |
| refine | wd_L1 | ADAUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.0075 | -18.2 | -455.0 | -553.4 | -55.7 | 53.0 | 0.283 | 0.16 |
| refine | wd_L1 | BNBUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.01 | -17.7 | -442.0 | -527.1 | -89.2 | 106.0 | 0.396 | 0.28 |
| refine | wd_L1 | BTCUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.01 | -11.6 | -290.6 | -495.0 | -80.1 | 106.0 | 0.472 | 0.56 |
| refine | wd_L1 | DOTUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.0025 | -10.7 | -267.1 | -267.1 | -17.8 | 33.0 | 0.061 | 0.0 |
| refine | wd_L1 | ETHUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.01 | -19.6 | -490.4 | -578.5 | -98.1 | 106.0 | 0.396 | 0.4 |
| refine | wd_L1 | LTCUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.0025 | -15.7 | -393.2 | -393.2 | -25.0 | 106.0 | 0.292 | 0.12 |
| refine | wd_L1 | SOLUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.0075 | -22.0 | -483.6 | -566.1 | -74.8 | 93.0 | 0.355 | 0.318 |
| refine | wd_L1 | XRPUSD | D1 | build_weekday | {"long_days": [1], "short_days": []} | 0.005 | -19.0 | -418.6 | -445.3 | -50.0 | 88.0 | 0.352 | 0.273 |
| refine | wd_L1_h1 | BTCUSD | H1 | build_weekday | {"long_days": [1], "short_days": []} | 0.0025 | -9.9 | -248.4 | -471.1 | -25.0 | 100.0 | 0.38 | 0.44 |
| refine | wd_L1_h1 | ETHUSD | H1 | build_weekday | {"long_days": [1], "short_days": []} | nan | -21.8 | -545.5 | -693.6 | -25.0 | 106.0 | 0.321 | 0.36 |
| refine | wd_L1_h1 | SOLUSD | H1 | build_weekday | {"long_days": [1], "short_days": []} | nan | -27.4 | -602.3 | -647.1 | -24.7 | 95.0 | 0.305 | 0.273 |
| refine | wd_L1_h1 | XRPUSD | H1 | build_weekday | {"long_days": [1], "short_days": []} | nan | -38.9 | -856.0 | -975.2 | -25.0 | 94.0 | 0.277 | 0.318 |
| refine | wd_L2 | ADAUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.01 | -13.2 | -329.2 | -565.0 | -73.5 | 73.0 | 0.384 | 0.32 |
| refine | wd_L2 | BNBUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.02 | 5.6 | 140.9 | -581.9 | -171.6 | 106.0 | 0.509 | 0.44 |
| refine | wd_L2 | BTCUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.02 | 60.7 | 1518.6 | -372.1 | -107.0 | 106.0 | 0.557 | 0.64 |
| refine | wd_L2 | DOTUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | -9.7 | -242.6 | -289.1 | -23.4 | 33.0 | 0.061 | 0.04 |
| refine | wd_L2 | ETHUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.02 | 60.5 | 1513.3 | -458.8 | -199.4 | 106.0 | 0.528 | 0.68 |
| refine | wd_L2 | LTCUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | -19.7 | -493.3 | -549.2 | -37.2 | 106.0 | 0.33 | 0.28 |
| refine | wd_L2 | SOLUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.015 | -5.1 | -112.8 | -484.7 | -100.1 | 93.0 | 0.43 | 0.364 |
| refine | wd_L2 | XRPUSD | D1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0125 | -14.0 | -308.5 | -500.5 | -125.0 | 93.0 | 0.409 | 0.455 |
| refine | wd_L2_h1 | BTCUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | 54.8 | 1371.2 | -568.7 | -49.4 | 106.0 | 0.509 | 0.64 |
| refine | wd_L2_h1 | ETHUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | 61.1 | 1528.5 | -477.5 | -50.0 | 106.0 | 0.453 | 0.64 |
| refine | wd_L2_h1 | SOLUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | 0.9 | 19.9 | -319.5 | -35.5 | 95.0 | 0.389 | 0.364 |
| refine | wd_L2_h1 | XRPUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | -12.1 | -266.5 | -518.2 | -25.0 | 95.0 | 0.347 | 0.409 |
| refine | wd_L3 | ADAUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.0075 | -17.6 | -438.9 | -515.9 | -62.0 | 52.0 | 0.346 | 0.16 |
| refine | wd_L3 | BNBUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.005 | -18.5 | -463.5 | -490.1 | -49.9 | 106.0 | 0.406 | 0.28 |
| refine | wd_L3 | BTCUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.0075 | -8.5 | -212.8 | -395.5 | -71.7 | 80.0 | 0.425 | 0.44 |
| refine | wd_L3 | DOTUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.0025 | -9.6 | -238.8 | -238.8 | -19.6 | 32.0 | 0.125 | 0.0 |
| refine | wd_L3 | ETHUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.005 | -15.9 | -397.5 | -456.9 | -47.7 | 106.0 | 0.377 | 0.24 |
| refine | wd_L3 | LTCUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.0025 | -13.3 | -331.6 | -367.5 | -25.0 | 106.0 | 0.283 | 0.2 |
| refine | wd_L3 | SOLUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.005 | -15.7 | -344.8 | -374.3 | -50.0 | 94.0 | 0.362 | 0.273 |
| refine | wd_L3 | XRPUSD | D1 | build_weekday | {"long_days": [3], "short_days": []} | 0.005 | -16.7 | -366.3 | -459.9 | -50.0 | 90.0 | 0.356 | 0.318 |
| refine | wd_L4 | ADAUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.015 | 1.1 | 27.7 | -535.3 | -150.0 | 91.0 | 0.418 | 0.44 |
| refine | wd_L4 | BNBUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.02 | -14.4 | -360.1 | -467.4 | -132.7 | 106.0 | 0.406 | 0.44 |
| refine | wd_L4 | BTCUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.02 | -1.2 | -29.2 | -540.7 | -173.2 | 106.0 | 0.481 | 0.44 |
| refine | wd_L4 | DOTUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.0025 | -9.4 | -234.8 | -234.8 | -19.4 | 32.0 | 0.094 | 0.0 |
| refine | wd_L4 | ETHUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.02 | 7.6 | 190.1 | -511.2 | -199.5 | 106.0 | 0.509 | 0.52 |
| refine | wd_L4 | LTCUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.0075 | -17.0 | -424.2 | -527.3 | -75.0 | 106.0 | 0.387 | 0.24 |
| refine | wd_L4 | SOLUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.0125 | -5.5 | -120.6 | -475.5 | -76.9 | 94.0 | 0.436 | 0.364 |
| refine | wd_L4 | XRPUSD | D1 | build_weekday | {"long_days": [4], "short_days": []} | 0.02 | -5.6 | -123.1 | -530.4 | -138.4 | 94.0 | 0.426 | 0.5 |
| refine | wd_L5 | ADAUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0075 | -11.4 | -284.5 | -294.3 | -75.0 | 52.0 | 0.308 | 0.08 |
| refine | wd_L5 | BNBUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.015 | 15.4 | 385.7 | -544.6 | -153.1 | 106.0 | 0.538 | 0.48 |
| refine | wd_L5 | BTCUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.02 | -7.9 | -198.2 | -432.4 | -163.7 | 106.0 | 0.547 | 0.44 |
| refine | wd_L5 | DOTUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0025 | -9.8 | -244.7 | -244.7 | -14.6 | 32.0 | 0.0 | 0.0 |
| refine | wd_L5 | ETHUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.02 | 0.3 | 8.7 | -428.0 | -199.4 | 106.0 | 0.594 | 0.52 |
| refine | wd_L5 | LTCUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0025 | -13.7 | -342.4 | -362.0 | -58.2 | 106.0 | 0.189 | 0.2 |
| refine | wd_L5 | SOLUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0125 | -17.2 | -377.9 | -560.9 | -119.9 | 94.0 | 0.426 | 0.318 |
| refine | wd_L5 | XRPUSD | D1 | build_weekday | {"long_days": [5], "short_days": []} | 0.01 | -16.5 | -362.1 | -517.4 | -126.4 | 94.0 | 0.457 | 0.273 |
| refine | wd_L5_h1 | BTCUSD | H1 | build_weekday | {"long_days": [5], "short_days": []} | 0.005 | -11.6 | -289.5 | -508.3 | -79.2 | 105.0 | 0.524 | 0.32 |
| refine | wd_L5_h1 | ETHUSD | H1 | build_weekday | {"long_days": [5], "short_days": []} | 0.005 | 2.5 | 63.4 | -410.4 | -50.2 | 105.0 | 0.571 | 0.52 |
| refine | wd_L5_h1 | SOLUSD | H1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0025 | -13.9 | -305.1 | -427.2 | -36.9 | 95.0 | 0.421 | 0.318 |
| refine | wd_L5_h1 | XRPUSD | H1 | build_weekday | {"long_days": [5], "short_days": []} | 0.0025 | -13.4 | -295.7 | -450.7 | -117.8 | 95.0 | 0.442 | 0.273 |
| refine | wd_L6 | ADAUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0075 | -12.6 | -314.6 | -524.3 | -39.6 | 53.0 | 0.264 | 0.16 |
| refine | wd_L6 | BNBUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0075 | -19.4 | -485.3 | -570.2 | -74.7 | 105.0 | 0.362 | 0.28 |
| refine | wd_L6 | BTCUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.02 | -1.4 | -34.2 | -429.4 | -127.8 | 105.0 | 0.505 | 0.48 |
| refine | wd_L6 | DOTUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | -11.8 | -294.0 | -294.0 | -16.7 | 33.0 | 0.03 | 0.0 |
| refine | wd_L6 | ETHUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0125 | -11.1 | -277.6 | -582.6 | -124.5 | 105.0 | 0.41 | 0.44 |
| refine | wd_L6 | LTCUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | -14.9 | -373.7 | -373.7 | -25.0 | 105.0 | 0.2 | 0.16 |
| refine | wd_L6 | SOLUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.015 | -23.0 | -506.1 | -522.2 | -105.2 | 93.0 | 0.419 | 0.409 |
| refine | wd_L6 | XRPUSD | D1 | build_weekday | {"long_days": [6], "short_days": []} | 0.015 | -15.7 | -344.4 | -503.5 | -150.0 | 93.0 | 0.366 | 0.364 |
| refine | wd_L6_h1 | BTCUSD | H1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | 1.3 | 32.7 | -362.6 | -24.9 | 104.0 | 0.404 | 0.48 |
| refine | wd_L6_h1 | ETHUSD | H1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | -7.4 | -183.8 | -447.6 | -25.0 | 104.0 | 0.356 | 0.4 |
| refine | wd_L6_h1 | SOLUSD | H1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | -22.8 | -500.6 | -521.6 | -38.1 | 94.0 | 0.372 | 0.318 |
| refine | wd_L6_h1 | XRPUSD | H1 | build_weekday | {"long_days": [6], "short_days": []} | 0.0025 | -14.6 | -322.0 | -513.1 | -25.0 | 94.0 | 0.319 | 0.273 |
| refine | wd_MTW_Th | ADAUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.0025 | -9.0 | -226.0 | -226.0 | -25.0 | 48.0 | 0.271 | 0.0 |
| refine | wd_MTW_Th | BNBUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.005 | -14.9 | -372.4 | -525.4 | -50.0 | 424.0 | 0.491 | 0.44 |
| refine | wd_MTW_Th | BTCUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.015 | 85.8 | 2144.1 | -570.1 | -147.9 | 424.0 | 0.552 | 0.6 |
| refine | wd_MTW_Th | DOTUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | nan | -40.1 | -1001.7 | -1053.0 | -24.9 | 132.0 | 0.076 | 0.04 |
| refine | wd_MTW_Th | ETHUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.01 | 38.2 | 954.5 | -493.5 | -99.7 | 424.0 | 0.519 | 0.6 |
| refine | wd_MTW_Th | LTCUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | nan | -57.0 | -1425.8 | -1446.8 | -25.0 | 424.0 | 0.321 | 0.08 |
| refine | wd_MTW_Th | SOLUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.005 | -16.5 | -363.4 | -534.8 | -47.6 | 373.0 | 0.461 | 0.409 |
| refine | wd_MTW_Th | XRPUSD | D1 | build_weekday | {"long_days": [0, 1, 2]} | 0.005 | -19.2 | -421.3 | -538.9 | -50.0 | 357.0 | 0.457 | 0.364 |
| refine | wd_MWSu_Th | ADAUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.0025 | -8.0 | -200.7 | -200.7 | -25.0 | 48.0 | 0.25 | 0.0 |
| refine | wd_MWSu_Th | BNBUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.005 | -19.0 | -475.4 | -598.5 | -50.0 | 423.0 | 0.482 | 0.24 |
| refine | wd_MWSu_Th | BTCUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.02 | 153.9 | 3846.6 | -356.0 | -188.4 | 423.0 | 0.56 | 0.76 |
| refine | wd_MWSu_Th | DOTUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | nan | -41.1 | -1028.6 | -1078.1 | -24.9 | 132.0 | 0.068 | 0.04 |
| refine | wd_MWSu_Th | ETHUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.01 | 48.8 | 1220.8 | -506.1 | -99.7 | 423.0 | 0.522 | 0.6 |
| refine | wd_MWSu_Th | LTCUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | nan | -56.2 | -1406.2 | -1425.8 | -25.0 | 423.0 | 0.298 | 0.04 |
| refine | wd_MWSu_Th | SOLUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.0075 | -14.1 | -310.0 | -517.5 | -69.4 | 373.0 | 0.477 | 0.409 |
| refine | wd_MWSu_Th | XRPUSD | D1 | build_weekday | {"long_days": [0, 2, 6]} | 0.0075 | -8.4 | -184.0 | -550.1 | -75.0 | 373.0 | 0.461 | 0.5 |
| refine | wd_MW_ThF | ADAUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.0025 | -9.6 | -240.5 | -240.5 | -25.0 | 48.0 | 0.25 | 0.0 |
| refine | wd_MW_ThF | BNBUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.0025 | -10.8 | -270.1 | -327.7 | -25.0 | 424.0 | 0.5 | 0.24 |
| refine | wd_MW_ThF | BTCUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.02 | 150.7 | 3767.5 | -517.0 | -188.4 | 424.0 | 0.561 | 0.8 |
| refine | wd_MW_ThF | DOTUSD | D1 | build_weekday | {"short_days": [3, 4]} | nan | -39.9 | -996.9 | -1049.8 | -24.9 | 131.0 | 0.084 | 0.04 |
| refine | wd_MW_ThF | ETHUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.01 | 42.8 | 1070.8 | -496.5 | -99.7 | 424.0 | 0.531 | 0.68 |
| refine | wd_MW_ThF | LTCUSD | D1 | build_weekday | {"short_days": [3, 4]} | nan | -62.9 | -1573.6 | -1587.6 | -25.0 | 424.0 | 0.307 | 0.08 |
| refine | wd_MW_ThF | SOLUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.005 | -13.0 | -286.7 | -414.5 | -48.0 | 374.0 | 0.484 | 0.364 |
| refine | wd_MW_ThF | XRPUSD | D1 | build_weekday | {"short_days": [3, 4]} | 0.0075 | -14.1 | -310.6 | -509.4 | -75.0 | 374.0 | 0.492 | 0.364 |
| refine | wd_MW_Th_a15 | ADAUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.0025 | -13.5 | -337.2 | -374.4 | -25.0 | 78.0 | 0.321 | 0.08 |
| refine | wd_MW_Th_a15 | BNBUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.005 | -5.3 | -131.7 | -412.4 | -50.0 | 318.0 | 0.522 | 0.44 |
| refine | wd_MW_Th_a15 | BTCUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.02 | 195.4 | 4885.5 | -585.3 | -198.0 | 318.0 | 0.579 | 0.76 |
| refine | wd_MW_Th_a15 | DOTUSD | D1 | build_weekday | {"atr_mult": 1.5} | nan | -39.6 | -989.5 | -997.9 | -25.0 | 128.0 | 0.117 | 0.04 |
| refine | wd_MW_Th_a15 | ETHUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.015 | 126.9 | 3171.4 | -520.2 | -149.9 | 318.0 | 0.56 | 0.68 |
| refine | wd_MW_Th_a15 | LTCUSD | D1 | build_weekday | {"atr_mult": 1.5} | nan | -51.5 | -1287.1 | -1315.8 | -25.0 | 318.0 | 0.33 | 0.12 |
| refine | wd_MW_Th_a15 | SOLUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.0075 | 0.7 | 15.3 | -578.3 | -75.0 | 280.0 | 0.496 | 0.455 |
| refine | wd_MW_Th_a15 | XRPUSD | D1 | build_weekday | {"atr_mult": 1.5} | 0.0075 | 10.5 | 231.4 | -531.2 | -75.0 | 280.0 | 0.493 | 0.5 |
| refine | wd_MW_Th_a3 | ADAUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.005 | -14.6 | -366.1 | -444.6 | -35.3 | 89.0 | 0.348 | 0.08 |
| refine | wd_MW_Th_a3 | BNBUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.0125 | -8.9 | -221.5 | -578.2 | -124.3 | 318.0 | 0.522 | 0.48 |
| refine | wd_MW_Th_a3 | BTCUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.02 | 87.8 | 2195.6 | -239.2 | -143.5 | 318.0 | 0.579 | 0.76 |
| refine | wd_MW_Th_a3 | BTCUSD | H1 | build_weekday | {"atr_mult": 3.0} | 0.005 | 104.1 | 2601.6 | -398.9 | -49.9 | 318.0 | 0.522 | 0.8 |
| refine | wd_MW_Th_a3 | DOTUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.0025 | -12.1 | -302.0 | -307.3 | -18.1 | 42.0 | 0.024 | 0.0 |
| refine | wd_MW_Th_a3 | ETHUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.02 | 79.5 | 1987.1 | -434.9 | -199.8 | 318.0 | 0.56 | 0.64 |
| refine | wd_MW_Th_a3 | ETHUSD | H1 | build_weekday | {"atr_mult": 3.0} | 0.005 | 126.3 | 3157.2 | -465.5 | -50.0 | 318.0 | 0.528 | 0.72 |
| refine | wd_MW_Th_a3 | LTCUSD | D1 | build_weekday | {"atr_mult": 3.0} | nan | -29.2 | -730.2 | -746.1 | -24.9 | 318.0 | 0.33 | 0.12 |
| refine | wd_MW_Th_a3 | SOLUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.0125 | -2.4 | -52.1 | -545.5 | -123.9 | 280.0 | 0.496 | 0.455 |
| refine | wd_MW_Th_a3 | SOLUSD | H1 | build_weekday | {"atr_mult": 3.0} | 0.0025 | 5.1 | 112.6 | -408.5 | -25.0 | 285.0 | 0.456 | 0.545 |
| refine | wd_MW_Th_a3 | XRPUSD | D1 | build_weekday | {"atr_mult": 3.0} | 0.0125 | 5.9 | 129.7 | -523.8 | -125.0 | 280.0 | 0.493 | 0.5 |
| refine | wd_MW_Th_a3 | XRPUSD | H1 | build_weekday | {"atr_mult": 3.0} | 0.0025 | 29.2 | 643.0 | -399.6 | -25.0 | 282.0 | 0.479 | 0.591 |
| refine | wd_MW_Th_e0 | BTCUSD | H1 | build_weekday | {"entry_hour": 0} | nan | -19.9 | -497.9 | -845.7 | -25.2 | 305.0 | 0.367 | 0.48 |
| refine | wd_MW_Th_e0 | ETHUSD | H1 | build_weekday | {"entry_hour": 0} | nan | -56.4 | -1410.6 | -1761.2 | -38.5 | 316.0 | 0.345 | 0.28 |
| refine | wd_MW_Th_e0 | SOLUSD | H1 | build_weekday | {"entry_hour": 0} | nan | -66.8 | -1470.2 | -1510.1 | -36.0 | 283.0 | 0.339 | 0.182 |
| refine | wd_MW_Th_e0 | XRPUSD | H1 | build_weekday | {"entry_hour": 0} | nan | -66.0 | -1452.2 | -1505.6 | -32.1 | 282.0 | 0.344 | 0.227 |
| refine | wd_MW_Th_e12 | BTCUSD | H1 | build_weekday | {"entry_hour": 12} | 0.0025 | 1.7 | 41.7 | -480.7 | -59.3 | 315.0 | 0.337 | 0.4 |
| refine | wd_MW_Th_e12 | ETHUSD | H1 | build_weekday | {"entry_hour": 12} | nan | -15.0 | -374.8 | -1002.3 | -62.1 | 318.0 | 0.346 | 0.4 |
| refine | wd_MW_Th_e12 | SOLUSD | H1 | build_weekday | {"entry_hour": 12} | nan | -31.9 | -701.1 | -808.7 | -91.7 | 285.0 | 0.368 | 0.273 |
| refine | wd_MW_Th_e12 | XRPUSD | H1 | build_weekday | {"entry_hour": 12} | nan | -15.2 | -335.4 | -703.8 | -143.5 | 285.0 | 0.379 | 0.409 |
| refine | wd_MW_Th_noS | ADAUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.0075 | -19.8 | -494.8 | -592.9 | -75.0 | 106.0 | 0.396 | 0.2 |
| refine | wd_MW_Th_noS | BNBUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.01 | -12.7 | -317.9 | -542.1 | -99.9 | 212.0 | 0.524 | 0.44 |
| refine | wd_MW_Th_noS | BTCUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.02 | 104.1 | 2603.2 | -327.7 | -172.2 | 212.0 | 0.566 | 0.68 |
| refine | wd_MW_Th_noS | DOTUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.0025 | -18.8 | -470.1 | -523.0 | -23.4 | 67.0 | 0.09 | 0.04 |
| refine | wd_MW_Th_noS | ETHUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.015 | 48.3 | 1207.1 | -543.3 | -149.6 | 212.0 | 0.552 | 0.52 |
| refine | wd_MW_Th_noS | LTCUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | nan | -28.9 | -722.3 | -726.6 | -25.0 | 212.0 | 0.302 | 0.04 |
| refine | wd_MW_Th_noS | SOLUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.015 | -15.8 | -347.1 | -597.7 | -138.8 | 186.0 | 0.462 | 0.318 |
| refine | wd_MW_Th_noS | XRPUSD | D1 | build_weekday | {"long_days": [0, 2], "short_days": []} | 0.0125 | -21.3 | -468.8 | -568.6 | -125.0 | 186.0 | 0.446 | 0.409 |
| refine | wd_S0 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.0075 | -19.3 | -482.2 | -507.9 | -57.1 | 53.0 | 0.377 | 0.16 |
| refine | wd_S0 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.005 | -15.1 | -377.4 | -418.9 | -50.0 | 106.0 | 0.396 | 0.36 |
| refine | wd_S0 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.0075 | -16.1 | -403.2 | -425.2 | -53.5 | 87.0 | 0.402 | 0.32 |
| refine | wd_S0 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.0025 | -11.4 | -284.1 | -284.1 | -24.9 | 34.0 | 0.059 | 0.0 |
| refine | wd_S0 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.0075 | -14.0 | -349.2 | -505.4 | -74.6 | 106.0 | 0.396 | 0.48 |
| refine | wd_S0 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.005 | -18.3 | -456.4 | -482.5 | -50.0 | 106.0 | 0.349 | 0.28 |
| refine | wd_S0 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.0075 | -19.1 | -419.5 | -575.4 | -73.2 | 93.0 | 0.387 | 0.318 |
| refine | wd_S0 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [0]} | 0.005 | -17.5 | -384.6 | -477.8 | -50.0 | 91.0 | 0.396 | 0.364 |
| refine | wd_S1 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.02 | -6.2 | -155.0 | -497.2 | -167.6 | 100.0 | 0.46 | 0.44 |
| refine | wd_S1 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.01 | -18.3 | -458.0 | -558.5 | -100.0 | 106.0 | 0.491 | 0.28 |
| refine | wd_S1 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.02 | 16.0 | 400.6 | -446.9 | -126.7 | 106.0 | 0.519 | 0.48 |
| refine | wd_S1 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.0025 | -8.9 | -222.3 | -222.3 | -24.9 | 33.0 | 0.061 | 0.0 |
| refine | wd_S1 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.015 | 13.9 | 346.4 | -474.3 | -149.8 | 106.0 | 0.566 | 0.48 |
| refine | wd_S1 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.005 | -21.0 | -526.1 | -527.0 | -33.4 | 106.0 | 0.33 | 0.24 |
| refine | wd_S1 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.015 | -2.7 | -60.0 | -491.4 | -110.5 | 93.0 | 0.495 | 0.364 |
| refine | wd_S1 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [1]} | 0.02 | 25.9 | 570.6 | -280.9 | -124.0 | 93.0 | 0.527 | 0.5 |
| refine | wd_S2 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.0075 | -13.6 | -340.4 | -406.5 | -75.0 | 53.0 | 0.434 | 0.2 |
| refine | wd_S2 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.005 | -21.3 | -532.3 | -554.9 | -49.8 | 106.0 | 0.396 | 0.24 |
| refine | wd_S2 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.0075 | -14.7 | -368.6 | -440.9 | -53.2 | 83.0 | 0.422 | 0.4 |
| refine | wd_S2 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.0025 | -9.5 | -237.5 | -237.5 | -25.0 | 33.0 | 0.091 | 0.0 |
| refine | wd_S2 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.005 | -14.9 | -373.1 | -480.7 | -49.8 | 106.0 | 0.453 | 0.28 |
| refine | wd_S2 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.0025 | -16.6 | -415.1 | -415.1 | -25.0 | 106.0 | 0.264 | 0.08 |
| refine | wd_S2 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.0075 | -18.2 | -400.3 | -453.6 | -74.5 | 93.0 | 0.452 | 0.364 |
| refine | wd_S2 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [2]} | 0.015 | -14.0 | -307.4 | -479.9 | -150.0 | 93.0 | 0.495 | 0.364 |
| refine | wd_S3 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0075 | -9.9 | -248.2 | -496.8 | -75.0 | 52.0 | 0.5 | 0.28 |
| refine | wd_S3 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0125 | 0.8 | 19.6 | -512.2 | -125.0 | 106.0 | 0.519 | 0.6 |
| refine | wd_S3 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.02 | 51.1 | 1277.6 | -524.1 | -188.4 | 106.0 | 0.604 | 0.64 |
| refine | wd_S3 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0025 | -10.6 | -264.5 | -272.0 | -24.9 | 32.0 | 0.062 | 0.0 |
| refine | wd_S3 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.02 | 51.6 | 1290.6 | -507.8 | -199.4 | 106.0 | 0.575 | 0.72 |
| refine | wd_S3 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0025 | -12.4 | -310.2 | -331.3 | -25.0 | 106.0 | 0.387 | 0.44 |
| refine | wd_S3 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0125 | 7.7 | 169.5 | -542.2 | -121.9 | 94.0 | 0.564 | 0.591 |
| refine | wd_S3 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.015 | 24.5 | 538.9 | -505.6 | -150.0 | 94.0 | 0.585 | 0.545 |
| refine | wd_S3_h1 | BTCUSD | H1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.005 | 31.7 | 793.1 | -553.7 | -49.6 | 106.0 | 0.472 | 0.48 |
| refine | wd_S3_h1 | ETHUSD | H1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0075 | 96.0 | 2399.4 | -537.9 | -74.9 | 106.0 | 0.509 | 0.64 |
| refine | wd_S3_h1 | SOLUSD | H1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.005 | 35.2 | 775.3 | -438.3 | -49.8 | 96.0 | 0.5 | 0.545 |
| refine | wd_S3_h1 | XRPUSD | H1 | build_weekday | {"long_days": [], "short_days": [3]} | 0.0075 | 92.3 | 2030.6 | -476.7 | -75.0 | 96.0 | 0.542 | 0.545 |
| refine | wd_S4 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0075 | -21.2 | -530.7 | -551.1 | -75.0 | 54.0 | 0.389 | 0.2 |
| refine | wd_S4 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.005 | -15.6 | -390.7 | -417.3 | -49.9 | 106.0 | 0.434 | 0.32 |
| refine | wd_S4 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.02 | -4.5 | -113.3 | -411.5 | -179.6 | 106.0 | 0.509 | 0.52 |
| refine | wd_S4 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0025 | -10.5 | -262.3 | -262.3 | -24.9 | 32.0 | 0.094 | 0.0 |
| refine | wd_S4 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0125 | -19.2 | -478.8 | -527.9 | -124.7 | 106.0 | 0.443 | 0.44 |
| refine | wd_S4 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0025 | -21.6 | -541.1 | -541.1 | -25.0 | 106.0 | 0.236 | 0.04 |
| refine | wd_S4 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.01 | -24.5 | -538.5 | -538.5 | -96.1 | 94.0 | 0.447 | 0.364 |
| refine | wd_S4 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0125 | -22.6 | -497.9 | -569.3 | -125.0 | 94.0 | 0.489 | 0.364 |
| refine | wd_S4_h1 | BTCUSD | H1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.005 | -8.7 | -217.8 | -530.5 | -50.0 | 106.0 | 0.396 | 0.48 |
| refine | wd_S4_h1 | ETHUSD | H1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0025 | -10.4 | -260.5 | -399.8 | -25.0 | 106.0 | 0.368 | 0.4 |
| refine | wd_S4_h1 | SOLUSD | H1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0025 | -14.1 | -310.1 | -320.0 | -24.7 | 96.0 | 0.375 | 0.409 |
| refine | wd_S4_h1 | XRPUSD | H1 | build_weekday | {"long_days": [], "short_days": [4]} | 0.0075 | -5.2 | -113.4 | -557.6 | -75.0 | 96.0 | 0.438 | 0.455 |
| refine | wd_S5 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.01 | -18.3 | -456.7 | -554.8 | -100.0 | 74.0 | 0.351 | 0.32 |
| refine | wd_S5 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.005 | -21.0 | -525.7 | -531.9 | -49.8 | 106.0 | 0.321 | 0.2 |
| refine | wd_S5 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.02 | 2.1 | 52.7 | -302.0 | -55.9 | 106.0 | 0.406 | 0.44 |
| refine | wd_S5 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.0025 | -10.5 | -261.8 | -261.8 | -25.0 | 32.0 | 0.031 | 0.0 |
| refine | wd_S5 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.02 | -18.6 | -463.9 | -516.5 | -129.1 | 106.0 | 0.377 | 0.32 |
| refine | wd_S5 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.0025 | -13.0 | -325.6 | -330.2 | -25.0 | 106.0 | 0.226 | 0.2 |
| refine | wd_S5 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.015 | -24.7 | -543.1 | -566.2 | -147.9 | 94.0 | 0.404 | 0.364 |
| refine | wd_S5 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.015 | -15.2 | -333.7 | -564.3 | -150.0 | 94.0 | 0.383 | 0.409 |
| refine | wd_S5_h1 | BTCUSD | H1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.005 | -13.5 | -337.4 | -560.7 | -100.1 | 105.0 | 0.4 | 0.44 |
| refine | wd_S5_h1 | ETHUSD | H1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.0025 | -13.8 | -345.0 | -406.3 | -38.6 | 105.0 | 0.362 | 0.36 |
| refine | wd_S5_h1 | SOLUSD | H1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.0025 | -9.4 | -207.7 | -294.3 | -36.5 | 95.0 | 0.389 | 0.364 |
| refine | wd_S5_h1 | XRPUSD | H1 | build_weekday | {"long_days": [], "short_days": [5]} | 0.0025 | -17.1 | -377.2 | -462.6 | -44.7 | 95.0 | 0.368 | 0.364 |
| refine | wd_S6 | ADAUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.015 | -21.3 | -533.5 | -557.2 | -150.0 | 89.0 | 0.461 | 0.4 |
| refine | wd_S6 | BNBUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0075 | -8.6 | -215.1 | -537.4 | -74.9 | 105.0 | 0.476 | 0.48 |
| refine | wd_S6 | BTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.02 | -5.2 | -129.3 | -531.7 | -157.1 | 105.0 | 0.486 | 0.48 |
| refine | wd_S6 | DOTUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.005 | -23.2 | -579.8 | -579.8 | -49.7 | 67.0 | 0.239 | 0.2 |
| refine | wd_S6 | ETHUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0125 | -1.8 | -45.1 | -523.8 | -124.8 | 105.0 | 0.486 | 0.52 |
| refine | wd_S6 | LTCUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.005 | -21.7 | -542.0 | -573.3 | -49.9 | 105.0 | 0.333 | 0.32 |
| refine | wd_S6 | SOLUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.01 | -20.2 | -445.2 | -488.4 | -90.4 | 93.0 | 0.409 | 0.318 |
| refine | wd_S6 | XRPUSD | D1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0125 | -16.8 | -370.1 | -535.7 | -125.0 | 93.0 | 0.43 | 0.5 |
| refine | wd_S6_h1 | BTCUSD | H1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0025 | -7.2 | -180.0 | -439.9 | -24.9 | 104.0 | 0.365 | 0.4 |
| refine | wd_S6_h1 | ETHUSD | H1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0025 | 2.2 | 55.8 | -555.0 | -25.0 | 104.0 | 0.413 | 0.48 |
| refine | wd_S6_h1 | SOLUSD | H1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0025 | -13.6 | -299.1 | -597.7 | -24.9 | 94.0 | 0.383 | 0.455 |
| refine | wd_S6_h1 | XRPUSD | H1 | build_weekday | {"long_days": [], "short_days": [6]} | 0.0025 | -4.3 | -95.1 | -444.8 | -25.0 | 94.0 | 0.394 | 0.5 |
| screen | weekday_MW | ADAUSD | H1 | build_weekday | {"short_days": []} | 0.0025 | -12.2 | -304.3 | -582.8 | -25.0 | 166.0 | 0.386 | 0.36 |
| screen | weekday_MW | BNBUSD | H1 | build_weekday | {"short_days": []} | 0.0025 | -13.3 | -331.7 | -570.5 | -25.0 | 212.0 | 0.448 | 0.44 |
| screen | weekday_MW | BTCUSD | H1 | build_weekday | {"short_days": []} | 0.0025 | 40.5 | 1011.9 | -321.6 | -24.9 | 208.0 | 0.418 | 0.64 |
| screen | weekday_MW | DOTUSD | H1 | build_weekday | {"short_days": []} | nan | -53.2 | -1329.4 | -1472.8 | -35.0 | 193.0 | 0.259 | 0.24 |
| screen | weekday_MW | ETHUSD | H1 | build_weekday | {"short_days": []} | 0.005 | 84.6 | 2113.9 | -535.7 | -50.0 | 212.0 | 0.425 | 0.56 |
| screen | weekday_MW | LTCUSD | H1 | build_weekday | {"short_days": []} | nan | -86.1 | -2153.7 | -2181.7 | -32.5 | 212.0 | 0.255 | 0.08 |
| screen | weekday_MW | SOLUSD | H1 | build_weekday | {"short_days": []} | 0.0025 | -4.7 | -103.7 | -439.5 | -35.5 | 190.0 | 0.379 | 0.455 |
| screen | weekday_MW | XRPUSD | H1 | build_weekday | {"short_days": []} | 0.0025 | -8.2 | -180.6 | -401.7 | -25.0 | 190.0 | 0.353 | 0.409 |
| screen | weekday_MWF_Th | ADAUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | nan | -18.8 | -470.5 | -910.1 | -25.0 | 327.0 | 0.394 | 0.4 |
| screen | weekday_MWF_Th | BNBUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | nan | -22.3 | -557.0 | -827.9 | -25.0 | 424.0 | 0.427 | 0.32 |
| screen | weekday_MWF_Th | BTCUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | 0.0025 | 61.0 | 1525.6 | -324.2 | -24.9 | 412.0 | 0.434 | 0.8 |
| screen | weekday_MWF_Th | DOTUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | nan | -89.8 | -2244.8 | -2519.5 | -35.0 | 390.0 | 0.282 | 0.36 |
| screen | weekday_MWF_Th | ETHUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | 0.0025 | 87.3 | 2182.3 | -318.2 | -25.0 | 424.0 | 0.455 | 0.68 |
| screen | weekday_MWF_Th | LTCUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | nan | -135.5 | -3388.3 | -3441.9 | -32.5 | 424.0 | 0.3 | 0.04 |
| screen | weekday_MWF_Th | SOLUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | 0.0025 | 11.5 | 253.6 | -405.3 | -35.5 | 382.0 | 0.416 | 0.636 |
| screen | weekday_MWF_Th | XRPUSD | H1 | build_weekday | {"long_days": [0, 2, 4]} | 0.0025 | 24.0 | 527.8 | -576.5 | -25.0 | 382.0 | 0.408 | 0.545 |
| screen | weekday_MW_Th | ADAUSD | H1 | build_weekday | {} | nan | -8.2 | -206.0 | -775.4 | -25.0 | 246.0 | 0.411 | 0.48 |
| screen | weekday_MW_Th | BNBUSD | H1 | build_weekday | {} | 0.0025 | -4.7 | -118.2 | -470.2 | -25.0 | 318.0 | 0.453 | 0.4 |
| screen | weekday_MW_Th | BTCUSD | H1 | build_weekday | {} | 0.0025 | 54.2 | 1355.9 | -256.5 | -24.9 | 311.0 | 0.434 | 0.76 |
| screen | weekday_MW_Th | DOTUSD | H1 | build_weekday | {} | nan | -67.1 | -1676.3 | -1855.3 | -35.0 | 292.0 | 0.277 | 0.32 |
| screen | weekday_MW_Th | ETHUSD | H1 | build_weekday | {} | 0.005 | 147.9 | 3698.0 | -497.8 | -50.0 | 318.0 | 0.453 | 0.6 |
| screen | weekday_MW_Th | LTCUSD | H1 | build_weekday | {} | nan | -114.2 | -2854.7 | -2925.7 | -32.5 | 318.0 | 0.283 | 0.08 |
| screen | weekday_MW_Th | SOLUSD | H1 | build_weekday | {} | 0.0025 | 12.6 | 278.2 | -390.1 | -35.5 | 286.0 | 0.42 | 0.591 |
| screen | weekday_MW_Th | XRPUSD | H1 | build_weekday | {} | 0.0025 | 22.3 | 490.6 | -450.5 | -25.0 | 286.0 | 0.416 | 0.5 |
| screen | weekday_Th | ADAUSD | H1 | build_weekday | {"long_days": []} | 0.0025 | 3.9 | 98.3 | -327.6 | -25.0 | 80.0 | 0.463 | 0.44 |
| screen | weekday_Th | BNBUSD | H1 | build_weekday | {"long_days": []} | 0.0025 | 8.6 | 215.5 | -388.4 | -25.0 | 106.0 | 0.462 | 0.52 |
| screen | weekday_Th | BTCUSD | H1 | build_weekday | {"long_days": []} | 0.005 | 31.7 | 793.1 | -553.7 | -49.6 | 106.0 | 0.472 | 0.48 |
| screen | weekday_Th | DOTUSD | H1 | build_weekday | {"long_days": []} | 0.0025 | -13.8 | -346.2 | -529.6 | -25.0 | 99.0 | 0.313 | 0.32 |
| screen | weekday_Th | ETHUSD | H1 | build_weekday | {"long_days": []} | 0.0075 | 96.0 | 2399.4 | -537.9 | -74.9 | 106.0 | 0.509 | 0.64 |
| screen | weekday_Th | LTCUSD | H1 | build_weekday | {"long_days": []} | nan | -27.9 | -698.4 | -778.1 | -25.0 | 106.0 | 0.34 | 0.36 |
| screen | weekday_Th | SOLUSD | H1 | build_weekday | {"long_days": []} | 0.005 | 35.2 | 775.3 | -438.3 | -49.8 | 96.0 | 0.5 | 0.545 |
| screen | weekday_Th | XRPUSD | H1 | build_weekday | {"long_days": []} | 0.0075 | 92.3 | 2030.6 | -476.7 | -75.0 | 96.0 | 0.542 | 0.545 |
| screen | weekday_W | ADAUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | -8.2 | -205.9 | -423.1 | -25.0 | 80.0 | 0.338 | 0.36 |
| screen | weekday_W | BNBUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | -9.0 | -225.0 | -535.5 | -50.0 | 106.0 | 0.453 | 0.48 |
| screen | weekday_W | BTCUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | 54.8 | 1371.2 | -568.7 | -49.4 | 106.0 | 0.509 | 0.64 |
| screen | weekday_W | DOTUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | nan | -15.1 | -377.2 | -601.4 | -25.0 | 96.0 | 0.302 | 0.32 |
| screen | weekday_W | ETHUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.005 | 61.1 | 1528.5 | -477.5 | -50.0 | 106.0 | 0.453 | 0.64 |
| screen | weekday_W | LTCUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | nan | -34.8 | -869.0 | -916.0 | -25.0 | 106.0 | 0.292 | 0.16 |
| screen | weekday_W | SOLUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | 0.9 | 19.9 | -319.5 | -35.5 | 95.0 | 0.389 | 0.364 |
| screen | weekday_W | XRPUSD | H1 | build_weekday | {"long_days": [2], "short_days": []} | 0.0025 | -12.1 | -266.5 | -518.2 | -25.0 | 95.0 | 0.347 | 0.409 |
| screen | weekday_d1_MW_Th | ADAUSD | D1 | build_weekday | {} | 0.0025 | -6.4 | -160.8 | -160.8 | -25.0 | 36.0 | 0.278 | 0.0 |
| screen | weekday_d1_MW_Th | BNBUSD | D1 | build_weekday | {} | 0.0075 | -9.1 | -227.2 | -497.3 | -75.0 | 318.0 | 0.522 | 0.48 |
| screen | weekday_d1_MW_Th | BTCUSD | D1 | build_weekday | {} | 0.02 | 155.2 | 3880.8 | -378.9 | -188.4 | 318.0 | 0.579 | 0.8 |
| screen | weekday_d1_MW_Th | DOTUSD | D1 | build_weekday | {} | nan | -29.4 | -734.6 | -794.3 | -24.9 | 99.0 | 0.081 | 0.04 |
| screen | weekday_d1_MW_Th | ETHUSD | D1 | build_weekday | {} | 0.015 | 86.8 | 2170.3 | -466.2 | -149.6 | 318.0 | 0.56 | 0.64 |
| screen | weekday_d1_MW_Th | LTCUSD | D1 | build_weekday | {} | nan | -41.3 | -1032.5 | -1055.1 | -25.0 | 318.0 | 0.33 | 0.12 |
| screen | weekday_d1_MW_Th | SOLUSD | D1 | build_weekday | {} | 0.0075 | -3.5 | -76.3 | -437.2 | -69.4 | 280.0 | 0.496 | 0.455 |
| screen | weekday_d1_MW_Th | XRPUSD | D1 | build_weekday | {} | 0.01 | -0.7 | -15.8 | -588.1 | -100.0 | 280.0 | 0.493 | 0.409 |
| rerun | weekend_atr_rr2 | ADAUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.0025 | -18.7 | -466.4 | -578.8 | -46.2 | 69.0 | 0.377 | 0.32 |
| rerun | weekend_atr_rr2 | BNBUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.0025 | -7.0 | -175.9 | -444.8 | -29.4 | 77.0 | 0.455 | 0.4 |
| screen | weekend_atr_rr2 | BTCUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.005 | 15.8 | 394.0 | -445.6 | -78.5 | 98.0 | 0.378 | 0.52 |
| screen | weekend_atr_rr2 | DOTUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.0025 | -10.7 | -267.1 | -300.7 | -33.2 | 43.0 | 0.349 | 0.24 |
| screen | weekend_atr_rr2 | ETHUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | nan | -21.9 | -547.4 | -720.0 | -32.5 | 84.0 | 0.262 | 0.28 |
| rerun | weekend_atr_rr2 | LTCUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | nan | -30.5 | -762.2 | -815.1 | -29.8 | 62.0 | 0.274 | 0.12 |
| rerun | weekend_atr_rr2 | SOLUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.0025 | -15.1 | -332.3 | -465.7 | -29.2 | 75.0 | 0.373 | 0.227 |
| screen | weekend_atr_rr2 | XRPUSD | H1 | build_weekend_bo | {"stop": "atr", "rr": 2.0, "hold": 48} | 0.0025 | -11.8 | -258.9 | -375.6 | -25.0 | 71.0 | 0.366 | 0.409 |
| screen | weekend_mid_h24 | ADAUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | 0.0025 | -13.8 | -345.3 | -444.1 | -37.2 | 53.0 | 0.321 | 0.24 |
| screen | weekend_mid_h24 | BNBUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | nan | -25.6 | -639.3 | -715.0 | -51.8 | 77.0 | 0.325 | 0.16 |
| screen | weekend_mid_h24 | BTCUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | 0.005 | 3.5 | 88.2 | -555.8 | -105.6 | 98.0 | 0.378 | 0.52 |
| screen | weekend_mid_h24 | DOTUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | nan | -22.7 | -567.2 | -650.2 | -62.0 | 64.0 | 0.219 | 0.2 |
| screen | weekend_mid_h24 | ETHUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | nan | -24.9 | -621.5 | -621.5 | -44.6 | 84.0 | 0.298 | 0.28 |
| screen | weekend_mid_h24 | LTCUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | nan | -27.0 | -675.6 | -748.9 | -28.7 | 72.0 | 0.208 | 0.2 |
| screen | weekend_mid_h24 | SOLUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | 0.0025 | -11.2 | -246.8 | -356.4 | -30.1 | 75.0 | 0.36 | 0.364 |
| screen | weekend_mid_h24 | XRPUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 24} | 0.0025 | -6.7 | -146.8 | -351.9 | -62.3 | 70.0 | 0.343 | 0.364 |
| screen | weekend_mid_h48_montue | ADAUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | 0.0025 | -6.0 | -151.1 | -370.7 | -37.2 | 58.0 | 0.362 | 0.2 |
| rerun | weekend_mid_h48_montue | BNBUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | nan | -27.7 | -692.9 | -748.8 | -51.8 | 94.0 | 0.309 | 0.36 |
| rerun | weekend_mid_h48_montue | BTCUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | 0.005 | 7.3 | 181.9 | -517.4 | -183.7 | 101.0 | 0.317 | 0.48 |
| rerun | weekend_mid_h48_montue | DOTUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | nan | -29.1 | -726.7 | -818.2 | -62.0 | 78.0 | 0.218 | 0.2 |
| screen | weekend_mid_h48_montue | ETHUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | 0.0025 | -16.0 | -399.6 | -481.5 | -44.6 | 94.0 | 0.309 | 0.44 |
| rerun | weekend_mid_h48_montue | LTCUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | nan | -34.3 | -856.7 | -931.5 | -52.8 | 85.0 | 0.259 | 0.24 |
| screen | weekend_mid_h48_montue | SOLUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | 0.0025 | -12.5 | -274.1 | -401.5 | -66.3 | 83.0 | 0.325 | 0.364 |
| screen | weekend_mid_h48_montue | XRPUSD | H1 | build_weekend_bo | {"stop": "mid", "hold": 48, "days": [0, 1]} | 0.0025 | -13.3 | -292.3 | -536.8 | -99.9 | 82.0 | 0.317 | 0.273 |
| refine | wemr_fade_sun20 | ADAUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.01 | -17.8 | -445.8 | -564.8 | -100.0 | 12.0 | 0.25 | 0.08 |
| refine | wemr_fade_sun20 | BNBUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.005 | -9.1 | -228.6 | -410.1 | -74.7 | 21.0 | 0.286 | 0.16 |
| refine | wemr_fade_sun20 | BTCUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.005 | -11.5 | -288.2 | -369.8 | -76.9 | 7.0 | 0.0 | 0.0 |
| refine | wemr_fade_sun20 | DOTUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.005 | -18.9 | -472.2 | -519.5 | -70.3 | 14.0 | 0.214 | 0.08 |
| refine | wemr_fade_sun20 | ETHUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.0075 | -13.9 | -346.6 | -494.9 | -139.9 | 9.0 | 0.111 | 0.04 |
| refine | wemr_fade_sun20 | LTCUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.005 | -19.7 | -493.2 | -522.2 | -64.1 | 14.0 | 0.071 | 0.0 |
| refine | wemr_fade_sun20 | SOLUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.0075 | -12.2 | -268.1 | -539.7 | -116.9 | 9.0 | 0.333 | 0.136 |
| refine | wemr_fade_sun20 | XRPUSD | H1 | build_weekend_mr | {"entry_hour": 20} | 0.005 | -7.6 | -167.5 | -406.7 | -110.1 | 9.0 | 0.333 | 0.136 |
| refine | wemr_fade_t05 | ADAUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.005 | -13.6 | -339.1 | -387.1 | -50.0 | 35.0 | 0.343 | 0.28 |
| refine | wemr_fade_t05 | BNBUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0125 | 3.5 | 86.4 | -598.7 | -125.0 | 44.0 | 0.432 | 0.32 |
| refine | wemr_fade_t05 | BTCUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.005 | -11.0 | -275.8 | -516.6 | -49.9 | 23.0 | 0.174 | 0.16 |
| refine | wemr_fade_t05 | DOTUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0025 | -10.7 | -266.6 | -292.8 | -25.0 | 41.0 | 0.268 | 0.28 |
| refine | wemr_fade_t05 | ETHUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0125 | 14.3 | 356.3 | -553.9 | -125.0 | 29.0 | 0.345 | 0.32 |
| refine | wemr_fade_t05 | LTCUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0025 | -18.7 | -466.5 | -502.3 | -25.0 | 38.0 | 0.184 | 0.16 |
| refine | wemr_fade_t05 | SOLUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0075 | -2.5 | -55.4 | -571.4 | -74.6 | 31.0 | 0.387 | 0.364 |
| refine | wemr_fade_t05 | XRPUSD | H1 | build_weekend_mr | {"thresh": 0.5} | 0.0025 | -9.2 | -203.2 | -354.0 | -25.0 | 28.0 | 0.25 | 0.182 |
| refine | wemr_fade_t10 | ADAUSD | H1 | build_weekend_mr | {} | 0.01 | -21.4 | -535.8 | -599.1 | -100.0 | 13.0 | 0.231 | 0.08 |
| refine | wemr_fade_t10 | BNBUSD | H1 | build_weekend_mr | {} | 0.0125 | -5.9 | -147.2 | -580.5 | -125.0 | 21.0 | 0.333 | 0.24 |
| refine | wemr_fade_t10 | BTCUSD | H1 | build_weekend_mr | {} | 0.02 | 36.8 | 920.7 | -579.0 | -198.8 | 9.0 | 0.333 | 0.12 |
| refine | wemr_fade_t10 | DOTUSD | H1 | build_weekend_mr | {} | 0.015 | 14.3 | 358.7 | -490.0 | -150.0 | 14.0 | 0.5 | 0.28 |
| refine | wemr_fade_t10 | ETHUSD | H1 | build_weekend_mr | {} | 0.015 | 37.8 | 944.7 | -488.6 | -149.9 | 12.0 | 0.417 | 0.2 |
| refine | wemr_fade_t10 | LTCUSD | H1 | build_weekend_mr | {} | 0.005 | -16.5 | -411.6 | -411.6 | -50.0 | 14.0 | 0.143 | 0.08 |
| refine | wemr_fade_t10 | SOLUSD | H1 | build_weekend_mr | {} | 0.015 | 36.8 | 809.7 | -546.3 | -149.5 | 9.0 | 0.556 | 0.227 |
| refine | wemr_fade_t10 | XRPUSD | H1 | build_weekend_mr | {} | 0.01 | 3.1 | 68.3 | -582.7 | -100.0 | 9.0 | 0.333 | 0.136 |
| refine | wemr_fade_t15_h48 | ADAUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.0075 | -18.0 | -450.0 | -476.4 | -75.0 | 6.0 | 0.0 | 0.0 |
| refine | wemr_fade_t15_h48 | BNBUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.0125 | -3.8 | -95.9 | -567.9 | -299.0 | 8.0 | 0.25 | 0.08 |
| refine | wemr_fade_t15_h48 | BTCUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.0125 | 9.2 | 230.0 | -559.1 | -260.2 | 3.0 | 0.333 | 0.04 |
| refine | wemr_fade_t15_h48 | DOTUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.015 | 5.9 | 146.9 | -464.4 | -150.0 | 6.0 | 0.333 | 0.08 |
| refine | wemr_fade_t15_h48 | ETHUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.02 | 37.6 | 940.1 | -587.2 | -225.8 | 6.0 | 0.333 | 0.08 |
| refine | wemr_fade_t15_h48 | LTCUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.0075 | -24.0 | -599.8 | -599.8 | -75.0 | 8.0 | 0.0 | 0.0 |
| refine | wemr_fade_t15_h48 | SOLUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.015 | 4.6 | 100.6 | -526.3 | -149.5 | 4.0 | 0.25 | 0.045 |
| refine | wemr_fade_t15_h48 | XRPUSD | H1 | build_weekend_mr | {"thresh": 1.5, "hold": 48} | 0.02 | 45.2 | 993.4 | -375.1 | -286.4 | 4.0 | 0.5 | 0.091 |
| refine | wemr_follow_t05_h48 | ADAUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -21.5 | -537.9 | -559.1 | -41.8 | 30.0 | 0.1 | 0.08 |
| refine | wemr_follow_t05_h48 | BNBUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | nan | -26.2 | -655.9 | -691.2 | -88.7 | 44.0 | 0.136 | 0.12 |
| refine | wemr_follow_t05_h48 | BTCUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.005 | 2.7 | 66.7 | -457.9 | -168.8 | 23.0 | 0.217 | 0.12 |
| refine | wemr_follow_t05_h48 | DOTUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -15.6 | -389.2 | -446.8 | -44.8 | 41.0 | 0.195 | 0.12 |
| refine | wemr_follow_t05_h48 | ETHUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -15.7 | -393.7 | -440.4 | -66.6 | 29.0 | 0.103 | 0.08 |
| refine | wemr_follow_t05_h48 | LTCUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -15.3 | -382.6 | -440.2 | -52.4 | 38.0 | 0.289 | 0.16 |
| refine | wemr_follow_t05_h48 | SOLUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -17.0 | -373.5 | -551.9 | -78.2 | 31.0 | 0.161 | 0.091 |
| refine | wemr_follow_t05_h48 | XRPUSD | H1 | build_weekend_mr | {"follow": true, "thresh": 0.5, "hold": 48} | 0.0025 | -21.7 | -477.6 | -521.2 | -140.2 | 28.0 | 0.036 | 0.091 |
| refine | wemr_follow_t10 | ADAUSD | H1 | build_weekend_mr | {"follow": true} | 0.0025 | -4.6 | -114.7 | -256.8 | -25.0 | 9.0 | 0.222 | 0.08 |
| refine | wemr_follow_t10 | BNBUSD | H1 | build_weekend_mr | {"follow": true} | 0.0025 | -15.0 | -374.9 | -487.0 | -25.0 | 21.0 | 0.19 | 0.08 |
| refine | wemr_follow_t10 | BTCUSD | H1 | build_weekend_mr | {"follow": true} | 0.0075 | 6.3 | 156.9 | -548.9 | -74.1 | 9.0 | 0.222 | 0.08 |
| refine | wemr_follow_t10 | DOTUSD | H1 | build_weekend_mr | {"follow": true} | 0.005 | -15.1 | -377.2 | -520.7 | -50.0 | 13.0 | 0.231 | 0.12 |
| refine | wemr_follow_t10 | ETHUSD | H1 | build_weekend_mr | {"follow": true} | 0.0025 | -9.7 | -241.8 | -345.7 | -24.9 | 12.0 | 0.083 | 0.04 |
| refine | wemr_follow_t10 | LTCUSD | H1 | build_weekend_mr | {"follow": true} | 0.005 | -14.9 | -372.3 | -566.3 | -50.0 | 14.0 | 0.143 | 0.04 |
| refine | wemr_follow_t10 | SOLUSD | H1 | build_weekend_mr | {"follow": true} | 0.005 | -17.2 | -379.5 | -454.0 | -49.8 | 9.0 | 0.0 | 0.0 |
| refine | wemr_follow_t10 | XRPUSD | H1 | build_weekend_mr | {"follow": true} | 0.005 | -19.2 | -423.5 | -534.9 | -50.0 | 9.0 | 0.0 | 0.0 |
| screen | wopen_h1_05 | ADAUSD | H1 | build_weekly_open | {} | nan | -24.7 | -616.4 | -705.7 | -35.1 | 80.0 | 0.2 | 0.16 |
| screen | wopen_h1_05 | BNBUSD | H1 | build_weekly_open | {} | nan | -34.8 | -869.1 | -893.8 | -25.0 | 106.0 | 0.264 | 0.16 |
| screen | wopen_h1_05 | BTCUSD | H1 | build_weekly_open | {} | 0.0025 | 4.1 | 103.4 | -474.7 | -24.8 | 104.0 | 0.337 | 0.44 |
| screen | wopen_h1_05 | DOTUSD | H1 | build_weekly_open | {} | nan | -41.9 | -1048.5 | -1163.6 | -25.0 | 99.0 | 0.141 | 0.16 |
| screen | wopen_h1_05 | ETHUSD | H1 | build_weekly_open | {} | nan | -28.0 | -701.0 | -862.4 | -28.6 | 106.0 | 0.245 | 0.12 |
| screen | wopen_h1_05 | LTCUSD | H1 | build_weekly_open | {} | nan | -53.5 | -1337.5 | -1387.3 | -25.0 | 106.0 | 0.132 | 0.12 |
| screen | wopen_h1_05 | SOLUSD | H1 | build_weekly_open | {} | 0.0025 | -15.2 | -335.1 | -536.0 | -24.8 | 96.0 | 0.375 | 0.318 |
| screen | wopen_h1_05 | XRPUSD | H1 | build_weekly_open | {} | 0.0025 | -18.7 | -411.6 | -593.2 | -25.8 | 95.0 | 0.284 | 0.182 |
| screen | wopen_h1_10 | ADAUSD | H1 | build_weekly_open | {"min_dist": 1.0} | nan | -25.7 | -643.0 | -712.4 | -35.1 | 80.0 | 0.2 | 0.08 |
| screen | wopen_h1_10 | BNBUSD | H1 | build_weekly_open | {"min_dist": 1.0} | nan | -30.2 | -754.3 | -767.0 | -25.0 | 106.0 | 0.292 | 0.16 |
| screen | wopen_h1_10 | BTCUSD | H1 | build_weekly_open | {"min_dist": 1.0} | 0.0025 | -2.6 | -63.9 | -510.4 | -24.8 | 104.0 | 0.308 | 0.44 |
| screen | wopen_h1_10 | DOTUSD | H1 | build_weekly_open | {"min_dist": 1.0} | nan | -42.9 | -1073.0 | -1147.6 | -25.0 | 99.0 | 0.152 | 0.12 |
| screen | wopen_h1_10 | ETHUSD | H1 | build_weekly_open | {"min_dist": 1.0} | nan | -33.3 | -832.9 | -947.9 | -27.8 | 106.0 | 0.236 | 0.16 |
| screen | wopen_h1_10 | LTCUSD | H1 | build_weekly_open | {"min_dist": 1.0} | nan | -52.7 | -1317.4 | -1367.1 | -25.0 | 106.0 | 0.132 | 0.12 |
| screen | wopen_h1_10 | SOLUSD | H1 | build_weekly_open | {"min_dist": 1.0} | 0.0025 | -15.8 | -347.5 | -562.1 | -24.7 | 96.0 | 0.375 | 0.318 |
| screen | wopen_h1_10 | XRPUSD | H1 | build_weekly_open | {"min_dist": 1.0} | 0.0025 | -17.3 | -379.5 | -525.9 | -25.8 | 95.0 | 0.284 | 0.318 |
| screen | wopen_h4_05 | ADAUSD | H4 | build_weekly_open | {} | 0.0025 | -11.8 | -294.9 | -420.1 | -25.0 | 54.0 | 0.259 | 0.16 |
| screen | wopen_h4_05 | BNBUSD | H4 | build_weekly_open | {} | 0.0025 | -12.0 | -299.1 | -503.5 | -33.7 | 106.0 | 0.34 | 0.4 |
| screen | wopen_h4_05 | BTCUSD | H4 | build_weekly_open | {} | 0.005 | 22.1 | 553.6 | -538.0 | -67.4 | 106.0 | 0.321 | 0.44 |
| screen | wopen_h4_05 | DOTUSD | H4 | build_weekly_open | {} | nan | -35.3 | -881.8 | -916.0 | -34.4 | 82.0 | 0.183 | 0.08 |
| screen | wopen_h4_05 | ETHUSD | H4 | build_weekly_open | {} | 0.0025 | 7.1 | 176.3 | -300.0 | -41.2 | 106.0 | 0.311 | 0.44 |
| screen | wopen_h4_05 | LTCUSD | H4 | build_weekly_open | {} | nan | -45.2 | -1130.8 | -1179.6 | -30.8 | 106.0 | 0.198 | 0.16 |
| screen | wopen_h4_05 | SOLUSD | H4 | build_weekly_open | {} | 0.0025 | -16.5 | -364.0 | -572.4 | -38.6 | 95.0 | 0.221 | 0.273 |
| screen | wopen_h4_05 | XRPUSD | H4 | build_weekly_open | {} | nan | -11.4 | -250.7 | -600.5 | -38.5 | 93.0 | 0.301 | 0.409 |
| screen | wopen_h4_notrail | ADAUSD | H4 | build_weekly_open | {"trail": false} | 0.0025 | -13.8 | -346.0 | -559.1 | -47.2 | 54.0 | 0.278 | 0.24 |
| screen | wopen_h4_notrail | BNBUSD | H4 | build_weekly_open | {"trail": false} | 0.0025 | -11.6 | -291.0 | -499.1 | -61.9 | 106.0 | 0.321 | 0.44 |
| screen | wopen_h4_notrail | BTCUSD | H4 | build_weekly_open | {"trail": false} | 0.0025 | 13.1 | 328.6 | -314.4 | -80.4 | 73.0 | 0.315 | 0.44 |
| screen | wopen_h4_notrail | DOTUSD | H4 | build_weekly_open | {"trail": false} | nan | -48.5 | -1212.4 | -1308.0 | -65.0 | 82.0 | 0.171 | 0.04 |
| screen | wopen_h4_notrail | ETHUSD | H4 | build_weekly_open | {"trail": false} | 0.0025 | 5.8 | 145.8 | -538.8 | -65.6 | 106.0 | 0.33 | 0.36 |
| screen | wopen_h4_notrail | LTCUSD | H4 | build_weekly_open | {"trail": false} | nan | -55.3 | -1381.8 | -1432.2 | -42.5 | 106.0 | 0.226 | 0.16 |
| screen | wopen_h4_notrail | SOLUSD | H4 | build_weekly_open | {"trail": false} | 0.0025 | -8.5 | -186.3 | -526.5 | -47.6 | 95.0 | 0.316 | 0.364 |
| screen | wopen_h4_notrail | XRPUSD | H4 | build_weekly_open | {"trail": false} | nan | -3.8 | -83.9 | -716.2 | -79.2 | 93.0 | 0.301 | 0.364 |

# published_research family - NOTES

All results are in-sample only: 2015-01 .. 2023-12. Indices start in 2016, USTEC only covers 2022-23, and M30 data only starts in 2018.
Every number below comes from `research.prop.harness.score`. That means fixed $ risk on $10k, with spread, commission and slippage included. best_risk is the highest risk in 0.25%..2% that keeps the worst day above -3% and max DD above -6%. avg_month is measured at best_risk, in dollars.
No 2024+ data was read at any point.

Files:
- `strategies.py`: the builders.
- `batches.py`: every experiment.
- `run.py`: serial, resumable runner that writes to `results.jsonl`.
- `portfolio.py`: basket estimate, for information only.
- `check_causal.py`: truncation test. Signals built on df[:k+1] must equal the full-df signal at bar k. It found 0 mismatches for all three candidate builders.
- `explore_hours.py`: hour-of-day mean returns.

Machine note: the machine was short on memory during this run because other agents were using it. Runs that crashed with out-of-memory were re-run, and their error rows are left out of the table.
DE40 and USTEC data arrived late. Index D1/M30 files were missing when the index batch ran, so the index RSI(2), TSMOM and M30 intraday-momentum runs were skipped and never scored.

## Ideas tested and sources

| # | idea | source | verdict in-sample |
|---|---|---|---|
| 1 | Gold rises in Asian hours and falls in the West (hour-of-day drift) | Donati & Jung, CBS thesis "Gold Price Dynamics Around the Clock" (https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/) | The pattern exists in our data (hours 1, 2 and 4 positive, t up to 5.8). But it is ~1-3 bp/hour against ~3 bp round-trip cost, so every variant loses. DEAD. |
| 2 | London PM fix / western-hours gold weakness | Caminschi & Heaney 2014, "Fixing a leaky fixing", J. Futures Markets (https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html) | Shorts over 15-17, 15-20, 16-20 and 10-17 all lose. DEAD. The paper's effect plays out over minutes, and the fix was reformed in 2015. |
| 3 | Currencies weaken during their home trading hours | Breedon & Ranaldo, "Intraday patterns in FX returns and order flow" (SNB WP 2011-04, https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04) | The sign holds for EURUSD: negative in the European morning, positive in US hours (hours 13 and 14 were positive in only 0/9 and 1/9 years). But the moves are too small for the costs, and all 10 runs lose. DEAD. |
| 4 | USD rises into FX fixes and falls after them (W-shape) | Krohn, Mueller & Whelan, J. Finance 2024, "Foreign exchange fixings and returns around the clock" (https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf) | Pre- and post-London-fix windows on 6 USD pairs all lose after costs. DEAD at H1 bar size. |
| 5 | Time-series momentum (sign of the 12/6/3-month return) | Moskowitz, Ooi & Pedersen 2012 JFE, "Time series momentum" (https://papers.ssrn.com/abstract=2089463) | 18 runs on D1 with monthly rebalance give -3..+9 $/mo. On a single instrument the Sharpe ratio is too low for the 6% DD cap. Not a candidate. |
| 6 | Donchian / turtle trend | Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following" (AQR); Faith, "Way of the Turtle" | -4..+7 $/mo. The best was XAUUSD H4 55/20 at +$7 with 0.25% risk. Not a candidate. |
| 7 | Short-term reversal, RSI(2) | Connors & Alvarez 2009 (widely replicated on equity indices) | Gold and FX on D1 all make <= +$1/mo. Not run on index D1 because the file was missing. |
| 8 | Pre-FOMC drift / USD weakness on FOMC days | Lucca & Moench 2015 J. Finance, "The pre-FOMC announcement drift"; Mueller, Tahbaz-Salehi & Vedolin 2017 J. Finance, "Exchange rates and monetary policy uncertainty" (https://researchonline.lse.ac.uk/id/eprint/77256) | **Shorting USD from 14:00 ET the day before to 14:00 ET on FOMC day is positive on ALL 9 USD instruments tested** (EURUSD GBPUSD AUDUSD NZDUSD USDCHF USDCAD USDJPY XAUUSD XAGUSD). Going long US500/US30 over the same window is also positive. It holds up with stops of 1.0-2.0 ATR, entries from 21:00 to 23:00 server time, and when held through the announcement. CANDIDATE, but it only trades 8 times a year. |
| 9 | Turn of the month (equities) | Lakonishok & Smidt 1988; McConnell & Xu 2008; Quantpedia (https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes) | Positive on US500, US30, DE40 and USTEC. Also positive on gold, though the gold literature is thin (only practitioner notes such as In Gold We Trust and Seasonax: https://ingoldwetrust.report/nuggets/calendar-anomalies-and-the-gold-market/). Nothing on FX: 5 pairs, both sides, ~0. |
| 10 | Pre-holiday effect | Ariel 1990 J. Finance; Kim & Park 1994 | US500 +$10/mo and US30 +$7 at 2% risk. Weak on its own, but it adds to the combo. |
| 11 | Overnight drift (close to open) | Kelly & Clark 2011; Lou, Polk & Skouras 2019 JFE, "A tug of war" | US500 loses and US30 makes +$4..15, so the result does not agree across indices. Costs eat most of it over 1,500-2,000 trades. Not a candidate. |
| 12 | Intraday momentum (the first half-hour predicts the last) | Gao, Han, Li & Zhou 2018 JFE, "Market intraday momentum" | 15 runs on gold/silver (COMEX session), FX, and US500/US30 H1 all lose: a 1-bar hold is dominated by costs. USTEC made +$25 but on only 2 years of data, so it is ignored. DEAD. |
| 13 | FOMC cycle (even weeks) | Cieslak, Morse & Vissing-Jorgensen 2019 J. Finance, "Stock returns over the FOMC cycle" | Even weeks make US30 +$20, US500 +$13 and gold +$7, while odd weeks make ~0. That matches the paper's direction, but it beats the placebo only a little. Not chosen. |
| 14 | Gold "autumn effect" (September, November) | Baur 2013, "The autumn effect of gold" (https://opus.lib.uts.edu.au/handle/10453/23416) | Loses in 2015-23 (-2..-4 $/mo). A December-January "winter" variant (arXiv 2003.11027) made +$14 on 17 trades, which is too few to trust. |
| 15 | Opening-gap fade (indices) | Quantpedia, "gap fading"; Plastun et al. 2019 | US500 loses and US30 makes +$3 at 0.25% risk. DEAD. |
| - | Placebo: go long every 8th day regardless of the calendar, same hold and stop | (control) | US500 +2..8, US30 +6..19, DE40 -2..5 and XAUUSD +4..9 $/mo. The calendar combos beat this on every symbol, so their edge is more than a long-only drift. |

## Combos (the useful results)

* `build_equity_calendar` combines three long-only edges in one position: turn of the month (enter at the US close on the LAST business day, hold 4 days), pre-holiday, and pre-FOMC. Entering the turn of the month on day 0 instead of day -1 was clearly better on US500, US30 and DE40. It was worse on USTEC, which only has a 2-year sample.
  All neighbouring settings are positive (tom_hold 2/3/4/6, stop 1.0/1.5/2.0 daily ATR): US500 19-29, US30 26-47 and DE40 23-37 $/mo.
* `build_gold_calendar` combines pre-FOMC long and turn-of-the-month long on gold. All 16 neighbouring settings are positive at 13-29 $/mo (tom_days_before 0/1, tom_hold 2/3/4/6, FOMC stop 1.0/1.5). The silver version is positive but weaker (5-12).
* `build_pre_fomc` (short USD) on FX makes 10-26 $/mo per pair at 2% risk.

## Basket check (portfolio.py, summed curves, for information only)

* A 4-pair pre-FOMC basket (EUR, GBP, AUD, CHF) at 0.75% per leg makes $35/mo, with DD -$375 and a worst day of -$247.
  That is only ~1.5x a single pair at 2%. The legs are highly correlated because they all trade on the same 8 days a year.
* A calendar basket of US30, DE40, US500 and XAU at 0.5% per leg makes $32/mo with DD -$451. At 0.75% per leg it is no longer safe.
  That is NOT better than US30 alone at 1.5%, because all four legs trade on the same days.

## What failed and why

1. Every intraday time-of-day effect from the literature failed: gold Asia drift, Breedon-Ranaldo, the KMW fix W-shape, Gao intraday momentum, the gap fade, and overnight drift.
   Their sign is roughly right, but each window moves only 1-3 bp. One round trip costs ~2-4 bp: the spread floor, $14/lot commission and slippage.
   Over ~2,000 trades the cost drag adds up to 40-60 R. These effects would need sub-bp execution costs to be tradeable.
2. Trend and momentum on single instruments (TSMOM, Donchian) have a Sharpe ratio too low to scale under a 6% DD cap. The papers get their edge from diversifying across 50+ instruments.
3. Hour-labelling pitfall, found and fixed: `exit_hour` exits at the FIRST later bar with that hour. So an entry at 18 with exit 20 is a 2-hour trade, not 26 hours.
   The prefomc_18to20, 16to20, 20to21 and 20to23 rows are these short versions, not the FOMC window.
4. Rollover hours (23-01 server time) show huge t-stats in the raw hour means (EURUSD hour 1 has t=9.4). These are almost certainly quote or spread artefacts, so they were deliberately not traded.

## Honest bottom line

The published effects that survive costs are the infrequent CALENDAR ones: pre-FOMC, turn of the month, and pre-holiday.
They hold up across instruments, neighbouring settings and the placebo, but they are SMALL. At the highest safe risk they make $25-35/month per $10k, which is 0.25-0.35%/month.
The challenge "100% pass rate" is misleading, because the median time to pass both phases is 2-4 YEARS.
They make good low-correlation add-ons to a faster core strategy, since they only trade ~2-4 days a month. They are not a standalone way to pass.

## Every scored run
| # | name | builder | symbol | tf | params | best_risk | avg_month | max_dd | worst_day | trades | green | chal pass (median d) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | asia_long_1to4_sl0.5 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 4, "sl_datr": 0.5}` | none | -12 | -1453 | -25 | 2268 | 32% | 0% () |
| 2 | asia_long_1to4_sl1.0 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 4, "sl_datr": 1.0}` | none | -6 | -638 | -25 | 1743 | 33% | 0% () |
| 3 | asia_long_1to6_sl0.5 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 6, "sl_datr": 0.5}` | none | -13 | -1558 | -25 | 2268 | 31% | 0% () |
| 4 | asia_long_1to6_sl1.0 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 6, "sl_datr": 1.0}` | none | -5 | -637 | -25 | 1743 | 32% | 0% () |
| 5 | asia_long_1to8_sl0.5 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 8, "sl_datr": 0.5}` | none | -12 | -1677 | -25 | 2268 | 40% | 0% () |
| 6 | asia_long_1to8_sl1.0 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 8, "sl_datr": 1.0}` | none | -5 | -659 | -25 | 1743 | 37% | 0% () |
| 7 | asia_long_1to10_sl0.5 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 10, "sl_datr": 0.5}` | none | -17 | -1946 | -25 | 2268 | 29% | 0% () |
| 8 | asia_long_1to10_sl1.0 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 10, "sl_datr": 1.0}` | none | -6 | -707 | -25 | 1743 | 31% | 0% () |
| 9 | asia_long_0to8_sl1 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 0, "exit_hour": 8, "sl_datr": 1.0}` | 2.00% | 1 | -287 | -112 | 50 | 2% | 0% () |
| 10 | asia_long_2to8_sl1 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 2, "exit_hour": 8, "sl_datr": 1.0}` | none | -7 | -783 | -25 | 1744 | 32% | 0% () |
| 11 | west_short_15to17 | session_drift | XAUUSD | H1 | `{"side": "short", "entry_hour": 15, "exit_hour": 17, "sl_datr": 1.0}` | none | -9 | -1068 | -24 | 1752 | 26% | 0% () |
| 12 | west_short_15to20 | session_drift | XAUUSD | H1 | `{"side": "short", "entry_hour": 15, "exit_hour": 20, "sl_datr": 1.0}` | none | -8 | -1027 | -25 | 1720 | 37% | 0% () |
| 13 | west_short_16to20 | session_drift | XAUUSD | H1 | `{"side": "short", "entry_hour": 16, "exit_hour": 20, "sl_datr": 1.0}` | none | -10 | -1262 | -25 | 1721 | 32% | 0% () |
| 14 | west_short_10to17 | session_drift | XAUUSD | H1 | `{"side": "short", "entry_hour": 10, "exit_hour": 17, "sl_datr": 1.0}` | none | -10 | -1407 | -25 | 1752 | 39% | 0% () |
| 15 | gold_daycycle | two_leg_session | XAUUSD | H1 | `{}` | none | -14 | -1709 | -36 | 3495 | 31% | 0% () |
| 16 | asia_long_1to8_sl1 | session_drift | XAGUSD | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 8, "sl_datr": 1.0}` | none | -25 | -2706 | -24 | 1241 | 5% | 0% () |
| 17 | br_eu_morning_short_9to14 | session_drift | EURUSD | H1 | `{"side": "short", "entry_hour": 9, "exit_hour": 14, "sl_datr": 1.0}` | none | -7 | -853 | -25 | 2321 | 43% | 0% () |
| 18 | br_us_hours_long_15to21 | session_drift | EURUSD | H1 | `{"side": "long", "entry_hour": 15, "exit_hour": 21, "sl_datr": 1.0}` | none | -11 | -1564 | -25 | 2314 | 36% | 0% () |
| 19 | br_two_leg | two_leg_session | EURUSD | H1 | `{"long_entry": 15, "long_exit": 21, "short_entry": 9, "short_exit": 14, "sl_datr": 1.0}` | none | -17 | -2307 | -39 | 4642 | 29% | 0% () |
| 20 | br_eu_morning_short_9to14 | session_drift | GBPUSD | H1 | `{"side": "short", "entry_hour": 9, "exit_hour": 14, "sl_datr": 1.0}` | none | -7 | -919 | -25 | 2286 | 38% | 0% () |
| 21 | br_us_hours_long_15to21 | session_drift | GBPUSD | H1 | `{"side": "long", "entry_hour": 15, "exit_hour": 21, "sl_datr": 1.0}` | none | -9 | -1124 | -25 | 2281 | 41% | 0% () |
| 22 | br_two_leg | two_leg_session | GBPUSD | H1 | `{"long_entry": 15, "long_exit": 21, "short_entry": 9, "short_exit": 14, "sl_datr": 1.0}` | none | -16 | -1841 | -47 | 4572 | 36% | 0% () |
| 23 | br_tokyo_long_1to9 | session_drift | USDJPY | H1 | `{"side": "long", "entry_hour": 1, "exit_hour": 9, "sl_datr": 1.0}` | none | -15 | -1679 | -25 | 2313 | 28% | 0% () |
| 24 | br_tokyo_long_2to9 | session_drift | USDJPY | H1 | `{"side": "long", "entry_hour": 2, "exit_hour": 9, "sl_datr": 1.0}` | none | -15 | -1736 | -24 | 2313 | 25% | 0% () |
| 25 | br_asia_short_1to9 | session_drift | AUDUSD | H1 | `{"side": "short", "entry_hour": 1, "exit_hour": 9, "sl_datr": 1.0}` | none | -20 | -2192 | -25 | 2313 | 20% | 0% () |
| 26 | br_asia_short_1to9 | session_drift | NZDUSD | H1 | `{"side": "short", "entry_hour": 1, "exit_hour": 9, "sl_datr": 1.0}` | none | -21 | -2349 | -25 | 2314 | 24% | 0% () |
| 27 | tsmom_lb63_M | tsmom | XAUUSD | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.75% | -3 | -533 | -163 | 33 | 41% | 0% () |
| 28 | tsmom_lb126_M | tsmom | XAUUSD | D1 | `{"lookback": 126, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | 3 | -421 | -126 | 15 | 29% | 0% () |
| 29 | tsmom_lb252_M | tsmom | XAUUSD | D1 | `{"lookback": 252, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | 2 | -440 | -126 | 23 | 27% | 0% () |
| 30 | tsmom_lb63_M | tsmom | XAGUSD | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.75% | 2 | -461 | -236 | 25 | 31% | 0% () |
| 31 | tsmom_lb126_M | tsmom | XAGUSD | D1 | `{"lookback": 126, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | -3 | -524 | -68 | 19 | 17% | 0% () |
| 32 | tsmom_lb252_M | tsmom | XAGUSD | D1 | `{"lookback": 252, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | -3 | -346 | -68 | 13 | 15% | 0% () |
| 33 | tsmom_lb63_M | tsmom | EURUSD | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | -0 | -461 | -49 | 42 | 46% | 0% () |
| 34 | tsmom_lb126_M | tsmom | EURUSD | D1 | `{"lookback": 126, "rebalance": "M", "sl_atr": 3.0}` | 0.75% | 2 | -558 | -89 | 19 | 52% | 0% () |
| 35 | tsmom_lb252_M | tsmom | EURUSD | D1 | `{"lookback": 252, "rebalance": "M", "sl_atr": 3.0}` | 0.75% | 3 | -595 | -87 | 13 | 47% | 0% () |
| 36 | tsmom_lb63_M | tsmom | GBPUSD | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | -1 | -329 | -54 | 30 | 44% | 0% () |
| 37 | tsmom_lb126_M | tsmom | GBPUSD | D1 | `{"lookback": 126, "rebalance": "M", "sl_atr": 3.0}` | 0.75% | 9 | -572 | -113 | 18 | 53% | 100% (2567) |
| 38 | tsmom_lb252_M | tsmom | GBPUSD | D1 | `{"lookback": 252, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | 2 | -406 | -75 | 16 | 43% | 0% () |
| 39 | tsmom_lb63_M | tsmom | USDJPY | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | 5 | -417 | -99 | 34 | 49% | 0% () |
| 40 | tsmom_lb126_M | tsmom | USDJPY | D1 | `{"lookback": 126, "rebalance": "M", "sl_atr": 3.0}` | 0.25% | 1 | -341 | -39 | 23 | 43% | 0% () |
| 41 | tsmom_lb252_M | tsmom | USDJPY | D1 | `{"lookback": 252, "rebalance": "M", "sl_atr": 3.0}` | 0.50% | 3 | -529 | -118 | 21 | 43% | 0% () |
| 42 | tsmom_lb63_M | tsmom | AUDUSD | D1 | `{"lookback": 63, "rebalance": "M", "sl_atr": 3.0}` | 0.25% | -3 | -399 | -26 | 35 | 27% | 0% () |
| 43 | donchian_55_20 | donchian | XAUUSD | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.50% | 2 | -522 | -163 | 31 | 31% | 0% () |
| 44 | donchian_20_10 | donchian | XAUUSD | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.50% | 1 | -487 | -163 | 64 | 37% | 0% () |
| 45 | donchian_55_20 | donchian | XAGUSD | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.50% | -1 | -340 | -236 | 23 | 16% | 0% () |
| 46 | donchian_20_10 | donchian | XAGUSD | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.75% | -0 | -568 | -236 | 70 | 40% | 0% () |
| 47 | donchian_55_20 | donchian | EURUSD | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.25% | -2 | -326 | -33 | 39 | 24% | 0% () |
| 48 | donchian_20_10 | donchian | EURUSD | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.25% | -4 | -598 | -44 | 80 | 31% | 0% () |
| 49 | donchian_55_20 | donchian | GBPUSD | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.50% | -1 | -373 | -62 | 39 | 32% | 0% () |
| 50 | donchian_20_10 | donchian | GBPUSD | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.25% | -1 | -210 | -42 | 62 | 32% | 0% () |
| 51 | donchian_55_20 | donchian | USDJPY | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.25% | -1 | -341 | -37 | 41 | 28% | 0% () |
| 52 | donchian_20_10 | donchian | USDJPY | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.25% | 0 | -310 | -40 | 72 | 42% | 0% () |
| 53 | rsi2_long | rsi2 | XAUUSD | D1 | `{}` | 1.00% | -3 | -564 | -70 | 48 | 18% | 0% () |
| 54 | rsi2_both | rsi2 | XAUUSD | D1 | `{"long_only": false}` | 0.50% | -3 | -302 | -30 | 45 | 12% | 0% () |
| 55 | rsi2_long | rsi2 | XAGUSD | D1 | `{}` | 1.50% | -3 | -496 | -132 | 41 | 16% | 0% () |
| 56 | rsi2_both | rsi2 | XAGUSD | D1 | `{"long_only": false}` | 0.75% | -4 | -562 | -60 | 70 | 23% | 0% () |
| 57 | rsi2_long | rsi2 | EURUSD | D1 | `{}` | 1.25% | -4 | -575 | -93 | 37 | 15% | 0% () |
| 58 | rsi2_both | rsi2 | EURUSD | D1 | `{"long_only": false}` | 1.25% | 1 | -506 | -125 | 101 | 44% | 0% () |
| 59 | rsi2_long | rsi2 | USDJPY | D1 | `{}` | 1.00% | -2 | -554 | -97 | 54 | 23% | 0% () |
| 60 | rsi2_both | rsi2 | USDJPY | D1 | `{"long_only": false}` | 1.25% | -0 | -548 | -130 | 107 | 44% | 0% () |
| 61 | donchian_55_20 | donchian | AUDUSD | D1 | `{"entry_n": 55, "exit_n": 20}` | 0.25% | -3 | -344 | -51 | 46 | 31% | 0% () |
| 62 | donchian_20_10 | donchian | AUDUSD | D1 | `{"entry_n": 20, "exit_n": 10}` | 0.25% | 0 | -249 | -77 | 77 | 44% | 0% () |
| 63 | donchian_55_20 | donchian | XAUUSD | H4 | `{"entry_n": 55, "exit_n": 20}` | 0.25% | 7 | -345 | -142 | 209 | 48% | 0% () |
| 64 | donchian_110_40 | donchian | XAUUSD | H4 | `{"entry_n": 110, "exit_n": 40}` | 0.25% | 2 | -458 | -104 | 134 | 35% | 0% () |
| 65 | prefomc_long | pre_fomc | XAUUSD | H1 | `{"side": "long"}` | 2.00% | 11 | -424 | -179 | 71 | 34% | 100% (2861) |
| 66 | prefomc_short | pre_fomc | XAUUSD | H1 | `{"side": "short"}` | 0.75% | -5 | -578 | -77 | 71 | 33% | 0% () |
| 67 | prefomc_long | pre_fomc | EURUSD | H1 | `{"side": "long"}` | 2.00% | 16 | -252 | -191 | 71 | 40% | 100% (2421) |
| 68 | prefomc_short | pre_fomc | EURUSD | H1 | `{"side": "short"}` | 0.50% | -5 | -555 | -45 | 71 | 25% | 0% () |
| 69 | prefomc_long | pre_fomc | USDJPY | H1 | `{"side": "long"}` | 0.50% | -4 | -431 | -47 | 71 | 26% | 0% () |
| 70 | prefomc_short | pre_fomc | USDJPY | H1 | `{"side": "short"}` | 1.50% | 7 | -475 | -108 | 71 | 39% | 0% () |
| 71 | tom_long | turn_of_month | XAUUSD | H1 | `{}` | 1.50% | 11 | -485 | -154 | 103 | 56% | 100% (1725) |
| 72 | kmw_postfix_17to21 | session_drift | EURUSD | H1 | `{"side": "long", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -8 | -1113 | -25 | 2313 | 37% | 0% () |
| 73 | kmw_prefix_14to17 | session_drift | EURUSD | H1 | `{"side": "short", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -15 | -1688 | -25 | 2320 | 33% | 0% () |
| 74 | kmw_postfix_17to21 | session_drift | GBPUSD | H1 | `{"side": "long", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -9 | -1124 | -24 | 2279 | 35% | 0% () |
| 75 | kmw_prefix_14to17 | session_drift | GBPUSD | H1 | `{"side": "short", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -12 | -1369 | -24 | 2285 | 36% | 0% () |
| 76 | kmw_postfix_17to21 | session_drift | AUDUSD | H1 | `{"side": "long", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -17 | -1883 | -32 | 2315 | 25% | 0% () |
| 77 | kmw_prefix_14to17 | session_drift | AUDUSD | H1 | `{"side": "short", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -16 | -1815 | -25 | 2320 | 31% | 0% () |
| 78 | kmw_postfix_17to21 | session_drift | NZDUSD | H1 | `{"side": "long", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -23 | -2527 | -25 | 2315 | 14% | 0% () |
| 79 | kmw_prefix_14to17 | session_drift | NZDUSD | H1 | `{"side": "short", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -23 | -2543 | -24 | 2320 | 19% | 0% () |
| 80 | kmw_postfix_17to21 | session_drift | USDJPY | H1 | `{"side": "short", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -18 | -1972 | -25 | 2313 | 26% | 0% () |
| 81 | kmw_prefix_14to17 | session_drift | USDJPY | H1 | `{"side": "long", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -20 | -2219 | -25 | 2320 | 29% | 0% () |
| 82 | kmw_postfix_17to21 | session_drift | XAUUSD | H1 | `{"side": "long", "entry_hour": 17, "exit_hour": 21, "sl_datr": 1.0}` | none | -8 | -975 | -28 | 1714 | 31% | 0% () |
| 83 | kmw_prefix_14to17 | session_drift | XAUUSD | H1 | `{"side": "short", "entry_hour": 14, "exit_hour": 17, "sl_datr": 1.0}` | none | -9 | -1133 | -25 | 1751 | 28% | 0% () |
| 84 | prefomc_usdshort | pre_fomc | XAUUSD | H1 | `{"side": "long"}` | 2.00% | 11 | -424 | -179 | 71 | 34% | 100% (2861) |
| 85 | prefomc_usdshort | pre_fomc | XAGUSD | H1 | `{"side": "long"}` | 2.00% | 9 | -574 | -150 | 71 | 36% | 0% () |
| 86 | prefomc_usdshort | pre_fomc | EURUSD | H1 | `{"side": "long"}` | 2.00% | 16 | -252 | -191 | 71 | 40% | 100% (2421) |
| 87 | prefomc_usdshort | pre_fomc | GBPUSD | H1 | `{"side": "long"}` | 2.00% | 16 | -305 | -119 | 71 | 39% | 100% (2078) |
| 88 | prefomc_usdshort | pre_fomc | AUDUSD | H1 | `{"side": "long"}` | 2.00% | 17 | -398 | -199 | 71 | 45% | 100% (1868) |
| 89 | prefomc_usdshort | pre_fomc | NZDUSD | H1 | `{"side": "long"}` | 2.00% | 16 | -336 | -157 | 71 | 40% | 100% (1925) |
| 90 | prefomc_usdshort | pre_fomc | USDJPY | H1 | `{"side": "short"}` | 1.50% | 7 | -475 | -108 | 71 | 39% | 0% () |
| 91 | prefomc_usdshort | pre_fomc | USDCHF | H1 | `{"side": "short"}` | 2.00% | 16 | -281 | -126 | 71 | 39% | 100% (2757) |
| 92 | prefomc_usdshort | pre_fomc | USDCAD | H1 | `{"side": "short"}` | 2.00% | 10 | -330 | -192 | 71 | 43% | 100% (2610) |
| 93 | prefomc_18to20 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 18, "exit_hour": 20}` | 2.00% | -1 | -160 | -50 | 71 | 28% | 0% () |
| 94 | prefomc_22to20 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 22, "exit_hour": 20}` | 2.00% | 11 | -353 | -181 | 71 | 38% | 100% (2861) |
| 95 | prefomc_20to19 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 19}` | 2.00% | 5 | -463 | -179 | 71 | 34% | 0% () |
| 96 | prefomc_20to21 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 21}` | 2.00% | -3 | -284 | -45 | 71 | 23% | 0% () |
| 97 | prefomc_20to23 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 23}` | 2.00% | 8 | -327 | -179 | 71 | 28% | 0% () |
| 98 | prefomc_16to20 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 16, "exit_hour": 20}` | 2.00% | -1 | -337 | -86 | 71 | 29% | 0% () |
| 99 | prefomc_sl1.0 | pre_fomc | XAUUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 1.50% | 12 | -478 | -135 | 71 | 34% | 100% (2581) |
| 100 | prefomc_sl2.0 | pre_fomc | XAUUSD | H1 | `{"side": "long", "sl_datr": 2.0}` | 2.00% | 8 | -317 | -119 | 71 | 34% | 0% () |
| 101 | prefomc_18to20 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 18, "exit_hour": 20}` | 2.00% | -2 | -241 | -55 | 71 | 28% | 0% () |
| 102 | prefomc_22to20 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 22, "exit_hour": 20}` | 2.00% | 15 | -257 | -188 | 71 | 39% | 100% (2463) |
| 103 | prefomc_20to19 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 19}` | 2.00% | 6 | -360 | -171 | 71 | 37% | 0% () |
| 104 | prefomc_20to21 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 21}` | 2.00% | -2 | -257 | -31 | 71 | 27% | 0% () |
| 105 | prefomc_20to23 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 20, "exit_hour": 23}` | 2.00% | -3 | -431 | -45 | 71 | 22% | 0% () |
| 106 | prefomc_16to20 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 16, "exit_hour": 20}` | 1.50% | -5 | -591 | -64 | 71 | 23% | 0% () |
| 107 | prefomc_sl1.0 | pre_fomc | EURUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 2.00% | 24 | -359 | -198 | 71 | 40% | 100% (1588) |
| 108 | prefomc_sl2.0 | pre_fomc | EURUSD | H1 | `{"side": "long", "sl_datr": 2.0}` | 2.00% | 12 | -192 | -146 | 71 | 40% | 100% (2876) |
| 109 | tom_db0_hd2 | turn_of_month | XAUUSD | H1 | `{"days_before": 0, "hold_days": 2}` | 1.50% | 6 | -486 | -154 | 100 | 51% | 100% (1448) |
| 110 | tom_db0_hd4 | turn_of_month | XAUUSD | H1 | `{"days_before": 0, "hold_days": 4}` | 1.50% | 15 | -517 | -154 | 100 | 53% | 100% (1649) |
| 111 | tom_db0_hd6 | turn_of_month | XAUUSD | H1 | `{"days_before": 0, "hold_days": 6}` | 1.25% | 8 | -545 | -203 | 100 | 53% | 100% (2363) |
| 112 | tom_db1_hd2 | turn_of_month | XAUUSD | H1 | `{"days_before": 1, "hold_days": 2}` | 2.00% | 12 | -462 | -230 | 103 | 50% | 100% (2037) |
| 113 | tom_db1_hd4 | turn_of_month | XAUUSD | H1 | `{"days_before": 1, "hold_days": 4}` | 1.50% | 11 | -485 | -154 | 103 | 56% | 100% (1725) |
| 114 | tom_db1_hd6 | turn_of_month | XAUUSD | H1 | `{"days_before": 1, "hold_days": 6}` | 1.25% | 8 | -572 | -146 | 102 | 51% | 100% (1682) |
| 115 | tom_db2_hd2 | turn_of_month | XAUUSD | H1 | `{"days_before": 2, "hold_days": 2}` | 1.50% | -1 | -477 | -179 | 103 | 50% | 0% () |
| 116 | tom_db2_hd4 | turn_of_month | XAUUSD | H1 | `{"days_before": 2, "hold_days": 4}` | 1.25% | 8 | -520 | -134 | 102 | 56% | 100% (2499) |
| 117 | tom_db2_hd6 | turn_of_month | XAUUSD | H1 | `{"days_before": 2, "hold_days": 6}` | 1.00% | 10 | -490 | -103 | 101 | 54% | 100% (2364) |
| 118 | tom_db3_hd2 | turn_of_month | XAUUSD | H1 | `{"days_before": 3, "hold_days": 2}` | 0.75% | -4 | -533 | -59 | 100 | 42% | 0% () |
| 119 | tom_db3_hd4 | turn_of_month | XAUUSD | H1 | `{"days_before": 3, "hold_days": 4}` | 1.25% | 1 | -587 | -146 | 103 | 49% | 0% () |
| 120 | tom_db3_hd6 | turn_of_month | XAUUSD | H1 | `{"days_before": 3, "hold_days": 6}` | 1.00% | 4 | -454 | -103 | 102 | 50% | 0% () |
| 121 | tom_long_1_4 | turn_of_month | XAGUSD | H1 | `{}` | 1.00% | -0 | -487 | -137 | 99 | 45% | 0% () |
| 122 | tom_short_1_4 | turn_of_month | XAGUSD | H1 | `{"side": "short"}` | 0.50% | -2 | -304 | -58 | 59 | 28% | 0% () |
| 123 | tom_long_1_4 | turn_of_month | EURUSD | H1 | `{}` | 0.50% | -1 | -441 | -47 | 108 | 50% | 0% () |
| 124 | tom_short_1_4 | turn_of_month | EURUSD | H1 | `{"side": "short"}` | 0.50% | -0 | -388 | -45 | 108 | 45% | 0% () |
| 125 | tom_long_1_4 | turn_of_month | GBPUSD | H1 | `{}` | 1.00% | -3 | -532 | -135 | 108 | 44% | 0% () |
| 126 | tom_short_1_4 | turn_of_month | GBPUSD | H1 | `{"side": "short"}` | 0.75% | -1 | -406 | -82 | 108 | 52% | 0% () |
| 127 | tom_long_1_4 | turn_of_month | USDJPY | H1 | `{}` | 0.50% | -2 | -464 | -61 | 108 | 47% | 0% () |
| 128 | tom_short_1_4 | turn_of_month | USDJPY | H1 | `{"side": "short"}` | 0.50% | -1 | -442 | -56 | 108 | 45% | 0% () |
| 129 | tom_long_1_4 | turn_of_month | AUDUSD | H1 | `{}` | 0.75% | -0 | -522 | -71 | 108 | 47% | 0% () |
| 130 | tom_short_1_4 | turn_of_month | AUDUSD | H1 | `{"side": "short"}` | 0.50% | -2 | -396 | -55 | 108 | 48% | 0% () |
| 131 | tom_eh10 | turn_of_month | XAUUSD | H1 | `{"entry_hour": 10}` | 1.25% | 9 | -489 | -111 | 107 | 56% | 100% (2546) |
| 132 | tom_eh16 | turn_of_month | XAUUSD | H1 | `{"entry_hour": 16}` | 1.50% | 14 | -478 | -154 | 108 | 58% | 100% (1343) |
| 133 | tom_d1 | turn_of_month | XAUUSD | D1 | `{}` | 1.50% | 15 | -416 | -154 | 108 | 55% | 100% (1604) |
| 134 | fomc_through_27b | pre_fomc | XAUUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 21 | -473 | -204 | 71 | 46% | 100% (1776) |
| 135 | prefomc_sl1 | pre_fomc | XAUUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 1.50% | 12 | -478 | -135 | 71 | 34% | 100% (2581) |
| 136 | fomc_through_27b | pre_fomc | XAGUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 21 | -556 | -177 | 71 | 49% | 100% (1779) |
| 137 | prefomc_sl1 | pre_fomc | XAGUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 1.50% | 11 | -571 | -143 | 71 | 36% | 100% (3148) |
| 138 | fomc_through_27b | pre_fomc | EURUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 16 | -431 | -195 | 71 | 42% | 100% (2638) |
| 139 | prefomc_sl1 | pre_fomc | EURUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 2.00% | 24 | -359 | -198 | 71 | 40% | 100% (1588) |
| 140 | fomc_through_27b | pre_fomc | GBPUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 17 | -381 | -151 | 71 | 42% | 100% (2239) |
| 141 | prefomc_sl1 | pre_fomc | GBPUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 2.00% | 24 | -463 | -179 | 71 | 39% | 100% (1455) |
| 142 | fomc_through_27b | pre_fomc | AUDUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 16 | -440 | -217 | 71 | 42% | 100% (1981) |
| 143 | prefomc_sl1 | pre_fomc | AUDUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 2.00% | 26 | -493 | -230 | 71 | 45% | 100% (1246) |
| 144 | fomc_through_27b | pre_fomc | NZDUSD | H1 | `{"side": "long", "hold_bars": 27}` | 2.00% | 13 | -577 | -182 | 71 | 39% | 100% (2288) |
| 145 | prefomc_sl1 | pre_fomc | NZDUSD | H1 | `{"side": "long", "sl_datr": 1.0}` | 2.00% | 23 | -435 | -171 | 71 | 40% | 100% (965) |
| 146 | fomc_through_27b | pre_fomc | USDJPY | H1 | `{"side": "short", "hold_bars": 27}` | 1.25% | 6 | -512 | -113 | 71 | 39% | 0% () |
| 147 | prefomc_sl1 | pre_fomc | USDJPY | H1 | `{"side": "short", "sl_datr": 1.0}` | 1.00% | 6 | -535 | -100 | 71 | 39% | 0% () |
| 148 | fomc_through_27b | pre_fomc | USDCHF | H1 | `{"side": "short", "hold_bars": 27}` | 2.00% | 19 | -540 | -188 | 71 | 41% | 100% (2135) |
| 149 | prefomc_sl1 | pre_fomc | USDCHF | H1 | `{"side": "short", "sl_datr": 1.0}` | 2.00% | 24 | -425 | -181 | 71 | 39% | 100% (1771) |
| 150 | fomc_through_27b | pre_fomc | USDCAD | H1 | `{"side": "short", "hold_bars": 27}` | 2.00% | 10 | -446 | -192 | 71 | 38% | 100% (2687) |
| 151 | prefomc_sl1 | pre_fomc | USDCAD | H1 | `{"side": "short", "sl_datr": 1.0}` | 2.00% | 15 | -499 | -201 | 71 | 43% | 100% (1171) |
| 152 | prefomc_eve22_to20 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 22}` | 2.00% | 11 | -353 | -181 | 71 | 38% | 100% (2861) |
| 153 | prefomc_eve19_to20 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 19}` | 2.00% | -1 | -140 | -39 | 71 | 29% | 0% () |
| 154 | prefomc_eve20_to19 | pre_fomc | XAUUSD | H1 | `{"side": "long", "exit_hour": 19}` | 2.00% | 5 | -463 | -179 | 71 | 34% | 0% () |
| 155 | prefomc_tp2 | pre_fomc | XAUUSD | H1 | `{"side": "long", "sl_datr": 1.0, "tp_datr": 2.0}` | 1.50% | 12 | -478 | -135 | 71 | 34% | 100% (2581) |
| 156 | fomc_daywithann_24b_from23 | pre_fomc | XAUUSD | H1 | `{"side": "long", "entry_hour": 23, "hold_bars": 24}` | 2.00% | 11 | -464 | -199 | 56 | 35% | 100% (3127) |
| 157 | prefomc_eve22_to20 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 22}` | 2.00% | 15 | -257 | -188 | 71 | 39% | 100% (2463) |
| 158 | prefomc_eve19_to20 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 19}` | 2.00% | -3 | -387 | -34 | 71 | 25% | 0% () |
| 159 | prefomc_eve20_to19 | pre_fomc | EURUSD | H1 | `{"side": "long", "exit_hour": 19}` | 2.00% | 6 | -360 | -171 | 71 | 37% | 0% () |
| 160 | prefomc_tp2 | pre_fomc | EURUSD | H1 | `{"side": "long", "sl_datr": 1.0, "tp_datr": 2.0}` | 2.00% | 25 | -359 | -198 | 71 | 40% | 100% (1477) |
| 161 | fomc_daywithann_24b_from23 | pre_fomc | EURUSD | H1 | `{"side": "long", "entry_hour": 23, "hold_bars": 24}` | 2.00% | 17 | -436 | -198 | 71 | 41% | 100% (2512) |
| 162 | prefomc_eve22_to20 | pre_fomc | GBPUSD | H1 | `{"side": "long", "entry_hour": 22}` | 2.00% | 16 | -278 | -119 | 71 | 37% | 100% (2029) |
| 163 | prefomc_eve19_to20 | pre_fomc | GBPUSD | H1 | `{"side": "long", "entry_hour": 19}` | 2.00% | -3 | -309 | -27 | 71 | 23% | 0% () |
| 164 | prefomc_eve20_to19 | pre_fomc | GBPUSD | H1 | `{"side": "long", "exit_hour": 19}` | 2.00% | 9 | -314 | -119 | 71 | 39% | 0% () |
| 165 | prefomc_tp2 | pre_fomc | GBPUSD | H1 | `{"side": "long", "sl_datr": 1.0, "tp_datr": 2.0}` | 2.00% | 24 | -463 | -179 | 71 | 39% | 100% (1455) |
| 166 | fomc_daywithann_24b_from23 | pre_fomc | GBPUSD | H1 | `{"side": "long", "entry_hour": 23, "hold_bars": 24}` | 2.00% | 19 | -322 | -156 | 71 | 42% | 100% (2078) |
| 167 | fomc_cycle_even_usdshort | fomc_cycle | XAUUSD | H1 | `{"side": "long"}` | 0.75% | 7 | -557 | -92 | 215 | 53% | 0% () |
| 168 | fomc_cycle_odd_usdshort | fomc_cycle | XAUUSD | H1 | `{"side": "long", "weeks": [1, 3, 5]}` | 0.75% | 0 | -547 | -67 | 179 | 41% | 0% () |
| 169 | fomc_cycle_even_usdshort | fomc_cycle | EURUSD | H1 | `{"side": "long"}` | 0.50% | 1 | -519 | -49 | 239 | 46% | 0% () |
| 170 | fomc_cycle_odd_usdshort | fomc_cycle | EURUSD | H1 | `{"side": "long", "weeks": [1, 3, 5]}` | 0.25% | -1 | -263 | -29 | 191 | 40% | 0% () |
| 171 | fomc_cycle_even_usdshort | fomc_cycle | GBPUSD | H1 | `{"side": "long"}` | 0.50% | 1 | -436 | -62 | 237 | 50% | 0% () |
| 172 | fomc_cycle_odd_usdshort | fomc_cycle | GBPUSD | H1 | `{"side": "long", "weeks": [1, 3, 5]}` | 0.25% | -3 | -322 | -26 | 143 | 33% | 0% () |
| 173 | fomc_cycle_even_usdshort | fomc_cycle | AUDUSD | H1 | `{"side": "long"}` | 0.25% | -1 | -323 | -32 | 238 | 44% | 0% () |
| 174 | fomc_cycle_odd_usdshort | fomc_cycle | AUDUSD | H1 | `{"side": "long", "weeks": [1, 3, 5]}` | 0.25% | -2 | -260 | -45 | 209 | 43% | 0% () |
| 175 | autumn_sep_nov | month_season | XAUUSD | D1 | `{}` | 0.50% | -2 | -255 | -30 | 9 | 1% | 0% () |
| 176 | autumn_sep_nov | month_season | XAGUSD | D1 | `{}` | 0.75% | -4 | -453 | -55 | 11 | 2% | 0% () |
| 177 | winter_dec_jan | month_season | XAUUSD | D1 | `{"months": [12, 1]}` | 2.00% | 14 | -284 | -156 | 17 | 10% | 100% (1450) |
| 178 | autumn_sep_nov_sl2 | month_season | XAUUSD | D1 | `{"sl_atr": 2.0}` | 0.50% | -4 | -449 | -101 | 15 | 1% | 0% () |
| 179 | gold_calendar | gold_calendar | XAUUSD | H1 | `{}` | 1.50% | 17 | -537 | -154 | 158 | 58% | 100% (1433) |
| 180 | gold_calendar_fsl1 | gold_calendar | XAUUSD | H1 | `{"fomc_sl": 1.0}` | 1.25% | 18 | -498 | -138 | 157 | 56% | 100% (1216) |
| 181 | gold_calendar_tom0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0}` | 2.00% | 29 | -586 | -206 | 157 | 56% | 100% (947) |
| 182 | gold_calendar | gold_calendar | XAGUSD | H1 | `{}` | 1.50% | 12 | -519 | -164 | 157 | 53% | 100% (2254) |
| 183 | imom_comex_m30 | intraday_momentum | XAUUSD | M30 | `{"signal_close": "16:00", "entry_close": "20:00", "exit_close": "20:30", "ref_close": "20:30"}` | none | -18 | -1224 | -25 | 1425 | 13% | 0% () |
| 184 | imom_comex_h1 | intraday_momentum | XAUUSD | H1 | `{"signal_close": "16:00", "entry_close": "20:00", "exit_close": "21:00", "ref_close": "21:00"}` | none | -23 | -2448 | -25 | 2272 | 18% | 0% () |
| 185 | imom_nyclose_m30 | intraday_momentum | XAUUSD | M30 | `{}` | none | -16 | -1157 | -19 | 1377 | 16% | 0% () |
| 186 | imom_nyclose_h1 | intraday_momentum | XAUUSD | H1 | `{}` | none | -22 | -2433 | -25 | 2218 | 18% | 0% () |
| 187 | imom_comex_m30 | intraday_momentum | XAGUSD | M30 | `{"signal_close": "16:00", "entry_close": "20:00", "exit_close": "20:30", "ref_close": "20:30"}` | none | -53 | -3626 | -24 | 1335 | 3% | 0% () |
| 188 | imom_comex_h1 | intraday_momentum | XAGUSD | H1 | `{"signal_close": "16:00", "entry_close": "20:00", "exit_close": "21:00", "ref_close": "21:00"}` | none | -65 | -7023 | -28 | 2188 | 3% | 0% () |
| 189 | imom_nyclose_m30 | intraday_momentum | XAGUSD | M30 | `{}` | none | -54 | -3693 | -18 | 1289 | 0% | 0% () |
| 190 | imom_nyclose_h1 | intraday_momentum | XAGUSD | H1 | `{}` | none | -65 | -7048 | -20 | 2139 | 0% | 0% () |
| 191 | gcal_db1_hd6_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 6, "fomc_sl": 1.0}` | 1.00% | 13 | -518 | -105 | 155 | 53% | 100% (1517) |
| 192 | gcal_db1_hd6_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 6, "fomc_sl": 1.5}` | 1.25% | 13 | -587 | -146 | 156 | 53% | 100% (1278) |
| 193 | gcal_db0_hd4 | gold_calendar | XAGUSD | H1 | `{"tom_days_before": 0}` | 1.00% | 5 | -419 | -137 | 153 | 44% | 0% () |
| 194 | gcal_tom_only_db0 | gold_calendar | XAUUSD | H1 | `{"fomc": false, "tom_days_before": 0}` | 1.50% | 15 | -517 | -154 | 100 | 53% | 100% (1649) |
| 195 | imom_nyclose_m30 | intraday_momentum | EURUSD | M30 | `{}` | none | -34 | -2140 | -14 | 1340 | 0% | 0% () |
| 196 | imom_nyclose_h1 | intraday_momentum | EURUSD | H1 | `{}` | none | -33 | -3607 | -25 | 2307 | 6% | 0% () |
| 197 | imom_nyclose_m30 | intraday_momentum | GBPUSD | M30 | `{}` | none | -27 | -1697 | -12 | 1340 | 2% | 0% () |
| 198 | imom_nyclose_h1 | intraday_momentum | GBPUSD | H1 | `{}` | none | -27 | -2966 | -24 | 2310 | 10% | 0% () |
| 199 | imom_nyclose_m30 | intraday_momentum | USDJPY | M30 | `{}` | none | -40 | -2515 | -24 | 1339 | 0% | 0% () |
| 200 | imom_nyclose_h1 | intraday_momentum | USDJPY | H1 | `{}` | none | -42 | -4544 | -25 | 2309 | 2% | 0% () |
| 201 | imom_comex_m30_sl1 | intraday_momentum | XAUUSD | M30 | `{"signal_close": "16:00", "entry_close": "20:00", "exit_close": "20:30", "ref_close": "20:30", "sl_datr": 1.0}` | 0.25% | -7 | -492 | -17 | 940 | 17% | 0% () |
| 202 | imom_comex_m30_sig1630 | intraday_momentum | XAUUSD | M30 | `{"signal_close": "16:30", "entry_close": "20:00", "exit_close": "20:30", "ref_close": "20:30"}` | none | -19 | -1344 | -25 | 1427 | 12% | 0% () |
| 203 | gcal_db0_hd2_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 2, "fomc_sl": 1.0}` | 1.50% | 20 | -418 | -154 | 158 | 56% | 100% (1265) |
| 204 | gcal_db0_hd2_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 2, "fomc_sl": 1.5}` | 2.00% | 22 | -465 | -206 | 158 | 53% | 100% (1105) |
| 205 | gcal_db0_hd3_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 3, "fomc_sl": 1.0}` | 1.50% | 20 | -500 | -154 | 157 | 56% | 100% (1419) |
| 206 | gcal_db0_hd3_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 3, "fomc_sl": 1.5}` | 1.50% | 17 | -440 | -154 | 157 | 56% | 100% (1590) |
| 207 | gcal_db0_hd4_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 4, "fomc_sl": 1.0}` | 1.50% | 26 | -479 | -154 | 157 | 59% | 100% (1112) |
| 208 | gcal_db0_hd4_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 4, "fomc_sl": 1.5}` | 2.00% | 29 | -586 | -206 | 157 | 56% | 100% (947) |
| 209 | gcal_db0_hd6_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 6, "fomc_sl": 1.0}` | 1.25% | 17 | -476 | -203 | 156 | 56% | 100% (1680) |
| 210 | gcal_db0_hd6_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 0, "tom_hold": 6, "fomc_sl": 1.5}` | 1.25% | 14 | -427 | -203 | 156 | 56% | 100% (1839) |
| 211 | gcal_db1_hd2_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 2, "fomc_sl": 1.0}` | 1.50% | 21 | -554 | -138 | 163 | 55% | 100% (1573) |
| 212 | gcal_db1_hd2_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 2, "fomc_sl": 1.5}` | 1.50% | 17 | -463 | -138 | 163 | 56% | 100% (1900) |
| 213 | gcal_db1_hd3_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 3, "fomc_sl": 1.0}` | 1.50% | 27 | -535 | -154 | 159 | 58% | 100% (1027) |
| 214 | gcal_db1_hd3_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 3, "fomc_sl": 1.5}` | 1.50% | 22 | -446 | -154 | 159 | 59% | 100% (1230) |
| 215 | gcal_db1_hd4_fsl1.0 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 4, "fomc_sl": 1.0}` | 1.25% | 18 | -498 | -138 | 157 | 56% | 100% (1216) |
| 216 | gcal_db1_hd4_fsl1.5 | gold_calendar | XAUUSD | H1 | `{"tom_days_before": 1, "tom_hold": 4, "fomc_sl": 1.5}` | 1.50% | 17 | -537 | -154 | 158 | 58% | 100% (1433) |
| 217 | overnight_22to15 | overnight | US500 | H1 | `{}` | 0.50% | -3 | -562 | -90 | 1977 | 40% | 0% () |
| 218 | tom_1_4 | turn_of_month | US500 | H1 | `{}` | 1.50% | 4 | -594 | -284 | 92 | 45% | 0% () |
| 219 | preholiday | pre_holiday | US500 | H1 | `{}` | 2.00% | 10 | -510 | -227 | 77 | 39% | 100% (902) |
| 220 | prefomc_long | pre_fomc | US500 | H1 | `{}` | 2.00% | 7 | -374 | -188 | 63 | 34% | 0% () |
| 221 | gap_fade | gap_fade | US500 | H1 | `{}` | none | -9 | -1724 | -37 | 1251 | 37% | 0% () |
| 222 | intraday_mom_h1 | intraday_momentum | US500 | H1 | `{}` | none | -26 | -2950 | -25 | 1970 | 26% | 0% () |
| 223 | overnight_22to15 | overnight | US30 | H1 | `{}` | 0.50% | 4 | -185 | -67 | 968 | 36% | 0% () |
| 224 | tom_1_4 | turn_of_month | US30 | H1 | `{}` | 1.50% | 7 | -521 | -180 | 89 | 45% | 0% () |
| 225 | preholiday | pre_holiday | US30 | H1 | `{}` | 2.00% | 7 | -531 | -188 | 76 | 36% | 0% () |
| 226 | prefomc_long | pre_fomc | US30 | H1 | `{}` | 2.00% | 7 | -402 | -143 | 63 | 40% | 0% () |
| 227 | gap_fade | gap_fade | US30 | H1 | `{}` | 0.25% | 3 | -544 | -31 | 941 | 38% | 0% () |
| 228 | intraday_mom_h1 | intraday_momentum | US30 | H1 | `{}` | none | -13 | -1471 | -25 | 1491 | 20% | 0% () |
| 229 | overnight_22to15 | overnight | USTEC | H1 | `{}` | 1.25% | 12 | -496 | -88 | 357 | 50% | 0% () |
| 230 | tom_1_4 | turn_of_month | USTEC | H1 | `{}` | 2.00% | 25 | -339 | -156 | 18 | 56% | 0% () |
| 231 | preholiday | pre_holiday | USTEC | H1 | `{}` | 2.00% | 9 | -177 | -89 | 15 | 39% | 0% () |
| 232 | prefomc_long | pre_fomc | USTEC | H1 | `{}` | 2.00% | 11 | -141 | -122 | 11 | 50% | 0% () |
| 233 | gap_fade | gap_fade | USTEC | H1 | `{}` | 0.50% | 0 | -390 | -72 | 222 | 44% | 0% () |
| 234 | intraday_mom_h1 | intraday_momentum | USTEC | H1 | `{}` | 1.25% | 25 | -571 | -123 | 356 | 56% | 0% () |
| 235 | eqcal_all | equity_calendar | US500 | H1 | `{}` | 1.00% | 10 | -502 | -225 | 193 | 52% | 100% (2387) |
| 236 | eqcal_sl1.0 | equity_calendar | US500 | H1 | `{"sl_datr": 1.0}` | 0.50% | 6 | -406 | -139 | 199 | 56% | 0% () |
| 237 | eqcal_sl2.0 | equity_calendar | US500 | H1 | `{"sl_datr": 2.0}` | 1.00% | 7 | -481 | -185 | 193 | 54% | 0% () |
| 238 | eqcal_db0 | equity_calendar | US500 | H1 | `{"tom_days_before": 0}` | 1.00% | 23 | -395 | -244 | 201 | 55% | 100% (990) |
| 239 | eqcal_hd2 | equity_calendar | US500 | H1 | `{"tom_hold": 2}` | 1.25% | 18 | -536 | -179 | 205 | 54% | 100% (1812) |
| 240 | eqcal_all | equity_calendar | US30 | H1 | `{}` | 1.00% | 11 | -521 | -116 | 178 | 48% | 100% (1804) |
| 241 | eqcal_sl1.0 | equity_calendar | US30 | H1 | `{"sl_datr": 1.0}` | 0.50% | 3 | -448 | -83 | 154 | 40% | 0% () |
| 242 | eqcal_sl2.0 | equity_calendar | US30 | H1 | `{"sl_datr": 2.0}` | 1.25% | 13 | -459 | -116 | 172 | 49% | 100% (1382) |
| 243 | eqcal_db0 | equity_calendar | US30 | H1 | `{"tom_days_before": 0}` | 1.50% | 35 | -481 | -203 | 198 | 56% | 100% (733) |
| 244 | eqcal_hd2 | equity_calendar | US30 | H1 | `{"tom_hold": 2}` | 0.75% | 5 | -530 | -85 | 157 | 45% | 0% () |
| 245 | eqcal_all | equity_calendar | USTEC | H1 | `{}` | 2.00% | 65 | -477 | -202 | 34 | 61% | 100% (363) |
| 246 | eqcal_sl1.0 | equity_calendar | USTEC | H1 | `{"sl_datr": 1.0}` | 1.50% | 64 | -480 | -202 | 35 | 56% | 100% (275) |
| 247 | eqcal_sl2.0 | equity_calendar | USTEC | H1 | `{"sl_datr": 2.0}` | 2.00% | 44 | -395 | -156 | 34 | 61% | 0% () |
| 248 | eqcal_db0 | equity_calendar | USTEC | H1 | `{"tom_days_before": 0}` | 2.00% | 4 | -487 | -181 | 36 | 39% | 0% () |
| 249 | eqcal_hd2 | equity_calendar | USTEC | H1 | `{"tom_hold": 2}` | 2.00% | 68 | -178 | -122 | 37 | 72% | 100% (464) |
| 250 | eqcal_all | equity_calendar | DE40 | H1 | `{}` | 1.00% | 10 | -496 | -148 | 193 | 51% | 100% (2225) |
| 251 | eqcal_sl1.0 | equity_calendar | DE40 | H1 | `{"sl_datr": 1.0}` | 0.75% | 6 | -489 | -142 | 203 | 46% | 0% () |
| 252 | eqcal_sl2.0 | equity_calendar | DE40 | H1 | `{"sl_datr": 2.0}` | 1.50% | 13 | -538 | -211 | 193 | 53% | 100% (2157) |
| 253 | eqcal_db0 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0}` | 1.25% | 28 | -567 | -166 | 194 | 53% | 100% (943) |
| 254 | eqcal_hd2 | equity_calendar | DE40 | H1 | `{"tom_hold": 2}` | 1.00% | 9 | -496 | -110 | 204 | 55% | 0% () |
| 255 | overnight_22to15_sl1 | overnight | US500 | H1 | `{"sl_datr": 1.0}` | 0.25% | -2 | -440 | -66 | 1978 | 43% | 0% () |
| 256 | overnight_22to16 | overnight | US500 | H1 | `{"exit_hour": 16}` | 0.50% | 2 | -532 | -90 | 1978 | 44% | 0% () |
| 257 | fomc_cycle_even | fomc_cycle | US500 | H1 | `{}` | 0.75% | 13 | -483 | -109 | 194 | 53% | 100% (3007) |
| 258 | gap_fade_0.4 | gap_fade | US500 | H1 | `{"min_gap_datr": 0.4}` | none | -9 | -1364 | -25 | 665 | 35% | 0% () |
| 259 | overnight_22to15_sl1 | overnight | US30 | H1 | `{"sl_datr": 1.0}` | 0.50% | 9 | -498 | -126 | 1506 | 44% | 100% (1425) |
| 260 | overnight_22to16 | overnight | US30 | H1 | `{"exit_hour": 16}` | 0.75% | 15 | -462 | -126 | 1505 | 49% | 100% (1069) |
| 261 | fomc_cycle_even | fomc_cycle | US30 | H1 | `{}` | 1.00% | 20 | -347 | -114 | 149 | 44% | 100% (749) |
| 262 | gap_fade_0.4 | gap_fade | US30 | H1 | `{"min_gap_datr": 0.4}` | none | -2 | -884 | -25 | 538 | 34% | 0% () |
| 263 | eqcal_db0_hd2 | equity_calendar | US500 | H1 | `{"tom_days_before": 0, "tom_hold": 2}` | 1.50% | 29 | -528 | -176 | 205 | 58% | 100% (789) |
| 264 | eqcal_db0_hd3 | equity_calendar | US500 | H1 | `{"tom_days_before": 0, "tom_hold": 3}` | 1.00% | 19 | -395 | -244 | 201 | 52% | 100% (1056) |
| 265 | eqcal_db0_hd6 | equity_calendar | US500 | H1 | `{"tom_days_before": 0, "tom_hold": 6}` | 1.00% | 27 | -395 | -244 | 200 | 55% | 100% (888) |
| 266 | eqcal_db0_sl1.0 | equity_calendar | US500 | H1 | `{"tom_days_before": 0, "sl_datr": 1.0}` | 0.75% | 22 | -421 | -235 | 203 | 50% | 100% (1006) |
| 267 | eqcal_db0_sl2.0 | equity_calendar | US500 | H1 | `{"tom_days_before": 0, "sl_datr": 2.0}` | 1.25% | 23 | -316 | -258 | 199 | 55% | 100% (1018) |
| 268 | tom_only_db0_hd4 | turn_of_month | US500 | H1 | `{"days_before": 0, "hold_days": 4}` | 1.25% | 18 | -395 | -258 | 89 | 54% | 100% (1314) |
| 269 | control_every8_off0 | control_long | US500 | H1 | `{"every": 8, "offset": 0, "hold_days": 4}` | 0.50% | 8 | -576 | -79 | 246 | 47% | 100% (1792) |
| 270 | control_every8_off3 | control_long | US500 | H1 | `{"every": 8, "offset": 3, "hold_days": 4}` | 0.25% | 2 | -313 | -65 | 245 | 47% | 0% () |
| 271 | control_every8_off6 | control_long | US500 | H1 | `{"every": 8, "offset": 6, "hold_days": 4}` | 0.50% | 5 | -401 | -112 | 248 | 48% | 0% () |
| 272 | eqcal_db0_hd2 | equity_calendar | US30 | H1 | `{"tom_days_before": 0, "tom_hold": 2}` | 1.50% | 26 | -481 | -159 | 203 | 56% | 100% (1000) |
| 273 | eqcal_db0_hd3 | equity_calendar | US30 | H1 | `{"tom_days_before": 0, "tom_hold": 3}` | 1.50% | 30 | -481 | -180 | 199 | 55% | 100% (830) |
| 274 | eqcal_db0_hd6 | equity_calendar | US30 | H1 | `{"tom_days_before": 0, "tom_hold": 6}` | 1.50% | 47 | -481 | -203 | 197 | 55% | 100% (528) |
| 275 | eqcal_db0_sl1.0 | equity_calendar | US30 | H1 | `{"tom_days_before": 0, "sl_datr": 1.0}` | 1.00% | 32 | -367 | -204 | 200 | 53% | 100% (691) |
| 276 | eqcal_db0_sl2.0 | equity_calendar | US30 | H1 | `{"tom_days_before": 0, "sl_datr": 2.0}` | 2.00% | 36 | -468 | -203 | 198 | 57% | 100% (666) |
| 277 | tom_only_db0_hd4 | turn_of_month | US30 | H1 | `{"days_before": 0, "hold_days": 4}` | 1.50% | 17 | -483 | -203 | 87 | 51% | 100% (1207) |
| 278 | control_every8_off0 | control_long | US30 | H1 | `{"every": 8, "offset": 0, "hold_days": 4}` | 0.75% | 19 | -486 | -93 | 190 | 50% | 100% (896) |
| 279 | control_every8_off3 | control_long | US30 | H1 | `{"every": 8, "offset": 3, "hold_days": 4}` | 0.75% | 6 | -586 | -200 | 190 | 41% | 0% () |
| 280 | control_every8_off6 | control_long | US30 | H1 | `{"every": 8, "offset": 6, "hold_days": 4}` | 0.75% | 10 | -431 | -149 | 189 | 43% | 100% (2106) |
| 281 | eqcal_db0_hd2 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0, "tom_hold": 2}` | 1.50% | 29 | -554 | -208 | 198 | 55% | 100% (941) |
| 282 | eqcal_db0_hd3 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0, "tom_hold": 3}` | 1.25% | 26 | -533 | -166 | 195 | 54% | 100% (1006) |
| 283 | eqcal_db0_hd6 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0, "tom_hold": 6}` | 1.25% | 30 | -553 | -195 | 192 | 52% | 100% (945) |
| 284 | eqcal_db0_sl1.0 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0, "sl_datr": 1.0}` | 1.00% | 37 | -560 | -160 | 196 | 50% | 100% (690) |
| 285 | eqcal_db0_sl2.0 | equity_calendar | DE40 | H1 | `{"tom_days_before": 0, "sl_datr": 2.0}` | 1.50% | 23 | -502 | -151 | 194 | 54% | 100% (1081) |
| 286 | tom_only_db0_hd4 | turn_of_month | DE40 | H1 | `{"days_before": 0, "hold_days": 4}` | 1.50% | 13 | -598 | -171 | 82 | 43% | 100% (1405) |
| 287 | control_every8_off0 | control_long | DE40 | H1 | `{"every": 8, "offset": 0, "hold_days": 4}` | 0.50% | -2 | -556 | -96 | 210 | 44% | 0% () |
| 288 | control_every8_off3 | control_long | DE40 | H1 | `{"every": 8, "offset": 3, "hold_days": 4}` | 0.50% | 5 | -371 | -73 | 210 | 43% | 0% () |
| 289 | control_every8_off6 | control_long | DE40 | H1 | `{"every": 8, "offset": 6, "hold_days": 4}` | 0.50% | -2 | -569 | -58 | 213 | 40% | 0% () |
| 290 | control_every8_off0 | control_long | XAUUSD | H1 | `{"every": 8, "offset": 0, "hold_days": 4}` | 0.50% | 4 | -500 | -49 | 266 | 52% | 0% () |
| 291 | control_every8_off3 | control_long | XAUUSD | H1 | `{"every": 8, "offset": 3, "hold_days": 4}` | 0.75% | 9 | -595 | -108 | 275 | 47% | 100% (2793) |
| 292 | control_every8_off6 | control_long | XAUUSD | H1 | `{"every": 8, "offset": 6, "hold_days": 4}` | 0.50% | 5 | -348 | -81 | 260 | 47% | 0% () |
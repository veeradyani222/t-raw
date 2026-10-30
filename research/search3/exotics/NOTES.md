# search3 / exotics — USDZAR USDMXN USDNOK USDSEK EURNOK EURSEK USDSGD USDCNH USDPLN

Round 3, from-scratch, per-market search. Judge: `research/prop/harness.py`,
`PROP_OOS=1`, scored 2024-10-20 .. 2026-10-30 on H1 / H4 / D1. No statistical
gates (owner's call); what stays: the look-ahead check (every candidate) and the
300/800 rule (best_risk = highest risk with worst day > -$300 and max DD > -$600).

Files: `strategies.py` (27 builders + `patch_harness()` + `clean()`), `batches.py`
(sweeps), `run.py` (Pool(2) runner, writes `results.jsonl` and `lookahead.jsonl`),
`study.py` (market study + data quality, writes `study.md`), `table.py` (this table).

## Harness patch (what I used for costs / conversion)

`strategies.patch_harness()` must be called before `H.load` on these symbols:

* **Profit-currency conversion.** The stock harness only knows JPY/CHF/CAD/GBP/EUR.
  USDZAR P&L is in ZAR, EURNOK in NOK, etc. The patch converts with the quote
  currency's USD pair (USDXXX -> conv = 1/close of the pair itself; EURNOK/EURSEK
  -> 1/USDNOK, 1/USDSEK), decided from the symbol name, so a missing
  `symbol_specs.json` entry can never silently treat ZAR as USD (18x overstatement).
* **Symbol specs** default to 5-digit FX (point 1e-5, contract 100k, min 0.01 lot)
  if the fetch has not written them (stock default point=0.01 would scale the
  bar's spread column 1000x).
* **Spread floors (price units)** from IC Markets' published raw-spread averages
  (icmarkets.com/global/en/trading-pricing/spreads, read 2026-10-30) scaled x1.3
  for a FundedNext feed; the harness takes the larger of floor and the bar's own
  recorded spread, so quiet-hour bars are never cheaper than this:

  | symbol | IC raw avg (pips) | floor used | ~bp of price |
  |---|---|---|---|
  | USDZAR | 79.9 | 0.0100 | ~5.7 |
  | USDMXN | 28.6 | 0.0040 | ~2.1 |
  | USDNOK | 36.8 | 0.0050 | ~5.0 |
  | USDSEK | 30.3 | 0.0040 | ~4.2 |
  | EURNOK | n/a (assumed USDNOK x1.1) | 0.0055 | ~4.7 |
  | EURSEK | n/a (assumed USDSEK x1.1) | 0.0045 | ~4.1 |
  | USDSGD | 0.85 | 0.00012 | ~0.9 |
  | USDCNH | 2.9 | 0.00040 | ~0.6 |
  | USDPLN | 15.8 | 0.0022 | ~5.9 |

* Commission: stock $14/lot round trip (FX). Slippage: stock 0.1 pip per fill.
* Swap/carry is NOT modelled by the harness (positive or negative); "carry"
  ideas below are therefore tested only as a *direction filter* (trade the side
  the carry/depreciation drift favours), never as earned interest.

## Practitioner research (what people say works on exotics)

Mostly broker education and forum material; none of it comes with a cost-adjusted
backtest, so every rule below was tested here rather than trusted.

* IG / tastyfx "How to trade USD/ZAR part 2: swing trading and position sizing":
  MA for trend, RSI for timing, size from fixed risk and stop distance -> tested
  as `ema_pullback` (EMA20/100-200 + RSI) and `rsi2_trend`.
  https://www.ig.com/za/trading-strategies/how-to-trade-the-usd-zar-part-2--swing-trading---position-sizing-190405
* DailyFX "Walk on the Exotic Side" (2012): USDMXN/USDZAR highest rollover; filter
  trades to the positive-carry side -> tested as `carry_trend` (side filter).
  https://www.dailyfx.com/forex/education/trading_tips/daily_trading_lesson/2012/10/12/Take_Your_Forex_Trading_For_a_Walk_on_the_Exotic_Side.html
* Saxo "FX Breakout Monitor" (2018-19): breaks of 19-day / 49-day closing
  highs/lows on EURSEK/EURNOK, often around Swedish/Norwegian CPI -> tested as
  `range_compression_break` (n=20/50 closing-channel, compressed-range filter)
  and `donchian_trail`.
  https://home.saxo/en-gb/content/articles/forex/fx-breakout-monitor-december-12-2018-12122018
* TMGM / broker pages: EURNOK best traded 07:00-15:00 UTC (Oslo/Frankfurt
  overlap, server 09/10-17/18), NOKSEK 08:00-16:00 CET; Norges Bank 09:00 UTC,
  Riksbank / CPI in the same morning window -> tested as `session_range_break`
  (Asian range, European morning break) and `hour_drift` windows.
  https://www.tmgm.com/en-eu/trading/instrument/eurnok
* OCBC via FXStreet, VT Markets: USDCNH anchored by the PBoC fix, range trades
  favoured; USDSGD managed inside the MAS band -> tested as `bb_revert`,
  `pdh_pdl_fade`, `round_number` fade on the managed pairs.
  https://www.fxstreet.com/news//chinese-yuan-rangebound-trade-against-us-dollar-guided-by-pboc-fix-ocbc-202607272157
* Academic EM carry/momentum (Daniel-Hodrick-Lu NBER w20433; CXO summary of EM
  carry drawdowns): EM currencies sell off together in risk-off, drawdowns
  -5% to -17% over 1-3 months, momentum diversifies carry -> tested as
  `spike_follow` (follow vs fade a >1.5-2.5 ATR day) and `tsmom`.
  https://www.cxoadvisory.com/currency-trading/currency-carry-trade-drawdowns
* Broker session notes for USDZAR: liquidity thinnest in Asia, peak in the
  London/NY overlap (12-16 UTC = server 15-19), SARB at 13:00 UTC.
  https://tiomarkets.com/article/forex-trading-sessions-in-south-africa-sast-best-trading-hours-and-usdzar-guide
* IC Markets spreads page (cost inputs above).
  https://www.icmarkets.com/global/en/trading-pricing/spreads/
* Second pass (2026-10-30, round-3 continuation): searches for USDMXN session /
  Banxico rules, EURNOK-EURSEK range rules around Norges Bank / Riksbank, and
  USDCNH "fade the 09:15 fix" strategies returned only broker pages (TMGM,
  Pepperstone 2023 "trend-followers dream"), Newsquawk / MNI fix commentary
  (a single fix deviation is noise, a run of them is the signal, spot vs the
  band edge matters) and TradingView opinions; nothing with entry/exit rules
  or a backtest, so nothing new was added from that channel. The USDCNH fix
  idea is covered indirectly by tsmom / carry_trend (the fix drift IS the
  trend) and by range_box_fade / bb_revert (band behaviour).
* No credible video/podcast rule set with a transcript turned up for these pairs
  (results were broker marketing), so nothing from that channel was tested.

## Ideas tested (27 builders)

| # | builder | idea | exit |
|---|---|---|---|
| 1 | donchian_trail | N-bar channel break, ATR trail | trail |
| 2 | ema_pullback | EMA trend + pullback to fast EMA + RSI | tp_r / trail |
| 3 | tsmom | sign of N-bar return, ATR stop | trail / time |
| 4 | range_compression_break | Saxo-style closing-channel break only when the range is compressed | trail / tp_r |
| 5 | session_range_break | Asian range break during the European morning | time (exit_hour) + tp |
| 6 | pdh_pdl_break | prior-day high/low break, intraday | time + tp |
| 7 | pdh_pdl_fade | prior-day high/low sweep-and-reject | tp / time |
| 8 | bb_revert | Bollinger fade (managed pairs) | midline / tp |
| 9 | rsi2_trend | RSI(2) pullback in 200-MA trend | RSI exit / time |
| 10 | round_number | big-figure break or fade | tp / time |
| 11 | squeeze_break | ATR percentile squeeze then N-bar break | tp / trail |
| 12 | gap_fade | weekend gap fade to Friday close (or follow) | tp fill / time |
| 13 | inside_day_break | NR-k / inside day break on D1 | tp / time |
| 14 | spike_follow | follow or fade a >k ATR day (risk-off spikes) | tp / time |
| 15 | hour_drift | enter at hour h, exit at hour h2, side fixed or D1 trend | time |
| 16 | pwh_pwl_break | prior-week high/low break | trail / tp |
| 17 | keltner_ride | close outside Keltner in trend direction | midline exit |
| 18 | daily_follow | yesterday's direction, day open to day end | time |
| 19 | ema_cross_flip | EMA cross, always-in, flip | flip / trail |
| 20 | carry_trend | one-sided Donchian break on the carry/drift side | trail |
| 21 | swing_bos | fractal swing high/low break-of-structure, stop at last swing | trail / tp_r |
| 22 | range_box_fade | tight multi-week box (< k ATR): buy bottom q / sell top q, target the middle | tp mid / time |
| 23 | three_bar_pullback | m counter-trend closes on the trend side of the SMA, re-entry close | tp_r / time / trail |
| 24 | pwh_pwl_fade | prior-week high/low sweep-and-reject | tp / time |
| 25 | weekly_open_follow | Monday open: follow or fade the k-week direction, exit Friday | time |
| 26 | vol_regime_tsmom | momentum only while ATR is above (rising) / below (falling) its SMA | trail |
| 27 | london_fix_fade | fade / follow the 3h move into the 16:00 London fix | tp / time |
| -- | hour_drift (openhour batch) | the study's server-09:00 positive hour on its own | time |

## Look-ahead check

`run.lookahead_check`: `build(df)` vs `build(df.iloc[:k])` (attrs re-attached) for
5 random k in [n/3, n); every Entry at index < k compared on side / sl / tp /
max_hold / exit_hour / manage name / meta. Run once per (builder, params) on the
first symbol met (1814 checks, 0 failures, `lookahead.jsonl`) and
again, on its own symbol with two more seeds, for each of the 8 returned
candidates (all passed, `candidates.json`).

## Data quality

Source: IC Markets demo via `research.data_fetch` (same fetch() as the
orchestrator; hedge copy staged in the session scratchpad and copied into
`data/search/` only where the orchestrator had not written the file).

* **History is short.** The demo serves USDZAR USDMXN USDNOK USDSEK USDSGD USDCNH
  USDPLN only from **2025-01-02** (475 trading days, 11.4k H1 bars) and EURNOK /
  EURSEK only from **2025-09-22** (288 days, 6.9k H1 bars). The scoring window
  therefore starts 2.5 months (9 months for EURNOK/EURSEK) after 2024-10-20 and
  every D1 result below rests on 5-90 trades. Treat avg_month as a 13-22 month
  sample, not a two-year one.
* **Flat / stale days (daily range < 5% of the median daily range): 0 on every
  symbol. Gaps > 3.5 days: 0. Zero-volume bars: 0.** `strategies.clean()` would
  have dropped them; nothing was dropped.
* **Rollover artefact, not a signal.** On every pair the server-hour 23:00 and
  00:00 bars show a large negative mean "return" and 01:00 a matching positive
  one (|t| 7-26). That is the bid sagging while the 00:00 spread blows out (ZAR
  median bar spread 509 points, ~2,000+ at the roll). No builder trades
  22:00-02:00 server, and hour_drift windows avoid it.
* Symbol specs (digits 5, point 1e-5, contract 100k, min 0.01 lot, profit
  currency = quote) were read from the terminal into the staged `specs.json`
  and match the defaults `patch_harness()` falls back to. One run (USDPLN
  session_range_break) crashed with a JSONDecodeError while the orchestrator's
  fetch was rewriting `symbol_specs.json`; it was re-run. One result line was
  lost to two writers appending at once (table.py now skips and counts it).

## Market study (study.py, 2025-01 / 2025-09 .. 2026-10-30, server time)

What the numbers say, group-wide:

* **Mean reversion at the daily scale, everywhere.** Variance ratios VR(20) are
  below 1 on 8 of 9 pairs (USDZAR 0.57, USDCNH 0.43, USDSGD 0.67, USDPLN 0.75,
  USDMXN 0.82, EURSEK 0.84, USDSEK 0.88, USDNOK 0.92); only EURNOK (1.12, short
  sample) trends. 20-day breakouts do NOT follow through on any pair (5-day
  forward return after an up-break is negative on all 9). This is why the
  plain Donchian / channel breakouts score worse than squeezes, inside-day
  breaks and pullbacks, and why the 2-week fade (weekly_open_follow mode=fade)
  works on USDSEK / USDPLN.
* **USD drift.** Every USDXXX pair fell over the window (USDNOK -2,115 bp,
  USDSEK -1,265 bp, USDZAR -1,202 bp, USDCNH -981 bp, USDMXN -878 bp). The
  "carry side" (short USDMXN / USDZAR) and the trend side coincided, so
  carry_trend side=short results are really USD-downtrend results.
* **Sessions.** Busiest hours are the London/NY overlap (server 15-17) on all
  pairs plus 10-11 (European morning) on the Scandis and ZAR, and 03-04 on
  USDCNH (onshore open / PBoC fix at 09:15 Beijing = server 03:15). Server
  hour 09 (08:00 CET, European open) has a positive mean return on every
  EUR/USD-vs-Scandi/CEE pair (t 3.6-9.7) and hour 08 negative; traded on its own
  (openhour batch, 153 runs) it loses to spread on every pair: 5-7 bp of drift
  against a 4-6 bp floor.
* **Cost is the filter.** Spread floor as % of H1 ATR: USDPLN 38%, EURSEK 35%,
  EURNOK 32%, USDZAR 28%, USDNOK 26%, USDSEK 22%, USDMXN 16%, USDCNH 13%,
  USDSGD 12%. Everything intraday (session range breaks, PDH/PDL, round
  numbers, London fix, open hour) is negative after spread on the high-cost
  pairs; H1 is only viable on USDCNH / USDSGD / USDMXN, and even there the
  survivors are H4 / D1. As % of D1 ATR the floor is 2-7%, which is where the
  candidates live.
* **Weekend gaps** are small (median 5-30 bp) and fill the same day 84-96% of
  the time; gap_fade still cannot beat the Monday 00:00 spread.
* **Risk-off days.** Biggest single days: USDNOK 413 bp, USDMXN 308 bp, USDZAR
  289 bp, USDSEK 245 bp. With a 1.5-2.5 ATR stop at 2% risk that is a $200-300
  day, which is what caps best_risk at 1.5-2% on the D1 candidates.

Per-symbol detail (verbatim from study.py):

### USDZAR
- data H1: 11376 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~17.1050; median bar spread 0.00509 (3.0 bp), floor 0.01 (5.8 bp); H1 ATR 0.03607 -> spread/ATR(H1) 0.28; D1 ATR 0.1924 -> spread/ATR(D1) 0.052
- busiest server hours (mean H1 range bp): 15:33.4, 17:32.9, 16:31.5, 10:30.8, 11:27.3
- hours with |t|>2 mean return (bp/hr): 0:-2.22(t=-2.3), 1:+10.21(t=15.9), 2:+1.62(t=2.8), 9:+2.89(t=3.8), 23:-12.77(t=-17.8)
- weekday total drift bp (Mon..Fri): -395, -158, -725, +558, -535; mean H1 range bp: 22.5, 21.8, 22.9, 23.7, 23.2
- D1 return autocorr lag1 -0.105, lag5 -0.034; variance ratio VR(5) 0.78, VR(20) 0.57 (>1 trend, <1 mean-revert); sign persistence 0.47; H1 autocorr lag1 -0.053; total drift since 2024-10-20 -1202 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -95 (n=12), down +16 (n=40)
- weekend gap: median |gap| 19.8 bp, mean -0.4 bp, same-day fill rate 0.86 (n=95)
- D1 ATR p10/p50/p90 bp: 77/112/151; biggest day move 289 bp

### USDMXN
- data H1: 11374 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~18.3480; median bar spread 0.00209 (1.1 bp), floor 0.004 (2.2 bp); H1 ATR 0.02570 -> spread/ATR(H1) 0.16; D1 ATR 0.1425 -> spread/ATR(D1) 0.028
- busiest server hours (mean H1 range bp): 17:29.8, 15:28.6, 16:28.0, 18:24.1, 19:20.2
- hours with |t|>2 mean return (bp/hr): 0:-5.81(t=-7.6), 1:+8.94(t=20.2), 15:-2.05(t=-2.1), 23:-2.53(t=-5.5)
- weekday total drift bp (Mon..Fri): -470, -695, -241, +364, +66; mean H1 range bp: 16.9, 16.0, 15.7, 16.3, 15.9
- D1 return autocorr lag1 -0.098, lag5 -0.026; variance ratio VR(5) 0.77, VR(20) 0.82 (>1 trend, <1 mean-revert); sign persistence 0.47; H1 autocorr lag1 -0.026; total drift since 2024-10-20 -878 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -11 (n=18), down -32 (n=45)
- weekend gap: median |gap| 15.6 bp, mean -4.5 bp, same-day fill rate 0.89 (n=95)
- D1 ATR p10/p50/p90 bp: 51/78/140; biggest day move 308 bp

### USDNOK
- data H1: 11380 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~10.0067; median bar spread 0.00341 (3.4 bp), floor 0.005 (5.0 bp); H1 ATR 0.01956 -> spread/ATR(H1) 0.26; D1 ATR 0.1036 -> spread/ATR(D1) 0.048
- busiest server hours (mean H1 range bp): 0:35.1, 17:29.4, 15:28.5, 10:27.9, 16:26.9
- hours with |t|>2 mean return (bp/hr): 0:-13.06(t=-18.2), 1:+12.59(t=20.3), 2:+1.63(t=3.4), 4:+0.97(t=2.1), 8:-1.92(t=-4.4), 9:+6.67(t=9.5), 10:-2.25(t=-2.6), 14:-1.33(t=-2.1), 19:-1.59(t=-3.4), 23:-3.89(t=-9.9)
- weekday total drift bp (Mon..Fri): -659, -520, -586, -102, -217; mean H1 range bp: 21.8, 20.1, 20.7, 21.1, 21.4
- D1 return autocorr lag1 -0.009, lag5 +0.000; variance ratio VR(5) 0.95, VR(20) 0.92 (>1 trend, <1 mean-revert); sign persistence 0.50; H1 autocorr lag1 -0.100; total drift since 2024-10-20 -2115 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -8 (n=19), down -15 (n=28)
- weekend gap: median |gap| 30.2 bp, mean -32.6 bp, same-day fill rate 0.94 (n=95)
- D1 ATR p10/p50/p90 bp: 80/104/131; biggest day move 413 bp

### USDSEK
- data H1: 11382 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~9.5301; median bar spread 0.00419 (4.4 bp), floor 0.004 (4.2 bp); H1 ATR 0.01798 -> spread/ATR(H1) 0.22; D1 ATR 0.1030 -> spread/ATR(D1) 0.039
- busiest server hours (mean H1 range bp): 17:32.5, 0:31.6, 15:30.9, 16:28.3, 10:26.4
- hours with |t|>2 mean return (bp/hr): 0:-10.52(t=-15.2), 1:+10.98(t=18.0), 4:+1.06(t=2.3), 8:-1.45(t=-3.3), 9:+2.58(t=3.6), 18:+1.85(t=2.5), 23:-3.45(t=-8.3)
- weekday total drift bp (Mon..Fri): -575, -324, +376, -200, -449; mean H1 range bp: 20.9, 19.7, 20.5, 21.1, 20.4
- D1 return autocorr lag1 -0.039, lag5 -0.023; variance ratio VR(5) 0.90, VR(20) 0.88 (>1 trend, <1 mean-revert); sign persistence 0.46; H1 autocorr lag1 -0.063; total drift since 2024-10-20 -1265 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -9 (n=20), down -32 (n=31)
- weekend gap: median |gap| 28.1 bp, mean -23.8 bp, same-day fill rate 0.92 (n=95)
- D1 ATR p10/p50/p90 bp: 78/108/148; biggest day move 245 bp

### EURNOK
- data H1: 6892 bars 2025-09-22..2026-10-30, 288 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~11.1571; median bar spread 0.00510 (4.6 bp), floor 0.0055 (4.9 bp); H1 ATR 0.01716 -> spread/ATR(H1) 0.32; D1 ATR 0.0888 -> spread/ATR(D1) 0.062
- busiest server hours (mean H1 range bp): 0:31.1, 10:22.2, 1:22.1, 16:19.9, 17:19.8
- hours with |t|>2 mean return (bp/hr): 0:-12.52(t=-14.9), 1:+10.89(t=14.3), 2:+1.11(t=2.2), 5:-0.86(t=-2.4), 8:-1.58(t=-3.6), 9:+7.07(t=9.7), 10:-2.04(t=-2.4), 13:-1.73(t=-2.7), 14:-1.74(t=-2.7), 19:-1.79(t=-4.8), 21:-0.75(t=-2.5), 23:-2.25(t=-6.8)
- weekday total drift bp (Mon..Fri): +143, -315, -767, +167, -439; mean H1 range bp: 16.5, 15.5, 15.6, 16.0, 16.7
- D1 return autocorr lag1 -0.069, lag5 +0.054; variance ratio VR(5) 0.90, VR(20) 1.12 (>1 trend, <1 mean-revert); sign persistence 0.52; H1 autocorr lag1 -0.143; total drift since 2024-10-20 -1264 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -17 (n=13), down -4 (n=22)
- weekend gap: median |gap| 18.5 bp, mean -24.0 bp, same-day fill rate 0.96 (n=57)
- D1 ATR p10/p50/p90 bp: 64/80/100; biggest day move 216 bp

### EURSEK
- data H1: 6894 bars 2025-09-22..2026-10-30, 288 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~10.9442; median bar spread 0.00494 (4.5 bp), floor 0.0045 (4.1 bp); H1 ATR 0.01294 -> spread/ATR(H1) 0.35; D1 ATR 0.0688 -> spread/ATR(D1) 0.065
- busiest server hours (mean H1 range bp): 0:24.6, 17:18.5, 15:17.0, 10:16.4, 16:16.3
- hours with |t|>2 mean return (bp/hr): 0:-10.63(t=-14.3), 1:+10.16(t=14.3), 4:+0.69(t=2.2), 6:-0.51(t=-2.4), 7:+0.51(t=2.1), 8:-1.15(t=-4.0), 9:+3.18(t=5.8), 14:-1.69(t=-3.2), 19:-0.86(t=-2.3), 23:-1.28(t=-4.1)
- weekday total drift bp (Mon..Fri): +165, +44, -86, +134, -276; mean H1 range bp: 12.4, 12.1, 12.3, 12.7, 12.3
- D1 return autocorr lag1 -0.108, lag5 -0.005; variance ratio VR(5) 0.81, VR(20) 0.84 (>1 trend, <1 mean-revert); sign persistence 0.47; H1 autocorr lag1 -0.143; total drift since 2024-10-20 -40 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -13 (n=14), down -4 (n=10)
- weekend gap: median |gap| 17.7 bp, mean -21.9 bp, same-day fill rate 0.96 (n=57)
- D1 ATR p10/p50/p90 bp: 52/63/88; biggest day move 101 bp

### USDSGD
- data H1: 11383 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~1.2859; median bar spread 0.00001 (0.1 bp), floor 0.00012 (0.9 bp); H1 ATR 0.00099 -> spread/ATR(H1) 0.12; D1 ATR 0.0053 -> spread/ATR(D1) 0.023
- busiest server hours (mean H1 range bp): 15:12.3, 17:11.7, 1:10.9, 16:10.6, 10:9.9
- hours with |t|>2 mean return (bp/hr): 0:-2.12(t=-7.6), 1:+6.80(t=26.4), 16:-0.73(t=-2.3), 18:+0.69(t=2.4), 23:-4.85(t=-23.4)
- weekday total drift bp (Mon..Fri): -352, -89, -69, +121, -266; mean H1 range bp: 8.6, 8.2, 8.5, 8.8, 8.6
- D1 return autocorr lag1 -0.002, lag5 -0.061; variance ratio VR(5) 0.90, VR(20) 0.67 (>1 trend, <1 mean-revert); sign persistence 0.45; H1 autocorr lag1 -0.049; total drift since 2024-10-20 -694 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -63 (n=14), down +20 (n=29)
- weekend gap: median |gap| 7.9 bp, mean -4.3 bp, same-day fill rate 0.93 (n=95)
- D1 ATR p10/p50/p90 bp: 32/41/63; biggest day move 106 bp

### USDCNH
- data H1: 11383 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~7.0709; median bar spread 0.00008 (0.1 bp), floor 0.0004 (0.6 bp); H1 ATR 0.00310 -> spread/ATR(H1) 0.13; D1 ATR 0.0165 -> spread/ATR(D1) 0.024
- busiest server hours (mean H1 range bp): 4:9.0, 3:7.1, 17:6.5, 15:6.4, 10:6.2
- hours with |t|>2 mean return (bp/hr): 0:-1.39(t=-6.5), 1:+1.63(t=9.3), 23:-0.82(t=-6.3)
- weekday total drift bp (Mon..Fri): -399, -127, -89, -259, -97; mean H1 range bp: 5.2, 4.9, 5.1, 5.2, 5.3
- D1 return autocorr lag1 -0.019, lag5 +0.051; variance ratio VR(5) 0.66, VR(20) 0.43 (>1 trend, <1 mean-revert); sign persistence 0.49; H1 autocorr lag1 -0.010; total drift since 2024-10-20 -981 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -33 (n=4), down +0 (n=58)
- weekend gap: median |gap| 5.2 bp, mean -3.5 bp, same-day fill rate 0.84 (n=95)
- D1 ATR p10/p50/p90 bp: 15/23/46; biggest day move 113 bp

### USDPLN
- data H1: 11383 bars 2025-01-02..2026-10-30, 475 days; flat days (range<5% of median) 0 []; gaps>3.5d 0; zero-vol bars 0
- price ~3.6931; median bar spread 0.00145 (3.9 bp), floor 0.0022 (6.0 bp); H1 ATR 0.00572 -> spread/ATR(H1) 0.38; D1 ATR 0.0321 -> spread/ATR(D1) 0.069
- busiest server hours (mean H1 range bp): 17:26.5, 15:26.0, 10:24.1, 16:23.8, 0:23.0
- hours with |t|>2 mean return (bp/hr): 0:-6.86(t=-11.1), 1:+7.82(t=17.8), 4:+1.22(t=3.2), 9:+3.11(t=5.2), 16:-1.56(t=-2.3), 18:+1.86(t=3.2), 23:-4.49(t=-11.3)
- weekday total drift bp (Mon..Fri): -21, -198, +68, +102, -457; mean H1 range bp: 17.6, 16.5, 17.2, 17.5, 17.0
- D1 return autocorr lag1 -0.013, lag5 -0.014; variance ratio VR(5) 0.89, VR(20) 0.75 (>1 trend, <1 mean-revert); sign persistence 0.49; H1 autocorr lag1 -0.028; total drift since 2024-10-20 -589 bp
- D1 20-day breakout follow-through (5d fwd, bp): up -53 (n=23), down -6 (n=31)
- weekend gap: median |gap| 21.6 bp, mean -12.2 bp, same-day fill rate 0.89 (n=95)
- D1 ATR p10/p50/p90 bp: 64/87/126; biggest day move 194 bp

## Results

**2416 scored runs** on 9 symbols x H1/H4/D1 (27 builders, 8 batches:
trend pullback breakout intraday meanrev hours extra openhour), **462
candidates** (best_risk not None and avg_month > 0). Full table of every run:
`results_table.md` (sorted by avg_month); raw rows `results.jsonl`.

By builder (runs / candidates / best avg_month $):

| build_fn | n | cands | best |
|---|---|---|---|
| pwh_pwl_break | 68 | 11 | 166 |
| inside_day_break | 72 | 25 | 149 |
| squeeze_break | 135 | 40 | 141 |
| rsi2_trend | 129 | 25 | 141 |
| tsmom | 84 | 28 | 137 |
| vol_regime_tsmom | 72 | 17 | 134 |
| ema_pullback | 130 | 32 | 131 |
| three_bar_pullback | 90 | 21 | 112 |
| range_compression_break | 136 | 44 | 112 |
| swing_bos | 144 | 39 | 105 |
| weekly_open_follow | 54 | 16 | 93 |
| carry_trend | 34 | 12 | 93 |
| ema_cross_flip | 51 | 21 | 91 |
| donchian_trail | 168 | 43 | 82 |
| spike_follow | 102 | 24 | 55 |
| bb_revert | 143 | 16 | 48 |
| range_box_fade | 72 | 14 | 43 |
| keltner_ride | 34 | 12 | 42 |
| pwh_pwl_fade | 45 | 8 | 39 |
| hour_drift | 261 | 2 | 38 |
| gap_fade | 32 | 6 | 16 |
| session_range_break | 108 | 6 | 11 |
| pdh_pdl_break | 72 | 0 | -9 |
| daily_follow | 36 | 0 | -11 |
| pdh_pdl_fade | 36 | 0 | -12 |
| round_number | 36 | 0 | -26 |
| london_fix_fade | 72 | 0 | -41 |

By symbol:

| symbol | n | cands | best |
|---|---|---|---|
| EURNOK | 280 | 98 | 166 |
| USDCNH | 279 | 86 | 137 |
| USDMXN | 280 | 91 | 88 |
| USDSEK | 279 | 39 | 73 |
| EURSEK | 279 | 30 | 66 |
| USDPLN | 280 | 19 | 65 |
| USDSGD | 279 | 29 | 44 |
| USDZAR | 180 | 18 | 39 |
| USDNOK | 280 | 52 | 37 |

Dead on arrival after costs (0 candidates on any pair): pdh_pdl_break,
pdh_pdl_fade, daily_follow, round_number, london_fix_fade; near-dead: hour_drift
(2/261), session_range_break (6/108), gap_fade (6/32), bb_revert (16/143).

Top 60 runs:

| build_fn | symbol | tf | params_s | best_risk | avg_month | net | max_dd | worst_day | trades | green_months | win_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pwh_pwl_break | EURNOK | D1 | {"max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": null} | 0.02 | 166 | 2,331 | -545 | -237 | 17 | 0.786 | 0.647 |
| inside_day_break | EURNOK | D1 | {"k_nr": 4, "max_hold": 5, "require_inside": true, "tp_r": 1.5} | 0.02 | 149 | 2,092 | -253 | -191 | 14 | 0.643 | 0.857 |
| inside_day_break | EURNOK | D1 | {"k_nr": 7, "max_hold": 5, "require_inside": true, "tp_r": 1.5} | 0.02 | 145 | 2,025 | -279 | -168 | 12 | 0.571 | 0.917 |
| squeeze_break | EURNOK | D1 | {"max_hold": 40, "n": 10, "pct": 0.2, "tp_r": 3.0} | 0.02 | 141 | 1,979 | -381 | -287 | 5 | 0.429 | 0.8 |
| rsi2_trend | EURNOK | H4 | {"hi": 90, "lo": 10, "max_hold": 10, "tp_r": 1.5, "trend_n": 100} | 0.015 | 141 | 1,972 | -534 | -244 | 57 | 0.643 | 0.596 |
| tsmom | USDCNH | D1 | {"max_hold": null, "n": 60, "sl_atr": 2.5, "trail_k": 3.0} | 0.02 | 137 | 3,004 | -405 | -163 | 8 | 0.727 | 0.875 |
| vol_regime_tsmom | USDCNH | D1 | {"n": 60, "regime": "falling", "trail_k": 3.0} | 0.02 | 134 | 2,940 | -391 | -192 | 9 | 0.545 | 0.667 |
| ema_pullback | USDCNH | D1 | {"fast": 20, "max_hold": 60, "slow": 100, "tp_r": 3.0} | 0.02 | 131 | 2,891 | -591 | -209 | 8 | 0.636 | 0.75 |
| squeeze_break | EURNOK | D1 | {"max_hold": 40, "n": 20, "pct": 0.35, "tp_r": 3.0} | 0.02 | 129 | 1,802 | -381 | -287 | 4 | 0.5 | 1 |
| ema_pullback | USDCNH | D1 | {"fast": 20, "slow": 100, "tp_r": null, "trail_k": 2.5} | 0.015 | 128 | 2,825 | -475 | -196 | 11 | 0.591 | 0.727 |
| squeeze_break | EURNOK | D1 | {"max_hold": 40, "n": 10, "pct": 0.35, "tp_r": 3.0} | 0.02 | 128 | 1,788 | -386 | -212 | 7 | 0.357 | 0.714 |
| squeeze_break | EURNOK | D1 | {"max_hold": 40, "n": 20, "pct": 0.2, "tp_r": 3.0} | 0.02 | 117 | 1,635 | -381 | -287 | 3 | 0.429 | 1 |
| inside_day_break | EURNOK | D1 | {"k_nr": 4, "max_hold": 5, "require_inside": false, "tp_r": 3.0} | 0.015 | 115 | 1,610 | -547 | -226 | 30 | 0.571 | 0.633 |
| ema_pullback | USDCNH | D1 | {"fast": 20, "max_hold": 60, "slow": 200, "tp_r": 3.0} | 0.02 | 115 | 2,529 | -591 | -209 | 6 | 0.5 | 0.833 |
| tsmom | USDCNH | D1 | {"max_hold": 30, "n": 60, "sl_atr": 2.5, "trail_k": null} | 0.02 | 114 | 2,518 | -487 | -254 | 16 | 0.682 | 0.75 |
| three_bar_pullback | USDCNH | D1 | {"m": 2, "max_hold": 15, "tp_r": 2.0, "trend_n": 100} | 0.02 | 112 | 2,467 | -499 | -206 | 21 | 0.545 | 0.619 |
| range_compression_break | EURNOK | H4 | {"n": 50, "tp_r": 3.0, "trail_k": null, "vol_pct": 0.3} | 0.0125 | 112 | 1,568 | -542 | -253 | 15 | 0.714 | 0.533 |
| inside_day_break | EURNOK | D1 | {"k_nr": 4, "max_hold": 5, "require_inside": false, "tp_r": 1.5} | 0.015 | 107 | 1,501 | -425 | -233 | 31 | 0.714 | 0.645 |
| ema_pullback | USDCNH | D1 | {"fast": 20, "max_hold": 60, "slow": 100, "tp_r": 1.5} | 0.02 | 106 | 2,326 | -591 | -209 | 12 | 0.5 | 0.833 |
| swing_bos | USDCNH | D1 | {"k": 2, "trail_k": 3.0, "trend_n": 100} | 0.02 | 105 | 2,320 | -330 | -208 | 7 | 0.545 | 0.714 |
| squeeze_break | EURNOK | D1 | {"n": 10, "pct": 0.35, "trail_k": 2.5} | 0.02 | 105 | 1,476 | -443 | -235 | 5 | 0.286 | 0.8 |
| vol_regime_tsmom | USDCNH | D1 | {"n": 60, "regime": "rising", "trail_k": 3.0} | 0.02 | 105 | 2,317 | -395 | -175 | 8 | 0.455 | 0.75 |
| ema_pullback | USDCNH | D1 | {"fast": 20, "max_hold": 60, "slow": 200, "tp_r": 1.5} | 0.02 | 102 | 2,249 | -591 | -209 | 10 | 0.409 | 0.9 |
| tsmom | EURNOK | H4 | {"max_hold": 120, "n": 240, "sl_atr": 2.5, "trail_k": null} | 0.01 | 96 | 1,338 | -490 | -224 | 25 | 0.643 | 0.4 |
| weekly_open_follow | EURNOK | D1 | {"mode": "follow", "sl_atr": 1.5, "weeks": 2} | 0.015 | 93 | 1,304 | -560 | -157 | 55 | 0.571 | 0.582 |
| carry_trend | USDCNH | D1 | {"n": 20, "side": "short", "trend_n": 100} | 0.02 | 93 | 2,038 | -347 | -187 | 7 | 0.5 | 0.714 |
| squeeze_break | EURNOK | D1 | {"n": 10, "pct": 0.2, "trail_k": 2.5} | 0.02 | 92 | 1,284 | -497 | -278 | 5 | 0.286 | 0.8 |
| ema_cross_flip | USDCNH | D1 | {"fast": 10, "sl_atr": 3.0, "slow": 40} | 0.02 | 91 | 1,997 | -555 | -271 | 6 | 0.591 | 0.5 |
| pwh_pwl_break | EURNOK | D1 | {"max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": 100} | 0.02 | 89 | 1,253 | -504 | -207 | 7 | 0.5 | 0.714 |
| pwh_pwl_break | USDCNH | D1 | {"trail_k": 2.5, "trend_n": 100} | 0.015 | 89 | 1,965 | -483 | -187 | 10 | 0.545 | 0.5 |
| ema_pullback | USDMXN | D1 | {"fast": 20, "max_hold": 60, "slow": 100, "tp_r": 3.0} | 0.02 | 88 | 1,940 | -553 | -197 | 10 | 0.455 | 0.6 |
| swing_bos | EURNOK | D1 | {"k": 2, "max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": null} | 0.02 | 88 | 1,233 | -531 | -226 | 13 | 0.5 | 0.538 |
| squeeze_break | USDCNH | D1 | {"max_hold": 40, "n": 20, "pct": 0.2, "tp_r": 3.0} | 0.02 | 87 | 1,922 | -400 | -205 | 10 | 0.5 | 0.6 |
| inside_day_break | EURNOK | D1 | {"k_nr": 7, "max_hold": 5, "require_inside": false, "tp_r": 1.5} | 0.015 | 86 | 1,201 | -289 | -233 | 22 | 0.571 | 0.636 |
| three_bar_pullback | EURNOK | H4 | {"m": 3, "max_hold": 15, "tp_r": 2.0, "trend_n": 50} | 0.01 | 85 | 1,186 | -569 | -286 | 65 | 0.571 | 0.585 |
| donchian_trail | USDCNH | D1 | {"n": 55, "sl_atr": 2.0, "trail_k": 4.0} | 0.02 | 82 | 1,814 | -558 | -297 | 5 | 0.455 | 0.8 |
| ema_cross_flip | EURNOK | D1 | {"fast": 10, "sl_atr": 3.0, "slow": 40} | 0.02 | 81 | 1,131 | -383 | -226 | 3 | 0.5 | 0.667 |
| inside_day_break | EURNOK | D1 | {"k_nr": 4, "max_hold": 5, "require_inside": true, "tp_r": 3.0} | 0.015 | 80 | 1,125 | -504 | -255 | 14 | 0.5 | 0.714 |
| donchian_trail | USDCNH | D1 | {"n": 55, "sl_atr": 2.0, "trail_k": 2.5} | 0.02 | 80 | 1,767 | -481 | -187 | 7 | 0.409 | 0.429 |
| range_compression_break | EURNOK | H4 | {"n": 50, "tp_r": 3.0, "trail_k": null, "vol_pct": 0.5} | 0.01 | 79 | 1,100 | -554 | -208 | 20 | 0.714 | 0.45 |
| inside_day_break | EURNOK | D1 | {"k_nr": 7, "max_hold": 5, "require_inside": true, "tp_r": 3.0} | 0.015 | 78 | 1,095 | -504 | -255 | 12 | 0.429 | 0.75 |
| ema_pullback | EURNOK | D1 | {"fast": 20, "max_hold": 60, "slow": 200, "tp_r": 3.0} | 0.02 | 78 | 1,092 | -221 | -181 | 2 | 0.214 | 1 |
| inside_day_break | EURNOK | D1 | {"k_nr": 7, "max_hold": 5, "require_inside": false, "tp_r": 3.0} | 0.015 | 77 | 1,076 | -504 | -255 | 21 | 0.429 | 0.571 |
| vol_regime_tsmom | EURNOK | D1 | {"n": 20, "regime": "falling", "trail_k": 3.0} | 0.02 | 77 | 1,072 | -478 | -208 | 8 | 0.5 | 0.625 |
| ema_cross_flip | EURNOK | D1 | {"fast": 5, "sl_atr": 3.0, "slow": 30} | 0.02 | 76 | 1,065 | -267 | -198 | 7 | 0.643 | 0.714 |
| squeeze_break | USDCNH | D1 | {"n": 20, "pct": 0.2, "trail_k": 2.5} | 0.015 | 75 | 1,648 | -477 | -183 | 9 | 0.5 | 0.444 |
| pwh_pwl_break | EURNOK | D1 | {"trail_k": 2.5, "trend_n": 100} | 0.02 | 73 | 1,028 | -351 | -207 | 6 | 0.5 | 0.667 |
| weekly_open_follow | USDSEK | D1 | {"mode": "fade", "sl_atr": 1.5, "weeks": 2} | 0.015 | 73 | 1,598 | -468 | -147 | 92 | 0.727 | 0.576 |
| ema_pullback | EURNOK | D1 | {"fast": 20, "slow": 100, "tp_r": null, "trail_k": 2.5} | 0.02 | 71 | 1,000 | -374 | -157 | 5 | 0.286 | 0.6 |
| pwh_pwl_break | USDCNH | D1 | {"max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": 100} | 0.015 | 70 | 1,539 | -527 | -166 | 17 | 0.5 | 0.588 |
| range_compression_break | USDCNH | D1 | {"n": 20, "trail_k": 3.0, "vol_pct": 0.5} | 0.02 | 68 | 1,494 | -554 | -187 | 11 | 0.455 | 0.455 |
| ema_cross_flip | EURNOK | H4 | {"fast": 5, "sl_atr": 3.0, "slow": 30} | 0.0125 | 67 | 940 | -520 | -175 | 70 | 0.571 | 0.314 |
| pwh_pwl_break | EURNOK | D1 | {"trail_k": 2.5, "trend_n": null} | 0.015 | 66 | 923 | -455 | -173 | 14 | 0.571 | 0.5 |
| squeeze_break | USDCNH | D1 | {"max_hold": 40, "n": 20, "pct": 0.35, "tp_r": 3.0} | 0.015 | 66 | 1,447 | -472 | -154 | 14 | 0.5 | 0.5 |
| rsi2_trend | EURSEK | H4 | {"hi": 90, "lo": 10, "max_hold": 10, "tp_r": 1.5, "trend_n": 100} | 0.0125 | 66 | 918 | -584 | -214 | 66 | 0.5 | 0.591 |
| swing_bos | USDCNH | D1 | {"k": 4, "trail_k": 3.0, "trend_n": 100} | 0.02 | 65 | 1,433 | -240 | -142 | 7 | 0.5 | 0.714 |
| three_bar_pullback | USDCNH | D1 | {"m": 3, "max_hold": 15, "tp_r": 2.0, "trend_n": 100} | 0.015 | 65 | 1,430 | -573 | -154 | 16 | 0.364 | 0.562 |
| weekly_open_follow | USDPLN | D1 | {"mode": "fade", "sl_atr": 1.5, "weeks": 2} | 0.015 | 65 | 1,420 | -549 | -176 | 92 | 0.682 | 0.598 |
| swing_bos | USDCNH | D1 | {"k": 4, "max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": 100} | 0.02 | 61 | 1,336 | -300 | -138 | 9 | 0.455 | 0.778 |
| vol_regime_tsmom | USDCNH | D1 | {"n": 20, "regime": "rising", "trail_k": 3.0} | 0.02 | 58 | 1,267 | -469 | -175 | 9 | 0.364 | 0.333 |

## Returned candidates (8, distinct idea or market)

| name | symbol | tf | builder | params | risk | avg/mo | net | maxDD | worst day | trades | green | exit | causal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exo_eurnok_pwhl_break | EURNOK | D1 | build_pwh_pwl_break | `{"max_hold": 30, "tp_r": 2.0, "trail_k": null, "trend_n": null}` | 2% | $166 | $2,331 | $-545 | $-237 | 17 | 79% | tp_or_time | ok |
| exo_eurnok_inside_day | EURNOK | D1 | build_inside_day_break | `{"k_nr": 4, "max_hold": 5, "require_inside": true, "tp_r": 1.5}` | 2% | $149 | $2,092 | $-253 | $-191 | 14 | 64% | tp_or_time | ok |
| exo_usdcnh_tsmom60 | USDCNH | D1 | build_tsmom | `{"max_hold": null, "n": 60, "sl_atr": 2.5, "trail_k": 3.0}` | 2% | $137 | $3,004 | $-405 | $-163 | 8 | 73% | trail | ok |
| exo_eurnok_rsi2_h4 | EURNOK | H4 | build_rsi2_trend | `{"hi": 90, "lo": 10, "max_hold": 10, "tp_r": 1.5, "trend_n": 100}` | 1.5% | $141 | $1,972 | $-534 | $-244 | 57 | 64% | tp_or_time | ok |
| exo_usdcnh_3bar_pullback | USDCNH | D1 | build_three_bar_pullback | `{"m": 2, "max_hold": 15, "tp_r": 2.0, "trend_n": 100}` | 2% | $112 | $2,467 | $-499 | $-206 | 21 | 55% | tp_or_time | ok |
| exo_usdmxn_ema_pullback | USDMXN | D1 | build_ema_pullback | `{"fast": 20, "max_hold": 60, "slow": 100, "tp_r": 3.0}` | 2% | $88 | $1,940 | $-553 | $-197 | 10 | 46% | tp_or_time | ok |
| exo_usdsek_weekly_fade | USDSEK | D1 | build_weekly_open_follow | `{"mode": "fade", "sl_atr": 1.5, "weeks": 2}` | 1.5% | $73 | $1,598 | $-468 | $-148 | 92 | 73% | time | ok |
| exo_usdzar_rsi2_d1 | USDZAR | D1 | build_rsi2_trend | `{"hi": 75, "lo": 25, "max_hold": 10, "trend_n": 200}` | 2% | $39 | $851 | $-339 | $-187 | 27 | 46% | rsi_or_time | ok |

Why these eight and not the raw top of the table: the top of the table is five
EURNOK D1 breakout variants and six USDCNH D1 trend variants, most with 3-9
trades. I took the best of each idea family per market, preferred the variant
with more trades when avg_month was close (EURNOK H4 rsi2 with 57 trades over
the 4-trade squeeze_break; USDCNH three_bar_pullback with 21 trades alongside
the 8-trade tsmom), and kept one mean-reversion idea (USDSEK weekly fade, 92
trades) because the study says these pairs mean-revert.

Caveats the owner should see:

* Samples: 8-27 trades on six of the eight; only the EURNOK H4 rsi2 (57) and
  USDSEK weekly fade (92) have a sample worth the name. EURNOK is 13 months of
  data in total.
* The USDCNH results are one long USD down-trend (-981 bp) with the PBoC
  leaning the same way; if the fix regime flips the tsmom / pullback shorts
  flip with it (they are two-sided rules, so they would follow, but the
  smoothness would not).
* Swap is not modelled. Long USDZAR / USDMXN / USDPLN carries a negative swap
  that would take 1-3 bp a day off any long held for weeks (the D1 trend
  entries); short USDCNH swap is roughly flat.
* Costs used: floors above (IC raw x1.3), $14/lot commission, 0.1 pip slip.
  USDPLN / EURSEK / EURNOK are the pairs where a FundedNext spread 50% wider
  than assumed would erase the H4 candidates.

## Status

Complete 2026-10-30 ~12:00 server-local. Files: `strategies.py` (27 builders),
`batches.py` (8 batches), `run.py`, `study.py` -> `study.md`, `table.py` ->
`results_table.md`, `results.jsonl`, `lookahead.jsonl`, `candidates.json`,
run logs `_log_*.txt`.

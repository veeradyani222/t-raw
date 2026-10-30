# Round 3 search: US indices (US30 / US500 / USTEC / US2000)

Group `us_indices`. From-scratch, per-market search, no statistical gates (only the look-ahead
check and the 300/800 rule). Judge = `research/prop/harness.py`, `PROP_OOS=1`, scoring window
2024-10-20 .. 2026-10-19 (last bar in the files). All runs: `python research/search3/us_indices/run.py all 2`
(Pool(2)); results in `results.jsonl`, this file's table from `make_table.py all`.

Files: `study.py` (market study + data quality, output in `study_out.txt`), `strategies.py`
(27 builders, `build_<name>(df, **params)`), `run.py` (sweep + look-ahead check), `make_table.py`.

## 0. Data quality

Files `data/search/{us30,us500,ustec}-{m30,h1,h4,d1}.csv` (server time EET, cash 16:30-23:00).
US30/US500 H1-D1 from 2015-01-02, M30 from 2018-02 (100k-bar cap). USTEC from 2022-07-06 only.
**US2000: no file in data/search at any time during this session** (checked 11:13, 11:20, and
again at the end; two fetch attempts with `research.data_fetch US2000` failed with MT5
"IPC initialize failed" because another group's fetch (JP225/HK50/...) held the terminal pipe).
US2000 is therefore not scored; every builder handles it (cost floor 0.5 pts set in
`strategies.py`, added to `H.INDICES`, ROUND grid 100/50) once the file exists.

Checks per file: flat days (daily range < 5% of the rolling median), gaps > 72h, zero-volume
bars, OHLC-equal bars.

| sym | tf | bars | first | flat days | gaps>72h | zero vol | ohlc-equal bars |
|---|---|---|---|---|---|---|---|
| US30 | M30 | 100000 | 2018-02-22 | 8 | 15 | 0 | 99 |
| US30 | H1 | 62891 | 2015-01-02 | 8 | 23 | 0 | 324 |
| US30 | H4 | 16600 | 2015-01-02 | 8 | 23 | 0 | 11 |
| US30 | D1 | 3012 | 2015-01-02 | 8 | 23 | 0 | 2 |
| US500 | M30 | 100000 | 2018-02-23 | 9 | 15 | 0 | 154 |
| US500 | H1 | 62920 | 2015-01-02 | 9 | 23 | 0 | 322 |
| US500 | H4 | 16602 | 2015-01-02 | 9 | 23 | 0 | 9 |
| US500 | D1 | 3011 | 2015-01-02 | 9 | 23 | 0 | 1 |
| USTEC | M30 | 48477 | 2022-07-06 | 5 | 9 | 0 | 28 |
| USTEC | H1 | 24268 | 2022-07-06 | 5 | 9 | 0 | 25 |
| USTEC | H4 | 6377 | 2022-07-06 | 5 | 9 | 0 | 0 |
| USTEC | D1 | 1070 | 2022-07-06 | 5 | 9 | 0 | 0 |

**Bar-level stale stretches (found in this session, second pass).** The daily check above misses
days where the feed froze for 5-20 hours inside an otherwise normal day (e.g. USTEC H1
2024-11-05 20:00 .. 2024-11-06 15:00: 20 bars with a 0.38-point range, then one 543-point bar).
An early version of the H1 dip builder earned 95% of its profit on those fake fills (R of 100-207
on tiny ATR stops), which is how it was caught. `strategies.P` now flags a bar as stale when its
14-bar ATR < 20% of the rolling 500-bar median, or the last 6 bars share one high and low, or the
range is 0; the whole day and the following day are excluded from entries on M30/H1/H4. Inside the
scoring window that removes (stale bars / stale days / excluded days incl. next-day rule):
US30 M30 1215/46/56, H1 483/40/51, H4 47/14/21; US500 M30 1193/43/52, H1 481/40/51, H4 49/12/20;
USTEC M30 1169/44/54, H1 476/41/52, H4 36/9/18. Nearly all between 2024-10-21 and 2025-01-07
(plus 2025-11-28, the Thanksgiving half day), i.e. about 10% of the 2-year window is dropped for
intraday strategies. D1 bars are not affected (daily ranges stay normal). Open positions that
straddle a frozen stretch can still get a stale fill; entries cannot. The v1 results before this
fix are kept in `results_v1_prestale.jsonl` for comparison; the table below is the re-run.

Flat / stale-feed days (shared by all three symbols, the broker feed was stuck): 2018-04-07/08,
2024-10-30, 2024-11-14, 2024-11-15, 2024-12-03, 2024-12-31, 2025-01-01/02/03. Every builder
excludes entries on those days AND the following day (prior-day levels would be stale); the
exclusion list is `strategies.EXCLUDE_DAYS`. The gaps > 72h are all Good Friday / Christmas /
New Year holiday weekends (normal). No zero-volume bars. OHLC-equal bars are thin Sunday-open
and holiday half-session bars; they are left in (they carry no entries because ATR/range gates
reject them).

## 1. Market study (study.py, 2022-01 .. 2026-10, H1 and D1)

Hour-of-day (server time EET, bar close-to-close, bp): the only hours with a visible positive
mean are 16:00 (bar closing at the 17:00, i.e. the first cash half hour, +1.2..1.6 bp, t 1.3-1.7),
20:00 (+1.2..1.8 bp, t 1.3-1.7) and 06:00 (+0.3..0.6 bp but t 1.5-2.3 on a tiny std; this is the
"overnight drift" hour before the European open, matching Boyarchenko-Larsen-Whelan). 17:00 is
negative (-0.5..-0.7 bp): the second cash half hour gives back part of the open.

Sessions (bp/day): overnight 0.2 (US30) / 1.4 (US500) / 4.2 (USTEC), cash 3.3-5.8, first hour
1.8, last hour 0.5-0.6. The cash session carries more than the overnight in this window for
US30/US500 (the academic overnight premium is weaker in 2022-26 than in the 1998-2019 sample).

Weekday (D1 close-to-close, bp): Monday 10-29, Wednesday 4-15, Thursday -0.3..-1.8, Friday -2..6.
Monday is the strongest day for all three (Friday close -> Monday close), so the weekday idea
is "long Friday close, out Monday close".

Gaps: |gap| > 0.2% fills the same day only 45-48% of the time; down-gaps are followed by a
positive cash session (+7 bp mean) while up-gaps are flat/negative. So: fade down-gaps, do not
chase up-gaps.

Open: first-hour direction continues to the close on 51-53% of days (corr 0.05-0.11, weak).
Close above the 30-min opening range high 37-42% of days, below the low 31-34%; OR30 is 38-44%
of the day range (median). So ORB has a small edge for longs only.

Persistence: D1 lag-1 autocorrelation -0.13 (US30, US500), -0.06 (USTEC); variance ratios
< 1 at 2-20 days (0.80-0.94) => daily mean reversion. H1 variance ratios ~1.0 (random walk
intraday). Mean reversion at D1 extremes: close < 20-day low -> next-day +34..38 bp, 5-day
+37..70 bp (USTEC +9 / +40); 3 down closes -> +12..30 bp next day, +60..127 bp over 5 days; above
SMA200 adds nothing to the 1-day number but keeps the 5-day number positive.

Turn of month: last day (-1) +13..26 bp, first day +7..13 bp (US30/US500), USTEC -15 bp on day 1
but +29 on day -2. OpEx week: -3.5 bp/day vs +6-9 the week after and +6-12 other weeks (OpEx
weeks are the weak ones). FOMC: day before +10..12 bp (US30/US500) = Lucca-Moench pre-FOMC drift,
USTEC day-before -13 bp; FOMC day itself mixed; day after +3..31 bp. High-vol regime (ATR14 >
1.3x 100-day median) has higher 5-day forward returns (13-47 bp) than low vol.

## 2. What practitioners / papers use here (sources)

- Overnight drift: Boyarchenko, Larsen, Whelan, "The Overnight Drift", NY Fed Staff Report 917
  (close-to-open carries ~3.1% of the 4.5%/yr S&P close-to-close 1998-2019, concentrated 2-3am ET)
  https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf ;
  Elm Wealth "Night shift" https://elmwealth.com/night-shift/
  -> builders `overnight` (long 23:00 close -> 16:30 open, variants after down days / with trend)
  and `hour_window` (5-6, 9-10 etc. server hours).
- Intraday momentum, first half-hour predicts last half-hour: Gao, Han, Li, Zhou, "Market intraday
  momentum", JFE 2018 (abstract/replications: https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/ ,
  https://www.quantconnect.com/learning/articles/investment-strategy-library/intraday-etf-momentum)
  -> builder `first_last` (sign of 16:30->17:00 move vs yesterday close, trade the last half hour).
- Pre-FOMC announcement drift: Lucca & Moench, J. Finance 2015 (~49 bp in the 24h before the
  statement) https://libertystreeteconomics.newyorkfed.org/?p=1112 -> builder `fomc`
  (pre_drift long from the day-before close / 16:00 / 20:00 until 20:00 FOMC day; post_mom / post_fade).
- Turn of the month: Lakonishok & Smidt 1988; Quantpedia "Turn of the month in equity indexes"
  https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes ; Atlanta Fed WP 2000-11
  (effect weakened after 1990, concentrated on day 1) -> builder `tom`.
- Monday / weekend effect: fading since the 1990s, recent samples show Monday as the strongest
  day (Benzinga 2023, https://benzinga.com/etfs/broad-u-s-equity-etfs/23/11/35590363/the-end-of-monday-blues-new-data-reveals-shift-in-stock-market-patterns);
  our own study agrees -> builder `weekday`.
- Gap fills: ES fills ~60-70% of small opening gaps, bigger gaps fill less, 1%+ up-gaps tend to
  continue (edgeful https://www.edgeful.com/blog/posts/half-gaps-vs-full-gaps , proptradingvibes
  https://proptradingvibes.com/blog/gap-trading-strategy , tradethatswing
  https://tradethatswing.com/sp-500-spy-es-gap-fill-strategy-and-statistics/). Our CFD data (gap =
  16:30 cash open vs yesterday 23:00 close) fills only 45-48% because the CFD trades 23h and most
  of the futures gap is already in the overnight bars -> builders `gap_struct` (gap inside /
  outside yesterday's range, fade vs continue) and `overnight`.
- Opening range breakout: 30-min ORB vendor stats 55-60% win rate on ES
  (https://proptradingvibes.com/blog/opening-range-breakout-strategy ,
  https://therighttrader.com/learn/trading-strategies/opening-range-breakout) -> builder `orb`
  (1 or 2 M30 bars, stop at range mid / far side, optional relative-volume filter, flat at the close).
- Mean reversion at daily extremes, Connors: RSI(2) < 5/10 above SMA200, exit above SMA5/10
  (https://backtrex.com/en/backtests/connors-rsi-2-sp-500); Double 7s (buy 7-day low close, sell
  7-day high close, above SMA200; https://strategyquant.com/blog/larry-connors-double-7-strategy-tested-on-spy-and-8-other-markets/);
  consecutive down closes -> builders `rsi2`, `double7s`, `down_streak`, `capitulation`.
- Internal bar strength: IBS = (C-L)/(H-L) < 0.2-0.25 buy at close, exit on IBS > 0.8 / first
  up close (quantifiedstrategies https://quantifiedstrategies.substack.com/p/ibs-internal-bar-strength-trading-64c ,
  abouttrading https://abouttrading.substack.com/p/back-testing-the-internal-bar-strength) -> builder `ibs`.
- Market structure (ICT-style liquidity sweeps of the prior-day low, prior-week high/low breaks,
  round numbers, NR7 / inside-day breakouts, Asia-range breakout): common retail rule sets; we test
  the actual mechanics -> builders `pdl_sweep`, `prev_week`, `pdh_break`, `round`, `nr_break`,
  `asia_break`.
- Turtle soup (Connors & Raschke, Street Smarts: fade a 20-day low break that reverses) -> `turtle_soup`.
- Trend following: 20/50-day channel breakouts with chandelier trail; H4 EMA pullbacks;
  H4 N-bar-low dips in a daily uptrend -> `d1_breakout`, `h4_pullback`, `h4_dip`.
- Late-day dip / power hour: afternoon weakness reverting into the close -> `late_dip`,
  `hour_window` (19->21, 20->22 etc.), `first_hour` (continuation / fade of the first cash hour).

## 3. Costs used

Harness defaults for US30 (spread floor 3.0), US500 (0.6), USTEC (1.8), no commission (indices).
Added in `strategies.py`: `H.SPREAD_FLOOR["US2000"] = 0.5`, `H.INDICES.add("US2000")`. Slippage
per the harness `_pip` (1.0 point for indices). Contract sizes from `data/search/symbol_specs.json`.

## 4. Look-ahead check

`run.py:lookahead_check`: for 5 random cut points k in [n/3, n-2], rebuild on `df.iloc[:k]`
(attrs re-attached) and compare every Entry at index < k (side, sl, tp, max_hold, exit_hour).
Every scored run passed (`causal_ok` column). Manage callbacks only read arrays at index <= j.

## 5. Ideas tested (27 builders)

| # | builder | tf | idea |
|---|---|---|---|
| 1 | tom | D1 | turn of month long (k days before month end -> day k of new month) |
| 2 | opex | D1 | OpEx week short / long the week after |
| 3 | fomc | H1/M30 | pre-FOMC drift long; post-FOMC momentum / fade |
| 4 | overnight | M30/H1 | long 23:00 close -> 16:30 open (after down days / with trend / by weekday) |
| 5 | orb | M30 | opening range breakout (1-2 bars), rvol filter, mid/far stop |
| 6 | hour_window | H1 | fixed hour windows (19->21 etc.), conditional on day-so-far |
| 7 | pdl_sweep | M30/H1 | prior-day-low sweep and reclaim -> long to pd mid/high |
| 8 | turtle_soup | D1 | fade a 10/20-day low break that closes back inside |
| 9 | nr_break | M30 | NR7 / inside-day breakout in cash hours |
| 10 | rsi2 | D1 | Connors RSI(2) |
| 11 | down_streak | D1 | k consecutive down closes above SMA200 |
| 12 | weekday | D1 | Friday close -> Monday close etc. |
| 13 | round | M30 | round-number bounce / break |
| 14 | prev_week | H1/H4 | prior-week high/low break or fade |
| 15 | first_last | M30 | first half hour sign -> last half hour (Gao et al.) |
| 16 | gap_struct | M30 | cash-open gap inside/outside yesterday's range, fade/continue |
| 17 | h4_pullback | H1/H4 | EMA20/50 pullback with trend |
| 18 | asia_break | H1 | Asia-range breakout into London |
| 19 | capitulation | D1 | big down day on high volume -> long |
| 20 | first_hour | M30 | first cash hour continuation / fade |
| 21 | pdh_break | M30/H1 | prior-day high/low break continuation (new this session) |
| 22 | ibs | D1 | internal bar strength (new) |
| 23 | double7s | D1 | Connors Double 7s (new) |
| 24 | h4_dip | H4/H1 | N-bar low dip in daily uptrend, exit at N-bar high (new) |
| 25 | late_dip | M30/H1 | afternoon dip (20:00) long into the close (new) |
| 26 | d1_breakout | D1 | 20/50-day breakout, chandelier trail, optional squeeze (new) |
| 27 | (variants) | | trend gates (`trend="with"`: yesterday close > daily SMA50), tp/sl variants |

## 6. Best candidates (distinct ideas / markets, ranked by avg $/month at best_risk)

| # | name | sym | tf | best risk | $/mo | net | maxDD | worst day | trades | exit | idea |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | down_streak:k2_exit_rulehold_trend_reqTrue | US500 | D1 | 2.00% | 134 | 3212 | -557 | -248 | 52 | time (5 daily bars) or 2xATR stop | two consecutive lower closes above SMA200 -> long at close, out after 5 days (buy-the-dip in an uptrend; D1 lag-1 autocorr -0.13) |
| 2 | ibs:lo0.2_hi0.8_sl_atr1.5_max_hold5 | US30 | D1 | 2.00% | 107 | 2567 | -434 | -182 | 58 | manage: close with IBS>0.8, else 5 days or 1.5xATR stop | internal bar strength < 0.2 above SMA200 -> long at close (close near the day's low mean-reverts) |
| 3 | rsi2:thresh10_exit_sma5 | US500 | D1 | 2.00% | 106 | 2550 | -203 | -145 | 25 | manage: first close above SMA5, else 10 days or 2xATR stop | Connors RSI(2) < 10 above SMA200 -> long at close |
| 4 | weekday:enter_dow4_hold1_trendwith | USTEC | D1 | 2.00% | 96 | 2295 | -253 | -162 | 64 | time (1 daily bar = Monday close) or 1.5xATR stop | Friday close -> Monday close when yesterday's close > daily SMA50 (Monday is the strongest weekday, +29 bp on USTEC) |
| 5 | turtle_soup:n20_modelong_hold3_exit_rulehold_sl_pad0.5 | US30 | D1 | 1.50% | 76 | 1827 | -328 | -137 | 20 | time (3 days) or stop 0.5xATR below the 20-day low | turtle soup: a break below the 20-day low that closes back above it -> long (failed breakdown) |
| 6 | prev_week:modebreak_stopmid_sideslong | USTEC | H1 | 1.50% | 76 | 1818 | -460 | -238 | 46 | opposite-signal flip / stop at the mid between the prior-week high and the week's low | first H1 close above the prior week's high -> long continuation (weekly structure break) |
| 7 | overnight:sl_atr1.5_afterany_trendwith | US500 | M30 | 2.00% | 67 | 1608 | -560 | -202 | 295 | exit at the 16:00 bar (cash open), 1.5x daily-ATR stop | overnight drift: long at the 23:00 cash close, flat at the 16:30 cash open, only when yesterday's close > daily SMA50 |
| 8 | round:stepbig_modebounce_tp_rNone | USTEC | M30 | 0.75% | 59 | 1418 | -487 | -75 | 105 | flat at the 22:30 bar (cash close), 0.4x daily-ATR stop | round-number bounce: bar touches a 1000-point level from above and closes back above it in cash hours -> long (mirror short) |

Notes on the ranking: the D1 mean-reversion family (down_streak, ibs, rsi2, double7s, turtle_soup)
dominates on US500/US30, consistent with the study (negative lag-1 autocorrelation, variance ratios
< 1). Intraday structure ideas (ORB, gap fades, first/last half hour, NR7, PDL sweeps, pdh_break,
late_dip, first_hour, asia_break) are mostly flat-to-negative after the 1-3 point spreads; the only
intraday ideas that survive are overnight drift (US500/USTEC M30), round-number bounces (USTEC) and
prior-week-high continuation (USTEC H1/H4). FOMC, turn-of-month and OpEx ideas have too few trades
(12-30) to rank. US2000 could not be scored (no data file, see section 0).

Not in the table: `h4_dip:n12_exit_rulenhigh USTEC H1` was $551/mo before the stale-feed fix and
$60/mo after it; it is the reason the bar-level stale detector exists.

## 7. All scored runs (837; best_risk = highest risk with worst day > -3% and max DD > -6%)

scored runs: 837; candidates (safe risk & avg_month>0): 432; causal failures: 0

| name | sym | tf | risk | $/mo | net | green | maxDD | worst day | trades | win | causal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| down_streak:k2_exit_rulehold_trend_reqTrue | US500 | D1 | 2.00% | 134 | 3212 | 62% | -557 | -248 | 52 | 65% | ok |
| ibs:lo0.2_hi0.8_sl_atr1.5_max_hold5 | US30 | D1 | 2.00% | 107 | 2567 | 67% | -434 | -182 | 58 | 72% | ok |
| rsi2:thresh10_exit_sma5 | US500 | D1 | 2.00% | 106 | 2550 | 62% | -203 | -145 | 25 | 92% | ok |
| ibs:lo0.3_hi0.7 | US500 | D1 | 2.00% | 97 | 2325 | 62% | -502 | -194 | 69 | 67% | ok |
| weekday:enter_dow4_hold1_trendwith | USTEC | D1 | 2.00% | 96 | 2295 | 58% | -253 | -162 | 64 | 67% | ok |
| weekday:enter_dow4_hold1 | USTEC | D1 | 2.00% | 94 | 2252 | 67% | -540 | -162 | 92 | 64% | ok |
| ibs:lo0.1_hi0.7 | US500 | D1 | 2.00% | 87 | 2097 | 50% | -285 | -165 | 29 | 72% | ok |
| down_streak:k2_exit_rulehold_trend_reqTrue | USTEC | D1 | 2.00% | 87 | 2097 | 67% | -487 | -206 | 48 | 62% | ok |
| ibs:lo0.2_hi0.7 | US500 | D1 | 2.00% | 87 | 2094 | 67% | -351 | -194 | 47 | 74% | ok |
| rsi2:thresh10_exit_sma10 | US500 | D1 | 2.00% | 86 | 2074 | 58% | -492 | -196 | 24 | 75% | ok |
| ibs:lo0.2_hi0.8 | US500 | D1 | 2.00% | 84 | 2022 | 62% | -523 | -243 | 46 | 72% | ok |
| ibs:lo0.1_hi0.8 | US500 | D1 | 2.00% | 77 | 1859 | 46% | -285 | -243 | 28 | 68% | ok |
| turtle_soup:n20_modelong_hold3_exit_rulehold_sl_pad0.5 | US30 | D1 | 1.50% | 76 | 1827 | 46% | -328 | -137 | 20 | 65% | ok |
| prev_week:modebreak_stopmid_sideslong | USTEC | H1 | 1.50% | 76 | 1818 | 46% | -460 | -237 | 46 | 50% | ok |
| double7s:n7 | US500 | D1 | 2.00% | 75 | 1806 | 58% | -556 | -199 | 29 | 72% | ok |
| ibs:lo0.2_hi0.8_trend_reqFalse | US30 | D1 | 2.00% | 73 | 1764 | 71% | -449 | -173 | 62 | 76% | ok |
| ibs:lo0.2_hi0.8_sl_atr1.5_max_hold5 | USTEC | D1 | 2.00% | 72 | 1723 | 58% | -408 | -240 | 54 | 69% | ok |
| double7s:n7_max_hold8 | US500 | D1 | 2.00% | 71 | 1700 | 58% | -546 | -199 | 30 | 67% | ok |
| double7s:n10 | US500 | D1 | 2.00% | 71 | 1699 | 62% | -417 | -238 | 22 | 77% | ok |
| down_streak:k3_exit_rulehold_trend_reqTrue | US500 | D1 | 2.00% | 69 | 1652 | 42% | -557 | -164 | 24 | 58% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | USTEC | H4 | 1.50% | 69 | 1649 | 38% | -566 | -290 | 44 | 52% | ok |
| down_streak:k2_exit_rulepdh_trend_reqTrue | US500 | D1 | 2.00% | 67 | 1609 | 58% | -526 | -248 | 55 | 71% | ok |
| overnight:sl_atr1.5_afterany_trendwith | US500 | M30 | 2.00% | 67 | 1608 | 54% | -560 | -202 | 295 | 58% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | USTEC | H1 | 1.50% | 67 | 1599 | 42% | -563 | -219 | 43 | 49% | ok |
| weekday:enter_dow4_hold1_sl_atr1.0 | US500 | D1 | 1.25% | 66 | 1581 | 50% | -582 | -161 | 93 | 60% | ok |
| ibs:lo0.2_hi0.8 | US30 | D1 | 2.00% | 65 | 1572 | 58% | -449 | -173 | 53 | 75% | ok |
| overnight:sl_atr1.5_afterany_trendwith | USTEC | M30 | 2.00% | 65 | 1564 | 42% | -589 | -178 | 266 | 56% | ok |
| rsi2:thresh5_exit_sma5 | US500 | D1 | 2.00% | 63 | 1515 | 38% | -246 | -145 | 11 | 91% | ok |
| down_streak:k3_exit_rulehold_hold10_trend_reqTrue | US500 | D1 | 2.00% | 63 | 1514 | 58% | -557 | -265 | 22 | 64% | ok |
| rsi2:thresh10_exit_sma5_sl_atr3.0 | US500 | D1 | 2.00% | 63 | 1508 | 62% | -267 | -127 | 24 | 92% | ok |
| down_streak:k2_exit_rulehold_trend_reqFalse | US500 | D1 | 1.00% | 63 | 1504 | 62% | -468 | -119 | 59 | 64% | ok |
| ibs:lo0.2_hi0.8_trend_reqFalse | US500 | D1 | 1.50% | 62 | 1481 | 62% | -496 | -187 | 55 | 69% | ok |
| ibs:lo0.3_hi0.8 | USTEC | D1 | 2.00% | 61 | 1475 | 58% | -367 | -168 | 68 | 71% | ok |
| round:stepbig_modebounce_tp_r1.5_trendwith | USTEC | M30 | 1.50% | 61 | 1462 | 46% | -599 | -149 | 62 | 63% | ok |
| prev_week:modebreak_stopmid_sideslong | USTEC | H4 | 1.25% | 61 | 1461 | 42% | -531 | -249 | 47 | 53% | ok |
| ibs:lo0.3_hi0.8 | US500 | D1 | 1.50% | 60 | 1445 | 58% | -472 | -187 | 63 | 67% | ok |
| overnight:sl_atr1.5_afterdown_trendwith | USTEC | M30 | 2.00% | 60 | 1443 | 46% | -536 | -178 | 123 | 58% | ok |
| h4_dip:n12_exit_rulenhigh | USTEC | H1 | 0.25% | 60 | 1440 | 58% | -345 | -135 | 429 | 41% | ok |
| ibs:lo0.2_hi0.7 | USTEC | D1 | 2.00% | 59 | 1419 | 75% | -264 | -180 | 53 | 75% | ok |
| weekday:enter_dow4_hold1 | US500 | D1 | 1.50% | 59 | 1419 | 62% | -554 | -149 | 93 | 62% | ok |
| round:stepbig_modebounce_tp_rNone | USTEC | M30 | 0.75% | 59 | 1418 | 58% | -487 | -75 | 105 | 60% | ok |
| weekday:enter_dow4_hold1_trendwith | US500 | D1 | 2.00% | 58 | 1403 | 58% | -417 | -199 | 66 | 62% | ok |
| h4_dip:n8_exit_rulehold | USTEC | H4 | 0.50% | 57 | 1375 | 54% | -469 | -172 | 125 | 36% | ok |
| h4_dip:n6_exit_rulenhigh | USTEC | H4 | 0.50% | 57 | 1367 | 54% | -591 | -158 | 175 | 45% | ok |
| ibs:lo0.15_hi0.9_sma_trend100 | US500 | D1 | 1.50% | 57 | 1364 | 54% | -455 | -187 | 32 | 62% | ok |
| overnight:sl_atr0.8 | US30 | H1 | 0.75% | 56 | 1336 | 58% | -544 | -89 | 387 | 54% | ok |
| double7s:n7_sl_atr1.5 | US500 | D1 | 1.25% | 55 | 1331 | 54% | -564 | -209 | 39 | 54% | ok |
| turtle_soup:n10_modelong_hold10_exit_rulepdh | US30 | D1 | 0.75% | 55 | 1324 | 25% | -268 | -91 | 26 | 38% | ok |
| h4_dip:n12_exit_rulehold | USTEC | H4 | 0.50% | 55 | 1323 | 50% | -525 | -144 | 100 | 37% | ok |
| overnight:sl_atr0.8_afterdown_trendwith | USTEC | M30 | 1.00% | 55 | 1322 | 42% | -518 | -172 | 123 | 58% | ok |
| ibs:lo0.3_hi0.7 | USTEC | D1 | 2.00% | 55 | 1320 | 71% | -305 | -168 | 75 | 69% | ok |
| rsi2:thresh5_exit_sma10 | US500 | D1 | 2.00% | 54 | 1307 | 33% | -551 | -196 | 11 | 73% | ok |
| ibs:lo0.2_hi0.7 | US30 | D1 | 2.00% | 54 | 1298 | 62% | -449 | -173 | 56 | 75% | ok |
| down_streak:k2_exit_rulehold_trend_reqFalse | USTEC | D1 | 1.50% | 54 | 1293 | 62% | -543 | -137 | 52 | 62% | ok |
| overnight:sl_atr1.5_trendwith | US30 | H1 | 1.50% | 54 | 1287 | 58% | -483 | -141 | 283 | 56% | ok |
| ibs:lo0.2_hi0.8 | USTEC | D1 | 2.00% | 53 | 1284 | 67% | -337 | -180 | 49 | 76% | ok |
| ibs:lo0.2_hi0.8_sl_atr1.5_max_hold5 | US500 | D1 | 1.25% | 53 | 1269 | 62% | -506 | -165 | 48 | 67% | ok |
| turtle_soup:n10_modeboth_hold10_exit_rulepdh | US500 | D1 | 0.75% | 52 | 1247 | 50% | -596 | -99 | 77 | 45% | ok |
| overnight:sl_atr0.8_afterdown_trendwith | US500 | M30 | 1.00% | 52 | 1237 | 54% | -568 | -171 | 141 | 57% | ok |
| double7s:n7 | USTEC | D1 | 2.00% | 50 | 1211 | 54% | -412 | -134 | 25 | 68% | ok |
| round:stepbig_modebounce_tp_r1.5 | USTEC | M30 | 0.75% | 50 | 1202 | 58% | -487 | -75 | 105 | 61% | ok |
| turtle_soup:n20_modelong_hold10_exit_rulepdh | US30 | D1 | 0.75% | 50 | 1193 | 25% | -262 | -88 | 18 | 50% | ok |
| double7s:n7_max_hold8 | USTEC | D1 | 2.00% | 48 | 1150 | 50% | -412 | -134 | 27 | 67% | ok |
| overnight:sl_atr1.5_trendwith | US500 | H1 | 1.50% | 48 | 1143 | 54% | -590 | -160 | 296 | 54% | ok |
| down_streak:k3_exit_rulehold_hold5_trend_reqTrue_tp_r1.5 | US500 | D1 | 2.00% | 47 | 1139 | 42% | -525 | -164 | 24 | 58% | ok |
| ibs:lo0.1_hi0.8 | US30 | D1 | 2.00% | 47 | 1138 | 58% | -449 | -173 | 35 | 71% | ok |
| overnight:sl_atr1.5_afterany_trendNone | USTEC | M30 | 1.25% | 47 | 1122 | 62% | -529 | -127 | 389 | 56% | ok |
| ibs:lo0.15_hi0.9_sma_trend100 | US30 | D1 | 2.00% | 45 | 1092 | 54% | -506 | -173 | 33 | 67% | ok |
| turtle_soup:n10_modeboth_hold10_exit_rulepdh | US30 | D1 | 0.75% | 45 | 1082 | 46% | -498 | -205 | 69 | 45% | ok |
| overnight:sl_atr1.5_afterdown_trendNone | USTEC | M30 | 1.50% | 45 | 1079 | 58% | -539 | -149 | 192 | 55% | ok |
| h4_dip:n24_exit_rulenhigh_max_hold48 | USTEC | H1 | 0.25% | 45 | 1075 | 46% | -529 | -135 | 259 | 33% | ok |
| weekday:enter_dow4_hold1_sl_atr1.0 | USTEC | D1 | 1.00% | 45 | 1075 | 58% | -463 | -115 | 92 | 61% | ok |
| h4_dip:n6_exit_rulenhigh | US500 | H4 | 0.50% | 45 | 1074 | 46% | -493 | -171 | 187 | 46% | ok |
| ibs:lo0.2_hi0.8_trend_reqFalse | USTEC | D1 | 1.50% | 44 | 1056 | 67% | -358 | -135 | 53 | 72% | ok |
| double7s:n10 | US30 | D1 | 2.00% | 44 | 1046 | 46% | -395 | -138 | 24 | 58% | ok |
| down_streak:k3_exit_rulepdh_trend_reqFalse | US500 | D1 | 2.00% | 43 | 1040 | 54% | -581 | -199 | 28 | 68% | ok |
| down_streak:k3_exit_rulehold_trend_reqFalse | US500 | D1 | 1.50% | 43 | 1039 | 54% | -469 | -149 | 27 | 56% | ok |
| down_streak:k3_exit_rulepdh_trend_reqTrue | US500 | D1 | 2.00% | 43 | 1033 | 46% | -525 | -164 | 25 | 68% | ok |
| ibs:lo0.3_hi0.8 | US30 | D1 | 2.00% | 42 | 1019 | 50% | -528 | -173 | 68 | 65% | ok |
| rsi2:thresh5_exit_sma5 | US30 | D1 | 2.00% | 42 | 1016 | 29% | -418 | -192 | 14 | 71% | ok |
| gap_struct:whereinside_modefade_gmin0.2_tppd_mid | USTEC | M30 | 1.00% | 42 | 1014 | 58% | -557 | -97 | 75 | 65% | ok |
| ibs:lo0.3_hi0.7 | US30 | D1 | 2.00% | 41 | 995 | 54% | -452 | -173 | 75 | 67% | ok |
| overnight:sl_atr0.8_afterany_trendwith | US500 | M30 | 0.75% | 41 | 984 | 50% | -501 | -131 | 295 | 57% | ok |
| double7s:n10 | USTEC | D1 | 2.00% | 41 | 982 | 46% | -393 | -173 | 19 | 58% | ok |
| weekday:enter_dow4_hold1 | US30 | D1 | 2.00% | 41 | 981 | 58% | -329 | -170 | 91 | 64% | ok |
| h4_pullback:sideslong_trailTrue | USTEC | H4 | 0.50% | 41 | 979 | 38% | -363 | -62 | 73 | 32% | ok |
| overnight:sl_atr1.5_afterdown_trendwith | US500 | M30 | 1.50% | 41 | 972 | 54% | -442 | -149 | 141 | 57% | ok |
| pdh_break:sideslong_stoplevel_tp_r2.0 | US30 | M30 | 0.50% | 40 | 960 | 62% | -452 | -84 | 110 | 49% | ok |
| turtle_soup:n10_modelong_hold5_exit_rulehold | US500 | D1 | 0.50% | 39 | 947 | 29% | -467 | -105 | 34 | 38% | ok |
| h4_dip:n12_exit_rulehold | US30 | H4 | 0.50% | 39 | 933 | 54% | -460 | -106 | 110 | 35% | ok |
| double7s:n7_sl_atr1.5 | USTEC | D1 | 1.50% | 38 | 907 | 46% | -536 | -179 | 35 | 54% | ok |
| h4_dip:n12_exit_rulenhigh | USTEC | H4 | 0.50% | 37 | 890 | 46% | -501 | -130 | 101 | 38% | ok |
| h4_pullback:sidesboth_trailTrue | USTEC | H4 | 0.50% | 37 | 882 | 38% | -535 | -62 | 112 | 28% | ok |
| turtle_soup:n20_modeboth_hold10_exit_rulepdh | US30 | D1 | 0.75% | 36 | 870 | 54% | -506 | -205 | 54 | 48% | ok |
| overnight:sl_atr0.8_afterany_trendNone | US30 | M30 | 0.75% | 36 | 868 | 54% | -530 | -89 | 383 | 54% | ok |
| turtle_soup:n10_modelong_hold5_exit_rulehold | US30 | D1 | 0.50% | 36 | 860 | 17% | -325 | -80 | 18 | 17% | ok |
| hour_window:entry_hour19_exit_hour20_sidelong_sl_atr0.6 | USTEC | H1 | 1.00% | 36 | 857 | 46% | -546 | -145 | 413 | 54% | ok |
| overnight:sl_atr0.8_afterany_trendwith | USTEC | M30 | 0.75% | 36 | 853 | 46% | -506 | -118 | 266 | 56% | ok |
| overnight:sl_atr0.8_afterdown_trendNone | USTEC | M30 | 0.75% | 35 | 850 | 62% | -482 | -149 | 187 | 54% | ok |
| double7s:n7 | US30 | D1 | 2.00% | 35 | 847 | 58% | -577 | -150 | 31 | 65% | ok |
| rsi2:thresh10_exit_sma10 | US30 | D1 | 2.00% | 35 | 844 | 46% | -437 | -173 | 25 | 68% | ok |
| down_streak:k3_exit_rulepdh_trend_reqFalse | US30 | D1 | 2.00% | 35 | 842 | 46% | -596 | -173 | 30 | 63% | ok |
| down_streak:k3_exit_rulehold_hold10_trend_reqTrue | US30 | D1 | 1.50% | 35 | 841 | 42% | -488 | -125 | 22 | 55% | ok |
| turtle_soup:n20_modeboth_hold10_exit_rulepdh | USTEC | D1 | 0.75% | 35 | 836 | 46% | -551 | -124 | 53 | 49% | ok |
| rsi2:thresh5_exit_sma10 | US30 | D1 | 2.00% | 35 | 833 | 29% | -418 | -192 | 14 | 57% | ok |
| double7s:n7_max_hold8 | US30 | D1 | 2.00% | 35 | 829 | 62% | -577 | -150 | 33 | 67% | ok |
| double7s:n7_sl_atr1.5 | US30 | D1 | 1.25% | 34 | 824 | 58% | -510 | -121 | 38 | 55% | ok |
| ibs:lo0.15_hi0.9_sma_trend100 | USTEC | D1 | 2.00% | 33 | 795 | 38% | -385 | -168 | 29 | 69% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold | USTEC | D1 | 1.25% | 33 | 791 | 25% | -516 | -289 | 18 | 39% | ok |
| opex:modelong_after_sl_atr1.5 | US30 | D1 | 2.00% | 33 | 787 | 50% | -455 | -227 | 20 | 60% | ok |
| down_streak:k3_exit_rulepdh_trend_reqTrue | US30 | D1 | 2.00% | 33 | 785 | 38% | -380 | -173 | 25 | 64% | ok |
| weekday:enter_dow4_hold1_trendwith | US30 | D1 | 2.00% | 32 | 779 | 54% | -329 | -170 | 68 | 62% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone | US30 | M30 | 0.50% | 32 | 771 | 58% | -477 | -98 | 327 | 51% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_dow0-1-2 | USTEC | H1 | 1.50% | 32 | 768 | 58% | -464 | -225 | 253 | 53% | ok |
| tom:days_before1_days_after3_sl_atr1.5_trendwith | USTEC | D1 | 2.00% | 32 | 765 | 54% | -464 | -177 | 15 | 73% | ok |
| hour_window:entry_hour9_exit_hour12_sidelong_sl_atr0.6 | US500 | H1 | 1.25% | 32 | 764 | 50% | -595 | -125 | 424 | 48% | ok |
| d1_breakout:n20_trail_atr2.0 | USTEC | D1 | 2.00% | 31 | 756 | 42% | -435 | -147 | 13 | 46% | ok |
| h4_dip:n8_exit_rulehold | US500 | H4 | 0.50% | 31 | 753 | 46% | -596 | -281 | 147 | 38% | ok |
| asia_break:tp_rNone_trendwith | US30 | H1 | 0.50% | 31 | 747 | 58% | -459 | -50 | 130 | 39% | ok |
| overnight:sl_atr0.8_afterdown_trendNone | US500 | M30 | 0.75% | 31 | 743 | 67% | -565 | -129 | 197 | 56% | ok |
| h4_dip:n8_sl_atr1.0_daily_sma100 | USTEC | H4 | 0.25% | 31 | 740 | 58% | -381 | -103 | 188 | 31% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | US500 | H1 | 0.25% | 30 | 719 | 58% | -349 | -96 | 292 | 40% | ok |
| down_streak:k2_exit_rulehold_trend_reqFalse | US30 | D1 | 1.50% | 30 | 718 | 62% | -504 | -141 | 48 | 56% | ok |
| down_streak:k2_exit_rulehold_trend_reqTrue | US30 | D1 | 1.50% | 30 | 712 | 54% | -488 | -119 | 43 | 56% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_r2.0 | US30 | M30 | 0.50% | 29 | 702 | 58% | -494 | -98 | 328 | 51% | ok |
| double7s:n5 | US500 | D1 | 1.50% | 29 | 701 | 54% | -575 | -167 | 37 | 68% | ok |
| prev_week:modefade_sideslong | US30 | H1 | 0.75% | 29 | 697 | 33% | -512 | -111 | 31 | 35% | ok |
| overnight:sl_atr1.5_afterany_trendwith | US30 | M30 | 1.50% | 29 | 693 | 42% | -381 | -141 | 280 | 54% | ok |
| overnight:sl_atr1.5_afterdown_trendwith | US30 | M30 | 2.00% | 29 | 692 | 42% | -442 | -145 | 131 | 56% | ok |
| overnight:sl_atr1.5_afterdown_trendNone | US500 | M30 | 1.25% | 29 | 690 | 67% | -590 | -119 | 197 | 56% | ok |
| down_streak:k3_exit_rulehold_hold5_trend_reqTrue_tp_r1.5 | USTEC | D1 | 2.00% | 29 | 689 | 46% | -352 | -169 | 21 | 62% | ok |
| down_streak:k3_exit_rulehold_hold10_trend_reqTrue | USTEC | D1 | 1.50% | 29 | 688 | 42% | -421 | -146 | 20 | 55% | ok |
| double7s:n5 | US30 | D1 | 2.00% | 28 | 676 | 62% | -577 | -150 | 37 | 70% | ok |
| overnight:sl_atr1.5_trendwith | USTEC | H1 | 1.50% | 28 | 675 | 42% | -581 | -159 | 268 | 54% | ok |
| overnight:sl_atr0.8_dow0-1-2-3 | US30 | M30 | 0.75% | 28 | 672 | 54% | -496 | -83 | 307 | 54% | ok |
| d1_breakout:n50_trail_atr2.0 | USTEC | D1 | 2.00% | 28 | 667 | 29% | -373 | -147 | 10 | 40% | ok |
| weekday:enter_dow3_hold1_sideshort | US500 | D1 | 2.00% | 28 | 667 | 42% | -485 | -194 | 91 | 47% | ok |
| overnight:sl_atr0.8_afterany_trendNone | US500 | M30 | 0.50% | 28 | 662 | 58% | -505 | -87 | 408 | 56% | ok |
| ibs:lo0.1_hi0.7 | US30 | D1 | 2.00% | 27 | 659 | 54% | -449 | -173 | 35 | 69% | ok |
| down_streak:k2_exit_rulepdh_trend_reqFalse | US500 | D1 | 1.00% | 27 | 658 | 58% | -478 | -119 | 62 | 69% | ok |
| rsi2:thresh5_exit_sma10 | USTEC | D1 | 2.00% | 27 | 649 | 33% | -432 | -206 | 12 | 75% | ok |
| opex:modelong_week_sl_atr1.5 | US30 | D1 | 1.50% | 27 | 637 | 46% | -369 | -142 | 22 | 55% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendwith | USTEC | M30 | 0.75% | 26 | 631 | 50% | -592 | -75 | 96 | 58% | ok |
| rsi2:thresh10_exit_sma5 | US30 | D1 | 2.00% | 26 | 630 | 33% | -437 | -173 | 25 | 60% | ok |
| rsi2:thresh10_exit_sma10 | USTEC | D1 | 2.00% | 26 | 628 | 42% | -370 | -206 | 20 | 70% | ok |
| pdh_break:sidesboth_stoplevel_tp_r2.0 | US30 | M30 | 0.50% | 26 | 620 | 58% | -409 | -84 | 196 | 44% | ok |
| d1_breakout:n20_trail_atr3.0 | US30 | D1 | 2.00% | 26 | 620 | 46% | -355 | -142 | 10 | 40% | ok |
| tom:days_before5_days_after3_sl_atr1.5 | US30 | D1 | 2.00% | 26 | 614 | 46% | -497 | -251 | 21 | 57% | ok |
| ibs:lo0.1_hi0.7 | USTEC | D1 | 2.00% | 25 | 612 | 42% | -264 | -168 | 25 | 80% | ok |
| tom:days_before5_days_after3_sl_atr2.5 | US30 | D1 | 2.00% | 25 | 601 | 58% | -272 | -125 | 20 | 70% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | USTEC | H1 | 0.50% | 25 | 599 | 50% | -542 | -142 | 143 | 41% | ok |
| h4_dip:n6_exit_rulehold | US500 | H4 | 0.25% | 25 | 598 | 42% | -318 | -101 | 149 | 38% | ok |
| hour_window:entry_hour9_exit_hour12_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | 25 | 592 | 46% | -455 | -99 | 421 | 52% | ok |
| pdh_break:sidesboth_stoplevel_tp_rNone | US30 | M30 | 0.25% | 25 | 590 | 67% | -269 | -42 | 181 | 42% | ok |
| weekday:enter_dow4_hold1_sl_atr1.0 | US30 | D1 | 1.50% | 25 | 589 | 50% | -473 | -152 | 91 | 60% | ok |
| h4_pullback:sideslong_trailTrue | USTEC | H1 | 0.25% | 24 | 588 | 62% | -421 | -96 | 260 | 27% | ok |
| hour_window:entry_hour9_exit_hour12_sidelong_sl_atr0.6 | USTEC | H1 | 1.25% | 24 | 582 | 50% | -502 | -118 | 422 | 51% | ok |
| h4_pullback:sidesboth_trailTrue | USTEC | H1 | 0.25% | 24 | 581 | 54% | -509 | -112 | 436 | 25% | ok |
| down_streak:k3_exit_rulehold_trend_reqTrue | USTEC | D1 | 2.00% | 24 | 581 | 46% | -456 | -169 | 21 | 62% | ok |
| overnight:sl_atr0.8_afterany_trendwith | US30 | M30 | 0.75% | 24 | 580 | 46% | -323 | -81 | 280 | 54% | ok |
| pdh_break:sideslong_stoplevel_tp_rNone | US30 | M30 | 0.25% | 24 | 575 | 62% | -353 | -42 | 101 | 47% | ok |
| overnight:sl_atr1.5_afterany_trendNone | US500 | M30 | 0.75% | 24 | 570 | 71% | -478 | -100 | 408 | 57% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_dow0-1-2 | US500 | H1 | 1.50% | 23 | 560 | 54% | -593 | -297 | 254 | 53% | ok |
| pdl_sweep:tppd_mid_sidesshort_sl_pad0.1 | US30 | M30 | 0.75% | 23 | 556 | 46% | -518 | -75 | 127 | 54% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_up | USTEC | H1 | 2.00% | 23 | 547 | 54% | -507 | -181 | 222 | 55% | ok |
| tom:days_before1_days_after3_sl_atr1.5 | USTEC | D1 | 1.50% | 23 | 545 | 58% | -592 | -178 | 21 | 67% | ok |
| h4_dip:n8_sl_atr1.0_daily_sma100 | US500 | H4 | 0.25% | 23 | 543 | 54% | -375 | -101 | 222 | 31% | ok |
| overnight:sl_atr0.8_dow0-1-2-3 | USTEC | M30 | 0.75% | 22 | 537 | 46% | -533 | -121 | 318 | 55% | ok |
| h4_dip:n12_exit_rulenhigh | US500 | H4 | 0.50% | 22 | 537 | 54% | -446 | -143 | 127 | 39% | ok |
| gap_struct:whereinside_modefade_gmin0.4 | USTEC | M30 | 1.25% | 22 | 537 | 50% | -539 | -122 | 51 | 53% | ok |
| first_hour:modecont_thresh_atr0.3 | USTEC | M30 | 0.75% | 22 | 532 | 50% | -495 | -73 | 134 | 51% | ok |
| opex:modelong_after_sl_atr1.5 | US500 | D1 | 1.50% | 22 | 530 | 46% | -475 | -229 | 20 | 55% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_trendwith | US30 | H1 | 1.50% | 22 | 520 | 38% | -569 | -147 | 297 | 49% | ok |
| h4_dip:n6_exit_rulehold | USTEC | H4 | 0.25% | 22 | 520 | 42% | -386 | -66 | 103 | 34% | ok |
| hour_window:entry_hour17_exit_hour18_sidelong_sl_atr0.6 | USTEC | H1 | 1.50% | 22 | 519 | 58% | -591 | -149 | 423 | 52% | ok |
| d1_breakout:n20_trail_atr3.0_squeeze0.9 | USTEC | D1 | 2.00% | 21 | 514 | 25% | -484 | -233 | 7 | 57% | ok |
| d1_breakout:n10_trail_atr2.0_squeeze0.8 | USTEC | D1 | 2.00% | 21 | 500 | 21% | -446 | -147 | 6 | 50% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_up | US500 | H1 | 1.25% | 20 | 481 | 54% | -537 | -137 | 226 | 54% | ok |
| prev_week:modebreak_stopatr_sideslong | USTEC | H1 | 0.50% | 20 | 479 | 38% | -572 | -235 | 48 | 21% | ok |
| prev_week:modebreak_stopatr_sideslong | US500 | H1 | 0.50% | 20 | 479 | 33% | -565 | -194 | 47 | 30% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | US500 | H1 | 0.25% | 20 | 477 | 58% | -393 | -96 | 162 | 42% | ok |
| h4_dip:n12_exit_rulenhigh | US30 | H4 | 0.50% | 20 | 476 | 50% | -580 | -106 | 115 | 37% | ok |
| overnight:sl_atr0.8_afterup | US30 | M30 | 0.75% | 20 | 475 | 46% | -507 | -83 | 204 | 54% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendwith | USTEC | M30 | 0.75% | 20 | 473 | 50% | -569 | -75 | 96 | 54% | ok |
| tom:days_before2_days_after2_sl_atr1.0 | US500 | D1 | 1.00% | 20 | 472 | 58% | -513 | -148 | 22 | 55% | ok |
| pdh_break:sideslong_stopatr_tp_rNone | USTEC | M30 | 1.00% | 20 | 470 | 58% | -570 | -100 | 109 | 60% | ok |
| down_streak:k3_exit_rulehold_trend_reqFalse | US30 | D1 | 1.50% | 19 | 459 | 42% | -488 | -137 | 26 | 46% | ok |
| asia_break:tp_rNone_trendwith | US500 | H1 | 0.25% | 19 | 457 | 46% | -317 | -25 | 88 | 48% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_up | USTEC | H1 | 1.50% | 19 | 456 | 50% | -452 | -145 | 222 | 53% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_r2.0 | US30 | M30 | 0.50% | 19 | 456 | 58% | -334 | -90 | 247 | 51% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | US500 | H4 | 0.75% | 19 | 456 | 50% | -569 | -180 | 61 | 43% | ok |
| overnight:sl_atr0.8_afterdown_trendwith | US30 | M30 | 1.25% | 19 | 449 | 42% | -491 | -131 | 131 | 55% | ok |
| overnight:sl_atr0.8_afterany_trendNone | USTEC | M30 | 0.50% | 19 | 446 | 54% | -460 | -75 | 349 | 54% | ok |
| prev_week:modefade_sideslong | US500 | H4 | 0.75% | 19 | 444 | 38% | -509 | -105 | 35 | 43% | ok |
| opex:modelong_after_sl_atr1.5 | USTEC | D1 | 1.50% | 19 | 444 | 50% | -395 | -179 | 20 | 55% | ok |
| h4_dip:n12_exit_rulehold | US500 | H4 | 0.50% | 18 | 444 | 42% | -548 | -179 | 126 | 37% | ok |
| h4_dip:n8_exit_rulehold_tp_r1.5_max_hold12 | US500 | H4 | 0.50% | 18 | 431 | 42% | -431 | -155 | 168 | 45% | ok |
| prev_week:modebreak_stopmid_sidesboth | USTEC | H4 | 0.75% | 18 | 428 | 46% | -498 | -124 | 59 | 44% | ok |
| down_streak:k3_exit_rulehold_trend_reqTrue | US30 | D1 | 1.50% | 18 | 428 | 33% | -488 | -119 | 24 | 46% | ok |
| turtle_soup:n20_modeboth_hold5_exit_rulehold | US30 | D1 | 0.25% | 18 | 426 | 25% | -163 | -59 | 11 | 45% | ok |
| fomc:modepost_fade_sl_atr0.7 | US500 | H1 | 2.00% | 18 | 426 | 33% | -161 | -125 | 12 | 67% | ok |
| prev_week:modefade_sideslong | US30 | H4 | 0.75% | 18 | 425 | 42% | -438 | -82 | 32 | 53% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | US30 | H1 | 0.50% | 18 | 424 | 50% | -532 | -95 | 73 | 40% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_last_entry_hm1730 | US30 | M30 | 0.50% | 18 | 424 | 58% | -407 | -98 | 238 | 50% | ok |
| down_streak:k3_exit_rulehold_trend_reqFalse | USTEC | D1 | 1.50% | 18 | 422 | 54% | -476 | -127 | 24 | 58% | ok |
| turtle_soup:n20_modeboth_hold10_exit_rulepdh | US500 | D1 | 0.50% | 18 | 420 | 62% | -399 | -267 | 61 | 48% | ok |
| turtle_soup:n10_modeboth_hold5_exit_rulehold | US500 | D1 | 0.25% | 17 | 414 | 50% | -361 | -246 | 76 | 34% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone | US30 | M30 | 0.50% | 17 | 414 | 54% | -334 | -90 | 246 | 50% | ok |
| prev_week:modefade_sidesboth | USTEC | H1 | 0.25% | 17 | 414 | 33% | -507 | -77 | 68 | 18% | ok |
| overnight:sl_atr0.8_dow0-1-2-3 | US500 | M30 | 0.50% | 17 | 411 | 54% | -433 | -81 | 328 | 57% | ok |
| h4_dip:n8_exit_rulenhigh | US500 | H4 | 0.50% | 17 | 409 | 42% | -529 | -281 | 157 | 42% | ok |
| opex:modelong_after_sl_atr1.5_trendwith | USTEC | D1 | 2.00% | 17 | 408 | 29% | -579 | -224 | 11 | 55% | ok |
| round:stepbig_modebounce_tp_r2.5_sl_atr0.3 | USTEC | M30 | 0.50% | 17 | 406 | 54% | -433 | -50 | 105 | 53% | ok |
| pdh_break:sideslong_stopatr_tp_r2.0 | USTEC | M30 | 1.00% | 17 | 404 | 58% | -570 | -100 | 109 | 60% | ok |
| turtle_soup:n10_modeboth_hold10_exit_rulepdh | USTEC | D1 | 0.75% | 17 | 402 | 50% | -505 | -130 | 70 | 43% | ok |
| weekday:enter_dow3_hold1_sideshort | USTEC | D1 | 2.00% | 17 | 401 | 50% | -539 | -199 | 91 | 44% | ok |
| rsi2:thresh10_exit_sma5_sl_atr3.0 | US30 | D1 | 2.00% | 17 | 401 | 33% | -397 | -180 | 19 | 63% | ok |
| tom:days_before1_days_after3_sl_atr1.5_trendwith | US30 | D1 | 2.00% | 17 | 401 | 46% | -260 | -134 | 14 | 71% | ok |
| ibs:lo0.1_hi0.8 | USTEC | D1 | 2.00% | 17 | 397 | 33% | -327 | -168 | 23 | 74% | ok |
| gap_struct:whereoutside_modefade_gmin0.4 | US500 | M30 | 0.50% | 17 | 397 | 58% | -470 | -115 | 88 | 52% | ok |
| overnight:sl_atr0.8_dow4 | US500 | M30 | 0.75% | 16 | 383 | 50% | -530 | -129 | 80 | 55% | ok |
| hour_window:entry_hour20_exit_hour21_sideshort_sl_atr0.6 | USTEC | H1 | 1.00% | 16 | 378 | 50% | -551 | -87 | 408 | 51% | ok |
| down_streak:k2_exit_rulepdh_trend_reqTrue | US30 | D1 | 1.50% | 15 | 369 | 58% | -344 | -119 | 44 | 59% | ok |
| round:stepbig_modebreak_tp_r1.5 | USTEC | M30 | 0.75% | 15 | 369 | 42% | -495 | -75 | 102 | 51% | ok |
| tom:days_before1_days_after2_sl_atr1.5 | US30 | D1 | 2.00% | 15 | 363 | 58% | -507 | -181 | 20 | 60% | ok |
| down_streak:k2_exit_rulepdh_trend_reqTrue | USTEC | D1 | 2.00% | 15 | 363 | 54% | -521 | -206 | 51 | 69% | ok |
| weekday:enter_dow2_hold1 | US30 | D1 | 1.50% | 15 | 359 | 58% | -383 | -135 | 89 | 47% | ok |
| rsi2:thresh10_exit_sma5 | USTEC | D1 | 2.00% | 15 | 358 | 50% | -454 | -206 | 20 | 80% | ok |
| prev_week:modebreak_stopmid_sideslong | US500 | H1 | 1.25% | 15 | 357 | 46% | -522 | -165 | 46 | 54% | ok |
| tom:days_before2_days_after3_sl_atr1.5 | US500 | D1 | 1.25% | 15 | 352 | 58% | -510 | -124 | 22 | 55% | ok |
| tom:days_before5_days_after3_sl_atr1.5 | USTEC | D1 | 1.50% | 15 | 349 | 50% | -541 | -216 | 21 | 52% | ok |
| double7s:n5 | USTEC | D1 | 2.00% | 14 | 348 | 54% | -592 | -169 | 35 | 63% | ok |
| round:stepbig_modebreak_tp_rNone | USTEC | M30 | 0.75% | 14 | 340 | 38% | -513 | -75 | 102 | 50% | ok |
| turtle_soup:n10_modelong_hold10_exit_rulepdh | US500 | D1 | 0.50% | 14 | 339 | 42% | -403 | -61 | 33 | 48% | ok |
| hour_window:entry_hour16_exit_hour18_sidelong_sl_atr0.6 | USTEC | H1 | 0.75% | 14 | 339 | 58% | -524 | -140 | 424 | 55% | ok |
| tom:days_before5_days_after3_sl_atr2.5 | US500 | D1 | 1.25% | 14 | 337 | 62% | -533 | -111 | 22 | 59% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendwith | USTEC | M30 | 0.50% | 14 | 335 | 50% | -429 | -50 | 96 | 49% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | USTEC | H4 | 1.00% | 14 | 334 | 38% | -528 | -229 | 48 | 40% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendNone | US30 | M30 | 0.50% | 14 | 332 | 42% | -393 | -55 | 221 | 53% | ok |
| tom:days_before1_days_after2_sl_atr1.5 | USTEC | D1 | 1.50% | 14 | 328 | 46% | -495 | -178 | 21 | 52% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold_tp_r2.0 | US30 | D1 | 0.75% | 14 | 326 | 21% | -250 | -88 | 19 | 42% | ok |
| down_streak:k2_exit_rulepdh_trend_reqFalse | US30 | D1 | 1.50% | 14 | 326 | 67% | -450 | -141 | 49 | 61% | ok |
| opex:modelong_after_sl_atr1.5_trendwith | US30 | D1 | 2.00% | 13 | 322 | 29% | -381 | -174 | 13 | 54% | ok |
| turtle_soup:n10_modeboth_hold5_exit_rulehold | US30 | D1 | 0.50% | 13 | 319 | 33% | -595 | -147 | 49 | 22% | ok |
| nr_break:modeinside_stopmid_tp_rNone | US500 | M30 | 1.50% | 13 | 315 | 38% | -597 | -150 | 38 | 55% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | USTEC | H1 | 0.75% | 13 | 308 | 42% | -490 | -75 | 148 | 57% | ok |
| overnight:sl_atr0.8_dow4 | US30 | M30 | 1.25% | 13 | 307 | 42% | -588 | -177 | 78 | 54% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_r2.0 | US500 | M30 | 0.75% | 13 | 307 | 25% | -468 | -75 | 35 | 51% | ok |
| fomc:modepost_fade_sl_atr0.7 | USTEC | H1 | 2.00% | 13 | 307 | 29% | -144 | -85 | 13 | 54% | ok |
| round:stepsmall_modebreak_tp_r1.5 | USTEC | M30 | 0.50% | 13 | 304 | 46% | -356 | -50 | 212 | 48% | ok |
| nr_break:modeinside_stopmid_tp_r2.0 | US500 | M30 | 1.50% | 13 | 302 | 38% | -597 | -150 | 38 | 55% | ok |
| tom:days_before2_days_after3_sl_atr1.5 | USTEC | D1 | 1.50% | 13 | 300 | 54% | -592 | -260 | 22 | 64% | ok |
| first_hour:modecont_thresh_atr0.5 | USTEC | M30 | 1.25% | 12 | 298 | 42% | -553 | -125 | 49 | 49% | ok |
| gap_struct:whereinside_modecont_gmin0.2 | US500 | M30 | 0.50% | 12 | 296 | 42% | -481 | -79 | 113 | 53% | ok |
| h4_pullback:sidesboth_trailTrue | US500 | H1 | 0.25% | 12 | 293 | 50% | -563 | -161 | 442 | 25% | ok |
| tom:days_before5_days_after2_sl_atr1.5 | US30 | D1 | 2.00% | 12 | 291 | 50% | -554 | -251 | 21 | 48% | ok |
| rsi2:thresh5_exit_sma5 | USTEC | D1 | 2.00% | 12 | 290 | 33% | -370 | -206 | 12 | 75% | ok |
| hour_window:entry_hour21_exit_hour22_sideshort_sl_atr0.6 | US30 | H1 | 1.00% | 12 | 285 | 54% | -457 | -87 | 406 | 50% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendNone | US30 | M30 | 0.50% | 12 | 285 | 42% | -537 | -87 | 221 | 46% | ok |
| round:stepsmall_modebreak_tp_rNone | USTEC | M30 | 0.50% | 12 | 282 | 50% | -366 | -50 | 212 | 48% | ok |
| opex:modelong_week_sl_atr1.5 | US500 | D1 | 1.00% | 12 | 281 | 38% | -469 | -114 | 23 | 43% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_condbelow_pdc | USTEC | H1 | 1.00% | 12 | 279 | 54% | -551 | -192 | 194 | 56% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_r2.0 | USTEC | M30 | 0.50% | 12 | 278 | 50% | -461 | -84 | 267 | 51% | ok |
| tom:days_before1_days_after3_sl_atr1.5 | US30 | D1 | 1.50% | 11 | 272 | 67% | -429 | -181 | 20 | 60% | ok |
| weekday:enter_dow3_hold1_sideshort | US30 | D1 | 2.00% | 11 | 270 | 38% | -455 | -173 | 88 | 47% | ok |
| overnight:sl_atr1.5_afterdown_trendNone | US30 | M30 | 1.25% | 11 | 270 | 58% | -425 | -102 | 168 | 55% | ok |
| tom:days_before2_days_after2_sl_atr1.0 | USTEC | D1 | 1.00% | 11 | 267 | 50% | -561 | -244 | 22 | 50% | ok |
| overnight:sl_atr1.5_afterany_trendNone | US30 | M30 | 0.75% | 11 | 262 | 29% | -148 | -71 | 90 | 57% | ok |
| pdh_break:sidesboth_stopmid_tp_rNone | US30 | M30 | 0.50% | 11 | 260 | 54% | -421 | -76 | 183 | 47% | ok |
| overnight:sl_atr0.8_afterup | USTEC | M30 | 1.00% | 11 | 260 | 46% | -596 | -121 | 211 | 56% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_condbelow_pdc | US500 | H1 | 1.00% | 11 | 259 | 50% | -579 | -196 | 191 | 54% | ok |
| asia_break:tp_rNone_trendNone | US500 | H1 | 0.25% | 11 | 258 | 38% | -528 | -25 | 195 | 38% | ok |
| gap_struct:whereoutside_modefade_gmin0.2 | US30 | M30 | 0.75% | 11 | 256 | 42% | -555 | -100 | 112 | 51% | ok |
| hour_window:entry_hour19_exit_hour20_sidelong_sl_atr0.6 | US500 | H1 | 0.75% | 11 | 255 | 42% | -552 | -126 | 415 | 51% | ok |
| first_hour:modecont_thresh_atr0.3_tp_r2.0 | USTEC | M30 | 0.75% | 11 | 255 | 50% | -511 | -73 | 134 | 51% | ok |
| overnight:sl_atr0.8_afterup | US500 | M30 | 0.75% | 11 | 254 | 46% | -499 | -121 | 209 | 57% | ok |
| round:stepsmall_modebounce_tp_r1.5 | USTEC | M30 | 0.50% | 11 | 254 | 46% | -413 | -50 | 212 | 54% | ok |
| gap_struct:whereinside_modefade_gmin0.2 | USTEC | M30 | 0.75% | 10 | 251 | 46% | -580 | -74 | 101 | 56% | ok |
| hour_window:entry_hour12_exit_hour13_sidelong_sl_atr0.6 | USTEC | H1 | 2.00% | 10 | 245 | 50% | -334 | -196 | 424 | 54% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | US500 | H1 | 0.25% | 10 | 243 | 50% | -340 | -77 | 137 | 38% | ok |
| tom:days_before5_days_after3_sl_atr2.5 | USTEC | D1 | 1.50% | 10 | 243 | 58% | -474 | -130 | 19 | 63% | ok |
| weekday:enter_dow2_hold1 | USTEC | D1 | 1.25% | 10 | 239 | 42% | -531 | -114 | 89 | 43% | ok |
| pdh_break:sideslong_stopatr_tp_rNone | US30 | M30 | 0.50% | 10 | 238 | 62% | -461 | -62 | 105 | 53% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.25 | US500 | M30 | 1.00% | 10 | 237 | 58% | -509 | -101 | 98 | 60% | ok |
| rsi2:thresh10_exit_sma5_sl_atr3.0 | USTEC | D1 | 2.00% | 10 | 234 | 54% | -331 | -120 | 20 | 80% | ok |
| gap_struct:whereinside_modecont_gmin0.4 | US30 | M30 | 1.00% | 10 | 233 | 42% | -575 | -114 | 44 | 48% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | USTEC | H1 | 0.25% | 10 | 231 | 58% | -308 | -68 | 168 | 40% | ok |
| prev_week:modebreak_stopmid_sidesboth | USTEC | H1 | 0.50% | 10 | 229 | 42% | -376 | -73 | 38 | 37% | ok |
| round:stepbig_modebreak_tp_rNone | US500 | M30 | 0.50% | 9 | 226 | 62% | -578 | -61 | 196 | 47% | ok |
| round:stepsmall_modebounce_tp_rNone | USTEC | M30 | 0.50% | 9 | 225 | 46% | -460 | -50 | 212 | 53% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_r2.0 | US30 | M30 | 0.25% | 9 | 222 | 50% | -520 | -43 | 285 | 44% | ok |
| pdh_break:sideslong_stopmid_tp_rNone | US30 | M30 | 0.50% | 9 | 222 | 46% | -494 | -76 | 102 | 50% | ok |
| pdh_break:sideslong_stopatr_tp_r2.0 | US30 | M30 | 0.50% | 9 | 220 | 62% | -461 | -62 | 105 | 53% | ok |
| prev_week:modebreak_stopatr_sidesboth | US30 | H1 | 0.25% | 9 | 219 | 38% | -438 | -172 | 63 | 22% | ok |
| overnight:sl_atr0.8 | US500 | H1 | 0.25% | 9 | 217 | 46% | -306 | -43 | 409 | 52% | ok |
| h4_dip:n8_exit_rulenhigh | USTEC | H4 | 0.25% | 9 | 214 | 50% | -310 | -62 | 97 | 39% | ok |
| first_last:thresh_atr0.3_modemom_entry_hm2130 | USTEC | M30 | 2.00% | 9 | 212 | 46% | -522 | -192 | 201 | 49% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold | US30 | D1 | 0.50% | 9 | 212 | 8% | -325 | -125 | 11 | 18% | ok |
| down_streak:k3_exit_rulepdh_trend_reqFalse | USTEC | D1 | 1.50% | 9 | 209 | 50% | -420 | -127 | 24 | 67% | ok |
| tom:days_before1_days_after3_sl_atr1.5 | US500 | D1 | 1.25% | 9 | 209 | 54% | -542 | -182 | 21 | 57% | ok |
| nr_break:modenr7_stopmid_tp_r2.0 | US500 | M30 | 1.00% | 9 | 208 | 54% | -553 | -187 | 54 | 46% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | US500 | H1 | 1.25% | 9 | 207 | 42% | -549 | -165 | 43 | 53% | ok |
| prev_week:modebreak_stopatr_sidesboth | US30 | H4 | 0.25% | 9 | 204 | 25% | -350 | -162 | 21 | 38% | ok |
| hour_window:entry_hour16_exit_hour18_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | 8 | 204 | 58% | -597 | -173 | 423 | 50% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_condbelow_pdc | US30 | H1 | 1.00% | 8 | 203 | 54% | -476 | -173 | 203 | 51% | ok |
| opex:modeshort_week_sl_atr1.5 | US30 | D1 | 1.25% | 8 | 202 | 42% | -578 | -172 | 20 | 45% | ok |
| opex:modeshort_week_sl_atr1.5 | US500 | D1 | 0.75% | 8 | 201 | 54% | -531 | -246 | 23 | 52% | ok |
| tom:days_before1_days_after2_sl_atr1.5 | US500 | D1 | 1.50% | 8 | 201 | 54% | -534 | -210 | 21 | 62% | ok |
| overnight:sl_atr0.8_afterdown_trendNone | US30 | M30 | 1.00% | 8 | 199 | 54% | -566 | -121 | 182 | 54% | ok |
| pdh_break:sideslong_stopmid_min_dist0.1 | US30 | M30 | 1.00% | 8 | 198 | 54% | -463 | -97 | 48 | 52% | ok |
| tom:days_before2_days_after2_sl_atr1.5 | US500 | D1 | 1.25% | 8 | 196 | 58% | -582 | -124 | 22 | 55% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | US30 | H4 | 0.75% | 8 | 195 | 46% | -498 | -137 | 89 | 37% | ok |
| fomc:modepost_fade_sl_atr0.7 | USTEC | M30 | 2.00% | 8 | 194 | 29% | -94 | -70 | 13 | 54% | ok |
| gap_struct:whereinside_modefade_gmin0.4 | US30 | M30 | 1.25% | 8 | 188 | 42% | -546 | -123 | 44 | 57% | ok |
| overnight:sl_atr0.8_dow4 | USTEC | M30 | 0.75% | 8 | 188 | 46% | -487 | -149 | 78 | 54% | ok |
| gap_struct:whereoutside_modefade_gmin0.4 | US30 | M30 | 0.50% | 8 | 181 | 42% | -397 | -50 | 80 | 49% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold_tp_r2.0 | USTEC | D1 | 1.25% | 8 | 181 | 25% | -516 | -121 | 19 | 42% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone_trendwith | USTEC | M30 | 0.50% | 7 | 179 | 58% | -391 | -79 | 153 | 59% | ok |
| tom:days_before2_days_after3_sl_atr1.5 | US30 | D1 | 1.50% | 7 | 175 | 62% | -525 | -181 | 21 | 48% | ok |
| pdh_break:sideslong_stopmid_tp_r2.0 | US30 | M30 | 0.50% | 7 | 175 | 50% | -425 | -76 | 102 | 51% | ok |
| asia_break:tp_r1.5_trendwith | US500 | H1 | 0.25% | 7 | 174 | 46% | -295 | -25 | 88 | 50% | ok |
| tom:days_before5_days_after3_sl_atr1.5 | US500 | D1 | 1.50% | 7 | 169 | 58% | -597 | -171 | 22 | 50% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_r2.0 | USTEC | M30 | 2.00% | 7 | 168 | 8% | -267 | -96 | 3 | 67% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_rNone | USTEC | M30 | 2.00% | 7 | 168 | 8% | -267 | -96 | 3 | 67% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_r2.0 | USTEC | M30 | 2.00% | 7 | 168 | 8% | -267 | -96 | 3 | 67% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_rNone | USTEC | M30 | 2.00% | 7 | 168 | 8% | -267 | -96 | 3 | 67% | ok |
| prev_week:modefade_sideslong | US500 | H1 | 0.25% | 7 | 166 | 38% | -376 | -35 | 36 | 31% | ok |
| overnight:sl_atr0.8 | USTEC | H1 | 0.50% | 7 | 165 | 50% | -542 | -75 | 351 | 52% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | US30 | H1 | 0.25% | 7 | 162 | 46% | -499 | -75 | 218 | 37% | ok |
| d1_breakout:n50_trail_atr3.0 | USTEC | D1 | 2.00% | 7 | 161 | 33% | -568 | -233 | 9 | 33% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendNone | US500 | M30 | 0.75% | 7 | 157 | 54% | -597 | -75 | 97 | 58% | ok |
| h4_dip:n8_sl_atr1.0_daily_sma100 | US30 | H4 | 0.25% | 6 | 152 | 42% | -581 | -106 | 169 | 27% | ok |
| d1_breakout:n10_trail_atr2.0_squeeze0.8 | US500 | D1 | 2.00% | 6 | 152 | 17% | -578 | -259 | 6 | 33% | ok |
| d1_breakout:n20_trail_atr3.0_squeeze0.9 | US30 | D1 | 2.00% | 6 | 150 | 29% | -494 | -180 | 6 | 33% | ok |
| gap_struct:whereoutside_modefade_gmin0.2 | US500 | M30 | 0.50% | 6 | 150 | 50% | -585 | -115 | 127 | 51% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_trendwith | USTEC | H1 | 0.75% | 6 | 147 | 42% | -433 | -73 | 283 | 55% | ok |
| nr_break:modeinside_stopfar_tp_r2.0 | US500 | M30 | 2.00% | 6 | 147 | 38% | -565 | -198 | 38 | 55% | ok |
| nr_break:modeinside_stopfar_tp_rNone | US500 | M30 | 2.00% | 6 | 147 | 38% | -565 | -198 | 38 | 55% | ok |
| turtle_soup:n20_modeboth_hold5_exit_rulehold | USTEC | D1 | 0.25% | 6 | 147 | 25% | -215 | -99 | 20 | 40% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r2.0 | USTEC | M30 | 2.00% | 6 | 146 | 8% | -233 | -60 | 3 | 67% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_rNone | USTEC | M30 | 2.00% | 6 | 146 | 8% | -233 | -60 | 3 | 67% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_r2.0 | USTEC | M30 | 2.00% | 6 | 146 | 8% | -233 | -60 | 3 | 67% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_rNone | USTEC | M30 | 2.00% | 6 | 146 | 8% | -233 | -60 | 3 | 67% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r3.0 | USTEC | M30 | 2.00% | 6 | 146 | 8% | -233 | -60 | 3 | 67% | ok |
| asia_break:tp_rNone_trendNone | US30 | H1 | 0.25% | 6 | 146 | 46% | -549 | -25 | 216 | 35% | ok |
| d1_breakout:n50_trail_atr3.0 | US30 | D1 | 2.00% | 6 | 146 | 25% | -415 | -100 | 7 | 29% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_dow0-1-2 | US30 | H1 | 1.25% | 6 | 142 | 54% | -570 | -180 | 256 | 51% | ok |
| fomc:modepost_fade_sl_atr0.7 | US500 | M30 | 2.00% | 6 | 141 | 25% | -147 | -119 | 12 | 50% | ok |
| prev_week:modebreak_stopmid_sideslong | US500 | H4 | 1.25% | 6 | 135 | 46% | -518 | -163 | 47 | 53% | ok |
| pdh_break:sideslong_stopmid_trendwith | US30 | M30 | 0.50% | 6 | 133 | 29% | -412 | -76 | 75 | 51% | ok |
| hour_window:entry_hour16_exit_hour18_sidelong_sl_atr0.6 | US500 | H1 | 0.75% | 6 | 133 | 62% | -511 | -146 | 426 | 53% | ok |
| fomc:modepre_drift_entry_hour16_sl_atr1.0 | USTEC | H1 | 2.00% | 5 | 132 | 33% | -134 | -105 | 14 | 57% | ok |
| overnight:sl_atr0.5_tp_r1.0 | US30 | M30 | 0.25% | 5 | 129 | 33% | -107 | -44 | 88 | 60% | ok |
| turtle_soup:n20_modeboth_hold5_exit_rulehold | US500 | D1 | 0.25% | 5 | 129 | 54% | -516 | -246 | 60 | 33% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.3 | USTEC | H1 | 0.50% | 5 | 126 | 50% | -520 | -99 | 417 | 50% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_r2.0 | USTEC | M30 | 0.25% | 5 | 125 | 38% | -240 | -66 | 265 | 49% | ok |
| fomc:modepre_drift_entry_hour16_sl_atr1.0 | US500 | H1 | 2.00% | 5 | 123 | 29% | -152 | -102 | 14 | 50% | ok |
| first_hour:modecont_thresh_atr0.3 | US500 | M30 | 0.75% | 5 | 119 | 54% | -555 | -75 | 112 | 47% | ok |
| pdh_break:sidesboth_stopmid_tp_r2.0 | US30 | M30 | 0.50% | 5 | 117 | 62% | -373 | -76 | 183 | 48% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condbelow_pdc | USTEC | H1 | 1.50% | 5 | 116 | 54% | -524 | -142 | 196 | 52% | ok |
| first_hour:modefade_thresh_atr0.3 | US30 | M30 | 0.75% | 5 | 115 | 46% | -584 | -75 | 117 | 50% | ok |
| d1_breakout:n20_trail_atr2.0 | US500 | D1 | 2.00% | 5 | 115 | 42% | -599 | -259 | 15 | 33% | ok |
| hour_window:entry_hour1_exit_hour4_sidelong_sl_atr0.6 | USTEC | H1 | 1.50% | 5 | 112 | 50% | -580 | -149 | 423 | 53% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_up | US500 | H1 | 1.50% | 5 | 111 | 50% | -573 | -165 | 226 | 52% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r2.0 | US500 | M30 | 0.25% | 5 | 111 | 42% | -416 | -57 | 302 | 45% | ok |
| round:stepbig_modebreak_tp_r1.5 | US30 | M30 | 0.50% | 5 | 109 | 50% | -490 | -73 | 146 | 53% | ok |
| turtle_soup:n10_modelong_hold5_exit_rulehold | USTEC | D1 | 0.75% | 4 | 105 | 25% | -427 | -146 | 27 | 30% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | USTEC | H4 | 0.75% | 4 | 104 | 29% | -552 | -163 | 40 | 35% | ok |
| hour_window:entry_hour9_exit_hour10_sidelong_sl_atr0.6 | USTEC | H1 | 2.00% | 4 | 101 | 54% | -565 | -122 | 423 | 50% | ok |
| prev_week:modefade_sidesboth | US30 | H4 | 0.50% | 4 | 101 | 42% | -390 | -93 | 53 | 36% | ok |
| h4_pullback:sideslong_trailTrue | US500 | H1 | 0.25% | 4 | 98 | 46% | -396 | -63 | 247 | 25% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_last_entry_hm1730 | USTEC | M30 | 0.25% | 4 | 94 | 42% | -231 | -49 | 203 | 51% | ok |
| nr_break:modenr7_stopmid_tp_rNone | US500 | M30 | 1.00% | 4 | 91 | 54% | -582 | -187 | 54 | 46% | ok |
| down_streak:k3_exit_rulepdh_trend_reqTrue | USTEC | D1 | 2.00% | 4 | 90 | 42% | -550 | -169 | 21 | 67% | ok |
| asia_break:tp_r1.5_trendwith | USTEC | H1 | 0.25% | 4 | 90 | 58% | -309 | -25 | 100 | 48% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | USTEC | M30 | 0.75% | 4 | 88 | 46% | -508 | -85 | 191 | 56% | ok |
| nr_break:modenr7_stopfar_tp_r2.0 | US500 | M30 | 1.50% | 4 | 88 | 54% | -508 | -192 | 54 | 46% | ok |
| nr_break:modenr7_stopfar_tp_rNone | US500 | M30 | 1.50% | 4 | 88 | 54% | -508 | -192 | 54 | 46% | ok |
| turtle_soup:n20_modelong_hold3_exit_rulehold_sl_pad0.5 | USTEC | D1 | 1.25% | 4 | 85 | 25% | -286 | -116 | 17 | 53% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_up | US30 | H1 | 0.75% | 4 | 85 | 46% | -470 | -74 | 201 | 53% | ok |
| weekday:enter_dow2_hold1 | US500 | D1 | 0.75% | 3 | 82 | 46% | -455 | -74 | 93 | 52% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | US30 | H4 | 1.00% | 3 | 82 | 38% | -543 | -239 | 42 | 38% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | US30 | H1 | 0.50% | 3 | 80 | 42% | -541 | -140 | 157 | 36% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_r2.0 | US30 | M30 | 2.00% | 3 | 78 | 8% | -461 | -198 | 5 | 60% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_rNone | US30 | M30 | 2.00% | 3 | 78 | 8% | -461 | -198 | 5 | 60% | ok |
| hour_window:entry_hour19_exit_hour20_sidelong_sl_atr0.6 | US30 | H1 | 0.75% | 3 | 77 | 46% | -492 | -97 | 405 | 54% | ok |
| down_streak:k3_exit_rulehold_hold5_trend_reqTrue_tp_r1.5 | US30 | D1 | 2.00% | 3 | 74 | 33% | -496 | -173 | 25 | 44% | ok |
| prev_week:modebreak_stopatr_sideslong | US500 | H4 | 0.50% | 3 | 73 | 46% | -500 | -85 | 47 | 38% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_trendwith | USTEC | M30 | 0.50% | 3 | 72 | 50% | -517 | -103 | 210 | 55% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.3 | US30 | H1 | 0.25% | 3 | 69 | 42% | -256 | -36 | 378 | 50% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | US30 | H1 | 2.00% | 3 | 69 | 33% | -530 | -145 | 14 | 57% | ok |
| d1_breakout:n20_trail_atr3.0_sidesboth | USTEC | D1 | 1.00% | 3 | 68 | 50% | -487 | -208 | 16 | 38% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendNone | US30 | M30 | 0.50% | 3 | 67 | 50% | -424 | -50 | 219 | 54% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | USTEC | H4 | 0.25% | 3 | 66 | 33% | -154 | -53 | 42 | 36% | ok |
| down_streak:k2_exit_rulepdh_trend_reqFalse | USTEC | D1 | 1.50% | 3 | 65 | 50% | -570 | -137 | 55 | 65% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condbelow_pdc | US500 | H1 | 1.00% | 3 | 61 | 54% | -590 | -198 | 190 | 52% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendNone | US500 | M30 | 0.50% | 2 | 60 | 58% | -424 | -52 | 98 | 57% | ok |
| prev_week:modebreak_stopatr_sidesboth | USTEC | H4 | 0.25% | 2 | 59 | 25% | -376 | -147 | 42 | 26% | ok |
| h4_dip:n8_exit_rulehold_tp_r1.5_max_hold12 | USTEC | H4 | 0.50% | 2 | 59 | 46% | -503 | -159 | 146 | 41% | ok |
| d1_breakout:n20_trail_atr3.0 | USTEC | D1 | 1.50% | 2 | 58 | 38% | -561 | -193 | 12 | 42% | ok |
| rsi2:thresh10_exit_sma5_sideshort | US30 | D1 | 2.00% | 2 | 54 | 4% | -23 | -16 | 1 | 100% | ok |
| fomc:modepost_fade_sl_atr0.7 | US30 | H1 | 2.00% | 2 | 53 | 29% | -178 | -178 | 13 | 54% | ok |
| capitulation:drop_atr2.5_exit_rulepdh | US30 | D1 | 2.00% | 2 | 53 | 4% | -416 | -163 | 4 | 50% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_r2.0 | US30 | M30 | 2.00% | 2 | 52 | 8% | -400 | -163 | 5 | 60% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_rNone | US30 | M30 | 2.00% | 2 | 52 | 8% | -400 | -163 | 5 | 60% | ok |
| round:stepbig_modebreak_tp_rNone | US30 | M30 | 0.50% | 2 | 48 | 50% | -530 | -73 | 146 | 53% | ok |
| tom:days_before2_days_after2_sl_atr1.5 | USTEC | D1 | 1.25% | 2 | 46 | 46% | -522 | -216 | 20 | 55% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr2.0 | US30 | H1 | 2.00% | 2 | 45 | 33% | -235 | -95 | 14 | 57% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | US30 | H4 | 0.75% | 2 | 45 | 42% | -545 | -137 | 56 | 38% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | 2 | 45 | 42% | -455 | -173 | 423 | 49% | ok |
| fomc:modepost_mom_sl_atr0.7 | US30 | M30 | 2.00% | 2 | 39 | 29% | -147 | -147 | 13 | 54% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone_trendwith | US500 | M30 | 0.50% | 2 | 37 | 46% | -401 | -83 | 169 | 52% | ok |
| gap_struct:whereinside_modefade_gmin0.2 | US30 | M30 | 0.75% | 2 | 37 | 50% | -591 | -74 | 107 | 59% | ok |
| round:stepbig_modebreak_tp_r1.5 | US500 | M30 | 0.25% | 2 | 37 | 50% | -290 | -30 | 196 | 48% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_moderip | US30 | M30 | 1.50% | 1 | 35 | 42% | -521 | -145 | 108 | 47% | ok |
| capitulation:drop_atr2.5_exit_rulehold | US30 | D1 | 2.00% | 1 | 31 | 4% | -459 | -240 | 4 | 50% | ok |
| gap_struct:whereoutside_modecont_gmin0.3_sl_atr0.8 | USTEC | M30 | 0.75% | 1 | 25 | 42% | -454 | -101 | 117 | 57% | ok |
| prev_week:modebreak_stopmid_sidesboth | US30 | H4 | 0.50% | 1 | 18 | 25% | -368 | -162 | 15 | 47% | ok |
| rsi2:thresh10_exit_sma5_sideshort | US500 | D1 | 2.00% | 1 | 16 | 8% | -73 | -46 | 2 | 50% | ok |
| hour_window:entry_hour21_exit_hour22_sideshort_sl_atr0.6 | US500 | H1 | 0.75% | 1 | 16 | 50% | -558 | -74 | 409 | 47% | ok |
| opex:modeshort_week_sl_atr1.5 | USTEC | D1 | 0.75% | 1 | 12 | 29% | -386 | -99 | 15 | 47% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.25 | US30 | M30 | 1.00% | 0 | 11 | 42% | -491 | -96 | 115 | 48% | ok |
| overnight:sl_atr0.5_tp_r1.0 | US500 | M30 | 0.25% | 0 | 9 | 50% | -413 | -66 | 408 | 56% | ok |
| pdl_sweep:tpNone_sideslong_sl_pad0.1 | US30 | M30 | 0.50% | 0 | 9 | 33% | -420 | -49 | 113 | 46% | ok |
| hour_window:entry_hour15_exit_hour16_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | 0 | 9 | 50% | -366 | -50 | 382 | 50% | ok |
| hour_window:entry_hour12_exit_hour13_sidelong_sl_atr0.6 | US30 | H1 | 2.00% | 0 | 9 | 58% | -526 | -164 | 426 | 51% | ok |
| turtle_soup:n20_modelong_hold10_exit_rulepdh | USTEC | D1 | 1.25% | 0 | 7 | 29% | -512 | -121 | 19 | 53% | ok |
| pdh_break:sideslong_stopmid | USTEC | H1 | 1.25% | 0 | 6 | 46% | -592 | -125 | 85 | 56% | ok |
| turtle_soup:n10_modeboth_hold5_exit_rulehold | USTEC | D1 | 0.25% | 0 | 5 | 25% | -227 | -99 | 28 | 25% | ok |
| first_hour:modecont_thresh_atr0.3_tp_r2.0 | US500 | M30 | 0.50% | 0 | 3 | 54% | -430 | -50 | 112 | 47% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | 0 | 2 | 42% | -426 | -78 | 394 | 52% | ok |
| hour_window:entry_hour18_exit_hour19_sideshort_sl_atr0.6 | USTEC | H1 | 1.25% | 0 | 1 | 54% | -538 | -124 | 423 | 49% | ok |
| h4_dip:n12_exit_rulenhigh | US500 | H1 | none | 21 | 502 | 46% | -770 | -145 | 488 | 39% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_rNone | US30 | M30 | none | 14 | 342 | 50% | -618 | -43 | 285 | 43% | ok |
| h4_dip:n24_exit_rulenhigh_max_hold48 | US500 | H1 | none | 10 | 246 | 46% | -842 | -151 | 289 | 29% | ok |
| h4_dip:n24_exit_rulenhigh_max_hold48 | US30 | H1 | none | 2 | 55 | 38% | -666 | -106 | 266 | 26% | ok |
| first_hour:modecont_thresh_atr0.3_trendwith | USTEC | M30 | 0.75% | -0 | -0 | 46% | -472 | -73 | 66 | 50% | ok |
| prev_week:modebreak_stopatr_sideslong | USTEC | H4 | 0.25% | -0 | -2 | 29% | -346 | -147 | 33 | 27% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | US30 | H4 | 0.25% | -0 | -4 | 29% | -265 | -162 | 21 | 48% | ok |
| gap_struct:whereinside_modefade_gmin0.2_tppd_mid | US500 | M30 | 0.75% | -0 | -5 | 38% | -537 | -74 | 76 | 58% | ok |
| asia_break:tp_rNone_trendwith | USTEC | H1 | 0.25% | -0 | -6 | 46% | -382 | -25 | 100 | 42% | ok |
| rsi2:thresh10_exit_sma5_sideshort | USTEC | D1 | 2.00% | -0 | -7 | 4% | -79 | -48 | 2 | 50% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1 | USTEC | H1 | 0.25% | -0 | -9 | 50% | -243 | -25 | 140 | 48% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr2.0 | USTEC | H1 | 2.00% | -0 | -12 | 21% | -114 | -61 | 14 | 36% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | USTEC | M30 | 2.00% | -1 | -13 | 25% | -41 | -27 | 14 | 43% | ok |
| first_last:thresh_atr0.3_modemom_entry_hm2130 | US30 | M30 | 1.50% | -1 | -13 | 50% | -452 | -137 | 185 | 47% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr1.0_trendwith | USTEC | H1 | 2.00% | -1 | -15 | 42% | -573 | -182 | 271 | 52% | ok |
| first_hour:modecont_thresh_atr0.3_tp_r2.0 | US30 | M30 | 0.25% | -1 | -18 | 25% | -217 | -24 | 42 | 48% | ok |
| capitulation:drop_atr2.5_exit_rulepdh | US500 | D1 | 2.00% | -1 | -20 | 4% | -499 | -199 | 4 | 50% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | US500 | H4 | 1.25% | -1 | -21 | 42% | -543 | -163 | 44 | 52% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_up | US30 | H1 | 1.25% | -1 | -22 | 50% | -523 | -116 | 201 | 49% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r1.0 | US30 | M30 | 0.25% | -1 | -22 | 54% | -254 | -49 | 215 | 51% | ok |
| first_hour:modecont_thresh_atr0.3 | US30 | M30 | 0.25% | -1 | -23 | 25% | -217 | -24 | 42 | 48% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condbelow_pdc | USTEC | H1 | 1.00% | -1 | -24 | 50% | -483 | -161 | 197 | 49% | ok |
| opex:modelong_week_sl_atr1.5 | USTEC | D1 | 1.25% | -1 | -27 | 33% | -490 | -245 | 22 | 36% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | USTEC | H4 | 0.50% | -1 | -27 | 38% | -479 | -114 | 71 | 37% | ok |
| h4_dip:n8_exit_rulehold | US30 | H4 | 0.25% | -1 | -28 | 38% | -320 | -56 | 57 | 25% | ok |
| tom:days_before5_days_after2_sl_atr1.5 | USTEC | D1 | 1.50% | -1 | -28 | 46% | -531 | -216 | 21 | 43% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | USTEC | H1 | 2.00% | -1 | -28 | 21% | -324 | -163 | 14 | 36% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendNone | US30 | M30 | 0.50% | -1 | -29 | 33% | -464 | -49 | 113 | 46% | ok |
| prev_week:modefade_sidesboth | US500 | H4 | 0.25% | -1 | -29 | 38% | -502 | -146 | 73 | 37% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | US30 | H1 | 0.25% | -1 | -31 | 46% | -468 | -78 | 268 | 35% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_r2.0 | US500 | M30 | 0.25% | -1 | -31 | 54% | -415 | -41 | 302 | 48% | ok |
| capitulation:drop_atr2.5_exit_rulehold | US500 | D1 | 2.00% | -2 | -37 | 8% | -539 | -222 | 4 | 50% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | USTEC | H1 | 0.25% | -2 | -38 | 54% | -513 | -68 | 291 | 37% | ok |
| pdh_break:sideslong_stoplevel_tp_rNone | USTEC | M30 | 0.25% | -2 | -40 | 42% | -307 | -25 | 107 | 47% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condbelow_pdc | US500 | H1 | 1.25% | -2 | -41 | 54% | -517 | -204 | 190 | 51% | ok |
| hour_window:entry_hour20_exit_hour21_sideshort_sl_atr0.6 | US500 | H1 | 0.75% | -2 | -41 | 29% | -572 | -74 | 409 | 44% | ok |
| first_last:thresh_atr0.4_modemom | US30 | M30 | 1.25% | -2 | -45 | 42% | -589 | -115 | 139 | 46% | ok |
| tom:days_before2_days_after2_sl_atr1.5 | US30 | D1 | 1.50% | -2 | -45 | 50% | -568 | -181 | 21 | 48% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_rNone | US500 | M30 | 0.25% | -2 | -46 | 46% | -500 | -57 | 302 | 44% | ok |
| gap_struct:whereinside_modefade_gmin0.2_tppd_mid | US30 | M30 | 0.75% | -2 | -51 | 50% | -487 | -74 | 81 | 65% | ok |
| tom:days_before1_days_after3_sl_atr1.5_trendwith | US500 | D1 | 2.00% | -2 | -55 | 38% | -557 | -197 | 15 | 53% | ok |
| first_hour:modecont_thresh_atr0.5 | US30 | M30 | 0.75% | -2 | -56 | 38% | -462 | -73 | 53 | 49% | ok |
| gap_struct:whereoutside_modecont_gmin0.2 | US30 | M30 | 0.25% | -2 | -59 | 17% | -135 | -25 | 24 | 46% | ok |
| capitulation:drop_atr1.5_exit_rulehold_vol_mult1.0 | US500 | D1 | 1.00% | -2 | -59 | 33% | -525 | -111 | 21 | 52% | ok |
| tom:days_before2_days_after2_sl_atr1.0 | US30 | D1 | 1.00% | -2 | -59 | 46% | -464 | -170 | 21 | 38% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | US30 | M30 | 2.00% | -2 | -60 | 25% | -71 | -23 | 13 | 46% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_down | US30 | H1 | 1.50% | -3 | -61 | 62% | -574 | -211 | 214 | 49% | ok |
| gap_struct:whereinside_modefade_gmin0.4 | US500 | M30 | 0.75% | -3 | -61 | 33% | -469 | -75 | 49 | 49% | ok |
| asia_break:tp_r1.5_trendNone | USTEC | H1 | 0.25% | -3 | -62 | 38% | -380 | -25 | 191 | 47% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | US500 | M30 | 2.00% | -3 | -65 | 25% | -95 | -34 | 14 | 43% | ok |
| d1_breakout:n20_trail_atr3.0_squeeze0.9 | US500 | D1 | 1.50% | -3 | -65 | 25% | -560 | -194 | 8 | 25% | ok |
| capitulation:drop_atr2.5_exit_rulepdh | USTEC | D1 | 2.00% | -3 | -67 | 8% | -457 | -188 | 6 | 50% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_r2.0 | US500 | M30 | 1.00% | -3 | -69 | 25% | -554 | -99 | 35 | 49% | ok |
| d1_breakout:n20_trail_atr3.0_sidesboth | US500 | D1 | 0.25% | -3 | -69 | 46% | -233 | -100 | 22 | 23% | ok |
| turtle_soup:n10_modelong_hold10_exit_rulepdh | USTEC | D1 | 1.00% | -3 | -70 | 21% | -481 | -173 | 27 | 37% | ok |
| first_last:thresh_atr0.3_modemom_entry_hm2130 | US500 | M30 | 1.50% | -3 | -71 | 46% | -518 | -150 | 195 | 51% | ok |
| first_last:thresh_atr0.2_modefade | USTEC | M30 | 0.75% | -3 | -73 | 50% | -543 | -75 | 255 | 46% | ok |
| h4_dip:n6_exit_rulenhigh | US30 | H4 | 0.50% | -3 | -76 | 38% | -588 | -106 | 168 | 39% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_rNone | US30 | M30 | 0.25% | -3 | -79 | 46% | -373 | -49 | 215 | 43% | ok |
| pdh_break:sidesboth_stopatr_tp_rNone | US30 | M30 | 0.50% | -3 | -81 | 46% | -421 | -65 | 190 | 48% | ok |
| asia_break:tp_rNone_trendNone | USTEC | H1 | 0.25% | -3 | -82 | 46% | -543 | -25 | 191 | 41% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr2.0 | US500 | H1 | 2.00% | -3 | -82 | 21% | -282 | -114 | 14 | 36% | ok |
| h4_dip:n8_exit_rulenhigh | US30 | H4 | 0.25% | -3 | -83 | 42% | -334 | -49 | 57 | 30% | ok |
| round:stepsmall_modebreak_tp_r1.5 | US30 | M30 | 0.25% | -4 | -86 | 46% | -309 | -36 | 176 | 49% | ok |
| hour_window:entry_hour18_exit_hour19_sideshort_sl_atr0.6 | US30 | H1 | 1.25% | -4 | -88 | 62% | -558 | -121 | 425 | 48% | ok |
| gap_struct:whereoutside_modecont_gmin0.4 | USTEC | M30 | 0.50% | -4 | -90 | 42% | -383 | -65 | 97 | 52% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_sideslong | US30 | M30 | 0.50% | -4 | -91 | 54% | -538 | -99 | 175 | 50% | ok |
| round:stepsmall_modebreak_tp_rNone | US500 | M30 | 0.25% | -4 | -93 | 54% | -580 | -32 | 320 | 45% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone | USTEC | M30 | 0.50% | -4 | -96 | 42% | -598 | -84 | 267 | 50% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone | USTEC | M30 | 0.25% | -4 | -97 | 33% | -338 | -66 | 265 | 48% | ok |
| first_hour:modecont_thresh_atr0.3_trendwith | US500 | M30 | 0.50% | -4 | -98 | 46% | -418 | -50 | 55 | 51% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.25 | USTEC | M30 | 0.75% | -4 | -98 | 54% | -485 | -75 | 102 | 55% | ok |
| round:stepsmall_modebreak_tp_rNone | US30 | M30 | 0.25% | -4 | -99 | 42% | -323 | -36 | 175 | 48% | ok |
| h4_pullback:sideslong_trailTrue | US500 | H4 | 0.50% | -4 | -100 | 25% | -430 | -97 | 82 | 23% | ok |
| pdh_break:sideslong_stopmid_trendwith | USTEC | M30 | 1.00% | -4 | -100 | 33% | -483 | -100 | 79 | 57% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | US500 | H4 | 0.25% | -4 | -101 | 42% | -362 | -60 | 85 | 34% | ok |
| h4_dip:n6_exit_rulehold | US30 | H4 | 0.25% | -4 | -102 | 33% | -299 | -56 | 63 | 25% | ok |
| asia_break:tp_r1.5_trendwith | US30 | H1 | 0.75% | -4 | -103 | 54% | -586 | -75 | 132 | 45% | ok |
| opex:modelong_after_sl_atr1.5_trendwith | US500 | D1 | 2.00% | -4 | -103 | 29% | -534 | -222 | 13 | 54% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_sideslong | US500 | M30 | 0.25% | -4 | -104 | 54% | -338 | -64 | 228 | 51% | ok |
| gap_struct:whereoutside_modecont_gmin0.2 | USTEC | M30 | 0.50% | -4 | -104 | 46% | -430 | -65 | 141 | 52% | ok |
| gap_struct:whereoutside_modecont_gmin0.3_sl_atr0.8 | US30 | M30 | 0.75% | -4 | -105 | 29% | -398 | -66 | 100 | 51% | ok |
| nr_break:modeinside_stopfar_tp_rNone_trendwith | USTEC | M30 | 2.00% | -4 | -106 | 29% | -319 | -187 | 23 | 57% | ok |
| round:stepsmall_modebreak_tp_r1.5 | US500 | M30 | 0.25% | -4 | -107 | 50% | -469 | -32 | 320 | 46% | ok |
| hour_window:entry_hour18_exit_hour21_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -5 | -110 | 46% | -373 | -51 | 413 | 53% | ok |
| pdh_break:sideslong_stopmid_end_hm1800 | US30 | M30 | 0.50% | -5 | -110 | 42% | -531 | -76 | 78 | 44% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendNone | US500 | M30 | 0.50% | -5 | -110 | 46% | -569 | -50 | 208 | 57% | ok |
| turtle_soup:n20_modelong_hold3_exit_rulehold_sl_pad0.5 | US500 | D1 | 1.00% | -5 | -110 | 25% | -423 | -258 | 22 | 50% | ok |
| capitulation:drop_atr1.5_exit_rulehold_vol_mult1.0 | US30 | D1 | 2.00% | -5 | -111 | 33% | -573 | -240 | 21 | 52% | ok |
| orb:or_bars2_rvol_min1.5_stopmid_tp_rNone | US500 | M30 | 0.75% | -5 | -112 | 25% | -537 | -75 | 35 | 46% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | US30 | H4 | 0.50% | -5 | -113 | 38% | -437 | -86 | 61 | 34% | ok |
| fomc:modepost_fade_sl_atr0.7 | US30 | M30 | 2.00% | -5 | -114 | 21% | -192 | -178 | 13 | 38% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendwith | US500 | M30 | 0.25% | -5 | -114 | 46% | -302 | -25 | 101 | 51% | ok |
| hour_window:entry_hour18_exit_hour21_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -5 | -117 | 50% | -439 | -82 | 394 | 52% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_trendwith | US500 | M30 | 0.25% | -5 | -117 | 50% | -460 | -64 | 225 | 49% | ok |
| nr_break:modenr7_stopmid_tp_r2.0 | USTEC | M30 | 1.00% | -5 | -118 | 29% | -514 | -98 | 46 | 54% | ok |
| capitulation:drop_atr1.5_exit_rulehold | USTEC | D1 | 1.50% | -5 | -119 | 21% | -508 | -144 | 11 | 55% | ok |
| pdh_break:sideslong_stoplevel_tp_r2.0 | US500 | M30 | 0.25% | -5 | -124 | 42% | -316 | -43 | 122 | 41% | ok |
| prev_week:modebreak_stopatr_sideslong | US30 | H1 | 0.25% | -5 | -124 | 21% | -280 | -111 | 41 | 17% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone | US500 | M30 | 0.25% | -5 | -125 | 50% | -410 | -41 | 302 | 48% | ok |
| capitulation:drop_atr1.5_exit_rulepdh | USTEC | D1 | 1.50% | -5 | -126 | 17% | -521 | -118 | 13 | 54% | ok |
| pdl_sweep:tppd_mid_sidesshort_sl_pad0.1 | USTEC | M30 | 0.25% | -5 | -127 | 33% | -314 | -25 | 125 | 39% | ok |
| prev_week:modebreak_stopmid_sidesboth | US30 | H1 | 0.50% | -5 | -128 | 17% | -265 | -64 | 14 | 36% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | US30 | H1 | 1.25% | -5 | -128 | 38% | -411 | -127 | 35 | 46% | ok |
| first_last:thresh_atr0.4_modefade | USTEC | M30 | 1.00% | -5 | -129 | 46% | -549 | -96 | 161 | 47% | ok |
| hour_window:entry_hour16_exit_hour22_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -5 | -130 | 38% | -427 | -58 | 414 | 50% | ok |
| tom:days_before5_days_after2_sl_atr1.5 | US500 | D1 | 1.25% | -5 | -131 | 54% | -502 | -142 | 22 | 41% | ok |
| prev_week:modebreak_stopatr_sideslong | US30 | H4 | 0.50% | -5 | -131 | 29% | -304 | -90 | 39 | 38% | ok |
| h4_pullback:sideslong_trailFalse_tp_r2.0 | US500 | H4 | 0.50% | -5 | -131 | 33% | -451 | -120 | 55 | 35% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | US500 | H1 | 0.25% | -5 | -132 | 46% | -574 | -73 | 215 | 36% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r1.0 | US500 | M30 | 0.25% | -5 | -132 | 54% | -305 | -57 | 302 | 50% | ok |
| pdh_break:sidesboth_stoplevel_tp_rNone | US500 | M30 | 0.25% | -6 | -134 | 38% | -487 | -45 | 209 | 36% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendNone | USTEC | M30 | 0.25% | -6 | -134 | 42% | -318 | -36 | 195 | 50% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_r2.0 | US30 | M30 | 1.25% | -6 | -136 | 8% | -503 | -125 | 7 | 43% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_rNone | US30 | M30 | 1.25% | -6 | -136 | 8% | -503 | -125 | 7 | 43% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r2.0 | US30 | M30 | 1.50% | -6 | -138 | 8% | -579 | -147 | 7 | 43% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_rNone | US30 | M30 | 1.50% | -6 | -138 | 8% | -579 | -147 | 7 | 43% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r3.0 | US30 | M30 | 1.50% | -6 | -138 | 8% | -579 | -147 | 7 | 43% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | US30 | M30 | 0.50% | -6 | -138 | 42% | -402 | -65 | 190 | 48% | ok |
| first_last:thresh_atr0.2_modemom | US30 | M30 | 0.50% | -6 | -140 | 33% | -392 | -41 | 257 | 46% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.25 | US500 | M30 | 0.75% | -6 | -141 | 42% | -531 | -75 | 98 | 51% | ok |
| prev_week:modefade_sidesboth | US500 | H1 | none | -6 | -141 | 38% | -716 | -127 | 74 | 23% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | US30 | H1 | 0.25% | -6 | -141 | 33% | -398 | -67 | 110 | 33% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold_tp_r2.0 | US500 | D1 | 1.00% | -6 | -143 | 29% | -578 | -132 | 24 | 38% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condbelow_pdc | US30 | H1 | 1.25% | -6 | -143 | 50% | -530 | -180 | 216 | 49% | ok |
| nr_break:modenr7_stopfar_tp_rNone_trendwith | US30 | M30 | 1.25% | -6 | -145 | 29% | -458 | -101 | 32 | 44% | ok |
| pdh_break:sideslong_stoplevel_tp_rNone | US500 | M30 | 0.25% | -6 | -145 | 46% | -325 | -43 | 122 | 40% | ok |
| fomc:modepost_mom_sl_atr0.7 | US30 | H1 | 2.00% | -6 | -146 | 21% | -178 | -160 | 13 | 38% | ok |
| first_last:thresh_atr0.4_modemom | USTEC | M30 | 0.75% | -7 | -157 | 33% | -564 | -74 | 161 | 48% | ok |
| nr_break:modeinside_stopfar_tp_r2.0 | USTEC | M30 | 2.00% | -7 | -158 | 38% | -485 | -187 | 38 | 55% | ok |
| nr_break:modeinside_stopfar_tp_rNone | USTEC | M30 | 2.00% | -7 | -158 | 38% | -485 | -187 | 38 | 55% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r2.0 | US30 | M30 | 0.25% | -7 | -159 | 50% | -344 | -49 | 215 | 44% | ok |
| gap_struct:whereinside_modecont_gmin0.2 | USTEC | M30 | 0.50% | -7 | -159 | 46% | -518 | -50 | 111 | 50% | ok |
| hour_window:entry_hour16_exit_hour22_sidelong_sl_atr0.6 | USTEC | H1 | 0.25% | -7 | -160 | 33% | -298 | -47 | 177 | 51% | ok |
| capitulation:drop_atr1.5_exit_rulehold | US500 | D1 | 1.25% | -7 | -161 | 12% | -555 | -148 | 11 | 45% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_r2.0 | USTEC | M30 | 0.25% | -7 | -161 | 33% | -422 | -49 | 339 | 43% | ok |
| fomc:modepost_mom_sl_atr0.7 | US500 | M30 | 2.00% | -7 | -161 | 25% | -309 | -195 | 12 | 50% | ok |
| h4_pullback:sidesboth_trailTrue | US500 | H4 | 0.25% | -7 | -164 | 33% | -306 | -49 | 130 | 24% | ok |
| first_hour:modecont_thresh_atr0.5 | US500 | M30 | 0.50% | -7 | -165 | 25% | -400 | -50 | 32 | 44% | ok |
| first_last:thresh_atr0.2_modefade | US30 | M30 | 1.25% | -7 | -166 | 54% | -576 | -120 | 265 | 52% | ok |
| first_last:thresh_atr0.4_modemom | US500 | M30 | 1.00% | -7 | -167 | 46% | -572 | -98 | 144 | 42% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendwith | US500 | M30 | 0.25% | -7 | -168 | 33% | -301 | -25 | 67 | 46% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendNone | US500 | M30 | 0.25% | -7 | -169 | 42% | -324 | -25 | 212 | 51% | ok |
| hour_window:entry_hour15_exit_hour16_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -7 | -171 | 46% | -439 | -49 | 408 | 51% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.3 | US500 | H1 | 0.25% | -7 | -172 | 50% | -411 | -47 | 421 | 49% | ok |
| prev_week:modebreak_stopmid_sideslong | US30 | H1 | 1.25% | -7 | -172 | 42% | -466 | -127 | 38 | 47% | ok |
| turtle_soup:n20_modelong_hold5_exit_rulehold | US500 | D1 | 0.50% | -7 | -172 | 21% | -410 | -267 | 24 | 33% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendwith | US500 | M30 | 0.50% | -7 | -174 | 38% | -523 | -50 | 66 | 55% | ok |
| nr_break:modeinside_stopfar_tp_rNone_trendwith | US500 | M30 | 1.50% | -7 | -175 | 25% | -597 | -147 | 23 | 48% | ok |
| gap_struct:whereinside_modecont_gmin0.2 | US30 | M30 | 0.50% | -7 | -175 | 42% | -442 | -83 | 114 | 45% | ok |
| hour_window:entry_hour17_exit_hour18_sideshort_sl_atr0.6 | US30 | H1 | 0.75% | -7 | -177 | 33% | -425 | -61 | 411 | 46% | ok |
| prev_week:modefade_sidesboth | US30 | H1 | 0.25% | -8 | -180 | 33% | -391 | -109 | 54 | 22% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip | USTEC | H1 | 1.00% | -8 | -181 | 38% | -514 | -99 | 97 | 46% | ok |
| first_hour:modecont_thresh_atr0.3_trendwith | US30 | M30 | 0.50% | -8 | -181 | 42% | -419 | -48 | 64 | 38% | ok |
| d1_breakout:n10_trail_atr2.0_squeeze0.8 | US30 | D1 | 2.00% | -8 | -181 | 8% | -393 | -114 | 5 | 40% | ok |
| pdh_break:sideslong_stoplevel_tp_r2.0 | USTEC | M30 | 0.50% | -8 | -181 | 46% | -551 | -50 | 110 | 47% | ok |
| hour_window:entry_hour18_exit_hour21_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | -8 | -181 | 38% | -519 | -64 | 372 | 51% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | USTEC | H1 | 0.50% | -8 | -183 | 42% | -438 | -109 | 76 | 32% | ok |
| first_last:thresh_atr0.2_modefade | US500 | M30 | 0.50% | -8 | -185 | 54% | -400 | -50 | 249 | 50% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendwith | US30 | M30 | 0.50% | -8 | -186 | 33% | -403 | -49 | 114 | 51% | ok |
| hour_window:entry_hour1_exit_hour4_sidelong_sl_atr0.6 | US500 | H1 | 1.00% | -8 | -187 | 50% | -504 | -99 | 425 | 52% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6_trendwith | US500 | H1 | 0.50% | -8 | -187 | 42% | -496 | -50 | 311 | 50% | ok |
| first_hour:modefade_thresh_atr0.5 | US30 | M30 | 0.50% | -8 | -188 | 38% | -424 | -50 | 53 | 43% | ok |
| hour_window:entry_hour21_exit_hour22_sideshort_sl_atr0.6 | USTEC | H1 | 0.75% | -8 | -188 | 54% | -548 | -63 | 408 | 47% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -8 | -189 | 33% | -362 | -50 | 413 | 50% | ok |
| capitulation:drop_atr1.5_exit_rulepdh | US30 | D1 | 2.00% | -8 | -189 | 0% | -505 | -163 | 8 | 38% | ok |
| gap_struct:whereoutside_modefade_gmin0.4 | USTEC | M30 | 0.50% | -8 | -191 | 38% | -431 | -73 | 95 | 44% | ok |
| hour_window:entry_hour16_exit_hour17_sideshort_sl_atr0.6 | USTEC | H1 | 0.75% | -8 | -192 | 46% | -574 | -70 | 423 | 46% | ok |
| prev_week:modefade_sideslong | USTEC | H4 | 0.25% | -8 | -192 | 8% | -241 | -25 | 22 | 14% | ok |
| nr_break:modeinside_stopmid_tp_r2.0 | USTEC | M30 | 2.00% | -8 | -196 | 33% | -550 | -192 | 38 | 55% | ok |
| nr_break:modeinside_stopmid_tp_rNone | USTEC | M30 | 2.00% | -8 | -196 | 33% | -550 | -192 | 38 | 55% | ok |
| fomc:modepre_drift_entry_hour16_sl_atr1.0 | US30 | H1 | 2.00% | -8 | -197 | 25% | -303 | -148 | 14 | 43% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_end_hm1800 | US30 | M30 | 0.75% | -8 | -198 | 38% | -534 | -74 | 82 | 54% | ok |
| capitulation:drop_atr2.5_exit_rulehold | USTEC | D1 | 2.00% | -8 | -199 | 8% | -514 | -144 | 5 | 40% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendNone | USTEC | M30 | 0.25% | -8 | -203 | 46% | -410 | -36 | 197 | 37% | ok |
| orb:or_bars2_rvol_min1.5_stopfar_tp_rNone | US500 | M30 | 0.75% | -8 | -203 | 25% | -527 | -75 | 35 | 49% | ok |
| nr_break:modeinside_stopfar_tp_rNone_trendwith | US30 | M30 | 2.00% | -8 | -203 | 29% | -339 | -179 | 22 | 55% | ok |
| pdh_break:sideslong_stopmid_min_dist0.1 | USTEC | M30 | 1.00% | -8 | -204 | 21% | -574 | -99 | 36 | 56% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendNone | US30 | M30 | 0.50% | -9 | -206 | 33% | -545 | -49 | 111 | 52% | ok |
| pdh_break:sidesboth_stopatr_tp_rNone | US500 | M30 | 0.25% | -9 | -207 | 42% | -319 | -31 | 207 | 43% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -9 | -209 | 42% | -405 | -89 | 407 | 52% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1 | US500 | H1 | 0.75% | -9 | -209 | 50% | -545 | -87 | 91 | 57% | ok |
| capitulation:drop_atr1.5_exit_rulepdh | US500 | D1 | 1.25% | -9 | -209 | 8% | -589 | -124 | 13 | 46% | ok |
| prev_week:modefade_sidesboth | USTEC | H4 | 0.25% | -9 | -210 | 29% | -338 | -99 | 52 | 21% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_down | USTEC | H1 | 1.50% | -9 | -210 | 50% | -526 | -142 | 193 | 50% | ok |
| gap_struct:whereoutside_modecont_gmin0.2 | US500 | M30 | 0.25% | -9 | -211 | 42% | -426 | -47 | 133 | 48% | ok |
| capitulation:drop_atr1.5_exit_rulehold_vol_mult1.0 | USTEC | D1 | 1.00% | -9 | -211 | 21% | -417 | -70 | 17 | 41% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.25 | US30 | M30 | 1.25% | -9 | -212 | 42% | -558 | -124 | 115 | 53% | ok |
| hour_window:entry_hour14_exit_hour15_sideshort_sl_atr0.6 | US30 | H1 | 0.50% | -9 | -214 | 38% | -425 | -40 | 382 | 45% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendwith | USTEC | M30 | 0.75% | -9 | -216 | 33% | -592 | -75 | 61 | 57% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_rNone | US500 | M30 | 0.50% | -9 | -217 | 21% | -449 | -50 | 44 | 32% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_r2.0 | US500 | M30 | 0.25% | -9 | -217 | 50% | -563 | -64 | 384 | 46% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | -9 | -218 | 42% | -449 | -56 | 372 | 50% | ok |
| round:stepbig_modebounce_tp_r1.5 | US30 | M30 | 0.25% | -9 | -218 | 29% | -320 | -25 | 84 | 43% | ok |
| hour_window:entry_hour14_exit_hour15_sideshort_sl_atr0.6 | USTEC | H1 | 0.75% | -9 | -218 | 38% | -580 | -71 | 425 | 49% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendwith | USTEC | M30 | 0.50% | -9 | -223 | 33% | -405 | -50 | 61 | 49% | ok |
| late_dip:entry_hm1900_thresh_atr0.3_modedip | US500 | M30 | 0.25% | -9 | -223 | 38% | -383 | -27 | 104 | 44% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_trendwith | US30 | M30 | 0.50% | -9 | -225 | 46% | -569 | -99 | 183 | 46% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip | US500 | H1 | 0.75% | -9 | -225 | 42% | -507 | -75 | 97 | 43% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendwith | US30 | M30 | 0.75% | -10 | -229 | 25% | -550 | -74 | 82 | 43% | ok |
| orb:or_bars2_rvol_minNone_stopfar_tp_rNone_trendwith | US30 | M30 | 0.50% | -10 | -230 | 29% | -381 | -90 | 131 | 47% | ok |
| round:stepsmall_modebounce_tp_r1.5 | US30 | M30 | 0.25% | -10 | -230 | 33% | -391 | -43 | 179 | 45% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_sideslong | USTEC | M30 | 0.50% | -10 | -233 | 38% | -580 | -132 | 215 | 53% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendNone | US30 | M30 | 0.75% | -10 | -233 | 33% | -510 | -75 | 115 | 50% | ok |
| hour_window:entry_hour21_exit_hour22_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -10 | -234 | 42% | -410 | -49 | 391 | 50% | ok |
| fomc:modepre_drift_entry_hour20_sl_atr1.0 | US500 | H1 | 2.00% | -10 | -234 | 21% | -555 | -188 | 14 | 36% | ok |
| pdl_sweep:tppd_mid_sidesshort_sl_pad0.1 | US500 | M30 | 0.25% | -10 | -235 | 42% | -363 | -25 | 129 | 46% | ok |
| first_hour:modefade_thresh_atr0.3 | US500 | M30 | 0.25% | -10 | -236 | 25% | -348 | -25 | 112 | 39% | ok |
| late_dip:entry_hm2000_thresh_atr0.3_modedip | USTEC | M30 | 0.50% | -10 | -236 | 42% | -390 | -50 | 113 | 44% | ok |
| fomc:modepost_mom_sl_atr0.7 | USTEC | M30 | 2.00% | -10 | -237 | 25% | -334 | -190 | 13 | 46% | ok |
| nr_break:modeinside_stopfar_tp_r2.0 | US30 | M30 | 1.50% | -10 | -237 | 33% | -455 | -138 | 34 | 53% | ok |
| nr_break:modeinside_stopfar_tp_rNone | US30 | M30 | 1.50% | -10 | -237 | 33% | -455 | -138 | 34 | 53% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_end_hm1800 | USTEC | M30 | 0.25% | -10 | -238 | 29% | -289 | -25 | 63 | 48% | ok |
| h4_pullback:sidesboth_trailFalse_tp_r2.0 | USTEC | H4 | 0.50% | -10 | -238 | 42% | -461 | -114 | 77 | 34% | ok |
| nr_break:modeinside_stopmid_tp_r2.0 | US30 | M30 | 1.00% | -10 | -239 | 29% | -450 | -100 | 35 | 51% | ok |
| hour_window:entry_hour16_exit_hour17_sidelong_sl_atr0.6 | US500 | H1 | 0.50% | -10 | -240 | 42% | -457 | -98 | 426 | 51% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r3.0 | US500 | M30 | 0.50% | -10 | -240 | 12% | -411 | -50 | 44 | 36% | ok |
| nr_break:modenr7_stopmid_tp_rNone | USTEC | M30 | 1.00% | -10 | -240 | 29% | -514 | -98 | 46 | 54% | ok |
| capitulation:drop_atr1.5_exit_rulehold | US30 | D1 | 2.00% | -10 | -241 | 4% | -573 | -240 | 8 | 38% | ok |
| turtle_soup:n20_modelong_hold10_exit_rulepdh | US500 | D1 | 0.50% | -10 | -242 | 29% | -458 | -267 | 23 | 48% | ok |
| h4_pullback:sideslong_fast10_slow30_trailFalse_tp_r2.0 | USTEC | H1 | 0.25% | -10 | -244 | 33% | -484 | -67 | 219 | 34% | ok |
| pdh_break:sideslong_stopmid_tp_r2.0 | USTEC | M30 | 0.75% | -10 | -244 | 42% | -544 | -75 | 109 | 55% | ok |
| hour_window:entry_hour16_exit_hour17_sideshort_sl_atr0.6 | US500 | H1 | 0.25% | -10 | -244 | 46% | -324 | -25 | 425 | 45% | ok |
| pdh_break:sideslong_stopmid_trendwith | US500 | M30 | 0.50% | -10 | -246 | 46% | -441 | -56 | 93 | 48% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_end_hm1800 | US500 | M30 | 0.75% | -10 | -246 | 38% | -593 | -80 | 60 | 53% | ok |
| first_last:thresh_atr0.2_modemom | USTEC | M30 | 0.50% | -10 | -246 | 42% | -534 | -45 | 255 | 49% | ok |
| weekday:enter_dow0_hold1 | USTEC | D1 | 2.00% | -10 | -248 | 58% | -504 | -162 | 95 | 49% | ok |
| pdh_break:sideslong_stopmid_end_hm1800 | US500 | M30 | 0.25% | -10 | -248 | 38% | -305 | -25 | 77 | 42% | ok |
| hour_window:entry_hour17_exit_hour18_sidelong_sl_atr0.6 | US500 | H1 | 0.75% | -10 | -248 | 50% | -500 | -74 | 425 | 51% | ok |
| hour_window:entry_hour1_exit_hour4_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | -10 | -249 | 42% | -484 | -92 | 422 | 51% | ok |
| round:stepbig_modebounce_tp_rNone | US30 | M30 | 0.25% | -10 | -252 | 29% | -389 | -25 | 84 | 40% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_sl_atr0.3 | US500 | M30 | 0.25% | -11 | -252 | 38% | -355 | -25 | 92 | 45% | ok |
| late_dip:entry_hm1900_thresh_atr0.5_modedip | USTEC | M30 | 0.50% | -11 | -256 | 42% | -385 | -50 | 81 | 42% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.25 | USTEC | M30 | 0.50% | -11 | -257 | 38% | -371 | -50 | 101 | 49% | ok |
| hour_window:entry_hour20_exit_hour21_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -11 | -257 | 46% | -293 | -25 | 410 | 48% | ok |
| pdh_break:sidesboth_stopmid_tp_rNone | US500 | M30 | 0.25% | -11 | -257 | 50% | -371 | -42 | 207 | 43% | ok |
| fomc:modepost_mom_sl_atr0.7 | US500 | H1 | 2.00% | -11 | -257 | 12% | -257 | -195 | 12 | 25% | ok |
| first_hour:modefade_thresh_atr0.5 | USTEC | M30 | 0.25% | -11 | -258 | 17% | -275 | -24 | 39 | 36% | ok |
| gap_struct:whereoutside_modecont_gmin0.4 | US30 | M30 | 0.50% | -11 | -259 | 38% | -548 | -50 | 82 | 46% | ok |
| late_dip:entry_hm1900_thresh_atr0.5_modedip | US500 | M30 | 0.50% | -11 | -260 | 33% | -527 | -50 | 80 | 45% | ok |
| d1_breakout:n50_trail_atr2.0 | US30 | D1 | 1.25% | -11 | -261 | 17% | -414 | -88 | 10 | 30% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendNone | US500 | M30 | 0.50% | -11 | -262 | 46% | -542 | -52 | 98 | 49% | ok |
| hour_window:entry_hour9_exit_hour10_sidelong_sl_atr0.6 | US30 | H1 | 1.50% | -11 | -264 | 50% | -511 | -108 | 425 | 51% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_sl_atr0.3 | USTEC | M30 | 0.25% | -11 | -265 | 33% | -331 | -24 | 92 | 38% | ok |
| hour_window:entry_hour18_exit_hour19_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -11 | -268 | 33% | -336 | -25 | 425 | 46% | ok |
| gap_struct:whereoutside_modecont_gmin0.4 | US500 | M30 | 0.25% | -11 | -268 | 38% | -405 | -47 | 88 | 47% | ok |
| hour_window:entry_hour20_exit_hour21_sideshort_sl_atr0.6 | US30 | H1 | 0.75% | -11 | -270 | 38% | -514 | -74 | 395 | 47% | ok |
| round:stepsmall_modebounce_tp_rNone | US30 | M30 | 0.25% | -11 | -271 | 25% | -473 | -43 | 179 | 43% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendwith | US500 | M30 | 0.25% | -11 | -271 | 42% | -392 | -25 | 102 | 49% | ok |
| d1_breakout:n20_trail_atr3.0 | US500 | D1 | 1.00% | -11 | -274 | 38% | -531 | -130 | 13 | 23% | ok |
| late_dip:entry_hm2100_thresh_atr0.3_modedip | US30 | M30 | 0.75% | -12 | -276 | 46% | -440 | -63 | 116 | 45% | ok |
| d1_breakout:n50_trail_atr3.0 | US500 | D1 | 0.75% | -12 | -276 | 29% | -452 | -97 | 12 | 17% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_rNone | US500 | M30 | none | -12 | -278 | 42% | -653 | -76 | 384 | 41% | ok |
| asia_break:tp_r1.0_exit_hour12 | USTEC | H1 | 0.25% | -12 | -278 | 38% | -314 | -25 | 191 | 42% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1_trendNone | USTEC | M30 | 0.25% | -12 | -279 | 38% | -375 | -36 | 197 | 42% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1 | US30 | H1 | 0.50% | -12 | -280 | 46% | -530 | -49 | 88 | 45% | ok |
| d1_breakout:n20_trail_atr3.0_sidesboth | US30 | D1 | 0.75% | -12 | -282 | 4% | -340 | -69 | 4 | 0% | ok |
| late_dip:entry_hm1900_thresh_atr0.5_modedip | US30 | M30 | 0.75% | -12 | -282 | 25% | -455 | -72 | 62 | 44% | ok |
| pdh_break:sideslong_stopmid_tp_rNone | USTEC | M30 | 0.75% | -12 | -284 | 42% | -584 | -75 | 108 | 56% | ok |
| round:stepbig_modebounce_tp_r2.5_sl_atr0.3 | US30 | M30 | 0.25% | -12 | -284 | 29% | -399 | -25 | 124 | 38% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendwith | USTEC | M30 | 0.75% | -12 | -286 | 33% | -546 | -75 | 61 | 56% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | US500 | H1 | 0.25% | -12 | -287 | 38% | -369 | -28 | 161 | 45% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_down | USTEC | H1 | 1.00% | -12 | -292 | 42% | -524 | -161 | 194 | 48% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_trendwith | US500 | M30 | 0.75% | -12 | -292 | 38% | -476 | -75 | 67 | 48% | ok |
| prev_week:modebreak_stopatr_sidesboth | USTEC | H1 | none | -12 | -293 | 29% | -605 | -117 | 73 | 12% | ok |
| pdh_break:sideslong_stopmid | US30 | H1 | 0.75% | -12 | -295 | 54% | -591 | -79 | 78 | 44% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_trendwith | USTEC | M30 | 1.00% | -12 | -296 | 46% | -573 | -99 | 59 | 44% | ok |
| prev_week:modebreak_stopmid_sidesboth | US500 | H4 | 0.25% | -12 | -297 | 33% | -345 | -44 | 77 | 43% | ok |
| prev_week:modebreak_stopmid_sidesboth | US500 | H1 | 0.25% | -12 | -297 | 29% | -343 | -44 | 80 | 42% | ok |
| nr_break:modenr7_stopfar_tp_r2.0 | USTEC | M30 | 1.00% | -12 | -297 | 33% | -435 | -87 | 45 | 53% | ok |
| nr_break:modenr7_stopfar_tp_rNone | USTEC | M30 | 1.00% | -12 | -297 | 33% | -435 | -87 | 45 | 53% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr0.6_condday_down | US500 | H1 | 0.50% | -12 | -298 | 42% | -453 | -99 | 192 | 51% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | US30 | H1 | 0.50% | -12 | -299 | 46% | -466 | -52 | 140 | 45% | ok |
| d1_breakout:n50_trail_atr2.0 | US500 | D1 | 1.50% | -12 | -299 | 29% | -555 | -194 | 14 | 21% | ok |
| pdl_sweep:tpNone_sideslong_sl_pad0.1 | US500 | M30 | 0.50% | -12 | -300 | 42% | -542 | -52 | 98 | 48% | ok |
| fomc:modepost_mom_sl_atr0.7 | USTEC | H1 | 2.00% | -13 | -300 | 25% | -326 | -190 | 13 | 46% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_moderip | US500 | M30 | 1.25% | -13 | -302 | 33% | -503 | -124 | 106 | 40% | ok |
| late_dip:entry_hm2000_thresh_atr0.5_modedip | US30 | M30 | 0.75% | -13 | -303 | 29% | -596 | -72 | 72 | 49% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendwith | US30 | M30 | 0.50% | -13 | -304 | 21% | -505 | -49 | 80 | 49% | ok |
| hour_window:entry_hour20_exit_hour21_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | -13 | -305 | 50% | -552 | -98 | 407 | 48% | ok |
| pdh_break:sidesboth_stopmid_tp_r2.0 | US500 | M30 | 0.25% | -13 | -307 | 50% | -361 | -42 | 207 | 43% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendNone | US500 | M30 | 0.25% | -13 | -308 | 38% | -511 | -25 | 212 | 44% | ok |
| late_dip:entry_hm2100_thresh_atr0.3_modedip | USTEC | M30 | 0.50% | -13 | -308 | 17% | -360 | -49 | 114 | 44% | ok |
| round:stepbig_modebounce_tp_r1.5_trendwith | US500 | M30 | 0.25% | -13 | -308 | 25% | -418 | -25 | 142 | 46% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendwith | US500 | M30 | 0.50% | -13 | -308 | 42% | -568 | -50 | 67 | 54% | ok |
| h4_pullback:sideslong_trailTrue | US30 | H4 | 0.50% | -13 | -308 | 21% | -404 | -89 | 87 | 25% | ok |
| gap_struct:whereoutside_modefade_gmin0.2 | USTEC | M30 | 0.50% | -13 | -310 | 33% | -501 | -73 | 133 | 47% | ok |
| nr_break:modeinside_stopmid_tp_rNone | US30 | M30 | 1.00% | -13 | -311 | 29% | -519 | -100 | 35 | 51% | ok |
| first_hour:modefade_thresh_atr0.3 | USTEC | M30 | 0.25% | -13 | -311 | 25% | -319 | -24 | 102 | 38% | ok |
| pdh_break:sidesboth_stopatr_tp_rNone | USTEC | M30 | 0.50% | -13 | -312 | 46% | -421 | -51 | 191 | 55% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1 | US500 | H1 | 0.50% | -13 | -314 | 46% | -449 | -57 | 91 | 49% | ok |
| hour_window:entry_hour21_exit_hour22_sidelong_sl_atr0.6 | US500 | H1 | 0.25% | -13 | -316 | 38% | -342 | -25 | 409 | 45% | ok |
| hour_window:entry_hour5_exit_hour6_sidelong_sl_atr0.6 | USTEC | H1 | 1.50% | -13 | -318 | 46% | -596 | -87 | 423 | 49% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendwith | US500 | M30 | 0.25% | -13 | -319 | 46% | -443 | -25 | 102 | 42% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_r2.0 | US500 | M30 | none | -13 | -320 | 38% | -635 | -76 | 384 | 42% | ok |
| hour_window:entry_hour16_exit_hour17_sideshort_sl_atr0.6 | US30 | H1 | 0.50% | -13 | -320 | 46% | -561 | -49 | 381 | 48% | ok |
| pdl_sweep:tppd_high_sidesboth_sl_pad0.1_trendwith | US30 | M30 | 0.50% | -13 | -321 | 38% | -492 | -49 | 114 | 43% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_rNone | US500 | M30 | 0.50% | -14 | -328 | 12% | -484 | -50 | 44 | 36% | ok |
| late_dip:entry_hm2000_thresh_atr0.5_modedip | USTEC | M30 | 0.50% | -14 | -328 | 50% | -398 | -50 | 72 | 42% | ok |
| hour_window:entry_hour17_exit_hour18_sidelong_sl_atr0.6 | US30 | H1 | 1.00% | -14 | -330 | 54% | -591 | -95 | 422 | 50% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condbelow_pdc | US30 | H1 | 1.25% | -14 | -333 | 33% | -448 | -108 | 205 | 50% | ok |
| nr_break:modenr7_stopmid_tp_rNone | US30 | M30 | 0.50% | -14 | -336 | 25% | -447 | -51 | 48 | 40% | ok |
| nr_break:modenr7_stopmid_tp_r2.0 | US30 | M30 | 0.50% | -14 | -337 | 25% | -448 | -51 | 48 | 40% | ok |
| pdl_sweep:tppd_close_sideslong_sl_pad0.1_trendNone | USTEC | M30 | 0.50% | -14 | -342 | 46% | -391 | -53 | 102 | 54% | ok |
| pdh_break:sidesboth_stopatr_tp_r2.0 | US500 | M30 | 0.50% | -14 | -343 | 50% | -511 | -65 | 207 | 44% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr1.0_trendwith | US30 | H1 | 1.25% | -14 | -343 | 29% | -390 | -117 | 285 | 51% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1 | US500 | H1 | 0.25% | -14 | -343 | 25% | -475 | -27 | 189 | 50% | ok |
| hour_window:entry_hour18_exit_hour19_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -14 | -343 | 42% | -448 | -49 | 406 | 47% | ok |
| first_hour:modefade_thresh_atr0.5 | US500 | M30 | 0.50% | -14 | -344 | 21% | -439 | -49 | 32 | 38% | ok |
| late_dip:entry_hm2000_thresh_atr0.3_modedip | US500 | M30 | 0.50% | -14 | -344 | 50% | -492 | -50 | 111 | 47% | ok |
| h4_pullback:sideslong_trailFalse_tp_r3.0_sl_atr2.0 | US500 | H4 | 0.50% | -14 | -346 | 25% | -479 | -116 | 44 | 34% | ok |
| h4_pullback:sidesboth_trailTrue | US30 | H1 | none | -14 | -346 | 33% | -619 | -90 | 381 | 24% | ok |
| pdh_break:sideslong_stopmid_tp_r2.0 | US500 | M30 | 0.50% | -15 | -350 | 46% | -489 | -56 | 122 | 46% | ok |
| pdh_break:sideslong_stopatr_tp_rNone | US500 | M30 | 0.75% | -15 | -352 | 50% | -594 | -97 | 122 | 48% | ok |
| pdh_break:sideslong_stopatr_tp_r2.0 | US500 | M30 | 0.75% | -15 | -352 | 50% | -594 | -97 | 122 | 48% | ok |
| weekday:enter_dow0_hold1 | US30 | D1 | 1.25% | -15 | -354 | 50% | -391 | -117 | 86 | 49% | ok |
| hour_window:entry_hour17_exit_hour18_sideshort_sl_atr0.6 | USTEC | H1 | 0.50% | -15 | -356 | 33% | -403 | -38 | 406 | 44% | ok |
| late_dip:entry_hm1900_thresh_atr0.3_modedip | US30 | M30 | 0.50% | -15 | -358 | 29% | -557 | -86 | 111 | 44% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_down | US500 | H1 | 0.75% | -15 | -359 | 42% | -493 | -117 | 192 | 49% | ok |
| hour_window:entry_hour19_exit_hour21_sidelong_sl_atr1.0_trendwith | US500 | H1 | 1.25% | -15 | -359 | 29% | -551 | -193 | 300 | 52% | ok |
| hour_window:entry_hour18_exit_hour19_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | -15 | -360 | 25% | -516 | -41 | 381 | 46% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone | US500 | M30 | none | -15 | -360 | 50% | -648 | -64 | 384 | 46% | ok |
| h4_dip:n8_exit_rulehold_tp_r1.5_max_hold12 | US30 | H4 | 0.50% | -15 | -362 | 42% | -598 | -121 | 155 | 39% | ok |
| hour_window:entry_hour14_exit_hour15_sideshort_sl_atr0.6 | US500 | H1 | 0.50% | -15 | -362 | 33% | -599 | -49 | 427 | 45% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | US500 | H1 | 0.25% | -15 | -363 | 38% | -419 | -51 | 84 | 30% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1 | USTEC | H1 | 0.50% | -15 | -364 | 25% | -446 | -49 | 76 | 42% | ok |
| prev_week:modebreak_stopatr_sidesboth_tp_r2.0 | US500 | H4 | 0.25% | -15 | -364 | 38% | -450 | -39 | 78 | 31% | ok |
| pdh_break:sidesboth_stoplevel_tp_r2.0 | US500 | M30 | 0.25% | -15 | -367 | 46% | -501 | -45 | 209 | 38% | ok |
| first_last:thresh_atr0.4_modefade | US500 | M30 | 0.75% | -15 | -367 | 42% | -527 | -74 | 144 | 47% | ok |
| hour_window:entry_hour18_exit_hour19_sideshort_sl_atr0.6 | US500 | H1 | 0.75% | -15 | -368 | 46% | -553 | -74 | 425 | 46% | ok |
| late_dip:entry_hm2000_thresh_atr0.3_modedip | US30 | M30 | 0.75% | -15 | -369 | 38% | -589 | -72 | 121 | 50% | ok |
| hour_window:entry_hour17_exit_hour18_sideshort_sl_atr0.6 | US500 | H1 | 0.50% | -15 | -369 | 33% | -445 | -50 | 425 | 44% | ok |
| late_dip:entry_hm2100_thresh_atr0.3_modedip | US500 | M30 | 0.50% | -15 | -371 | 42% | -452 | -50 | 111 | 44% | ok |
| pdh_break:sidesboth_stoplevel_tp_r2.0 | USTEC | M30 | 0.25% | -15 | -371 | 33% | -531 | -39 | 186 | 42% | ok |
| gap_struct:whereinside_modefade_gmin0.2 | US500 | M30 | 0.50% | -15 | -372 | 29% | -555 | -49 | 105 | 49% | ok |
| nr_break:modenr7_stopfar_tp_rNone_trendwith | US500 | M30 | 1.50% | -16 | -372 | 25% | -559 | -149 | 28 | 43% | ok |
| hour_window:entry_hour9_exit_hour10_sidelong_sl_atr0.6 | US500 | H1 | 1.00% | -16 | -375 | 42% | -483 | -75 | 425 | 49% | ok |
| prev_week:modebreak_stopmid_sideslong_trendwith | US30 | H4 | 1.25% | -16 | -377 | 33% | -528 | -127 | 33 | 48% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendwith | US30 | M30 | 0.75% | -16 | -379 | 25% | -511 | -74 | 82 | 49% | ok |
| pdl_sweep:tppd_close_sidesboth_sl_pad0.1_trendwith | US30 | M30 | 0.50% | -16 | -379 | 25% | -518 | -49 | 113 | 50% | ok |
| prev_week:modefade_sideslong | USTEC | H1 | 0.50% | -16 | -380 | 17% | -475 | -98 | 35 | 20% | ok |
| gap_struct:whereoutside_modecont_gmin0.3_sl_atr0.8 | US500 | M30 | 0.50% | -16 | -380 | 38% | -537 | -86 | 108 | 47% | ok |
| overnight:sl_atr0.5_tp_r1.0 | USTEC | M30 | 0.25% | -16 | -381 | 33% | -526 | -74 | 270 | 52% | ok |
| gap_struct:whereinside_modecont_gmin0.4 | US500 | M30 | 0.75% | -16 | -384 | 42% | -551 | -75 | 49 | 43% | ok |
| late_dip:entry_hm2100_thresh_atr0.5_modedip | US500 | M30 | 0.75% | -16 | -390 | 29% | -507 | -75 | 81 | 44% | ok |
| pdh_break:sideslong_stopmid_end_hm1800 | USTEC | M30 | 0.75% | -16 | -390 | 38% | -553 | -75 | 66 | 53% | ok |
| late_dip:entry_hm1900_thresh_atr0.3_modedip | USTEC | M30 | 0.50% | -16 | -391 | 33% | -484 | -50 | 110 | 43% | ok |
| pdh_break:sideslong_stopmid_tp_rNone | US500 | M30 | 0.50% | -16 | -392 | 46% | -531 | -56 | 122 | 46% | ok |
| late_dip:entry_hm2000_thresh_atr0.5_modedip | US500 | M30 | 0.75% | -16 | -395 | 33% | -596 | -75 | 76 | 49% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_sl_atr0.3 | US30 | M30 | 0.50% | -17 | -396 | 33% | -576 | -49 | 91 | 47% | ok |
| round:stepbig_modebounce_tp_r1.5 | US500 | M30 | 0.25% | -17 | -398 | 38% | -467 | -25 | 198 | 42% | ok |
| pdh_break:sidesboth_stopmid_tp_r2.0 | USTEC | M30 | 0.75% | -17 | -399 | 50% | -552 | -122 | 191 | 52% | ok |
| round:stepbig_modebounce_tp_rNone | US500 | M30 | none | -17 | -399 | 21% | -609 | -25 | 198 | 41% | ok |
| pdh_break:sideslong_stopmid_min_dist0.1 | US500 | M30 | 0.75% | -17 | -404 | 21% | -577 | -75 | 43 | 44% | ok |
| late_dip:entry_hm2100_thresh_atr0.5_modedip | USTEC | M30 | 0.75% | -17 | -406 | 29% | -437 | -71 | 83 | 43% | ok |
| first_last:thresh_atr0.2_modemom | US500 | M30 | 0.50% | -17 | -406 | 38% | -582 | -50 | 249 | 41% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip | US30 | H1 | 0.50% | -17 | -407 | 38% | -510 | -48 | 96 | 43% | ok |
| first_last:thresh_atr0.4_modefade | US30 | M30 | 1.25% | -17 | -408 | 46% | -527 | -120 | 139 | 53% | ok |
| orb:or_bars1_rvol_min1.5_stopmid_tp_r2.0 | US500 | M30 | 0.50% | -17 | -408 | 17% | -534 | -50 | 44 | 32% | ok |
| hour_window:entry_hour12_exit_hour13_sidelong_sl_atr0.6 | US500 | H1 | 1.25% | -17 | -409 | 38% | -514 | -124 | 426 | 49% | ok |
| hour_window:entry_hour20_exit_hour21_sidelong_sl_atr0.6 | USTEC | H1 | 0.50% | -17 | -410 | 38% | -475 | -50 | 392 | 44% | ok |
| orb:or_bars1_rvol_minNone_stopfar_tp_rNone_last_entry_hm1730 | US500 | M30 | none | -17 | -413 | 46% | -730 | -64 | 307 | 46% | ok |
| orb:or_bars1_rvol_min1.5_stopfar_tp_r2.0 | US500 | M30 | 0.75% | -17 | -415 | 12% | -586 | -75 | 44 | 36% | ok |
| hour_window:entry_hour16_exit_hour22_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | -17 | -416 | 42% | -543 | -69 | 371 | 49% | ok |
| pdh_break:sideslong_stopmid | US500 | H1 | 0.50% | -17 | -418 | 42% | -530 | -50 | 96 | 52% | ok |
| round:stepbig_modebounce_tp_r1.5_trendwith | US30 | M30 | 0.50% | -17 | -419 | 33% | -548 | -49 | 90 | 39% | ok |
| hour_window:entry_hour15_exit_hour16_sidelong_sl_atr0.6 | US500 | H1 | 0.50% | -18 | -424 | 46% | -487 | -48 | 427 | 50% | ok |
| pdh_break:sidesboth_stoplevel_tp_rNone | USTEC | M30 | none | -18 | -426 | 33% | -694 | -39 | 185 | 42% | ok |
| d1_breakout:n20_trail_atr2.0 | US30 | D1 | 1.25% | -18 | -427 | 21% | -576 | -88 | 14 | 29% | ok |
| late_dip:entry_hm2100_thresh_atr0.5_modedip | US30 | M30 | 1.00% | -18 | -427 | 33% | -566 | -84 | 75 | 45% | ok |
| hour_window:entry_hour5_exit_hour6_sidelong_sl_atr0.6 | US500 | H1 | 0.75% | -18 | -433 | 29% | -485 | -45 | 425 | 47% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1_trendNone | USTEC | M30 | 0.50% | -18 | -436 | 42% | -471 | -53 | 102 | 50% | ok |
| nr_break:modenr7_stopfar_tp_r2.0 | US30 | M30 | 1.25% | -18 | -441 | 33% | -558 | -124 | 55 | 44% | ok |
| nr_break:modenr7_stopfar_tp_rNone | US30 | M30 | 1.25% | -18 | -441 | 33% | -558 | -124 | 55 | 44% | ok |
| gap_struct:whereinside_modecont_gmin0.4 | USTEC | M30 | 1.00% | -18 | -442 | 33% | -577 | -99 | 51 | 47% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r1.0 | USTEC | M30 | 0.25% | -19 | -446 | 25% | -558 | -46 | 253 | 48% | ok |
| asia_break:tp_r1.0_exit_hour12 | US30 | H1 | 0.25% | -19 | -450 | 29% | -528 | -31 | 216 | 46% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_moderip | USTEC | M30 | 2.00% | -19 | -451 | 33% | -550 | -194 | 104 | 42% | ok |
| h4_pullback:sidesboth_trailTrue | US30 | H4 | 0.50% | -19 | -453 | 29% | -524 | -89 | 126 | 24% | ok |
| prev_week:modebreak_stopatr_sidesboth | US500 | H4 | 0.25% | -19 | -454 | 25% | -561 | -65 | 78 | 28% | ok |
| asia_break:tp_r1.5_trendNone | US30 | H1 | 0.25% | -19 | -455 | 29% | -562 | -25 | 216 | 39% | ok |
| hour_window:entry_hour19_exit_hour22_sidelong_sl_atr1.0_condday_down | US30 | H1 | 1.25% | -19 | -462 | 38% | -551 | -108 | 202 | 50% | ok |
| hour_window:entry_hour5_exit_hour6_sidelong_sl_atr0.6 | US30 | H1 | 1.50% | -19 | -463 | 33% | -591 | -54 | 425 | 47% | ok |
| late_dip:entry_hm2000_thresh_atr0.4_modedip_trendwith | US30 | M30 | 0.75% | -19 | -467 | 29% | -529 | -72 | 61 | 46% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_rNone | USTEC | M30 | 0.25% | -20 | -470 | 33% | -560 | -46 | 252 | 42% | ok |
| orb:or_bars2_rvol_minNone_stopmid_tp_r2.0 | USTEC | M30 | none | -20 | -473 | 33% | -651 | -46 | 252 | 42% | ok |
| pdh_break:sidesboth_stopmid_tp_rNone | USTEC | M30 | 0.50% | -20 | -473 | 42% | -562 | -78 | 186 | 52% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1 | USTEC | H1 | 0.75% | -20 | -485 | 33% | -596 | -75 | 76 | 45% | ok |
| hour_window:entry_hour21_exit_hour22_sidelong_sl_atr0.6 | US30 | H1 | 0.50% | -20 | -492 | 25% | -518 | -45 | 365 | 44% | ok |
| nr_break:modenr7_stopfar_tp_rNone_trendwith | USTEC | M30 | 1.50% | -21 | -499 | 29% | -517 | -146 | 25 | 52% | ok |
| prev_week:modebreak_stopmid_sideslong | US30 | H4 | 0.75% | -21 | -500 | 12% | -562 | -88 | 18 | 33% | ok |
| asia_break:tp_r1.0_exit_hour12 | US500 | H1 | 0.50% | -21 | -500 | 38% | -584 | -50 | 195 | 45% | ok |
| pdl_sweep:tppd_mid_sidesboth_sl_pad0.1 | US30 | H1 | 0.50% | -21 | -504 | 38% | -584 | -50 | 173 | 51% | ok |
| pdl_sweep:tppd_high_sideslong_sl_pad0.1_trendNone | USTEC | M30 | 0.50% | -21 | -504 | 42% | -543 | -53 | 102 | 45% | ok |
| pdl_sweep:tpNone_sideslong_sl_pad0.1 | USTEC | M30 | 0.50% | -21 | -507 | 38% | -570 | -53 | 102 | 44% | ok |
| h4_pullback:sideslong_trailTrue | US30 | H1 | 0.25% | -22 | -519 | 25% | -595 | -61 | 223 | 22% | ok |
| weekday:enter_dow0_hold1 | US500 | D1 | 1.25% | -22 | -539 | 42% | -591 | -123 | 95 | 45% | ok |
| asia_break:tp_r1.5_trendNone | US500 | H1 | none | -23 | -545 | 25% | -734 | -25 | 195 | 40% | ok |
| round:stepsmall_modebounce_tp_r1.5 | US500 | M30 | none | -23 | -557 | 33% | -662 | -25 | 324 | 43% | ok |
| pdl_sweep:tppd_mid_sideslong_sl_pad0.1 | US30 | H1 | 0.50% | -23 | -563 | 33% | -586 | -49 | 88 | 49% | ok |
| orb:or_bars1_rvol_minNone_stopmid_tp_rNone | USTEC | M30 | none | -24 | -576 | 25% | -766 | -83 | 339 | 41% | ok |
| round:stepbig_modebounce_tp_r2.5_sl_atr0.3 | US500 | M30 | none | -25 | -592 | 33% | -800 | -25 | 198 | 39% | ok |
| prev_week:modebreak_stopatr_sidesboth | US500 | H1 | none | -25 | -597 | 25% | -710 | -93 | 82 | 17% | ok |
| h4_dip:n12_exit_rulenhigh | US30 | H1 | none | -26 | -614 | 29% | -856 | -104 | 468 | 36% | ok |
| round:stepsmall_modebounce_tp_rNone | US500 | M30 | none | -27 | -639 | 33% | -806 | -25 | 324 | 42% | ok |

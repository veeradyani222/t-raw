# search3 / asia_indices â€” JPN225, HK50, CHINA50, AUS200 (round 3, from scratch)

Owner goal: most profit on a FundedNext $10k while never losing $400 in a server day (we design to $300)
and never dropping below $9,200. Judge = `research/prop/harness.py`, window 2024-10-20..2026-10-30
(`PROP_OOS=1`, `split="oos"`), one judge for every run. No statistical gates by design (no IS/OOS split,
no placebo, no skeptic); what stays is the **look-ahead check** and the **300/800 rule**. Every run is on
the harness's fixed-dollar-risk accounting, `best_risk` = highest risk in the ladder with worst day > -3%
and max DD > -6%. A run "passes" if `best_risk` is set and `avg_month > 0`; passing runs are ranked by
`avg_month`.

Scored runs: **1409** (354 pass). Distinct ideas: 21 builders in `strategies.py`
(`build_orb`, `build_orb_fade`, `build_gap_fill`, `build_gap_go`, `build_gap_continuation`,
`build_pdhl_break`, `build_pdhl_fade`, `build_overnight`, `build_hour_drift`, `build_zscore_mr`,
`build_rsi_mr`, `build_daily_mr`, `build_donchian`, `build_weekly_break`, `build_us_follow`,
`build_asia_to_us`, `build_nr_break`, `build_lunch_fade`, `build_round_bounce`,
`build_session_pullback`, `build_prev_session_follow`). Files: `strategies.py` (builders + harness
patches), `batches.py` (every job), `run.py` (scorer, 1 worker; RAM on this laptop is tight),
`check.py` (look-ahead check), `study.py` -> `study_out.txt` (market study), `gen_notes.py` (this file),
`results.jsonl` (every scored run), `candidates.json` (the 8 returned).

## IMPORTANT data event during this round (2026-10-30 11:34-11:49 laptop time)

A fetch rewrote `data/search/hk50-*`, `china50-*`, `aus200-*` and `symbol_specs.json` while the first
sweep was running (JPN225 files were untouched). The new files come from a different feed:

| symbol | before | after |
|---|---|---|
| HK50 | 2019-10-23.., 1 HKD/pt, vol_min 1.0 | **2015-01-02..2026-10-30**, 1 HKD/pt, vol_min 0.1, bars 02:00-21:00 only |
| CHINA50 | 2015/2016.., 26 flat days in window | **2025-09-25..2026-10-30 only** (13 of the 24 window months), 0 flat days |
| AUS200 | 2019-04-29.., contract 10 AUD/pt | **2025-01-02..2026-10-30** (22 of 24 months), contract 1 AUD/pt, vol_min 0.1 |

Everything scored before the rewrite was thrown away (kept for reference as
`results_olddata_20261030.jsonl`, do not use) and **all 1409 runs were re-scored on the new files**
after they had been stable for 15+ minutes. Consequences the reader must keep in mind:
* CHINA50 `avg_month` is over ~13 months, AUS200 over ~22 months, JPN225/HK50 over the full 24.
  The harness divides by months present, so CHINA50 numbers are the least seasoned.
* The old-data sweep had CHINA50 D1 RSI(2) mean reversion as the group leader (+$122/mo, 134 trades,
  2015-sourced data). That history no longer exists in the repo, so it is not claimed here.

## Costs used (monkeypatched in `strategies.py: patch_harness()`)

* `H.SPREAD_FLOOR`: JPN225 10.0, HK50 15.0, CHINA50 10.0, AUS200 2.0 (index points). The bar's own
  spread is used when larger (CHINA50 median 4.5 pts, HK50 7.0, AUS200 1.2 in the new files, so the
  floors bind and are conservative).
* `H.INDICES` += the four symbols -> no $14/lot commission, slippage 1 point per fill (`_pip` = 1.0).
* Profit currency: HKD at a fixed 7.80 (peg), AUD via `audusd-h1.csv` per bar, JPY via the harness's
  USDJPY path. Contract sizes / min lots from `data/search/symbol_specs.json` at run time
  (JPN225 100 JPY/pt, **min lot 1.0** -> at 0.25% risk only stops < ~40 pts fit, which is why JPN225
  intraday trade counts are low at small risks and `best_risk` tends to land at 1-2%).

## Data quality (scored window, after the rewrite; `study.py`)

| symbol | tf | bars | flat days (<5% of median daily range) | gaps > 72h | zero tick_volume |
|---|---|---|---|---|---|
| JPN225 | M30/H1/H4/D1 | 23911/11970/3126/524 | 0 | 1 | 0 |
| HK50 | M30/H1/H4/D1 | 16391/8451/2634/500 | 0 | 11 (HK holidays) | 0 |
| CHINA50 | M30/H1/H4/D1 | 11384/5767/1553/282 | 0 | 1 | 0 |
| AUS200 | M30/H1/H4/D1 | 20049/10461/2792/469 | 0 | 4 | 8703/4518/1193/200 |

AUS200's zero-volume bars are all Jan..Oct 2025: that stretch carries volume in `real_volume` and
`spread=0` (stitched source). Prices are normal (median H1 range 15.9 vs 17.8 pts, only 59 of 4518 bars
have high==low), so they were kept; the spread floor covers the missing spread. A rolling frozen-quote
filter (`_stale`: 3 bars in a row with true range < 3% of the 200-bar median) drops entries on frozen
quotes for every builder (CHINA50 00:00-02:00 server bars are flat placeholders and are never traded).

## Market study (summary of `study_out.txt`, 2022+ where history allows)

Server time is EET (UTC+2 winter / UTC+3 summer). Builders use a DST-free "asia clock" (UTC+2):
Tokyo cash 02:00-08:30, HK 03:30-10:00 (lunch 06:00-07:00), A50 futures 03:00-10:30, Sydney 02:00-08:00
(AUS200 is shifted so Sydney 10:00 always reads 02:00). Each session builder takes `open_h/close_h`.

* **Persistence**: variance ratios < 1 on D1 for all four (D1 ac1: JPN225 -0.07, HK50 -0.03, CHINA50
  -0.15 (13 months), AUS200 -0.18 (22 months)); intraday roughly random (M30/H1 var ratio ~1.0). The
  group is **mean-reverting day to day**, not trending: it drove the RSI(2)/daily-MR family.
* **Weekday**: Monday is the only consistently positive day (JPN225 +29 bp t=3.9, HK50 +15 bp,
  CHINA50 +25 bp, AUS200 +27 bp t=3.3); Friday negative for CHINA50 (-34 bp) and AUS200 (-17 bp).
* **Hours**: JPN225 01:00 pre-open +4 bp (t=5), 16:00 (US pre-market) +1.8 bp; HK50 12:00 +1.5 bp
  (t=2.6, post-close), 07:00 (post-lunch) -2.5 bp; AUS200 00:00-02:00 pre-open positive. Hour-to-next
  hour autocorrelation is ~0 everywhere: no intraday momentum to lean on.
* **Gaps (cash open vs prior cash close)**: median |gap| 60 bp JPN225, 59 bp HK50, 29 bp CHINA50, 37 bp
  AUS200. Same-session fill rate 39-42% JPN225, 51-58% HK50, 61-68% CHINA50, 40-42% AUS200; big gaps
  (> median) fill far less (JPN225 14-16%, AUS200 15-16%, HK50 26-36%, CHINA50 39-58%). Gap sign vs
  rest-of-session: JPN225/AUS200 slightly negative (-0.03/-0.23), i.e. fade bias on AUS200; HK50/CHINA50
  ~0. First-hour vs rest-of-session correlation ~0 to +0.07: open-drive continuation is weak.
* **US dependence**: tested as `build_us_follow` (prior US session move -> same/opposite in Asia) and
  `build_asia_to_us`; nothing survives costs in either direction.

## Sources (practitioner rule sets tested, and what they map to)

* Nikkei225 Gap Continuation EA (mql5 product 187414): gap >= 1% vs prior close, cancelled if price
  retraces half the gap, 10-min opening range break in the gap direction within 90 min, SL opposite OR,
  partial at 1R + break-even, TP 2R, flat 15:25 JST. -> `build_gap_continuation` (M30/H1 OR, 0.5%/1%
  gap, TP 1R/2R, with/without break-even; no partial since the harness has one exit).
  https://www.mql5.com/en/market/product/187414
* HSI first-30-minute candle breakout (TradingView community scripts "HSI1! First 30m Candle Strategy"):
  range 09:15-09:45 HKT, break either side, SL opposite side, TP 1R, one trade/day, skip ranges > 200 pts.
  -> `build_orb` (n_bars=1 on M30 = first 30 min, `tp_r=1`, `sl_mode="opp"`, ATR-relative range filter).
  https://www.tradingview.com/script/m8Vxw0hQ-HSI1-First-30m-Candle-Strategy-15m-Chart
* Overnight drift literature: Boyarchenko/Larsen/Whelan "The Overnight Drift" (NY Fed SR 917);
  Sydney Futures Exchange research note (positive overnight SPI return, 1997); Milliman 2024 overnight
  futures risk paper (includes SPI 200). -> `build_overnight` (in at cash close, out at next cash open,
  with/without prior-session filter and Friday skip).
  https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf
  https://researchers.mq.edu.au/en/publications/intraday-returns-and-the-frequency-of-trading-at-the-ask-on-the-s/
* China day/night: Zhang (2020, Economic Modelling) and Diao/Qiu/Tong (2018, CFRI) on T+1 induced
  negative overnight stock returns; index futures (T+0) overnight ~0 or positive. -> informs
  `build_overnight` side tests on CHINA50 and the daily MR focus.
  https://ideas.repec.org/a/eee/ecmode/v89y2020icp55-71.html
  https://emerald.com/insight/content/doi/10.1108/CFRI-12-2016-0130/full/html
* Opening range breakout methodology write-ups (Backtests Not Signals substack, proptraderedge):
  ORB with trend filter / dynamic stop / forced session exit. -> `build_orb`, `build_orb_fade`,
  `build_nr_break` (narrow-range / inside-day breakout variant).
  https://backtestsnotsignals.substack.com/p/opening-range-breakout-real-edge
* Connors RSI(2) (public rule set: RSI(2) < 10 long / > 90 short, exit on RSI cross of 50 or time) ->
  `build_rsi_mr`, swept to 15/85, 20/80, 25/75, 30/70 with and without a 50/100/200 SMA regime filter.

## Look-ahead check (mandatory, `check.py`)

`build(df)` vs `build(df.iloc[:k])` (attrs re-attached) for 5 random k in [n/2, n-10]; every Entry
at index < k compared on (side, sl, tp, max_hold, exit_hour, has-manage, meta). First pass flagged a
real issue: session builders computed `max_hold` by scanning forward to the close bar, so an entry a few
bars before a truncation point got a different `max_hold`. Fixed by making every clock exit a causal
`Entry.manage` (`_exit_at`: close on the first bar whose asia-hour >= target / next-day open) with
`max_hold` only a schedule-based safety cap. After the fix the top 60 passing runs and all 8 returned
candidates pass with zero differences (`check_out.txt`).

## Results by idea (new data; see tables below for every run)

| idea | runs | passing | best passing run (symbol tf, avg/mo $, trades, best_risk) |
|---|---|---|---|
| daily_mr | 144 | 74 | CHINA50 D1, 112, 40, 2.00% |
| rsi_mr | 400 | 170 | AUS200 H4, 88, 191, 1.25% |
| gap_go | 64 | 8 | JPN225 M30, 79, 24, 1.50% |
| donchian | 48 | 3 | CHINA50 D1, 35, 2, 2.00% |
| round_bounce | 32 | 6 | JPN225 H1, 26, 27, 1.00% |
| gap_continuation | 64 | 17 | AUS200 H1, 26, 13, 2.00% |
| zscore_mr | 64 | 17 | JPN225 H1, 25, 34, 1.50% |
| weekly_break | 32 | 2 | JPN225 H1, 25, 5, 1.50% |
| pdhl_break | 64 | 3 | JPN225 M30, 24, 62, 1.50% |
| gap_fill | 64 | 12 | AUS200 H1, 23, 114, 1.50% |
| hour_drift | 37 | 7 | CHINA50 H1, 22, 1, 2.00% |
| nr_break | 24 | 6 | CHINA50 H1, 16, 32, 1.50% |
| orb | 68 | 9 | JPN225 M30, 14, 40, 2.00% |
| prev_session_follow | 64 | 4 | JPN225 M30, 14, 18, 0.50% |
| overnight | 32 | 4 | JPN225 H1, 14, 9, 2.00% |
| lunch_fade | 48 | 6 | JPN225 H1, 12, 54, 1.00% |
| pdhl_fade | 32 | 2 | AUS200 M30, 3, 131, 0.50% |
| us_follow | 16 | 1 | JPN225 H1, 1, 17, 0.75% |
| session_pullback | 32 | 3 | JPN225 H1, 1, 2, 0.50% |
| orb_fade | 64 | 0 | none |
| asia_to_us | 16 | 0 | none |

## Returned candidates (distinct idea or market; all pass the look-ahead check)

| idea | symbol | tf | best_risk | avg/mo $ | net $ | maxDD $ | worst day $ | trades | green mo | params |
|---|---|---|---|---|---|---|---|---|---|---|
| daily_mr | CHINA50 | D1 | 2.00% | 112 | 1574 | -295 | -177 | 40 | 50% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 88 | 1933 | -565 | -245 | 191 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H1 | 1.25% | 82 | 2061 | -241 | -186 | 81 | 28% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| gap_go | JPN225 | M30 | 1.50% | 79 | 1974 | -570 | -135 | 24 | 40% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 82 | 1149 | -482 | -149 | 71 | 50% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| daily_mr | AUS200 | D1 | 2.00% | 63 | 1388 | -355 | -181 | 102 | 73% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 2.00% | 42 | 1046 | -426 | -196 | 19 | 36% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| gap_fill | AUS200 | H1 | 1.50% | 23 | 511 | -533 | -150 | 114 | 59% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |

Reading the table: `best_risk` is the per-trade risk the harness picked; `avg/mo` is on the fixed $10k
baseline (not compounding) over the months the symbol has data in the window.



## Top 40 passing runs (best_risk set and avg_month > 0), ranked by avg_month

| idea | symbol | tf | best_risk | avg/mo $ | net $ | maxDD $ | worst day $ | trades | green mo | params |
|---|---|---|---|---|---|---|---|---|---|---|
| daily_mr | CHINA50 | D1 | 2.00% | 112 | 1574 | -295 | -177 | 40 | 50% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 111 | 1552 | -342 | -177 | 40 | 57% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 105 | 1471 | -334 | -177 | 28 | 43% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 94 | 1315 | -355 | -177 | 28 | 29% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| rsi_mr | AUS200 | H4 | 1.25% | 88 | 1933 | -565 | -245 | 191 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H1 | 1.25% | 82 | 2061 | -241 | -186 | 81 | 28% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H1 | 1.25% | 82 | 2061 | -241 | -186 | 81 | 28% | `{"hi": 75, "lo": 25, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 82 | 1149 | -482 | -149 | 71 | 50% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 2.00% | 81 | 1780 | -443 | -197 | 173 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| daily_mr | CHINA50 | D1 | 2.00% | 81 | 1131 | -514 | -195 | 65 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| gap_go | JPN225 | M30 | 1.50% | 79 | 1974 | -570 | -135 | 24 | 40% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 79 | 1736 | -534 | -245 | 212 | 64% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| daily_mr | CHINA50 | D1 | 2.00% | 74 | 1040 | -600 | -190 | 62 | 50% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 73 | 1022 | -374 | -160 | 44 | 57% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| rsi_mr | AUS200 | H4 | 2.00% | 70 | 1548 | -543 | -200 | 223 | 59% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| daily_mr | CHINA50 | D1 | 2.00% | 68 | 957 | -408 | -157 | 26 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 67 | 938 | -374 | -157 | 26 | 36% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 63 | 1388 | -355 | -181 | 102 | 73% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| rsi_mr | AUS200 | H4 | 1.00% | 62 | 1358 | -547 | -229 | 360 | 64% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 60 | 1326 | -568 | -258 | 438 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| gap_go | JPN225 | M30 | 0.75% | 60 | 1498 | -435 | -73 | 30 | 32% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| rsi_mr | AUS200 | H4 | 2.00% | 60 | 1311 | -479 | -197 | 207 | 59% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| gap_go | JPN225 | M30 | 1.50% | 59 | 1477 | -570 | -146 | 32 | 40% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | JPN225 | M30 | 0.75% | 57 | 1418 | -484 | -73 | 33 | 32% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| rsi_mr | CHINA50 | H4 | 2.00% | 56 | 785 | -520 | -198 | 103 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 56 | 780 | -598 | -190 | 65 | 64% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.50% | 56 | 779 | -567 | -144 | 87 | 57% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| daily_mr | AUS200 | D1 | 1.50% | 56 | 1223 | -597 | -215 | 86 | 55% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 54 | 757 | -302 | -213 | 14 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 53 | 742 | -215 | -157 | 14 | 43% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| rsi_mr | CHINA50 | H4 | 1.50% | 52 | 729 | -506 | -172 | 53 | 64% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.50% | 52 | 1136 | -525 | -233 | 141 | 55% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.50% | 51 | 1124 | -508 | -167 | 516 | 68% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.50% | 48 | 669 | -445 | -109 | 57 | 64% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| daily_mr | AUS200 | D1 | 1.50% | 48 | 1048 | -452 | -131 | 77 | 73% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 48 | 666 | -319 | -127 | 34 | 71% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 48 | 1046 | -582 | -171 | 343 | 68% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.50% | 48 | 1046 | -478 | -264 | 98 | 55% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| daily_mr | AUS200 | D1 | 1.25% | 48 | 1046 | -502 | -179 | 112 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 46 | 647 | -551 | -164 | 44 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |


## Every scored run (1409)

| idea | symbol | tf | best_risk | avg/mo $ | net $ | maxDD $ | worst day $ | trades | green mo | params |
|---|---|---|---|---|---|---|---|---|---|---|
| asia_to_us | AUS200 | H1 | none | -28 | -610 | -833 | -96 | 355 | 36% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | AUS200 | H1 | none | -40 | -873 | -1015 | -96 | 403 | 36% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | AUS200 | H1 | none | -72 | -1584 | -1617 | -96 | 355 | 18% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | AUS200 | H1 | none | -79 | -1749 | -1781 | -96 | 403 | 36% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | CHINA50 | H1 | none | -43 | -605 | -837 | -69 | 262 | 29% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | CHINA50 | H1 | none | -44 | -617 | -770 | -69 | 248 | 29% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | CHINA50 | H1 | none | -110 | -1544 | -1701 | -84 | 248 | 14% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | CHINA50 | H1 | none | -117 | -1642 | -1819 | -84 | 262 | 7% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | HK50 | H1 | none | -11 | -277 | -919 | -299 | 401 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | HK50 | H1 | none | -17 | -414 | -1023 | -299 | 436 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | HK50 | H1 | none | -59 | -1468 | -1807 | -78 | 401 | 36% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | HK50 | H1 | none | -73 | -1815 | -2008 | -78 | 436 | 32% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | JPN225 | H1 | 0.75% | -3 | -74 | -418 | -141 | 35 | 24% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| asia_to_us | JPN225 | H1 | 0.75% | -7 | -165 | -550 | -130 | 34 | 12% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | JPN225 | H1 | 0.75% | -7 | -172 | -438 | -141 | 34 | 20% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| asia_to_us | JPN225 | H1 | 0.75% | -9 | -232 | -550 | -130 | 35 | 12% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| daily_mr | AUS200 | D1 | 2.00% | 63 | 1388 | -355 | -181 | 102 | 73% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.50% | 56 | 1223 | -597 | -215 | 86 | 55% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.50% | 48 | 1048 | -452 | -131 | 77 | 73% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.25% | 48 | 1046 | -502 | -179 | 112 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.00% | 42 | 920 | -516 | -144 | 109 | 68% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 2.00% | 39 | 864 | -576 | -181 | 63 | 64% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 39 | 859 | -507 | -174 | 85 | 64% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.00% | 37 | 821 | -581 | -144 | 81 | 64% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 2.00% | 36 | 799 | -360 | -215 | 46 | 64% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 31 | 688 | -517 | -174 | 42 | 45% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 26 | 579 | -593 | -181 | 110 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | AUS200 | D1 | 1.00% | 23 | 511 | -547 | -144 | 68 | 64% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 22 | 489 | -302 | -174 | 18 | 27% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 1.00% | 15 | 328 | -520 | -144 | 69 | 59% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 14 | 309 | -554 | -215 | 45 | 41% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 1.50% | 12 | 273 | -532 | -215 | 46 | 41% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 12 | 258 | -314 | -215 | 25 | 45% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 9 | 207 | -461 | -174 | 45 | 41% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 1.25% | 9 | 188 | -589 | -179 | 45 | 41% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 2.00% | 8 | 178 | -576 | -181 | 35 | 50% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 1.25% | 6 | 139 | -531 | -179 | 38 | 45% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 1.50% | 5 | 113 | -486 | -141 | 68 | 55% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 1.50% | 5 | 106 | -589 | -215 | 19 | 27% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 2.00% | 4 | 81 | -215 | -215 | 9 | 14% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | D1 | 2.00% | -0 | -3 | -361 | -174 | 19 | 27% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 2.00% | -6 | -124 | -215 | -215 | 7 | 14% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | D1 | 1.50% | -6 | -143 | -581 | -215 | 19 | 27% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 1.50% | -9 | -202 | -544 | -162 | 25 | 27% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | AUS200 | D1 | 1.00% | -12 | -275 | -505 | -144 | 38 | 41% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 1.50% | -18 | -387 | -486 | -141 | 37 | 36% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | AUS200 | D1 | 2.00% | -19 | -414 | -491 | -215 | 9 | 9% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | D1 | 2.00% | -23 | -503 | -580 | -215 | 7 | 9% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | H4 | 1.25% | 30 | 651 | -460 | -271 | 82 | 59% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | H4 | 1.50% | 29 | 631 | -450 | -268 | 82 | 59% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | AUS200 | H4 | 2.00% | 25 | 548 | -495 | -189 | 7 | 18% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | AUS200 | H4 | 2.00% | 16 | 344 | -159 | -92 | 7 | 18% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | CHINA50 | D1 | 2.00% | 112 | 1574 | -295 | -177 | 40 | 50% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 111 | 1552 | -342 | -177 | 40 | 57% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 105 | 1471 | -334 | -177 | 28 | 43% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 94 | 1315 | -355 | -177 | 28 | 29% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 81 | 1131 | -514 | -195 | 65 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 74 | 1040 | -600 | -190 | 62 | 50% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 73 | 1022 | -374 | -160 | 44 | 57% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 68 | 957 | -408 | -157 | 26 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 67 | 938 | -374 | -157 | 26 | 36% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 54 | 757 | -302 | -213 | 14 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 53 | 742 | -215 | -157 | 14 | 43% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 45 | 635 | -283 | -105 | 26 | 36% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 44 | 622 | -190 | -114 | 40 | 50% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 41 | 576 | -220 | -117 | 28 | 36% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 41 | 573 | -205 | -117 | 40 | 57% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 36 | 502 | -220 | -114 | 28 | 36% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 35 | 493 | -435 | -160 | 43 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 32 | 450 | -263 | -120 | 65 | 64% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 32 | 445 | -177 | -89 | 43 | 64% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 30 | 422 | -177 | -75 | 26 | 43% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 27 | 376 | -291 | -114 | 26 | 43% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 24 | 337 | -120 | -75 | 14 | 50% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 23 | 326 | -322 | -114 | 59 | 43% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 23 | 320 | -151 | -107 | 14 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | CHINA50 | D1 | 2.00% | 22 | 309 | -192 | -105 | 16 | 36% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 20 | 284 | -173 | -82 | 27 | 43% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | CHINA50 | D1 | 2.00% | 16 | 219 | -107 | -88 | 5 | 21% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | D1 | 2.00% | 16 | 219 | -107 | -88 | 5 | 21% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | D1 | 2.00% | 12 | 172 | -294 | -114 | 42 | 50% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | CHINA50 | D1 | 2.00% | 10 | 138 | 0 | 0 | 5 | 29% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | D1 | 2.00% | 10 | 138 | 0 | 0 | 5 | 29% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | D1 | 2.00% | 7 | 101 | -88 | -82 | 17 | 43% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | CHINA50 | H4 | 1.00% | -5 | -68 | -496 | -109 | 87 | 57% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | H4 | 0.50% | -15 | -205 | -383 | -59 | 86 | 36% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | CHINA50 | H4 | 1.25% | -22 | -312 | -574 | -110 | 23 | 21% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | CHINA50 | H4 | 1.00% | -25 | -346 | -492 | -88 | 23 | 21% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | HK50 | D1 | 2.00% | 42 | 1046 | -426 | -196 | 19 | 36% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 1.50% | 24 | 591 | -583 | -143 | 59 | 52% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 20 | 505 | -213 | -100 | 19 | 36% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 19 | 472 | -140 | -95 | 10 | 20% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | D1 | 2.00% | 18 | 447 | -416 | -196 | 19 | 24% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 16 | 395 | -114 | -48 | 10 | 20% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | D1 | 2.00% | 15 | 386 | -520 | -193 | 60 | 52% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 11 | 268 | -191 | -95 | 6 | 16% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | D1 | 2.00% | 10 | 257 | -374 | -199 | 59 | 52% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 9 | 224 | -197 | -100 | 19 | 24% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 2.00% | 8 | 189 | -91 | -48 | 6 | 16% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | D1 | 2.00% | 7 | 169 | -493 | -189 | 59 | 44% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 2.00% | 5 | 134 | -317 | -199 | 60 | 48% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | HK50 | D1 | 1.25% | -0 | -9 | -522 | -116 | 118 | 44% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 1.00% | -2 | -47 | -582 | -103 | 56 | 40% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 1.25% | -3 | -67 | -573 | -116 | 84 | 40% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 0.50% | -4 | -91 | -428 | -52 | 124 | 48% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 0.50% | -4 | -108 | -447 | -60 | 91 | 32% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 1.50% | -5 | -117 | -538 | -149 | 52 | 40% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 0.75% | -7 | -186 | -535 | -83 | 88 | 40% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 1.50% | -9 | -226 | -539 | -149 | 83 | 40% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 0.75% | -10 | -238 | -455 | -67 | 57 | 24% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 1.50% | -10 | -245 | -583 | -149 | 132 | 40% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 0.75% | -10 | -251 | -579 | -80 | 133 | 44% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 2.00% | -11 | -266 | -415 | -189 | 26 | 20% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 2.00% | -12 | -293 | -599 | -199 | 91 | 36% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 0.75% | -12 | -294 | -591 | -71 | 58 | 28% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 1.25% | -12 | -311 | -567 | -116 | 57 | 24% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 0.75% | -13 | -336 | -573 | -80 | 91 | 32% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | HK50 | D1 | 0.50% | -14 | -338 | -465 | -60 | 96 | 28% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 1.00% | -16 | -406 | -539 | -100 | 93 | 24% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | HK50 | D1 | 1.25% | -18 | -458 | -556 | -122 | 25 | 16% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | HK50 | H4 | 1.50% | 8 | 199 | -502 | -149 | 16 | 28% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | HK50 | H4 | 0.75% | -2 | -43 | -448 | -117 | 120 | 52% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | H4 | 1.25% | -2 | -51 | -582 | -192 | 122 | 52% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | HK50 | H4 | 1.50% | -3 | -69 | -467 | -149 | 16 | 24% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 1, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "side": "long", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 0.75}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.0}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 1, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3.0, "thr": 1.25}` |
| daily_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 1.5}` |
| daily_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 2, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| daily_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hold": 4, "lb": 1, "side": "both", "sl_atr": 2.0, "thr": 2.5}` |
| donchian | AUS200 | D1 | 1.00% | -0 | -7 | -482 | -156 | 12 | 55% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | AUS200 | D1 | 1.50% | -8 | -182 | -586 | -188 | 5 | 27% | `{"n": 50, "side": "long", "trail": 3.0}` |
| donchian | AUS200 | D1 | 1.50% | -14 | -314 | -594 | -188 | 8 | 41% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | AUS200 | D1 | 1.00% | -16 | -348 | -529 | -113 | 8 | 27% | `{"n": 50, "side": "both", "trail": 3.0}` |
| donchian | AUS200 | H4 | 0.25% | -6 | -137 | -353 | -30 | 66 | 36% | `{"n": 55, "side": "both", "trail": 2.0}` |
| donchian | AUS200 | H4 | 0.25% | -12 | -267 | -328 | -26 | 40 | 14% | `{"n": 55, "side": "long", "trail": 2.0}` |
| donchian | AUS200 | H4 | 0.25% | -14 | -315 | -469 | -45 | 58 | 36% | `{"n": 55, "side": "both", "trail": 3.0}` |
| donchian | AUS200 | H4 | 0.25% | -18 | -385 | -433 | -38 | 36 | 14% | `{"n": 55, "side": "long", "trail": 3.0}` |
| donchian | AUS200 | H4 | 0.25% | -18 | -385 | -444 | -40 | 49 | 27% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | AUS200 | H4 | 0.25% | -18 | -389 | -473 | -28 | 61 | 23% | `{"n": 20, "side": "long", "trail": 2.0}` |
| donchian | AUS200 | H4 | none | -21 | -463 | -640 | -28 | 106 | 41% | `{"n": 20, "side": "both", "trail": 2.0}` |
| donchian | AUS200 | H4 | none | -30 | -650 | -782 | -43 | 92 | 32% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | CHINA50 | D1 | 2.00% | 35 | 491 | -310 | -104 | 2 | 36% | `{"n": 50, "side": "both", "trail": 3.0}` |
| donchian | CHINA50 | D1 | 2.00% | 6 | 84 | -190 | -104 | 1 | 7% | `{"n": 50, "side": "long", "trail": 3.0}` |
| donchian | CHINA50 | D1 | 1.50% | 5 | 64 | -535 | -95 | 6 | 36% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | CHINA50 | D1 | 2.00% | -16 | -226 | -440 | -116 | 3 | 7% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | CHINA50 | H4 | 0.25% | -21 | -299 | -384 | -37 | 44 | 21% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | CHINA50 | H4 | 0.25% | -22 | -302 | -316 | -37 | 52 | 21% | `{"n": 20, "side": "both", "trail": 2.0}` |
| donchian | CHINA50 | H4 | 1.00% | -24 | -330 | -497 | -92 | 15 | 14% | `{"n": 55, "side": "long", "trail": 2.0}` |
| donchian | CHINA50 | H4 | 1.00% | -25 | -345 | -551 | -136 | 12 | 14% | `{"n": 55, "side": "long", "trail": 3.0}` |
| donchian | CHINA50 | H4 | 0.50% | -28 | -389 | -541 | -73 | 26 | 29% | `{"n": 55, "side": "both", "trail": 3.0}` |
| donchian | CHINA50 | H4 | 0.50% | -32 | -449 | -502 | -68 | 24 | 14% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | CHINA50 | H4 | 0.50% | -33 | -459 | -512 | -46 | 29 | 14% | `{"n": 20, "side": "long", "trail": 2.0}` |
| donchian | CHINA50 | H4 | 0.50% | -34 | -475 | -505 | -73 | 32 | 29% | `{"n": 55, "side": "both", "trail": 2.0}` |
| donchian | HK50 | D1 | 1.00% | -4 | -96 | -510 | -107 | 9 | 28% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | HK50 | D1 | 0.50% | -5 | -118 | -387 | -47 | 18 | 40% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | HK50 | D1 | 1.00% | -9 | -226 | -548 | -95 | 6 | 16% | `{"n": 50, "side": "long", "trail": 3.0}` |
| donchian | HK50 | D1 | 0.75% | -11 | -269 | -552 | -71 | 10 | 24% | `{"n": 50, "side": "both", "trail": 3.0}` |
| donchian | HK50 | H4 | 0.50% | -1 | -31 | -434 | -72 | 56 | 40% | `{"n": 20, "side": "long", "trail": 2.0}` |
| donchian | HK50 | H4 | 0.50% | -6 | -155 | -488 | -100 | 46 | 40% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | HK50 | H4 | 0.25% | -7 | -170 | -361 | -33 | 109 | 44% | `{"n": 20, "side": "both", "trail": 2.0}` |
| donchian | HK50 | H4 | 0.25% | -8 | -188 | -300 | -33 | 37 | 20% | `{"n": 55, "side": "long", "trail": 2.0}` |
| donchian | HK50 | H4 | 0.25% | -8 | -209 | -364 | -33 | 62 | 32% | `{"n": 55, "side": "both", "trail": 2.0}` |
| donchian | HK50 | H4 | 0.25% | -9 | -237 | -342 | -50 | 32 | 24% | `{"n": 55, "side": "long", "trail": 3.0}` |
| donchian | HK50 | H4 | 0.25% | -10 | -252 | -473 | -58 | 52 | 36% | `{"n": 55, "side": "both", "trail": 3.0}` |
| donchian | HK50 | H4 | 0.25% | -14 | -345 | -528 | -50 | 92 | 40% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 50, "side": "both", "trail": 3.0}` |
| donchian | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 50, "side": "long", "trail": 3.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "both", "trail": 2.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "long", "trail": 2.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "both", "trail": 3.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 20, "side": "long", "trail": 3.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 55, "side": "both", "trail": 2.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 55, "side": "long", "trail": 2.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 55, "side": "both", "trail": 3.0}` |
| donchian | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"n": 55, "side": "long", "trail": 3.0}` |
| gap_continuation | AUS200 | H1 | 2.00% | 26 | 573 | -470 | -198 | 13 | 14% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 2.00% | 26 | 573 | -470 | -198 | 13 | 14% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 2.00% | 14 | 307 | -354 | -198 | 13 | 14% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 2.00% | 14 | 307 | -354 | -198 | 13 | 14% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 1.50% | 14 | 305 | -583 | -150 | 45 | 36% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 1.50% | 14 | 305 | -583 | -150 | 45 | 36% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 1.50% | 3 | 60 | -586 | -150 | 45 | 36% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | H1 | 1.50% | 3 | 60 | -586 | -150 | 45 | 36% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 0.25% | -13 | -287 | -305 | -25 | 59 | 41% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 0.25% | -13 | -287 | -305 | -25 | 59 | 41% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 1.00% | -14 | -307 | -511 | -100 | 17 | 18% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 1.00% | -14 | -307 | -511 | -100 | 17 | 18% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 0.50% | -17 | -369 | -489 | -50 | 59 | 50% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 0.50% | -17 | -369 | -489 | -50 | 59 | 50% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 1.00% | -21 | -466 | -511 | -100 | 17 | 18% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | AUS200 | M30 | 1.00% | -21 | -466 | -511 | -100 | 17 | 18% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -16 | -218 | -272 | -199 | 5 | 7% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -16 | -218 | -272 | -199 | 5 | 7% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -16 | -218 | -272 | -199 | 5 | 7% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -16 | -218 | -272 | -199 | 5 | 7% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -23 | -319 | -340 | -199 | 17 | 29% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -23 | -319 | -340 | -199 | 17 | 29% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -26 | -360 | -381 | -199 | 17 | 29% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | H1 | 2.00% | -26 | -360 | -381 | -199 | 17 | 29% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | 10 | 136 | -499 | -195 | 26 | 64% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | 10 | 136 | -499 | -195 | 26 | 64% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | 8 | 105 | -499 | -195 | 26 | 64% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | 8 | 105 | -499 | -195 | 26 | 64% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | -6 | -89 | -359 | -195 | 10 | 21% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | -6 | -89 | -359 | -195 | 10 | 21% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | -19 | -261 | -359 | -195 | 10 | 14% | `{"be_at_1r": true, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | CHINA50 | M30 | 2.00% | -19 | -261 | -359 | -195 | 10 | 14% | `{"be_at_1r": false, "close_h": 9.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 0.75% | -15 | -387 | -537 | -75 | 66 | 36% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 0.75% | -15 | -387 | -537 | -75 | 66 | 36% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 1.25% | -16 | -391 | -527 | -124 | 29 | 24% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 1.25% | -16 | -391 | -527 | -124 | 29 | 24% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 1.25% | -16 | -391 | -513 | -124 | 29 | 24% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 1.25% | -16 | -391 | -513 | -124 | 29 | 24% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 0.75% | -16 | -405 | -551 | -75 | 66 | 32% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | H1 | 0.75% | -16 | -405 | -551 | -75 | 66 | 32% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 0.50% | -12 | -298 | -406 | -50 | 77 | 36% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 0.50% | -12 | -298 | -406 | -50 | 77 | 36% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 0.50% | -15 | -364 | -424 | -50 | 77 | 36% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 0.50% | -15 | -364 | -424 | -50 | 77 | 36% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 1.00% | -16 | -402 | -555 | -99 | 40 | 32% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 1.00% | -16 | -402 | -555 | -99 | 40 | 32% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 2.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 1.00% | -16 | -404 | -568 | -99 | 40 | 36% | `{"be_at_1r": true, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | HK50 | M30 | 1.00% | -16 | -404 | -568 | -99 | 40 | 36% | `{"be_at_1r": false, "close_h": 10.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 3.5, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | 4 | 90 | -417 | -130 | 11 | 20% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | 4 | 90 | -417 | -130 | 11 | 20% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -3 | -72 | -417 | -130 | 11 | 16% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -4 | -88 | -427 | -130 | 11 | 16% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -7 | -183 | -252 | -111 | 4 | 0% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -7 | -183 | -252 | -111 | 4 | 0% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -7 | -183 | -252 | -111 | 4 | 0% | `{"be_at_1r": false, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | H1 | 2.00% | -7 | -183 | -252 | -111 | 4 | 0% | `{"be_at_1r": true, "close_h": 8.0, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | 16 | 409 | -542 | -195 | 28 | 28% | `{"be_at_1r": true, "close_h": 8.5, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | 16 | 409 | -542 | -195 | 28 | 28% | `{"be_at_1r": false, "close_h": 8.5, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 1.50% | 0 | 3 | -585 | -146 | 18 | 12% | `{"be_at_1r": true, "close_h": 8.5, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | -7 | -177 | -490 | -188 | 16 | 20% | `{"be_at_1r": false, "close_h": 8.5, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | -8 | -201 | -514 | -188 | 16 | 16% | `{"be_at_1r": true, "close_h": 8.5, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | -12 | -305 | -423 | -188 | 16 | 20% | `{"be_at_1r": true, "close_h": 8.5, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 2.00% | -12 | -305 | -423 | -188 | 16 | 20% | `{"be_at_1r": false, "close_h": 8.5, "min_gap_pct": 1.0, "n_bars": 1, "open_h": 2.0, "tp_r": 1.0, "window": 3}` |
| gap_continuation | JPN225 | M30 | 1.25% | -13 | -324 | -554 | -104 | 10 | 12% | `{"be_at_1r": false, "close_h": 8.5, "min_gap_pct": 0.5, "n_bars": 1, "open_h": 2.0, "tp_r": 2.0, "window": 3}` |
| gap_fill | AUS200 | H1 | 1.50% | 23 | 511 | -533 | -150 | 114 | 59% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | H1 | 1.25% | 15 | 326 | -501 | -125 | 104 | 64% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | H1 | 0.75% | -2 | -43 | -450 | -75 | 104 | 50% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | H1 | 0.50% | -5 | -102 | -409 | -50 | 212 | 59% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | H1 | 1.00% | -12 | -262 | -599 | -100 | 114 | 45% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | H1 | 0.25% | -14 | -311 | -501 | -28 | 212 | 55% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | H1 | 0.50% | -16 | -358 | -503 | -50 | 245 | 55% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | H1 | 0.25% | -21 | -466 | -554 | -28 | 245 | 41% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | M30 | 2.00% | 20 | 449 | -495 | -199 | 61 | 77% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | M30 | 2.00% | 16 | 354 | -495 | -200 | 64 | 73% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | M30 | 1.50% | 13 | 280 | -562 | -150 | 61 | 59% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | M30 | 0.50% | -6 | -127 | -423 | -50 | 159 | 55% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | M30 | 1.50% | -8 | -169 | -562 | -150 | 64 | 59% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | M30 | 0.25% | -11 | -240 | -373 | -25 | 178 | 55% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | AUS200 | M30 | 0.25% | -15 | -333 | -412 | -25 | 159 | 41% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | AUS200 | M30 | 0.25% | -23 | -505 | -578 | -25 | 178 | 32% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | H1 | 0.25% | -22 | -303 | -396 | -25 | 117 | 43% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | H1 | 0.25% | -22 | -312 | -312 | -25 | 29 | 21% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | H1 | 1.25% | -23 | -318 | -490 | -123 | 27 | 50% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | H1 | 1.00% | -31 | -436 | -577 | -99 | 30 | 57% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | H1 | 0.50% | -37 | -512 | -540 | -50 | 27 | 21% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | H1 | 0.25% | -38 | -535 | -556 | -25 | 138 | 21% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | H1 | none | -71 | -997 | -1027 | -25 | 121 | 7% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | H1 | none | -103 | -1436 | -1456 | -25 | 142 | 0% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | M30 | 2.00% | 13 | 179 | -351 | -193 | 20 | 57% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | M30 | 2.00% | 13 | 179 | -351 | -193 | 20 | 57% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | M30 | 0.25% | -16 | -229 | -316 | -25 | 86 | 50% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | M30 | 1.00% | -27 | -377 | -509 | -97 | 20 | 43% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | M30 | 1.00% | -27 | -377 | -509 | -97 | 20 | 43% | `{"close_h": 9.0, "confirm": true, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | M30 | 0.25% | -33 | -468 | -533 | -25 | 98 | 36% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | CHINA50 | M30 | none | -42 | -582 | -725 | -25 | 86 | 29% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | CHINA50 | M30 | none | -62 | -864 | -984 | -25 | 98 | 21% | `{"close_h": 9.0, "confirm": false, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | HK50 | H1 | 1.50% | -11 | -284 | -534 | -149 | 83 | 52% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | HK50 | H1 | 1.25% | -12 | -306 | -529 | -125 | 87 | 52% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | HK50 | H1 | 0.25% | -14 | -340 | -349 | -25 | 83 | 20% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | HK50 | H1 | 0.25% | -16 | -409 | -421 | -25 | 87 | 20% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | HK50 | H1 | none | -22 | -556 | -644 | -25 | 264 | 36% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | HK50 | H1 | none | -23 | -575 | -641 | -25 | 238 | 28% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 2.0}` |
| gap_fill | HK50 | H1 | none | -44 | -1109 | -1201 | -25 | 238 | 24% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.6, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | HK50 | H1 | none | -51 | -1274 | -1404 | -25 | 264 | 20% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.3, "open_h": 3.0, "sl_mult": 1.0}` |
| gap_fill | HK50 | M30 | 1.50% | -5 | -136 | -497 | -150 | 57 | 48% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | HK50 | M30 | 1.25% | -14 | -358 | -537 | -125 | 59 | 40% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | HK50 | M30 | 0.50% | -19 | -465 | -481 | -50 | 59 | 32% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | HK50 | M30 | 0.25% | -21 | -520 | -544 | -61 | 185 | 28% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | HK50 | M30 | 0.75% | -22 | -547 | -572 | -75 | 57 | 32% | `{"close_h": 10.0, "confirm": true, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | HK50 | M30 | none | -36 | -903 | -920 | -61 | 210 | 20% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 2.0}` |
| gap_fill | HK50 | M30 | none | -41 | -1032 | -1066 | -25 | 185 | 16% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.6, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | HK50 | M30 | none | -57 | -1416 | -1450 | -25 | 210 | 16% | `{"close_h": 10.0, "confirm": false, "min_gap": 0.3, "open_h": 3.5, "sl_mult": 1.0}` |
| gap_fill | JPN225 | H1 | 1.50% | 1 | 29 | -252 | -129 | 7 | 16% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | H1 | 0.50% | -8 | -198 | -198 | -49 | 8 | 8% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | H1 | 1.00% | -9 | -221 | -221 | -92 | 8 | 8% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | H1 | 0.75% | -12 | -301 | -301 | -74 | 6 | 4% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | H1 | 2.00% | -16 | -405 | -436 | -189 | 12 | 20% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | H1 | 1.00% | -17 | -414 | -496 | -98 | 11 | 12% | `{"close_h": 8.0, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | H1 | 1.50% | -18 | -448 | -456 | -148 | 13 | 20% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | H1 | 0.75% | -23 | -565 | -565 | -74 | 10 | 4% | `{"close_h": 8.0, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | M30 | 2.00% | 11 | 269 | -255 | -192 | 19 | 48% | `{"close_h": 8.5, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | M30 | 2.00% | 10 | 239 | -255 | -192 | 18 | 44% | `{"close_h": 8.5, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | M30 | 0.75% | 3 | 63 | -521 | -73 | 29 | 24% | `{"close_h": 8.5, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | M30 | 1.25% | 1 | 20 | -540 | -123 | 25 | 20% | `{"close_h": 8.5, "confirm": false, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_fill | JPN225 | M30 | 1.25% | -2 | -43 | -449 | -118 | 28 | 36% | `{"close_h": 8.5, "confirm": true, "min_gap": 0.3, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | M30 | 1.25% | -3 | -73 | -449 | -118 | 27 | 32% | `{"close_h": 8.5, "confirm": true, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | M30 | 0.75% | -12 | -300 | -482 | -73 | 15 | 12% | `{"close_h": 8.5, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 1.0}` |
| gap_fill | JPN225 | M30 | 1.25% | -12 | -307 | -411 | -115 | 13 | 8% | `{"close_h": 8.5, "confirm": false, "min_gap": 0.6, "open_h": 2.0, "sl_mult": 2.0}` |
| gap_go | AUS200 | H1 | 0.25% | -6 | -123 | -332 | -25 | 166 | 36% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | AUS200 | H1 | 0.50% | -9 | -197 | -439 | -50 | 166 | 45% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | AUS200 | H1 | 0.25% | -10 | -209 | -463 | -25 | 166 | 45% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | AUS200 | H1 | 0.25% | -10 | -227 | -316 | -25 | 189 | 45% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | AUS200 | H1 | 0.75% | -11 | -231 | -485 | -75 | 166 | 55% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | AUS200 | H1 | 0.25% | -12 | -269 | -429 | -25 | 189 | 32% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | AUS200 | H1 | 0.25% | -13 | -280 | -337 | -25 | 189 | 41% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | AUS200 | H1 | 0.25% | -18 | -390 | -538 | -25 | 189 | 36% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | AUS200 | M30 | 0.25% | -12 | -256 | -295 | -25 | 200 | 41% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | AUS200 | M30 | none | -12 | -272 | -769 | -55 | 216 | 36% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | AUS200 | M30 | 0.25% | -13 | -290 | -486 | -36 | 216 | 36% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | AUS200 | M30 | 0.25% | -13 | -293 | -371 | -25 | 216 | 36% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | AUS200 | M30 | none | -16 | -355 | -661 | -55 | 200 | 32% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | AUS200 | M30 | 0.25% | -17 | -375 | -389 | -36 | 200 | 32% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | AUS200 | M30 | 0.25% | -19 | -416 | -578 | -25 | 200 | 36% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | AUS200 | M30 | none | -21 | -464 | -658 | -25 | 216 | 32% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | CHINA50 | H1 | 0.25% | -5 | -64 | -309 | -25 | 116 | 43% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | CHINA50 | H1 | 0.50% | -6 | -80 | -525 | -50 | 118 | 43% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | CHINA50 | H1 | 0.25% | -9 | -131 | -368 | -25 | 134 | 43% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | CHINA50 | H1 | 0.25% | -20 | -274 | -355 | -25 | 128 | 50% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | CHINA50 | H1 | 0.25% | -23 | -322 | -350 | -25 | 128 | 29% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | CHINA50 | H1 | 0.50% | -25 | -345 | -469 | -50 | 118 | 43% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | CHINA50 | H1 | 0.50% | -26 | -370 | -467 | -50 | 118 | 29% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | CHINA50 | H1 | 0.50% | -39 | -547 | -586 | -50 | 136 | 29% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | CHINA50 | M30 | 0.25% | -15 | -209 | -387 | -25 | 131 | 29% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | CHINA50 | M30 | 0.25% | -18 | -253 | -418 | -25 | 120 | 29% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | CHINA50 | M30 | 0.50% | -25 | -345 | -448 | -50 | 122 | 36% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | CHINA50 | M30 | 0.25% | -25 | -350 | -397 | -25 | 116 | 29% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | CHINA50 | M30 | 0.25% | -27 | -379 | -399 | -25 | 131 | 21% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | CHINA50 | M30 | 0.25% | -27 | -383 | -393 | -25 | 120 | 14% | `{"close_h": 9.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | CHINA50 | M30 | 0.25% | -29 | -404 | -451 | -25 | 127 | 29% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | CHINA50 | M30 | 0.50% | -30 | -419 | -531 | -50 | 134 | 29% | `{"close_h": 9.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | HK50 | H1 | 0.75% | 13 | 326 | -537 | -75 | 194 | 60% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | HK50 | H1 | 0.50% | 10 | 242 | -445 | -50 | 216 | 52% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | HK50 | H1 | 0.25% | -2 | -51 | -326 | -25 | 216 | 44% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | HK50 | H1 | 0.25% | -4 | -94 | -336 | -25 | 193 | 48% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | HK50 | H1 | 0.25% | -7 | -178 | -376 | -25 | 215 | 48% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | HK50 | H1 | 0.25% | -9 | -222 | -459 | -25 | 194 | 40% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | HK50 | H1 | 0.50% | -9 | -222 | -559 | -50 | 194 | 44% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | HK50 | H1 | 0.25% | -12 | -304 | -508 | -25 | 216 | 40% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | HK50 | M30 | 0.25% | -4 | -96 | -298 | -25 | 234 | 48% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | HK50 | M30 | 0.25% | -6 | -146 | -386 | -25 | 212 | 36% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | HK50 | M30 | 0.50% | -11 | -285 | -495 | -50 | 212 | 44% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | HK50 | M30 | 0.25% | -12 | -295 | -414 | -25 | 212 | 40% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | HK50 | M30 | 0.25% | -13 | -320 | -507 | -25 | 234 | 40% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | HK50 | M30 | 0.25% | -15 | -378 | -423 | -25 | 211 | 36% | `{"close_h": 10.0, "min_gap": 0.6, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | HK50 | M30 | 0.25% | -16 | -411 | -433 | -25 | 233 | 36% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | HK50 | M30 | 0.50% | -17 | -416 | -560 | -50 | 234 | 36% | `{"close_h": 10.0, "min_gap": 0.3, "open_h": 3.5, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | JPN225 | H1 | 0.50% | -4 | -93 | -290 | -49 | 10 | 4% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | JPN225 | H1 | 0.50% | -4 | -93 | -290 | -49 | 10 | 4% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | JPN225 | H1 | 1.00% | -4 | -100 | -193 | -99 | 6 | 4% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | JPN225 | H1 | 1.00% | -6 | -144 | -347 | -96 | 5 | 4% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | JPN225 | H1 | 0.75% | -10 | -242 | -600 | -72 | 21 | 16% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | JPN225 | H1 | 0.75% | -10 | -242 | -600 | -72 | 21 | 16% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | JPN225 | H1 | 1.00% | -10 | -243 | -377 | -99 | 6 | 4% | `{"close_h": 8.0, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | JPN225 | H1 | 1.25% | -16 | -395 | -524 | -120 | 12 | 12% | `{"close_h": 8.0, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | JPN225 | M30 | 1.50% | 79 | 1974 | -570 | -135 | 24 | 40% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | JPN225 | M30 | 0.75% | 60 | 1498 | -435 | -73 | 30 | 32% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | JPN225 | M30 | 1.50% | 59 | 1477 | -570 | -146 | 32 | 40% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 0}` |
| gap_go | JPN225 | M30 | 0.75% | 57 | 1418 | -484 | -73 | 33 | 32% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 0}` |
| gap_go | JPN225 | M30 | 1.50% | 12 | 302 | -300 | -135 | 24 | 28% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | JPN225 | M30 | 1.50% | 4 | 110 | -405 | -135 | 32 | 40% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "pc", "tp_atr": 1.5}` |
| gap_go | JPN225 | M30 | 0.75% | -3 | -86 | -429 | -73 | 30 | 32% | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| gap_go | JPN225 | M30 | 0.75% | -7 | -166 | -440 | -73 | 33 | 24% | `{"close_h": 8.5, "min_gap": 0.3, "open_h": 2.0, "sl_mode": "bar", "tp_atr": 1.5}` |
| hour_drift | AUS200 | H1 | 0.50% | 3 | 76 | -564 | -54 | 84 | 59% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | 0.50% | 2 | 43 | -429 | -50 | 84 | 50% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | AUS200 | H1 | 0.25% | -4 | -82 | -351 | -25 | 84 | 45% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | 0.25% | -7 | -158 | -438 | -31 | 174 | 36% | `{"dows": [0, 2], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | AUS200 | H1 | 0.50% | -9 | -196 | -436 | -50 | 84 | 45% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 2.0}` |
| hour_drift | AUS200 | H1 | 0.25% | -16 | -344 | -344 | -25 | 89 | 27% | `{"dows": [0], "entry_h": 2.0, "hold_h": 6.0, "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | none | -52 | -1136 | -1258 | -122 | 452 | 32% | `{"entry_h": 22.0, "hold_h": 2.0, "side": "short", "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | none | -59 | -1302 | -1522 | -25 | 464 | 27% | `{"entry_h": 2.0, "hold_h": 1.0, "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | none | -69 | -1527 | -1676 | -25 | 465 | 32% | `{"entry_h": 1.0, "hold_h": 3.0, "sl_atr": 1.0}` |
| hour_drift | AUS200 | H1 | none | -70 | -1547 | -1659 | -25 | 465 | 23% | `{"entry_h": 1.0, "hold_h": 2.0, "sl_atr": 1.0}` |
| hour_drift | CHINA50 | H1 | 2.00% | 22 | 307 | -322 | -39 | 1 | 7% | `{"dows": [0, 2], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | CHINA50 | H1 | 0.25% | -2 | -33 | -309 | -25 | 51 | 43% | `{"dows": [0], "entry_h": 2.0, "hold_h": 6.0, "sl_atr": 1.0}` |
| hour_drift | CHINA50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 1.0}` |
| hour_drift | CHINA50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 2.0}` |
| hour_drift | CHINA50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 1.0}` |
| hour_drift | CHINA50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | HK50 | H1 | 0.50% | -9 | -226 | -572 | -115 | 92 | 48% | `{"dows": [0], "entry_h": 2.0, "hold_h": 6.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -38 | -944 | -1122 | -40 | 493 | 24% | `{"entry_h": 10.0, "hold_h": 2.0, "side": "short", "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -40 | -992 | -1067 | -25 | 491 | 12% | `{"entry_h": 12.0, "hold_h": 2.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -53 | -1316 | -1340 | -25 | 491 | 16% | `{"entry_h": 11.0, "hold_h": 2.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -53 | -1332 | -1394 | -48 | 491 | 8% | `{"entry_h": 16.0, "hold_h": 2.0, "side": "long", "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -55 | -1376 | -1377 | -25 | 491 | 4% | `{"entry_h": 12.0, "hold_h": 1.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | none | -96 | -2393 | -2404 | -25 | 494 | 4% | `{"entry_h": 7.0, "hold_h": 1.0, "side": "short", "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 2.0}` |
| hour_drift | HK50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 1.0}` |
| hour_drift | HK50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | HK50 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"dows": [0, 2], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | JPN225 | H1 | 0.75% | 7 | 169 | -249 | -72 | 6 | 8% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 1.0}` |
| hour_drift | JPN225 | H1 | 0.50% | 5 | 120 | -123 | -13 | 1 | 4% | `{"entry_h": 0.0, "hold_h": 2.0, "sl_atr": 1.0}` |
| hour_drift | JPN225 | H1 | 0.50% | 5 | 120 | -123 | -13 | 1 | 4% | `{"entry_h": 1.0, "hold_h": 2.0, "sl_atr": 1.0}` |
| hour_drift | JPN225 | H1 | 0.50% | 5 | 116 | -123 | -13 | 1 | 4% | `{"entry_h": 0.0, "hold_h": 3.0, "sl_atr": 1.0}` |
| hour_drift | JPN225 | H1 | 1.25% | -3 | -64 | -131 | -117 | 2 | 4% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 2.0}` |
| hour_drift | JPN225 | H1 | 0.75% | -4 | -94 | -320 | -72 | 6 | 8% | `{"dows": [0], "entry_h": 0.0, "hold_h": 8.0, "sl_atr": 1.0}` |
| hour_drift | JPN225 | H1 | 1.50% | -4 | -96 | -569 | -145 | 11 | 20% | `{"dows": [0], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | JPN225 | H1 | 1.00% | -4 | -97 | -97 | -97 | 1 | 0% | `{"dows": [0, 2], "entry_h": 0.0, "hold_h": 22.0, "sl_atr": 2.0}` |
| hour_drift | JPN225 | H1 | 1.00% | -13 | -327 | -418 | -98 | 22 | 12% | `{"dows": [0], "entry_h": 2.0, "hold_h": 6.0, "sl_atr": 1.0}` |
| lunch_fade | AUS200 | H1 | 0.25% | -20 | -434 | -542 | -25 | 293 | 45% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | AUS200 | H1 | 0.25% | -22 | -487 | -570 | -25 | 293 | 41% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | AUS200 | H1 | none | -25 | -539 | -639 | -25 | 361 | 41% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | AUS200 | H1 | none | -33 | -716 | -776 | -25 | 361 | 27% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | AUS200 | H1 | none | -48 | -1053 | -1106 | -53 | 293 | 27% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | AUS200 | H1 | none | -54 | -1194 | -1244 | -53 | 361 | 23% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | AUS200 | M30 | none | -40 | -887 | -1019 | -25 | 341 | 23% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | AUS200 | M30 | none | -50 | -1096 | -1245 | -25 | 341 | 18% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | AUS200 | M30 | none | -52 | -1152 | -1264 | -25 | 390 | 18% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | AUS200 | M30 | none | -54 | -1196 | -1335 | -25 | 390 | 18% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | AUS200 | M30 | none | -70 | -1548 | -1568 | -76 | 390 | 18% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | AUS200 | M30 | none | -72 | -1590 | -1611 | -76 | 341 | 23% | `{"close_h": 8.0, "lunch_h": 5.0, "open_h": 2.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | H1 | none | -47 | -659 | -732 | -25 | 200 | 14% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | H1 | none | -51 | -718 | -791 | -25 | 230 | 14% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | H1 | none | -54 | -762 | -797 | -25 | 200 | 7% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | CHINA50 | H1 | none | -61 | -851 | -885 | -25 | 222 | 7% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | CHINA50 | H1 | none | -72 | -1007 | -1026 | -25 | 200 | 29% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | H1 | none | -104 | -1462 | -1462 | -25 | 230 | 14% | `{"close_h": 9.0, "lunch_h": 5.0, "open_h": 3.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | M30 | none | -57 | -802 | -883 | -25 | 209 | 21% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | M30 | none | -64 | -897 | -978 | -25 | 237 | 14% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | M30 | none | -65 | -908 | -957 | -25 | 206 | 14% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | CHINA50 | M30 | none | -68 | -956 | -999 | -25 | 221 | 7% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | CHINA50 | M30 | none | -83 | -1159 | -1225 | -25 | 209 | 21% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | CHINA50 | M30 | none | -93 | -1295 | -1362 | -25 | 237 | 21% | `{"close_h": 9.0, "lunch_h": 5.5, "open_h": 3.5, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | HK50 | H1 | none | -34 | -842 | -923 | -25 | 345 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | HK50 | H1 | none | -36 | -910 | -993 | -25 | 392 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | HK50 | H1 | none | -40 | -1008 | -1105 | -25 | 345 | 16% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | HK50 | H1 | none | -42 | -1061 | -1164 | -25 | 392 | 20% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | HK50 | H1 | none | -51 | -1268 | -1335 | -25 | 345 | 20% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | HK50 | H1 | none | -63 | -1586 | -1654 | -25 | 392 | 16% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | HK50 | M30 | none | -46 | -1150 | -1186 | -25 | 369 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | HK50 | M30 | none | -48 | -1209 | -1244 | -25 | 417 | 28% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | HK50 | M30 | none | -50 | -1247 | -1296 | -25 | 369 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | HK50 | M30 | none | -52 | -1304 | -1354 | -25 | 418 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | HK50 | M30 | none | -69 | -1724 | -1903 | -28 | 369 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | HK50 | M30 | none | -83 | -2070 | -2174 | -28 | 418 | 24% | `{"close_h": 10.0, "lunch_h": 6.0, "open_h": 3.5, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | JPN225 | H1 | 1.00% | 12 | 299 | -410 | -99 | 54 | 28% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | JPN225 | H1 | 1.00% | 8 | 205 | -506 | -99 | 60 | 28% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | JPN225 | H1 | 1.00% | 3 | 67 | -410 | -99 | 54 | 24% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | JPN225 | H1 | 0.50% | -3 | -63 | -120 | -50 | 2 | 0% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | JPN225 | H1 | 0.50% | -3 | -65 | -120 | -50 | 3 | 0% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | JPN225 | H1 | 1.00% | -4 | -94 | -542 | -99 | 60 | 24% | `{"close_h": 8.0, "lunch_h": 4.0, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | JPN225 | M30 | 0.75% | 8 | 191 | -509 | -74 | 43 | 24% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "half"}` |
| lunch_fade | JPN225 | M30 | 0.50% | 2 | 42 | -105 | -50 | 4 | 8% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | JPN225 | M30 | 0.50% | 2 | 42 | -105 | -50 | 4 | 8% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": -1, "thr": 0.8, "tp_mode": "open"}` |
| lunch_fade | JPN225 | M30 | 0.75% | -0 | -2 | -571 | -74 | 49 | 20% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": -1, "thr": 0.5, "tp_mode": "half"}` |
| lunch_fade | JPN225 | M30 | 0.50% | -15 | -381 | -457 | -50 | 57 | 12% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": 1, "thr": 0.5, "tp_mode": "open"}` |
| lunch_fade | JPN225 | M30 | 0.50% | -16 | -388 | -517 | -49 | 45 | 16% | `{"close_h": 8.5, "lunch_h": 4.5, "open_h": 2.0, "sign": 1, "thr": 0.8, "tp_mode": "open"}` |
| nr_break | AUS200 | H1 | 2.00% | 3 | 56 | -505 | -183 | 35 | 41% | `{"close_h": 10.0, "inside": true, "nr": 4, "open_h": 2.0, "tp_r": 0}` |
| nr_break | AUS200 | H1 | 2.00% | 1 | 16 | -505 | -183 | 35 | 41% | `{"close_h": 10.0, "inside": true, "nr": 4, "open_h": 2.0, "tp_r": 1.0}` |
| nr_break | AUS200 | H1 | 1.50% | -6 | -131 | -552 | -111 | 46 | 41% | `{"close_h": 10.0, "inside": false, "nr": 7, "open_h": 2.0, "tp_r": 0}` |
| nr_break | AUS200 | H1 | 1.50% | -9 | -191 | -552 | -111 | 46 | 41% | `{"close_h": 10.0, "inside": false, "nr": 7, "open_h": 2.0, "tp_r": 1.0}` |
| nr_break | AUS200 | H1 | 1.50% | -16 | -360 | -579 | -142 | 74 | 45% | `{"close_h": 10.0, "inside": false, "nr": 4, "open_h": 2.0, "tp_r": 0}` |
| nr_break | AUS200 | H1 | 1.50% | -17 | -371 | -554 | -142 | 74 | 45% | `{"close_h": 10.0, "inside": false, "nr": 4, "open_h": 2.0, "tp_r": 1.0}` |
| nr_break | CHINA50 | H1 | 1.50% | 16 | 229 | -485 | -149 | 32 | 50% | `{"close_h": 11.0, "inside": true, "nr": 4, "open_h": 3.0, "tp_r": 0}` |
| nr_break | CHINA50 | H1 | 2.00% | 14 | 199 | -550 | -186 | 35 | 43% | `{"close_h": 11.0, "inside": false, "nr": 7, "open_h": 3.0, "tp_r": 0}` |
| nr_break | CHINA50 | H1 | 1.50% | 4 | 54 | -485 | -149 | 32 | 50% | `{"close_h": 11.0, "inside": true, "nr": 4, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | CHINA50 | H1 | 2.00% | 1 | 18 | -484 | -186 | 35 | 50% | `{"close_h": 11.0, "inside": false, "nr": 7, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | CHINA50 | H1 | 1.00% | -14 | -197 | -600 | -93 | 55 | 43% | `{"close_h": 11.0, "inside": false, "nr": 4, "open_h": 3.0, "tp_r": 0}` |
| nr_break | CHINA50 | H1 | 1.00% | -20 | -285 | -567 | -93 | 55 | 50% | `{"close_h": 11.0, "inside": false, "nr": 4, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | HK50 | H1 | 0.50% | -16 | -403 | -403 | -49 | 109 | 36% | `{"close_h": 12.0, "inside": false, "nr": 4, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | HK50 | H1 | 0.50% | -16 | -411 | -411 | -49 | 109 | 36% | `{"close_h": 12.0, "inside": false, "nr": 4, "open_h": 3.0, "tp_r": 0}` |
| nr_break | HK50 | H1 | 1.00% | -20 | -493 | -538 | -99 | 64 | 32% | `{"close_h": 12.0, "inside": false, "nr": 7, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | HK50 | H1 | 1.00% | -21 | -536 | -581 | -99 | 64 | 32% | `{"close_h": 12.0, "inside": false, "nr": 7, "open_h": 3.0, "tp_r": 0}` |
| nr_break | HK50 | H1 | 0.75% | -22 | -551 | -565 | -75 | 45 | 32% | `{"close_h": 12.0, "inside": true, "nr": 4, "open_h": 3.0, "tp_r": 1.0}` |
| nr_break | HK50 | H1 | 0.75% | -22 | -556 | -571 | -75 | 45 | 32% | `{"close_h": 12.0, "inside": true, "nr": 4, "open_h": 3.0, "tp_r": 0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": false, "nr": 4, "open_h": 2.0, "tp_r": 0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": false, "nr": 4, "open_h": 2.0, "tp_r": 1.0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": false, "nr": 7, "open_h": 2.0, "tp_r": 0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": false, "nr": 7, "open_h": 2.0, "tp_r": 1.0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": true, "nr": 4, "open_h": 2.0, "tp_r": 0}` |
| nr_break | JPN225 | H1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 10.0, "inside": true, "nr": 4, "open_h": 2.0, "tp_r": 1.0}` |
| orb | AUS200 | H1 | 0.50% | -4 | -95 | -430 | -50 | 297 | 41% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | AUS200 | H1 | 0.50% | -9 | -202 | -420 | -50 | 297 | 41% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | AUS200 | H1 | 0.25% | -12 | -259 | -465 | -25 | 297 | 32% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | AUS200 | H1 | 0.25% | -16 | -361 | -453 | -25 | 151 | 36% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | AUS200 | H1 | 0.25% | -17 | -382 | -466 | -25 | 151 | 36% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | AUS200 | H1 | 0.75% | -18 | -394 | -566 | -73 | 151 | 36% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | AUS200 | H1 | 0.25% | -20 | -433 | -564 | -25 | 297 | 23% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | AUS200 | H1 | 0.75% | -20 | -441 | -596 | -73 | 151 | 36% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | AUS200 | M30 | 0.25% | -1 | -20 | -330 | -25 | 200 | 55% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | AUS200 | M30 | 0.25% | -5 | -108 | -350 | -25 | 200 | 45% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | AUS200 | M30 | 0.25% | -7 | -144 | -324 | -25 | 200 | 36% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | AUS200 | M30 | 0.25% | -8 | -173 | -307 | -25 | 200 | 45% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | AUS200 | M30 | 0.25% | -25 | -544 | -584 | -25 | 307 | 41% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | AUS200 | M30 | none | -28 | -617 | -700 | -26 | 307 | 36% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | AUS200 | M30 | none | -29 | -628 | -768 | -26 | 307 | 36% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | AUS200 | M30 | none | -29 | -631 | -676 | -25 | 307 | 32% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | CHINA50 | H1 | 2.00% | -7 | -96 | -200 | -92 | 12 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | CHINA50 | H1 | 2.00% | -7 | -96 | -200 | -92 | 12 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | CHINA50 | H1 | 2.00% | -8 | -110 | -280 | -153 | 12 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | CHINA50 | H1 | 2.00% | -8 | -110 | -280 | -153 | 12 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | CHINA50 | H1 | 0.25% | -17 | -239 | -341 | -25 | 54 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | CHINA50 | H1 | 0.25% | -19 | -268 | -341 | -25 | 54 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | CHINA50 | H1 | 0.50% | -32 | -448 | -555 | -49 | 57 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | CHINA50 | H1 | 0.50% | -35 | -492 | -555 | -49 | 57 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | CHINA50 | M30 | 0.50% | -2 | -26 | -413 | -48 | 39 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "mid", "tp_r": 0}` |
| orb | CHINA50 | M30 | 0.50% | -9 | -128 | -421 | -48 | 39 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | CHINA50 | M30 | 0.75% | -13 | -180 | -588 | -72 | 39 | 14% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "opp", "tp_r": 0}` |
| orb | CHINA50 | M30 | 0.75% | -18 | -253 | -574 | -72 | 39 | 14% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | CHINA50 | M30 | 2.00% | -29 | -404 | -404 | -199 | 5 | 7% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "opp", "tp_r": 0}` |
| orb | CHINA50 | M30 | 2.00% | -29 | -404 | -404 | -199 | 5 | 7% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | CHINA50 | M30 | 2.00% | -30 | -422 | -422 | -198 | 5 | 7% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "mid", "tp_r": 0}` |
| orb | CHINA50 | M30 | 2.00% | -30 | -422 | -422 | -198 | 5 | 7% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | HK50 | H1 | 0.25% | -15 | -374 | -399 | -25 | 100 | 16% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | HK50 | H1 | 0.25% | -15 | -374 | -399 | -25 | 100 | 16% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -21 | -518 | -740 | -36 | 266 | 20% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | HK50 | H1 | 0.50% | -22 | -558 | -590 | -49 | 100 | 12% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | HK50 | H1 | 0.50% | -22 | -558 | -590 | -49 | 100 | 12% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -22 | -562 | -677 | -36 | 266 | 20% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -26 | -661 | -786 | -37 | 324 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 4.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -30 | -749 | -865 | -37 | 324 | 28% | `{"close_h": 10.0, "n_bars": 1, "open_h": 4.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | HK50 | H1 | none | -35 | -886 | -971 | -42 | 266 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -37 | -928 | -1118 | -42 | 266 | 20% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | HK50 | H1 | none | -38 | -948 | -1087 | -58 | 324 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 4.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | HK50 | H1 | none | -43 | -1078 | -1198 | -58 | 324 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 4.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | HK50 | M30 | 0.75% | 6 | 156 | -463 | -75 | 68 | 32% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "mid", "tp_r": 0}` |
| orb | HK50 | M30 | 1.50% | 1 | 18 | -578 | -150 | 68 | 36% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "opp", "tp_r": 0}` |
| orb | HK50 | M30 | 0.75% | 0 | 10 | -482 | -75 | 68 | 36% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | HK50 | M30 | 1.00% | -4 | -105 | -515 | -100 | 68 | 40% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | HK50 | M30 | 0.25% | -8 | -210 | -342 | -25 | 184 | 48% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "opp", "tp_r": 0}` |
| orb | HK50 | M30 | 0.25% | -13 | -316 | -497 | -25 | 184 | 44% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "mid", "tp_r": 0}` |
| orb | HK50 | M30 | 0.25% | -19 | -483 | -519 | -25 | 184 | 40% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | HK50 | M30 | none | -27 | -685 | -779 | -25 | 184 | 28% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | JPN225 | H1 | 1.50% | 3 | 85 | -115 | -63 | 7 | 12% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | JPN225 | H1 | 1.50% | 3 | 85 | -115 | -63 | 7 | 12% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | JPN225 | H1 | 1.00% | -2 | -58 | -365 | -99 | 20 | 16% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | JPN225 | H1 | 1.25% | -4 | -102 | -289 | -112 | 8 | 12% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | JPN225 | H1 | 1.25% | -4 | -104 | -289 | -112 | 8 | 12% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | JPN225 | H1 | 1.00% | -7 | -186 | -365 | -99 | 20 | 16% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | JPN225 | H1 | 0.75% | -20 | -494 | -494 | -73 | 13 | 8% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | JPN225 | H1 | 0.75% | -20 | -496 | -496 | -73 | 13 | 8% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | JPN225 | M30 | 2.00% | 14 | 346 | -481 | -180 | 40 | 36% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | JPN225 | M30 | 1.00% | 11 | 285 | -375 | -99 | 31 | 32% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | JPN225 | M30 | 1.00% | 9 | 218 | -375 | -99 | 31 | 32% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | JPN225 | M30 | 2.00% | 6 | 149 | -536 | -180 | 40 | 32% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb | JPN225 | M30 | 0.50% | -3 | -68 | -214 | -48 | 6 | 4% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 1.5}` |
| orb | JPN225 | M30 | 1.00% | -3 | -85 | -435 | -97 | 13 | 24% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 1.5}` |
| orb | JPN225 | M30 | 0.50% | -5 | -113 | -221 | -48 | 6 | 4% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "sl_mode": "mid", "tp_r": 0}` |
| orb | JPN225 | M30 | 1.00% | -5 | -123 | -443 | -97 | 13 | 24% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "sl_mode": "opp", "tp_r": 0}` |
| orb_fade | AUS200 | H1 | none | -29 | -635 | -956 | -25 | 216 | 27% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | AUS200 | H1 | none | -39 | -855 | -979 | -25 | 216 | 23% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | AUS200 | H1 | none | -40 | -873 | -956 | -25 | 164 | 23% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | AUS200 | H1 | none | -44 | -968 | -1033 | -25 | 164 | 27% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | AUS200 | H1 | none | -46 | -1017 | -1206 | -25 | 303 | 27% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | AUS200 | H1 | none | -53 | -1173 | -1251 | -25 | 252 | 23% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | AUS200 | H1 | none | -55 | -1217 | -1294 | -25 | 303 | 18% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | AUS200 | H1 | none | -70 | -1534 | -1560 | -25 | 252 | 14% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | AUS200 | M30 | none | -50 | -1110 | -1292 | -25 | 223 | 27% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | AUS200 | M30 | none | -51 | -1115 | -1258 | -25 | 223 | 23% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | AUS200 | M30 | none | -72 | -1584 | -1674 | -25 | 312 | 23% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | AUS200 | M30 | none | -73 | -1597 | -1670 | -25 | 186 | 14% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | AUS200 | M30 | none | -77 | -1689 | -1732 | -25 | 312 | 9% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | AUS200 | M30 | none | -81 | -1779 | -1870 | -25 | 186 | 18% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | AUS200 | M30 | none | -93 | -2045 | -2114 | -25 | 266 | 9% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | AUS200 | M30 | none | -95 | -2087 | -2140 | -25 | 266 | 9% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | CHINA50 | H1 | none | -26 | -365 | -609 | -25 | 181 | 43% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | CHINA50 | H1 | none | -31 | -434 | -633 | -25 | 219 | 36% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | CHINA50 | H1 | none | -37 | -513 | -649 | -25 | 181 | 43% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | CHINA50 | H1 | none | -46 | -642 | -740 | -25 | 218 | 29% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | CHINA50 | H1 | none | -51 | -719 | -995 | -25 | 169 | 36% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | CHINA50 | H1 | none | -78 | -1090 | -1289 | -25 | 209 | 21% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | CHINA50 | H1 | none | -83 | -1156 | -1204 | -25 | 169 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | CHINA50 | H1 | none | -104 | -1452 | -1501 | -25 | 201 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | CHINA50 | M30 | none | -42 | -594 | -771 | -25 | 232 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | CHINA50 | M30 | none | -45 | -625 | -790 | -25 | 208 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | CHINA50 | M30 | none | -68 | -959 | -1085 | -25 | 205 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | CHINA50 | M30 | none | -72 | -1003 | -1129 | -25 | 225 | 21% | `{"close_h": 9.0, "n_bars": 2, "open_h": 3.5, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | CHINA50 | M30 | none | -124 | -1743 | -1743 | -25 | 192 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | CHINA50 | M30 | none | -136 | -1907 | -1907 | -25 | 189 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | CHINA50 | M30 | none | -143 | -1997 | -1997 | -25 | 231 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | CHINA50 | M30 | none | -149 | -2079 | -2079 | -25 | 214 | 0% | `{"close_h": 9.0, "n_bars": 1, "open_h": 3.5, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | HK50 | H1 | none | -23 | -568 | -709 | -88 | 233 | 52% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | HK50 | H1 | none | -44 | -1103 | -1212 | -25 | 233 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | HK50 | H1 | none | -47 | -1164 | -1304 | -88 | 342 | 32% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | HK50 | H1 | none | -59 | -1468 | -1504 | -57 | 289 | 32% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | HK50 | H1 | none | -61 | -1524 | -1539 | -57 | 289 | 16% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | HK50 | H1 | none | -73 | -1828 | -1850 | -57 | 368 | 16% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | HK50 | H1 | none | -73 | -1833 | -1904 | -57 | 368 | 24% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | HK50 | H1 | none | -78 | -1962 | -2071 | -25 | 342 | 16% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | HK50 | M30 | none | -41 | -1034 | -1152 | -123 | 318 | 28% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | HK50 | M30 | none | -51 | -1271 | -1423 | -123 | 386 | 32% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | HK50 | M30 | none | -57 | -1435 | -1471 | -103 | 280 | 28% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | HK50 | M30 | none | -59 | -1472 | -1527 | -25 | 318 | 12% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | HK50 | M30 | none | -68 | -1709 | -1753 | -25 | 280 | 16% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | HK50 | M30 | none | -72 | -1801 | -1858 | -25 | 386 | 16% | `{"close_h": 10.0, "n_bars": 2, "open_h": 3.5, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | HK50 | M30 | none | -81 | -2026 | -2078 | -125 | 361 | 24% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | HK50 | M30 | none | -99 | -2480 | -2497 | -25 | 358 | 12% | `{"close_h": 10.0, "n_bars": 1, "open_h": 3.5, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | JPN225 | H1 | 0.50% | -3 | -71 | -128 | -48 | 11 | 12% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | JPN225 | H1 | 0.50% | -4 | -94 | -151 | -48 | 2 | 0% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | JPN225 | H1 | 0.50% | -4 | -94 | -151 | -48 | 2 | 0% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | JPN225 | H1 | 0.50% | -4 | -94 | -151 | -48 | 2 | 0% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | JPN225 | H1 | 0.50% | -5 | -115 | -167 | -46 | 6 | 8% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | JPN225 | H1 | 0.50% | -5 | -133 | -218 | -48 | 11 | 8% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | JPN225 | H1 | 0.50% | -8 | -208 | -266 | -46 | 6 | 4% | `{"close_h": 8.0, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | JPN225 | H1 | 0.75% | -13 | -329 | -508 | -73 | 54 | 20% | `{"close_h": 8.0, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | JPN225 | M30 | 0.50% | -5 | -115 | -410 | -48 | 39 | 20% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| orb_fade | JPN225 | M30 | 0.50% | -6 | -160 | -454 | -48 | 40 | 20% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | JPN225 | M30 | 0.50% | -14 | -340 | -529 | -48 | 39 | 12% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | JPN225 | M30 | 0.50% | -15 | -384 | -573 | -48 | 40 | 12% | `{"close_h": 8.5, "n_bars": 2, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "open"}` |
| orb_fade | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "thr": 0.6, "tp_mode": "half"}` |
| orb_fade | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "open"}` |
| orb_fade | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "n_bars": 1, "open_h": 2.0, "thr": 1.0, "tp_mode": "half"}` |
| overnight | AUS200 | H1 | none | -9 | -194 | -952 | -73 | 370 | 55% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "skip_fri": true, "sl_atr": 1.5}` |
| overnight | AUS200 | H1 | none | -13 | -288 | -944 | -67 | 232 | 50% | `{"close_h": 8.0, "filt": "down_day", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| overnight | AUS200 | H1 | 0.25% | -18 | -390 | -476 | -56 | 228 | 41% | `{"close_h": 8.0, "filt": "up_day", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | AUS200 | H1 | none | -18 | -406 | -692 | -55 | 232 | 36% | `{"close_h": 8.0, "filt": "down_day", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | AUS200 | H1 | 0.25% | -19 | -425 | -554 | -113 | 228 | 41% | `{"close_h": 8.0, "filt": "up_day", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| overnight | AUS200 | H1 | none | -38 | -841 | -1127 | -113 | 462 | 45% | `{"close_h": 8.0, "filt": "none", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| overnight | AUS200 | H1 | none | -40 | -874 | -1037 | -56 | 462 | 32% | `{"close_h": 8.0, "filt": "none", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | AUS200 | H1 | none | -70 | -1529 | -2005 | -98 | 462 | 23% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 1.5}` |
| overnight | CHINA50 | H1 | none | 1 | 17 | -693 | -94 | 281 | 43% | `{"close_h": 9.0, "open_h": 3.0, "side": "short", "sl_atr": 1.5}` |
| overnight | CHINA50 | H1 | 0.50% | -4 | -59 | -583 | -118 | 144 | 36% | `{"close_h": 9.0, "filt": "down_day", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | CHINA50 | H1 | 0.75% | -5 | -75 | -561 | -139 | 144 | 57% | `{"close_h": 9.0, "filt": "down_day", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | CHINA50 | H1 | 0.25% | -33 | -464 | -467 | -33 | 134 | 21% | `{"close_h": 9.0, "filt": "up_day", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | CHINA50 | H1 | 0.25% | -35 | -496 | -551 | -43 | 273 | 36% | `{"close_h": 9.0, "filt": "none", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | CHINA50 | H1 | none | -47 | -661 | -810 | -77 | 224 | 29% | `{"close_h": 9.0, "open_h": 3.0, "side": "long", "skip_fri": true, "sl_atr": 1.5}` |
| overnight | CHINA50 | H1 | none | -64 | -900 | -912 | -54 | 137 | 14% | `{"close_h": 9.0, "filt": "up_day", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | CHINA50 | H1 | none | -69 | -967 | -1110 | -77 | 281 | 21% | `{"close_h": 9.0, "filt": "none", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | HK50 | H1 | 0.25% | -4 | -93 | -299 | -89 | 237 | 44% | `{"close_h": 10.0, "filt": "up_day", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | HK50 | H1 | 0.25% | -14 | -345 | -509 | -80 | 237 | 40% | `{"close_h": 10.0, "filt": "up_day", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | HK50 | H1 | 0.25% | -14 | -346 | -426 | -43 | 255 | 44% | `{"close_h": 10.0, "filt": "down_day", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | HK50 | H1 | 0.25% | -17 | -413 | -561 | -70 | 255 | 36% | `{"close_h": 10.0, "filt": "down_day", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | HK50 | H1 | 0.25% | -19 | -463 | -578 | -99 | 493 | 36% | `{"close_h": 10.0, "filt": "none", "open_h": 3.0, "side": "long", "sl_atr": 3.0}` |
| overnight | HK50 | H1 | none | -31 | -784 | -851 | -94 | 493 | 40% | `{"close_h": 10.0, "filt": "none", "open_h": 3.0, "side": "long", "sl_atr": 1.5}` |
| overnight | HK50 | H1 | none | -33 | -819 | -910 | -94 | 395 | 36% | `{"close_h": 10.0, "open_h": 3.0, "side": "long", "skip_fri": true, "sl_atr": 1.5}` |
| overnight | HK50 | H1 | none | -40 | -993 | -1351 | -99 | 493 | 32% | `{"close_h": 10.0, "open_h": 3.0, "side": "short", "sl_atr": 1.5}` |
| overnight | JPN225 | H1 | 2.00% | 14 | 341 | -576 | -239 | 9 | 16% | `{"close_h": 8.0, "filt": "down_day", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | JPN225 | H1 | 0.75% | 1 | 34 | -135 | -116 | 1 | 4% | `{"close_h": 8.0, "filt": "none", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| overnight | JPN225 | H1 | 1.50% | 1 | 34 | -135 | -116 | 1 | 4% | `{"close_h": 8.0, "filt": "none", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | JPN225 | H1 | 0.75% | 1 | 34 | -135 | -116 | 1 | 4% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "skip_fri": true, "sl_atr": 1.5}` |
| overnight | JPN225 | H1 | 0.75% | -3 | -75 | -88 | -75 | 1 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 1.5}` |
| overnight | JPN225 | H1 | 2.00% | -6 | -157 | -462 | -188 | 6 | 8% | `{"close_h": 8.0, "filt": "up_day", "open_h": 2.0, "side": "long", "sl_atr": 3.0}` |
| overnight | JPN225 | H1 | 1.00% | -6 | -160 | -344 | -206 | 5 | 4% | `{"close_h": 8.0, "filt": "down_day", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| overnight | JPN225 | H1 | 1.00% | -13 | -320 | -334 | -172 | 4 | 0% | `{"close_h": 8.0, "filt": "up_day", "open_h": 2.0, "side": "long", "sl_atr": 1.5}` |
| pdhl_break | AUS200 | H1 | 0.75% | -14 | -316 | -470 | -75 | 67 | 41% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | H1 | 0.25% | -17 | -367 | -450 | -25 | 67 | 27% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | H1 | 0.25% | -20 | -440 | -458 | -25 | 67 | 23% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | AUS200 | H1 | 0.25% | -21 | -462 | -472 | -25 | 131 | 23% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | AUS200 | H1 | 0.25% | -21 | -464 | -507 | -25 | 131 | 18% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | H1 | 0.75% | -21 | -473 | -503 | -75 | 67 | 36% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | AUS200 | H1 | none | -37 | -808 | -827 | -25 | 131 | 23% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | AUS200 | H1 | none | -38 | -834 | -915 | -25 | 131 | 23% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | M30 | 0.50% | -4 | -80 | -448 | -50 | 90 | 45% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | M30 | 0.75% | -11 | -251 | -578 | -75 | 90 | 36% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | AUS200 | M30 | none | -22 | -491 | -624 | -25 | 176 | 27% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | M30 | none | -26 | -569 | -616 | -27 | 90 | 36% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | AUS200 | M30 | none | -29 | -629 | -654 | -25 | 176 | 27% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | AUS200 | M30 | none | -29 | -643 | -690 | -27 | 90 | 36% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | M30 | none | -56 | -1243 | -1308 | -27 | 176 | 14% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | AUS200 | M30 | none | -63 | -1379 | -1437 | -27 | 176 | 14% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | CHINA50 | H1 | 0.25% | -9 | -131 | -295 | -25 | 103 | 43% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | H1 | 0.25% | -10 | -133 | -391 | -25 | 103 | 43% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | H1 | 0.50% | -15 | -209 | -444 | -49 | 56 | 43% | `{"close_h": 9.0, "open_h": 3.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | H1 | 0.50% | -17 | -244 | -548 | -50 | 56 | 50% | `{"close_h": 9.0, "open_h": 3.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | H1 | 0.25% | -21 | -296 | -391 | -25 | 103 | 29% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | CHINA50 | H1 | 0.25% | -22 | -302 | -317 | -25 | 56 | 29% | `{"close_h": 9.0, "open_h": 3.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | CHINA50 | H1 | 0.50% | -28 | -393 | -543 | -49 | 56 | 36% | `{"close_h": 9.0, "open_h": 3.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | CHINA50 | H1 | 0.25% | -30 | -423 | -522 | -25 | 103 | 21% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | CHINA50 | M30 | 0.25% | -12 | -171 | -328 | -25 | 65 | 43% | `{"close_h": 9.0, "open_h": 3.5, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | M30 | 0.25% | -18 | -247 | -317 | -25 | 65 | 36% | `{"close_h": 9.0, "open_h": 3.5, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | CHINA50 | M30 | 0.75% | -25 | -346 | -583 | -75 | 65 | 36% | `{"close_h": 9.0, "open_h": 3.5, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | M30 | 0.25% | -25 | -352 | -479 | -25 | 65 | 29% | `{"close_h": 9.0, "open_h": 3.5, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | CHINA50 | M30 | 0.50% | -32 | -442 | -442 | -50 | 123 | 43% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | M30 | 0.25% | -34 | -471 | -489 | -25 | 123 | 36% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | CHINA50 | M30 | 0.25% | -39 | -549 | -586 | -25 | 123 | 36% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | CHINA50 | M30 | none | -68 | -947 | -975 | -25 | 123 | 21% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | HK50 | H1 | 0.25% | -14 | -354 | -354 | -25 | 86 | 24% | `{"close_h": 10.0, "open_h": 3.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | HK50 | H1 | 0.25% | -16 | -410 | -457 | -25 | 86 | 32% | `{"close_h": 10.0, "open_h": 3.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | HK50 | H1 | 0.25% | -17 | -428 | -428 | -25 | 86 | 24% | `{"close_h": 10.0, "open_h": 3.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | HK50 | H1 | 0.25% | -22 | -550 | -557 | -25 | 86 | 28% | `{"close_h": 10.0, "open_h": 3.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | HK50 | H1 | none | -25 | -618 | -708 | -29 | 181 | 16% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | HK50 | H1 | none | -27 | -680 | -928 | -54 | 181 | 32% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | HK50 | H1 | none | -29 | -723 | -792 | -29 | 181 | 12% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | HK50 | H1 | none | -35 | -880 | -1076 | -54 | 181 | 24% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | HK50 | M30 | 0.25% | -22 | -546 | -590 | -25 | 102 | 24% | `{"close_h": 10.0, "open_h": 3.5, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | HK50 | M30 | none | -22 | -549 | -637 | -25 | 102 | 28% | `{"close_h": 10.0, "open_h": 3.5, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | HK50 | M30 | none | -28 | -695 | -795 | -31 | 102 | 20% | `{"close_h": 10.0, "open_h": 3.5, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | HK50 | M30 | none | -30 | -738 | -747 | -31 | 102 | 24% | `{"close_h": 10.0, "open_h": 3.5, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | HK50 | M30 | none | -43 | -1084 | -1267 | -36 | 211 | 20% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | HK50 | M30 | none | -44 | -1099 | -1203 | -36 | 211 | 16% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | HK50 | M30 | none | -62 | -1544 | -1845 | -62 | 211 | 20% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | HK50 | M30 | none | -66 | -1648 | -1847 | -62 | 211 | 16% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | H1 | 1.00% | -2 | -48 | -50 | -50 | 1 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | JPN225 | H1 | 1.00% | -2 | -48 | -50 | -50 | 1 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | H1 | 0.75% | -13 | -320 | -505 | -75 | 22 | 16% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | JPN225 | H1 | 0.75% | -13 | -320 | -505 | -75 | 22 | 16% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | H1 | 0.75% | -14 | -341 | -516 | -75 | 34 | 20% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | H1 | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | JPN225 | H1 | 1.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | JPN225 | H1 | 1.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | M30 | 1.50% | 24 | 604 | -460 | -149 | 62 | 44% | `{"close_h": 8.5, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | M30 | 0.75% | 13 | 331 | -509 | -72 | 57 | 32% | `{"close_h": 8.5, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | M30 | 1.00% | 3 | 66 | -470 | -98 | 38 | 24% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | M30 | 0.75% | -7 | -181 | -272 | -71 | 4 | 0% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | JPN225 | M30 | 0.75% | -7 | -181 | -272 | -71 | 4 | 0% | `{"close_h": 8.5, "open_h": 2.0, "side": "long", "sl_atr": 1.5, "tp_atr": 0}` |
| pdhl_break | JPN225 | M30 | 0.50% | -7 | -184 | -477 | -49 | 27 | 12% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 2.0}` |
| pdhl_break | JPN225 | M30 | 0.50% | -18 | -440 | -580 | -49 | 16 | 8% | `{"close_h": 8.5, "open_h": 2.0, "side": "long", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_break | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 0.75, "tp_atr": 0}` |
| pdhl_fade | AUS200 | H1 | 0.75% | 2 | 35 | -493 | -75 | 117 | 59% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | AUS200 | H1 | 0.50% | -2 | -39 | -412 | -50 | 117 | 45% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | AUS200 | H1 | 0.25% | -13 | -295 | -559 | -25 | 220 | 45% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | AUS200 | H1 | none | -16 | -344 | -608 | -25 | 220 | 45% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | AUS200 | M30 | 0.50% | 3 | 77 | -534 | -50 | 131 | 64% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | AUS200 | M30 | 0.50% | -3 | -58 | -472 | -50 | 131 | 50% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | AUS200 | M30 | none | -21 | -460 | -721 | -25 | 241 | 41% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | AUS200 | M30 | none | -24 | -522 | -724 | -25 | 241 | 36% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | CHINA50 | H1 | 0.50% | -22 | -307 | -444 | -50 | 80 | 29% | `{"close_h": 9.0, "open_h": 3.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | CHINA50 | H1 | 0.25% | -30 | -421 | -433 | -25 | 153 | 29% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | CHINA50 | H1 | 0.25% | -35 | -488 | -521 | -25 | 153 | 21% | `{"close_h": 9.0, "open_h": 3.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | CHINA50 | H1 | 0.50% | -35 | -495 | -598 | -50 | 80 | 21% | `{"close_h": 9.0, "open_h": 3.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | CHINA50 | M30 | 0.25% | -20 | -276 | -372 | -25 | 83 | 29% | `{"close_h": 9.0, "open_h": 3.5, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | CHINA50 | M30 | 0.25% | -30 | -413 | -456 | -25 | 83 | 14% | `{"close_h": 9.0, "open_h": 3.5, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | CHINA50 | M30 | none | -43 | -607 | -657 | -25 | 161 | 29% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | CHINA50 | M30 | none | -46 | -641 | -681 | -25 | 161 | 14% | `{"close_h": 9.0, "open_h": 3.5, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | HK50 | H1 | 0.25% | -4 | -111 | -411 | -25 | 157 | 32% | `{"close_h": 10.0, "open_h": 3.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | HK50 | H1 | 0.50% | -10 | -260 | -566 | -50 | 157 | 36% | `{"close_h": 10.0, "open_h": 3.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | HK50 | H1 | none | -12 | -302 | -606 | -25 | 285 | 36% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | HK50 | H1 | 0.25% | -12 | -312 | -453 | -25 | 285 | 32% | `{"close_h": 10.0, "open_h": 3.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | HK50 | M30 | none | -9 | -234 | -665 | -25 | 292 | 44% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | HK50 | M30 | 0.25% | -11 | -287 | -524 | -25 | 162 | 36% | `{"close_h": 10.0, "open_h": 3.5, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | HK50 | M30 | 0.25% | -19 | -468 | -490 | -25 | 162 | 28% | `{"close_h": 10.0, "open_h": 3.5, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | HK50 | M30 | none | -19 | -477 | -657 | -25 | 292 | 24% | `{"close_h": 10.0, "open_h": 3.5, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | JPN225 | H1 | 1.00% | -17 | -422 | -489 | -93 | 12 | 4% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | JPN225 | H1 | 1.00% | -17 | -422 | -489 | -93 | 12 | 4% | `{"close_h": 8.0, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | JPN225 | H1 | 1.00% | -20 | -495 | -539 | -93 | 23 | 12% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | JPN225 | H1 | 1.00% | -22 | -538 | -577 | -93 | 23 | 12% | `{"close_h": 8.0, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | JPN225 | M30 | 0.50% | -7 | -187 | -187 | -48 | 4 | 0% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 1.5}` |
| pdhl_fade | JPN225 | M30 | 0.50% | -7 | -187 | -187 | -48 | 4 | 0% | `{"close_h": 8.5, "open_h": 2.0, "side": "both", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | JPN225 | M30 | 0.75% | -18 | -448 | -448 | -73 | 10 | 4% | `{"close_h": 8.5, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 3.0}` |
| pdhl_fade | JPN225 | M30 | 0.75% | -19 | -474 | -474 | -73 | 10 | 4% | `{"close_h": 8.5, "open_h": 2.0, "side": "short", "sl_atr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | H1 | none | -27 | -591 | -669 | -60 | 284 | 36% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | AUS200 | H1 | none | -28 | -625 | -701 | -60 | 284 | 50% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | H1 | none | -33 | -725 | -818 | -60 | 375 | 45% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | H1 | none | -35 | -760 | -838 | -60 | 375 | 41% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | AUS200 | H1 | none | -41 | -912 | -986 | -25 | 284 | 32% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | H1 | none | -55 | -1205 | -1223 | -25 | 284 | 27% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | AUS200 | H1 | none | -59 | -1305 | -1426 | -25 | 375 | 32% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | H1 | none | -74 | -1638 | -1680 | -25 | 375 | 18% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | AUS200 | M30 | none | 5 | 114 | -654 | -31 | 334 | 45% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | M30 | none | 3 | 58 | -719 | -31 | 396 | 36% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | M30 | none | -3 | -56 | -879 | -74 | 396 | 45% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | AUS200 | M30 | none | -6 | -138 | -1010 | -74 | 334 | 41% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | AUS200 | M30 | none | -69 | -1508 | -1598 | -25 | 334 | 41% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | AUS200 | M30 | none | -72 | -1586 | -1688 | -25 | 396 | 32% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | AUS200 | M30 | none | -76 | -1679 | -1795 | -25 | 334 | 18% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | AUS200 | M30 | none | -82 | -1794 | -1915 | -25 | 396 | 27% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | H1 | none | -75 | -1049 | -1273 | -25 | 223 | 21% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | H1 | none | -90 | -1265 | -1528 | -25 | 251 | 14% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | H1 | none | -96 | -1338 | -1416 | -25 | 223 | 21% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | H1 | none | -98 | -1377 | -1448 | -25 | 223 | 21% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | H1 | none | -104 | -1450 | -1530 | -25 | 223 | 14% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | H1 | none | -113 | -1575 | -1690 | -25 | 251 | 7% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | H1 | none | -116 | -1630 | -1708 | -25 | 251 | 21% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | H1 | none | -125 | -1752 | -1794 | -25 | 251 | 7% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | M30 | none | -91 | -1280 | -1461 | -25 | 239 | 29% | `{"close_h": 9.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | M30 | none | -120 | -1682 | -1863 | -25 | 265 | 21% | `{"close_h": 9.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | M30 | none | -122 | -1712 | -1730 | -25 | 239 | 0% | `{"close_h": 9.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | M30 | none | -125 | -1753 | -1762 | -25 | 239 | 0% | `{"close_h": 9.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | M30 | none | -139 | -1946 | -1965 | -25 | 265 | 0% | `{"close_h": 9.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | M30 | none | -151 | -2110 | -2110 | -25 | 265 | 0% | `{"close_h": 9.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | CHINA50 | M30 | none | -159 | -2229 | -2290 | -25 | 239 | 7% | `{"close_h": 9.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | CHINA50 | M30 | none | -187 | -2612 | -2666 | -25 | 265 | 7% | `{"close_h": 9.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | H1 | none | -16 | -401 | -686 | -41 | 349 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | H1 | none | -26 | -639 | -1037 | -81 | 349 | 28% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | HK50 | H1 | none | -26 | -661 | -810 | -41 | 415 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | H1 | none | -32 | -791 | -1135 | -81 | 415 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | HK50 | H1 | none | -74 | -1842 | -1935 | -69 | 349 | 16% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | H1 | none | -81 | -2032 | -2139 | -93 | 415 | 32% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | H1 | none | -86 | -2151 | -2170 | -69 | 349 | 16% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | HK50 | H1 | none | -98 | -2459 | -2573 | -93 | 415 | 20% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | HK50 | M30 | none | -49 | -1225 | -1365 | -25 | 378 | 28% | `{"close_h": 10.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | M30 | none | -59 | -1471 | -2016 | -25 | 378 | 28% | `{"close_h": 10.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | HK50 | M30 | none | -71 | -1784 | -1784 | -25 | 441 | 32% | `{"close_h": 10.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | M30 | none | -76 | -1896 | -2273 | -25 | 441 | 28% | `{"close_h": 10.0, "open_h": 3.5, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | HK50 | M30 | none | -86 | -2144 | -2173 | -25 | 378 | 20% | `{"close_h": 10.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | M30 | none | -95 | -2367 | -2421 | -88 | 441 | 16% | `{"close_h": 10.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | HK50 | M30 | none | -106 | -2647 | -2758 | -25 | 378 | 16% | `{"close_h": 10.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | HK50 | M30 | none | -124 | -3089 | -3151 | -113 | 441 | 8% | `{"close_h": 10.0, "open_h": 3.5, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | JPN225 | H1 | 0.75% | 7 | 179 | -334 | -73 | 20 | 16% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | H1 | 0.75% | 6 | 158 | -464 | -73 | 27 | 20% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | H1 | 0.75% | -0 | -6 | -466 | -75 | 20 | 8% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | JPN225 | H1 | 0.75% | -8 | -210 | -590 | -75 | 27 | 8% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | JPN225 | H1 | 0.75% | -10 | -257 | -428 | -75 | 27 | 12% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | H1 | 0.75% | -15 | -369 | -540 | -75 | 20 | 12% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | H1 | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | JPN225 | H1 | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | JPN225 | M30 | 0.50% | 14 | 344 | -263 | -50 | 18 | 20% | `{"close_h": 8.5, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| prev_session_follow | JPN225 | M30 | 0.50% | 8 | 193 | -263 | -50 | 15 | 16% | `{"close_h": 8.5, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -1 | -18 | -263 | -50 | 18 | 20% | `{"close_h": 8.5, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -1 | -29 | -222 | -50 | 15 | 16% | `{"close_h": 8.5, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -7 | -166 | -360 | -50 | 18 | 16% | `{"close_h": 8.5, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -7 | -173 | -263 | -50 | 15 | 12% | `{"close_h": 8.5, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 1.5}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -10 | -255 | -424 | -50 | 15 | 8% | `{"close_h": 8.5, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 1.0, "tp_atr": 0}` |
| prev_session_follow | JPN225 | M30 | 0.50% | -16 | -393 | -562 | -50 | 18 | 8% | `{"close_h": 8.5, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.5, "tp_atr": 0}` |
| round_bounce | AUS200 | H1 | none | -32 | -701 | -836 | -62 | 338 | 41% | `{"hours": [1, 11], "step": 100, "tp_atr": 1.5}` |
| round_bounce | AUS200 | H1 | none | -34 | -741 | -1267 | -97 | 635 | 32% | `{"hours": [1, 11], "step": 50, "tp_atr": 3.0}` |
| round_bounce | AUS200 | H1 | none | -35 | -765 | -1004 | -97 | 660 | 27% | `{"hours": [1, 11], "step": 50, "tp_atr": 1.5}` |
| round_bounce | AUS200 | H1 | none | -47 | -1030 | -1185 | -62 | 324 | 18% | `{"hours": [1, 11], "step": 100, "tp_atr": 3.0}` |
| round_bounce | AUS200 | M30 | none | -26 | -563 | -1334 | -101 | 789 | 27% | `{"hours": [1, 11], "step": 50, "tp_atr": 3.0}` |
| round_bounce | AUS200 | M30 | none | -32 | -699 | -885 | -101 | 413 | 45% | `{"hours": [1, 11], "step": 100, "tp_atr": 1.5}` |
| round_bounce | AUS200 | M30 | none | -34 | -745 | -1045 | -101 | 396 | 36% | `{"hours": [1, 11], "step": 100, "tp_atr": 3.0}` |
| round_bounce | AUS200 | M30 | none | -57 | -1253 | -1506 | -101 | 819 | 32% | `{"hours": [1, 11], "step": 50, "tp_atr": 1.5}` |
| round_bounce | CHINA50 | H1 | none | -47 | -655 | -680 | -59 | 222 | 21% | `{"hours": [1, 11], "step": 250, "tp_atr": 1.5}` |
| round_bounce | CHINA50 | H1 | none | -49 | -689 | -713 | -61 | 206 | 14% | `{"hours": [1, 11], "step": 250, "tp_atr": 3.0}` |
| round_bounce | CHINA50 | H1 | none | -60 | -833 | -907 | -70 | 439 | 14% | `{"hours": [1, 11], "step": 100, "tp_atr": 3.0}` |
| round_bounce | CHINA50 | H1 | none | -76 | -1066 | -1112 | -70 | 478 | 14% | `{"hours": [1, 11], "step": 100, "tp_atr": 1.5}` |
| round_bounce | CHINA50 | M30 | none | -83 | -1158 | -1162 | -70 | 274 | 14% | `{"hours": [1, 11], "step": 250, "tp_atr": 3.0}` |
| round_bounce | CHINA50 | M30 | none | -88 | -1228 | -1232 | -70 | 296 | 7% | `{"hours": [1, 11], "step": 250, "tp_atr": 1.5}` |
| round_bounce | CHINA50 | M30 | none | -148 | -2065 | -2109 | -81 | 632 | 7% | `{"hours": [1, 11], "step": 100, "tp_atr": 3.0}` |
| round_bounce | CHINA50 | M30 | none | -205 | -2870 | -2885 | -77 | 686 | 7% | `{"hours": [1, 11], "step": 100, "tp_atr": 1.5}` |
| round_bounce | HK50 | H1 | 0.25% | -11 | -280 | -545 | -64 | 307 | 44% | `{"hours": [1, 11], "step": 500, "tp_atr": 1.5}` |
| round_bounce | HK50 | H1 | none | -14 | -347 | -643 | -64 | 599 | 36% | `{"hours": [1, 11], "step": 250, "tp_atr": 1.5}` |
| round_bounce | HK50 | H1 | none | -22 | -557 | -638 | -95 | 303 | 40% | `{"hours": [1, 11], "step": 500, "tp_atr": 3.0}` |
| round_bounce | HK50 | H1 | none | -22 | -559 | -634 | -95 | 568 | 40% | `{"hours": [1, 11], "step": 250, "tp_atr": 3.0}` |
| round_bounce | HK50 | M30 | none | -46 | -1155 | -1213 | -113 | 380 | 24% | `{"hours": [1, 11], "step": 500, "tp_atr": 3.0}` |
| round_bounce | HK50 | M30 | none | -51 | -1281 | -1386 | -66 | 395 | 32% | `{"hours": [1, 11], "step": 500, "tp_atr": 1.5}` |
| round_bounce | HK50 | M30 | none | -94 | -2352 | -2390 | -113 | 757 | 20% | `{"hours": [1, 11], "step": 250, "tp_atr": 3.0}` |
| round_bounce | HK50 | M30 | none | -102 | -2557 | -2646 | -89 | 801 | 16% | `{"hours": [1, 11], "step": 250, "tp_atr": 1.5}` |
| round_bounce | JPN225 | H1 | 1.00% | 26 | 660 | -431 | -98 | 27 | 24% | `{"hours": [1, 11], "step": 1000, "tp_atr": 3.0}` |
| round_bounce | JPN225 | H1 | 1.00% | 10 | 257 | -315 | -98 | 27 | 24% | `{"hours": [1, 11], "step": 1000, "tp_atr": 1.5}` |
| round_bounce | JPN225 | H1 | 0.75% | 7 | 165 | -159 | -74 | 7 | 12% | `{"hours": [1, 11], "step": 500, "tp_atr": 1.5}` |
| round_bounce | JPN225 | H1 | 1.00% | -4 | -102 | -561 | -98 | 52 | 24% | `{"hours": [1, 11], "step": 500, "tp_atr": 3.0}` |
| round_bounce | JPN225 | M30 | 0.75% | 11 | 269 | -496 | -117 | 39 | 28% | `{"hours": [1, 11], "step": 1000, "tp_atr": 3.0}` |
| round_bounce | JPN225 | M30 | 0.75% | 3 | 86 | -383 | -117 | 39 | 32% | `{"hours": [1, 11], "step": 1000, "tp_atr": 1.5}` |
| round_bounce | JPN225 | M30 | 0.50% | 0 | 2 | -98 | -49 | 4 | 8% | `{"hours": [1, 11], "step": 500, "tp_atr": 1.5}` |
| round_bounce | JPN225 | M30 | 0.50% | -4 | -88 | -181 | -49 | 4 | 4% | `{"hours": [1, 11], "step": 500, "tp_atr": 3.0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 44 | 970 | -472 | -229 | 57 | 64% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 41 | 911 | -453 | -186 | 112 | 50% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 40 | 884 | -531 | -229 | 53 | 64% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 40 | 876 | -410 | -229 | 34 | 59% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 1.25% | 39 | 848 | -577 | -162 | 118 | 50% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 38 | 826 | -422 | -229 | 33 | 59% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 35 | 772 | -524 | -186 | 88 | 55% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.50% | 35 | 770 | -473 | -147 | 115 | 55% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.50% | 22 | 488 | -483 | -109 | 156 | 55% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 21 | 469 | -205 | -131 | 33 | 59% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 21 | 460 | -304 | -131 | 31 | 59% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 20 | 430 | -251 | -197 | 10 | 41% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.00% | 19 | 422 | -512 | -126 | 101 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 17 | 374 | -293 | -131 | 56 | 64% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 1.50% | 17 | 372 | -510 | -109 | 122 | 55% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 14 | 319 | -591 | -186 | 82 | 59% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 13 | 287 | -514 | -197 | 51 | 64% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 12 | 270 | -525 | -196 | 39 | 41% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | AUS200 | D1 | 0.75% | 12 | 259 | -426 | -90 | 166 | 55% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.50% | 11 | 248 | -560 | -147 | 71 | 59% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 10 | 228 | -446 | -131 | 51 | 55% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 9 | 195 | -585 | -186 | 64 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 0.75% | 8 | 186 | -463 | -90 | 142 | 55% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 7 | 165 | -477 | -229 | 22 | 41% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 7 | 165 | -548 | -229 | 22 | 41% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 4 | 95 | -239 | -197 | 6 | 23% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 4 | 81 | -237 | -131 | 21 | 41% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 2.00% | 4 | 79 | -304 | -131 | 20 | 41% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | D1 | 1.00% | 4 | 78 | -578 | -126 | 88 | 59% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | 3 | 77 | -301 | -131 | 24 | 32% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 2.00% | 3 | 59 | -399 | -131 | 36 | 23% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.50% | 2 | 42 | -477 | -172 | 25 | 32% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 2.00% | 2 | 36 | -408 | -131 | 34 | 23% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 2.00% | -1 | -20 | -537 | -197 | 25 | 41% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | -1 | -24 | -364 | -131 | 22 | 27% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 0.75% | -2 | -54 | -424 | -90 | 76 | 55% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.25% | -3 | -69 | -561 | -143 | 39 | 23% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 2.00% | -5 | -99 | -389 | -131 | 17 | 23% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.25% | -5 | -119 | -541 | -126 | 51 | 55% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.25% | -8 | -174 | -500 | -143 | 18 | 23% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 2.00% | -8 | -176 | -427 | -131 | 16 | 18% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.00% | -9 | -189 | -554 | -115 | 37 | 23% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.25% | -9 | -198 | -489 | -143 | 23 | 27% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.25% | -10 | -212 | -528 | -126 | 32 | 36% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.25% | -15 | -321 | -530 | -126 | 26 | 32% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 1.00% | -15 | -325 | -505 | -115 | 17 | 18% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | D1 | 1.50% | -17 | -379 | -529 | -144 | 14 | 9% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | D1 | 2.00% | -23 | -495 | -553 | -196 | 13 | 5% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | AUS200 | H1 | none | -20 | -450 | -880 | -104 | 1381 | 41% | `{"hi": 90, "lo": 10, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H1 | none | -21 | -454 | -876 | -104 | 1386 | 41% | `{"hi": 90, "lo": 10, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H1 | none | -85 | -1880 | -2188 | -124 | 2636 | 32% | `{"hi": 75, "lo": 25, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H1 | none | -87 | -1910 | -2223 | -124 | 2644 | 32% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 88 | 1933 | -565 | -245 | 191 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 2.00% | 81 | 1780 | -443 | -197 | 173 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 1.25% | 79 | 1736 | -534 | -245 | 212 | 64% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 2.00% | 70 | 1548 | -543 | -200 | 223 | 59% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 1.00% | 62 | 1358 | -547 | -229 | 360 | 64% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 60 | 1326 | -568 | -258 | 438 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 2.00% | 60 | 1311 | -479 | -197 | 207 | 59% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 1.50% | 52 | 1136 | -525 | -233 | 141 | 55% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.50% | 51 | 1124 | -508 | -167 | 516 | 68% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 48 | 1046 | -582 | -171 | 343 | 68% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.50% | 48 | 1046 | -478 | -264 | 98 | 55% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | AUS200 | H4 | 1.25% | 42 | 927 | -556 | -130 | 320 | 55% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 1.00% | 41 | 899 | -583 | -176 | 565 | 73% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.00% | 41 | 898 | -564 | -183 | 727 | 50% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 2.00% | 40 | 881 | -421 | -200 | 123 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.75% | 39 | 855 | -520 | -154 | 359 | 50% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 1.50% | 37 | 822 | -574 | -194 | 270 | 55% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 0.75% | 35 | 769 | -493 | -146 | 278 | 55% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 2.00% | 33 | 734 | -456 | -200 | 140 | 59% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 1.25% | 32 | 698 | -576 | -291 | 141 | 50% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.25% | 31 | 684 | -564 | -150 | 389 | 55% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 0.50% | 31 | 682 | -507 | -111 | 474 | 64% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.50% | 30 | 667 | -598 | -265 | 127 | 59% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.75% | 28 | 618 | -450 | -132 | 536 | 45% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 2.00% | 26 | 576 | -571 | -200 | 204 | 50% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 1.00% | 23 | 507 | -551 | -178 | 279 | 55% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | AUS200 | H4 | 1.25% | 21 | 452 | -528 | -291 | 72 | 68% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.50% | 20 | 433 | -501 | -148 | 179 | 64% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.50% | 19 | 409 | -402 | -96 | 249 | 59% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 0.50% | 18 | 387 | -439 | -113 | 403 | 50% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | AUS200 | H4 | 0.25% | 17 | 364 | -379 | -67 | 635 | 55% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.25% | 16 | 352 | -328 | -77 | 597 | 68% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 15 | 336 | -452 | -174 | 60 | 68% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.25% | 13 | 296 | -342 | -67 | 845 | 45% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.00% | 13 | 295 | -565 | -191 | 207 | 45% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.75% | 13 | 282 | -495 | -171 | 224 | 68% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 12 | 267 | -572 | -171 | 167 | 64% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.50% | 11 | 235 | -400 | -100 | 698 | 55% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.25% | 8 | 167 | -501 | -76 | 738 | 45% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 7 | 161 | -508 | -174 | 33 | 59% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 1.00% | 7 | 161 | -591 | -191 | 188 | 55% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.50% | 6 | 128 | -402 | -100 | 946 | 45% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.50% | 6 | 125 | -490 | -94 | 300 | 50% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.25% | 5 | 120 | -507 | -76 | 995 | 41% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | AUS200 | H4 | 0.75% | 4 | 77 | -459 | -74 | 285 | 59% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.50% | 3 | 57 | -526 | -93 | 330 | 50% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 1.00% | 2 | 49 | -570 | -100 | 324 | 50% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | AUS200 | H4 | 0.25% | -2 | -40 | -348 | -64 | 720 | 41% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 82 | 1149 | -482 | -149 | 71 | 50% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 56 | 780 | -598 | -190 | 65 | 64% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.50% | 56 | 779 | -567 | -144 | 87 | 57% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.50% | 48 | 669 | -445 | -109 | 57 | 64% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 48 | 666 | -319 | -127 | 34 | 71% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 46 | 647 | -551 | -164 | 44 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.25% | 46 | 639 | -524 | -122 | 97 | 64% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 36 | 506 | -201 | -103 | 15 | 43% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 33 | 468 | -447 | -190 | 51 | 57% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 32 | 445 | -332 | -128 | 27 | 57% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 27 | 374 | -533 | -114 | 95 | 57% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 26 | 371 | -331 | -117 | 64 | 64% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 26 | 367 | -370 | -137 | 27 | 57% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 26 | 359 | -243 | -128 | 13 | 50% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 25 | 354 | -563 | -117 | 76 | 57% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 17 | 232 | -308 | -117 | 50 | 57% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 15 | 212 | -117 | -101 | 5 | 21% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 15 | 208 | -332 | -137 | 13 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 1.50% | 15 | 207 | -489 | -112 | 45 | 71% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 12 | 173 | -151 | -56 | 27 | 57% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 11 | 159 | -340 | -117 | 52 | 64% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 11 | 155 | -237 | -87 | 7 | 36% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 9 | 131 | -117 | -101 | 3 | 14% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 9 | 128 | -94 | -52 | 13 | 50% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 6 | 87 | -517 | -135 | 31 | 57% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 5 | 74 | -181 | -105 | 5 | 14% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 4 | 51 | -208 | -75 | 26 | 50% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 3 | 47 | -181 | -105 | 5 | 14% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 3 | 45 | -324 | -117 | 40 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 35 | -91 | -52 | 5 | 14% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 26 | -91 | -52 | 5 | 14% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 24 | -181 | -105 | 2 | 14% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 24 | -181 | -105 | 2 | 14% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 24 | -181 | -105 | 2 | 14% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 2 | 24 | -181 | -105 | 2 | 14% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 1 | 10 | -91 | -52 | 2 | 14% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 1 | 10 | -91 | -52 | 2 | 14% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 1 | 10 | -91 | -52 | 2 | 14% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | 1 | 10 | -91 | -52 | 2 | 14% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -3 | -44 | -140 | -52 | 8 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -4 | -63 | -294 | -115 | 8 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -6 | -80 | -288 | -75 | 13 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -10 | -147 | -418 | -165 | 9 | 29% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 1.50% | -13 | -183 | -538 | -112 | 25 | 64% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -14 | -195 | -418 | -165 | 7 | 21% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -15 | -214 | -445 | -137 | 8 | 36% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -16 | -222 | -541 | -135 | 19 | 50% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | D1 | 2.00% | -18 | -253 | -349 | -75 | 8 | 36% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H1 | none | -95 | -1333 | -1468 | -83 | 801 | 21% | `{"hi": 90, "lo": 10, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H1 | none | -98 | -1369 | -1504 | -83 | 814 | 7% | `{"hi": 90, "lo": 10, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H1 | none | -187 | -2617 | -2714 | -108 | 1354 | 14% | `{"hi": 75, "lo": 25, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H1 | none | -190 | -2664 | -2760 | -108 | 1372 | 14% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 2.00% | 56 | 785 | -520 | -198 | 103 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.50% | 52 | 729 | -506 | -172 | 53 | 64% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.25% | 34 | 478 | -554 | -227 | 112 | 43% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 2.00% | 31 | 428 | -494 | -198 | 90 | 50% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.00% | 27 | 377 | -552 | -162 | 118 | 43% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.75% | 21 | 294 | -549 | -162 | 291 | 64% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.00% | 20 | 275 | -577 | -149 | 231 | 50% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.00% | 19 | 261 | -444 | -191 | 299 | 50% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.00% | 15 | 213 | -385 | -191 | 250 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.75% | 5 | 65 | -443 | -108 | 103 | 43% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.75% | 4 | 54 | -578 | -132 | 218 | 50% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | 3 | 45 | -589 | -138 | 356 | 36% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | 3 | 43 | -494 | -138 | 300 | 43% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.00% | 1 | 18 | -419 | -108 | 143 | 36% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.00% | -1 | -14 | -468 | -98 | 135 | 36% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.50% | -3 | -41 | -549 | -189 | 68 | 43% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | CHINA50 | H4 | 1.50% | -4 | -58 | -559 | -147 | 85 | 43% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -7 | -98 | -388 | -68 | 115 | 43% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 1.00% | -7 | -99 | -508 | -171 | 62 | 43% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -7 | -103 | -459 | -81 | 165 | 36% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.25% | -9 | -132 | -562 | -125 | 109 | 43% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.75% | -11 | -155 | -473 | -106 | 89 | 36% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -11 | -156 | -370 | -74 | 393 | 36% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.25% | -12 | -167 | -589 | -119 | 117 | 43% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 1.50% | -12 | -169 | -499 | -162 | 25 | 43% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -13 | -185 | -585 | -77 | 145 | 36% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -14 | -192 | -464 | -56 | 135 | 29% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | CHINA50 | H4 | 0.75% | -15 | -206 | -535 | -132 | 110 | 43% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -15 | -212 | -336 | -37 | 368 | 29% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 1.25% | -15 | -212 | -499 | -114 | 99 | 50% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.75% | -15 | -212 | -538 | -162 | 151 | 36% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -16 | -223 | -376 | -64 | 327 | 29% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -17 | -232 | -321 | -33 | 204 | 29% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -18 | -250 | -579 | -68 | 133 | 29% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 1.00% | -18 | -252 | -587 | -98 | 128 | 29% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -18 | -252 | -394 | -63 | 356 | 29% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -18 | -258 | -479 | -63 | 429 | 29% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -19 | -261 | -478 | -96 | 372 | 29% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -19 | -266 | -332 | -33 | 161 | 29% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -20 | -285 | -449 | -68 | 103 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -20 | -286 | -568 | -68 | 125 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -23 | -324 | -415 | -49 | 147 | 29% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.75% | -24 | -339 | -522 | -78 | 192 | 21% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -26 | -366 | -406 | -33 | 189 | 29% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | 0.25% | -27 | -377 | -525 | -63 | 450 | 21% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -28 | -397 | -597 | -74 | 510 | 29% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | CHINA50 | H4 | 0.50% | -29 | -403 | -473 | -49 | 181 | 21% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | CHINA50 | H4 | none | -38 | -537 | -683 | -63 | 560 | 21% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 20 | 493 | -593 | -289 | 43 | 52% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 17 | 427 | -339 | -155 | 10 | 20% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 16 | 392 | -380 | -289 | 27 | 40% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | 14 | 351 | -497 | -289 | 66 | 52% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.50% | 13 | 328 | -500 | -224 | 70 | 60% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 13 | 320 | -171 | -99 | 3 | 12% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 12 | 309 | -552 | -200 | 109 | 52% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | 11 | 265 | -574 | -222 | 63 | 44% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.00% | 9 | 231 | -528 | -133 | 93 | 52% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | 8 | 201 | -506 | -289 | 57 | 52% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 2.00% | 8 | 200 | -339 | -200 | 63 | 48% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.50% | 7 | 174 | -543 | -133 | 89 | 56% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 0.75% | 6 | 142 | -469 | -133 | 106 | 64% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.25% | 6 | 141 | -496 | -244 | 50 | 52% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.00% | 5 | 134 | -590 | -200 | 116 | 56% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.25% | 4 | 109 | -517 | -244 | 44 | 48% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 0.75% | 4 | 97 | -460 | -133 | 122 | 64% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | 3 | 74 | -497 | -178 | 51 | 52% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 2.00% | 3 | 65 | -374 | -291 | 9 | 20% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | 1 | 21 | -556 | -289 | 42 | 40% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.50% | -0 | -8 | -552 | -139 | 132 | 56% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | -0 | -9 | -403 | -200 | 48 | 48% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.50% | -1 | -13 | -557 | -224 | 23 | 32% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | -1 | -21 | -583 | -289 | 38 | 44% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.25% | -1 | -28 | -484 | -122 | 104 | 60% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 0.75% | -1 | -37 | -472 | -133 | 139 | 64% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.00% | -2 | -60 | -487 | -133 | 129 | 56% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | -3 | -87 | -369 | -200 | 36 | 48% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -4 | -96 | -365 | -200 | 32 | 48% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -4 | -103 | -378 | -200 | 39 | 40% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 0.75% | -4 | -107 | -533 | -133 | 150 | 56% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.25% | -5 | -120 | -509 | -122 | 169 | 48% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 1.50% | -6 | -138 | -502 | -289 | 40 | 56% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -6 | -138 | -420 | -200 | 33 | 48% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 1.50% | -6 | -143 | -551 | -289 | 33 | 48% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 1.25% | -6 | -147 | -506 | -122 | 129 | 48% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 0.50% | -6 | -148 | -426 | -89 | 176 | 52% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | D1 | 2.00% | -7 | -168 | -555 | -200 | 39 | 48% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | D1 | 2.00% | -8 | -199 | -487 | -291 | 22 | 32% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | HK50 | D1 | 1.50% | -8 | -211 | -510 | -289 | 46 | 56% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 1.50% | -9 | -231 | -553 | -289 | 37 | 48% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 1.50% | -11 | -287 | -479 | -200 | 48 | 52% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | HK50 | D1 | 1.00% | -12 | -295 | -551 | -178 | 56 | 44% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 1.00% | -13 | -314 | -520 | -200 | 65 | 44% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -13 | -331 | -544 | -200 | 39 | 56% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 1.50% | -13 | -331 | -456 | -156 | 64 | 48% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -13 | -336 | -549 | -200 | 45 | 56% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | D1 | 2.00% | -13 | -337 | -596 | -191 | 55 | 48% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H1 | none | -64 | -1590 | -1744 | -95 | 1141 | 36% | `{"hi": 90, "lo": 10, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H1 | none | -64 | -1604 | -1773 | -95 | 1150 | 32% | `{"hi": 90, "lo": 10, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H1 | none | -141 | -3522 | -3547 | -95 | 2057 | 20% | `{"hi": 75, "lo": 25, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H1 | none | -142 | -3542 | -3567 | -95 | 2072 | 20% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | 8 | 193 | -501 | -251 | 174 | 60% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | 5 | 126 | -456 | -121 | 362 | 60% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | 3 | 81 | -408 | -251 | 82 | 56% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | 3 | 69 | -321 | -251 | 78 | 56% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | 2 | 40 | -296 | -38 | 397 | 60% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | -0 | -11 | -329 | -251 | 171 | 56% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | -2 | -43 | -322 | -251 | 37 | 36% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.75% | -4 | -98 | -589 | -82 | 177 | 60% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -7 | -170 | -385 | -42 | 269 | 36% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | HK50 | H4 | 0.25% | -7 | -171 | -271 | -26 | 274 | 40% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 1.00% | -7 | -177 | -564 | -115 | 127 | 56% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | HK50 | H4 | 0.25% | -7 | -180 | -354 | -49 | 207 | 52% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -7 | -181 | -363 | -33 | 422 | 36% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.75% | -8 | -195 | -570 | -82 | 225 | 52% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -8 | -209 | -394 | -49 | 239 | 48% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -8 | -209 | -281 | -27 | 332 | 28% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.25% | -9 | -231 | -332 | -31 | 563 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | -10 | -245 | -314 | -30 | 389 | 28% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -10 | -255 | -340 | -35 | 157 | 40% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -10 | -262 | -543 | -61 | 221 | 44% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -11 | -267 | -386 | -47 | 209 | 44% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -12 | -290 | -519 | -61 | 285 | 40% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.50% | -12 | -294 | -479 | -50 | 148 | 44% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -12 | -304 | -497 | -51 | 195 | 48% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.25% | -12 | -305 | -487 | -30 | 494 | 36% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | -12 | -308 | -406 | -40 | 234 | 40% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -12 | -311 | -517 | -63 | 291 | 40% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -13 | -326 | -359 | -35 | 176 | 44% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -13 | -329 | -504 | -251 | 232 | 36% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.50% | -14 | -347 | -418 | -50 | 171 | 36% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.50% | -15 | -369 | -471 | -51 | 227 | 40% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.25% | -15 | -374 | -532 | -51 | 303 | 44% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | 0.25% | -15 | -376 | -574 | -46 | 297 | 40% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.25% | -16 | -388 | -574 | -53 | 338 | 36% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | HK50 | H4 | 0.25% | -16 | -400 | -496 | -31 | 672 | 32% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | -16 | -401 | -556 | -41 | 629 | 24% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | 0.25% | -17 | -419 | -564 | -51 | 262 | 32% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | none | -18 | -458 | -614 | -63 | 345 | 40% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | none | -19 | -481 | -743 | -59 | 520 | 36% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -21 | -532 | -852 | -121 | 474 | 32% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -22 | -560 | -693 | -63 | 408 | 24% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | HK50 | H4 | none | -24 | -600 | -724 | -41 | 881 | 24% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -27 | -669 | -857 | -59 | 601 | 32% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -30 | -743 | -1013 | -54 | 659 | 28% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -33 | -813 | -1081 | -59 | 614 | 20% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -38 | -957 | -1161 | -59 | 717 | 32% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -44 | -1110 | -1404 | -63 | 778 | 20% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | HK50 | H4 | none | -58 | -1439 | -1665 | -63 | 934 | 20% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | D1 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H1 | 1.25% | 82 | 2061 | -241 | -186 | 81 | 28% | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H1 | 1.25% | 82 | 2061 | -241 | -186 | 81 | 28% | `{"hi": 75, "lo": 25, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H1 | 1.25% | 43 | 1073 | -241 | -160 | 40 | 24% | `{"hi": 90, "lo": 10, "max_hold": 8, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H1 | 1.25% | 43 | 1073 | -241 | -160 | 40 | 24% | `{"hi": 90, "lo": 10, "max_hold": 16, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 25 | 627 | -290 | -200 | 12 | 16% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 25 | 627 | -290 | -200 | 12 | 16% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 16 | 389 | -290 | -200 | 8 | 8% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 16 | 389 | -290 | -200 | 8 | 8% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 12 | 296 | -293 | -184 | 7 | 8% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 12 | 296 | -293 | -184 | 7 | 8% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 2 | 44 | 0 | 0 | 1 | 4% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 2 | 44 | 0 | 0 | 1 | 4% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | -1 | -31 | -184 | -184 | 4 | 4% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | -1 | -31 | -184 | -184 | 4 | 4% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | -3 | -74 | -184 | -184 | 2 | 4% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | -3 | -74 | -184 | -184 | 2 | 4% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | -6 | -141 | -184 | -184 | 2 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | -6 | -141 | -184 | -184 | 2 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | -7 | -181 | -181 | -181 | 1 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | -7 | -181 | -181 | -181 | 1 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | -7 | -184 | -184 | -184 | 1 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | -7 | -184 | -184 | -184 | 1 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2.0, "trend_n": 100}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 70, "lo": 30, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 50}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 3, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 80, "lo": 20, "max_hold": 8, "n": 2, "sl_atr": 3.0, "trend_n": 200}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 3, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 90, "lo": 10, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "both", "sl_atr": 2.0, "trend_n": 0}` |
| rsi_mr | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 4, "side": "long", "sl_atr": 2.0, "trend_n": 0}` |
| session_pullback | AUS200 | H1 | none | -28 | -619 | -673 | -25 | 242 | 27% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | AUS200 | H1 | none | -36 | -802 | -869 | -25 | 282 | 23% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | AUS200 | H1 | none | -55 | -1217 | -1219 | -25 | 318 | 18% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.35}` |
| session_pullback | AUS200 | H1 | none | -62 | -1366 | -1367 | -25 | 369 | 27% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | AUS200 | M30 | none | -39 | -849 | -1049 | -56 | 342 | 32% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | AUS200 | M30 | none | -39 | -850 | -1020 | -56 | 364 | 32% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | AUS200 | M30 | none | -44 | -977 | -1258 | -28 | 415 | 23% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | AUS200 | M30 | none | -53 | -1156 | -1372 | -28 | 397 | 18% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.35}` |
| session_pullback | CHINA50 | H1 | none | -49 | -691 | -758 | -52 | 143 | 14% | `{"close_h": 9.0, "open_h": 3.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | CHINA50 | H1 | none | -50 | -707 | -774 | -52 | 142 | 14% | `{"close_h": 9.0, "open_h": 3.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | CHINA50 | H1 | none | -61 | -859 | -924 | -52 | 192 | 21% | `{"close_h": 9.0, "open_h": 3.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | CHINA50 | H1 | none | -62 | -875 | -940 | -52 | 191 | 21% | `{"close_h": 9.0, "open_h": 3.0, "thr": 1.2, "tol": 0.35}` |
| session_pullback | CHINA50 | M30 | none | -122 | -1709 | -1756 | -25 | 182 | 14% | `{"close_h": 9.0, "open_h": 3.5, "thr": 0.8, "tol": 0.2}` |
| session_pullback | CHINA50 | M30 | none | -122 | -1709 | -1756 | -25 | 182 | 14% | `{"close_h": 9.0, "open_h": 3.5, "thr": 1.2, "tol": 0.2}` |
| session_pullback | CHINA50 | M30 | none | -146 | -2037 | -2097 | -25 | 212 | 14% | `{"close_h": 9.0, "open_h": 3.5, "thr": 0.8, "tol": 0.35}` |
| session_pullback | CHINA50 | M30 | none | -146 | -2037 | -2097 | -25 | 212 | 14% | `{"close_h": 9.0, "open_h": 3.5, "thr": 1.2, "tol": 0.35}` |
| session_pullback | HK50 | H1 | none | -38 | -940 | -974 | -52 | 267 | 32% | `{"close_h": 10.0, "open_h": 3.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | HK50 | H1 | none | -45 | -1114 | -1173 | -52 | 359 | 40% | `{"close_h": 10.0, "open_h": 3.0, "thr": 1.2, "tol": 0.35}` |
| session_pullback | HK50 | H1 | none | -46 | -1140 | -1163 | -52 | 286 | 28% | `{"close_h": 10.0, "open_h": 3.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | HK50 | H1 | none | -57 | -1437 | -1456 | -52 | 383 | 24% | `{"close_h": 10.0, "open_h": 3.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | HK50 | M30 | none | -74 | -1857 | -1905 | -50 | 434 | 24% | `{"close_h": 10.0, "open_h": 3.5, "thr": 0.8, "tol": 0.35}` |
| session_pullback | HK50 | M30 | none | -76 | -1900 | -1948 | -50 | 430 | 24% | `{"close_h": 10.0, "open_h": 3.5, "thr": 1.2, "tol": 0.35}` |
| session_pullback | HK50 | M30 | none | -84 | -2108 | -2167 | -43 | 378 | 28% | `{"close_h": 10.0, "open_h": 3.5, "thr": 0.8, "tol": 0.2}` |
| session_pullback | HK50 | M30 | none | -85 | -2132 | -2191 | -43 | 373 | 28% | `{"close_h": 10.0, "open_h": 3.5, "thr": 1.2, "tol": 0.2}` |
| session_pullback | JPN225 | H1 | 0.50% | 1 | 31 | -25 | -25 | 2 | 4% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | JPN225 | H1 | 0.75% | 1 | 13 | -516 | -74 | 89 | 28% | `{"close_h": 8.0, "open_h": 2.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | JPN225 | H1 | 0.50% | 0 | 3 | -44 | -44 | 3 | 8% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.35}` |
| session_pullback | JPN225 | H1 | 0.75% | -5 | -130 | -590 | -74 | 79 | 24% | `{"close_h": 8.0, "open_h": 2.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | JPN225 | M30 | 0.50% | -17 | -416 | -555 | -50 | 55 | 12% | `{"close_h": 8.5, "open_h": 2.0, "thr": 1.2, "tol": 0.2}` |
| session_pullback | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "open_h": 2.0, "thr": 0.8, "tol": 0.2}` |
| session_pullback | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "open_h": 2.0, "thr": 0.8, "tol": 0.35}` |
| session_pullback | JPN225 | M30 | 0.25% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.5, "open_h": 2.0, "thr": 1.2, "tol": 0.35}` |
| us_follow | AUS200 | H1 | none | -26 | -574 | -869 | -35 | 288 | 45% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | AUS200 | H1 | none | -40 | -879 | -961 | -35 | 360 | 41% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | AUS200 | H1 | none | -65 | -1440 | -1510 | -25 | 288 | 9% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | AUS200 | H1 | none | -73 | -1603 | -1726 | -25 | 360 | 18% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | CHINA50 | H1 | none | -48 | -672 | -744 | -25 | 116 | 29% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | CHINA50 | H1 | none | -56 | -778 | -1003 | -25 | 187 | 43% | `{"close_h": 9.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | CHINA50 | H1 | none | -62 | -863 | -1046 | -25 | 116 | 21% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | CHINA50 | H1 | none | -95 | -1335 | -1399 | -25 | 187 | 7% | `{"close_h": 9.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | HK50 | H1 | none | -24 | -593 | -615 | -69 | 245 | 44% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | HK50 | H1 | none | -31 | -764 | -764 | -69 | 358 | 40% | `{"close_h": 10.0, "open_h": 3.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | HK50 | H1 | none | -67 | -1671 | -1933 | -30 | 245 | 16% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | HK50 | H1 | none | -101 | -2514 | -2737 | -30 | 358 | 12% | `{"close_h": 10.0, "open_h": 3.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | JPN225 | H1 | 0.75% | 1 | 31 | -513 | -75 | 17 | 12% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | JPN225 | H1 | 0.75% | -11 | -271 | -509 | -75 | 24 | 8% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.3}` |
| us_follow | JPN225 | H1 | 0.75% | -12 | -288 | -419 | -75 | 17 | 8% | `{"close_h": 8.0, "open_h": 2.0, "sign": -1, "sl_atr": 1.0, "thr": 0.6}` |
| us_follow | JPN225 | H1 | 0.50% | 0 | 0 | 0 | 0 | 0 | 0% | `{"close_h": 8.0, "open_h": 2.0, "sign": 1, "sl_atr": 1.0, "thr": 0.3}` |
| weekly_break | AUS200 | H1 | 0.25% | -13 | -290 | -309 | -25 | 46 | 27% | `{"side": "long", "trail": 2.0}` |
| weekly_break | AUS200 | H1 | 0.25% | -15 | -331 | -350 | -34 | 45 | 23% | `{"side": "long", "trail": 3.0}` |
| weekly_break | AUS200 | H1 | 0.25% | -25 | -539 | -544 | -25 | 83 | 32% | `{"side": "both", "trail": 2.0}` |
| weekly_break | AUS200 | H1 | none | -36 | -796 | -807 | -34 | 82 | 14% | `{"side": "both", "trail": 3.0}` |
| weekly_break | AUS200 | H4 | 0.25% | -8 | -170 | -311 | -30 | 68 | 41% | `{"side": "both", "trail": 2.0}` |
| weekly_break | AUS200 | H4 | 0.25% | -15 | -324 | -371 | -40 | 36 | 14% | `{"side": "long", "trail": 3.0}` |
| weekly_break | AUS200 | H4 | 0.50% | -16 | -344 | -521 | -56 | 38 | 23% | `{"side": "long", "trail": 2.0}` |
| weekly_break | AUS200 | H4 | 0.25% | -19 | -421 | -511 | -45 | 64 | 27% | `{"side": "both", "trail": 3.0}` |
| weekly_break | CHINA50 | H1 | 0.25% | -9 | -128 | -387 | -73 | 50 | 21% | `{"side": "both", "trail": 2.0}` |
| weekly_break | CHINA50 | H1 | 0.25% | -19 | -270 | -474 | -73 | 50 | 21% | `{"side": "both", "trail": 3.0}` |
| weekly_break | CHINA50 | H1 | 0.50% | -31 | -434 | -493 | -69 | 25 | 21% | `{"side": "long", "trail": 2.0}` |
| weekly_break | CHINA50 | H1 | 0.50% | -36 | -509 | -551 | -82 | 25 | 14% | `{"side": "long", "trail": 3.0}` |
| weekly_break | CHINA50 | H4 | 0.25% | -19 | -268 | -393 | -37 | 36 | 21% | `{"side": "both", "trail": 3.0}` |
| weekly_break | CHINA50 | H4 | 0.25% | -20 | -284 | -365 | -37 | 41 | 14% | `{"side": "both", "trail": 2.0}` |
| weekly_break | CHINA50 | H4 | 0.50% | -25 | -349 | -410 | -58 | 18 | 14% | `{"side": "long", "trail": 3.0}` |
| weekly_break | CHINA50 | H4 | 0.50% | -28 | -393 | -456 | -45 | 21 | 14% | `{"side": "long", "trail": 2.0}` |
| weekly_break | HK50 | H1 | 0.25% | -18 | -441 | -484 | -43 | 53 | 20% | `{"side": "long", "trail": 2.0}` |
| weekly_break | HK50 | H1 | 0.25% | -22 | -543 | -565 | -37 | 52 | 20% | `{"side": "long", "trail": 3.0}` |
| weekly_break | HK50 | H1 | none | -29 | -728 | -738 | -45 | 96 | 16% | `{"side": "both", "trail": 2.0}` |
| weekly_break | HK50 | H1 | none | -37 | -931 | -931 | -39 | 94 | 24% | `{"side": "both", "trail": 3.0}` |
| weekly_break | HK50 | H4 | 0.25% | -10 | -239 | -357 | -50 | 41 | 32% | `{"side": "long", "trail": 3.0}` |
| weekly_break | HK50 | H4 | 0.25% | -11 | -263 | -298 | -25 | 47 | 32% | `{"side": "long", "trail": 2.0}` |
| weekly_break | HK50 | H4 | 0.25% | -19 | -472 | -487 | -46 | 82 | 36% | `{"side": "both", "trail": 2.0}` |
| weekly_break | HK50 | H4 | none | -20 | -511 | -694 | -50 | 74 | 28% | `{"side": "both", "trail": 3.0}` |
| weekly_break | JPN225 | H1 | 1.50% | 25 | 615 | -525 | -149 | 5 | 8% | `{"side": "long", "trail": 3.0}` |
| weekly_break | JPN225 | H1 | 1.50% | 25 | 615 | -525 | -149 | 5 | 8% | `{"side": "both", "trail": 3.0}` |
| weekly_break | JPN225 | H1 | 1.50% | -11 | -265 | -570 | -149 | 5 | 4% | `{"side": "both", "trail": 2.0}` |
| weekly_break | JPN225 | H1 | 1.50% | -11 | -265 | -570 | -149 | 5 | 4% | `{"side": "long", "trail": 2.0}` |
| weekly_break | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"side": "both", "trail": 2.0}` |
| weekly_break | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"side": "long", "trail": 2.0}` |
| weekly_break | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"side": "both", "trail": 3.0}` |
| weekly_break | JPN225 | H4 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0% | `{"side": "long", "trail": 3.0}` |
| zscore_mr | AUS200 | H1 | 0.25% | 8 | 169 | -547 | -58 | 253 | 45% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | H1 | 0.50% | 6 | 139 | -506 | -207 | 114 | 55% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | H1 | 0.25% | 2 | 47 | -333 | -99 | 213 | 55% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | H1 | 0.25% | -0 | -3 | -378 | -58 | 142 | 50% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | H1 | 0.25% | -4 | -90 | -382 | -124 | 235 | 50% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | H1 | none | -5 | -108 | -914 | -112 | 618 | 41% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | H1 | none | -7 | -155 | -655 | -112 | 320 | 41% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | H1 | none | -10 | -226 | -628 | -124 | 451 | 32% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | M30 | 0.25% | 22 | 483 | -438 | -135 | 440 | 50% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | M30 | 0.25% | 16 | 351 | -359 | -135 | 243 | 64% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | M30 | 0.25% | -11 | -240 | -521 | -176 | 459 | 45% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | M30 | none | -36 | -782 | -1061 | -131 | 670 | 41% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | M30 | none | -36 | -794 | -1226 | -176 | 880 | 32% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | AUS200 | M30 | none | -40 | -887 | -1273 | -110 | 288 | 32% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | M30 | none | -56 | -1240 | -1653 | -110 | 519 | 32% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | AUS200 | M30 | none | -71 | -1556 | -2006 | -130 | 1240 | 27% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | H1 | 0.50% | 20 | 280 | -415 | -194 | 133 | 64% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | H1 | 0.50% | 5 | 70 | -512 | -194 | 239 | 57% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | H1 | 0.50% | -0 | -2 | -401 | -170 | 116 | 43% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | H1 | 0.75% | -0 | -4 | -462 | -216 | 72 | 36% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | H1 | 0.25% | -6 | -87 | -284 | -51 | 131 | 29% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | H1 | 0.25% | -12 | -167 | -435 | -66 | 256 | 36% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | H1 | 0.25% | -14 | -198 | -394 | -71 | 208 | 36% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | H1 | none | -37 | -518 | -914 | -110 | 404 | 36% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | M30 | none | -61 | -850 | -882 | -126 | 154 | 14% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | M30 | none | -75 | -1049 | -1187 | -126 | 275 | 14% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | M30 | none | -84 | -1178 | -1259 | -126 | 291 | 21% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | M30 | none | -127 | -1778 | -1842 | -106 | 299 | 21% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | M30 | none | -131 | -1832 | -1978 | -126 | 508 | 14% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | M30 | none | -198 | -2774 | -2838 | -106 | 554 | 7% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | CHINA50 | M30 | none | -200 | -2794 | -2807 | -129 | 464 | 0% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | CHINA50 | M30 | none | -313 | -4386 | -4386 | -129 | 862 | 0% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | H1 | 0.50% | -2 | -58 | -523 | -99 | 126 | 48% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | H1 | 0.25% | -6 | -153 | -404 | -70 | 249 | 32% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | H1 | 0.25% | -9 | -235 | -366 | -92 | 173 | 48% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | H1 | 0.50% | -13 | -330 | -544 | -194 | 89 | 36% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | H1 | 0.25% | -14 | -354 | -558 | -117 | 187 | 48% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | H1 | none | -22 | -549 | -703 | -68 | 252 | 36% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | H1 | none | -28 | -710 | -905 | -125 | 367 | 36% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | H1 | none | -38 | -962 | -1068 | -73 | 529 | 36% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | M30 | 0.50% | -10 | -242 | -580 | -188 | 185 | 44% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | M30 | 0.25% | -11 | -267 | -551 | -92 | 383 | 52% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | M30 | none | -28 | -700 | -834 | -119 | 359 | 32% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | M30 | none | -44 | -1109 | -1195 | -109 | 291 | 32% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | M30 | none | -60 | -1501 | -1656 | -121 | 566 | 28% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | M30 | none | -71 | -1784 | -1878 | -113 | 586 | 32% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | HK50 | M30 | none | -75 | -1880 | -2275 | -176 | 746 | 24% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | HK50 | M30 | none | -137 | -3420 | -3658 | -127 | 1148 | 12% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | H1 | 1.50% | 25 | 637 | -593 | -279 | 34 | 28% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | H1 | 1.00% | 22 | 562 | -209 | -167 | 17 | 20% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | H1 | 1.00% | 14 | 354 | -237 | -211 | 12 | 16% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | H1 | 1.00% | 6 | 149 | -148 | -101 | 8 | 8% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | H1 | 1.00% | 3 | 76 | -202 | -167 | 7 | 12% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | H1 | 1.00% | -2 | -46 | -261 | -211 | 5 | 4% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | H1 | 1.00% | -2 | -51 | -121 | -121 | 3 | 0% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | H1 | 1.00% | -4 | -96 | -148 | -100 | 3 | 4% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | M30 | 0.75% | 8 | 199 | -451 | -232 | 50 | 24% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | M30 | 0.75% | 8 | 190 | -209 | -133 | 14 | 24% | `{"max_hold": 8, "n": 50, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | M30 | 0.75% | 6 | 151 | -502 | -146 | 53 | 16% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | M30 | 0.75% | 4 | 104 | -93 | -93 | 4 | 12% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | M30 | 0.75% | 2 | 46 | -264 | -232 | 13 | 12% | `{"max_hold": 8, "n": 50, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | M30 | 0.50% | -1 | -15 | -119 | -91 | 4 | 4% | `{"max_hold": 8, "n": 20, "side": "both", "sl_atr": 1.5, "z_in": 2.0}` |
| zscore_mr | JPN225 | M30 | 0.75% | -5 | -135 | -346 | -103 | 20 | 12% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.5}` |
| zscore_mr | JPN225 | M30 | 0.75% | -6 | -139 | -465 | -230 | 38 | 24% | `{"max_hold": 8, "n": 20, "side": "long", "sl_atr": 1.5, "z_in": 2.0}` |


## Appendix: market study output (study.py, verbatim)

```
C:\Users\veera\Desktop\mt5-trader\.venv\Lib\site-packages\numpy\lib\_function_base_impl.py:3028: RuntimeWarning: Degrees of freedom <= 0 for slice
  c = cov(x, y, rowvar, dtype=dtype)
C:\Users\veera\Desktop\mt5-trader\.venv\Lib\site-packages\numpy\lib\_function_base_impl.py:2901: RuntimeWarning: divide by zero encountered in divide
  c *= np.true_divide(1, fact)
C:\Users\veera\Desktop\mt5-trader\.venv\Lib\site-packages\numpy\lib\_function_base_impl.py:2901: RuntimeWarning: invalid value encountered in multiply
  c *= np.true_divide(1, fact)
================================================================================ 
 JPN225
QUALITY (scored window 2024-10-20..):
   M30 {'bars': 23911, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2019-04-29', 'last': '2026-10-29 22:30'}
   H1 {'bars': 11970, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2019-04-29', 'last': '2026-10-29 22:00'}
   H4 {'bars': 3126, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2019-04-29', 'last': '2026-10-29 20:00'}
   D1 {'bars': 524, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2019-04-29', 'last': '2026-10-29 00:00'}
PERSISTENCE (2022+): {'M30': {'ac1': np.float64(0.013), 'ac2': np.float64(0.012), 'var_ratio_5': 1.028}, 'H1': {'ac1': np.float64(0.0), 'ac2': np.float64(-0.006), 'var_ratio_5': 0.987}, 'H4': {'ac1': np.float64(-0.024), 'ac2': np.float64(0.008), 'var_ratio_5': 0.964}, 'D1': {'ac1': np.float64(-0.066), 'ac2': np.float64(0.02), 'var_ratio_5': 0.901}}
WEEKDAY D1 (bp, 2022+):
     mean_bp      sd    n     t
wd                            
0     28.89  116.22  248  3.91
1     -5.52  126.98  250 -0.69
2     20.91  140.61  248  2.34
3     -1.43  144.65  248 -0.16
4      3.61  154.41  246  0.37
HOUR H1 (bp, 2022+):
       mean_bp  sd_bp  rng_bp     n      vol     t  ac_next
hour                                                      
0        0.89  26.64   24.71   103   249.56  0.34     0.08
1        3.95  26.76   32.11  1159   586.49  5.02    -0.04
2       -0.83  36.60   52.48  1226  2292.56 -0.79     0.01
3       -0.74  48.81   69.12  1226  4690.95 -0.53     0.06
4        0.55  37.10   50.07  1225  3698.35  0.52    -0.04
5        0.08  26.53   38.05  1224  2757.22  0.10    -0.05
6        0.38  25.32   36.42  1223  2582.40  0.53     0.07
7        0.31  26.14   34.71  1224  2583.13  0.41     0.07
8        0.53  30.62   37.86  1224  2636.79  0.60     0.00
9        0.28  27.16   33.95  1224  1815.67  0.36     0.08
10       1.35  32.28   39.45  1226  2407.65  1.47    -0.02
11      -0.60  26.90   36.47  1225  2752.75 -0.78    -0.03
12       0.69  18.89   27.78  1225  2111.46  1.27    -0.02
13       0.20  19.88   25.90  1225  1889.84  0.36     0.06
14       0.26  20.71   27.28  1225  2061.12  0.43     0.01
15       0.34  27.63   35.84  1225  2751.26  0.43    -0.07
16       1.82  33.49   46.15  1225  4273.74  1.91    -0.02
17      -0.00  34.60   49.55  1224  4924.85 -0.00     0.03
18       0.72  28.64   39.52  1224  3900.16  0.88     0.05
19       0.18  23.04   32.56  1224  3162.00  0.28     0.06
20       1.72  32.25   32.81  1195  2976.20  1.85    -0.04
21      -0.23  24.41   31.67  1163  3022.24 -0.32    -0.12
22       0.74  26.01   33.46  1181  2916.56  0.98     0.06
23      -1.27  22.34   24.03  1032  1044.99 -1.83     0.03
SESSION A open=3 close=8: {'n': 1223, 'gap_abs_med_bp': np.float64(64.2), 'fill_rate_all': np.float64(0.387), 'fill_rate_big': np.float64(0.142), 'gap_vs_session_corr': np.float64(-0.005), 'first_hour_vs_rest_corr': np.float64(0.018), 'session_mean_bp': np.float64(1.43), 'session_t': np.float64(0.6)}
SESSION B open=2 close=7: {'n': 1214, 'gap_abs_med_bp': np.float64(60.9), 'fill_rate_all': np.float64(0.417), 'fill_rate_big': np.float64(0.161), 'gap_vs_session_corr': np.float64(-0.03), 'first_hour_vs_rest_corr': np.float64(-0.01), 'session_mean_bp': np.float64(-0.26), 'session_t': np.float64(-0.1)}
================================================================================ 
 HK50
QUALITY (scored window 2024-10-20..):
   M30 {'bars': 16391, 'flat_days': 0, 'long_gaps': 11, 'zero_vol': 0, 'first': '2015-01-02', 'last': '2026-10-30 09:00'}
   H1 {'bars': 8451, 'flat_days': 0, 'long_gaps': 11, 'zero_vol': 0, 'first': '2015-01-02', 'last': '2026-10-30 09:00'}
   H4 {'bars': 2634, 'flat_days': 0, 'long_gaps': 11, 'zero_vol': 0, 'first': '2015-01-02', 'last': '2026-10-30 08:00'}
   D1 {'bars': 500, 'flat_days': 0, 'long_gaps': 11, 'zero_vol': 0, 'first': '2015-01-02', 'last': '2026-10-30 00:00'}
PERSISTENCE (2022+): {'M30': {'ac1': np.float64(0.012), 'ac2': np.float64(0.001), 'var_ratio_5': 1.027}, 'H1': {'ac1': np.float64(0.014), 'ac2': np.float64(0.009), 'var_ratio_5': 1.034}, 'H4': {'ac1': np.float64(0.009), 'ac2': np.float64(-0.014), 'var_ratio_5': 1.009}, 'D1': {'ac1': np.float64(-0.026), 'ac2': np.float64(-0.011), 'var_ratio_5': 0.938}}
WEEKDAY D1 (bp, 2022+):
     mean_bp      sd    n     t
wd                            
0     15.19  142.41  229  1.61
1     -8.22  157.64  240 -0.81
2      3.63  153.09  239  0.37
3     -2.03  148.20  242 -0.21
4     -0.74  150.89  235 -0.08
HOUR H1 (bp, 2022+):
       mean_bp  sd_bp  rng_bp     n      vol     t  ac_next
hour                                                      
2       -2.00  12.81   19.99    50   678.52 -1.10    -0.11
3       -2.16  61.23   92.98   441  7477.35 -0.74     0.01
4        0.68  63.87   95.14  1183  8901.62  0.37     0.04
5       -1.56  50.67   73.90  1183  8618.53 -1.06    -0.02
6        1.68  34.94   47.95   947  5225.13  1.48    -0.00
7       -2.46  33.66   43.47   597  4943.46 -1.78    -0.02
8       -0.28  43.08   62.01  1176  7314.43 -0.22     0.10
9        1.58  35.58   50.61  1175  5977.59  1.53    -0.00
10      -0.41  28.14   40.89  1175  4420.28 -0.50    -0.05
11      -0.75  20.47   30.85  1175  2187.52 -1.25    -0.07
12       1.48  19.53   26.91  1170  1947.00  2.58    -0.05
13       0.68  18.56   25.00  1171  2068.73  1.25    -0.00
14       0.01  19.21   24.89  1170  2188.55  0.01     0.01
15      -0.05  27.92   34.63  1169  2867.14 -0.06    -0.02
16       0.24  41.46   60.99  1169  5517.09  0.20     0.04
17       0.72  36.59   52.78  1169  5907.54  0.67    -0.01
18      -0.57  29.40   38.32  1169  4449.53 -0.67     0.13
19       0.50  21.07   29.30  1119  3336.22  0.79    -0.01
20       0.32  21.16   26.19  1075  2771.44  0.50    -0.03
21       0.25  17.67   24.11   744  2531.45  0.39    -0.01
22       0.00    NaN    0.00     1     1.00   NaN      NaN
SESSION A open=4 close=10: {'n': 1172, 'gap_abs_med_bp': np.float64(59.2), 'fill_rate_all': np.float64(0.509), 'fill_rate_big': np.float64(0.259), 'gap_vs_session_corr': np.float64(0.073), 'first_hour_vs_rest_corr': np.float64(0.067), 'session_mean_bp': np.float64(-0.8), 'session_t': np.float64(-0.24)}
SESSION B open=3 close=9: {'n': 432, 'gap_abs_med_bp': np.float64(59.4), 'fill_rate_all': np.float64(0.581), 'fill_rate_big': np.float64(0.356), 'gap_vs_session_corr': np.float64(-0.103), 'first_hour_vs_rest_corr': np.float64(0.046), 'session_mean_bp': np.float64(-2.98), 'session_t': np.float64(-0.52)}
================================================================================ 
 CHINA50
QUALITY (scored window 2024-10-20..):
   M30 {'bars': 11384, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2025-09-25', 'last': '2026-10-30 09:00'}
   H1 {'bars': 5767, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2025-09-25', 'last': '2026-10-30 09:00'}
   H4 {'bars': 1553, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2025-09-25', 'last': '2026-10-30 08:00'}
   D1 {'bars': 282, 'flat_days': 0, 'long_gaps': 1, 'zero_vol': 0, 'first': '2025-09-25', 'last': '2026-10-30 00:00'}
PERSISTENCE (2022+): {'M30': {'ac1': np.float64(0.022), 'ac2': np.float64(0.001), 'var_ratio_5': 1.023}, 'H1': {'ac1': np.float64(-0.008), 'ac2': np.float64(-0.021), 'var_ratio_5': 0.969}, 'H4': {'ac1': np.float64(-0.023), 'ac2': np.float64(-0.023), 'var_ratio_5': 0.929}, 'D1': {'ac1': np.float64(-0.151), 'ac2': np.float64(-0.178), 'var_ratio_5': 0.629}}
WEEKDAY D1 (bp, 2022+):
     mean_bp      sd   n     t
wd                           
0     25.29   94.29  56  2.01
1     -3.30   93.65  56 -0.26
2      3.30   82.68  57  0.30
3    -15.07  108.98  56 -1.03
4    -34.12  124.78  57 -2.06
HOUR H1 (bp, 2022+):
       mean_bp  sd_bp  rng_bp    n       vol     t  ac_next
hour                                                      
0       -0.00   0.00    0.00   58      1.02 -1.00    -0.15
3       -5.57  45.79   76.30   88  18844.50 -1.14    -0.10
4       -3.16  57.27   82.90  282  17012.41 -0.93     0.02
5       -1.87  38.47   59.34  282  15996.07 -0.82    -0.15
6        0.71  21.31   32.25  282   8537.20  0.56    -0.04
7        1.87  21.79   26.19  282   8326.08  1.44    -0.00
8       -0.88  43.46   59.42  282  16425.57 -0.34     0.07
9       -1.18  31.58   42.20  281  12067.92 -0.63    -0.11
10       0.49   9.82   18.47  281   6127.07  0.83    -0.06
11      -1.79  10.47   16.70  281   3888.85 -2.87    -0.13
12      -0.15   9.21   16.31  281   3313.34 -0.27    -0.18
13      -0.21   8.42   12.65  281   2813.40 -0.42     0.02
14       1.11   9.53   13.58  281   3099.58  1.95     0.30
15       1.09  13.13   16.82  281   3827.94  1.40    -0.12
16       2.18  15.96   23.07  281   7026.77  2.29    -0.11
17       0.73  15.79   22.93  281   7759.36  0.78     0.13
18      -0.93  20.80   19.23  281   6021.58 -0.75     0.49
19      -0.85  10.47   14.32  281   4596.22 -1.36    -0.21
20       0.58  10.27   13.79  281   4018.03  0.95    -0.10
21      -0.41  10.09   11.98  281   3450.67 -0.68    -0.24
22       0.65  10.20   12.58  279   3121.00  1.06    -0.22
23      -1.08   9.12    8.24  279    850.67 -1.97    -0.02
SESSION A open=4 close=10: {'n': 280, 'gap_abs_med_bp': np.float64(29.3), 'fill_rate_all': np.float64(0.611), 'fill_rate_big': np.float64(0.386), 'gap_vs_session_corr': np.float64(0.016), 'first_hour_vs_rest_corr': np.float64(-0.028), 'session_mean_bp': np.float64(-3.68), 'session_t': np.float64(-0.66)}
SESSION B open=3 close=9: {'n': 87, 'gap_abs_med_bp': np.float64(21.7), 'fill_rate_all': np.float64(0.678), 'fill_rate_big': np.float64(0.581), 'gap_vs_session_corr': np.float64(0.131), 'first_hour_vs_rest_corr': np.float64(-0.299), 'session_mean_bp': np.float64(-8.61), 'session_t': np.float64(-1.17)}
================================================================================ 
 AUS200
QUALITY (scored window 2024-10-20..):
   M30 {'bars': 20049, 'flat_days': 0, 'long_gaps': 4, 'zero_vol': 8703, 'first': '2025-01-02', 'last': '2026-10-30 09:00'}
   H1 {'bars': 10461, 'flat_days': 0, 'long_gaps': 4, 'zero_vol': 4518, 'first': '2025-01-02', 'last': '2026-10-30 09:00'}
   H4 {'bars': 2792, 'flat_days': 0, 'long_gaps': 4, 'zero_vol': 1193, 'first': '2025-01-02', 'last': '2026-10-30 08:00'}
   D1 {'bars': 469, 'flat_days': 0, 'long_gaps': 4, 'zero_vol': 200, 'first': '2025-01-02', 'last': '2026-10-30 00:00'}
PERSISTENCE (2022+): {'M30': {'ac1': np.float64(-0.013), 'ac2': np.float64(0.016), 'var_ratio_5': 0.988}, 'H1': {'ac1': np.float64(-0.007), 'ac2': np.float64(-0.018), 'var_ratio_5': 0.956}, 'H4': {'ac1': np.float64(-0.073), 'ac2': np.float64(0.026), 'var_ratio_5': 0.892}, 'D1': {'ac1': np.float64(-0.178), 'ac2': np.float64(0.067), 'var_ratio_5': 0.766}}
WEEKDAY D1 (bp, 2022+):
     mean_bp     sd   n     t
wd                          
0     26.91  79.49  92  3.25
1      8.56  75.00  95  1.11
2      6.69  92.44  95  0.71
3      2.55  88.00  94  0.28
4    -16.73  93.56  93 -1.72
HOUR H1 (bp, 2022+):
       mean_bp  sd_bp  rng_bp    n     vol     t  ac_next
hour                                                    
0        2.55  12.41   15.94  169   42.58  2.67    -0.04
1        1.67  22.51   31.19  256  302.02  1.19     0.05
2        0.23  19.09   27.60  465  320.20  0.26     0.05
3       -2.30  26.53   39.48  465  715.81 -1.87     0.06
4        1.87  23.24   30.90  465  513.88  1.74    -0.04
5       -0.27  14.73   23.02  465  356.39 -0.39     0.08
6        0.10  13.45   19.99  463  301.05  0.17    -0.02
7        0.68  11.61   18.68  463  252.21  1.26    -0.04
8        1.26  11.48   18.51  465  230.89  2.38    -0.04
9        0.51  13.38   18.21  464  195.27  0.82     0.06
10       0.30  16.82   24.08  466  371.78  0.38     0.03
11      -0.46  16.21   22.22  466  450.31 -0.61    -0.03
12       1.12  12.41   17.87  466  348.45  1.96     0.02
13       0.66  15.77   18.99  466  331.53  0.90    -0.02
14       0.06  17.16   20.36  466  366.54  0.08     0.04
15      -0.58  17.45   24.30  466  449.95 -0.71     0.06
16       0.80  20.88   31.98  465  709.37  0.82    -0.03
17       0.65  23.23   33.37  464  774.69  0.60    -0.08
18      -0.94  18.56   27.13  464  610.62 -1.09     0.03
19      -0.19  15.24   21.72  464  461.97 -0.27     0.15
20       1.55  24.20   21.93  464  382.57  1.38    -0.20
21      -0.15  16.04   20.58  464  377.42 -0.20    -0.21
22       1.18  16.44   22.74  452  374.02  1.53    -0.00
23      -0.96  14.16   12.93  288  103.47 -1.15    -0.01
SESSION A open=3 close=8: {'n': 462, 'gap_abs_med_bp': np.float64(36.8), 'fill_rate_all': np.float64(0.396), 'fill_rate_big': np.float64(0.147), 'gap_vs_session_corr': np.float64(-0.226), 'first_hour_vs_rest_corr': np.float64(0.017), 'session_mean_bp': np.float64(0.44), 'session_t': np.float64(0.22)}
SESSION B open=2 close=7: {'n': 462, 'gap_abs_med_bp': np.float64(37.2), 'fill_rate_all': np.float64(0.424), 'fill_rate_big': np.float64(0.16), 'gap_vs_session_corr': np.float64(-0.23), 'first_hour_vs_rest_corr': np.float64(-0.014), 'session_mean_bp': np.float64(-0.23), 'session_t': np.float64(-0.11)}

```
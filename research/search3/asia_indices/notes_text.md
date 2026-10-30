# search3 / asia_indices — JPN225, HK50, CHINA50, AUS200 (round 3, from scratch)

Owner goal: most profit on a FundedNext $10k while never losing $400 in a server day (we design to $300)
and never dropping below $9,200. Judge = `research/prop/harness.py`, window 2024-10-20..2026-10-30
(`PROP_OOS=1`, `split="oos"`), one judge for every run. No statistical gates by design (no IS/OOS split,
no placebo, no skeptic); what stays is the **look-ahead check** and the **300/800 rule**. Every run is on
the harness's fixed-dollar-risk accounting, `best_risk` = highest risk in the ladder with worst day > -3%
and max DD > -6%. A run "passes" if `best_risk` is set and `avg_month > 0`; passing runs are ranked by
`avg_month`.

Scored runs: **{{N_RUNS}}** ({{N_OK}} pass). Distinct ideas: 21 builders in `strategies.py`
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
`results_olddata_20261030.jsonl`, do not use) and **all {{N_RUNS}} runs were re-scored on the new files**
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

{{BY_IDEA}}

## Returned candidates (distinct idea or market; all pass the look-ahead check)

{{CANDIDATES}}

Reading the table: `best_risk` is the per-trade risk the harness picked; `avg/mo` is on the fixed $10k
baseline (not compounding) over the months the symbol has data in the window.

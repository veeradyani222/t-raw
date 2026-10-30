# Round 3 - oil_gas group (XTIUSD, XBRUSD, XNGUSD)

Judge: `research/prop/harness.py`, `PROP_OOS=1`, scoring window 2024-10-20 .. 2026-10-30, every run logged to
`runs.jsonl` by `common.run`. Code: `strategies.py` (24 `build_*` functions), `search.py` + `search2.py` (grids),
`summarize.py` (table + look-ahead re-check of the shortlist). Nothing under trader/, ops/, tests/ or older research/ touched.

## Cost / contract assumptions (monkeypatched in `common.py`)

| symbol | spread floor (price) | ~bp of price | pip for slippage | commission | contract |
|---|---|---|---|---|---|
| XTIUSD | 0.04 | ~6.5 bp at $60 | 0.01 | none (added to `H.INDICES`) | 100 bbl |
| XBRUSD | 0.04 | ~6 bp at $65 | 0.01 | none | 100 bbl |
| XNGUSD | 0.010 | ~30 bp at $3.3 | 0.001 | none | 10,000 MMBtu |

The IC Markets demo files carry median raw spreads far below these floors (XTIUSD 0.002, XBRUSD 0.001, XNGUSD 0.007),
so the harness' max(floor, bar spread) rule makes the floors binding: every oil trade pays ~6 bp, every gas trade ~30 bp,
plus the harness' slippage per fill. This is deliberately harsh and is why thin time-of-day drifts (5-9 bp/hour) did not survive.
Contract sizes from `data/search/symbol_specs.json` (XTIUSD/XBRUSD contract 100, XNGUSD 10,000).

## Data quality (`study_intraday.py`, filter = `common.clean`)

Filter: drop zero-volume bars and all bars of any day whose range < 5% of the median daily range; count gaps > 3.5 days.

| file | bars | zero-vol | flat days | long gaps | span |
|---|---|---|---|---|---|
| XTIUSD M30 | 26,938 | 0 | 0 | 0 | 2024-07-19 .. 2026-10-30 |
| XTIUSD H1 | 14,978 | 0 | 0 | 0 | 2024-04-19 .. 2026-10-30 |
| XTIUSD H4 | 6,135 | 0 | 0 | 0 | 2022-11-11 .. |
| XTIUSD D1 | 2,668 | 0 | 0 | 21 (holiday weekends) | 2016-06-30 .. |
| XBRUSD M30 | 25,413 | 0 | 0 | 0 | 2024-07-15 .. |
| XBRUSD H1 | 14,256 | 0 | 0 | 0 | 2024-04-12 .. |
| XBRUSD H4 | 6,139 | 0 | 0 | 0 | 2022-11-11 .. |
| XBRUSD D1 | 2,623 | 0 | 0 | 21 | 2016-08-25 .. |
| XNGUSD M30 | 26,937 | 0 | 0 | 0 | 2024-07-19 .. |
| XNGUSD H1 | 14,977 | 0 | 0 | 0 | 2024-04-19 .. |
| XNGUSD H4 | 6,135 | 0 | 0 | 0 | 2022-11-11 .. |
| XNGUSD D1 | 2,625 | 0 | 1 (dropped) | 22 | 2016-08-23 .. |

Clean files. The only caveat: the M30/H1 files start mid-2024, so intraday indicators have 3-6 months of warmup before
the 2024-10-20 scoring start (fine for ATR(20)-type features, not for 400-bar lookbacks on M30 in the first weeks).
XBRUSD trades hour 0 (Brent CFD opens 03:00 but a few bars at 00:00-02:00 exist in the data - 99-114 bars, ignored).

## Market study (scoring window, server time = EET)

Hour-of-day (H1, mean log return bp / mean range %), from `out/study_intraday.txt`:

* All three energies: range peaks 16:00-18:00 (NY pit open 16:00, EIA 17:30), second peak 10:00-12:00 (London).
* Drifts: **hours 14-16 negative** on all three (WTI -2.6/-1.3/-2.7 bp, gas -5.8/-5.4 bp); **17-18 positive**;
  **settlement bar 21:00 positive on all three** (+4.9 / +5.4 / +9.0 bp). Too thin against a 6 bp (oil) / 30 bp (gas) spread floor:
  `time_drift` runs confirmed (none positive on oil, see table).
* **EIA report bar anti-correlates with the rest of the day**: Wed 17:00 H1 bar vs 18:00->close corr = -0.23 (WTI), -0.19 (Brent),
  -0.39 (gas, Wednesday petroleum report also moves gas); Thu 17:00 (gas storage report) -0.25 (WTI), -0.17 (Brent), -0.11 (gas).
  Mean |17:00 bar| on report days is 1.5-2.5x a normal hour. This is the "fade the first move after the number" rule
  (Unger Academy strategy #230) and it tested positive here (report_momentum direction=fade).
* Day-open -> hour h move vs h -> close: ~0 for WTI; mildly positive (+0.07..0.14) for Brent and gas late in the day,
  i.e. weak intraday continuation into settlement, not fade.
* **Weekday**: WTI/Brent sum of returns over the window Mon -1,670 bp, Tue +480, Wed +1,070/+1,550, **Thu +4,090/+4,130**, Fri ~0.
  D1 since 2019 agrees: Thursday mean +30 bp WTI / +21 bp Brent, Monday -13/-11 bp. Matches the academic "Thursday effect"
  (positive Thu/Fri, negative Mon in WTI and Brent). Gas is different: **Wed +5,890 bp, Thu (storage day) -3,370 bp**, Mon -2,180.
* D1 persistence (since 2019): return acf1 ~0; 5- and 20-day momentum sign carries +10-15 bp next-day for oil
  (mom5 up +14.6 bp vs down -10.2 bp WTI); 10- and 60-day do not. Gas: tiny.
* Overnight gaps >0.5%: 159 (WTI) / 260 (Brent) / 437 (gas) since 2019; filled same day 53-59%; gap direction and day
  direction agree only 43-53% -> gaps lean to fade, weakly.
* Brent-WTI spread (D1 since 2019): mean $4.6, sd $2.2, acf1 0.98 - very persistent; z>1.5 next-day change +0.03 (wrong sign),
  i.e. no daily reversion edge. Hourly ratio z-scores (the blog rule set below) tested via `spread_reversion`.

## Practitioner / academic sources used

* Wen, Indriawan, Lien, Xu (Energy Journal 2023) - on EIA days the 10:30-11:00 ET half-hour return predicts the last
  half-hour; Quantpedia implementation trades the announcement-window direction into the close. https://www.iaee.org/ej/ejexec/ej44-5-Xu-exsum.pdf ,
  https://vvv.quantpedia.com/?p=37776  -> `build_report_momentum` (follow) and `build_intraday_momentum`.
* Geman & Li, "intraday market response to crude oil inventory shocks", Journal of Energy Markets. https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks
* Unger Academy crude strategies: #230 = one Wednesday trade, counter-order against the first move after the 10:30 ET
  inventory release, flat at session end (https://ungeracademy.com/blog/trading-crude-oil-usd37-000-with-these-2-game-changing-strategies);
  15-min 30/140 MA cross trend follower on crude, prior-session high/low breakout on RB gasoline
  (https://ungeracademy.com/blog/trading-strategies-crude-oil-gasoline) -> `build_report_momentum(direction="fade")`,
  `build_ma_cross`, `build_pdhl_breakout`.
* Day-of-week literature (Soft Computing 2019 WTI/Brent; Cardiff Met "Seasonality in crude oil returns"): negative Monday,
  positive Thursday/Friday. -> `build_weekday_hold`, `build_week_structure`.
* Gao, Han, Li, Zhou "Market intraday momentum" (first half-hour predicts last half-hour) and Wen et al. on USO.
  https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/ -> `build_intraday_momentum`.
* Brent/WTI hourly z-score spread (15-day = 360 h window, +-2.0 entry, exit near 0, one-bar delay):
  https://www.ethanogrodniczuk.com/articles/blog-post-title-two-tjlh3-b2x5b-bpmdg ; Quantpedia "Trading WTI/Brent spread"
  (20-day MA rule, 1995-2004, Sharpe 0.88, max DD -69%) https://quantpedia.com/strategies/trading-wti-brent-spread -> `build_spread_reversion`.
* Gas storage report (Thu 10:30 ET) commentary: surprise-driven $0.30-0.50 spikes several times a year; no published systematic rule set found
  (https://www.fxempire.com/forecasts/article/natural-gas-news-futures-fall-as-eia-weekly-storage-report-tests-bulls-1617822).

## Ideas tested (24 build functions)

1 weekday_hold (Thursday effect / gas Wed-Thu), 2 report_momentum (EIA bar follow / fade), 3 report_breakout (pre-release range),
4 pit_orb (16:00 opening range), 5 session_range_break (Asia+London range, traded in NY), 6 gap (fade / follow first bar),
7 spread_reversion (Brent-WTI ratio z), 8 donchian (incl. Unger 160-bar), 9 trend_pullback (Connors RSI2 in trend),
10 rsi_reversion, 11 nr_breakout (NR7 / inside day), 12 squeeze (Bollinger bandwidth), 13 pdhl_sweep (sweep & reclaim prior day/week level),
14 intraday_momentum (day direction at h into settlement), 15 time_drift, 16 settlement_overnight, 17 london_fade,
18 ema_pullback, 19 tsmom (D1 time-series momentum with vol regime), 20 week_structure, 21 round_number ($1 / $0.10),
22 ma_cross, 23 pdhl_breakout (prior day/week H/L, any day), 24 inside_bar, 25 close_fade (big-bar reversal).

## Look-ahead check

`common.causal_ok`: build on the full df vs. `df.iloc[:k]` (attrs re-attached) for 5 random k; every Entry at index < k must match on
(side, sl, tp, max_hold, exit_hour). `smoke.py` ran it for every build function with defaults on XTIUSD H1 and D1: all passed.
`summarize.py --check` re-ran it with the winning parameters on the shortlisted candidates (results below).

## Scored runs

5,115 scored runs (25 build functions x 3 symbols x M30/H1/H4/D1 grids; `search.py` 2,883 + 305 before a restart with trimmed
grids, `search2.py` 1,932). 3,218 runs had a best_risk, 1,066 are candidates (best_risk set and avg_month > 0).
**The full table of every scored run is `RUNS.md`** (same folder, sorted by avg_month; raw rows in `runs.jsonl`).
One run (`ma_cross fast=15 slow=140 ... XBRUSD M30`) errored because another group's fetch was rewriting
`data/search/symbol_specs.json` at that instant; one `runs.jsonl` line is unparseable because two sweeps appended at once
(logger made unbuffered afterwards).

Per idea (best avg_month in $/month at best_risk, scoring window 2024-10-20 .. 2026-10-30):

| idea | runs | candidates | best $/mo | comment |
|---|---|---|---|---|
| spread_reversion (Brent-WTI z) | 304 | 275 | 100.5 | XTIUSD leg: 286 of 288 runs positive, H1 and H4, every lookback/z/stop. XBRUSD leg (16 runs) all negative |
| donchian | 105 | 40 | 93.7 | 160-bar H4 on WTI (Unger's channel length); only 22 trades |
| report_momentum (EIA fade) | 686 | 152 | 77.7 | fade the 17:30 bar on XTIUSD M30 (68/102 fade runs positive); follow loses everywhere; gas storage day negative |
| inside_bar | 72 | 17 | 50.6 | XTIUSD H4 12/12 positive, Brent/gas no |
| ma_cross | 407 | 84 | 49.0 | D1 10/50 on WTI (8 trades) and 15/140 on gas H1 (122 trades) |
| tsmom (D1, high-vol regime only) | 144 | 39 | 48.7 | 20-day on Brent, 60-day on gas; low-vol regime loses |
| rsi_reversion | 152 | 32 | 44.4 | RSI14 25/75 on gas H4 |
| weekday_hold (Thursday effect) | 276 | 123 | 38.1 | long Wed 10:00 -> Thu close on Brent H1; D1 version 17/mo |
| settlement_overnight | 192 | 7 | 37.4 | thin |
| nr_breakout | 144 | 38 | 37.3 | NR7 day break on Brent H1 |
| trend_pullback (RSI2) | 198 | 43 | 36.9 | gas D1 |
| pdhl_breakout | 576 | 87 | 26.0 | prior-day H/L in NY hours, Brent H1, 309 trades |
| time_drift | 213 | 2 | 25.6 | 21:00 settlement-bar drift does not cover the spread floor |
| ema_pullback | 96 | 40 | 25.3 | |
| intraday_momentum | 168 | 8 | 22.8 | |
| gap | 216 | 45 | 21.7 | fade first-bar gap on WTI M30 |
| squeeze | 36 | 7 | 17.8 | |
| week_structure | 104 | 4 | 17.7 | |
| close_fade | 120 | 17 | 14.9 | |
| pdhl_sweep | 192 | 3 | 11.7 | |
| report_breakout | 192 | 2 | 6.2 | pre-release range break: no |
| london_fade | 48 | 1 | 5.8 | no |
| session_range_break | 216 | 0 | -2.8 | Asia/London range traded in NY: no |
| pit_orb | 210 | 0 | -5.6 | 16:00 opening range: no on all three |
| round_number | 48 | 0 | -17.3 | no |

Dead ends worth recording: every opening-range / session-range breakout (pit_orb, session_range_break, report_breakout) is
negative on all three energies; EIA "follow" (Wen et al.) is negative here while the Unger "fade" is the one that works;
gas storage-day trades (Thu) lose in both directions; pure time-of-day drifts are real in the study but smaller than the cost floor.

## Candidates (distinct ideas, all passed the look-ahead re-check with their winning parameters)

| # | name | symbol | tf | build_fn | params | best_risk | $/mo | net | max DD | worst day | trades | exit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | brent_wti_spread_z | XTIUSD | H4 | build_spread_reversion | other=XBRUSD lookback=100 z_in=2.5 z_out=0.0 sl_atr=2.0 max_hold=120 mode=diff | 0.75% | 100.5 | 2514 | -502 | -192 | 39 | z back to 0 / ATR stop / 120 bars |
| 2 | donchian160_h4 | XTIUSD | H4 | build_donchian | n=160 trail_atr=3.0 sl_atr=2.0 side=both | 0.75% | 93.7 | 2342 | -577 | -172 | 22 | 3xATR trail, flip on opposite break |
| 3 | eia_fade_m30 | XTIUSD | M30 | build_report_momentum | report_wd=2 exit_hour=21 sl_atr=1.0 min_move_atr=0.3 tp_r=None direction=fade | 0.75% | 77.7 | 1944 | -549 | -125 | 77 | flat at the 21:xx settlement bar / 1xATR stop |
| 4 | inside_bar_h4 | XTIUSD | H4 | build_inside_bar | sl_mode=atr sl_atr=1.5 tp_r=2.5 max_hold=10 | 0.50% | 50.6 | 1266 | -412 | -134 | 122 | 2.5R target / ATR stop / 10 bars |
| 5 | tsmom20_highvol | XBRUSD | D1 | build_tsmom | mom_n=20 vol_filter=high hold=5 sl_atr=2.0 side=both | 1.50% | 48.7 | 1218 | -564 | -226 | 57 | 5-day time stop / 2xATR stop |
| 6 | gas_rsi14_h4 | XNGUSD | H4 | build_rsi_reversion | rsi_n=14 lo=25 hi=75 sl_atr=2.5 max_hold=12 side=both | 1.50% | 44.4 | 1111 | -486 | -243 | 35 | RSI back through 50 / 12 bars / stop |
| 7 | gas_ma15_140_h1 | XNGUSD | H1 | build_ma_cross | fast=15 slow=140 sl_atr=3.0 tp_r=3.0 trail_atr=3.0 | 0.75% | 37.7 | 943 | -468 | -267 | 122 | 3R target / 3xATR trail |
| 8 | thursday_effect_h1 | XBRUSD | H1 | build_weekday_hold | enter_wd=2 enter_hour=10 hold_bars=46 side=long sl_atr=3.0 | 0.50% | 38.1 | 952 | -593 | -139 | 104 | time exit after 46 bars (Thu close) / 3xATR stop |

Honest read: every number above is at the harness' harsh cost floors; the max-DD side (not the daily limit) is what caps
best_risk at 0.5-0.75% for the oil ideas. The spread-z idea is the only family that is positive almost regardless of parameters;
donchian160 and the D1 trend ideas rest on 8-25 trades and should be read as "trend worked on WTI in this window", not as proven.

# commodity_fx (round 3) - NOTES

Group: AUDUSD NZDUSD USDCAD EURAUD GBPAUD AUDNZD EURNZD GBPNZD EURCAD GBPCAD AUDCHF CADCHF NZDCAD NZDCHF on H1/H4/D1.
Judge: `research/prop/harness.py`, split="oos" (scoring from 2024-10-20, warmup kept), no statistical gates.
Files: `strategies.py` (20 builders), `run.py` (sweep + harness patches), `check_causal.py` (look-ahead check), `table.py`, `results.jsonl` (every scored run), `_table.md` (same, as a markdown table).

## Harness patches (in run.py, applied on import)
- `H._attach_conv` replaced: the stock one has no AUD/NZD profit-currency map, so EURAUD/GBPAUD (AUD P&L) and AUDNZD/EURNZD/GBPNZD (NZD P&L) raised KeyError. Added AUD -> AUDUSD and NZD -> NZDUSD (not inverted); CHF/CAD via USDCHF/USDCAD inverted as before.
- `H.SPREAD_FLOOR` additions (price units): EURAUD 0.00025, GBPAUD 0.00035, AUDNZD 0.00025, EURNZD 0.00040, GBPNZD 0.00050, EURCAD 0.00025, GBPCAD 0.00035, AUDCHF 0.00025, CADCHF 0.00025, NZDCAD 0.00030, NZDCHF 0.00030. The harness uses max(floor, the bar's own recorded spread) and the recorded spreads are usually above the floor (medians 17-41 points, p90 39-81), so costs are conservative.
- `H._spec` wrapped to add contract specs for GBPCAD/AUDCHF/CADCHF/NZDCAD/NZDCHF (100k contract, point 1e-5, profit ccy CAD/CHF), which are missing from `data/search/symbol_specs.json`.
- Commission stays $14/lot round trip (forex). No index/crypto symbols in this group.

## Data quality (H1 files, 2024-10-20 onward)
| symbol | bars | days | flat days (range < 5% of median) | zero-volume bars | gaps > 6h (all weekends; max 50h) |
|---|---|---|---|---|---|
| AUDUSD | 12382 | 520 | 1 (2025-01-01) | 0 | 109 |
| NZDUSD | 12381 | 519 | 1 (2024-12-25) | 0 | 109 |
| USDCAD | 12381 | 519 | 0 | 0 | 109 |
| EURAUD | 12572 | 526 | 1 (2025-01-01) | 0 | 110 |
| GBPAUD | 12571 | 525 | 0 | 0 | 110 |
| AUDNZD | 12571 | 525 | 0 | 0 | 110 |
| EURNZD | 12572 | 526 | 1 (2025-01-01) | 0 | 110 |
| GBPNZD | 12507 | 525 | 1 (2025-01-01) | 0 | 112 |
| EURCAD | 12572 | 526 | 0 | 0 | 110 |
| GBPCAD, AUDCHF, CADCHF, NZDCAD, NZDCHF | MISSING | | | | |

Flat days are holiday sessions (Christmas / New Year); `run.load()` drops every bar of a flat day and every zero-volume bar before building and scoring (0 zero-volume bars found). No long gaps beyond weekends. AUDUSD/NZDUSD/USDCAD files end 2026-10-20; crosses end 2026-10-29.
The five missing crosses were polled every 2 minutes for 20 minutes (see "Missing symbols" at the end).

## Market study (H1, 2022-01 .. 2026-10, log returns in bp)
Full numbers in `_study_log.txt`.
- **Mean reversion dominates at every horizon.** Variance ratios are below 1 for every pair: VR(24h) 0.86-0.95, VR(5d) 0.84-0.97, VR(20d) 0.79-1.00. Hourly lag-1 autocorrelation is negative everywhere (AUDNZD -0.053, EURCAD -0.036 the strongest); daily lag-1 autocorrelation negative on all crosses (EURNZD -0.062, GBPNZD -0.061, EURCAD -0.050, EURAUD -0.045). AUDUSD VR(20d) 0.79 is the most mean-reverting at the monthly scale. NZDUSD is the only pair near a random walk at 20 days.
- **Sessions.** London (10-17 server) has the widest hourly ranges on every pair; the 15:00-17:00 bars (US data / London-NY overlap) are the most volatile (AUDUSD 23 bp std at 15:00 vs 10 bp overnight). The Sydney/Tokyo window (01-09) is the quiet range on the AUD/NZD majors (17-18 bp mean bar range vs 22 in London) and dead on USDCAD and EURCAD (8 bp). AUDNZD is the exception: its Asia session is as active as London (10.4 vs 10.2 bp), i.e. AUDNZD moves on antipodean data (RBA/RBNZ, 03:30-05:00 server) and sleeps in NY (19-22: 4.3-4.7 bp).
- **Rollover artefact (not tradable).** The 23:00 bar has a mean return of -1.3 to -2.2 bp on every pair and the 01:00 bar +1.0 to +3.4 bp. That is the bid quote dipping when spreads widen at the 00:00 swap and recovering after; a strategy that "buys at 23:00 and sells at 01:00" would be an artefact. No builder here enters at 23:00; session exits are at 22-23 and the 01:00 entries pay that bar's recorded spread (p90 of the spread column is 2-4x the median).
- **Weekday.** AUD/NZD vs USD: Monday positive, Friday negative (AUDUSD sum of Monday returns +1345 bp, Friday -1763 bp over 4.8 years; NZDUSD Friday -1406; AUDNZD Monday +1530, Friday -801). USDCAD and EURAUD lean the other way (USDCAD Friday +629, EURAUD Friday +865): "risk-off into the weekend". Tested as `weekday`.
- **Weekend gaps** are small (mean |gap| 8-18 bp) and fill the same day 87-97% of the time (AUDNZD 97%). Tested as `monday_gap`; the catch is that the gap is often smaller than the Monday 00:00 spread.
- **Prior-day levels.** PDH or PDL is broken on roughly half the days; after a break the day closes beyond the level only 41-50% of the time (AUDNZD 41-43%, the most false breaks; AUDUSD/USDCAD 49-50%). Both broken on 11-15% of days. Prior-day breaks are coin flips on majors and lean to failure on AUDNZD, which motivated `pd_sweep` (fade) more than `pd_break` (follow).
- **Commodity links (daily, 2022-).** AUDUSD-XAUUSD correlation 0.46, NZDUSD-XAUUSD 0.43, USDCAD-XAUUSD -0.36, AUDUSD-US500 0.53, AUDUSD-NZDUSD 0.89, USDCAD-AUDUSD -0.75. Lead-lag is nil: XAUUSD(t-1) -> AUDUSD(t) +0.03, US500(t-1) -> AUDUSD(t) +0.08. Gold does not lead AUD day to day; the only tradable angle is a stretched residual (AUD lagging a gold run), tested as `gold_div`. No oil series (XTIUSD) exists in data/search, so the CAD-oil idea could not be tested; USDCAD went into the gold-divergence sweep instead.
- **AUDNZD** structure: lowest volatility of the group (hourly std 4-9 bp), active in Asia, strongest hourly mean reversion. Practitioner material (Pepperstone/DailyFX/BabyPips range notes; RBA-RBNZ differential pieces) treats it as a range pair driven by the policy-rate gap; in the scoring window it trended (13-year high in 2026 per FXStreet, May 2026), which is exactly where range rules get hurt and D1 trend rules do well.

## Practitioner sources used (web search 2026-10-30)
- Asia-range / London breakout: MQL5 blog "London Breakout on Gold: 3.7 years of backtests" and "Why the same strategy wins in London and dies in Tokyo" (session hour drifts with DST), BabyPips "London Breakout Strategy 1H modified" thread (close outside the range of the last Asia candles; skip when the move before London was large), Akatsuki/ORB listings (first London candle close confirmation, ADX and ATR range-size filters). Implemented as `asia_break` (range-size filter in ATR, first close outside, flat at 18/23) and `asia_fade`.
- AUDNZD range: Pepperstone "AUDNZD range trade opportunity", DailyFX "AUDNZD reaches daily range support" (RSI turning up at support, stop 25% of the range, target 75%), BabyPips TA alert (daily close below the lower Bollinger band, mid band as target, wait for the close back inside), FXStreet range analysis (RSI 40-60 = non-directional). Implemented as `bb_reentry` (close back inside the band + RSI + optional ADX ceiling, target mid band) and `zmean`.
- Prior-day high/low sweeps: Backtrex "Liquidity sweep strategy 5-year backtest" (wick beyond the level, close back inside, stop beyond the wick, minimum penetration filter, session filter), TradingView "Sweep & Reverse" / "Liquidity Sweep Stop-Hunt" scripts, MQL5 "Reversal liquidity grab". Implemented as `pd_sweep` and `week_fade`.
- Trend pullback: TradingView Mustang Algo "EMA 20/50 pullback with RSI gate + 200 EMA bias" (touch the 20 EMA, close back, exit on the opposite cross or a close beyond the 50), "Trend Pullback EMA Combo" (zone between the 50 and 200). Implemented as `trend_pullback`.
- Connors RSI(2): Backtrex "Does the RSI(2) strategy work on forex" (EURUSD D1 loses, PF 0.78; suggests tighter thresholds / fixed hold), ProRealCode "RSI 2P" thread. Implemented as `rsi2` (SMA200 filter, SMA5 exit, ATR stop, fixed max hold) and tested with the tighter thresholds they suggest.
- Gold / AUD correlation: FXStreet "Correlation of forex with gold and oil", DailyFX "Trade gold using currency correlations" (gold rallies and AUD fails to follow = the signal). Implemented as `gold_div` (rolling-beta residual z-score, follow or fade).
- Donchian/turtle, inside-day/NR7, squeeze, weekday seasonality, Monday gap, London-open reversal, round numbers, prior-day-close magnet: standard practitioner playbooks, parameterised from the market study above.

## Ideas tested (20 builders)
| # | builder | idea | tfs |
|---|---|---|---|
| 1 | asia_break | Sydney/Tokyo range (01-09) breakout from the London open, range-size filter, flat by day end | H1 |
| 2 | asia_fade | false break of the Asia range during London, target the range midpoint | H1 |
| 3 | pd_sweep | prior-day high/low sweep + close back inside -> reverse to the prior close | H1 |
| 4 | pd_break | first close beyond the prior-day high/low -> continuation | H1 |
| 5 | d1_meanrev | fade an outsized daily return (z-score), optional 3-day streak | D1, H4 |
| 6 | trend_pullback | EMA 20/50/200 stack, pullback to the fast EMA, R-target or chandelier trail | D1, H4 |
| 7 | bb_reentry | Bollinger close back inside the band + RSI (+ADX ceiling), target the mid band | H1, H4 |
| 8 | weekday | long AUD/NZD Mondays, short Fridays (session hold with ATR stop) | H1 |
| 9 | monday_gap | fade the weekend gap to the Friday close | H1 |
| 10 | gold_div | AUD/NZD/CAD vs XAUUSD rolling-beta residual z-score, follow or fade | H1, D1 |
| 11 | london_rev | fade an over-extended London open (09->11 move > x ATR) | H1 |
| 12 | squeeze | Bollinger-width squeeze then 20-bar breakout, chandelier trail | H4, D1 |
| 13 | round_bounce | rejection wick through a 25/50/100-pip round level | H1 |
| 14 | week_fade | prior-week high/low touch + close back inside in low ADX | H1, H4 |
| 15 | donchian | turtle 20/10 and 55/20 with ATR stop | D1, H4 |
| 16 | rsi2 | Connors RSI(2) with SMA200 filter and SMA5 exit | D1, H4 |
| 17 | inside_break | inside-day / NR7 breakout, stop at the other side | D1 |
| 18 | zmean | z-score to the rolling mean, exit at the mean | H1, H4, D1 |
| 19 | asia_drift | trade the Asia session in (or against) the direction of its recent average | H1 |
| 20 | pdc_magnet | far from the prior-day close in the London morning, bar turns -> trade to the close | H1 |

## Scored runs
829 runs, 0 errors (34 USDCAD/NZDUSD H1 runs first died with an out-of-memory parser error while another group was running; re-run after, all scored). 171 of 829 runs are candidates (best_risk not None and avg_month > 0). Every run (idea, params, symbol, tf, best_risk, avg/mo, net, maxDD, worst day, trades, green months) is in `_table.md` and `results.jsonl`.
Runs per tf: H1 360, H4 207, D1 228 (9 symbols x 20 ideas x 1-4 parameter sets x 1-3 tfs). Rank: `python -m research.search3.commodity_fx.table 40 --md`.

Best run per idea (avg $/month at best_risk on the $10k account):
| idea | best run | symbol | tf | best_risk | avg/mo | net | maxDD | worst day | trades |
|---|---|---|---|---|---|---|---|---|---|
| bb_reentry | tp_mode=r sl_atr=0.8 | EURNZD | H4 | 1.50% | 69 | 1,717 | -510 | -235 | 56 |
| zmean | n=100 adx_max=25 | NZDUSD | H4 | 1.25% | 66 | 1,659 | -498 | -244 | 23 |
| squeeze | pct_n=60 tp_r=2 no trail max_hold=20 | USDCAD | D1 | 2.00% | 58 | 1,444 | -339 | -197 | 7 |
| trend_pullback | trail_atr=3 max_hold=40 no tp | AUDNZD | D1 | 2.00% | 52 | 1,300 | -294 | -147 | 11 |
| d1_meanrev | z_thr=1 streak=3 tp_r=1.5 max_hold=5 | GBPAUD | D1 | 1.50% | 48 | 1,200 | -459 | -192 | 42 |
| donchian | 20/10 defaults | USDCAD | D1 | 1.50% | 40 | 990 | -539 | -152 | 15 |
| gold_div | defaults (follow, n=5, z_n=60) | NZDUSD | D1 | 1.25% | 39 | 971 | -522 | -181 | 71 |
| rsi2 | rsi_thr=5 | AUDUSD | D1 | 2.00% | 23 | 564 | -199 | -140 | 14 |
| asia_break | tp_r=1.5 last_hour=12 exit 18 | USDCAD | H1 | 2.00% | 18 | 440 | -306 | -200 | 9 |
| week_fade | defaults | EURCAD | H4 | 0.50% | 17 | 418 | -517 | -100 | 93 |
| inside_break | trend_n=50 tp_r=2 | GBPAUD | D1 | 1.50% | 16 | 407 | -588 | -169 | 31 |
| weekday | long Mondays only, no tp | AUDUSD | H1 | 0.50% | 13 | 317 | -542 | -50 | 105 |
| pdc_magnet | dist 0.8 ATR | GBPNZD | H1 | 0.25% | 2 | 57 | -325 | -53 | 119 |
| round_bounce | step 0.01 tp_r=2 | USDCAD | H1 | 0.50% | 1 | 30 | -508 | -99 | 70 |
| asia_fade, asia_drift, pd_sweep, pd_break, monday_gap, london_rev | no candidate on any symbol | | | | | | | | |

What the table says about the group: the H1 session/level ideas (Asia breakout, Asia fade, prior-day sweeps and breaks, London reversal, Monday gap, round numbers, prior-close magnet) all lose after spread on these pairs; their edges are a few pips and the crosses cost 2-5 pips. What survives is slower: H4/D1 mean reversion (BB re-entry, z-score to mean, 3-day streak fades, RSI(2)), D1 trend following with a pullback or squeeze entry on USDCAD/AUDNZD, and the gold-residual idea on NZDUSD/AUDUSD D1. Several of the D1 winners have 7-15 trades in 25 months, so their avg/month rests on a handful of trades.

## Look-ahead check
`check_causal.py` (build(df) vs build(df.iloc[:k]) with df.attrs re-attached, 5 random k in [n/3, n-5], every Entry at index < k compared on side/sl/tp/max_hold/exit_hour). Run on the 12 best distinct (idea, symbol) runs with their exact params: all 12 identical at every k (causal_ok=True). The smoke run over all 20 builders with defaults on AUDNZD H1 also passed.

## Candidates returned (distinct idea or market)
1. bb_reentry EURNZD H4 (tp_mode=r, sl_atr=0.8) - 1.50% - $69/mo
2. zmean NZDUSD H4 (n=100, adx_max=25) - 1.25% - $66/mo
3. squeeze USDCAD D1 (pct_n=60, tp_r=2, trail None, max_hold=20) - 2.00% - $58/mo (7 trades)
4. trend_pullback AUDNZD D1 (trail_atr=3, max_hold=40, no tp) - 2.00% - $52/mo (11 trades)
5. d1_meanrev GBPAUD D1 (z_thr=1, need_streak=3, tp_r=1.5, max_hold=5) - 1.50% - $48/mo
6. trend_pullback USDCAD H4 (fast=10, slow=30, bias=100, tp_r=2, max_hold=30) - 0.75% - $46/mo (96 trades)
7. donchian USDCAD D1 (20/10 defaults) - 1.50% - $40/mo
8. gold_div NZDUSD D1 (defaults) - 1.25% - $39/mo

## Missing symbols
GBPCAD, AUDCHF, CADCHF, NZDCAD, NZDCHF: no `data/search/<sym>-<tf>.csv` existed at the start, after 20 minutes of 2-minute polling, or at the final check (2026-10-30, end of this run). All jobs for them were skipped (`avail()` in run.py); their spread floors and contract specs are already in run.py, so `python -m research.search3.commodity_fx.run` will pick them up unchanged once the files land.

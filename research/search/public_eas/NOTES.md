# public_eas: open-source EA rule sets judged by the prop harness

In-sample only (2015-01 .. 2023-12, `split="is"`). PROP_OOS was never set. Every number
below comes from `research/prop/harness.py` `H.score` (risk ladder 0.25..2%, best = highest
SAFE risk: worst day > -$300 and max DD > -$600 on $10k). 364 scored runs, all in
`results.jsonl`; the full table is at the bottom.

## Bottom line (plain words)

- Almost every public EA loses money at its own defaults, which matches what the authors
  themselves say on their pages. None of them is a money machine.
- Three things survived the neighbour/cost checks, and they are small earners:
  1. **Bollinger Bands Breakout (EarnForex) on gold H1** with a slow trend filter:
     about **$41/month** at 0.5% risk, positive in all 9 years, every neighbouring setting
     positive, still $30/month at 2x spread. It works ONLY on gold (fails on 15 other symbols).
  2. **Connors RSI(2) on daily bars**: positive on 16 of 22 symbols. Best on GBPUSD ($18/month at 2% risk)
     and US500 ($14). It is real but slow (about 6 trades a year), so it makes little money.
  3. **myPickyBreakout / Weekly Breakout on GBPJPY**: about $12/month, positive in 7-8 of 9 years,
     but only on some JPY crosses (fails on CHFJPY/CADJPY), so treat it as weak.
- With these numbers a phase-1 challenge (+$800) takes years, not weeks. The harness's
  "challenge pass rate 100%" only means that no attempt breached before it passed. The
  median time to pass was 730+ days.

## What was re-implemented (12 EAs and published rule sets)

All of them were re-implemented in Python from source read as text. Nothing downloaded was installed or run.
Distances in pips or points were converted to ATR multiples so the rules work on any symbol.
"ADDED STOP" means the original had no stop loss.

| # | EA / rule set | Source (URL + version/commit) | Key rules kept | Changes |
|---|---|---|---|---|
| 1 | MACD Sample (MetaQuotes) | `MQL5/Experts/Examples/MACD/MACD Sample.mq5` shipped in the local MT5 terminal, `#property version "5.50"`, (c) 2000-2026 MetaQuotes. | MACD(12,26,9) signal cross below/above zero, \|MACD\|>3 pips, EMA26 slope, TP 50 pips, trail 30 pips, close on reverse cross >2 pips | pips -> ATR (open 0.12, close 0.08, TP 2.0, trail 1.2); ADDED STOP 2 ATR; signals on closed bars (source reads bar 0) |
| 2 | Moving Average (MetaQuotes) | `MQL5/Experts/Examples/Moving Average/Moving Average.mq5` (local MT5 install) | candle open/close crosses SMA12 shifted 6, close and reverse on opposite cross | ADDED STOP 2 ATR; no lot reduction after losses (risk is fixed) |
| 3 | "Free Robots" pattern + oscillator family (MetaQuotes, 7 patterns x RSI/CCI/MFI/Stoch, 28 EAs) | `MQL5/Experts/Free Robots/*.mq5` (local MT5 install, e.g. `BullishBearish Engulfing RSI.mq5`) | exact pattern formulas (AvgBody12, SMA5 trend), confirmations RSI37<40/>60, CCI37 +-50, MFI37 40/60, Stoch(47,9,13) signal 30/70, exit on oscillator cross-backs, 10-bar hold, SL=TP=200 points | 200 points -> 1.5 ATR; **source bug**: Piercing Line has a stray `return(true);`, so it never buys. We implemented the intended rule |
| 4 | Spike Trader (EarnForex) | https://github.com/EarnForex/Spike-Trader `SpikeTrader.mq5` @ abc322e8da3c7fc9c701d056f01a70ebe4e20cd5 | fade a bar whose high (low) beats 3 prior bars by >=0.3% and closes in the lower (upper) half; hold 11 bars, re-armed by repeat signals | ADDED STOP: spike extreme +1 ATR |
| 5 | Ichimoku Chikou Cross 1.01 (EarnForex) | https://www.earnforex.com/mt5-expert-advisors/Ichimoku-Chikou-Cross.mq5 (v1.01, fetched 2026-10-20) | chikou/price cross (close[t] vs close[t-26]) armed until kumo confirmations; opposite cross closes | ADDED STOP 2x ATR(20) (the EA uses ATR20 only for sizing); buffer shifts taken literally from the CopyBuffer calls |
| 6 | Weekly Breakout (EarnForex) | https://www.earnforex.com/mt5-expert-advisors/WeeklyBreakout.mq5 (fetched 2026-10-20; no version string) | break of previous week's high/low, stop = other side of last week, out at week end | stop orders replaced by "first H1 close beyond the level" (later, worse fill); exit Friday >= 20:00 broker time instead of the Monday open |
| 7 | Bollinger Bands Breakout 1.00 (EarnForex) | https://www.earnforex.com/mt4-expert-advisors/EA-BollingerBreakout_v1-0.mq4 (`#property version "1.00"`) | close crosses BB(200, 2) -> trade, fixed SL 20 / TP 50 pips, no other exit | pips -> 1.5 / 3.75 ATR (same 1:2.5); closed bars (source reads bar 0) |
| 8 | myPickyBreakout (EarnForex, 2009) | https://www.earnforex.com/mt4-expert-advisors/myPickyBreakout.mq4 | last high above 8 prior highs (or low below 8 lows), trade only Tue-Thu, exit after 5 bars or on reverse | MinDiff 3 points -> 0; ADDED STOP 2 ATR |
| 9 | PersistentAnti 1.01 (EarnForex) | https://www.earnforex.com/mt5-expert-advisors/PersistentAnti.mq5 (v1.01) | persistence vs anti-persistence count over 10 candle pairs, ratio 0.66, Reverse=true, one-bar holds | W1 bars built from D1 (closed weeks only); ADDED STOP 2 ATR |
| 10 | Bill Williams Alligator (EarnForex) | https://www.earnforex.com/metatrader-expert-advisors/bill-williams-alligator/ (`EA-Alligator_v1-0.mq4`, page rules) | jaw/teeth/lips 13/8/5 with shifts 8/5/3, all rising and ordered -> buy (mirror), exit on opposite entry | SMMA of median price (standard Alligator); ADDED STOP 2 ATR |
| 11 | Original Turtle Trading Rules (Curtis Faith, 2003, public PDF) | "The Original Turtle Trading Rules" PDF (Curtis Faith, 2003); rules from the text, not re-fetched this session | System 1 20/10 and System 2 55/20 Donchian, 2N stop | close-based breakout; one unit, no pyramiding; System-1 "skip after winner" filter not used |
| 12 | Connors RSI(2) (Connors & Alvarez, *Short Term Trading Strategies That Work*, 2009) | published rule set | close > SMA200 and RSI(2) < 5 -> long, exit close > SMA5 (mirror short > 95) | ADDED STOP 2 ATR (Connors trades it with no stop) |
| + | `build_filtered` wrapper (our "fix") | - | any EA plus an optional SMA trend filter, one side only, or hour window | - |

The earlier repo work (docs/2026-09-17-public-ea-*.md) covered Adjustable MA, RSI EA and
Heiken Ashi Naive on EURUSD at fixed lots. Those were not redone.

## What failed and why

- **Fast always-in-the-market crossovers** (Moving Average EA, Alligator, MACD Sample on H1)
  lose money on every symbol. Over 4,000 trades a decade at H1, costs and whipsaw dominate.
  For example, Moving Average EURUSD H1 lost -$10.7k at 0.25% risk.
- **The Free Robots candlestick family** is nearly dead on gold H1, H4 and D1 across all 28 pattern x
  oscillator pairs. The best was hammer+RSI at $3/month. Meeting-lines never fires (0 trades), and many pairs fire fewer than 10 times.
  The pattern definitions are too strict and they have no edge.
- **Spike Trader, Ichimoku Chikou, PersistentAnti and MACD Sample on H4/D1** come out about flat (-$5..+$9/month)
  and change sign from one symbol to the next. That is noise.
- **Bollinger Breakout outside gold**: negative on XAGUSD, all 7 JPY pairs, EURUSD, GBPUSD,
  AUDUSD and US30. DE40 is positive only with the trend filter. Most of the edge is gold-specific.
  A large part of that edge is gold's 2015-2023 uptrend: longs earned +47R and shorts +17R
  (dev 2.5). Shorts were still positive, so it is not purely drift.
- **Side-picking looks great and is overfit.** Weekly Breakout AUDJPY short-only made $29/month, but
  AUDJPY long-only lost money. That is hindsight about the pair's trend, so it is NOT a candidate.
- **Connors on H4/H1**: H1 loses money on every pair tested. H4 GBPUSD with trend_n=1200 made $12/month, but
  trend_n 600 / 2400 / buy-level 10 collapse to about $0. It is fragile, so it is not a candidate.
- **M30 and H4 versions of the gold BB breakout** are negative or weak. H1 is the only timeframe that works,
  which is a warning sign. Neighbouring periods and deviations on H1 are all positive, though.
- **Why the money is small**: the limit is drawdown, not edge. For example, BB-gold makes about 7R a year,
  but its worst losing run is about 11R. That caps risk at 0.5%, because 0.75% breaks the $600 DD line.
  More profit needs a lower-DD version or several uncorrelated strategies run side by side, and the
  harness scores only one strategy at a time.

## Robustness of the shortlisted candidates

Neighbourhood (avg_month at best risk, $; r.25 = net at 0.25% risk, which is comparable across rows):
- BB+trend gold H1: dev 2.0/2.25/2.5/2.75 = 9/41/30/9; trend_n 500/750/1000/1500/2000 (dev2.5 or 2.25) = 31/18/41/13/9;
  period 150/250 = 8/16; SL/TP variants 12..19; 2x spread = 30. All positive.
- BB plain gold H1: period 150/200/250 x dev 2.25..3.0 are all positive (r.25 $124..$1,777). Dev 2.5 is best. 2x spread gives $19.
- Connors D1: positive on 16/22 symbols at defaults. On GBPUSD: exit_n 3/5/10 = 13/18/14, sl 3 = 12,
  trend 100 = 10, levels 10/90 = 9, levels 3/97 = 8, 2x spread = 17. On US500: 14 at defaults, 9-13 for most neighbours.
- Picky GBPJPY D1: lookup 5/8/12 = 4/12/10, hold 3/5/8 = 11/12/17, sl 3 = 9; AUDJPY 12, NZDJPY 13;
  CHFJPY/CADJPY/EURJPY negative or zero.
- Weekly breakout GBPJPY H1: 12 at defaults, fri_hour16 = 14, trend filter = 3, ATR stop = 7 (not safe); AUDJPY 14,
  NZDJPY 7, EURJPY 2, CHFJPY -1, CADJPY -3.

Per year at best risk (net $):
- BB+trend gold: 2015 17, 2016 906, 2017 273, 2018 385, 2019 571, 2020 1454, 2021 187, 2022 509, 2023 93
- Connors GBPUSD: 2016 918, 2017 259, 2018 -255, 2019 230, 2020 135, 2021 26, 2022 327, 2023 296
- Picky GBPJPY: -23, 439, 97, 207, 98, 283, 273, -133, 6

## Lessons

1. Published EAs are teaching code. Their authors say they lose money, and the harness agrees.
2. The things that survived are slow breakouts on trending markets (gold, the JPY crosses) and
   daily mean reversion with a trend filter (Connors). The fast H1 crossover systems did not.
3. A slow trend filter (about 40 trading days of H1 bars) is a cheap and robust "fix". It lifted BB-gold
   from $28 to $41 a month with fewer trades. One-sided filters chosen by hindsight are not a fix.
4. Gold results lean on the 2015-2023 uptrend. Run the out-of-sample test before trusting them.

## Files

- `strategies.py`: all builders (`build_<name>`, plus `BUILDERS`)
- `run.py`: parallel runner and `results.jsonl` writer; `batches/b1..b5.py` hold the exact job lists
- `summarize.py`: table printer; `final_check.py`: per-year and 2x-spread checks
- `test_causal.py`: truncation test. Signals and manage() decisions are unchanged when future rows are removed (15 cases pass)

## Every scored run (in-sample)

| # | batch | run (EA_tf_params) | symbol | tf | best_risk | avg_month $ | net $ | max_dd $ | worst_day $ | trades | net @0.25% $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | b1 | macd_sample (defaults) | XAUUSD | H4 | 0.50% | -0.4 | -46 | -448 | -56 | 164 | -111 |
| 2 | b1 | macd_sample (defaults) | EURUSD | H4 | 0.25% | -0.6 | -67 | -369 | -30 | 160 | -67 |
| 3 | b1 | macd_sample (defaults) | USDJPY | H4 | 0.50% | 4.1 | 447 | -401 | -60 | 148 | 172 |
| 4 | b1 | macd_sample (defaults) | GBPUSD | H4 | 0.25% | -1.2 | -128 | -377 | -30 | 180 | -128 |
| 5 | b1 | macd_sample (defaults) | XAUUSD | H1 | none | -4.9 | -528 | -743 | -56 | 627 | -528 |
| 6 | b1 | macd_sample (defaults) | USDJPY | H1 | none | -17.2 | -1876 | -1944 | -55 | 656 | -1877 |
| 7 | b1 | macd_sample (defaults) | EURUSD | H1 | none | -18.9 | -2057 | -2090 | -51 | 663 | -2057 |
| 8 | b1 | macd_sample (defaults) | GBPUSD | H1 | none | -6.8 | -738 | -986 | -54 | 605 | -738 |
| 9 | b1 | moving_average (defaults) | XAUUSD | H1 | none | -17.7 | -1914 | -2552 | -109 | 4148 | -1914 |
| 10 | b1 | moving_average (defaults) | USDJPY | H1 | none | -58.0 | -6324 | -6689 | -192 | 4448 | -6324 |
| 11 | b1 | moving_average (defaults) | XAUUSD | H4 | none | -1.6 | -172 | -842 | -83 | 1034 | -172 |
| 12 | b1 | moving_average (defaults) | EURUSD | H1 | none | -98.1 | -10696 | -11507 | -135 | 4559 | -10697 |
| 13 | b1 | moving_average (defaults) | USDJPY | H4 | none | -1.5 | -164 | -1104 | -99 | 1048 | -163 |
| 14 | b1 | moving_average (defaults) | EURUSD | H4 | none | -3.2 | -348 | -1144 | -84 | 1029 | -348 |
| 15 | b1 | moving_average (defaults) | GBPUSD | H4 | none | -10.3 | -1116 | -1216 | -64 | 1032 | -1116 |
| 16 | b1 | moving_average (defaults) | GBPUSD | H1 | none | -67.8 | -7394 | -7680 | -123 | 4567 | -7394 |
| 17 | b1 | free_robot (pattern=engulfing, osc=rsi) | XAUUSD | H1 | none | -6.1 | -657 | -657 | -72 | 148 | -657 |
| 18 | b1 | free_robot (pattern=engulfing, osc=rsi) | USDJPY | H1 | 0.25% | -3.3 | -359 | -475 | -48 | 116 | -359 |
| 19 | b1 | spike_trader (defaults) | XAUUSD | D1 | 0.50% | 3.1 | 339 | -481 | -60 | 179 | 69 |
| 20 | b1 | spike_trader (defaults) | USDJPY | D1 | 0.25% | -1.0 | -112 | -284 | -32 | 111 | -112 |
| 21 | b1 | spike_trader (defaults) | EURUSD | D1 | 0.25% | -1.0 | -112 | -285 | -24 | 113 | -112 |
| 22 | b1 | free_robot (pattern=engulfing, osc=rsi) | GBPUSD | H1 | 0.25% | -3.0 | -329 | -429 | -67 | 128 | -329 |
| 23 | b1 | free_robot (pattern=engulfing, osc=rsi) | EURUSD | H1 | 0.25% | -3.8 | -415 | -559 | -30 | 114 | -415 |
| 24 | b1 | spike_trader (defaults) | GBPUSD | D1 | 0.50% | 1.9 | 203 | -554 | -94 | 152 | 164 |
| 25 | b1 | ichimoku_chikou (defaults) | XAUUSD | D1 | 0.75% | 3.1 | 336 | -529 | -163 | 93 | 78 |
| 26 | b1 | ichimoku_chikou (defaults) | USDJPY | D1 | 0.50% | 4.0 | 436 | -567 | -109 | 97 | 249 |
| 27 | b1 | ichimoku_chikou (defaults) | GBPUSD | D1 | 0.25% | -0.5 | -56 | -247 | -27 | 67 | -56 |
| 28 | b1 | ichimoku_chikou (defaults) | EURUSD | D1 | 0.25% | -1.3 | -142 | -354 | -41 | 97 | -142 |
| 29 | b1 | weekly_breakout (defaults) | XAUUSD | H1 | 0.75% | 8.8 | 950 | -513 | -90 | 365 | 109 |
| 30 | b1 | weekly_breakout (defaults) | EURUSD | H1 | 0.25% | -1.4 | -154 | -319 | -26 | 334 | -154 |
| 31 | b1 | weekly_breakout (defaults) | USDJPY | H1 | 0.25% | -0.2 | -24 | -270 | -29 | 352 | -24 |
| 32 | b1 | weekly_breakout (defaults) | GBPUSD | H1 | 0.50% | 0.0 | 1 | -469 | -86 | 405 | 110 |
| 33 | b1 | bb_breakout (defaults) | XAUUSD | H1 | 0.25% | 8.6 | 924 | -559 | -68 | 593 | 924 |
| 34 | b1 | bb_breakout (defaults) | USDJPY | H1 | none | -4.3 | -467 | -1437 | -74 | 645 | -467 |
| 35 | b1 | picky_breakout (defaults) | XAUUSD | D1 | 0.50% | 6.7 | 725 | -412 | -52 | 222 | 57 |
| 36 | b1 | picky_breakout (defaults) | USDJPY | D1 | 0.25% | 0.0 | 5 | -365 | -35 | 269 | 5 |
| 37 | b1 | picky_breakout (defaults) | EURUSD | D1 | 0.25% | -2.6 | -282 | -377 | -20 | 285 | -282 |
| 38 | b1 | picky_breakout (defaults) | GBPUSD | D1 | 0.25% | -0.5 | -52 | -318 | -31 | 201 | -53 |
| 39 | b1 | persistent_anti (defaults) | XAUUSD | W1 | 2.00% | 2.8 | 298 | -589 | -140 | 91 | 0 |
| 40 | b1 | persistent_anti (defaults) | USDJPY | W1 | 1.00% | -3.5 | -382 | -481 | -84 | 97 | -28 |
| 41 | b1 | bb_breakout (defaults) | EURUSD | H1 | none | -12.3 | -1339 | -1968 | -68 | 625 | -1339 |
| 42 | b1 | persistent_anti (defaults) | EURUSD | W1 | 1.50% | 0.6 | 64 | -512 | -93 | 120 | 4 |
| 43 | b1 | persistent_anti (defaults) | GBPUSD | W1 | 2.00% | 0.9 | 99 | -463 | -144 | 101 | 0 |
| 44 | b1 | bb_breakout (defaults) | GBPUSD | H1 | none | -1.3 | -138 | -978 | -66 | 641 | -138 |
| 45 | b1 | turtle (defaults) | XAUUSD | D1 | 0.50% | -0.1 | -7 | -526 | -126 | 62 | 205 |
| 46 | b1 | turtle (defaults) | USDJPY | D1 | 0.25% | 0.5 | 54 | -287 | -43 | 72 | 54 |
| 47 | b1 | turtle (defaults) | EURUSD | D1 | 0.25% | -3.3 | -360 | -482 | -44 | 77 | -360 |
| 48 | b1 | turtle (defaults) | GBPUSD | D1 | 0.25% | -0.6 | -64 | -226 | -42 | 54 | -64 |
| 49 | b1 | turtle (entry_n=55, exit_n=20) | XAUUSD | D1 | 0.75% | 3.5 | 378 | -524 | -163 | 34 | 191 |
| 50 | b1 | turtle (entry_n=55, exit_n=20) | USDJPY | D1 | 0.25% | -0.9 | -101 | -338 | -37 | 41 | -101 |
| 51 | b1 | turtle (entry_n=55, exit_n=20) | EURUSD | D1 | 0.25% | -1.9 | -201 | -306 | -32 | 38 | -201 |
| 52 | b1 | turtle (entry_n=55, exit_n=20) | GBPUSD | D1 | 0.50% | -1.3 | -138 | -376 | -62 | 40 | 6 |
| 53 | b1 | connors_rsi2 (defaults) | XAUUSD | D1 | 0.75% | -3.8 | -406 | -458 | -85 | 42 | -21 |
| 54 | b1 | connors_rsi2 (defaults) | USDJPY | D1 | 1.50% | 3.2 | 340 | -584 | -128 | 53 | 42 |
| 55 | b1 | connors_rsi2 (defaults) | EURUSD | D1 | 2.00% | 4.2 | 452 | -366 | -155 | 44 | 33 |
| 56 | b1 | connors_rsi2 (defaults) | GBPUSD | D1 | 2.00% | 17.9 | 1934 | -511 | -150 | 54 | 36 |
| 57 | b1 | alligator (defaults) | XAUUSD | H1 | none | -16.8 | -1811 | -3268 | -114 | 1684 | -1811 |
| 58 | b1 | alligator (defaults) | USDJPY | H1 | none | -1.8 | -194 | -1569 | -227 | 1721 | -194 |
| 59 | b1 | alligator (defaults) | EURUSD | H1 | none | -11.3 | -1227 | -2477 | -168 | 1699 | -1227 |
| 60 | b1 | alligator (defaults) | GBPUSD | H1 | none | -5.3 | -583 | -2308 | -141 | 1624 | -583 |
| 61 | b2 | connors_rsi2 (defaults) | AUDUSD | D1 | 1.25% | 0.2 | 26 | -553 | -84 | 44 | -3 |
| 62 | b2 | connors_rsi2 (defaults) | XAGUSD | D1 | 1.00% | -3.4 | -366 | -465 | -90 | 48 | -15 |
| 63 | b2 | connors_rsi2 (defaults) | NZDUSD | D1 | 2.00% | 11.5 | 1247 | -411 | -159 | 49 | 102 |
| 64 | b2 | connors_rsi2 (defaults) | USDCAD | D1 | 2.00% | 4.5 | 485 | -521 | -192 | 46 | 35 |
| 65 | b2 | connors_rsi2 (defaults) | USDCHF | D1 | 1.25% | -1.7 | -188 | -529 | -118 | 48 | -18 |
| 66 | b2 | connors_rsi2 (defaults) | EURJPY | D1 | 1.50% | 5.5 | 598 | -435 | -281 | 60 | 51 |
| 67 | b2 | connors_rsi2 (defaults) | GBPJPY | D1 | 0.75% | -0.9 | -93 | -534 | -67 | 61 | -33 |
| 68 | b2 | connors_rsi2 (defaults) | AUDJPY | D1 | 2.00% | 8.1 | 874 | -500 | -195 | 51 | 91 |
| 69 | b2 | connors_rsi2 (defaults) | NZDJPY | D1 | 1.25% | -0.3 | -31 | -281 | -94 | 18 | 0 |
| 70 | b2 | connors_rsi2 (defaults) | CHFJPY | D1 | 1.50% | 3.7 | 402 | -564 | -113 | 54 | 82 |
| 71 | b2 | connors_rsi2 (defaults) | CADJPY | D1 | 2.00% | 4.8 | 518 | -552 | -183 | 57 | 63 |
| 72 | b2 | connors_rsi2 (defaults) | EURGBP | D1 | 1.50% | 2.3 | 244 | -592 | -145 | 50 | 11 |
| 73 | b2 | connors_rsi2 (defaults) | EURCHF | D1 | 2.00% | 2.1 | 229 | -354 | -182 | 49 | 31 |
| 74 | b2 | connors_rsi2 (defaults) | GBPCHF | D1 | 0.50% | -1.4 | -146 | -345 | -47 | 56 | -13 |
| 75 | b2 | connors_rsi2 (defaults) | AUDCAD | D1 | 1.50% | 2.2 | 216 | -533 | -139 | 43 | 34 |
| 76 | b2 | connors_rsi2 (defaults) | USTEC | D1 | 2.00% | 12.8 | 230 | -142 | -112 | 4 | 0 |
| 77 | b2 | connors_rsi2 (defaults) | US30 | D1 | 1.50% | 4.7 | 507 | -581 | -147 | 58 | 15 |
| 78 | b2 | connors_rsi2 (defaults) | DE40 | D1 | 1.25% | -2.8 | -304 | -399 | -115 | 49 | -6 |
| 79 | b2 | connors_rsi2 (defaults) | US500 | D1 | 1.50% | 14.4 | 1556 | -508 | -160 | 51 | 225 |
| 80 | b2 | connors_rsi2 (side=long) | US30 | D1 | 2.00% | 6.3 | 678 | -524 | -176 | 47 | 15 |
| 81 | b2 | connors_rsi2 (side=long) | US500 | D1 | 1.50% | 8.9 | 961 | -590 | -160 | 37 | 146 |
| 82 | b2 | connors_rsi2 (side=long) | USTEC | D1 | 2.00% | 12.8 | 230 | -142 | -112 | 4 | 0 |
| 83 | b2 | connors_rsi2 (side=long) | DE40 | D1 | 1.50% | -0.7 | -75 | -545 | -173 | 25 | -6 |
| 84 | b2 | connors_rsi2 (side=long) | XAUUSD | D1 | 2.00% | 0.5 | 56 | -456 | -159 | 26 | 14 |
| 85 | b2 | connors_rsi2 (buy_lvl=10, sell_lvl=90) | GBPUSD | D1 | 1.25% | 9.2 | 993 | -543 | -124 | 109 | 57 |
| 86 | b2 | connors_rsi2 (buy_lvl=10, sell_lvl=90) | EURUSD | D1 | 1.25% | 1.5 | 159 | -591 | -160 | 103 | 39 |
| 87 | b2 | connors_rsi2 (buy_lvl=10, sell_lvl=90) | US500 | D1 | 0.75% | 3.8 | 406 | -477 | -87 | 102 | 132 |
| 88 | b2 | connors_rsi2 (buy_lvl=10, sell_lvl=90) | XAUUSD | D1 | 0.50% | -2.7 | -286 | -367 | -48 | 64 | -34 |
| 89 | b2 | connors_rsi2 (defaults) | GBPUSD | H4 | 0.50% | 1.7 | 189 | -431 | -103 | 396 | 122 |
| 90 | b2 | connors_rsi2 (defaults) | XAUUSD | H4 | none | -6.9 | -742 | -786 | -60 | 330 | -742 |
| 91 | b2 | connors_rsi2 (defaults) | EURUSD | H4 | 0.25% | -3.4 | -372 | -596 | -41 | 357 | -373 |
| 92 | b2 | connors_rsi2 (defaults) | USDJPY | H4 | 0.25% | -3.7 | -398 | -566 | -49 | 354 | -398 |
| 93 | b2 | free_robot (pattern=engulfing, osc=mfi) | XAUUSD | H1 | none | -10.2 | -1102 | -1121 | -98 | 301 | -1102 |
| 94 | b2 | free_robot (pattern=engulfing, osc=cci) | XAUUSD | H1 | none | -20.7 | -2231 | -2275 | -98 | 631 | -2231 |
| 95 | b2 | free_robot (pattern=harami, osc=rsi) | XAUUSD | H1 | 0.25% | -1.1 | -121 | -400 | -58 | 319 | -121 |
| 96 | b2 | free_robot (pattern=engulfing, osc=stoch) | XAUUSD | H1 | none | -10.0 | -1081 | -1147 | -98 | 462 | -1081 |
| 97 | b2 | free_robot (pattern=hammer, osc=rsi) | XAUUSD | H1 | 0.50% | 3.0 | 321 | -480 | -117 | 182 | 91 |
| 98 | b2 | free_robot (pattern=harami, osc=mfi) | XAUUSD | H1 | none | -7.7 | -831 | -1024 | -58 | 493 | -831 |
| 99 | b2 | free_robot (pattern=harami, osc=stoch) | XAUUSD | H1 | none | -7.1 | -767 | -960 | -54 | 584 | -767 |
| 100 | b2 | free_robot (pattern=harami, osc=cci) | XAUUSD | H1 | none | -15.1 | -1632 | -1736 | -65 | 1053 | -1632 |
| 101 | b2 | free_robot (pattern=hammer, osc=mfi) | XAUUSD | H1 | 0.25% | -2.4 | -260 | -371 | -46 | 243 | -260 |
| 102 | b2 | free_robot (pattern=star, osc=rsi) | XAUUSD | H1 | 0.50% | -2.3 | -250 | -444 | -163 | 53 | -117 |
| 103 | b2 | free_robot (pattern=hammer, osc=stoch) | XAUUSD | H1 | 0.25% | -1.5 | -162 | -354 | -46 | 286 | -162 |
| 104 | b2 | free_robot (pattern=hammer, osc=cci) | XAUUSD | H1 | none | -5.7 | -619 | -815 | -55 | 568 | -619 |
| 105 | b2 | free_robot (pattern=star, osc=stoch) | XAUUSD | H1 | 0.25% | -3.1 | -336 | -452 | -72 | 180 | -336 |
| 106 | b2 | free_robot (pattern=star, osc=mfi) | XAUUSD | H1 | none | -6.0 | -651 | -710 | -72 | 126 | -651 |
| 107 | b2 | free_robot (pattern=star, osc=cci) | XAUUSD | H1 | none | -7.1 | -763 | -803 | -72 | 239 | -763 |
| 108 | b2 | free_robot (pattern=soldiers, osc=rsi) | XAUUSD | H1 | 2.00% | 1.8 | 194 | -194 | -118 | 2 | 19 |
| 109 | b2 | free_robot (pattern=soldiers, osc=mfi) | XAUUSD | H1 | 0.50% | -2.3 | -254 | -488 | -50 | 48 | -128 |
| 110 | b2 | free_robot (pattern=soldiers, osc=cci) | XAUUSD | H1 | 1.25% | 1.8 | 196 | -521 | -124 | 24 | 35 |
| 111 | b2 | free_robot (pattern=darkcloud, osc=rsi) | XAUUSD | H1 | 1.00% | -3.7 | -401 | -488 | -99 | 9 | -88 |
| 112 | b2 | free_robot (pattern=soldiers, osc=stoch) | XAUUSD | H1 | none | -4.8 | -518 | -602 | -25 | 188 | -518 |
| 113 | b2 | free_robot (pattern=darkcloud, osc=mfi) | XAUUSD | H1 | 2.00% | 0.1 | 16 | -586 | -200 | 9 | 0 |
| 114 | b2 | free_robot (pattern=darkcloud, osc=cci) | XAUUSD | H1 | 0.75% | -3.6 | -392 | -515 | -75 | 23 | -125 |
| 115 | b2 | free_robot (pattern=darkcloud, osc=stoch) | XAUUSD | H1 | 1.50% | -0.6 | -63 | -500 | -149 | 10 | -7 |
| 116 | b2 | free_robot (pattern=meetinglines, osc=rsi) | XAUUSD | H1 | 2.00% | 0.0 | 0 | 0 | 0 | 0 | 0 |
| 117 | b2 | free_robot (pattern=meetinglines, osc=cci) | XAUUSD | H1 | 2.00% | 0.0 | 0 | 0 | 0 | 0 | 0 |
| 118 | b2 | free_robot (pattern=meetinglines, osc=stoch) | XAUUSD | H1 | 2.00% | 0.0 | 0 | 0 | 0 | 0 | 0 |
| 119 | b2 | free_robot (pattern=meetinglines, osc=mfi) | XAUUSD | H1 | 2.00% | 0.0 | 0 | 0 | 0 | 0 | 0 |
| 120 | b2 | weekly_breakout (defaults) | USTEC | H1 | 1.00% | -14.6 | -263 | -578 | -96 | 74 | 0 |
| 121 | b2 | weekly_breakout (defaults) | XAGUSD | H1 | 0.50% | 1.1 | 116 | -523 | -64 | 215 | 10 |
| 122 | b2 | weekly_breakout (defaults) | US30 | H1 | 0.50% | -0.5 | -49 | -508 | -84 | 129 | 43 |
| 123 | b2 | weekly_breakout (defaults) | US500 | H1 | 0.25% | -1.6 | -177 | -379 | -45 | 384 | -177 |
| 124 | b2 | weekly_breakout (defaults) | DE40 | H1 | 0.50% | 1.3 | 145 | -500 | -150 | 219 | 28 |
| 125 | b2 | weekly_breakout (defaults) | EURJPY | H1 | 0.50% | 1.5 | 168 | -500 | -60 | 400 | 146 |
| 126 | b2 | weekly_breakout (defaults) | GBPJPY | H1 | 0.75% | 11.8 | 1287 | -440 | -116 | 398 | 286 |
| 127 | b2 | weekly_breakout (side=long) | XAUUSD | H1 | 1.25% | 16.9 | 1820 | -553 | -152 | 214 | 140 |
| 128 | b2 | weekly_breakout (defaults) | AUDJPY | H1 | 1.00% | 13.7 | 1498 | -595 | -208 | 382 | 368 |
| 129 | b2 | weekly_breakout (sl_mode=atr, sl=3.0) | XAUUSD | H1 | 0.25% | 11.6 | 1251 | -429 | -68 | 396 | 1251 |
| 130 | b2 | weekly_breakout (sl_mode=atr, sl=3.0) | USDJPY | H1 | none | 1.5 | 164 | -772 | -108 | 416 | 164 |
| 131 | b2 | weekly_breakout (period=D) | XAUUSD | H1 | none | -6.2 | -670 | -984 | -54 | 1329 | -670 |
| 132 | b2 | weekly_breakout (period=D) | USDJPY | H1 | none | -9.5 | -1038 | -1318 | -48 | 1835 | -1038 |
| 133 | b2 | weekly_breakout (period=D) | US500 | H1 | none | -14.4 | -1560 | -1755 | -72 | 1703 | -1560 |
| 134 | b2 | bb_breakout (defaults) | USTEC | H1 | 0.25% | -0.5 | -9 | -310 | -64 | 104 | -9 |
| 135 | b2 | bb_breakout (defaults) | XAGUSD | H1 | none | -19.2 | -2068 | -2157 | -68 | 594 | -2068 |
| 136 | b2 | bb_breakout (defaults) | US30 | H1 | none | -4.2 | -456 | -921 | -88 | 562 | -456 |
| 137 | b2 | bb_breakout (defaults) | US500 | H1 | none | -7.5 | -812 | -1181 | -74 | 571 | -812 |
| 138 | b2 | bb_breakout (defaults) | DE40 | H1 | none | 5.2 | 567 | -644 | -151 | 554 | 567 |
| 139 | b2 | bb_breakout (defaults) | EURJPY | H1 | none | -22.2 | -2421 | -2786 | -75 | 679 | -2421 |
| 140 | b2 | bb_breakout (defaults) | GBPJPY | H1 | none | -9.2 | -1004 | -1449 | -68 | 649 | -1004 |
| 141 | b2 | bb_breakout (defaults) | AUDJPY | H1 | none | -11.7 | -1277 | -1907 | -63 | 677 | -1277 |
| 142 | b2 | bb_breakout (period=100, dev=2.0) | XAUUSD | H1 | none | -0.1 | -13 | -1049 | -64 | 881 | -13 |
| 143 | b2 | picky_breakout (defaults) | XAGUSD | D1 | 0.50% | -0.2 | -20 | -377 | -60 | 179 | -45 |
| 144 | b2 | bb_breakout (period=300, dev=2.0) | XAUUSD | H1 | none | 1.1 | 115 | -642 | -73 | 471 | 115 |
| 145 | b2 | picky_breakout (defaults) | US30 | D1 | 0.75% | 7.2 | 778 | -552 | -81 | 190 | 95 |
| 146 | b2 | bb_breakout (period=200, dev=1.5) | XAUUSD | H1 | none | -8.0 | -862 | -1521 | -67 | 866 | -862 |
| 147 | b2 | picky_breakout (defaults) | USTEC | D1 | 0.75% | -13.1 | -236 | -594 | -58 | 59 | 0 |
| 148 | b2 | picky_breakout (defaults) | US500 | D1 | 0.25% | 0.2 | 26 | -317 | -38 | 314 | 26 |
| 149 | b2 | picky_breakout (defaults) | DE40 | D1 | 0.50% | -0.5 | -57 | -440 | -80 | 199 | -34 |
| 150 | b2 | picky_breakout (defaults) | EURJPY | D1 | 0.50% | -0.1 | -9 | -587 | -62 | 286 | 74 |
| 151 | b2 | picky_breakout (defaults) | GBPJPY | D1 | 0.75% | 11.5 | 1247 | -413 | -84 | 299 | 258 |
| 152 | b2 | bb_breakout (period=200, dev=2.5) | XAUUSD | H1 | 0.50% | 28.5 | 3073 | -566 | -170 | 346 | 1348 |
| 153 | b2 | picky_breakout (lookup=12) | XAUUSD | D1 | 1.00% | 8.4 | 906 | -478 | -103 | 230 | 122 |
| 154 | b2 | picky_breakout (defaults) | AUDJPY | D1 | 1.00% | 11.5 | 1237 | -496 | -126 | 280 | 177 |
| 155 | b2 | picky_breakout (lookup=5) | XAUUSD | D1 | 0.50% | 8.8 | 946 | -280 | -50 | 279 | 298 |
| 156 | b2 | picky_breakout (hold=3) | XAUUSD | D1 | 1.00% | 7.3 | 792 | -562 | -95 | 322 | 33 |
| 157 | b2 | picky_breakout (hold=8) | XAUUSD | D1 | 0.75% | 5.8 | 627 | -554 | -146 | 221 | 126 |
| 158 | b2 | picky_breakout (days=[0, 1, 2, 3, 4]) | XAUUSD | D1 | 0.75% | 4.9 | 528 | -591 | -101 | 347 | 143 |
| 159 | b3 | bb_breakout (period=150, dev=2.75) | XAUUSD | H1 | 0.25% | 4.7 | 502 | -470 | -57 | 322 | 502 |
| 160 | b3 | bb_breakout (period=150, dev=3.0) | XAUUSD | H1 | 0.25% | 2.3 | 251 | -425 | -59 | 241 | 251 |
| 161 | b3 | bb_breakout (period=150, dev=2.5) | XAUUSD | H1 | none | 5.4 | 583 | -996 | -73 | 411 | 583 |
| 162 | b3 | bb_breakout (period=150, dev=2.25) | XAUUSD | H1 | 0.25% | 9.8 | 1060 | -452 | -77 | 551 | 1060 |
| 163 | b3 | bb_breakout (period=200, dev=3.0) | XAUUSD | H1 | 0.25% | 1.2 | 124 | -341 | -62 | 203 | 124 |
| 164 | b3 | bb_breakout (period=200, dev=2.75) | XAUUSD | H1 | 0.25% | 8.1 | 879 | -275 | -73 | 259 | 879 |
| 165 | b3 | bb_breakout (period=200, dev=2.25) | XAUUSD | H1 | 0.25% | 16.5 | 1777 | -344 | -73 | 459 | 1777 |
| 166 | b3 | bb_breakout (period=250, dev=2.25) | XAUUSD | H1 | 0.25% | 15.2 | 1640 | -354 | -61 | 400 | 1640 |
| 167 | b3 | bb_breakout (period=250, dev=2.75) | XAUUSD | H1 | 0.25% | 6.2 | 671 | -305 | -73 | 229 | 671 |
| 168 | b3 | bb_breakout (period=250, dev=2.5) | XAUUSD | H1 | 0.25% | 13.1 | 1413 | -337 | -75 | 316 | 1413 |
| 169 | b3 | bb_breakout (period=250, dev=3.0) | XAUUSD | H1 | 0.25% | 2.1 | 223 | -319 | -73 | 176 | 223 |
| 170 | b3 | bb_breakout (dev=2.5, sl=1.0, tp=2.5) | XAUUSD | H1 | 0.25% | 4.0 | 429 | -465 | -111 | 436 | 429 |
| 171 | b3 | bb_breakout (dev=2.5, sl=1.5, tp=2.0) | XAUUSD | H1 | 0.50% | 18.4 | 1989 | -442 | -114 | 418 | 902 |
| 172 | b3 | bb_breakout (dev=2.5, sl=2.0, tp=5.0) | XAUUSD | H1 | 0.25% | 9.3 | 1009 | -350 | -59 | 296 | 1009 |
| 173 | b3 | bb_breakout (dev=2.5, sl=1.5, tp=6.0) | XAUUSD | H1 | 0.25% | 18.4 | 1988 | -353 | -81 | 305 | 1988 |
| 174 | b3 | bb_breakout (dev=2.5) | XAGUSD | H1 | none | -1.5 | -157 | -893 | -61 | 361 | -157 |
| 175 | b3 | bb_breakout (dev=2.5) | US500 | H1 | 0.25% | 5.0 | 543 | -479 | -74 | 299 | 543 |
| 176 | b3 | bb_breakout (dev=2.5) | US30 | H1 | none | -0.2 | -22 | -732 | -69 | 316 | -22 |
| 177 | b3 | bb_breakout (dev=2.5) | DE40 | H1 | 0.25% | 10.4 | 1123 | -373 | -66 | 320 | 1123 |
| 178 | b3 | bb_breakout (dev=2.5) | USDJPY | H1 | none | 3.6 | 396 | -807 | -92 | 348 | 396 |
| 179 | b3 | bb_breakout (dev=2.5) | EURJPY | H1 | none | -15.7 | -1708 | -1911 | -70 | 389 | -1708 |
| 180 | b3 | bb_breakout (dev=2.5) | GBPJPY | H1 | none | -3.7 | -407 | -612 | -58 | 350 | -407 |
| 181 | b3 | bb_breakout (dev=2.5) | AUDJPY | H1 | none | -3.7 | -401 | -891 | -96 | 396 | -401 |
| 182 | b3 | bb_breakout (dev=2.5) | CHFJPY | H1 | none | -22.6 | -2466 | -2562 | -103 | 369 | -2466 |
| 183 | b3 | bb_breakout (dev=2.5) | NZDJPY | H1 | none | -3.6 | -388 | -835 | -67 | 209 | -388 |
| 184 | b3 | bb_breakout (dev=2.5) | CADJPY | H1 | none | -13.5 | -1468 | -1660 | -78 | 350 | -1468 |
| 185 | b3 | bb_breakout (dev=2.5) | EURUSD | H1 | none | -6.4 | -700 | -1152 | -79 | 350 | -700 |
| 186 | b3 | bb_breakout (dev=2.5) | GBPUSD | H1 | 0.25% | -4.5 | -494 | -546 | -66 | 347 | -494 |
| 187 | b3 | bb_breakout (dev=2.5) | XAUUSD | H4 | 0.25% | -1.2 | -131 | -312 | -50 | 94 | -131 |
| 188 | b3 | bb_breakout (dev=2.5) | XAGUSD | H4 | 0.50% | 1.6 | 169 | -380 | -99 | 85 | 87 |
| 189 | b3 | bb_breakout (dev=2.5) | USDJPY | H4 | 0.50% | 10.3 | 1113 | -499 | -99 | 86 | 548 |
| 190 | b3 | bb_breakout (dev=2.5) | AUDUSD | H1 | none | -6.2 | -679 | -710 | -74 | 357 | -679 |
| 191 | b3 | filtered (base=bb_breakout, dev=2.5, side=long) | XAUUSD | H1 | 0.50% | 20.9 | 2259 | -497 | -170 | 202 | 962 |
| 192 | b3 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | XAUUSD | H1 | 0.50% | 30.4 | 3282 | -591 | -170 | 283 | 1494 |
| 193 | b3 | bb_breakout (dev=2.5) | XAUUSD | M30 | 0.25% | -0.2 | -17 | -531 | -70 | 440 | -17 |
| 194 | b3 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | USDJPY | H1 | 0.25% | 1.6 | 177 | -503 | -92 | 291 | 177 |
| 195 | b3 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | GBPJPY | H1 | none | -2.9 | -317 | -608 | -58 | 285 | -317 |
| 196 | b3 | weekly_breakout (defaults) | NZDJPY | H1 | 1.00% | 6.9 | 748 | -270 | -130 | 49 | 0 |
| 197 | b3 | weekly_breakout (defaults) | CHFJPY | H1 | 0.25% | -1.4 | -150 | -340 | -34 | 330 | -149 |
| 198 | b3 | weekly_breakout (defaults) | CADJPY | H1 | 0.50% | -2.9 | -311 | -596 | -80 | 417 | -20 |
| 199 | b3 | weekly_breakout (period=D) | AUDJPY | H1 | none | -12.2 | -1325 | -1529 | -46 | 1824 | -1325 |
| 200 | b3 | weekly_breakout (period=D) | GBPJPY | H1 | none | -3.2 | -345 | -935 | -49 | 1721 | -345 |
| 201 | b3 | weekly_breakout (period=D) | EURJPY | H1 | none | -6.0 | -651 | -862 | -46 | 1828 | -651 |
| 202 | b3 | weekly_breakout (fri_hour=16) | AUDJPY | H1 | 1.00% | 12.7 | 1389 | -532 | -208 | 374 | 345 |
| 203 | b3 | weekly_breakout (fri_hour=16) | GBPJPY | H1 | 1.00% | 14.1 | 1533 | -501 | -119 | 397 | 250 |
| 204 | b3 | weekly_breakout (fri_hour=16) | XAUUSD | H1 | 0.75% | 5.0 | 539 | -418 | -90 | 354 | 126 |
| 205 | b3 | weekly_breakout (sl_mode=atr, sl=3.0) | AUDJPY | H1 | 0.25% | 6.1 | 667 | -453 | -101 | 379 | 667 |
| 206 | b3 | weekly_breakout (sl_mode=atr, sl=3.0) | GBPJPY | H1 | none | 6.8 | 746 | -738 | -87 | 406 | 746 |
| 207 | b3 | weekly_breakout (side=long) | AUDJPY | H1 | 0.50% | -2.4 | -262 | -468 | -61 | 207 | -100 |
| 208 | b3 | weekly_breakout (side=long) | GBPJPY | H1 | 1.25% | 9.4 | 1022 | -594 | -143 | 209 | 157 |
| 209 | b3 | weekly_breakout (side=short) | AUDJPY | H1 | 1.50% | 29.1 | 3170 | -589 | -185 | 172 | 467 |
| 210 | b3 | weekly_breakout (side=short) | GBPJPY | H1 | 0.75% | 6.0 | 650 | -453 | -102 | 196 | 129 |
| 211 | b3 | filtered (base=weekly_breakout, trend_n=1000) | XAUUSD | H1 | 1.25% | 9.9 | 1070 | -580 | -217 | 287 | 113 |
| 212 | b3 | filtered (base=weekly_breakout, trend_n=1000) | AUDJPY | H1 | 1.00% | 12.2 | 1326 | -574 | -208 | 278 | 282 |
| 213 | b3 | picky_breakout (defaults) | CHFJPY | D1 | 0.25% | -2.1 | -228 | -485 | -28 | 280 | -228 |
| 214 | b3 | picky_breakout (defaults) | NZDJPY | D1 | 1.25% | 12.7 | 1369 | -479 | -146 | 94 | 0 |
| 215 | b3 | filtered (base=weekly_breakout, trend_n=1000) | GBPJPY | H1 | 0.75% | 3.4 | 375 | -472 | -102 | 296 | 86 |
| 216 | b3 | picky_breakout (defaults) | CADJPY | D1 | 0.25% | -2.6 | -276 | -378 | -26 | 298 | -276 |
| 217 | b3 | filtered (base=weekly_breakout, trend_n=1000) | EURJPY | H1 | 0.50% | 0.8 | 88 | -436 | -57 | 289 | 85 |
| 218 | b3 | picky_breakout (lookup=5) | GBPJPY | D1 | 0.50% | 3.9 | 418 | -368 | -88 | 366 | 123 |
| 219 | b3 | picky_breakout (lookup=5) | AUDJPY | D1 | 0.50% | 3.8 | 407 | -341 | -92 | 360 | 202 |
| 220 | b3 | picky_breakout (lookup=12) | GBPJPY | D1 | 0.75% | 9.6 | 1039 | -558 | -84 | 241 | 197 |
| 221 | b3 | picky_breakout (lookup=12) | AUDJPY | D1 | 0.75% | 5.6 | 607 | -455 | -100 | 227 | 132 |
| 222 | b3 | picky_breakout (hold=3) | GBPJPY | D1 | 1.00% | 11.1 | 1204 | -552 | -112 | 332 | 140 |
| 223 | b3 | filtered (base=weekly_breakout, trend_n=1000) | USDJPY | H1 | 0.25% | -0.0 | -4 | -220 | -27 | 270 | -4 |
| 224 | b3 | picky_breakout (hold=3) | AUDJPY | D1 | 1.00% | 6.2 | 673 | -503 | -126 | 307 | 46 |
| 225 | b3 | picky_breakout (hold=8) | GBPJPY | D1 | 0.75% | 17.1 | 1848 | -543 | -84 | 230 | 552 |
| 226 | b3 | picky_breakout (hold=8) | AUDJPY | D1 | 0.75% | 4.1 | 440 | -456 | -138 | 218 | 59 |
| 227 | b3 | connors_rsi2 (buy_lvl=3, sell_lvl=97) | US500 | D1 | 1.25% | 1.6 | 178 | -563 | -132 | 26 | 32 |
| 228 | b3 | picky_breakout (sl=3.0) | AUDJPY | D1 | 1.50% | 9.7 | 1049 | -491 | -167 | 280 | 186 |
| 229 | b3 | picky_breakout (sl=3.0) | GBPJPY | D1 | 1.00% | 9.4 | 1020 | -493 | -69 | 297 | 23 |
| 230 | b3 | connors_rsi2 (buy_lvl=3, sell_lvl=97) | GBPUSD | D1 | 2.00% | 7.8 | 840 | -539 | -153 | 30 | 11 |
| 231 | b3 | connors_rsi2 (buy_lvl=3, sell_lvl=97) | NZDUSD | D1 | 2.00% | -0.6 | -65 | -554 | -139 | 27 | -12 |
| 232 | b3 | connors_rsi2 (exit_n=3) | US500 | D1 | 1.50% | 10.1 | 1089 | -509 | -146 | 51 | 154 |
| 233 | b3 | connors_rsi2 (exit_n=3) | GBPUSD | D1 | 2.00% | 13.4 | 1448 | -522 | -150 | 55 | 37 |
| 234 | b3 | connors_rsi2 (exit_n=3) | NZDUSD | D1 | 2.00% | 7.2 | 781 | -466 | -159 | 49 | 59 |
| 235 | b3 | connors_rsi2 (exit_n=10) | US500 | D1 | 1.25% | 8.1 | 873 | -520 | -164 | 49 | 135 |
| 236 | b3 | connors_rsi2 (exit_n=10) | GBPUSD | D1 | 1.50% | 14.3 | 1548 | -416 | -130 | 52 | 31 |
| 237 | b3 | connors_rsi2 (exit_n=10) | NZDUSD | D1 | 1.25% | 0.5 | 59 | -529 | -104 | 46 | 15 |
| 238 | b3 | connors_rsi2 (sl=3.0) | US500 | D1 | 2.00% | 10.8 | 1166 | -527 | -192 | 51 | 108 |
| 239 | b3 | connors_rsi2 (sl=3.0) | GBPUSD | D1 | 2.00% | 12.3 | 1334 | -290 | -102 | 52 | 16 |
| 240 | b3 | connors_rsi2 (sl=3.0) | NZDUSD | D1 | 2.00% | 7.2 | 776 | -383 | -103 | 49 | 88 |
| 241 | b3 | connors_rsi2 (trend_n=100) | US500 | D1 | 1.50% | 13.1 | 1409 | -459 | -160 | 44 | 203 |
| 242 | b3 | connors_rsi2 (trend_n=100) | GBPUSD | D1 | 2.00% | 10.0 | 1075 | -446 | -148 | 48 | -24 |
| 243 | b3 | connors_rsi2 (trend_n=100) | NZDUSD | D1 | 1.50% | 8.9 | 964 | -462 | -112 | 48 | 121 |
| 244 | b3 | connors_rsi2 (rsi_n=3) | US500 | D1 | 2.00% | -0.5 | -58 | -347 | -198 | 8 | 0 |
| 245 | b3 | connors_rsi2 (rsi_n=3) | GBPUSD | D1 | 2.00% | 1.3 | 144 | -147 | -70 | 3 | 7 |
| 246 | b3 | connors_rsi2 (rsi_n=3) | NZDUSD | D1 | 2.00% | 1.3 | 146 | -230 | -136 | 11 | 14 |
| 247 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[12, 19], trend_n=1000) | XAUUSD | H1 | 0.25% | 11.9 | 1280 | -291 | -73 | 174 | 1280 |
| 248 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[13, 20], trend_n=1000) | XAUUSD | H1 | 0.25% | 10.4 | 1118 | -307 | -73 | 181 | 1118 |
| 249 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[12, 19]) | XAUUSD | H1 | 0.50% | 24.1 | 2606 | -504 | -145 | 217 | 1284 |
| 250 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[13, 20]) | XAUUSD | H1 | 0.50% | 20.8 | 2243 | -561 | -145 | 226 | 1100 |
| 251 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[8, 20]) | XAUUSD | H1 | 0.50% | 30.5 | 3292 | -556 | -145 | 281 | 1556 |
| 252 | b4 | filtered (base=bb_breakout, dev=2.5, hours=[8, 20], trend_n=1000) | XAUUSD | H1 | 0.25% | 14.2 | 1535 | -327 | -73 | 221 | 1535 |
| 253 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=500) | XAUUSD | H1 | 0.50% | 31.2 | 3373 | -474 | -170 | 327 | 1496 |
| 254 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=2000) | XAUUSD | H1 | 0.25% | 9.2 | 989 | -336 | -75 | 244 | 989 |
| 255 | b4 | filtered (base=bb_breakout, dev=2.75, trend_n=1000) | XAUUSD | H1 | 0.25% | 9.2 | 993 | -296 | -73 | 220 | 993 |
| 256 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=1000, sl=1.5, tp=2.5) | XAUUSD | H1 | 0.25% | 12.6 | 1358 | -289 | -48 | 318 | 1358 |
| 257 | b4 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | XAUUSD | H1 | 0.50% | 40.7 | 4397 | -565 | -145 | 358 | 1989 |
| 258 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | XAGUSD | H1 | none | -3.4 | -367 | -830 | -61 | 293 | -367 |
| 259 | b4 | turtle (defaults) | XAUUSD | H4 | 0.25% | 8.8 | 950 | -463 | -121 | 387 | 950 |
| 260 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | US500 | H1 | 0.25% | 4.3 | 468 | -381 | -72 | 215 | 468 |
| 261 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | DE40 | H1 | 0.25% | 8.4 | 907 | -363 | -66 | 250 | 907 |
| 262 | b4 | turtle (defaults) | USDJPY | H4 | 0.25% | 0.7 | 76 | -427 | -93 | 443 | 76 |
| 263 | b4 | filtered (base=bb_breakout, dev=2.5, trend_n=1000) | AUDJPY | H1 | none | -1.2 | -131 | -751 | -96 | 336 | -131 |
| 264 | b4 | turtle (defaults) | GBPJPY | D1 | 0.75% | 5.5 | 599 | -513 | -134 | 71 | 190 |
| 265 | b4 | turtle (defaults) | GBPJPY | H4 | 0.25% | 7.3 | 789 | -429 | -66 | 429 | 789 |
| 266 | b4 | turtle (entry_n=55, exit_n=20) | XAUUSD | H4 | 0.25% | 7.7 | 831 | -345 | -142 | 206 | 831 |
| 267 | b4 | turtle (defaults) | AUDJPY | D1 | 0.75% | 0.7 | 77 | -559 | -182 | 66 | 56 |
| 268 | b4 | turtle (entry_n=55, exit_n=20) | USDJPY | H4 | none | -1.8 | -198 | -981 | -110 | 227 | -198 |
| 269 | b4 | turtle (defaults) | US500 | D1 | 0.50% | -0.6 | -66 | -486 | -128 | 76 | 21 |
| 270 | b4 | turtle (defaults) | XAGUSD | D1 | 0.50% | -1.4 | -154 | -483 | -236 | 47 | -33 |
| 271 | b4 | turtle (side=long) | XAUUSD | D1 | 0.75% | 6.2 | 667 | -464 | -163 | 37 | 243 |
| 272 | b4 | turtle (side=long) | US500 | D1 | 1.00% | 15.9 | 1719 | -486 | -197 | 39 | 426 |
| 273 | b4 | ichimoku_chikou (defaults) | GBPJPY | D1 | 0.25% | 0.5 | 53 | -324 | -45 | 52 | 53 |
| 274 | b4 | ichimoku_chikou (defaults) | AUDJPY | D1 | 0.25% | -0.4 | -38 | -270 | -61 | 102 | -38 |
| 275 | b4 | ichimoku_chikou (defaults) | EURJPY | D1 | 0.25% | -2.1 | -226 | -279 | -35 | 105 | -226 |
| 276 | b4 | ichimoku_chikou (defaults) | US500 | D1 | 0.50% | 4.1 | 440 | -483 | -189 | 85 | 239 |
| 277 | b4 | ichimoku_chikou (defaults) | XAGUSD | D1 | 0.50% | -0.7 | -74 | -569 | -236 | 65 | 57 |
| 278 | b4 | ichimoku_chikou (defaults) | XAUUSD | H4 | 0.25% | 8.7 | 942 | -476 | -67 | 562 | 942 |
| 279 | b4 | ichimoku_chikou (defaults) | USDJPY | H4 | none | -3.7 | -404 | -851 | -111 | 624 | -404 |
| 280 | b4 | spike_trader (pct=0.002) | XAUUSD | D1 | 0.50% | 2.0 | 217 | -539 | -60 | 234 | 51 |
| 281 | b4 | spike_trader (pct=0.005) | XAUUSD | D1 | 0.50% | 4.3 | 466 | -443 | -60 | 117 | -78 |
| 282 | b4 | spike_trader (bars=2) | XAUUSD | D1 | 0.25% | -0.2 | -20 | -276 | -24 | 65 | -20 |
| 283 | b4 | spike_trader (bars=5) | XAUUSD | D1 | 0.50% | 3.6 | 394 | -407 | -60 | 151 | 107 |
| 284 | b4 | spike_trader (sl_mode=atr, sl=2.0) | XAUUSD | D1 | 0.50% | 2.1 | 224 | -480 | -60 | 163 | 68 |
| 285 | b4 | spike_trader (defaults) | AUDJPY | D1 | 0.25% | 0.1 | 6 | -371 | -38 | 179 | 6 |
| 286 | b4 | spike_trader (defaults) | GBPJPY | D1 | 0.75% | 8.9 | 963 | -458 | -141 | 178 | 251 |
| 287 | b4 | spike_trader (defaults) | US500 | D1 | 0.50% | -3.3 | -352 | -586 | -130 | 219 | -179 |
| 288 | b4 | spike_trader (defaults) | XAGUSD | D1 | 0.25% | -3.1 | -332 | -349 | -27 | 46 | -332 |
| 289 | b4 | macd_sample (defaults) | XAGUSD | H4 | 0.25% | -3.9 | -419 | -513 | -28 | 140 | -419 |
| 290 | b4 | macd_sample (defaults) | AUDUSD | H4 | 0.25% | -4.4 | -475 | -583 | -32 | 208 | -475 |
| 291 | b4 | macd_sample (defaults) | USDCAD | H4 | 0.25% | 1.8 | 192 | -302 | -31 | 189 | 192 |
| 292 | b4 | macd_sample (defaults) | NZDUSD | H4 | 0.25% | -3.4 | -365 | -542 | -33 | 200 | -365 |
| 293 | b4 | macd_sample (defaults) | XAUUSD | D1 | 0.75% | -3.1 | -338 | -485 | -75 | 30 | -24 |
| 294 | b4 | macd_sample (defaults) | USDJPY | D1 | 0.75% | 2.0 | 215 | -522 | -77 | 35 | 57 |
| 295 | b4 | macd_sample (use_trail=False) | USDJPY | H4 | 0.75% | 5.3 | 575 | -567 | -133 | 148 | 130 |
| 296 | b4 | macd_sample (defaults) | GBPJPY | D1 | 1.50% | 6.1 | 657 | -591 | -115 | 28 | -5 |
| 297 | b4 | macd_sample (use_trail=False) | XAUUSD | H4 | 0.50% | 1.1 | 116 | -461 | -56 | 164 | -61 |
| 298 | b4 | persistent_anti (defaults) | XAUUSD | D1 | 0.50% | -2.0 | -215 | -498 | -50 | 432 | -117 |
| 299 | b4 | persistent_anti (reverse=False) | XAUUSD | W1 | 2.00% | -4.5 | -491 | -513 | -150 | 90 | 0 |
| 300 | b4 | persistent_anti (reverse=False) | USDJPY | W1 | 1.50% | 3.5 | 373 | -526 | -129 | 97 | 22 |
| 301 | b4 | persistent_anti (defaults) | USDJPY | D1 | 0.25% | -3.5 | -380 | -469 | -22 | 503 | -380 |
| 302 | b4 | persistent_anti (defaults) | GBPUSD | D1 | 0.75% | 5.8 | 628 | -464 | -102 | 453 | 287 |
| 303 | b4 | connors_rsi2 (trend_n=1200) | XAUUSD | H4 | none | -6.5 | -706 | -717 | -47 | 382 | -706 |
| 304 | b4 | connors_rsi2 (trend_n=1200) | GBPUSD | H4 | 0.75% | 11.8 | 1271 | -552 | -167 | 468 | 458 |
| 305 | b4 | connors_rsi2 (trend_n=1200) | USDJPY | H4 | 0.25% | -1.4 | -148 | -321 | -51 | 432 | -148 |
| 306 | b4 | connors_rsi2 (trend_n=1200) | NZDUSD | H4 | none | -6.2 | -670 | -711 | -50 | 426 | -669 |
| 307 | b4 | alligator (defaults) | XAUUSD | D1 | 0.25% | -0.0 | -1 | -203 | -81 | 15 | -1 |
| 308 | b4 | alligator (defaults) | USDJPY | D1 | 0.25% | 2.7 | 289 | -320 | -44 | 69 | 289 |
| 309 | b4 | alligator (defaults) | GBPJPY | D1 | 0.25% | 0.6 | 70 | -279 | -46 | 40 | 70 |
| 310 | b4 | moving_average (defaults) | XAUUSD | D1 | 0.50% | 0.2 | 26 | -371 | -81 | 127 | 72 |
| 311 | b4 | moving_average (defaults) | USDJPY | D1 | 0.25% | -1.7 | -188 | -471 | -44 | 181 | -188 |
| 312 | b4 | moving_average (defaults) | GBPUSD | D1 | 0.25% | -2.4 | -262 | -320 | -47 | 138 | -262 |
| 313 | b4 | moving_average (defaults) | GBPJPY | D1 | 0.50% | 3.9 | 423 | -489 | -89 | 141 | 213 |
| 314 | b4 | alligator (defaults) | XAUUSD | H4 | none | 3.3 | 353 | -997 | -154 | 430 | 353 |
| 315 | b4 | alligator (defaults) | USDJPY | H4 | none | -18.3 | -1979 | -2212 | -111 | 483 | -1979 |
| 316 | b4 | free_robot (pattern=hammer, osc=rsi) | XAUUSD | D1 | 1.25% | -4.1 | -448 | -468 | -84 | 4 | -33 |
| 317 | b4 | free_robot (pattern=hammer, osc=rsi) | XAUUSD | H4 | 0.75% | -4.6 | -502 | -583 | -97 | 40 | -128 |
| 318 | b4 | free_robot (pattern=hammer, osc=rsi) | USDJPY | H4 | 0.75% | 0.0 | 5 | -496 | -139 | 56 | -16 |
| 319 | b4 | free_robot (pattern=engulfing, osc=rsi) | XAUUSD | D1 | 2.00% | 5.3 | 572 | -355 | -169 | 10 | 19 |
| 320 | b4 | free_robot (pattern=engulfing, osc=rsi) | XAUUSD | H4 | 0.50% | -2.9 | -313 | -572 | -66 | 42 | -115 |
| 321 | b4 | free_robot (pattern=engulfing, osc=rsi) | USDJPY | H4 | 1.00% | 1.5 | 165 | -502 | -100 | 24 | 46 |
| 322 | b4 | free_robot (pattern=soldiers, osc=cci) | XAUUSD | D1 | 2.00% | 0.1 | 6 | -328 | -146 | 2 | -4 |
| 323 | b4 | free_robot (pattern=soldiers, osc=cci) | XAUUSD | H4 | 2.00% | -0.4 | -49 | -458 | -199 | 10 | -3 |
| 324 | b4 | free_robot (pattern=soldiers, osc=cci) | USDJPY | H4 | 2.00% | 0.8 | 84 | -382 | -198 | 6 | 6 |
| 325 | b4 | free_robot (pattern=harami, osc=stoch) | XAUUSD | D1 | 1.00% | -2.7 | -293 | -548 | -86 | 40 | 15 |
| 326 | b4 | free_robot (pattern=harami, osc=stoch) | XAUUSD | H4 | 0.25% | -2.4 | -262 | -566 | -34 | 170 | -262 |
| 327 | b4 | free_robot (pattern=harami, osc=stoch) | USDJPY | H4 | 0.25% | -2.4 | -259 | -310 | -48 | 115 | -259 |
| 328 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, sl=1.5, tp=3.0) | XAUUSD | H1 | 0.25% | 12.3 | 1323 | -300 | -49 | 374 | 1323 |
| 329 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, sl=1.25, tp=3.1) | XAUUSD | H1 | 0.25% | 13.1 | 1419 | -387 | -75 | 390 | 1419 |
| 330 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, sl=1.5, tp=4.5) | XAUUSD | H1 | 0.25% | 17.5 | 1889 | -450 | -73 | 331 | 1889 |
| 331 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, sl=2.0, tp=5.0) | XAUUSD | H1 | 0.25% | 14.5 | 1566 | -263 | -54 | 298 | 1566 |
| 332 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, sl=1.0, tp=3.75) | XAUUSD | H1 | 0.25% | 19.2 | 2074 | -545 | -84 | 398 | 2074 |
| 333 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, period=250) | XAUUSD | H1 | 0.25% | 15.5 | 1677 | -289 | -61 | 329 | 1677 |
| 334 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000, period=150) | XAUUSD | H1 | 0.25% | 8.3 | 901 | -390 | -73 | 413 | 901 |
| 335 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=750) | XAUUSD | H1 | 0.25% | 18.0 | 1944 | -290 | -73 | 384 | 1943 |
| 336 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1500) | XAUUSD | H1 | 0.25% | 13.2 | 1428 | -387 | -61 | 342 | 1428 |
| 337 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | XAUUSD | H1 | 0.50% | 29.6 | 3200 | -586 | -121 | 358 | 1437 |
| 338 | b5 | filtered (base=bb_breakout, dev=2.5) | XAUUSD | H1 | 0.50% | 19.1 | 2064 | -588 | -173 | 346 | 908 |
| 339 | b5 | filtered (base=bb_breakout, dev=2.0, trend_n=1000) | XAUUSD | H1 | 0.25% | 9.3 | 1010 | -501 | -68 | 458 | 1010 |
| 340 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | XAGUSD | H1 | none | -10.6 | -1147 | -1287 | -52 | 360 | -1147 |
| 341 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | EURUSD | H1 | none | -8.3 | -902 | -1195 | -79 | 401 | -902 |
| 342 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | USDJPY | H1 | none | -3.8 | -412 | -1292 | -68 | 405 | -412 |
| 343 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | GBPJPY | H1 | none | -5.0 | -545 | -1058 | -60 | 377 | -545 |
| 344 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=250) | XAUUSD | H4 | 0.50% | 6.6 | 715 | -493 | -127 | 118 | 361 |
| 345 | b5 | connors_rsi2 (trend_n=1200) | EURUSD | H4 | 0.25% | -1.3 | -145 | -400 | -56 | 423 | -145 |
| 346 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | US30 | H1 | none | -4.7 | -506 | -795 | -88 | 326 | -507 |
| 347 | b5 | connors_rsi2 (trend_n=1200) | USDCAD | H4 | 0.25% | -4.2 | -455 | -532 | -47 | 421 | -455 |
| 348 | b5 | connors_rsi2 (trend_n=1200) | AUDUSD | H4 | 0.25% | -3.8 | -411 | -471 | -46 | 426 | -411 |
| 349 | b5 | filtered (base=bb_breakout, dev=2.25, trend_n=1000) | DE40 | H1 | none | 6.0 | 645 | -657 | -105 | 341 | 645 |
| 350 | b5 | connors_rsi2 (trend_n=1200, exit_n=10) | GBPUSD | H4 | 0.75% | 16.3 | 1759 | -579 | -167 | 458 | 628 |
| 351 | b5 | connors_rsi2 (trend_n=1200, buy_lvl=10, sell_lvl=90) | GBPUSD | H4 | 0.25% | -0.0 | -2 | -304 | -48 | 779 | -2 |
| 352 | b5 | connors_rsi2 (trend_n=600) | GBPUSD | H4 | 0.75% | 2.8 | 302 | -549 | -167 | 456 | 175 |
| 353 | b5 | connors_rsi2 (trend_n=2400) | GBPUSD | H4 | 0.25% | 0.1 | 14 | -289 | -52 | 433 | 14 |
| 354 | b5 | connors_rsi2 (trend_n=1200, sl=3.0) | GBPUSD | H4 | 1.00% | 13.3 | 1439 | -477 | -167 | 426 | 391 |
| 355 | b5 | connors_rsi2 (trend_n=1200) | GBPUSD | H4 | 0.75% | 6.6 | 714 | -571 | -161 | 468 | 255 |
| 356 | b5 | connors_rsi2 (defaults) | GBPUSD | D1 | 2.00% | 17.4 | 1876 | -517 | -150 | 54 | 32 |
| 357 | b5 | turtle (side=long, entry_n=55, exit_n=20) | US500 | D1 | 0.50% | 3.2 | 345 | -437 | -189 | 23 | 170 |
| 358 | b5 | turtle (side=long, entry_n=55, exit_n=20) | US30 | D1 | 0.50% | 0.5 | 54 | -525 | -136 | 14 | 273 |
| 359 | b5 | turtle (side=long, entry_n=55, exit_n=20) | DE40 | D1 | 0.50% | -2.2 | -240 | -362 | -54 | 21 | -72 |
| 360 | b5 | turtle (side=long) | US30 | D1 | 0.75% | 9.2 | 999 | -550 | -140 | 28 | 325 |
| 361 | b5 | turtle (side=long) | DE40 | D1 | 0.50% | -1.6 | -172 | -436 | -48 | 36 | -45 |
| 362 | b5 | connors_rsi2 (trend_n=4800) | EURGBP | H1 | none | -41.0 | -4464 | -4591 | -121 | 1710 | -4464 |
| 363 | b5 | connors_rsi2 (trend_n=4800) | GBPUSD | H1 | none | -16.3 | -1775 | -2072 | -112 | 1802 | -1775 |
| 364 | b5 | connors_rsi2 (trend_n=4800) | EURUSD | H1 | none | -25.6 | -2790 | -2952 | -126 | 1737 | -2790 |

# indicator_screen - broad indicator screen (in-sample 2015-01 .. 2023-12 only)

## Bottom line (honest)

**No indicator rule in this screen is a good prop-challenge strategy.** With the standard exit
(2xATR stop, 3xATR target, 48-bar time exit) the best rules that survive the luck checks make
about **$15-20 a month on $10k** (0.15-0.2%/month) at the highest safe risk. At that pace phase 1
(+8% = $800) takes about 3-4 years. The harness reports "100% challenge pass" for some of them, but
that only means the few attempts that finished all passed; the median time to pass both phases is
1,000-1,650 days and most attempts were still open at the end of the data.

The screen does tell us clearly **where** plain indicator strategies fail:

1. **H1 is dead after costs.** 46 rules x 23 symbols on H1: 3-10% of runs net positive, median
   profit factor 0.75-0.9. Spread + $7/side commission is ~0.1R per trade when the stop is 2xATR(H1).
   Every H1 run is worse than its H4 twin.
2. **H4 is cost-dragged but less so** (median PF ~0.9). D1 is roughly break-even: 47% of D1 runs
   are net positive, about what zero edge looks like when costs are small. So the indicators have
   **no gross edge**; the timeframe only changes how much the costs bite.
3. **Mean-reversion oscillator rules (RSI/Stoch/W%R/CCI/MFI/BB back inside band) lose most** on
   H1/H4 - many trades, ~40% win rate at 1.5R reward, PF 0.7-0.85.
4. **Trend/breakout rules are the least bad on H4** (Keltner breakout, squeeze breakout, DMI cross,
   Aroon cross): 20-28% of symbols positive. Adding the SMA(200) trend filter mostly helps
   (cuts trades in half, raises median PF ~0.03-0.05) but never turns a family positive.
5. **Indices (US30, US500) are the only place trend rules are consistently positive**, and even
   there short trades are about flat - it is mostly the 2015-2023 equity drift (long beta).
   DE40 does not confirm.
6. A "fix" attempt - a **consensus trend vote** (6 trend indicators must agree; v=4/5/6) - did not
   help: H4 still loses on 70-90% of symbols; D1 v=5 + trend filter is the best version at 50%
   positive / 36% positive in both halves, i.e. still near chance.
7. Longer holds (96 bars) change nothing; wider targets (4-5 ATR) cut results.

## Data coverage / caveats

- Symbols screened: all 23 (XAUUSD XAGUSD EURUSD GBPUSD USDJPY AUDUSD NZDUSD USDCAD USDCHF EURJPY
  GBPJPY AUDJPY CHFJPY NZDJPY CADJPY EURGBP EURCHF GBPCHF AUDCAD US30 US500 USTEC DE40), H1 + H4 + D1.
- **USTEC data starts 2022-07-06**, so its in-sample is only 1.5 years and it sits in a Nasdaq rally.
  USTEC tops the raw ranking (Table C) but is excluded from every conclusion and candidate.
- M30/M15 not used (task spec is H1/H4; M15 has ~1.5yr in-sample).
- The machine was short on RAM while other searches ran; some screen jobs hit MemoryError and were
  re-run in-process (screen.py resumes). Nothing is missing in the final CSVs.
- Causality: all indicators are trailing pandas rolling/ewm; entries fire on the close of the
  event bar. Checked: building signals on a truncated frame gives the identical prefix.

## Method

1. `strategies.py`: 15 indicators (RSI, MACD, Stochastic, CCI, ADX/DMI, Bollinger %B, Keltner,
   ATR percentile, Aroon, Williams %R, MFI + CMF on tick volume, OBV vs its EMA, EMA slope,
   Heikin-Ashi, Donchian position) turned into 23 cross/threshold rules (+1 consensus vote rule),
   each with and without the SMA(200) filter. ONE exit for all: stop 2xATR(14), target 3xATR(14),
   48-bar time exit, one position, opposite signal flips.
2. `screen.py`: fast pass - one `H.simulate` at 1% risk per run (risk is fixed-dollar so P&L scales
   ~linearly), best risk estimated by scaling DD/worst day to the 6%/3% limits, split into
   2015-2019 / 2020-2023 halves. 2,116 H1/H4 runs + 1,058 D1 runs + 252 vote runs = 3,426.
3. `verify.py` / `stage2.py` / `stage3.py`: the real `H.score` on every top cluster, with both
   halves at the chosen risk, neighbouring parameters and sister symbols (Table A).

## Luck checks on the top clusters (from Table A)

| cluster | default | neighbours | sister symbols | verdict |
|---|---|---|---|---|
| US30 H4 Aroon(25) cross + SMA200 | $20/mo @0.75%, both halves + | n=20 $10, n=35 $13, hold 96 $19, both sides + | US500 $4, DE40 -$1 | best of the screen, but mostly index drift; weak |
| US500 H4 EMA20xEMA50 + SMA200 | $17/mo @0.75%, halves $16/$18 | 10/50 $3, 20/100 $7 | US30 $1, DE40 $0 | long side only; peaky; weak |
| GBPJPY H4 Keltner breakout | $20/mo @0.5%, halves $16/$26 | n=15/30, k=1.5/2.5 all $2-4 @0.25% | EURJPY -, CHFJPY -, others ~0 | default is a lucky peak; NOT robust |
| GBPJPY H4 squeeze breakout + T | $5/mo | q=0.15 $13 (2015-19 flat) | AUDJPY $7, others <= $2 or negative | no |
| D1 squeeze breakout + T (all symbols) | 13/22 symbols positive | - | US500 $23, US30 $17, EURCHF $27 but 20-27 trades in 9 years | too few trades to trust |
| GBPJPY D1 Donchian(20) breakout | $19/mo @1% | n=15 $15, n=30 $1 | all other JPY crosses ~0 or negative | 2015-19 carries it; weak |
| CHFJPY H4 MFI reversal | $13/mo @0.5% | lo=15 -$3, lo=25 $0 | - | single-setting fluke; rejected |
| AUDUSD H4 Keltner reversion | $13/mo @0.5% | k=1.5 -$3, k=2.5 -$3 | NZDUSD -$2 | single-setting fluke; rejected |
| XAUUSD H4 DMI cross | $2/mo | n=10/20 negative, adx=25 $3 | XAGUSD negative | nothing on gold |

**Gold:** no indicator rule with the standard exit does anything on XAUUSD H1/H4/D1
(best real score $3/mo). The gold BOS strategy already live is far better than anything here.

## What to take from this

- The only lasting value here is negative knowledge plus the indicator library: plain textbook
  indicator entries with a symmetric ATR exit have no edge on these markets after FundedNext
  costs. Edges in this repo come from **structure + session timing** (gold BOS, JPY Tokyo-open),
  not from oscillators.
- If anyone keeps a candidate from this family, US30 H4 Aroon + trend is the only one that held up
  on neighbours, halves and both sides. Even it is ~0.2%/month and needs out-of-sample proof. As a
  standalone prop strategy it is too slow; at most it is a small diversifier.
- Possible next steps (not done): use these indicators as *filters* on the existing session/structure
  edges instead of as entry triggers; test indices with a long-only, volatility-targeted trend rule
  explicitly (that is beta, and should be named as such).


## Table A - every H.score run (90 runs, real judge, in-sample 2015-2023)

Halves are scored at the full-period best_risk (or 0.25% if none safe).

| name | sym | tf | best_risk% | avg_month | net | green | max_dd | worst_day | trades | 2015-19 $/mo | 2020-23 $/mo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| kelt_brk | GBPJPY | H4 | 0.50 | 20.1 | 2170.0 | 0.5 | -498.0 | -106.2 | 391 | 15.8 | 25.5 |
| kelt_brk | EURJPY | H4 |  | -7.6 | -820.4 | 0.4 | -1014.0 | -45.3 | 390 | -3.7 | -12.5 |
| kelt_brk | AUDJPY | H4 | 0.25 | 2.4 | 258.9 | 0.5 | -439.8 | -57.0 | 374 | 2.6 | 2.1 |
| kelt_brk | CADJPY | H4 | 0.25 | 0.2 | 24.4 | 0.4 | -461.9 | -68.6 | 402 | -5.1 | 6.9 |
| kelt_brk | NZDJPY | H4 | 0.50 | 1.8 | 193.0 | 0.2 | -527.9 | -69.1 | 89 | 8.5 | -6.8 |
| kelt_brk | CHFJPY | H4 |  | -9.2 | -995.9 | 0.4 | -1143.6 | -61.2 | 335 | -6.4 | -12.7 |
| kelt_brk | USDJPY | H4 | 0.25 | 2.8 | 305.9 | 0.6 | -439.8 | -54.3 | 425 | 2.5 | 3.2 |
| kelt_brk | XAUUSD | H4 | 0.25 | 1.3 | 138.9 | 0.5 | -384.4 | -44.4 | 381 | -2.9 | 6.5 |
| kelt_brk n=15 | GBPJPY | H4 | 0.25 | 2.0 | 215.0 | 0.5 | -415.7 | -44.8 | 328 | 0.6 | 3.7 |
| kelt_brk n=30 | GBPJPY | H4 | 0.25 | 4.4 | 478.6 | 0.5 | -374.7 | -46.0 | 419 | 3.8 | 5.3 |
| kelt_brk k=1.5 | GBPJPY | H4 | 0.25 | 3.6 | 388.5 | 0.5 | -314.8 | -43.9 | 525 | 3.9 | 3.3 |
| kelt_brk k=2.5 | GBPJPY | H4 | 0.25 | 4.3 | 460.6 | 0.5 | -335.7 | -44.8 | 239 | 8.5 | -1.0 |
| kelt_brk+T | GBPJPY | H4 | 0.50 | 17.6 | 1905.5 | 0.6 | -484.9 | -106.2 | 307 | 12.2 | 24.5 |
| squeeze_brk+T | GBPJPY | H4 | 0.25 | 5.3 | 575.0 | 0.4 | -317.0 | -33.4 | 172 | -0.1 | 12.1 |
| squeeze_brk+T | EURJPY | H4 |  | -5.1 | -555.9 | 0.3 | -790.5 | -44.6 | 192 | -10.8 | 1.9 |
| squeeze_brk+T | AUDJPY | H4 | 0.50 | 7.3 | 797.9 | 0.4 | -454.0 | -111.1 | 184 | -0.1 | 16.7 |
| squeeze_brk+T | CADJPY | H4 |  | -3.7 | -396.4 | 0.3 | -672.3 | -41.1 | 177 | -8.0 | 1.8 |
| squeeze_brk+T | NZDJPY | H4 | 0.25 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 |
| squeeze_brk+T | CHFJPY | H4 |  | -3.4 | -368.2 | 0.3 | -647.7 | -48.6 | 166 | -5.7 | -0.6 |
| squeeze_brk+T | USDJPY | H4 | 0.25 | 2.3 | 251.3 | 0.4 | -435.8 | -42.3 | 204 | 1.9 | 2.9 |
| squeeze_brk+T | XAUUSD | H4 | 0.50 | 3.1 | 338.1 | 0.4 | -578.0 | -89.4 | 197 | 5.2 | 0.6 |
| squeeze_brk+T q=0.15 | GBPJPY | H4 | 0.75 | 12.8 | 1381.5 | 0.3 | -531.5 | -120.1 | 120 | 1.0 | 27.6 |
| squeeze_brk+T q=0.35 | GBPJPY | H4 | 0.25 | 5.8 | 630.4 | 0.5 | -423.8 | -44.8 | 213 | 0.1 | 13.1 |
| squeeze_brk+T n=30 | GBPJPY | H4 | 0.25 | 3.6 | 394.2 | 0.3 | -348.3 | -32.8 | 146 | -2.0 | 10.7 |
| aroon_x+T | US30 | H4 | 0.75 | 20.1 | 2175.7 | 0.5 | -523.8 | -181.0 | 223 | 28.5 | 9.7 |
| ema_x+T | US30 | H4 | 0.25 | 0.9 | 96.3 | 0.2 | -216.7 | -31.3 | 53 | -0.4 | 2.5 |
| aroon_x+T | US500 | H4 | 0.25 | 4.1 | 447.4 | 0.5 | -362.0 | -47.7 | 226 | 1.2 | 7.8 |
| ema_x+T | US500 | H4 | 0.75 | 16.9 | 1823.7 | 0.4 | -519.5 | -125.7 | 115 | 16.3 | 17.7 |
| aroon_x+T | DE40 | H4 | 0.25 | -1.5 | -160.4 | 0.4 | -374.8 | -60.5 | 212 | -1.0 | -2.0 |
| ema_x+T | DE40 | H4 | 0.25 | 0.4 | 48.6 | 0.3 | -373.7 | -36.5 | 121 | 4.5 | -4.6 |
| aroon_x+T n=20 | US30 | H4 | 0.50 | 9.6 | 1034.4 | 0.5 | -533.8 | -99.5 | 230 | 14.2 | 3.8 |
| aroon_x+T n=35 | US30 | H4 | 0.75 | 12.9 | 1397.4 | 0.5 | -526.7 | -160.4 | 172 | 18.7 | 5.7 |
| ema_x+T f=10,s=50 | US500 | H4 | 0.50 | 3.3 | 356.7 | 0.4 | -523.0 | -98.6 | 160 | -1.7 | 9.6 |
| ema_x+T f=20,s=100 | US500 | H4 | 0.50 | 6.7 | 727.2 | 0.4 | -513.3 | -92.5 | 110 | 9.3 | 3.6 |
| dmi_x | XAUUSD | H4 | 0.25 | 1.6 | 171.3 | 0.5 | -392.1 | -46.8 | 439 | -1.8 | 5.8 |
| dmi_x n=10 | XAUUSD | H4 | 0.25 | -0.2 | -21.5 | 0.5 | -590.7 | -53.5 | 751 | -0.6 | 0.2 |
| dmi_x n=20 | XAUUSD | H4 | 0.25 | -2.0 | -216.1 | 0.3 | -530.1 | -36.9 | 218 | -1.8 | -2.2 |
| dmi_x adx=25 | XAUUSD | H4 | 0.50 | 3.3 | 361.6 | 0.5 | -433.0 | -98.7 | 235 | 4.4 | 2.0 |
| dmi_x | XAGUSD | H4 |  | -6.9 | -745.7 | 0.3 | -840.7 | -41.7 | 353 | -8.5 | -4.9 |
| mfi_rev | CHFJPY | H4 | 0.50 | 13.2 | 1425.3 | 0.5 | -433.5 | -90.2 | 236 | 7.2 | 20.7 |
| mfi_rev lo=15 | CHFJPY | H4 | 0.25 | -3.4 | -362.9 | 0.2 | -431.8 | -38.7 | 99 | -3.4 | -3.3 |
| mfi_rev lo=25 | CHFJPY | H4 | 0.25 | 0.2 | 22.5 | 0.5 | -492.2 | -59.3 | 409 | -5.9 | 7.9 |
| kelt_rev | AUDUSD | H4 | 0.50 | 12.8 | 1384.3 | 0.6 | -495.4 | -109.1 | 469 | 7.7 | 19.2 |
| kelt_rev k=1.5 | AUDUSD | H4 |  | -3.0 | -320.9 | 0.5 | -712.6 | -49.2 | 672 | -2.7 | -3.3 |
| kelt_rev k=2.5 | AUDUSD | H4 |  | -3.3 | -355.5 | 0.5 | -623.9 | -46.5 | 284 | -7.7 | 2.2 |
| kelt_rev | NZDUSD | H4 |  | -2.2 | -235.4 | 0.4 | -645.6 | -45.9 | 481 | -6.0 | 2.6 |
| don_brk | GBPJPY | D1 | 1.00 | 19.4 | 2099.0 | 0.5 | -517.0 | -105.9 | 101 | 30.0 | 6.2 |
| don_brk | EURJPY | D1 | 0.25 | -3.2 | -347.7 | 0.4 | -436.1 | -32.5 | 93 | -2.9 | -3.7 |
| don_brk | AUDJPY | D1 | 0.75 | 3.3 | 354.1 | 0.4 | -580.0 | -90.3 | 89 | 4.0 | 2.4 |
| don_brk | CADJPY | D1 | 0.50 | -2.0 | -220.3 | 0.5 | -556.8 | -54.4 | 101 | 1.0 | -5.9 |
| don_brk | NZDJPY | D1 | 1.25 | 2.6 | 278.7 | 0.2 | -514.0 | -127.5 | 25 | 8.8 | -5.1 |
| don_brk | CHFJPY | D1 | 0.25 | -2.9 | -313.2 | 0.4 | -477.2 | -31.4 | 94 | -3.2 | -2.5 |
| don_brk | USDJPY | D1 | 0.50 | 0.3 | 36.8 | 0.5 | -521.8 | -70.2 | 103 | 1.2 | -0.7 |
| don_brk | XAUUSD | D1 | 0.50 | -0.3 | -30.8 | 0.4 | -411.1 | -51.2 | 82 | -2.9 | 3.0 |
| don_brk n=15 | GBPJPY | D1 | 1.00 | 14.6 | 1574.7 | 0.5 | -592.3 | -105.9 | 122 | 25.5 | 0.9 |
| don_brk n=30 | GBPJPY | D1 | 0.50 | 0.6 | 61.9 | 0.4 | -507.0 | -52.9 | 87 | 7.6 | -8.2 |
| squeeze_brk+T | XAUUSD | D1 | 1.00 | 4.9 | 526.7 | 0.2 | -478.0 | -93.8 | 34 | 3.5 | 6.6 |
| squeeze_brk+T | XAGUSD | D1 | 0.50 | -2.5 | -275.4 | 0.1 | -425.3 | -68.8 | 24 | -4.9 | 0.3 |
| squeeze_brk+T | EURUSD | D1 | 0.75 | 1.7 | 186.0 | 0.1 | -518.0 | -75.7 | 24 | 4.1 | -1.3 |
| squeeze_brk+T | GBPUSD | D1 | 0.75 | 3.9 | 415.9 | 0.2 | -408.7 | -94.4 | 29 | 7.0 | -0.1 |
| squeeze_brk+T | USDJPY | D1 | 0.25 | -2.3 | -245.4 | 0.1 | -286.7 | -42.6 | 31 | -1.3 | -3.4 |
| squeeze_brk+T | AUDUSD | D1 | 1.25 | 7.9 | 850.4 | 0.2 | -507.1 | -113.6 | 27 | 12.2 | 2.4 |
| squeeze_brk+T | NZDUSD | D1 | 1.50 | 12.4 | 1339.4 | 0.1 | -482.9 | -148.9 | 31 | 14.9 | 9.3 |
| squeeze_brk+T | USDCAD | D1 | 0.25 | -1.4 | -152.9 | 0.1 | -286.6 | -21.5 | 35 | -1.7 | -1.0 |
| squeeze_brk+T | USDCHF | D1 | 0.50 | -4.0 | -436.1 | 0.1 | -512.3 | -59.7 | 27 | -4.6 | -3.3 |
| squeeze_brk+T | EURJPY | D1 | 0.75 | -0.3 | -37.1 | 0.2 | -527.9 | -140.1 | 30 | 4.9 | -6.9 |
| squeeze_brk+T | GBPJPY | D1 | 1.00 | 8.5 | 920.4 | 0.2 | -466.4 | -105.9 | 26 | 16.5 | -1.4 |
| squeeze_brk+T | AUDJPY | D1 | 1.25 | 3.7 | 403.1 | 0.2 | -554.4 | -150.6 | 26 | 1.8 | 6.2 |
| squeeze_brk+T | CHFJPY | D1 | 0.50 | -3.9 | -421.7 | 0.1 | -545.3 | -59.4 | 22 | -6.0 | -1.3 |
| squeeze_brk+T | NZDJPY | D1 | 1.25 | 7.4 | 795.0 | 0.1 | -307.2 | -127.5 | 13 | 10.8 | 3.0 |
| squeeze_brk+T | CADJPY | D1 | 1.00 | 2.9 | 315.1 | 0.1 | -488.6 | -108.9 | 26 | 4.6 | 0.8 |
| squeeze_brk+T | EURGBP | D1 | 0.75 | -2.3 | -243.6 | 0.1 | -461.1 | -76.9 | 28 | -1.7 | -2.9 |
| squeeze_brk+T | EURCHF | D1 | 2.00 | 26.6 | 2876.4 | 0.2 | -523.8 | -191.2 | 20 | 26.2 | 27.1 |
| squeeze_brk+T | GBPCHF | D1 | 1.00 | 3.6 | 391.2 | 0.2 | -588.7 | -119.9 | 28 | 7.2 | -0.8 |
| squeeze_brk+T | AUDCAD | D1 | 0.50 | -2.6 | -250.1 | 0.1 | -412.3 | -44.0 | 31 | -0.8 | -5.6 |
| squeeze_brk+T | US30 | D1 | 1.50 | 17.4 | 1883.7 | 0.2 | -427.0 | -150.8 | 27 | 23.2 | 10.3 |
| squeeze_brk+T | US500 | D1 | 1.50 | 22.7 | 2456.7 | 0.2 | -532.1 | -171.6 | 26 | 24.6 | 20.4 |
| squeeze_brk+T | DE40 | D1 | 0.75 | 2.6 | 275.5 | 0.2 | -375.8 | -79.4 | 20 | 5.6 | -1.3 |
| kelt_brk hold=96 tp=3.0 hold=96,tp_atr=3.0 | GBPJPY | H4 | 0.50 | 20.2 | 2185.3 | 0.5 | -545.5 | -106.2 | 389 | 16.1 | 25.5 |
| aroon_x+T hold=96 tp=3.0 hold=96,tp_atr=3.0 | US30 | H4 | 0.75 | 18.9 | 2042.5 | 0.5 | -509.4 | -181.0 | 215 | 27.7 | 7.9 |
| kelt_brk hold=48 tp=4.0 hold=48,tp_atr=4.0 | GBPJPY | H4 | 0.25 | 5.5 | 595.1 | 0.5 | -421.1 | -58.7 | 351 | 3.9 | 7.5 |
| aroon_x+T hold=48 tp=4.0 hold=48,tp_atr=4.0 | US30 | H4 | 0.50 | 13.6 | 1471.9 | 0.5 | -462.2 | -142.1 | 201 | 17.6 | 8.6 |
| kelt_brk hold=96 tp=5.0 hold=96,tp_atr=5.0 | GBPJPY | H4 | 0.25 | 6.0 | 650.4 | 0.5 | -280.7 | -58.7 | 318 | 5.9 | 6.2 |
| aroon_x+T hold=96 tp=5.0 hold=96,tp_atr=5.0 | US30 | H4 | 0.25 | 2.3 | 244.9 | 0.3 | -338.0 | -48.2 | 97 | 5.1 | -1.2 |
| aroon_x+T/long | US30 | H4 | 0.75 | 14.9 | 1608.4 | 0.4 | -552.6 | -132.7 | 140 | 18.7 | 10.2 |
| ema_x+T/long | US500 | H4 | 0.75 | 16.9 | 1821.5 | 0.3 | -542.6 | -125.7 | 71 | 17.2 | 16.5 |
| kelt_brk/long | GBPJPY | H4 | 0.25 | 5.2 | 565.7 | 0.4 | -246.8 | -32.5 | 189 | 1.8 | 9.5 |
| aroon_x+T/short | US30 | H4 | 1.00 | 9.4 | 1015.9 | 0.3 | -553.3 | -130.1 | 85 | 12.4 | 5.7 |
| ema_x+T/short | US500 | H4 | 0.50 | -0.1 | -12.6 | 0.2 | -471.5 | -71.8 | 44 | -0.7 | 0.6 |
| kelt_brk/short | GBPJPY | H4 | 0.25 | 3.3 | 353.6 | 0.4 | -290.4 | -37.4 | 198 | 5.2 | 0.9 |

## Table B - rule-level summary of the fast screen (USTEC excluded: data starts 2022-07)

share_both_halves is the key luck check: a zero-edge rule lands positive in both halves about 25% of the time by chance.

| tf | rule | T | symbols | share_net_pos | share_both_halves | median_pf | sum_net_at_1pct |
|---|---|---|---|---|---|---|---|
| D1 | cci_rev |  | 22 | 0.59 | 0.45 | 1.04 | 2086.19 |
| D1 | kelt_rev |  | 22 | 0.64 | 0.41 | 1.05 | 6024.52 |
| D1 | aroon_x | T | 22 | 0.55 | 0.36 | 1.05 | 1845.16 |
| D1 | don_rev |  | 22 | 0.73 | 0.36 | 1.10 | 8718.81 |
| D1 | macd_zero | T | 22 | 0.55 | 0.36 | 1.14 | 771.08 |
| D1 | squeeze_brk |  | 22 | 0.55 | 0.36 | 1.19 | 2980.80 |
| D1 | squeeze_brk | T | 22 | 0.64 | 0.36 | 1.27 | 3984.66 |
| D1 | trend_vote v=5 | T | 22 | 0.50 | 0.36 | 1.10 | 1305.49 |
| D1 | aroon_x |  | 22 | 0.45 | 0.32 | 0.98 | -649.59 |
| D1 | bb_rev |  | 22 | 0.64 | 0.32 | 1.05 | 6490.68 |
| D1 | cci_mom | T | 22 | 0.59 | 0.32 | 1.04 | 2776.60 |
| D1 | ema_slope | T | 22 | 0.64 | 0.32 | 1.10 | 1178.63 |
| D1 | bb_rev | T | 22 | 0.50 | 0.27 | 1.02 | -689.30 |
| D1 | kelt_rev | T | 22 | 0.45 | 0.27 | 0.93 | 581.58 |
| D1 | macd_zero |  | 22 | 0.36 | 0.27 | 0.97 | -5524.29 |
| D1 | trend_vote v=4 | T | 22 | 0.45 | 0.27 | 0.99 | -665.02 |
| D1 | cci_rev | T | 22 | 0.41 | 0.23 | 0.95 | -1422.25 |
| D1 | don_brk |  | 22 | 0.41 | 0.23 | 0.92 | -8024.00 |
| D1 | ha_flip | T | 22 | 0.32 | 0.23 | 0.93 | -2759.26 |
| D1 | macd_x |  | 22 | 0.59 | 0.23 | 1.02 | 3189.43 |
| D1 | mfi_rev |  | 22 | 0.32 | 0.23 | 0.86 | -2363.70 |
| D1 | rsi_rev |  | 22 | 0.55 | 0.23 | 1.03 | -136.74 |
| D1 | willr_rev |  | 22 | 0.55 | 0.23 | 1.02 | -4416.03 |
| D1 | willr_rev | T | 22 | 0.45 | 0.23 | 0.96 | -2446.89 |
| D1 | bb_brk | T | 22 | 0.50 | 0.18 | 1.00 | -1828.49 |
| D1 | don_brk | T | 22 | 0.32 | 0.18 | 0.96 | -2791.95 |
| D1 | don_rev | T | 22 | 0.41 | 0.18 | 0.96 | 164.88 |
| D1 | ema_x |  | 22 | 0.50 | 0.18 | 0.97 | -2195.81 |
| D1 | ema_x | T | 22 | 0.55 | 0.18 | 1.11 | 2242.98 |
| D1 | kelt_brk | T | 22 | 0.55 | 0.18 | 1.01 | 840.95 |
| D1 | mfi_rev | T | 22 | 0.32 | 0.18 | 0.49 | -1540.76 |
| D1 | obv_slope | T | 22 | 0.45 | 0.18 | 0.99 | -217.37 |
| D1 | rsi_mom | T | 22 | 0.50 | 0.18 | 1.02 | -2406.78 |
| D1 | stoch_rev |  | 22 | 0.64 | 0.18 | 1.07 | 7152.28 |
| D1 | stoch_rev | T | 22 | 0.50 | 0.18 | 0.96 | 586.04 |
| D1 | bb_brk |  | 22 | 0.41 | 0.14 | 0.97 | -4686.85 |
| D1 | dmi_x |  | 22 | 0.36 | 0.14 | 0.94 | -4727.85 |
| D1 | dmi_x | T | 22 | 0.50 | 0.14 | 1.01 | -75.26 |
| D1 | ema_slope |  | 22 | 0.41 | 0.14 | 0.96 | -7980.52 |
| D1 | ha_flip |  | 22 | 0.45 | 0.14 | 0.97 | -12275.63 |
| D1 | macd_x | T | 22 | 0.50 | 0.14 | 1.00 | 861.67 |
| D1 | trend_vote v=5 |  | 22 | 0.50 | 0.14 | 0.98 | -4485.72 |
| D1 | trend_vote v=6 | T | 22 | 0.50 | 0.14 | 1.01 | 585.70 |
| D1 | cci_mom |  | 22 | 0.50 | 0.09 | 0.99 | -3501.16 |
| D1 | cmf_zero | T | 22 | 0.55 | 0.09 | 1.01 | -1495.12 |
| D1 | kelt_brk |  | 22 | 0.41 | 0.09 | 0.96 | -2207.69 |
| D1 | obv_slope |  | 22 | 0.14 | 0.09 | 0.91 | -18932.82 |
| D1 | rsi_rev | T | 22 | 0.32 | 0.09 | 0.58 | -1052.47 |
| D1 | trend_vote v=4 |  | 22 | 0.45 | 0.09 | 0.95 | -6789.71 |
| D1 | trend_vote v=6 |  | 22 | 0.45 | 0.09 | 0.94 | -6623.02 |
| D1 | cmf_zero |  | 22 | 0.32 | 0.05 | 0.95 | -10187.23 |
| D1 | rsi_mom |  | 22 | 0.18 | 0.05 | 0.89 | -15894.55 |
| H1 | squeeze_brk | T | 22 | 0.09 | 0.09 | 0.84 | -151088.17 |
| H1 | aroon_x | T | 22 | 0.09 | 0.05 | 0.91 | -162438.49 |
| H1 | macd_zero |  | 22 | 0.05 | 0.05 | 0.83 | -375830.80 |
| H1 | macd_zero | T | 22 | 0.09 | 0.05 | 0.85 | -170018.47 |
| H1 | aroon_x |  | 22 | 0.00 | 0.00 | 0.83 | -399068.85 |
| H1 | bb_brk |  | 22 | 0.00 | 0.00 | 0.81 | -550236.92 |
| H1 | bb_brk | T | 22 | 0.00 | 0.00 | 0.82 | -361001.73 |
| H1 | bb_rev |  | 22 | 0.00 | 0.00 | 0.81 | -627445.72 |
| H1 | bb_rev | T | 22 | 0.09 | 0.00 | 0.84 | -179541.24 |
| H1 | cci_mom |  | 22 | 0.00 | 0.00 | 0.79 | -750309.37 |
| H1 | cci_mom | T | 22 | 0.00 | 0.00 | 0.83 | -420321.84 |
| H1 | cci_rev |  | 22 | 0.00 | 0.00 | 0.74 | -943532.54 |
| H1 | cci_rev | T | 22 | 0.00 | 0.00 | 0.81 | -311019.27 |
| H1 | cmf_zero |  | 22 | 0.00 | 0.00 | 0.77 | -778323.51 |
| H1 | cmf_zero | T | 22 | 0.00 | 0.00 | 0.82 | -399565.30 |
| H1 | dmi_x |  | 22 | 0.00 | 0.00 | 0.74 | -469801.62 |
| H1 | dmi_x | T | 22 | 0.00 | 0.00 | 0.81 | -195685.49 |
| H1 | don_brk |  | 22 | 0.00 | 0.00 | 0.81 | -538989.02 |
| H1 | don_brk | T | 22 | 0.00 | 0.00 | 0.82 | -386302.70 |
| H1 | don_rev |  | 22 | 0.00 | 0.00 | 0.77 | -800213.54 |
| H1 | don_rev | T | 22 | 0.05 | 0.00 | 0.80 | -229011.06 |
| H1 | ema_slope |  | 22 | 0.00 | 0.00 | 0.79 | -562287.54 |
| H1 | ema_slope | T | 22 | 0.00 | 0.00 | 0.84 | -222070.73 |
| H1 | ema_x |  | 22 | 0.00 | 0.00 | 0.86 | -213651.81 |
| H1 | ema_x | T | 22 | 0.00 | 0.00 | 0.87 | -115106.78 |
| H1 | ha_flip |  | 22 | 0.00 | 0.00 | 0.65 | -2136459.75 |
| H1 | ha_flip | T | 22 | 0.00 | 0.00 | 0.81 | -618948.87 |
| H1 | kelt_brk |  | 22 | 0.05 | 0.00 | 0.84 | -302811.57 |
| H1 | kelt_brk | T | 22 | 0.05 | 0.00 | 0.84 | -258593.47 |
| H1 | kelt_rev |  | 22 | 0.00 | 0.00 | 0.83 | -407778.75 |
| H1 | kelt_rev | T | 22 | 0.05 | 0.00 | 0.79 | -88470.25 |
| H1 | macd_x |  | 22 | 0.00 | 0.00 | 0.76 | -1002223.95 |
| H1 | macd_x | T | 22 | 0.00 | 0.00 | 0.81 | -370355.31 |
| H1 | mfi_rev |  | 22 | 0.00 | 0.00 | 0.78 | -297932.23 |
| H1 | mfi_rev | T | 22 | 0.00 | 0.00 | 0.82 | -79776.17 |
| H1 | obv_slope |  | 22 | 0.00 | 0.00 | 0.62 | -2016397.14 |
| H1 | obv_slope | T | 22 | 0.00 | 0.00 | 0.80 | -472438.41 |
| H1 | rsi_mom |  | 22 | 0.00 | 0.00 | 0.65 | -1515201.12 |
| H1 | rsi_mom | T | 22 | 0.00 | 0.00 | 0.81 | -384627.06 |
| H1 | rsi_rev |  | 22 | 0.00 | 0.00 | 0.81 | -316008.20 |
| H1 | rsi_rev | T | 22 | 0.09 | 0.00 | 0.82 | -45987.81 |
| H1 | squeeze_brk |  | 22 | 0.05 | 0.00 | 0.82 | -230390.11 |
| H1 | stoch_rev |  | 22 | 0.00 | 0.00 | 0.78 | -777090.85 |
| H1 | stoch_rev | T | 22 | 0.00 | 0.00 | 0.81 | -238992.64 |
| H1 | willr_rev |  | 22 | 0.00 | 0.00 | 0.72 | -1209131.38 |
| H1 | willr_rev | T | 22 | 0.00 | 0.00 | 0.79 | -397557.12 |
| H4 | kelt_brk |  | 22 | 0.45 | 0.23 | 0.97 | -22221.50 |
| H4 | mfi_rev | T | 22 | 0.32 | 0.23 | 0.92 | -8325.21 |
| H4 | cci_mom | T | 22 | 0.23 | 0.18 | 0.95 | -34698.35 |
| H4 | dmi_x |  | 22 | 0.36 | 0.18 | 0.94 | -27629.66 |
| H4 | don_brk |  | 22 | 0.27 | 0.18 | 0.94 | -45787.07 |
| H4 | don_brk | T | 22 | 0.18 | 0.18 | 0.93 | -39908.74 |
| H4 | kelt_brk | T | 22 | 0.50 | 0.18 | 0.95 | -14246.94 |
| H4 | squeeze_brk | T | 22 | 0.32 | 0.18 | 0.93 | -12313.56 |
| H4 | trend_vote v=5 | T | 22 | 0.18 | 0.18 | 0.90 | -36238.82 |
| H4 | trend_vote v=6 |  | 22 | 0.27 | 0.18 | 0.88 | -49289.10 |
| H4 | aroon_x | T | 22 | 0.23 | 0.14 | 0.93 | -27234.65 |
| H4 | dmi_x | T | 22 | 0.23 | 0.14 | 0.89 | -24955.68 |
| H4 | cci_mom |  | 22 | 0.14 | 0.09 | 0.93 | -61143.11 |
| H4 | cci_rev | T | 22 | 0.23 | 0.09 | 0.86 | -38424.81 |
| H4 | ema_x |  | 22 | 0.27 | 0.09 | 0.90 | -28337.43 |
| H4 | kelt_rev |  | 22 | 0.14 | 0.09 | 0.91 | -52447.06 |
| H4 | macd_zero | T | 22 | 0.23 | 0.09 | 0.91 | -21345.54 |
| H4 | rsi_rev |  | 22 | 0.23 | 0.09 | 0.91 | -35828.58 |
| H4 | rsi_rev | T | 22 | 0.23 | 0.09 | 0.91 | -8021.38 |
| H4 | squeeze_brk |  | 22 | 0.32 | 0.09 | 0.94 | -20410.35 |
| H4 | trend_vote v=4 | T | 22 | 0.14 | 0.09 | 0.91 | -39028.66 |
| H4 | trend_vote v=5 |  | 22 | 0.32 | 0.09 | 0.93 | -38451.92 |
| H4 | trend_vote v=6 | T | 22 | 0.23 | 0.09 | 0.87 | -44001.24 |
| H4 | aroon_x |  | 22 | 0.14 | 0.05 | 0.90 | -66292.69 |
| H4 | bb_brk |  | 22 | 0.18 | 0.05 | 0.95 | -47541.49 |
| H4 | bb_brk | T | 22 | 0.09 | 0.05 | 0.93 | -41672.69 |
| H4 | bb_rev |  | 22 | 0.09 | 0.05 | 0.90 | -81521.34 |
| H4 | bb_rev | T | 22 | 0.14 | 0.05 | 0.89 | -33232.11 |
| H4 | cmf_zero |  | 22 | 0.14 | 0.05 | 0.87 | -99162.85 |
| H4 | ema_slope | T | 22 | 0.09 | 0.05 | 0.86 | -42685.30 |
| H4 | ema_x | T | 22 | 0.32 | 0.05 | 0.89 | -20253.78 |
| H4 | ha_flip | T | 22 | 0.05 | 0.05 | 0.92 | -73670.75 |
| H4 | kelt_rev | T | 22 | 0.14 | 0.05 | 0.87 | -14214.24 |
| H4 | macd_x |  | 22 | 0.05 | 0.05 | 0.87 | -131170.75 |
| H4 | macd_x | T | 22 | 0.27 | 0.05 | 0.91 | -56242.37 |
| H4 | macd_zero |  | 22 | 0.23 | 0.05 | 0.93 | -37973.26 |
| H4 | mfi_rev |  | 22 | 0.09 | 0.05 | 0.91 | -32549.72 |
| H4 | obv_slope |  | 22 | 0.09 | 0.05 | 0.82 | -208952.49 |
| H4 | obv_slope | T | 22 | 0.14 | 0.05 | 0.86 | -69976.48 |
| H4 | stoch_rev | T | 22 | 0.18 | 0.05 | 0.84 | -42131.00 |
| H4 | trend_vote v=4 |  | 22 | 0.09 | 0.05 | 0.89 | -72815.65 |
| H4 | willr_rev | T | 22 | 0.14 | 0.05 | 0.84 | -62508.01 |
| H4 | cci_rev |  | 22 | 0.09 | 0.00 | 0.91 | -81774.28 |
| H4 | cmf_zero | T | 22 | 0.05 | 0.00 | 0.91 | -53604.05 |
| H4 | don_rev |  | 22 | 0.05 | 0.00 | 0.88 | -121059.28 |
| H4 | don_rev | T | 22 | 0.14 | 0.00 | 0.86 | -41161.73 |
| H4 | ema_slope |  | 22 | 0.05 | 0.00 | 0.90 | -71877.53 |
| H4 | ha_flip |  | 22 | 0.00 | 0.00 | 0.84 | -236174.03 |
| H4 | rsi_mom |  | 22 | 0.00 | 0.00 | 0.84 | -164948.02 |
| H4 | rsi_mom | T | 22 | 0.09 | 0.00 | 0.89 | -57314.63 |
| H4 | stoch_rev |  | 22 | 0.00 | 0.00 | 0.88 | -116596.52 |
| H4 | willr_rev |  | 22 | 0.09 | 0.00 | 0.85 | -153530.07 |

## Table C - FULL ranked fast screen (3438 runs, 1% risk sim, best risk estimated by linear scaling; ranked by est_avg_mo)

| sym | tf | rule | T | trades | PF | net@1% | maxDD@1% | worstDay@1% | est_best_risk% | est_avg_mo | 2015-19 $/mo@1% | 2020-23 $/mo@1% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USTEC | H1 | macd_zero |  | 255.0 | 1.2 | 2953.7 | -901.2 | -285.5 | 0.50 | 82.0 | 0.0 | 164.1 |
| USTEC | H4 | mfi_rev | T | 15.0 | 3.1 | 934.3 | -345.2 | -142.2 | 1.50 | 77.9 | 0.0 | 51.9 |
| USTEC | H1 | macd_zero | T | 116.0 | 1.3 | 1814.7 | -704.8 | -261.4 | 0.75 | 75.6 | 0.0 | 100.8 |
| USTEC | H4 | mfi_rev |  | 58.0 | 1.4 | 1013.3 | -438.1 | -136.5 | 1.25 | 70.4 | 0.0 | 56.3 |
| USTEC | D1 | cci_mom | T | 6.0 | 12.3 | 607.1 | -98.1 | -53.3 | 2.00 | 67.5 | 0.0 | 33.7 |
| USTEC | D1 | don_brk | T | 6.0 | inf | 590.1 | -81.7 | -56.9 | 2.00 | 65.6 | 0.0 | 32.8 |
| USTEC | H4 | cci_mom | T | 71.0 | 1.4 | 1156.2 | -562.5 | -142.9 | 1.00 | 64.2 | 0.0 | 64.2 |
| USTEC | H4 | macd_x |  | 164.0 | 1.3 | 2119.5 | -853.8 | -201.0 | 0.50 | 58.9 | 0.0 | 117.8 |
| USTEC | H4 | cci_mom |  | 130.0 | 1.2 | 1344.2 | -763.0 | -196.1 | 0.75 | 56.0 | 0.0 | 74.7 |
| USTEC | H4 | willr_rev | T | 76.0 | 1.3 | 1071.4 | -620.3 | -160.4 | 0.75 | 44.6 | 0.0 | 59.5 |
| USTEC | H4 | obv_slope |  | 302.0 | 1.2 | 1463.7 | -1007.5 | -200.9 | 0.50 | 40.7 | 0.0 | 81.3 |
| USTEC | H4 | stoch_rev |  | 150.0 | 1.1 | 937.8 | -772.9 | -188.4 | 0.75 | 39.1 | 0.0 | 52.1 |
| USTEC | D1 | cci_mom |  | 20.0 | 2.0 | 556.2 | -439.8 | -74.9 | 1.25 | 38.6 | 0.0 | 30.9 |
| USTEC | H4 | ha_flip |  | 347.0 | 1.1 | 1352.2 | -879.6 | -233.8 | 0.50 | 37.6 | 0.0 | 75.1 |
| USTEC | D1 | kelt_brk | T | 5.0 | 5.0 | 333.8 | -147.9 | -77.9 | 2.00 | 37.1 | 0.0 | 18.5 |
| USTEC | D1 | don_brk |  | 15.0 | 2.0 | 405.6 | -326.3 | -78.0 | 1.50 | 33.8 | 0.0 | 22.5 |
| USTEC | H4 | kelt_brk | T | 58.0 | 1.5 | 1214.9 | -808.6 | -143.0 | 0.50 | 33.7 | 0.0 | 67.5 |
| USTEC | H1 | stoch_rev | T | 151.0 | 1.2 | 1210.3 | -827.6 | -190.1 | 0.50 | 33.6 | 0.0 | 67.2 |
| USTEC | D1 | obv_slope | T | 7.0 | 2.3 | 268.3 | -190.2 | -67.5 | 2.00 | 29.8 | 0.0 | 14.9 |
| USTEC | H4 | ema_x | T | 21.0 | 1.4 | 407.5 | -446.6 | -127.8 | 1.25 | 28.3 | 0.0 | 22.6 |
| USTEC | D1 | ha_flip | T | 9.0 | 2.1 | 320.5 | -326.4 | -105.9 | 1.50 | 26.7 | 0.0 | 17.8 |
| USTEC | H1 | mfi_rev | T | 44.0 | 1.3 | 637.5 | -647.1 | -160.2 | 0.75 | 26.6 | 0.0 | 35.4 |
| EURCHF | D1 | squeeze_brk | T | 20.0 | 3.9 | 1426.6 | -252.6 | -95.6 | 2.00 | 26.4 | 12.9 | 13.5 |
| EURUSD | D1 | trend_vote v=5 | T | 53.0 | 1.7 | 1403.4 | -289.8 | -97.0 | 2.00 | 26.0 | 4.2 | 24.0 |
| AUDCAD | D1 | cci_mom | T | 60.0 | 1.6 | 1642.8 | -361.5 | -110.2 | 1.50 | 25.7 | 13.7 | 22.8 |
| USTEC | H1 | ema_slope |  | 312.0 | 1.1 | 1829.5 | -1745.5 | -364.9 | 0.25 | 25.4 | 0.0 | 101.6 |
| USTEC | H4 | don_rev | T | 37.0 | 1.3 | 453.3 | -542.9 | -198.1 | 1.00 | 25.2 | 0.0 | 25.2 |
| USTEC | H4 | aroon_x | T | 40.0 | 1.3 | 582.9 | -731.9 | -144.6 | 0.75 | 24.3 | 0.0 | 32.4 |
| US500 | D1 | squeeze_brk | T | 26.0 | 3.1 | 1618.9 | -354.2 | -111.7 | 1.50 | 22.5 | 16.2 | 13.4 |
| GBPJPY | H4 | trend_vote v=6 |  | 445.0 | 1.2 | 4699.2 | -1079.0 | -208.0 | 0.50 | 21.8 | 37.5 | 51.0 |
| USTEC | H4 | kelt_rev | T | 19.0 | 1.3 | 312.8 | -474.9 | -136.5 | 1.25 | 21.7 | 0.0 | 17.4 |
| CHFJPY | D1 | trend_vote v=5 | T | 48.0 | 1.9 | 1542.0 | -396.0 | -125.4 | 1.50 | 21.4 | 12.5 | 16.5 |
| USTEC | H1 | rsi_mom |  | 800.0 | 1.1 | 1541.2 | -1377.2 | -371.5 | 0.25 | 21.4 | 0.0 | 85.6 |
| USTEC | H1 | kelt_rev |  | 338.0 | 1.1 | 1534.8 | -1698.7 | -268.4 | 0.25 | 21.3 | 0.0 | 85.3 |
| US30 | D1 | squeeze_brk | T | 27.0 | 2.5 | 1147.8 | -275.4 | -100.5 | 2.00 | 21.3 | 15.5 | 4.5 |
| USTEC | H1 | cmf_zero | T | 263.0 | 1.1 | 1516.6 | -1573.2 | -325.0 | 0.25 | 21.1 | 0.0 | 84.3 |
| USTEC | H4 | kelt_brk |  | 83.0 | 1.2 | 751.1 | -1088.7 | -184.8 | 0.50 | 20.9 | 0.0 | 41.7 |
| GBPJPY | H4 | kelt_brk |  | 392.0 | 1.2 | 4498.3 | -1106.4 | -213.7 | 0.50 | 20.8 | 33.4 | 52.0 |
| EURCHF | D1 | squeeze_brk |  | 26.0 | 2.1 | 1090.0 | -269.2 | -111.6 | 2.00 | 20.2 | 13.7 | 5.6 |
| US30 | H4 | aroon_x | T | 226.0 | 1.3 | 2869.8 | -799.0 | -237.5 | 0.75 | 19.9 | 38.6 | 11.5 |
| USDCHF | D1 | kelt_rev |  | 59.0 | 1.7 | 1685.2 | -427.2 | -110.6 | 1.25 | 19.5 | 20.9 | 9.0 |
| GBPJPY | D1 | don_brk |  | 101.0 | 1.5 | 2099.0 | -517.0 | -105.9 | 1.00 | 19.4 | 30.0 | 6.2 |
| USTEC | H4 | rsi_mom |  | 201.0 | 1.1 | 696.2 | -1038.0 | -254.5 | 0.50 | 19.3 | 0.0 | 38.7 |
| EURCHF | D1 | don_rev | T | 30.0 | 2.5 | 1372.4 | -343.3 | -101.0 | 1.50 | 19.1 | 5.2 | 22.1 |
| GBPJPY | D1 | aroon_x |  | 98.0 | 1.7 | 2022.4 | -492.5 | -105.4 | 1.00 | 18.7 | 22.8 | 13.6 |
| USTEC | H4 | bb_rev |  | 117.0 | 1.1 | 671.3 | -1004.3 | -166.8 | 0.50 | 18.6 | 0.0 | 37.3 |
| GBPJPY | H4 | kelt_brk | T | 308.0 | 1.3 | 3977.1 | -1023.9 | -213.7 | 0.50 | 18.4 | 25.0 | 51.6 |
| USTEC | D1 | kelt_brk |  | 13.0 | 1.5 | 217.7 | -394.3 | -77.9 | 1.50 | 18.1 | 0.0 | 12.1 |
| USTEC | D1 | ha_flip |  | 60.0 | 1.3 | 325.4 | -550.4 | -105.9 | 1.00 | 18.1 | 0.0 | 18.1 |
| EURCHF | D1 | stoch_rev | T | 31.0 | 2.3 | 1284.4 | -352.8 | -101.0 | 1.50 | 17.8 | 10.5 | 13.7 |
| USTEC | H4 | stoch_rev | T | 44.0 | 1.1 | 316.7 | -510.6 | -175.6 | 1.00 | 17.6 | 0.0 | 17.6 |
| US500 | H4 | ema_x | T | 115.0 | 1.4 | 2430.5 | -711.5 | -165.9 | 0.75 | 16.9 | 21.6 | 23.6 |
| USDCHF | D1 | rsi_rev |  | 40.0 | 2.0 | 1409.9 | -453.9 | -88.1 | 1.25 | 16.3 | 25.5 | -2.5 |
| USTEC | H4 | bb_rev | T | 38.0 | 1.2 | 289.5 | -529.4 | -155.6 | 1.00 | 16.1 | 0.0 | 16.1 |
| US500 | D1 | squeeze_brk |  | 32.0 | 2.0 | 1275.9 | -452.1 | -111.7 | 1.25 | 14.8 | 11.4 | 12.4 |
| CHFJPY | D1 | cmf_zero | T | 57.0 | 1.5 | 1264.3 | -406.8 | -120.8 | 1.25 | 14.6 | 14.8 | 7.9 |
| USTEC | D1 | kelt_rev | T | 3.0 | 2.4 | 131.5 | -216.6 | -105.9 | 2.00 | 14.6 | 0.0 | 7.3 |
| CHFJPY | D1 | aroon_x | T | 39.0 | 1.7 | 1045.4 | -345.4 | -125.4 | 1.50 | 14.5 | 7.8 | 12.1 |
| GBPCHF | D1 | dmi_x |  | 67.0 | 1.7 | 1234.6 | -412.7 | -118.0 | 1.25 | 14.3 | 17.0 | 4.5 |
| US500 | D1 | obv_slope | T | 83.0 | 1.6 | 2022.4 | -663.3 | -140.1 | 0.75 | 14.0 | 22.0 | 14.6 |
| USTEC | H4 | don_rev |  | 145.0 | 1.1 | 1002.2 | -1350.7 | -231.0 | 0.25 | 13.9 | 0.0 | 55.7 |
| CHFJPY | H4 | mfi_rev |  | 236.0 | 1.3 | 2996.6 | -889.4 | -180.5 | 0.50 | 13.9 | 15.3 | 43.3 |
| EURUSD | D1 | obv_slope | T | 84.0 | 1.4 | 1480.9 | -495.8 | -126.5 | 1.00 | 13.7 | 8.2 | 20.6 |
| NZDJPY | H4 | dmi_x |  | 404.0 | 1.2 | 2979.4 | -954.3 | -203.1 | 0.50 | 13.7 | 38.5 | 13.2 |
| EURGBP | D1 | stoch_rev |  | 133.0 | 1.4 | 1941.2 | -729.9 | -127.4 | 0.75 | 13.5 | 18.7 | 17.1 |
| US30 | H4 | trend_vote v=6 | T | 323.0 | 1.2 | 2886.9 | -975.3 | -199.0 | 0.50 | 13.4 | 38.3 | 12.3 |
| AUDUSD | H4 | kelt_rev |  | 469.0 | 1.1 | 2886.5 | -1050.4 | -218.1 | 0.50 | 13.4 | 16.9 | 39.1 |
| GBPJPY | H4 | trend_vote v=6 | T | 345.0 | 1.2 | 2831.0 | -1010.5 | -188.4 | 0.50 | 13.1 | 37.1 | 12.6 |
| USTEC | D1 | cmf_zero | T | 6.0 | 1.5 | 113.3 | -298.9 | -77.9 | 2.00 | 12.6 | 0.0 | 6.3 |
| EURUSD | D1 | aroon_x | T | 43.0 | 1.6 | 1086.8 | -472.5 | -141.9 | 1.25 | 12.6 | 5.5 | 15.8 |
| USTEC | H4 | macd_zero | T | 37.0 | 1.1 | 225.9 | -521.7 | -132.7 | 1.00 | 12.6 | 0.0 | 12.6 |
| GBPJPY | D1 | macd_x |  | 183.0 | 1.3 | 1801.6 | -714.3 | -125.8 | 0.75 | 12.5 | 14.1 | 19.9 |
| EURCHF | D1 | trend_vote v=4 | T | 40.0 | 1.7 | 1077.6 | -405.4 | -166.6 | 1.25 | 12.5 | 12.7 | 6.5 |
| GBPJPY | D1 | squeeze_brk |  | 34.0 | 1.9 | 1076.6 | -437.9 | -105.9 | 1.25 | 12.5 | 16.0 | 2.4 |
| EURJPY | D1 | bb_rev |  | 112.0 | 1.4 | 1784.5 | -718.4 | -171.9 | 0.75 | 12.4 | 14.8 | 18.6 |
| NZDUSD | D1 | squeeze_brk | T | 31.0 | 1.7 | 886.6 | -325.0 | -96.4 | 1.50 | 12.3 | 10.1 | 5.8 |
| USTEC | D1 | bb_brk | T | 3.0 | 2.3 | 108.6 | -148.2 | -77.9 | 2.00 | 12.1 | 0.0 | 6.0 |
| DE40 | D1 | obv_slope | T | 70.0 | 1.4 | 1017.4 | -429.4 | -148.9 | 1.25 | 11.8 | 9.5 | 9.4 |
| EURJPY | D1 | stoch_rev |  | 138.0 | 1.5 | 2473.0 | -956.9 | -186.6 | 0.50 | 11.4 | 11.5 | 37.2 |
| EURCHF | D1 | bb_brk | T | 50.0 | 1.6 | 1233.6 | -559.5 | -131.6 | 1.00 | 11.4 | 11.2 | 11.7 |
| GBPJPY | D1 | macd_zero |  | 81.0 | 1.3 | 978.9 | -422.7 | -110.3 | 1.25 | 11.3 | 11.0 | 6.6 |
| US500 | D1 | trend_vote v=4 | T | 40.0 | 1.6 | 971.6 | -346.5 | -214.0 | 1.25 | 11.2 | 9.6 | 8.3 |
| USTEC | D1 | macd_x | T | 6.0 | 1.5 | 100.4 | -245.9 | -77.9 | 2.00 | 11.2 | 0.0 | 5.6 |
| DE40 | H4 | dmi_x |  | 419.0 | 1.2 | 2397.4 | -852.2 | -287.3 | 0.50 | 11.1 | 14.1 | 32.4 |
| US500 | D1 | ema_slope | T | 37.0 | 1.5 | 794.7 | -373.4 | -182.3 | 1.50 | 11.0 | 8.9 | 5.4 |
| US500 | D1 | don_brk | T | 75.0 | 1.3 | 1190.7 | -597.7 | -151.5 | 1.00 | 11.0 | 14.8 | 6.3 |
| GBPJPY | D1 | rsi_rev |  | 61.0 | 1.5 | 1188.3 | -529.2 | -113.9 | 1.00 | 11.0 | 8.8 | 13.8 |
| AUDJPY | D1 | don_brk | T | 60.0 | 1.3 | 941.6 | -448.5 | -125.6 | 1.25 | 10.9 | 3.7 | 15.0 |
| USTEC | D1 | dmi_x | T | 4.0 | 1.9 | 96.8 | -107.8 | -50.4 | 2.00 | 10.8 | 0.0 | 5.4 |
| DE40 | D1 | trend_vote v=5 |  | 90.0 | 1.4 | 1153.6 | -558.8 | -98.4 | 1.00 | 10.7 | 11.6 | 9.5 |
| GBPJPY | D1 | squeeze_brk | T | 26.0 | 2.0 | 920.4 | -466.4 | -105.9 | 1.25 | 10.7 | 16.5 | -1.4 |
| AUDJPY | D1 | ema_x |  | 48.0 | 1.6 | 1133.7 | -562.6 | -125.0 | 1.00 | 10.5 | 9.0 | 12.4 |
| USTEC | H4 | rsi_mom | T | 67.0 | 1.1 | 244.9 | -729.9 | -174.7 | 0.75 | 10.2 | 0.0 | 13.6 |
| EURCHF | D1 | ha_flip | T | 84.0 | 1.4 | 1458.3 | -708.1 | -154.9 | 0.75 | 10.1 | 11.6 | 15.8 |
| US500 | D1 | kelt_brk | T | 44.0 | 1.5 | 1072.9 | -486.7 | -119.0 | 1.00 | 9.9 | 8.0 | 12.4 |
| AUDJPY | D1 | ema_slope | T | 36.0 | 1.5 | 715.1 | -301.7 | -93.7 | 1.50 | 9.9 | 6.7 | 6.6 |
| AUDUSD | D1 | squeeze_brk | T | 27.0 | 1.7 | 714.4 | -386.5 | -92.3 | 1.50 | 9.9 | 10.1 | 2.2 |
| USTEC | H4 | macd_zero |  | 83.0 | 1.1 | 356.2 | -1084.7 | -189.0 | 0.50 | 9.9 | 0.0 | 19.8 |
| GBPUSD | D1 | macd_x | T | 67.0 | 1.5 | 1409.8 | -642.0 | -112.6 | 0.75 | 9.8 | 13.6 | 12.3 |
| USTEC | D1 | rsi_mom |  | 36.0 | 1.2 | 117.2 | -378.5 | -83.4 | 1.50 | 9.8 | 0.0 | 6.5 |
| AUDCAD | D1 | ema_x |  | 46.0 | 1.5 | 915.3 | -593.2 | -98.6 | 1.00 | 9.5 | 5.0 | 17.1 |
| EURUSD | D1 | don_rev | T | 36.0 | 1.5 | 821.3 | -413.1 | -128.9 | 1.25 | 9.5 | 7.6 | 7.6 |
| EURCHF | D1 | don_brk | T | 56.0 | 1.4 | 1022.1 | -533.2 | -102.7 | 1.00 | 9.5 | 9.2 | 9.7 |
| EURUSD | D1 | macd_zero | T | 33.0 | 1.5 | 677.7 | -389.7 | -135.1 | 1.50 | 9.4 | -1.1 | 15.5 |
| EURGBP | D1 | bb_rev |  | 101.0 | 1.3 | 1350.4 | -614.2 | -112.9 | 0.75 | 9.4 | 8.6 | 17.4 |
| AUDUSD | H4 | kelt_rev | T | 88.0 | 1.3 | 1348.2 | -694.0 | -154.5 | 0.75 | 9.4 | 9.7 | 15.9 |
| USDCAD | D1 | bb_brk |  | 85.0 | 1.4 | 1335.8 | -781.0 | -133.5 | 0.75 | 9.3 | 15.6 | 8.4 |
| AUDJPY | D1 | squeeze_brk |  | 33.0 | 1.4 | 667.7 | -322.4 | -120.5 | 1.50 | 9.3 | 4.6 | 8.2 |
| USTEC | H1 | rsi_mom | T | 229.0 | 1.1 | 665.0 | -1730.8 | -283.6 | 0.25 | 9.2 | 0.0 | 36.9 |
| US500 | D1 | dmi_x | T | 26.0 | 1.7 | 796.6 | -462.1 | -140.1 | 1.25 | 9.2 | 0.2 | 16.3 |
| CHFJPY | D1 | macd_zero | T | 35.0 | 1.5 | 794.7 | -465.8 | -97.7 | 1.25 | 9.2 | 3.2 | 12.6 |
| AUDUSD | D1 | ema_x | T | 24.0 | 1.9 | 784.3 | -420.5 | -87.8 | 1.25 | 9.1 | 5.9 | 8.9 |
| EURCHF | H4 | mfi_rev | T | 57.0 | 1.4 | 973.3 | -488.0 | -183.9 | 1.00 | 9.0 | 12.1 | 5.2 |
| EURCHF | D1 | cci_rev | T | 39.0 | 1.4 | 648.6 | -399.6 | -158.8 | 1.50 | 9.0 | 6.1 | 5.9 |
| USDJPY | D1 | mfi_rev | T | 5.0 | 13.0 | 482.9 | -117.3 | -74.1 | 2.00 | 8.9 | 2.1 | 7.4 |
| AUDCAD | D1 | ema_x | T | 18.0 | 1.8 | 571.5 | -363.2 | -98.6 | 1.50 | 8.9 | -1.3 | 18.0 |
| CHFJPY | D1 | cmf_zero |  | 114.0 | 1.3 | 1271.9 | -783.3 | -123.0 | 0.75 | 8.8 | 20.2 | 1.2 |
| XAUUSD | D1 | ha_flip |  | 362.0 | 1.3 | 1907.7 | -902.3 | -99.7 | 0.50 | 8.8 | 17.9 | 17.4 |
| AUDUSD | D1 | ha_flip | T | 101.0 | 1.3 | 1264.2 | -698.4 | -153.3 | 0.75 | 8.8 | 12.8 | 10.3 |
| AUDCAD | D1 | cmf_zero | T | 47.0 | 1.4 | 842.5 | -496.7 | -107.0 | 1.00 | 8.8 | 0.5 | 22.6 |
| XAUUSD | D1 | ema_x |  | 56.0 | 1.5 | 940.9 | -539.9 | -80.0 | 1.00 | 8.7 | 12.2 | 4.3 |
| US500 | H4 | rsi_rev | T | 34.0 | 1.5 | 751.9 | -430.3 | -181.4 | 1.25 | 8.7 | 2.7 | 12.3 |
| USTEC | H4 | ema_x |  | 41.0 | 1.1 | 208.5 | -780.2 | -157.7 | 0.75 | 8.7 | 0.0 | 11.6 |
| XAUUSD | D1 | kelt_brk | T | 53.0 | 1.7 | 1250.3 | -636.2 | -102.3 | 0.75 | 8.7 | 7.0 | 17.3 |
| USDCHF | D1 | mfi_rev |  | 31.0 | 1.5 | 624.2 | -357.9 | -91.0 | 1.50 | 8.7 | 1.3 | 11.4 |
| CADJPY | D1 | don_rev |  | 139.0 | 1.3 | 1869.8 | -952.2 | -196.3 | 0.50 | 8.7 | 3.0 | 35.2 |
| USTEC | D1 | dmi_x |  | 16.0 | 1.2 | 77.5 | -201.9 | -57.8 | 2.00 | 8.6 | 0.0 | 4.3 |
| GBPUSD | H4 | ema_x | T | 133.0 | 1.2 | 1231.5 | -688.5 | -275.4 | 0.75 | 8.6 | 21.6 | -1.3 |
| US500 | D1 | trend_vote v=5 | T | 50.0 | 1.4 | 922.6 | -570.9 | -161.8 | 1.00 | 8.5 | 10.6 | 5.9 |
| US500 | D1 | macd_zero | T | 26.0 | 1.5 | 613.0 | -311.7 | -161.8 | 1.50 | 8.5 | 6.2 | 5.1 |
| USTEC | D1 | ema_x | T | 1.0 | inf | 76.4 | -34.0 | -30.1 | 2.00 | 8.5 | 0.0 | 4.2 |
| US30 | D1 | don_brk | T | 67.0 | 1.5 | 1211.1 | -627.0 | -114.7 | 0.75 | 8.4 | 18.3 | 2.3 |
| EURCHF | D1 | kelt_rev | T | 6.0 | 5.8 | 453.1 | -160.4 | -65.8 | 2.00 | 8.4 | 2.0 | 6.9 |
| GBPCHF | D1 | bb_rev |  | 113.0 | 1.3 | 1206.2 | -604.7 | -110.8 | 0.75 | 8.4 | -0.5 | 25.8 |
| USDJPY | D1 | ema_slope | T | 44.0 | 1.5 | 898.3 | -528.0 | -124.3 | 1.00 | 8.3 | 6.4 | 10.7 |
| USDJPY | D1 | macd_zero | T | 33.0 | 1.4 | 597.6 | -317.8 | -124.5 | 1.50 | 8.3 | 4.2 | 7.2 |
| USTEC | H4 | bb_brk | T | 62.0 | 1.1 | 298.5 | -987.9 | -140.2 | 0.50 | 8.3 | 0.0 | 16.6 |
| GBPJPY | D1 | kelt_rev |  | 78.0 | 1.4 | 1187.1 | -600.8 | -113.9 | 0.75 | 8.2 | 2.5 | 21.6 |
| GBPCHF | D1 | mfi_rev | T | 7.0 | 3.7 | 444.0 | -170.3 | -70.5 | 2.00 | 8.2 | 3.3 | 5.2 |
| US500 | H4 | dmi_x | T | 191.0 | 1.2 | 1769.8 | -990.1 | -200.6 | 0.50 | 8.2 | 16.3 | 16.4 |
| GBPUSD | D1 | stoch_rev |  | 139.0 | 1.2 | 1179.0 | -751.3 | -155.0 | 0.75 | 8.2 | 25.8 | -7.7 |
| EURUSD | D1 | willr_rev | T | 65.0 | 1.2 | 706.9 | -460.7 | -128.9 | 1.25 | 8.2 | 7.2 | 5.7 |
| XAUUSD | D1 | trend_vote v=6 | T | 51.0 | 1.5 | 877.4 | -525.7 | -96.8 | 1.00 | 8.1 | 4.7 | 12.4 |
| GBPUSD | D1 | trend_vote v=6 | T | 55.0 | 1.3 | 701.4 | -437.0 | -123.8 | 1.25 | 8.1 | 2.9 | 10.9 |
| USTEC | D1 | macd_x |  | 25.0 | 1.1 | 97.1 | -339.9 | -76.1 | 1.50 | 8.1 | 0.0 | 5.4 |
| US500 | H4 | ema_x |  | 214.0 | 1.2 | 1725.5 | -1155.6 | -198.2 | 0.50 | 8.0 | 12.3 | 20.5 |
| US30 | D1 | willr_rev | T | 46.0 | 1.3 | 570.4 | -385.8 | -125.2 | 1.50 | 7.9 | 7.3 | 2.8 |
| GBPUSD | D1 | don_rev |  | 149.0 | 1.2 | 1136.5 | -622.0 | -147.5 | 0.75 | 7.9 | 14.5 | 5.6 |
| GBPCHF | D1 | rsi_rev | T | 7.0 | 3.4 | 426.2 | -166.2 | -85.8 | 2.00 | 7.9 | 3.1 | 5.0 |
| GBPUSD | D1 | stoch_rev | T | 42.0 | 1.4 | 681.6 | -456.4 | -106.0 | 1.25 | 7.9 | 12.2 | -1.1 |
| EURUSD | D1 | cmf_zero | T | 68.0 | 1.3 | 844.3 | -487.9 | -99.9 | 1.00 | 7.8 | -1.8 | 19.9 |
| US30 | H4 | trend_vote v=6 |  | 410.0 | 1.2 | 3374.8 | -1713.3 | -206.2 | 0.25 | 7.8 | 40.4 | 19.8 |
| EURJPY | D1 | cci_rev |  | 146.0 | 1.3 | 1681.0 | -806.4 | -161.5 | 0.50 | 7.8 | 16.5 | 14.4 |
| US500 | H1 | squeeze_brk | T | 631.0 | 1.1 | 3359.0 | -1592.0 | -250.7 | 0.25 | 7.8 | 28.7 | 34.1 |
| NZDUSD | D1 | squeeze_brk |  | 36.0 | 1.4 | 667.5 | -418.3 | -99.5 | 1.25 | 7.7 | 10.9 | 0.3 |
| US30 | D1 | aroon_x |  | 68.0 | 1.5 | 1108.6 | -619.4 | -80.7 | 0.75 | 7.7 | 4.9 | 16.9 |
| EURCHF | H4 | rsi_rev | T | 36.0 | 1.3 | 550.5 | -341.0 | -100.7 | 1.50 | 7.6 | 9.5 | -0.4 |
| EURJPY | D1 | macd_zero | T | 41.0 | 1.5 | 825.6 | -487.5 | -129.9 | 1.00 | 7.6 | 9.4 | 5.5 |
| US500 | D1 | cci_mom | T | 74.0 | 1.2 | 812.9 | -522.0 | -161.8 | 1.00 | 7.5 | 8.7 | 6.0 |
| CHFJPY | D1 | ema_x | T | 23.0 | 1.4 | 406.4 | -289.6 | -125.7 | 2.00 | 7.5 | 7.8 | -1.3 |
| US30 | H4 | bb_brk |  | 509.0 | 1.1 | 3234.9 | -1842.5 | -184.7 | 0.25 | 7.5 | 43.7 | 12.8 |
| XAGUSD | D1 | kelt_rev |  | 69.0 | 1.4 | 1077.5 | -767.8 | -94.9 | 0.75 | 7.5 | 10.9 | 8.8 |
| NZDJPY | D1 | stoch_rev |  | 3.0 | inf | 402.8 | -111.5 | -32.9 | 2.00 | 7.5 | 4.5 | 2.8 |
| NZDJPY | D1 | cci_rev |  | 3.0 | inf | 402.6 | -123.5 | -63.2 | 2.00 | 7.5 | 4.4 | 2.9 |
| AUDCAD | D1 | trend_vote v=5 | T | 43.0 | 1.3 | 572.2 | -444.5 | -99.2 | 1.25 | 7.5 | -1.3 | 18.1 |
| NZDJPY | D1 | don_rev |  | 3.0 | inf | 400.0 | -111.5 | -32.8 | 2.00 | 7.4 | 4.4 | 2.8 |
| USTEC | H4 | cci_rev | T | 55.0 | 1.1 | 177.6 | -768.6 | -160.4 | 0.75 | 7.4 | 0.0 | 9.9 |
| AUDCAD | H4 | rsi_rev | T | 34.0 | 1.5 | 717.7 | -525.1 | -185.6 | 1.00 | 7.4 | 6.0 | 9.8 |
| AUDJPY | H4 | squeeze_brk | T | 184.0 | 1.2 | 1598.0 | -932.2 | -232.6 | 0.50 | 7.3 | -1.2 | 34.8 |
| EURCHF | D1 | aroon_x | T | 42.0 | 1.6 | 1052.7 | -657.7 | -166.6 | 0.75 | 7.3 | 15.6 | 2.5 |
| XAGUSD | D1 | willr_rev |  | 178.0 | 1.3 | 1577.2 | -824.2 | -116.2 | 0.50 | 7.3 | 14.4 | 14.9 |
| EURGBP | D1 | don_rev |  | 145.0 | 1.3 | 1568.8 | -999.0 | -127.4 | 0.50 | 7.3 | 4.9 | 26.5 |
| GBPJPY | D1 | bb_brk |  | 92.0 | 1.3 | 1043.0 | -799.4 | -118.3 | 0.75 | 7.2 | 22.4 | -6.3 |
| US500 | D1 | macd_x | T | 61.0 | 1.3 | 781.5 | -584.7 | -161.8 | 1.00 | 7.2 | 13.6 | -0.7 |
| USDCHF | D1 | don_rev |  | 143.0 | 1.2 | 1546.0 | -1073.9 | -129.8 | 0.50 | 7.2 | 24.6 | 1.5 |
| USDJPY | D1 | trend_vote v=4 | T | 43.0 | 1.4 | 769.9 | -483.7 | -161.3 | 1.00 | 7.1 | 0.7 | 15.1 |
| CHFJPY | D1 | willr_rev | T | 50.0 | 1.5 | 1026.4 | -698.0 | -168.1 | 0.75 | 7.1 | 11.1 | 7.5 |
| US500 | H4 | cci_rev | T | 285.0 | 1.2 | 3064.9 | -1652.4 | -240.5 | 0.25 | 7.1 | 16.5 | 43.2 |
| GBPJPY | D1 | cci_rev |  | 156.0 | 1.3 | 1526.0 | -891.1 | -113.9 | 0.50 | 7.1 | 7.0 | 23.0 |
| USDJPY | D1 | bb_brk |  | 85.0 | 1.2 | 760.3 | -531.5 | -152.6 | 1.00 | 7.0 | 5.7 | 8.8 |
| US30 | H4 | dmi_x |  | 433.0 | 1.1 | 1515.6 | -1088.2 | -241.6 | 0.50 | 7.0 | -2.5 | 34.7 |
| EURJPY | D1 | don_rev |  | 122.0 | 1.3 | 1512.8 | -1017.3 | -133.1 | 0.50 | 7.0 | 5.1 | 25.2 |
| AUDJPY | D1 | stoch_rev |  | 135.0 | 1.3 | 1512.0 | -879.4 | -104.2 | 0.50 | 7.0 | 28.6 | -4.2 |
| NZDJPY | D1 | obv_slope |  | 7.0 | 9.8 | 376.7 | -111.5 | -63.2 | 2.00 | 7.0 | 3.7 | 3.2 |
| DE40 | H4 | bb_rev |  | 609.0 | 1.1 | 3002.2 | -1574.8 | -282.5 | 0.25 | 6.9 | 3.0 | 58.8 |
| USDJPY | D1 | mfi_rev |  | 29.0 | 1.6 | 738.6 | -566.2 | -153.2 | 1.00 | 6.8 | 6.7 | 7.0 |
| EURUSD | D1 | rsi_mom | T | 58.0 | 1.3 | 738.1 | -535.2 | -141.9 | 1.00 | 6.8 | -3.8 | 20.2 |
| GBPCHF | D1 | cci_rev |  | 149.0 | 1.3 | 1473.8 | -979.4 | -109.1 | 0.50 | 6.8 | 6.0 | 23.2 |
| AUDJPY | D1 | ema_x | T | 23.0 | 1.6 | 587.1 | -427.7 | -125.0 | 1.25 | 6.8 | 7.8 | 2.5 |
| US30 | H4 | bb_brk | T | 347.0 | 1.2 | 2913.2 | -1245.7 | -203.4 | 0.25 | 6.7 | 42.0 | 8.1 |
| US30 | D1 | trend_vote v=6 | T | 39.0 | 1.7 | 968.6 | -653.6 | -114.7 | 0.75 | 6.7 | 15.7 | 0.6 |
| US30 | H4 | trend_vote v=5 |  | 475.0 | 1.1 | 2905.0 | -2364.5 | -237.3 | 0.25 | 6.7 | 10.6 | 47.3 |
| US30 | D1 | trend_vote v=5 | T | 33.0 | 1.5 | 580.8 | -465.7 | -114.7 | 1.25 | 6.7 | 9.8 | -0.1 |
| USTEC | H1 | ema_slope | T | 140.0 | 1.1 | 480.1 | -1401.7 | -225.9 | 0.25 | 6.7 | 0.0 | 26.7 |
| AUDJPY | D1 | rsi_rev |  | 51.0 | 1.4 | 957.5 | -784.7 | -97.8 | 0.75 | 6.6 | 1.2 | 18.4 |
| XAGUSD | D1 | rsi_mom | T | 57.0 | 1.3 | 573.5 | -459.4 | -102.3 | 1.25 | 6.6 | 3.2 | 8.0 |
| EURCHF | D1 | trend_vote v=5 | T | 49.0 | 1.2 | 572.0 | -460.2 | -166.6 | 1.25 | 6.6 | 4.7 | 6.1 |
| AUDCAD | D1 | cci_mom |  | 108.0 | 1.3 | 1262.1 | -895.3 | -110.2 | 0.50 | 6.6 | 13.3 | 12.9 |
| GBPUSD | D1 | don_rev | T | 45.0 | 1.4 | 705.4 | -585.5 | -147.5 | 1.00 | 6.5 | 6.9 | 6.1 |
| USDCAD | H4 | kelt_brk | T | 323.0 | 1.2 | 2821.7 | -2160.6 | -185.4 | 0.25 | 6.5 | 23.2 | 29.8 |
| GBPJPY | D1 | trend_vote v=5 |  | 87.0 | 1.2 | 693.9 | -545.1 | -105.9 | 1.00 | 6.4 | 14.8 | -4.0 |
| GBPJPY | D1 | aroon_x | T | 40.0 | 1.4 | 683.5 | -521.7 | -90.6 | 1.00 | 6.3 | 14.8 | -4.3 |
| XAGUSD | D1 | cci_rev |  | 144.0 | 1.3 | 1359.4 | -1016.7 | -102.3 | 0.50 | 6.3 | 11.4 | 14.1 |
| US30 | H1 | squeeze_brk | T | 664.0 | 1.1 | 2695.6 | -2059.0 | -227.5 | 0.25 | 6.2 | 41.4 | 4.4 |
| AUDUSD | D1 | squeeze_brk |  | 35.0 | 1.3 | 534.9 | -479.8 | -100.2 | 1.25 | 6.2 | 7.2 | 2.1 |
| GBPCHF | D1 | kelt_rev |  | 71.0 | 1.2 | 661.3 | -517.0 | -109.1 | 1.00 | 6.1 | 3.7 | 9.1 |
| US30 | D1 | macd_x |  | 142.0 | 1.2 | 879.5 | -689.1 | -93.6 | 0.75 | 6.1 | 5.4 | 11.6 |
| XAUUSD | D1 | ema_x | T | 23.0 | 1.7 | 527.1 | -439.5 | -80.0 | 1.25 | 6.1 | 7.7 | 1.4 |
| XAUUSD | D1 | squeeze_brk | T | 34.0 | 1.3 | 526.7 | -478.0 | -93.8 | 1.25 | 6.1 | 3.5 | 6.6 |
| AUDUSD | D1 | stoch_rev |  | 145.0 | 1.1 | 877.7 | -784.4 | -221.1 | 0.75 | 6.1 | 16.7 | -2.6 |
| GBPCHF | D1 | don_rev |  | 150.0 | 1.2 | 1307.8 | -1042.0 | -112.4 | 0.50 | 6.1 | -4.7 | 33.1 |
| CHFJPY | D1 | cci_mom | T | 67.0 | 1.2 | 652.0 | -483.8 | -125.2 | 1.00 | 6.0 | 8.2 | 3.3 |
| US30 | H4 | aroon_x |  | 472.0 | 1.1 | 2602.1 | -1747.8 | -247.4 | 0.25 | 6.0 | 25.8 | 21.9 |
| US30 | D1 | kelt_rev | T | 12.0 | 2.2 | 432.6 | -318.4 | -103.9 | 1.50 | 6.0 | 2.0 | 6.5 |
| US30 | H4 | don_brk | T | 417.0 | 1.1 | 2590.3 | -2061.6 | -237.5 | 0.25 | 6.0 | 42.4 | 1.0 |
| US30 | H4 | cci_mom | T | 418.0 | 1.1 | 2565.2 | -1422.7 | -201.2 | 0.25 | 5.9 | 25.1 | 22.0 |
| US30 | D1 | don_brk |  | 92.0 | 1.2 | 854.4 | -797.0 | -114.7 | 0.75 | 5.9 | 10.7 | 4.4 |
| GBPUSD | D1 | squeeze_brk |  | 37.0 | 1.4 | 639.0 | -545.9 | -83.9 | 1.00 | 5.9 | 8.1 | 3.2 |
| EURCHF | D1 | mfi_rev | T | 5.0 | 4.5 | 318.3 | -134.6 | -65.8 | 2.00 | 5.9 | 2.3 | 3.7 |
| USTEC | D1 | bb_brk |  | 13.0 | 1.1 | 70.7 | -390.8 | -78.0 | 1.50 | 5.9 | 0.0 | 3.9 |
| USTEC | D1 | aroon_x | T | 2.0 | 1.6 | 53.0 | -165.9 | -61.9 | 2.00 | 5.9 | 0.0 | 2.9 |
| USDCAD | D1 | trend_vote v=4 |  | 99.0 | 1.2 | 844.6 | -633.8 | -136.7 | 0.75 | 5.9 | 8.0 | 7.6 |
| USTEC | H4 | ha_flip | T | 110.0 | 1.1 | 415.1 | -1275.0 | -187.0 | 0.25 | 5.8 | 0.0 | 23.1 |
| CHFJPY | D1 | kelt_rev | T | 14.0 | 1.5 | 309.0 | -256.0 | -87.6 | 2.00 | 5.7 | 4.3 | 1.1 |
| GBPJPY | D1 | rsi_mom |  | 264.0 | 1.1 | 823.7 | -706.3 | -125.8 | 0.75 | 5.7 | 10.6 | 4.0 |
| AUDUSD | D1 | stoch_rev | T | 42.0 | 1.3 | 616.7 | -545.4 | -95.5 | 1.00 | 5.7 | 7.0 | 4.1 |
| GBPJPY | H4 | squeeze_brk | T | 173.0 | 1.3 | 2458.6 | -1603.6 | -165.2 | 0.25 | 5.7 | -3.6 | 55.8 |
| GBPUSD | D1 | trend_vote v=5 | T | 56.0 | 1.2 | 614.6 | -541.0 | -106.6 | 1.00 | 5.7 | 7.7 | 3.1 |
| GBPCHF | D1 | obv_slope | T | 82.0 | 1.2 | 804.8 | -797.5 | -109.1 | 0.75 | 5.6 | 15.3 | -2.4 |
| EURCHF | D1 | mfi_rev |  | 28.0 | 1.3 | 401.7 | -390.1 | -86.2 | 1.50 | 5.6 | 0.1 | 8.2 |
| EURGBP | D1 | cci_rev |  | 158.0 | 1.2 | 1184.5 | -917.8 | -212.4 | 0.50 | 5.5 | 9.5 | 12.8 |
| AUDJPY | D1 | willr_rev |  | 189.0 | 1.2 | 1184.3 | -908.1 | -104.2 | 0.50 | 5.5 | 17.0 | 3.4 |
| NZDJPY | D1 | willr_rev |  | 3.0 | inf | 294.0 | -111.5 | -32.8 | 2.00 | 5.4 | 4.4 | 0.6 |
| DE40 | H4 | dmi_x | T | 172.0 | 1.1 | 1175.7 | -1028.9 | -199.3 | 0.50 | 5.4 | 7.7 | 14.9 |
| EURJPY | D1 | dmi_x |  | 74.0 | 1.3 | 782.7 | -668.6 | -123.1 | 0.75 | 5.4 | 8.0 | 6.3 |
| NZDUSD | D1 | aroon_x |  | 84.0 | 1.2 | 782.0 | -701.6 | -110.5 | 0.75 | 5.4 | 11.7 | 1.6 |
| GBPUSD | D1 | willr_rev | T | 59.0 | 1.2 | 584.9 | -570.2 | -147.5 | 1.00 | 5.4 | 11.2 | -1.8 |
| GBPCHF | D1 | kelt_rev | T | 14.0 | 1.5 | 290.6 | -277.3 | -109.1 | 2.00 | 5.4 | -1.5 | 7.9 |
| US30 | D1 | kelt_rev |  | 52.0 | 1.4 | 770.3 | -605.5 | -103.9 | 0.75 | 5.3 | 3.4 | 11.8 |
| USDCHF | D1 | kelt_rev | T | 4.0 | 4.0 | 288.5 | -173.9 | -88.3 | 2.00 | 5.3 | 4.1 | 0.9 |
| USDCAD | H4 | mfi_rev | T | 66.0 | 1.4 | 1150.5 | -980.3 | -163.5 | 0.50 | 5.3 | 3.7 | 19.3 |
| DE40 | D1 | willr_rev |  | 194.0 | 1.2 | 1150.0 | -970.7 | -111.1 | 0.50 | 5.3 | 28.3 | -11.4 |
| GBPUSD | D1 | ha_flip | T | 88.0 | 1.2 | 766.3 | -646.3 | -112.0 | 0.75 | 5.3 | 9.4 | 4.2 |
| EURJPY | D1 | cci_rev | T | 44.0 | 1.3 | 573.2 | -526.3 | -149.4 | 1.00 | 5.3 | 8.5 | 1.3 |
| US30 | D1 | squeeze_brk |  | 35.0 | 1.6 | 762.5 | -657.7 | -100.5 | 0.75 | 5.3 | 12.9 | -0.3 |
| GBPCHF | D1 | macd_x | T | 59.0 | 1.3 | 759.8 | -714.7 | -115.2 | 0.75 | 5.3 | 5.4 | 9.0 |
| US30 | D1 | macd_x | T | 43.0 | 1.2 | 452.1 | -467.9 | -101.9 | 1.25 | 5.2 | 3.3 | 5.3 |
| NZDJPY | D1 | ha_flip |  | 6.0 | 5.0 | 282.3 | -115.8 | -54.7 | 2.00 | 5.2 | 4.7 | 0.0 |
| XAUUSD | H4 | dmi_x |  | 483.0 | 1.1 | 2256.7 | -1482.2 | -262.0 | 0.25 | 5.2 | -2.1 | 49.6 |
| NZDUSD | D1 | trend_vote v=4 |  | 115.0 | 1.2 | 746.6 | -688.9 | -110.5 | 0.75 | 5.2 | 15.4 | -3.6 |
| XAUUSD | D1 | cci_mom | T | 76.0 | 1.2 | 559.9 | -578.0 | -92.8 | 1.00 | 5.2 | 1.6 | 9.6 |
| GBPJPY | D1 | cci_mom |  | 126.0 | 1.2 | 1112.0 | -885.7 | -121.9 | 0.50 | 5.1 | 27.3 | -10.9 |
| XAGUSD | D1 | kelt_rev | T | 11.0 | 1.8 | 277.1 | -194.7 | -77.7 | 2.00 | 5.1 | 5.2 | -0.7 |
| US500 | D1 | kelt_rev | T | 20.0 | 1.4 | 368.8 | -358.9 | -106.4 | 1.50 | 5.1 | 3.9 | 2.9 |
| NZDJPY | D1 | bb_rev |  | 2.0 | inf | 276.2 | -111.5 | -32.8 | 2.00 | 5.1 | 2.4 | 2.8 |
| GBPUSD | D1 | ema_slope | T | 41.0 | 1.5 | 735.0 | -620.9 | -106.0 | 0.75 | 5.1 | 8.6 | 4.5 |
| US500 | D1 | ha_flip | T | 100.0 | 1.1 | 734.7 | -762.6 | -178.1 | 0.75 | 5.1 | 9.5 | 3.4 |
| GBPCHF | D1 | willr_rev | T | 53.0 | 1.3 | 733.9 | -760.7 | -109.0 | 0.75 | 5.1 | 8.3 | 4.9 |
| NZDJPY | D1 | kelt_rev |  | 2.0 | inf | 275.2 | -123.3 | -63.1 | 2.00 | 5.1 | 1.2 | 4.2 |
| GBPJPY | D1 | trend_vote v=4 |  | 107.0 | 1.1 | 439.5 | -473.5 | -111.8 | 1.25 | 5.1 | 8.4 | -1.3 |
| CADJPY | D1 | cmf_zero | T | 66.0 | 1.2 | 731.8 | -698.4 | -112.5 | 0.75 | 5.1 | 13.2 | -1.3 |
| US500 | D1 | don_brk |  | 106.0 | 1.1 | 730.8 | -762.0 | -151.5 | 0.75 | 5.1 | 3.3 | 11.1 |
| GBPUSD | D1 | ema_x | T | 14.0 | 1.8 | 437.5 | -434.1 | -106.6 | 1.25 | 5.1 | -0.7 | 9.9 |
| EURCHF | D1 | rsi_rev | T | 3.0 | inf | 271.5 | -119.0 | -65.8 | 2.00 | 5.0 | 0.0 | 5.7 |
| AUDJPY | D1 | macd_zero | T | 36.0 | 1.3 | 432.6 | -422.8 | -124.9 | 1.25 | 5.0 | 3.5 | 4.6 |
| GBPUSD | D1 | bb_rev |  | 110.0 | 1.2 | 1076.0 | -826.3 | -147.5 | 0.50 | 5.0 | 21.9 | -4.9 |
| EURUSD | D1 | mfi_rev |  | 22.0 | 1.6 | 537.3 | -544.5 | -90.8 | 1.00 | 5.0 | 7.0 | 2.4 |
| EURJPY | D1 | ema_slope |  | 110.0 | 1.2 | 715.2 | -641.0 | -132.7 | 0.75 | 5.0 | 2.2 | 12.2 |
| XAUUSD | D1 | trend_vote v=6 |  | 78.0 | 1.2 | 710.9 | -799.8 | -96.8 | 0.75 | 4.9 | 0.6 | 14.1 |
| EURJPY | D1 | ha_flip |  | 365.0 | 1.1 | 1065.9 | -1176.3 | -146.7 | 0.50 | 4.9 | 2.1 | 19.6 |
| EURUSD | D1 | obv_slope |  | 430.0 | 1.1 | 704.7 | -731.4 | -144.8 | 0.75 | 4.9 | 3.0 | 11.0 |
| USTEC | H4 | aroon_x |  | 83.0 | 1.0 | 175.5 | -978.7 | -166.7 | 0.50 | 4.9 | 0.0 | 9.8 |
| CHFJPY | H4 | mfi_rev | T | 69.0 | 1.3 | 1052.2 | -927.0 | -180.5 | 0.50 | 4.9 | -0.8 | 22.9 |
| NZDJPY | D1 | cmf_zero |  | 3.0 | 24.9 | 262.4 | -63.0 | -40.3 | 2.00 | 4.9 | 4.4 | 0.0 |
| DE40 | D1 | don_rev |  | 129.0 | 1.2 | 1048.4 | -825.1 | -151.7 | 0.50 | 4.9 | 11.6 | 7.4 |
| US30 | H4 | don_brk |  | 569.0 | 1.1 | 2094.3 | -1886.2 | -207.2 | 0.25 | 4.8 | 32.2 | 3.3 |
| AUDUSD | D1 | cmf_zero | T | 65.0 | 1.2 | 522.7 | -584.3 | -109.5 | 1.00 | 4.8 | 12.1 | -4.2 |
| DE40 | H4 | trend_vote v=6 |  | 416.0 | 1.1 | 2089.4 | -2047.5 | -311.3 | 0.25 | 4.8 | 18.1 | 20.9 |
| US30 | H4 | kelt_brk |  | 391.0 | 1.1 | 2086.8 | -1489.2 | -237.5 | 0.25 | 4.8 | 28.8 | 7.5 |
| USDCAD | H4 | stoch_rev | T | 260.0 | 1.1 | 1042.9 | -1128.4 | -164.8 | 0.50 | 4.8 | -7.6 | 31.3 |
| US500 | D1 | aroon_x |  | 81.0 | 1.2 | 694.5 | -678.6 | -121.9 | 0.75 | 4.8 | 9.1 | 3.1 |
| DE40 | D1 | obv_slope |  | 380.0 | 1.2 | 1036.9 | -873.6 | -148.9 | 0.50 | 4.8 | -3.5 | 26.0 |
| USTEC | H4 | cmf_zero | T | 77.0 | 1.0 | 172.3 | -1083.9 | -148.0 | 0.50 | 4.8 | 0.0 | 9.6 |
| XAGUSD | D1 | stoch_rev |  | 128.0 | 1.2 | 1028.2 | -1108.6 | -94.9 | 0.50 | 4.8 | 20.3 | -4.0 |
| XAUUSD | D1 | squeeze_brk |  | 39.0 | 1.3 | 513.9 | -482.9 | -93.8 | 1.00 | 4.8 | 5.0 | 4.4 |
| GBPUSD | H4 | macd_zero |  | 490.0 | 1.1 | 2050.5 | -2179.7 | -282.6 | 0.25 | 4.7 | 26.1 | 10.0 |
| GBPJPY | D1 | stoch_rev |  | 147.0 | 1.1 | 679.5 | -776.1 | -107.1 | 0.75 | 4.7 | 5.3 | 7.5 |
| AUDJPY | D1 | kelt_brk | T | 47.0 | 1.2 | 406.4 | -468.8 | -93.5 | 1.25 | 4.7 | 1.7 | 6.3 |
| EURCHF | H4 | kelt_rev | T | 65.0 | 1.2 | 671.7 | -623.2 | -132.0 | 0.75 | 4.7 | 13.2 | -2.5 |
| US500 | D1 | bb_rev | T | 33.0 | 1.2 | 400.1 | -479.1 | -108.4 | 1.25 | 4.6 | 4.4 | 2.9 |
| USDJPY | D1 | kelt_rev |  | 76.0 | 1.2 | 663.9 | -774.1 | -142.7 | 0.75 | 4.6 | 12.4 | -1.7 |
| XAUUSD | D1 | bb_rev |  | 110.0 | 1.1 | 663.2 | -688.7 | -107.0 | 0.75 | 4.6 | 13.5 | -3.1 |
| DE40 | D1 | ema_x | T | 21.0 | 1.4 | 329.9 | -376.5 | -74.5 | 1.50 | 4.6 | -2.8 | 10.4 |
| AUDCAD | D1 | mfi_rev | T | 5.0 | 2.2 | 218.6 | -131.5 | -66.4 | 2.00 | 4.6 | -1.6 | 8.7 |
| US30 | D1 | rsi_mom | T | 48.0 | 1.3 | 491.5 | -483.2 | -149.7 | 1.00 | 4.6 | 7.5 | 0.9 |
| EURGBP | D1 | kelt_brk |  | 51.0 | 1.2 | 489.1 | -549.5 | -110.5 | 1.00 | 4.5 | 10.9 | -3.5 |
| GBPUSD | D1 | bb_brk | T | 60.0 | 1.2 | 651.6 | -669.6 | -125.9 | 0.75 | 4.5 | 1.1 | 12.3 |
| CHFJPY | H4 | dmi_x |  | 447.0 | 1.1 | 1940.5 | -1258.1 | -198.8 | 0.25 | 4.5 | 17.9 | 18.0 |
| AUDJPY | H4 | squeeze_brk |  | 237.0 | 1.1 | 973.6 | -1123.5 | -232.6 | 0.50 | 4.5 | -0.9 | 21.4 |
| AUDUSD | D1 | macd_zero |  | 88.0 | 1.1 | 481.3 | -578.3 | -127.7 | 1.00 | 4.5 | 5.1 | 3.6 |
| USDCAD | D1 | rsi_rev |  | 45.0 | 1.2 | 481.1 | -524.4 | -86.3 | 1.00 | 4.5 | 6.8 | 1.5 |
| AUDCAD | D1 | macd_zero | T | 24.0 | 1.2 | 284.8 | -329.8 | -115.2 | 1.50 | 4.4 | 3.8 | 1.5 |
| AUDJPY | D1 | kelt_rev | T | 13.0 | 1.6 | 318.2 | -302.1 | -88.7 | 1.50 | 4.4 | 3.3 | 2.5 |
| XAUUSD | D1 | bb_brk |  | 92.0 | 1.2 | 634.1 | -771.4 | -93.8 | 0.75 | 4.4 | -5.9 | 20.6 |
| EURCHF | D1 | ema_x | T | 28.0 | 1.4 | 474.3 | -508.8 | -166.6 | 1.00 | 4.4 | 1.4 | 8.2 |
| GBPUSD | D1 | obv_slope | T | 78.0 | 1.3 | 945.4 | -859.5 | -123.8 | 0.50 | 4.4 | 17.9 | -2.6 |
| CHFJPY | D1 | trend_vote v=6 | T | 49.0 | 1.3 | 630.3 | -652.0 | -125.7 | 0.75 | 4.4 | 12.1 | -2.1 |
| GBPCHF | D1 | ha_flip | T | 90.0 | 1.2 | 942.3 | -931.3 | -122.9 | 0.50 | 4.4 | 17.0 | -1.7 |
| US500 | H4 | ema_slope | T | 222.0 | 1.2 | 1884.5 | -1451.3 | -193.1 | 0.25 | 4.4 | 6.9 | 30.6 |
| US500 | H4 | aroon_x | T | 226.0 | 1.2 | 1862.3 | -1482.2 | -197.8 | 0.25 | 4.3 | 5.6 | 31.8 |
| AUDCAD | D1 | rsi_mom | T | 57.0 | 1.2 | 549.1 | -615.4 | -98.7 | 0.75 | 4.3 | -6.1 | 25.4 |
| USDJPY | H4 | ema_slope | T | 269.0 | 1.1 | 1845.0 | -1607.9 | -281.0 | 0.25 | 4.3 | 39.4 | -10.8 |
| USTEC | H4 | dmi_x |  | 91.0 | 1.0 | 153.5 | -983.3 | -191.6 | 0.50 | 4.3 | 0.0 | 8.5 |
| GBPCHF | D1 | kelt_brk | T | 37.0 | 1.3 | 458.2 | -495.1 | -121.1 | 1.00 | 4.2 | -1.9 | 11.9 |
| USTEC | H1 | squeeze_brk | T | 125.0 | 1.0 | 305.4 | -1477.2 | -215.0 | 0.25 | 4.2 | 0.0 | 17.0 |
| EURJPY | D1 | ema_slope | T | 48.0 | 1.3 | 608.2 | -682.5 | -132.7 | 0.75 | 4.2 | 9.1 | 1.3 |
| XAUUSD | D1 | kelt_brk |  | 67.0 | 1.3 | 907.9 | -1114.0 | -93.8 | 0.50 | 4.2 | -5.9 | 26.3 |
| CHFJPY | D1 | cci_rev | T | 47.0 | 1.3 | 604.3 | -740.7 | -153.2 | 0.75 | 4.2 | 11.8 | -2.1 |
| US30 | H4 | squeeze_brk | T | 173.0 | 1.2 | 1805.4 | -1411.5 | -160.1 | 0.25 | 4.2 | 26.6 | 4.4 |
| GBPCHF | D1 | cci_rev | T | 45.0 | 1.3 | 601.4 | -742.6 | -109.1 | 0.75 | 4.2 | 1.2 | 11.1 |
| USDJPY | D1 | trend_vote v=5 | T | 60.0 | 1.2 | 600.6 | -683.2 | -161.3 | 0.75 | 4.2 | 2.4 | 9.5 |
| GBPUSD | H4 | trend_vote v=5 | T | 340.0 | 1.1 | 1799.0 | -1665.5 | -196.0 | 0.25 | 4.2 | 3.2 | 33.5 |
| EURCHF | D1 | bb_rev | T | 27.0 | 1.5 | 597.0 | -653.9 | -158.8 | 0.75 | 4.1 | 4.3 | 7.0 |
| EURCHF | D1 | cci_mom | T | 63.0 | 1.3 | 889.7 | -811.8 | -138.8 | 0.50 | 4.1 | 16.7 | -2.3 |
| US30 | D1 | ema_x | T | 14.0 | 1.7 | 296.3 | -368.5 | -114.7 | 1.50 | 4.1 | 5.5 | -0.6 |
| USDCHF | D1 | bb_rev |  | 99.0 | 1.2 | 889.0 | -1196.0 | -124.4 | 0.50 | 4.1 | 12.1 | 3.4 |
| US30 | H4 | trend_vote v=5 | T | 299.0 | 1.1 | 1767.2 | -1409.5 | -237.3 | 0.25 | 4.1 | 16.6 | 16.0 |
| USTEC | D1 | bb_rev | T | 4.0 | 1.2 | 36.7 | -188.6 | -105.9 | 2.00 | 4.1 | 0.0 | 2.0 |
| GBPCHF | D1 | cci_mom | T | 69.0 | 1.2 | 583.1 | -699.1 | -121.1 | 0.75 | 4.0 | 6.9 | 3.6 |
| XAUUSD | D1 | macd_zero |  | 81.0 | 1.2 | 582.2 | -600.7 | -92.0 | 0.75 | 4.0 | 1.7 | 10.0 |
| EURCHF | D1 | kelt_brk | T | 32.0 | 1.3 | 436.4 | -573.4 | -131.6 | 1.00 | 4.0 | 1.9 | 6.8 |
| US500 | H4 | bb_rev | T | 192.0 | 1.2 | 1742.6 | -1242.7 | -260.1 | 0.25 | 4.0 | 24.7 | 5.5 |
| GBPCHF | D1 | stoch_rev | T | 38.0 | 1.4 | 579.6 | -667.8 | -90.4 | 0.75 | 4.0 | -5.4 | 18.9 |
| NZDJPY | D1 | macd_x |  | 5.0 | 5.2 | 216.9 | -111.5 | -46.5 | 2.00 | 4.0 | 3.6 | 0.0 |
| EURUSD | H4 | aroon_x | T | 264.0 | 1.1 | 1731.4 | -2195.5 | -217.8 | 0.25 | 4.0 | 5.3 | 29.4 |
| USDCHF | D1 | cci_rev |  | 163.0 | 1.1 | 864.4 | -1152.1 | -124.6 | 0.50 | 4.0 | 13.3 | 1.4 |
| XAGUSD | D1 | bb_rev |  | 109.0 | 1.2 | 862.1 | -943.4 | -98.8 | 0.50 | 4.0 | 12.9 | 1.8 |
| EURJPY | D1 | dmi_x | T | 33.0 | 1.3 | 430.3 | -498.8 | -113.5 | 1.00 | 4.0 | 4.5 | 3.4 |
| EURUSD | D1 | macd_x | T | 61.0 | 1.1 | 429.6 | -533.4 | -125.4 | 1.00 | 4.0 | -1.1 | 10.3 |
| GBPUSD | H4 | macd_zero | T | 230.0 | 1.1 | 1713.0 | -1356.3 | -196.0 | 0.25 | 4.0 | 13.7 | 18.6 |
| AUDJPY | D1 | don_rev |  | 131.0 | 1.1 | 852.6 | -1034.0 | -104.2 | 0.50 | 3.9 | 21.0 | -8.5 |
| USTEC | D1 | don_rev | T | 4.0 | 1.2 | 35.4 | -198.4 | -105.9 | 2.00 | 3.9 | 0.0 | 2.0 |
| AUDUSD | D1 | ema_x |  | 48.0 | 1.2 | 421.7 | -520.4 | -92.9 | 1.00 | 3.9 | -5.2 | 15.2 |
| EURJPY | D1 | kelt_rev |  | 70.0 | 1.3 | 833.4 | -883.8 | -165.8 | 0.50 | 3.9 | 0.5 | 16.8 |
| US30 | D1 | trend_vote v=6 |  | 56.0 | 1.4 | 833.0 | -914.0 | -114.7 | 0.50 | 3.9 | 16.1 | -2.8 |
| US500 | H4 | macd_zero | T | 198.0 | 1.2 | 1659.3 | -2030.6 | -200.6 | 0.25 | 3.8 | -1.6 | 36.6 |
| AUDJPY | D1 | bb_brk | T | 56.0 | 1.2 | 550.7 | -775.9 | -125.6 | 0.75 | 3.8 | -1.9 | 13.8 |
| GBPUSD | D1 | squeeze_brk | T | 29.0 | 1.4 | 545.4 | -641.8 | -125.9 | 0.75 | 3.8 | 9.4 | -0.4 |
| USDCHF | H4 | ema_x |  | 256.0 | 1.1 | 1635.3 | -1529.3 | -174.7 | 0.25 | 3.8 | 30.7 | -4.3 |
| US30 | D1 | rsi_rev | T | 7.0 | 2.1 | 272.5 | -310.5 | -97.0 | 1.50 | 3.8 | -2.1 | 8.3 |
| CHFJPY | D1 | obv_slope | T | 81.0 | 1.2 | 812.9 | -1137.7 | -127.8 | 0.50 | 3.8 | 2.1 | 14.3 |
| AUDCAD | D1 | trend_vote v=6 | T | 54.0 | 1.1 | 361.0 | -590.6 | -99.2 | 1.00 | 3.8 | -5.2 | 18.6 |
| AUDJPY | D1 | stoch_rev | T | 37.0 | 1.2 | 406.0 | -526.8 | -92.8 | 1.00 | 3.8 | 11.0 | -5.3 |
| NZDUSD | D1 | ema_x |  | 48.0 | 1.2 | 535.9 | -757.1 | -96.4 | 0.75 | 3.7 | 5.3 | 4.6 |
| GBPJPY | D1 | don_brk | T | 73.0 | 1.2 | 535.3 | -640.6 | -105.9 | 0.75 | 3.7 | 15.4 | -8.1 |
| CADJPY | D1 | cci_rev |  | 157.0 | 1.1 | 534.2 | -696.0 | -144.2 | 0.75 | 3.7 | -3.2 | 15.1 |
| USDCAD | H4 | don_rev | T | 254.0 | 1.1 | 1593.2 | -1250.1 | -175.8 | 0.25 | 3.7 | -0.7 | 34.1 |
| XAGUSD | D1 | mfi_rev |  | 30.0 | 1.4 | 398.3 | -589.4 | -86.9 | 1.00 | 3.7 | 6.2 | 0.5 |
| EURUSD | D1 | ha_flip | T | 91.0 | 1.1 | 529.6 | -720.9 | -124.7 | 0.75 | 3.7 | -0.1 | 11.1 |
| NZDUSD | D1 | bb_brk |  | 84.0 | 1.1 | 528.1 | -639.4 | -99.5 | 0.75 | 3.7 | 5.1 | 4.6 |
| NZDUSD | D1 | stoch_rev |  | 149.0 | 1.1 | 789.9 | -814.5 | -192.2 | 0.50 | 3.7 | 18.0 | -6.1 |
| NZDUSD | D1 | trend_vote v=6 | T | 60.0 | 1.2 | 524.6 | -753.8 | -107.7 | 0.75 | 3.6 | 14.0 | -6.6 |
| GBPCHF | D1 | squeeze_brk | T | 28.0 | 1.3 | 391.2 | -588.7 | -119.9 | 1.00 | 3.6 | 7.2 | -0.8 |
| AUDCAD | H4 | mfi_rev | T | 47.0 | 1.2 | 467.7 | -670.2 | -155.8 | 0.75 | 3.6 | -0.5 | 13.9 |
| AUDJPY | D1 | squeeze_brk | T | 26.0 | 1.2 | 312.4 | -441.3 | -120.5 | 1.25 | 3.6 | 1.5 | 4.7 |
| NZDJPY | H4 | kelt_brk | T | 280.0 | 1.1 | 786.6 | -1192.1 | -175.8 | 0.50 | 3.6 | 21.6 | -11.1 |
| US30 | D1 | trend_vote v=4 | T | 36.0 | 1.2 | 311.2 | -468.1 | -114.7 | 1.25 | 3.6 | 4.5 | 0.9 |
| US30 | H4 | cci_mom |  | 692.0 | 1.0 | 1543.9 | -1896.8 | -224.8 | 0.25 | 3.6 | 3.3 | 28.1 |
| USDCAD | D1 | macd_zero |  | 81.0 | 1.2 | 513.3 | -669.5 | -106.3 | 0.75 | 3.6 | 0.2 | 10.5 |
| AUDUSD | D1 | ema_slope | T | 43.0 | 1.2 | 384.2 | -509.1 | -153.3 | 1.00 | 3.6 | 2.5 | 4.9 |
| USDJPY | D1 | aroon_x | T | 39.0 | 1.1 | 254.6 | -394.3 | -197.9 | 1.50 | 3.5 | 2.1 | 2.6 |
| GBPCHF | D1 | rsi_rev |  | 55.0 | 1.1 | 304.9 | -443.8 | -105.4 | 1.25 | 3.5 | 2.8 | 2.8 |
| AUDJPY | D1 | cmf_zero | T | 59.0 | 1.2 | 506.9 | -635.8 | -100.0 | 0.75 | 3.5 | -6.2 | 18.3 |
| EURUSD | D1 | trend_vote v=4 | T | 47.0 | 1.1 | 300.6 | -456.0 | -152.1 | 1.25 | 3.5 | 2.7 | 2.9 |
| AUDJPY | D1 | don_brk |  | 89.0 | 1.1 | 497.5 | -766.3 | -120.5 | 0.75 | 3.5 | 5.3 | 3.8 |
| AUDCAD | D1 | obv_slope | T | 63.0 | 1.1 | 441.0 | -659.0 | -90.6 | 0.75 | 3.4 | -4.7 | 20.0 |
| NZDUSD | D1 | ha_flip | T | 106.0 | 1.1 | 495.5 | -787.8 | -110.0 | 0.75 | 3.4 | 6.5 | 2.2 |
| GBPCHF | D1 | stoch_rev |  | 141.0 | 1.1 | 738.8 | -1100.8 | -102.5 | 0.50 | 3.4 | -6.4 | 23.4 |
| US500 | H4 | don_brk | T | 407.0 | 1.1 | 1473.5 | -2125.5 | -220.2 | 0.25 | 3.4 | 4.5 | 25.1 |
| GBPUSD | H4 | kelt_brk |  | 404.0 | 1.1 | 1466.3 | -2101.6 | -209.3 | 0.25 | 3.4 | 47.6 | -28.9 |
| US30 | H4 | dmi_x | T | 182.0 | 1.2 | 1463.3 | -1269.8 | -223.5 | 0.25 | 3.4 | 23.2 | 1.5 |
| GBPJPY | D1 | ha_flip |  | 382.0 | 1.1 | 730.6 | -922.1 | -118.3 | 0.50 | 3.4 | 18.9 | -8.4 |
| GBPJPY | H4 | squeeze_brk |  | 235.0 | 1.1 | 1452.5 | -1678.3 | -165.2 | 0.25 | 3.4 | -4.6 | 36.0 |
| AUDJPY | D1 | macd_x |  | 186.0 | 1.1 | 724.8 | -1134.0 | -102.0 | 0.50 | 3.4 | -0.3 | 15.5 |
| GBPUSD | H4 | trend_vote v=5 |  | 569.0 | 1.1 | 1449.5 | -2156.7 | -319.3 | 0.25 | 3.4 | 34.0 | -12.3 |
| GBPJPY | H1 | kelt_rev | T | 373.0 | 1.0 | 726.8 | -1144.4 | -338.7 | 0.50 | 3.3 | 22.1 | -12.9 |
| AUDCAD | D1 | aroon_x | T | 30.0 | 1.2 | 318.5 | -499.6 | -107.9 | 1.00 | 3.3 | 3.5 | 3.0 |
| USDJPY | H4 | squeeze_brk |  | 258.0 | 1.1 | 1429.0 | -1590.9 | -180.0 | 0.25 | 3.3 | 19.4 | 5.6 |
| CADJPY | D1 | stoch_rev | T | 43.0 | 1.2 | 475.6 | -752.4 | -95.3 | 0.75 | 3.3 | 1.3 | 8.3 |
| DE40 | D1 | trend_vote v=5 | T | 55.0 | 1.1 | 237.8 | -384.2 | -98.4 | 1.50 | 3.3 | 3.3 | 0.8 |
| GBPJPY | D1 | cci_rev | T | 47.0 | 1.1 | 283.0 | -465.2 | -101.2 | 1.25 | 3.3 | 1.5 | 4.0 |
| AUDJPY | H4 | kelt_brk | T | 302.0 | 1.1 | 1426.1 | -2123.0 | -238.8 | 0.25 | 3.3 | 4.2 | 24.3 |
| EURJPY | D1 | aroon_x | T | 49.0 | 1.1 | 351.1 | -530.0 | -129.9 | 1.00 | 3.3 | 0.6 | 6.6 |
| AUDJPY | H4 | don_brk | T | 451.0 | 1.1 | 1415.8 | -1622.4 | -249.1 | 0.25 | 3.2 | 2.0 | 26.9 |
| US500 | H4 | willr_rev | T | 348.0 | 1.1 | 1393.4 | -2059.4 | -268.7 | 0.25 | 3.2 | 5.2 | 22.6 |
| GBPUSD | D1 | trend_vote v=6 |  | 79.0 | 1.1 | 464.0 | -701.5 | -168.8 | 0.75 | 3.2 | -0.4 | 10.1 |
| CHFJPY | D1 | aroon_x |  | 82.0 | 1.2 | 694.8 | -811.3 | -125.4 | 0.50 | 3.2 | 3.0 | 10.7 |
| AUDJPY | D1 | rsi_rev | T | 5.0 | 1.9 | 173.3 | -262.6 | -89.0 | 2.00 | 3.2 | 3.8 | -1.2 |
| GBPJPY | D1 | ema_slope |  | 126.0 | 1.1 | 458.1 | -643.2 | -125.8 | 0.75 | 3.2 | 5.9 | 2.2 |
| GBPJPY | H4 | ema_x |  | 257.0 | 1.1 | 1371.2 | -1736.5 | -208.0 | 0.25 | 3.2 | 7.9 | 18.6 |
| XAUUSD | D1 | dmi_x | T | 28.0 | 1.3 | 341.1 | -572.0 | -92.1 | 1.00 | 3.2 | -1.4 | 8.8 |
| XAUUSD | D1 | dmi_x |  | 73.0 | 1.3 | 677.4 | -824.6 | -92.1 | 0.50 | 3.1 | 0.3 | 13.7 |
| GBPUSD | H4 | ema_x |  | 258.0 | 1.1 | 1354.7 | -1461.4 | -275.4 | 0.25 | 3.1 | 32.7 | -12.6 |
| AUDUSD | D1 | rsi_rev | T | 2.0 | inf | 169.2 | -176.9 | -55.0 | 2.00 | 3.1 | 0.6 | 2.8 |
| US500 | H4 | trend_vote v=4 | T | 262.0 | 1.1 | 1351.8 | -1770.3 | -206.1 | 0.25 | 3.1 | 9.7 | 16.1 |
| GBPUSD | D1 | mfi_rev |  | 29.0 | 1.2 | 224.6 | -343.6 | -92.3 | 1.50 | 3.1 | -1.3 | 6.4 |
| CADJPY | D1 | don_rev | T | 46.0 | 1.3 | 672.8 | -928.0 | -116.4 | 0.50 | 3.1 | 1.9 | 11.6 |
| AUDCAD | D1 | ema_slope | T | 29.0 | 1.2 | 238.0 | -454.5 | -98.7 | 1.25 | 3.1 | -2.5 | 10.8 |
| CADJPY | D1 | bb_rev |  | 117.0 | 1.1 | 667.1 | -909.9 | -166.3 | 0.50 | 3.1 | 0.7 | 13.1 |
| USDJPY | H4 | cci_mom |  | 766.0 | 1.0 | 1332.2 | -1673.1 | -209.7 | 0.25 | 3.1 | 11.3 | 13.6 |
| AUDUSD | H4 | cci_rev | T | 325.0 | 1.1 | 1316.4 | -1964.1 | -208.8 | 0.25 | 3.0 | -12.6 | 43.2 |
| GBPJPY | D1 | don_rev |  | 152.0 | 1.1 | 653.7 | -834.4 | -114.4 | 0.50 | 3.0 | -3.1 | 17.5 |
| CADJPY | D1 | kelt_brk |  | 62.0 | 1.1 | 435.0 | -732.9 | -105.2 | 0.75 | 3.0 | 5.2 | 2.6 |
| USDJPY | D1 | don_rev |  | 144.0 | 1.1 | 651.1 | -1117.7 | -142.7 | 0.50 | 3.0 | 25.1 | -17.8 |
| XAUUSD | D1 | bb_brk | T | 68.0 | 1.1 | 433.5 | -610.3 | -93.8 | 0.75 | 3.0 | -0.3 | 9.4 |
| XAUUSD | H4 | kelt_brk |  | 412.0 | 1.1 | 1284.5 | -1802.6 | -195.1 | 0.25 | 3.0 | -4.9 | 32.9 |
| US30 | D1 | bb_rev | T | 25.0 | 1.2 | 213.1 | -364.5 | -103.9 | 1.50 | 3.0 | 0.7 | 3.6 |
| CADJPY | D1 | squeeze_brk | T | 26.0 | 1.2 | 315.1 | -488.6 | -108.9 | 1.00 | 2.9 | 4.6 | 0.8 |
| GBPUSD | D1 | macd_zero | T | 36.0 | 1.2 | 314.0 | -592.2 | -112.6 | 1.00 | 2.9 | -1.4 | 8.3 |
| XAUUSD | D1 | obv_slope | T | 73.0 | 1.1 | 313.0 | -578.6 | -101.3 | 1.00 | 2.9 | -1.2 | 8.0 |
| US30 | D1 | aroon_x | T | 31.0 | 1.2 | 208.6 | -383.0 | -127.2 | 1.50 | 2.9 | 1.6 | 2.3 |
| AUDJPY | D1 | ema_slope |  | 119.0 | 1.1 | 416.2 | -786.1 | -124.9 | 0.75 | 2.9 | 2.5 | 5.5 |
| USDJPY | H4 | squeeze_brk | T | 204.0 | 1.1 | 1247.5 | -1713.4 | -180.0 | 0.25 | 2.9 | 8.6 | 15.3 |
| EURGBP | D1 | willr_rev |  | 195.0 | 1.1 | 611.7 | -1133.7 | -115.6 | 0.50 | 2.8 | 3.9 | 7.9 |
| CHFJPY | H4 | aroon_x | T | 258.0 | 1.1 | 1210.6 | -2049.0 | -196.5 | 0.25 | 2.8 | 37.3 | -21.4 |
| AUDCAD | H4 | rsi_mom | T | 345.0 | 1.1 | 1086.7 | -1499.4 | -232.1 | 0.25 | 2.8 | -9.1 | 45.6 |
| US30 | D1 | trend_vote v=4 |  | 78.0 | 1.2 | 400.2 | -683.4 | -114.7 | 0.75 | 2.8 | 0.8 | 7.4 |
| GBPUSD | H4 | trend_vote v=6 |  | 476.0 | 1.0 | 1193.7 | -2095.8 | -275.4 | 0.25 | 2.8 | -8.6 | 35.7 |
| US30 | D1 | trend_vote v=5 |  | 58.0 | 1.1 | 298.2 | -567.9 | -114.7 | 1.00 | 2.8 | 4.6 | 0.5 |
| AUDJPY | D1 | cci_rev |  | 156.0 | 1.1 | 594.3 | -1143.5 | -194.5 | 0.50 | 2.8 | 21.5 | -14.5 |
| AUDUSD | H4 | rsi_rev |  | 322.0 | 1.0 | 593.5 | -1105.1 | -218.1 | 0.50 | 2.7 | 1.2 | 10.8 |
| EURGBP | D1 | bb_rev | T | 26.0 | 1.2 | 294.5 | -572.7 | -106.1 | 1.00 | 2.7 | -2.8 | 9.6 |
| AUDJPY | H4 | don_brk |  | 616.0 | 1.0 | 1185.7 | -2004.6 | -249.1 | 0.25 | 2.7 | 6.1 | 16.9 |
| USDCAD | D1 | macd_zero | T | 34.0 | 1.1 | 233.8 | -457.7 | -106.3 | 1.25 | 2.7 | -1.0 | 6.1 |
| XAUUSD | H4 | rsi_rev |  | 376.0 | 1.1 | 1163.3 | -1379.0 | -166.7 | 0.25 | 2.7 | 16.3 | 3.8 |
| US500 | D1 | trend_vote v=5 |  | 86.0 | 1.1 | 387.1 | -713.2 | -161.8 | 0.75 | 2.7 | -4.2 | 13.4 |
| XAUUSD | H4 | kelt_rev |  | 499.0 | 1.0 | 1158.5 | -2203.8 | -179.8 | 0.25 | 2.7 | 11.8 | 9.4 |
| GBPJPY | D1 | macd_zero | T | 39.0 | 1.2 | 385.0 | -661.4 | -86.5 | 0.75 | 2.7 | 5.9 | 0.7 |
| CHFJPY | H4 | cci_mom | T | 428.0 | 1.1 | 1144.8 | -1975.4 | -183.7 | 0.25 | 2.7 | 0.6 | 23.2 |
| USTEC | H1 | squeeze_brk |  | 175.0 | 1.0 | 189.7 | -1464.9 | -255.1 | 0.25 | 2.6 | 0.0 | 10.5 |
| GBPCHF | D1 | cci_mom |  | 125.0 | 1.1 | 556.5 | -835.0 | -121.1 | 0.50 | 2.6 | 12.4 | -3.9 |
| US500 | D1 | bb_brk | T | 56.0 | 1.1 | 277.7 | -505.6 | -161.8 | 1.00 | 2.6 | 2.2 | 3.1 |
| NZDJPY | D1 | rsi_rev |  | 1.0 | inf | 137.8 | -123.5 | -63.2 | 2.00 | 2.6 | 0.0 | 2.9 |
| AUDUSD | D1 | cci_mom |  | 120.0 | 1.1 | 550.7 | -941.7 | -112.4 | 0.50 | 2.5 | -0.3 | 11.8 |
| EURCHF | D1 | bb_brk |  | 80.0 | 1.2 | 550.7 | -934.5 | -129.7 | 0.50 | 2.5 | 11.3 | -2.7 |
| US30 | H4 | trend_vote v=4 | T | 271.0 | 1.1 | 1097.4 | -1412.3 | -253.3 | 0.25 | 2.5 | 18.1 | 0.2 |
| EURJPY | D1 | trend_vote v=5 | T | 65.0 | 1.1 | 365.1 | -673.1 | -129.9 | 0.75 | 2.5 | 5.4 | 0.8 |
| DE40 | D1 | squeeze_brk |  | 26.0 | 1.3 | 363.2 | -794.3 | -119.1 | 0.75 | 2.5 | 9.1 | -3.8 |
| USDJPY | H4 | kelt_brk |  | 425.0 | 1.0 | 1079.4 | -1896.8 | -258.3 | 0.25 | 2.5 | 10.5 | 9.4 |
| NZDJPY | D1 | cmf_zero | T | 1.0 | inf | 134.0 | -59.9 | -10.9 | 2.00 | 2.5 | 2.2 | 0.0 |
| AUDUSD | D1 | trend_vote v=4 |  | 105.0 | 1.1 | 535.7 | -909.6 | -109.5 | 0.50 | 2.5 | 11.6 | -3.4 |
| GBPUSD | D1 | dmi_x | T | 27.0 | 1.2 | 265.7 | -591.3 | -138.1 | 1.00 | 2.5 | 2.6 | 2.2 |
| NZDJPY | D1 | rsi_mom |  | 1.0 | inf | 132.7 | -59.9 | -14.6 | 2.00 | 2.5 | 2.2 | 0.0 |
| NZDJPY | D1 | rsi_mom | T | 1.0 | inf | 132.7 | -59.9 | -14.6 | 2.00 | 2.5 | 2.2 | 0.0 |
| US30 | H4 | mfi_rev | T | 78.0 | 1.1 | 527.4 | -905.0 | -215.1 | 0.50 | 2.4 | 6.2 | 3.2 |
| US30 | H4 | kelt_brk | T | 317.0 | 1.1 | 1054.0 | -1534.4 | -237.5 | 0.25 | 2.4 | 18.8 | -1.5 |
| EURCHF | D1 | macd_zero | T | 38.0 | 1.2 | 349.4 | -656.0 | -166.6 | 0.75 | 2.4 | 4.5 | 1.7 |
| US500 | D1 | aroon_x | T | 32.0 | 1.2 | 261.9 | -525.5 | -121.9 | 1.00 | 2.4 | 1.9 | 3.1 |
| AUDCAD | D1 | rsi_rev |  | 40.0 | 1.1 | 185.6 | -424.5 | -109.0 | 1.25 | 2.4 | 4.1 | -1.7 |
| US30 | H4 | ema_x |  | 233.0 | 1.1 | 1035.2 | -2127.9 | -189.8 | 0.25 | 2.4 | -7.1 | 30.4 |
| NZDJPY | D1 | ema_slope | T | 1.0 | inf | 129.3 | -59.9 | -15.1 | 2.00 | 2.4 | 2.2 | 0.0 |
| NZDJPY | D1 | ema_x | T | 1.0 | inf | 129.3 | -59.9 | -15.1 | 2.00 | 2.4 | 2.2 | 0.0 |
| NZDJPY | D1 | trend_vote v=4 | T | 1.0 | inf | 129.3 | -59.9 | -15.1 | 2.00 | 2.4 | 2.2 | 0.0 |
| NZDJPY | D1 | stoch_rev | T | 1.0 | inf | 128.6 | -54.4 | -9.9 | 2.00 | 2.4 | 2.1 | 0.0 |
| NZDJPY | D1 | cci_rev | T | 1.0 | inf | 128.6 | -54.4 | -9.9 | 2.00 | 2.4 | 2.1 | 0.0 |
| USDCHF | D1 | rsi_rev | T | 1.0 | inf | 128.3 | -56.6 | -39.5 | 2.00 | 2.4 | 2.1 | 0.0 |
| USDCHF | H4 | mfi_rev |  | 290.0 | 1.1 | 1022.9 | -1666.7 | -199.2 | 0.25 | 2.4 | -2.0 | 23.8 |
| GBPUSD | H4 | trend_vote v=4 |  | 708.0 | 1.0 | 1016.1 | -2327.9 | -319.3 | 0.25 | 2.4 | 11.5 | 6.8 |
| USTEC | H1 | rsi_rev |  | 239.0 | 1.0 | 168.9 | -1619.6 | -261.3 | 0.25 | 2.3 | 0.0 | 9.4 |
| NZDJPY | D1 | willr_rev | T | 1.0 | inf | 126.7 | -39.9 | -9.8 | 2.00 | 2.3 | 2.1 | 0.0 |
| NZDJPY | D1 | don_rev | T | 1.0 | inf | 126.7 | -39.9 | -9.8 | 2.00 | 2.3 | 2.1 | 0.0 |
| GBPUSD | H4 | trend_vote v=6 | T | 360.0 | 1.1 | 1004.1 | -2211.4 | -275.4 | 0.25 | 2.3 | -17.2 | 42.4 |
| EURUSD | D1 | squeeze_brk | T | 24.0 | 1.3 | 333.1 | -684.5 | -97.3 | 0.75 | 2.3 | 6.3 | -0.9 |
| US500 | D1 | willr_rev | T | 57.0 | 1.1 | 330.2 | -720.7 | -236.9 | 0.75 | 2.3 | 6.6 | -1.3 |
| US30 | D1 | rsi_rev |  | 45.0 | 1.3 | 494.9 | -807.3 | -97.0 | 0.50 | 2.3 | -2.7 | 13.7 |
| AUDUSD | D1 | ha_flip |  | 369.0 | 1.1 | 492.7 | -1106.6 | -153.3 | 0.50 | 2.3 | 10.1 | -2.3 |
| EURJPY | D1 | macd_x | T | 65.0 | 1.2 | 491.7 | -841.4 | -113.5 | 0.50 | 2.3 | 11.8 | -4.6 |
| AUDJPY | D1 | trend_vote v=5 | T | 55.0 | 1.1 | 327.3 | -663.3 | -125.0 | 0.75 | 2.3 | 11.4 | -7.5 |
| US30 | H4 | cmf_zero |  | 694.0 | 1.0 | 975.2 | -1732.8 | -237.3 | 0.25 | 2.3 | 13.6 | 3.3 |
| US500 | D1 | rsi_mom | T | 67.0 | 1.1 | 324.3 | -733.4 | -182.3 | 0.75 | 2.3 | 5.0 | 0.5 |
| EURJPY | D1 | macd_x |  | 182.0 | 1.2 | 969.6 | -1215.2 | -121.8 | 0.25 | 2.2 | 4.3 | 14.9 |
| GBPJPY | D1 | willr_rev |  | 196.0 | 1.1 | 483.5 | -902.7 | -105.2 | 0.50 | 2.2 | 2.4 | 7.0 |
| GBPUSD | D1 | bb_rev | T | 30.0 | 1.2 | 238.4 | -503.9 | -147.5 | 1.00 | 2.2 | 2.7 | 1.6 |
| AUDJPY | D1 | kelt_rev |  | 76.0 | 1.1 | 476.3 | -903.8 | -97.8 | 0.50 | 2.2 | 2.2 | 7.2 |
| AUDCAD | D1 | aroon_x |  | 76.0 | 1.1 | 418.2 | -901.3 | -107.9 | 0.50 | 2.2 | 8.6 | -2.7 |
| EURCHF | D1 | dmi_x | T | 29.0 | 1.2 | 234.3 | -572.3 | -140.9 | 1.00 | 2.2 | 8.9 | -6.3 |
| US500 | D1 | trend_vote v=6 |  | 77.0 | 1.1 | 467.9 | -1187.6 | -140.1 | 0.50 | 2.2 | 13.5 | -7.2 |
| GBPUSD | D1 | cci_rev |  | 163.0 | 1.0 | 309.4 | -661.8 | -126.8 | 0.75 | 2.1 | 2.1 | 3.9 |
| AUDJPY | D1 | bb_brk |  | 85.0 | 1.1 | 464.0 | -973.7 | -120.5 | 0.50 | 2.1 | -6.7 | 18.0 |
| EURUSD | D1 | cci_mom | T | 76.0 | 1.1 | 308.9 | -676.1 | -110.8 | 0.75 | 2.1 | 2.9 | 2.9 |
| NZDJPY | D1 | ema_slope |  | 2.0 | 9.6 | 115.8 | -92.3 | -40.4 | 2.00 | 2.1 | 1.9 | 0.0 |
| NZDJPY | D1 | trend_vote v=4 |  | 2.0 | 9.6 | 115.8 | -92.3 | -40.4 | 2.00 | 2.1 | 1.9 | 0.0 |
| CHFJPY | D1 | kelt_brk | T | 45.0 | 1.1 | 184.6 | -447.5 | -118.7 | 1.25 | 2.1 | 4.5 | -1.7 |
| GBPUSD | D1 | trend_vote v=5 |  | 101.0 | 1.1 | 456.5 | -959.1 | -106.6 | 0.50 | 2.1 | 5.0 | 3.3 |
| USDCHF | D1 | dmi_x | T | 30.0 | 1.2 | 226.6 | -581.7 | -109.6 | 1.00 | 2.1 | -0.5 | 5.3 |
| DE40 | D1 | ema_slope | T | 37.0 | 1.1 | 225.8 | -591.1 | -97.0 | 1.00 | 2.1 | 3.9 | -0.2 |
| EURJPY | D1 | stoch_rev | T | 34.0 | 1.2 | 300.6 | -737.6 | -113.5 | 0.75 | 2.1 | 0.3 | 5.8 |
| USDCHF | D1 | macd_x |  | 186.0 | 1.1 | 450.8 | -1114.3 | -161.7 | 0.50 | 2.1 | -6.1 | 17.1 |
| CHFJPY | D1 | macd_zero |  | 75.0 | 1.1 | 299.9 | -714.8 | -105.3 | 0.75 | 2.1 | 0.8 | 5.3 |
| EURCHF | D1 | ema_slope | T | 36.0 | 1.1 | 224.7 | -583.5 | -140.9 | 1.00 | 2.1 | 2.8 | 1.2 |
| XAGUSD | D1 | macd_x |  | 179.0 | 1.2 | 887.6 | -1448.6 | -143.2 | 0.25 | 2.1 | -1.0 | 19.8 |
| US500 | H4 | stoch_rev | T | 194.0 | 1.1 | 885.6 | -1455.6 | -189.4 | 0.25 | 2.1 | 12.6 | 2.7 |
| USDCAD | D1 | bb_brk | T | 57.0 | 1.2 | 441.4 | -846.7 | -97.2 | 0.50 | 2.0 | 5.1 | 2.9 |
| USTEC | H4 | cmf_zero |  | 140.0 | 1.0 | 146.1 | -1579.3 | -148.0 | 0.25 | 2.0 | 0.0 | 8.1 |
| DE40 | D1 | ema_x |  | 44.0 | 1.2 | 292.1 | -666.0 | -107.1 | 0.75 | 2.0 | -6.1 | 13.7 |
| CHFJPY | D1 | trend_vote v=4 | T | 56.0 | 1.2 | 429.8 | -886.4 | -97.6 | 0.50 | 2.0 | 2.4 | 5.9 |
| XAUUSD | H4 | cmf_zero |  | 745.0 | 1.0 | 858.1 | -2179.6 | -235.2 | 0.25 | 2.0 | 29.8 | -19.4 |
| XAUUSD | D1 | aroon_x |  | 99.0 | 1.1 | 284.9 | -626.1 | -85.2 | 0.75 | 2.0 | 1.5 | 4.0 |
| US30 | H4 | obv_slope |  | 1760.0 | 1.0 | 853.5 | -2095.3 | -282.4 | 0.25 | 2.0 | -5.5 | 24.7 |
| USDCAD | D1 | macd_x | T | 60.0 | 1.1 | 422.1 | -874.6 | -139.4 | 0.50 | 2.0 | -3.5 | 13.1 |
| DE40 | H4 | macd_x | T | 383.0 | 1.0 | 834.8 | -2021.5 | -254.7 | 0.25 | 1.9 | 16.1 | -2.8 |
| EURUSD | D1 | don_brk | T | 67.0 | 1.1 | 416.1 | -861.8 | -136.0 | 0.50 | 1.9 | -4.2 | 13.9 |
| USTEC | D1 | cci_rev | T | 4.0 | 1.1 | 22.9 | -308.7 | -105.9 | 1.50 | 1.9 | 0.0 | 1.3 |
| AUDUSD | D1 | bb_rev |  | 118.0 | 1.1 | 405.2 | -1062.9 | -176.2 | 0.50 | 1.9 | 5.9 | 1.0 |
| AUDUSD | D1 | willr_rev | T | 63.0 | 1.1 | 402.0 | -929.0 | -95.5 | 0.50 | 1.9 | 6.8 | -0.1 |
| GBPCHF | D1 | willr_rev |  | 195.0 | 1.1 | 397.9 | -954.5 | -110.8 | 0.50 | 1.8 | 11.6 | -6.2 |
| XAGUSD | D1 | rsi_mom |  | 239.0 | 1.2 | 785.1 | -1253.6 | -102.3 | 0.25 | 1.8 | -1.3 | 18.0 |
| US500 | H4 | mfi_rev | T | 72.0 | 1.1 | 392.5 | -1102.5 | -208.5 | 0.50 | 1.8 | 4.1 | 3.1 |
| US30 | D1 | bb_rev |  | 72.0 | 1.1 | 392.1 | -824.4 | -112.8 | 0.50 | 1.8 | -0.2 | 8.4 |
| AUDUSD | H4 | don_rev | T | 253.0 | 1.1 | 780.5 | -1463.3 | -248.5 | 0.25 | 1.8 | -7.9 | 26.1 |
| EURJPY | D1 | bb_rev | T | 34.0 | 1.2 | 253.9 | -622.2 | -150.5 | 0.75 | 1.8 | 6.8 | -3.2 |
| EURCHF | D1 | kelt_brk |  | 40.0 | 1.2 | 379.9 | -821.3 | -106.7 | 0.50 | 1.8 | 4.9 | 1.8 |
| GBPCHF | D1 | bb_rev | T | 31.0 | 1.2 | 253.0 | -625.2 | -109.0 | 0.75 | 1.8 | -8.0 | 15.3 |
| EURCHF | D1 | cci_mom |  | 115.0 | 1.1 | 379.3 | -1181.3 | -138.8 | 0.50 | 1.8 | 14.3 | -9.9 |
| CHFJPY | D1 | bb_rev | T | 34.0 | 1.1 | 250.9 | -610.8 | -168.1 | 0.75 | 1.7 | 4.1 | 0.1 |
| XAUUSD | D1 | macd_x |  | 182.0 | 1.1 | 750.7 | -1211.0 | -100.8 | 0.25 | 1.7 | 3.5 | 11.3 |
| AUDUSD | D1 | bb_rev | T | 33.0 | 1.2 | 250.1 | -695.1 | -95.5 | 0.75 | 1.7 | 1.1 | 3.9 |
| GBPUSD | H4 | cci_mom | T | 468.0 | 1.0 | 744.5 | -2137.7 | -264.2 | 0.25 | 1.7 | 8.5 | 4.9 |
| DE40 | D1 | stoch_rev |  | 128.0 | 1.1 | 372.2 | -1033.4 | -111.1 | 0.50 | 1.7 | 9.6 | -4.2 |
| AUDUSD | H4 | macd_zero | T | 222.0 | 1.1 | 741.2 | -1558.3 | -190.7 | 0.25 | 1.7 | 20.3 | -9.9 |
| USDJPY | D1 | stoch_rev | T | 45.0 | 1.1 | 242.1 | -724.7 | -161.3 | 0.75 | 1.7 | -4.7 | 11.0 |
| US30 | H4 | macd_zero | T | 196.0 | 1.1 | 723.4 | -1275.7 | -215.1 | 0.25 | 1.7 | 7.8 | 5.3 |
| GBPUSD | D1 | mfi_rev | T | 6.0 | 1.3 | 90.1 | -163.8 | -54.9 | 2.00 | 1.7 | 0.7 | 1.0 |
| EURUSD | D1 | don_rev |  | 150.0 | 1.1 | 716.2 | -1261.6 | -130.3 | 0.25 | 1.7 | 22.8 | -13.6 |
| EURCHF | D1 | willr_rev | T | 52.0 | 1.1 | 238.0 | -630.6 | -154.9 | 0.75 | 1.7 | 3.7 | 0.3 |
| US30 | H4 | cmf_zero | T | 376.0 | 1.0 | 710.6 | -1388.9 | -237.3 | 0.25 | 1.6 | 14.9 | -3.9 |
| US30 | D1 | bb_brk | T | 41.0 | 1.2 | 350.6 | -904.8 | -114.7 | 0.50 | 1.6 | 10.8 | -6.1 |
| NZDUSD | D1 | cci_mom |  | 118.0 | 1.1 | 349.1 | -808.7 | -114.7 | 0.50 | 1.6 | 6.2 | -0.5 |
| EURUSD | D1 | trend_vote v=5 |  | 95.0 | 1.1 | 347.7 | -895.0 | -133.3 | 0.50 | 1.6 | -6.8 | 15.7 |
| US500 | D1 | trend_vote v=6 | T | 62.0 | 1.1 | 342.6 | -1023.2 | -140.1 | 0.50 | 1.6 | 14.3 | -10.8 |
| EURJPY | D1 | willr_rev | T | 55.0 | 1.1 | 227.9 | -615.9 | -123.9 | 0.75 | 1.6 | 8.6 | -6.0 |
| NZDJPY | D1 | ema_x |  | 2.0 | 2.9 | 85.3 | -67.2 | -38.4 | 2.00 | 1.6 | 1.4 | 0.0 |
| XAUUSD | H4 | squeeze_brk | T | 197.0 | 1.1 | 681.4 | -1212.6 | -202.0 | 0.25 | 1.6 | 10.5 | 1.1 |
| CADJPY | H4 | macd_zero |  | 477.0 | 1.0 | 681.2 | -1673.1 | -218.4 | 0.25 | 1.6 | 16.3 | -6.2 |
| DE40 | H4 | trend_vote v=6 | T | 327.0 | 1.0 | 668.6 | -2000.1 | -254.7 | 0.25 | 1.5 | 15.3 | -5.2 |
| EURGBP | D1 | kelt_brk | T | 37.0 | 1.1 | 167.0 | -545.6 | -102.5 | 1.00 | 1.5 | 7.8 | -6.3 |
| AUDJPY | H4 | kelt_brk |  | 374.0 | 1.0 | 668.5 | -2025.2 | -238.8 | 0.25 | 1.5 | 8.1 | 3.7 |
| XAUUSD | H4 | dmi_x | T | 193.0 | 1.1 | 659.2 | -1885.8 | -150.7 | 0.25 | 1.5 | -8.5 | 24.3 |
| EURCHF | D1 | don_brk |  | 85.0 | 1.1 | 329.1 | -1024.6 | -111.6 | 0.50 | 1.5 | 9.0 | -4.4 |
| US500 | H4 | kelt_brk | T | 313.0 | 1.0 | 655.1 | -1719.8 | -197.0 | 0.25 | 1.5 | -13.4 | 30.4 |
| USDJPY | H4 | mfi_rev | T | 52.0 | 1.1 | 326.7 | -852.6 | -183.1 | 0.50 | 1.5 | 4.2 | 1.6 |
| XAUUSD | D1 | cci_rev |  | 162.0 | 1.1 | 652.4 | -1416.6 | -141.7 | 0.25 | 1.5 | 6.4 | 5.6 |
| EURJPY | H4 | dmi_x |  | 444.0 | 1.0 | 646.5 | -1643.8 | -244.3 | 0.25 | 1.5 | 17.2 | -8.0 |
| AUDCAD | D1 | rsi_mom |  | 241.0 | 1.1 | 286.8 | -1157.0 | -112.8 | 0.50 | 1.5 | -13.5 | 30.4 |
| EURGBP | D1 | stoch_rev | T | 38.0 | 1.1 | 160.2 | -559.7 | -125.7 | 1.00 | 1.5 | 2.8 | -0.1 |
| GBPCHF | D1 | don_rev | T | 40.0 | 1.2 | 320.3 | -932.9 | -109.1 | 0.50 | 1.5 | -9.3 | 18.2 |
| DE40 | H4 | ema_x |  | 248.0 | 1.1 | 640.4 | -1976.7 | -186.7 | 0.25 | 1.5 | 21.0 | -12.9 |
| CADJPY | H4 | ema_x | T | 159.0 | 1.1 | 640.1 | -1450.5 | -226.8 | 0.25 | 1.5 | 17.7 | -8.7 |
| US500 | D1 | ema_slope |  | 99.0 | 1.1 | 320.0 | -1152.4 | -182.3 | 0.50 | 1.5 | -2.7 | 10.1 |
| AUDCAD | D1 | trend_vote v=5 |  | 84.0 | 1.1 | 280.3 | -1098.4 | -107.4 | 0.50 | 1.5 | -7.9 | 20.9 |
| US500 | D1 | don_rev | T | 38.0 | 1.1 | 157.1 | -578.2 | -132.7 | 1.00 | 1.5 | -3.5 | 7.6 |
| USDJPY | D1 | macd_zero |  | 81.0 | 1.1 | 209.2 | -776.7 | -175.5 | 0.75 | 1.5 | -3.4 | 8.7 |
| XAUUSD | H4 | squeeze_brk |  | 253.0 | 1.0 | 623.1 | -2162.0 | -202.0 | 0.25 | 1.4 | 4.3 | 7.6 |
| EURGBP | D1 | macd_x | T | 60.0 | 1.1 | 308.6 | -937.2 | -120.2 | 0.50 | 1.4 | 14.6 | -11.8 |
| AUDCAD | D1 | macd_x | T | 52.0 | 1.1 | 272.9 | -854.3 | -98.7 | 0.50 | 1.4 | -6.7 | 18.7 |
| USDCAD | D1 | cci_mom |  | 118.0 | 1.1 | 304.1 | -1100.2 | -118.2 | 0.50 | 1.4 | 5.4 | -0.4 |
| USDCAD | D1 | dmi_x | T | 18.0 | 1.2 | 152.0 | -510.8 | -93.3 | 1.00 | 1.4 | 7.8 | -6.5 |
| DE40 | D1 | squeeze_brk | T | 20.0 | 1.2 | 201.8 | -688.0 | -119.1 | 0.75 | 1.4 | 7.3 | -5.0 |
| NZDJPY | D1 | obv_slope | T | 4.0 | 1.4 | 75.4 | -275.9 | -84.9 | 2.00 | 1.4 | -1.1 | 2.9 |
| GBPUSD | H4 | trend_vote v=4 | T | 319.0 | 1.0 | 600.3 | -1986.9 | -192.7 | 0.25 | 1.4 | -2.6 | 15.7 |
| XAUUSD | H4 | trend_vote v=5 | T | 328.0 | 1.0 | 598.3 | -2082.3 | -206.8 | 0.25 | 1.4 | 1.2 | 11.0 |
| US500 | D1 | ema_x | T | 18.0 | 1.2 | 149.4 | -523.7 | -93.5 | 1.00 | 1.4 | 3.9 | -1.8 |
| DE40 | D1 | cmf_zero | T | 63.0 | 1.1 | 297.8 | -860.9 | -88.2 | 0.50 | 1.4 | -7.6 | 15.7 |
| DE40 | D1 | trend_vote v=6 | T | 60.0 | 1.1 | 148.4 | -536.5 | -109.6 | 1.00 | 1.4 | 3.3 | -1.0 |
| DE40 | D1 | rsi_mom | T | 68.0 | 1.1 | 144.1 | -548.4 | -98.6 | 1.00 | 1.3 | 0.2 | 2.7 |
| US30 | D1 | obv_slope | T | 68.0 | 1.1 | 191.7 | -634.1 | -117.1 | 0.75 | 1.3 | 6.0 | -3.5 |
| US500 | H4 | squeeze_brk | T | 172.0 | 1.1 | 565.4 | -1260.8 | -178.7 | 0.25 | 1.3 | 6.9 | 3.2 |
| USTEC | H1 | aroon_x | T | 151.0 | 1.0 | 93.7 | -1682.6 | -251.4 | 0.25 | 1.3 | 0.0 | 5.2 |
| NZDUSD | D1 | kelt_brk |  | 64.0 | 1.1 | 280.1 | -917.2 | -145.5 | 0.50 | 1.3 | -0.6 | 6.5 |
| CADJPY | H4 | squeeze_brk |  | 233.0 | 1.0 | 560.0 | -1242.4 | -165.8 | 0.25 | 1.3 | -16.7 | 32.5 |
| GBPCHF | D1 | trend_vote v=5 |  | 95.0 | 1.1 | 558.5 | -1651.8 | -121.2 | 0.25 | 1.3 | 27.1 | -22.3 |
| AUDUSD | H4 | obv_slope | T | 538.0 | 1.0 | 556.0 | -1622.5 | -264.3 | 0.25 | 1.3 | -6.8 | 20.0 |
| GBPJPY | H4 | rsi_rev | T | 51.0 | 1.1 | 274.3 | -982.3 | -186.0 | 0.50 | 1.3 | 6.9 | -2.9 |
| EURUSD | D1 | kelt_rev |  | 73.0 | 1.1 | 273.7 | -963.9 | -130.3 | 0.50 | 1.3 | 2.2 | 2.9 |
| GBPUSD | D1 | rsi_rev | T | 2.0 | 1.9 | 67.1 | -173.9 | -38.4 | 2.00 | 1.2 | 0.0 | 1.4 |
| EURUSD | D1 | cci_rev | T | 47.0 | 1.1 | 178.4 | -619.7 | -107.7 | 0.75 | 1.2 | 3.2 | -0.3 |
| CADJPY | D1 | willr_rev |  | 199.0 | 1.0 | 264.5 | -1131.4 | -187.5 | 0.50 | 1.2 | -11.7 | 20.1 |
| XAUUSD | D1 | cci_mom |  | 126.0 | 1.1 | 261.2 | -850.5 | -92.8 | 0.50 | 1.2 | -8.4 | 15.9 |
| GBPJPY | D1 | rsi_mom | T | 72.0 | 1.1 | 260.3 | -1124.1 | -125.8 | 0.50 | 1.2 | 11.3 | -8.7 |
| EURJPY | D1 | rsi_mom | T | 78.0 | 1.1 | 252.2 | -830.0 | -137.1 | 0.50 | 1.2 | 8.0 | -4.7 |
| XAGUSD | D1 | rsi_rev |  | 49.0 | 1.1 | 168.0 | -764.7 | -94.9 | 0.75 | 1.2 | 3.5 | -0.8 |
| CHFJPY | D1 | macd_x |  | 174.0 | 1.0 | 250.1 | -1025.2 | -159.5 | 0.50 | 1.2 | 13.3 | -11.4 |
| EURJPY | D1 | trend_vote v=4 | T | 58.0 | 1.1 | 250.1 | -881.2 | -129.9 | 0.50 | 1.2 | 8.2 | -5.0 |
| US30 | D1 | willr_rev |  | 151.0 | 1.1 | 249.0 | -826.0 | -134.7 | 0.50 | 1.2 | 6.4 | -2.8 |
| US30 | D1 | cci_mom | T | 60.0 | 1.1 | 164.8 | -703.0 | -117.1 | 0.75 | 1.1 | 4.1 | -1.7 |
| AUDCAD | D1 | mfi_rev |  | 19.0 | 1.2 | 145.6 | -669.2 | -91.2 | 0.75 | 1.1 | -1.0 | 5.7 |
| XAGUSD | D1 | ema_slope | T | 44.0 | 1.1 | 163.0 | -656.7 | -102.3 | 0.75 | 1.1 | 4.7 | -2.5 |
| USDCAD | H4 | kelt_rev | T | 106.0 | 1.0 | 243.8 | -856.7 | -163.5 | 0.50 | 1.1 | -2.1 | 7.8 |
| USDJPY | D1 | bb_brk | T | 58.0 | 1.1 | 162.1 | -698.1 | -110.9 | 0.75 | 1.1 | -6.6 | 11.7 |
| USTEC | H4 | ema_slope |  | 106.0 | 1.0 | 80.9 | -1250.2 | -219.8 | 0.25 | 1.1 | 0.0 | 4.5 |
| GBPUSD | D1 | rsi_rev |  | 43.0 | 1.1 | 120.7 | -508.8 | -123.4 | 1.00 | 1.1 | -3.0 | 6.3 |
| GBPCHF | D1 | dmi_x | T | 22.0 | 1.2 | 159.7 | -629.3 | -96.0 | 0.75 | 1.1 | 4.4 | -2.2 |
| GBPCHF | D1 | squeeze_brk |  | 38.0 | 1.1 | 156.8 | -750.9 | -119.9 | 0.75 | 1.1 | 12.3 | -12.1 |
| EURJPY | D1 | don_rev | T | 35.0 | 1.1 | 156.0 | -733.6 | -113.6 | 0.75 | 1.1 | 5.3 | -3.4 |
| AUDJPY | D1 | cci_mom | T | 61.0 | 1.1 | 228.7 | -926.2 | -125.6 | 0.50 | 1.1 | -11.7 | 19.4 |
| DE40 | D1 | cci_rev |  | 157.0 | 1.0 | 152.0 | -657.4 | -178.2 | 0.75 | 1.1 | 1.6 | 1.1 |
| GBPJPY | D1 | cci_mom | T | 68.0 | 1.0 | 150.5 | -632.1 | -121.9 | 0.75 | 1.0 | 11.9 | -11.7 |
| USDCAD | D1 | aroon_x | T | 39.0 | 1.0 | 90.0 | -458.4 | -97.2 | 1.25 | 1.0 | 3.4 | -2.4 |
| US30 | D1 | bb_brk |  | 70.0 | 1.0 | 149.3 | -738.5 | -114.7 | 0.75 | 1.0 | 3.6 | -1.4 |
| DE40 | D1 | trend_vote v=6 |  | 80.0 | 1.0 | 148.3 | -700.1 | -109.6 | 0.75 | 1.0 | 2.1 | 0.5 |
| USDJPY | D1 | don_rev | T | 43.0 | 1.1 | 148.1 | -638.5 | -161.3 | 0.75 | 1.0 | 3.8 | -1.6 |
| GBPUSD | D1 | ha_flip |  | 377.0 | 1.0 | 218.4 | -888.9 | -130.6 | 0.50 | 1.0 | 2.8 | 1.1 |
| XAGUSD | D1 | don_rev |  | 128.0 | 1.1 | 429.5 | -1258.7 | -115.0 | 0.25 | 1.0 | 1.8 | 6.7 |
| GBPJPY | D1 | kelt_brk | T | 51.0 | 1.1 | 143.0 | -677.8 | -88.3 | 0.75 | 1.0 | 7.3 | -6.1 |
| EURJPY | D1 | aroon_x |  | 102.0 | 1.0 | 214.4 | -873.9 | -129.9 | 0.50 | 1.0 | 2.2 | 1.7 |
| USDJPY | D1 | cmf_zero | T | 64.0 | 1.1 | 213.5 | -834.3 | -197.9 | 0.50 | 1.0 | -9.6 | 16.4 |
| GBPUSD | D1 | kelt_brk | T | 48.0 | 1.1 | 141.9 | -670.3 | -125.9 | 0.75 | 1.0 | -1.0 | 4.3 |
| AUDCAD | D1 | trend_vote v=6 |  | 75.0 | 1.0 | 125.4 | -782.5 | -99.2 | 0.75 | 1.0 | -6.7 | 14.6 |
| DE40 | H4 | trend_vote v=5 |  | 517.0 | 1.0 | 418.6 | -2387.9 | -254.5 | 0.25 | 1.0 | 15.0 | -10.0 |
| AUDCAD | H4 | dmi_x | T | 144.0 | 1.1 | 375.9 | -1332.2 | -146.9 | 0.25 | 1.0 | -17.5 | 40.1 |
| EURUSD | D1 | ema_slope | T | 41.0 | 1.1 | 206.3 | -858.6 | -124.7 | 0.50 | 1.0 | -9.9 | 16.7 |
| US500 | H1 | rsi_rev | T | 165.0 | 1.0 | 411.7 | -1662.1 | -268.0 | 0.25 | 1.0 | -2.2 | 11.3 |
| XAUUSD | D1 | macd_zero | T | 38.0 | 1.1 | 101.4 | -568.1 | -92.0 | 1.00 | 0.9 | -1.6 | 4.1 |
| EURCHF | D1 | stoch_rev |  | 123.0 | 1.1 | 404.7 | -1205.7 | -118.4 | 0.25 | 0.9 | -2.8 | 12.0 |
| EURUSD | D1 | bb_brk | T | 61.0 | 1.1 | 200.4 | -1096.8 | -103.3 | 0.50 | 0.9 | -6.2 | 12.0 |
| US30 | H4 | macd_zero |  | 431.0 | 1.0 | 398.4 | -2144.5 | -250.3 | 0.25 | 0.9 | -12.0 | 23.3 |
| GBPUSD | D1 | macd_x |  | 189.0 | 1.1 | 396.6 | -1210.9 | -112.0 | 0.25 | 0.9 | -1.0 | 9.5 |
| CHFJPY | D1 | rsi_mom | T | 74.0 | 1.1 | 394.9 | -1243.5 | -125.2 | 0.25 | 0.9 | -2.9 | 11.8 |
| AUDCAD | H4 | rsi_rev |  | 258.0 | 1.0 | 351.5 | -1769.9 | -185.6 | 0.25 | 0.9 | 15.6 | -16.6 |
| EURUSD | H4 | rsi_rev |  | 349.0 | 1.0 | 386.6 | -1533.2 | -338.6 | 0.25 | 0.9 | 23.7 | -21.6 |
| EURUSD | D1 | stoch_rev |  | 127.0 | 1.1 | 381.7 | -1498.9 | -130.3 | 0.25 | 0.9 | 9.6 | -4.0 |
| US30 | H4 | macd_x | T | 383.0 | 1.0 | 369.7 | -1626.8 | -300.3 | 0.25 | 0.9 | 8.1 | -2.4 |
| CADJPY | D1 | stoch_rev |  | 141.0 | 1.1 | 365.5 | -1370.2 | -187.5 | 0.25 | 0.8 | -18.7 | 31.0 |
| NZDUSD | D1 | ema_slope |  | 124.0 | 1.0 | 120.9 | -686.2 | -107.7 | 0.75 | 0.8 | 4.5 | -3.1 |
| CADJPY | H4 | macd_x | T | 394.0 | 1.0 | 359.3 | -1445.8 | -196.5 | 0.25 | 0.8 | 0.9 | 6.4 |
| US500 | D1 | trend_vote v=4 |  | 93.0 | 1.0 | 179.5 | -1089.8 | -182.3 | 0.50 | 0.8 | -3.4 | 8.0 |
| GBPJPY | D1 | kelt_brk |  | 68.0 | 1.1 | 178.2 | -1009.0 | -101.3 | 0.50 | 0.8 | 12.6 | -12.0 |
| EURJPY | D1 | trend_vote v=6 | T | 57.0 | 1.1 | 178.1 | -1109.9 | -112.9 | 0.50 | 0.8 | 4.5 | -1.9 |
| EURUSD | D1 | ha_flip |  | 387.0 | 1.0 | 349.4 | -1260.1 | -97.3 | 0.25 | 0.8 | -2.9 | 10.9 |
| AUDUSD | D1 | ema_slope |  | 123.0 | 1.0 | 173.4 | -979.5 | -153.3 | 0.50 | 0.8 | -1.2 | 5.1 |
| GBPCHF | D1 | cmf_zero |  | 116.0 | 1.0 | 172.9 | -1154.7 | -101.0 | 0.50 | 0.8 | 12.4 | -11.9 |
| CADJPY | D1 | bb_rev | T | 37.0 | 1.1 | 115.2 | -690.4 | -95.3 | 0.75 | 0.8 | 3.4 | -1.9 |
| DE40 | D1 | ema_slope |  | 107.0 | 1.1 | 343.8 | -1333.4 | -159.5 | 0.25 | 0.8 | -1.9 | 9.6 |
| NZDUSD | D1 | ha_flip |  | 368.0 | 1.0 | 340.9 | -1240.5 | -134.6 | 0.25 | 0.8 | 13.4 | -9.6 |
| US30 | D1 | ema_slope | T | 27.0 | 1.1 | 67.9 | -469.0 | -122.1 | 1.25 | 0.8 | -3.7 | 6.1 |
| CHFJPY | D1 | don_rev |  | 128.0 | 1.0 | 167.9 | -836.1 | -112.5 | 0.50 | 0.8 | -6.2 | 11.3 |
| USDJPY | D1 | aroon_x |  | 92.0 | 1.0 | 167.0 | -850.0 | -197.9 | 0.50 | 0.8 | 7.0 | -5.3 |
| GBPCHF | D1 | ema_slope | T | 44.0 | 1.1 | 166.1 | -973.6 | -87.6 | 0.50 | 0.8 | 9.7 | -8.6 |
| EURCHF | D1 | kelt_rev |  | 47.0 | 1.1 | 165.3 | -932.0 | -130.1 | 0.50 | 0.8 | -6.6 | 11.7 |
| USDJPY | D1 | trend_vote v=4 |  | 110.0 | 1.0 | 160.9 | -896.8 | -175.5 | 0.50 | 0.7 | -2.8 | 6.8 |
| GBPJPY | D1 | kelt_rev | T | 12.0 | 1.1 | 40.1 | -259.9 | -94.5 | 2.00 | 0.7 | -1.1 | 2.2 |
| AUDUSD | D1 | rsi_rev |  | 48.0 | 1.0 | 79.8 | -576.2 | -176.2 | 1.00 | 0.7 | 0.3 | 1.3 |
| NZDUSD | D1 | macd_zero |  | 84.0 | 1.0 | 104.5 | -666.2 | -114.7 | 0.75 | 0.7 | 3.5 | -2.2 |
| DE40 | H4 | rsi_mom | T | 378.0 | 1.0 | 312.5 | -2297.2 | -200.1 | 0.25 | 0.7 | -0.7 | 7.4 |
| DE40 | H4 | macd_x |  | 1002.0 | 1.0 | 310.3 | -2119.1 | -265.3 | 0.25 | 0.7 | 1.8 | 4.2 |
| USTEC | H1 | dmi_x | T | 138.0 | 1.0 | 51.2 | -1646.2 | -336.6 | 0.25 | 0.7 | 0.0 | 2.8 |
| AUDUSD | D1 | aroon_x | T | 42.0 | 1.1 | 150.7 | -920.1 | -109.5 | 0.50 | 0.7 | 6.6 | -5.1 |
| NZDJPY | D1 | bb_brk | T | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | squeeze_brk | T | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | cci_mom | T | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | don_brk |  | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | don_brk | T | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | squeeze_brk |  | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| NZDJPY | D1 | bb_brk |  | 2.0 | 1.4 | 37.3 | -142.3 | -43.3 | 2.00 | 0.7 | 0.6 | 0.0 |
| CADJPY | H4 | kelt_brk | T | 321.0 | 1.0 | 296.8 | -1552.2 | -213.1 | 0.25 | 0.7 | -17.0 | 27.5 |
| US500 | D1 | kelt_brk |  | 64.0 | 1.0 | 147.9 | -975.7 | -119.0 | 0.50 | 0.7 | -5.3 | 9.7 |
| US500 | D1 | cci_mom |  | 131.0 | 1.0 | 295.7 | -1266.2 | -161.8 | 0.25 | 0.7 | -5.3 | 12.8 |
| XAUUSD | D1 | aroon_x | T | 43.0 | 1.1 | 97.8 | -730.3 | -95.9 | 0.75 | 0.7 | -2.8 | 5.5 |
| USDJPY | D1 | ema_x |  | 45.0 | 1.0 | 97.3 | -700.9 | -135.1 | 0.75 | 0.7 | -2.0 | 4.5 |
| EURCHF | D1 | trend_vote v=6 | T | 52.0 | 1.0 | 96.9 | -618.6 | -180.5 | 0.75 | 0.7 | -1.9 | 4.4 |
| USDCHF | D1 | willr_rev |  | 197.0 | 1.0 | 290.1 | -1742.4 | -124.6 | 0.25 | 0.7 | -1.8 | 8.3 |
| NZDJPY | D1 | macd_x | T | 2.0 | 1.4 | 36.1 | -115.6 | -45.1 | 2.00 | 0.7 | 0.6 | 0.0 |
| AUDCAD | D1 | dmi_x | T | 29.0 | 1.0 | 64.0 | -510.9 | -98.7 | 1.00 | 0.7 | -6.0 | 11.8 |
| AUDUSD | D1 | cci_rev | T | 55.0 | 1.0 | 95.5 | -750.0 | -95.5 | 0.75 | 0.7 | 4.3 | -3.3 |
| GBPUSD | D1 | cci_rev | T | 51.0 | 1.1 | 142.8 | -882.9 | -126.8 | 0.50 | 0.7 | 2.3 | 0.1 |
| AUDCAD | H4 | cci_rev | T | 276.0 | 1.0 | 245.5 | -1368.3 | -172.5 | 0.25 | 0.6 | -18.9 | 38.8 |
| GBPUSD | D1 | cci_mom | T | 74.0 | 1.0 | 132.6 | -1134.7 | -112.0 | 0.50 | 0.6 | 0.2 | 2.5 |
| US30 | H4 | ema_x | T | 127.0 | 1.0 | 263.3 | -1539.9 | -155.0 | 0.25 | 0.6 | -2.9 | 9.1 |
| DE40 | H4 | ema_x | T | 139.0 | 1.0 | 261.3 | -2316.0 | -172.5 | 0.25 | 0.6 | 29.6 | -31.6 |
| USDJPY | D1 | bb_rev |  | 108.0 | 1.0 | 128.5 | -1174.5 | -167.8 | 0.50 | 0.6 | 9.7 | -9.4 |
| EURJPY | D1 | willr_rev |  | 201.0 | 1.0 | 249.1 | -1241.5 | -176.6 | 0.25 | 0.6 | 5.8 | -2.0 |
| EURUSD | D1 | mfi_rev | T | 2.0 | 1.3 | 31.1 | -139.2 | -90.8 | 2.00 | 0.6 | 0.5 | 0.0 |
| DE40 | H4 | bb_rev | T | 180.0 | 1.0 | 247.8 | -1741.6 | -282.5 | 0.25 | 0.6 | -9.3 | 16.7 |
| GBPJPY | D1 | cmf_zero |  | 122.0 | 1.1 | 247.6 | -1645.1 | -115.8 | 0.25 | 0.6 | 14.3 | -12.7 |
| GBPUSD | D1 | cmf_zero | T | 68.0 | 1.0 | 123.7 | -902.9 | -119.2 | 0.50 | 0.6 | 4.0 | -2.4 |
| AUDUSD | D1 | don_brk |  | 104.0 | 1.0 | 120.8 | -949.1 | -111.7 | 0.50 | 0.6 | 1.6 | 0.5 |
| XAGUSD | D1 | bb_rev | T | 29.0 | 1.0 | 29.9 | -299.9 | -87.3 | 2.00 | 0.6 | 1.8 | -1.6 |
| USDJPY | D1 | trend_vote v=6 |  | 79.0 | 1.0 | 119.4 | -883.1 | -161.3 | 0.50 | 0.6 | -4.1 | 7.6 |
| US30 | D1 | kelt_brk | T | 34.0 | 1.0 | 59.3 | -582.6 | -101.6 | 1.00 | 0.5 | 1.6 | -0.8 |
| US30 | D1 | ema_slope |  | 85.0 | 1.0 | 117.4 | -983.6 | -114.7 | 0.50 | 0.5 | -6.4 | 10.5 |
| AUDUSD | H4 | ema_x | T | 161.0 | 1.0 | 231.4 | -1406.9 | -188.9 | 0.25 | 0.5 | 15.4 | -14.4 |
| US500 | D1 | mfi_rev | T | 10.0 | 1.1 | 28.4 | -296.8 | -94.4 | 2.00 | 0.5 | 3.2 | -3.4 |
| NZDUSD | H4 | rsi_rev | T | 32.0 | 1.0 | 74.4 | -711.6 | -160.9 | 0.75 | 0.5 | -1.1 | 2.9 |
| GBPCHF | H4 | squeeze_brk |  | 220.0 | 1.0 | 225.0 | -1751.2 | -178.0 | 0.25 | 0.5 | 20.6 | -21.5 |
| CHFJPY | D1 | trend_vote v=6 |  | 73.0 | 1.1 | 211.1 | -1456.2 | -125.7 | 0.25 | 0.5 | 9.2 | -7.1 |
| AUDCAD | H4 | macd_x | T | 345.0 | 1.0 | 189.3 | -1309.6 | -208.2 | 0.25 | 0.5 | -9.3 | 21.1 |
| NZDUSD | D1 | macd_x |  | 180.0 | 1.0 | 207.8 | -1565.3 | -136.3 | 0.25 | 0.5 | -10.4 | 17.3 |
| US500 | D1 | dmi_x |  | 76.0 | 1.0 | 99.9 | -1088.5 | -131.0 | 0.50 | 0.5 | -1.9 | 4.4 |
| EURGBP | D1 | bb_brk | T | 60.0 | 1.0 | 66.3 | -738.6 | -111.7 | 0.75 | 0.5 | 6.6 | -6.9 |
| DE40 | H4 | cmf_zero |  | 703.0 | 1.0 | 197.5 | -2009.0 | -235.4 | 0.25 | 0.5 | 24.1 | -26.0 |
| GBPCHF | D1 | rsi_mom | T | 68.0 | 1.1 | 196.1 | -1229.1 | -109.0 | 0.25 | 0.5 | 4.0 | -1.0 |
| EURUSD | D1 | aroon_x |  | 96.0 | 1.0 | 64.9 | -704.5 | -141.9 | 0.75 | 0.5 | -2.9 | 5.0 |
| NZDUSD | D1 | trend_vote v=6 |  | 83.0 | 1.0 | 189.7 | -1223.9 | -107.7 | 0.25 | 0.4 | -0.6 | 4.7 |
| CADJPY | D1 | rsi_rev |  | 39.0 | 1.0 | 63.1 | -797.2 | -105.6 | 0.75 | 0.4 | 4.0 | -3.7 |
| USDCHF | D1 | dmi_x |  | 74.0 | 1.0 | 46.2 | -591.3 | -161.7 | 1.00 | 0.4 | 2.5 | -2.2 |
| EURUSD | D1 | kelt_brk |  | 62.0 | 1.0 | 91.2 | -1011.1 | -110.8 | 0.50 | 0.4 | -5.4 | 8.7 |
| CHFJPY | D1 | trend_vote v=5 |  | 89.0 | 1.0 | 90.4 | -993.9 | -125.4 | 0.50 | 0.4 | 5.5 | -5.0 |
| GBPJPY | H4 | ema_x | T | 136.0 | 1.0 | 180.6 | -1373.7 | -172.8 | 0.25 | 0.4 | 10.4 | -9.2 |
| EURGBP | D1 | kelt_rev |  | 65.0 | 1.0 | 87.5 | -884.6 | -127.4 | 0.50 | 0.4 | -7.9 | 11.7 |
| EURGBP | D1 | dmi_x | T | 28.0 | 1.0 | 58.0 | -608.3 | -111.7 | 0.75 | 0.4 | -1.5 | 3.1 |
| EURUSD | H4 | macd_x | T | 403.0 | 1.0 | 167.2 | -2238.1 | -264.5 | 0.25 | 0.4 | -3.8 | 8.2 |
| USTEC | H1 | mfi_rev |  | 176.0 | 1.0 | 27.0 | -1428.4 | -205.6 | 0.25 | 0.4 | 0.0 | 1.5 |
| CADJPY | H4 | aroon_x |  | 522.0 | 1.0 | 157.0 | -1960.3 | -207.0 | 0.25 | 0.4 | 8.1 | -6.8 |
| US500 | D1 | kelt_rev |  | 76.0 | 1.0 | 73.8 | -925.2 | -118.4 | 0.50 | 0.3 | -4.2 | 6.7 |
| USDCHF | D1 | ha_flip |  | 351.0 | 1.0 | 146.1 | -1840.9 | -108.8 | 0.25 | 0.3 | -0.9 | 4.2 |
| USDJPY | H4 | stoch_rev | T | 247.0 | 1.0 | 145.7 | -2106.9 | -233.7 | 0.25 | 0.3 | 14.6 | -15.2 |
| NZDJPY | H4 | kelt_brk |  | 349.0 | 1.0 | 146.1 | -1511.7 | -227.7 | 0.25 | 0.3 | 19.3 | -21.4 |
| USDJPY | D1 | trend_vote v=5 |  | 100.0 | 1.0 | 47.1 | -709.9 | -161.3 | 0.75 | 0.3 | -1.3 | 2.6 |
| USDJPY | D1 | cci_mom |  | 121.0 | 1.0 | 141.0 | -1356.7 | -212.8 | 0.25 | 0.3 | 3.7 | -1.7 |
| GBPCHF | D1 | macd_x |  | 194.0 | 1.0 | 70.0 | -1070.5 | -149.7 | 0.50 | 0.3 | 0.8 | 0.5 |
| USDJPY | D1 | trend_vote v=6 | T | 62.0 | 1.0 | 46.5 | -649.8 | -161.3 | 0.75 | 0.3 | 2.7 | -2.5 |
| EURJPY | D1 | ema_x | T | 24.0 | 1.1 | 69.2 | -849.7 | -140.4 | 0.50 | 0.3 | 5.4 | -5.3 |
| AUDUSD | D1 | cci_mom | T | 67.0 | 1.0 | 133.3 | -1447.9 | -109.5 | 0.25 | 0.3 | 7.6 | -6.7 |
| AUDJPY | D1 | bb_rev |  | 104.0 | 1.0 | 130.7 | -1232.7 | -216.4 | 0.25 | 0.3 | 7.8 | -7.0 |
| EURUSD | D1 | cci_rev |  | 166.0 | 1.0 | 129.4 | -1463.6 | -130.3 | 0.25 | 0.3 | 5.7 | -4.4 |
| AUDJPY | D1 | cmf_zero |  | 132.0 | 1.0 | 127.8 | -1229.0 | -216.4 | 0.25 | 0.3 | -10.0 | 15.2 |
| DE40 | D1 | ha_flip |  | 355.0 | 1.0 | 125.5 | -1472.6 | -178.2 | 0.25 | 0.3 | 9.9 | -9.8 |
| US500 | D1 | cmf_zero | T | 64.0 | 1.0 | 60.5 | -1073.8 | -125.7 | 0.50 | 0.3 | 4.3 | -4.1 |
| AUDCAD | D1 | dmi_x |  | 83.0 | 1.0 | 51.8 | -1085.7 | -108.2 | 0.50 | 0.3 | -10.9 | 19.7 |
| XAGUSD | D1 | dmi_x | T | 26.0 | 1.0 | 24.9 | -527.4 | -116.2 | 1.00 | 0.2 | 0.5 | -0.1 |
| NZDUSD | D1 | stoch_rev | T | 42.0 | 1.0 | 31.3 | -681.1 | -110.2 | 0.75 | 0.2 | 3.1 | -3.3 |
| EURJPY | D1 | macd_zero |  | 79.0 | 1.0 | 29.9 | -740.3 | -133.0 | 0.75 | 0.2 | 0.1 | 0.5 |
| GBPUSD | D1 | ema_x |  | 40.0 | 1.0 | 42.8 | -851.4 | -112.1 | 0.50 | 0.2 | -7.5 | 10.3 |
| EURCHF | D1 | don_rev |  | 123.0 | 1.0 | 75.1 | -1439.4 | -131.2 | 0.25 | 0.2 | -16.0 | 21.6 |
| USDJPY | H4 | aroon_x | T | 256.0 | 1.0 | 74.8 | -1624.7 | -290.7 | 0.25 | 0.2 | 3.1 | -2.4 |
| USDCAD | D1 | trend_vote v=5 |  | 87.0 | 1.0 | 35.8 | -956.5 | -136.3 | 0.50 | 0.2 | -5.6 | 7.8 |
| EURJPY | D1 | trend_vote v=6 |  | 76.0 | 1.0 | 34.7 | -1050.2 | -113.6 | 0.50 | 0.2 | -0.4 | 1.2 |
| AUDCAD | D1 | don_brk |  | 84.0 | 1.0 | 30.0 | -851.5 | -108.2 | 0.50 | 0.2 | -1.2 | 2.9 |
| XAUUSD | H1 | rsi_rev | T | 160.0 | 1.0 | 59.9 | -1668.6 | -195.9 | 0.25 | 0.1 | 14.6 | -16.9 |
| DE40 | D1 | trend_vote v=4 |  | 99.0 | 1.0 | 54.6 | -1240.1 | -97.0 | 0.25 | 0.1 | -7.1 | 10.0 |
| DE40 | H4 | squeeze_brk | T | 154.0 | 1.0 | 53.2 | -1826.5 | -204.6 | 0.25 | 0.1 | -19.4 | 25.4 |
| EURUSD | D1 | cci_mom |  | 128.0 | 1.0 | 25.1 | -919.0 | -133.3 | 0.50 | 0.1 | 0.4 | 0.1 |
| USDJPY | H4 | dmi_x |  | 458.0 | 1.0 | 49.7 | -1667.0 | -265.4 | 0.25 | 0.1 | 0.7 | 0.2 |
| NZDUSD | D1 | kelt_brk | T | 53.0 | 1.0 | 24.3 | -858.8 | -145.5 | 0.50 | 0.1 | -7.2 | 9.5 |
| EURCHF | H4 | stoch_rev | T | 238.0 | 1.0 | 44.7 | -1683.6 | -186.5 | 0.25 | 0.1 | 14.5 | -17.2 |
| EURUSD | D1 | kelt_brk | T | 52.0 | 1.0 | 21.9 | -818.9 | -110.8 | 0.50 | 0.1 | -4.7 | 6.3 |
| CADJPY | H4 | trend_vote v=4 |  | 627.0 | 1.0 | 41.9 | -2240.9 | -202.9 | 0.25 | 0.1 | 0.9 | -0.2 |
| US500 | D1 | macd_x |  | 192.0 | 1.0 | 40.5 | -1259.9 | -127.0 | 0.25 | 0.1 | -13.5 | 17.7 |
| NZDUSD | D1 | cmf_zero | T | 65.0 | 1.0 | 13.5 | -748.3 | -161.2 | 0.75 | 0.1 | 2.6 | -3.0 |
| USDCHF | D1 | macd_x | T | 60.0 | 1.0 | 37.7 | -1381.3 | -109.6 | 0.25 | 0.1 | -15.3 | 19.9 |
| EURJPY | D1 | kelt_rev | T | 12.0 | 1.0 | 9.3 | -549.6 | -71.4 | 1.00 | 0.1 | 1.5 | -1.7 |
| GBPUSD | D1 | willr_rev |  | 194.0 | 1.0 | 37.3 | -1559.4 | -147.5 | 0.25 | 0.1 | 21.1 | -25.6 |
| XAUUSD | H4 | kelt_brk | T | 337.0 | 1.0 | 35.8 | -1320.4 | -176.6 | 0.25 | 0.1 | -11.8 | 15.5 |
| CADJPY | D1 | kelt_rev |  | 69.0 | 1.0 | 17.7 | -1029.0 | -166.3 | 0.50 | 0.1 | 7.0 | -8.4 |
| CADJPY | D1 | ema_x |  | 51.0 | 1.0 | 17.3 | -1050.9 | -132.1 | 0.50 | 0.1 | 7.1 | -8.6 |
| GBPUSD | D1 | trend_vote v=4 | T | 48.0 | 1.0 | 15.2 | -862.5 | -138.1 | 0.50 | 0.1 | 7.8 | -9.5 |
| US500 | D1 | ema_x |  | 36.0 | 1.0 | 9.5 | -743.5 | -111.8 | 0.75 | 0.1 | 1.9 | -2.1 |
| US30 | H4 | squeeze_brk |  | 239.0 | 1.0 | 28.3 | -2388.3 | -212.9 | 0.25 | 0.1 | 4.7 | -5.3 |
| DE40 | D1 | don_brk |  | 98.0 | 1.0 | 12.6 | -1039.8 | -100.6 | 0.50 | 0.1 | 10.1 | -12.4 |
| DE40 | D1 | cmf_zero |  | 120.0 | 1.0 | 12.1 | -859.8 | -90.7 | 0.50 | 0.1 | -8.9 | 11.4 |
| GBPUSD | D1 | cmf_zero |  | 141.0 | 1.0 | 21.7 | -1401.3 | -112.6 | 0.25 | 0.1 | 7.7 | -9.2 |
| GBPJPY | D1 | trend_vote v=4 | T | 52.0 | 1.0 | 9.2 | -1025.5 | -111.8 | 0.50 | 0.0 | 0.4 | -0.3 |
| CADJPY | H4 | kelt_brk |  | 402.0 | 1.0 | 16.5 | -2075.3 | -306.3 | 0.25 | 0.0 | -22.5 | 28.4 |
| USDJPY | H4 | rsi_rev |  | 357.0 | 1.0 | 13.9 | -2346.8 | -217.7 | 0.25 | 0.0 | -24.4 | 30.8 |
| EURCHF | D1 | dmi_x |  | 76.0 | 1.0 | 4.1 | -724.9 | -140.9 | 0.75 | 0.0 | 4.5 | -5.5 |
| AUDUSD | D1 | kelt_brk |  | 63.0 | 1.0 | 3.5 | -641.2 | -111.7 | 0.75 | 0.0 | -0.8 | 1.0 |
| USDCAD | D1 | dmi_x |  | 64.0 | 1.0 | 5.0 | -969.2 | -93.3 | 0.50 | 0.0 | 14.8 | -18.4 |
| CHFJPY | D1 | bb_rev |  | 110.0 | 1.0 | 3.2 | -837.6 | -168.1 | 0.50 | 0.0 | -2.4 | 3.1 |
| US30 | D1 | don_rev |  | 112.0 | 1.0 | 2.8 | -839.6 | -90.8 | 0.50 | 0.0 | 2.2 | -2.7 |
| GBPCHF | D1 | trend_vote v=4 |  | 106.0 | 1.0 | 4.3 | -1986.0 | -121.2 | 0.25 | 0.0 | 23.6 | -29.4 |
| AUDUSD | H4 | bb_rev | T | 200.0 | 1.0 | 4.2 | -1763.9 | -180.7 | 0.25 | 0.0 | -12.0 | 15.1 |
| NZDJPY | H1 | mfi_rev |  | 941.0 | 0.8 | -12391.5 | -12835.8 | -304.5 |  | -0.0 | -108.6 | -120.1 |
| NZDJPY | H1 | willr_rev | T | 1549.0 | 0.8 | -21358.8 | -21586.5 | -354.7 |  | -0.0 | -154.6 | -248.5 |
| CHFJPY | H1 | don_brk |  | 2287.0 | 0.8 | -25077.0 | -25953.4 | -431.5 |  | -0.0 | -279.2 | -167.7 |
| CHFJPY | H1 | ha_flip | T | 2545.0 | 0.8 | -33911.9 | -34818.8 | -358.9 |  | -0.0 | -301.6 | -323.3 |
| CHFJPY | H1 | ha_flip |  | 9110.0 | 0.6 | -119765.7 | -120253.6 | -412.7 |  | -0.0 | -1078.3 | -1124.8 |
| CHFJPY | H1 | ema_x | T | 573.0 | 0.8 | -6965.8 | -7642.1 | -377.2 |  | -0.0 | -65.6 | -61.8 |
| CHFJPY | H1 | ema_x |  | 1026.0 | 0.8 | -10988.3 | -11940.8 | -377.2 |  | -0.0 | -119.5 | -77.1 |
| CHFJPY | H1 | ema_slope | T | 1018.0 | 0.8 | -11854.6 | -12444.0 | -369.4 |  | -0.0 | -129.7 | -82.2 |
| NZDJPY | H1 | kelt_rev |  | 1757.0 | 0.8 | -24140.9 | -24614.3 | -407.9 |  | -0.0 | -238.6 | -199.7 |
| NZDJPY | H1 | kelt_brk | T | 1209.0 | 0.8 | -14178.0 | -14662.8 | -277.1 |  | -0.0 | -159.2 | -93.1 |
| NZDJPY | H1 | kelt_brk |  | 1472.0 | 0.8 | -17141.1 | -19057.3 | -288.8 |  | -0.0 | -184.7 | -122.4 |
| NZDJPY | H1 | bb_brk | T | 1543.0 | 0.8 | -16502.0 | -17295.6 | -307.9 |  | -0.0 | -137.3 | -169.3 |
| NZDJPY | H1 | bb_brk |  | 2233.0 | 0.8 | -25876.8 | -26866.3 | -338.1 |  | -0.0 | -268.8 | -197.5 |
| NZDJPY | H1 | bb_rev | T | 818.0 | 0.8 | -11979.2 | -12161.7 | -410.7 |  | -0.0 | -66.1 | -165.5 |
| CADJPY | H1 | rsi_mom |  | 6057.0 | 0.6 | -74539.4 | -74888.9 | -411.9 |  | -0.0 | -695.4 | -669.1 |
| CADJPY | H1 | rsi_rev | T | 193.0 | 0.8 | -2539.3 | -2773.2 | -253.7 |  | -0.0 | -31.8 | -12.5 |
| CADJPY | H1 | rsi_rev |  | 1378.0 | 0.7 | -22867.6 | -24187.8 | -351.1 |  | -0.0 | -184.7 | -241.7 |
| NZDJPY | H1 | don_rev | T | 962.0 | 0.8 | -13235.5 | -13420.4 | -410.7 |  | -0.0 | -79.4 | -174.9 |
| NZDJPY | H1 | cci_mom |  | 3034.0 | 0.8 | -32624.1 | -33046.8 | -397.0 |  | -0.0 | -347.2 | -238.4 |
| NZDJPY | H1 | cci_rev | T | 1281.0 | 0.8 | -17741.7 | -17965.5 | -358.9 |  | -0.0 | -93.0 | -251.5 |
| NZDJPY | H1 | cci_rev |  | 3752.0 | 0.7 | -58775.6 | -59276.2 | -410.6 |  | -0.0 | -434.1 | -672.8 |
| NZDJPY | H1 | stoch_rev | T | 985.0 | 0.8 | -13987.1 | -14356.5 | -295.7 |  | -0.0 | -78.4 | -191.8 |
| NZDJPY | H1 | stoch_rev |  | 3109.0 | 0.7 | -52561.6 | -52720.1 | -423.7 |  | -0.0 | -407.4 | -577.3 |
| NZDJPY | H1 | macd_zero | T | 859.0 | 0.9 | -6470.7 | -7219.8 | -400.4 |  | -0.0 | -33.2 | -92.7 |
| NZDJPY | H1 | ema_x |  | 1063.0 | 0.8 | -13178.5 | -13972.4 | -334.3 |  | -0.0 | -111.9 | -132.4 |
| NZDJPY | H1 | ema_slope | T | 1057.0 | 0.8 | -11600.7 | -12382.3 | -360.2 |  | -0.0 | -80.7 | -139.1 |
| NZDJPY | H1 | ema_slope |  | 2540.0 | 0.8 | -23445.3 | -24064.8 | -392.4 |  | -0.0 | -224.4 | -203.2 |
| NZDJPY | H1 | obv_slope | T | 1973.0 | 0.8 | -26235.1 | -26803.0 | -364.1 |  | -0.0 | -184.4 | -312.2 |
| NZDJPY | H1 | obv_slope |  | 8560.0 | 0.6 | -100104.7 | -100620.2 | -423.8 |  | -0.0 | -941.4 | -889.2 |
| NZDJPY | H1 | cmf_zero | T | 1642.0 | 0.8 | -21578.1 | -22390.6 | -353.1 |  | -0.0 | -205.6 | -188.2 |
| CADJPY | H1 | bb_brk |  | 2385.0 | 0.8 | -23418.1 | -25532.9 | -441.2 |  | -0.0 | -320.6 | -80.5 |
| CADJPY | H1 | bb_rev | T | 894.0 | 0.8 | -12184.6 | -13212.6 | -315.7 |  | -0.0 | -77.8 | -154.9 |
| CADJPY | H1 | bb_rev |  | 2797.0 | 0.7 | -39981.4 | -40309.8 | -445.6 |  | -0.0 | -322.0 | -423.8 |
| CADJPY | H1 | dmi_x | T | 730.0 | 0.9 | -4664.9 | -5224.9 | -354.9 |  | -0.0 | -50.1 | -33.6 |
| NZDJPY | H1 | willr_rev |  | 4524.0 | 0.6 | -72032.6 | -72356.3 | -410.6 |  | -0.0 | -604.9 | -732.0 |
| NZDJPY | H1 | aroon_x | T | 1003.0 | 0.8 | -10645.5 | -11979.5 | -323.2 |  | -0.0 | -74.1 | -127.6 |
| NZDJPY | H1 | aroon_x |  | 2178.0 | 0.8 | -21162.9 | -22772.9 | -421.7 |  | -0.0 | -184.7 | -206.2 |
| NZDJPY | H1 | squeeze_brk | T | 717.0 | 0.8 | -6751.6 | -7021.7 | -297.8 |  | -0.0 | -83.4 | -34.7 |
| NZDJPY | H1 | squeeze_brk |  | 952.0 | 0.8 | -8700.1 | -9033.1 | -298.2 |  | -0.0 | -113.4 | -37.1 |
| NZDJPY | H1 | kelt_rev | T | 340.0 | 0.7 | -5913.3 | -5948.6 | -321.2 |  | -0.0 | -31.6 | -83.0 |
| CADJPY | H1 | stoch_rev |  | 3098.0 | 0.7 | -47860.8 | -47908.7 | -378.1 |  | -0.0 | -385.3 | -507.4 |
| CADJPY | H1 | macd_zero | T | 889.0 | 0.8 | -10225.3 | -10734.7 | -441.2 |  | -0.0 | -134.6 | -42.0 |
| CADJPY | H1 | macd_zero |  | 1866.0 | 0.8 | -23016.0 | -23616.6 | -441.2 |  | -0.0 | -283.0 | -119.8 |
| CADJPY | H1 | macd_x | T | 1617.0 | 0.8 | -19101.8 | -19803.0 | -366.4 |  | -0.0 | -182.2 | -166.5 |
| CADJPY | H1 | macd_x |  | 4257.0 | 0.7 | -52924.1 | -54112.6 | -389.7 |  | -0.0 | -502.6 | -463.8 |
| CADJPY | H1 | rsi_mom | T | 1632.0 | 0.9 | -11946.3 | -13296.1 | -339.8 |  | -0.0 | -77.1 | -150.9 |
| CADJPY | H1 | obv_slope |  | 8597.0 | 0.6 | -107019.8 | -107359.9 | -407.0 |  | -0.0 | -1116.3 | -811.0 |
| CADJPY | H1 | cmf_zero | T | 1628.0 | 0.9 | -10704.5 | -11519.9 | -361.3 |  | -0.0 | -106.4 | -87.8 |
| CADJPY | H1 | cmf_zero |  | 3227.0 | 0.8 | -27808.6 | -28697.4 | -428.7 |  | -0.0 | -263.2 | -244.9 |
| CADJPY | H1 | mfi_rev | T | 282.0 | 0.8 | -3643.1 | -4789.9 | -265.8 |  | -0.0 | -0.2 | -75.7 |
| NZDJPY | H1 | don_rev |  | 3172.0 | 0.7 | -50699.8 | -50999.4 | -436.3 |  | -0.0 | -416.2 | -527.3 |
| NZDJPY | H1 | don_brk | T | 1740.0 | 0.8 | -20512.1 | -20955.5 | -307.9 |  | -0.0 | -212.5 | -157.3 |
| NZDJPY | H1 | don_brk |  | 2352.0 | 0.8 | -25416.8 | -25978.1 | -307.9 |  | -0.0 | -274.6 | -180.6 |
| NZDJPY | H1 | ha_flip | T | 2624.0 | 0.8 | -33741.5 | -34313.9 | -395.4 |  | -0.0 | -205.0 | -442.4 |
| NZDJPY | H1 | ha_flip |  | 8911.0 | 0.6 | -117387.3 | -117732.2 | -414.5 |  | -0.0 | -1036.3 | -1128.6 |
| NZDJPY | H1 | ema_x | T | 580.0 | 0.7 | -10005.5 | -10832.0 | -321.4 |  | -0.0 | -89.5 | -94.7 |
| CADJPY | H1 | squeeze_brk |  | 987.0 | 0.8 | -12322.7 | -12597.0 | -441.2 |  | -0.0 | -135.8 | -84.2 |
| CADJPY | H1 | kelt_rev | T | 403.0 | 0.7 | -6433.4 | -6449.2 | -258.0 |  | -0.0 | -33.8 | -91.1 |
| CADJPY | H1 | kelt_rev |  | 1913.0 | 0.7 | -32533.0 | -32764.6 | -390.1 |  | -0.0 | -260.4 | -346.9 |
| CADJPY | H1 | kelt_brk | T | 1277.0 | 0.9 | -10279.9 | -12983.3 | -416.1 |  | -0.0 | -189.6 | 26.8 |
| CADJPY | H1 | kelt_brk |  | 1578.0 | 0.9 | -10939.3 | -15228.4 | -416.1 |  | -0.0 | -211.1 | 40.4 |
| CADJPY | H1 | bb_brk | T | 1618.0 | 0.8 | -16249.3 | -17314.8 | -441.2 |  | -0.0 | -183.2 | -105.7 |
| EURUSD | H1 | macd_x |  | 4372.0 | 0.8 | -45753.6 | -45887.6 | -428.2 |  | -0.0 | -418.7 | -421.2 |
| EURUSD | H1 | rsi_mom | T | 1702.0 | 0.8 | -20960.3 | -21468.8 | -392.4 |  | -0.0 | -210.9 | -168.7 |
| EURUSD | H1 | rsi_mom |  | 5985.0 | 0.7 | -64731.8 | -64864.1 | -446.3 |  | -0.0 | -493.4 | -721.6 |
| EURUSD | H1 | rsi_rev | T | 178.0 | 0.8 | -1789.2 | -3160.1 | -272.0 |  | -0.0 | -6.0 | -29.7 |
| CADJPY | H1 | dmi_x |  | 1785.0 | 0.7 | -20544.2 | -21067.0 | -361.4 |  | -0.0 | -237.2 | -126.6 |
| CADJPY | H1 | cci_mom | T | 1872.0 | 0.8 | -15660.2 | -15844.3 | -459.3 |  | -0.0 | -208.4 | -61.5 |
| CADJPY | H1 | cci_mom |  | 3110.0 | 0.8 | -34771.7 | -35317.0 | -393.8 |  | -0.0 | -455.6 | -145.4 |
| CADJPY | H1 | cci_rev | T | 1293.0 | 0.8 | -12936.9 | -14143.4 | -293.8 |  | -0.0 | -116.5 | -121.4 |
| CADJPY | H1 | cci_rev |  | 3761.0 | 0.7 | -55441.6 | -55608.2 | -357.3 |  | -0.0 | -435.1 | -602.1 |
| CADJPY | H1 | stoch_rev | T | 971.0 | 0.8 | -12746.7 | -13237.8 | -319.8 |  | -0.0 | -102.6 | -135.2 |
| CADJPY | H1 | ha_flip |  | 9021.0 | 0.6 | -123242.6 | -123559.9 | -419.1 |  | -0.0 | -1060.5 | -1219.8 |
| CADJPY | H1 | ema_x | T | 545.0 | 0.9 | -2696.9 | -4394.4 | -385.2 |  | -0.0 | -55.7 | 14.6 |
| CADJPY | H1 | ema_x |  | 992.0 | 0.9 | -6593.7 | -7962.5 | -385.2 |  | -0.0 | -88.8 | -24.6 |
| CADJPY | H1 | ema_slope | T | 1027.0 | 0.8 | -8967.3 | -9771.3 | -381.3 |  | -0.0 | -124.0 | -29.2 |
| CADJPY | H1 | ema_slope |  | 2550.0 | 0.7 | -30056.3 | -31034.8 | -412.6 |  | -0.0 | -330.8 | -205.8 |
| CADJPY | H1 | obv_slope | T | 2041.0 | 0.8 | -23072.2 | -23651.2 | -366.5 |  | -0.0 | -246.9 | -166.9 |
| EURUSD | H1 | kelt_brk |  | 1627.0 | 0.9 | -10947.2 | -12543.5 | -367.3 |  | -0.0 | -80.3 | -126.0 |
| EURUSD | H1 | bb_brk | T | 1642.0 | 0.9 | -10496.8 | -12832.9 | -283.1 |  | -0.0 | -38.5 | -169.8 |
| EURUSD | H1 | bb_brk |  | 2458.0 | 0.9 | -14123.0 | -16700.8 | -363.7 |  | -0.0 | -75.1 | -198.8 |
| EURUSD | H1 | bb_rev | T | 972.0 | 0.9 | -6700.2 | -7095.9 | -312.6 |  | -0.0 | -27.1 | -105.2 |
| CADJPY | H1 | mfi_rev |  | 1084.0 | 0.7 | -16890.9 | -17441.8 | -319.2 |  | -0.0 | -158.2 | -150.8 |
| CADJPY | H1 | willr_rev | T | 1596.0 | 0.8 | -19095.4 | -20300.4 | -334.8 |  | -0.0 | -130.6 | -231.9 |
| CADJPY | H1 | willr_rev |  | 4674.0 | 0.7 | -67207.2 | -67417.1 | -396.3 |  | -0.0 | -567.7 | -678.7 |
| CADJPY | H1 | aroon_x | T | 983.0 | 0.9 | -4471.8 | -5681.1 | -428.7 |  | -0.0 | -55.2 | -23.0 |
| CADJPY | H1 | aroon_x |  | 2126.0 | 0.8 | -16178.6 | -18507.9 | -428.7 |  | -0.0 | -243.9 | -27.1 |
| CADJPY | H1 | squeeze_brk | T | 722.0 | 0.8 | -9816.9 | -10215.3 | -441.2 |  | -0.0 | -100.2 | -77.2 |
| EURUSD | H1 | cci_rev |  | 3814.0 | 0.8 | -42378.7 | -42479.6 | -375.0 |  | -0.0 | -405.8 | -367.2 |
| EURUSD | H1 | stoch_rev | T | 974.0 | 0.8 | -10468.1 | -11539.7 | -306.4 |  | -0.0 | -83.9 | -111.4 |
| EURUSD | H1 | stoch_rev |  | 2968.0 | 0.8 | -25663.1 | -26701.1 | -377.6 |  | -0.0 | -280.1 | -178.7 |
| EURUSD | H1 | macd_zero | T | 882.0 | 0.9 | -6248.8 | -8206.1 | -315.5 |  | -0.0 | -23.3 | -100.5 |
| EURUSD | H1 | macd_zero |  | 1868.0 | 0.9 | -11011.3 | -15784.3 | -605.9 |  | -0.0 | -59.0 | -154.4 |
| EURUSD | H1 | macd_x | T | 1729.0 | 0.8 | -16933.1 | -18894.2 | -336.1 |  | -0.0 | -201.9 | -96.2 |
| EURUSD | H1 | ema_slope |  | 2530.0 | 0.8 | -16460.3 | -18579.0 | -413.3 |  | -0.0 | -99.1 | -217.0 |
| EURUSD | H1 | obv_slope | T | 2074.0 | 0.8 | -21060.6 | -22342.9 | -433.1 |  | -0.0 | -222.9 | -155.5 |
| EURUSD | H1 | obv_slope |  | 8572.0 | 0.7 | -82969.7 | -83186.4 | -570.2 |  | -0.0 | -788.3 | -726.7 |
| EURUSD | H1 | cmf_zero | T | 1835.0 | 0.8 | -19627.7 | -20638.2 | -350.6 |  | -0.0 | -186.7 | -171.6 |
| EURUSD | H1 | rsi_rev |  | 1372.0 | 0.8 | -13822.7 | -14428.0 | -350.1 |  | -0.0 | -109.8 | -148.4 |
| CADJPY | H1 | don_rev | T | 1019.0 | 0.8 | -14813.0 | -15653.9 | -334.9 |  | -0.0 | -91.0 | -192.9 |
| CADJPY | H1 | don_rev |  | 3311.0 | 0.7 | -54932.9 | -55937.3 | -448.7 |  | -0.0 | -398.7 | -637.7 |
| CADJPY | H1 | don_brk | T | 1794.0 | 0.8 | -19972.1 | -20368.2 | -441.2 |  | -0.0 | -215.9 | -141.7 |
| CADJPY | H1 | don_brk |  | 2466.0 | 0.8 | -25544.7 | -26958.5 | -441.2 |  | -0.0 | -339.2 | -101.2 |
| CADJPY | H1 | ha_flip | T | 2554.0 | 0.8 | -30060.3 | -30882.4 | -413.2 |  | -0.0 | -291.7 | -255.6 |
| EURUSD | H1 | aroon_x |  | 2086.0 | 0.9 | -5376.5 | -11895.2 | -605.9 |  | -0.0 | -8.1 | -101.7 |
| EURUSD | H1 | squeeze_brk | T | 703.0 | 0.9 | -6110.1 | -7609.8 | -292.8 |  | -0.0 | -27.0 | -93.0 |
| EURUSD | H1 | squeeze_brk |  | 981.0 | 0.9 | -8245.3 | -9948.4 | -292.8 |  | -0.0 | -50.2 | -108.0 |
| EURUSD | H1 | kelt_rev | T | 409.0 | 0.9 | -3492.0 | -4396.7 | -279.3 |  | -0.0 | -22.2 | -44.6 |
| EURUSD | H1 | kelt_rev |  | 1910.0 | 0.8 | -16933.7 | -18553.3 | -350.1 |  | -0.0 | -141.6 | -172.9 |
| EURUSD | H1 | kelt_brk | T | 1310.0 | 0.9 | -6723.3 | -9676.6 | -268.5 |  | -0.0 | -10.0 | -127.4 |
| USDJPY | H1 | macd_zero |  | 1839.0 | 0.9 | -10331.4 | -12174.0 | -466.3 |  | -0.0 | -90.7 | -100.0 |
| USDJPY | H1 | macd_x | T | 1557.0 | 0.8 | -15490.3 | -16037.5 | -353.2 |  | -0.0 | -119.8 | -170.5 |
| USDJPY | H1 | macd_x |  | 4153.0 | 0.8 | -32210.7 | -33027.4 | -425.7 |  | -0.0 | -240.9 | -364.9 |
| USDJPY | H1 | rsi_mom | T | 1559.0 | 0.9 | -10901.1 | -11357.5 | -417.9 |  | -0.0 | -95.4 | -105.9 |
| EURUSD | H1 | bb_rev |  | 2866.0 | 0.8 | -26153.7 | -27406.3 | -417.5 |  | -0.0 | -247.4 | -230.4 |
| EURUSD | H1 | dmi_x | T | 767.0 | 0.8 | -9900.4 | -10062.4 | -346.8 |  | -0.0 | -77.6 | -107.7 |
| EURUSD | H1 | dmi_x |  | 1895.0 | 0.8 | -20790.6 | -22185.2 | -605.9 |  | -0.0 | -190.4 | -191.2 |
| EURUSD | H1 | cci_mom | T | 1914.0 | 0.8 | -18852.8 | -19997.7 | -329.8 |  | -0.0 | -122.3 | -237.4 |
| EURUSD | H1 | cci_mom |  | 3201.0 | 0.8 | -28576.8 | -29935.3 | -605.9 |  | -0.0 | -192.7 | -350.4 |
| EURUSD | H1 | cci_rev | T | 1378.0 | 0.8 | -16514.2 | -16972.0 | -357.3 |  | -0.0 | -158.5 | -142.6 |
| EURUSD | H1 | don_brk |  | 2432.0 | 0.9 | -17728.2 | -19782.0 | -354.7 |  | -0.0 | -85.1 | -261.1 |
| EURUSD | H1 | ha_flip | T | 2612.0 | 0.8 | -23835.8 | -25589.8 | -392.6 |  | -0.0 | -184.9 | -261.6 |
| EURUSD | H1 | ha_flip |  | 9019.0 | 0.7 | -89291.5 | -89415.7 | -449.8 |  | -0.0 | -820.2 | -817.9 |
| EURUSD | H1 | ema_x | T | 551.0 | 0.9 | -2812.9 | -4318.1 | -295.5 |  | -0.0 | -25.0 | -26.8 |
| EURUSD | H1 | ema_x |  | 1030.0 | 0.9 | -2867.9 | -6014.4 | -361.3 |  | -0.0 | -39.5 | -9.6 |
| EURUSD | H1 | ema_slope | T | 1018.0 | 0.8 | -9947.1 | -10582.0 | -382.6 |  | -0.0 | -67.0 | -122.1 |
| USDJPY | H1 | kelt_rev |  | 1889.0 | 0.8 | -17260.3 | -18650.2 | -343.4 |  | -0.0 | -140.0 | -181.7 |
| USDJPY | H1 | kelt_brk | T | 1302.0 | 0.9 | -8888.3 | -10118.5 | -348.8 |  | -0.0 | -92.2 | -68.0 |
| USDJPY | H1 | kelt_brk |  | 1574.0 | 0.9 | -8838.8 | -10249.9 | -348.8 |  | -0.0 | -111.6 | -42.3 |
| USDJPY | H1 | bb_brk | T | 1593.0 | 0.9 | -8111.6 | -11844.3 | -357.5 |  | -0.0 | -104.4 | -36.3 |
| EURUSD | H1 | cmf_zero |  | 3618.0 | 0.8 | -41029.8 | -41892.5 | -411.9 |  | -0.0 | -417.9 | -323.7 |
| EURUSD | H1 | mfi_rev | T | 391.0 | 0.6 | -9105.3 | -9321.9 | -222.6 |  | -0.0 | -80.3 | -87.6 |
| EURUSD | H1 | mfi_rev |  | 1255.0 | 0.8 | -13753.0 | -14253.0 | -340.1 |  | -0.0 | -129.2 | -122.3 |
| EURUSD | H1 | willr_rev | T | 1768.0 | 0.8 | -22041.1 | -22715.5 | -442.4 |  | -0.0 | -205.6 | -197.9 |
| EURUSD | H1 | willr_rev |  | 4931.0 | 0.8 | -52627.9 | -53725.7 | -442.4 |  | -0.0 | -492.7 | -470.3 |
| EURUSD | H1 | aroon_x | T | 985.0 | 0.9 | -5007.4 | -8588.6 | -400.8 |  | -0.0 | -10.3 | -91.3 |
| USDJPY | H1 | cci_mom |  | 3094.0 | 0.8 | -24819.8 | -26736.9 | -466.4 |  | -0.0 | -279.4 | -162.1 |
| USDJPY | H1 | cci_rev | T | 1262.0 | 0.9 | -10168.3 | -10700.0 | -333.9 |  | -0.0 | -39.2 | -162.0 |
| USDJPY | H1 | cci_rev |  | 3721.0 | 0.8 | -33409.9 | -34971.9 | -369.2 |  | -0.0 | -249.8 | -378.5 |
| USDJPY | H1 | stoch_rev | T | 934.0 | 0.8 | -11197.4 | -11659.7 | -306.1 |  | -0.0 | -68.0 | -146.9 |
| USDJPY | H1 | stoch_rev |  | 3044.0 | 0.8 | -38124.7 | -39357.2 | -378.1 |  | -0.0 | -334.1 | -369.7 |
| USDJPY | H1 | macd_zero | T | 856.0 | 0.9 | -4756.9 | -7608.3 | -348.8 |  | -0.0 | -18.5 | -75.6 |
| USDJPY | H1 | ema_x |  | 1029.0 | 1.0 | -1054.4 | -5909.6 | -357.7 |  | -0.0 | -53.6 | 46.2 |
| USDJPY | H1 | ema_slope | T | 995.0 | 0.9 | -3958.3 | -6902.0 | -417.9 |  | -0.0 | -30.0 | -44.3 |
| USDJPY | H1 | ema_slope |  | 2538.0 | 0.8 | -18485.8 | -20608.8 | -405.2 |  | -0.0 | -196.0 | -136.0 |
| USDJPY | H1 | obv_slope | T | 1990.0 | 0.8 | -23950.2 | -24272.5 | -368.8 |  | -0.0 | -230.6 | -205.9 |
| USDJPY | H1 | rsi_mom |  | 5934.0 | 0.7 | -55120.7 | -55485.2 | -419.3 |  | -0.0 | -560.4 | -436.2 |
| USDJPY | H1 | rsi_rev | T | 176.0 | 0.7 | -3826.9 | -4239.5 | -292.4 |  | -0.0 | -14.2 | -61.7 |
| USDJPY | H1 | rsi_rev |  | 1406.0 | 0.8 | -18124.6 | -19393.4 | -379.5 |  | -0.0 | -137.6 | -202.7 |
| EURUSD | H1 | don_rev | T | 1012.0 | 0.7 | -16586.5 | -17058.7 | -351.0 |  | -0.0 | -122.4 | -190.1 |
| EURUSD | H1 | don_rev |  | 3169.0 | 0.8 | -40717.6 | -41010.4 | -412.6 |  | -0.0 | -410.9 | -326.0 |
| EURUSD | H1 | don_brk | T | 1748.0 | 0.9 | -12649.9 | -14590.9 | -304.1 |  | -0.0 | -56.2 | -192.2 |
| USDJPY | H1 | willr_rev |  | 4586.0 | 0.7 | -52274.0 | -53056.8 | -405.7 |  | -0.0 | -427.6 | -545.6 |
| USDJPY | H1 | aroon_x | T | 1016.0 | 1.0 | -783.3 | -4699.6 | -357.5 |  | -0.0 | -9.8 | -3.9 |
| USDJPY | H1 | aroon_x |  | 2204.0 | 0.9 | -8487.8 | -10952.6 | -466.3 |  | -0.0 | -88.7 | -64.1 |
| USDJPY | H1 | squeeze_brk | T | 733.0 | 0.9 | -3696.0 | -4841.9 | -357.5 |  | -0.0 | -46.8 | -17.5 |
| USDJPY | H1 | squeeze_brk |  | 959.0 | 1.0 | -2581.9 | -4239.1 | -357.5 |  | -0.0 | -50.5 | 10.4 |
| USDJPY | H1 | kelt_rev | T | 361.0 | 0.7 | -5370.1 | -5797.8 | -274.7 |  | -0.0 | -28.4 | -75.7 |
| EURGBP | H1 | stoch_rev |  | 2772.0 | 0.8 | -26242.4 | -26810.7 | -405.8 |  | -0.0 | -219.7 | -267.5 |
| EURGBP | H1 | macd_zero | T | 903.0 | 0.8 | -10711.9 | -11298.1 | -461.1 |  | -0.0 | -71.4 | -132.4 |
| EURGBP | H1 | macd_zero |  | 1895.0 | 0.8 | -22083.7 | -22643.3 | -461.1 |  | -0.0 | -187.3 | -222.1 |
| EURGBP | H1 | macd_x | T | 1658.0 | 0.8 | -16800.9 | -19319.9 | -461.0 |  | -0.0 | -132.7 | -181.4 |
| USDJPY | H1 | bb_brk |  | 2303.0 | 0.9 | -15586.7 | -17483.2 | -466.3 |  | -0.0 | -202.5 | -67.3 |
| USDJPY | H1 | bb_rev | T | 827.0 | 0.8 | -9846.7 | -10556.9 | -336.8 |  | -0.0 | -62.8 | -125.4 |
| USDJPY | H1 | bb_rev |  | 2730.0 | 0.8 | -29237.0 | -30939.2 | -368.1 |  | -0.0 | -173.3 | -388.8 |
| USDJPY | H1 | dmi_x | T | 783.0 | 0.8 | -8709.7 | -9148.6 | -357.5 |  | -0.0 | -66.4 | -97.1 |
| USDJPY | H1 | dmi_x |  | 1927.0 | 0.8 | -18268.5 | -18342.2 | -384.0 |  | -0.0 | -182.4 | -148.8 |
| USDJPY | H1 | cci_mom | T | 1869.0 | 0.9 | -11576.7 | -12519.4 | -357.5 |  | -0.0 | -90.6 | -126.0 |
| USDJPY | H1 | don_rev |  | 3148.0 | 0.8 | -37854.1 | -39629.1 | -412.0 |  | -0.0 | -305.1 | -400.9 |
| USDJPY | H1 | don_brk | T | 1807.0 | 0.9 | -10799.0 | -13887.8 | -357.5 |  | -0.0 | -167.3 | -12.3 |
| USDJPY | H1 | don_brk |  | 2424.0 | 0.9 | -12752.2 | -16463.8 | -361.0 |  | -0.0 | -235.2 | 33.3 |
| USDJPY | H1 | ha_flip | T | 2624.0 | 0.8 | -28810.1 | -29960.9 | -379.0 |  | -0.0 | -278.5 | -246.3 |
| USDJPY | H1 | ha_flip |  | 9102.0 | 0.7 | -90131.6 | -90219.9 | -400.7 |  | -0.0 | -886.2 | -751.6 |
| USDJPY | H1 | ema_x | T | 559.0 | 1.0 | -696.6 | -3951.3 | -357.7 |  | -0.0 | -21.9 | 13.3 |
| EURGBP | H1 | kelt_rev | T | 372.0 | 0.9 | -2215.9 | -4701.8 | -320.2 |  | -0.0 | 14.8 | -65.0 |
| EURGBP | H1 | kelt_rev |  | 1776.0 | 0.8 | -16554.8 | -16761.2 | -388.6 |  | -0.0 | -146.3 | -158.9 |
| EURGBP | H1 | kelt_brk | T | 1218.0 | 0.8 | -12563.7 | -14403.7 | -313.3 |  | -0.0 | -70.0 | -172.8 |
| EURGBP | H1 | kelt_brk |  | 1504.0 | 0.8 | -16046.8 | -18034.5 | -321.6 |  | -0.0 | -94.7 | -214.0 |
| USDJPY | H1 | obv_slope |  | 8587.0 | 0.7 | -81226.3 | -81735.6 | -426.9 |  | -0.0 | -802.3 | -672.7 |
| USDJPY | H1 | cmf_zero | T | 1648.0 | 0.9 | -9732.4 | -11374.6 | -365.9 |  | -0.0 | -87.8 | -91.2 |
| USDJPY | H1 | cmf_zero |  | 3110.0 | 0.9 | -20331.0 | -22777.8 | -466.7 |  | -0.0 | -250.1 | -105.8 |
| USDJPY | H1 | mfi_rev | T | 249.0 | 0.6 | -5589.5 | -6213.2 | -198.9 |  | -0.0 | -46.7 | -57.0 |
| USDJPY | H1 | mfi_rev |  | 1002.0 | 0.7 | -17430.0 | -18335.0 | -320.7 |  | -0.0 | -140.7 | -184.4 |
| USDJPY | H1 | willr_rev | T | 1538.0 | 0.8 | -18390.9 | -18846.1 | -333.9 |  | -0.0 | -129.0 | -219.3 |
| EURGBP | H1 | dmi_x |  | 1867.0 | 0.7 | -22251.9 | -22906.5 | -391.1 |  | -0.0 | -219.9 | -184.1 |
| EURGBP | H1 | cci_mom | T | 1871.0 | 0.8 | -25904.3 | -26667.4 | -445.1 |  | -0.0 | -205.7 | -278.2 |
| EURGBP | H1 | cci_mom |  | 3236.0 | 0.7 | -45781.2 | -46473.9 | -445.1 |  | -0.0 | -434.0 | -402.2 |
| EURGBP | H1 | cci_rev | T | 1326.0 | 0.8 | -13386.8 | -15932.9 | -445.1 |  | -0.0 | -104.7 | -145.9 |
| EURGBP | H1 | cci_rev |  | 3751.0 | 0.8 | -34108.1 | -34443.1 | -445.1 |  | -0.0 | -285.9 | -347.3 |
| EURGBP | H1 | stoch_rev | T | 895.0 | 0.8 | -10501.1 | -11251.9 | -312.6 |  | -0.0 | -73.6 | -125.2 |
| EURGBP | H1 | ema_x | T | 599.0 | 0.9 | -2787.0 | -3486.2 | -296.1 |  | -0.0 | -13.1 | -41.4 |
| EURGBP | H1 | ema_x |  | 1030.0 | 0.9 | -7426.9 | -8732.1 | -432.1 |  | -0.0 | -80.7 | -52.1 |
| EURGBP | H1 | ema_slope | T | 1068.0 | 0.8 | -13966.0 | -14623.9 | -444.5 |  | -0.0 | -104.9 | -157.6 |
| EURGBP | H1 | ema_slope |  | 2583.0 | 0.7 | -29336.0 | -29399.5 | -444.5 |  | -0.0 | -266.3 | -272.8 |
| EURGBP | H1 | macd_x |  | 4388.0 | 0.8 | -42439.8 | -42947.2 | -445.1 |  | -0.0 | -353.8 | -434.5 |
| EURGBP | H1 | rsi_mom | T | 1662.0 | 0.8 | -21022.0 | -21816.3 | -445.1 |  | -0.0 | -156.5 | -239.1 |
| EURGBP | H1 | rsi_mom |  | 6195.0 | 0.6 | -72973.1 | -73250.3 | -430.1 |  | -0.0 | -623.6 | -727.8 |
| EURGBP | H1 | rsi_rev |  | 1342.0 | 0.8 | -11547.9 | -11934.7 | -341.4 |  | -0.0 | -85.1 | -132.5 |
| USDJPY | H1 | don_rev | T | 912.0 | 0.8 | -10004.0 | -11020.8 | -329.4 |  | -0.0 | -54.0 | -139.7 |
| EURGBP | H1 | mfi_rev |  | 1179.0 | 0.8 | -10588.6 | -11397.0 | -278.0 |  | -0.0 | -78.9 | -120.3 |
| EURGBP | H1 | willr_rev | T | 1736.0 | 0.8 | -17577.3 | -19423.2 | -445.1 |  | -0.0 | -136.8 | -192.3 |
| EURGBP | H1 | willr_rev |  | 4832.0 | 0.7 | -57269.0 | -57808.6 | -382.2 |  | -0.0 | -442.7 | -630.6 |
| EURGBP | H1 | aroon_x | T | 1034.0 | 0.8 | -13253.6 | -15460.9 | -461.1 |  | -0.0 | -76.5 | -178.9 |
| EURGBP | H1 | aroon_x |  | 2169.0 | 0.7 | -27878.2 | -28057.3 | -461.1 |  | -0.0 | -218.3 | -303.4 |
| EURGBP | H1 | squeeze_brk | T | 686.0 | 0.8 | -6400.2 | -6424.4 | -243.1 |  | -0.0 | -55.2 | -63.2 |
| EURGBP | H1 | squeeze_brk |  | 977.0 | 0.8 | -12379.7 | -12404.0 | -264.2 |  | -0.0 | -119.2 | -106.4 |
| EURCHF | H1 | stoch_rev | T | 885.0 | 0.8 | -10628.4 | -11989.3 | -279.5 |  | -0.0 | -79.7 | -120.1 |
| EURCHF | H1 | stoch_rev |  | 2714.0 | 0.8 | -28525.3 | -30276.1 | -364.1 |  | -0.0 | -234.4 | -296.4 |
| EURCHF | H1 | macd_zero | T | 971.0 | 0.7 | -18671.8 | -19810.2 | -347.4 |  | -0.0 | -195.8 | -140.1 |
| EURCHF | H1 | macd_zero |  | 1954.0 | 0.7 | -34861.7 | -35124.9 | -374.4 |  | -0.0 | -339.2 | -295.2 |
| EURGBP | H1 | bb_brk | T | 1702.0 | 0.8 | -21112.2 | -22025.0 | -461.1 |  | -0.0 | -159.0 | -237.8 |
| EURGBP | H1 | bb_brk |  | 2564.0 | 0.8 | -31472.0 | -32086.8 | -461.1 |  | -0.0 | -301.5 | -272.5 |
| EURGBP | H1 | bb_rev | T | 965.0 | 0.8 | -8604.9 | -10245.0 | -402.7 |  | -0.0 | -51.4 | -114.0 |
| EURGBP | H1 | bb_rev |  | 2945.0 | 0.9 | -21693.7 | -22096.7 | -402.7 |  | -0.0 | -187.6 | -213.6 |
| EURGBP | H1 | dmi_x | T | 770.0 | 0.8 | -9832.5 | -10578.9 | -295.7 |  | -0.0 | -117.0 | -56.2 |
| EURCHF | H1 | rsi_rev |  | 1124.0 | 0.8 | -10870.1 | -11810.9 | -372.8 |  | -0.0 | -61.5 | -148.3 |
| EURGBP | H1 | don_rev | T | 984.0 | 0.8 | -10668.9 | -12092.6 | -295.1 |  | -0.0 | -26.0 | -189.2 |
| EURGBP | H1 | don_rev |  | 3112.0 | 0.9 | -23223.0 | -24984.4 | -414.5 |  | -0.0 | -189.3 | -243.2 |
| EURGBP | H1 | don_brk | T | 1740.0 | 0.8 | -19970.4 | -20790.4 | -395.0 |  | -0.0 | -168.6 | -201.8 |
| EURGBP | H1 | don_brk |  | 2423.0 | 0.8 | -32173.3 | -32342.1 | -395.0 |  | -0.0 | -278.4 | -316.5 |
| EURGBP | H1 | ha_flip | T | 2521.0 | 0.8 | -28839.3 | -31513.7 | -444.5 |  | -0.0 | -232.1 | -305.8 |
| EURGBP | H1 | ha_flip |  | 9049.0 | 0.7 | -98510.1 | -98701.4 | -444.6 |  | -0.0 | -912.2 | -893.1 |
| EURCHF | H1 | cmf_zero |  | 3366.0 | 0.6 | -65641.4 | -65965.9 | -385.3 |  | -0.0 | -645.0 | -547.9 |
| EURCHF | H1 | mfi_rev | T | 310.0 | 0.9 | -1790.3 | -3149.5 | -249.6 |  | -0.0 | -22.2 | -9.1 |
| EURCHF | H1 | mfi_rev |  | 1084.0 | 0.7 | -15948.7 | -16777.8 | -361.0 |  | -0.0 | -137.2 | -157.9 |
| EURCHF | H1 | willr_rev | T | 1594.0 | 0.8 | -21972.0 | -23191.0 | -374.2 |  | -0.0 | -228.7 | -167.1 |
| EURGBP | H1 | obv_slope | T | 2041.0 | 0.8 | -27391.3 | -28315.5 | -444.6 |  | -0.0 | -220.9 | -290.0 |
| EURGBP | H1 | obv_slope |  | 8861.0 | 0.6 | -95978.5 | -95988.5 | -431.5 |  | -0.0 | -801.1 | -981.4 |
| EURGBP | H1 | cmf_zero | T | 1747.0 | 0.8 | -20956.6 | -23259.0 | -592.8 |  | -0.0 | -155.1 | -239.4 |
| EURGBP | H1 | cmf_zero |  | 3450.0 | 0.7 | -42829.7 | -43041.4 | -592.8 |  | -0.0 | -493.6 | -265.0 |
| EURGBP | H1 | mfi_rev | T | 365.0 | 0.8 | -3622.2 | -6586.2 | -268.4 |  | -0.0 | -21.5 | -48.1 |
| EURCHF | H1 | bb_rev |  | 2787.0 | 0.7 | -36480.1 | -36899.8 | -343.9 |  | -0.0 | -325.1 | -346.9 |
| EURCHF | H1 | dmi_x | T | 734.0 | 0.6 | -16106.1 | -16610.9 | -319.3 |  | -0.0 | -180.0 | -106.8 |
| EURCHF | H1 | dmi_x |  | 1758.0 | 0.6 | -36438.0 | -36726.3 | -388.3 |  | -0.0 | -358.2 | -303.9 |
| EURCHF | H1 | cci_mom | T | 1904.0 | 0.6 | -42380.1 | -42808.0 | -373.5 |  | -0.0 | -394.6 | -381.5 |
| EURCHF | H1 | cci_mom |  | 3146.0 | 0.6 | -67798.0 | -68271.3 | -392.8 |  | -0.0 | -615.1 | -630.7 |
| EURCHF | H1 | cci_rev | T | 1262.0 | 0.7 | -19977.1 | -21336.7 | -316.5 |  | -0.0 | -227.7 | -126.8 |
| EURCHF | H1 | cci_rev |  | 3714.0 | 0.7 | -53387.0 | -53555.2 | -346.7 |  | -0.0 | -482.4 | -499.1 |
| GBPCHF | H1 | rsi_mom |  | 6352.0 | 0.6 | -80105.5 | -80301.9 | -400.6 |  | -0.0 | -720.7 | -753.0 |
| GBPCHF | H1 | rsi_rev | T | 192.0 | 0.8 | -1901.1 | -2637.5 | -237.8 |  | -0.0 | -7.6 | -30.0 |
| GBPCHF | H1 | rsi_rev |  | 1282.0 | 0.8 | -16506.5 | -16827.3 | -306.7 |  | -0.0 | -138.8 | -167.5 |
| EURCHF | H1 | don_rev | T | 883.0 | 0.8 | -11672.7 | -12530.1 | -342.2 |  | -0.0 | -139.5 | -65.9 |
| EURCHF | H1 | macd_x | T | 1704.0 | 0.7 | -30969.2 | -31497.5 | -361.2 |  | -0.0 | -293.0 | -272.9 |
| EURCHF | H1 | macd_x |  | 4590.0 | 0.6 | -81963.7 | -82114.5 | -428.7 |  | -0.0 | -736.4 | -771.7 |
| EURCHF | H1 | rsi_mom | T | 1830.0 | 0.7 | -34963.3 | -35653.0 | -361.3 |  | -0.0 | -363.1 | -267.0 |
| EURCHF | H1 | rsi_mom |  | 6733.0 | 0.5 | -124191.2 | -124723.4 | -440.3 |  | -0.0 | -1161.8 | -1110.9 |
| CADJPY | H4 | trend_vote v=6 | T | 360.0 | 0.9 | -1721.3 | -2654.5 | -202.4 |  | -0.0 | -15.7 | -16.3 |
| CADJPY | H4 | trend_vote v=6 |  | 465.0 | 0.9 | -3502.3 | -3926.3 | -202.4 |  | -0.0 | -32.2 | -32.7 |
| CADJPY | H4 | trend_vote v=5 | T | 330.0 | 0.9 | -1933.8 | -2451.7 | -226.8 |  | -0.0 | -19.2 | -16.3 |
| NZDJPY | D1 | trend_vote v=6 | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| NZDJPY | D1 | trend_vote v=6 |  | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| NZDJPY | D1 | trend_vote v=5 | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| GBPCHF | H1 | bb_brk |  | 2493.0 | 0.8 | -29104.2 | -29257.1 | -419.7 |  | -0.0 | -209.4 | -340.2 |
| GBPCHF | H1 | bb_rev | T | 937.0 | 0.9 | -4906.3 | -7822.0 | -285.5 |  | -0.0 | 17.7 | -124.8 |
| GBPCHF | H1 | bb_rev |  | 2861.0 | 0.8 | -27752.9 | -28219.3 | -348.5 |  | -0.0 | -254.1 | -255.3 |
| GBPCHF | H1 | dmi_x | T | 767.0 | 0.8 | -7508.7 | -10625.7 | -335.7 |  | -0.0 | -21.8 | -128.8 |
| EURCHF | H1 | willr_rev |  | 4625.0 | 0.7 | -65730.2 | -65846.9 | -398.7 |  | -0.0 | -547.7 | -673.4 |
| EURCHF | H1 | aroon_x | T | 1082.0 | 0.7 | -21506.2 | -22634.0 | -267.2 |  | -0.0 | -234.5 | -150.0 |
| EURCHF | H1 | aroon_x |  | 2286.0 | 0.6 | -40984.7 | -41484.8 | -331.4 |  | -0.0 | -394.4 | -352.7 |
| EURCHF | H1 | squeeze_brk | T | 674.0 | 0.6 | -15040.3 | -15701.5 | -260.9 |  | -0.0 | -130.8 | -147.1 |
| EURCHF | H1 | squeeze_brk |  | 903.0 | 0.7 | -18638.3 | -19474.2 | -279.7 |  | -0.0 | -170.6 | -171.5 |
| EURCHF | H1 | kelt_rev | T | 306.0 | 0.8 | -3238.4 | -4442.2 | -313.3 |  | -0.0 | -29.8 | -29.6 |
| EURCHF | H1 | kelt_rev |  | 1525.0 | 0.8 | -16963.6 | -17241.9 | -400.1 |  | -0.0 | -146.4 | -167.4 |
| EURCHF | H1 | kelt_brk | T | 1094.0 | 0.6 | -24866.0 | -25717.4 | -655.4 |  | -0.0 | -273.8 | -170.1 |
| EURCHF | H1 | kelt_brk |  | 1304.0 | 0.6 | -28801.3 | -29554.6 | -655.4 |  | -0.0 | -282.2 | -241.4 |
| EURCHF | H1 | bb_brk | T | 1664.0 | 0.6 | -39425.4 | -40055.3 | -655.4 |  | -0.0 | -399.6 | -313.6 |
| EURCHF | H1 | bb_brk |  | 2438.0 | 0.6 | -57324.6 | -57836.6 | -344.0 |  | -0.0 | -508.5 | -548.0 |
| EURCHF | H1 | bb_rev | T | 912.0 | 0.8 | -11941.7 | -13351.1 | -274.8 |  | -0.0 | -144.5 | -65.2 |
| GBPCHF | H1 | obv_slope |  | 8846.0 | 0.6 | -107028.7 | -107329.5 | -418.1 |  | -0.0 | -910.6 | -1072.6 |
| GBPCHF | H1 | cmf_zero | T | 1718.0 | 0.8 | -22641.5 | -23465.6 | -357.0 |  | -0.0 | -152.9 | -277.4 |
| GBPCHF | H1 | cmf_zero |  | 3486.0 | 0.7 | -51682.3 | -51770.1 | -395.4 |  | -0.0 | -526.7 | -407.4 |
| GBPCHF | H1 | mfi_rev | T | 349.0 | 1.0 | -83.4 | -2475.3 | -239.8 |  | -0.0 | 33.5 | -44.3 |
| EURCHF | H1 | don_rev |  | 3000.0 | 0.8 | -38319.7 | -38732.9 | -390.5 |  | -0.0 | -312.7 | -400.9 |
| EURCHF | H1 | don_brk | T | 1667.0 | 0.6 | -39303.1 | -39837.7 | -655.4 |  | -0.0 | -387.8 | -326.0 |
| EURCHF | H1 | don_brk |  | 2213.0 | 0.6 | -51359.7 | -52005.3 | -655.4 |  | -0.0 | -503.6 | -430.0 |
| EURCHF | H1 | ha_flip | T | 2562.0 | 0.7 | -45930.1 | -46869.1 | -627.4 |  | -0.0 | -489.5 | -334.8 |
| EURCHF | H1 | ha_flip |  | 9119.0 | 0.5 | -151463.5 | -152275.5 | -627.4 |  | -0.0 | -1310.2 | -1490.5 |
| EURCHF | H1 | ema_x | T | 687.0 | 0.7 | -13627.5 | -13864.6 | -338.2 |  | -0.0 | -132.3 | -115.8 |
| EURCHF | H1 | ema_x |  | 1166.0 | 0.6 | -24461.0 | -24661.9 | -357.1 |  | -0.0 | -210.7 | -241.9 |
| EURCHF | H1 | ema_slope | T | 1202.0 | 0.6 | -24746.4 | -25816.5 | -392.1 |  | -0.0 | -289.7 | -147.4 |
| EURCHF | H1 | ema_slope |  | 2826.0 | 0.5 | -59443.7 | -59765.6 | -450.4 |  | -0.0 | -626.9 | -441.7 |
| EURCHF | H1 | obv_slope | T | 2112.0 | 0.7 | -34535.5 | -35127.8 | -655.4 |  | -0.0 | -311.8 | -323.2 |
| EURCHF | H1 | obv_slope |  | 8854.0 | 0.5 | -150381.2 | -150457.4 | -641.4 |  | -0.0 | -1391.1 | -1365.0 |
| EURCHF | H1 | cmf_zero | T | 1695.0 | 0.7 | -33848.6 | -34094.1 | -328.1 |  | -0.0 | -331.4 | -284.0 |
| GBPCHF | H4 | macd_x |  | 1117.0 | 0.8 | -9014.7 | -10275.5 | -247.0 |  | -0.0 | -99.2 | -61.7 |
| GBPCHF | H4 | rsi_mom | T | 396.0 | 0.8 | -4288.0 | -4866.8 | -288.8 |  | -0.0 | -10.5 | -76.0 |
| GBPCHF | H4 | rsi_mom |  | 1484.0 | 0.8 | -9509.5 | -9994.0 | -300.3 |  | -0.0 | -55.0 | -128.2 |
| GBPCHF | H4 | rsi_rev |  | 356.0 | 0.7 | -5738.1 | -6208.5 | -256.7 |  | -0.0 | -87.9 | -7.9 |
| GBPCHF | H1 | dmi_x |  | 1828.0 | 0.7 | -22346.6 | -22945.9 | -347.8 |  | -0.0 | -197.8 | -214.2 |
| GBPCHF | H1 | cci_mom | T | 1892.0 | 0.8 | -20764.4 | -22771.1 | -382.8 |  | -0.0 | -75.5 | -336.7 |
| GBPCHF | H1 | cci_mom |  | 3233.0 | 0.7 | -44540.9 | -44649.1 | -395.5 |  | -0.0 | -344.2 | -490.5 |
| GBPCHF | H1 | cci_rev | T | 1335.0 | 0.9 | -10183.5 | -12698.6 | -290.5 |  | -0.0 | -23.7 | -182.1 |
| GBPCHF | H1 | cci_rev |  | 3828.0 | 0.7 | -47659.7 | -48144.4 | -394.5 |  | -0.0 | -407.3 | -475.3 |
| GBPCHF | H1 | stoch_rev | T | 904.0 | 0.9 | -6170.5 | -9215.0 | -290.1 |  | -0.0 | 17.7 | -151.1 |
| GBPCHF | H1 | stoch_rev |  | 2761.0 | 0.8 | -31236.9 | -31954.9 | -323.6 |  | -0.0 | -230.2 | -358.2 |
| GBPCHF | H1 | macd_zero | T | 902.0 | 0.9 | -6762.6 | -7551.0 | -385.9 |  | -0.0 | -28.2 | -105.1 |
| GBPCHF | H1 | macd_zero |  | 1930.0 | 0.8 | -21310.1 | -21865.6 | -399.7 |  | -0.0 | -155.6 | -246.3 |
| GBPCHF | H1 | macd_x | T | 1660.0 | 0.9 | -12243.4 | -13812.5 | -368.1 |  | -0.0 | -42.0 | -201.7 |
| GBPCHF | H1 | macd_x |  | 4479.0 | 0.7 | -52420.2 | -52441.0 | -387.3 |  | -0.0 | -370.4 | -621.4 |
| GBPCHF | H1 | rsi_mom | T | 1684.0 | 0.9 | -12522.1 | -17019.9 | -362.4 |  | -0.0 | -9.2 | -249.2 |
| GBPCHF | H4 | bb_brk | T | 401.0 | 0.9 | -2956.8 | -5041.5 | -225.4 |  | -0.0 | 15.5 | -81.3 |
| GBPCHF | H4 | bb_brk |  | 548.0 | 0.9 | -2521.9 | -4338.3 | -266.2 |  | -0.0 | -7.5 | -43.0 |
| GBPCHF | H4 | bb_rev | T | 194.0 | 0.8 | -2549.5 | -3116.7 | -185.3 |  | -0.0 | -29.8 | -15.2 |
| GBPCHF | H4 | bb_rev |  | 656.0 | 0.8 | -8808.7 | -9179.0 | -256.8 |  | -0.0 | -106.5 | -48.2 |
| GBPCHF | H1 | mfi_rev |  | 1171.0 | 0.9 | -7466.6 | -8593.3 | -279.3 |  | -0.0 | -56.8 | -83.3 |
| GBPCHF | H1 | willr_rev | T | 1660.0 | 0.8 | -14917.1 | -16104.1 | -362.4 |  | -0.0 | -73.8 | -217.0 |
| GBPCHF | H1 | willr_rev |  | 4752.0 | 0.7 | -56987.8 | -57739.8 | -434.7 |  | -0.0 | -496.8 | -555.9 |
| GBPCHF | H1 | aroon_x | T | 1004.0 | 0.9 | -5115.3 | -7700.9 | -293.8 |  | -0.0 | 0.1 | -106.7 |
| GBPCHF | H1 | aroon_x |  | 2157.0 | 0.8 | -21799.4 | -22285.6 | -389.4 |  | -0.0 | -190.2 | -212.4 |
| GBPCHF | H1 | squeeze_brk | T | 731.0 | 0.8 | -7007.1 | -8532.2 | -281.3 |  | -0.0 | -15.5 | -126.3 |
| GBPCHF | H1 | squeeze_brk |  | 965.0 | 0.8 | -10612.4 | -11137.5 | -297.4 |  | -0.0 | -76.2 | -124.2 |
| GBPCHF | H1 | kelt_rev | T | 358.0 | 0.8 | -3051.9 | -4875.5 | -289.9 |  | -0.0 | 5.9 | -71.1 |
| GBPCHF | H1 | kelt_rev |  | 1680.0 | 0.8 | -21514.6 | -21905.1 | -334.9 |  | -0.0 | -172.6 | -228.9 |
| GBPCHF | H1 | kelt_brk | T | 1184.0 | 0.8 | -12921.4 | -13764.1 | -379.7 |  | -0.0 | -83.5 | -163.1 |
| GBPCHF | H1 | kelt_brk |  | 1446.0 | 0.8 | -17051.9 | -17723.8 | -385.9 |  | -0.0 | -137.7 | -180.2 |
| GBPCHF | H1 | bb_brk | T | 1661.0 | 0.8 | -15303.2 | -17086.9 | -379.7 |  | -0.0 | -70.9 | -228.8 |
| GBPCHF | H4 | obv_slope |  | 2246.0 | 0.7 | -14223.3 | -15167.3 | -308.3 |  | -0.0 | -92.2 | -179.1 |
| GBPCHF | H4 | cmf_zero | T | 422.0 | 0.8 | -4929.9 | -6644.7 | -190.2 |  | -0.0 | -18.4 | -79.4 |
| GBPCHF | H4 | cmf_zero |  | 824.0 | 0.8 | -8790.5 | -10765.8 | -237.9 |  | -0.0 | -50.0 | -119.6 |
| GBPCHF | H4 | mfi_rev |  | 254.0 | 0.7 | -4270.9 | -4788.5 | -170.3 |  | -0.0 | -57.2 | -16.3 |
| GBPCHF | H1 | don_rev | T | 935.0 | 0.9 | -5095.0 | -7140.7 | -382.3 |  | -0.0 | 3.6 | -110.7 |
| GBPCHF | H1 | don_rev |  | 3072.0 | 0.8 | -37382.8 | -38276.7 | -382.3 |  | -0.0 | -322.0 | -369.5 |
| GBPCHF | H1 | don_brk | T | 1721.0 | 0.8 | -17360.6 | -18082.6 | -379.7 |  | -0.0 | -112.8 | -218.4 |
| GBPCHF | H1 | don_brk |  | 2354.0 | 0.8 | -26746.7 | -27354.2 | -352.1 |  | -0.0 | -242.3 | -249.3 |
| GBPCHF | H1 | ha_flip | T | 2560.0 | 0.8 | -25044.8 | -27014.5 | -370.6 |  | -0.0 | -175.8 | -298.4 |
| GBPCHF | H1 | ha_flip |  | 9174.0 | 0.6 | -113539.1 | -114054.4 | -386.2 |  | -0.0 | -956.0 | -1150.5 |
| GBPCHF | H1 | ema_x | T | 582.0 | 0.8 | -7474.0 | -7840.1 | -335.3 |  | -0.0 | -34.1 | -112.4 |
| GBPCHF | H1 | ema_x |  | 1008.0 | 0.8 | -13675.9 | -14296.9 | -337.7 |  | -0.0 | -65.4 | -201.8 |
| GBPCHF | H1 | ema_slope | T | 1026.0 | 0.8 | -9666.6 | -11666.2 | -385.9 |  | -0.0 | -45.8 | -143.2 |
| GBPCHF | H1 | ema_slope |  | 2580.0 | 0.7 | -29220.7 | -29607.4 | -397.0 |  | -0.0 | -190.8 | -366.3 |
| GBPCHF | H1 | obv_slope | T | 2002.0 | 0.8 | -16415.7 | -17883.0 | -379.7 |  | -0.0 | -53.7 | -273.8 |
| GBPCHF | H4 | kelt_brk |  | 356.0 | 1.0 | 254.3 | -3258.7 | -241.4 |  | 0.0 | 28.4 | -30.8 |
| AUDCAD | H1 | rsi_mom |  | 6692.0 | 0.5 | -116476.0 | -116530.7 | -399.0 |  | -0.0 | -1178.1 | -929.4 |
| AUDCAD | H1 | rsi_rev | T | 149.0 | 0.8 | -1517.5 | -2939.9 | -219.8 |  | -0.0 | -27.6 | 3.4 |
| AUDCAD | H1 | rsi_rev |  | 1156.0 | 0.7 | -19222.9 | -21342.6 | -346.6 |  | -0.0 | -207.3 | -137.0 |
| GBPCHF | H4 | don_rev | T | 234.0 | 0.8 | -2460.2 | -2910.2 | -185.3 |  | -0.0 | -38.0 | -3.0 |
| GBPCHF | H4 | dmi_x | T | 182.0 | 0.8 | -2266.4 | -2780.7 | -160.9 |  | -0.0 | -3.7 | -42.5 |
| GBPCHF | H4 | dmi_x |  | 465.0 | 0.9 | -2277.8 | -3565.6 | -251.6 |  | -0.0 | -18.9 | -23.5 |
| GBPCHF | H4 | cci_mom | T | 468.0 | 1.0 | -1194.1 | -4732.9 | -224.8 |  | -0.0 | 37.9 | -73.0 |
| GBPCHF | H4 | cci_mom |  | 750.0 | 0.9 | -2710.0 | -5518.4 | -266.3 |  | -0.0 | 20.8 | -82.9 |
| GBPCHF | H4 | cci_rev | T | 313.0 | 0.8 | -2974.0 | -3574.3 | -188.0 |  | -0.0 | -35.2 | -17.3 |
| GBPCHF | H4 | cci_rev |  | 940.0 | 0.8 | -7387.0 | -8016.8 | -337.2 |  | -0.0 | -119.7 | -1.7 |
| GBPCHF | H4 | stoch_rev |  | 810.0 | 0.9 | -4226.5 | -7500.1 | -256.7 |  | -0.0 | -108.8 | 50.2 |
| GBPCHF | H4 | macd_zero | T | 214.0 | 0.8 | -2545.4 | -3563.3 | -184.8 |  | -0.0 | 4.4 | -58.7 |
| GBPCHF | H4 | macd_zero |  | 463.0 | 0.9 | -2755.1 | -4682.2 | -277.4 |  | -0.0 | 1.3 | -59.1 |
| GBPCHF | H4 | macd_x | T | 443.0 | 0.8 | -3956.7 | -4692.5 | -218.9 |  | -0.0 | -23.1 | -53.1 |
| GBPCHF | H4 | ema_slope |  | 640.0 | 0.8 | -4611.4 | -5140.2 | -283.4 |  | -0.0 | -34.3 | -52.5 |
| GBPCHF | H4 | obv_slope | T | 522.0 | 0.8 | -6163.4 | -6649.8 | -194.7 |  | -0.0 | -33.7 | -85.6 |
| AUDCAD | H1 | bb_brk |  | 2263.0 | 0.7 | -44925.0 | -44956.7 | -379.4 |  | -0.0 | -416.6 | -406.5 |
| AUDCAD | H1 | bb_rev | T | 836.0 | 0.7 | -13265.8 | -13905.6 | -288.7 |  | -0.0 | -138.8 | -100.0 |
| AUDCAD | H1 | bb_rev |  | 2661.0 | 0.7 | -39306.9 | -40569.0 | -425.0 |  | -0.0 | -363.9 | -356.4 |
| AUDCAD | H1 | dmi_x | T | 714.0 | 0.6 | -17470.3 | -18003.3 | -272.7 |  | -0.0 | -173.8 | -143.1 |
| GBPCHF | H4 | willr_rev | T | 377.0 | 0.9 | -2948.8 | -4003.2 | -198.8 |  | -0.0 | -39.3 | -11.5 |
| GBPCHF | H4 | willr_rev |  | 1131.0 | 0.7 | -13395.6 | -13679.6 | -296.9 |  | -0.0 | -189.0 | -38.9 |
| GBPCHF | H4 | aroon_x | T | 249.0 | 0.7 | -3990.4 | -4319.1 | -173.2 |  | -0.0 | -8.5 | -72.3 |
| GBPCHF | H4 | aroon_x |  | 542.0 | 0.8 | -6599.7 | -6896.3 | -283.3 |  | -0.0 | -52.1 | -71.3 |
| GBPCHF | H4 | kelt_rev | T | 81.0 | 0.7 | -1678.7 | -2545.4 | -163.3 |  | -0.0 | -32.1 | 5.9 |
| GBPCHF | H4 | kelt_rev |  | 445.0 | 0.8 | -6397.9 | -6912.3 | -256.7 |  | -0.0 | -98.6 | -8.0 |
| GBPCHF | H4 | kelt_brk | T | 295.0 | 1.0 | 6.0 | -2633.2 | -185.1 |  | 0.0 | 29.8 | -37.7 |
| AUDCAD | H1 | macd_zero |  | 2020.0 | 0.6 | -37847.3 | -37914.8 | -383.4 |  | -0.0 | -376.5 | -310.1 |
| AUDCAD | H1 | macd_x | T | 1661.0 | 0.7 | -26902.2 | -27318.3 | -335.5 |  | -0.0 | -265.9 | -222.5 |
| AUDCAD | H1 | macd_x |  | 4468.0 | 0.6 | -76086.5 | -76888.4 | -418.1 |  | -0.0 | -798.3 | -570.6 |
| AUDCAD | H1 | rsi_mom | T | 1755.0 | 0.7 | -24973.8 | -25223.1 | -353.0 |  | -0.0 | -258.7 | -191.5 |
| AUDCAD | H1 | obv_slope |  | 9223.0 | 0.5 | -154723.9 | -154895.8 | -428.6 |  | -0.0 | -1572.2 | -1225.4 |
| AUDCAD | H1 | cmf_zero | T | 1751.0 | 0.7 | -35639.5 | -35990.1 | -378.9 |  | -0.0 | -373.4 | -267.9 |
| AUDCAD | H1 | cmf_zero |  | 3450.0 | 0.6 | -63608.9 | -64286.8 | -378.9 |  | -0.0 | -620.8 | -536.2 |
| AUDCAD | H1 | mfi_rev | T | 278.0 | 0.7 | -5518.6 | -5933.1 | -250.9 |  | -0.0 | -45.8 | -56.8 |
| GBPCHF | H4 | don_rev |  | 797.0 | 0.8 | -8905.0 | -9481.4 | -256.7 |  | -0.0 | -138.0 | -10.1 |
| GBPCHF | H4 | don_brk | T | 427.0 | 0.9 | -2316.3 | -4356.8 | -185.1 |  | -0.0 | 24.2 | -79.0 |
| GBPCHF | H4 | don_brk |  | 572.0 | 0.9 | -4181.1 | -5922.5 | -283.3 |  | -0.0 | -2.2 | -84.4 |
| GBPCHF | H4 | ha_flip | T | 651.0 | 0.9 | -4969.3 | -5566.5 | -209.5 |  | -0.0 | -33.7 | -60.7 |
| GBPCHF | H4 | ha_flip |  | 2237.0 | 0.8 | -15397.8 | -16764.8 | -251.0 |  | -0.0 | -140.7 | -142.0 |
| GBPCHF | H4 | ema_x | T | 146.0 | 0.9 | -651.9 | -2418.3 | -168.3 |  | -0.0 | 21.9 | -41.4 |
| GBPCHF | H4 | ema_x |  | 261.0 | 1.0 | -559.4 | -2942.5 | -238.6 |  | -0.0 | 27.6 | -46.7 |
| GBPCHF | H4 | ema_slope | T | 276.0 | 0.7 | -5061.1 | -5222.5 | -193.5 |  | -0.0 | -18.2 | -82.2 |
| AUDCAD | H1 | kelt_rev |  | 1586.0 | 0.8 | -22651.1 | -25535.8 | -333.3 |  | -0.0 | -190.5 | -229.8 |
| AUDCAD | H1 | kelt_brk | T | 1115.0 | 0.7 | -22163.1 | -22210.3 | -272.3 |  | -0.0 | -203.8 | -202.8 |
| AUDCAD | H1 | kelt_brk |  | 1330.0 | 0.7 | -26629.2 | -26655.8 | -314.8 |  | -0.0 | -239.8 | -250.0 |
| AUDCAD | H1 | bb_brk | T | 1590.0 | 0.7 | -31525.0 | -31647.8 | -298.5 |  | -0.0 | -299.2 | -276.6 |
| AUDCAD | H4 | rsi_mom |  | 1463.0 | 0.7 | -13722.3 | -14567.5 | -260.9 |  | -0.0 | -186.9 | -64.5 |
| AUDCAD | H1 | dmi_x |  | 1806.0 | 0.6 | -33112.7 | -33509.9 | -335.1 |  | -0.0 | -326.4 | -275.0 |
| AUDCAD | H1 | cci_mom | T | 1849.0 | 0.7 | -34103.7 | -34248.5 | -354.9 |  | -0.0 | -338.1 | -280.9 |
| AUDCAD | H1 | cci_mom |  | 3068.0 | 0.7 | -55209.4 | -55241.1 | -377.9 |  | -0.0 | -548.2 | -453.5 |
| AUDCAD | H1 | cci_rev | T | 1319.0 | 0.7 | -19197.7 | -19333.5 | -301.5 |  | -0.0 | -171.6 | -181.8 |
| AUDCAD | H1 | cci_rev |  | 3796.0 | 0.6 | -63128.4 | -63924.2 | -384.8 |  | -0.0 | -610.4 | -539.4 |
| AUDCAD | H1 | stoch_rev | T | 1012.0 | 0.7 | -18961.1 | -19170.2 | -360.8 |  | -0.0 | -184.8 | -160.1 |
| AUDCAD | H1 | stoch_rev |  | 3059.0 | 0.7 | -50492.7 | -51484.8 | -360.8 |  | -0.0 | -517.6 | -394.2 |
| AUDCAD | H1 | macd_zero | T | 936.0 | 0.7 | -17428.7 | -17822.7 | -344.8 |  | -0.0 | -190.8 | -120.7 |
| AUDCAD | H1 | ema_x |  | 1168.0 | 0.6 | -24913.2 | -25143.9 | -387.3 |  | -0.0 | -217.9 | -242.1 |
| AUDCAD | H1 | ema_slope | T | 1117.0 | 0.7 | -18085.7 | -18410.8 | -347.9 |  | -0.0 | -204.7 | -116.7 |
| AUDCAD | H1 | ema_slope |  | 2847.0 | 0.6 | -49993.4 | -50025.2 | -379.2 |  | -0.0 | -488.5 | -420.8 |
| AUDCAD | H1 | obv_slope | T | 2079.0 | 0.7 | -35396.4 | -35562.8 | -357.0 |  | -0.0 | -380.9 | -253.4 |
| AUDCAD | H4 | bb_brk |  | 487.0 | 0.8 | -5941.5 | -6913.8 | -206.4 |  | -0.0 | -82.9 | -24.6 |
| AUDCAD | H4 | bb_rev |  | 578.0 | 0.9 | -3624.9 | -5087.3 | -221.6 |  | -0.0 | -29.2 | -51.3 |
| AUDCAD | H4 | dmi_x |  | 403.0 | 0.8 | -3345.6 | -5090.4 | -270.9 |  | -0.0 | -55.9 | 1.8 |
| AUDCAD | H1 | mfi_rev |  | 982.0 | 0.7 | -14288.5 | -16815.8 | -259.0 |  | -0.0 | -133.6 | -127.9 |
| AUDCAD | H1 | willr_rev | T | 1591.0 | 0.7 | -22898.8 | -23097.2 | -336.2 |  | -0.0 | -247.1 | -163.1 |
| AUDCAD | H1 | willr_rev |  | 4639.0 | 0.6 | -72067.7 | -73118.4 | -385.6 |  | -0.0 | -668.9 | -651.3 |
| AUDCAD | H1 | aroon_x | T | 1067.0 | 0.7 | -20182.7 | -20284.3 | -395.4 |  | -0.0 | -198.6 | -168.0 |
| AUDCAD | H1 | aroon_x |  | 2296.0 | 0.6 | -43835.8 | -44413.0 | -395.4 |  | -0.0 | -397.3 | -408.3 |
| AUDCAD | H1 | squeeze_brk | T | 710.0 | 0.7 | -14462.6 | -14690.2 | -264.2 |  | -0.0 | -132.7 | -132.7 |
| AUDCAD | H1 | squeeze_brk |  | 965.0 | 0.7 | -19470.3 | -19501.5 | -300.2 |  | -0.0 | -194.9 | -157.9 |
| AUDCAD | H1 | kelt_rev | T | 310.0 | 0.7 | -4533.8 | -5114.4 | -213.0 |  | -0.0 | -37.0 | -47.5 |
| AUDCAD | H4 | stoch_rev |  | 667.0 | 0.8 | -5357.8 | -6977.6 | -192.7 |  | -0.0 | -68.1 | -33.5 |
| AUDCAD | H4 | macd_zero |  | 454.0 | 0.9 | -3048.7 | -3846.8 | -256.4 |  | -0.0 | -46.2 | -6.3 |
| AUDCAD | H4 | macd_x |  | 1024.0 | 0.8 | -8411.8 | -8610.9 | -265.8 |  | -0.0 | -114.7 | -39.3 |
| AUDCAD | H4 | willr_rev | T | 336.0 | 1.0 | 522.9 | -2655.4 | -209.5 |  | 0.0 | -37.2 | 77.6 |
| AUDCAD | H4 | willr_rev |  | 1006.0 | 0.8 | -7408.4 | -8622.5 | -236.1 |  | -0.0 | -109.8 | -19.7 |
| AUDCAD | H4 | aroon_x |  | 522.0 | 0.8 | -4213.1 | -4750.0 | -269.2 |  | -0.0 | -45.8 | -39.4 |
| AUDCAD | H4 | squeeze_brk | T | 154.0 | 0.7 | -2515.9 | -2676.4 | -185.1 |  | -0.0 | -30.6 | -18.1 |
| AUDCAD | H1 | don_rev | T | 1009.0 | 0.8 | -14455.5 | -14885.3 | -345.3 |  | -0.0 | -148.7 | -112.2 |
| AUDCAD | H1 | don_rev |  | 3171.0 | 0.7 | -47413.2 | -48402.0 | -373.5 |  | -0.0 | -453.3 | -411.7 |
| AUDCAD | H1 | don_brk | T | 1695.0 | 0.7 | -29406.0 | -29475.1 | -294.7 |  | -0.0 | -275.1 | -263.0 |
| AUDCAD | H1 | don_brk |  | 2317.0 | 0.7 | -43671.2 | -43671.2 | -325.1 |  | -0.0 | -435.6 | -356.2 |
| AUDCAD | H1 | ha_flip | T | 2580.0 | 0.7 | -46805.8 | -47274.9 | -358.8 |  | -0.0 | -483.0 | -361.3 |
| AUDCAD | H1 | ha_flip |  | 9016.0 | 0.5 | -143496.0 | -143512.8 | -442.7 |  | -0.0 | -1470.0 | -1121.4 |
| AUDCAD | H1 | ema_x | T | 636.0 | 0.7 | -12260.5 | -12478.1 | -320.8 |  | -0.0 | -121.7 | -100.7 |
| AUDCAD | H4 | squeeze_brk |  | 213.0 | 0.7 | -3766.7 | -3977.4 | -185.1 |  | -0.0 | -44.4 | -29.3 |
| AUDCAD | H4 | kelt_rev |  | 358.0 | 1.0 | -932.3 | -2493.7 | -185.6 |  | -0.0 | -12.2 | -5.2 |
| AUDCAD | H4 | kelt_brk | T | 246.0 | 0.8 | -3066.4 | -3305.1 | -248.9 |  | -0.0 | -41.2 | -15.4 |
| AUDCAD | H4 | kelt_brk |  | 298.0 | 0.8 | -3632.5 | -3881.3 | -296.9 |  | -0.0 | -39.8 | -33.5 |
| AUDCAD | H4 | bb_brk | T | 347.0 | 0.8 | -3938.4 | -4650.9 | -185.2 |  | -0.0 | -63.9 | -1.2 |
| CHFJPY | H4 | trend_vote v=6 | T | 371.0 | 0.8 | -3342.8 | -4511.8 | -196.4 |  | -0.0 | -25.5 | -37.8 |
| CHFJPY | H4 | trend_vote v=6 |  | 454.0 | 0.8 | -4696.5 | -5677.4 | -196.4 |  | -0.0 | -43.5 | -43.5 |
| CHFJPY | H4 | trend_vote v=5 | T | 346.0 | 0.9 | -2019.8 | -2656.8 | -182.5 |  | -0.0 | -10.4 | -29.1 |
| US30 | H1 | cci_rev |  | 3325.0 | 0.9 | -12209.4 | -13489.1 | -402.4 |  | -0.0 | -133.4 | -87.6 |
| AUDCAD | H4 | cci_mom | T | 393.0 | 0.9 | -1265.0 | -3123.7 | -187.9 |  | -0.0 | -37.8 | 28.8 |
| AUDCAD | H4 | cci_mom |  | 669.0 | 0.8 | -5931.5 | -6274.8 | -264.0 |  | -0.0 | -65.0 | -54.6 |
| AUDCAD | H4 | cci_rev |  | 839.0 | 0.9 | -5155.6 | -6516.3 | -190.0 |  | -0.0 | -67.8 | -28.4 |
| AUDCAD | H4 | stoch_rev | T | 207.0 | 0.7 | -3111.9 | -3837.1 | -192.7 |  | -0.0 | -52.3 | 2.2 |
| AUDCAD | H4 | ha_flip |  | 2052.0 | 0.7 | -19623.7 | -20131.1 | -279.2 |  | -0.0 | -196.9 | -211.5 |
| AUDCAD | H4 | ema_x |  | 266.0 | 0.8 | -3498.4 | -3962.3 | -206.3 |  | -0.0 | -43.2 | -24.0 |
| AUDCAD | H4 | ema_slope |  | 633.0 | 0.9 | -3523.8 | -4399.1 | -279.7 |  | -0.0 | -53.5 | -7.2 |
| AUDCAD | H4 | obv_slope | T | 457.0 | 0.9 | -3381.0 | -4377.4 | -219.6 |  | -0.0 | -58.2 | 4.8 |
| AUDCAD | H4 | obv_slope |  | 2156.0 | 0.6 | -21283.1 | -21578.5 | -395.5 |  | -0.0 | -266.2 | -140.1 |
| AUDCAD | H4 | cmf_zero |  | 737.0 | 0.8 | -5788.5 | -6410.6 | -223.8 |  | -0.0 | -47.9 | -79.7 |
| AUDCAD | H4 | don_brk | T | 371.0 | 0.7 | -5680.9 | -6216.6 | -185.2 |  | -0.0 | -63.3 | -50.5 |
| AUDCAD | H4 | don_brk |  | 497.0 | 0.8 | -7047.8 | -7592.2 | -215.8 |  | -0.0 | -76.0 | -66.9 |
| AUDCAD | H4 | ha_flip | T | 536.0 | 1.0 | -923.9 | -2796.5 | -224.2 |  | -0.0 | -17.5 | 3.9 |
| US30 | H1 | aroon_x |  | 1782.0 | 0.9 | -6336.4 | -7762.8 | -442.1 |  | -0.0 | -59.5 | -57.6 |
| NZDJPY | H4 | trend_vote v=6 | T | 349.0 | 0.8 | -4819.3 | -5129.9 | -165.5 |  | -0.0 | -32.4 | -59.2 |
| NZDJPY | H4 | trend_vote v=6 |  | 441.0 | 0.9 | -3028.2 | -4174.3 | -166.4 |  | -0.0 | -17.5 | -40.8 |
| NZDJPY | H4 | trend_vote v=5 | T | 308.0 | 0.9 | -2246.2 | -2841.8 | -176.1 |  | -0.0 | -26.1 | -13.7 |
| NZDJPY | H4 | trend_vote v=5 |  | 500.0 | 1.0 | 221.7 | -2467.6 | -199.0 |  | 0.0 | 5.1 | -1.9 |
| NZDJPY | H4 | trend_vote v=4 | T | 301.0 | 0.7 | -4331.1 | -4752.9 | -236.4 |  | -0.0 | -24.8 | -58.7 |
| NZDJPY | H4 | trend_vote v=4 |  | 659.0 | 0.8 | -4568.0 | -5815.6 | -226.7 |  | -0.0 | -18.7 | -71.4 |
| US30 | H1 | cci_mom | T | 1695.0 | 0.9 | -5889.1 | -8321.3 | -352.9 |  | -0.0 | -60.4 | -47.1 |
| US30 | H1 | cci_mom |  | 2812.0 | 0.9 | -15279.0 | -15705.4 | -436.3 |  | -0.0 | -134.9 | -149.7 |
| US30 | H1 | cci_rev | T | 1164.0 | 0.9 | -4652.7 | -6116.8 | -340.2 |  | -0.0 | -22.4 | -69.0 |
| US30 | H1 | don_brk |  | 2157.0 | 0.9 | -6309.6 | -7731.6 | -442.1 |  | -0.0 | -39.4 | -82.2 |
| US30 | H1 | ha_flip | T | 2289.0 | 0.9 | -5952.2 | -8043.3 | -468.7 |  | -0.0 | -62.4 | -45.9 |
| US30 | H1 | stoch_rev | T | 762.0 | 0.9 | -3282.2 | -4982.0 | -328.8 |  | -0.0 | -43.5 | -14.0 |
| US30 | H1 | stoch_rev |  | 2538.0 | 0.9 | -13667.4 | -14831.2 | -426.1 |  | -0.0 | -210.1 | -22.1 |
| US30 | H1 | macd_zero | T | 757.0 | 1.0 | 100.4 | -3002.9 | -352.4 |  | 0.0 | -8.6 | 12.8 |
| US30 | H1 | macd_zero |  | 1592.0 | 0.9 | -4106.8 | -5158.7 | -442.1 |  | -0.0 | -22.8 | -57.0 |
| US30 | H1 | macd_x | T | 1447.0 | 0.9 | -4232.5 | -9595.1 | -336.8 |  | -0.0 | 19.0 | -111.9 |
| US30 | H1 | macd_x |  | 3628.0 | 0.9 | -10894.8 | -12858.9 | -421.8 |  | -0.0 | -100.6 | -101.2 |
| US30 | H1 | rsi_mom | T | 1419.0 | 0.9 | -5286.3 | -8034.4 | -365.2 |  | -0.0 | -62.5 | -32.1 |
| US30 | H1 | rsi_mom |  | 4952.0 | 0.8 | -22274.3 | -22468.0 | -414.7 |  | -0.0 | -280.2 | -113.8 |
| US30 | H1 | rsi_rev | T | 170.0 | 0.9 | -972.7 | -2543.4 | -197.2 |  | -0.0 | 4.3 | -25.6 |
| US30 | H1 | rsi_rev |  | 1217.0 | 0.9 | -5729.7 | -8214.2 | -370.8 |  | -0.0 | -45.7 | -62.2 |
| AUDCAD | H4 | don_rev |  | 704.0 | 0.8 | -5798.3 | -6993.5 | -201.5 |  | -0.0 | -69.0 | -44.2 |
| US30 | H1 | willr_rev | T | 1438.0 | 0.9 | -7126.1 | -12128.3 | -422.5 |  | -0.0 | -107.6 | -13.9 |
| US30 | H1 | willr_rev |  | 4156.0 | 0.9 | -14491.7 | -20278.4 | -436.9 |  | -0.0 | -215.6 | -32.4 |
| US30 | H1 | aroon_x | T | 886.0 | 0.9 | -5406.4 | -6848.4 | -295.3 |  | -0.0 | -68.7 | -26.7 |
| US30 | H4 | cci_rev |  | 876.0 | 0.9 | -3699.2 | -3962.3 | -227.1 |  | -0.0 | -45.9 | -19.7 |
| US30 | H1 | squeeze_brk |  | 910.0 | 1.0 | 1326.6 | -3742.8 | -348.9 |  | 0.0 | 64.4 | -52.8 |
| US30 | H1 | kelt_rev | T | 386.0 | 1.0 | -892.9 | -2401.3 | -281.1 |  | -0.0 | 8.4 | -29.2 |
| US30 | H1 | kelt_rev |  | 1725.0 | 0.9 | -9064.8 | -10328.3 | -360.8 |  | -0.0 | -53.7 | -121.8 |
| US30 | H1 | kelt_brk | T | 1166.0 | 1.0 | -1781.0 | -3716.8 | -445.2 |  | -0.0 | -37.6 | 9.9 |
| US30 | H1 | kelt_brk |  | 1457.0 | 1.0 | -927.6 | -3377.7 | -397.9 |  | -0.0 | -16.7 | 1.6 |
| US30 | H1 | bb_brk | T | 1464.0 | 0.9 | -7546.1 | -8794.2 | -320.5 |  | -0.0 | -120.8 | -6.2 |
| US30 | H1 | bb_brk |  | 2159.0 | 0.9 | -9051.6 | -9949.8 | -442.1 |  | -0.0 | -110.5 | -50.4 |
| US30 | H1 | bb_rev | T | 791.0 | 1.0 | 127.4 | -4022.0 | -424.6 |  | 0.0 | -27.8 | 37.4 |
| US30 | H1 | bb_rev |  | 2477.0 | 0.9 | -8898.7 | -10762.2 | -383.5 |  | -0.0 | -107.9 | -50.5 |
| US30 | H1 | dmi_x | T | 690.0 | 0.9 | -3477.5 | -3901.4 | -328.8 |  | -0.0 | -26.0 | -39.9 |
| US30 | H1 | dmi_x |  | 1690.0 | 0.9 | -4619.6 | -5251.8 | -442.1 |  | -0.0 | -81.3 | 5.4 |
| US30 | H1 | don_brk | T | 1578.0 | 1.0 | -4232.2 | -6703.3 | -445.2 |  | -0.0 | -56.8 | -17.1 |
| US30 | H4 | willr_rev |  | 1045.0 | 0.9 | -4241.9 | -5408.2 | -257.9 |  | -0.0 | -20.6 | -62.6 |
| US30 | H1 | ha_flip |  | 7666.0 | 0.9 | -28359.2 | -28806.3 | -406.0 |  | -0.0 | -356.0 | -145.8 |
| US30 | H1 | ema_x | T | 516.0 | 0.9 | -4124.1 | -4898.1 | -445.2 |  | -0.0 | -37.8 | -38.7 |
| US30 | H1 | ema_x |  | 894.0 | 0.9 | -6855.6 | -7624.2 | -445.2 |  | -0.0 | -72.7 | -51.9 |
| US30 | H1 | ema_slope | T | 922.0 | 1.0 | -1760.9 | -5047.4 | -353.7 |  | -0.0 | -61.1 | 39.7 |
| US30 | H1 | ema_slope |  | 2189.0 | 0.9 | -9754.3 | -10529.0 | -442.1 |  | -0.0 | -113.1 | -61.8 |
| US30 | H1 | obv_slope | T | 1787.0 | 1.0 | -1394.3 | -8449.3 | -363.6 |  | -0.0 | 6.0 | -36.6 |
| US30 | H1 | obv_slope |  | 7153.0 | 0.9 | -26080.3 | -26611.4 | -425.1 |  | -0.0 | -307.1 | -159.5 |
| US30 | H1 | cmf_zero | T | 1448.0 | 0.9 | -4121.9 | -7053.4 | -354.6 |  | -0.0 | -90.1 | 26.7 |
| US30 | H1 | cmf_zero |  | 2848.0 | 1.0 | -6210.7 | -8096.3 | -400.3 |  | -0.0 | -73.5 | -37.6 |
| US30 | H1 | mfi_rev | T | 336.0 | 0.9 | -1155.5 | -3130.1 | -194.7 |  | -0.0 | -8.2 | -13.8 |
| US30 | H1 | mfi_rev |  | 1162.0 | 0.9 | -4985.7 | -7840.1 | -290.1 |  | -0.0 | -82.0 | -1.4 |
| US30 | H4 | ha_flip |  | 1935.0 | 0.9 | -6093.2 | -7111.1 | -298.9 |  | -0.0 | -25.6 | -95.0 |
| US30 | H4 | ema_slope |  | 590.0 | 0.9 | -2192.6 | -3110.9 | -300.3 |  | -0.0 | -18.6 | -22.5 |
| US30 | H4 | stoch_rev | T | 207.0 | 0.8 | -1737.2 | -2943.4 | -227.1 |  | -0.0 | -17.1 | -14.8 |
| US30 | H4 | stoch_rev |  | 741.0 | 0.8 | -6018.8 | -6794.4 | -227.1 |  | -0.0 | -45.5 | -68.5 |
| US30 | H4 | macd_x |  | 972.0 | 1.0 | -1584.6 | -2697.5 | -300.3 |  | -0.0 | -29.6 | 4.0 |
| US30 | H4 | rsi_mom |  | 1309.0 | 0.9 | -3555.9 | -5271.0 | -337.4 |  | -0.0 | -76.4 | 21.4 |
| US30 | H4 | rsi_rev |  | 325.0 | 0.9 | -2450.0 | -3285.1 | -182.3 |  | -0.0 | -15.0 | -32.2 |
| US30 | H1 | don_rev | T | 832.0 | 1.0 | 161.5 | -4519.5 | -337.2 |  | 0.0 | -32.4 | 43.8 |
| US30 | H1 | don_rev |  | 2757.0 | 0.9 | -8662.7 | -15458.3 | -398.1 |  | -0.0 | -177.7 | 41.6 |
| US500 | H1 | cci_rev |  | 3337.0 | 0.8 | -24194.2 | -25425.8 | -399.9 |  | -0.0 | -237.8 | -206.7 |
| US500 | H1 | stoch_rev | T | 792.0 | 0.9 | -5628.7 | -7308.1 | -394.2 |  | -0.0 | -72.6 | -26.5 |
| US500 | H1 | stoch_rev |  | 2601.0 | 0.9 | -17131.1 | -18993.4 | -434.3 |  | -0.0 | -240.8 | -55.9 |
| US500 | H1 | macd_zero | T | 808.0 | 0.9 | -3650.9 | -5724.1 | -361.8 |  | -0.0 | -66.2 | 6.7 |
| US500 | H1 | macd_zero |  | 1622.0 | 0.8 | -15995.8 | -16391.9 | -389.5 |  | -0.0 | -183.1 | -104.4 |
| US500 | H1 | macd_x | T | 1430.0 | 0.9 | -6179.8 | -9108.9 | -425.9 |  | -0.0 | -72.0 | -38.7 |
| US30 | H4 | kelt_rev |  | 468.0 | 0.8 | -5216.7 | -5753.3 | -223.0 |  | -0.0 | -50.3 | -45.8 |
| US30 | H4 | bb_rev |  | 622.0 | 0.9 | -2411.7 | -3257.0 | -223.0 |  | -0.0 | -33.2 | -8.7 |
| US30 | H4 | don_rev |  | 759.0 | 0.9 | -2500.0 | -3993.5 | -215.0 |  | -0.0 | -49.1 | 9.3 |
| US500 | H1 | squeeze_brk |  | 904.0 | 1.0 | -2048.0 | -4470.3 | -312.4 |  | -0.0 | -19.7 | -18.0 |
| US500 | H1 | kelt_rev | T | 419.0 | 0.9 | -2942.0 | -4259.3 | -361.5 |  | -0.0 | -35.2 | -17.3 |
| US500 | H1 | kelt_rev |  | 1782.0 | 0.9 | -10966.0 | -13746.5 | -386.9 |  | -0.0 | -44.3 | -173.0 |
| US500 | H1 | kelt_brk | T | 1195.0 | 0.9 | -6345.5 | -8570.4 | -466.6 |  | -0.0 | -105.5 | -0.4 |
| US500 | H1 | kelt_brk |  | 1516.0 | 0.9 | -9005.1 | -10483.4 | -466.6 |  | -0.0 | -100.3 | -62.2 |
| US30 | H4 | obv_slope | T | 441.0 | 1.0 | -750.1 | -3261.3 | -237.7 |  | -0.0 | 5.5 | -22.6 |
| US30 | H4 | willr_rev | T | 359.0 | 0.8 | -3313.5 | -4090.1 | -223.5 |  | -0.0 | -19.5 | -44.7 |
| US500 | H1 | dmi_x |  | 1657.0 | 0.8 | -12463.4 | -13351.3 | -349.9 |  | -0.0 | -163.8 | -54.9 |
| US500 | H1 | cci_mom | T | 1709.0 | 0.9 | -12304.2 | -13677.5 | -330.6 |  | -0.0 | -157.1 | -60.0 |
| US500 | H1 | cci_mom |  | 2817.0 | 0.8 | -28922.2 | -29203.1 | -396.2 |  | -0.0 | -292.8 | -236.6 |
| US500 | H1 | cci_rev | T | 1202.0 | 0.9 | -9873.1 | -10646.7 | -393.9 |  | -0.0 | -106.9 | -72.0 |
| US500 | H1 | ha_flip |  | 7582.0 | 0.8 | -56030.1 | -56697.1 | -414.3 |  | -0.0 | -717.6 | -270.3 |
| US500 | H1 | ema_x | T | 529.0 | 0.9 | -4329.3 | -7018.5 | -394.7 |  | -0.0 | -97.5 | 31.7 |
| US500 | H1 | ema_x |  | 908.0 | 0.8 | -8270.0 | -10890.6 | -394.7 |  | -0.0 | -157.9 | 25.1 |
| US500 | H1 | ema_slope | T | 927.0 | 0.9 | -3776.2 | -7250.8 | -355.8 |  | -0.0 | -99.8 | 46.1 |
| US500 | H1 | ema_slope |  | 2137.0 | 0.8 | -16248.4 | -16612.2 | -441.1 |  | -0.0 | -260.0 | -13.6 |
| US500 | H1 | obv_slope | T | 1816.0 | 0.8 | -17851.6 | -19178.9 | -384.0 |  | -0.0 | -195.0 | -128.2 |
| US500 | H1 | macd_x |  | 3546.0 | 0.9 | -19894.6 | -20175.6 | -429.5 |  | -0.0 | -281.6 | -62.4 |
| US500 | H1 | rsi_mom | T | 1469.0 | 0.9 | -11349.0 | -12037.3 | -377.6 |  | -0.0 | -173.3 | -19.9 |
| US500 | H1 | rsi_mom |  | 4988.0 | 0.8 | -37979.3 | -38254.1 | -413.1 |  | -0.0 | -487.8 | -181.5 |
| US500 | H1 | rsi_rev |  | 1209.0 | 0.9 | -6799.1 | -10258.3 | -394.6 |  | -0.0 | -36.2 | -96.4 |
| US500 | H1 | mfi_rev |  | 1201.0 | 0.9 | -8208.8 | -11282.3 | -298.8 |  | -0.0 | -87.3 | -61.9 |
| US500 | H1 | willr_rev | T | 1483.0 | 0.9 | -11958.0 | -13387.5 | -394.1 |  | -0.0 | -157.6 | -52.2 |
| US500 | H1 | willr_rev |  | 4211.0 | 0.9 | -20268.5 | -23703.3 | -407.6 |  | -0.0 | -281.2 | -70.8 |
| US500 | H1 | aroon_x | T | 876.0 | 1.0 | -1289.9 | -6617.1 | -327.1 |  | -0.0 | -18.4 | -3.9 |
| US500 | H1 | aroon_x |  | 1815.0 | 0.9 | -10385.1 | -11208.9 | -426.8 |  | -0.0 | -100.6 | -90.6 |
| AUDJPY | H4 | trend_vote v=5 |  | 579.0 | 0.9 | -2133.2 | -3182.2 | -262.1 |  | -0.0 | -16.6 | -23.4 |
| AUDJPY | H4 | trend_vote v=4 | T | 309.0 | 0.8 | -3646.8 | -4187.0 | -236.5 |  | -0.0 | -23.5 | -46.2 |
| AUDJPY | H4 | trend_vote v=4 |  | 650.0 | 0.9 | -3404.6 | -3815.5 | -236.5 |  | -0.0 | -11.2 | -56.8 |
| US500 | H4 | bb_rev |  | 609.0 | 1.0 | 44.9 | -3325.9 | -260.1 |  | 0.0 | 13.2 | -15.5 |
| US500 | H4 | dmi_x |  | 474.0 | 1.0 | -889.6 | -3043.3 | -300.4 |  | -0.0 | -24.5 | 12.1 |
| US500 | H4 | cci_mom | T | 426.0 | 1.0 | 499.0 | -3420.0 | -185.5 |  | 0.0 | 6.4 | 2.4 |
| US500 | H1 | bb_brk | T | 1446.0 | 0.9 | -9477.8 | -11968.6 | -327.0 |  | -0.0 | -93.1 | -81.1 |
| US500 | H1 | bb_brk |  | 2141.0 | 0.8 | -19434.9 | -20846.9 | -360.5 |  | -0.0 | -164.6 | -199.2 |
| US500 | H1 | bb_rev | T | 785.0 | 1.1 | 3028.9 | -3789.1 | -394.6 |  | 0.0 | -23.9 | 93.0 |
| US500 | H1 | bb_rev |  | 2434.0 | 0.9 | -9106.4 | -11538.5 | -463.7 |  | -0.0 | -108.5 | -54.1 |
| US500 | H1 | dmi_x | T | 691.0 | 0.9 | -3519.1 | -5703.7 | -349.9 |  | -0.0 | -69.9 | 14.0 |
| US500 | H1 | don_rev | T | 831.0 | 0.9 | -3026.0 | -4997.5 | -361.4 |  | -0.0 | -57.0 | 8.2 |
| US500 | H1 | don_rev |  | 2785.0 | 0.9 | -12963.4 | -14769.5 | -411.3 |  | -0.0 | -195.9 | -25.2 |
| US500 | H1 | don_brk | T | 1587.0 | 1.0 | -3242.3 | -7505.2 | -315.7 |  | -0.0 | -70.4 | 20.5 |
| US500 | H1 | don_brk |  | 2188.0 | 0.9 | -10454.9 | -12455.8 | -348.9 |  | -0.0 | -116.4 | -72.3 |
| US500 | H1 | ha_flip | T | 2343.0 | 0.8 | -22066.9 | -25047.8 | -385.2 |  | -0.0 | -328.0 | -49.7 |
| US500 | H4 | macd_x |  | 1025.0 | 0.9 | -5217.3 | -6087.6 | -296.5 |  | -0.0 | -66.0 | -26.3 |
| US500 | H4 | rsi_mom | T | 380.0 | 1.0 | -926.9 | -2877.3 | -209.7 |  | -0.0 | -22.1 | 8.3 |
| US500 | H4 | rsi_mom |  | 1341.0 | 0.9 | -4397.6 | -8568.1 | -331.4 |  | -0.0 | -130.0 | 70.8 |
| US500 | H4 | cmf_zero |  | 697.0 | 1.0 | -829.5 | -4365.1 | -324.4 |  | -0.0 | -44.3 | 38.1 |
| US500 | H4 | mfi_rev |  | 286.0 | 0.8 | -3067.1 | -4393.4 | -216.0 |  | -0.0 | -32.9 | -22.8 |
| US500 | H1 | obv_slope |  | 6797.0 | 0.8 | -51978.9 | -52154.5 | -442.4 |  | -0.0 | -611.2 | -318.9 |
| US500 | H1 | cmf_zero | T | 1456.0 | 0.9 | -11925.4 | -13707.6 | -415.2 |  | -0.0 | -165.9 | -41.0 |
| US500 | H1 | cmf_zero |  | 2751.0 | 0.8 | -20765.4 | -23438.9 | -430.4 |  | -0.0 | -230.5 | -144.5 |
| US500 | H1 | mfi_rev | T | 354.0 | 0.9 | -1919.2 | -4149.5 | -247.8 |  | -0.0 | -29.5 | -3.1 |
| CHFJPY | H4 | trend_vote v=5 |  | 535.0 | 0.9 | -3021.0 | -3564.6 | -207.4 |  | -0.0 | -34.4 | -20.0 |
| CHFJPY | H4 | trend_vote v=4 |  | 679.0 | 0.9 | -4048.5 | -4730.9 | -220.3 |  | -0.0 | -35.6 | -39.9 |
| AUDJPY | H4 | trend_vote v=6 | T | 338.0 | 0.9 | -2246.7 | -3183.3 | -170.6 |  | -0.0 | -13.6 | -29.5 |
| AUDJPY | H4 | trend_vote v=6 |  | 463.0 | 0.9 | -3008.8 | -3660.2 | -173.1 |  | -0.0 | -7.5 | -53.2 |
| US500 | H4 | bb_brk | T | 345.0 | 1.0 | -440.6 | -2462.5 | -220.2 |  | -0.0 | -19.1 | 14.7 |
| US500 | H4 | bb_brk |  | 513.0 | 0.9 | -3198.2 | -4143.5 | -234.2 |  | -0.0 | -51.9 | -1.8 |
| US500 | H4 | don_rev |  | 752.0 | 0.9 | -3653.0 | -5150.2 | -274.0 |  | -0.0 | -8.4 | -65.6 |
| US500 | H4 | don_brk |  | 562.0 | 1.0 | 644.1 | -3263.3 | -263.9 |  | 0.0 | -17.2 | 34.9 |
| US500 | H4 | ha_flip | T | 587.0 | 1.0 | 1364.4 | -3264.5 | -224.6 |  | 0.0 | 7.9 | 18.5 |
| US500 | H4 | cci_mom |  | 717.0 | 0.9 | -2856.4 | -5030.5 | -247.1 |  | -0.0 | -40.8 | -8.6 |
| US500 | H4 | cci_rev |  | 876.0 | 1.0 | -137.6 | -3303.1 | -240.5 |  | -0.0 | -26.5 | 30.2 |
| US500 | H4 | stoch_rev |  | 742.0 | 0.9 | -2504.2 | -4048.0 | -201.7 |  | -0.0 | -4.2 | -46.9 |
| US500 | H4 | macd_zero |  | 452.0 | 1.0 | 890.9 | -4104.6 | -300.4 |  | 0.0 | -48.1 | 78.6 |
| US500 | H4 | macd_x | T | 392.0 | 1.0 | 418.2 | -3154.8 | -197.4 |  | 0.0 | -18.9 | 32.4 |
| EURUSD | H4 | rsi_mom |  | 1562.0 | 0.8 | -8388.1 | -9401.3 | -287.9 |  | -0.0 | -20.8 | -148.8 |
| US500 | H4 | obv_slope | T | 450.0 | 1.1 | 1587.2 | -2415.2 | -265.3 |  | 0.0 | 8.4 | 22.6 |
| US500 | H4 | obv_slope |  | 1815.0 | 0.9 | -4883.2 | -7605.8 | -365.0 |  | -0.0 | -94.7 | 16.7 |
| US500 | H4 | cmf_zero | T | 369.0 | 1.0 | -95.4 | -3200.0 | -271.6 |  | -0.0 | -19.2 | 22.0 |
| USTEC | H1 | bb_brk |  | 407.0 | 0.9 | -1721.6 | -3263.7 | -317.6 |  | -0.0 | 0.0 | -95.6 |
| USTEC | H1 | cci_mom |  | 507.0 | 1.1 | 1679.0 | -2568.1 | -356.6 |  | 0.0 | 0.0 | 93.3 |
| USTEC | H1 | cci_rev |  | 590.0 | 0.8 | -5054.9 | -5169.0 | -300.8 |  | -0.0 | 0.0 | -280.8 |
| USTEC | H1 | stoch_rev |  | 468.0 | 1.0 | -46.2 | -2520.7 | -340.4 |  | -0.0 | 0.0 | -2.6 |
| US500 | H4 | willr_rev |  | 1046.0 | 1.1 | 2341.3 | -3567.6 | -308.4 |  | 0.0 | -3.4 | 53.1 |
| US500 | H4 | aroon_x |  | 498.0 | 0.9 | -2426.5 | -3719.6 | -294.6 |  | -0.0 | -51.3 | 13.6 |
| US500 | H4 | kelt_rev |  | 485.0 | 0.9 | -3744.4 | -4454.9 | -260.1 |  | -0.0 | -19.8 | -53.2 |
| US500 | H4 | kelt_brk |  | 398.0 | 1.0 | -954.4 | -2895.1 | -263.9 |  | -0.0 | -34.9 | 23.8 |
| US500 | H4 | ema_slope |  | 579.0 | 1.0 | 504.4 | -3029.2 | -301.6 |  | 0.0 | -38.2 | 58.3 |
| AUDCAD | H4 | trend_vote v=6 | T | 353.0 | 0.8 | -3040.8 | -3936.5 | -203.7 |  | -0.0 | -57.1 | 12.2 |
| AUDCAD | H4 | trend_vote v=6 |  | 449.0 | 0.8 | -3871.2 | -5339.2 | -203.7 |  | -0.0 | -70.1 | 11.3 |
| AUDCAD | H4 | trend_vote v=5 |  | 479.0 | 0.9 | -2171.8 | -4092.5 | -229.7 |  | -0.0 | -53.6 | 30.5 |
| AUDCAD | H4 | trend_vote v=4 |  | 612.0 | 0.8 | -5144.3 | -6532.0 | -267.5 |  | -0.0 | -73.4 | -18.5 |
| GBPUSD | H4 | rsi_rev |  | 382.0 | 0.9 | -1486.7 | -3801.4 | -215.6 |  | -0.0 | -51.8 | 33.8 |
| EURUSD | H4 | don_rev | T | 255.0 | 0.9 | -1865.1 | -3117.3 | -188.5 |  | -0.0 | -24.6 | -8.1 |
| EURUSD | H4 | don_rev |  | 839.0 | 0.9 | -4533.8 | -6543.9 | -338.6 |  | -0.0 | -39.0 | -45.7 |
| EURUSD | H4 | don_brk | T | 474.0 | 0.8 | -4203.3 | -5022.0 | -224.2 |  | -0.0 | -47.7 | -27.9 |
| EURUSD | H4 | macd_zero |  | 462.0 | 1.0 | -1034.7 | -2993.5 | -220.5 |  | -0.0 | -6.3 | -13.7 |
| EURUSD | H4 | macd_x |  | 1065.0 | 1.0 | -678.5 | -3531.8 | -338.6 |  | -0.0 | 9.8 | -26.4 |
| EURUSD | H4 | rsi_mom | T | 453.0 | 0.9 | -2921.3 | -3884.6 | -282.3 |  | -0.0 | -20.5 | -35.2 |
| USTEC | H1 | don_brk | T | 290.0 | 1.0 | -617.7 | -2581.9 | -271.6 |  | -0.0 | 0.0 | -34.3 |
| USTEC | H1 | macd_x | T | 251.0 | 0.9 | -910.9 | -2780.0 | -312.4 |  | -0.0 | 0.0 | -50.6 |
| USTEC | H1 | macd_x |  | 643.0 | 0.9 | -1469.5 | -3942.4 | -357.9 |  | -0.0 | 0.0 | -81.6 |
| GBPJPY | H4 | trend_vote v=5 | T | 327.0 | 0.9 | -2013.5 | -3456.1 | -190.8 |  | -0.0 | -6.3 | -34.1 |
| GBPJPY | H4 | trend_vote v=5 |  | 541.0 | 1.0 | 401.2 | -2616.8 | -225.1 |  | 0.0 | 9.2 | -3.1 |
| GBPJPY | H4 | trend_vote v=4 | T | 293.0 | 0.9 | -1392.6 | -2540.8 | -176.8 |  | -0.0 | 5.8 | -36.2 |
| GBPJPY | H4 | trend_vote v=4 |  | 643.0 | 0.9 | -1635.3 | -3314.0 | -335.2 |  | -0.0 | -11.8 | -19.3 |
| US500 | H4 | ha_flip |  | 1934.0 | 0.9 | -7087.9 | -7935.0 | -307.7 |  | -0.0 | -71.3 | -58.5 |
| EURUSD | H4 | aroon_x |  | 533.0 | 0.9 | -1354.5 | -3459.1 | -229.0 |  | -0.0 | -8.3 | -17.8 |
| EURUSD | H4 | kelt_rev |  | 531.0 | 0.9 | -2571.4 | -3001.2 | -338.6 |  | -0.0 | -5.4 | -46.9 |
| EURUSD | H4 | kelt_brk | T | 345.0 | 0.9 | -2033.3 | -3252.8 | -234.5 |  | -0.0 | -29.0 | -6.2 |
| EURUSD | H4 | kelt_brk |  | 431.0 | 0.9 | -2909.9 | -4133.1 | -234.5 |  | -0.0 | -33.4 | -18.8 |
| EURUSD | H4 | bb_brk | T | 410.0 | 1.0 | -897.0 | -3316.0 | -234.5 |  | -0.0 | -30.9 | 20.0 |
| XAUUSD | H1 | ema_slope | T | 965.0 | 0.9 | -3142.9 | -6429.8 | -353.2 |  | -0.0 | -61.8 | 11.8 |
| XAUUSD | H1 | ema_slope |  | 2402.0 | 0.9 | -13088.3 | -13889.0 | -387.4 |  | -0.0 | -165.6 | -65.6 |
| XAUUSD | H1 | obv_slope | T | 1919.0 | 0.9 | -6019.8 | -10500.0 | -351.1 |  | -0.0 | -83.9 | -20.5 |
| XAUUSD | H1 | obv_slope |  | 8172.0 | 0.8 | -49486.5 | -50136.9 | -417.4 |  | -0.0 | -523.5 | -376.6 |
| XAUUSD | H1 | cmf_zero | T | 1654.0 | 0.9 | -12178.8 | -15391.3 | -311.2 |  | -0.0 | -159.0 | -54.9 |
| USTEC | H1 | willr_rev |  | 770.0 | 0.9 | -3212.0 | -4116.2 | -368.8 |  | -0.0 | 0.0 | -178.4 |
| USTEC | H1 | aroon_x |  | 324.0 | 0.9 | -1233.7 | -2713.1 | -277.1 |  | -0.0 | 0.0 | -68.5 |
| USTEC | H1 | don_rev |  | 499.0 | 1.0 | -1020.3 | -2934.5 | -306.6 |  | -0.0 | 0.0 | -56.7 |
| USTEC | H1 | don_brk |  | 402.0 | 0.9 | -1098.7 | -2530.6 | -296.0 |  | -0.0 | 0.0 | -61.0 |
| USTEC | H1 | ha_flip | T | 410.0 | 1.0 | 13.2 | -2578.3 | -380.5 |  | 0.0 | 0.0 | 0.7 |
| USTEC | H1 | ha_flip |  | 1392.0 | 0.9 | -2623.8 | -4199.8 | -365.0 |  | -0.0 | 0.0 | -145.8 |
| USTEC | H1 | obv_slope |  | 1409.0 | 0.8 | -6164.8 | -7503.0 | -395.6 |  | -0.0 | 0.0 | -342.5 |
| USTEC | H1 | cmf_zero |  | 486.0 | 1.0 | -658.0 | -3041.3 | -422.0 |  | -0.0 | 0.0 | -36.6 |
| XAUUSD | H1 | don_rev | T | 820.0 | 0.9 | -3765.8 | -6128.0 | -384.0 |  | -0.0 | -38.6 | -30.2 |
| EURUSD | H4 | mfi_rev |  | 292.0 | 0.9 | -1484.2 | -3061.7 | -190.5 |  | -0.0 | 16.3 | -51.3 |
| EURUSD | H4 | willr_rev | T | 427.0 | 0.9 | -2416.1 | -3318.4 | -192.9 |  | -0.0 | -24.1 | -20.2 |
| EURUSD | H4 | willr_rev |  | 1174.0 | 0.9 | -3258.9 | -5429.6 | -232.1 |  | -0.0 | -14.7 | -49.6 |
| DE40 | H4 | rsi_mom |  | 1319.0 | 1.0 | -1520.1 | -3070.5 | -287.2 |  | -0.0 | -30.1 | 6.0 |
| DE40 | H4 | rsi_rev |  | 323.0 | 0.9 | -2086.8 | -2622.3 | -247.0 |  | -0.0 | -21.7 | -16.3 |
| USTEC | H4 | don_brk |  | 116.0 | 0.8 | -1430.9 | -2527.8 | -172.0 |  | -0.0 | 0.0 | -79.5 |
| EURJPY | H4 | trend_vote v=6 | T | 384.0 | 0.8 | -4083.4 | -4599.3 | -178.9 |  | -0.0 | -49.3 | -23.4 |
| EURJPY | H4 | trend_vote v=6 |  | 483.0 | 0.8 | -4286.5 | -4572.9 | -178.9 |  | -0.0 | -38.3 | -41.4 |
| EURJPY | H4 | trend_vote v=5 | T | 342.0 | 0.8 | -3963.2 | -4527.4 | -188.9 |  | -0.0 | -53.3 | -16.0 |
| EURJPY | H4 | trend_vote v=5 |  | 548.0 | 1.0 | -1373.3 | -2929.0 | -195.8 |  | -0.0 | -22.8 | -0.1 |
| EURJPY | H4 | trend_vote v=4 | T | 313.0 | 0.8 | -3236.2 | -3708.9 | -213.8 |  | -0.0 | -42.0 | -14.9 |
| EURJPY | H4 | trend_vote v=4 |  | 655.0 | 0.9 | -1956.9 | -2698.5 | -228.6 |  | -0.0 | -22.9 | -12.1 |
| USDCHF | D1 | trend_vote v=4 |  | 142.0 | 0.6 | -2773.5 | -3279.1 | -156.3 |  | -0.0 | -36.8 | -11.8 |
| USDCHF | H4 | trend_vote v=6 | T | 381.0 | 0.8 | -4338.4 | -5488.9 | -189.8 |  | -0.0 | -47.0 | -31.6 |
| USDCHF | H4 | trend_vote v=6 |  | 462.0 | 0.9 | -2163.0 | -3715.7 | -189.8 |  | -0.0 | -15.2 | -26.0 |
| USDCHF | H4 | trend_vote v=5 | T | 357.0 | 0.9 | -2772.2 | -4165.9 | -258.4 |  | -0.0 | -37.7 | -10.6 |
| XAUUSD | H4 | stoch_rev | T | 238.0 | 0.8 | -2227.6 | -2464.9 | -183.8 |  | -0.0 | -15.8 | -26.6 |
| US500 | H4 | trend_vote v=6 | T | 342.0 | 1.1 | 1334.8 | -2747.5 | -288.2 |  | 0.0 | -1.4 | 29.5 |
| USDCHF | H4 | trend_vote v=4 |  | 671.0 | 0.9 | -2222.4 | -3728.0 | -230.1 |  | -0.0 | 2.5 | -49.4 |
| US500 | H4 | trend_vote v=6 |  | 427.0 | 1.1 | 1410.7 | -3199.4 | -288.2 |  | 0.0 | -9.1 | 40.8 |
| US500 | H4 | trend_vote v=5 | T | 300.0 | 1.1 | 2071.2 | -2497.6 | -204.2 |  | 0.0 | 4.8 | 37.2 |
| USDCAD | H4 | trend_vote v=6 | T | 395.0 | 0.8 | -3813.3 | -5542.3 | -210.7 |  | -0.0 | -44.7 | -23.6 |
| USDCAD | H4 | trend_vote v=6 |  | 514.0 | 0.8 | -6361.9 | -7579.3 | -210.7 |  | -0.0 | -51.2 | -68.5 |
| USDCAD | H4 | trend_vote v=5 | T | 362.0 | 0.8 | -3367.1 | -5037.3 | -242.8 |  | -0.0 | -18.3 | -47.3 |
| USDCAD | H4 | trend_vote v=5 |  | 587.0 | 0.8 | -6605.8 | -7556.9 | -268.6 |  | -0.0 | -46.3 | -79.8 |
| USDCAD | H4 | trend_vote v=4 | T | 321.0 | 0.8 | -3475.5 | -5360.7 | -239.0 |  | -0.0 | -27.4 | -38.2 |
| USDCAD | H4 | trend_vote v=4 |  | 710.0 | 0.7 | -8779.0 | -9461.1 | -292.3 |  | -0.0 | -93.4 | -66.2 |
| DE40 | H4 | trend_vote v=5 | T | 322.0 | 1.0 | -847.9 | -2838.6 | -204.6 |  | -0.0 | 1.3 | -19.3 |
| DE40 | H4 | kelt_brk | T | 298.0 | 0.9 | -2278.7 | -3685.8 | -241.8 |  | -0.0 | -3.6 | -43.0 |
| DE40 | H4 | trend_vote v=4 | T | 294.0 | 0.9 | -1378.2 | -2497.2 | -195.5 |  | -0.0 | -3.6 | -24.2 |
| DE40 | H4 | macd_zero |  | 444.0 | 0.9 | -2323.6 | -3910.2 | -289.8 |  | -0.0 | -15.6 | -29.0 |
| DE40 | H4 | trend_vote v=4 |  | 615.0 | 0.9 | -2728.0 | -4538.7 | -289.8 |  | -0.0 | -28.1 | -21.8 |
| EURUSD | H4 | bb_brk |  | 582.0 | 0.9 | -1589.8 | -3694.1 | -234.5 |  | -0.0 | -27.1 | 0.7 |
| EURUSD | H4 | bb_rev | T | 208.0 | 0.9 | -1338.0 | -2856.5 | -192.9 |  | -0.0 | -24.1 | 2.2 |
| DE40 | H4 | bb_brk | T | 357.0 | 0.9 | -1041.7 | -2833.9 | -256.8 |  | -0.0 | 7.4 | -30.9 |
| DE40 | H4 | bb_brk |  | 522.0 | 1.0 | -890.1 | -2813.3 | -256.8 |  | -0.0 | 2.8 | -22.0 |
| EURUSD | H4 | bb_rev |  | 698.0 | 0.9 | -5079.3 | -6310.2 | -259.0 |  | -0.0 | -45.9 | -48.5 |
| EURUSD | H4 | dmi_x | T | 206.0 | 0.7 | -3507.2 | -4157.4 | -234.8 |  | -0.0 | -52.8 | -7.1 |
| XAUUSD | H4 | bb_brk |  | 557.0 | 1.0 | 237.6 | -2896.5 | -234.4 |  | 0.0 | 10.4 | -8.0 |
| DE40 | H4 | cci_mom | T | 431.0 | 0.9 | -1965.2 | -3155.4 | -254.7 |  | -0.0 | -23.3 | -11.8 |
| DE40 | H4 | cci_mom |  | 723.0 | 0.9 | -3984.6 | -5536.2 | -349.9 |  | -0.0 | -50.4 | -20.0 |
| DE40 | H4 | cci_rev | T | 282.0 | 1.0 | -401.3 | -2716.9 | -176.8 |  | -0.0 | -34.0 | 34.2 |
| DE40 | H4 | cci_rev |  | 876.0 | 1.1 | 2609.8 | -3386.7 | -180.8 |  | 0.0 | -18.5 | 77.5 |
| DE40 | H4 | stoch_rev |  | 697.0 | 0.9 | -2488.5 | -3542.2 | -211.3 |  | -0.0 | -41.5 | 0.0 |
| XAUUSD | H4 | bb_rev |  | 679.0 | 0.9 | -2510.3 | -4102.8 | -218.1 |  | -0.0 | -27.7 | -17.6 |
| DE40 | H4 | ema_slope | T | 247.0 | 0.9 | -1663.8 | -2617.4 | -196.5 |  | -0.0 | -15.0 | -15.9 |
| DE40 | H4 | ema_slope |  | 623.0 | 0.9 | -1850.2 | -3558.0 | -215.6 |  | -0.0 | -26.9 | -4.9 |
| DE40 | H4 | obv_slope | T | 459.0 | 0.9 | -3405.7 | -4642.3 | -205.6 |  | -0.0 | -27.3 | -36.8 |
| USDCHF | H4 | trend_vote v=5 |  | 565.0 | 0.9 | -2262.2 | -5265.3 | -258.4 |  | -0.0 | -11.0 | -33.4 |
| USDCHF | H4 | trend_vote v=4 | T | 336.0 | 0.9 | -2444.4 | -3103.3 | -198.5 |  | -0.0 | -34.3 | -8.1 |
| XAUUSD | H4 | cci_mom | T | 462.0 | 0.9 | -2147.0 | -3380.9 | -204.4 |  | -0.0 | -27.8 | -10.0 |
| DE40 | H4 | mfi_rev |  | 270.0 | 0.8 | -3275.0 | -3762.6 | -219.8 |  | -0.0 | -36.7 | -22.3 |
| DE40 | H4 | willr_rev | T | 331.0 | 1.1 | 1005.7 | -2764.5 | -195.7 |  | 0.0 | -18.2 | 43.7 |
| DE40 | H4 | willr_rev |  | 1015.0 | 1.0 | 1070.9 | -3331.7 | -276.0 |  | 0.0 | -16.0 | 42.3 |
| DE40 | H4 | aroon_x |  | 509.0 | 0.9 | -2623.7 | -4127.5 | -254.7 |  | -0.0 | -12.5 | -39.0 |
| XAUUSD | H4 | cci_mom |  | 752.0 | 1.0 | -4.4 | -3802.0 | -262.0 |  | -0.0 | 8.0 | -10.1 |
| DE40 | H4 | squeeze_brk |  | 217.0 | 0.9 | -757.5 | -2531.4 | -277.3 |  | -0.0 | -22.4 | 12.2 |
| NZDUSD | H4 | stoch_rev |  | 866.0 | 0.9 | -2673.3 | -4451.4 | -173.8 |  | -0.0 | -60.0 | 19.3 |
| NZDUSD | H4 | macd_zero |  | 458.0 | 0.9 | -1396.6 | -3842.8 | -209.9 |  | -0.0 | 32.9 | -70.3 |
| NZDUSD | H4 | macd_x | T | 426.0 | 0.9 | -1990.0 | -3652.9 | -182.5 |  | -0.0 | 14.4 | -59.5 |
| NZDUSD | H4 | macd_x |  | 1129.0 | 0.9 | -5786.0 | -6516.2 | -249.8 |  | -0.0 | -49.4 | -58.8 |
| NZDUSD | H4 | rsi_mom | T | 418.0 | 1.0 | -931.4 | -2926.0 | -193.3 |  | -0.0 | -1.7 | -17.2 |
| NZDUSD | H4 | rsi_mom |  | 1500.0 | 0.9 | -4693.7 | -5238.3 | -314.9 |  | -0.0 | -25.6 | -65.8 |
| XAUUSD | H4 | cci_rev |  | 930.0 | 0.9 | -3631.6 | -3798.6 | -179.2 |  | -0.0 | -54.1 | -8.0 |
| NZDUSD | H4 | rsi_rev |  | 326.0 | 0.9 | -2566.5 | -3236.5 | -160.9 |  | -0.0 | -25.3 | -21.8 |
| DE40 | H4 | kelt_brk |  | 375.0 | 0.9 | -1163.8 | -2877.1 | -241.8 |  | -0.0 | -4.2 | -19.0 |
| DE40 | H4 | don_brk | T | 396.0 | 1.0 | -72.7 | -2436.7 | -254.7 |  | -0.0 | -0.2 | -1.2 |
| DE40 | H4 | don_brk |  | 546.0 | 1.0 | -765.7 | -2800.4 | -277.3 |  | -0.0 | -13.0 | 0.2 |
| DE40 | H4 | ha_flip | T | 593.0 | 0.9 | -1915.3 | -3346.1 | -254.7 |  | -0.0 | -24.3 | -9.5 |
| DE40 | H4 | ha_flip |  | 1961.0 | 1.0 | -1517.2 | -2964.2 | -290.1 |  | -0.0 | -12.3 | -16.3 |
| XAUUSD | H4 | rsi_mom | T | 388.0 | 0.9 | -1953.7 | -3759.5 | -196.2 |  | -0.0 | -28.6 | -4.9 |
| NZDUSD | H4 | squeeze_brk |  | 262.0 | 0.8 | -2557.2 | -3294.3 | -183.2 |  | -0.0 | 11.0 | -67.0 |
| NZDUSD | H4 | kelt_rev |  | 481.0 | 1.0 | -1208.1 | -2748.8 | -213.5 |  | -0.0 | -25.7 | 7.0 |
| NZDUSD | H4 | kelt_brk | T | 317.0 | 0.9 | -2030.1 | -2806.6 | -197.4 |  | -0.0 | -27.6 | -7.8 |
| NZDUSD | H4 | kelt_brk |  | 398.0 | 0.8 | -3863.2 | -4654.4 | -210.8 |  | -0.0 | -43.5 | -26.2 |
| NZDUSD | H4 | bb_brk | T | 392.0 | 0.9 | -3348.6 | -4095.2 | -235.6 |  | -0.0 | -12.2 | -54.5 |
| NZDUSD | H4 | bb_brk |  | 570.0 | 0.9 | -4714.6 | -5391.3 | -242.8 |  | -0.0 | -4.1 | -93.1 |
| NZDUSD | H4 | bb_rev | T | 206.0 | 0.9 | -865.6 | -2437.4 | -192.1 |  | -0.0 | -12.9 | -1.9 |
| NZDUSD | H4 | bb_rev |  | 672.0 | 1.0 | -1385.1 | -5803.0 | -205.1 |  | -0.0 | -41.9 | 23.5 |
| NZDUSD | H4 | cci_mom | T | 459.0 | 1.0 | 408.9 | -2750.7 | -170.0 |  | 0.0 | 32.9 | -32.6 |
| NZDUSD | H4 | cci_mom |  | 755.0 | 0.9 | -1927.7 | -3025.4 | -314.4 |  | -0.0 | 11.0 | -53.9 |
| DE40 | H4 | obv_slope |  | 1822.0 | 0.9 | -3676.0 | -5508.9 | -260.7 |  | -0.0 | -53.8 | -9.3 |
| NZDUSD | H4 | cci_rev |  | 961.0 | 0.9 | -3717.9 | -5923.6 | -190.0 |  | -0.0 | -59.9 | -2.6 |
| NZDUSD | H4 | stoch_rev | T | 266.0 | 0.9 | -2031.8 | -2469.4 | -166.4 |  | -0.0 | -23.5 | -13.0 |
| EURUSD | H4 | don_brk |  | 637.0 | 0.9 | -4694.9 | -5519.9 | -231.5 |  | -0.0 | -48.3 | -37.4 |
| EURUSD | H4 | ha_flip | T | 668.0 | 0.9 | -3701.6 | -4795.7 | -188.3 |  | -0.0 | -31.5 | -37.8 |
| NZDUSD | H4 | trend_vote v=5 | T | 345.0 | 0.9 | -968.7 | -3036.9 | -211.2 |  | -0.0 | 5.5 | -27.0 |
| NZDUSD | H4 | trend_vote v=5 |  | 558.0 | 0.9 | -1891.9 | -4263.8 | -211.2 |  | -0.0 | 9.4 | -51.1 |
| NZDUSD | H4 | trend_vote v=4 | T | 308.0 | 0.8 | -3611.8 | -3895.7 | -195.8 |  | -0.0 | -9.7 | -63.2 |
| NZDUSD | H4 | trend_vote v=4 |  | 654.0 | 0.8 | -4599.2 | -4858.2 | -304.8 |  | -0.0 | -3.0 | -92.1 |
| NZDUSD | H4 | ha_flip |  | 2245.0 | 0.8 | -11777.2 | -12185.0 | -276.0 |  | -0.0 | -133.3 | -78.7 |
| NZDUSD | H4 | ema_x | T | 149.0 | 0.8 | -2215.0 | -2588.8 | -156.6 |  | -0.0 | -1.4 | -44.5 |
| NZDUSD | H4 | ema_x |  | 288.0 | 0.9 | -2298.1 | -3387.4 | -211.5 |  | -0.0 | -8.8 | -36.8 |
| NZDUSD | H4 | ema_slope | T | 279.0 | 0.9 | -1821.9 | -2425.8 | -191.7 |  | -0.0 | -3.7 | -33.3 |
| NZDUSD | H4 | ema_slope |  | 687.0 | 0.9 | -4247.8 | -4662.3 | -275.3 |  | -0.0 | -23.4 | -59.3 |
| NZDUSD | H4 | obv_slope | T | 515.0 | 0.9 | -2606.0 | -3282.2 | -183.6 |  | -0.0 | -12.3 | -38.9 |
| NZDUSD | H4 | obv_slope |  | 2342.0 | 0.8 | -12276.6 | -13820.3 | -263.3 |  | -0.0 | -109.8 | -118.5 |
| DE40 | H4 | don_rev |  | 710.0 | 1.0 | 303.3 | -3456.6 | -205.5 |  | 0.0 | -25.9 | 38.7 |
| NZDUSD | H4 | cmf_zero |  | 824.0 | 0.8 | -8665.4 | -8875.9 | -240.0 |  | -0.0 | -65.8 | -98.2 |
| NZDUSD | H4 | mfi_rev |  | 230.0 | 0.8 | -2910.6 | -3211.0 | -170.8 |  | -0.0 | -31.2 | -21.6 |
| NZDUSD | H4 | willr_rev | T | 405.0 | 0.8 | -4888.3 | -5550.2 | -177.9 |  | -0.0 | -54.6 | -33.5 |
| NZDUSD | H4 | willr_rev |  | 1198.0 | 0.8 | -8009.2 | -9290.0 | -234.1 |  | -0.0 | -111.1 | -27.9 |
| NZDUSD | H4 | aroon_x | T | 238.0 | 0.9 | -670.8 | -3143.6 | -163.1 |  | -0.0 | 29.5 | -50.9 |
| NZDUSD | H4 | aroon_x |  | 512.0 | 0.9 | -2818.3 | -3928.7 | -220.1 |  | -0.0 | 3.0 | -62.5 |
| NZDUSD | H4 | squeeze_brk | T | 208.0 | 0.9 | -1799.7 | -2617.5 | -183.2 |  | -0.0 | 12.3 | -52.9 |
| USDCAD | H4 | cci_rev |  | 973.0 | 1.0 | -204.0 | -3641.1 | -309.7 |  | -0.0 | -11.7 | 10.3 |
| EURUSD | H4 | ha_flip |  | 2184.0 | 0.9 | -6015.1 | -8636.5 | -338.6 |  | -0.0 | -47.3 | -66.2 |
| USDCAD | H4 | stoch_rev |  | 848.0 | 0.9 | -3122.2 | -6174.1 | -217.0 |  | -0.0 | -89.1 | 46.3 |
| USDCAD | H4 | macd_zero | T | 240.0 | 0.9 | -1260.3 | -2861.0 | -239.0 |  | -0.0 | -2.6 | -23.0 |
| USDCAD | H4 | macd_zero |  | 506.0 | 0.8 | -5904.3 | -6356.1 | -268.6 |  | -0.0 | -76.5 | -27.4 |
| USDCAD | H4 | macd_x | T | 446.0 | 0.8 | -4372.0 | -5641.4 | -228.5 |  | -0.0 | -34.6 | -47.8 |
| USDCAD | H4 | macd_x |  | 1160.0 | 0.8 | -10790.9 | -12317.6 | -269.0 |  | -0.0 | -84.7 | -118.9 |
| USDCAD | H4 | rsi_mom | T | 408.0 | 0.9 | -1088.4 | -3728.6 | -209.1 |  | -0.0 | -3.1 | -18.8 |
| NZDUSD | H4 | cci_rev | T | 309.0 | 0.9 | -2393.9 | -3158.8 | -170.8 |  | -0.0 | -9.7 | -37.8 |
| USDCAD | H4 | rsi_rev |  | 351.0 | 0.9 | -2988.9 | -3887.6 | -315.6 |  | -0.0 | -39.4 | -13.0 |
| NZDUSD | H4 | don_rev | T | 256.0 | 0.8 | -2399.7 | -2999.3 | -192.1 |  | -0.0 | -26.9 | -16.4 |
| NZDUSD | H4 | don_rev |  | 856.0 | 0.9 | -3510.7 | -6587.3 | -217.9 |  | -0.0 | -78.7 | 25.2 |
| NZDUSD | H4 | don_brk | T | 454.0 | 0.9 | -3540.2 | -3780.9 | -191.4 |  | -0.0 | -4.4 | -68.2 |
| NZDUSD | H4 | don_brk |  | 610.0 | 0.9 | -3261.4 | -4213.1 | -260.0 |  | -0.0 | 7.4 | -77.2 |
| NZDUSD | H4 | ha_flip | T | 669.0 | 0.9 | -2293.8 | -3618.9 | -190.6 |  | -0.0 | -8.4 | -37.3 |
| USDCAD | H4 | aroon_x |  | 548.0 | 0.8 | -4504.8 | -6485.0 | -239.8 |  | -0.0 | -20.2 | -68.6 |
| USDCAD | H4 | squeeze_brk | T | 221.0 | 0.9 | -1431.4 | -3382.2 | -225.5 |  | -0.0 | -43.4 | 24.4 |
| USDCAD | H4 | squeeze_brk |  | 293.0 | 0.9 | -2057.3 | -3957.0 | -225.5 |  | -0.0 | -52.3 | 22.5 |
| EURUSD | H4 | ema_x |  | 302.0 | 0.8 | -3081.1 | -4205.8 | -180.7 |  | -0.0 | -13.9 | -46.9 |
| USDCAD | H4 | kelt_rev |  | 517.0 | 0.9 | -4237.1 | -4779.2 | -229.2 |  | -0.0 | -44.5 | -32.7 |
| EURUSD | H4 | ema_slope |  | 683.0 | 0.9 | -2256.3 | -3814.2 | -235.2 |  | -0.0 | 10.9 | -60.7 |
| USDCAD | H4 | kelt_brk |  | 414.0 | 1.1 | 1155.3 | -3000.8 | -196.8 |  | 0.0 | 11.7 | 9.5 |
| USDCAD | H4 | bb_brk | T | 393.0 | 0.8 | -3812.1 | -5214.9 | -206.8 |  | -0.0 | -49.5 | -17.5 |
| USDCAD | H4 | bb_brk |  | 574.0 | 0.9 | -3649.7 | -4953.8 | -247.8 |  | -0.0 | -42.2 | -23.3 |
| NZDUSD | H4 | cmf_zero | T | 445.0 | 0.8 | -4834.7 | -5110.9 | -182.4 |  | -0.0 | -32.3 | -60.3 |
| USDCAD | H4 | dmi_x | T | 194.0 | 0.9 | -1048.2 | -2969.7 | -178.5 |  | -0.0 | 4.3 | -27.2 |
| USDCAD | H4 | dmi_x |  | 492.0 | 0.9 | -3195.4 | -4676.7 | -240.0 |  | -0.0 | -13.0 | -50.3 |
| USDCAD | H4 | cci_mom | T | 513.0 | 0.9 | -4133.3 | -5272.2 | -219.3 |  | -0.0 | -53.0 | -19.8 |
| USDCAD | H4 | cci_mom |  | 809.0 | 0.9 | -5375.0 | -7174.3 | -242.7 |  | -0.0 | -41.2 | -60.4 |
| USDCAD | H4 | cci_rev | T | 292.0 | 1.0 | 69.8 | -2673.2 | -189.7 |  | 0.0 | -17.2 | 22.9 |
| USDCAD | H4 | don_brk |  | 618.0 | 0.9 | -1830.1 | -4060.1 | -247.8 |  | -0.0 | -21.2 | -11.6 |
| USDCAD | H4 | ha_flip | T | 634.0 | 1.0 | -726.2 | -3317.1 | -221.0 |  | -0.0 | -7.0 | -6.4 |
| USDCAD | H4 | ha_flip |  | 2227.0 | 0.8 | -12522.1 | -13517.6 | -248.7 |  | -0.0 | -118.6 | -112.7 |
| USDCAD | H4 | ema_x | T | 155.0 | 0.8 | -1799.2 | -2607.9 | -229.3 |  | -0.0 | -13.5 | -20.6 |
| USDCAD | H4 | ema_x |  | 270.0 | 0.7 | -4497.2 | -4797.4 | -229.3 |  | -0.0 | -40.9 | -42.6 |
| USDCAD | H4 | ema_slope | T | 269.0 | 0.9 | -1365.6 | -4094.6 | -225.9 |  | -0.0 | 16.9 | -49.5 |
| USDCAD | H4 | ema_slope |  | 689.0 | 0.8 | -5812.4 | -6281.0 | -246.0 |  | -0.0 | -47.0 | -62.4 |
| USDCAD | H4 | obv_slope | T | 520.0 | 0.9 | -3473.7 | -6441.5 | -230.1 |  | -0.0 | -35.5 | -28.0 |
| USDCAD | H4 | obv_slope |  | 2163.0 | 0.9 | -8293.1 | -9526.6 | -294.2 |  | -0.0 | -64.9 | -91.7 |
| USDCAD | H4 | cmf_zero | T | 439.0 | 0.9 | -2265.1 | -4342.8 | -184.9 |  | -0.0 | -5.7 | -40.1 |
| USDCAD | H4 | rsi_mom |  | 1490.0 | 0.8 | -8747.6 | -9823.1 | -247.0 |  | -0.0 | -71.2 | -93.2 |
| EURUSD | H4 | obv_slope | T | 524.0 | 0.9 | -1631.5 | -3099.2 | -217.0 |  | -0.0 | -31.1 | 4.9 |
| USDCAD | H4 | willr_rev | T | 384.0 | 1.0 | -919.3 | -2796.9 | -182.5 |  | -0.0 | -27.1 | 14.7 |
| USDCAD | H4 | willr_rev |  | 1199.0 | 0.9 | -4643.9 | -6722.2 | -265.4 |  | -0.0 | -81.9 | 5.7 |
| USDCAD | H4 | aroon_x | T | 264.0 | 0.9 | -1966.2 | -4375.7 | -239.8 |  | -0.0 | -9.1 | -29.6 |
| USDCHF | H1 | cci_mom |  | 3207.0 | 0.8 | -40812.0 | -41080.5 | -386.0 |  | -0.0 | -418.3 | -318.7 |
| USDCHF | H1 | cci_rev | T | 1321.0 | 0.8 | -17876.4 | -18387.0 | -347.0 |  | -0.0 | -137.0 | -198.3 |
| USDCHF | H1 | cci_rev |  | 3831.0 | 0.7 | -51488.7 | -51643.8 | -377.5 |  | -0.0 | -420.0 | -538.9 |
| USDCHF | H1 | stoch_rev | T | 938.0 | 0.8 | -12446.4 | -13624.8 | -395.6 |  | -0.0 | -108.1 | -121.9 |
| USDCHF | H1 | stoch_rev |  | 2918.0 | 0.8 | -32941.6 | -33569.2 | -407.3 |  | -0.0 | -326.6 | -271.2 |
| USDCHF | H1 | macd_zero | T | 915.0 | 0.7 | -18108.4 | -18446.8 | -386.3 |  | -0.0 | -147.4 | -189.9 |
| USDCHF | H1 | macd_zero |  | 1887.0 | 0.7 | -26453.3 | -26626.8 | -397.9 |  | -0.0 | -241.8 | -243.9 |
| USDCHF | H1 | macd_x | T | 1710.0 | 0.8 | -23929.7 | -24526.5 | -356.0 |  | -0.0 | -199.7 | -244.7 |
| USDCHF | H1 | macd_x |  | 4494.0 | 0.7 | -62063.1 | -62209.8 | -397.8 |  | -0.0 | -601.3 | -528.8 |
| USDCHF | H1 | rsi_mom | T | 1744.0 | 0.8 | -23428.8 | -24415.5 | -349.1 |  | -0.0 | -232.7 | -192.4 |
| USDCHF | H1 | rsi_mom |  | 6284.0 | 0.6 | -86641.2 | -86861.2 | -406.1 |  | -0.0 | -883.1 | -682.7 |
| USDCAD | H4 | bb_rev |  | 686.0 | 1.0 | -1529.1 | -4012.9 | -291.8 |  | -0.0 | -34.7 | 11.5 |
| USDCHF | H1 | rsi_rev |  | 1315.0 | 0.8 | -15881.5 | -15988.6 | -328.5 |  | -0.0 | -153.1 | -136.2 |
| EURUSD | H4 | obv_slope |  | 2171.0 | 0.9 | -7907.8 | -8262.0 | -338.6 |  | -0.0 | -73.1 | -73.4 |
| USDCAD | H4 | don_rev |  | 866.0 | 1.0 | -2030.2 | -4652.8 | -205.5 |  | -0.0 | -58.1 | 30.3 |
| USDCAD | H4 | don_brk | T | 461.0 | 0.9 | -1906.8 | -3745.9 | -239.8 |  | -0.0 | -19.8 | -14.9 |
| USDCHF | H1 | willr_rev |  | 4855.0 | 0.7 | -58340.0 | -58671.3 | -391.4 |  | -0.0 | -507.3 | -570.7 |
| USDCHF | H1 | aroon_x | T | 1041.0 | 0.8 | -13116.9 | -13874.3 | -355.3 |  | -0.0 | -85.4 | -164.7 |
| USDCHF | H1 | aroon_x |  | 2141.0 | 0.8 | -24945.7 | -25308.8 | -370.5 |  | -0.0 | -213.9 | -247.9 |
| USDCHF | H1 | squeeze_brk | T | 726.0 | 0.8 | -9518.4 | -11897.7 | -313.4 |  | -0.0 | -49.0 | -136.1 |
| USDCHF | H1 | squeeze_brk |  | 1002.0 | 0.8 | -13783.2 | -15383.0 | -313.4 |  | -0.0 | -109.6 | -147.8 |
| USDCHF | H1 | kelt_rev | T | 365.0 | 0.7 | -7178.9 | -7416.7 | -279.0 |  | -0.0 | -76.5 | -52.3 |
| USDCHF | H1 | kelt_rev |  | 1801.0 | 0.8 | -23107.9 | -23373.1 | -356.9 |  | -0.0 | -194.7 | -234.0 |
| USDCHF | H1 | kelt_brk | T | 1236.0 | 0.8 | -15228.9 | -17335.3 | -255.4 |  | -0.0 | -95.0 | -196.5 |
| USDCHF | H1 | kelt_brk |  | 1530.0 | 0.8 | -16144.4 | -18210.4 | -329.2 |  | -0.0 | -93.6 | -217.3 |
| USDCHF | H1 | bb_brk | T | 1653.0 | 0.8 | -22663.9 | -23892.0 | -294.9 |  | -0.0 | -169.2 | -257.1 |
| USDCHF | H1 | bb_brk |  | 2427.0 | 0.8 | -29177.9 | -29746.8 | -337.0 |  | -0.0 | -254.9 | -284.0 |
| USDCAD | H4 | cmf_zero |  | 851.0 | 0.8 | -7200.0 | -9212.5 | -205.2 |  | -0.0 | -35.1 | -106.2 |
| USDCHF | H1 | bb_rev |  | 2822.0 | 0.8 | -35544.7 | -35754.9 | -417.0 |  | -0.0 | -333.8 | -316.3 |
| USDCHF | H1 | dmi_x | T | 737.0 | 0.7 | -12614.6 | -13375.2 | -266.2 |  | -0.0 | -109.1 | -124.2 |
| USDCHF | H1 | dmi_x |  | 1809.0 | 0.7 | -25414.6 | -25986.6 | -414.0 |  | -0.0 | -213.6 | -258.1 |
| USDCHF | H1 | cci_mom | T | 1915.0 | 0.8 | -23959.0 | -24385.7 | -375.0 |  | -0.0 | -205.3 | -238.2 |
| USDCHF | H1 | don_rev |  | 3134.0 | 0.8 | -38504.6 | -38892.4 | -426.4 |  | -0.0 | -287.2 | -437.2 |
| USDCHF | H1 | don_brk | T | 1758.0 | 0.7 | -27664.6 | -28481.4 | -328.0 |  | -0.0 | -226.1 | -289.0 |
| USDCHF | H1 | don_brk |  | 2378.0 | 0.8 | -32544.1 | -33204.8 | -373.3 |  | -0.0 | -312.3 | -281.1 |
| USDCHF | H1 | ha_flip | T | 2580.0 | 0.7 | -37595.0 | -38440.3 | -364.0 |  | -0.0 | -332.7 | -360.5 |
| USDCHF | H1 | ha_flip |  | 9120.0 | 0.6 | -113560.0 | -113950.7 | -439.6 |  | -0.0 | -1027.3 | -1060.3 |
| USDCHF | H1 | ema_x | T | 600.0 | 0.7 | -9325.8 | -9571.5 | -377.9 |  | -0.0 | -88.3 | -82.1 |
| USDCHF | H1 | ema_x |  | 1088.0 | 0.7 | -15765.6 | -15874.6 | -377.9 |  | -0.0 | -160.3 | -124.8 |
| USDCHF | H1 | ema_slope | T | 1092.0 | 0.7 | -22059.8 | -22410.2 | -370.8 |  | -0.0 | -163.1 | -252.3 |
| USDCHF | H1 | ema_slope |  | 2656.0 | 0.7 | -41052.9 | -41306.3 | -402.8 |  | -0.0 | -374.5 | -379.4 |
| USDCHF | H1 | obv_slope | T | 2044.0 | 0.7 | -30160.0 | -31249.9 | -402.2 |  | -0.0 | -293.2 | -255.7 |
| USDCHF | H1 | obv_slope |  | 8370.0 | 0.6 | -106086.1 | -106605.5 | -434.7 |  | -0.0 | -1018.0 | -916.4 |
| USDCHF | H1 | rsi_rev | T | 184.0 | 0.7 | -3320.3 | -3870.4 | -251.7 |  | -0.0 | -36.8 | -22.4 |
| USDCHF | H1 | cmf_zero |  | 3529.0 | 0.7 | -53540.9 | -53914.8 | -410.8 |  | -0.0 | -498.6 | -481.7 |
| USDCHF | H1 | mfi_rev | T | 374.0 | 0.7 | -6819.6 | -7899.0 | -223.9 |  | -0.0 | -94.2 | -22.4 |
| USDCHF | H1 | mfi_rev |  | 1251.0 | 0.8 | -15553.4 | -15895.2 | -352.7 |  | -0.0 | -205.7 | -62.6 |
| USDCHF | H1 | willr_rev | T | 1666.0 | 0.8 | -19813.5 | -21342.8 | -346.9 |  | -0.0 | -195.6 | -164.2 |
| USDCHF | H4 | dmi_x |  | 511.0 | 0.9 | -2801.5 | -3593.9 | -244.4 |  | -0.0 | -31.9 | -18.5 |
| USDCHF | H4 | cci_mom | T | 480.0 | 0.9 | -2950.0 | -5428.3 | -206.4 |  | -0.0 | -44.9 | -5.3 |
| USDCHF | H4 | cci_mom |  | 760.0 | 0.9 | -2632.1 | -4360.4 | -231.9 |  | -0.0 | -9.5 | -43.0 |
| USDCHF | H4 | cci_rev | T | 313.0 | 0.8 | -3080.1 | -5109.3 | -198.4 |  | -0.0 | -52.0 | 0.8 |
| USDCHF | H4 | cci_rev |  | 941.0 | 0.9 | -6298.8 | -8731.6 | -212.4 |  | -0.0 | -107.6 | 3.3 |
| USDCHF | H4 | stoch_rev | T | 236.0 | 0.8 | -2769.4 | -3725.0 | -165.3 |  | -0.0 | -37.8 | -10.5 |
| USDCHF | H4 | stoch_rev |  | 802.0 | 0.9 | -3703.8 | -4707.8 | -199.2 |  | -0.0 | -38.9 | -28.5 |
| USDCHF | H4 | macd_zero |  | 492.0 | 1.0 | 188.9 | -3105.7 | -193.4 |  | 0.0 | 25.4 | -27.8 |
| USDCHF | H4 | macd_x | T | 417.0 | 0.8 | -3975.6 | -6164.5 | -219.9 |  | -0.0 | -50.1 | -20.2 |
| USDCHF | H4 | macd_x |  | 1095.0 | 0.8 | -9220.8 | -10209.1 | -293.2 |  | -0.0 | -81.8 | -89.9 |
| USDCHF | H4 | rsi_mom | T | 457.0 | 0.9 | -1991.5 | -3485.3 | -230.1 |  | -0.0 | -28.3 | -6.1 |
| USDCHF | H1 | bb_rev | T | 913.0 | 0.7 | -14287.6 | -14877.7 | -378.0 |  | -0.0 | -138.4 | -121.8 |
| USDCHF | H1 | don_rev | T | 929.0 | 0.8 | -12119.2 | -13573.2 | -341.0 |  | -0.0 | -89.0 | -139.4 |
| EURUSD | H4 | cmf_zero | T | 465.0 | 0.9 | -2238.7 | -4357.6 | -246.5 |  | -0.0 | -47.9 | 13.2 |
| AUDUSD | H4 | trend_vote v=6 | T | 378.0 | 0.8 | -3580.9 | -4336.5 | -188.9 |  | -0.0 | -31.9 | -34.8 |
| AUDUSD | H4 | trend_vote v=6 |  | 498.0 | 0.8 | -5940.3 | -6232.8 | -188.9 |  | -0.0 | -47.4 | -64.5 |
| AUDUSD | H4 | trend_vote v=5 |  | 568.0 | 0.9 | -2146.1 | -3853.5 | -223.9 |  | -0.0 | 18.5 | -67.8 |
| AUDUSD | H4 | trend_vote v=4 |  | 693.0 | 0.9 | -4055.0 | -4717.0 | -290.3 |  | -0.0 | -3.8 | -79.8 |
| EURUSD | H4 | cmf_zero |  | 865.0 | 0.8 | -6873.6 | -7362.0 | -325.3 |  | -0.0 | -79.7 | -43.6 |
| EURUSD | H4 | mfi_rev | T | 75.0 | 0.6 | -1714.3 | -2642.9 | -151.8 |  | -0.0 | 11.7 | -50.3 |
| GBPUSD | H4 | bb_rev |  | 684.0 | 1.0 | -1425.7 | -2806.4 | -196.0 |  | -0.0 | -29.7 | 7.5 |
| GBPUSD | H4 | dmi_x | T | 215.0 | 0.8 | -2970.7 | -3547.9 | -154.3 |  | -0.0 | -43.0 | -8.1 |
| GBPUSD | H4 | dmi_x |  | 530.0 | 1.0 | 476.4 | -3018.8 | -226.7 |  | 0.0 | 38.9 | -38.7 |
| GBPUSD | H4 | cci_mom |  | 776.0 | 1.0 | 1059.6 | -2651.1 | -264.2 |  | 0.0 | 30.3 | -15.8 |
| USDJPY | H4 | trend_vote v=6 | T | 359.0 | 0.9 | -1009.5 | -2713.1 | -169.5 |  | -0.0 | 4.3 | -26.4 |
| USDJPY | H4 | trend_vote v=6 |  | 463.0 | 0.9 | -1804.5 | -2807.5 | -235.0 |  | -0.0 | -10.5 | -24.5 |
| USDJPY | H4 | trend_vote v=5 | T | 357.0 | 0.9 | -1928.9 | -3232.3 | -223.4 |  | -0.0 | -4.9 | -34.0 |
| USDCHF | H1 | cmf_zero | T | 1778.0 | 0.7 | -29794.9 | -30318.5 | -364.6 |  | -0.0 | -230.2 | -328.1 |
| USDCHF | H4 | willr_rev | T | 393.0 | 0.9 | -2047.8 | -3547.0 | -213.6 |  | -0.0 | -18.7 | -19.3 |
| USDCHF | H4 | willr_rev |  | 1134.0 | 0.9 | -5909.6 | -6418.5 | -193.1 |  | -0.0 | -39.0 | -74.3 |
| USDCHF | H4 | aroon_x |  | 537.0 | 1.0 | -680.9 | -2970.1 | -254.0 |  | -0.0 | 15.2 | -33.2 |
| USDCHF | H4 | squeeze_brk | T | 185.0 | 0.8 | -2541.1 | -3190.4 | -176.1 |  | -0.0 | -20.0 | -27.9 |
| USDCHF | H4 | squeeze_brk |  | 244.0 | 0.8 | -3241.4 | -3839.9 | -250.3 |  | -0.0 | -11.6 | -53.1 |
| USDCHF | H4 | kelt_brk | T | 303.0 | 0.9 | -2622.6 | -3449.7 | -169.4 |  | -0.0 | -42.4 | -1.6 |
| USDCHF | H4 | kelt_brk |  | 370.0 | 1.0 | -424.7 | -2863.9 | -169.4 |  | -0.0 | -19.6 | 15.6 |
| USDCHF | H4 | bb_brk | T | 398.0 | 0.9 | -2902.6 | -4914.9 | -206.4 |  | -0.0 | -46.2 | -2.7 |
| USDCHF | H4 | bb_brk |  | 554.0 | 1.0 | -745.7 | -2644.2 | -208.2 |  | -0.0 | -9.3 | -3.9 |
| USDCHF | H4 | bb_rev | T | 188.0 | 0.8 | -1809.2 | -3435.6 | -232.8 |  | -0.0 | -33.8 | 4.5 |
| USDCHF | H4 | bb_rev |  | 660.0 | 0.8 | -6786.6 | -7735.3 | -232.8 |  | -0.0 | -60.1 | -66.2 |
| USDCHF | H4 | dmi_x | T | 193.0 | 0.9 | -1154.2 | -3915.5 | -187.2 |  | -0.0 | -44.3 | 31.4 |
| USDCHF | H4 | don_rev | T | 238.0 | 0.8 | -3199.4 | -4582.7 | -232.8 |  | -0.0 | -50.1 | -4.0 |
| USDCHF | H4 | don_rev |  | 834.0 | 0.8 | -7193.5 | -7570.1 | -232.8 |  | -0.0 | -53.2 | -83.3 |
| USDCHF | H4 | don_brk | T | 463.0 | 0.8 | -5041.3 | -6303.6 | -206.4 |  | -0.0 | -73.5 | -13.1 |
| USDCHF | H4 | rsi_mom |  | 1595.0 | 0.8 | -10686.1 | -10938.8 | -258.0 |  | -0.0 | -88.9 | -111.5 |
| USDCHF | H4 | ha_flip | T | 678.0 | 0.8 | -6489.4 | -8099.1 | -221.1 |  | -0.0 | -70.6 | -47.0 |
| USDCHF | H4 | ha_flip |  | 2204.0 | 0.8 | -14335.9 | -14763.0 | -270.5 |  | -0.0 | -151.1 | -109.8 |
| GBPUSD | H4 | cci_rev | T | 351.0 | 0.8 | -3526.9 | -4946.3 | -196.3 |  | -0.0 | -52.4 | -7.9 |
| USDCHF | H4 | ema_slope | T | 313.0 | 0.9 | -1261.1 | -2514.0 | -197.9 |  | -0.0 | -13.7 | -9.2 |
| USDCHF | H4 | ema_slope |  | 719.0 | 0.8 | -4572.9 | -5829.3 | -258.4 |  | -0.0 | -22.6 | -67.0 |
| USDCHF | H4 | obv_slope | T | 542.0 | 0.9 | -4130.8 | -6679.0 | -235.6 |  | -0.0 | -65.5 | -4.2 |
| USDCHF | H4 | obv_slope |  | 2196.0 | 0.8 | -13637.2 | -14335.5 | -293.2 |  | -0.0 | -135.8 | -114.3 |
| USDCHF | H4 | cmf_zero | T | 417.0 | 0.9 | -2126.4 | -3141.4 | -198.0 |  | -0.0 | -19.4 | -20.1 |
| USDCHF | H4 | cmf_zero |  | 815.0 | 0.9 | -4828.4 | -5528.3 | -228.8 |  | -0.0 | -63.8 | -20.8 |
| EURJPY | H4 | bb_rev |  | 688.0 | 0.9 | -3147.6 | -5257.0 | -454.8 |  | -0.0 | -13.3 | -49.0 |
| GBPUSD | H4 | cci_rev |  | 970.0 | 0.9 | -2390.7 | -4291.6 | -186.7 |  | -0.0 | -48.3 | 10.6 |
| EURJPY | H4 | cci_mom |  | 763.0 | 1.0 | -40.0 | -2551.7 | -238.2 |  | -0.0 | -20.9 | 25.3 |
| EURJPY | H4 | cci_rev | T | 308.0 | 0.8 | -3175.2 | -3825.4 | -454.6 |  | -0.0 | -31.9 | -26.3 |
| EURJPY | H4 | cci_rev |  | 941.0 | 1.0 | -1400.8 | -4023.2 | -454.6 |  | -0.0 | 14.6 | -47.5 |
| EURJPY | H4 | stoch_rev | T | 267.0 | 0.8 | -4062.3 | -4788.7 | -420.0 |  | -0.0 | -67.9 | 0.2 |
| GBPUSD | H4 | stoch_rev | T | 269.0 | 0.8 | -2484.3 | -4389.5 | -181.2 |  | -0.0 | -59.9 | 23.1 |
| XAUUSD | H1 | kelt_brk |  | 1509.0 | 0.9 | -9653.1 | -12038.8 | -288.1 |  | -0.0 | -134.6 | -32.8 |
| XAUUSD | H1 | bb_brk | T | 1563.0 | 1.0 | -3969.3 | -7696.0 | -347.8 |  | -0.0 | -26.1 | -50.0 |
| XAUUSD | H1 | bb_brk |  | 2268.0 | 0.9 | -10915.9 | -11907.1 | -347.8 |  | -0.0 | -89.9 | -115.1 |
| XAUUSD | H1 | bb_rev | T | 846.0 | 0.9 | -4323.2 | -6304.0 | -384.4 |  | -0.0 | -30.8 | -51.6 |
| EURJPY | H4 | rsi_mom | T | 429.0 | 0.8 | -3777.4 | -4187.1 | -453.9 |  | -0.0 | -41.1 | -27.3 |
| EURJPY | H4 | rsi_mom |  | 1495.0 | 0.9 | -2210.4 | -4176.6 | -453.9 |  | -0.0 | -33.6 | -4.1 |
| EURJPY | H4 | cmf_zero |  | 748.0 | 0.9 | -2494.8 | -4189.3 | -454.4 |  | -0.0 | -6.6 | -43.7 |
| EURJPY | H4 | willr_rev | T | 383.0 | 0.8 | -4285.2 | -5154.8 | -419.7 |  | -0.0 | -59.4 | -15.0 |
| EURJPY | H4 | willr_rev |  | 1166.0 | 0.9 | -6365.9 | -7935.6 | -419.7 |  | -0.0 | -71.4 | -43.4 |
| EURJPY | H4 | aroon_x | T | 268.0 | 0.9 | -1396.1 | -2847.5 | -204.1 |  | -0.0 | -26.4 | 3.9 |
| EURJPY | H4 | aroon_x |  | 555.0 | 0.9 | -2063.6 | -2976.1 | -244.5 |  | -0.0 | -18.1 | -20.3 |
| EURJPY | H4 | squeeze_brk | T | 192.0 | 0.8 | -2318.9 | -3397.0 | -189.7 |  | -0.0 | -46.6 | 10.0 |
| EURJPY | H4 | squeeze_brk |  | 252.0 | 0.9 | -1669.4 | -2411.4 | -189.7 |  | -0.0 | -24.4 | -4.3 |
| EURJPY | H4 | kelt_rev |  | 472.0 | 0.9 | -1743.8 | -2565.5 | -454.8 |  | -0.0 | -34.2 | 6.4 |
| EURJPY | H4 | kelt_brk | T | 316.0 | 0.8 | -2746.8 | -3654.7 | -183.6 |  | -0.0 | -19.3 | -33.0 |
| USDCHF | H4 | don_brk |  | 626.0 | 0.9 | -4713.0 | -5910.8 | -250.3 |  | -0.0 | -60.6 | -22.5 |
| EURJPY | H4 | macd_zero | T | 231.0 | 0.8 | -2442.6 | -3819.8 | -213.8 |  | -0.0 | -50.3 | 12.0 |
| EURJPY | H4 | macd_zero |  | 471.0 | 1.0 | -394.1 | -2725.8 | -222.1 |  | -0.0 | -31.5 | 31.2 |
| EURJPY | H4 | macd_x | T | 430.0 | 0.9 | -2918.5 | -4413.6 | -454.2 |  | -0.0 | -41.3 | -9.2 |
| EURJPY | H4 | macd_x |  | 1096.0 | 0.9 | -3946.0 | -5665.0 | -454.2 |  | -0.0 | -52.0 | -17.2 |
| XAUUSD | H1 | cmf_zero |  | 3211.0 | 0.8 | -22038.6 | -23577.0 | -382.6 |  | -0.0 | -328.9 | -48.0 |
| XAUUSD | H1 | mfi_rev |  | 1084.0 | 0.8 | -12509.0 | -14026.5 | -293.5 |  | -0.0 | -80.6 | -159.9 |
| XAUUSD | H1 | willr_rev | T | 1501.0 | 0.9 | -10110.7 | -12874.2 | -341.3 |  | -0.0 | -55.0 | -141.9 |
| EURUSD | H4 | dmi_x |  | 521.0 | 0.7 | -7199.6 | -8487.4 | -255.8 |  | -0.0 | -86.5 | -41.9 |
| EURUSD | H4 | cci_mom | T | 482.0 | 1.0 | -1161.5 | -4139.2 | -243.8 |  | -0.0 | -59.8 | 50.5 |
| EURUSD | H4 | cci_mom |  | 775.0 | 0.9 | -3631.6 | -5105.4 | -338.6 |  | -0.0 | -49.4 | -13.9 |
| EURUSD | H4 | cci_rev | T | 341.0 | 0.8 | -3008.9 | -3459.7 | -188.1 |  | -0.0 | -31.1 | -23.8 |
| EURUSD | H4 | cci_rev |  | 986.0 | 0.9 | -5596.5 | -6912.5 | -211.0 |  | -0.0 | -29.4 | -79.9 |
| EURUSD | H4 | stoch_rev | T | 264.0 | 0.9 | -1797.6 | -3701.5 | -190.3 |  | -0.0 | -22.1 | -9.9 |
| EURUSD | H4 | stoch_rev |  | 864.0 | 0.8 | -7912.4 | -8602.1 | -338.6 |  | -0.0 | -68.2 | -79.6 |
| EURUSD | H4 | macd_zero | T | 229.0 | 1.0 | 565.4 | -2505.1 | -200.3 |  | 0.0 | -11.7 | 26.4 |
| XAUUSD | H1 | kelt_brk | T | 1234.0 | 0.9 | -8346.5 | -10534.9 | -277.0 |  | -0.0 | -97.3 | -52.2 |
| EURJPY | H4 | kelt_brk |  | 391.0 | 0.8 | -3663.6 | -4642.3 | -192.7 |  | -0.0 | -14.2 | -58.6 |
| EURJPY | H4 | bb_brk | T | 402.0 | 0.9 | -1165.1 | -2893.1 | -200.4 |  | -0.0 | -23.4 | 5.0 |
| EURJPY | H4 | bb_brk |  | 568.0 | 1.0 | -1374.1 | -2993.9 | -207.5 |  | -0.0 | -5.0 | -22.4 |
| EURJPY | H4 | bb_rev | T | 201.0 | 0.7 | -4059.5 | -4523.8 | -454.8 |  | -0.0 | -48.1 | -24.4 |
| USDJPY | H4 | trend_vote v=5 |  | 559.0 | 0.9 | -2991.7 | -3828.9 | -235.0 |  | -0.0 | -13.6 | -45.3 |
| USDJPY | H4 | trend_vote v=4 | T | 309.0 | 0.9 | -1630.6 | -2816.3 | -289.7 |  | -0.0 | -4.7 | -28.1 |
| USDJPY | H4 | trend_vote v=4 |  | 680.0 | 0.9 | -2611.8 | -3304.9 | -289.7 |  | -0.0 | -17.0 | -33.1 |
| GBPUSD | H4 | stoch_rev |  | 842.0 | 1.0 | -2048.8 | -5552.7 | -197.7 |  | -0.0 | -67.6 | 41.8 |
| GBPUSD | H4 | macd_x |  | 1085.0 | 1.0 | -2189.0 | -4881.9 | -337.7 |  | -0.0 | -69.1 | 40.8 |
| GBPUSD | H4 | rsi_mom | T | 429.0 | 0.9 | -2130.8 | -3879.7 | -319.3 |  | -0.0 | -34.0 | -1.9 |
| GBPUSD | H4 | rsi_mom |  | 1518.0 | 0.9 | -3330.1 | -3546.4 | -319.3 |  | -0.0 | -24.0 | -39.3 |
| GBPUSD | H4 | cmf_zero |  | 881.0 | 0.8 | -6374.0 | -6806.1 | -301.0 |  | -0.0 | -43.2 | -78.8 |
| GBPUSD | H4 | mfi_rev |  | 268.0 | 1.0 | -606.9 | -2843.5 | -186.7 |  | -0.0 | -6.3 | -4.7 |
| GBPUSD | H4 | willr_rev | T | 416.0 | 0.8 | -4075.3 | -6262.1 | -224.9 |  | -0.0 | -76.5 | 10.7 |
| GBPUSD | H4 | willr_rev |  | 1182.0 | 0.9 | -4575.2 | -7575.9 | -218.2 |  | -0.0 | -91.3 | 18.8 |
| EURJPY | H4 | stoch_rev |  | 839.0 | 0.9 | -3440.7 | -4478.3 | -420.0 |  | -0.0 | -53.8 | -4.4 |
| GBPUSD | H4 | aroon_x |  | 524.0 | 1.0 | 206.0 | -3462.2 | -282.6 |  | 0.0 | 40.0 | -45.7 |
| GBPUSD | H4 | squeeze_brk |  | 242.0 | 0.8 | -2530.3 | -3639.2 | -179.6 |  | -0.0 | -0.5 | -52.0 |
| GBPJPY | H4 | rsi_mom |  | 1438.0 | 0.9 | -2347.3 | -5014.7 | -290.8 |  | -0.0 | -33.4 | -7.2 |
| GBPUSD | H4 | kelt_rev |  | 504.0 | 1.0 | 380.7 | -3067.5 | -215.6 |  | 0.0 | -36.3 | 53.3 |
| GBPJPY | H4 | rsi_rev |  | 362.0 | 0.9 | -1848.4 | -3563.0 | -203.5 |  | -0.0 | -49.2 | 22.9 |
| EURJPY | H4 | don_rev | T | 249.0 | 0.7 | -4628.6 | -4865.1 | -420.0 |  | -0.0 | -49.2 | -34.9 |
| EURJPY | H4 | don_rev |  | 819.0 | 0.9 | -6114.4 | -6686.4 | -420.0 |  | -0.0 | -48.2 | -67.2 |
| EURJPY | H4 | don_brk | T | 447.0 | 0.9 | -2713.8 | -3891.9 | -189.7 |  | -0.0 | -31.7 | -16.9 |
| EURJPY | H4 | ha_flip | T | 675.0 | 0.8 | -7087.3 | -8160.6 | -454.6 |  | -0.0 | -75.4 | -53.4 |
| EURJPY | H4 | ha_flip |  | 2233.0 | 0.9 | -6352.0 | -7227.5 | -454.6 |  | -0.0 | -81.2 | -30.9 |
| EURJPY | H4 | ema_x | T | 173.0 | 0.8 | -2412.6 | -3311.4 | -178.9 |  | -0.0 | -28.6 | -14.6 |
| EURJPY | H4 | ema_x |  | 303.0 | 0.9 | -1654.3 | -3211.4 | -178.9 |  | -0.0 | -18.4 | -11.4 |
| EURJPY | H4 | ema_slope | T | 283.0 | 0.8 | -2917.1 | -3387.9 | -423.1 |  | -0.0 | -34.3 | -17.8 |
| EURJPY | H4 | ema_slope |  | 677.0 | 0.9 | -2586.7 | -3833.7 | -423.2 |  | -0.0 | -44.9 | 2.3 |
| EURJPY | H4 | obv_slope | T | 499.0 | 0.8 | -5747.2 | -6640.2 | -454.6 |  | -0.0 | -68.3 | -34.3 |
| EURJPY | H4 | obv_slope |  | 2201.0 | 0.9 | -5697.6 | -7819.9 | -454.6 |  | -0.0 | -68.4 | -33.2 |
| EURJPY | H4 | cmf_zero | T | 397.0 | 0.9 | -2573.9 | -3494.4 | -454.4 |  | -0.0 | -34.2 | -10.8 |
| GBPJPY | H4 | bb_brk |  | 550.0 | 1.0 | 264.9 | -2790.3 | -207.8 |  | 0.0 | -26.6 | 38.8 |
| GBPJPY | H4 | bb_rev | T | 206.0 | 0.8 | -2805.8 | -3471.7 | -242.3 |  | -0.0 | -1.8 | -56.2 |
| GBPJPY | H4 | bb_rev |  | 661.0 | 0.8 | -7052.7 | -8914.1 | -252.7 |  | -0.0 | -62.6 | -68.7 |
| GBPJPY | H4 | dmi_x | T | 198.0 | 0.9 | -1329.0 | -3385.3 | -175.2 |  | -0.0 | -13.5 | -10.8 |
| GBPJPY | H4 | dmi_x |  | 488.0 | 0.9 | -1408.2 | -4499.9 | -220.0 |  | -0.0 | -29.8 | 8.0 |
| GBPJPY | H4 | cci_mom | T | 456.0 | 1.0 | -983.9 | -3575.6 | -270.5 |  | -0.0 | -0.2 | -20.2 |
| GBPJPY | H4 | cci_mom |  | 743.0 | 1.0 | -22.9 | -3789.0 | -270.5 |  | -0.0 | -10.7 | 12.9 |
| GBPJPY | H4 | cci_rev | T | 299.0 | 0.9 | -1339.0 | -3071.4 | -186.5 |  | -0.0 | -3.7 | -23.3 |
| GBPJPY | H4 | cci_rev |  | 934.0 | 0.9 | -2811.3 | -5748.7 | -248.6 |  | -0.0 | -84.5 | 47.0 |
| GBPJPY | H4 | stoch_rev | T | 255.0 | 0.8 | -3201.7 | -4344.7 | -194.6 |  | -0.0 | -19.9 | -41.9 |
| GBPJPY | H4 | stoch_rev |  | 840.0 | 0.8 | -9059.9 | -10058.3 | -218.7 |  | -0.0 | -93.6 | -71.8 |
| GBPJPY | H4 | macd_zero | T | 213.0 | 0.9 | -1426.8 | -2646.6 | -187.9 |  | -0.0 | -9.9 | -17.4 |
| GBPJPY | H4 | macd_zero |  | 459.0 | 1.0 | -343.6 | -3182.3 | -283.5 |  | -0.0 | -11.2 | 6.9 |
| GBPJPY | H4 | macd_x | T | 417.0 | 1.0 | -137.3 | -2513.2 | -201.0 |  | -0.0 | -8.0 | 7.2 |
| GBPJPY | H4 | macd_x |  | 1101.0 | 0.9 | -4119.8 | -5675.2 | -284.9 |  | -0.0 | -79.1 | 13.1 |
| GBPUSD | H4 | kelt_brk | T | 327.0 | 1.0 | 647.9 | -2487.4 | -209.3 |  | 0.0 | 33.6 | -28.5 |
| AUDJPY | H4 | bb_brk | T | 405.0 | 1.0 | -256.4 | -2432.3 | -249.1 |  | -0.0 | 0.9 | -6.4 |
| GBPJPY | H4 | rsi_mom | T | 425.0 | 0.8 | -3862.9 | -5993.1 | -186.6 |  | -0.0 | -18.7 | -57.1 |
| GBPJPY | H4 | obv_slope |  | 2229.0 | 0.8 | -9977.1 | -11366.6 | -267.6 |  | -0.0 | -89.4 | -96.1 |
| GBPJPY | H4 | cmf_zero | T | 414.0 | 1.0 | -947.7 | -3941.2 | -242.5 |  | -0.0 | 8.1 | -29.8 |
| GBPJPY | H4 | cmf_zero |  | 769.0 | 1.0 | -1285.8 | -4480.7 | -242.5 |  | -0.0 | -38.9 | 21.9 |
| GBPJPY | H4 | mfi_rev |  | 258.0 | 0.9 | -960.0 | -2824.7 | -187.4 |  | -0.0 | -20.4 | 5.5 |
| GBPJPY | H4 | willr_rev | T | 392.0 | 0.8 | -3547.5 | -4905.0 | -187.4 |  | -0.0 | -16.6 | -53.1 |
| GBPJPY | H4 | willr_rev |  | 1165.0 | 0.8 | -7937.2 | -9656.2 | -227.1 |  | -0.0 | -107.8 | -30.6 |
| GBPJPY | H4 | aroon_x | T | 253.0 | 0.9 | -1590.5 | -2670.7 | -184.8 |  | -0.0 | -10.6 | -19.9 |
| GBPJPY | H4 | aroon_x |  | 525.0 | 0.9 | -3493.1 | -4927.1 | -197.3 |  | -0.0 | -47.8 | -13.1 |
| GBPUSD | H4 | bb_brk | T | 403.0 | 1.0 | -955.3 | -2422.8 | -264.2 |  | -0.0 | -20.3 | 5.4 |
| GBPCHF | H4 | trend_vote v=6 | T | 381.0 | 0.8 | -3911.9 | -4361.4 | -184.0 |  | -0.0 | -13.6 | -64.3 |
| GBPJPY | H4 | kelt_rev |  | 482.0 | 0.9 | -3065.6 | -5436.1 | -252.7 |  | -0.0 | -67.3 | 20.3 |
| GBPJPY | H4 | bb_brk | T | 385.0 | 1.0 | 354.7 | -2482.5 | -207.8 |  | 0.0 | -17.5 | 29.3 |
| AUDJPY | H4 | macd_x |  | 1120.0 | 0.9 | -5882.8 | -8216.6 | -324.6 |  | -0.0 | -123.6 | 34.5 |
| AUDJPY | H4 | obv_slope |  | 2288.0 | 0.8 | -13797.7 | -13828.5 | -285.7 |  | -0.0 | -124.0 | -129.9 |
| AUDJPY | H4 | cmf_zero | T | 404.0 | 0.8 | -4746.7 | -5266.1 | -270.1 |  | -0.0 | -28.2 | -63.1 |
| AUDJPY | H4 | rsi_mom | T | 454.0 | 0.8 | -5142.5 | -5843.0 | -254.4 |  | -0.0 | -63.1 | -27.0 |
| AUDJPY | H4 | rsi_mom |  | 1629.0 | 0.8 | -7727.3 | -8490.0 | -305.9 |  | -0.0 | -83.1 | -55.4 |
| AUDJPY | H4 | rsi_rev |  | 336.0 | 1.0 | -903.9 | -3610.2 | -192.8 |  | -0.0 | -47.5 | 41.5 |
| GBPJPY | H4 | don_rev | T | 248.0 | 0.8 | -2230.6 | -3342.5 | -192.2 |  | -0.0 | -16.0 | -26.5 |
| GBPJPY | H4 | don_rev |  | 835.0 | 0.9 | -4474.4 | -7265.0 | -255.9 |  | -0.0 | -64.2 | -13.0 |
| GBPJPY | H4 | don_brk | T | 446.0 | 1.1 | 2123.7 | -2571.1 | -213.7 |  | 0.0 | 11.9 | 29.4 |
| GBPJPY | H4 | don_brk |  | 610.0 | 1.1 | 3241.9 | -2881.2 | -213.7 |  | 0.0 | 18.0 | 45.0 |
| GBPJPY | H4 | ha_flip | T | 634.0 | 0.9 | -2017.9 | -4231.8 | -223.7 |  | -0.0 | -4.2 | -36.7 |
| GBPJPY | H4 | ha_flip |  | 2223.0 | 0.9 | -3743.1 | -7847.6 | -239.1 |  | -0.0 | -81.2 | 23.5 |
| GBPCHF | H4 | trend_vote v=6 |  | 478.0 | 0.8 | -4278.8 | -5696.4 | -184.0 |  | -0.0 | -5.9 | -81.7 |
| GBPCHF | H4 | trend_vote v=5 | T | 339.0 | 0.8 | -3039.0 | -5060.5 | -184.3 |  | -0.0 | 26.9 | -97.5 |
| GBPJPY | H4 | ema_slope | T | 267.0 | 0.8 | -2398.7 | -3309.3 | -240.8 |  | -0.0 | -10.7 | -36.6 |
| GBPJPY | H4 | ema_slope |  | 628.0 | 1.0 | -359.7 | -2962.7 | -240.9 |  | -0.0 | -2.5 | -4.3 |
| GBPJPY | H4 | obv_slope | T | 530.0 | 0.8 | -4885.2 | -6759.8 | -207.5 |  | -0.0 | -30.7 | -63.4 |
| CHFJPY | H4 | rsi_mom |  | 1587.0 | 0.8 | -8094.3 | -9505.6 | -270.0 |  | -0.0 | -92.7 | -52.7 |
| AUDJPY | H4 | don_rev | T | 257.0 | 0.8 | -3423.7 | -4029.2 | -185.8 |  | -0.0 | -48.6 | -9.5 |
| AUDJPY | H4 | bb_rev | T | 199.0 | 0.8 | -2307.2 | -2606.8 | -209.8 |  | -0.0 | -33.9 | -5.0 |
| AUDJPY | H4 | bb_rev |  | 682.0 | 0.8 | -5917.0 | -6634.1 | -235.7 |  | -0.0 | -64.1 | -41.8 |
| AUDJPY | H4 | dmi_x |  | 430.0 | 1.0 | -637.5 | -2804.2 | -211.9 |  | -0.0 | 6.6 | -21.7 |
| AUDJPY | H4 | cci_mom | T | 475.0 | 0.8 | -4738.8 | -4871.0 | -233.3 |  | -0.0 | -59.2 | -23.5 |
| AUDJPY | H4 | cci_mom |  | 783.0 | 0.9 | -4199.0 | -4857.0 | -284.8 |  | -0.0 | -62.7 | -7.8 |
| AUDJPY | H4 | cci_rev | T | 322.0 | 0.8 | -3028.1 | -3343.2 | -173.8 |  | -0.0 | -37.9 | -15.0 |
| AUDJPY | H4 | cci_rev |  | 944.0 | 0.9 | -5448.8 | -8292.2 | -231.7 |  | -0.0 | -70.7 | -23.7 |
| AUDJPY | H4 | stoch_rev | T | 267.0 | 0.8 | -3273.6 | -3831.0 | -206.2 |  | -0.0 | -52.4 | -1.6 |
| AUDJPY | H4 | stoch_rev |  | 832.0 | 0.8 | -7461.4 | -9588.1 | -219.5 |  | -0.0 | -120.5 | -2.3 |
| AUDJPY | H4 | macd_zero | T | 230.0 | 0.8 | -2254.7 | -2731.1 | -202.1 |  | -0.0 | -9.8 | -34.5 |
| AUDJPY | H4 | macd_zero |  | 512.0 | 0.9 | -1739.0 | -2409.0 | -215.7 |  | -0.0 | -9.4 | -24.2 |
| AUDJPY | H4 | macd_x | T | 434.0 | 0.7 | -7771.8 | -7825.7 | -233.1 |  | -0.0 | -91.3 | -45.8 |
| AUDJPY | H4 | ema_slope |  | 686.0 | 0.9 | -2012.6 | -3337.1 | -262.6 |  | -0.0 | 8.9 | -53.2 |
| AUDJPY | H4 | obv_slope | T | 514.0 | 0.7 | -7348.0 | -7488.4 | -288.8 |  | -0.0 | -61.1 | -75.5 |
| GBPCHF | H4 | trend_vote v=5 |  | 544.0 | 0.9 | -3372.5 | -5046.1 | -277.3 |  | -0.0 | 10.6 | -83.8 |
| CHFJPY | H4 | cci_mom |  | 732.0 | 1.0 | -604.5 | -3501.6 | -258.4 |  | -0.0 | -18.8 | 10.9 |
| AUDJPY | H4 | cmf_zero |  | 802.0 | 0.8 | -6839.4 | -7192.0 | -270.1 |  | -0.0 | -22.2 | -114.3 |
| AUDJPY | H4 | mfi_rev |  | 220.0 | 0.8 | -1984.6 | -4297.5 | -219.5 |  | -0.0 | -38.1 | 7.0 |
| AUDJPY | H4 | willr_rev | T | 396.0 | 0.7 | -6065.2 | -6152.6 | -261.6 |  | -0.0 | -71.9 | -35.0 |
| AUDJPY | H4 | willr_rev |  | 1166.0 | 0.8 | -10696.9 | -12393.2 | -261.6 |  | -0.0 | -111.9 | -80.7 |
| AUDJPY | H4 | aroon_x | T | 262.0 | 0.9 | -1857.3 | -3339.3 | -233.1 |  | -0.0 | -50.1 | 25.0 |
| AUDJPY | H4 | aroon_x |  | 565.0 | 0.9 | -2286.3 | -4084.0 | -284.5 |  | -0.0 | -48.5 | 14.0 |
| GBPCHF | H4 | trend_vote v=4 | T | 305.0 | 0.8 | -3793.0 | -4478.8 | -194.3 |  | -0.0 | -11.5 | -64.3 |
| GBPCHF | H4 | trend_vote v=4 |  | 640.0 | 0.9 | -3904.9 | -6080.5 | -283.4 |  | -0.0 | -9.9 | -68.7 |
| AUDJPY | H4 | kelt_rev |  | 469.0 | 0.9 | -2620.9 | -5206.0 | -219.7 |  | -0.0 | -51.4 | 10.7 |
| EURCHF | H4 | trend_vote v=6 | T | 369.0 | 0.8 | -5350.5 | -6314.4 | -186.8 |  | -0.0 | -48.6 | -50.8 |
| CHFJPY | H4 | macd_zero |  | 486.0 | 0.9 | -2399.7 | -3478.0 | -227.9 |  | -0.0 | -10.4 | -37.0 |
| CHFJPY | H4 | macd_x | T | 441.0 | 0.9 | -3431.7 | -5074.3 | -315.9 |  | -0.0 | -39.9 | -21.6 |
| CHFJPY | H4 | macd_x |  | 1132.0 | 0.9 | -6493.2 | -8301.5 | -315.9 |  | -0.0 | -56.6 | -64.6 |
| CHFJPY | H4 | rsi_mom | T | 446.0 | 0.9 | -2938.1 | -3836.4 | -270.0 |  | -0.0 | -18.0 | -38.6 |
| CHFJPY | H4 | obv_slope | T | 513.0 | 0.9 | -3824.1 | -5234.8 | -316.2 |  | -0.0 | -2.8 | -76.2 |
| CHFJPY | H4 | obv_slope |  | 2221.0 | 0.8 | -9796.5 | -11177.1 | -315.9 |  | -0.0 | -94.5 | -86.0 |
| AUDJPY | H4 | don_rev |  | 839.0 | 0.8 | -10466.9 | -11755.6 | -257.4 |  | -0.0 | -107.7 | -81.2 |
| EURCHF | H4 | trend_vote v=6 |  | 458.0 | 0.8 | -6590.5 | -7931.7 | -225.1 |  | -0.0 | -63.9 | -57.4 |
| EURCHF | H4 | trend_vote v=5 | T | 377.0 | 0.8 | -4028.9 | -4529.1 | -398.0 |  | -0.0 | -51.4 | -19.7 |
| AUDJPY | H4 | ha_flip | T | 659.0 | 0.8 | -5882.8 | -6023.2 | -264.6 |  | -0.0 | -66.4 | -38.2 |
| AUDJPY | H4 | ha_flip |  | 2241.0 | 0.9 | -9405.9 | -10686.5 | -315.9 |  | -0.0 | -134.4 | -25.1 |
| AUDJPY | H4 | ema_slope | T | 269.0 | 0.8 | -3184.2 | -3386.9 | -200.7 |  | -0.0 | -20.4 | -40.4 |
| CHFJPY | H4 | kelt_rev |  | 411.0 | 1.0 | -160.0 | -2818.4 | -334.5 |  | -0.0 | -25.8 | 28.9 |
| CHFJPY | H4 | kelt_brk | T | 270.0 | 0.8 | -2670.5 | -4131.0 | -217.6 |  | -0.0 | -29.9 | -18.2 |
| CHFJPY | H4 | kelt_brk |  | 337.0 | 0.8 | -4883.8 | -5369.2 | -254.9 |  | -0.0 | -31.2 | -62.8 |
| CHFJPY | H4 | bb_brk | T | 387.0 | 0.9 | -2447.4 | -3718.1 | -217.6 |  | -0.0 | -23.5 | -21.6 |
| CHFJPY | H4 | bb_brk |  | 547.0 | 0.9 | -1851.3 | -3390.8 | -219.9 |  | -0.0 | -24.2 | -8.3 |
| CHFJPY | H4 | bb_rev | T | 198.0 | 0.8 | -2291.4 | -3904.8 | -232.9 |  | -0.0 | -22.5 | -19.6 |
| CHFJPY | H4 | bb_rev |  | 666.0 | 0.9 | -5150.7 | -6331.6 | -232.9 |  | -0.0 | -48.8 | -46.3 |
| USDJPY | H4 | rsi_mom |  | 1467.0 | 0.9 | -3144.2 | -4566.3 | -306.4 |  | -0.0 | -11.3 | -51.4 |
| NZDJPY | H4 | macd_x |  | 1101.0 | 0.8 | -7865.4 | -8679.8 | -330.2 |  | -0.0 | -104.1 | -31.6 |
| NZDJPY | H4 | rsi_mom | T | 395.0 | 0.8 | -4011.9 | -5245.9 | -184.4 |  | -0.0 | -12.5 | -67.7 |
| NZDJPY | H4 | rsi_mom |  | 1520.0 | 0.8 | -8462.9 | -9878.7 | -263.3 |  | -0.0 | -72.2 | -84.6 |
| CHFJPY | H4 | cci_rev | T | 324.0 | 0.8 | -3962.1 | -4720.2 | -334.3 |  | -0.0 | -33.7 | -40.4 |
| CHFJPY | H4 | cci_rev |  | 947.0 | 0.8 | -6702.6 | -7035.9 | -334.3 |  | -0.0 | -64.9 | -58.6 |
| CHFJPY | H4 | stoch_rev | T | 249.0 | 0.8 | -2258.8 | -4022.8 | -296.6 |  | -0.0 | -26.6 | -13.8 |
| CHFJPY | H4 | stoch_rev |  | 799.0 | 0.9 | -3827.3 | -4777.4 | -296.6 |  | -0.0 | -50.7 | -16.4 |
| USDJPY | H4 | willr_rev | T | 388.0 | 1.0 | -766.9 | -3496.0 | -218.2 |  | -0.0 | 4.3 | -21.4 |
| GBPUSD | H4 | don_rev | T | 265.0 | 0.9 | -1983.1 | -3178.3 | -198.6 |  | -0.0 | -35.4 | 2.9 |
| EURUSD | H4 | trend_vote v=6 |  | 502.0 | 0.9 | -2773.5 | -3560.5 | -180.4 |  | -0.0 | -28.7 | -21.9 |
| EURUSD | H4 | trend_vote v=5 | T | 379.0 | 0.9 | -1946.9 | -3518.8 | -190.2 |  | -0.0 | -11.2 | -26.5 |
| EURUSD | H4 | trend_vote v=5 |  | 575.0 | 0.9 | -3204.7 | -4936.9 | -195.1 |  | -0.0 | -7.3 | -57.6 |
| EURUSD | H4 | trend_vote v=4 | T | 343.0 | 0.9 | -1456.6 | -3514.1 | -217.8 |  | -0.0 | -27.9 | 4.5 |
| EURUSD | H4 | trend_vote v=4 |  | 682.0 | 0.9 | -4315.0 | -5584.6 | -230.6 |  | -0.0 | -48.5 | -29.3 |
| CHFJPY | H4 | ema_slope | T | 285.0 | 0.8 | -3046.8 | -3844.4 | -204.9 |  | -0.0 | -6.9 | -54.9 |
| CHFJPY | H4 | ema_slope |  | 695.0 | 0.8 | -4477.0 | -5328.0 | -261.9 |  | -0.0 | -36.5 | -47.6 |
| NZDJPY | H4 | bb_brk |  | 534.0 | 0.9 | -2941.7 | -3649.9 | -257.8 |  | -0.0 | -25.5 | -28.8 |
| NZDJPY | H4 | bb_rev | T | 203.0 | 0.8 | -1868.4 | -3680.1 | -204.1 |  | -0.0 | -18.2 | -15.8 |
| NZDJPY | H4 | bb_rev |  | 637.0 | 0.9 | -3711.3 | -6526.4 | -250.7 |  | -0.0 | -35.2 | -32.6 |
| NZDJPY | H4 | cci_mom | T | 466.0 | 0.9 | -2818.7 | -3329.9 | -221.5 |  | -0.0 | -23.4 | -29.0 |
| CHFJPY | H4 | cmf_zero | T | 436.0 | 0.9 | -1668.4 | -3297.8 | -316.3 |  | -0.0 | -10.5 | -21.6 |
| CHFJPY | H4 | cmf_zero |  | 814.0 | 0.9 | -3044.7 | -5181.1 | -316.3 |  | -0.0 | -30.8 | -24.9 |
| GBPUSD | H4 | don_rev |  | 837.0 | 0.9 | -2667.7 | -4196.6 | -198.5 |  | -0.0 | -36.8 | -9.6 |
| CHFJPY | H4 | willr_rev | T | 405.0 | 0.8 | -4230.2 | -5972.4 | -296.6 |  | -0.0 | -9.4 | -76.4 |
| CHFJPY | H4 | willr_rev |  | 1139.0 | 0.8 | -10409.4 | -11198.5 | -296.6 |  | -0.0 | -94.8 | -98.3 |
| GBPUSD | H4 | don_brk | T | 450.0 | 1.0 | -854.6 | -3055.8 | -301.0 |  | -0.0 | 10.9 | -31.5 |
| CHFJPY | H4 | squeeze_brk | T | 166.0 | 0.8 | -1627.7 | -2787.6 | -194.5 |  | -0.0 | -24.9 | -2.8 |
| CHFJPY | H4 | squeeze_brk |  | 230.0 | 0.9 | -1725.5 | -2578.1 | -194.5 |  | -0.0 | -32.5 | 4.7 |
| NZDJPY | H4 | stoch_rev |  | 783.0 | 0.8 | -7409.7 | -9670.3 | -229.2 |  | -0.0 | -91.7 | -37.9 |
| NZDJPY | H4 | macd_zero | T | 221.0 | 0.8 | -3025.1 | -3895.7 | -191.4 |  | -0.0 | -37.2 | -15.8 |
| NZDJPY | H4 | macd_zero |  | 476.0 | 0.9 | -3073.9 | -4836.6 | -198.0 |  | -0.0 | -37.3 | -16.6 |
| NZDJPY | H4 | macd_x | T | 411.0 | 0.8 | -4714.2 | -5754.6 | -243.9 |  | -0.0 | -41.8 | -45.1 |
| GBPUSD | H4 | don_brk |  | 606.0 | 1.0 | -1494.6 | -3952.7 | -301.0 |  | -0.0 | 17.7 | -53.2 |
| XAUUSD | H4 | trend_vote v=6 |  | 459.0 | 1.0 | 660.8 | -3201.6 | -262.3 |  | 0.0 | 3.8 | 9.0 |
| GBPUSD | H4 | ha_flip | T | 690.0 | 0.9 | -5584.7 | -7024.1 | -293.8 |  | -0.0 | -67.3 | -32.2 |
| NZDJPY | H4 | ha_flip |  | 2066.0 | 0.9 | -6237.7 | -9950.8 | -322.9 |  | -0.0 | -47.9 | -69.1 |
| NZDJPY | H4 | ema_x | T | 147.0 | 0.7 | -2668.2 | -3115.3 | -187.8 |  | -0.0 | -25.2 | -23.6 |
| NZDJPY | H4 | rsi_rev |  | 317.0 | 0.9 | -1617.9 | -3673.4 | -198.8 |  | -0.0 | -50.6 | 30.7 |
| CHFJPY | H4 | don_rev | T | 254.0 | 0.9 | -1718.6 | -4012.9 | -296.9 |  | -0.0 | -19.7 | -11.2 |
| CHFJPY | H4 | don_rev |  | 808.0 | 0.8 | -8510.1 | -9397.1 | -296.9 |  | -0.0 | -92.0 | -62.3 |
| CHFJPY | H4 | don_brk | T | 415.0 | 0.9 | -1664.0 | -4340.1 | -194.5 |  | -0.0 | -19.6 | -10.1 |
| CHFJPY | H4 | don_brk |  | 575.0 | 0.9 | -3658.3 | -5838.8 | -194.5 |  | -0.0 | -42.4 | -23.2 |
| CHFJPY | H4 | ha_flip | T | 652.0 | 0.8 | -5302.4 | -7121.8 | -316.2 |  | -0.0 | -44.5 | -54.8 |
| CHFJPY | H4 | ha_flip |  | 2213.0 | 0.8 | -11135.0 | -12418.8 | -316.2 |  | -0.0 | -125.5 | -75.2 |
| NZDJPY | H4 | squeeze_brk |  | 242.0 | 1.0 | -252.5 | -2400.9 | -207.2 |  | -0.0 | 29.9 | -43.3 |
| NZDJPY | H4 | kelt_rev |  | 425.0 | 0.9 | -3433.9 | -5783.0 | -207.1 |  | -0.0 | -79.5 | 29.5 |
| GBPUSD | H4 | ha_flip |  | 2179.0 | 0.9 | -6915.3 | -8507.4 | -271.9 |  | -0.0 | -77.8 | -46.8 |
| GBPUSD | H4 | obv_slope | T | 535.0 | 1.0 | -784.5 | -3339.1 | -326.6 |  | -0.0 | -38.5 | 31.8 |
| NZDJPY | H4 | aroon_x |  | 520.0 | 0.8 | -6437.6 | -7171.3 | -227.7 |  | -0.0 | -45.9 | -75.8 |
| CADJPY | H4 | cci_rev |  | 945.0 | 0.8 | -6729.8 | -7387.7 | -190.1 |  | -0.0 | -88.4 | -29.7 |
| CADJPY | H4 | stoch_rev | T | 276.0 | 0.7 | -4610.6 | -5074.0 | -200.0 |  | -0.0 | -56.1 | -26.0 |
| CADJPY | H4 | stoch_rev |  | 853.0 | 0.8 | -9750.4 | -10514.6 | -203.1 |  | -0.0 | -103.6 | -73.6 |
| GBPUSD | H4 | obv_slope |  | 2181.0 | 1.0 | 2149.5 | -3467.5 | -326.6 |  | 0.0 | 34.2 | 2.0 |
| GBPUSD | H4 | cmf_zero | T | 448.0 | 0.9 | -1947.5 | -3558.1 | -301.0 |  | -0.0 | -19.7 | -15.9 |
| NZDJPY | H4 | cci_mom |  | 744.0 | 0.9 | -4254.3 | -5290.1 | -230.3 |  | -0.0 | -36.9 | -41.7 |
| NZDJPY | H4 | cci_rev | T | 308.0 | 0.8 | -3693.6 | -4091.0 | -258.1 |  | -0.0 | -36.1 | -31.0 |
| NZDJPY | H4 | cci_rev |  | 907.0 | 0.9 | -4932.0 | -7551.9 | -258.1 |  | -0.0 | -80.9 | 0.1 |
| NZDJPY | H4 | stoch_rev | T | 247.0 | 0.8 | -2612.4 | -3878.5 | -171.6 |  | -0.0 | -23.8 | -24.2 |
| XAGUSD | H4 | trend_vote v=6 | T | 350.0 | 0.8 | -3881.3 | -4945.4 | -176.2 |  | -0.0 | -58.1 | -8.3 |
| XAGUSD | H4 | trend_vote v=6 |  | 471.0 | 0.8 | -4649.1 | -6254.7 | -176.2 |  | -0.0 | -72.8 | -5.9 |
| XAGUSD | H4 | trend_vote v=5 | T | 321.0 | 0.8 | -3004.9 | -3890.3 | -172.2 |  | -0.0 | -55.2 | 6.4 |
| XAGUSD | H4 | trend_vote v=5 |  | 541.0 | 0.8 | -4846.4 | -7370.3 | -180.4 |  | -0.0 | -96.5 | 19.6 |
| XAGUSD | H4 | trend_vote v=4 | T | 299.0 | 0.8 | -3964.7 | -4476.0 | -188.6 |  | -0.0 | -61.8 | -5.3 |
| XAGUSD | H4 | trend_vote v=4 |  | 685.0 | 0.7 | -9169.5 | -9732.2 | -236.6 |  | -0.0 | -138.7 | -17.6 |
| CADJPY | H4 | squeeze_brk | T | 177.0 | 0.8 | -1589.9 | -2907.0 | -166.3 |  | -0.0 | -34.7 | 10.3 |
| USDJPY | H4 | bb_brk |  | 548.0 | 1.0 | -1045.9 | -2593.0 | -215.8 |  | -0.0 | -12.7 | -5.9 |
| CADJPY | H4 | kelt_rev |  | 490.0 | 0.9 | -3443.4 | -4542.5 | -191.3 |  | -0.0 | -51.5 | -7.3 |
| USDJPY | H4 | bb_rev | T | 187.0 | 1.0 | -445.2 | -2989.9 | -232.6 |  | -0.0 | -11.3 | 4.9 |
| USDJPY | H4 | bb_rev |  | 657.0 | 0.9 | -2408.0 | -4619.4 | -232.6 |  | -0.0 | -29.0 | -13.9 |
| CADJPY | H4 | bb_brk | T | 405.0 | 0.9 | -2761.1 | -3641.7 | -213.1 |  | -0.0 | -41.2 | -6.1 |
| NZDJPY | H4 | ema_slope | T | 255.0 | 0.7 | -3482.1 | -3908.4 | -236.7 |  | -0.0 | -26.6 | -38.7 |
| NZDJPY | H4 | ema_slope |  | 679.0 | 0.8 | -4161.0 | -5281.3 | -322.9 |  | -0.0 | -52.6 | -19.8 |
| NZDJPY | H4 | obv_slope | T | 476.0 | 0.9 | -3339.0 | -4517.4 | -252.4 |  | -0.0 | -17.9 | -46.8 |
| NZDJPY | H4 | obv_slope |  | 2211.0 | 0.8 | -10251.8 | -11468.5 | -297.3 |  | -0.0 | -83.0 | -108.1 |
| NZDJPY | H4 | cmf_zero | T | 376.0 | 0.8 | -4003.3 | -4145.3 | -224.2 |  | -0.0 | -22.4 | -54.9 |
| NZDJPY | H4 | cmf_zero |  | 727.0 | 0.9 | -3965.7 | -4738.6 | -224.2 |  | -0.0 | -32.3 | -41.6 |
| NZDJPY | H4 | mfi_rev |  | 242.0 | 0.8 | -2137.1 | -3596.6 | -171.8 |  | -0.0 | -33.7 | -1.7 |
| NZDJPY | H4 | willr_rev | T | 367.0 | 0.8 | -4823.8 | -5488.6 | -265.0 |  | -0.0 | -58.1 | -26.6 |
| NZDJPY | H4 | willr_rev |  | 1093.0 | 0.9 | -6493.8 | -9621.0 | -270.7 |  | -0.0 | -106.4 | -0.0 |
| NZDJPY | H4 | aroon_x | T | 244.0 | 0.7 | -3634.0 | -3945.8 | -178.2 |  | -0.0 | -13.4 | -58.7 |
| USDJPY | H4 | don_rev |  | 836.0 | 0.9 | -5274.9 | -7384.0 | -217.7 |  | -0.0 | -53.9 | -42.5 |
| CADJPY | H4 | ema_slope | T | 258.0 | 0.8 | -2289.7 | -2850.9 | -213.1 |  | -0.0 | -12.8 | -31.7 |
| CADJPY | H4 | ema_slope |  | 690.0 | 0.9 | -2250.7 | -2862.3 | -223.0 |  | -0.0 | -6.7 | -38.6 |
| CADJPY | H4 | obv_slope | T | 496.0 | 0.9 | -2760.5 | -3549.8 | -241.0 |  | -0.0 | -17.9 | -35.1 |
| CADJPY | H4 | obv_slope |  | 2175.0 | 0.8 | -10126.4 | -10780.0 | -252.5 |  | -0.0 | -112.8 | -69.9 |
| CADJPY | H4 | cmf_zero | T | 395.0 | 0.8 | -3784.4 | -4377.9 | -189.8 |  | -0.0 | -35.5 | -34.5 |
| CADJPY | H4 | macd_x |  | 1043.0 | 1.0 | -1011.7 | -2735.6 | -225.0 |  | -0.0 | -18.8 | 2.4 |
| CADJPY | H4 | rsi_mom | T | 390.0 | 0.8 | -4934.2 | -5299.5 | -208.0 |  | -0.0 | -38.0 | -55.3 |
| CADJPY | H4 | rsi_mom |  | 1450.0 | 0.9 | -4715.1 | -5465.5 | -267.8 |  | -0.0 | -54.7 | -29.8 |
| CADJPY | H4 | rsi_rev |  | 337.0 | 0.9 | -2545.6 | -3266.4 | -200.2 |  | -0.0 | -36.4 | -7.6 |
| NZDJPY | H4 | don_rev | T | 246.0 | 0.8 | -2917.3 | -4364.7 | -236.6 |  | -0.0 | -32.8 | -19.1 |
| NZDJPY | H4 | don_rev |  | 819.0 | 0.8 | -6684.9 | -10000.5 | -236.6 |  | -0.0 | -80.2 | -37.4 |
| NZDJPY | H4 | don_brk | T | 442.0 | 0.9 | -1233.7 | -2895.5 | -187.0 |  | -0.0 | 17.5 | -48.0 |
| NZDJPY | H4 | don_brk |  | 591.0 | 0.9 | -2169.9 | -3519.1 | -227.7 |  | -0.0 | 11.5 | -59.8 |
| NZDJPY | H4 | ha_flip | T | 631.0 | 0.8 | -5279.5 | -5992.2 | -236.4 |  | -0.0 | 1.5 | -111.9 |
| USDJPY | H4 | don_brk | T | 486.0 | 0.9 | -2469.9 | -5180.1 | -248.7 |  | -0.0 | -31.5 | -12.1 |
| USDJPY | H4 | cci_mom | T | 471.0 | 1.0 | -363.0 | -3291.8 | -209.7 |  | -0.0 | -20.9 | 18.6 |
| USDJPY | H4 | cci_rev | T | 313.0 | 1.1 | 1190.8 | -2676.3 | -233.5 |  | 0.0 | 9.7 | 12.7 |
| USDJPY | H4 | cci_rev |  | 941.0 | 1.0 | -255.7 | -3291.4 | -233.5 |  | -0.0 | -29.0 | 30.9 |
| USDJPY | H4 | stoch_rev |  | 866.0 | 0.9 | -5524.2 | -6925.2 | -233.7 |  | -0.0 | -28.7 | -79.2 |
| USDJPY | H4 | macd_zero | T | 246.0 | 1.0 | -59.9 | -2620.7 | -191.5 |  | -0.0 | 23.0 | -30.1 |
| USDJPY | H4 | macd_zero |  | 504.0 | 0.9 | -1906.3 | -3700.9 | -276.0 |  | -0.0 | 0.6 | -40.5 |
| CADJPY | H4 | bb_brk |  | 564.0 | 0.9 | -1671.9 | -3521.0 | -269.5 |  | -0.0 | -34.5 | 8.3 |
| CADJPY | H4 | bb_rev | T | 190.0 | 0.7 | -3994.2 | -4679.0 | -232.5 |  | -0.0 | -33.7 | -41.1 |
| CADJPY | H4 | bb_rev |  | 675.0 | 0.8 | -7248.7 | -9456.3 | -271.4 |  | -0.0 | -36.9 | -104.9 |
| CADJPY | H4 | dmi_x |  | 455.0 | 0.9 | -2715.5 | -3712.6 | -219.4 |  | -0.0 | -18.8 | -33.0 |
| CADJPY | H4 | cci_mom | T | 458.0 | 1.0 | -711.8 | -2571.3 | -232.7 |  | -0.0 | -2.2 | -12.1 |
| CADJPY | H4 | cci_mom |  | 754.0 | 1.0 | -106.2 | -3501.1 | -269.5 |  | -0.0 | 19.1 | -26.0 |
| CADJPY | H4 | cci_rev | T | 298.0 | 0.8 | -4274.3 | -4484.3 | -184.0 |  | -0.0 | -45.6 | -32.0 |
| CADJPY | H4 | don_brk |  | 616.0 | 1.0 | 872.5 | -2482.9 | -269.5 |  | 0.0 | 17.4 | -3.5 |
| CADJPY | H4 | ha_flip | T | 630.0 | 1.0 | -1490.7 | -3294.9 | -218.6 |  | -0.0 | -18.3 | -8.1 |
| CADJPY | H4 | ha_flip |  | 2234.0 | 0.8 | -14612.0 | -15117.7 | -309.3 |  | -0.0 | -148.6 | -118.6 |
| EURGBP | H4 | rsi_mom |  | 1491.0 | 0.8 | -9252.4 | -10425.5 | -287.9 |  | -0.0 | -49.6 | -130.7 |
| EURGBP | H4 | rsi_rev |  | 347.0 | 0.9 | -2040.2 | -2682.0 | -203.6 |  | -0.0 | -33.9 | -0.1 |
| CADJPY | H4 | don_rev | T | 255.0 | 0.7 | -4286.7 | -4556.2 | -230.3 |  | -0.0 | -50.6 | -26.1 |
| CADJPY | H4 | don_rev |  | 862.0 | 0.8 | -10603.0 | -11129.7 | -230.3 |  | -0.0 | -125.4 | -64.2 |
| CADJPY | H4 | don_brk | T | 456.0 | 1.0 | -202.6 | -3179.7 | -196.5 |  | -0.0 | 2.6 | -7.4 |
| EURGBP | H4 | willr_rev |  | 1147.0 | 0.8 | -10667.6 | -10965.2 | -287.9 |  | -0.0 | -169.8 | -10.1 |
| EURGBP | H4 | aroon_x | T | 269.0 | 0.8 | -3744.3 | -3810.8 | -241.5 |  | -0.0 | -23.1 | -49.1 |
| CADJPY | H4 | cmf_zero |  | 790.0 | 0.9 | -2959.8 | -4274.0 | -201.5 |  | -0.0 | -1.4 | -59.9 |
| CADJPY | H4 | mfi_rev |  | 245.0 | 0.9 | -1591.2 | -2455.7 | -168.3 |  | -0.0 | -13.1 | -16.8 |
| CADJPY | H4 | willr_rev | T | 375.0 | 0.8 | -5356.4 | -5722.7 | -231.9 |  | -0.0 | -44.9 | -55.4 |
| CADJPY | H4 | willr_rev |  | 1152.0 | 0.8 | -9921.2 | -11073.7 | -231.9 |  | -0.0 | -104.4 | -76.2 |
| XAUUSD | H4 | trend_vote v=5 |  | 515.0 | 1.1 | 2674.9 | -2490.7 | -262.0 |  | 0.0 | 8.1 | 45.6 |
| XAUUSD | H4 | trend_vote v=4 | T | 310.0 | 1.0 | -343.5 | -2469.3 | -231.8 |  | -0.0 | -23.8 | 22.6 |
| USDJPY | H4 | macd_x | T | 396.0 | 0.9 | -1407.0 | -4430.6 | -182.9 |  | -0.0 | -27.3 | 4.8 |
| USDJPY | H4 | macd_x |  | 1046.0 | 1.0 | -1343.2 | -4204.8 | -249.9 |  | -0.0 | -47.7 | 31.7 |
| USDJPY | H4 | rsi_mom | T | 403.0 | 1.0 | -564.3 | -3294.2 | -247.0 |  | -0.0 | 6.5 | -19.9 |
| EURGBP | H4 | bb_rev |  | 683.0 | 0.8 | -7345.9 | -7566.6 | -214.9 |  | -0.0 | -106.3 | -20.1 |
| EURGBP | H4 | dmi_x | T | 177.0 | 0.7 | -3912.7 | -3984.3 | -184.8 |  | -0.0 | -28.2 | -46.3 |
| EURGBP | H4 | dmi_x |  | 461.0 | 0.9 | -1716.0 | -2605.6 | -254.1 |  | -0.0 | 3.1 | -39.6 |
| EURGBP | H4 | cci_mom | T | 459.0 | 0.9 | -2992.6 | -4542.7 | -255.5 |  | -0.0 | 0.0 | -62.4 |
| EURGBP | H4 | don_rev |  | 792.0 | 0.9 | -4957.3 | -5584.8 | -207.8 |  | -0.0 | -74.0 | -10.7 |
| EURGBP | H4 | don_brk | T | 438.0 | 0.8 | -5307.5 | -5998.2 | -227.4 |  | -0.0 | -23.8 | -80.8 |
| EURGBP | H4 | don_brk |  | 582.0 | 0.9 | -2189.1 | -4585.4 | -227.4 |  | -0.0 | 8.0 | -55.6 |
| EURGBP | H4 | cci_mom |  | 768.0 | 0.9 | -3333.0 | -6147.7 | -255.5 |  | -0.0 | 7.4 | -78.7 |
| EURGBP | H4 | cci_rev |  | 949.0 | 1.0 | -793.6 | -3141.1 | -177.4 |  | -0.0 | -18.4 | 6.4 |
| EURGBP | H4 | stoch_rev | T | 256.0 | 0.8 | -2686.7 | -3125.2 | -185.0 |  | -0.0 | -43.9 | -1.1 |
| EURGBP | H4 | stoch_rev |  | 803.0 | 0.9 | -4477.8 | -5210.2 | -185.0 |  | -0.0 | -78.9 | 5.3 |
| EURGBP | H4 | macd_zero | T | 225.0 | 0.8 | -2048.8 | -2591.4 | -228.9 |  | -0.0 | -15.0 | -23.9 |
| EURGBP | H4 | macd_zero |  | 503.0 | 0.9 | -2646.0 | -5209.2 | -228.9 |  | -0.0 | -21.6 | -28.1 |
| EURGBP | H4 | macd_x | T | 400.0 | 0.8 | -5750.4 | -6597.9 | -201.6 |  | -0.0 | -31.6 | -80.4 |
| EURGBP | H4 | macd_x |  | 1102.0 | 0.8 | -6885.8 | -7312.2 | -254.1 |  | -0.0 | -77.8 | -46.2 |
| EURGBP | H4 | rsi_mom | T | 406.0 | 0.9 | -3221.7 | -5494.5 | -221.7 |  | -0.0 | -6.0 | -59.6 |
| EURGBP | H4 | cmf_zero |  | 829.0 | 0.9 | -3131.1 | -4655.3 | -258.2 |  | -0.0 | -16.8 | -44.2 |
| EURGBP | H4 | mfi_rev |  | 247.0 | 0.9 | -1331.0 | -2996.8 | -171.8 |  | -0.0 | -0.8 | -26.8 |
| EURGBP | H4 | willr_rev | T | 401.0 | 0.8 | -5327.7 | -5454.6 | -207.8 |  | -0.0 | -63.5 | -31.6 |
| EURCHF | H4 | dmi_x |  | 477.0 | 0.7 | -6570.8 | -7012.1 | -280.2 |  | -0.0 | -64.3 | -56.5 |
| EURCHF | H4 | cci_mom | T | 453.0 | 0.8 | -6409.4 | -6904.3 | -403.2 |  | -0.0 | -53.7 | -66.4 |
| EURCHF | H4 | cci_mom |  | 736.0 | 0.7 | -11328.8 | -12363.7 | -403.2 |  | -0.0 | -88.6 | -125.2 |
| EURCHF | H4 | cci_rev | T | 300.0 | 0.8 | -3359.4 | -3586.6 | -444.7 |  | -0.0 | -24.6 | -39.3 |
| EURGBP | H4 | aroon_x |  | 561.0 | 0.9 | -3453.7 | -5436.5 | -246.1 |  | -0.0 | -21.5 | -45.0 |
| EURGBP | H4 | squeeze_brk | T | 182.0 | 0.8 | -1690.9 | -2722.3 | -188.2 |  | -0.0 | 1.2 | -36.8 |
| EURGBP | H4 | kelt_rev | T | 84.0 | 0.6 | -2354.8 | -3111.3 | -182.0 |  | -0.0 | -43.4 | 5.2 |
| EURGBP | H4 | kelt_rev |  | 442.0 | 0.8 | -4755.5 | -5610.0 | -203.6 |  | -0.0 | -87.2 | 9.9 |
| EURGBP | H4 | kelt_brk | T | 321.0 | 0.9 | -2465.4 | -3831.4 | -185.8 |  | -0.0 | 4.1 | -56.5 |
| EURGBP | H4 | kelt_brk |  | 375.0 | 0.9 | -1715.8 | -4013.2 | -202.3 |  | -0.0 | 21.1 | -62.1 |
| EURGBP | H4 | bb_brk | T | 405.0 | 1.0 | -881.3 | -2882.0 | -257.7 |  | -0.0 | 6.3 | -26.3 |
| EURGBP | H4 | bb_brk |  | 565.0 | 1.0 | 318.0 | -2647.2 | -257.7 |  | 0.0 | 18.3 | -16.2 |
| EURGBP | H4 | bb_rev | T | 202.0 | 0.7 | -3438.2 | -3604.0 | -207.8 |  | -0.0 | -49.1 | -10.3 |
| USDJPY | H4 | obv_slope |  | 2200.0 | 0.9 | -4824.2 | -6266.4 | -308.4 |  | -0.0 | -97.8 | 21.7 |
| EURCHF | H4 | rsi_rev |  | 285.0 | 0.8 | -3740.5 | -3859.1 | -194.3 |  | -0.0 | -36.4 | -32.5 |
| EURCHF | H4 | willr_rev | T | 375.0 | 0.8 | -3453.4 | -3920.0 | -194.3 |  | -0.0 | -24.2 | -41.7 |
| EURCHF | H4 | willr_rev |  | 1134.0 | 0.8 | -9596.4 | -9956.1 | -221.3 |  | -0.0 | -85.3 | -93.2 |
| EURCHF | H4 | aroon_x | T | 260.0 | 0.6 | -5760.4 | -6066.3 | -398.0 |  | -0.0 | -47.8 | -60.2 |
| EURCHF | H4 | aroon_x |  | 577.0 | 0.7 | -8678.6 | -9747.3 | -398.4 |  | -0.0 | -76.5 | -85.2 |
| EURCHF | H4 | squeeze_brk |  | 206.0 | 0.8 | -1925.1 | -3357.3 | -227.3 |  | -0.0 | -43.2 | 13.9 |
| EURGBP | H4 | ha_flip | T | 674.0 | 0.9 | -5398.1 | -6156.0 | -266.7 |  | -0.0 | -7.5 | -103.1 |
| EURGBP | H4 | ha_flip |  | 2255.0 | 0.8 | -15565.6 | -16271.9 | -261.9 |  | -0.0 | -152.2 | -134.0 |
| EURGBP | H4 | ema_x | T | 163.0 | 0.8 | -1643.1 | -2470.1 | -252.9 |  | -0.0 | -1.1 | -32.9 |
| EURGBP | H4 | ema_x |  | 279.0 | 0.8 | -2540.8 | -3728.7 | -252.9 |  | -0.0 | -7.1 | -44.1 |
| EURGBP | H4 | ema_slope | T | 273.0 | 0.8 | -3088.2 | -3929.1 | -255.5 |  | -0.0 | -31.8 | -24.6 |
| EURGBP | H4 | ema_slope |  | 688.0 | 0.8 | -5069.4 | -6596.8 | -255.5 |  | -0.0 | -46.3 | -47.7 |
| EURGBP | H4 | obv_slope | T | 495.0 | 0.8 | -4378.3 | -5310.2 | -293.8 |  | -0.0 | -6.4 | -83.2 |
| EURGBP | H4 | obv_slope |  | 2269.0 | 0.8 | -11277.8 | -12075.9 | -353.3 |  | -0.0 | -100.2 | -109.7 |
| EURGBP | H4 | cmf_zero | T | 436.0 | 0.8 | -4431.3 | -7045.5 | -258.2 |  | -0.0 | -16.9 | -71.2 |
| DE40 | H1 | rsi_rev |  | 1159.0 | 0.9 | -4535.7 | -5382.2 | -349.3 |  | -0.0 | -9.2 | -83.0 |
| EURCHF | H4 | don_rev | T | 222.0 | 0.9 | -1695.8 | -2409.4 | -175.8 |  | -0.0 | -8.4 | -24.8 |
| EURCHF | H4 | don_rev |  | 743.0 | 0.8 | -5764.3 | -6594.8 | -197.9 |  | -0.0 | -38.3 | -72.2 |
| EURCHF | H4 | don_brk | T | 412.0 | 0.8 | -5826.9 | -6276.3 | -398.0 |  | -0.0 | -56.2 | -51.1 |
| EURCHF | H4 | don_brk |  | 545.0 | 0.7 | -8284.9 | -9183.4 | -398.0 |  | -0.0 | -90.5 | -59.5 |
| EURCHF | H4 | ha_flip | T | 627.0 | 0.8 | -6280.3 | -6760.7 | -444.7 |  | -0.0 | -75.5 | -36.4 |
| EURCHF | H4 | ha_flip |  | 2247.0 | 0.7 | -23426.9 | -23957.0 | -444.7 |  | -0.0 | -260.2 | -162.8 |
| EURCHF | H4 | cci_rev |  | 915.0 | 0.8 | -9604.9 | -9937.6 | -444.7 |  | -0.0 | -86.3 | -92.3 |
| USDJPY | H4 | cmf_zero | T | 414.0 | 0.9 | -1440.6 | -3831.2 | -260.5 |  | -0.0 | -32.3 | 10.4 |
| EURCHF | H4 | stoch_rev |  | 756.0 | 0.9 | -3779.7 | -4756.2 | -186.5 |  | -0.0 | -20.0 | -53.7 |
| EURCHF | H4 | macd_zero | T | 245.0 | 0.7 | -3635.0 | -4183.1 | -398.0 |  | -0.0 | -45.3 | -19.1 |
| EURCHF | H4 | macd_zero |  | 525.0 | 0.7 | -6632.4 | -7588.3 | -398.4 |  | -0.0 | -70.8 | -49.7 |
| EURCHF | H4 | macd_x | T | 426.0 | 0.7 | -8583.2 | -8894.0 | -431.0 |  | -0.0 | -108.9 | -42.7 |
| EURCHF | H4 | macd_x |  | 1173.0 | 0.7 | -14667.7 | -15369.2 | -431.0 |  | -0.0 | -145.6 | -123.6 |
| EURCHF | H4 | rsi_mom | T | 448.0 | 0.7 | -7557.3 | -7743.5 | -431.0 |  | -0.0 | -102.6 | -29.2 |
| EURCHF | H4 | rsi_mom |  | 1766.0 | 0.6 | -23757.9 | -24483.8 | -431.0 |  | -0.0 | -252.3 | -179.6 |
| DE40 | H1 | bb_rev |  | 2304.0 | 0.9 | -10410.4 | -11417.6 | -567.2 |  | -0.0 | -56.7 | -146.0 |
| DE40 | H1 | dmi_x | T | 648.0 | 0.8 | -7081.6 | -7179.4 | -307.3 |  | -0.0 | -100.9 | -21.4 |
| DE40 | H1 | dmi_x |  | 1555.0 | 0.9 | -6183.3 | -8862.2 | -377.1 |  | -0.0 | -140.9 | 47.3 |
| DE40 | H1 | cci_mom | T | 1638.0 | 1.0 | -2633.5 | -7307.9 | -344.7 |  | -0.0 | -67.1 | 29.1 |
| DE40 | H1 | cci_mom |  | 2676.0 | 1.0 | -6215.3 | -11820.0 | -432.5 |  | -0.0 | -162.5 | 73.7 |
| DE40 | H1 | cci_rev | T | 1108.0 | 0.8 | -10406.3 | -11435.1 | -510.6 |  | -0.0 | -81.1 | -115.5 |
| DE40 | H1 | cci_rev |  | 3196.0 | 0.9 | -18715.6 | -19042.1 | -510.6 |  | -0.0 | -174.7 | -171.5 |
| USDJPY | H4 | cmf_zero |  | 755.0 | 0.9 | -2179.1 | -5762.6 | -251.4 |  | -0.0 | -72.4 | 45.2 |
| EURCHF | H4 | kelt_rev |  | 361.0 | 0.8 | -4270.2 | -4729.5 | -190.6 |  | -0.0 | -40.1 | -38.8 |
| EURCHF | H4 | kelt_brk | T | 247.0 | 0.8 | -2250.1 | -2974.3 | -194.1 |  | -0.0 | -5.0 | -40.7 |
| EURCHF | H4 | kelt_brk |  | 298.0 | 0.8 | -3898.1 | -4447.0 | -224.2 |  | -0.0 | -34.0 | -38.8 |
| EURCHF | H4 | bb_brk | T | 380.0 | 0.7 | -6246.9 | -6935.5 | -398.0 |  | -0.0 | -61.6 | -53.1 |
| EURCHF | H4 | bb_brk |  | 526.0 | 0.8 | -7359.0 | -8471.9 | -398.0 |  | -0.0 | -73.0 | -62.1 |
| EURCHF | H4 | bb_rev | T | 186.0 | 0.8 | -2303.3 | -2730.7 | -458.6 |  | -0.0 | -11.8 | -33.3 |
| EURCHF | H4 | bb_rev |  | 622.0 | 0.9 | -2615.3 | -3711.8 | -196.0 |  | -0.0 | -16.6 | -33.7 |
| EURCHF | H4 | dmi_x | T | 189.0 | 0.6 | -4340.3 | -4515.9 | -177.6 |  | -0.0 | -57.9 | -18.0 |
| DE40 | H1 | cmf_zero |  | 2751.0 | 1.0 | -1394.0 | -6815.7 | -391.9 |  | -0.0 | -42.3 | 23.8 |
| DE40 | H1 | mfi_rev | T | 469.0 | 0.7 | -8376.6 | -8583.6 | -313.9 |  | -0.0 | -70.6 | -86.2 |
| DE40 | H1 | mfi_rev |  | 1438.0 | 0.9 | -10939.4 | -12150.7 | -329.1 |  | -0.0 | -92.8 | -112.0 |
| DE40 | H1 | willr_rev | T | 1372.0 | 0.9 | -9195.1 | -11514.5 | -510.6 |  | -0.0 | -66.8 | -108.1 |
| DE40 | H1 | willr_rev |  | 3969.0 | 0.9 | -18584.0 | -20823.6 | -510.6 |  | -0.0 | -148.0 | -202.2 |
| DE40 | H1 | aroon_x | T | 878.0 | 0.9 | -4296.3 | -7074.1 | -378.5 |  | -0.0 | -69.2 | -3.1 |
| DE40 | H1 | aroon_x |  | 1813.0 | 0.9 | -5768.4 | -8628.7 | -432.5 |  | -0.0 | -109.6 | 16.9 |
| DE40 | H1 | squeeze_brk | T | 629.0 | 0.9 | -2123.0 | -3043.8 | -251.8 |  | -0.0 | -22.1 | -16.6 |
| EURCHF | H4 | ema_x | T | 164.0 | 0.6 | -3819.9 | -3997.7 | -186.1 |  | -0.0 | -52.8 | -13.6 |
| EURCHF | H4 | ema_x |  | 298.0 | 0.7 | -5955.1 | -6493.1 | -193.8 |  | -0.0 | -78.5 | -26.0 |
| EURCHF | H4 | ema_slope | T | 284.0 | 0.7 | -4494.0 | -4782.6 | -403.2 |  | -0.0 | -50.5 | -30.6 |
| GBPUSD | H1 | cci_mom | T | 1955.0 | 0.8 | -17179.9 | -17179.9 | -347.9 |  | -0.0 | -120.9 | -204.3 |
| EURCHF | H4 | obv_slope | T | 474.0 | 0.8 | -6404.2 | -6702.0 | -431.0 |  | -0.0 | -67.0 | -49.7 |
| EURCHF | H4 | obv_slope |  | 2256.0 | 0.6 | -20673.6 | -21148.4 | -431.0 |  | -0.0 | -177.7 | -208.6 |
| EURCHF | H4 | cmf_zero | T | 411.0 | 0.8 | -5059.3 | -5767.5 | -403.2 |  | -0.0 | -45.1 | -49.0 |
| EURCHF | H4 | cmf_zero |  | 800.0 | 0.7 | -10957.7 | -12065.3 | -403.2 |  | -0.0 | -76.2 | -133.0 |
| XAGUSD | H1 | rsi_mom |  | 5879.0 | 0.4 | -122945.2 | -123332.3 | -391.3 |  | -0.0 | -1418.7 | -788.0 |
| XAGUSD | H1 | rsi_rev | T | 156.0 | 0.6 | -3422.6 | -4072.1 | -196.2 |  | -0.0 | -34.2 | -28.6 |
| XAGUSD | H1 | rsi_rev |  | 1228.0 | 0.6 | -29413.1 | -29427.4 | -349.9 |  | -0.0 | -292.6 | -247.1 |
| DE40 | H1 | don_rev | T | 826.0 | 0.9 | -6647.6 | -6991.9 | -368.0 |  | -0.0 | -43.5 | -84.2 |
| DE40 | H1 | don_rev |  | 2671.0 | 0.9 | -13366.8 | -14625.9 | -368.0 |  | -0.0 | -120.7 | -127.6 |
| DE40 | H1 | don_brk | T | 1519.0 | 1.0 | -4056.5 | -6482.7 | -477.8 |  | -0.0 | -89.5 | 27.4 |
| DE40 | H1 | don_brk |  | 2057.0 | 0.9 | -10094.8 | -11236.3 | -477.8 |  | -0.0 | -153.4 | -18.6 |
| DE40 | H1 | ha_flip | T | 2261.0 | 0.9 | -13776.5 | -16367.5 | -510.1 |  | -0.0 | -194.3 | -44.1 |
| DE40 | H1 | stoch_rev | T | 839.0 | 0.8 | -7813.9 | -8144.7 | -368.0 |  | -0.0 | -69.5 | -75.9 |
| DE40 | H1 | stoch_rev |  | 2525.0 | 0.9 | -19448.1 | -20571.3 | -401.5 |  | -0.0 | -222.3 | -127.3 |
| DE40 | H1 | macd_zero | T | 764.0 | 1.0 | -678.0 | -4255.0 | -395.8 |  | -0.0 | -18.1 | 8.5 |
| DE40 | H1 | macd_zero |  | 1583.0 | 0.9 | -8045.4 | -11092.2 | -407.2 |  | -0.0 | -130.6 | -4.3 |
| DE40 | H1 | macd_x | T | 1390.0 | 0.9 | -5582.4 | -8066.5 | -381.6 |  | -0.0 | -94.6 | 1.9 |
| DE40 | H1 | macd_x |  | 3511.0 | 0.9 | -10893.5 | -12798.6 | -424.5 |  | -0.0 | -163.2 | -23.0 |
| DE40 | H1 | rsi_mom | T | 1455.0 | 0.8 | -12835.3 | -14373.6 | -365.3 |  | -0.0 | -145.2 | -85.9 |
| DE40 | H1 | rsi_mom |  | 5076.0 | 0.9 | -20393.4 | -23456.2 | -429.1 |  | -0.0 | -320.2 | -24.7 |
| XAGUSD | H1 | bb_brk |  | 2231.0 | 0.7 | -40195.9 | -40392.6 | -308.2 |  | -0.0 | -503.8 | -207.6 |
| XAGUSD | H1 | bb_rev | T | 788.0 | 0.7 | -13425.4 | -13893.7 | -278.4 |  | -0.0 | -131.9 | -114.9 |
| XAGUSD | H1 | bb_rev |  | 2564.0 | 0.6 | -56561.5 | -56720.8 | -362.7 |  | -0.0 | -546.2 | -495.6 |
| XAGUSD | H1 | dmi_x | T | 724.0 | 0.6 | -14238.3 | -14383.4 | -288.5 |  | -0.0 | -176.3 | -76.2 |
| XAGUSD | H1 | dmi_x |  | 1795.0 | 0.6 | -35348.3 | -35595.9 | -382.1 |  | -0.0 | -462.0 | -158.9 |
| XAGUSD | H1 | cci_mom | T | 1818.0 | 0.7 | -34546.6 | -34769.0 | -323.7 |  | -0.0 | -422.6 | -191.4 |
| XAGUSD | H1 | cci_mom |  | 2990.0 | 0.6 | -56930.9 | -57121.4 | -365.8 |  | -0.0 | -669.3 | -349.5 |
| XAGUSD | H1 | cci_rev | T | 1209.0 | 0.7 | -22436.9 | -22987.0 | -312.6 |  | -0.0 | -262.5 | -139.4 |
| DE40 | H1 | squeeze_brk |  | 881.0 | 0.9 | -5568.6 | -7539.9 | -294.8 |  | -0.0 | -54.0 | -48.6 |
| DE40 | H1 | kelt_rev | T | 335.0 | 0.9 | -1688.2 | -2591.3 | -285.2 |  | -0.0 | -0.3 | -34.8 |
| DE40 | H1 | kelt_rev |  | 1601.0 | 1.0 | -3348.8 | -8071.1 | -356.8 |  | -0.0 | 37.4 | -116.5 |
| DE40 | H1 | kelt_brk | T | 1111.0 | 1.0 | 1821.4 | -2795.8 | -410.9 |  | 0.0 | -31.2 | 76.9 |
| DE40 | H1 | kelt_brk |  | 1372.0 | 1.0 | 1189.9 | -3595.1 | -410.9 |  | 0.0 | -38.5 | 72.9 |
| DE40 | H1 | bb_brk | T | 1416.0 | 1.0 | -3374.0 | -6793.1 | -410.9 |  | -0.0 | -75.8 | 24.4 |
| DE40 | H1 | bb_brk |  | 2032.0 | 0.9 | -9327.0 | -12463.0 | -410.9 |  | -0.0 | -150.0 | -6.8 |
| DE40 | H1 | bb_rev | T | 715.0 | 0.9 | -4224.0 | -4971.1 | -567.2 |  | -0.0 | -16.9 | -66.9 |
| XAGUSD | H1 | obv_slope |  | 8131.0 | 0.4 | -165667.5 | -165878.3 | -387.1 |  | -0.0 | -1829.3 | -1164.8 |
| XAGUSD | H1 | cmf_zero | T | 1726.0 | 0.6 | -33536.1 | -34282.4 | -327.1 |  | -0.0 | -381.1 | -222.3 |
| XAGUSD | H1 | cmf_zero |  | 3278.0 | 0.6 | -63951.9 | -64097.5 | -357.6 |  | -0.0 | -773.0 | -366.0 |
| XAGUSD | H1 | mfi_rev | T | 301.0 | 0.7 | -4534.1 | -5227.5 | -193.6 |  | -0.0 | -64.4 | -14.0 |
| XAGUSD | H1 | mfi_rev |  | 1052.0 | 0.6 | -26249.3 | -26635.0 | -257.4 |  | -0.0 | -259.6 | -222.4 |
| XAGUSD | H1 | willr_rev | T | 1422.0 | 0.7 | -25822.4 | -26754.9 | -285.5 |  | -0.0 | -319.4 | -138.7 |
| XAGUSD | H1 | willr_rev |  | 4345.0 | 0.5 | -93351.3 | -93388.6 | -343.3 |  | -0.0 | -1018.9 | -671.2 |
| XAGUSD | H1 | aroon_x | T | 999.0 | 0.7 | -13092.3 | -13855.4 | -272.5 |  | -0.0 | -169.6 | -60.7 |
| DE40 | H1 | ha_flip |  | 7421.0 | 0.9 | -28335.2 | -28973.2 | -411.8 |  | -0.0 | -296.3 | -220.0 |
| DE40 | H1 | ema_x | T | 529.0 | 0.9 | -3195.2 | -5111.3 | -391.7 |  | -0.0 | -37.2 | -20.0 |
| DE40 | H1 | ema_x |  | 912.0 | 0.9 | -4365.9 | -5854.4 | -391.7 |  | -0.0 | -63.5 | -11.6 |
| DE40 | H1 | ema_slope | T | 916.0 | 0.9 | -5853.1 | -7165.1 | -376.0 |  | -0.0 | -69.3 | -35.4 |
| DE40 | H1 | ema_slope |  | 2167.0 | 0.9 | -8642.2 | -10791.2 | -403.3 |  | -0.0 | -138.9 | -6.4 |
| DE40 | H1 | obv_slope | T | 1644.0 | 0.9 | -11500.8 | -12417.7 | -363.5 |  | -0.0 | -107.8 | -104.8 |
| DE40 | H1 | obv_slope |  | 6297.0 | 0.9 | -22977.6 | -25856.9 | -409.2 |  | -0.0 | -271.5 | -139.3 |
| DE40 | H1 | cmf_zero | T | 1362.0 | 1.0 | -1006.2 | -5720.0 | -352.4 |  | -0.0 | -49.1 | 40.4 |
| GBPUSD | H1 | cci_mom |  | 3256.0 | 0.9 | -22530.2 | -23474.5 | -366.0 |  | -0.0 | -166.9 | -257.3 |
| XAGUSD | H1 | don_rev | T | 739.0 | 0.7 | -12509.8 | -12878.1 | -278.5 |  | -0.0 | -163.0 | -56.9 |
| XAGUSD | H1 | don_rev |  | 2654.0 | 0.6 | -54635.7 | -54903.8 | -383.5 |  | -0.0 | -585.0 | -407.0 |
| XAGUSD | H1 | don_brk | T | 1590.0 | 0.7 | -27717.2 | -28662.7 | -251.0 |  | -0.0 | -307.6 | -192.9 |
| XAGUSD | H1 | don_brk |  | 2153.0 | 0.7 | -38674.3 | -39689.0 | -293.9 |  | -0.0 | -449.3 | -244.1 |
| XAGUSD | H1 | ha_flip | T | 2453.0 | 0.6 | -47166.1 | -48600.4 | -340.0 |  | -0.0 | -556.8 | -286.6 |
| XAGUSD | H1 | ha_flip |  | 8588.0 | 0.4 | -175834.3 | -175843.1 | -403.8 |  | -0.0 | -2001.2 | -1161.7 |
| XAGUSD | H1 | ema_x | T | 585.0 | 0.7 | -11062.0 | -11567.2 | -285.4 |  | -0.0 | -164.1 | -25.3 |
| XAGUSD | H1 | cci_rev |  | 3541.0 | 0.5 | -75171.8 | -75184.2 | -340.7 |  | -0.0 | -853.1 | -499.7 |
| XAGUSD | H1 | stoch_rev | T | 779.0 | 0.6 | -16779.4 | -17157.2 | -287.7 |  | -0.0 | -172.6 | -133.8 |
| XAGUSD | H1 | stoch_rev |  | 2594.0 | 0.6 | -60604.4 | -60793.7 | -363.5 |  | -0.0 | -645.1 | -456.2 |
| XAGUSD | H1 | macd_zero | T | 870.0 | 0.7 | -15866.8 | -16613.5 | -323.3 |  | -0.0 | -247.7 | -20.9 |
| XAGUSD | H1 | macd_zero |  | 1845.0 | 0.6 | -34082.0 | -34387.1 | -362.6 |  | -0.0 | -455.6 | -140.5 |
| XAGUSD | H1 | macd_x | T | 1612.0 | 0.6 | -31515.3 | -32107.3 | -346.0 |  | -0.0 | -385.4 | -174.8 |
| XAGUSD | H1 | macd_x |  | 4123.0 | 0.5 | -84115.5 | -84332.5 | -388.8 |  | -0.0 | -971.7 | -537.8 |
| XAGUSD | H1 | rsi_mom | T | 1570.0 | 0.6 | -32437.4 | -33504.9 | -327.9 |  | -0.0 | -362.5 | -222.6 |
| USDJPY | H4 | willr_rev |  | 1155.0 | 0.8 | -9588.1 | -10404.0 | -218.2 |  | -0.0 | -97.9 | -77.4 |
| USDJPY | H4 | aroon_x |  | 553.0 | 0.9 | -2567.3 | -2921.0 | -290.7 |  | -0.0 | -14.0 | -35.9 |
| USDJPY | H4 | kelt_rev |  | 519.0 | 0.9 | -1884.0 | -4333.8 | -207.7 |  | -0.0 | -27.0 | -5.5 |
| USDJPY | H4 | kelt_brk | T | 340.0 | 1.1 | 1225.5 | -2438.6 | -258.3 |  | 0.0 | 5.8 | 18.3 |
| USDJPY | H4 | bb_brk | T | 404.0 | 0.9 | -1939.8 | -4329.8 | -187.0 |  | -0.0 | -30.9 | -1.8 |
| GBPUSD | H1 | macd_x |  | 4337.0 | 0.8 | -28378.0 | -28950.1 | -406.6 |  | -0.0 | -273.2 | -244.0 |
| GBPUSD | H1 | rsi_mom | T | 1694.0 | 0.9 | -11315.9 | -11652.2 | -440.6 |  | -0.0 | -71.5 | -144.8 |
| GBPUSD | H1 | rsi_mom |  | 5853.0 | 0.8 | -42452.9 | -42860.7 | -459.0 |  | -0.0 | -355.8 | -432.2 |
| XAGUSD | H1 | aroon_x |  | 2113.0 | 0.7 | -31403.9 | -31951.1 | -337.9 |  | -0.0 | -428.7 | -118.4 |
| XAGUSD | H1 | squeeze_brk | T | 690.0 | 0.7 | -11189.1 | -11859.2 | -219.0 |  | -0.0 | -128.9 | -71.9 |
| XAGUSD | H1 | squeeze_brk |  | 913.0 | 0.6 | -18734.3 | -19617.3 | -293.9 |  | -0.0 | -196.2 | -145.0 |
| XAGUSD | H1 | kelt_rev | T | 310.0 | 0.7 | -5443.2 | -5957.3 | -290.1 |  | -0.0 | -61.0 | -37.2 |
| XAGUSD | H1 | kelt_rev |  | 1599.0 | 0.6 | -36087.3 | -36101.6 | -332.8 |  | -0.0 | -370.2 | -289.1 |
| XAGUSD | H1 | kelt_brk | T | 1102.0 | 0.7 | -16764.0 | -17480.6 | -222.1 |  | -0.0 | -217.7 | -77.2 |
| XAGUSD | H1 | kelt_brk |  | 1359.0 | 0.7 | -20980.2 | -22237.2 | -293.9 |  | -0.0 | -281.7 | -85.0 |
| XAGUSD | H1 | bb_brk | T | 1562.0 | 0.7 | -27798.3 | -28230.7 | -251.0 |  | -0.0 | -342.6 | -150.8 |
| GBPUSD | H1 | rsi_rev |  | 1398.0 | 0.9 | -7120.8 | -8446.1 | -308.5 |  | -0.0 | -69.2 | -60.4 |
| USDJPY | H4 | don_rev | T | 224.0 | 1.0 | 166.2 | -3049.2 | -217.7 |  | 0.0 | 9.2 | -8.0 |
| GBPUSD | H1 | willr_rev | T | 1743.0 | 0.8 | -16544.9 | -16856.9 | -440.6 |  | -0.0 | -105.2 | -211.0 |
| GBPUSD | H1 | willr_rev |  | 4984.0 | 0.8 | -47058.4 | -47651.4 | -440.6 |  | -0.0 | -362.5 | -519.6 |
| USDJPY | H4 | don_brk |  | 637.0 | 0.9 | -2124.1 | -2963.3 | -248.7 |  | -0.0 | -22.8 | -15.7 |
| USDJPY | H4 | ha_flip | T | 686.0 | 1.0 | -624.7 | -4197.0 | -223.4 |  | -0.0 | -27.8 | 21.7 |
| USDJPY | H4 | ha_flip |  | 2282.0 | 0.9 | -7209.6 | -8893.4 | -289.3 |  | -0.0 | -102.5 | -22.0 |
| USDJPY | H4 | ema_x |  | 278.0 | 0.8 | -2372.9 | -3235.2 | -237.2 |  | -0.0 | -3.7 | -44.8 |
| XAGUSD | H1 | ema_x |  | 996.0 | 0.6 | -20520.3 | -20886.9 | -296.4 |  | -0.0 | -266.2 | -94.8 |
| XAGUSD | H1 | ema_slope | T | 1031.0 | 0.6 | -25465.4 | -26168.5 | -342.5 |  | -0.0 | -303.8 | -150.8 |
| XAGUSD | H1 | ema_slope |  | 2452.0 | 0.5 | -53910.6 | -54084.2 | -391.8 |  | -0.0 | -609.3 | -361.5 |
| XAGUSD | H1 | obv_slope | T | 1937.0 | 0.6 | -38441.7 | -39750.1 | -377.8 |  | -0.0 | -436.8 | -254.8 |
| USDJPY | H4 | ema_slope |  | 629.0 | 1.0 | -899.5 | -3184.6 | -290.7 |  | -0.0 | 7.9 | -28.6 |
| USDJPY | H4 | obv_slope | T | 517.0 | 1.0 | 916.2 | -3147.3 | -308.4 |  | 0.0 | -6.8 | 27.6 |
| GBPUSD | H1 | kelt_brk |  | 1627.0 | 0.9 | -12734.6 | -13461.0 | -295.0 |  | -0.0 | -104.0 | -133.2 |
| GBPUSD | H1 | bb_brk | T | 1669.0 | 0.9 | -10607.2 | -11508.0 | -332.6 |  | -0.0 | -73.7 | -127.4 |
| XAUUSD | H1 | macd_x |  | 4045.0 | 0.9 | -22118.8 | -23670.8 | -409.5 |  | -0.0 | -218.5 | -187.7 |
| XAUUSD | H1 | rsi_mom | T | 1535.0 | 0.9 | -8487.6 | -9923.7 | -347.8 |  | -0.0 | -71.7 | -87.2 |
| XAUUSD | H1 | rsi_mom |  | 5591.0 | 0.8 | -37920.8 | -38539.9 | -426.7 |  | -0.0 | -358.9 | -341.4 |
| GBPUSD | H1 | bb_brk |  | 2534.0 | 0.9 | -18268.4 | -19551.3 | -370.0 |  | -0.0 | -117.9 | -230.8 |
| GBPUSD | H1 | bb_rev | T | 963.0 | 0.9 | -5035.9 | -5130.8 | -440.6 |  | -0.0 | -36.1 | -59.0 |
| GBPUSD | H1 | bb_rev |  | 2902.0 | 0.9 | -14324.4 | -15741.8 | -440.6 |  | -0.0 | -122.0 | -143.4 |
| GBPUSD | H1 | dmi_x | T | 778.0 | 0.9 | -5960.9 | -7386.7 | -243.3 |  | -0.0 | -18.3 | -100.9 |
| GBPUSD | H1 | dmi_x |  | 1873.0 | 0.8 | -13300.4 | -15839.6 | -361.5 |  | -0.0 | -122.8 | -121.0 |
| GBPUSD | H1 | don_brk | T | 1769.0 | 0.9 | -10735.0 | -11160.5 | -274.5 |  | -0.0 | -21.0 | -197.0 |
| GBPUSD | H1 | don_brk |  | 2464.0 | 0.9 | -15781.4 | -16640.9 | -330.0 |  | -0.0 | -54.2 | -260.0 |
| USTEC | D1 | squeeze_brk | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| USTEC | D1 | squeeze_brk |  | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| GBPUSD | H1 | cci_rev | T | 1351.0 | 0.8 | -12082.4 | -13083.9 | -459.0 |  | -0.0 | -95.5 | -130.4 |
| GBPUSD | H1 | cci_rev |  | 3827.0 | 0.8 | -29625.8 | -31656.4 | -459.0 |  | -0.0 | -273.7 | -269.3 |
| GBPUSD | H1 | stoch_rev | T | 982.0 | 0.9 | -7105.5 | -7966.5 | -298.1 |  | -0.0 | -30.3 | -109.5 |
| GBPUSD | H1 | stoch_rev |  | 2963.0 | 0.8 | -23164.3 | -24817.8 | -326.9 |  | -0.0 | -124.1 | -324.8 |
| GBPUSD | H1 | macd_zero | T | 852.0 | 1.0 | 1527.9 | -3556.3 | -466.3 |  | 0.0 | 16.1 | 11.3 |
| GBPUSD | H1 | macd_zero |  | 1755.0 | 1.0 | 708.9 | -3262.5 | -466.5 |  | 0.0 | 1.2 | 13.2 |
| GBPUSD | H1 | macd_x | T | 1691.0 | 0.9 | -10032.1 | -11439.7 | -368.4 |  | -0.0 | -76.8 | -111.3 |
| USTEC | D1 | mfi_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| XAUUSD | H1 | bb_rev |  | 2639.0 | 0.8 | -24726.3 | -25174.9 | -400.2 |  | -0.0 | -161.3 | -313.6 |
| XAUUSD | H1 | dmi_x | T | 718.0 | 0.9 | -5982.8 | -6731.4 | -350.0 |  | -0.0 | -57.7 | -52.5 |
| XAUUSD | H1 | dmi_x |  | 1779.0 | 0.8 | -14544.7 | -14982.7 | -342.6 |  | -0.0 | -182.9 | -74.4 |
| XAUUSD | H1 | cci_mom | T | 1782.0 | 0.9 | -6182.7 | -9272.0 | -393.8 |  | -0.0 | -89.2 | -17.3 |
| XAUUSD | H1 | don_rev |  | 2794.0 | 0.8 | -26565.2 | -27497.2 | -389.0 |  | -0.0 | -243.2 | -249.5 |
| XAUUSD | H1 | don_brk | T | 1696.0 | 0.9 | -7854.3 | -9428.7 | -294.8 |  | -0.0 | -50.5 | -100.5 |
| XAUUSD | H1 | don_brk |  | 2291.0 | 0.9 | -15789.3 | -17241.7 | -337.2 |  | -0.0 | -155.9 | -134.1 |
| XAUUSD | H1 | ha_flip | T | 2430.0 | 0.9 | -15028.2 | -18669.4 | -336.5 |  | -0.0 | -200.2 | -62.9 |
| XAUUSD | H1 | ha_flip |  | 8455.0 | 0.8 | -52300.5 | -53292.7 | -414.0 |  | -0.0 | -570.1 | -376.9 |
| XAUUSD | H1 | ema_x | T | 569.0 | 0.9 | -2567.2 | -5018.2 | -379.6 |  | -0.0 | -64.3 | 26.9 |
| XAUUSD | H1 | ema_x |  | 1022.0 | 0.9 | -5842.7 | -7204.6 | -379.6 |  | -0.0 | -107.5 | 12.6 |
| XAUUSD | H1 | macd_x | T | 1567.0 | 0.9 | -8963.8 | -10824.2 | -350.1 |  | -0.0 | -67.2 | -102.7 |
| XAGUSD | H4 | cmf_zero |  | 781.0 | 0.8 | -6905.8 | -7146.4 | -176.9 |  | -0.0 | -81.2 | -42.4 |
| GBPUSD | H1 | ema_slope |  | 2478.0 | 0.9 | -13568.5 | -14732.7 | -459.0 |  | -0.0 | -72.4 | -190.7 |
| GBPUSD | H1 | obv_slope | T | 2053.0 | 0.9 | -9500.0 | -10446.3 | -394.4 |  | -0.0 | -107.6 | -61.2 |
| GBPUSD | H1 | obv_slope |  | 8665.0 | 0.8 | -57682.5 | -58652.1 | -435.0 |  | -0.0 | -456.4 | -621.7 |
| GBPUSD | H1 | cmf_zero | T | 1769.0 | 0.8 | -17039.0 | -18102.6 | -440.6 |  | -0.0 | -207.9 | -90.8 |
| GBPUSD | H1 | cmf_zero |  | 3489.0 | 0.8 | -33748.4 | -34312.6 | -440.6 |  | -0.0 | -418.5 | -171.2 |
| GBPUSD | H1 | mfi_rev | T | 385.0 | 0.9 | -1904.3 | -3050.6 | -244.9 |  | -0.0 | -5.9 | -32.1 |
| GBPUSD | H1 | mfi_rev |  | 1238.0 | 0.9 | -10404.2 | -11548.4 | -293.6 |  | -0.0 | -71.8 | -125.5 |
| AUDUSD | H4 | cci_mom |  | 799.0 | 0.8 | -7109.1 | -7515.4 | -260.6 |  | -0.0 | -52.8 | -82.1 |
| GBPUSD | H1 | aroon_x | T | 1045.0 | 1.0 | 2101.9 | -2785.2 | -339.0 |  | 0.0 | 26.9 | 9.6 |
| GBPUSD | H1 | aroon_x |  | 2156.0 | 1.0 | -4318.7 | -7914.1 | -385.4 |  | -0.0 | 17.2 | -111.8 |
| GBPUSD | H1 | squeeze_brk | T | 722.0 | 0.9 | -5632.9 | -6929.2 | -219.6 |  | -0.0 | -29.0 | -80.5 |
| GBPUSD | H1 | squeeze_brk |  | 1003.0 | 0.8 | -9040.5 | -10381.4 | -284.5 |  | -0.0 | -61.0 | -110.8 |
| GBPUSD | H1 | kelt_rev | T | 420.0 | 0.8 | -6149.2 | -6227.1 | -275.4 |  | -0.0 | -49.9 | -64.6 |
| GBPUSD | H1 | kelt_rev |  | 1933.0 | 0.9 | -12201.7 | -12701.1 | -364.8 |  | -0.0 | -97.0 | -130.9 |
| GBPUSD | H1 | kelt_brk | T | 1306.0 | 0.9 | -11057.2 | -11337.2 | -291.6 |  | -0.0 | -116.8 | -81.9 |
| AUDUSD | H4 | macd_zero |  | 492.0 | 1.0 | -515.8 | -2789.5 | -288.5 |  | -0.0 | 28.1 | -45.8 |
| XAUUSD | H1 | rsi_rev |  | 1345.0 | 0.8 | -11399.4 | -12389.1 | -381.0 |  | -0.0 | -108.2 | -102.3 |
| XAGUSD | H4 | don_rev | T | 218.0 | 0.8 | -2832.1 | -2982.3 | -179.5 |  | -0.0 | -31.0 | -20.2 |
| XAGUSD | H4 | don_rev |  | 775.0 | 0.7 | -11195.6 | -11342.3 | -200.7 |  | -0.0 | -101.2 | -106.7 |
| XAGUSD | H4 | don_brk | T | 415.0 | 0.9 | -2408.3 | -3649.5 | -218.7 |  | -0.0 | -52.8 | 15.9 |
| XAUUSD | H1 | willr_rev |  | 4476.0 | 0.8 | -38387.5 | -39611.1 | -371.2 |  | -0.0 | -343.3 | -370.6 |
| XAUUSD | H1 | aroon_x | T | 1056.0 | 0.9 | -3189.3 | -7259.0 | -321.3 |  | -0.0 | -27.5 | -32.1 |
| XAUUSD | H1 | aroon_x |  | 2203.0 | 0.9 | -12189.8 | -15453.4 | -373.0 |  | -0.0 | -143.7 | -74.3 |
| XAUUSD | H1 | squeeze_brk | T | 747.0 | 0.9 | -4672.8 | -6506.6 | -287.1 |  | -0.0 | -8.1 | -87.2 |
| XAUUSD | H1 | squeeze_brk |  | 1004.0 | 0.9 | -8019.9 | -10123.8 | -322.9 |  | -0.0 | -49.0 | -105.8 |
| XAUUSD | H1 | kelt_rev | T | 354.0 | 0.9 | -1738.0 | -2560.1 | -231.2 |  | -0.0 | -5.6 | -29.2 |
| XAUUSD | H1 | kelt_rev |  | 1783.0 | 0.9 | -14349.0 | -15963.9 | -389.0 |  | -0.0 | -138.1 | -126.3 |
| XAGUSD | H4 | ema_slope |  | 700.0 | 0.7 | -8064.4 | -8589.0 | -253.7 |  | -0.0 | -92.6 | -52.3 |
| XAGUSD | H4 | obv_slope | T | 487.0 | 0.8 | -5457.6 | -5888.6 | -236.1 |  | -0.0 | -88.5 | -3.1 |
| XAGUSD | H4 | obv_slope |  | 2129.0 | 0.7 | -19112.4 | -19274.7 | -328.7 |  | -0.0 | -271.3 | -59.1 |
| XAGUSD | H4 | cmf_zero | T | 405.0 | 0.8 | -3225.7 | -3395.6 | -188.8 |  | -0.0 | -28.0 | -32.2 |
| AUDUSD | H4 | macd_x | T | 442.0 | 0.9 | -2404.7 | -3086.6 | -183.6 |  | -0.0 | -30.9 | -11.5 |
| AUDUSD | H4 | macd_x |  | 1181.0 | 0.8 | -9763.6 | -10543.9 | -299.7 |  | -0.0 | -80.6 | -102.6 |
| AUDUSD | H4 | rsi_mom |  | 1588.0 | 0.8 | -6832.7 | -7221.1 | -330.8 |  | -0.0 | -82.7 | -38.9 |
| GBPUSD | H1 | don_rev | T | 996.0 | 0.8 | -9050.4 | -9634.9 | -297.6 |  | -0.0 | -37.6 | -140.8 |
| GBPUSD | H1 | don_rev |  | 3193.0 | 0.9 | -24296.7 | -25057.7 | -358.8 |  | -0.0 | -190.6 | -264.0 |
| AUDUSD | H4 | ema_x |  | 294.0 | 0.9 | -1735.4 | -2521.4 | -221.6 |  | -0.0 | 6.0 | -43.7 |
| AUDUSD | H4 | ema_slope |  | 715.0 | 0.9 | -1439.8 | -3457.5 | -257.4 |  | -0.0 | 22.8 | -58.5 |
| GBPUSD | H1 | ha_flip | T | 2625.0 | 0.8 | -24060.4 | -24367.9 | -459.0 |  | -0.0 | -214.1 | -229.1 |
| GBPUSD | H1 | ha_flip |  | 9037.0 | 0.8 | -60288.5 | -61180.1 | -459.0 |  | -0.0 | -576.9 | -522.8 |
| GBPUSD | H1 | ema_x | T | 582.0 | 0.9 | -4106.2 | -6202.6 | -282.7 |  | -0.0 | -63.4 | -4.9 |
| GBPUSD | H1 | ema_x |  | 1040.0 | 0.9 | -7018.7 | -7474.3 | -370.5 |  | -0.0 | -73.3 | -53.0 |
| GBPUSD | H1 | ema_slope | T | 1012.0 | 0.9 | -6495.5 | -7200.8 | -459.0 |  | -0.0 | -30.8 | -96.2 |
| AUDUSD | H4 | kelt_brk | T | 319.0 | 0.8 | -2796.1 | -3787.7 | -260.2 |  | -0.0 | -2.6 | -55.0 |
| AUDUSD | H4 | kelt_brk |  | 387.0 | 0.8 | -4864.6 | -5139.6 | -260.2 |  | -0.0 | -26.0 | -68.8 |
| AUDUSD | H4 | bb_brk | T | 384.0 | 0.9 | -3359.5 | -3761.5 | -230.9 |  | -0.0 | -21.1 | -43.6 |
| USTEC | D1 | rsi_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| AUDUSD | H4 | bb_brk |  | 561.0 | 0.8 | -5459.7 | -5765.2 | -277.7 |  | -0.0 | -38.9 | -65.2 |
| AUDUSD | H4 | bb_rev |  | 668.0 | 1.0 | -570.3 | -4092.6 | -194.0 |  | -0.0 | -37.0 | 34.4 |
| AUDUSD | H4 | dmi_x |  | 429.0 | 0.8 | -3167.2 | -3896.3 | -232.9 |  | -0.0 | -18.5 | -42.8 |
| AUDUSD | H4 | cci_mom | T | 476.0 | 0.9 | -2473.7 | -3031.1 | -230.9 |  | -0.0 | -16.4 | -31.0 |
| EURUSD | D1 | willr_rev |  | 208.0 | 0.8 | -1469.6 | -2979.0 | -128.9 |  | -0.0 | 3.1 | -34.5 |
| AUDUSD | H1 | rsi_mom |  | 6098.0 | 0.7 | -61294.2 | -61756.7 | -431.1 |  | -0.0 | -644.1 | -458.4 |
| AUDUSD | H1 | rsi_rev | T | 144.0 | 0.7 | -2369.9 | -2909.5 | -197.4 |  | -0.0 | 1.0 | -50.6 |
| AUDUSD | H1 | rsi_rev |  | 1348.0 | 0.8 | -15038.6 | -18726.4 | -394.9 |  | -0.0 | -142.7 | -131.9 |
| AUDUSD | H4 | cci_rev |  | 971.0 | 1.0 | 943.0 | -3926.7 | -208.8 |  | 0.0 | -37.8 | 66.9 |
| AUDUSD | H4 | stoch_rev | T | 263.0 | 0.9 | -1187.2 | -2678.5 | -179.9 |  | -0.0 | -24.2 | 5.6 |
| AUDUSD | H4 | stoch_rev |  | 838.0 | 0.9 | -5510.3 | -6739.8 | -177.7 |  | -0.0 | -56.6 | -44.1 |
| EURCHF | H4 | trend_vote v=5 |  | 565.0 | 0.8 | -7717.9 | -8303.2 | -398.0 |  | -0.0 | -94.5 | -42.7 |
| EURCHF | H4 | trend_vote v=4 | T | 319.0 | 0.8 | -3302.2 | -4070.8 | -398.0 |  | -0.0 | -48.5 | -8.2 |
| EURCHF | H4 | trend_vote v=4 |  | 668.0 | 0.7 | -7969.3 | -8766.2 | -398.4 |  | -0.0 | -87.0 | -57.3 |
| EURGBP | D1 | trend_vote v=5 | T | 60.0 | 0.5 | -2037.2 | -2402.1 | -145.8 |  | -0.0 | -2.8 | -38.9 |
| EURGBP | H4 | trend_vote v=6 | T | 395.0 | 0.8 | -4640.1 | -6878.2 | -226.5 |  | -0.0 | -13.5 | -79.8 |
| EURGBP | H4 | trend_vote v=6 |  | 496.0 | 0.8 | -4633.3 | -7153.8 | -226.5 |  | -0.0 | -10.3 | -83.6 |
| EURGBP | H4 | trend_vote v=5 | T | 362.0 | 0.7 | -5853.3 | -7807.9 | -201.4 |  | -0.0 | -39.6 | -72.4 |
| EURGBP | H4 | trend_vote v=5 |  | 565.0 | 0.9 | -2727.7 | -6151.6 | -209.6 |  | -0.0 | -20.3 | -31.5 |
| EURGBP | H4 | trend_vote v=4 |  | 653.0 | 0.9 | -1850.1 | -4911.4 | -259.4 |  | -0.0 | -10.9 | -24.9 |
| AUDUSD | H1 | bb_brk | T | 1635.0 | 0.7 | -25290.5 | -25890.2 | -358.6 |  | -0.0 | -214.7 | -254.1 |
| AUDUSD | H1 | bb_brk |  | 2359.0 | 0.7 | -34800.0 | -35184.0 | -378.0 |  | -0.0 | -350.4 | -279.7 |
| AUDUSD | H1 | bb_rev | T | 832.0 | 0.8 | -8215.1 | -9559.5 | -360.1 |  | -0.0 | -18.1 | -148.2 |
| AUDUSD | H1 | bb_rev |  | 2759.0 | 0.8 | -25164.3 | -25962.3 | -395.8 |  | -0.0 | -229.6 | -232.4 |
| AUDUSD | H4 | obv_slope |  | 2328.0 | 0.9 | -8045.7 | -9779.0 | -261.1 |  | -0.0 | -120.6 | -16.9 |
| AUDUSD | H4 | cmf_zero | T | 438.0 | 0.9 | -2732.3 | -3287.2 | -189.0 |  | -0.0 | -43.7 | -2.2 |
| AUDUSD | H4 | cmf_zero |  | 861.0 | 0.8 | -8079.8 | -8389.9 | -253.1 |  | -0.0 | -72.1 | -78.2 |
| AUDUSD | H4 | willr_rev | T | 405.0 | 0.9 | -1537.3 | -3739.7 | -264.3 |  | -0.0 | -46.7 | 26.4 |
| AUDUSD | H4 | willr_rev |  | 1217.0 | 0.9 | -4879.0 | -6819.9 | -259.1 |  | -0.0 | -92.9 | 14.4 |
| AUDUSD | H4 | aroon_x |  | 552.0 | 0.8 | -5805.7 | -6695.3 | -257.4 |  | -0.0 | -31.3 | -81.9 |
| AUDUSD | H1 | stoch_rev |  | 3293.0 | 0.8 | -28087.5 | -29101.6 | -377.6 |  | -0.0 | -228.9 | -294.3 |
| AUDUSD | H1 | macd_zero | T | 953.0 | 0.8 | -11767.9 | -12445.5 | -406.7 |  | -0.0 | -112.2 | -102.6 |
| AUDUSD | H1 | macd_zero |  | 1962.0 | 0.8 | -23647.5 | -24294.6 | -389.3 |  | -0.0 | -248.4 | -177.0 |
| AUDUSD | H1 | macd_x | T | 1674.0 | 0.8 | -20592.2 | -20798.3 | -394.3 |  | -0.0 | -187.6 | -190.5 |
| AUDUSD | H1 | macd_x |  | 4272.0 | 0.8 | -42072.0 | -43069.8 | -425.4 |  | -0.0 | -434.3 | -324.6 |
| AUDUSD | H1 | rsi_mom | T | 1744.0 | 0.8 | -15687.0 | -16382.1 | -345.7 |  | -0.0 | -169.2 | -111.8 |
| AUDUSD | H1 | obv_slope | T | 2119.0 | 0.8 | -21443.2 | -22163.8 | -359.4 |  | -0.0 | -210.7 | -179.0 |
| AUDUSD | H1 | obv_slope |  | 8790.0 | 0.6 | -87875.7 | -88271.6 | -426.7 |  | -0.0 | -949.2 | -624.4 |
| AUDUSD | H1 | cmf_zero | T | 1773.0 | 0.8 | -24094.3 | -24703.0 | -361.2 |  | -0.0 | -238.6 | -198.7 |
| AUDUSD | H1 | cmf_zero |  | 3528.0 | 0.7 | -44109.4 | -44481.8 | -375.6 |  | -0.0 | -427.5 | -375.6 |
| AUDUSD | H4 | don_rev |  | 859.0 | 0.9 | -2684.5 | -4761.5 | -248.5 |  | -0.0 | -35.6 | -11.4 |
| AUDUSD | H4 | don_brk | T | 452.0 | 0.9 | -1636.6 | -2649.3 | -230.9 |  | -0.0 | -11.3 | -19.9 |
| AUDUSD | H4 | don_brk |  | 634.0 | 0.9 | -4580.1 | -4690.3 | -277.7 |  | -0.0 | -29.3 | -58.8 |
| AUDUSD | H4 | ha_flip | T | 653.0 | 1.0 | -1428.1 | -3382.9 | -188.9 |  | -0.0 | 2.7 | -33.1 |
| AUDUSD | H4 | ha_flip |  | 2250.0 | 0.8 | -12354.3 | -13690.9 | -252.3 |  | -0.0 | -112.8 | -116.3 |
| AUDUSD | H1 | squeeze_brk |  | 1027.0 | 0.7 | -17856.8 | -18838.9 | -323.9 |  | -0.0 | -198.3 | -120.1 |
| AUDUSD | H1 | kelt_rev | T | 350.0 | 0.8 | -4560.8 | -5184.6 | -263.1 |  | -0.0 | -40.6 | -43.4 |
| AUDUSD | H1 | kelt_rev |  | 1918.0 | 0.9 | -14050.4 | -17800.7 | -414.9 |  | -0.0 | -161.8 | -87.1 |
| AUDUSD | H1 | kelt_brk | T | 1331.0 | 0.8 | -17578.9 | -17681.5 | -348.9 |  | -0.0 | -169.0 | -151.4 |
| AUDUSD | H1 | kelt_brk |  | 1601.0 | 0.8 | -16998.2 | -17599.1 | -348.9 |  | -0.0 | -159.4 | -151.5 |
| NZDUSD | H1 | macd_x | T | 1617.0 | 0.8 | -19255.8 | -20100.7 | -374.1 |  | -0.0 | -206.5 | -138.7 |
| NZDUSD | H1 | macd_x |  | 4255.0 | 0.7 | -46412.4 | -46714.7 | -402.9 |  | -0.0 | -471.2 | -368.1 |
| NZDUSD | H1 | rsi_mom | T | 1683.0 | 0.8 | -20504.9 | -20971.3 | -365.5 |  | -0.0 | -146.3 | -241.3 |
| NZDUSD | H1 | rsi_mom |  | 6123.0 | 0.6 | -76430.6 | -76796.9 | -436.6 |  | -0.0 | -668.0 | -743.4 |
| AUDUSD | H1 | dmi_x | T | 804.0 | 0.8 | -8418.5 | -9096.8 | -292.2 |  | -0.0 | -54.2 | -106.5 |
| AUDUSD | H1 | dmi_x |  | 1952.0 | 0.8 | -21033.9 | -22676.0 | -355.8 |  | -0.0 | -173.0 | -218.4 |
| AUDUSD | H1 | cci_mom | T | 1939.0 | 0.8 | -27738.5 | -28345.0 | -378.3 |  | -0.0 | -295.4 | -202.5 |
| AUDUSD | H1 | cci_mom |  | 3170.0 | 0.8 | -37334.0 | -38561.3 | -396.2 |  | -0.0 | -417.8 | -246.8 |
| AUDUSD | H1 | cci_rev | T | 1353.0 | 0.8 | -17861.0 | -18119.6 | -302.9 |  | -0.0 | -165.0 | -162.4 |
| AUDUSD | H1 | cci_rev |  | 3907.0 | 0.8 | -40742.0 | -41389.4 | -383.6 |  | -0.0 | -358.0 | -393.9 |
| AUDUSD | H1 | stoch_rev | T | 1062.0 | 0.8 | -10050.7 | -11132.4 | -315.1 |  | -0.0 | -53.4 | -141.5 |
| AUDUSD | H1 | ha_flip |  | 8870.0 | 0.7 | -89777.9 | -90116.9 | -439.3 |  | -0.0 | -940.1 | -675.6 |
| AUDUSD | H1 | ema_x | T | 613.0 | 0.9 | -3873.5 | -7429.6 | -330.0 |  | -0.0 | -58.2 | -6.7 |
| AUDUSD | H1 | ema_x |  | 1056.0 | 0.9 | -6898.8 | -9074.3 | -395.4 |  | -0.0 | -66.0 | -59.8 |
| XAGUSD | H4 | squeeze_brk |  | 242.0 | 0.8 | -2119.0 | -3265.9 | -234.9 |  | -0.0 | -20.7 | -18.3 |
| XAGUSD | H4 | kelt_rev |  | 454.0 | 0.8 | -5664.2 | -6069.1 | -187.9 |  | -0.0 | -25.4 | -86.2 |
| XAGUSD | H4 | kelt_brk | T | 293.0 | 0.9 | -2219.6 | -2868.9 | -186.6 |  | -0.0 | -38.5 | 1.9 |
| XAGUSD | H4 | kelt_brk |  | 360.0 | 0.8 | -2903.0 | -3860.3 | -199.4 |  | -0.0 | -53.8 | 6.8 |
| AUDUSD | H1 | ema_slope | T | 1070.0 | 0.9 | -6860.7 | -7570.6 | -360.6 |  | -0.0 | -40.5 | -91.5 |
| AUDUSD | H1 | ema_slope |  | 2548.0 | 0.8 | -21020.4 | -21467.4 | -388.8 |  | -0.0 | -200.7 | -182.9 |
| NZDUSD | H1 | kelt_brk | T | 1277.0 | 0.8 | -16939.3 | -17633.0 | -328.3 |  | -0.0 | -184.6 | -118.3 |
| NZDUSD | H1 | kelt_brk |  | 1529.0 | 0.8 | -19022.9 | -20460.2 | -328.3 |  | -0.0 | -220.6 | -116.0 |
| NZDUSD | H1 | bb_brk | T | 1609.0 | 0.8 | -22433.8 | -23890.1 | -316.1 |  | -0.0 | -170.5 | -250.7 |
| NZDUSD | H1 | bb_brk |  | 2340.0 | 0.8 | -32972.0 | -33139.6 | -368.4 |  | -0.0 | -290.6 | -317.6 |
| AUDUSD | H1 | mfi_rev | T | 282.0 | 0.9 | -1867.2 | -2935.6 | -255.5 |  | -0.0 | -17.7 | -16.4 |
| AUDUSD | H1 | mfi_rev |  | 1042.0 | 0.9 | -7668.3 | -12023.8 | -297.1 |  | -0.0 | -71.1 | -69.5 |
| AUDUSD | H1 | willr_rev | T | 1676.0 | 0.8 | -20450.2 | -21772.5 | -372.7 |  | -0.0 | -167.6 | -213.0 |
| AUDUSD | H1 | willr_rev |  | 4796.0 | 0.8 | -48306.7 | -48999.6 | -411.6 |  | -0.0 | -472.2 | -406.3 |
| AUDUSD | H1 | aroon_x | T | 1046.0 | 0.8 | -9694.3 | -11173.6 | -289.6 |  | -0.0 | -108.8 | -63.7 |
| AUDUSD | H1 | aroon_x |  | 2163.0 | 0.8 | -20789.2 | -21781.5 | -356.7 |  | -0.0 | -207.0 | -170.0 |
| AUDUSD | H1 | squeeze_brk | T | 748.0 | 0.7 | -11901.2 | -12365.3 | -296.3 |  | -0.0 | -123.1 | -91.4 |
| NZDUSD | H1 | cci_rev |  | 3880.0 | 0.7 | -53125.1 | -53532.7 | -364.4 |  | -0.0 | -526.9 | -437.1 |
| NZDUSD | H1 | stoch_rev | T | 1020.0 | 0.7 | -15126.3 | -16063.0 | -329.9 |  | -0.0 | -122.5 | -159.4 |
| NZDUSD | H1 | stoch_rev |  | 3213.0 | 0.7 | -45637.1 | -46622.0 | -394.7 |  | -0.0 | -475.9 | -346.0 |
| XAGUSD | H4 | mfi_rev |  | 239.0 | 0.6 | -5126.7 | -5259.1 | -186.2 |  | -0.0 | -45.6 | -49.8 |
| XAGUSD | H4 | willr_rev | T | 350.0 | 0.8 | -3630.5 | -4497.6 | -175.0 |  | -0.0 | -30.1 | -38.1 |
| XAGUSD | H4 | willr_rev |  | 1097.0 | 0.7 | -12919.3 | -13583.9 | -175.3 |  | -0.0 | -115.5 | -124.8 |
| XAGUSD | H4 | aroon_x | T | 256.0 | 0.7 | -4185.2 | -5291.9 | -183.8 |  | -0.0 | -69.3 | -0.6 |
| XAUUSD | H1 | cci_mom |  | 2964.0 | 0.9 | -13778.4 | -16711.1 | -393.8 |  | -0.0 | -190.5 | -48.9 |
| XAUUSD | H1 | cci_rev | T | 1224.0 | 0.9 | -5773.1 | -7356.5 | -333.3 |  | -0.0 | -56.8 | -49.3 |
| XAUUSD | H1 | cci_rev |  | 3498.0 | 0.8 | -25109.9 | -25262.2 | -314.6 |  | -0.0 | -236.8 | -227.1 |
| XAUUSD | H1 | stoch_rev | T | 859.0 | 0.9 | -7273.8 | -8687.9 | -282.3 |  | -0.0 | -43.3 | -97.5 |
| XAUUSD | H1 | stoch_rev |  | 2771.0 | 0.8 | -30306.3 | -30839.9 | -369.8 |  | -0.0 | -294.9 | -262.8 |
| XAUUSD | H1 | macd_zero | T | 843.0 | 1.0 | -2082.2 | -4419.7 | -367.5 |  | -0.0 | -48.0 | 16.7 |
| XAUUSD | H1 | macd_zero |  | 1794.0 | 0.9 | -7472.8 | -9885.3 | -367.5 |  | -0.0 | -138.8 | 17.8 |
| XAGUSD | H4 | aroon_x |  | 553.0 | 0.7 | -7435.4 | -8644.4 | -191.8 |  | -0.0 | -111.4 | -15.7 |
| NZDUSD | H1 | macd_zero | T | 903.0 | 0.9 | -2870.3 | -5697.9 | -377.6 |  | -0.0 | -10.6 | -46.4 |
| NZDUSD | H1 | macd_zero |  | 1884.0 | 0.8 | -14228.9 | -15982.7 | -394.6 |  | -0.0 | -147.5 | -109.0 |
| NZDUSD | H1 | ema_slope | T | 1018.0 | 0.9 | -5471.7 | -7087.2 | -285.9 |  | -0.0 | -15.1 | -94.8 |
| AUDCAD | D1 | ha_flip |  | 342.0 | 0.8 | -1612.9 | -2657.1 | -112.8 |  | -0.0 | -30.4 | 5.9 |
| NZDUSD | H1 | ema_slope |  | 2513.0 | 0.8 | -20323.1 | -21837.3 | -405.9 |  | -0.0 | -193.2 | -177.9 |
| NZDUSD | H1 | obv_slope | T | 2100.0 | 0.8 | -27068.9 | -27762.6 | -383.3 |  | -0.0 | -205.3 | -303.0 |
| NZDUSD | H1 | obv_slope |  | 8725.0 | 0.6 | -109019.5 | -109243.5 | -446.2 |  | -0.0 | -1135.8 | -827.8 |
| NZDUSD | H1 | rsi_rev | T | 147.0 | 0.5 | -4445.0 | -4520.1 | -244.7 |  | -0.0 | -42.0 | -39.3 |
| AUDCAD | D1 | willr_rev |  | 183.0 | 0.8 | -1796.9 | -2985.3 | -96.8 |  | -0.0 | -11.2 | -31.3 |
| NZDUSD | H1 | rsi_rev |  | 1334.0 | 0.8 | -18912.8 | -20726.4 | -339.6 |  | -0.0 | -237.2 | -92.6 |
| AUDUSD | H1 | don_rev | T | 993.0 | 0.8 | -10467.8 | -11833.2 | -359.4 |  | -0.0 | -81.3 | -114.8 |
| AUDUSD | H1 | don_rev |  | 3289.0 | 0.8 | -33521.4 | -34873.0 | -406.9 |  | -0.0 | -334.5 | -273.2 |
| AUDUSD | H1 | don_brk | T | 1827.0 | 0.7 | -29340.0 | -29854.7 | -351.9 |  | -0.0 | -305.4 | -223.2 |
| AUDUSD | H1 | don_brk |  | 2496.0 | 0.7 | -37088.4 | -37404.1 | -367.9 |  | -0.0 | -395.4 | -270.1 |
| AUDUSD | H1 | ha_flip | T | 2715.0 | 0.8 | -33643.4 | -34020.3 | -412.7 |  | -0.0 | -388.8 | -206.8 |
| NZDUSD | H1 | aroon_x |  | 2205.0 | 0.8 | -18862.7 | -21363.2 | -370.7 |  | -0.0 | -158.3 | -191.8 |
| NZDUSD | H1 | squeeze_brk | T | 717.0 | 0.8 | -7358.0 | -8139.5 | -237.8 |  | -0.0 | -45.8 | -95.1 |
| NZDUSD | H1 | squeeze_brk |  | 997.0 | 0.8 | -12290.1 | -13519.1 | -283.4 |  | -0.0 | -119.1 | -104.7 |
| NZDUSD | H1 | kelt_rev | T | 342.0 | 0.8 | -4108.7 | -4937.5 | -322.9 |  | -0.0 | -16.5 | -64.6 |
| NZDUSD | H1 | kelt_rev |  | 1846.0 | 0.8 | -17336.6 | -18618.0 | -395.6 |  | -0.0 | -200.0 | -107.0 |
| USDCAD | H1 | macd_zero | T | 893.0 | 0.8 | -8475.4 | -9384.5 | -330.2 |  | -0.0 | -59.1 | -101.4 |
| USDCAD | H1 | macd_zero |  | 1908.0 | 0.8 | -21013.9 | -21248.4 | -395.9 |  | -0.0 | -154.1 | -241.9 |
| USDCAD | H1 | macd_x | T | 1648.0 | 0.8 | -18777.4 | -19422.8 | -368.9 |  | -0.0 | -164.0 | -182.8 |
| USDCAD | H1 | macd_x |  | 4309.0 | 0.7 | -52567.4 | -53064.5 | -407.8 |  | -0.0 | -484.5 | -479.4 |
| NZDUSD | H1 | bb_rev | T | 859.0 | 0.9 | -7042.8 | -8135.9 | -325.5 |  | -0.0 | -24.8 | -115.1 |
| NZDUSD | H1 | bb_rev |  | 2732.0 | 0.8 | -27118.9 | -27917.2 | -353.1 |  | -0.0 | -318.9 | -159.7 |
| NZDUSD | H1 | dmi_x | T | 771.0 | 0.8 | -11040.6 | -11807.4 | -338.2 |  | -0.0 | -84.5 | -122.6 |
| USDJPY | D1 | ha_flip |  | 406.0 | 0.8 | -2318.8 | -2609.2 | -162.3 |  | -0.0 | -9.8 | -36.0 |
| NZDUSD | H1 | dmi_x |  | 1929.0 | 0.7 | -25249.0 | -26446.5 | -370.4 |  | -0.0 | -230.0 | -233.7 |
| NZDUSD | H1 | cci_mom | T | 1912.0 | 0.8 | -22481.8 | -22683.3 | -338.5 |  | -0.0 | -170.1 | -252.2 |
| NZDUSD | H1 | cci_mom |  | 3187.0 | 0.8 | -37396.5 | -37618.2 | -397.5 |  | -0.0 | -345.2 | -340.4 |
| NZDUSD | H1 | cci_rev | T | 1341.0 | 0.7 | -20129.0 | -20252.1 | -322.0 |  | -0.0 | -158.5 | -218.0 |
| NZDUSD | H1 | don_brk |  | 2460.0 | 0.8 | -35116.8 | -35444.1 | -328.3 |  | -0.0 | -281.1 | -374.4 |
| NZDUSD | H1 | ha_flip | T | 2631.0 | 0.8 | -27027.1 | -27267.2 | -357.2 |  | -0.0 | -201.4 | -307.1 |
| NZDUSD | H1 | ha_flip |  | 8949.0 | 0.6 | -110419.8 | -110793.6 | -413.6 |  | -0.0 | -1007.0 | -1020.7 |
| NZDUSD | H1 | ema_x | T | 586.0 | 1.0 | -332.3 | -2897.3 | -325.9 |  | -0.0 | -6.3 | 1.1 |
| NZDUSD | H1 | ema_x |  | 1072.0 | 0.9 | -5714.9 | -7523.3 | -362.2 |  | -0.0 | -77.7 | -20.3 |
| EURCHF | H4 | ema_slope |  | 742.0 | 0.7 | -8744.5 | -9076.8 | -403.2 |  | -0.0 | -119.9 | -32.4 |
| USDCAD | H1 | kelt_rev |  | 1856.0 | 0.9 | -11917.9 | -12882.5 | -365.6 |  | -0.0 | -163.5 | -40.6 |
| USDCAD | H1 | kelt_brk | T | 1312.0 | 0.8 | -16006.5 | -16512.6 | -281.8 |  | -0.0 | -140.2 | -155.3 |
| USDCAD | H1 | kelt_brk |  | 1599.0 | 0.8 | -19232.7 | -19808.3 | -290.8 |  | -0.0 | -163.6 | -192.7 |
| USDCAD | H1 | bb_brk | T | 1659.0 | 0.8 | -19237.5 | -20064.6 | -373.3 |  | -0.0 | -151.5 | -208.2 |
| NZDUSD | H1 | cmf_zero | T | 1727.0 | 0.8 | -22093.8 | -22476.9 | -326.6 |  | -0.0 | -201.4 | -204.3 |
| NZDUSD | H1 | cmf_zero |  | 3437.0 | 0.7 | -42625.6 | -42795.0 | -372.4 |  | -0.0 | -407.3 | -370.4 |
| NZDUSD | H1 | mfi_rev | T | 292.0 | 0.8 | -2858.7 | -3221.6 | -201.5 |  | -0.0 | -23.4 | -29.8 |
| NZDUSD | H1 | mfi_rev |  | 1021.0 | 0.8 | -12294.8 | -12763.7 | -258.5 |  | -0.0 | -121.7 | -101.5 |
| NZDUSD | H1 | willr_rev | T | 1635.0 | 0.8 | -21883.1 | -22548.3 | -326.7 |  | -0.0 | -175.3 | -233.1 |
| NZDUSD | H1 | willr_rev |  | 4732.0 | 0.7 | -66219.9 | -66509.7 | -400.5 |  | -0.0 | -691.3 | -501.1 |
| NZDUSD | H1 | aroon_x | T | 1029.0 | 0.9 | -5297.9 | -7443.2 | -336.9 |  | -0.0 | -13.5 | -93.2 |
| USDCAD | H1 | cci_mom |  | 3264.0 | 0.7 | -46496.3 | -46601.8 | -391.8 |  | -0.0 | -388.5 | -475.0 |
| USDCAD | H1 | cci_rev | T | 1338.0 | 0.8 | -13536.6 | -14817.1 | -348.4 |  | -0.0 | -129.7 | -117.2 |
| USDCAD | H1 | cci_rev |  | 3860.0 | 0.8 | -36386.2 | -37765.4 | -401.4 |  | -0.0 | -380.4 | -274.6 |
| USDCAD | H1 | stoch_rev | T | 996.0 | 0.8 | -9110.7 | -9824.3 | -395.3 |  | -0.0 | -90.8 | -74.4 |
| USDCAD | H1 | stoch_rev |  | 3077.0 | 0.8 | -33654.0 | -33974.0 | -395.3 |  | -0.0 | -355.8 | -248.9 |
| USDCAD | H1 | ema_x |  | 1079.0 | 0.8 | -12057.8 | -12515.6 | -372.3 |  | -0.0 | -78.0 | -152.1 |
| GBPCHF | D1 | obv_slope |  | 432.0 | 0.9 | -719.1 | -2515.8 | -113.0 |  | -0.0 | 14.5 | -33.1 |
| USDCAD | H1 | ema_slope | T | 1062.0 | 0.8 | -8945.7 | -10197.9 | -343.3 |  | -0.0 | -89.9 | -72.1 |
| USDCAD | H1 | ema_slope |  | 2604.0 | 0.8 | -25958.0 | -26119.7 | -397.2 |  | -0.0 | -193.5 | -294.9 |
| USDCAD | H1 | obv_slope | T | 2097.0 | 0.8 | -22047.3 | -23016.0 | -337.1 |  | -0.0 | -223.3 | -175.5 |
| USDCAD | H1 | rsi_mom | T | 1722.0 | 0.8 | -20108.3 | -21273.7 | -354.1 |  | -0.0 | -180.8 | -189.1 |
| USDCAD | H1 | rsi_mom |  | 6203.0 | 0.6 | -79222.6 | -79656.3 | -428.4 |  | -0.0 | -805.6 | -626.7 |
| USDCAD | H1 | rsi_rev | T | 159.0 | 0.9 | -535.8 | -2569.6 | -249.7 |  | -0.0 | -26.5 | 22.5 |
| USDCAD | H1 | rsi_rev |  | 1294.0 | 0.9 | -8997.6 | -10386.0 | -322.5 |  | -0.0 | -149.7 | 2.8 |
| NZDUSD | H1 | don_rev | T | 1021.0 | 0.8 | -13064.7 | -13772.2 | -326.7 |  | -0.0 | -96.4 | -149.7 |
| XAGUSD | H4 | cci_rev |  | 916.0 | 0.8 | -8428.5 | -8504.1 | -168.3 |  | -0.0 | -96.1 | -55.5 |
| XAGUSD | H4 | stoch_rev | T | 223.0 | 0.7 | -3211.7 | -3526.7 | -148.8 |  | -0.0 | -27.6 | -32.4 |
| XAGUSD | H4 | stoch_rev |  | 734.0 | 0.7 | -10134.6 | -10383.8 | -187.2 |  | -0.0 | -101.8 | -83.9 |
| NZDUSD | H1 | don_rev |  | 3318.0 | 0.7 | -48316.3 | -48937.8 | -400.5 |  | -0.0 | -510.8 | -357.4 |
| NZDUSD | H1 | don_brk | T | 1793.0 | 0.8 | -24903.3 | -25239.6 | -328.3 |  | -0.0 | -168.7 | -304.4 |
| USDCAD | H1 | willr_rev |  | 4894.0 | 0.7 | -60589.2 | -61195.0 | -425.8 |  | -0.0 | -603.9 | -494.8 |
| USDCAD | H1 | aroon_x | T | 1019.0 | 0.8 | -8866.3 | -9168.0 | -331.6 |  | -0.0 | -60.5 | -107.8 |
| USDCAD | H1 | aroon_x |  | 2170.0 | 0.8 | -20623.7 | -21546.6 | -363.1 |  | -0.0 | -161.1 | -225.0 |
| USDCAD | H1 | squeeze_brk | T | 730.0 | 0.8 | -10491.2 | -11389.6 | -342.8 |  | -0.0 | -79.4 | -117.6 |
| USDCAD | H1 | squeeze_brk |  | 1013.0 | 0.8 | -14922.9 | -16051.0 | -342.8 |  | -0.0 | -126.1 | -150.6 |
| EURJPY | H1 | stoch_rev |  | 3078.0 | 0.8 | -39072.3 | -39380.9 | -625.7 |  | -0.0 | -336.3 | -386.6 |
| EURJPY | H1 | macd_zero | T | 826.0 | 0.8 | -7634.2 | -8192.0 | -361.3 |  | -0.0 | -36.2 | -113.0 |
| EURJPY | H1 | macd_zero |  | 1771.0 | 0.9 | -9666.1 | -11351.8 | -942.3 |  | -0.0 | -105.7 | -67.1 |
| EURJPY | H1 | macd_x | T | 1607.0 | 0.8 | -14457.5 | -15278.3 | -356.9 |  | -0.0 | -127.0 | -139.9 |
| USDCAD | H1 | bb_brk |  | 2470.0 | 0.8 | -31464.8 | -31923.2 | -373.3 |  | -0.0 | -268.1 | -314.8 |
| USDCAD | H1 | bb_rev | T | 929.0 | 0.8 | -8129.4 | -9096.6 | -337.0 |  | -0.0 | -87.7 | -58.0 |
| USDCAD | H1 | bb_rev |  | 2868.0 | 0.9 | -19810.0 | -21216.6 | -363.9 |  | -0.0 | -253.6 | -90.4 |
| USDCAD | H1 | dmi_x | T | 750.0 | 0.7 | -11737.8 | -12908.7 | -278.8 |  | -0.0 | -104.6 | -111.6 |
| USDCAD | H1 | dmi_x |  | 1854.0 | 0.7 | -27379.3 | -28659.9 | -364.4 |  | -0.0 | -270.2 | -227.0 |
| XAGUSD | H4 | bb_brk | T | 387.0 | 0.8 | -3982.9 | -4183.2 | -218.7 |  | -0.0 | -62.9 | -4.3 |
| XAGUSD | H4 | bb_brk |  | 561.0 | 0.8 | -5491.5 | -6144.6 | -218.7 |  | -0.0 | -72.0 | -24.4 |
| XAGUSD | H4 | bb_rev |  | 657.0 | 0.8 | -5839.6 | -5907.3 | -188.6 |  | -0.0 | -69.4 | -34.9 |
| XAGUSD | H4 | dmi_x |  | 451.0 | 0.8 | -3562.4 | -4288.9 | -187.5 |  | -0.0 | -40.4 | -23.7 |
| XAGUSD | H4 | cci_mom | T | 450.0 | 0.9 | -2934.4 | -3725.1 | -218.7 |  | -0.0 | -50.1 | 1.5 |
| XAGUSD | H4 | cci_mom |  | 717.0 | 0.9 | -5027.9 | -6017.0 | -224.8 |  | -0.0 | -84.5 | 0.9 |
| XAGUSD | H4 | cci_rev | T | 309.0 | 0.8 | -3284.3 | -4048.8 | -168.2 |  | -0.0 | -30.2 | -30.6 |
| XAGUSD | H4 | don_brk |  | 560.0 | 0.9 | -2559.4 | -3973.7 | -234.9 |  | -0.0 | -51.9 | 11.6 |
| XAGUSD | H4 | ha_flip | T | 605.0 | 0.8 | -6602.0 | -6716.9 | -175.1 |  | -0.0 | -98.8 | -14.1 |
| XAGUSD | H4 | ha_flip |  | 2265.0 | 0.7 | -21337.1 | -21664.6 | -215.5 |  | -0.0 | -274.7 | -101.2 |
| XAGUSD | H4 | ema_slope | T | 260.0 | 0.6 | -5588.5 | -6061.4 | -244.8 |  | -0.0 | -64.2 | -36.2 |
| XAUUSD | H4 | aroon_x |  | 543.0 | 0.9 | -1372.9 | -3009.8 | -263.2 |  | -0.0 | -9.5 | -16.8 |
| USDCAD | H1 | cci_mom | T | 1942.0 | 0.8 | -24968.7 | -25767.4 | -342.2 |  | -0.0 | -178.7 | -293.0 |
| USDCAD | H1 | don_rev |  | 3265.0 | 0.8 | -34728.2 | -35121.4 | -386.3 |  | -0.0 | -413.6 | -197.9 |
| USDCAD | H1 | don_brk | T | 1769.0 | 0.8 | -17864.5 | -19074.9 | -360.2 |  | -0.0 | -96.0 | -250.2 |
| USDCAD | H1 | don_brk |  | 2464.0 | 0.8 | -25816.5 | -27317.5 | -360.2 |  | -0.0 | -186.5 | -300.8 |
| USDCAD | H1 | ha_flip | T | 2511.0 | 0.8 | -26008.4 | -26823.5 | -438.0 |  | -0.0 | -235.2 | -242.9 |
| USDCAD | H1 | ha_flip |  | 9075.0 | 0.6 | -109793.0 | -109842.3 | -438.8 |  | -0.0 | -1011.8 | -1001.5 |
| USDCAD | H1 | ema_x | T | 615.0 | 0.8 | -6126.6 | -6900.8 | -354.3 |  | -0.0 | -15.5 | -107.9 |
| EURJPY | H1 | squeeze_brk |  | 931.0 | 0.9 | -7325.2 | -8380.2 | -977.5 |  | -0.0 | -83.9 | -46.0 |
| EURJPY | H1 | kelt_rev | T | 384.0 | 0.7 | -7603.8 | -8124.4 | -248.3 |  | -0.0 | -67.1 | -73.1 |
| EURJPY | H1 | kelt_rev |  | 1825.0 | 0.8 | -22637.6 | -23607.1 | -380.6 |  | -0.0 | -211.4 | -203.0 |
| EURCHF | D1 | willr_rev |  | 183.0 | 0.8 | -1484.3 | -2400.4 | -105.3 |  | -0.0 | -21.6 | -3.9 |
| EURJPY | H1 | kelt_brk | T | 1258.0 | 0.9 | -9380.2 | -10174.9 | -399.2 |  | -0.0 | -88.2 | -83.3 |
| USDCAD | H1 | obv_slope |  | 8542.0 | 0.6 | -97702.7 | -98408.9 | -459.0 |  | -0.0 | -952.4 | -825.2 |
| USDCAD | H1 | cmf_zero | T | 1739.0 | 0.9 | -14258.8 | -15628.9 | -365.0 |  | -0.0 | -123.3 | -140.4 |
| USDCAD | H1 | cmf_zero |  | 3431.0 | 0.8 | -37150.6 | -38022.9 | -424.4 |  | -0.0 | -383.6 | -286.4 |
| USDCAD | H1 | mfi_rev | T | 335.0 | 0.8 | -3710.9 | -4858.4 | -245.4 |  | -0.0 | -58.3 | -3.3 |
| USDCAD | H1 | mfi_rev |  | 1167.0 | 0.8 | -12250.2 | -13655.7 | -286.0 |  | -0.0 | -149.3 | -65.5 |
| USDCAD | H1 | willr_rev | T | 1700.0 | 0.8 | -18536.9 | -19704.8 | -339.4 |  | -0.0 | -172.9 | -166.4 |
| EURJPY | H1 | dmi_x |  | 1854.0 | 0.8 | -16684.1 | -16928.3 | -346.6 |  | -0.0 | -174.5 | -125.8 |
| EURJPY | H1 | cci_mom | T | 1822.0 | 0.9 | -9252.3 | -10291.8 | -414.9 |  | -0.0 | -53.8 | -124.4 |
| EURCHF | D1 | rsi_mom |  | 292.0 | 0.7 | -2264.6 | -2849.6 | -184.6 |  | -0.0 | -28.3 | -11.8 |
| EURJPY | H1 | cci_mom |  | 3031.0 | 0.9 | -17952.4 | -20261.9 | -414.9 |  | -0.0 | -203.0 | -116.1 |
| EURJPY | H1 | cci_rev | T | 1352.0 | 0.8 | -17023.5 | -18156.8 | -341.8 |  | -0.0 | -143.0 | -172.9 |
| EURJPY | H1 | cci_rev |  | 3753.0 | 0.7 | -49670.8 | -50364.2 | -626.0 |  | -0.0 | -415.6 | -506.6 |
| EURJPY | H1 | stoch_rev | T | 1019.0 | 0.8 | -10554.7 | -12365.8 | -294.7 |  | -0.0 | -103.8 | -87.9 |
| EURJPY | H1 | ha_flip |  | 8999.0 | 0.7 | -84536.0 | -85929.2 | -577.9 |  | -0.0 | -708.4 | -860.9 |
| EURJPY | H1 | ema_x | T | 561.0 | 1.0 | -1185.3 | -2695.1 | -310.9 |  | -0.0 | -34.6 | 19.3 |
| EURJPY | H1 | ema_x |  | 1008.0 | 0.9 | -2921.3 | -6343.5 | -378.9 |  | -0.0 | -66.7 | 23.9 |
| EURJPY | H1 | ema_slope | T | 1000.0 | 0.9 | -5244.1 | -6534.8 | -331.0 |  | -0.0 | -60.5 | -32.4 |
| EURJPY | H1 | macd_x |  | 4251.0 | 0.8 | -29947.5 | -32046.0 | -602.0 |  | -0.0 | -260.1 | -293.4 |
| EURJPY | H1 | rsi_mom | T | 1658.0 | 0.8 | -16904.4 | -17958.2 | -365.9 |  | -0.0 | -154.9 | -155.3 |
| EURJPY | H1 | rsi_mom |  | 6009.0 | 0.7 | -59003.2 | -59571.4 | -610.0 |  | -0.0 | -611.8 | -451.8 |
| EURJPY | H1 | rsi_rev | T | 189.0 | 0.6 | -5006.2 | -5556.6 | -235.1 |  | -0.0 | -46.5 | -45.2 |
| EURJPY | H1 | rsi_rev |  | 1384.0 | 0.8 | -15382.6 | -16254.4 | -382.4 |  | -0.0 | -155.1 | -123.3 |
| USDCAD | D1 | obv_slope |  | 406.0 | 0.7 | -2443.2 | -2877.3 | -154.6 |  | -0.0 | -18.0 | -28.4 |
| USDCAD | H1 | don_rev | T | 1037.0 | 0.8 | -9440.7 | -10197.7 | -347.1 |  | -0.0 | -77.3 | -98.4 |
| EURJPY | H1 | mfi_rev |  | 964.0 | 0.7 | -17225.6 | -18131.6 | -437.0 |  | -0.0 | -149.0 | -169.5 |
| EURJPY | H1 | willr_rev | T | 1683.0 | 0.8 | -21026.8 | -22499.3 | -333.7 |  | -0.0 | -196.2 | -188.7 |
| EURJPY | H1 | willr_rev |  | 4748.0 | 0.7 | -66392.6 | -66400.9 | -556.1 |  | -0.0 | -546.5 | -688.6 |
| EURJPY | H1 | aroon_x | T | 984.0 | 0.9 | -3302.3 | -5551.9 | -291.0 |  | -0.0 | -21.7 | -41.2 |
| NZDUSD | D1 | don_rev |  | 149.0 | 0.8 | -2014.6 | -2866.5 | -192.2 |  | -0.0 | -18.0 | -19.5 |
| EURJPY | H1 | aroon_x |  | 2124.0 | 0.9 | -11053.2 | -13245.4 | -942.3 |  | -0.0 | -119.1 | -78.9 |
| EURJPY | H1 | squeeze_brk | T | 680.0 | 0.9 | -3305.6 | -5701.2 | -259.3 |  | -0.0 | -26.9 | -34.7 |
| GBPJPY | H1 | cci_rev |  | 3748.0 | 0.8 | -32696.9 | -33936.7 | -390.7 |  | -0.0 | -181.8 | -450.1 |
| GBPJPY | H1 | stoch_rev | T | 951.0 | 0.9 | -7321.9 | -9032.8 | -335.1 |  | -0.0 | -10.8 | -138.8 |
| GBPJPY | H1 | stoch_rev |  | 3003.0 | 0.8 | -36178.3 | -37385.2 | -416.6 |  | -0.0 | -251.9 | -433.6 |
| GBPJPY | H1 | macd_zero | T | 869.0 | 1.0 | -2143.8 | -3943.7 | -368.6 |  | -0.0 | -26.7 | -10.8 |
| EURJPY | H1 | kelt_brk |  | 1521.0 | 0.9 | -8742.7 | -9795.4 | -399.2 |  | -0.0 | -89.8 | -68.1 |
| EURJPY | H1 | bb_brk | T | 1593.0 | 0.9 | -9028.1 | -10757.4 | -283.8 |  | -0.0 | -53.5 | -120.1 |
| USDCAD | D1 | ha_flip |  | 374.0 | 0.8 | -2049.4 | -2822.5 | -154.7 |  | -0.0 | -31.2 | -3.7 |
| EURGBP | D1 | rsi_mom |  | 279.0 | 0.8 | -1719.5 | -2499.5 | -145.8 |  | -0.0 | 2.1 | -38.4 |
| EURJPY | H1 | bb_brk |  | 2303.0 | 0.9 | -11582.1 | -13841.9 | -314.3 |  | -0.0 | -101.7 | -112.0 |
| EURJPY | H1 | bb_rev | T | 858.0 | 0.8 | -11538.4 | -12330.4 | -333.7 |  | -0.0 | -98.8 | -114.8 |
| EURJPY | H1 | bb_rev |  | 2738.0 | 0.8 | -36480.7 | -36584.0 | -601.6 |  | -0.0 | -318.1 | -355.7 |
| EURJPY | H1 | dmi_x | T | 749.0 | 0.9 | -5229.3 | -6947.9 | -296.4 |  | -0.0 | -66.9 | -24.0 |
| GBPJPY | H1 | rsi_rev |  | 1377.0 | 0.9 | -8549.8 | -10189.8 | -337.2 |  | -0.0 | -77.5 | -79.7 |
| EURJPY | H1 | don_rev | T | 1005.0 | 0.8 | -12167.9 | -12879.4 | -356.0 |  | -0.0 | -99.7 | -126.8 |
| EURGBP | D1 | don_brk |  | 102.0 | 0.7 | -2094.9 | -2519.6 | -102.5 |  | -0.0 | -14.2 | -25.9 |
| EURGBP | D1 | ha_flip |  | 402.0 | 0.6 | -4193.5 | -5173.3 | -145.8 |  | -0.0 | -18.0 | -64.8 |
| EURGBP | D1 | ema_slope |  | 138.0 | 0.6 | -2194.9 | -2682.4 | -145.8 |  | -0.0 | -14.8 | -27.2 |
| EURGBP | D1 | obv_slope |  | 494.0 | 0.7 | -3621.4 | -4644.1 | -212.4 |  | -0.0 | -8.6 | -64.6 |
| EURJPY | H1 | don_rev |  | 3221.0 | 0.8 | -44191.0 | -44966.0 | -437.0 |  | -0.0 | -426.4 | -378.8 |
| EURJPY | H1 | don_brk | T | 1754.0 | 0.9 | -13126.2 | -14211.8 | -293.7 |  | -0.0 | -118.4 | -123.0 |
| EURJPY | H1 | don_brk |  | 2397.0 | 0.9 | -17103.7 | -18538.8 | -977.5 |  | -0.0 | -189.2 | -115.9 |
| EURJPY | H1 | ha_flip | T | 2612.0 | 0.8 | -29447.6 | -30123.2 | -377.4 |  | -0.0 | -243.3 | -304.3 |
| GBPJPY | H1 | aroon_x |  | 2199.0 | 0.9 | -10161.0 | -12099.8 | -386.6 |  | -0.0 | -143.4 | -29.4 |
| GBPJPY | H1 | squeeze_brk | T | 718.0 | 0.9 | -4580.0 | -7753.8 | -237.4 |  | -0.0 | -53.8 | -27.0 |
| GBPJPY | H1 | squeeze_brk |  | 981.0 | 0.8 | -8647.2 | -10057.0 | -260.3 |  | -0.0 | -93.5 | -61.3 |
| EURJPY | H1 | ema_slope |  | 2409.0 | 0.9 | -10225.0 | -12222.5 | -394.3 |  | -0.0 | -114.8 | -67.1 |
| USDCHF | D1 | cci_mom | T | 74.0 | 0.5 | -2184.4 | -2930.8 | -150.4 |  | -0.0 | -26.3 | -12.7 |
| USDCHF | D1 | cci_mom |  | 120.0 | 0.7 | -1795.0 | -2805.6 | -150.4 |  | -0.0 | -17.1 | -16.0 |
| EURJPY | H1 | obv_slope | T | 2095.0 | 0.8 | -24139.2 | -24975.7 | -397.0 |  | -0.0 | -194.5 | -255.7 |
| USDCHF | D1 | macd_zero |  | 114.0 | 0.6 | -2425.7 | -2731.2 | -161.7 |  | -0.0 | -27.2 | -16.6 |
| EURJPY | H1 | obv_slope |  | 9052.0 | 0.7 | -85197.7 | -85572.2 | -529.6 |  | -0.0 | -816.5 | -737.3 |
| EURJPY | H1 | cmf_zero | T | 1690.0 | 0.8 | -14910.4 | -15708.8 | -436.4 |  | -0.0 | -148.2 | -122.3 |
| EURJPY | H1 | cmf_zero |  | 3174.0 | 0.9 | -15381.5 | -15581.2 | -610.0 |  | -0.0 | -144.6 | -136.7 |
| EURJPY | H1 | mfi_rev | T | 280.0 | 0.8 | -4066.0 | -4906.8 | -276.6 |  | -0.0 | -23.6 | -54.7 |
| GBPJPY | H1 | bb_rev |  | 2772.0 | 0.8 | -24392.2 | -24417.5 | -356.3 |  | -0.0 | -159.4 | -305.6 |
| EURGBP | D1 | macd_x |  | 204.0 | 0.8 | -1193.3 | -2539.4 | -120.2 |  | -0.0 | 7.6 | -34.3 |
| GBPJPY | H1 | dmi_x | T | 779.0 | 0.9 | -4139.6 | -4919.7 | -355.7 |  | -0.0 | -21.6 | -58.8 |
| GBPJPY | H1 | dmi_x |  | 1889.0 | 0.8 | -20193.4 | -20375.1 | -448.0 |  | -0.0 | -198.5 | -168.4 |
| GBPJPY | H1 | cci_mom | T | 1888.0 | 0.9 | -11541.5 | -12290.7 | -375.9 |  | -0.0 | -115.2 | -94.0 |
| GBPJPY | H1 | cci_mom |  | 3106.0 | 0.8 | -24856.2 | -26136.3 | -399.4 |  | -0.0 | -281.1 | -160.6 |
| GBPJPY | H1 | cci_rev | T | 1279.0 | 0.9 | -4399.9 | -9825.4 | -378.4 |  | -0.0 | -4.0 | -86.6 |
| GBPJPY | H1 | don_brk |  | 2440.0 | 0.9 | -12934.6 | -14485.8 | -355.7 |  | -0.0 | -147.2 | -82.4 |
| GBPJPY | H1 | ha_flip | T | 2590.0 | 0.9 | -14795.3 | -17352.4 | -365.3 |  | -0.0 | -120.1 | -155.6 |
| GBPJPY | H1 | ha_flip |  | 9057.0 | 0.7 | -81800.2 | -82929.1 | -472.3 |  | -0.0 | -769.2 | -726.7 |
| GBPJPY | H1 | ema_x | T | 557.0 | 1.0 | -603.8 | -3682.4 | -355.6 |  | -0.0 | -45.0 | 44.6 |
| NZDJPY | D1 | mfi_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| USDCHF | D1 | ema_slope |  | 157.0 | 0.6 | -2389.1 | -2771.3 | -140.0 |  | -0.0 | -21.5 | -22.8 |
| USDCHF | D1 | cmf_zero | T | 69.0 | 0.6 | -1824.2 | -2497.3 | -118.5 |  | -0.0 | -27.1 | -4.1 |
| GBPJPY | H1 | macd_zero |  | 1830.0 | 0.9 | -7698.7 | -9626.9 | -386.1 |  | -0.0 | -111.6 | -18.6 |
| GBPJPY | H1 | macd_x | T | 1608.0 | 0.9 | -4726.7 | -5991.5 | -325.3 |  | -0.0 | -38.8 | -49.2 |
| GBPJPY | H1 | macd_x |  | 4199.0 | 0.8 | -27810.9 | -28559.1 | -388.3 |  | -0.0 | -264.6 | -243.2 |
| GBPJPY | H1 | rsi_mom | T | 1695.0 | 0.9 | -9879.7 | -12559.8 | -378.6 |  | -0.0 | -55.9 | -134.8 |
| GBPJPY | H1 | rsi_mom |  | 6085.0 | 0.7 | -53050.2 | -53232.6 | -402.9 |  | -0.0 | -510.2 | -456.8 |
| GBPJPY | H1 | rsi_rev | T | 194.0 | 0.9 | -1555.7 | -2584.7 | -273.0 |  | -0.0 | 1.8 | -34.7 |
| GBPJPY | H1 | cmf_zero |  | 3231.0 | 0.9 | -20483.8 | -21112.2 | -413.0 |  | -0.0 | -238.4 | -123.7 |
| GBPJPY | H1 | mfi_rev | T | 273.0 | 0.9 | -2171.8 | -3129.2 | -221.8 |  | -0.0 | 5.1 | -51.7 |
| GBPJPY | H1 | mfi_rev |  | 1066.0 | 0.8 | -14894.4 | -15428.1 | -319.4 |  | -0.0 | -106.4 | -175.1 |
| GBPJPY | H1 | willr_rev | T | 1626.0 | 0.8 | -15323.1 | -17507.8 | -323.8 |  | -0.0 | -97.9 | -194.9 |
| USDCHF | D1 | don_brk | T | 78.0 | 0.6 | -1945.0 | -2425.1 | -150.4 |  | -0.0 | -25.0 | -9.2 |
| USDCHF | D1 | ha_flip | T | 90.0 | 0.7 | -1288.6 | -2430.3 | -125.0 |  | -0.0 | -24.4 | 3.6 |
| GBPJPY | H1 | willr_rev |  | 4708.0 | 0.7 | -54480.8 | -54550.0 | -376.3 |  | -0.0 | -402.5 | -623.5 |
| NZDJPY | D1 | mfi_rev |  | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| GBPJPY | H1 | aroon_x | T | 1018.0 | 1.0 | 1614.2 | -2943.1 | -355.7 |  | 0.0 | -0.8 | 34.6 |
| AUDJPY | H1 | cci_mom |  | 3068.0 | 0.8 | -31900.5 | -32515.9 | -421.1 |  | -0.0 | -316.4 | -262.5 |
| AUDJPY | H1 | cci_rev | T | 1297.0 | 0.8 | -14646.6 | -15174.4 | -450.9 |  | -0.0 | -96.2 | -182.8 |
| AUDJPY | H1 | cci_rev |  | 3834.0 | 0.7 | -50385.0 | -50559.9 | -450.9 |  | -0.0 | -391.0 | -552.8 |
| AUDJPY | H1 | stoch_rev | T | 985.0 | 0.8 | -13395.2 | -14226.6 | -374.6 |  | -0.0 | -64.1 | -197.6 |
| GBPJPY | H1 | kelt_rev |  | 1870.0 | 0.9 | -15436.8 | -16636.4 | -377.9 |  | -0.0 | -140.9 | -142.6 |
| GBPJPY | H1 | kelt_brk | T | 1252.0 | 1.0 | -1948.3 | -5697.5 | -278.9 |  | -0.0 | -21.5 | -13.3 |
| GBPJPY | H1 | kelt_brk |  | 1519.0 | 0.9 | -5091.3 | -8343.7 | -358.0 |  | -0.0 | -49.5 | -43.1 |
| GBPJPY | H1 | bb_brk | T | 1618.0 | 0.9 | -5330.5 | -8034.5 | -355.7 |  | -0.0 | -56.3 | -39.5 |
| NZDJPY | D1 | kelt_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| GBPJPY | H1 | bb_brk |  | 2358.0 | 0.9 | -11219.9 | -13126.9 | -406.8 |  | -0.0 | -151.5 | -41.2 |
| GBPJPY | H1 | bb_rev | T | 883.0 | 0.9 | -4441.7 | -7707.0 | -335.1 |  | -0.0 | 6.1 | -100.3 |
| AUDJPY | H1 | rsi_mom |  | 6124.0 | 0.7 | -64975.0 | -65260.0 | -411.3 |  | -0.0 | -651.2 | -526.1 |
| NZDJPY | D1 | bb_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| AUDJPY | H1 | rsi_rev | T | 155.0 | 0.7 | -3465.8 | -3535.7 | -451.3 |  | -0.0 | -19.3 | -47.7 |
| AUDJPY | H1 | rsi_rev |  | 1339.0 | 0.8 | -19581.1 | -20258.7 | -451.3 |  | -0.0 | -146.9 | -221.2 |
| GBPJPY | H1 | don_rev | T | 954.0 | 0.9 | -7836.8 | -10187.7 | -350.0 |  | -0.0 | -9.7 | -150.9 |
| GBPJPY | H1 | don_rev |  | 3177.0 | 0.8 | -36092.7 | -36570.6 | -386.8 |  | -0.0 | -228.5 | -461.5 |
| GBPJPY | H1 | don_brk | T | 1795.0 | 0.9 | -6126.3 | -9458.3 | -355.7 |  | -0.0 | -61.7 | -49.3 |
| AUDJPY | H1 | willr_rev |  | 4576.0 | 0.7 | -57207.3 | -57530.8 | -437.7 |  | -0.0 | -493.9 | -564.1 |
| USDCHF | D1 | cmf_zero |  | 130.0 | 0.6 | -3006.6 | -3588.9 | -118.5 |  | -0.0 | -34.3 | -19.8 |
| AUDJPY | H1 | aroon_x | T | 1032.0 | 0.8 | -13375.9 | -13486.8 | -314.5 |  | -0.0 | -104.9 | -145.3 |
| AUDJPY | H1 | aroon_x |  | 2183.0 | 0.8 | -23356.0 | -23471.3 | -497.6 |  | -0.0 | -233.5 | -189.9 |
| AUDJPY | H1 | squeeze_brk | T | 752.0 | 0.9 | -6111.4 | -6281.4 | -308.1 |  | -0.0 | -54.5 | -58.0 |
| XAUUSD | H4 | ha_flip |  | 2238.0 | 0.9 | -3509.5 | -7429.8 | -220.1 |  | -0.0 | -114.9 | 70.6 |
| XAUUSD | H4 | ema_x | T | 152.0 | 0.7 | -2653.6 | -2871.1 | -184.6 |  | -0.0 | -34.4 | -12.3 |
| GBPJPY | H1 | ema_x |  | 978.0 | 0.9 | -4546.7 | -7393.7 | -379.1 |  | -0.0 | -101.8 | 34.7 |
| GBPJPY | H1 | ema_slope | T | 1037.0 | 1.0 | -1490.3 | -3657.1 | -355.7 |  | -0.0 | -4.3 | -25.6 |
| GBPJPY | H1 | ema_slope |  | 2553.0 | 0.8 | -16192.3 | -16994.0 | -370.6 |  | -0.0 | -178.0 | -111.2 |
| GBPJPY | H1 | obv_slope | T | 2056.0 | 0.9 | -11958.2 | -16306.7 | -407.2 |  | -0.0 | -74.2 | -154.8 |
| NZDJPY | D1 | macd_zero | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| NZDJPY | D1 | macd_zero |  | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| GBPJPY | H1 | obv_slope |  | 8754.0 | 0.7 | -73719.0 | -74061.8 | -419.2 |  | -0.0 | -736.8 | -599.5 |
| GBPJPY | H1 | cmf_zero | T | 1670.0 | 0.9 | -4515.9 | -10011.3 | -374.2 |  | -0.0 | -43.1 | -39.4 |
| AUDJPY | H1 | bb_brk |  | 2239.0 | 0.8 | -22389.2 | -23267.4 | -324.1 |  | -0.0 | -281.6 | -108.6 |
| AUDJPY | H1 | bb_rev | T | 815.0 | 0.8 | -8840.2 | -9151.7 | -295.9 |  | -0.0 | -7.1 | -175.1 |
| NZDJPY | D1 | rsi_rev | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| NZDJPY | D1 | aroon_x | T | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| NZDJPY | D1 | aroon_x |  | 0.0 |  | 0.0 | 0.0 | 0.0 | 2.00 | 0.0 | 0.0 | 0.0 |
| AUDJPY | H1 | bb_rev |  | 2659.0 | 0.8 | -36291.0 | -36387.5 | -398.2 |  | -0.0 | -265.3 | -419.0 |
| AUDJPY | H1 | dmi_x | T | 748.0 | 0.8 | -6898.9 | -7344.1 | -384.5 |  | -0.0 | -49.1 | -81.3 |
| AUDJPY | H1 | dmi_x |  | 1848.0 | 0.7 | -25312.6 | -25527.8 | -384.7 |  | -0.0 | -219.1 | -248.9 |
| XAGUSD | H4 | macd_zero | T | 210.0 | 0.7 | -3403.0 | -3580.2 | -183.8 |  | -0.0 | -37.4 | -24.2 |
| XAGUSD | H4 | macd_zero |  | 479.0 | 0.7 | -5785.8 | -7039.7 | -205.7 |  | -0.0 | -87.1 | -11.6 |
| XAGUSD | H4 | macd_x | T | 394.0 | 0.7 | -5918.6 | -5948.9 | -181.4 |  | -0.0 | -68.3 | -37.9 |
| XAGUSD | H4 | macd_x |  | 1065.0 | 0.7 | -14107.9 | -14327.2 | -286.3 |  | -0.0 | -127.1 | -135.1 |
| XAGUSD | H4 | rsi_mom | T | 401.0 | 0.7 | -5570.5 | -5824.4 | -188.6 |  | -0.0 | -74.1 | -23.4 |
| XAGUSD | H4 | rsi_mom |  | 1570.0 | 0.6 | -18051.9 | -18661.6 | -265.7 |  | -0.0 | -228.4 | -90.6 |
| XAGUSD | H4 | rsi_rev |  | 352.0 | 0.7 | -5096.5 | -5266.1 | -163.5 |  | -0.0 | -32.3 | -65.8 |
| XAUUSD | H4 | don_rev |  | 790.0 | 0.9 | -3840.1 | -4193.2 | -225.0 |  | -0.0 | -11.7 | -65.4 |
| XAUUSD | H4 | don_brk | T | 456.0 | 1.0 | -432.6 | -2479.5 | -225.7 |  | -0.0 | -0.8 | -8.1 |
| XAUUSD | H4 | don_brk |  | 600.0 | 1.0 | 710.5 | -2694.3 | -262.0 |  | 0.0 | 5.9 | 7.5 |
| XAUUSD | H4 | ha_flip | T | 638.0 | 1.0 | -353.8 | -3532.7 | -196.2 |  | -0.0 | -42.5 | 45.8 |
| AUDJPY | H1 | cci_mom | T | 1908.0 | 0.8 | -18539.6 | -19013.3 | -371.0 |  | -0.0 | -149.2 | -196.7 |
| AUDJPY | H1 | don_rev |  | 3263.0 | 0.7 | -47398.0 | -48107.5 | -451.3 |  | -0.0 | -390.9 | -490.7 |
| AUDJPY | H1 | don_brk | T | 1808.0 | 0.8 | -18116.3 | -18467.3 | -308.1 |  | -0.0 | -195.3 | -129.2 |
| AUDJPY | H1 | don_brk |  | 2403.0 | 0.8 | -20810.7 | -23372.0 | -319.6 |  | -0.0 | -306.6 | -44.0 |
| AUDJPY | H1 | ha_flip | T | 2659.0 | 0.8 | -25402.1 | -25916.6 | -428.9 |  | -0.0 | -238.7 | -225.8 |
| AUDJPY | H1 | stoch_rev |  | 3184.0 | 0.7 | -47217.5 | -47297.2 | -412.4 |  | -0.0 | -392.9 | -484.4 |
| AUDJPY | H1 | macd_zero | T | 892.0 | 0.8 | -8359.7 | -10433.3 | -377.9 |  | -0.0 | -109.8 | -34.6 |
| AUDJPY | H1 | macd_zero |  | 1895.0 | 0.8 | -14555.1 | -18389.2 | -377.9 |  | -0.0 | -226.1 | -16.0 |
| AUDJPY | H1 | macd_x | T | 1659.0 | 0.8 | -17819.6 | -18564.0 | -497.4 |  | -0.0 | -129.0 | -207.3 |
| AUDJPY | H1 | macd_x |  | 4231.0 | 0.8 | -44177.9 | -45012.1 | -497.4 |  | -0.0 | -398.7 | -413.7 |
| AUDJPY | H1 | rsi_mom | T | 1656.0 | 0.8 | -17600.1 | -18105.5 | -375.4 |  | -0.0 | -124.1 | -209.0 |
| AUDJPY | H1 | obv_slope |  | 8864.0 | 0.6 | -95490.2 | -95607.4 | -528.8 |  | -0.0 | -930.5 | -806.9 |
| AUDJPY | H1 | cmf_zero | T | 1672.0 | 0.8 | -16039.6 | -16604.5 | -528.7 |  | -0.0 | -156.0 | -136.0 |
| AUDJPY | H1 | cmf_zero |  | 3145.0 | 0.8 | -22225.6 | -23369.0 | -528.7 |  | -0.0 | -274.2 | -114.6 |
| AUDJPY | H1 | mfi_rev | T | 276.0 | 0.7 | -4881.7 | -5148.4 | -451.2 |  | -0.0 | -47.5 | -41.3 |
| AUDJPY | H1 | mfi_rev |  | 987.0 | 0.7 | -18534.9 | -19047.5 | -451.2 |  | -0.0 | -173.0 | -166.3 |
| AUDJPY | H1 | willr_rev | T | 1537.0 | 0.8 | -16432.7 | -16662.2 | -383.7 |  | -0.0 | -128.6 | -178.9 |
| CHFJPY | H1 | dmi_x |  | 1764.0 | 0.7 | -24072.9 | -27172.9 | -364.9 |  | -0.0 | -303.1 | -116.4 |
| CHFJPY | H1 | cci_mom | T | 1854.0 | 0.8 | -16747.2 | -20150.7 | -324.4 |  | -0.0 | -193.5 | -102.9 |
| CHFJPY | H1 | cci_mom |  | 3095.0 | 0.8 | -35783.6 | -40515.3 | -431.5 |  | -0.0 | -445.1 | -179.9 |
| CHFJPY | H1 | cci_rev | T | 1298.0 | 0.7 | -20215.5 | -20439.8 | -292.6 |  | -0.0 | -178.5 | -194.4 |
| AUDJPY | H1 | squeeze_brk |  | 1000.0 | 0.8 | -8925.6 | -10194.4 | -309.9 |  | -0.0 | -117.3 | -36.9 |
| AUDJPY | H1 | kelt_rev | T | 364.0 | 0.8 | -5067.4 | -5475.0 | -451.3 |  | -0.0 | -20.7 | -79.3 |
| AUDJPY | H1 | kelt_rev |  | 1823.0 | 0.8 | -25664.7 | -26588.2 | -451.3 |  | -0.0 | -193.9 | -288.3 |
| AUDJPY | H1 | kelt_brk | T | 1246.0 | 0.9 | -9444.2 | -9828.0 | -256.9 |  | -0.0 | -87.7 | -85.3 |
| AUDJPY | H1 | kelt_brk |  | 1514.0 | 0.9 | -11295.4 | -11918.1 | -358.0 |  | -0.0 | -138.1 | -59.8 |
| AUDJPY | H1 | bb_brk | T | 1580.0 | 0.8 | -16151.1 | -17043.3 | -324.1 |  | -0.0 | -179.6 | -108.2 |
| CHFJPY | H1 | macd_x |  | 4489.0 | 0.6 | -71155.8 | -71593.5 | -482.7 |  | -0.0 | -700.6 | -592.0 |
| CHFJPY | H1 | rsi_mom | T | 1728.0 | 0.8 | -21115.3 | -21151.6 | -387.8 |  | -0.0 | -202.4 | -182.7 |
| CHFJPY | H1 | rsi_mom |  | 6496.0 | 0.6 | -89670.0 | -89833.0 | -482.7 |  | -0.0 | -891.5 | -735.2 |
| CHFJPY | H1 | rsi_rev | T | 153.0 | 0.6 | -3742.2 | -4008.5 | -175.1 |  | -0.0 | -29.4 | -40.6 |
| CHFJPY | H1 | rsi_rev |  | 1216.0 | 0.7 | -18385.6 | -19076.5 | -374.4 |  | -0.0 | -222.4 | -100.4 |
| AUDJPY | H1 | don_rev | T | 957.0 | 0.7 | -16476.9 | -16859.4 | -451.3 |  | -0.0 | -130.0 | -178.1 |
| CHFJPY | H1 | mfi_rev |  | 1029.0 | 0.7 | -17456.5 | -18886.1 | -313.1 |  | -0.0 | -149.1 | -174.2 |
| CHFJPY | H1 | willr_rev | T | 1538.0 | 0.7 | -25082.2 | -25671.4 | -341.8 |  | -0.0 | -211.9 | -253.3 |
| CHFJPY | H1 | willr_rev |  | 4619.0 | 0.7 | -69257.2 | -69544.7 | -394.7 |  | -0.0 | -580.0 | -705.8 |
| CHFJPY | H1 | aroon_x | T | 980.0 | 0.9 | -4261.0 | -7541.9 | -317.9 |  | -0.0 | -47.8 | -28.0 |
| AUDJPY | H1 | ha_flip |  | 8878.0 | 0.7 | -98597.6 | -98817.3 | -453.0 |  | -0.0 | -914.9 | -891.4 |
| AUDJPY | H1 | ema_x | T | 588.0 | 0.8 | -4948.6 | -5388.4 | -391.2 |  | -0.0 | -36.8 | -56.4 |
| AUDJPY | H1 | ema_x |  | 1039.0 | 0.9 | -7713.7 | -10131.2 | -391.2 |  | -0.0 | -119.4 | -9.0 |
| AUDJPY | H1 | ema_slope | T | 1066.0 | 0.8 | -12711.8 | -13535.7 | -322.2 |  | -0.0 | -104.8 | -131.7 |
| AUDJPY | H1 | ema_slope |  | 2639.0 | 0.8 | -25708.4 | -26305.1 | -418.8 |  | -0.0 | -290.2 | -166.8 |
| AUDJPY | H1 | obv_slope | T | 2005.0 | 0.8 | -16962.2 | -17339.7 | -383.9 |  | -0.0 | -184.8 | -118.5 |
| CHFJPY | H1 | kelt_brk |  | 1366.0 | 0.8 | -17777.7 | -19496.3 | -318.2 |  | -0.0 | -162.6 | -163.7 |
| CHFJPY | H1 | bb_brk | T | 1570.0 | 0.8 | -19367.9 | -20199.6 | -297.6 |  | -0.0 | -182.5 | -171.6 |
| CHFJPY | H1 | bb_brk |  | 2300.0 | 0.8 | -27606.9 | -29206.6 | -374.8 |  | -0.0 | -330.4 | -155.2 |
| CHFJPY | H1 | bb_rev | T | 868.0 | 0.7 | -13764.4 | -14248.3 | -296.6 |  | -0.0 | -91.0 | -171.1 |
| CHFJPY | H1 | bb_rev |  | 2698.0 | 0.7 | -38003.8 | -38467.9 | -389.7 |  | -0.0 | -310.0 | -397.8 |
| CHFJPY | H1 | dmi_x | T | 715.0 | 0.7 | -11501.2 | -12288.7 | -340.2 |  | -0.0 | -103.5 | -108.0 |
| NZDJPY | H1 | rsi_rev |  | 1283.0 | 0.8 | -17318.7 | -17953.8 | -349.2 |  | -0.0 | -166.9 | -148.7 |
| CHFJPY | H1 | don_rev | T | 944.0 | 0.7 | -16067.9 | -17780.1 | -335.7 |  | -0.0 | -140.0 | -156.8 |
| CHFJPY | H1 | don_rev |  | 3138.0 | 0.7 | -46427.7 | -46944.4 | -389.8 |  | -0.0 | -362.4 | -506.7 |
| US500 | H4 | trend_vote v=5 |  | 501.0 | 1.0 | 1098.4 | -2722.1 | -300.4 |  | 0.0 | -16.4 | 43.4 |
| CHFJPY | H1 | don_brk | T | 1681.0 | 0.8 | -21350.9 | -21862.5 | -316.0 |  | -0.0 | -210.6 | -177.2 |
| CHFJPY | H1 | cci_rev |  | 3764.0 | 0.7 | -55722.1 | -56367.6 | -371.7 |  | -0.0 | -486.2 | -543.0 |
| CHFJPY | H1 | stoch_rev | T | 918.0 | 0.7 | -18443.0 | -19244.6 | -291.8 |  | -0.0 | -153.9 | -188.7 |
| CHFJPY | H1 | stoch_rev |  | 2903.0 | 0.7 | -49273.5 | -49737.4 | -414.5 |  | -0.0 | -411.4 | -503.7 |
| CHFJPY | H1 | macd_zero | T | 854.0 | 0.8 | -8732.4 | -9241.8 | -321.4 |  | -0.0 | -103.9 | -49.9 |
| CHFJPY | H1 | macd_zero |  | 1834.0 | 0.8 | -17638.0 | -17916.2 | -357.6 |  | -0.0 | -200.4 | -112.8 |
| CHFJPY | H1 | macd_x | T | 1657.0 | 0.7 | -23483.4 | -23932.1 | -382.0 |  | -0.0 | -240.6 | -183.4 |
| CHFJPY | H1 | ema_slope |  | 2581.0 | 0.7 | -30153.6 | -30858.5 | -431.5 |  | -0.0 | -338.7 | -197.7 |
| CHFJPY | H1 | obv_slope | T | 2033.0 | 0.8 | -25894.5 | -26366.3 | -365.9 |  | -0.0 | -246.2 | -226.6 |
| CHFJPY | H1 | obv_slope |  | 8669.0 | 0.6 | -108000.1 | -108488.7 | -612.2 |  | -0.0 | -1079.9 | -877.6 |
| CHFJPY | H1 | cmf_zero | T | 1645.0 | 0.8 | -19321.2 | -19986.8 | -386.1 |  | -0.0 | -183.6 | -169.2 |
| CHFJPY | H1 | cmf_zero |  | 3330.0 | 0.7 | -42143.1 | -42434.4 | -513.6 |  | -0.0 | -370.8 | -406.8 |
| CHFJPY | H1 | mfi_rev | T | 294.0 | 0.8 | -3784.4 | -4942.3 | -198.1 |  | -0.0 | -35.9 | -33.2 |
| NZDJPY | H1 | bb_rev |  | 2646.0 | 0.7 | -40006.8 | -40528.6 | -436.3 |  | -0.0 | -383.7 | -345.8 |
| NZDJPY | H1 | dmi_x | T | 734.0 | 0.8 | -9652.1 | -9698.5 | -294.8 |  | -0.0 | -85.6 | -92.3 |
| NZDJPY | H1 | dmi_x |  | 1813.0 | 0.7 | -24249.6 | -24355.9 | -372.8 |  | -0.0 | -226.1 | -217.9 |
| NZDJPY | H1 | cci_mom | T | 1858.0 | 0.8 | -17115.1 | -17958.3 | -397.0 |  | -0.0 | -168.9 | -141.9 |
| CHFJPY | H1 | aroon_x |  | 2112.0 | 0.9 | -13171.1 | -17239.4 | -333.9 |  | -0.0 | -171.6 | -56.3 |
| XAUUSD | H4 | stoch_rev |  | 822.0 | 0.9 | -6164.4 | -6298.4 | -211.2 |  | -0.0 | -34.5 | -85.4 |
| CHFJPY | H1 | squeeze_brk | T | 702.0 | 0.7 | -10974.5 | -11628.2 | -271.5 |  | -0.0 | -88.2 | -116.6 |
| US500 | H4 | trend_vote v=4 |  | 579.0 | 1.0 | -197.7 | -3547.8 | -300.4 |  | -0.0 | -43.7 | 50.5 |
| CHFJPY | H1 | squeeze_brk |  | 937.0 | 0.8 | -11603.9 | -12027.7 | -336.3 |  | -0.0 | -114.5 | -96.2 |
| CHFJPY | H1 | kelt_rev | T | 312.0 | 0.6 | -7319.5 | -7950.9 | -258.7 |  | -0.0 | -75.9 | -56.0 |
| CHFJPY | H1 | kelt_rev |  | 1623.0 | 0.8 | -23057.2 | -23420.1 | -346.5 |  | -0.0 | -224.2 | -195.4 |
| CHFJPY | H1 | kelt_brk | T | 1129.0 | 0.7 | -17010.6 | -18382.5 | -251.5 |  | -0.0 | -148.8 | -165.3 |
| NZDJPY | H1 | macd_zero |  | 1837.0 | 0.9 | -11473.9 | -13160.4 | -400.4 |  | -0.0 | -113.6 | -94.7 |
| NZDJPY | H1 | macd_x | T | 1601.0 | 0.8 | -22366.1 | -23126.3 | -366.7 |  | -0.0 | -184.0 | -232.2 |
| NZDJPY | H1 | macd_x |  | 4307.0 | 0.7 | -65923.1 | -66359.8 | -425.4 |  | -0.0 | -647.0 | -551.1 |
| NZDJPY | H1 | rsi_mom | T | 1635.0 | 0.8 | -20398.2 | -20542.0 | -383.2 |  | -0.0 | -128.2 | -262.1 |
| NZDJPY | H1 | rsi_mom |  | 5999.0 | 0.6 | -72810.5 | -72985.5 | -410.5 |  | -0.0 | -679.0 | -654.0 |
| NZDJPY | H1 | rsi_rev | T | 142.0 | 0.7 | -2469.5 | -2920.8 | -240.4 |  | -0.0 | -14.2 | -33.4 |
| AUDJPY | D1 | ha_flip |  | 394.0 | 0.8 | -2457.6 | -2697.4 | -183.8 |  | -0.0 | -12.2 | -35.9 |
| NZDJPY | H1 | cmf_zero |  | 3196.0 | 0.7 | -39622.1 | -40317.8 | -398.3 |  | -0.0 | -427.1 | -282.6 |
| XAUUSD | H4 | ema_x |  | 280.0 | 0.8 | -3120.6 | -4006.1 | -242.3 |  | -0.0 | -40.7 | -14.1 |
| XAUUSD | H4 | ema_slope | T | 269.0 | 0.8 | -2332.8 | -3580.0 | -211.2 |  | -0.0 | -39.1 | 0.3 |
| XAUUSD | H4 | ema_slope |  | 683.0 | 0.9 | -1813.9 | -3382.7 | -246.4 |  | -0.0 | -35.0 | 5.9 |
| XAUUSD | H4 | obv_slope | T | 483.0 | 0.9 | -2565.3 | -3553.0 | -293.5 |  | -0.0 | -36.9 | -7.3 |
| XAUUSD | H4 | obv_slope |  | 2033.0 | 1.0 | -2194.4 | -3817.2 | -298.9 |  | -0.0 | -36.0 | -0.7 |
| XAUUSD | H4 | cmf_zero | T | 399.0 | 1.0 | -692.3 | -2546.5 | -215.5 |  | -0.0 | 14.0 | -31.9 |
| NZDJPY | H1 | mfi_rev | T | 233.0 | 0.8 | -2269.0 | -2873.1 | -197.7 |  | -0.0 | 6.8 | -55.9 |
| XAUUSD | H4 | mfi_rev |  | 263.0 | 0.8 | -2685.2 | -3027.1 | -147.8 |  | -0.0 | -31.2 | -16.9 |
| XAUUSD | H4 | willr_rev | T | 382.0 | 0.9 | -1796.9 | -3073.3 | -196.0 |  | -0.0 | -44.3 | 18.0 |
| XAUUSD | H4 | willr_rev |  | 1157.0 | 0.9 | -6024.8 | -6686.2 | -214.1 |  | -0.0 | -50.0 | -63.0 |
| XAUUSD | H4 | aroon_x | T | 266.0 | 0.9 | -1864.3 | -2541.6 | -263.2 |  | -0.0 | -21.9 | -11.5 |
| XAUUSD | H4 | rsi_mom |  | 1449.0 | 1.0 | -1800.6 | -3103.5 | -304.5 |  | -0.0 | -29.4 | -0.8 |
| XAUUSD | H4 | macd_x |  | 1055.0 | 0.9 | -2500.3 | -3304.7 | -221.5 |  | -0.0 | -31.4 | -12.9 |
| CHFJPY | D1 | ha_flip | T | 96.0 | 1.0 | -0.9 | -1103.4 | -159.9 | 0.50 | -0.0 | -4.2 | 5.2 |
| CADJPY | D1 | kelt_brk | T | 47.0 | 1.0 | -2.7 | -953.8 | -105.2 | 0.50 | -0.0 | -1.6 | 1.9 |
| GBPUSD | D1 | kelt_brk |  | 58.0 | 1.0 | -3.6 | -962.7 | -125.9 | 0.50 | -0.0 | -0.7 | 0.8 |
| NZDUSD | D1 | bb_rev |  | 97.0 | 1.0 | -3.0 | -770.0 | -183.3 | 0.75 | -0.0 | -1.2 | 1.5 |
| GBPJPY | D1 | bb_rev |  | 110.0 | 1.0 | -5.5 | -1006.3 | -107.1 | 0.50 | -0.0 | -12.6 | 15.7 |
| USDJPY | D1 | cci_mom | T | 75.0 | 1.0 | -6.2 | -1158.3 | -129.4 | 0.50 | -0.0 | -6.5 | 8.0 |
| AUDJPY | D1 | obv_slope | T | 84.0 | 1.0 | -7.9 | -854.9 | -96.7 | 0.50 | -0.0 | -3.1 | 3.7 |
| NZDUSD | H4 | kelt_rev | T | 93.0 | 1.0 | -9.0 | -1002.4 | -171.3 | 0.50 | -0.0 | -1.6 | 1.9 |
| EURJPY | D1 | squeeze_brk | T | 30.0 | 1.0 | -6.2 | -722.6 | -175.1 | 0.75 | -0.0 | 7.1 | -9.0 |
| USDJPY | D1 | dmi_x | T | 27.0 | 1.0 | -6.8 | -638.7 | -161.3 | 0.75 | -0.0 | -2.9 | 3.4 |
| AUDCAD | D1 | trend_vote v=4 | T | 36.0 | 1.0 | -4.5 | -599.4 | -115.2 | 1.00 | -0.0 | -1.4 | 2.2 |
| DE40 | D1 | aroon_x | T | 40.0 | 1.0 | -4.3 | -460.6 | -84.4 | 1.25 | -0.0 | 0.7 | -1.0 |
| GBPCHF | D1 | trend_vote v=4 | T | 46.0 | 1.0 | -22.3 | -1331.2 | -121.2 | 0.25 | -0.1 | 10.2 | -13.3 |
| AUDCAD | H4 | macd_zero | T | 204.0 | 1.0 | -21.4 | -1256.9 | -199.6 | 0.25 | -0.1 | -10.2 | 16.8 |
| USDJPY | D1 | stoch_rev |  | 148.0 | 1.0 | -12.2 | -1101.8 | -161.3 | 0.50 | -0.1 | 8.6 | -11.0 |
| DE40 | D1 | don_rev | T | 34.0 | 1.0 | -9.2 | -653.8 | -109.7 | 0.75 | -0.1 | -5.7 | 7.0 |
| EURJPY | H4 | rsi_rev |  | 347.0 | 1.0 | -28.5 | -1700.7 | -454.8 | 0.25 | -0.1 | -13.5 | 16.3 |
| US500 | D1 | cmf_zero |  | 109.0 | 1.0 | -33.1 | -1690.2 | -125.7 | 0.25 | -0.1 | 11.3 | -14.9 |
| USDCHF | H4 | macd_zero | T | 241.0 | 1.0 | -36.7 | -1684.4 | -193.4 | 0.25 | -0.1 | -2.0 | 1.7 |
| USDCAD | H4 | mfi_rev |  | 276.0 | 1.0 | -37.3 | -2150.0 | -184.2 | 0.25 | -0.1 | -12.5 | 14.9 |
| AUDUSD | D1 | macd_x |  | 184.0 | 1.0 | -41.1 | -1299.5 | -127.7 | 0.25 | -0.1 | -8.3 | 9.5 |
| XAUUSD | D1 | rsi_mom | T | 69.0 | 1.0 | -14.8 | -746.4 | -105.0 | 0.75 | -0.1 | -5.8 | 7.0 |
| GBPUSD | D1 | bb_brk |  | 94.0 | 1.0 | -45.8 | -1325.3 | -106.6 | 0.25 | -0.1 | -14.0 | 16.6 |
| NZDUSD | H4 | dmi_x | T | 182.0 | 1.0 | -48.3 | -1445.3 | -162.7 | 0.25 | -0.1 | -14.5 | 17.2 |
| CADJPY | D1 | squeeze_brk |  | 35.0 | 1.0 | -16.3 | -641.4 | -113.8 | 0.75 | -0.1 | 2.1 | -3.0 |
| EURUSD | H4 | ema_slope | T | 298.0 | 1.0 | -52.0 | -2003.0 | -204.4 | 0.25 | -0.1 | -12.0 | 14.0 |
| EURJPY | H4 | mfi_rev | T | 63.0 | 1.0 | -52.2 | -1305.7 | -162.7 | 0.25 | -0.1 | -13.9 | 16.2 |
| DE40 | D1 | macd_zero | T | 31.0 | 1.0 | -13.5 | -559.2 | -78.8 | 1.00 | -0.1 | 0.1 | -0.4 |
| AUDUSD | H4 | ema_slope | T | 293.0 | 1.0 | -59.8 | -2017.4 | -187.2 | 0.25 | -0.1 | 15.2 | -20.2 |
| AUDJPY | D1 | willr_rev | T | 57.0 | 1.0 | -20.8 | -628.9 | -94.2 | 0.75 | -0.1 | -0.9 | 0.7 |
| EURGBP | D1 | cci_mom | T | 73.0 | 1.0 | -66.9 | -1221.0 | -111.7 | 0.25 | -0.2 | 5.8 | -8.7 |
| GBPUSD | D1 | dmi_x |  | 72.0 | 1.0 | -23.7 | -746.1 | -138.1 | 0.75 | -0.2 | 0.0 | -0.5 |
| EURUSD | D1 | macd_zero |  | 84.0 | 1.0 | -35.7 | -1154.9 | -135.1 | 0.50 | -0.2 | -12.0 | 14.2 |
| USDCHF | D1 | ema_x | T | 27.0 | 1.0 | -25.5 | -701.6 | -126.5 | 0.75 | -0.2 | 1.6 | -2.6 |
| EURUSD | D1 | bb_brk |  | 88.0 | 1.0 | -77.3 | -1439.7 | -103.3 | 0.25 | -0.2 | -6.0 | 5.9 |
| EURJPY | H4 | dmi_x | T | 172.0 | 1.0 | -39.3 | -1083.9 | -202.4 | 0.50 | -0.2 | -1.5 | 1.0 |
| USDJPY | D1 | don_brk |  | 103.0 | 1.0 | -42.2 | -1106.8 | -175.5 | 0.50 | -0.2 | -0.0 | -0.9 |
| USDJPY | H4 | rsi_rev | T | 42.0 | 1.0 | -28.5 | -644.4 | -217.7 | 0.75 | -0.2 | -0.3 | -0.2 |
| USDJPY | D1 | ema_x | T | 19.0 | 1.0 | -17.2 | -447.9 | -99.6 | 1.25 | -0.2 | -2.2 | 2.4 |
| XAUUSD | H4 | rsi_rev | T | 43.0 | 1.0 | -43.5 | -1098.8 | -133.8 | 0.50 | -0.2 | 5.5 | -7.7 |
| GBPCHF | D1 | cmf_zero | T | 54.0 | 1.0 | -87.9 | -1306.0 | -101.0 | 0.25 | -0.2 | 1.7 | -3.9 |
| CHFJPY | D1 | rsi_rev | T | 5.0 | 1.0 | -11.8 | -251.9 | -66.3 | 2.00 | -0.2 | -2.4 | 2.7 |
| EURJPY | D1 | squeeze_brk |  | 37.0 | 1.0 | -47.4 | -1002.4 | -122.6 | 0.50 | -0.2 | 10.0 | -13.5 |
| EURUSD | D1 | trend_vote v=6 | T | 60.0 | 1.0 | -48.2 | -1152.9 | -103.3 | 0.50 | -0.2 | -9.7 | 11.1 |
| NZDJPY | H4 | ema_x |  | 268.0 | 1.0 | -98.1 | -2107.5 | -223.7 | 0.25 | -0.2 | -4.2 | 3.3 |
| AUDCAD | D1 | ha_flip | T | 86.0 | 1.0 | -45.7 | -802.3 | -99.3 | 0.50 | -0.2 | -3.4 | 4.4 |
| NZDJPY | H4 | rsi_rev | T | 39.0 | 1.0 | -26.1 | -549.7 | -159.0 | 1.00 | -0.2 | -3.2 | 3.5 |
| GBPJPY | D1 | ema_slope | T | 51.0 | 1.0 | -51.9 | -1164.2 | -125.8 | 0.50 | -0.2 | -2.5 | 2.0 |
| XAUUSD | H1 | mfi_rev | T | 261.0 | 1.0 | -104.7 | -2319.4 | -182.8 | 0.25 | -0.2 | 5.4 | -9.0 |
| EURUSD | D1 | bb_rev | T | 28.0 | 1.0 | -26.4 | -547.3 | -91.9 | 1.00 | -0.2 | -0.6 | 0.2 |
| EURCHF | D1 | macd_x | T | 55.0 | 1.0 | -53.0 | -874.5 | -138.8 | 0.50 | -0.2 | 6.2 | -8.9 |
| XAUUSD | D1 | don_rev |  | 145.0 | 1.0 | -107.3 | -1271.7 | -145.2 | 0.25 | -0.2 | 2.7 | -5.6 |
| EURJPY | D1 | rsi_rev |  | 52.0 | 1.0 | -108.6 | -1372.4 | -171.9 | 0.25 | -0.3 | -8.8 | 8.7 |
| GBPUSD | D1 | aroon_x |  | 95.0 | 1.0 | -108.9 | -1283.5 | -168.8 | 0.25 | -0.3 | -6.8 | 6.2 |
| AUDUSD | H4 | rsi_mom | T | 417.0 | 1.0 | -113.4 | -2009.8 | -208.7 | 0.25 | -0.3 | -18.4 | 20.6 |
| USTEC | H1 | don_rev | T | 143.0 | 1.0 | -19.1 | -1655.9 | -279.9 | 0.25 | -0.3 | 0.0 | -1.1 |
| AUDJPY | D1 | cci_mom |  | 120.0 | 1.0 | -119.7 | -1525.5 | -124.9 | 0.25 | -0.3 | -23.1 | 26.4 |
| USDCHF | D1 | obv_slope |  | 410.0 | 1.0 | -120.5 | -1652.4 | -161.7 | 0.25 | -0.3 | -18.4 | 20.5 |
| CHFJPY | D1 | bb_brk | T | 54.0 | 1.0 | -63.3 | -1053.3 | -125.4 | 0.50 | -0.3 | -2.2 | 1.4 |
| CHFJPY | D1 | macd_x | T | 62.0 | 1.0 | -63.4 | -1037.6 | -123.6 | 0.50 | -0.3 | -1.0 | -0.1 |
| GBPCHF | D1 | trend_vote v=5 | T | 54.0 | 1.0 | -64.0 | -1128.1 | -121.2 | 0.50 | -0.3 | 9.4 | -13.1 |
| AUDCAD | D1 | macd_x |  | 179.0 | 1.0 | -115.6 | -1959.6 | -112.8 | 0.25 | -0.3 | -15.8 | 23.1 |
| GBPUSD | D1 | rsi_mom | T | 64.0 | 1.0 | -65.3 | -883.9 | -126.8 | 0.50 | -0.3 | 0.9 | -2.5 |
| AUDUSD | D1 | aroon_x |  | 85.0 | 1.0 | -69.4 | -1036.4 | -109.5 | 0.50 | -0.3 | 5.0 | -7.7 |
| US30 | D1 | macd_zero |  | 51.0 | 1.0 | -70.7 | -975.6 | -114.7 | 0.50 | -0.3 | -6.9 | 7.1 |
| GBPUSD | H4 | squeeze_brk | T | 171.0 | 1.0 | -141.7 | -1962.6 | -179.6 | 0.25 | -0.3 | 12.1 | -18.1 |
| CHFJPY | D1 | don_brk | T | 65.0 | 1.0 | -143.6 | -1286.5 | -125.4 | 0.25 | -0.3 | -10.1 | 9.7 |
| DE40 | D1 | cci_mom | T | 72.0 | 1.0 | -49.0 | -703.4 | -83.7 | 0.75 | -0.3 | -0.7 | -0.2 |
| NZDUSD | D1 | aroon_x | T | 36.0 | 1.0 | -36.8 | -548.9 | -110.5 | 1.00 | -0.3 | 5.9 | -8.1 |
| GBPJPY | D1 | obv_slope | T | 79.0 | 1.0 | -74.9 | -1099.2 | -125.8 | 0.50 | -0.3 | 11.8 | -16.3 |
| AUDUSD | D1 | don_brk | T | 73.0 | 1.0 | -75.0 | -961.8 | -111.7 | 0.50 | -0.3 | 0.6 | -2.3 |
| USDCAD | D1 | kelt_brk |  | 52.0 | 1.0 | -75.7 | -1066.3 | -109.2 | 0.50 | -0.4 | -1.4 | 0.2 |
| US30 | D1 | ha_flip |  | 291.0 | 1.0 | -151.5 | -1381.0 | -121.1 | 0.25 | -0.4 | -6.3 | 4.7 |
| XAUUSD | D1 | kelt_rev |  | 85.0 | 1.0 | -77.4 | -1026.2 | -117.6 | 0.50 | -0.4 | 4.9 | -7.7 |
| NZDJPY | H4 | squeeze_brk | T | 187.0 | 1.0 | -156.2 | -2199.1 | -165.5 | 0.25 | -0.4 | 29.7 | -40.9 |
| AUDUSD | D1 | kelt_brk | T | 50.0 | 1.0 | -53.7 | -708.5 | -111.7 | 0.75 | -0.4 | -0.9 | -0.0 |
| DE40 | D1 | kelt_rev |  | 75.0 | 1.0 | -54.4 | -736.8 | -127.9 | 0.75 | -0.4 | 1.9 | -3.5 |
| XAGUSD | D1 | don_rev | T | 39.0 | 1.0 | -41.3 | -572.3 | -88.9 | 1.00 | -0.4 | -1.4 | 0.8 |
| USDCAD | D1 | kelt_rev |  | 64.0 | 1.0 | -83.6 | -979.1 | -119.7 | 0.50 | -0.4 | -1.9 | 0.7 |
| XAUUSD | D1 | trend_vote v=4 | T | 53.0 | 1.0 | -86.6 | -875.7 | -92.0 | 0.50 | -0.4 | -5.0 | 4.4 |
| AUDUSD | H4 | rsi_rev | T | 36.0 | 1.0 | -90.8 | -896.3 | -127.1 | 0.50 | -0.4 | -8.1 | 8.2 |
| AUDJPY | D1 | dmi_x | T | 27.0 | 1.0 | -45.8 | -582.0 | -92.8 | 1.00 | -0.4 | 0.4 | -1.5 |
| USDJPY | D1 | rsi_mom | T | 62.0 | 1.0 | -96.6 | -1129.6 | -161.3 | 0.50 | -0.4 | -7.0 | 6.7 |
| EURCHF | D1 | obv_slope | T | 73.0 | 1.0 | -100.4 | -998.2 | -151.2 | 0.50 | -0.5 | 4.0 | -7.1 |
| AUDCAD | D1 | bb_rev | T | 29.0 | 0.9 | -91.7 | -831.7 | -90.6 | 0.50 | -0.5 | -5.3 | 6.3 |
| GBPUSD | D1 | kelt_rev | T | 11.0 | 0.9 | -34.5 | -378.4 | -106.0 | 1.50 | -0.5 | 0.3 | -1.1 |
| USDCAD | D1 | ha_flip | T | 100.0 | 1.0 | -104.1 | -1136.4 | -154.7 | 0.50 | -0.5 | -8.4 | 8.4 |
| DE40 | H4 | cmf_zero | T | 370.0 | 1.0 | -209.2 | -1683.7 | -186.2 | 0.25 | -0.5 | 3.3 | -8.5 |
| GBPUSD | D1 | kelt_rev |  | 64.0 | 1.0 | -105.8 | -1023.3 | -123.4 | 0.50 | -0.5 | 5.0 | -8.5 |
| EURCHF | D1 | cmf_zero |  | 99.0 | 0.9 | -213.3 | -1277.3 | -138.8 | 0.25 | -0.5 | -8.5 | 6.2 |
| DE40 | H4 | rsi_rev | T | 39.0 | 1.0 | -72.4 | -736.5 | -156.5 | 0.75 | -0.5 | 5.1 | -7.9 |
| NZDUSD | D1 | rsi_mom |  | 285.0 | 1.0 | -219.4 | -1488.4 | -116.0 | 0.25 | -0.5 | 16.1 | -24.7 |
| USDCHF | D1 | stoch_rev | T | 45.0 | 0.9 | -220.7 | -1220.1 | -124.6 | 0.25 | -0.5 | -5.6 | 2.4 |
| EURUSD | D1 | dmi_x | T | 25.0 | 0.9 | -111.1 | -800.3 | -106.9 | 0.50 | -0.5 | -3.9 | 2.5 |
| AUDUSD | D1 | dmi_x |  | 73.0 | 1.0 | -112.5 | -915.2 | -100.2 | 0.50 | -0.5 | 10.9 | -15.9 |
| EURGBP | H1 | rsi_rev | T | 189.0 | 1.0 | -227.9 | -2386.5 | -233.5 | 0.25 | -0.5 | 13.9 | -22.5 |
| CHFJPY | D1 | don_rev | T | 31.0 | 0.9 | -113.2 | -1125.0 | -168.1 | 0.50 | -0.5 | -7.0 | 6.4 |
| USDJPY | D1 | macd_x | T | 66.0 | 0.9 | -228.1 | -1366.3 | -111.3 | 0.25 | -0.5 | -14.4 | 13.3 |
| AUDUSD | D1 | trend_vote v=5 | T | 60.0 | 0.9 | -232.4 | -1228.5 | -184.0 | 0.25 | -0.5 | 7.9 | -14.7 |
| GBPUSD | D1 | ema_slope |  | 121.0 | 1.0 | -117.2 | -968.0 | -112.1 | 0.50 | -0.5 | -2.6 | 0.8 |
| USDCHF | D1 | stoch_rev |  | 141.0 | 1.0 | -239.8 | -2037.2 | -124.6 | 0.25 | -0.6 | 2.3 | -7.9 |
| EURGBP | D1 | rsi_rev |  | 45.0 | 1.0 | -81.0 | -761.6 | -127.4 | 0.75 | -0.6 | -0.3 | -1.4 |
| EURGBP | H4 | cci_rev | T | 306.0 | 1.0 | -245.9 | -2208.0 | -177.0 | 0.25 | -0.6 | -19.1 | 18.8 |
| AUDJPY | D1 | bb_rev | T | 28.0 | 0.9 | -123.3 | -878.6 | -84.7 | 0.50 | -0.6 | 7.2 | -11.5 |
| USDJPY | H4 | mfi_rev |  | 226.0 | 1.0 | -247.3 | -2120.9 | -183.1 | 0.25 | -0.6 | -4.5 | 0.5 |
| AUDUSD | D1 | willr_rev |  | 198.0 | 1.0 | -251.7 | -2166.9 | -221.1 | 0.25 | -0.6 | 20.3 | -30.7 |
| USDCAD | H1 | kelt_rev | T | 368.0 | 1.0 | -255.6 | -2036.1 | -297.2 | 0.25 | -0.6 | -9.8 | 7.1 |
| CHFJPY | D1 | rsi_rev |  | 58.0 | 1.0 | -127.1 | -831.4 | -98.7 | 0.50 | -0.6 | -0.1 | -2.5 |
| EURGBP | H4 | mfi_rev | T | 65.0 | 0.9 | -254.5 | -1225.0 | -171.8 | 0.25 | -0.6 | 2.7 | -8.7 |
| US30 | H4 | trend_vote v=4 |  | 578.0 | 1.0 | -255.2 | -2235.2 | -253.3 | 0.25 | -0.6 | -11.3 | 8.8 |
| AUDJPY | D1 | cci_rev | T | 50.0 | 1.0 | -127.7 | -1005.7 | -94.2 | 0.50 | -0.6 | 8.4 | -13.1 |
| GBPUSD | D1 | macd_zero |  | 90.0 | 0.9 | -258.7 | -1254.2 | -112.6 | 0.25 | -0.6 | -4.4 | 0.1 |
| GBPCHF | H4 | stoch_rev | T | 248.0 | 1.0 | -261.7 | -1427.7 | -190.2 | 0.25 | -0.6 | -8.6 | 5.5 |
| GBPCHF | D1 | don_brk | T | 68.0 | 1.0 | -131.6 | -974.2 | -121.1 | 0.50 | -0.6 | 6.1 | -10.4 |
| AUDCAD | D1 | cci_rev | T | 38.0 | 0.9 | -117.0 | -943.2 | -90.7 | 0.50 | -0.6 | -10.7 | 14.6 |
| EURGBP | D1 | cci_rev | T | 42.0 | 1.0 | -89.3 | -635.1 | -103.2 | 0.75 | -0.6 | -1.3 | -0.3 |
| USDCAD | H4 | bb_rev | T | 213.0 | 1.0 | -268.3 | -1626.2 | -165.4 | 0.25 | -0.6 | -1.2 | -4.1 |
| AUDJPY | D1 | trend_vote v=4 | T | 50.0 | 1.0 | -90.7 | -621.3 | -125.0 | 0.75 | -0.6 | -2.2 | 0.8 |
| CHFJPY | D1 | trend_vote v=4 |  | 122.0 | 1.0 | -137.0 | -1146.3 | -123.0 | 0.50 | -0.6 | -0.8 | -1.8 |
| DE40 | D1 | aroon_x |  | 85.0 | 1.0 | -91.5 | -712.5 | -105.4 | 0.75 | -0.6 | 3.7 | -6.5 |
| XAGUSD | D1 | cci_rev | T | 50.0 | 1.0 | -92.9 | -741.8 | -102.3 | 0.75 | -0.6 | 1.4 | -3.7 |
| XAGUSD | D1 | dmi_x |  | 67.0 | 0.9 | -139.6 | -952.6 | -116.2 | 0.50 | -0.6 | 0.8 | -3.9 |
| XAUUSD | H4 | macd_zero |  | 472.0 | 1.0 | -283.7 | -1694.8 | -262.0 | 0.25 | -0.7 | -10.9 | 7.8 |
| CADJPY | D1 | don_brk | T | 69.0 | 1.0 | -142.0 | -988.0 | -117.6 | 0.50 | -0.7 | 3.0 | -6.7 |
| USDJPY | D1 | ema_slope |  | 130.0 | 1.0 | -142.0 | -936.7 | -124.3 | 0.50 | -0.7 | -6.9 | 5.7 |
| GBPUSD | D1 | aroon_x | T | 41.0 | 1.0 | -57.2 | -442.5 | -112.6 | 1.25 | -0.7 | -0.4 | -0.7 |
| USDJPY | H4 | dmi_x | T | 172.0 | 1.0 | -286.5 | -1694.9 | -213.0 | 0.25 | -0.7 | -6.5 | 2.2 |
| EURCHF | D1 | cmf_zero | T | 49.0 | 1.0 | -96.2 | -680.0 | -138.8 | 0.75 | -0.7 | -2.4 | 1.0 |
| GBPJPY | D1 | trend_vote v=6 | T | 50.0 | 0.9 | -144.5 | -1011.8 | -91.1 | 0.50 | -0.7 | 11.2 | -17.1 |
| US30 | D1 | obv_slope |  | 291.0 | 1.0 | -144.8 | -996.1 | -97.0 | 0.50 | -0.7 | 6.2 | -10.7 |
| AUDUSD | D1 | rsi_mom |  | 271.0 | 1.0 | -146.8 | -930.0 | -184.0 | 0.50 | -0.7 | -2.6 | 0.2 |
| DE40 | D1 | macd_zero |  | 82.0 | 1.0 | -98.7 | -783.7 | -81.2 | 0.75 | -0.7 | -4.2 | 3.3 |
| AUDJPY | D1 | don_rev | T | 37.0 | 0.9 | -99.3 | -644.1 | -89.0 | 0.75 | -0.7 | 5.0 | -8.3 |
| AUDUSD | H4 | trend_vote v=4 | T | 313.0 | 1.0 | -298.1 | -1365.3 | -201.9 | 0.25 | -0.7 | 4.2 | -11.4 |
| XAGUSD | D1 | squeeze_brk |  | 34.0 | 0.9 | -100.8 | -632.0 | -137.7 | 0.75 | -0.7 | -2.0 | 0.4 |
| AUDUSD | H4 | aroon_x | T | 261.0 | 1.0 | -309.2 | -1575.8 | -190.2 | 0.25 | -0.7 | 0.7 | -7.3 |
| XAUUSD | D1 | rsi_mom |  | 255.0 | 0.9 | -309.3 | -1415.0 | -107.0 | 0.25 | -0.7 | -10.6 | 6.8 |
| USDJPY | D1 | don_brk | T | 72.0 | 1.0 | -157.0 | -1039.2 | -130.9 | 0.50 | -0.7 | -0.2 | -3.0 |
| EURGBP | D1 | trend_vote v=4 | T | 49.0 | 1.0 | -108.3 | -760.3 | -145.8 | 0.75 | -0.8 | 0.3 | -2.6 |
| CHFJPY | H4 | kelt_rev | T | 90.0 | 0.9 | -326.7 | -1959.5 | -334.5 | 0.25 | -0.8 | -13.6 | 10.2 |
| US30 | D1 | cci_rev | T | 34.0 | 0.9 | -81.7 | -493.7 | -149.7 | 1.00 | -0.8 | 2.3 | -4.5 |
| GBPUSD | D1 | don_brk | T | 72.0 | 1.0 | -164.2 | -1173.2 | -125.9 | 0.50 | -0.8 | -3.1 | 0.4 |
| NZDUSD | D1 | trend_vote v=4 | T | 53.0 | 1.0 | -109.5 | -725.1 | -110.5 | 0.75 | -0.8 | 1.3 | -4.0 |
| XAGUSD | H4 | rsi_rev | T | 41.0 | 0.9 | -165.3 | -836.8 | -168.2 | 0.50 | -0.8 | 0.3 | -3.8 |
| USDCAD | D1 | trend_vote v=6 | T | 60.0 | 0.9 | -332.2 | -1212.4 | -113.4 | 0.25 | -0.8 | -0.1 | -6.7 |
| EURGBP | D1 | ema_x |  | 57.0 | 0.9 | -167.3 | -866.3 | -92.3 | 0.50 | -0.8 | 2.0 | -6.0 |
| CADJPY | H4 | macd_zero | T | 219.0 | 1.0 | -335.6 | -1304.6 | -212.9 | 0.25 | -0.8 | -2.5 | -3.8 |
| GBPJPY | D1 | ema_x | T | 30.0 | 0.9 | -170.0 | -984.6 | -114.7 | 0.50 | -0.8 | 6.5 | -11.7 |
| GBPCHF | D1 | bb_brk | T | 65.0 | 0.9 | -340.3 | -1217.9 | -100.8 | 0.25 | -0.8 | -2.1 | -4.5 |
| US500 | D1 | obv_slope |  | 412.0 | 1.0 | -340.9 | -1603.4 | -126.1 | 0.25 | -0.8 | 5.0 | -13.3 |
| EURUSD | D1 | squeeze_brk |  | 35.0 | 0.9 | -171.7 | -1135.6 | -97.6 | 0.50 | -0.8 | 2.0 | -6.1 |
| USDJPY | D1 | obv_slope | T | 91.0 | 0.9 | -343.6 | -1438.9 | -161.3 | 0.25 | -0.8 | -16.8 | 13.8 |
| GBPCHF | D1 | ha_flip |  | 368.0 | 1.0 | -344.7 | -1314.9 | -149.7 | 0.25 | -0.8 | 2.4 | -10.2 |
| EURGBP | D1 | don_rev | T | 40.0 | 0.9 | -173.2 | -943.1 | -106.1 | 0.50 | -0.8 | -7.9 | 6.2 |
| USDJPY | D1 | cmf_zero |  | 128.0 | 1.0 | -175.7 | -1034.9 | -193.9 | 0.50 | -0.8 | 1.8 | -5.9 |
| XAGUSD | D1 | trend_vote v=5 | T | 50.0 | 0.9 | -176.3 | -896.5 | -137.7 | 0.50 | -0.8 | -8.6 | 7.1 |
| US500 | H4 | kelt_rev | T | 100.0 | 1.0 | -176.8 | -1153.6 | -260.1 | 0.50 | -0.8 | 1.1 | -5.1 |
| XAUUSD | D1 | obv_slope |  | 425.0 | 1.0 | -353.8 | -1735.9 | -99.7 | 0.25 | -0.8 | -4.2 | -2.2 |
| USDJPY | D1 | macd_x |  | 189.0 | 1.0 | -354.5 | -2154.4 | -212.8 | 0.25 | -0.8 | 4.3 | -12.7 |
| US30 | D1 | rsi_mom |  | 180.0 | 1.0 | -177.7 | -1141.9 | -110.3 | 0.50 | -0.8 | -1.0 | -2.5 |
| CADJPY | D1 | cci_rev | T | 62.0 | 0.9 | -180.2 | -1066.6 | -112.5 | 0.50 | -0.8 | -4.9 | 2.3 |
| USDCAD | D1 | kelt_brk | T | 41.0 | 0.8 | -362.9 | -1323.9 | -109.2 | 0.25 | -0.8 | -1.8 | -5.3 |
| AUDCAD | D1 | ema_slope |  | 106.0 | 0.9 | -323.8 | -1362.5 | -121.3 | 0.25 | -0.8 | -20.1 | 24.4 |
| GBPCHF | D1 | rsi_mom |  | 275.0 | 0.9 | -368.3 | -2267.3 | -109.0 | 0.25 | -0.9 | 27.5 | -42.1 |
| CHFJPY | D1 | dmi_x | T | 24.0 | 0.9 | -184.2 | -892.4 | -86.2 | 0.50 | -0.9 | 0.8 | -4.8 |
| EURGBP | H4 | squeeze_brk |  | 236.0 | 1.0 | -370.0 | -2047.1 | -188.2 | 0.25 | -0.9 | 8.6 | -18.4 |
| USDCAD | D1 | macd_x |  | 177.0 | 0.9 | -373.8 | -1299.6 | -139.4 | 0.25 | -0.9 | -10.5 | 5.3 |
| XAUUSD | D1 | rsi_rev |  | 56.0 | 0.9 | -187.2 | -1041.9 | -92.6 | 0.50 | -0.9 | -5.4 | 2.8 |
| AUDCAD | D1 | cmf_zero |  | 101.0 | 1.0 | -170.2 | -934.1 | -140.3 | 0.50 | -0.9 | 7.1 | -16.6 |
| GBPCHF | D1 | aroon_x |  | 93.0 | 0.9 | -385.0 | -1704.6 | -121.2 | 0.25 | -0.9 | 14.4 | -26.0 |
| XAGUSD | D1 | cci_mom | T | 70.0 | 1.0 | -128.8 | -684.3 | -114.5 | 0.75 | -0.9 | 6.4 | -10.6 |
| XAGUSD | D1 | kelt_brk | T | 44.0 | 0.9 | -129.5 | -659.3 | -134.3 | 0.75 | -0.9 | -1.6 | -0.7 |
| DE40 | D1 | don_brk | T | 63.0 | 1.0 | -97.4 | -490.4 | -100.6 | 1.00 | -0.9 | 3.0 | -5.7 |
| EURJPY | H4 | rsi_rev | T | 49.0 | 0.9 | -389.8 | -1316.8 | -454.8 | 0.25 | -0.9 | -15.8 | 11.6 |
| AUDCAD | H4 | kelt_rev | T | 68.0 | 1.0 | -176.3 | -957.3 | -185.6 | 0.50 | -0.9 | -5.1 | 3.8 |
| AUDCAD | D1 | bb_rev |  | 97.0 | 0.9 | -349.5 | -1433.7 | -109.0 | 0.25 | -0.9 | 2.3 | -13.6 |
| AUDUSD | D1 | macd_zero | T | 37.0 | 0.9 | -131.3 | -763.8 | -109.5 | 0.75 | -0.9 | 1.0 | -4.0 |
| GBPCHF | D1 | kelt_brk |  | 55.0 | 0.9 | -197.6 | -891.7 | -121.1 | 0.50 | -0.9 | -8.5 | 6.6 |
| CHFJPY | D1 | ema_slope | T | 45.0 | 0.9 | -198.4 | -1175.8 | -125.4 | 0.50 | -0.9 | -5.0 | 2.1 |
| GBPCHF | D1 | don_brk |  | 101.0 | 0.9 | -397.6 | -1511.6 | -121.1 | 0.25 | -0.9 | 12.4 | -23.8 |
| CADJPY | D1 | ema_slope | T | 51.0 | 0.9 | -400.0 | -1455.4 | -101.0 | 0.25 | -0.9 | -7.9 | 1.5 |
| AUDCAD | H4 | cmf_zero | T | 368.0 | 1.0 | -362.0 | -2267.2 | -189.3 | 0.25 | -0.9 | -10.2 | 7.3 |
| DE40 | D1 | trend_vote v=4 | T | 45.0 | 0.9 | -201.9 | -824.7 | -97.0 | 0.50 | -0.9 | -6.9 | 4.4 |
| XAGUSD | D1 | ema_x |  | 56.0 | 0.9 | -202.1 | -1000.9 | -137.7 | 0.50 | -0.9 | -11.7 | 10.4 |
| NZDUSD | H4 | dmi_x |  | 458.0 | 1.0 | -404.7 | -1593.8 | -275.7 | 0.25 | -0.9 | 0.4 | -8.9 |
| NZDUSD | D1 | ema_x | T | 21.0 | 0.9 | -81.0 | -465.6 | -96.4 | 1.25 | -0.9 | 2.7 | -5.1 |
| GBPJPY | D1 | mfi_rev |  | 39.0 | 0.9 | -135.2 | -640.3 | -114.4 | 0.75 | -0.9 | 6.8 | -11.3 |
| XAUUSD | D1 | don_brk | T | 72.0 | 0.9 | -204.5 | -887.2 | -102.3 | 0.50 | -0.9 | -4.4 | 1.3 |
| US500 | D1 | bb_rev |  | 105.0 | 0.9 | -409.6 | -1634.0 | -118.4 | 0.25 | -0.9 | -8.9 | 2.6 |
| AUDCAD | H4 | ema_slope | T | 221.0 | 1.0 | -184.1 | -1157.6 | -169.5 | 0.50 | -0.9 | -4.1 | 1.9 |
| GBPJPY | D1 | dmi_x |  | 76.0 | 1.0 | -136.9 | -777.7 | -114.7 | 0.75 | -1.0 | 2.3 | -5.7 |
| AUDCAD | H4 | trend_vote v=5 | T | 291.0 | 1.0 | -370.3 | -1845.2 | -229.7 | 0.25 | -1.0 | -25.8 | 33.4 |
| USDCHF | D1 | kelt_brk | T | 46.0 | 0.9 | -207.6 | -909.9 | -134.4 | 0.50 | -1.0 | -5.1 | 2.0 |
| EURUSD | D1 | trend_vote v=6 |  | 77.0 | 0.9 | -420.1 | -1580.9 | -103.3 | 0.25 | -1.0 | -14.9 | 9.8 |
| GBPJPY | D1 | trend_vote v=6 |  | 68.0 | 0.9 | -210.1 | -1197.0 | -91.1 | 0.50 | -1.0 | 7.6 | -13.9 |
| XAGUSD | D1 | macd_x | T | 66.0 | 0.9 | -212.4 | -824.7 | -114.5 | 0.50 | -1.0 | -2.8 | -0.9 |
| NZDUSD | D1 | trend_vote v=5 |  | 93.0 | 1.0 | -213.0 | -1077.8 | -120.3 | 0.50 | -1.0 | 4.6 | -10.2 |
| XAUUSD | D1 | trend_vote v=4 |  | 118.0 | 0.9 | -430.7 | -1255.2 | -92.0 | 0.25 | -1.0 | -11.8 | 5.8 |
| CHFJPY | H4 | ema_x | T | 150.0 | 1.0 | -216.7 | -1150.2 | -196.4 | 0.50 | -1.0 | -4.5 | 1.2 |
| AUDJPY | H4 | kelt_rev | T | 89.0 | 1.0 | -218.9 | -990.2 | -154.2 | 0.50 | -1.0 | -7.3 | 4.7 |
| DE40 | H4 | mfi_rev | T | 67.0 | 0.9 | -437.6 | -1298.1 | -160.5 | 0.25 | -1.0 | -8.6 | 1.6 |
| CHFJPY | H4 | aroon_x |  | 550.0 | 1.0 | -442.2 | -2199.9 | -207.2 | 0.25 | -1.0 | -5.2 | -2.7 |
| USTEC | H4 | cci_rev |  | 165.0 | 1.0 | -36.9 | -1184.2 | -160.4 | 0.50 | -1.0 | 0.0 | -2.0 |
| AUDCAD | D1 | rsi_rev | T | 3.0 | 0.7 | -49.2 | -226.6 | -76.4 | 2.00 | -1.0 | -3.1 | 3.8 |
| NZDUSD | D1 | cci_mom | T | 69.0 | 0.9 | -222.3 | -844.3 | -101.9 | 0.50 | -1.0 | 0.3 | -5.1 |
| USTEC | H4 | don_brk | T | 71.0 | 1.0 | -74.4 | -1215.7 | -179.4 | 0.25 | -1.0 | 0.0 | -4.1 |
| USDCAD | D1 | aroon_x |  | 87.0 | 0.9 | -224.0 | -1122.6 | -133.5 | 0.50 | -1.0 | -1.4 | -2.9 |
| USDCAD | D1 | don_brk |  | 103.0 | 0.9 | -448.5 | -1231.9 | -116.0 | 0.25 | -1.0 | -5.9 | -1.9 |
| GBPUSD | H4 | aroon_x | T | 255.0 | 1.0 | -449.1 | -1871.7 | -210.3 | 0.25 | -1.0 | -3.0 | -5.6 |
| AUDJPY | D1 | aroon_x | T | 39.0 | 1.0 | -90.0 | -476.7 | -125.0 | 1.25 | -1.0 | -3.1 | 1.9 |
| XAGUSD | D1 | ha_flip |  | 379.0 | 0.9 | -455.4 | -1350.2 | -143.2 | 0.25 | -1.1 | -12.6 | 6.2 |
| AUDUSD | H4 | mfi_rev | T | 65.0 | 1.0 | -152.9 | -649.1 | -161.7 | 0.75 | -1.1 | 1.5 | -5.0 |
| XAUUSD | H4 | trend_vote v=4 |  | 646.0 | 1.0 | -459.0 | -2305.6 | -262.0 | 0.25 | -1.1 | -20.5 | 16.0 |
| XAGUSD | D1 | bb_brk | T | 61.0 | 0.9 | -153.3 | -667.6 | -119.3 | 0.75 | -1.1 | -3.5 | 1.2 |
| XAUUSD | D1 | willr_rev |  | 202.0 | 1.0 | -230.6 | -1069.2 | -117.6 | 0.50 | -1.1 | -7.7 | 4.8 |
| CHFJPY | H4 | trend_vote v=4 | T | 316.0 | 1.0 | -462.5 | -1799.9 | -211.0 | 0.25 | -1.1 | -1.1 | -8.2 |
| NZDJPY | D1 | cci_mom |  | 3.0 | 0.7 | -57.9 | -237.5 | -43.3 | 2.00 | -1.1 | -1.0 | 0.0 |
| DE40 | H4 | don_rev | T | 188.0 | 1.0 | -464.7 | -1974.5 | -191.2 | 0.25 | -1.1 | -20.3 | 15.7 |
| CHFJPY | D1 | kelt_rev |  | 76.0 | 0.9 | -232.8 | -940.1 | -187.8 | 0.50 | -1.1 | 0.3 | -5.2 |
| US30 | H4 | rsi_rev | T | 32.0 | 0.9 | -155.9 | -670.7 | -171.7 | 0.75 | -1.1 | -3.4 | 1.0 |
| DE40 | D1 | macd_x |  | 183.0 | 0.9 | -469.0 | -1465.0 | -159.5 | 0.25 | -1.1 | -4.8 | -3.8 |
| GBPCHF | D1 | macd_zero | T | 39.0 | 0.8 | -470.0 | -1249.4 | -121.2 | 0.25 | -1.1 | 5.3 | -16.5 |
| AUDCAD | D1 | macd_zero |  | 72.0 | 0.9 | -209.7 | -1112.4 | -115.2 | 0.50 | -1.1 | -8.1 | 7.7 |
| AUDUSD | D1 | trend_vote v=6 | T | 60.0 | 0.9 | -159.2 | -638.4 | -127.7 | 0.75 | -1.1 | -6.6 | 4.9 |
| EURGBP | D1 | cmf_zero | T | 52.0 | 0.8 | -477.9 | -1252.4 | -129.0 | 0.25 | -1.1 | 2.1 | -12.6 |
| GBPCHF | H4 | squeeze_brk | T | 165.0 | 0.9 | -484.0 | -2098.6 | -182.8 | 0.25 | -1.1 | 22.0 | -38.1 |
| XAUUSD | D1 | macd_x | T | 68.0 | 0.9 | -239.9 | -801.9 | -101.3 | 0.50 | -1.1 | -1.7 | -2.9 |
| AUDCAD | D1 | squeeze_brk |  | 36.0 | 0.9 | -213.3 | -854.4 | -99.1 | 0.50 | -1.1 | 5.2 | -14.6 |
| AUDCAD | D1 | trend_vote v=4 |  | 94.0 | 0.9 | -428.4 | -1223.1 | -121.3 | 0.25 | -1.1 | -11.6 | 7.5 |
| AUDUSD | D1 | trend_vote v=5 |  | 103.0 | 0.9 | -484.6 | -1533.0 | -184.0 | 0.25 | -1.1 | 8.9 | -21.2 |
| GBPJPY | D1 | trend_vote v=5 | T | 54.0 | 0.9 | -242.9 | -826.2 | -105.9 | 0.50 | -1.1 | 4.9 | -11.2 |
| US30 | D1 | ema_x |  | 35.0 | 0.9 | -163.1 | -749.5 | -114.7 | 0.75 | -1.1 | 0.6 | -4.1 |
| AUDJPY | D1 | trend_vote v=6 |  | 78.0 | 0.9 | -245.0 | -1073.0 | -89.7 | 0.50 | -1.1 | -11.3 | 9.0 |
| EURUSD | H4 | rsi_rev | T | 47.0 | 0.8 | -491.1 | -1286.5 | -142.2 | 0.25 | -1.1 | 10.0 | -22.7 |
| USDCHF | H4 | kelt_rev |  | 452.0 | 1.0 | -492.0 | -2141.4 | -218.5 | 0.25 | -1.1 | -11.4 | 4.0 |
| EURGBP | D1 | rsi_rev | T | 4.0 | 0.7 | -61.6 | -150.0 | -74.7 | 2.00 | -1.1 | 0.6 | -2.0 |
| EURCHF | D1 | trend_vote v=5 |  | 87.0 | 0.9 | -247.6 | -936.5 | -166.6 | 0.50 | -1.1 | -9.5 | 6.7 |
| NZDJPY | D1 | ha_flip | T | 3.0 | 0.7 | -62.5 | -282.7 | -85.0 | 2.00 | -1.2 | -1.0 | 0.0 |
| AUDCAD | D1 | don_rev | T | 36.0 | 0.9 | -223.5 | -1062.6 | -90.6 | 0.50 | -1.2 | -8.2 | 7.5 |
| GBPJPY | D1 | macd_x | T | 62.0 | 0.8 | -504.7 | -1351.0 | -125.8 | 0.25 | -1.2 | 0.2 | -10.7 |
| EURUSD | D1 | ema_x | T | 24.0 | 0.8 | -252.6 | -861.4 | -103.3 | 0.50 | -1.2 | -7.6 | 4.3 |
| XAUUSD | H4 | macd_x | T | 410.0 | 1.0 | -506.9 | -1596.3 | -214.7 | 0.25 | -1.2 | -15.3 | 8.6 |
| EURJPY | D1 | cci_mom | T | 75.0 | 0.9 | -255.0 | -1102.6 | -154.1 | 0.50 | -1.2 | 2.2 | -8.1 |
| NZDUSD | D1 | ema_slope | T | 43.0 | 0.8 | -511.2 | -1219.1 | -93.5 | 0.25 | -1.2 | -7.5 | -1.3 |
| NZDUSD | H4 | trend_vote v=6 | T | 372.0 | 1.0 | -512.8 | -1481.0 | -177.5 | 0.25 | -1.2 | -2.1 | -8.0 |
| US30 | D1 | cmf_zero | T | 46.0 | 0.9 | -128.5 | -574.6 | -123.7 | 1.00 | -1.2 | -1.8 | -0.4 |
| AUDJPY | H4 | bb_brk |  | 577.0 | 1.0 | -521.2 | -1931.5 | -249.1 | 0.25 | -1.2 | -3.6 | -6.2 |
| CADJPY | H4 | kelt_rev | T | 96.0 | 0.9 | -516.8 | -1393.8 | -170.8 | 0.25 | -1.2 | -6.8 | -2.3 |
| XAGUSD | D1 | willr_rev | T | 56.0 | 0.9 | -172.4 | -648.5 | -116.2 | 0.75 | -1.2 | -3.2 | 0.4 |
| GBPJPY | D1 | bb_brk | T | 60.0 | 0.9 | -258.6 | -1005.0 | -105.9 | 0.50 | -1.2 | 6.4 | -13.4 |
| CADJPY | H4 | mfi_rev | T | 73.0 | 0.9 | -258.8 | -940.8 | -161.6 | 0.50 | -1.2 | -1.4 | -3.6 |
| GBPCHF | D1 | macd_zero |  | 90.0 | 0.9 | -517.9 | -1594.2 | -149.7 | 0.25 | -1.2 | 10.2 | -23.5 |
| EURUSD | D1 | macd_x |  | 192.0 | 0.9 | -520.1 | -2032.4 | -130.3 | 0.25 | -1.2 | -4.4 | -5.3 |
| DE40 | D1 | bb_rev |  | 103.0 | 0.9 | -260.2 | -1035.4 | -131.7 | 0.50 | -1.2 | 0.4 | -5.9 |
| EURUSD | D1 | rsi_rev |  | 48.0 | 0.8 | -525.0 | -1655.9 | -130.3 | 0.25 | -1.2 | 0.9 | -12.1 |
| CADJPY | D1 | cci_mom | T | 67.0 | 0.9 | -268.6 | -1131.1 | -122.9 | 0.50 | -1.2 | -2.8 | -2.1 |
| USDCAD | D1 | trend_vote v=4 | T | 45.0 | 0.9 | -268.6 | -895.8 | -136.7 | 0.50 | -1.2 | -2.6 | -2.3 |
| EURCHF | D1 | bb_rev |  | 94.0 | 0.9 | -540.2 | -1584.9 | -158.8 | 0.25 | -1.3 | -12.7 | 4.7 |
| US500 | D1 | stoch_rev | T | 29.0 | 0.9 | -180.3 | -661.1 | -230.6 | 0.75 | -1.3 | -0.1 | -3.6 |
| XAUUSD | D1 | cmf_zero |  | 125.0 | 1.0 | -180.7 | -745.7 | -109.3 | 0.75 | -1.3 | 3.3 | -7.9 |
| USDCHF | D1 | don_rev | T | 38.0 | 0.9 | -271.9 | -933.8 | -88.7 | 0.50 | -1.3 | 1.1 | -7.0 |
| AUDCAD | D1 | don_rev |  | 124.0 | 0.9 | -483.7 | -1200.4 | -109.0 | 0.25 | -1.3 | -1.3 | -11.2 |
| CADJPY | D1 | ema_slope |  | 134.0 | 0.9 | -545.8 | -1336.2 | -122.7 | 0.25 | -1.3 | -5.8 | -4.1 |
| CHFJPY | D1 | cci_mom |  | 124.0 | 0.9 | -547.6 | -1499.4 | -125.2 | 0.25 | -1.3 | -4.8 | -5.5 |
| NZDUSD | D1 | kelt_rev |  | 82.0 | 0.9 | -550.2 | -1437.9 | -154.5 | 0.25 | -1.3 | -14.5 | 6.7 |
| US30 | D1 | kelt_brk |  | 47.0 | 0.9 | -275.5 | -902.9 | -101.6 | 0.50 | -1.3 | -0.5 | -5.1 |
| CADJPY | D1 | aroon_x | T | 43.0 | 0.9 | -278.1 | -802.3 | -88.7 | 0.50 | -1.3 | 3.7 | -10.4 |
| AUDCAD | H4 | trend_vote v=4 | T | 268.0 | 1.0 | -505.5 | -2067.5 | -199.6 | 0.25 | -1.3 | -25.2 | 28.6 |
| CADJPY | H4 | ema_x |  | 277.0 | 1.0 | -567.7 | -2329.2 | -226.8 | 0.25 | -1.3 | 5.4 | -18.6 |
| USDCHF | D1 | ema_x |  | 54.0 | 0.9 | -284.0 | -1130.1 | -170.4 | 0.50 | -1.3 | 0.0 | -6.0 |
| US500 | D1 | bb_brk |  | 91.0 | 0.9 | -568.9 | -1239.4 | -161.8 | 0.25 | -1.3 | -17.2 | 9.7 |
| EURUSD | D1 | ema_slope |  | 127.0 | 0.9 | -570.7 | -1808.4 | -133.3 | 0.25 | -1.3 | -22.7 | 16.5 |
| AUDCAD | H4 | mfi_rev |  | 205.0 | 1.0 | -515.4 | -2002.9 | -164.8 | 0.25 | -1.3 | 4.3 | -21.6 |
| GBPJPY | D1 | mfi_rev | T | 6.0 | 0.7 | -98.8 | -392.8 | -114.4 | 1.50 | -1.4 | 3.9 | -7.0 |
| XAUUSD | H4 | bb_brk | T | 406.0 | 1.0 | -595.0 | -2275.3 | -225.7 | 0.25 | -1.4 | -3.2 | -8.4 |
| GBPUSD | D1 | rsi_mom |  | 285.0 | 0.9 | -595.4 | -1768.8 | -126.8 | 0.25 | -1.4 | -15.3 | 6.7 |
| CADJPY | D1 | macd_x |  | 180.0 | 1.0 | -300.5 | -1048.7 | -116.2 | 0.50 | -1.4 | 5.4 | -13.0 |
| EURUSD | D1 | ema_x |  | 46.0 | 0.8 | -601.7 | -1336.7 | -103.3 | 0.25 | -1.4 | -12.6 | 3.3 |
| US30 | H4 | cci_rev | T | 292.0 | 1.0 | -602.2 | -2275.4 | -227.1 | 0.25 | -1.4 | -9.3 | -0.9 |
| XAUUSD | D1 | ha_flip | T | 86.0 | 0.9 | -302.2 | -1074.4 | -101.3 | 0.50 | -1.4 | -10.6 | 6.9 |
| NZDUSD | D1 | kelt_rev | T | 9.0 | 0.7 | -151.2 | -489.3 | -88.6 | 1.00 | -1.4 | -3.2 | 0.9 |
| XAUUSD | D1 | ema_slope |  | 123.0 | 0.9 | -610.2 | -1293.6 | -101.3 | 0.25 | -1.4 | -14.4 | 5.3 |
| USDJPY | H4 | ema_x | T | 150.0 | 0.9 | -611.7 | -1806.5 | -152.7 | 0.25 | -1.4 | 6.1 | -20.3 |
| XAUUSD | H4 | kelt_rev | T | 95.0 | 0.9 | -616.0 | -1325.3 | -141.0 | 0.25 | -1.4 | -9.6 | -0.9 |
| USDCAD | D1 | rsi_mom | T | 68.0 | 0.8 | -619.6 | -1490.0 | -154.7 | 0.25 | -1.4 | -16.8 | 8.1 |
| XAGUSD | D1 | trend_vote v=6 | T | 46.0 | 0.9 | -206.9 | -748.3 | -143.2 | 0.75 | -1.4 | -6.3 | 3.5 |
| AUDUSD | D1 | mfi_rev |  | 23.0 | 0.8 | -207.1 | -737.7 | -92.0 | 0.75 | -1.4 | -6.0 | 3.2 |
| US30 | D1 | don_rev | T | 28.0 | 0.9 | -155.6 | -538.2 | -149.3 | 1.00 | -1.4 | -4.2 | 1.9 |
| USDJPY | D1 | cci_rev |  | 160.0 | 0.9 | -626.4 | -1382.8 | -153.2 | 0.25 | -1.5 | 1.6 | -15.0 |
| CADJPY | D1 | trend_vote v=6 |  | 85.0 | 0.9 | -628.8 | -1264.4 | -132.1 | 0.25 | -1.5 | -2.8 | -9.6 |
| GBPUSD | H4 | bb_brk |  | 576.0 | 1.0 | -629.1 | -1986.2 | -264.2 | 0.25 | -1.5 | -3.1 | -9.2 |
| CADJPY | D1 | don_brk |  | 101.0 | 0.9 | -629.7 | -1250.5 | -117.6 | 0.25 | -1.5 | -0.0 | -13.1 |
| AUDJPY | D1 | trend_vote v=5 |  | 97.0 | 0.9 | -629.7 | -1416.8 | -125.0 | 0.25 | -1.5 | -7.9 | -3.3 |
| AUDJPY | D1 | macd_zero |  | 89.0 | 0.9 | -315.5 | -1105.5 | -124.9 | 0.50 | -1.5 | -9.1 | 4.8 |
| AUDJPY | D1 | trend_vote v=4 |  | 124.0 | 0.9 | -634.5 | -1220.7 | -125.0 | 0.25 | -1.5 | -9.4 | -1.5 |
| XAGUSD | D1 | bb_brk |  | 93.0 | 1.0 | -159.2 | -508.6 | -143.2 | 1.00 | -1.5 | -4.0 | 1.7 |
| US500 | D1 | stoch_rev |  | 142.0 | 0.9 | -637.8 | -2010.3 | -118.4 | 0.25 | -1.5 | -5.4 | -6.5 |
| CHFJPY | D1 | obv_slope |  | 394.0 | 0.9 | -640.2 | -1534.2 | -125.4 | 0.25 | -1.5 | 7.1 | -22.2 |
| USDCAD | D1 | rsi_mom |  | 270.0 | 0.9 | -640.6 | -1689.1 | -154.7 | 0.25 | -1.5 | -18.3 | 9.6 |
| CHFJPY | H4 | rsi_rev |  | 309.0 | 1.0 | -648.0 | -2284.4 | -368.8 | 0.25 | -1.5 | -31.9 | 26.4 |
| USDCHF | D1 | bb_rev | T | 25.0 | 0.8 | -216.4 | -787.9 | -88.3 | 0.75 | -1.5 | -6.5 | 3.7 |
| EURCHF | D1 | ema_slope |  | 126.0 | 0.9 | -653.3 | -1220.6 | -166.6 | 0.25 | -1.5 | -10.5 | -0.5 |
| CHFJPY | D1 | ema_x |  | 58.0 | 0.8 | -655.1 | -1301.7 | -125.7 | 0.25 | -1.5 | 1.8 | -15.9 |
| GBPCHF | D1 | mfi_rev |  | 31.0 | 0.9 | -218.8 | -616.0 | -106.2 | 0.75 | -1.5 | -8.2 | 5.7 |
| EURCHF | D1 | aroon_x |  | 93.0 | 0.9 | -329.1 | -847.9 | -166.6 | 0.50 | -1.5 | 0.5 | -7.4 |
| EURJPY | D1 | cci_mom |  | 124.0 | 0.9 | -661.7 | -1298.0 | -154.1 | 0.25 | -1.5 | -0.5 | -13.1 |
| AUDJPY | D1 | mfi_rev |  | 29.0 | 0.6 | -662.6 | -1280.7 | -98.3 | 0.25 | -1.5 | -8.6 | -3.1 |
| GBPJPY | D1 | ha_flip | T | 104.0 | 0.9 | -663.5 | -1323.5 | -95.9 | 0.25 | -1.5 | 7.6 | -23.3 |
| XAGUSD | D1 | ema_slope |  | 140.0 | 0.9 | -222.3 | -604.9 | -143.2 | 0.75 | -1.5 | -1.5 | -2.7 |
| GBPJPY | D1 | obv_slope |  | 435.0 | 0.9 | -670.4 | -1417.6 | -176.5 | 0.25 | -1.6 | 2.9 | -17.6 |
| US30 | D1 | stoch_rev | T | 18.0 | 0.8 | -135.1 | -443.0 | -93.6 | 1.25 | -1.6 | -4.1 | 2.3 |
| USDCAD | D1 | cci_mom | T | 70.0 | 0.9 | -338.6 | -932.4 | -106.3 | 0.50 | -1.6 | 0.3 | -7.4 |
| DE40 | D1 | kelt_brk |  | 65.0 | 0.9 | -225.9 | -764.7 | -88.4 | 0.75 | -1.6 | -3.4 | -0.5 |
| AUDUSD | D1 | kelt_rev | T | 10.0 | 0.8 | -135.6 | -422.2 | -95.5 | 1.25 | -1.6 | -1.9 | -0.4 |
| US30 | H4 | ha_flip | T | 592.0 | 1.0 | -683.4 | -2338.4 | -298.9 | 0.25 | -1.6 | -5.6 | -7.2 |
| NZDUSD | D1 | dmi_x |  | 84.0 | 0.8 | -683.6 | -1215.8 | -88.7 | 0.25 | -1.6 | -9.3 | -2.7 |
| XAUUSD | D1 | willr_rev | T | 56.0 | 0.8 | -684.1 | -1223.7 | -101.3 | 0.25 | -1.6 | -13.9 | 3.1 |
| EURCHF | H4 | squeeze_brk | T | 161.0 | 0.9 | -684.3 | -2091.0 | -227.3 | 0.25 | -1.6 | -24.4 | 16.3 |
| AUDUSD | D1 | bb_brk | T | 63.0 | 0.9 | -342.8 | -863.4 | -111.7 | 0.50 | -1.6 | -5.8 | 0.1 |
| DE40 | D1 | ha_flip | T | 99.0 | 0.9 | -229.2 | -703.6 | -97.0 | 0.75 | -1.6 | -1.2 | -3.2 |
| NZDUSD | D1 | cmf_zero |  | 129.0 | 0.9 | -687.9 | -1363.7 | -161.2 | 0.25 | -1.6 | 4.2 | -19.6 |
| CADJPY | D1 | dmi_x |  | 72.0 | 0.9 | -344.3 | -807.8 | -101.0 | 0.50 | -1.6 | -2.9 | -3.6 |
| CADJPY | H4 | aroon_x | T | 250.0 | 0.9 | -694.2 | -1584.8 | -180.4 | 0.25 | -1.6 | -5.2 | -7.9 |
| EURGBP | D1 | ha_flip | T | 95.0 | 0.9 | -697.6 | -1322.5 | -145.8 | 0.25 | -1.6 | 6.7 | -22.9 |
| CHFJPY | D1 | cci_rev |  | 153.0 | 0.9 | -699.3 | -1310.9 | -166.0 | 0.25 | -1.6 | -1.6 | -12.6 |
| EURGBP | D1 | mfi_rev |  | 29.0 | 0.9 | -176.7 | -552.9 | -101.1 | 1.00 | -1.6 | -4.8 | 2.3 |
| XAUUSD | D1 | don_brk |  | 99.0 | 0.9 | -355.8 | -1162.7 | -102.3 | 0.50 | -1.6 | -7.7 | 2.2 |
| USDCHF | D1 | rsi_mom | T | 68.0 | 0.8 | -714.5 | -1412.7 | -109.2 | 0.25 | -1.7 | -16.9 | 6.2 |
| USDCAD | D1 | don_rev |  | 145.0 | 0.9 | -718.4 | -1488.1 | -154.6 | 0.25 | -1.7 | -8.9 | -3.8 |
| EURUSD | D1 | trend_vote v=4 |  | 122.0 | 0.9 | -359.8 | -1176.5 | -135.1 | 0.50 | -1.7 | -14.6 | 10.8 |
| AUDJPY | D1 | kelt_brk |  | 63.0 | 0.9 | -180.7 | -595.1 | -93.6 | 1.00 | -1.7 | -2.5 | -0.6 |
| DE40 | H4 | stoch_rev | T | 199.0 | 0.9 | -723.3 | -1833.2 | -161.3 | 0.25 | -1.7 | -28.8 | 21.0 |
| USDCHF | D1 | cci_rev | T | 54.0 | 0.8 | -724.0 | -1774.8 | -94.4 | 0.25 | -1.7 | -12.1 | -0.0 |
| EURGBP | D1 | trend_vote v=4 |  | 125.0 | 0.9 | -726.2 | -1488.3 | -145.8 | 0.25 | -1.7 | 7.0 | -23.9 |
| AUDCAD | D1 | don_brk | T | 61.0 | 0.9 | -322.8 | -972.9 | -101.5 | 0.50 | -1.7 | -9.4 | 6.8 |
| NZDUSD | D1 | don_brk |  | 104.0 | 0.9 | -729.8 | -1235.8 | -110.5 | 0.25 | -1.7 | -5.4 | -8.4 |
| US500 | D1 | mfi_rev |  | 32.0 | 0.6 | -730.0 | -1354.4 | -94.4 | 0.25 | -1.7 | 3.0 | -19.0 |
| USDJPY | D1 | ha_flip | T | 104.0 | 0.9 | -730.1 | -1411.6 | -161.2 | 0.25 | -1.7 | -12.0 | -0.2 |
| USDJPY | D1 | kelt_brk |  | 65.0 | 0.8 | -734.2 | -1251.3 | -132.9 | 0.25 | -1.7 | -5.7 | -8.2 |
| US30 | D1 | dmi_x | T | 22.0 | 0.9 | -147.1 | -405.3 | -114.7 | 1.25 | -1.7 | -5.0 | 3.2 |
| DE40 | H4 | aroon_x | T | 242.0 | 0.9 | -735.5 | -1905.2 | -254.7 | 0.25 | -1.7 | -4.1 | -10.2 |
| USDCAD | D1 | cmf_zero |  | 136.0 | 0.9 | -738.4 | -1675.7 | -136.7 | 0.25 | -1.7 | 9.6 | -27.4 |
| US500 | D1 | macd_zero |  | 68.0 | 0.8 | -741.0 | -1427.0 | -161.8 | 0.25 | -1.7 | -16.8 | 5.5 |
| EURCHF | D1 | rsi_mom | T | 54.0 | 0.9 | -370.9 | -1047.8 | -141.4 | 0.50 | -1.7 | 2.1 | -10.4 |
| GBPUSD | H4 | macd_x | T | 410.0 | 1.0 | -742.1 | -2266.3 | -337.7 | 0.25 | -1.7 | -28.6 | 20.2 |
| USDCHF | H4 | ema_x | T | 139.0 | 0.9 | -743.3 | -1879.0 | -174.7 | 0.25 | -1.7 | -6.2 | -7.8 |
| CADJPY | D1 | ema_x | T | 21.0 | 0.8 | -186.2 | -572.0 | -132.1 | 1.00 | -1.7 | 3.1 | -7.7 |
| CHFJPY | H4 | ema_x |  | 268.0 | 0.9 | -745.2 | -2203.9 | -196.4 | 0.25 | -1.7 | -13.1 | 0.8 |
| AUDUSD | H4 | squeeze_brk |  | 249.0 | 0.9 | -745.8 | -1940.2 | -215.4 | 0.25 | -1.7 | -1.6 | -13.6 |
| USDCAD | D1 | squeeze_brk |  | 45.0 | 0.7 | -746.1 | -1289.9 | -98.3 | 0.25 | -1.7 | -9.7 | -3.4 |
| EURUSD | D1 | rsi_rev | T | 1.0 | 0.0 | -93.6 | -143.1 | -54.5 | 2.00 | -1.7 | 0.0 | -1.9 |
| EURCHF | D1 | cci_rev |  | 141.0 | 0.9 | -750.6 | -1653.4 | -158.8 | 0.25 | -1.7 | -17.4 | 6.2 |
| AUDCAD | D1 | bb_brk |  | 80.0 | 0.8 | -671.8 | -1237.2 | -108.2 | 0.25 | -1.7 | -12.0 | 1.4 |
| US30 | H4 | bb_rev | T | 184.0 | 0.9 | -758.0 | -2009.8 | -223.0 | 0.25 | -1.8 | -7.1 | -6.9 |
| EURJPY | D1 | ha_flip | T | 98.0 | 0.9 | -761.9 | -1703.4 | -146.7 | 0.25 | -1.8 | 2.8 | -19.3 |
| DE40 | D1 | rsi_mom |  | 249.0 | 0.9 | -764.7 | -1618.3 | -178.2 | 0.25 | -1.8 | -10.0 | -3.5 |
| XAGUSD | D1 | obv_slope |  | 407.0 | 0.9 | -383.1 | -1149.8 | -102.3 | 0.50 | -1.8 | -6.2 | -0.3 |
| AUDUSD | H4 | squeeze_brk | T | 196.0 | 0.9 | -767.2 | -1386.1 | -202.2 | 0.25 | -1.8 | -3.1 | -12.1 |
| CADJPY | D1 | cci_mom |  | 122.0 | 0.9 | -386.0 | -1132.8 | -122.9 | 0.50 | -1.8 | -2.5 | -4.9 |
| GBPUSD | D1 | trend_vote v=4 |  | 123.0 | 0.8 | -775.1 | -1384.0 | -138.1 | 0.25 | -1.8 | -2.4 | -13.1 |
| USTEC | H4 | willr_rev |  | 198.0 | 1.0 | -129.2 | -1266.8 | -215.8 | 0.25 | -1.8 | 0.0 | -7.2 |
| EURCHF | D1 | rsi_rev |  | 44.0 | 0.7 | -777.7 | -1247.6 | -86.2 | 0.25 | -1.8 | -11.9 | -1.3 |
| DE40 | D1 | bb_rev | T | 36.0 | 0.9 | -195.1 | -589.5 | -131.7 | 1.00 | -1.8 | -6.9 | 4.5 |
| NZDUSD | D1 | cci_rev | T | 52.0 | 0.7 | -786.6 | -1350.5 | -96.5 | 0.25 | -1.8 | -1.2 | -14.9 |
| US30 | H4 | rsi_mom | T | 385.0 | 1.0 | -787.8 | -2045.4 | -261.7 | 0.25 | -1.8 | -2.5 | -13.3 |
| EURJPY | D1 | mfi_rev |  | 33.0 | 0.8 | -394.5 | -953.3 | -133.5 | 0.50 | -1.8 | -6.3 | -0.3 |
| AUDCAD | D1 | willr_rev | T | 56.0 | 0.9 | -350.7 | -842.3 | -96.8 | 0.50 | -1.8 | -8.1 | 3.7 |
| NZDJPY | D1 | trend_vote v=5 |  | 1.0 | 0.0 | -98.8 | -156.5 | -51.3 | 2.00 | -1.8 | -1.6 | 0.0 |
| NZDJPY | D1 | kelt_brk |  | 1.0 | 0.0 | -99.1 | -99.1 | -42.7 | 2.00 | -1.8 | -1.7 | 0.0 |
| NZDJPY | D1 | kelt_brk | T | 1.0 | 0.0 | -99.1 | -99.1 | -42.7 | 2.00 | -1.8 | -1.7 | 0.0 |
| XAGUSD | D1 | ema_x | T | 29.0 | 0.7 | -396.9 | -846.0 | -137.7 | 0.50 | -1.8 | -10.7 | 5.1 |
| GBPUSD | D1 | obv_slope |  | 449.0 | 0.9 | -794.6 | -1709.2 | -138.1 | 0.25 | -1.8 | -18.4 | 6.4 |
| US30 | H4 | kelt_rev | T | 102.0 | 0.9 | -794.6 | -1719.2 | -223.0 | 0.25 | -1.8 | -13.5 | 0.3 |
| USDCAD | D1 | stoch_rev | T | 41.0 | 0.8 | -399.0 | -840.9 | -88.2 | 0.50 | -1.8 | -1.3 | -6.8 |
| EURCHF | H1 | rsi_rev | T | 124.0 | 0.9 | -806.1 | -1509.7 | -212.0 | 0.25 | -1.8 | -14.8 | 2.0 |
| US500 | D1 | willr_rev |  | 194.0 | 0.9 | -798.9 | -1900.8 | -199.6 | 0.25 | -1.8 | 5.2 | -23.2 |
| NZDJPY | D1 | dmi_x | T | 1.0 | 0.0 | -100.1 | -100.1 | -39.6 | 2.00 | -1.9 | -1.7 | 0.0 |
| AUDCAD | H4 | bb_rev | T | 155.0 | 0.9 | -722.0 | -1680.7 | -192.7 | 0.25 | -1.9 | -19.0 | 12.1 |
| XAUUSD | D1 | cci_rev | T | 46.0 | 0.7 | -804.1 | -1202.9 | -113.8 | 0.25 | -1.9 | -12.8 | -0.8 |
| DE40 | D1 | bb_brk |  | 92.0 | 0.8 | -811.0 | -1357.8 | -116.6 | 0.25 | -1.9 | -4.0 | -11.9 |
| DE40 | H4 | kelt_rev | T | 92.0 | 0.9 | -405.8 | -1089.4 | -169.9 | 0.50 | -1.9 | -5.6 | -1.4 |
| AUDCAD | H4 | aroon_x | T | 239.0 | 0.9 | -729.6 | -1691.2 | -176.5 | 0.25 | -1.9 | -13.4 | 2.4 |
| EURJPY | D1 | ema_x |  | 49.0 | 0.7 | -812.3 | -1263.0 | -140.4 | 0.25 | -1.9 | -5.0 | -10.6 |
| US500 | D1 | ha_flip |  | 360.0 | 0.9 | -812.8 | -1343.6 | -178.1 | 0.25 | -1.9 | -8.7 | -6.1 |
| GBPCHF | D1 | aroon_x | T | 39.0 | 0.8 | -408.4 | -1090.2 | -121.2 | 0.50 | -1.9 | 3.2 | -12.5 |
| EURJPY | H4 | cci_mom | T | 464.0 | 1.0 | -818.1 | -2043.1 | -201.5 | 0.25 | -1.9 | -12.8 | -1.0 |
| XAGUSD | D1 | macd_zero | T | 44.0 | 0.9 | -273.7 | -769.8 | -114.5 | 0.75 | -1.9 | 2.7 | -9.0 |
| XAUUSD | D1 | stoch_rev |  | 137.0 | 0.9 | -823.0 | -1748.2 | -187.8 | 0.25 | -1.9 | -9.0 | -5.9 |
| DE40 | D1 | rsi_rev |  | 41.0 | 0.9 | -206.0 | -587.9 | -127.9 | 1.00 | -1.9 | -1.7 | -2.1 |
| GBPJPY | H4 | mfi_rev | T | 66.0 | 0.8 | -825.4 | -1226.8 | -187.4 | 0.25 | -1.9 | -10.6 | -4.0 |
| CADJPY | D1 | mfi_rev |  | 26.0 | 0.7 | -413.7 | -1070.7 | -105.6 | 0.50 | -1.9 | -12.7 | 7.2 |
| AUDJPY | D1 | obv_slope |  | 419.0 | 0.9 | -828.3 | -1292.1 | -183.8 | 0.25 | -1.9 | -15.6 | 2.3 |
| NZDUSD | D1 | macd_x | T | 60.0 | 0.8 | -829.0 | -1422.8 | -101.9 | 0.25 | -1.9 | -18.8 | 6.3 |
| NZDUSD | D1 | cci_rev |  | 155.0 | 0.9 | -829.5 | -2166.1 | -154.5 | 0.25 | -1.9 | 5.5 | -24.1 |
| AUDJPY | H4 | mfi_rev | T | 52.0 | 0.9 | -279.6 | -783.8 | -132.5 | 0.75 | -1.9 | -4.3 | -0.4 |
| USDCAD | D1 | squeeze_brk | T | 35.0 | 0.6 | -832.2 | -1586.2 | -98.3 | 0.25 | -1.9 | -7.9 | -7.4 |
| XAUUSD | D1 | trend_vote v=5 | T | 47.0 | 0.8 | -416.8 | -1155.4 | -122.3 | 0.50 | -1.9 | -5.7 | -1.5 |
| AUDUSD | H4 | trend_vote v=5 | T | 342.0 | 1.0 | -837.7 | -1896.8 | -190.7 | 0.25 | -1.9 | 0.4 | -17.9 |
| EURGBP | D1 | willr_rev | T | 60.0 | 0.9 | -279.7 | -776.8 | -107.8 | 0.75 | -1.9 | -4.4 | -0.3 |
| USDCAD | D1 | bb_rev |  | 101.0 | 0.8 | -841.9 | -1538.9 | -154.6 | 0.25 | -1.9 | -6.5 | -9.4 |
| GBPCHF | D1 | bb_brk |  | 95.0 | 0.8 | -845.1 | -1428.7 | -101.4 | 0.25 | -2.0 | 0.5 | -18.3 |
| CADJPY | D1 | rsi_mom | T | 73.0 | 0.8 | -849.3 | -1352.1 | -96.9 | 0.25 | -2.0 | -12.2 | -2.4 |
| AUDJPY | D1 | macd_x | T | 56.0 | 0.9 | -424.8 | -1084.5 | -120.5 | 0.50 | -2.0 | -10.5 | 4.2 |
| CHFJPY | D1 | mfi_rev |  | 37.0 | 0.8 | -426.1 | -881.7 | -109.2 | 0.50 | -2.0 | 4.8 | -14.9 |
| EURCHF | D1 | trend_vote v=4 |  | 110.0 | 0.9 | -426.4 | -1178.9 | -166.6 | 0.50 | -2.0 | -8.9 | 2.3 |
| US30 | D1 | ha_flip | T | 79.0 | 0.9 | -428.3 | -953.9 | -115.8 | 0.50 | -2.0 | -1.4 | -7.2 |
| CADJPY | D1 | ha_flip |  | 370.0 | 0.9 | -858.6 | -1881.5 | -144.2 | 0.25 | -2.0 | 6.9 | -26.5 |
| NZDUSD | D1 | dmi_x | T | 30.0 | 0.8 | -287.0 | -719.7 | -76.0 | 0.75 | -2.0 | -1.7 | -3.9 |
| EURJPY | D1 | trend_vote v=5 |  | 100.0 | 0.9 | -431.7 | -1038.2 | -129.9 | 0.50 | -2.0 | -7.5 | 0.4 |
| DE40 | D1 | dmi_x | T | 26.0 | 0.9 | -172.9 | -449.3 | -104.8 | 1.25 | -2.0 | 2.0 | -6.1 |
| XAUUSD | D1 | bb_rev | T | 24.0 | 0.8 | -216.4 | -549.0 | -101.3 | 1.00 | -2.0 | -2.8 | -0.9 |
| AUDJPY | D1 | dmi_x |  | 88.0 | 0.7 | -866.2 | -1491.6 | -102.0 | 0.25 | -2.0 | -8.8 | -7.1 |
| USDCAD | D1 | cci_rev |  | 157.0 | 0.9 | -433.9 | -1102.1 | -154.6 | 0.50 | -2.0 | -4.5 | -3.4 |
| USDJPY | D1 | cci_rev | T | 53.0 | 0.9 | -434.5 | -940.0 | -161.3 | 0.50 | -2.0 | -9.2 | 2.5 |
| CADJPY | D1 | aroon_x |  | 98.0 | 0.8 | -872.2 | -1410.5 | -101.3 | 0.25 | -2.0 | 0.2 | -18.4 |
| USDCAD | D1 | ema_slope |  | 117.0 | 0.8 | -873.2 | -1590.3 | -154.7 | 0.25 | -2.0 | -14.9 | 0.5 |
| XAUUSD | D1 | mfi_rev | T | 4.0 | 0.5 | -145.7 | -370.3 | -91.4 | 1.50 | -2.0 | -4.5 | 2.6 |
| EURUSD | D1 | stoch_rev | T | 31.0 | 0.9 | -219.1 | -584.4 | -128.9 | 1.00 | -2.0 | -4.6 | 1.2 |
| USDCAD | D1 | ema_slope | T | 42.0 | 0.8 | -438.5 | -1008.0 | -154.7 | 0.50 | -2.0 | -11.0 | 4.6 |
| CADJPY | D1 | willr_rev | T | 66.0 | 0.8 | -877.6 | -1549.9 | -95.3 | 0.25 | -2.0 | -11.8 | -3.5 |
| CADJPY | D1 | bb_brk | T | 68.0 | 0.8 | -881.1 | -1777.2 | -108.9 | 0.25 | -2.0 | -11.2 | -4.4 |
| XAGUSD | H4 | kelt_rev | T | 90.0 | 0.8 | -884.5 | -1593.5 | -139.0 | 0.25 | -2.0 | 0.6 | -19.2 |
| CADJPY | D1 | kelt_rev | T | 17.0 | 0.7 | -296.0 | -618.2 | -87.1 | 0.75 | -2.1 | -2.6 | -3.0 |
| US500 | H4 | rsi_rev |  | 320.0 | 1.0 | -890.2 | -1742.6 | -220.7 | 0.25 | -2.1 | 4.8 | -24.6 |
| USDCAD | D1 | stoch_rev |  | 145.0 | 0.9 | -899.1 | -1647.2 | -119.7 | 0.25 | -2.1 | -11.1 | -4.9 |
| GBPJPY | D1 | cmf_zero | T | 67.0 | 0.8 | -899.4 | -1468.9 | -115.8 | 0.25 | -2.1 | -6.5 | -10.6 |
| XAGUSD | D1 | rsi_rev | T | 2.0 | 0.0 | -112.4 | -163.2 | -69.4 | 2.00 | -2.1 | -0.9 | -1.2 |
| NZDUSD | H4 | macd_zero | T | 215.0 | 0.9 | -899.8 | -2364.2 | -195.8 | 0.25 | -2.1 | 15.4 | -38.0 |
| AUDUSD | D1 | trend_vote v=4 | T | 53.0 | 0.8 | -451.0 | -1000.9 | -109.5 | 0.50 | -2.1 | 3.9 | -14.3 |
| EURCHF | H4 | mfi_rev |  | 242.0 | 0.9 | -907.7 | -2268.2 | -183.9 | 0.25 | -2.1 | -24.3 | 11.4 |
| NZDUSD | D1 | mfi_rev |  | 33.0 | 0.9 | -227.2 | -549.5 | -146.8 | 1.00 | -2.1 | -0.5 | -4.1 |
| AUDJPY | D1 | trend_vote v=6 | T | 56.0 | 0.9 | -454.6 | -850.6 | -125.6 | 0.50 | -2.1 | -5.5 | -2.6 |
| XAGUSD | D1 | macd_zero |  | 96.0 | 0.9 | -456.6 | -867.0 | -143.2 | 0.50 | -2.1 | -5.3 | -2.9 |
| CHFJPY | D1 | kelt_brk |  | 61.0 | 0.9 | -456.9 | -869.4 | -174.7 | 0.50 | -2.1 | -1.8 | -7.3 |
| EURGBP | D1 | cmf_zero |  | 113.0 | 0.8 | -914.9 | -1330.7 | -100.3 | 0.25 | -2.1 | -1.4 | -17.3 |
| CADJPY | D1 | trend_vote v=6 | T | 55.0 | 0.9 | -458.4 | -960.8 | -132.1 | 0.50 | -2.1 | -0.3 | -9.2 |
| EURJPY | D1 | don_brk | T | 70.0 | 0.8 | -919.2 | -1284.2 | -175.1 | 0.25 | -2.1 | -2.1 | -16.6 |
| USTEC | H4 | dmi_x | T | 38.0 | 1.0 | -76.7 | -880.5 | -183.0 | 0.50 | -2.1 | 0.0 | -4.3 |
| EURJPY | D1 | trend_vote v=4 |  | 122.0 | 0.8 | -920.8 | -1542.1 | -137.3 | 0.25 | -2.1 | -4.7 | -13.3 |
| GBPJPY | D1 | stoch_rev | T | 35.0 | 0.8 | -462.3 | -877.0 | -101.2 | 0.50 | -2.1 | -2.9 | -6.0 |
| EURGBP | D1 | ema_slope | T | 48.0 | 0.7 | -924.7 | -1610.4 | -145.8 | 0.25 | -2.1 | -19.6 | 5.2 |
| USDJPY | D1 | squeeze_brk |  | 39.0 | 0.6 | -926.0 | -1412.5 | -212.8 | 0.25 | -2.1 | -9.2 | -7.8 |
| USDCHF | D1 | willr_rev | T | 62.0 | 0.7 | -929.9 | -1693.8 | -124.6 | 0.25 | -2.2 | -20.7 | 6.6 |
| AUDUSD | D1 | don_rev | T | 38.0 | 0.9 | -310.2 | -724.8 | -95.5 | 0.75 | -2.2 | -2.5 | -3.3 |
| AUDCAD | D1 | kelt_brk |  | 51.0 | 0.7 | -827.6 | -1209.6 | -131.0 | 0.25 | -2.2 | -11.4 | -3.9 |
| NZDJPY | H4 | kelt_rev | T | 85.0 | 0.8 | -939.9 | -1736.2 | -166.3 | 0.25 | -2.2 | -14.9 | -0.6 |
| USDCHF | D1 | kelt_brk |  | 55.0 | 0.9 | -466.1 | -1094.6 | -134.4 | 0.50 | -2.2 | -7.0 | -1.0 |
| EURJPY | D1 | mfi_rev | T | 5.0 | 0.4 | -155.4 | -333.8 | -113.6 | 1.50 | -2.2 | 0.6 | -4.0 |
| NZDUSD | D1 | rsi_mom | T | 68.0 | 0.9 | -466.6 | -948.8 | -120.3 | 0.50 | -2.2 | -1.8 | -7.5 |
| AUDUSD | D1 | don_rev |  | 142.0 | 0.9 | -466.9 | -1155.0 | -104.9 | 0.50 | -2.2 | 8.4 | -20.2 |
| EURUSD | D1 | bb_rev |  | 110.0 | 0.8 | -933.8 | -1501.0 | -130.3 | 0.25 | -2.2 | -6.7 | -11.1 |
| XAGUSD | D1 | don_brk | T | 70.0 | 0.7 | -935.8 | -1217.6 | -137.7 | 0.25 | -2.2 | -14.4 | -1.4 |
| GBPUSD | H1 | rsi_rev | T | 211.0 | 0.9 | -947.9 | -1749.5 | -257.6 | 0.25 | -2.2 | -4.7 | -13.7 |
| GBPCHF | H4 | mfi_rev | T | 73.0 | 0.8 | -953.1 | -1337.5 | -128.8 | 0.25 | -2.2 | -15.6 | 0.0 |
| CHFJPY | D1 | stoch_rev | T | 36.0 | 0.8 | -472.6 | -1036.8 | -168.1 | 0.50 | -2.2 | -5.9 | -2.5 |
| USDCAD | D1 | trend_vote v=5 | T | 52.0 | 0.9 | -316.2 | -751.2 | -136.3 | 0.75 | -2.2 | -6.6 | 1.6 |
| EURGBP | D1 | bb_brk |  | 89.0 | 0.8 | -948.6 | -1404.3 | -111.7 | 0.25 | -2.2 | 4.2 | -25.0 |
| EURGBP | D1 | trend_vote v=6 | T | 51.0 | 0.7 | -954.1 | -1365.0 | -101.6 | 0.25 | -2.2 | 3.0 | -23.6 |
| EURUSD | H4 | squeeze_brk |  | 278.0 | 0.9 | -964.5 | -2248.8 | -213.6 | 0.25 | -2.2 | -8.2 | -9.8 |
| NZDJPY | D1 | dmi_x |  | 2.0 | 0.0 | -120.7 | -156.5 | -51.3 | 2.00 | -2.2 | -2.0 | 0.0 |
| USDCHF | H4 | kelt_rev | T | 76.0 | 0.8 | -968.7 | -1504.4 | -147.6 | 0.25 | -2.2 | -15.9 | -0.3 |
| GBPUSD | H4 | ema_slope | T | 267.0 | 0.9 | -975.5 | -2223.0 | -192.1 | 0.25 | -2.3 | -15.1 | -1.5 |
| AUDUSD | D1 | trend_vote v=6 |  | 85.0 | 0.9 | -488.9 | -1101.1 | -127.8 | 0.50 | -2.3 | -14.0 | 7.3 |
| AUDCAD | D1 | stoch_rev |  | 115.0 | 0.8 | -869.4 | -1274.6 | -109.0 | 0.25 | -2.3 | 1.2 | -26.2 |
| DE40 | D1 | willr_rev | T | 67.0 | 0.9 | -326.3 | -615.6 | -131.7 | 0.75 | -2.3 | 0.1 | -7.0 |
| XAGUSD | D1 | stoch_rev | T | 40.0 | 0.7 | -489.7 | -1031.4 | -92.4 | 0.50 | -2.3 | -4.8 | -4.2 |
| EURJPY | H4 | don_brk |  | 604.0 | 1.0 | -981.7 | -1879.1 | -207.5 | 0.25 | -2.3 | -10.5 | -7.3 |
| EURUSD | H4 | trend_vote v=6 | T | 391.0 | 1.0 | -983.0 | -2117.0 | -180.4 | 0.25 | -2.3 | -13.2 | -3.9 |
| USDCHF | D1 | trend_vote v=6 | T | 60.0 | 0.7 | -983.7 | -1487.5 | -127.2 | 0.25 | -2.3 | -11.5 | -6.1 |
| XAUUSD | H4 | bb_rev | T | 182.0 | 0.9 | -988.7 | -2131.1 | -218.1 | 0.25 | -2.3 | -18.2 | 2.1 |
| USDCHF | H4 | mfi_rev | T | 74.0 | 0.8 | -989.7 | -1255.4 | -165.3 | 0.25 | -2.3 | -15.5 | -1.3 |
| AUDJPY | D1 | aroon_x |  | 98.0 | 0.8 | -993.0 | -1581.6 | -102.0 | 0.25 | -2.3 | -16.3 | -0.3 |
| GBPJPY | D1 | ema_x |  | 53.0 | 0.8 | -499.2 | -985.1 | -114.7 | 0.50 | -2.3 | 2.4 | -13.4 |
| NZDUSD | D1 | don_rev | T | 42.0 | 0.6 | -998.5 | -1516.0 | -88.7 | 0.25 | -2.3 | -13.2 | -4.3 |
| XAGUSD | D1 | don_brk |  | 97.0 | 0.9 | -501.1 | -853.2 | -137.7 | 0.50 | -2.3 | -9.9 | 1.9 |
| NZDJPY | H4 | bb_brk | T | 384.0 | 1.0 | -1012.1 | -2249.3 | -257.8 | 0.25 | -2.3 | -11.3 | -6.8 |
| NZDUSD | D1 | obv_slope | T | 77.0 | 0.9 | -501.5 | -1045.3 | -110.2 | 0.50 | -2.3 | -2.7 | -7.0 |
| EURUSD | D1 | rsi_mom |  | 291.0 | 0.9 | -1008.0 | -2153.3 | -135.1 | 0.25 | -2.3 | -27.1 | 12.9 |
| CADJPY | H4 | trend_vote v=4 | T | 291.0 | 0.9 | -1008.4 | -1957.5 | -202.9 | 0.25 | -2.3 | -17.7 | 1.1 |
| USDCAD | D1 | don_brk | T | 73.0 | 0.8 | -1008.5 | -1748.2 | -97.2 | 0.25 | -2.3 | -7.0 | -12.3 |
| USDJPY | D1 | willr_rev | T | 63.0 | 0.7 | -1009.4 | -1758.9 | -161.3 | 0.25 | -2.3 | -23.9 | 8.9 |
| EURCHF | D1 | ha_flip |  | 390.0 | 0.9 | -1010.3 | -1717.1 | -130.8 | 0.25 | -2.3 | -10.8 | -7.6 |
| US30 | D1 | cci_mom |  | 106.0 | 0.9 | -505.3 | -1165.7 | -101.2 | 0.50 | -2.3 | -12.9 | 5.6 |
| EURJPY | D1 | obv_slope |  | 445.0 | 0.9 | -1013.3 | -2187.8 | -176.9 | 0.25 | -2.3 | -11.5 | -6.7 |
| EURGBP | D1 | obv_slope | T | 85.0 | 0.8 | -1017.8 | -1366.6 | -145.8 | 0.25 | -2.4 | -5.9 | -13.9 |
| EURJPY | D1 | kelt_brk |  | 59.0 | 0.7 | -1018.8 | -1530.0 | -175.1 | 0.25 | -2.4 | -8.0 | -11.2 |
| EURJPY | D1 | obv_slope | T | 95.0 | 0.8 | -1019.1 | -1795.4 | -176.9 | 0.25 | -2.4 | 3.7 | -25.9 |
| US500 | H4 | squeeze_brk |  | 242.0 | 0.9 | -1019.5 | -1684.0 | -196.1 | 0.25 | -2.4 | -13.1 | -4.9 |
| NZDUSD | D1 | mfi_rev | T | 4.0 | 0.5 | -128.5 | -223.7 | -68.8 | 2.00 | -2.4 | -1.6 | -0.6 |
| CHFJPY | D1 | bb_brk |  | 87.0 | 0.9 | -514.7 | -1130.8 | -125.4 | 0.50 | -2.4 | -4.7 | -4.8 |
| XAUUSD | D1 | kelt_rev | T | 12.0 | 0.7 | -171.6 | -359.2 | -79.2 | 1.50 | -2.4 | -1.8 | -1.3 |
| GBPCHF | D1 | ema_slope |  | 132.0 | 0.8 | -1030.9 | -2046.6 | -149.7 | 0.25 | -2.4 | 11.7 | -36.1 |
| DE40 | H4 | kelt_rev |  | 445.0 | 1.0 | -1031.3 | -1908.1 | -249.0 | 0.25 | -2.4 | -17.7 | 0.7 |
| CHFJPY | H4 | macd_zero | T | 229.0 | 0.9 | -1033.2 | -2178.9 | -227.9 | 0.25 | -2.4 | 3.0 | -25.2 |
| AUDUSD | H4 | mfi_rev |  | 244.0 | 0.9 | -1033.6 | -1369.1 | -188.8 | 0.25 | -2.4 | 0.4 | -22.0 |
| US500 | D1 | cci_rev | T | 48.0 | 0.9 | -344.5 | -725.9 | -230.6 | 0.75 | -2.4 | -1.5 | -5.3 |
| AUDUSD | D1 | obv_slope |  | 439.0 | 0.9 | -1036.5 | -2045.6 | -129.9 | 0.25 | -2.4 | -11.6 | -7.1 |
| CADJPY | D1 | trend_vote v=5 | T | 64.0 | 0.7 | -1036.5 | -1459.7 | -131.0 | 0.25 | -2.4 | -7.3 | -12.5 |
| USDCHF | D1 | bb_brk | T | 63.0 | 0.7 | -1044.1 | -1650.0 | -134.4 | 0.25 | -2.4 | -16.4 | -1.2 |
| USDCAD | H4 | rsi_rev | T | 48.0 | 0.9 | -348.4 | -759.2 | -164.8 | 0.75 | -2.4 | -8.2 | 3.1 |
| XAGUSD | H4 | squeeze_brk | T | 177.0 | 0.9 | -1051.4 | -1918.3 | -218.7 | 0.25 | -2.4 | -19.0 | 1.8 |
| CADJPY | D1 | trend_vote v=4 | T | 59.0 | 0.7 | -1063.4 | -1401.6 | -101.0 | 0.25 | -2.5 | -6.8 | -13.7 |
| AUDCAD | D1 | stoch_rev | T | 37.0 | 0.8 | -473.1 | -965.8 | -96.8 | 0.50 | -2.5 | -11.1 | 5.4 |
| EURJPY | D1 | cmf_zero | T | 72.0 | 0.7 | -1068.9 | -1604.5 | -140.3 | 0.25 | -2.5 | -6.2 | -14.5 |
| DE40 | H4 | macd_zero | T | 210.0 | 0.9 | -1069.5 | -1955.2 | -205.4 | 0.25 | -2.5 | 4.3 | -27.7 |
| USDJPY | H4 | kelt_rev | T | 113.0 | 0.8 | -1070.8 | -2145.5 | -157.1 | 0.25 | -2.5 | -14.0 | -4.8 |
| EURUSD | D1 | cmf_zero |  | 137.0 | 0.8 | -1071.5 | -1363.7 | -99.9 | 0.25 | -2.5 | -12.1 | -7.2 |
| USDJPY | D1 | rsi_rev |  | 53.0 | 0.8 | -536.2 | -1198.7 | -142.7 | 0.50 | -2.5 | 1.5 | -13.1 |
| CHFJPY | H4 | dmi_x | T | 193.0 | 0.9 | -1076.9 | -1974.1 | -189.8 | 0.25 | -2.5 | 1.4 | -24.2 |
| CHFJPY | D1 | mfi_rev | T | 4.0 | 0.5 | -134.6 | -242.0 | -73.6 | 2.00 | -2.5 | -1.5 | -0.9 |
| XAGUSD | H4 | bb_rev | T | 192.0 | 0.9 | -1077.5 | -2200.8 | -188.6 | 0.25 | -2.5 | -24.3 | 7.9 |
| USDCHF | D1 | bb_brk |  | 88.0 | 0.8 | -1082.6 | -1801.2 | -134.4 | 0.25 | -2.5 | -17.8 | -0.3 |
| XAUUSD | D1 | trend_vote v=5 |  | 96.0 | 0.8 | -1083.8 | -1679.4 | -122.3 | 0.25 | -2.5 | -17.7 | -0.4 |
| US30 | D1 | cci_rev |  | 128.0 | 0.8 | -1087.7 | -1232.4 | -114.3 | 0.25 | -2.5 | -13.3 | -6.1 |
| CHFJPY | D1 | ema_slope |  | 141.0 | 0.8 | -1088.0 | -1955.2 | -125.4 | 0.25 | -2.5 | -6.2 | -14.9 |
| XAUUSD | D1 | mfi_rev |  | 33.0 | 0.7 | -544.3 | -1178.8 | -141.7 | 0.50 | -2.5 | -17.3 | 10.3 |
| EURCHF | D1 | macd_x |  | 185.0 | 0.8 | -1089.4 | -1931.3 | -138.8 | 0.25 | -2.5 | -8.7 | -11.8 |
| XAGUSD | D1 | aroon_x | T | 43.0 | 0.7 | -545.3 | -880.1 | -114.5 | 0.50 | -2.5 | -0.7 | -10.5 |
| EURGBP | D1 | rsi_mom | T | 69.0 | 0.7 | -1091.5 | -1778.8 | -145.8 | 0.25 | -2.5 | -0.9 | -21.6 |
| US30 | D1 | macd_zero | T | 22.0 | 0.8 | -219.0 | -458.6 | -114.7 | 1.25 | -2.5 | -3.5 | -0.2 |
| USDCHF | D1 | ema_slope | T | 60.0 | 0.7 | -1096.9 | -1632.0 | -140.0 | 0.25 | -2.5 | -14.7 | -4.5 |
| GBPCHF | D1 | trend_vote v=6 | T | 53.0 | 0.8 | -548.6 | -1052.8 | -101.0 | 0.50 | -2.5 | 1.7 | -13.6 |
| EURGBP | D1 | ema_x | T | 27.0 | 0.9 | -183.1 | -327.5 | -100.9 | 1.50 | -2.5 | 1.3 | -5.4 |
| XAGUSD | D1 | trend_vote v=5 |  | 96.0 | 0.7 | -1101.9 | -1590.7 | -137.7 | 0.25 | -2.6 | -18.1 | -0.3 |
| EURCHF | D1 | ema_x |  | 59.0 | 0.8 | -552.8 | -943.2 | -166.6 | 0.50 | -2.6 | -13.0 | 4.7 |
| USDCAD | D1 | ema_x |  | 61.0 | 0.7 | -1110.1 | -1735.9 | -154.7 | 0.25 | -2.6 | -12.0 | -8.1 |
| EURJPY | D1 | cmf_zero |  | 143.0 | 0.8 | -1111.9 | -2259.1 | -140.3 | 0.25 | -2.6 | -9.5 | -11.2 |
| US30 | D1 | stoch_rev |  | 102.0 | 0.8 | -1117.9 | -1518.8 | -96.7 | 0.25 | -2.6 | -15.9 | -3.4 |
| EURJPY | D1 | rsi_mom |  | 288.0 | 0.8 | -1118.3 | -1653.5 | -137.3 | 0.25 | -2.6 | -6.6 | -15.0 |
| EURGBP | D1 | kelt_rev | T | 10.0 | 0.7 | -186.5 | -345.0 | -101.2 | 1.50 | -2.6 | -3.7 | 0.8 |
| AUDUSD | D1 | kelt_rev |  | 75.0 | 0.9 | -559.6 | -922.5 | -129.9 | 0.50 | -2.6 | -8.7 | -0.8 |
| USDJPY | D1 | kelt_brk | T | 51.0 | 0.8 | -560.5 | -1191.9 | -132.9 | 0.50 | -2.6 | -4.9 | -5.5 |
| GBPCHF | D1 | ema_x | T | 30.0 | 0.7 | -560.7 | -1006.9 | -90.7 | 0.50 | -2.6 | 4.1 | -16.8 |
| USDCAD | D1 | rsi_rev | T | 4.0 | 0.5 | -140.3 | -213.7 | -86.1 | 2.00 | -2.6 | 0.9 | -4.0 |
| EURGBP | D1 | don_brk | T | 71.0 | 0.7 | -1124.1 | -1701.6 | -102.5 | 0.25 | -2.6 | -1.8 | -21.1 |
| US500 | H4 | don_rev | T | 201.0 | 0.9 | -1124.7 | -1880.0 | -249.6 | 0.25 | -2.6 | -9.5 | -11.6 |
| CADJPY | D1 | macd_zero | T | 47.0 | 0.8 | -563.2 | -948.7 | -131.0 | 0.50 | -2.6 | -5.5 | -4.8 |
| NZDUSD | D1 | trend_vote v=5 | T | 51.0 | 0.8 | -564.6 | -1127.3 | -120.3 | 0.50 | -2.6 | 2.9 | -15.3 |
| NZDUSD | H4 | trend_vote v=6 |  | 491.0 | 1.0 | -1129.3 | -2263.8 | -177.5 | 0.25 | -2.6 | -9.5 | -11.6 |
| DE40 | D1 | kelt_rev | T | 12.0 | 0.7 | -225.9 | -447.9 | -84.9 | 1.25 | -2.6 | -6.2 | 3.1 |
| CADJPY | D1 | cmf_zero |  | 142.0 | 0.8 | -1130.4 | -1991.2 | -112.5 | 0.25 | -2.6 | 9.2 | -35.0 |
| CADJPY | D1 | macd_zero |  | 91.0 | 0.8 | -1130.4 | -1551.2 | -131.0 | 0.25 | -2.6 | -4.3 | -18.2 |
| XAUUSD | D1 | cmf_zero | T | 67.0 | 0.8 | -567.0 | -1126.2 | -105.0 | 0.50 | -2.6 | -3.6 | -7.4 |
| NZDUSD | D1 | macd_zero | T | 37.0 | 0.8 | -378.1 | -785.2 | -110.5 | 0.75 | -2.6 | -6.8 | 0.7 |
| EURGBP | D1 | squeeze_brk | T | 28.0 | 0.8 | -378.8 | -660.8 | -102.5 | 0.75 | -2.6 | -3.5 | -3.5 |
| EURJPY | H4 | mfi_rev |  | 237.0 | 0.9 | -1144.7 | -2035.3 | -179.7 | 0.25 | -2.6 | -20.4 | 1.7 |
| US30 | H4 | ema_slope | T | 232.0 | 0.9 | -1147.9 | -2125.7 | -300.3 | 0.25 | -2.7 | -5.3 | -17.3 |
| USDJPY | D1 | squeeze_brk | T | 31.0 | 0.5 | -1148.6 | -1310.9 | -212.8 | 0.25 | -2.7 | -6.9 | -15.3 |
| USDCHF | D1 | squeeze_brk |  | 33.0 | 0.7 | -575.5 | -856.6 | -119.3 | 0.50 | -2.7 | -4.9 | -5.9 |
| USDCAD | D1 | kelt_rev | T | 12.0 | 0.6 | -287.8 | -584.1 | -86.1 | 1.00 | -2.7 | 0.5 | -6.7 |
| CADJPY | H4 | trend_vote v=5 |  | 539.0 | 1.0 | -1155.1 | -2322.5 | -226.8 | 0.25 | -2.7 | -24.3 | 6.3 |
| EURJPY | D1 | bb_brk | T | 68.0 | 0.7 | -1156.2 | -1440.6 | -175.1 | 0.25 | -2.7 | -0.8 | -23.1 |
| XAGUSD | D1 | trend_vote v=4 | T | 56.0 | 0.8 | -578.3 | -853.1 | -102.1 | 0.50 | -2.7 | -5.5 | -5.2 |
| EURCHF | D1 | obv_slope |  | 423.0 | 0.9 | -1161.9 | -1896.1 | -113.0 | 0.25 | -2.7 | -14.0 | -6.7 |
| USTEC | H1 | cci_mom | T | 298.0 | 1.0 | -193.7 | -2298.3 | -273.8 | 0.25 | -2.7 | 0.0 | -10.8 |
| EURGBP | D1 | dmi_x |  | 79.0 | 0.8 | -582.0 | -959.9 | -111.7 | 0.50 | -2.7 | -3.8 | -7.3 |
| XAGUSD | D1 | obv_slope | T | 82.0 | 0.8 | -583.0 | -1068.0 | -123.8 | 0.50 | -2.7 | -9.8 | 0.1 |
| AUDCAD | H4 | don_rev | T | 229.0 | 0.9 | -1051.4 | -2196.0 | -201.5 | 0.25 | -2.7 | -28.1 | 18.4 |
| EURGBP | D1 | macd_zero |  | 104.0 | 0.7 | -1173.7 | -1654.1 | -145.8 | 0.25 | -2.7 | 1.6 | -26.5 |
| AUDCAD | D1 | squeeze_brk | T | 31.0 | 0.7 | -522.2 | -882.9 | -99.1 | 0.50 | -2.7 | -1.5 | -11.9 |
| NZDJPY | H4 | mfi_rev | T | 66.0 | 0.7 | -1187.9 | -2111.3 | -149.5 | 0.25 | -2.7 | -8.5 | -13.9 |
| USDCHF | D1 | rsi_mom |  | 289.0 | 0.8 | -1180.6 | -2191.5 | -124.6 | 0.25 | -2.7 | -17.8 | -2.3 |
| XAUUSD | D1 | rsi_rev | T | 4.0 | 0.4 | -148.0 | -234.7 | -60.1 | 2.00 | -2.7 | -3.0 | 0.7 |
| GBPUSD | H4 | kelt_rev | T | 105.0 | 0.8 | -1185.4 | -1970.7 | -198.4 | 0.25 | -2.7 | -22.7 | 3.7 |
| US30 | D1 | mfi_rev |  | 31.0 | 0.7 | -396.1 | -771.8 | -87.0 | 0.75 | -2.8 | -3.9 | -3.3 |
| USDCAD | D1 | obv_slope | T | 82.0 | 0.7 | -1190.4 | -1840.6 | -154.6 | 0.25 | -2.8 | -7.3 | -15.7 |
| US500 | D1 | rsi_rev | T | 7.0 | 0.6 | -198.4 | -367.1 | -106.4 | 1.50 | -2.8 | -2.4 | -1.1 |
| US30 | D1 | cmf_zero |  | 87.0 | 0.8 | -597.0 | -945.9 | -123.7 | 0.50 | -2.8 | -4.4 | -7.0 |
| GBPUSD | D1 | don_brk |  | 110.0 | 0.8 | -1195.6 | -1605.2 | -112.0 | 0.25 | -2.8 | -15.7 | -5.3 |
| AUDJPY | D1 | rsi_mom |  | 286.0 | 0.8 | -1196.6 | -1784.1 | -102.0 | 0.25 | -2.8 | -17.4 | -3.1 |
| AUDJPY | D1 | rsi_mom | T | 65.0 | 0.7 | -1219.3 | -1799.1 | -93.7 | 0.25 | -2.8 | -10.7 | -12.0 |
| EURUSD | D1 | dmi_x |  | 72.0 | 0.9 | -408.0 | -797.1 | -133.3 | 0.75 | -2.8 | -3.2 | -4.5 |
| EURUSD | H4 | ema_x | T | 165.0 | 0.9 | -1225.1 | -2182.9 | -180.7 | 0.25 | -2.8 | 1.1 | -27.0 |
| USDCAD | D1 | cmf_zero | T | 67.0 | 0.7 | -1228.9 | -1826.4 | -136.7 | 0.25 | -2.8 | 3.6 | -30.1 |
| AUDCAD | D1 | kelt_rev | T | 12.0 | 0.7 | -219.3 | -428.1 | -76.4 | 1.25 | -2.9 | 2.0 | -9.4 |
| GBPJPY | D1 | bb_rev | T | 32.0 | 0.6 | -618.2 | -1007.0 | -104.5 | 0.50 | -2.9 | -4.6 | -7.1 |
| GBPJPY | D1 | willr_rev | T | 57.0 | 0.6 | -1236.5 | -1463.0 | -105.9 | 0.25 | -2.9 | -6.2 | -18.0 |
| XAGUSD | D1 | trend_vote v=4 |  | 125.0 | 0.7 | -1236.5 | -1484.7 | -143.2 | 0.25 | -2.9 | -14.1 | -8.1 |
| GBPJPY | D1 | dmi_x | T | 28.0 | 0.6 | -620.7 | -808.9 | -88.5 | 0.50 | -2.9 | -1.9 | -10.6 |
| US500 | D1 | rsi_rev |  | 49.0 | 0.6 | -1243.7 | -1479.9 | -106.4 | 0.25 | -2.9 | -9.1 | -14.5 |
| EURGBP | D1 | cci_mom |  | 124.0 | 0.8 | -1244.8 | -2121.9 | -111.7 | 0.25 | -2.9 | 4.1 | -31.1 |
| USDJPY | D1 | kelt_rev | T | 15.0 | 0.7 | -249.0 | -449.9 | -98.0 | 1.25 | -2.9 | -1.5 | -3.3 |
| XAUUSD | H4 | macd_zero | T | 227.0 | 0.9 | -1249.9 | -2064.8 | -223.0 | 0.25 | -2.9 | -20.2 | -0.8 |
| NZDUSD | D1 | bb_brk | T | 55.0 | 0.8 | -625.7 | -803.9 | -94.7 | 0.50 | -2.9 | -6.9 | -4.4 |
| US30 | H4 | mfi_rev |  | 276.0 | 0.9 | -1252.8 | -2089.8 | -215.1 | 0.25 | -2.9 | -7.0 | -17.3 |
| AUDCAD | D1 | kelt_rev |  | 68.0 | 0.9 | -559.9 | -913.0 | -115.1 | 0.50 | -2.9 | 2.6 | -19.9 |
| US30 | D1 | dmi_x |  | 62.0 | 0.7 | -637.6 | -872.6 | -111.9 | 0.50 | -3.0 | -10.8 | 0.2 |
| EURUSD | H4 | kelt_rev | T | 116.0 | 0.8 | -1278.7 | -1534.7 | -192.9 | 0.25 | -3.0 | -0.1 | -26.5 |
| CADJPY | D1 | mfi_rev | T | 6.0 | 0.3 | -320.4 | -572.0 | -74.9 | 1.00 | -3.0 | -7.6 | 2.8 |
| NZDUSD | D1 | willr_rev | T | 71.0 | 0.8 | -641.2 | -1093.5 | -115.1 | 0.50 | -3.0 | -12.4 | 2.1 |
| EURCHF | D1 | macd_zero |  | 95.0 | 0.7 | -1289.1 | -1698.8 | -166.6 | 0.25 | -3.0 | -13.4 | -10.2 |
| NZDUSD | H4 | mfi_rev | T | 63.0 | 0.7 | -1291.6 | -1602.4 | -170.8 | 0.25 | -3.0 | -7.4 | -17.6 |
| USDCAD | D1 | ema_x | T | 32.0 | 0.7 | -646.2 | -941.8 | -154.7 | 0.50 | -3.0 | -5.5 | -6.6 |
| DE40 | D1 | mfi_rev | T | 8.0 | 0.4 | -260.1 | -458.6 | -54.9 | 1.25 | -3.0 | -5.7 | 1.7 |
| DE40 | D1 | cci_mom |  | 125.0 | 0.8 | -1309.6 | -1822.1 | -85.3 | 0.25 | -3.0 | -6.8 | -18.8 |
| USTEC | D1 | macd_zero | T | 3.0 | 0.7 | -27.4 | -120.1 | -31.0 | 2.00 | -3.0 | 0.0 | -1.5 |
| AUDJPY | H4 | trend_vote v=5 | T | 347.0 | 0.9 | -1332.2 | -1845.8 | -254.4 | 0.25 | -3.1 | -19.0 | -3.6 |
| EURUSD | D1 | don_brk |  | 101.0 | 0.8 | -1324.4 | -1912.9 | -136.0 | 0.25 | -3.1 | -15.6 | -8.1 |
| AUDUSD | D1 | cci_rev |  | 164.0 | 0.8 | -1325.0 | -2130.7 | -129.9 | 0.25 | -3.1 | -6.9 | -19.0 |
| US500 | D1 | cci_rev |  | 169.0 | 0.8 | -1327.7 | -1895.0 | -118.4 | 0.25 | -3.1 | -11.1 | -13.8 |
| USDJPY | D1 | rsi_mom |  | 272.0 | 0.8 | -1329.3 | -2047.7 | -161.3 | 0.25 | -3.1 | -11.2 | -13.6 |
| EURGBP | D1 | squeeze_brk |  | 39.0 | 0.7 | -665.0 | -951.1 | -102.5 | 0.50 | -3.1 | -3.3 | -9.8 |
| USTEC | H1 | kelt_brk | T | 237.0 | 1.0 | -221.9 | -2035.0 | -236.1 | 0.25 | -3.1 | 0.0 | -12.3 |
| GBPUSD | H4 | bb_rev | T | 212.0 | 0.9 | -1336.7 | -2273.8 | -196.0 | 0.25 | -3.1 | -23.9 | 2.1 |
| US30 | D1 | mfi_rev | T | 2.0 | 0.0 | -167.1 | -167.1 | -74.4 | 2.00 | -3.1 | -2.8 | 0.0 |
| USDCHF | H4 | rsi_rev | T | 28.0 | 0.4 | -1337.7 | -1712.5 | -165.3 | 0.25 | -3.1 | -14.2 | -10.2 |
| AUDCAD | D1 | bb_brk | T | 52.0 | 0.8 | -594.6 | -1094.1 | -99.1 | 0.50 | -3.1 | -6.0 | -6.5 |
| USDCAD | D1 | don_rev | T | 47.0 | 0.8 | -669.0 | -868.6 | -154.6 | 0.50 | -3.1 | -0.1 | -13.8 |
| CHFJPY | D1 | squeeze_brk |  | 36.0 | 0.4 | -1342.5 | -1472.1 | -118.7 | 0.25 | -3.1 | -13.8 | -10.7 |
| XAGUSD | D1 | cmf_zero | T | 58.0 | 0.8 | -671.8 | -1028.8 | -102.3 | 0.50 | -3.1 | -7.7 | -4.4 |
| USDCHF | D1 | trend_vote v=5 | T | 64.0 | 0.7 | -1345.8 | -1732.7 | -126.5 | 0.25 | -3.1 | -17.5 | -6.1 |
| CADJPY | H4 | rsi_rev | T | 41.0 | 0.7 | -675.0 | -858.5 | -200.2 | 0.50 | -3.1 | -3.5 | -9.7 |
| XAUUSD | D1 | don_rev | T | 38.0 | 0.7 | -678.0 | -1142.0 | -101.3 | 0.50 | -3.1 | -9.4 | -2.3 |
| XAGUSD | D1 | trend_vote v=6 |  | 74.0 | 0.8 | -679.0 | -1152.3 | -143.2 | 0.50 | -3.1 | -16.1 | 6.0 |
| NZDUSD | D1 | willr_rev |  | 205.0 | 0.8 | -1360.7 | -1900.7 | -183.3 | 0.25 | -3.1 | -10.3 | -15.4 |
| USDJPY | D1 | dmi_x |  | 82.0 | 0.6 | -1363.2 | -1669.3 | -161.3 | 0.25 | -3.2 | -10.7 | -15.0 |
| GBPJPY | H4 | kelt_rev | T | 105.0 | 0.8 | -1363.3 | -2196.4 | -186.0 | 0.25 | -3.2 | -11.7 | -13.8 |
| CADJPY | D1 | ha_flip | T | 102.0 | 0.8 | -1365.4 | -2079.2 | -131.0 | 0.25 | -3.2 | -9.1 | -17.1 |
| GBPUSD | D1 | cci_mom |  | 131.0 | 0.8 | -1365.4 | -2289.6 | -112.1 | 0.25 | -3.2 | -26.5 | 4.6 |
| AUDUSD | D1 | obv_slope | T | 91.0 | 0.9 | -683.4 | -1053.5 | -109.5 | 0.50 | -3.2 | -11.3 | -0.1 |
| NZDJPY | H4 | dmi_x | T | 159.0 | 0.8 | -1379.7 | -2342.7 | -236.4 | 0.25 | -3.2 | -3.9 | -23.8 |
| EURGBP | D1 | macd_zero | T | 45.0 | 0.7 | -684.0 | -1124.0 | -145.8 | 0.50 | -3.2 | -4.0 | -9.3 |
| USDJPY | D1 | bb_rev | T | 26.0 | 0.6 | -686.3 | -866.2 | -161.3 | 0.50 | -3.2 | -7.0 | -5.6 |
| USDCHF | D1 | trend_vote v=6 |  | 78.0 | 0.7 | -1372.7 | -1798.3 | -170.4 | 0.25 | -3.2 | -16.6 | -7.8 |
| DE40 | D1 | stoch_rev | T | 29.0 | 0.7 | -458.0 | -718.1 | -111.1 | 0.75 | -3.2 | -7.7 | 0.1 |
| GBPUSD | H4 | mfi_rev | T | 67.0 | 0.7 | -1377.7 | -2036.6 | -167.2 | 0.25 | -3.2 | -8.3 | -18.3 |
| CADJPY | D1 | macd_x | T | 69.0 | 0.9 | -460.0 | -717.9 | -122.7 | 0.75 | -3.2 | -6.4 | -1.5 |
| AUDJPY | H4 | dmi_x | T | 175.0 | 0.9 | -1394.9 | -2286.7 | -181.4 | 0.25 | -3.2 | -1.1 | -27.7 |
| USDCHF | D1 | aroon_x |  | 92.0 | 0.7 | -1383.4 | -1803.6 | -126.5 | 0.25 | -3.2 | -15.8 | -9.0 |
| DE40 | D1 | cci_rev | T | 49.0 | 0.8 | -463.3 | -797.5 | -131.7 | 0.75 | -3.2 | -9.5 | 2.2 |
| EURGBP | D1 | trend_vote v=6 |  | 72.0 | 0.7 | -1392.5 | -1613.0 | -101.6 | 0.25 | -3.2 | 1.3 | -30.6 |
| AUDJPY | H4 | rsi_rev | T | 38.0 | 0.8 | -468.5 | -688.2 | -154.2 | 0.75 | -3.2 | -6.0 | -2.2 |
| CHFJPY | D1 | stoch_rev |  | 131.0 | 0.8 | -1394.7 | -1749.6 | -168.1 | 0.25 | -3.2 | -12.6 | -13.3 |
| CADJPY | D1 | obv_slope | T | 87.0 | 0.7 | -1394.7 | -1814.4 | -122.9 | 0.25 | -3.2 | -7.5 | -19.6 |
| USDCAD | D1 | mfi_rev |  | 34.0 | 0.8 | -350.8 | -494.6 | -154.7 | 1.00 | -3.2 | -1.2 | -5.9 |
| USDCHF | D1 | obv_slope | T | 88.0 | 0.7 | -1405.4 | -2146.0 | -125.0 | 0.25 | -3.3 | -21.9 | -2.0 |
| US500 | D1 | rsi_mom |  | 261.0 | 0.8 | -1406.2 | -2339.0 | -164.0 | 0.25 | -3.3 | -19.0 | -5.5 |
| USDCHF | H4 | aroon_x | T | 251.0 | 0.9 | -1406.5 | -2280.3 | -214.3 | 0.25 | -3.3 | -32.7 | 11.5 |
| USDCAD | D1 | trend_vote v=6 |  | 89.0 | 0.7 | -1409.2 | -1682.3 | -117.6 | 0.25 | -3.3 | -16.1 | -9.2 |
| XAGUSD | D1 | cmf_zero |  | 104.0 | 0.8 | -705.5 | -853.0 | -102.3 | 0.50 | -3.3 | -8.4 | -4.2 |
| EURCHF | D1 | trend_vote v=6 |  | 79.0 | 0.7 | -1420.4 | -1643.8 | -180.5 | 0.25 | -3.3 | -19.4 | -5.4 |
| CADJPY | D1 | trend_vote v=4 |  | 127.0 | 0.7 | -1422.5 | -1843.9 | -112.5 | 0.25 | -3.3 | -5.3 | -23.0 |
| DE40 | D1 | kelt_brk | T | 45.0 | 0.8 | -475.3 | -642.6 | -84.4 | 0.75 | -3.3 | -5.0 | -3.7 |
| US500 | D1 | don_rev |  | 153.0 | 0.8 | -1429.6 | -2321.6 | -132.7 | 0.25 | -3.3 | -11.8 | -15.0 |
| EURJPY | D1 | rsi_rev | T | 2.0 | 0.0 | -178.9 | -242.8 | -50.1 | 2.00 | -3.3 | -1.5 | -1.9 |
| USDCHF | D1 | trend_vote v=5 |  | 103.0 | 0.7 | -1432.0 | -1956.6 | -126.5 | 0.25 | -3.3 | -14.9 | -11.3 |
| GBPUSD | H4 | ema_slope |  | 711.0 | 0.9 | -1435.4 | -2246.4 | -319.3 | 0.25 | -3.3 | -8.3 | -19.6 |
| AUDUSD | D1 | macd_x | T | 61.0 | 0.8 | -718.1 | -1039.5 | -127.7 | 0.50 | -3.3 | -8.7 | -4.0 |
| CADJPY | D1 | trend_vote v=5 |  | 105.0 | 0.7 | -1437.9 | -2020.1 | -131.0 | 0.25 | -3.3 | -17.3 | -8.4 |
| CHFJPY | H4 | rsi_rev | T | 34.0 | 0.4 | -1443.5 | -2020.2 | -368.8 | 0.25 | -3.3 | -25.2 | 1.4 |
| USDCAD | D1 | willr_rev |  | 204.0 | 0.8 | -1446.0 | -2380.3 | -154.6 | 0.25 | -3.3 | -11.3 | -16.0 |
| GBPCHF | H4 | rsi_rev | T | 49.0 | 0.5 | -1461.3 | -1592.9 | -151.3 | 0.25 | -3.4 | -24.1 | 0.2 |
| XAUUSD | H4 | trend_vote v=6 | T | 361.0 | 0.9 | -1450.6 | -2388.3 | -184.6 | 0.25 | -3.4 | -23.1 | -1.3 |
| XAGUSD | H4 | ema_x | T | 144.0 | 0.8 | -1453.1 | -1600.0 | -166.0 | 0.25 | -3.4 | -8.4 | -19.8 |
| US30 | H4 | don_rev | T | 200.0 | 0.9 | -1454.0 | -2052.6 | -215.0 | 0.25 | -3.4 | -8.1 | -20.2 |
| XAGUSD | D1 | mfi_rev | T | 9.0 | 0.5 | -242.6 | -321.6 | -81.5 | 1.50 | -3.4 | -2.1 | -2.5 |
| AUDJPY | D1 | mfi_rev | T | 3.0 | 0.0 | -291.9 | -401.2 | -94.2 | 1.25 | -3.4 | -1.6 | -4.0 |
| AUDUSD | D1 | mfi_rev | T | 5.0 | 0.4 | -244.0 | -302.8 | -66.5 | 1.50 | -3.4 | -3.2 | -1.1 |
| XAGUSD | D1 | cci_mom |  | 123.0 | 0.8 | -744.9 | -827.7 | -143.2 | 0.50 | -3.4 | -1.8 | -13.3 |
| AUDJPY | D1 | ha_flip | T | 95.0 | 0.7 | -1490.1 | -1981.4 | -104.4 | 0.25 | -3.4 | -9.8 | -18.8 |
| EURUSD | D1 | kelt_rev | T | 6.0 | 0.4 | -248.4 | -345.6 | -91.0 | 1.50 | -3.4 | -1.2 | -3.7 |
| CHFJPY | D1 | willr_rev |  | 192.0 | 0.9 | -753.4 | -1068.1 | -187.8 | 0.50 | -3.5 | -11.4 | -1.5 |
| AUDCAD | D1 | kelt_brk | T | 41.0 | 0.7 | -671.6 | -1120.3 | -131.0 | 0.50 | -3.5 | -8.2 | -4.9 |
| AUDUSD | D1 | bb_brk |  | 96.0 | 0.9 | -755.8 | -1114.5 | -111.7 | 0.50 | -3.5 | -15.7 | 3.9 |
| EURJPY | H4 | kelt_rev | T | 101.0 | 0.8 | -1512.2 | -1965.5 | -454.8 | 0.25 | -3.5 | -22.1 | -3.9 |
| XAUUSD | D1 | ema_slope | T | 46.0 | 0.7 | -756.4 | -1085.7 | -101.3 | 0.50 | -3.5 | -8.3 | -5.4 |
| USDCAD | D1 | bb_rev | T | 28.0 | 0.6 | -763.9 | -1074.8 | -154.6 | 0.50 | -3.5 | -5.1 | -9.6 |
| USDJPY | D1 | obv_slope |  | 431.0 | 0.8 | -1533.8 | -2122.8 | -124.6 | 0.25 | -3.6 | -5.3 | -25.4 |
| USDCHF | D1 | aroon_x | T | 40.0 | 0.7 | -767.1 | -1007.6 | -126.5 | 0.50 | -3.6 | -11.1 | -2.1 |
| GBPUSD | H4 | rsi_rev | T | 51.0 | 0.6 | -1535.9 | -1900.5 | -198.6 | 0.25 | -3.6 | -26.5 | 1.2 |
| XAGUSD | D1 | squeeze_brk | T | 29.0 | 0.5 | -769.2 | -956.8 | -137.7 | 0.50 | -3.6 | -11.2 | -2.1 |
| DE40 | D1 | bb_brk | T | 54.0 | 0.7 | -773.8 | -879.6 | -116.6 | 0.50 | -3.6 | -4.2 | -10.9 |
| CHFJPY | D1 | dmi_x |  | 68.0 | 0.5 | -1549.3 | -2132.6 | -116.5 | 0.25 | -3.6 | -5.1 | -25.9 |
| NZDUSD | D1 | don_brk | T | 77.0 | 0.8 | -775.5 | -950.8 | -110.5 | 0.50 | -3.6 | -5.5 | -9.2 |
| XAGUSD | D1 | ha_flip | T | 101.0 | 0.8 | -780.1 | -1172.9 | -134.6 | 0.50 | -3.6 | -6.4 | -8.3 |
| AUDJPY | H4 | ema_x |  | 269.0 | 0.9 | -1576.8 | -2200.7 | -211.2 | 0.25 | -3.6 | 3.2 | -37.0 |
| CHFJPY | D1 | don_brk |  | 98.0 | 0.7 | -1563.5 | -2279.2 | -125.4 | 0.25 | -3.6 | -15.8 | -12.8 |
| AUDUSD | D1 | cmf_zero |  | 137.0 | 0.8 | -1566.3 | -1980.4 | -127.6 | 0.25 | -3.6 | -5.9 | -25.3 |
| AUDUSD | H4 | dmi_x | T | 162.0 | 0.8 | -1569.2 | -1730.7 | -183.3 | 0.25 | -3.6 | -5.7 | -25.5 |
| EURGBP | D1 | aroon_x | T | 44.0 | 0.5 | -1569.3 | -1908.2 | -129.2 | 0.25 | -3.6 | -7.6 | -23.2 |
| AUDJPY | H4 | ema_x | T | 147.0 | 0.8 | -1598.0 | -2055.5 | -183.3 | 0.25 | -3.7 | -8.3 | -22.8 |
| XAUUSD | H4 | mfi_rev | T | 57.0 | 0.6 | -1590.9 | -1847.4 | -137.9 | 0.25 | -3.7 | -17.5 | -11.3 |
| USDCAD | D1 | mfi_rev | T | 10.0 | 0.6 | -265.5 | -364.6 | -154.7 | 1.50 | -3.7 | -3.3 | -1.3 |
| DE40 | H1 | rsi_rev | T | 149.0 | 0.8 | -1597.6 | -1932.4 | -230.9 | 0.25 | -3.7 | -2.5 | -30.2 |
| EURGBP | D1 | mfi_rev | T | 6.0 | 0.3 | -321.9 | -452.3 | -101.1 | 1.25 | -3.7 | -4.7 | -0.9 |
| USDJPY | D1 | willr_rev |  | 186.0 | 0.8 | -1612.6 | -2383.9 | -129.7 | 0.25 | -3.7 | -3.3 | -29.4 |
| DE40 | D1 | macd_x | T | 72.0 | 0.8 | -806.9 | -950.8 | -98.7 | 0.50 | -3.7 | -3.0 | -13.0 |
| XAUUSD | D1 | stoch_rev | T | 38.0 | 0.6 | -810.8 | -1185.8 | -101.3 | 0.50 | -3.8 | -10.7 | -3.5 |
| CADJPY | D1 | rsi_rev | T | 3.0 | 0.0 | -203.1 | -251.4 | -70.4 | 2.00 | -3.8 | -1.7 | -2.1 |
| CHFJPY | D1 | squeeze_brk | T | 22.0 | 0.5 | -815.1 | -1062.3 | -118.7 | 0.50 | -3.8 | -11.3 | -2.8 |
| AUDUSD | D1 | dmi_x | T | 21.0 | 0.6 | -544.2 | -681.4 | -80.4 | 0.75 | -3.8 | -0.7 | -10.5 |
| GBPCHF | D1 | ema_x |  | 58.0 | 0.5 | -1639.9 | -1818.0 | -138.5 | 0.25 | -3.8 | -3.0 | -30.4 |
| CADJPY | D1 | obv_slope |  | 433.0 | 0.8 | -1645.2 | -1953.1 | -108.9 | 0.25 | -3.8 | -11.8 | -19.5 |
| DE40 | D1 | mfi_rev |  | 34.0 | 0.7 | -550.9 | -626.8 | -80.4 | 0.75 | -3.8 | -7.0 | -2.8 |
| EURGBP | H4 | rsi_rev | T | 41.0 | 0.4 | -1656.4 | -1667.0 | -195.4 | 0.25 | -3.8 | -17.9 | -12.2 |
| USDCHF | H4 | rsi_rev |  | 328.0 | 0.9 | -1660.4 | -2285.5 | -218.5 | 0.25 | -3.8 | -24.1 | -4.5 |
| GBPCHF | D1 | trend_vote v=6 |  | 76.0 | 0.6 | -1660.9 | -1990.4 | -101.0 | 0.25 | -3.8 | -3.7 | -30.0 |
| NZDUSD | D1 | rsi_rev | T | 5.0 | 0.4 | -208.0 | -288.9 | -88.6 | 2.00 | -3.9 | -2.1 | -1.7 |
| CADJPY | D1 | rsi_mom |  | 300.0 | 0.8 | -1666.6 | -2286.6 | -128.6 | 0.25 | -3.9 | -16.1 | -14.6 |
| CHFJPY | D1 | ha_flip |  | 389.0 | 0.8 | -1669.5 | -2267.2 | -159.9 | 0.25 | -3.9 | -22.2 | -7.0 |
| EURGBP | D1 | trend_vote v=5 |  | 103.0 | 0.7 | -1673.8 | -2136.8 | -145.8 | 0.25 | -3.9 | 7.7 | -44.5 |
| XAGUSD | D1 | kelt_brk |  | 58.0 | 0.8 | -558.9 | -633.5 | -134.3 | 0.75 | -3.9 | -5.1 | -5.3 |
| GBPJPY | D1 | rsi_rev | T | 6.0 | 0.3 | -285.3 | -351.6 | -94.5 | 1.50 | -4.0 | -3.3 | -1.8 |
| GBPJPY | D1 | don_rev | T | 37.0 | 0.7 | -572.5 | -789.8 | -114.4 | 0.75 | -4.0 | -2.1 | -9.3 |
| USDCHF | D1 | don_brk |  | 100.0 | 0.7 | -1725.2 | -2303.5 | -150.4 | 0.25 | -4.0 | -21.4 | -9.2 |
| EURJPY | D1 | don_brk |  | 99.0 | 0.7 | -1727.1 | -2203.2 | -149.1 | 0.25 | -4.0 | -14.7 | -17.6 |
| USDCAD | D1 | cci_rev | T | 52.0 | 0.8 | -432.0 | -592.1 | -154.6 | 1.00 | -4.0 | -2.9 | -5.4 |
| USDCAD | D1 | willr_rev | T | 64.0 | 0.8 | -865.4 | -1039.4 | -154.6 | 0.50 | -4.0 | -7.3 | -8.9 |
| NZDUSD | D1 | obv_slope |  | 382.0 | 0.8 | -1766.9 | -2027.8 | -113.2 | 0.25 | -4.1 | -23.2 | -7.8 |
| CADJPY | D1 | bb_brk |  | 104.0 | 0.7 | -1773.6 | -2241.1 | -113.8 | 0.25 | -4.1 | -18.9 | -13.3 |
| USDJPY | D1 | rsi_rev | T | 9.0 | 0.2 | -591.4 | -749.8 | -98.0 | 0.75 | -4.1 | -2.8 | -8.8 |
| XAGUSD | D1 | aroon_x |  | 95.0 | 0.8 | -598.0 | -795.3 | -114.5 | 0.75 | -4.2 | -4.7 | -6.6 |
| EURGBP | H4 | trend_vote v=4 | T | 302.0 | 0.9 | -1796.4 | -2385.0 | -259.4 | 0.25 | -4.2 | -16.0 | -17.5 |
| XAGUSD | H4 | ema_x |  | 281.0 | 0.9 | -1798.6 | -2247.2 | -166.0 | 0.25 | -4.2 | -17.1 | -16.1 |
| CHFJPY | D1 | rsi_mom |  | 299.0 | 0.7 | -1810.9 | -2217.2 | -162.9 | 0.25 | -4.2 | -10.3 | -24.9 |
| CADJPY | D1 | dmi_x | T | 31.0 | 0.7 | -608.6 | -763.3 | -101.0 | 0.75 | -4.2 | -4.2 | -7.5 |
| USDCHF | D1 | squeeze_brk | T | 27.0 | 0.5 | -920.8 | -1096.9 | -119.3 | 0.50 | -4.3 | -10.0 | -6.6 |
| EURGBP | H4 | don_rev | T | 230.0 | 0.9 | -1844.2 | -1972.6 | -207.8 | 0.25 | -4.3 | -23.7 | -8.8 |
| XAGUSD | H4 | mfi_rev | T | 51.0 | 0.4 | -1849.1 | -2153.9 | -147.3 | 0.25 | -4.3 | -18.4 | -15.5 |
| USDCHF | D1 | mfi_rev | T | 9.0 | 0.4 | -377.8 | -456.6 | -72.9 | 1.25 | -4.4 | -3.7 | -3.2 |
| USTEC | D1 | ema_x |  | 11.0 | 0.9 | -39.6 | -240.9 | -60.1 | 2.00 | -4.4 | 0.0 | -2.2 |
| AUDCAD | D1 | cci_rev |  | 147.0 | 0.7 | -1697.0 | -2079.2 | -94.9 | 0.25 | -4.4 | -18.4 | -16.5 |
| AUDUSD | D1 | rsi_mom | T | 65.0 | 0.7 | -954.9 | -1164.2 | -109.5 | 0.50 | -4.4 | -3.2 | -15.9 |
| EURUSD | H4 | squeeze_brk | T | 216.0 | 0.8 | -1922.7 | -2196.6 | -208.3 | 0.25 | -4.5 | -30.5 | -2.0 |
| EURJPY | D1 | kelt_brk | T | 44.0 | 0.7 | -962.1 | -1021.4 | -175.1 | 0.50 | -4.5 | -6.9 | -11.4 |
| EURJPY | D1 | bb_brk |  | 99.0 | 0.7 | -1934.9 | -2384.9 | -149.1 | 0.25 | -4.5 | -9.5 | -28.5 |
| NZDUSD | D1 | rsi_rev |  | 57.0 | 0.5 | -1935.8 | -2013.2 | -154.5 | 0.25 | -4.5 | -20.2 | -15.0 |
| CADJPY | H4 | dmi_x | T | 164.0 | 0.8 | -1936.4 | -2253.1 | -186.3 | 0.25 | -4.5 | -21.6 | -13.4 |
| NZDUSD | D1 | bb_rev | T | 27.0 | 0.6 | -647.6 | -706.7 | -110.2 | 0.75 | -4.5 | -7.8 | -3.8 |
| USDCHF | D1 | trend_vote v=4 | T | 67.0 | 0.5 | -1944.3 | -2146.9 | -156.3 | 0.25 | -4.5 | -24.5 | -9.8 |
| XAUUSD | H4 | cci_rev | T | 310.0 | 0.9 | -1963.1 | -2054.3 | -196.0 | 0.25 | -4.5 | -26.2 | -8.2 |
| AUDCAD | H4 | ema_x | T | 136.0 | 0.8 | -1780.9 | -2072.3 | -187.0 | 0.25 | -4.6 | -20.7 | -14.4 |
| DE40 | D1 | dmi_x |  | 78.0 | 0.8 | -662.2 | -689.2 | -107.1 | 0.75 | -4.6 | -4.1 | -8.6 |
| USTEC | H4 | obv_slope | T | 80.0 | 1.0 | -168.6 | -1137.2 | -186.7 | 0.50 | -4.7 | 0.0 | -9.4 |
| EURGBP | D1 | aroon_x |  | 99.0 | 0.6 | -2046.8 | -2200.2 | -129.2 | 0.25 | -4.7 | -3.5 | -38.2 |
| USTEC | H1 | ema_x |  | 161.0 | 1.0 | -341.9 | -1448.7 | -384.9 | 0.25 | -4.7 | 0.0 | -19.0 |
| AUDCAD | D1 | obv_slope |  | 406.0 | 0.8 | -1833.4 | -2114.9 | -118.7 | 0.25 | -4.8 | -33.7 | 5.2 |
| USDCHF | D1 | macd_zero | T | 55.0 | 0.4 | -2105.8 | -2315.2 | -156.3 | 0.25 | -4.9 | -20.1 | -18.7 |
| XAUUSD | H4 | don_rev | T | 234.0 | 0.8 | -2121.8 | -2249.1 | -196.0 | 0.25 | -4.9 | -21.3 | -17.6 |
| XAGUSD | H4 | dmi_x | T | 187.0 | 0.8 | -2139.7 | -2174.9 | -168.9 | 0.25 | -5.0 | -26.4 | -11.5 |
| DE40 | D1 | rsi_rev | T | 3.0 | 0.0 | -278.5 | -289.2 | -88.5 | 2.00 | -5.2 | -3.0 | -2.0 |
| USTEC | D1 | rsi_mom | T | 6.0 | 0.8 | -46.7 | -255.5 | -52.9 | 2.00 | -5.2 | 0.0 | -2.6 |
| USTEC | H1 | obv_slope | T | 338.0 | 1.0 | -382.3 | -2368.5 | -295.5 | 0.25 | -5.3 | 0.0 | -21.2 |
| USTEC | D1 | aroon_x |  | 10.0 | 0.9 | -69.6 | -383.2 | -78.0 | 1.50 | -5.8 | 0.0 | -3.9 |
| USTEC | H1 | dmi_x |  | 326.0 | 1.0 | -489.0 | -2059.0 | -336.6 | 0.25 | -6.8 | 0.0 | -27.2 |
| USTEC | H1 | ema_x | T | 78.0 | 0.9 | -565.0 | -1482.4 | -278.8 | 0.25 | -7.8 | 0.0 | -31.4 |
| USTEC | H1 | willr_rev | T | 278.0 | 1.0 | -591.3 | -2116.5 | -368.8 | 0.25 | -8.2 | 0.0 | -32.8 |
| USTEC | H4 | bb_brk |  | 103.0 | 0.9 | -593.1 | -1805.5 | -169.7 | 0.25 | -8.2 | 0.0 | -32.9 |
| USTEC | H4 | macd_x | T | 70.0 | 0.9 | -304.3 | -1099.6 | -184.0 | 0.50 | -8.5 | 0.0 | -16.9 |
| USTEC | D1 | macd_zero |  | 15.0 | 0.8 | -102.1 | -376.0 | -78.0 | 1.50 | -8.5 | 0.0 | -5.7 |
| USTEC | D1 | ema_slope | T | 4.0 | 0.5 | -78.4 | -163.2 | -50.4 | 2.00 | -8.7 | 0.0 | -4.4 |
| USTEC | H1 | bb_rev |  | 464.0 | 1.0 | -640.8 | -2018.6 | -376.9 | 0.25 | -8.9 | 0.0 | -35.6 |
| USTEC | H1 | kelt_brk |  | 304.0 | 1.0 | -693.8 | -2057.7 | -322.1 | 0.25 | -9.6 | 0.0 | -38.5 |
| USTEC | D1 | obv_slope |  | 67.0 | 0.9 | -116.3 | -371.2 | -83.4 | 1.50 | -9.7 | 0.0 | -6.5 |
| USTEC | H1 | kelt_rev | T | 76.0 | 0.9 | -350.7 | -947.0 | -202.0 | 0.50 | -9.7 | 0.0 | -19.5 |
| USTEC | D1 | stoch_rev |  | 28.0 | 0.9 | -142.8 | -434.2 | -105.9 | 1.25 | -9.9 | 0.0 | -7.9 |
| USTEC | D1 | mfi_rev |  | 1.0 | 0.0 | -93.9 | -118.7 | -51.0 | 2.00 | -10.4 | 0.0 | -5.2 |
| USTEC | H4 | squeeze_brk | T | 41.0 | 0.8 | -376.6 | -975.6 | -179.4 | 0.50 | -10.5 | 0.0 | -20.9 |
| USTEC | H1 | bb_brk | T | 265.0 | 0.9 | -826.7 | -2380.9 | -255.7 | 0.25 | -11.5 | 0.0 | -45.9 |
| USTEC | H4 | rsi_rev | T | 7.0 | 0.6 | -166.1 | -421.0 | -187.0 | 1.25 | -11.5 | 0.0 | -9.2 |
| USTEC | D1 | stoch_rev | T | 3.0 | 0.4 | -112.0 | -225.1 | -105.9 | 2.00 | -12.4 | 0.0 | -6.2 |
| USTEC | H1 | cci_rev | T | 196.0 | 0.9 | -1009.6 | -2343.7 | -300.8 | 0.25 | -14.0 | 0.0 | -56.1 |
| USTEC | D1 | willr_rev |  | 31.0 | 0.7 | -339.4 | -620.7 | -105.9 | 0.75 | -14.1 | 0.0 | -18.9 |
| USTEC | D1 | cci_rev |  | 29.0 | 0.7 | -339.8 | -631.4 | -105.9 | 0.75 | -14.2 | 0.0 | -18.9 |
| USTEC | H1 | bb_rev | T | 145.0 | 0.9 | -1088.7 | -1984.8 | -270.0 | 0.25 | -15.1 | 0.0 | -60.5 |
| USTEC | H4 | kelt_rev |  | 108.0 | 0.8 | -1089.0 | -1307.7 | -166.9 | 0.25 | -15.1 | 0.0 | -60.5 |
| USTEC | D1 | bb_rev |  | 16.0 | 0.8 | -138.1 | -248.5 | -105.9 | 2.00 | -15.3 | 0.0 | -7.7 |
| USTEC | D1 | don_rev |  | 25.0 | 0.7 | -278.9 | -494.6 | -105.9 | 1.00 | -15.5 | 0.0 | -15.5 |
| USTEC | H4 | ema_slope | T | 47.0 | 0.8 | -559.5 | -957.4 | -219.8 | 0.50 | -15.5 | 0.0 | -31.1 |
| USTEC | D1 | ema_slope |  | 20.0 | 0.7 | -186.6 | -392.8 | -78.0 | 1.50 | -15.6 | 0.0 | -10.4 |
| USTEC | D1 | rsi_rev |  | 8.0 | 0.5 | -237.3 | -440.6 | -61.4 | 1.25 | -16.5 | 0.0 | -13.2 |
| USTEC | D1 | willr_rev | T | 4.0 | 0.3 | -163.7 | -278.0 | -105.9 | 2.00 | -18.2 | 0.0 | -9.1 |
| USTEC | H1 | rsi_rev | T | 37.0 | 0.7 | -691.2 | -1130.3 | -206.9 | 0.50 | -19.2 | 0.0 | -38.4 |
| USTEC | D1 | kelt_rev |  | 17.0 | 0.5 | -482.9 | -668.7 | -105.9 | 0.75 | -20.1 | 0.0 | -26.8 |
| USTEC | H4 | rsi_rev |  | 72.0 | 0.8 | -730.3 | -1015.1 | -188.4 | 0.50 | -20.3 | 0.0 | -40.6 |
| USTEC | D1 | cmf_zero |  | 22.0 | 0.4 | -569.1 | -797.1 | -83.4 | 0.75 | -23.7 | 0.0 | -31.6 |
| USTEC | H4 | squeeze_brk |  | 53.0 | 0.7 | -927.3 | -1158.9 | -150.4 | 0.50 | -25.8 | 0.0 | -51.5 |

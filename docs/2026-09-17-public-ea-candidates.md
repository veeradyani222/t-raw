# Public MT5 EA candidates — source review, 17 September 2026

These are transparent research candidates, not verified profitable trading options. No downloaded third-party program was executed during this review. The parent task reported that automatic policy rejected downloading/installing source into the workspace; this review continued with read-only source inspection. Native installation or execution must not be claimed.

## 1. Adjustable MA 1.08

The author describes a two-moving-average crossover EA and explicitly reports poor default results and no consistently profitable parameter combination. Its value here is as a reproducible trend-following comparator. [Author description](https://www.earnforex.com/metatrader-expert-advisors/Adjustable-MA/).

Pinned revision: `45dc52ac6495351c5fb715d128b929597921de7b`. Defaults in the actual MT5 source: EMA 20/22, close price; minimum separation **3 points**; fixed 0.1 lot; money management disabled; SL, TP and trailing disabled; both directions; all times/days. Source defaults differ from the website's 30-point description. Initialize remembered direction by scanning backward from candle 2 until a separation of at least 3 points is found. On each new bar, inspect completed candle 1: reverse only when its separation reaches the opposite threshold. This is a persistent direction state with a neutral band, not simply a cross between the two latest candles. Standard Trade include; no external DLL import or WebRequest appears in the reviewed EA file. [Pinned source](https://raw.githubusercontent.com/EarnForex/Adjustable-MA/45dc52ac6495351c5fb715d128b929597921de7b/Adjustable_MA.mq5).

[Apache-2.0 license](https://github.com/EarnForex/Adjustable-MA/blob/45dc52ac6495351c5fb715d128b929597921de7b/LICENSE). The website reports EURUSD M5 testing, so an H1 replay must be identified as a timeframe change.

## 2. RSI EA

The author presents this as an unoptimized proof of concept likely to lose money. Its own EURUSD M5 three-year example reports $453 profit and $1,211 maximum drawdown at 0.1 lot. These are publisher backtest figures, not a verified live record. [Author description](https://www.earnforex.com/metatrader-expert-advisors/rsi-expert-advisor/).

Pinned revision: `6d8c37e74d352587cd1f6f185496c9c949c1caf0`. Defaults: built-in RSI14 on closes; buy when completed RSI rises above 20 after being at/below 20; sell when it falls below 80 after being at/above 80. Opposite signals close positions before entry processing. Fixed 0.1 lot, maximum one position, no SL/TP, maximum spread 50 points, unrestricted hours. Entry processing permits the first two ticks of a new candle to accommodate indicator refresh; indicator signals use completed candles 1 and 2. The source includes Trade plus two repository helper files: `MQLTA ErrorHandling.mqh` and `MQLTA Utils.mqh`. No external DLL import or WebRequest appears in the main EA; dependency audit is not complete. [Pinned source](https://raw.githubusercontent.com/EarnForex/RSI-EA/6d8c37e74d352587cd1f6f185496c9c949c1caf0/Experts/RSI%20EA.mq5).

[Apache-2.0 license](https://github.com/EarnForex/RSI-EA/blob/6d8c37e74d352587cd1f6f185496c9c949c1caf0/LICENSE). Exact indicator-seed parity should be checked against the installed MetaQuotes RSI example before claiming native-equivalent results.

## 3. Heiken Ashi Naive 1.03, normal version

The author reports EURUSD D1 testing from 2013-01-01 to 2022-04-13: $2,920.31 profit on $10,000 at fixed 0.1 lot, with 18% relative drawdown. This is a publisher backtest, not independently verified performance. The normal version avoids the separate Z-score trade-skipping variant. The author warns that MT5 trades can interfere with other EAs on the same symbol. [Author description](https://www.earnforex.com/metatrader-expert-advisors/Heiken-Ashi-Naive/).

Pinned revision: `56ecbe6d82ea938c9e4a1a87ef3b10e4b8a2937c`. Defaults: inverted signals enabled, fixed 0.1 lot, money management disabled, no SL or TP. Sell when two completed HA candles are bullish, latest body grows, and latest has no lower wick. Buy on the bearish mirror. Close a long on two bullish candles with latest no lower wick; close a short on the bearish mirror. Exit conditions do not require body growth. Same-direction signals do not add positions. The new-bar throttle is commented out, although signals use completed candles. Its ATR-based sizing option does **not** create a stop; ATR is only a hypothetical risk distance. Dependencies are standard Trade/PositionInfo and `Examples\\Heiken_Ashi`. No DLL import or WebRequest appears in the reviewed EA. [Pinned source](https://raw.githubusercontent.com/EarnForex/Heiken-Ashi-Naive/56ecbe6d82ea938c9e4a1a87ef3b10e4b8a2937c/HAN.mq5).

[Apache-2.0 license](https://github.com/EarnForex/Heiken-Ashi-Naive/blob/56ecbe6d82ea938c9e4a1a87ef3b10e4b8a2937c/LICENSE). The author's HA formulas seed the first candle with original OHLC, then recursively average prior HA open/close for the next HA open and average current OHLC for HA close. Backtest fills must use actual prices, never synthetic HA prices. [HA calculation rules](https://www.earnforex.com/metatrader-expert-advisors/Heiken-Ashi-Naive/).

## Scope and interpretation

None of these default strategies uses martingale or grid position escalation in its reviewed main source. That is a source observation, not proof of profitability or a complete security certification. All three lack a default protective stop, so fixed-lot default replays cannot honestly be called 1%-risk trades. Adding ATR stops or account loss halts creates a modified strategy and should be reported separately. A local Python replay can test the disclosed rules with costs; it is not an installed EA or a native MT5 Strategy Tester run.

Spike Trader was also considered: its author gives a USD/CAD D1 reversal rule with an 11-bar hold and no SL/TP. The available local datasets did not include USD/CAD, so it was not selected for the immediate comparison. [Author description](https://www.earnforex.com/metatrader-expert-advisors/Spike-Trader/).

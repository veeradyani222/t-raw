# Public use and opinions on clock-based FX strategies

Researched 2026-09-13. Scope: the project's CHFJPY/EURJPY long H1 strategy, entry after completion of the hour-0 bar (approximately 01:00 on that data clock), a 12-hour elapsed-time exit and a 2-ATR stop. This note compares public descriptions; it does not validate returns or change trading code.

## Finding

There is firsthand public evidence of traders using the **same general architecture: session/time-of-day entries and timed exits**. This bounded search did not find an independently verified public track record for the exact CHFJPY/EURJPY hour-0, 12-hour, 2-ATR configuration. The broader strategy family has precedent; exact rules and profitability remain separate questions.

## Closest public precedents

1. **Practitioner reports actually running systematic session trades.** In Spectra Markets' April 24, 2025 article, the author says they intermittently ran a strategy during 2009–2017 that bought EURUSD during New York afternoon/Asia, switched short at the European open and went flat during the New York/London overlap; another leg shorted USDJPY in Asia and bought it during New York. This is a close architectural precedent for exploiting direction by clock/session, but uses other pairs, directions and windows. The article's P&L is self-reported, not independently audited. It also discusses transaction-cost/capacity limits and a historical reversal in USDJPY's time-of-day pattern. [Spectra Markets: TOD Flipper and Supply Pains](https://www.spectramarkets.com/amfx/tod-flipper-and-supply-pains/).

2. **Clock-only entry and exit explicitly requested.** A Forex Factory trader on July 29, 2012 requested an EA that would enter at market at a specified time and close at another specified time, giving 10:15 long entry and 14:45 exit as examples. This matches the scheduling architecture more closely than a session breakout, but demonstrates a public implementation request, not verified trading or returns. [Forex Factory: Time Based Entry and Exit EA](https://www.forexfactory.com/thread/post/9709897).

3. **Trader reports an entry window plus timed exit.** A March 18, 2026 Reddit reply says: “I have one window for entry and a time exit if target or stop not hit.” This is firsthand self-reported use; the instrument, exact hours, selection rules and independent performance evidence are unspecified. [r/algotrading discussion](https://www.reddit.com/r/algotrading/comments/1rw2scs/the_thing_that_improved_my_strategy_wasnt_what_i/).

## What traders think

The March 2026 Reddit discussion is mixed. The original poster reports improved win rate and drawdown after restricting trading to a few windows, and several replies report similar experiences. Skeptics argue that selecting favorable start/end times after repeated backtests adds optimization choices and selection bias; others distinguish legitimate intraday seasonality from overfitting. These are useful practitioner opinions, not verified results or a representative survey. [Original discussion and replies](https://www.reddit.com/r/algotrading/comments/1rw2scs/the_thing_that_improved_my_strategy_wasnt_what_i/).

My inference: these sources support investigating a clock-based FX hypothesis, but public use cannot establish the edge of our precise configuration. A session breakout that waits for a range break is also a different entry rule and should not be presented as someone trading this exact strategy. Clock comparisons must preserve the underlying timezone and whether timestamps label bar opening or completed-bar evaluation.

## Search limits

Queries covered combinations of CHFJPY/EURJPY, intraday seasonality, time of day, 00:00/12:00, time-based entry/exit, and firsthand Forex Factory/Reddit discussions. Failure to find an exact independently verified match is a search result, not proof that nobody uses it. No code changes, backtests, account access or execution occurred in this research task.

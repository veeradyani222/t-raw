# Overlay lab: account-level rules on the live 66-strategy mix (2026-10-25)

**Short answer.** Two rules cut the bad year's loss at little cost, and one sizing fix closes a hole:

1. **Drawdown scaling**: when the account is below $9,700, trade every strategy at half size until it is back above $9,900. Costs nothing in the good two years (the account never went below $9,809). In the unseen bad year it cuts the daily-stop halts from 38 to 11 and lifts the lowest equity from $5,609 to $8,277.
2. **Monthly loss stop at -$500**: once a calendar month is down $500, no new trades until the next month. Together with rule 1 the bad year turns from -$2,620 into +$640, the lowest equity is $9,497 (above the $9,300 bot halt and the $9,200 firm rail), and the bot's permanent halt would never have fired. Cost in the good two years: $1,483 (3%, about $59 a month).
3. **Minimum stop for sizing** = max(strategy stop, 0.15 x the symbol's 20-day average daily range). Resizes 2% of trades; costs $1,579 in the good years, all of it from one DAX trade that was sized off a 9.9-point stop on a day of broken price data (see "The sizing hole").

Everything else tested (volatility targeting, equity-curve filter, Friday cutoff, event blackout, stop-the-month-after-N-halts, phase-target stop) either costs too much profit, does not help, or only looks free because of how the mix was built.

Code: `research/overlays/` (lab.py, sim.py, runs.py, test_lab.py). Numbers: `research/overlays/results.json`.

## How the lab works

- Every one of the 66 strategies is simulated exactly as the research harness does, at its live risk, starting flat at the window start. The account is the sum of the 66 curves.
- The live rule set is always on: close everything when the combined floating loss on the server day reaches $300 (the day is then pinned at -$325 including slippage) and no new trades that day. The permanent halt at $9,300 is reported separately so the overlays can still be compared over the whole window.
- An overlay gives every trade a **size factor** decided at the entry bar from what the bot would know then: 0 = skip, 0.5 = half size, 1 = as live. Because the bot sizes trades in fixed dollars, a trade's profit and its floating swings scale with that factor. Combinations multiply the factors.
- Two windows, each a fresh $10,000: **A** = 2024-10-20 to 2026-10-20 (the window the mix was sized on). **B** = 2023-10-20 to 2026-10-20 (adds the unseen year 2023-10 to 2024-10).
- The baseline reproduces the known numbers exactly before any overlay is trusted: window A net $47,845, worst day -$299, lowest equity $9,809; window B net $44,986, lowest equity $5,609, 38 halts.

## What the bad year actually does

Without the daily close-all stop, the unseen year is +$2,333 with lowest equity $9,327, but the worst day is -$673, which breaks the firm's 4% daily rule. With the stop, the unseen year is -$2,620 and the lowest equity $5,609: the account hits -$300 on 38 days and each halt locks in -$325 that the open trades would mostly have recovered. The bad year is not a year of bad trades so much as a year of **bigger daily swings** than the mix was sized for. The rules that help are the ones that make those -$300 days rarer (smaller size in drawdown) or stop the bleeding once a month has gone wrong.

Window B, baseline month by month (unseen year in bold): **-744, +1,551, +1,086, -1,972, -1,438, +331, -772, +872, -429, -1,281, -1,043, +1,157**, then +839, +1,228, +13,550, +2,848 ...

## Ranked table

Sorted by window B net (the full three years). "Cost in A" is the change versus the baseline in the good two years. "!" after the lowest equity means the $9,200 firm floor would have been breached. Worst day is -$325 everywhere because the daily stop pins every halted day there. Challenge pass = rolling two-phase FundedNext attempts started every two weeks.

| # | Overlay | Settings | A net | Cost in A | B net | Unseen year | Lowest equity (B) | Halts (B) | Challenge pass A / B |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **Baseline (live rules)** |  | $47,845 | 0 | $44,986 | -2,620 | $5,609 ! | 38 | 85% / 60% |
| 1 | Stop month after halts | after 3 halts | $47,845 | 0 | $48,274 | +668 | $9,157 ! | 30 | 85% / 59% |
| 2 | Combo | monthly stop 750 + drawdown scaling + blackout 30 | $47,347 | -498 | $47,539 | -53 | $9,117 ! | 22 | 88% / 64% |
| 3 | Combo | monthly stop 750 + drawdown scaling | $47,168 | -677 | $47,168 | -133 | $9,184 ! | 22 | 88% / 64% |
| 4 | Combo | stop month after 1 halt + drawdown scaling | $47,845 | 0 | $46,924 | +50 | $9,497 | 11 | 85% / 61% |
| 5 | Stop month after halts | after 1 halt | $47,845 | 0 | $46,645 | -229 | $9,189 ! | 12 | 85% / 63% |
| 6 | Drawdown scaling | below $9,800 half size until $9,950 | $47,845 | 0 | $46,607 | -505 | $8,327 ! | 10 | 85% / 63% |
| 7 | Combo | stop month after 2 halts + drawdown scaling | $47,845 | 0 | $46,563 | -548 | $8,284 ! | 8 | 85% / 61% |
| 8 | **Drawdown scaling** | **below $9,700 half size until $9,900** | $47,845 | 0 | $46,556 | -556 | $8,277 ! | 11 | 85% / 61% |
| 9 | Combo | stop month after 2 halts + quarter size below $9,700 | $47,845 | 0 | $46,447 | -292 | $9,124 ! | 5 | 85% / 80% |
| 10 | Drawdown scaling | below $9,500 half size until $9,800 | $47,845 | 0 | $46,416 | -729 | $8,103 ! | 11 | 85% / 61% |
| 11 | Combo | monthly stop 500 + quarter size below $9,700 | $46,362 | -1,483 | $46,288 | -162 | $9,413 | 20 | 88% / 68% |
| 12 | Stop month after halts | after 2 halts | $47,845 | 0 | $46,247 | -302 | $8,125 ! | 23 | 85% / 60% |
| 13 | Monthly loss stop | stop after -$1,000 | $46,843 | -1,002 | $46,151 | -454 | $7,735 ! | 34 | 88% / 61% |
| 14 | **Combo (recommended)** | **monthly stop 500 + drawdown scaling** | $46,362 | -1,483 | $46,031 | +640 | $9,497 | 23 | 88% / 64% |
| 15 | Drawdown scaling | below $9,700 quarter size until $9,900 | $47,845 | 0 | $45,977 | -426 | $8,990 ! | 8 | 85% / 79% |
| 16 | Monthly loss stop | stop after -$500 | $46,362 | -1,483 | $45,753 | +361 | $9,189 ! | 24 | 88% / 65% |
| 17 | Monthly loss stop | stop after -$750 | $47,168 | -677 | $45,336 | -861 | $8,283 ! | 29 | 88% / 61% |
| 18 | **Package (recommended)** | **min-stop 0.15 + monthly stop 500 + drawdown scaling** | $45,442 | -2,403 | $45,124 | +639 | $9,497 | 23 | 88% / 65% |
| 19 | Event blackout | 30 min before FOMC / NFP | $48,024 | +179 | $45,276 | -2,509 | $5,720 ! | 38 | 85% / 60% |
| 20 | Event blackout | 60 min before | $47,732 | -113 | $44,965 | -2,528 | $5,701 ! | 38 | 85% / 60% |
| 21 | Event blackout | 60 min before, 30 after | $47,396 | -449 | $44,942 | -2,215 | $5,791 ! | 36 | 88% / 64% |
| 22 | Combo | monthly stop 500 + stop month after 2 halts + drawdown scaling | $46,362 | -1,483 | $44,540 | -338 | $9,106 ! | 13 | 88% / 65% |
| 23 | Combo | monthly stop 750 + drawdown scaling + vol target 250 (down only) | $43,634 | -4,211 | $43,554 | -49 | $8,979 ! | 23 | 88% / 67% |
| 24 | Minimum sizing stop | k = 0.15 | $46,266 | -1,579 | $43,357 | -2,639 | $5,599 ! | 38 | 85% / 60% |
| 25 | Volatility targeting | $300/day, 0.5x to 1.0x | $46,160 | -1,684 | $43,317 | -2,608 | $5,609 ! | 38 | 85% / 63% |
| 26 | Combo | stop month after 2 halts + drawdown scaling + vol target 250 (down only) | $44,311 | -3,534 | $43,202 | -548 | $8,284 ! | 8 | 85% / 63% |
| 27 | Volatility targeting | $250/day, 0.5x to 1.0x | $44,311 | -3,534 | $41,722 | -2,364 | $5,608 ! | 36 | 85% / 63% |
| 28 | Equity-curve filter | pause after last 20 trades net negative | $43,015 | -4,829 | $39,865 | -992 | $6,857 ! | 30 | 92% / 65% |
| 29 | Volatility targeting | $200/day, 0.5x to 1.0x | $41,189 | -6,655 | $39,665 | -1,618 | $6,194 ! | 33 | 85% / 63% |
| 30 | Minimum sizing stop | k = 0.25 | $40,628 | -7,217 | $37,427 | -3,332 | $5,336 ! | 38 | 81% / 56% |
| 31 | Volatility targeting | $200/day, 0.5x to 1.5x | $38,180 | -9,664 | $36,429 | -1,987 | $5,570 ! | 52 | 75% / 60% |
| 32 | Volatility targeting | $250/day, 0.5x to 1.5x | $39,452 | -8,393 | $35,216 | -3,309 | $3,959 ! | 74 | 77% / 55% |
| 33 | Minimum sizing stop | k = 0.35 | $37,018 | -10,827 | $35,027 | -2,106 | $6,693 ! | 32 | 83% / 65% |
| 34 | Volatility targeting | $150/day, 0.5x to 1.5x | $35,483 | -12,362 | $33,940 | -1,431 | $6,541 ! | 32 | 85% / 65% |
| 35 | Friday cutoff | no new trades from 20:00 | $35,378 | -12,467 | $33,378 | -1,761 | $5,948 ! | 38 | 83% / 63% |
| 36 | Friday cutoff | no new trades from 18:00 | $34,177 | -13,667 | $32,262 | -1,677 | $6,206 ! | 37 | 83% / 64% |
| 37 | Equity-curve filter | pause after last 10 trades net negative | $39,084 | -8,761 | $24,293 | -814 | $7,114 ! | 27 | 89% / 70% |

The volatility-targeting rule was also run with settings of $150, $200 and $250 a day, and the drawdown scaler with a $9,500/$9,800 band and a quarter-size variant; all are in the table or in results.json.

## Why the "free" halt-count rules are not free

Window A has **zero** daily halts by construction: the optimiser that sized the mix required the worst day to stay above -$300, so it came out at -$299. Any rule that only acts after a halt therefore looks free in window A. To see its real cost I re-ran the candidates with a $250 daily stop instead, so that halts do happen in the good years (45 of them in window A):

| Rule, with a $250 daily stop | A net | B net | Unseen year | Lowest equity (B) |
|---|---|---|---|---|
| Baseline | $34,799 | $32,002 | -2,590 | $5,510 |
| Drawdown scaling (below $9,700 half size) | $34,799 | $33,758 | -888 | $7,944 |
| Monthly stop 500 + drawdown scaling | $29,400 | $28,423 | -824 | $8,004 |
| Stop month after 2 halts + quarter size below $9,700 | $18,340 | $16,689 | -307 | $9,084 |
| Stop month after 1 halt + drawdown scaling | $6,886 | $7,242 | -285 | $9,261 |
| Stop month after 1 halt | $6,886 | $3,923 | -1,856 | $7,490 |

So: the drawdown scaler stays free and still helps; the monthly stop costs about 15% when halts are common; the halt-count rules throw away most of the profit. Rows 1, 4, 5, 7, 9, 12 and 22 in the table above are rejected on this evidence. (The same table also shows that a tighter daily stop itself costs $13,000 over two years; Veer has already rejected tightening it.)

## The sizing hole

A trade's lot size comes from its stop distance, so a tiny stop means a huge position. The DAX turn-of-month trade on 2024-11-29 had a 9.9-point stop (its usual stop is 150 to 300 points) and was given 11.8 lots; it made +$11,231, **23% of the whole two-year profit**. Without that one trade window A nets about $36,600, or $1,465 a month instead of $1,914.

Why the stop was tiny: the index price files in `data/search` contain **flat days** where the whole day's high-low is a few points (stale bars). Since 2023-10: DE40 25 such days, US30 9, US500 8, USTEC 8, almost all between 2024-10 and 2025-01 (2024-11-29 is one of them). A strategy whose stop is an ATR multiple sees a near-zero ATR on those days. The live bot pulls real broker bars and will never see that stop or that profit; the $11,231 should be treated as a data artefact, not an edge. Trades entered on flat days total +$11,360 in window A, of which $11,231 is this one trade; the other 25 such trades net +$129.

The fix tested: size from max(strategy stop, k x 20-day average daily range), stop itself unchanged.

| k | A net | Cost in A | Trades resized (A) | Lowest equity (A) | B net | Trades resized (B) | Lowest equity (B) |
|---|---|---|---|---|---|---|---|
| 0 (live) | $47,845 | 0 | 0 of 4,139 | $9,809 | $44,986 | 0 of 7,189 | $5,609 |
| 0.15 | $46,266 | -1,579 | 85 (2%) | $9,814 | $43,357 | 121 | $5,599 |
| 0.25 | $40,628 | -7,217 | 532 (13%) | $9,819 | $37,427 | 926 | $5,336 |
| 0.35 | $37,018 | -10,827 | 1,307 (32%) | $9,838 | $35,027 | 2,318 | $6,693 |

At k = 0.15 the whole cost is the DAX trade (11.8 to 10.1 lots, -$1,618; the other 84 resized trades net +$39). It only trims that trade because the 20-day average range is itself dragged down by the flat days (77 points instead of about 240); on real broker data the same rule would have sized it at roughly 3 lots. Most resized trades are the XAUUSD M30 break-of-structure, the DAX M30 Crabel and the US30 H1 RSI strategies. k = 0.25 and 0.35 hit normal trades and cost 15% to 23%; not worth it.

## Phase-target stop (rule g)

"Once a fresh account is up 8%, stop until phase 1 ends; then 4% in phase 2." The challenge judge already declares a phase passed at the moment the target is hit, which is exactly what this rule does, so it cannot change the pass rate in the replay. The only measurable comparison is against the stricter reading where the target must still hold at the end of that server day:

| Window | Pass as soon as hit (rule g) | Must hold at day end (keep trading) |
|---|---|---|
| A | 41 of 48 pass (85%), median 18.5 days | 44 of 48 (92%), median 22.5 days |
| B | 45 of 75 (60%), median 20.5 days | 50 of 75 (67%), median 25.0 days |

Trading on through the day did not hurt in this data; the differences are within the noise of where phase 2 starts. Rule g has no profit case; its value is operational (lock in a pass the moment it is there), which costs nothing on a funded account because it only applies during the challenge.

## Recommendation for the bot

Put these in, in this order of importance:

1. **Drawdown scaling** below $9,700: every new trade at half size until equity (including floating) is back above $9,900. Free in the good years; the cheapest insurance found.
2. **Monthly loss stop** at -$500 (month-to-date P&L including floating, measured from the last close of the previous month): no new entries until the next month, open trades run to their own exits. Costs $1,483 over the good two years (3%); about 15% in a year with many halts. This is the rule that keeps the bad year above the firm floor.
3. **Minimum sizing stop** at 0.15 x the symbol's 20-day average daily range, from real broker bars. Costs $1,579 in the backtest, all of it the broken-data DAX trade. It caps the gap risk of any tiny-stop trade at roughly the same dollar risk as a normal one.

Together (row 18): window A $45,442 instead of $47,845 (-5%, of which $1,600 is the data artefact), 84% green months unchanged, challenge pass 88% instead of 85%; window B unseen year +$639 instead of -$2,620, lowest equity $9,497 instead of $5,609, halts 23 instead of 38, permanent halt never fires.

Optional: a 30-minute no-entry blackout before FOMC and NFP is noise-level (+$179 in A, +$290 in B); fine to add for peace of mind, not needed.

Do not add: Friday cutoff (-26% in A, Friday-evening entries are among the best), equity-curve filters (-10% to -18%), volatility targeting (any setting costs 4% to 26% and does not protect the floor), stop-the-month-after-N-halts rules (see the stress test).

## Caveats

- One bad year is one sample. The rules were chosen by looking at it, so their bad-year benefit is in-sample; the good-year cost is the more trustworthy number.
- A force-closed trade is removed, not replaced by whatever the strategy would have done next; same approximation as the sizing session's replay.
- FOMC times are 21:00 server, NFP first Friday 15:30 server; a few rescheduled releases are missed.
- Window A's headline profit depends heavily on one artefact trade; expect the live mix to run nearer $1,450 than $1,900 a month in a year like 2025.

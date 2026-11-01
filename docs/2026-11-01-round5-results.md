# Strategy search, round 5 results (2026-11-01)

Written for Veer. Plain language. The question for round 5 was: are there strategies that make MORE money
per month and keep making it in any market, judged on data they were not picked on, to add to (or replace
parts of) the live 23 on the FundedNext $5K account?

Short answer: **no.** Every idea in the brief was tested; none produced an honest edge worth more than
about $130 a month on the $5K account. The one useful product is a "steady" mix of 33 strategies that
never failed a challenge start in the unseen year (the live 23 failed 9 of 24 starts in that year and
touched $4,601, one dollar above the floor). It makes about the same per month as the live 23 did in
that year, and far less than the live 23 did on the two years the live 23 was picked on.

Code: `research/search5/` (`core5.py` judge and cache, `screen.py`, `session_scan.py`, `vol_filter.py`,
`build_mix.py`, `report.py`). Mix files: `docs/board/portfolio-round5-honest.json` (the proposal),
`-strict.json`, `-live23-adds.json`, `-pruned-adds.json`. The live file was not touched.
All tables: `docs/2026-11-01-round5-tables.md`; per-strategy screen: `research/search5/out/screen.md`.

## How the judging was done (the honest test)

- Every known strategy (the round-3 pool of 146 = the live 66 + 80 round-3 candidates, plus the 16
  round-4 price-action survivors, plus 2 time-of-day holds) was simulated once at 1% of $10K per trade
  over all the data we have, 2015-01-01 to 2026-10-31, with the round-3 judge (same costs, same cleaners).
- **dev** = 2015-01-01 to 2023-10-20. Every pick and every size in this round was decided on dev only.
- **unseen yr** = 2023-10-20 to 2024-10-20. **last 2y** = 2024-10-20 to 2026-10-31: this is the window the
  round-3 pool and the 66 were SEARCHED on, so for those strategies it is a fit period and its numbers are
  flattered. **Sep+Oct** = 2026-09-01 to 10-31, the live months.
- Accounts: $5K (risk fractions in the mix files are for $10K, so x0.5; daily close-all at -$125 with $12.5
  slippage; floor -$400; a challenge start every 14 days fails at -$400 before +$400) and $10K (x1.0,
  -$300/$25, -$800 before +$800). "stops" = days the close-all fired. "low" = lowest balance in the period.
- Markets with data only from 2022 or 2025 (EURUSD, USTEC, AUS200, SOL, XRP, exotics) cannot be judged on
  long history. Strategies needing a second market's bars (Brent/WTI spread, gold/silver ratio) cannot run
  live and were excluded from every new mix.

## The live 23 on long history

At 1% each, no account stop, the 24 (23 tradable) sum to:

| period | $/month at 1% each ($10K) |
|---|---|
| dev 2015-2023 | **-$518** |
| unseen yr Oct 2023-Oct 2024 | $463 |
| last 2y Oct 2024-Oct 2026 (the window they were picked on) | $2,018 |
| Sep+Oct 2026 | -$315 |

Six of the 23 lost money every year or nearly so before 2024: ab_mql_range (XAUUSD M30, -$132/mo),
rsi2_mr_jpn225 (-$181), eia_fade (-$91), inside_bar_h4 (-$69), nr_7_mid_r2 (-$47), sh_long_21-3 (-$32).
Only 10 of the 23 have 5+ dev years with at least half of them green.

## Ideas tested, in the order of the brief

| idea | what was tested | result on unseen data |
|---|---|---|
| 1. strategies in the 66/74/51 not in the 23 | 91 with 3+ dev years; 29 pass a relaxed dev rule | added to the live 23 at 0.5% each: unseen yr $103/mo with 8 failed starts vs $124 and 9 without them; last 2y $610 vs $696; Sep+Oct -$162 vs +$153. More stop days (51 vs 15). **Adds money nowhere.** |
| 2. steady screen (>= 5 dev years, >= 80% green) | 10 pass (3 from the pool, 7 round-4 survivors) | 10 at 0.75% each ("strict" mix): unseen yr $113/mo but 7 failed starts, Sep+Oct -$235. Too few, too lumpy. |
| 3a. time-of-day holds per market | 40,020 hour pairs x 40 markets, picked on dev | best t-stat 3.2 (chance level for a grid this size); the two carried into the real sim lost money in every period. **Dead.** |
| 3b. volatility-regime filter on existing winners | 52 strategies x skip-high-vol / skip-low-vol, chosen on dev | chosen for 9 of 52; those 9 did WORSE filtered in every unseen period (unseen yr $196 -> $151, Sep+Oct $129 -> -$82 at 1%). **Dead**, same as the gold-gate study. |
| 3c. cross-market spreads | Brent/WTI and gold/silver already in the pool | both near zero on dev, and neither can run live (second symbol). Not pursued. |
| 4. equity regime switch (half size while 20-day mean equity < 60-day mean) | every mix, both accounts | costs 3-25% of profit; cuts failed starts only on the steady mix (4 -> 0 of 77 over 3 years at $5K). Does nothing for the live 23. |

## The mixes, $5K account, exact replay with the live daily stop

Rules fixed before looking at unseen data: "relaxed" = 4+ dev years, at least half green, dev $/month > 0,
60+ dev trades, can run live; "strict" = 5+ dev years, 80% green. Sizes picked on dev: the largest equal
risk that kept the dev lowest balance above $4,750 and under 12 stop days a year.

| mix | strategies | dev 2015-23 | unseen yr | last 2y (fit for live23) | Sep+Oct 2026 | all 3 unseen yrs |
|---|---|---|---|---|---|---|
| live 23 as running | 23 | -$212/mo, blown many times | $124/mo, fail 9/24, low $4,601 | $696/mo, fail 0/51, low $4,807 | $153/mo | $507/mo, fail 10/77 |
| live 23 + 29 adds @0.5% | 52 | -$520/mo | $103/mo, fail 8/24, low $4,486 | $610/mo, fail 9/51 | -$162/mo | $442/mo, fail 18/77 |
| **steady 33 @0.30%** | 33 | $68/mo, low $4,762 | **$133/mo, fail 0/24, low $4,798** | $119/mo, fail 5/51 | -$173/mo | $124/mo, fail 4/77, 0 stop days |
| strict 10 @0.75% | 10 | $60/mo | $113/mo, fail 7/24 | $98/mo, fail 6/51 | -$235/mo | $103/mo, fail 13/77 |
| live 23 minus 6 dev losers + adds | 46 | -$219/mo | $117/mo, fail 10/24, low $4,500 | $561/mo, fail 6/51 | -$229/mo | $414/mo, fail 18/77 |

Same at $10K: live 23 $106/mo with 10 failed starts in the unseen year ($1,747/mo on the fit window);
steady 33 $306/mo with 0 failed starts ($403/mo on last 2y, -$218 Sep+Oct).

A sizing fact that matters at $5K: at 0.30% of $10K halved, the risk per trade is about $15. Several
daily-timeframe strategies in the steady mix cannot be funded at one minimum lot at that size and show
zero trades (tsmom BTC D1, ibs US30 D1, pin DE40 D1, pweek DE40 H1). The $5K account cannot spread
small risk across many slow strategies; on $10K the same mix funds them and makes 2.3x per month.

## Where the steady mix's money comes from (unseen yr, $5K, $ per strategy)

ETHUSD H4 pin bar $247, BTCUSD H1 spike_follow $222, DE40 H1 de_orb $186, XAUUSD M30 bos_hv $151,
DE40 M30 crabel $127, EURJPY H1 mon_long $119, EURJPY H1 monday_long_downweek $109, XAUUSD H1
bos_trail3 $95, XAUUSD H1 htf_bo50 $90, US500 D1 down_streak $68. The rest are under $30 each;
8 are negative (-$14 to -$79). Full list in the tables file.

## Recommendation

Nothing found this round makes more money than the live 23 on data it was not picked on; the only honest
improvement on offer is fewer blown challenge starts, not more profit. If the goal is to pass the $5K
challenge, the steady 33 at 0.30% (`portfolio-round5-honest.json`) is the mix with zero failed starts in
the unseen year and zero stop days in three unseen years, at roughly the same $130 a month the live 23
made in its unseen year, and it keeps making money on the $10K account ($300 a month). If the goal is
the $700-$1,700 a month the live 23 showed on 2024-2026, understand that number comes from the window the
23 were picked on; their honest record is $124 a month with 9 of 24 challenge starts failing. Do not add
the 29 extra strategies, do not add volatility or time-of-day filters, and do not expect a regime switch
to rescue the 23. My one-line view: run the steady 33 on the $5K challenge and keep hunting for real
edges elsewhere, because this pool is mined out.

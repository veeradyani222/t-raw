# Strategy search, round 6: the strategy-search gear and its first run (2026-11-01)

Written for Veer. Plain language. Round 6 built a repeatable rig that finds strategy descriptions
(YouTube videos, blogs, forums, the classic books, public EA pages), turns them into runnable rules, and
judges every one the honest way (picked on 2015..Oct 2023 data, reported on the three unseen periods,
each strategy on the market its source is about). This file is the first run's result; the rig keeps
running after this.

## What the gear is

| part | where | what it does |
|---|---|---|
| collector | `research/search6/collect.py`, `collect_more.py` | yt-dlp search per market (23 markets, 10 phrasings): 869 unique videos, each tagged with its market |
| captions | `fetch_transcripts_api.py` (library, fast), `fetch_subs.py` (yt-dlp, slow) | both resumable; YouTube rate-limits after a few hundred (HTTP 429), so the rest is fetched later |
| transcripts | `transcripts.py` | clean text + manifest (263 transcripts, 599k words, from 23 markets) |
| reader | `.claude/skills/strategy-reader/SKILL.md`, `extract_prompt.md`, `batches.py` | one sub-agent per batch of ~20 transcripts writes JSON specs; the skill says what counts as a rule and what to refuse |
| rule engine | `engine.py` | 27 entry triggers (EMA cross, pullback, RSI, stochastic, MACD, Bollinger, Donchian, session/opening range, prev-day break, engulfing, pin bar, inside bar, doji, S/R bounce, liquidity sweep, FVG, order block, supertrend, PSAR, Heikin Ashi, Ichimoku, VWAP bounce/cross, three-bar), 10 trend filters (EMA/SMA, EMA stack, ADX, supertrend, Ichimoku cloud, higher-timeframe EMA, RSI state, previous day, Fibonacci discount zone), 7 stop types, 9 exit types, session and weekday filters |
| judge | `run_specs.py` on `research/search5/core5.py` | every spec on its own market at the finest timeframe with long data, 2015..2026 at 1%; dev / unseen yr / last 2y / Sep+Oct |
| builder rules | `.claude/skills/strategy-builder/SKILL.md` | the hard-won rules: pick on dev, costs on, one source one market, plateau not peak, what is already dead |
| scoreboard | `scoreboard.py` -> `docs/board/scoreboard.{csv,md}`, cards in `knowledge/strategies/` | every strategy ever judged (349 now), one row each, honest columns only |
| routine | `routine.py` | one command runs collect -> captions -> text -> batch -> (read) -> merge -> judge -> board, skipping what is done |

## First run: what came out

| source | strategies tested | pass the dev rule | strict (80% green, 5+ yrs) | profitable in the unseen year |
|---|---|---|---|---|
| YouTube videos (263 read, 114 rule-based specs) | 114 | 5 | 2 | 23 |
| written sources (58 pages, 71 specs) | 71 | 5 | 0 | 21 |
| for comparison: round-3 pool | 80 | 9 | 1 | 26 |
| for comparison: round-4 price action | 16 | 9 | 7 | 6 |
| for comparison: the live 66 | 66 | 15 | 2 | 30 |

Only 126 of the 185 new specs could be judged on 4+ years: EURUSD and USTEC bars start in 2022 and M15
bars in 2021-2022, so M1/M5/M15 strategies run on M30 (long data from 2018) and EURUSD ones cannot be
judged honestly at all (41 specs, the single most common market on YouTube).

The 10 round-6 strategies that pass the dev rule, $/month at 1% of $10K (halve for $5K):

| strategy | market | tf | dev yrs | green | dev | unseen yr | last 2y | Sep+Oct | author's claim |
|---|---|---|---|---|---|---|---|---|---|
| us30_orb_demand_engulfing | US30 | M30 | 5 | 3 | 36 | -41 | -7 | -187 | "81% win rate backtested" |
| us500_daily_dip_buy_marubozu | US500 | D1 | 8 | 7 | 12 | 13 | -6 | 16 | "72% win, PF 2.5" |
| gbpjpy_sr_engulfing_ema50 | GBPJPY | H4 | 8 | 7 | 12 | -2 | -3 | -48 | one 70k trade |
| nzdusd_h4_structure_mirror_bars | NZDUSD | H4 | 9 | 6 | 11 | 36 | -38 | -63 | one 3:1 trade |
| tsg_bb_bounce_rsi_gbpusd | GBPUSD | H4 | 8 | 5 | 9 | 6 | -6 | -33 | none |
| pin_bar_h4_xauusd | XAUUSD | H4 | 9 | 5 | 6 | -7 | 38 | 271 | none |
| earnforex_spike_trader_usdcad | USDCAD | D1 | 8 | 5 | 4 | 27 | -22 | -15 | "16% in 9 yrs, 57% win" |
| rsi2_strict_5_short_90 | US500 | D1 | 8 | 5 | 1 | 14 | 22 | 7 | Connors variant |
| gold_swing_resistance_break_h1 | XAUUSD | H1 | 8 | 4 | 1 | 181 | 104 | -94 | none |
| connors_rsi2_5_95_sp500 | US500 | D1 | 8 | 5 | 0 | 12 | 5 | 3 | "71% win, PF 1.43" |
| **all 10 together** | | | | | **95** | **238** | **87** | **-143** | 7 of 10 green unseen |

All 126 judgeable specs together lose about $39,000 a month at 1% each: the typical YouTube rule set,
traded mechanically with real spread and commission, loses money. 20 of 126 were profitable on dev,
33 of 126 in the unseen year (about what coin flips give).

## What this means

- The gear works end to end and is cheap to re-run: 185 strategies were coded and judged in an evening,
  and every one is now on the scoreboard so it never gets re-tested.
- The yield of real edges from public sources is roughly 1 in 20, and the ones that pass are small
  (the best, the US500 daily dip buy, made $12 a month per 1% on dev and $13 unseen). This matches rounds
  3 to 5: retail rule sets are mostly noise after costs.
- The two closest things to "money" were a gold H1 resistance-break swing ($181/month unseen but only $1 on
  dev, so unproven) and the round-4 ETHUSD pin bar from before. Nothing here changes the advice from round 5.
- Half the videos could not be turned into rules at all (discretionary zones, "confirmation", proprietary
  indicators). Readers logged the missing blocks; the engine grew by 7 blocks during the run (opening
  range by minutes, Fibonacci zone, RSI state, previous-day colour, range-opposite stop, close-at-hour
  exit, VWAP cross) and the remaining gaps (round-number levels, divergence, volume profile, measured moves)
  are listed in the spec notes.

## What is left running

- 606 of the 869 videos still need captions (YouTube returned HTTP 429 after ~260). `python -m
  research.search6.routine captions text batch` resumes it; then one reader per new batch, then
  `routine merge judge board`.
- Readers worked from the first menu; a second pass over the 263 transcripts with the 7 new blocks would
  recover some of the opening-range and Fibonacci setups that were skipped.

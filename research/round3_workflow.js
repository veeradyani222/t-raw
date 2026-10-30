export const meta = {
  name: 'prop-strategy-search-round3',
  description: 'Round 3 from scratch: per-market strategy design across all markets, scored on the last 2 years under the prop rule, then one optimizer rebuild of the whole portfolio',
  phases: [
    { title: 'Design', detail: '10 market groups: study the market, research practitioners, design and score 10+ strategies each' },
    { title: 'Portfolio', detail: 'LP rebuild from the full pool (current 66 + all new), $300/day, $9,200 floor' },
  ],
}

const REPO = 'C:/Users/veera/Desktop/mt5-trader'
const PY = REPO + '/.venv/Scripts/python.exe'

const CONTEXT = [
  'You are part of ROUND 3 of a strategy-research team for an MT5 Python trading repo at ' + REPO + ' (branch multi-strategy-bot checked out; never switch branches, commit or push; never touch trader/, run_live.py, ops/, tests/, docs/board/ or existing research/ folders). Run python as: cd ' + REPO + ' && ' + PY + ' script.py . RAM is tight: multiprocessing Pool(2) at most.',
  '',
  'GOAL (owner Veer): the most PROFIT while never breaking a FundedNext $10k account: never lose $400 in a server day (floating counts; we design to $300), never let equity fall below $9,200 (static). He wants a FROM-SCRATCH, PER-MARKET search with no loyalty to the current 66-strategy portfolio and NO statistical gates (no in/out-of-sample split, no placebo, no skeptic). What stays: a LOOK-AHEAD BUG CHECK and the 300/800 rule. Design strategies FOR each market: study it first (returns and volatility by hour/weekday/session, trend persistence vs mean reversion per timeframe, gap behaviour), research what practitioners actually use there (web search; if a credible rule set comes from a video or podcast use its transcript and test the actual rules), and think in market structure (prior day/week/session highs and lows, round numbers, opens and closes, volatility regimes), not only indicators.',
  '',
  'THE JUDGE: research/prop/harness.py (read its docstring first). Score EVERYTHING on 2024-10-20..now:',
  '  import os; os.environ["PROP_OOS"] = "1"',
  '  from research.prop import harness as H',
  '  df = H.load("BTCUSD", "H1", split="oos")   # warmup kept; scoring counts from 2024-10-20',
  '  sigs = build(df, **params)                 # list of H.Entry|None, len(df), causal',
  '  s = H.score(df, sigs, name="...")          # best_risk = highest risk with worst day > -3% and max DD > -6%',
  'H.Entry(side, sl, tp=None, max_hold=None, exit_hour=None, manage=None, meta={}); manage(df,i,pos) -> new stop | "close" | None. Every trade has a stop and a defined exit (tp, trailing, time or opposite signal). A candidate counts if best_risk is not None and avg_month > 0; rank by avg_month.',
  'Costs are modelled per symbol via H.SPREAD_FLOOR, H._pip and H.INDICES. New symbols may be missing there: in your script set realistic values by monkeypatching (BTCUSD spread ~25, ETHUSD ~2, XRP/ADA/DOGE-type ~0.3% of price, XTIUSD/XBRUSD ~0.04, XNGUSD ~0.01, JP225 ~10, HK50 ~15, UK100 ~2, F40 ~1.5, AUS200 ~2, STOXX50 ~1.5, SWI20 ~3, US2000 ~0.5, CHINA50 ~10, IT40 ~10, XPTUSD ~1.5, XPDUSD ~4, exotic crosses 3-10x a major) and add crypto/index symbols to H.INDICES (no $14 commission). Say what you used in NOTES. Contract sizes: data/search/symbol_specs.json.',
  '',
  'DATA: data/search/<symbol>-<tf>.csv (h1/h4/d1/m30), server time (EET). Original 23 markets from 2015; new markets (IC Markets demo, mostly from 2019): BTCUSD ETHUSD XRPUSD LTCUSD SOLUSD ADAUSD BNBUSD DOTUSD, XTIUSD XBRUSD XNGUSD, JP225 HK50 UK100 F40 AUS200 STOXX50 SWI20 US2000 CHINA50 IT40 (+ DE40 US30 US500 USTEC), XPTUSD XPDUSD, crosses EURAUD GBPAUD AUDNZD EURNZD GBPNZD EURCAD GBPCAD AUDCHF CADCHF NZDCAD NZDCHF USDZAR USDMXN USDNOK USDSEK EURNOK EURSEK USDSGD USDCNH USDPLN. If a file you need is missing, re-check every 2 minutes for up to 20 minutes (a fetch may still be running) and do the market study meanwhile. DATA QUALITY FIRST: check your files for flat/stale days (daily range < 5% of its median), long gaps and zero-volume bars; exclude affected bars and report counts.',
  '',
  'LOOK-AHEAD CHECK (mandatory per candidate): compare build(df) with build(df.iloc[:k]) (re-attach df.attrs) for 5 random k; every Entry at index < k must be identical. Any difference = bug: fix or drop.',
  '',
  'DELIVERABLES: research/search3/<group>/strategies.py with def build_<name>(df, **params) -> list for every candidate (must work on any df from H.load); research/search3/<group>/NOTES.md (market study, sources, data-quality report, table of every scored run). Aim for 15+ distinct ideas and 300+ scored runs per group (sweep parameters and all symbols of your group; volume matters, the owner wants the search as wide as possible). Return up to 8 best candidates (distinct ideas or markets, not parameter variants of one idea).',
].join('\n')

const CAND_SCHEMA = {
  type: 'object',
  properties: {
    group: { type: 'string' }, scored_runs: { type: 'integer' }, market_study: { type: 'string' }, data_quality: { type: 'string' },
    sources: { type: 'array', items: { type: 'string' } },
    candidates: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, symbol: { type: 'string' }, tf: { type: 'string' },
      module: { type: 'string' }, build_fn: { type: 'string' }, params: { type: 'object' },
      best_risk: { type: 'number' }, avg_month: { type: 'number' }, net: { type: 'number' }, max_dd: { type: 'number' }, worst_day: { type: 'number' },
      green_months: { type: 'number' }, trades: { type: 'integer' }, exit_type: { type: 'string' }, causal_ok: { type: 'boolean' }, idea: { type: 'string' } },
      required: ['name', 'symbol', 'tf', 'module', 'build_fn', 'params', 'best_risk', 'avg_month', 'net', 'max_dd', 'worst_day', 'trades', 'exit_type', 'causal_ok', 'idea'] } },
  },
  required: ['group', 'scored_runs', 'market_study', 'data_quality', 'candidates'],
}

const GROUPS = [
  { key: 'crypto', prompt: 'GROUP crypto: BTCUSD ETHUSD XRPUSD LTCUSD SOLUSD ADAUSD BNBUSD DOTUSD on H1/H4/D1. These trade 24/7, so weekends and Asian hours count (nothing else in the portfolio trades then). Study hour/weekday returns and volatility, weekend behaviour, trend persistence by timeframe, BTC-ETH lead/lag. Research what systematic crypto traders use: time-series momentum, multi-day range breakouts, volatility compression, weekend and Monday-open effects, US-session momentum, alt-vs-BTC relative strength. Stops must be far wider than the spread.' },
  { key: 'oil_gas', prompt: 'GROUP oil_gas: XTIUSD XBRUSD XNGUSD on M30/H1/H4/D1. Study the session structure (NY pit open about 16:00 server, settlement about 21:30), Wednesday EIA inventory report (17:30 server) and Thursday gas storage report, Brent-WTI spread reversion, D1 trend persistence. Research oil/gas systematic approaches: session range breakouts, inventory-day patterns, overnight gaps, D1 momentum.' },
  { key: 'asia_indices', prompt: 'GROUP asia_indices: JP225 HK50 CHINA50 AUS200 on M30/H1/H4/D1. Study cash open/close in server time (Tokyo roughly 02:00-08:00, HK 04:30-11:00, Sydney 01:00-07:00), overnight gaps and fill rates, open-drive vs fade, lunch breaks, dependence on the prior US close. Research index session strategies: opening range breakout/fade, gap fill, first-hour reversal, close-to-open drift, prior-day high/low tests. Mind JP225 min lot 1.0 and HK50 0.1.' },
  { key: 'europe_indices', prompt: 'GROUP europe_indices: UK100 F40 STOXX50 SWI20 IT40 DE40 on M30/H1/H4/D1. Study the 10:00 server cash open, the 16:30 US-open shock, the 18:30 cash close, overnight gaps. Research European index patterns: opening range, 10:00-11:00 reversal, US-open continuation, late-day momentum. DE40 already has live strategies (research/search/breakout, jpy_session turn-of-month): design different ideas or better versions, and test ideas across all six.' },
  { key: 'us_indices', prompt: 'GROUP us_indices: US30 US500 USTEC US2000 on M30/H1/H4/D1. Study the 16:30 server cash open, the first and last hours, overnight gap fill rates, Fed-day behaviour, turn-of-month and options-expiry weeks, mean reversion at D1 extremes. Research well-documented US index effects: overnight drift, gap fades, opening-range breakouts, buy-the-dip in uptrends, end-of-day momentum. Round 1 covered z-score/dip combos on these; go beyond them.' },
  { key: 'metals', prompt: 'GROUP metals: XAUUSD XAGUSD XPTUSD XPDUSD on M30/H1/H4/D1. Gold has 14 live strategies (break of structure, Bollinger/Donchian breakouts, calendar, turn-of-month) which lose when gold chops; design DIFFERENT gold logic (London/NY fix behaviour 12:30/17:00 server, prior-day level tests, Asian-range breakouts with structure targets, silver/platinum/palladium relative moves, gold-silver ratio extremes) and strategies for the other three metals, which have no coverage yet.' },
  { key: 'jpy_crosses', prompt: 'GROUP jpy_crosses: USDJPY EURJPY GBPJPY AUDJPY CADJPY CHFJPY NZDJPY on M30/H1/H4/D1. Study Tokyo-session behaviour (00:00-09:00 server), the Tokyo fix at 02:55, London/NY momentum, risk-on/off co-movement, carry drift. Research what works on JPY crosses: session momentum, range breakouts after Tokyo, pullbacks in D1 trends, intervention-risk rules. Round 1 found Monday-long/turn-of-month effects; find different, intraday or structure-based ideas.' },
  { key: 'commodity_fx', prompt: 'GROUP commodity_fx: AUDUSD NZDUSD USDCAD EURAUD GBPAUD AUDNZD EURNZD GBPNZD EURCAD GBPCAD AUDCHF CADCHF NZDCAD NZDCHF on H1/H4/D1. Study links to commodities (AUD-metals, CAD-oil, NZD), Sydney/Asia session, AUDNZD range behaviour, cross volatility by session. Research cross-pair range trading, correlation-driven ideas (e.g. AUDUSD vs XAUUSD divergence), D1 trend following with pullback entries.' },
  { key: 'exotics', prompt: 'GROUP exotics: USDZAR USDMXN USDNOK USDSEK EURNOK EURSEK USDSGD USDCNH USDPLN on H1/H4/D1. Study trend persistence and carry drift, session volatility (Johannesburg, Mexico City, Oslo/Stockholm hours), spread cost relative to ATR (set realistic spread floors), risk-off behaviour. Research what works on exotics: D1/H4 trend following, breakout of multi-week ranges, carry-with-trend. Be strict about costs; many exotic edges vanish after spread.' },
  { key: 'majors', prompt: 'GROUP majors: EURUSD GBPUSD USDCHF EURGBP EURCHF GBPCHF on M30/H1/H4/D1. Study London open (10:00 server), the London/NY overlap, the 17:00 fix, Friday behaviour, range-day vs trend-day classification, prior-day and weekly level tests. Research structure-based FX ideas: Asian-range breakout with structure targets, London-open reversal, previous-day high/low sweeps and reversals, pivot-level reactions. Rounds 1-2 tried generic indicators on these pairs; this round is about structure and sessions.' },
]

phase('Design')
const results = await parallel(GROUPS.map(g => () =>
  agent(CONTEXT + '\n\n' + g.prompt + '\n\nYour folder: research/search3/' + g.key + '/ (create it with __init__.py; ensure research/search3/__init__.py exists). Return group="' + g.key + '".',
    { label: 'design:' + g.key, phase: 'Design', schema: CAND_SCHEMA })))

const pool = []
for (const r of results.filter(Boolean)) for (const c of (r.candidates || [])) if (c && c.best_risk && c.avg_month > 0 && c.causal_ok) pool.push({ ...c, group: r.group })
log('Design done: ' + results.filter(Boolean).length + '/10 groups, ' + pool.length + ' candidates; runs: ' + results.filter(Boolean).map(r => r.group + ':' + r.scored_runs).join(' '))

phase('Portfolio')
const report = await agent(CONTEXT + `

You are the PORTFOLIO stage. Build the new portfolio from the FULL pool with no preference for the current mix.
POOL A (new, this round): ${JSON.stringify(pool)}
POOL B (current live mix, 66 strategies): docs/board/portfolio-lp300-66.json (fields mix[] with module, fn, params, symbol, tf, risk).
Method, same as the live mix was built (reference code: research/search2/portfolio/*.py and research/overlays/sim.py, runs.py; reuse, do not edit): for every strategy in A and B, an exact simulation at 1% risk over 2024-10-20..now starting flat with 6000-bar warmup (Pool(2), float32, hourly buckets to save RAM); then a linear-programme over per-strategy size dials (0..3%) maximising total profit subject to, at every hour: combined floating loss on the server day > -$300 and combined equity > -$800 from start (static); then re-size the pick with exact per-level simulations at discrete levels (0.25%..3%); then replay the combined account with the live close-all stop at -$300 (slip $25). Report the new mix vs the current 66 (net, avg/month, green months, worst day, lowest equity, max $ at risk at once, stop fires, rolling-challenge pass/fail), which new strategies made it and which current ones were dropped, and a last-12-months fresh-start replay. Also flag anything that looks like a data artefact (one trade dominating, abnormal lots). Write docs/2026-10-30-round3-results.md in plain language for a non-quant owner with a ranked table of all candidates, and docs/board/portfolio-round3.json in the same format as portfolio-lp300-66.json. Return a concise summary (<= 25 lines).`,
  { label: 'portfolio+report', phase: 'Portfolio' })

return { report, candidates: pool.length, groups: results.filter(Boolean).map(r => ({ group: r.group, runs: r.scored_runs, n: (r.candidates || []).length })) }

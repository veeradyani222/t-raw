# Round 3 mixes: live readiness on the IC Markets demo (2026-10-31)

Which of the three round-3 mixes (`docs/board/portfolio-round3-2y.json`, `-3y.json`,
`-5y.json`) the multi-strategy bot (`trader/multi.py` + `trader/multi_live.py`) can run
as they stand, strategy by strategy. Reproducible: `tests/test_round3_live_readiness.py`
runs every check below on every `research.search3` strategy in the three files;
`tests/test_multi_mix_config.py` covers the mix switch, the symbol map, the skip list,
the conversion pairs and the sizing patches; `tests/test_multi_weekend.py` the 24/7
crypto questions. 347 tests pass, 1 skipped (274 + 1 skipped before this work).

## What was checked, per strategy

1. **Importable**: `module.fn` resolves.
2. **Runs live-shaped**: the builder is called on a 6,000-bar synthetic window at the
   strategy's timeframe with exactly the columns the runner supplies (`time open high low
   close tick_volume spread conv`, `df.attrs` symbol / tf / split="live"), weekday bars
   for everything but crypto (24/7), and returns one `Entry | None` per bar with a finite
   stop.
3. **Own symbol only, nothing from `data/`**: `pandas.read_csv` and `harness.load` are
   replaced by functions that raise and `harness.DATA` points at a missing folder. The
   live window carries one symbol; a strategy that needs another symbol's bars cannot run.
4. **No look-ahead**: the signals of the full window are compared with the signals of the
   window truncated at bars n-1, n-5, n-60 and n-400 (every entry before the cut must be
   identical) and with a window whose last 300 bars were re-priced at random (every entry
   before them must be identical).
5. **Sizable**: `size_trade` funds a 0.2 %-stop entry at 1 % risk at or above the
   symbol's lot minimum with the tracked contract spec and the research cost patches.

Result: 44 of the 46 distinct `search3` strategies pass everything; 2 need a second
symbol's bars and are excluded. No look-ahead was found in any of the 46 (the 2 excluded
ones could not be run that far, since they fail at the data read).

## Per mix

| mix | strategies | of which search3 | excluded (skip list) | runs live | symbols |
|---|---|---|---|---|---|
| `portfolio-round3-2y.json` | 51 | 32 | 1: `brent_wti_spread_z` (XTIUSD H4, needs XBRUSD) | **50** (subject to the IC pre-flight) | 28 |
| `portfolio-round3-3y.json` | 62 | 35 | 1: `rz_XAGUSD_n200_z2.5` (XAUUSD H1, needs XAGUSD) | **61** (subject to the IC pre-flight) | 29 |
| `portfolio-round3-5y.json` | 57 | 31 | 1: `rz_XAGUSD_n200_z2.5` (XAUUSD H1, needs XAGUSD) | **56** (subject to the IC pre-flight) | 27 |

The strategies carried over from the 66 (`research.search.*` modules, 19 / 27 / 26 per
mix) are the ones already running on the demo; nothing changed for them.

"Subject to the IC pre-flight": `run_live.py --preflight` on the IC account is the
remaining gate, and it could not be run here (no broker connection in this work). It
compares, per symbol, the broker's contract size / point / lot step / profit currency with
what the research sized with (`config/symbol_specs.json`) and the broker's P&L per lot
with contract x move x FX rate. Expected outcomes on IC (see "Symbol names" below):

- the 23 original symbols, the crypto (BTCUSD ETHUSD SOLUSD XRPUSD), energies (XTIUSD
  XNGUSD), US/EU indices (US500 USTEC US30 DE40), AUS200, CHINA50, XAGUSD, XPDUSD,
  NZDUSD: specs were fetched from the IC demo under these names; should pass;
- FRA40 and JPN225: fetched from IC under these exact names (both files and specs exist,
  alongside separate F40 / JP225 contracts with different specs). Expected to pass as-is.
  If the pre-flight says "not found", see "Symbol names";
- EURNOK, USDMXN, USDCNH: never had a fetched spec; the research sized them with the
  exotics group's default (5 digits, point 1e-5, contract 100,000, profit currency = quote,
  lot 0.01 / step 0.01), now tracked in `config/symbol_specs.json`. IC's contracts should
  match; a mismatch would disable the 4 exotic strategies (3y: 4, 5y: 5, 2y: 3) and is
  correct behaviour, not something to override.

## Every search3 strategy in the three mixes

Mix names are the `name` field of the mix entries. Risk is the per-mix setting.

| # | strategy (mix name) | group / builder | symbol | tf | params | in mixes (risk) | runs live | reason |
|---|---|---|---|---|---|---|---|---|
| 1 | daily_mr_aus200_d1 | asia_indices / daily_mr | AUS200 | D1 | `{"hold": 3, "lb": 2, "side": "both", "sl_atr": 3, "thr": 0.75}` | 3y 0.25% | yes | passes checks 1-5 |
| 2 | daily_mr_china50_d1 | asia_indices / daily_mr | CHINA50 | D1 | `{"hold": 2, "lb": 2, "side": "both", "sl_atr": 1.5, "thr": 1}` | 3y 1.25%, 5y 0.25% | yes | passes checks 1-5 |
| 3 | gap_fill_aus200_h1 | asia_indices / gap_fill | AUS200 | H1 | `{"close_h": 8, "confirm": true, "max_gap": 2.5, "min_gap": 0.3, "open_h": 2, "sl_mult": 2}` | 2y 0.5%, 3y 1.25%, 5y 0.75% | yes | passes checks 1-5 |
| 4 | gap_go_jpn225_m30 | asia_indices / gap_go | JPN225 | M30 | `{"close_h": 8.5, "min_gap": 0.6, "open_h": 2, "sl_mode": "pc", "tp_atr": 0}` | 3y 1.25% | yes | passes checks 1-5; JPN225 contract must pass the pre-flight |
| 5 | rsi2_mr_aus200_h4 | asia_indices / rsi_mr | AUS200 | H4 | `{"hi": 85, "lo": 15, "max_hold": 8, "n": 2, "sl_atr": 1.5, "trend_n": 200}` | 2y 0.75%, 3y 0.5%, 5y 0.5% | yes | passes checks 1-5 |
| 6 | rsi2_mr_china50_d1 | asia_indices / rsi_mr | CHINA50 | D1 | `{"hi": 75, "lo": 25, "max_hold": 5, "n": 2, "sl_atr": 2, "trend_n": 0}` | 3y 0.25%, 5y 0.25% | yes | passes checks 1-5 |
| 7 | rsi2_mr_jpn225_h1 | asia_indices / rsi_mr | JPN225 | H1 | `{"hi": 75, "lo": 25, "max_hold": 8, "n": 2, "sl_atr": 2, "trend_n": 0}` | 2y 1.25% | yes | passes checks 1-5; JPN225 contract must pass the pre-flight |
| 8 | zmean_n100_adx25 | commodity_fx / zmean | NZDUSD | H4 | `{"adx_max": 25, "n": 100}` | 2y 0.5%, 3y 1%, 5y 0.25% | yes | passes checks 1-5 |
| 9 | inside_h4_trail | crypto / inside_day | XRPUSD | H4 | `{"trail": true}` | 2y 0.5%, 3y 0.25%, 5y 0.5% | yes | passes checks 1-5 (needs the crypto lot cap lift, see "Runner changes") |
| 10 | pdm_t10_h24 | crypto / pd_mom | ETHUSD | H1 | `{"thresh": 1}` | 2y 0.25%, 5y 0.25% | yes | passes checks 1-5 |
| 11 | pw_h4_sfp_trail2 | crypto / pw_sfp | SOLUSD | H4 | `{"trail_mult": 2}` | 2y 0.75%, 3y 0.25%, 5y 0.25% | yes | passes checks 1-5 |
| 12 | squeeze_h4_a25_kc2 | crypto / squeeze | ETHUSD | H4 | `{"atr_mult": 2.5, "kc_mult": 2}` | 2y 0.25%, 3y 0.25%, 5y 0.5% | yes | passes checks 1-5 |
| 13 | spike_follow | crypto / vol_spike | BTCUSD | H1 | `{"hold": 12, "mode": "follow", "rr": 2}` | 3y 0.5%, 5y 0.25% | yes | passes checks 1-5 |
| 14 | wd_MW_Th_a15 | crypto / weekday | BTCUSD | D1 | `{"atr_mult": 1.5}` | 2y 1%, 3y 1.25%, 5y 0.5% | yes | passes checks 1-5 |
| 15 | monday_cash_long_de40 | europe_indices / calendar | DE40 | M30 | `{"kind": "weekday", "side": "long", "wd": 0}` | 2y 0.25%, 5y 1.25% | yes | passes checks 1-5 |
| 16 | first_hour_mult_break_de40 | europe_indices / fh_mult | DE40 | M30 | `{"mult": 0.5, "sl": "opp", "tp_r": null}` | 2y 0.25%, 3y 0.25%, 5y 0.5% | yes | passes checks 1-5 |
| 17 | or_fail_fra40 | europe_indices / or_fail | FRA40 | M30 | `{"re": 11, "tp": "mid", "trend": "with"}` | 2y 1%, 3y 0.75%, 5y 0.75% | yes | passes checks 1-5; FRA40 contract must pass the pre-flight |
| 18 | prev_week_high_long_de40 | europe_indices / prev_week | DE40 | M30 | `{"sides": "long", "sl_atr": 1.5, "trail_atr": 3}` | 2y 0.5%, 3y 0.5%, 5y 0.5% | yes | passes checks 1-5 |
| 19 | exo_usdmxn_ema_pullback | exotics / ema_pullback | USDMXN | D1 | `{"fast": 20, "max_hold": 60, "slow": 100, "tp_r": 3}` | 5y 0.25% | yes | passes checks 1-5; USDMXN spec is the research default, pre-flight verifies |
| 20 | exo_eurnok_inside_day | exotics / inside_day_break | EURNOK | D1 | `{"k_nr": 4, "max_hold": 5, "require_inside": true, "tp_r": 1.5}` | 2y 0.5%, 3y 1.25%, 5y 2% | yes | passes checks 1-5; EURNOK spec is the research default, pre-flight verifies; needs USDNOK quotes |
| 21 | exo_eurnok_pwhl_break | exotics / pwh_pwl_break | EURNOK | D1 | `{"max_hold": 30, "tp_r": 2, "trail_k": null, "trend_n": null}` | 3y 0.5% | yes | as #20 |
| 22 | exo_eurnok_rsi2_h4 | exotics / rsi2_trend | EURNOK | H4 | `{"hi": 90, "lo": 10, "max_hold": 10, "tp_r": 1.5, "trend_n": 100}` | 2y 0.5%, 3y 0.5%, 5y 0.75% | yes | as #20 |
| 23 | exo_usdcnh_3bar_pullback | exotics / three_bar_pullback | USDCNH | D1 | `{"m": 2, "max_hold": 15, "tp_r": 2, "trend_n": 100}` | 3y 0.25%, 5y 1.25% | yes | passes checks 1-5; USDCNH spec is the research default, pre-flight verifies |
| 24 | band_fade_h4_trend | jpy_crosses / band_fade | CHFJPY | H4 | `{"trend_n": 200}` | 3y 0.25% | yes | passes checks 1-5 |
| 25 | friday_week_fade_eurusd | majors / friday_week_fade | EURUSD | H1 | `{"hour": 14, "thr": 1.8, "tp_frac": 0.5}` | 2y 2%, 3y 1.5%, 5y 1.5% | yes | passes checks 1-5 |
| 26 | friday_week_fade_usdchf | majors / friday_week_fade | USDCHF | H1 | `{"hour": 14, "thr": 1.8, "tp_frac": 1}` | 3y 0.5%, 5y 0.25% | yes | passes checks 1-5 |
| 27 | inside_day_break_usdchf | majors / inside_nr_break | USDCHF | H4 | `{"kind": "inside", "max_hold": 18, "rr": 2, "sl_mode": "opp"}` | 2y 1%, 3y 0.75% | yes | passes checks 1-5 |
| 28 | monday_gap_fade_gbpusd | majors / monday_gap_fade | GBPUSD | H1 | `{"max_hold": 36, "min_gap": 0.2, "sl_mult": 1}` | 2y 2.5%, 3y 2%, 5y 2% | yes | passes checks 1-5 (no entries on the gap-free synthetic bars; the checks hold on the empty signal) |
| 29 | ab_mql_range_mid_mr0.3 | metals / asia_break | XAUUSD | M30 | `{"a0": 3, "a1": 8, "be_r": null, "exit_hour": 21, "last_entry": 14, "max_rng": 1.6, "min_rng": 0.3, "stop": "mid", "tp": "range"}` | 2y 0.5% | yes | passes checks 1-5 |
| 30 | nr_7_mid_r2 | metals / nr_break | XAGUSD | H1 | `{"inside": false, "nr": 7, "stop": "mid", "tp": "r:2"}` | 2y 1.25%, 3y 1.25% | yes | passes checks 1-5 |
| 31 | rz_XAGUSD_n200_z2.5 | metals / ratio_z | XAUUSD | H1 | `{"max_hold": 60, "other": "XAGUSD", "tp_r": 3, "z_in": 2.5, "z_n": 200, "z_out": 0.5}` | 3y 0.25%, 5y 0.5% | **no** | gold/silver ratio: needs XAGUSD bars via `harness.load` from `data/search` while trading XAUUSD (fails check 3; would also hit the PROP_OOS lock live). On `config/live_skip.json`. |
| 32 | sh_long_21-3_s3.0 | metals / session_hold | XAUUSD | H1 | `{"dows": null, "h_in": 21, "h_out": 3, "side": "long", "stop_atr": 3}` | 2y 0.5%, 3y 0.5%, 5y 0.75% | yes | passes checks 1-5 |
| 33 | up_long_23-9_s3.0_pdup | metals / session_hold | XPDUSD | H1 | `{"h_in": 23, "h_out": 9, "prev_day": "up", "side": "long", "stop_atr": 3}` | 2y 0.25% | yes | passes checks 1-5 |
| 34 | wo_d1.0_t0.2_r2 | metals / wopen_retest | XAUUSD | H4 | `{"max_hold": 12, "min_dist_atr": 1, "tol_atr": 0.2, "tp": "r:2"}` | 2y 0.25% | yes | passes checks 1-5 |
| 35 | donchian160_h4 | oil_gas / donchian | XTIUSD | H4 | `{"n": 160, "side": "both", "sl_atr": 2, "trail_atr": 3}` | 2y 1%, 3y 0.5%, 5y 0.25% | yes | passes checks 1-5 |
| 36 | inside_bar_h4 | oil_gas / inside_bar | XTIUSD | H4 | `{"atr_n": 14, "max_hold": 10, "sl_atr": 1.5, "sl_mode": "atr", "tp_r": 2.5}` | 2y 0.5% | yes | passes checks 1-5 |
| 37 | eia_fade_m30 | oil_gas / report_momentum | XTIUSD | M30 | `{"atr_n": 20, "direction": "fade", "exit_hour": 21, "min_move_atr": 0.3, "report_hour": 17, "report_wd": 2, "sl_atr": 1, "tp_r": null}` | 2y 0.75%, 3y 0.25% | yes | passes checks 1-5 (EIA time is a fixed server hour; no calendar read) |
| 38 | gas_rsi14_h4 | oil_gas / rsi_reversion | XNGUSD | H4 | `{"atr_n": 14, "hi": 75, "lo": 25, "max_hold": 12, "mid": 50, "rsi_n": 14, "side": "both", "sl_atr": 2.5}` | 2y 0.25%, 3y 0.25% | yes | passes checks 1-5 |
| 39 | brent_wti_spread_z | oil_gas / spread_reversion | XTIUSD | H4 | `{"lookback": 100, "max_hold": 120, "mode": "diff", "other": "XBRUSD", "sl_atr": 2, "z_in": 2.5, "z_out": 0}` | 2y 0.5% | **no** | Brent-WTI spread: needs XBRUSD bars via `harness.load` from `data/search` while trading XTIUSD (fails check 3; would also hit the PROP_OOS lock live). On `config/live_skip.json`. |
| 40 | ibs_lo0.2_hi0.8 | us_indices / ibs | US30 | D1 | `{"hi": 0.8, "lo": 0.2, "max_hold": 5, "sl_atr": 1.5}` | 3y 1%, 5y 0.5% | yes | passes checks 1-5 |
| 41 | overnight_trend | us_indices / overnight | US500 | M30 | `{"after": "any", "sl_atr": 1.5, "trend": "with"}` | 2y 0.5% | yes | passes checks 1-5 |
| 42 | prev_week_break_long | us_indices / prev_week | USTEC | H1 | `{"mode": "break", "sides": "long", "stop": "mid"}` | 3y 1%, 5y 0.5% | yes | passes checks 1-5 |
| 43 | round_big_bounce | us_indices / round | USTEC | M30 | `{"mode": "bounce", "step": "big", "tp_r": null}` | 2y 0.75%, 3y 1.25%, 5y 0.75% | yes | passes checks 1-5 |
| 44 | rsi2_thresh10_sma5 | us_indices / rsi2 | US500 | D1 | `{"exit_sma": 5, "thresh": 10}` | 2y 1.25%, 3y 1.5%, 5y 1.5% | yes | passes checks 1-5 |
| 45 | turtle_soup_n20_long | us_indices / turtle_soup | US30 | D1 | `{"exit_rule": "hold", "hold": 3, "mode": "long", "n": 20, "sl_pad": 0.5}` | 5y 0.75% | yes | passes checks 1-5 |
| 46 | weekday_fri_to_mon | us_indices / weekday | USTEC | D1 | `{"enter_dow": 4, "hold": 1, "trend": "with"}` | 2y 0.75%, 3y 1.5%, 5y 1.5% | yes | passes checks 1-5 |

## Skip list

`config/live_skip.json` is read at startup whatever mix is loaded. An entry matches on
module + builder (and symbol / timeframe when given); each matched strategy gets a
`SKIPPED` warning in the log, is listed as OFF in the startup Telegram message and in
`status`, and never fetches bars or trades. Removing an entry re-enables the strategy;
nothing in the mix files has to change. Today's two entries are the cross-symbol
strategies above.

## Runner changes made for the round-3 symbols

- **`MULTI_MIX_PATH`** (env / `.env`): the mix file to run; default unchanged (the 66).
  `compare_demo.py` reads the same variable, so the morning comparison follows the mix.
- **Symbol map** (`config/symbols.json`): a `servers` section with per-broker overrides
  keyed by a prefix of the MT5 server name, merged over `map` at startup. The IC section
  is intentionally empty (see "Symbol names").
- **Conversion pairs**: `CONV_PAIR` learned AUD (AUS200 is AUD-denominated), NOK, MXN,
  CNH, HKD, NZD and the other exotic quotes. Before this, AUS200 would have raised
  `KeyError('AUD')` on every bar and EURNOK/USDMXN/USDCNH (no spec) would have been sized
  as if their P&L were USD. The pairs are quote-only rows in the pre-flight: a strategy
  whose conversion pair does not quote is disabled with that reason. USDMXN and USDCNH
  convert with their own close (no second fetch).
- **Research cost patches**: `apply_research_patches()` replays the round-3 judge's
  harness patches (research/search3/portfolio/core3.py) on `load_mix`: spread floors and
  commission-free sets for crypto, energies, Asian/European indices, XPT/XPD, exotic
  floors, pip sizes. Without it live sizing would have reserved a $14/lot commission on
  crypto and energies the research did not, and the 50-lot cap would have made every
  XRPUSD signal unfundable (its lot minimum is 100; the judge lifted the cap for crypto,
  so does `size_trade` now).
- **Contract specs**: EURNOK, USDMXN, USDCNH added to `config/symbol_specs.json` with the
  research default spec (they had none; the pre-flight would otherwise compare against
  nothing and the runner would have treated their profit currency as USD).

## Weekend / 24-7 behaviour (crypto)

Checked against `harness.simulate` on synthetic BTCUSD H1 bars that run through a
weekend (`tests/test_multi_weekend.py`); nothing needed fixing:

- the server day is the broker's calendar day (`now.normalize()` on broker time, i.e.
  midnight server = 21:00/22:00 UTC on an EET server). It rolls on Saturday and Sunday
  as well, because the guard clock is the newest tick across the active symbols and
  crypto ticks all weekend; a daily stop hit on Saturday blocks Saturday only;
- `max_hold` counts bars and `exit_hour` fires on the first later bar with that hour, in
  the runner exactly as in the harness, so weekend bars count for crypto and do not exist
  for FX/indices, on both sides alike. The four parity cases (Friday entry + max_hold
  over midnight, Saturday entry with a Sunday exit hour, same hour next day, Sunday
  into Monday) match the harness bar for bar and to the cent.

## Symbol names on IC Markets (open point)

The brief assumed research `JPN225` = IC `JP225` and `FRA40` = IC `F40`. The repo says
otherwise: `research/data_fetch.py` (an IC demo via `.env`) wrote bars **and** contract
specs for both `FRA40` and `F40`, and for both `JPN225` and `JP225`, and the pairs
differ (FRA40 point 0.1 / lot min 1.0 vs F40 point 0.01 / lot min 0.1; JPN225 contract
100 / point 1 vs JP225 contract 1 / point 0.01). The round-3 research ran on the FRA40
and JPN225 files with those specs. So the map does **not** rename them. If
`run_live.py --preflight` on the IC account reports either as "not found", add
`"FRA40": "F40"` / `"JPN225": "JP225"` to the `ICMarketsSC` section of
`config/symbols.json`; the pre-flight will then fail them on contract size, which is
correct (the research was sized on the other contract), and `MULTI_SKIP_UNTRADABLE=1`
runs the rest. TODO: ESP35 is in no round-3 mix; its IC name was not verified.

## What the owner has to do on the VM

```
MULTI_MIX_PATH=docs/board/portfolio-round3-3y.json     # or -2y.json / -5y.json
MULTI_SKIP_UNTRADABLE=1
MT5_LOGIN=...
MT5_PASSWORD=...
MT5_SERVER=ICMarketsSC-Demo
```

then `python run_live.py --preflight` (read the table: every row of the chosen mix
should say YES; the conversion pairs USDJPY, USDCHF, EURUSD, AUDUSD, USDNOK and, for the
2y/5y mixes, USDCAD appear as extra rows and need only a quote) and `python run_live.py`. The startup Telegram message names the
mix, every live strategy, and every disabled one with its reason.

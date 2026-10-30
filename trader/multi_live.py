"""Live loop for the multi-strategy portfolio (trader/multi.py on MT5).

    python run_live.py                 # all strategies in docs/board/portfolio-lp300-66.json
    python run_live.py --preflight     # connect, print the symbol table, exit

Env (.env): MULTI_MIX_PATH=<mix json> runs another mix (default the 66);
MULTI_SKIP_UNTRADABLE=1 runs on with the strategies whose symbol fails the
pre-flight switched off instead of refusing to start. config/live_skip.json
names strategies that are never traded (one log line each).

Start-up: demo-only + hedging + Algo-Trading checks, the symbol pre-flight
table (refuses to run on any mismatch unless MULTI_SKIP_UNTRADABLE=1, which
disables just the affected strategies and says so loudly), a warm-up that
re-fetches every window until the newest bar stops moving, then a Telegram
message listing every strategy with symbol / timeframe / risk and whether it
is live.

Drawdown scaling from docs/2026-10-25-overlay-lab-results.md runs on top of
the daily stop and floor (see trader/multi.py): new trades at half size
while equity is below $9,700, full size again above $9,900.

Every POLL_SECONDS: the account guard on floating equity, then each
symbol/timeframe with a new closed bar. At the first poll of a new server
day a comparison of yesterday's demo deals against the backtest is produced
by compare_demo.py (in a subprocess) and sent to Telegram.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from . import mt5_market
from .alerts import send_alert
from .config import CONFIG, Config
from .multi import (DAILY_STOP, FLOOR, SCALE_HIGH, SCALE_LOW, SCALE_SIZE, STATE_PATH, WINDOW_BARS,
                    MultiRunner, conv_symbols, load_mix, load_skip_list, load_symbol_map,
                    load_symbol_specs, mix_path, skip_reasons)
from .mt5_market import MT5Error, MT5Market
from .telegram_commands import fetch_commands

log = logging.getLogger("trader")

POLL_SECONDS = 10
STATUS_EVERY_SECONDS = 30 * 60
DAILY_HEARTBEAT_SECONDS = 24 * 60 * 60
TG_LIMIT = 3800


def _chunks(lines: list[str], limit: int = TG_LIMIT) -> list[str]:
    out, cur = [], ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > limit:
            out.append(cur)
            cur = ""
        cur += ln + "\n"
    if cur:
        out.append(cur)
    return out


def _keyboard() -> dict:
    return {"keyboard": [["status", "risk"], ["report", "close all"], ["help"]],
            "resize_keyboard": True, "is_persistent": True}


HELP = ("\U0001F916 Commands:\n"
        "• status / positions — equity, today's P&L vs the stop, open positions\n"
        "• risk — the rails and the current size factor\n"
        "• report [YYYY-MM-DD] — demo vs backtest comparison (default: yesterday)\n"
        "• close all — close every position now (does not halt)\n"
        "• halt — close everything and stop trading until the state file is deleted\n"
        "• help — this list")


def strategy_lines(runner: MultiRunner) -> list[str]:
    lines = []
    for s in runner.specs:
        why = runner.disabled.get(s.idx)
        mark = "❌ OFF" if why else "✅"
        p = ", ".join(f"{k}={v}" for k, v in s.params.items()) or "-"
        lines.append(f"{mark} {s.name} risk {s.risk * 100:.2f}% ({p})" + (f" — {why}" if why else ""))
    return lines


def run_compare(date: str | None, telegram: bool = True) -> None:
    """compare_demo.py in a subprocess so a slow comparison never blocks the guard."""
    args = [sys.executable, str(Path(__file__).resolve().parents[1] / "compare_demo.py")]
    if date:
        args += ["--date", date]
    if telegram:
        args.append("--telegram")
    log.info("starting comparison: %s", " ".join(args))
    subprocess.Popen(args, cwd=str(Path(__file__).resolve().parents[1]))


def handle_command(runner: MultiRunner, text: str) -> str:
    parts = text.strip().lstrip("/").lower().split()
    cmd = parts[0] if parts else "help"
    arg = parts[1] if len(parts) > 1 else None
    if cmd in ("status", "positions", "pos", "risk", "limits"):
        return "\n".join(runner.status_lines())
    if cmd == "close" and arg == "all" or cmd in ("closeall", "flat"):
        n = runner.close_everything("manual")
        runner.save_state()
        return f"closed {n} position(s)."
    if cmd == "halt":
        runner.guard.blown = True
        n = runner.close_everything("halt")
        runner.save_state()
        return (f"\U0001F6D1 halted: closed {n} position(s); no more entries. To resume, stop the "
                f"bot, delete {STATE_PATH}, start it again.")
    if cmd == "report":
        run_compare(arg, telegram=True)
        return f"running the comparison for {arg or 'yesterday'} — it posts here when done."
    return HELP


def disabled_strategies(specs, problems: dict[str, str], conv: dict[str, list[str]],
                        skipped: dict[int, str]) -> dict[int, str]:
    """idx -> reason for every strategy that must not trade: its symbol failed
    the pre-flight, the pair that converts its P&L to USD does not quote, or it
    is on the skip list. Pure; one log line per strategy."""
    out = dict(skipped)
    for s in specs:
        if s.idx in out:
            continue
        if s.symbol in problems:
            out[s.idx] = problems[s.symbol]
        else:
            for pair, users in conv.items():
                if s.symbol in users and pair in problems:
                    out[s.idx] = f"conversion pair {pair}: {problems[pair]}"
        if s.idx in out:
            log.warning("%s DISABLED (%s)", s.name, out[s.idx])
    return out


def startup(cfg: Config, preflight_only: bool = False) -> MultiRunner | None:
    load_symbol_specs()                       # refuses to start without the sizing table
    acct = mt5_market.connect(cfg)
    path = mix_path()
    specs = load_mix(path)
    log.info("mix: %s (%d strategies)%s", path, len(specs),
             "" if not os.environ.get("MULTI_MIX_PATH") else "  [MULTI_MIX_PATH]")
    skipped = skip_reasons(specs, load_skip_list())
    symbol_map = load_symbol_map(server=acct["server"])
    conv = conv_symbols([s for s in specs if s.idx not in skipped])
    rows, problems = mt5_market.preflight([s.symbol for s in specs if s.idx not in skipped], symbol_map,
                                          quote_only=set(conv))
    table = mt5_market.preflight_table(rows)
    log.info("pre-flight:\n%s", table)
    print(table)
    disabled = disabled_strategies(specs, problems, conv, skipped)
    if problems:
        msg = "\n".join(f"  {k}: {v}" for k, v in problems.items())
        n_pf = len([i for i in disabled if i not in skipped])
        if os.environ.get("MULTI_SKIP_UNTRADABLE") != "1":
            raise MT5Error(f"pre-flight FAILED for {len(problems)} symbol(s) ({n_pf} "
                           f"strategies):\n{msg}\nFix the symbol map (config/symbols.json) or use "
                           "a broker that trades them. To run the rest anyway, set MULTI_SKIP_UNTRADABLE=1.")
        log.warning("MULTI_SKIP_UNTRADABLE=1: %d strategies DISABLED by the pre-flight:\n%s", n_pf, msg)
    if skipped:
        log.warning("%d strategies on the skip list (config/live_skip.json):\n%s", len(skipped),
                    "\n".join(f"  {specs[i].name}: {r}" for i, r in skipped.items()))
    if preflight_only:
        print(f"\naccount {acct['login']} on {acct['server']} ({acct['company']}), balance "
              f"{acct['balance']:.2f} {acct['currency']}; mix {path.name}: "
              f"{len(specs) - len(disabled)}/{len(specs)} strategies runnable "
              f"({len(skipped)} on the skip list)")
        return None
    runner = MultiRunner(MT5Market(), specs, symbol_map, alert=lambda t: send_alert(cfg, t),
                         disabled=disabled, state_path=STATE_PATH)
    log.info("warming up %d symbol/timeframe windows of %d bars", len(runner.keys), WINDOW_BARS)
    runner.warmup(sleep=time.sleep)
    for key, t in runner.last_bar.items():
        log.info("  %s %s: latest closed bar %s", key[0], key[1], t)
    runner.check_guard()

    live_n = len(specs) - len(disabled)
    head = (f"\U0001F7E2 multi-strategy bot started on {acct['server']} (account {acct['login']}, "
            f"{acct['company']}). Equity {acct['equity']:.2f} {acct['currency']}. Mix {path.name}: "
            f"{live_n}/{len(specs)} strategies live, {len(disabled)} disabled. "
            f"Rails: close ALL at -{DAILY_STOP:.0f} on the server day, permanent halt at equity "
            f"{FLOOR:.0f}. Risk rules: new trades at {SCALE_SIZE:g}x size while equity is below "
            f"{SCALE_LOW:.0f} (full size above {SCALE_HIGH:.0f}). Window {WINDOW_BARS} bars, "
            f"poll {POLL_SECONDS}s.")
    send_alert(cfg, head, reply_markup=_keyboard())
    for chunk in _chunks(strategy_lines(runner)):
        send_alert(cfg, chunk)
    for chunk in _chunks(["Pre-flight (research vs broker):"] + table.split("\n")):
        send_alert(cfg, chunk)
    if disabled:
        send_alert(cfg, f"⚠️ {len(disabled)} strategies are NOT running (symbol failed the pre-flight, "
                        f"conversion pair missing, or on config/live_skip.json):\n" +
                        "\n".join(f"  {specs[i].name}: {r}" for i, r in sorted(disabled.items())))
    send_alert(cfg, "\n".join(runner.status_lines()))
    return runner


def run_multi(cfg: Config = CONFIG) -> None:
    runner = startup(cfg)
    _, tg_offset = fetch_commands(cfg, None)        # drain backlog without acting on it
    last_status = last_heartbeat = time.time()
    polls = 0
    try:
        while True:
            try:
                events = runner.poll()
                polls += 1
                for ev in events:
                    if ev["kind"] == "new_day" and polls > 1:
                        prev = str((pd_ts(ev["day"]) - pd_td(1)).date())
                        run_compare(prev, telegram=True)
                if time.time() - last_status >= STATUS_EVERY_SECONDS:
                    if any(s.open for s in runner.states.values()):
                        send_alert(cfg, "⏳ " + "\n".join(runner.status_lines()))
                    last_status = time.time()
                if time.time() - last_heartbeat >= DAILY_HEARTBEAT_SECONDS:
                    send_alert(cfg, "✅ alive | " + runner.status_lines()[0])
                    last_heartbeat = time.time()
                cmds, tg_offset = fetch_commands(cfg, tg_offset)
                for c in cmds:
                    send_alert(cfg, handle_command(runner, c), reply_markup=_keyboard())
            except MT5Error as exc:
                log.error("MT5 error: %s", exc)
                send_alert(cfg, f"⚠️ ERROR: {exc}")
                time.sleep(60)
            time.sleep(POLL_SECONDS)
    finally:
        runner.save_state()
        mt5_market.shutdown()


def pd_ts(s):
    import pandas as pd
    return pd.Timestamp(s)


def pd_td(days):
    import pandas as pd
    return pd.Timedelta(days=days)

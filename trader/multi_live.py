"""Live loop for the multi-strategy portfolio (trader/multi.py on MT5).

    python run_live.py                 # all strategies in docs/board/portfolio-lp300-66.json
    python run_live.py --preflight     # connect, print the symbol table, exit

Start-up: demo-only + hedging + Algo-Trading checks, the symbol pre-flight
table (refuses to run on any mismatch unless MULTI_SKIP_UNTRADABLE=1, which
disables just the affected strategies and says so loudly), a warm-up that
re-fetches every window until the newest bar stops moving, then a Telegram
message listing every strategy with symbol / timeframe / risk and whether it
is live.

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
from .multi import (DAILY_STOP, FLOOR, MIX_PATH, STATE_PATH, WINDOW_BARS, MultiRunner, load_mix,
                    load_symbol_map)
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
        "• risk — the rails and where we are against them\n"
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


def startup(cfg: Config, preflight_only: bool = False) -> MultiRunner | None:
    acct = mt5_market.connect(cfg)
    specs = load_mix(MIX_PATH)
    symbol_map = load_symbol_map()
    rows, problems = mt5_market.preflight([s.symbol for s in specs], symbol_map)
    table = mt5_market.preflight_table(rows)
    log.info("pre-flight:\n%s", table)
    print(table)
    disabled = {s.idx: problems[s.symbol] for s in specs if s.symbol in problems}
    if problems:
        msg = "\n".join(f"  {k}: {v}" for k, v in problems.items())
        if os.environ.get("MULTI_SKIP_UNTRADABLE") != "1":
            raise MT5Error(f"pre-flight FAILED for {len(problems)} symbol(s) ({len(disabled)} "
                           f"strategies):\n{msg}\nFix the symbol map (config/symbols.json) or use "
                           "a broker that trades them. To run the rest anyway, set MULTI_SKIP_UNTRADABLE=1.")
        log.warning("MULTI_SKIP_UNTRADABLE=1: %d strategies DISABLED:\n%s", len(disabled), msg)
    if preflight_only:
        print(f"\naccount {acct['login']} on {acct['server']} ({acct['company']}), balance "
              f"{acct['balance']:.2f} {acct['currency']}; {len(specs) - len(disabled)}/{len(specs)} "
              f"strategies runnable")
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
            f"{acct['company']}). Equity {acct['equity']:.2f} {acct['currency']}. "
            f"{live_n}/{len(specs)} strategies live, {len(disabled)} disabled. "
            f"Rails: close ALL at -{DAILY_STOP:.0f} on the server day, permanent halt at equity "
            f"{FLOOR:.0f}. Window {WINDOW_BARS} bars, poll {POLL_SECONDS}s.")
    send_alert(cfg, head, reply_markup=_keyboard())
    for chunk in _chunks(strategy_lines(runner)):
        send_alert(cfg, chunk)
    for chunk in _chunks(["Pre-flight (research vs broker):"] + table.split("\n")):
        send_alert(cfg, chunk)
    if disabled:
        send_alert(cfg, f"⚠️ {len(disabled)} strategies are NOT running because their symbols "
                        f"cannot be traded on this account:\n" +
                        "\n".join(f"  {k}: {v}" for k, v in problems.items()))
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

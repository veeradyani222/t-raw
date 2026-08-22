"""Shared manual-command logic, used by BOTH the manual_trade CLI and the live
bot's Telegram listener — one code path so chat and command line behave
identically. Acts on cfg.symbol only (XAUUSD in the live config).

These commands deliberately bypass the strategy and RiskGuard: they are a
plumbing test of the order path ("can this account actually place/close an
order?"), not trade signals.
"""
from .broker import Broker
from .config import Config

LOTS_DEFAULT = 0.01

HELP = (
    "\U0001F916 Commands (XAUUSD only):\n"
    "• buy — open 0.01 lot long (market, no SL/TP)\n"
    "• sell — open 0.01 lot short\n"
    "• close — close ALL open positions\n"
    "• status — equity + open positions\n"
    "• help — show this list"
)


def _status(broker: Broker, cfg: Config) -> str:
    positions = broker.open_positions()
    equity = broker.equity()
    if not positions:
        return f"{cfg.symbol}: flat | equity {equity:.2f}"
    held = "\n".join(
        f"  {p.side.upper()} {p.lots} @ {p.entry_price:.2f} "
        f"(ticket {p.ticket}, sl {p.sl:.2f}, tp {p.tp:.2f})"
        for p in positions
    )
    return f"{cfg.symbol}: {len(positions)} open | equity {equity:.2f}\n{held}"


def run_command(broker: Broker, cfg: Config, command: str,
                lots: float = LOTS_DEFAULT) -> str:
    """Execute one command against `broker` and return a reply string. Accepts a
    leading slash and any case (`/Buy` == `buy`). Unknown commands return HELP
    rather than raising, so a typo over Telegram just gets the command list."""
    command = command.strip().lstrip("/").lower()

    if command in ("help", "commands", "start"):
        return HELP

    if command == "status":
        return _status(broker, cfg)

    if command in ("buy", "sell"):
        side = "long" if command == "buy" else "short"
        # No SL/TP (0.0 = none): a reachability ping closed by hand / `close`.
        pos = broker.open_position(side, lots, 0.0, 0.0)
        return (f"OPENED {side.upper()} {pos.lots} {cfg.symbol} @ "
                f"{pos.entry_price:.2f} (ticket {pos.ticket}). Send `close` when done.")

    if command in ("close", "closeall", "flat"):
        positions = broker.open_positions()
        if not positions:
            return f"nothing to close — no open {cfg.symbol} positions."
        lines, total = [], 0.0
        for pos in positions:
            profit = broker.close_position(pos)
            total += profit
            lines.append(f"closed {pos.side.upper()} {pos.lots} @ {pos.entry_price:.2f} "
                         f"(ticket {pos.ticket}) | P/L {profit:+.2f}")
        lines.append(f"closed {len(positions)} position(s) | total P/L {total:+.2f}")
        return "\n".join(lines)

    return f"unknown command '{command}'.\n{HELP}"


# --------------------------------------------------------------------------- #
# Multi-strategy commands (used by the live bot when several symbols run at     #
# once). One code path for "buy gold", "close usdjpy", "status", etc.          #
# --------------------------------------------------------------------------- #
def _help_multi(runners) -> str:
    syms = " / ".join(cfg.symbol for cfg, _ in runners)
    return (
        "\U0001F916 Commands:\n"
        "• status — equity, risk limits, and every open position\n"
        "• positions — just the open positions\n"
        "• risk — daily/total loss used vs the limits\n"
        "• buy <sym> / sell <sym> — open 0.01 lot (market, no SL/TP)\n"
        "• close <sym> — close all positions on that symbol\n"
        "• close all — close EVERYTHING\n"
        "• help — show this list\n"
        f"symbols: {syms}\n"
        "tip: tap the buttons below instead of typing."
    )


def _price_dp(cfg: Config) -> int:
    """Decimals to print a price at, from the pip size (gold 2, JPY 3, FX 5)."""
    return {0.1: 2, 0.01: 3, 0.0001: 5}.get(cfg.pip_size, 2)


def _friendly(symbol: str) -> str:
    """Short label used on the buttons and in `buy <x>` commands."""
    return {"XAUUSD": "gold", "USDJPY": "usdjpy"}.get(symbol, symbol.lower())


def command_keyboard(runners) -> dict:
    """A Telegram reply keyboard: tappable buttons whose text IS the command, so
    a tap sends e.g. `buy gold` and flows through the normal command parser. One
    buy/sell/close row per live symbol, plus account-wide buttons."""
    rows = [["status", "risk"], ["positions", "close all"]]
    for cfg, _ in runners:
        f = _friendly(cfg.symbol)
        rows.append([f"buy {f}", f"sell {f}", f"close {f}"])
    rows.append(["help"])
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def _resolve(token: str, by_symbol: dict) -> str | None:
    """Map a friendly name ('gold', 'jpy', 'xauusd') to one of the live symbols."""
    token = token.upper()
    aliases = {"GOLD": "XAUUSD", "XAU": "XAUUSD",
               "JPY": "USDJPY", "USDJPY": "USDJPY", "USD": "USDJPY"}
    want = aliases.get(token, token)
    for sym in by_symbol:
        if sym == want or sym == token:
            return sym
    return None


def _status_multi(runners, guard=None) -> str:
    """Account-wide status: equity + every open position across symbols."""
    broker0 = runners[0][1]
    equity = broker0.equity()
    lines = [f"\U0001F4B0 equity {equity:.2f}"]
    if guard is not None:
        if guard.blown:
            lines.append("\U0001F6D1 TOTAL-LOSS HALT active — trading stopped")
        elif guard.halted:
            lines.append("⏸️ daily loss halt active — no new trades today")
    any_open = False
    for cfg, broker in runners:
        dp = _price_dp(cfg)
        positions = broker.open_positions()
        if not positions:
            lines.append(f"• {cfg.symbol} ({cfg.strategy}): flat")
            continue
        any_open = True
        for p in positions:
            lines.append(f"• {cfg.symbol} {p.side.upper()} {p.lots} @ "
                         f"{p.entry_price:.{dp}f} (sl {p.sl:.{dp}f}, ticket {p.ticket})")
    if not any_open:
        lines.append("(all flat)")
    return "\n".join(lines)


def run_command_multi(runners, guard, text: str) -> str:
    """Execute one command across several running strategies. `runners` is a list
    of (Config, Broker). Returns a reply string. Deliberately bypasses strategy +
    RiskGuard for manual buy/sell/close (a plumbing control), same as run_command."""
    by_symbol = {cfg.symbol: (cfg, broker) for cfg, broker in runners}
    syms = " / ".join(f"{c.symbol}" for c, _ in runners)
    help_text = _help_multi(runners)

    parts = text.strip().lstrip("/").lower().split()
    if not parts:
        return help_text
    cmd, arg = parts[0], (parts[1] if len(parts) > 1 else None)

    if cmd in ("help", "commands", "start"):
        return help_text
    if cmd in ("status",):
        return _status_multi(runners, guard)
    if cmd in ("positions", "pos"):
        return _status_multi(runners, guard)
    if cmd in ("risk", "limits"):
        broker0 = runners[0][1]
        cfg0 = runners[0][0]
        equity = broker0.equity()
        base = cfg0.loss_baseline or 10_000.0
        daily_cap = cfg0.daily_loss_halt * base
        total_cap = cfg0.total_loss_halt * base
        down_total = base - equity
        return (f"\U0001F6E1 risk vs limits (baseline {base:.0f}):\n"
                f"• equity {equity:.2f}  (from {base:.0f}: {equity-base:+.2f})\n"
                f"• daily stop -{daily_cap:.0f} | total stop -{total_cap:.0f}\n"
                f"• total used so far: {down_total:+.2f} of -{total_cap:.0f}")

    if cmd in ("buy", "sell"):
        if not arg:
            return f"which symbol? e.g. `{cmd} gold` or `{cmd} usdjpy`.\nsymbols: {syms}"
        sym = _resolve(arg, by_symbol)
        if sym is None:
            return f"unknown symbol '{arg}'. symbols: {syms}"
        cfg, broker = by_symbol[sym]
        side = "long" if cmd == "buy" else "short"
        dp = _price_dp(cfg)
        pos = broker.open_position(side, LOTS_DEFAULT, 0.0, 0.0)
        return (f"OPENED {side.upper()} {pos.lots} {sym} @ {pos.entry_price:.{dp}f} "
                f"(ticket {pos.ticket}). Send `close {sym.lower()}` when done.")

    if cmd in ("close", "closeall", "flat"):
        targets = runners if (arg in ("all", None) or cmd in ("closeall", "flat")) \
            else None
        if targets is None:
            sym = _resolve(arg, by_symbol)
            if sym is None:
                return f"unknown symbol '{arg}'. symbols: {syms}, or `close all`."
            targets = [by_symbol[sym]]
        lines, total, n = [], 0.0, 0
        for cfg, broker in targets:
            dp = _price_dp(cfg)
            for pos in broker.open_positions():
                profit = broker.close_position(pos)
                total += profit
                n += 1
                lines.append(f"closed {cfg.symbol} {pos.side.upper()} {pos.lots} @ "
                             f"{pos.entry_price:.{dp}f} | P/L {profit:+.2f}")
        if not n:
            return "nothing to close — all flat."
        lines.append(f"closed {n} position(s) | total P/L {total:+.2f}")
        return "\n".join(lines)

    return f"unknown command '{cmd}'.\n{help_text}"

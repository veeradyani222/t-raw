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

"""Simulated broker + backtest runner.

Deliberately simple model: entries at the signal bar's close plus spread,
SL/TP checked against each subsequent bar's high/low (SL wins ties —
pessimistic). Good enough to prove the pipeline; not a research-grade tester.

Every run collects two record streams:
- trades: one dict per closed position, enriched with entry time, bars held,
  R multiple, equity after, and the strategy's diagnostics (box levels,
  volume ratio, structure state) captured at entry.
- events: the engine's "blocked"/"skipped" reports — signals that existed
  but did not become trades, and why.
"""
import logging
from dataclasses import dataclass, field

import pandas as pd

from .broker import Position
from .config import Config
from .engine import on_bar
from .risk import RiskGuard

log = logging.getLogger("trader")


class SimBroker:
    def __init__(self, history: pd.DataFrame, cfg: Config, starting_equity: float = 10_000.0):
        self.history = history.reset_index(drop=True)
        self.cfg = cfg
        self._equity = starting_equity
        self.cursor = 0  # index of the latest closed bar visible to the strategy
        self.positions: list[Position] = []
        self.trades: list[dict] = []
        self.events: list[dict] = []
        self._entry_info: dict[int, dict] = {}  # ticket -> entry-time context
        self._next_ticket = 1

    # --- Broker interface -------------------------------------------------
    def candles(self, count: int) -> pd.DataFrame:
        start = max(0, self.cursor + 1 - count)
        return self.history.iloc[start:self.cursor + 1]

    def equity(self) -> float:
        return self._equity

    def open_positions(self) -> list[Position]:
        return list(self.positions)

    def open_position(self, side: str, lots: float, sl: float, tp: float) -> Position:
        price = self.history["close"].iloc[self.cursor]
        spread = self.cfg.spread_pips * self.cfg.pip_size
        entry = price + spread if side == "long" else price - spread
        pos = Position(side, lots, entry, sl, tp, ticket=self._next_ticket)
        self._next_ticket += 1
        self.positions.append(pos)
        self._entry_info[pos.ticket] = {
            "entry_time": self.history["time"].iloc[self.cursor],
            "entry_bar": self.cursor,
            "risk_amount": abs(entry - sl) / self.cfg.pip_size
                           * self.cfg.pip_value_per_lot * lots,
            "meta": {},
        }
        return pos

    def close_position(self, position: Position) -> float:
        price = self.history["close"].iloc[self.cursor]
        return self._settle(position, price, "signal")

    # --- Simulation internals --------------------------------------------
    def attach_meta(self, ticket: int, meta: dict) -> None:
        if ticket in self._entry_info:
            self._entry_info[ticket]["meta"] = meta

    def _settle(self, pos: Position, price: float, reason: str) -> float:
        pips = (price - pos.entry_price) / self.cfg.pip_size
        if pos.side == "short":
            pips = -pips
        profit = pips * self.cfg.pip_value_per_lot * pos.lots
        self._equity += profit
        self.positions.remove(pos)
        info = self._entry_info.pop(pos.ticket, {})
        risk = info.get("risk_amount", 0.0)
        self.trades.append({
            "time": self.history["time"].iloc[self.cursor],
            "side": pos.side, "lots": pos.lots, "entry": pos.entry_price,
            "exit": price, "profit": profit, "reason": reason,
            "sl": pos.sl, "tp": pos.tp,
            "entry_time": info.get("entry_time"),
            "bars_held": self.cursor - info.get("entry_bar", self.cursor),
            "r_multiple": profit / risk if risk > 0 else float("nan"),
            "equity_after": self._equity,
            **info.get("meta", {}),
        })
        return profit

    def check_stops(self) -> None:
        """Called after the cursor advances: fill SL/TP against the new bar."""
        bar = self.history.iloc[self.cursor]
        for pos in list(self.positions):
            if pos.side == "long":
                if bar["low"] <= pos.sl:
                    self._settle(pos, pos.sl, "sl")
                elif bar["high"] >= pos.tp:
                    self._settle(pos, pos.tp, "tp")
            else:
                if bar["high"] >= pos.sl:
                    self._settle(pos, pos.sl, "sl")
                elif bar["low"] <= pos.tp:
                    self._settle(pos, pos.tp, "tp")


def run_backtest(history: pd.DataFrame, cfg: Config,
                 starting_equity: float = 10_000.0) -> dict:
    broker = SimBroker(history, cfg, starting_equity)
    guard = RiskGuard(cfg.max_open_positions, cfg.daily_loss_halt,
                      cfg.max_drawdown_halt, cfg.loss_baseline,
                      cfg.total_loss_halt)

    blown_at = None
    for i in range(len(history)):
        broker.cursor = i
        broker.check_stops()
        event = on_bar(broker, guard, cfg)
        if guard.blown and blown_at is None:
            blown_at = history["time"].iloc[i]
        if event is None:
            continue
        if event["kind"] == "open":
            broker.attach_meta(event["ticket"], event.get("meta", {}))
        else:
            broker.events.append(event)

    # Mark any position still open to the last close.
    for pos in list(broker.positions):
        broker._settle(pos, history["close"].iloc[-1], "end")

    trades = pd.DataFrame(broker.trades)
    wins = int((trades["profit"] > 0).sum()) if not trades.empty else 0
    if trades.empty:
        max_dd = 0.0
    else:
        eq = starting_equity + trades["profit"].cumsum()
        max_dd = float((eq - eq.cummax()).min())
    return {
        "bars": len(history),
        "trades": len(trades),
        "wins": wins,
        "win_rate": wins / len(trades) if len(trades) else 0.0,
        "net_profit": float(trades["profit"].sum()) if not trades.empty else 0.0,
        "max_drawdown": max_dd,
        "blown_at": blown_at,
        "final_equity": broker.equity(),
        "trade_log": trades,
        "events": pd.DataFrame(broker.events),
    }

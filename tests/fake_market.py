"""A replay broker for trader.multi: serves cached research bars one closed
bar at a time and fills orders with harness.simulate's fill model (entry at
close + spread + slippage, stop first when stop and target touch in one bar,
gap through the stop fills at the open). What the runner decides is the thing
under test; this just plays the part of MT5 faithfully."""
from __future__ import annotations

import math

import pandas as pd

from research.prop import harness as H
from trader.multi import LivePos, TF_MINUTES


class FakeMarket:
    def __init__(self, frames: dict[str, pd.DataFrame], tf: str, start_index: int,
                 balance: float = 10_000.0):
        """frames: broker symbol -> full bar frame (time, o, h, l, c, tick_volume,
        spread, conv). `start_index` = cursor into the PRIMARY frame (first key)."""
        self.frames = frames
        self.primary = next(iter(frames))
        self.tf = tf
        self.i = start_index
        self.balance = balance
        self.book: dict[int, LivePos] = {}
        self.closes: list[dict] = []
        self._ticket = 1000

    # ----------------------------------------------------------- helpers
    @property
    def now(self) -> pd.Timestamp:
        return pd.Timestamp(self.frames[self.primary]["time"].iloc[self.i])

    def _row(self, symbol: str):
        return self.frames[symbol].iloc[self.i]

    def _spec(self, symbol):
        spec = H._spec().get(symbol, {})
        contract = float(spec.get("contract", 100.0 if symbol == "XAUUSD" else 100000.0))
        comm = 0.0 if symbol in H.INDICES else H.COMMISSION_RT
        return contract, comm, 0.1 * H._pip(symbol)

    def _pnl(self, p: LivePos, price: float) -> float:
        contract, comm, _ = self._spec(p.symbol)
        conv = float(self._row(p.symbol)["conv"])
        d = (price - p.entry) if p.side == "long" else (p.entry - price)
        return d * contract * p.lots * conv - comm * p.lots

    def _settle(self, p: LivePos, price: float, reason: str):
        pnl = self._pnl(p, price)
        self.balance += pnl
        self.closes.append(dict(ticket=p.ticket, magic=p.magic, time=self.now, price=price,
                                reason=reason, pnl=pnl))
        del self.book[p.ticket]
        return pnl

    # ----------------------------------------------------------- replay
    def advance(self):
        """Move to the next closed bar and let the 'broker' fill stops/targets
        on it, the way the harness checks them."""
        self.i += 1
        for p in list(self.book.values()):
            r = self._row(p.symbol)
            o, h, l = float(r["open"]), float(r["high"]), float(r["low"])
            _, _, slip = self._spec(p.symbol)
            long_ = p.side == "long"
            if p.sl and ((long_ and o <= p.sl) or (not long_ and o >= p.sl)):
                self._settle(p, o - slip if long_ else o + slip, "gap_sl")
            elif p.sl and ((long_ and l <= p.sl) or (not long_ and h >= p.sl)):
                self._settle(p, p.sl - slip if long_ else p.sl + slip, "sl")
            elif p.tp and ((long_ and h >= p.tp) or (not long_ and l <= p.tp)):
                self._settle(p, p.tp, "tp")

    # ----------------------------------------------------------- Market API
    def rates(self, symbol, tf, count):
        df = self.frames[symbol]
        if tf == "D1" and self.tf != "D1":
            # the bot's minimum sizing stop asks for completed D1 bars
            past = df[df["time"] < self.now.normalize()]
            d = past.groupby(past["time"].dt.normalize()).agg(
                open=("open", "first"), high=("high", "max"), low=("low", "min"),
                close=("close", "last"), tick_volume=("tick_volume", "sum"), spread=("spread", "max"))
            d = d.tail(count).reset_index().rename(columns={"time": "time"})
            return d[["time", "open", "high", "low", "close", "tick_volume", "spread"]]
        if symbol == self.primary:
            lo = max(0, self.i - count + 1)
            return df.iloc[lo:self.i + 1][["time", "open", "high", "low", "close",
                                           "tick_volume", "spread"]].reset_index(drop=True)
        k = df["time"].searchsorted(self.now, side="right")
        return df.iloc[max(0, k - count):k][["time", "open", "high", "low", "close",
                                             "tick_volume", "spread"]].reset_index(drop=True)

    def tick_time(self, symbol):
        return self.now + pd.Timedelta(minutes=TF_MINUTES[self.tf])

    def account(self):
        floating = sum(self._pnl(p, float(self._row(p.symbol)["close"]))
                       for p in self.book.values())
        return self.balance + floating, self.balance

    def positions(self):
        return list(self.book.values())

    def open(self, symbol, side, lots, sl, tp, magic, comment):
        r = self._row(symbol)
        spec = H._spec().get(symbol, {})
        point = float(spec.get("point", 0.01))
        _, _, slip = self._spec(symbol)
        sp = max(H.SPREAD_FLOOR.get(symbol, 0.0), float(r["spread"]) * point)
        c = float(r["close"])
        price = c + sp + slip if side == "long" else c - sp - slip
        self._ticket += 1
        p = LivePos(self._ticket, symbol, magic, side, lots, price, sl, tp or 0.0,
                    self.now + pd.Timedelta(minutes=TF_MINUTES[self.tf]))
        self.book[p.ticket] = p
        return p

    def close(self, pos, comment):
        p = self.book[pos.ticket]
        _, _, slip = self._spec(p.symbol)
        c = float(self._row(p.symbol)["close"])
        return self._settle(p, c - slip if p.side == "long" else c + slip, comment.split()[-1])

    def modify(self, pos, sl, tp):
        p = self.book[pos.ticket]
        p.sl, p.tp = sl, tp

    def cancel_pending(self):
        return 0

    def realized_since(self, t):
        return sum(c["pnl"] for c in self.closes if c["time"] >= t)

    def balance_at(self, t):
        return self.balance - sum(c["pnl"] for c in self.closes if c["time"] >= t)

    def symbol_spec(self, symbol):
        s = dict(H._spec().get(symbol, {}))
        s.setdefault("trade_mode_ok", True)
        return s

"""Tests for run_command_multi — the multi-symbol Telegram command dispatcher
(gold + usdjpy on one account). Driven against fake brokers, no live MT5."""
from trader.commands import run_command_multi
from trader.broker import Position
from trader.config import Config


GOLD = Config(symbol="XAUUSD", timeframe="H1", strategy="orb",
              pip_size=0.1, pip_value_per_lot=10.0, loss_baseline=10_000.0,
              daily_loss_halt=0.03, total_loss_halt=0.06)
USDJPY = Config(symbol="USDJPY", timeframe="H1", strategy="session",
                pip_size=0.01, pip_value_per_lot=10.0, loss_baseline=10_000.0,
                daily_loss_halt=0.03, total_loss_halt=0.06)


class FakeBroker:
    def __init__(self, symbol, positions=None, equity=10_000.0, close_profit=3.0):
        self.symbol = symbol
        self._positions = list(positions or [])
        self._equity = equity
        self._close_profit = close_profit
        self.opened, self.closed = [], []

    def equity(self):
        return self._equity

    def open_positions(self):
        return list(self._positions)

    def open_position(self, side, lots, sl, tp):
        pos = Position(side=side, lots=lots, entry_price=150.0 if self.symbol == "USDJPY" else 4300.0,
                       sl=sl, tp=tp, ticket=100 + len(self.opened))
        self.opened.append(pos)
        self._positions.append(pos)
        return pos

    def close_position(self, position):
        self.closed.append(position)
        self._positions = [p for p in self._positions if p.ticket != position.ticket]
        return self._close_profit


class Guard:
    blown = False
    halted = False


def runners(gold_pos=None, jpy_pos=None):
    return [(GOLD, FakeBroker("XAUUSD", gold_pos)),
            (USDJPY, FakeBroker("USDJPY", jpy_pos))]


def test_buy_gold_opens_only_on_gold():
    r = runners()
    reply = run_command_multi(r, Guard(), "buy gold")
    assert len(r[0][1].opened) == 1 and r[0][1].opened[0].side == "long"
    assert r[1][1].opened == []
    assert "XAUUSD" in reply


def test_buy_usdjpy_alias_resolves():
    r = runners()
    run_command_multi(r, Guard(), "buy jpy")
    assert len(r[1][1].opened) == 1
    assert r[0][1].opened == []


def test_buy_without_symbol_asks_and_does_not_trade():
    r = runners()
    reply = run_command_multi(r, Guard(), "buy")
    assert r[0][1].opened == [] and r[1][1].opened == []
    assert "which symbol" in reply.lower()


def test_close_one_symbol_only():
    r = runners(gold_pos=[Position("long", 0.01, 4300.0, 0.0, 0.0, ticket=1)],
                jpy_pos=[Position("long", 0.01, 150.0, 0.0, 0.0, ticket=2)])
    reply = run_command_multi(r, Guard(), "close usdjpy")
    assert len(r[1][1].closed) == 1        # usdjpy closed
    assert r[0][1].closed == []            # gold untouched
    assert "USDJPY" in reply


def test_close_all_closes_everything():
    r = runners(gold_pos=[Position("long", 0.01, 4300.0, 0.0, 0.0, ticket=1)],
                jpy_pos=[Position("long", 0.01, 150.0, 0.0, 0.0, ticket=2)])
    reply = run_command_multi(r, Guard(), "close all")
    assert len(r[0][1].closed) == 1 and len(r[1][1].closed) == 1
    assert "total P/L" in reply


def test_status_lists_both_symbols_and_equity():
    r = runners(jpy_pos=[Position("long", 0.01, 150.0, 149.0, 0.0, ticket=9)])
    reply = run_command_multi(r, Guard(), "status")
    assert "XAUUSD" in reply and "USDJPY" in reply
    assert "equity" in reply.lower()


def test_risk_reports_limits():
    reply = run_command_multi(runners(), Guard(), "risk")
    assert "-300" in reply and "-600" in reply     # daily $300, total $600


def test_unknown_symbol_is_rejected_without_trading():
    r = runners()
    reply = run_command_multi(r, Guard(), "buy silver")
    assert r[0][1].opened == [] and r[1][1].opened == []
    assert "unknown symbol" in reply.lower()

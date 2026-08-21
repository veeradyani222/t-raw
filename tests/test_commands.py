"""Tests for trader.commands.run_command — the shared buy/sell/close/status/help
logic behind both the manual_trade CLI and the Telegram listener. Driven against
a fake broker so the order path is verified without a live MT5 terminal."""
from trader.commands import HELP, run_command
from trader.broker import Position
from trader.config import Config

CFG = Config(symbol="XAUUSD", timeframe="H1", pip_size=0.1, pip_value_per_lot=10.0)


class FakeBroker:
    """Minimal Broker stand-in that records opens/closes."""

    def __init__(self, positions=None, equity=10_000.0, close_profit=0.0):
        self._positions = list(positions or [])
        self._equity = equity
        self._close_profit = close_profit
        self.opened: list[Position] = []
        self.closed: list[Position] = []

    def equity(self):
        return self._equity

    def open_positions(self):
        return list(self._positions)

    def open_position(self, side, lots, sl, tp):
        pos = Position(side=side, lots=lots, entry_price=4300.0, sl=sl, tp=tp,
                       ticket=1000 + len(self.opened))
        self.opened.append(pos)
        self._positions.append(pos)
        return pos

    def close_position(self, position):
        self.closed.append(position)
        self._positions = [p for p in self._positions if p.ticket != position.ticket]
        return self._close_profit


def test_buy_opens_a_long_with_no_stops():
    broker = FakeBroker()
    reply = run_command(broker, CFG, "buy")
    assert len(broker.opened) == 1
    pos = broker.opened[0]
    assert pos.side == "long" and pos.lots == 0.01
    assert pos.sl == 0.0 and pos.tp == 0.0        # reachability ping — no SL/TP
    assert "OPENED LONG" in reply


def test_sell_opens_a_short():
    broker = FakeBroker()
    run_command(broker, CFG, "sell", 0.02)
    assert broker.opened[0].side == "short"
    assert broker.opened[0].lots == 0.02


def test_leading_slash_and_case_are_ignored():
    broker = FakeBroker()
    run_command(broker, CFG, "/BUY")
    assert broker.opened[0].side == "long"


def test_close_closes_every_open_position_and_sums_pnl():
    positions = [
        Position("long", 0.01, 4300.0, 0.0, 0.0, ticket=1),
        Position("short", 0.01, 4310.0, 0.0, 0.0, ticket=2),
    ]
    broker = FakeBroker(positions=positions, close_profit=5.0)
    reply = run_command(broker, CFG, "close")
    assert len(broker.closed) == 2
    assert broker.open_positions() == []
    assert "total P/L +10.00" in reply


def test_close_when_flat_reports_nothing_to_close():
    broker = FakeBroker()
    reply = run_command(broker, CFG, "close")
    assert broker.closed == []
    assert "nothing to close" in reply


def test_status_flat():
    broker = FakeBroker(equity=9_998.5)
    reply = run_command(broker, CFG, "status")
    assert "flat" in reply and "9998.50" in reply


def test_status_lists_open_positions():
    broker = FakeBroker(positions=[Position("long", 0.01, 4300.0, 0.0, 0.0, ticket=7)])
    reply = run_command(broker, CFG, "status")
    assert "1 open" in reply and "ticket 7" in reply


def test_help_lists_commands():
    assert run_command(FakeBroker(), CFG, "help") == HELP


def test_unknown_command_returns_help_without_trading():
    broker = FakeBroker()
    reply = run_command(broker, CFG, "frobnicate")
    assert broker.opened == [] and broker.closed == []
    assert "unknown command" in reply and "buy" in reply

"""Review fixes: the day baseline fails CLOSED, and a close-all that leaves a position open
keeps that strategy's state and retries on the next poll."""
import pandas as pd

from trader import multi


class Mkt:
    def __init__(self):
        self.fail_history = True
        self.positions_ = []
        self.closed = []
        self.equity = 5000.0
        self.balance = 5000.0

    def account(self):
        return self.equity, self.balance

    def realized_since(self, t):
        if self.fail_history:
            raise RuntimeError("history_deals_get failed")
        return 0.0

    def positions(self):
        return list(self.positions_)

    def close(self, p, comment):
        if getattr(p, "stuck", False):
            raise RuntimeError("requote")
        self.positions_.remove(p); self.closed.append(p.ticket)
        return -10.0

    def cancel_pending(self):
        return 0

    def tick_time(self, s):
        return pd.Timestamp("2026-11-03 10:00")


def _runner(tmp_path, mkt):
    r = multi.MultiRunner(mkt, [], {}, state_path=tmp_path / "s.json", window=50,
                          guard=multi.AccountGuard(daily_stop=150.0, floor=4650.0))
    return r


def test_history_failure_blocks_new_trades_until_it_is_readable(tmp_path, monkeypatch):
    mkt = Mkt(); r = _runner(tmp_path, mkt)
    mkt.balance = 4860.0; mkt.equity = 4860.0            # restarted after a -$140 morning
    r.check_guard(pd.Timestamp("2026-11-03 11:00"))
    ok, why = r.guard.may_open()
    assert not ok and "day-start" in why
    mkt.fail_history = False
    mkt.realized_since = lambda t: -140.0
    r.check_guard(pd.Timestamp("2026-11-03 11:01"))
    assert r.guard.may_open()[0] and r.guard.day_start_balance == 5000.0
    mkt.equity = 4849.0                                   # now -151 on the true baseline -> stop
    ev = r.check_guard(pd.Timestamp("2026-11-03 11:02"))
    assert "daily_stop" in ev and r.guard.blocked


def test_close_everything_keeps_state_of_a_position_that_did_not_close(tmp_path):
    mkt = Mkt(); mkt.fail_history = False; r = _runner(tmp_path, mkt)
    spec = multi.StrategySpec(0, "m", "f", {}, "XAUUSD", "H1", 0.01)
    r.specs = [spec]; r.states = {0: multi.StratState(ticket=7, side="long", entry=1.0, sl=0.9, sl0=0.9, lots=0.1)}
    good = multi.LivePos(8, "EURUSD", 520001, "long", 0.1, 1.1, 1.0, 0.0, pd.Timestamp("2026-11-03"))
    stuck = multi.LivePos(7, "XAUUSD", 520000, "long", 0.1, 1.0, 0.9, 0.0, pd.Timestamp("2026-11-03")); stuck.stuck = True
    mkt.positions_ = [good, stuck]
    n = r.close_everything("daily_stop")
    assert n == 1 and mkt.closed == [8]
    assert r.states[0].open and r.states[0].ticket == 7      # not forgotten
    stuck.stuck = False
    r.guard.blocked_day = r.guard.day = "2026-11-03"
    r.poll()                                                  # blocked day + open state -> retry
    assert mkt.closed == [8, 7] and not r.states[0].open

"""The account-wide guard: $300 floating loss on the server day closes
everything and blocks entries until the next server day; equity at the
$9,300 floor halts for good. Pure tests plus a runner-level one on the replay
broker so the close-all path (all magics, pending orders) is exercised."""
import pandas as pd

from trader import multi
from trader.multi import AccountGuard, LivePos


def T(s):
    return pd.Timestamp(s)


def test_daily_stop_blocks_until_next_server_day():
    g = AccountGuard()
    assert g.update(T("2026-10-20 00:05"), 10_000, 10_000) == ["new_day"]
    assert g.update(T("2026-10-20 09:00"), 9_720, 10_000) == []          # -280: fine
    assert g.update(T("2026-10-20 09:10"), 9_700, 10_000) == ["daily_stop"]
    assert g.blocked and g.may_open()[0] is False
    assert g.update(T("2026-10-20 15:00"), 9_650, 9_700) == ["scale_on"]  # once per day (9,650 < 9,700 halves size)
    assert g.update(T("2026-10-20 23:59"), 9_900, 9_700) == []            # recovery does not unblock
    assert g.blocked
    ev = g.update(T("2026-10-21 00:00"), 9_700, 9_700)                     # server day rolls
    assert ev == ["new_day"] and not g.blocked and g.day_start_balance == 9_700


def test_daily_stop_measures_floating_equity_from_day_start_balance():
    g = AccountGuard()
    g.update(T("2026-10-20 00:00"), 10_050, 10_000)        # equity above balance at 00:00
    assert g.update(T("2026-10-20 10:00"), 9_700.0, 10_000) == ["daily_stop"]


def test_day_start_balance_can_be_supplied_on_restart():
    g = AccountGuard()
    # restarted at noon with balance 9,900 after -100 already realised today: true 00:00 balance 10,000
    g.update(T("2026-10-20 12:00"), 9_900, 9_900, day_start_balance=10_000)
    assert g.day_start_balance == 10_000
    assert g.update(T("2026-10-20 12:01"), 9_700, 9_900) == ["daily_stop"]


def test_floor_is_permanent():
    g = AccountGuard()
    g.update(T("2026-10-20 00:00"), 10_000, 10_000)
    assert "blown" in g.update(T("2026-10-20 10:00"), 9_300, 9_400)
    g.update(T("2026-10-25 00:00"), 9_800, 9_800)
    assert g.blown and g.may_open()[0] is False
    assert "permanent" in g.may_open()[1]


def test_guard_state_round_trips():
    g = AccountGuard()
    g.update(T("2026-10-20 00:00"), 10_000, 10_000)
    g.update(T("2026-10-20 01:00"), 9_690, 10_000)
    g2 = AccountGuard.from_dict(g.to_dict())
    assert g2.blocked_day == "2026-10-20" and g2.day_start_balance == 10_000 and not g2.blown


class StubMarket:
    """Just enough broker for the close-all path: positions under several
    magics, a pending order, equity we can push around."""
    def __init__(self):
        self.equity, self.balance = 10_000.0, 10_000.0
        self.book = {1: LivePos(1, "XAUUSD", 500_001, "long", 0.1, 4000, 3990, 0, T("2026-10-20 01:00")),
                     2: LivePos(2, "XAUUSD", 500_020, "short", 0.2, 4000, 4010, 0, T("2026-10-20 01:00")),
                     3: LivePos(3, "EURUSD", 424242, "long", 0.5, 1.1, 1.09, 0, T("2026-10-20 01:00"))}
        self.pending = 1
        self.closed = []

    def rates(self, symbol, tf, count):
        return pd.DataFrame()
    def tick_time(self, symbol):
        return T("2026-10-20 10:00")
    def account(self):
        return self.equity, self.balance
    def positions(self):
        return list(self.book.values())
    def open(self, *a, **k):
        raise AssertionError("no entries expected")
    def close(self, pos, comment):
        self.closed.append((pos.ticket, comment))
        del self.book[pos.ticket]
        return -50.0
    def modify(self, pos, sl, tp):
        pass
    def cancel_pending(self):
        n, self.pending = self.pending, 0
        return n
    def realized_since(self, t):
        return 0.0


def test_runner_closes_every_magic_and_pending_on_daily_stop(tmp_path):
    mkt = StubMarket()
    alerts = []
    specs = multi.load_mix()[:2]
    r = multi.MultiRunner(mkt, specs, {}, alert=alerts.append, state_path=tmp_path / "s.json")
    r.states[specs[0].idx].ticket = 1
    assert r.check_guard(T("2026-10-20 09:00")) == ["new_day"]
    mkt.equity = 9_699.0                                  # -301 floating
    assert r.check_guard(T("2026-10-20 09:10")) == ["daily_stop", "scale_on"]
    assert sorted(t for t, _ in mkt.closed) == [1, 2, 3]  # ours, another strategy's, and a foreign magic
    assert mkt.pending == 0
    assert not r.states[specs[0].idx].open
    assert any("DAILY STOP" in a for a in alerts)
    assert r.guard.may_open() == (False, r.guard.may_open()[1]) and r.guard.blocked
    # the state file carries the block across a restart
    r2 = multi.MultiRunner(StubMarket(), specs, {}, state_path=tmp_path / "s.json")
    assert r2.guard.blocked_day == "2026-10-20"


def test_runner_permanent_halt_at_floor(tmp_path):
    mkt = StubMarket()
    alerts = []
    r = multi.MultiRunner(mkt, multi.load_mix()[:1], {}, alert=alerts.append, state_path=tmp_path / "s.json")
    r.check_guard(T("2026-10-20 09:00"))
    mkt.equity = 9_250.0
    ev = r.check_guard(T("2026-10-20 09:10"))
    assert "blown" in ev and "daily_stop" in ev
    assert len(mkt.closed) == 3 and r.guard.blown
    assert any("PERMANENT HALT" in a for a in alerts)

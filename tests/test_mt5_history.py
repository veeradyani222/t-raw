"""The MT5 adapter's history calls must hand the C extension what it accepts:
naive datetimes between 2000-01-01 and now + 1 day. A fake mt5 module stands
in for the terminal and raises on anything else (which is what the real one
does, as 'returned a result with an exception set')."""
from collections import namedtuple
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from trader import mt5_market
from trader.mt5_market import MT5Market, _history_dt

Deal = namedtuple("Deal", "time profit swap commission type")


def E(s):
    return int(pd.Timestamp(s).timestamp())


class FakeMT5:
    DEAL_TYPE_BUY, DEAL_TYPE_SELL = 0, 1

    def __init__(self, deals):
        self.deals = deals
        self.calls = []

    def history_deals_get(self, a, b):
        self.calls.append((a, b))
        for x in (a, b):
            if not isinstance(x, datetime) or x.tzinfo is not None or x.year < 1970 \
                    or x > datetime.now() + timedelta(days=2):
                raise SystemError("<built-in function history_deals_get> returned a result with an exception set")
        lo, hi = a.timestamp(), b.timestamp()
        return [d for d in self.deals if lo <= d.time < hi]

    def last_error(self):
        return (0, "ok")


@pytest.fixture
def fake(monkeypatch):
    deals = [Deal(E("2026-10-20 15:50"), 10_000.0, 0.0, 0.0, 2),
             Deal(E("2026-10-22 09:00"), -300.0, 0.0, -14.0, 0),
             Deal(E("2026-10-23 09:00"), -151.0, 0.0, 0.0, 1)]
    f = FakeMT5(deals)
    monkeypatch.setattr(mt5_market, "mt5", f)
    return f


def test_history_dates_are_naive_and_clamped():
    assert _history_dt(pd.Timestamp("1970-01-01")) == datetime(2000, 1, 1)
    assert _history_dt(pd.Timestamp("2100-01-01")) <= datetime.now() + timedelta(days=1, seconds=1)
    aware = pd.Timestamp("2026-10-01", tz=timezone.utc)
    out = _history_dt(aware)
    assert out.tzinfo is None and out == datetime(2026, 10, 1)
    assert _history_dt(pd.Timestamp("2026-10-01 10:00:00.5")) == datetime(2026, 10, 1, 10)


def test_balance_at_asks_mt5_with_acceptable_dates(fake):
    m = MT5Market()
    assert m.balance_at(pd.Timestamp("2026-10-01")) == 10_000.0          # account younger than the month
    assert m.balance_at(pd.Timestamp("2026-11-01")) == pytest.approx(9_535.0)
    for a, b in fake.calls:
        assert isinstance(a, datetime) and a.tzinfo is None and a.year >= 2000
        assert b <= datetime.now() + timedelta(days=1, seconds=1)


def test_realized_since_uses_the_same_guard(fake):
    m = MT5Market()
    assert m.realized_since(pd.Timestamp("2026-10-22")) == pytest.approx(-465.0)   # 22nd + 23rd within 2 days
    assert m.deals_between(pd.Timestamp("2026-10-25"), pd.Timestamp("2026-10-24")) == []


def test_bad_dates_would_have_raised(fake):
    with pytest.raises(SystemError):
        fake.history_deals_get(datetime(1, 1, 1), datetime.now())
    with pytest.raises(SystemError):
        fake.history_deals_get(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime.now())

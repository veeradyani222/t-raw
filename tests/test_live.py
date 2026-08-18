from trader.live import DAILY_HEARTBEAT_SECONDS, _heartbeat_due


def test_heartbeat_not_due_before_interval():
    assert not _heartbeat_due(now=1_000.0, last=1_000.0, interval=100.0)
    assert not _heartbeat_due(now=1_099.9, last=1_000.0, interval=100.0)


def test_heartbeat_due_at_and_after_interval():
    assert _heartbeat_due(now=1_100.0, last=1_000.0, interval=100.0)   # exactly due
    assert _heartbeat_due(now=9_999.0, last=1_000.0, interval=100.0)   # long overdue


def test_daily_heartbeat_interval_is_24h():
    assert DAILY_HEARTBEAT_SECONDS == 24 * 60 * 60

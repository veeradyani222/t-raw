from datetime import date

from trader.risk import RiskGuard, position_size_lots


def test_sizing_risks_one_percent():
    # 10k equity, 1% risk, 30 pip SL, $10/pip/lot → $100 / $300 = 0.33 lots
    assert position_size_lots(10_000, 0.01, 30, 10) == 0.33


def test_sizing_truncates_never_rounds_up():
    # $100 / $290 = 0.3448 → 0.34, not 0.35
    assert position_size_lots(10_000, 0.01, 29, 10) == 0.34


def test_sizing_zero_when_below_min_lot():
    assert position_size_lots(100, 0.01, 30, 10) == 0.0


def test_sizing_capped_at_max_lot():
    assert position_size_lots(1_000_000, 0.01, 30, 10, max_lot=1.0) == 1.0


def test_max_positions_blocks():
    guard = RiskGuard(max_open_positions=1, daily_loss_halt=0.03)
    guard.on_new_bar(date(2026, 1, 5), 10_000)
    assert guard.may_open(0) == (True, "")
    allowed, reason = guard.may_open(1)
    assert not allowed and "max open positions" in reason


def test_daily_loss_halt_trips_and_resets_next_day():
    guard = RiskGuard(max_open_positions=1, daily_loss_halt=0.03)
    d = date(2026, 1, 5)
    guard.on_new_bar(d, 10_000)
    guard.on_new_bar(d, 9_800)      # -2%: fine
    assert guard.may_open(0)[0]
    guard.on_new_bar(d, 9_690)      # -3.1%: halt
    assert not guard.may_open(0)[0]
    guard.on_new_bar(d, 9_900)      # recovery same day: still halted
    assert not guard.may_open(0)[0]
    guard.on_new_bar(date(2026, 1, 6), 9_690)  # new day: reset
    assert guard.may_open(0)[0]


def test_max_drawdown_halt_is_permanent():
    guard = RiskGuard(max_open_positions=1, daily_loss_halt=0.02,
                      max_drawdown_halt=0.05)
    guard.on_new_bar(date(2026, 1, 5), 500.0)     # peak = 500
    assert guard.may_open(0) == (True, "")
    guard.on_new_bar(date(2026, 1, 6), 476.0)     # -4.8% from peak: still alive
    assert guard.may_open(0)[0]
    guard.on_new_bar(date(2026, 1, 7), 475.0)     # -5.0%: breached
    allowed, reason = guard.may_open(0)
    assert not allowed and "drawdown" in reason
    guard.on_new_bar(date(2026, 2, 2), 600.0)     # recovery does NOT revive it
    assert not guard.may_open(0)[0]
    assert guard.blown


def test_max_drawdown_tracks_the_peak_not_the_start():
    guard = RiskGuard(max_open_positions=1, daily_loss_halt=0.02,
                      max_drawdown_halt=0.05)
    guard.on_new_bar(date(2026, 1, 5), 500.0)
    guard.on_new_bar(date(2026, 1, 6), 600.0)     # new peak
    guard.on_new_bar(date(2026, 1, 7), 570.0)     # -5% from 600, above start
    assert guard.blown


def test_max_drawdown_disabled_by_default():
    guard = RiskGuard(max_open_positions=1, daily_loss_halt=0.02)
    guard.on_new_bar(date(2026, 1, 5), 500.0)
    guard.on_new_bar(date(2026, 1, 6), 100.0)     # -80%, rule off
    assert not guard.blown

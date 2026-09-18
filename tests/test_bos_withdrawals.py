import pytest

from research.bos_monthly_withdrawals import withdrawal_amount


@pytest.mark.parametrize("balance,opening,policy,expected", [
    (10350., 10000., "above_baseline", 350.),
    (9800., 9600., "above_baseline", 0.),
    (10100., 9600., "above_baseline", 100.),
    (9800., 9600., "positive_month", 200.),
    (9500., 9800., "positive_month", 0.),
    (10350., 10000., "none", 0.),
])
def test_cashout_policy_preserves_loss_carryforward(balance, opening, policy, expected):
    assert withdrawal_amount(balance, opening, policy) == expected


def test_partial_year_excludes_future_bars_and_marks_final_position(monkeypatch, tmp_path):
    import pandas as pd
    from research import bos_monthly_withdrawals as study

    bars = pd.DataFrame(dict(time=pd.to_datetime(["2026-01-13", "2026-01-14", "2026-01-15"]),
                             open=[100., 101., 999.], high=[100., 101., 999.],
                             low=[100., 101., 999.], close=[100., 101., 999.]))
    monkeypatch.setattr(study, "START", pd.Timestamp("2026-01-01"))
    monkeypatch.setattr(study, "END", pd.Timestamp("2026-01-15"))
    monkeypatch.setattr(study, "OUT", tmp_path)
    seen = []

    def open_once(broker, guard, cfg):
        seen.append(broker.cursor)
        if broker.cursor == 0:
            broker.open_position("long", .01, 90., 200.)

    monkeypatch.setattr(study, "on_bar", open_once)
    result, trades = study.replay(bars, "positive_month", quiet=True)
    assert seen == [0, 1]
    assert len(result["monthly"]) == 1
    assert trades.iloc[0]["exit"] == 101.
    assert trades.iloc[0].reason == "end"
    assert result["withdrawals"] == pytest.approx(.70)
    assert result["final_balance"] == pytest.approx(10000.)

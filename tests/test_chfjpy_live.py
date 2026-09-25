"""Offline live-session tests. No terminal connection or real orders."""
from types import SimpleNamespace
from unittest.mock import Mock
import time

import pandas as pd
import pytest

from trader import broker_mt5, live
from trader.broker import Position
from trader.broker_mt5 import MT5Broker, MT5Error
from trader.config import Config
from trader.engine import on_bar
from trader.risk import RiskGuard


@pytest.fixture
def market(monkeypatch):
    now = pd.Timestamp('2026-09-17 01:00:10')
    monkeypatch.setattr(time, 'time', lambda: now.timestamp())
    tick = SimpleNamespace(ask=185.02, bid=185., time=now.timestamp())
    monkeypatch.setattr(broker_mt5.mt5, 'symbol_info_tick', lambda symbol: tick)
    monkeypatch.setattr(broker_mt5.mt5, 'symbol_info', lambda symbol: SimpleNamespace(
        volume_min=.01, volume_max=100., volume_step=.01, trade_tick_size=.001))
    monkeypatch.setattr(broker_mt5.mt5, 'history_deals_get', lambda *args, **kw: ())
    monkeypatch.setattr(broker_mt5.mt5, 'positions_get', lambda **kw: ())
    calc = Mock(side_effect=lambda side, symbol, lots, entry, stop: (stop-entry)*100000/150*lots)
    monkeypatch.setattr(broker_mt5.mt5, 'order_calc_profit', calc)
    cfg = Config(symbol='CHFJPY', timeframe='H1', strategy='session', pip_size=.01)
    return MT5Broker(cfg), tick, calc


def test_session_sizes_from_executable_quote_and_converted_loss(market):
    broker, tick, calc = market
    lots = broker.session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.)
    # 0.202 JPY stop distance incl. two slippage reserves / USDJPY150 + $14 fees.
    assert lots == .67
    assert calc.call_args.args[:3] == (broker_mt5.mt5.ORDER_TYPE_BUY, 'CHFJPY', 1.)
    assert calc.call_args.args[3:] == pytest.approx((185.021, 184.819))


def test_session_respects_broker_step_and_cap(market, monkeypatch):
    broker, _, _ = market
    monkeypatch.setattr(broker_mt5.mt5, 'symbol_info', lambda symbol: SimpleNamespace(
        volume_min=.1, volume_max=.55, volume_step=.1))
    assert broker.session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == .5


@pytest.mark.parametrize('equity', [0., 1., float('nan')])
def test_session_does_not_round_up_minimum_lot(market, equity):
    assert market[0].session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, equity) == 0.


def test_session_skips_old_signal(market):
    assert market[0].session_entry_lots(pd.Timestamp('2026-09-16'), 184.82, 10000.) == 0.


def test_session_does_not_reenter_after_restart_and_stop(market, monkeypatch):
    monkeypatch.setattr(broker_mt5.mt5, 'history_deals_get', lambda *args: (
        SimpleNamespace(symbol='CHFJPY', entry=broker_mt5.mt5.DEAL_ENTRY_IN),))
    assert market[0].session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == 0.


def test_session_skips_when_another_symbol_is_open(market, monkeypatch):
    monkeypatch.setattr(broker_mt5.mt5, 'positions_get', lambda **kw: (object(),))
    assert market[0].session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == 0.


@pytest.mark.parametrize('api', ['history_deals_get', 'positions_get', 'order_calc_profit'])
def test_session_fails_closed_on_broker_read_failure(market, monkeypatch, api):
    monkeypatch.setattr(broker_mt5.mt5, api, lambda *args, **kw: None)
    with pytest.raises(MT5Error):
        market[0].session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.)


def test_recovered_position_expires_exactly_twelve_hours_after_entry():
    cfg = SimpleNamespace(strategy='session', session_hold_hours=12, symbol='CHFJPY')
    pos = Position('long', .1, 185., 184., 0., ticket=7,
                   open_time=pd.Timestamp('2026-09-17 01:00:10'))
    broker = Mock()
    broker.open_positions.return_value = [pos]
    broker.market_time.return_value = pd.Timestamp('2026-09-17 13:00:09')
    live._close_expired_positions(cfg, broker)
    broker.close_position.assert_not_called()
    broker.market_time.return_value = pd.Timestamp('2026-09-17 13:00:10')
    live._close_expired_positions(cfg, broker)
    broker.close_position.assert_called_once_with(pos)


def test_expired_close_failure_is_retried_on_next_poll():
    cfg = SimpleNamespace(strategy='session', session_hold_hours=12, symbol='CHFJPY')
    pos = Position('long', .1, 185., 184., 0., open_time=pd.Timestamp('2026-09-16'))
    broker = Mock()
    broker.open_positions.return_value = [pos]
    broker.market_time.return_value = pd.Timestamp('2026-09-17')
    broker.close_position.side_effect = [MT5Error('market closed'), 0.]
    with pytest.raises(MT5Error):
        live._close_expired_positions(cfg, broker)
    live._close_expired_positions(cfg, broker)
    assert broker.close_position.call_count == 2


def test_bos_positions_do_not_get_session_exits():
    broker = Mock()
    live._close_expired_positions(Config(), broker)
    broker.open_positions.assert_not_called()


def session_bars():
    return pd.DataFrame(dict(time=pd.date_range('2026-09-16 10:00', periods=15, freq='h'),
                             open=185., high=185.1, low=184.9, close=185.))


def test_engine_uses_session_broker_sizing(market, monkeypatch):
    broker, _, calc = market
    monkeypatch.setattr(broker, 'candles', lambda count: session_bars())
    monkeypatch.setattr(broker, 'equity', lambda: 10000.)
    opened = Mock(return_value=Position('long', .35, 185.02, 184.6, 0., ticket=5))
    monkeypatch.setattr(broker, 'open_position', opened)
    event = on_bar(broker, RiskGuard(1, .03), broker.cfg)
    assert calc.called
    assert event['kind'] == 'open'
    assert opened.call_args.args[3] == 0.
    assert opened.call_args.args[1] < .4  # USD conversion, not gold's fixed $10/pip


def test_session_does_not_flip_existing_short(market, monkeypatch):
    broker, _, _ = market
    monkeypatch.setattr(broker, 'candles', lambda count: session_bars())
    monkeypatch.setattr(broker, 'equity', lambda: 10000.)
    monkeypatch.setattr(broker, 'open_positions', lambda: [Position('short', .1, 185., 186., 0.)])
    close = Mock()
    monkeypatch.setattr(broker, 'close_position', close)
    event = on_bar(broker, RiskGuard(1, .03), broker.cfg)
    close.assert_not_called()
    assert event['kind'] == 'skipped'


def test_runner_selects_only_chfjpy():
    import run_live
    assert len(run_live.LIVE_CONFIGS) == 1
    cfg = run_live.LIVE_CONFIGS[0]
    assert (cfg.symbol, cfg.timeframe, cfg.strategy) == ('CHFJPY', 'H1', 'session')
    assert (cfg.risk_per_trade, cfg.loss_baseline, cfg.daily_loss_halt, cfg.total_loss_halt) == (.01, 10000., .03, .06)


def test_live_loop_exits_recovered_position_even_with_static_halt(monkeypatch):
    cfg = Config(symbol='CHFJPY', strategy='session', timeframe='H1',
                 loss_baseline=10000., total_loss_halt=.06)
    pos = Position('long', .1, 185., 184., 0., ticket=7,
                   open_time=pd.Timestamp('2026-09-16 01:00'))
    positions = [pos]
    broker = Mock()
    broker.open_positions.side_effect = lambda: positions.copy()
    broker.close_position.side_effect = lambda p: positions.remove(p)
    broker.market_time.return_value = pd.Timestamp('2026-09-17 13:00')
    broker.equity.return_value = 9300.
    broker.candles.return_value = session_bars()
    monkeypatch.setattr(live.broker_mt5, 'connect', lambda cfg: None)
    monkeypatch.setattr(live.broker_mt5, 'shutdown', lambda: None)
    monkeypatch.setattr(live, 'MT5Broker', lambda cfg: broker)
    monkeypatch.setattr(live, 'send_alert', lambda *a, **k: None)
    monkeypatch.setattr(live, 'command_keyboard', lambda *a: None)
    monkeypatch.setattr(live, 'run_command_multi', lambda *a: '')
    monkeypatch.setattr(live, 'fetch_commands', lambda *a: ([], None))
    monkeypatch.setattr(live, '_report_closes', lambda *a: None)
    def check_entry(broker, guard, cfg):
        assert guard.blown
        assert not positions
    monkeypatch.setattr(live, 'on_bar', check_entry)
    def stop_poll(seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(live.time, 'sleep', stop_poll)
    with pytest.raises(KeyboardInterrupt):
        live.run_live([cfg])
    broker.close_position.assert_called_once_with(pos)


@pytest.mark.parametrize('profit', [0., 1., float('nan'), float('inf')])
def test_session_rejects_invalid_stop_valuation(market, profit):
    market[2].side_effect = None
    market[2].return_value = profit
    with pytest.raises(MT5Error):
        market[0].session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.)


def test_session_skips_stale_quote(market, monkeypatch):
    """Stale = the broker's last quote is outside the window after the close."""
    broker, tick, _ = market
    tick.time = pd.Timestamp('2026-09-17 01:01:01').timestamp()
    assert broker.session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == 0.
    tick.time = pd.Timestamp('2026-09-17 00:59:59').timestamp()
    assert broker.session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == 0.


@pytest.mark.parametrize('offset_hours', [3, 2, -5, 0])
def test_session_ignores_wall_clock_vs_broker_clock(market, monkeypatch, offset_hours):
    """MT5 labels broker-local time as UTC, so tick.time sits hours away from
    time.time() on a GMT+3 server. That gap must never veto an entry — it
    skipped every live trade with 'session entry ineligible'."""
    broker, tick, _ = market
    monkeypatch.setattr(time, 'time', lambda: tick.time - offset_hours * 3600)
    assert broker.session_entry_lots(pd.Timestamp('2026-09-17'), 184.82, 10000.) == .67


def _preflight_env(monkeypatch, **over):
    term = SimpleNamespace(connected=True, trade_allowed=True)
    acct = SimpleNamespace(login=1, trade_allowed=True, trade_expert=True)
    sym = SimpleNamespace(trade_mode=broker_mt5.mt5.SYMBOL_TRADE_MODE_FULL,
                          volume_min=.01, volume_max=100., volume_step=.01)
    for k, v in over.items():
        obj, attr = k.split('__')
        setattr({'term': term, 'acct': acct, 'sym': sym}[obj], attr, v)
    monkeypatch.setattr(broker_mt5.mt5, 'terminal_info', lambda: term)
    monkeypatch.setattr(broker_mt5.mt5, 'symbol_info', lambda symbol: sym)
    return acct


def test_preflight_passes_on_a_healthy_terminal(market, monkeypatch):
    acct = _preflight_env(monkeypatch)
    broker_mt5.preflight(market[0].cfg, acct)


@pytest.mark.parametrize('bad, needle', [
    ({'term__trade_allowed': False}, 'Algo Trading'),
    ({'term__connected': False}, 'NOT connected'),
    ({'acct__trade_allowed': False}, 'trading disabled'),
    ({'acct__trade_expert': False}, 'automated'),
    ({'sym__trade_mode': broker_mt5.mt5.SYMBOL_TRADE_MODE_DISABLED}, 'not fully tradable'),
])
def test_preflight_names_what_would_block_orders(market, monkeypatch, bad, needle):
    acct = _preflight_env(monkeypatch, **bad)
    with pytest.raises(MT5Error, match=needle):
        broker_mt5.preflight(market[0].cfg, acct)


def test_session_stop_rounds_down_to_broker_tick_before_sizing(market, monkeypatch):
    broker, _, calc = market
    monkeypatch.setattr(broker_mt5.mt5, 'symbol_info', lambda symbol: SimpleNamespace(
        volume_min=.01, volume_max=100., volume_step=.01, trade_tick_size=.005))
    assert broker.session_stop_price(184.8239) == 184.82
    bars = session_bars()
    bars['low'] = 184.8997
    monkeypatch.setattr(broker, 'candles', lambda count: bars)
    monkeypatch.setattr(broker, 'equity', lambda: 10000.)
    sent = Mock(return_value=SimpleNamespace(price=185.02, order=5))
    monkeypatch.setattr(broker_mt5, '_send_order', sent)
    on_bar(broker, RiskGuard(1, .03), broker.cfg)
    assert sent.call_args.args[0]['sl'] == 184.595
    assert sent.call_args.args[0]['tp'] == 0.
    assert calc.call_args.args[-1] == pytest.approx(184.594)


@pytest.mark.parametrize('gap_days', [0, 2])
def test_midnight_entry_uses_new_day_and_rejects_one_hour_late(market, monkeypatch, gap_days):
    from dataclasses import replace
    broker, tick, _ = market
    broker.cfg = replace(broker.cfg, session_entry_at_open=True)
    now = pd.Timestamp('2026-09-17 00:00:10')
    tick.time = now.timestamp()
    monkeypatch.setattr(time, 'time', lambda: tick.time)
    bars = session_bars()
    bars['time'] -= pd.Timedelta(hours=1, days=gap_days)
    monkeypatch.setattr(broker, 'candles', lambda count: bars)
    monkeypatch.setattr(broker, 'equity', lambda: 10000.)
    opened = Mock(return_value=Position('long', .35, 185.02, 184.6, 0., ticket=5))
    monkeypatch.setattr(broker, 'open_position', opened)
    history = Mock(return_value=())
    monkeypatch.setattr(broker_mt5.mt5, 'history_deals_get', history)
    guard = RiskGuard(1, .03)
    assert on_bar(broker, guard, broker.cfg)['kind'] == 'open'
    assert history.call_args.args[0] == int(now.normalize().timestamp())
    assert guard._day == now.date()
    tick.time += 3600
    assert broker.session_entry_lots(bars.time.iloc[-1], 184.6, 10000.) == 0.

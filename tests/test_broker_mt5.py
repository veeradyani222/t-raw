"""Tests for the order filling-mode selection (broker_mt5._filling_order).
Pure logic — no terminal connection needed."""
import MetaTrader5 as mt5

from trader.broker_mt5 import _filling_order


def test_prefers_ioc_first():
    # Gold fills with IOC → it's tried first, so gold's behavior is unchanged.
    assert _filling_order()[0] == mt5.ORDER_FILLING_IOC


def test_includes_fok_fallback_for_usdjpy():
    # USDJPY rejects IOC (retcode 10030) and needs FOK — it must be in the list.
    assert mt5.ORDER_FILLING_FOK in _filling_order()


def test_return_is_the_last_resort():
    assert _filling_order()[-1] == mt5.ORDER_FILLING_RETURN

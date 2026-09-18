"""BOS stays the research default alongside the restored session strategy."""
import pytest

from trader.config import CONFIG
from trader.strategies import STRATEGIES, get_strategy


def test_bos_and_session_are_registered_but_bos_remains_the_default():
    assert set(STRATEGIES) == {"bos", "session"}
    assert CONFIG.strategy == "bos"
    assert CONFIG.symbol == "XAUUSD"
    assert CONFIG.timeframe == "M30"


@pytest.mark.parametrize("name", ["orb", "sma_cross", "meanrev", "nope"])
def test_removed_and_unknown_strategy_names_are_rejected(name):
    with pytest.raises(ValueError, match="available: bos"):
        get_strategy(name)

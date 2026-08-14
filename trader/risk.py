"""Position sizing and safety rails. Pure logic — no MT5, no I/O."""
from dataclasses import dataclass, field
from datetime import date


def position_size_lots(
    equity: float,
    risk_per_trade: float,
    sl_pips: float,
    pip_value_per_lot: float,
    min_lot: float = 0.01,
    max_lot: float = 1.0,
) -> float:
    """Lots such that hitting the stop loses ~risk_per_trade of equity.

    Returns 0.0 if even the minimum lot would risk more than allowed.
    """
    if equity <= 0 or sl_pips <= 0:
        return 0.0
    risk_amount = equity * risk_per_trade
    lots = risk_amount / (sl_pips * pip_value_per_lot)
    lots = int(lots * 100) / 100  # truncate to 0.01 steps, never round up
    if lots < min_lot:
        return 0.0
    return min(lots, max_lot)


@dataclass
class RiskGuard:
    """Stateful rails checked before every order. Same object is used by
    backtest and live so the rules can't diverge."""

    max_open_positions: int
    daily_loss_halt: float          # e.g. 0.03 = halt at -3% on the day
    max_drawdown_halt: float = 0.0  # e.g. 0.05 = PERMANENT halt at -5% from the
                                    # equity peak (prop-firm style). 0 disables.
    _day: date | None = field(default=None, repr=False)
    _day_start_equity: float = field(default=0.0, repr=False)
    _peak_equity: float = field(default=0.0, repr=False)
    halted: bool = False
    blown: bool = False             # max-drawdown rule breached; never resets

    def on_new_bar(self, today: date, equity: float) -> None:
        """Call once per bar/tick batch. Resets the daily anchor on a new day;
        the peak-drawdown check never resets."""
        if self.max_drawdown_halt > 0:
            self._peak_equity = max(self._peak_equity, equity)
            if equity <= self._peak_equity * (1.0 - self.max_drawdown_halt):
                self.blown = True
        if self._day != today:
            self._day = today
            self._day_start_equity = equity
            self.halted = False
        elif self._day_start_equity > 0:
            drawdown = 1.0 - equity / self._day_start_equity
            if drawdown >= self.daily_loss_halt:
                self.halted = True

    def may_open(self, open_positions: int) -> tuple[bool, str]:
        """(allowed, reason_if_not)."""
        if self.blown:
            return False, "max drawdown halt — account rules breached, trading stopped"
        if self.halted:
            return False, "daily loss halt active"
        if open_positions >= self.max_open_positions:
            return False, f"max open positions ({self.max_open_positions}) reached"
        return True, ""

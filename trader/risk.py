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
    daily_loss_halt: float          # e.g. 0.03. Legacy: fraction of the day's
                                    # START equity. Prop mode (loss_baseline set):
                                    # fraction of the FIXED baseline, i.e. a flat
                                    # dollar cap = daily_loss_halt * loss_baseline.
    max_drawdown_halt: float = 0.0  # e.g. 0.05 = PERMANENT halt at -5% from the
                                    # equity PEAK (trailing). 0 disables.
    loss_baseline: float = 0.0      # prop mode: fixed $ the limits are measured
                                    # against (e.g. 10_000). 0 = legacy % mode.
    total_loss_halt: float = 0.0    # prop mode: fraction of loss_baseline for a
                                    # PERMANENT halt measured STATICALLY from the
                                    # baseline (equity <= baseline*(1-this)). Takes
                                    # precedence over max_drawdown_halt. 0 = off.
    _day: date | None = field(default=None, repr=False)
    _day_start_equity: float = field(default=0.0, repr=False)
    _peak_equity: float = field(default=0.0, repr=False)
    halted: bool = False
    blown: bool = False             # total-loss rule breached; never resets

    def on_new_bar(self, today: date, equity: float) -> None:
        """Call once per bar OR per live poll, with the CURRENT equity (which on
        MT5 includes floating P&L). Resets the daily anchor on a new day; the
        permanent total-loss / drawdown check never resets.

        Prop mode (loss_baseline > 0): the daily cap is a flat dollar amount
        (daily_loss_halt * loss_baseline) off the day's starting equity, and the
        permanent halt is measured statically from the baseline — neither uses
        current equity as its base, exactly as a prop firm scores you."""
        # --- permanent total-loss / drawdown halt ---
        if self.loss_baseline > 0 and self.total_loss_halt > 0:
            if equity <= self.loss_baseline * (1.0 - self.total_loss_halt):
                self.blown = True
        elif self.max_drawdown_halt > 0:
            self._peak_equity = max(self._peak_equity, equity)
            if equity <= self._peak_equity * (1.0 - self.max_drawdown_halt):
                self.blown = True
        # --- daily loss halt ---
        if self._day != today:
            self._day = today
            self._day_start_equity = equity
            self.halted = False
        elif self.loss_baseline > 0:
            if self._day_start_equity - equity >= self.daily_loss_halt * self.loss_baseline:
                self.halted = True
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

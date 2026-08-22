"""Central configuration. Credentials/secrets come from .env, never from code."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    symbol: str = "EURUSD"
    timeframe: str = "H1"          # matched to mt5.TIMEFRAME_* in broker_mt5

    # Which strategy the engine runs — a key of trader.strategies.STRATEGIES
    # ("sma_cross", "orb"). orb was authored for XAUUSD H1 — switch
    # symbol/timeframe/pip settings together.
    strategy: str = "sma_cross"

    # sma_cross
    fast_sma: int = 20
    slow_sma: int = 50

    # orb
    orb_session_start_hour: int = 1   # server time, per the source EA
    orb_box_candles: int = 3
    orb_tp_r: float = 3.0             # target = this many multiples of the stop distance

    # orb v2 — breakout confirmations. Each filter can veto a raw breakout;
    # turn one off to reproduce v1 behavior exactly.
    # Volume defaults OFF: the 2025-08→2026-08 XAUUSD H1 backtest showed it
    # cutting profit at every threshold tried (see docs/2026-08-11-orb-v2-design.md).
    orb_vol_filter: bool = False      # breakout bar needs above-average tick volume
    orb_vol_mult: float = 1.2         # ... at least this multiple of the recent mean
    orb_vol_lookback: int = 20        # bars in that mean (auto-passes if data has no volume)
    orb_structure_filter: bool = True  # longs need rising swing lows, shorts falling swing highs
    orb_swing_window: int = 2         # bars each side that a fractal swing must dominate

    # orb v2 — exits. "structure": TP at the most recent swing level beyond
    # entry (min orb_tp_min_r × risk away, else fall back to the R multiple).
    # "r_multiple": v1 behavior, TP = orb_tp_r × stop distance.
    orb_tp_mode: str = "r_multiple"
    orb_tp_min_r: float = 1.0

    # bos — break-of-structure + Chaikin Money Flow (XAUUSD M30). Break of the
    # most recent fractal swing, confirmed by a candle close and by CMF direction;
    # structure-derived stop + target (see docs/2026-08-23-gold-bos-cmf-design.md).
    bos_swing_window: int = 2         # bars each side that a fractal swing must dominate
    bos_cmf_n: int = 20               # Chaikin Money Flow lookback (bars)
    bos_lookback: int = 2000          # bars of history the structure-target search sees
                                      # (~6 weeks of M30). Stable across 1k-4k; 8-day
                                      # windows aim at worse targets. See the L-sweep.
    bos_cmf_min: float = 0.0          # require |CMF| > this in the break direction (0 = just the sign)
    bos_trend_ma: int = 0             # >0: only take breaks in the direction of this SMA (0 = off)
    bos_tp_mode: str = "structure"    # "structure" = next swing beyond entry, else "r_multiple"
    bos_tp_r: float = 3.0             # R-multiple target / fallback when no structure target
    bos_tp_min_r: float = 1.0         # a structure target must be at least this many R away

    # session (time-of-day) strategy — enters LONG at a fixed server hour,
    # protective ATR stop on the server, NO take-profit; the live loop closes it
    # by TIME after session_hold_bars bars. Validated on USDJPY morning (the
    # Tokyo→London handover) in wf_search.py. See docs.
    session_entry_hour: int = 6       # broker server-time hour to enter
    session_hold_bars: int = 12       # bars to hold before a time exit
    session_side: str = "long"        # the drift is a long (JPY weakens intraday)
    session_stop_atr_mult: float = 2.0  # protective stop = this × ATR
    session_atr_n: int = 14           # ATR lookback (bars)
    sl_pips: float = 30.0
    tp_pips: float = 60.0
    pip_size: float = 0.0001       # EURUSD pip
    pip_value_per_lot: float = 10.0  # USD per pip per 1.0 lot on EURUSD
    spread_pips: float = 1.0       # assumed cost in backtests

    # Risk rails
    risk_per_trade: float = 0.01   # 1% of equity risked per trade
    max_open_positions: int = 1
    daily_loss_halt: float = 0.03  # legacy: -% of the day's start equity.
                                   # prop mode (loss_baseline set): flat $ cap =
                                   # daily_loss_halt * loss_baseline.
    max_drawdown_halt: float = 0.0  # permanent stop this fraction below the
                                    # equity PEAK (trailing); 0 = off
    loss_baseline: float = 0.0     # prop mode: fixed $ the daily/total limits are
                                   # measured against (e.g. 10_000). 0 = legacy %.
    total_loss_halt: float = 0.0   # prop mode: permanent stop this fraction below
                                   # the fixed baseline (static); 0 = off
    min_lot: float = 0.01
    max_lot: float = 1.0

    # Alerts (optional; log-only if unset)
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # MT5 login (optional; if unset we attach to whatever account the
    # terminal is already logged into)
    mt5_login: int = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password: str = os.getenv("MT5_PASSWORD", "")
    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_path: str = os.getenv("MT5_PATH", "")  # full path to terminal64.exe;
                                               # blank = let the bridge auto-detect


CONFIG = Config()

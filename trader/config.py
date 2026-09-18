"""Central configuration. Credentials/secrets come from .env, never from code."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    symbol: str = "XAUUSD"
    timeframe: str = "M30"          # matched to mt5.TIMEFRAME_* in broker_mt5

    strategy: str = "bos"

    # H1 session: completed candle opening-label hour in broker time.
    session_hour: int = 0
    session_entry_at_open: bool = False  # hour denotes entry boundary when True
    session_atr_n: int = 14
    session_sl_atr: float = 2.0
    session_hold_hours: float = 12.0
    session_entry_window_seconds: float = 60
    session_commission_per_lot: float = 14.0  # round trip, account currency
    session_slippage_pips: float = 0.1

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

    sl_pips: float = 30.0
    tp_pips: float = 60.0
    pip_size: float = 0.1          # XAUUSD pip
    pip_value_per_lot: float = 10.0  # USD per pip per 1.0 lot on XAUUSD
    spread_pips: float = 3.0       # assumed cost in backtests

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

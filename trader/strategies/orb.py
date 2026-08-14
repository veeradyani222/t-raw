"""Opening-range breakout, ported from ea-library/GOLD_ORB (XAUUSD H1).

The first `orb_box_candles` bars of each trading day (starting at
`orb_session_start_hour`, server time) define a high/low box. A later bar
that CLOSES beyond the box in its own direction (bullish close above the box
high / bearish close below the box low) is the breakout.

Fires at most once per side per day without holding state: the signal only
triggers on the FIRST bar of the session to close beyond that side of the box
— if an earlier session bar already closed through it, the move is stale and
we stay flat.

Simplified from the original on purpose: the EA's long-wick box adjustments
and box-extension counters are dropped in favor of the plain first-N-bars
box; its per-trade risk (1%), max-2-trades-per-day, and drawdown halt come
from the engine's RiskGuard instead.

v2 (2026-08-11) adds two confirmation filters on top of the raw breakout,
each returning a Blocked record (not a silent FLAT) when it vetoes:

- Volume: the breakout bar's tick volume must be at least `orb_vol_mult` ×
  the mean of the previous `orb_vol_lookback` bars. Tick volume is the proxy
  — forex has no centralized real volume. Data without a tick_volume column
  auto-passes.
- Structure: longs need the two most recent swing lows to be RISING (higher
  lows into the breakout); shorts need the two most recent swing highs to be
  FALLING. Swings are fractals: a bar whose high/low dominates
  `orb_swing_window` bars on each side. Fewer than two swings = pass.

Exits are structure-derived, not fixed pips: the stop goes at the FAR side
of the box — the level that invalidates the breakout. The target depends on
`orb_tp_mode`: "structure" puts it at the most recent swing level beyond
entry (if at least `orb_tp_min_r` × risk away, else R-multiple fallback);
"r_multiple" is `orb_tp_r` × the stop distance. The engine sizes the
position from the stop distance, so every trade risks the same fraction of
equity regardless of box width.
"""
import numpy as np
import pandas as pd

from ..strategy import Blocked, Setup, Signal

_TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
               "H1": 60, "H4": 240, "D1": 1440}


def lookback(cfg) -> int:
    # ~3 trading days of bars: the current session's start plus enough prior
    # history for swing detection and the volume average.
    bars_per_day = (26 * 60) // _TF_MINUTES[cfg.timeframe]
    return max(3 * bars_per_day + cfg.orb_box_candles + 5,
               cfg.orb_box_candles + 2, cfg.orb_vol_lookback + 2)


def swing_points(high: np.ndarray, low: np.ndarray, window: int) -> tuple[list[int], list[int]]:
    """Fractal swings: index i is a swing high if high[i] is strictly greater
    than the `window` bars on each side (mirrored for lows). The last `window`
    bars can never qualify — they aren't confirmed yet."""
    n = len(high)
    highs, lows = [], []
    for i in range(window, n - window):
        left, right = slice(i - window, i), slice(i + 1, i + window + 1)
        if high[i] > high[left].max() and high[i] > high[right].max():
            highs.append(i)
        if low[i] < low[left].min() and low[i] < low[right].min():
            lows.append(i)
    return highs, lows


def _structure_state(high, low, swing_highs, swing_lows) -> str:
    """Label the trend by the two most recent swings on each side."""
    # bool() matters: numpy bools fail the `is` identity checks below.
    hh = bool(high[swing_highs[-1]] > high[swing_highs[-2]]) if len(swing_highs) >= 2 else None
    hl = bool(low[swing_lows[-1]] > low[swing_lows[-2]]) if len(swing_lows) >= 2 else None
    if hh is None and hl is None:
        return "n/a"
    if hh is not False and hl is not False:   # rising or unknown on both sides
        return "HH/HL"
    if hh is not True and hl is not True:
        return "LH/LL"
    return "mixed"


def compute_signal(candles: pd.DataFrame, cfg) -> Signal | Setup | Blocked:
    n = len(candles)
    if n < cfg.orb_box_candles + 2:
        return Signal.FLAT

    t = candles["time"].values  # datetime64[ns]
    hours = (t.astype("datetime64[h]") - t.astype("datetime64[D]")).astype(int)
    starts = np.nonzero(hours == cfg.orb_session_start_hour)[0]
    if starts.size == 0:
        return Signal.FLAT
    # First bar at the session-start hour of the current trading day.
    days = t.astype("datetime64[D]")
    session_start = starts[days[starts] == days[starts[-1]]][0]

    box_end = session_start + cfg.orb_box_candles
    if box_end >= n:  # box not complete yet, or no bar after it
        return Signal.FLAT

    high = candles["high"].values
    low = candles["low"].values
    close = candles["close"].values
    box_high = high[session_start:box_end].max()
    box_low = low[session_start:box_end].min()

    entry = close[-1]
    open_last = candles["open"].values[-1]
    prior = close[box_end:n - 1]  # session bars after the box, before the last

    if entry > open_last and entry > box_high and not (prior > box_high).any():
        side = "long"
    elif entry < open_last and entry < box_low and not (prior < box_low).any():
        side = "short"
    else:
        return Signal.FLAT

    meta = {"box_high": float(box_high), "box_low": float(box_low),
            "box_size": float(box_high - box_low), "vol_ratio": float("nan"),
            "structure": "n/a", "tp_source": ""}

    # --- volume confirmation ---------------------------------------------
    if "tick_volume" in candles.columns:
        vol = candles["tick_volume"].values.astype(float)
        prev = vol[max(0, n - 1 - cfg.orb_vol_lookback):n - 1]
        if len(prev) and prev.mean() > 0:
            meta["vol_ratio"] = float(vol[-1] / prev.mean())
    if cfg.orb_vol_filter and not np.isnan(meta["vol_ratio"]) \
            and meta["vol_ratio"] < cfg.orb_vol_mult:
        return Blocked(side, f"volume {meta['vol_ratio']:.2f}x, "
                             f"need {cfg.orb_vol_mult:.2f}x", meta)

    # --- structure confirmation ------------------------------------------
    swing_highs, swing_lows = swing_points(high, low, cfg.orb_swing_window)
    meta["structure"] = _structure_state(high, low, swing_highs, swing_lows)
    if cfg.orb_structure_filter:
        if side == "long" and len(swing_lows) >= 2 \
                and low[swing_lows[-1]] <= low[swing_lows[-2]]:
            return Blocked(side, "structure: swing lows not rising", meta)
        if side == "short" and len(swing_highs) >= 2 \
                and high[swing_highs[-1]] >= high[swing_highs[-2]]:
            return Blocked(side, "structure: swing highs not falling", meta)

    # --- exits ------------------------------------------------------------
    if side == "long":
        risk = entry - box_low
        sl, tp = box_low, entry + cfg.orb_tp_r * risk
    else:
        risk = box_high - entry
        sl, tp = box_high, entry - cfg.orb_tp_r * risk
    meta["tp_source"] = "r_multiple"

    if cfg.orb_tp_mode == "structure":
        # Most recent confirmed swing level beyond entry, if far enough away.
        if side == "long":
            levels = [high[i] for i in reversed(swing_highs)
                      if high[i] >= entry + cfg.orb_tp_min_r * risk]
        else:
            levels = [low[i] for i in reversed(swing_lows)
                      if low[i] <= entry - cfg.orb_tp_min_r * risk]
        if levels:
            tp = float(levels[0])
            meta["tp_source"] = "structure"

    return Setup(side, sl=float(sl), tp=float(tp), meta=meta)

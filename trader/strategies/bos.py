"""Break-of-Structure + Chaikin Money Flow — XAUUSD M30.

The strategy Aaryan designed (see docs/2026-08-23-gold-bos-cmf-design.md):

  1. Mark the most recent CONFIRMED fractal swing high / swing low.
  2. A candle that CLOSES beyond that level (a real close, not just a wick) is
     the break — LONG on a fresh close above the swing high, SHORT on a fresh
     close below the swing low. "Fresh" = the previous bar was on the other side
     of the level, so the signal fires once on the break, not every bar after.
  3. Chaikin Money Flow must agree: CMF > cmf_min for a long, < -cmf_min for a
     short. CMF is the honest buyer/seller-pressure proxy on a feed with no real
     volume — it weights each bar's tick volume by where price closed within the
     bar's range (close near the high = buyers, near the low = sellers).

Optional trend filter (bos_trend_ma > 0): only take breaks in the direction of
that SMA. Off by default — the baseline (plain CMF>0) won more out-of-sample.

Exits are structure-derived, like orb: the stop goes at the FAR side of the
broken structure (the opposing confirmed swing that invalidates the break); the
target is the next confirmed swing beyond entry (>= bos_tp_min_r x risk away),
falling back to bos_tp_r x the stop distance. The engine sizes from the stop
distance, so every trade risks the same fraction of equity.

Validated: bos_backtest.make_bos_signal wraps THIS function, so the researched
walk-forward numbers and the live signals are the same code (see tests).
"""
import numpy as np
import pandas as pd

from ..strategy import Blocked, Setup, Signal
from .orb import swing_points

_TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
               "H1": 60, "H4": 240, "D1": 1440}


def lookback(cfg) -> int:
    """Bars compute_signal sees. The window matters because the structure TARGET
    is the nearest overhead swing within it — too short and the bot can't see
    real resistance and aims at worse targets. `bos_lookback` (~6 weeks of M30
    bars by default) sits in a band (3 weeks–3 months) where results are stable;
    8-day-short windows are the only ones that break it. See the L-sweep in
    docs/2026-08-23-gold-bos-cmf-design.md."""
    return max(cfg.bos_lookback, cfg.bos_cmf_n + 5,
               cfg.bos_trend_ma + 5, cfg.bos_swing_window * 4 + 5)


def _cmf_last(high, low, close, vol, n) -> float:
    """Chaikin Money Flow of the most recent bar, over the last n bars. Uses only
    bars in the array (no lookahead). NaN if there isn't enough history/volume."""
    if len(close) < n:
        return float("nan")
    h, l, c, v = high[-n:], low[-n:], close[-n:], vol[-n:]
    rng = h - l
    mfm = np.where(rng > 0, ((c - l) - (h - c)) / np.where(rng > 0, rng, 1.0), 0.0)
    vsum = v.sum()
    if vsum <= 0:
        return float("nan")
    return float((mfm * v).sum() / vsum)


def compute_signal(candles: pd.DataFrame, cfg) -> Signal | Setup | Blocked:
    n = len(candles)
    w = cfg.bos_swing_window
    if n < max(cfg.bos_cmf_n, w * 2) + 2:
        return Signal.FLAT

    high = candles["high"].values.astype(float)
    low = candles["low"].values.astype(float)
    close = candles["close"].values.astype(float)
    openp = candles["open"].values.astype(float)
    vol = (candles["tick_volume"].values.astype(float)
           if "tick_volume" in candles.columns else np.ones(n))

    swing_highs, swing_lows = swing_points(high, low, w)  # all already confirmed
    last_high = swing_highs[-1] if swing_highs else -1     # resistance to break
    last_low = swing_lows[-1] if swing_lows else -1        # support to break
    cmf = _cmf_last(high, low, close, vol, cfg.bos_cmf_n)
    ma = float(close[-cfg.bos_trend_ma:].mean()) if cfg.bos_trend_ma > 0 else None

    entry = close[-1]
    cmf_str = round(cmf, 3) if not np.isnan(cmf) else None

    # ---- LONG: a fresh close above the last confirmed swing high -------------
    if last_high >= 0:
        level = high[last_high]
        raw = close[-1] > level and close[-2] <= level and close[-1] > openp[-1]
        if raw:
            meta = {"level": float(level), "cmf": cmf_str, "structure": "break_high",
                    "tp_source": ""}
            if np.isnan(cmf) or cmf <= cfg.bos_cmf_min:
                return Blocked("long", f"CMF {cmf_str} not > {cfg.bos_cmf_min}", meta)
            if ma is not None and entry <= ma:
                return Blocked("long", f"below MA{cfg.bos_trend_ma}", meta)
            if last_low >= 0 and low[last_low] < entry:
                sl = float(low[last_low])
                risk = entry - sl
                if risk > 0:
                    tp, src = entry + cfg.bos_tp_r * risk, "r_multiple"
                    if cfg.bos_tp_mode == "structure":
                        ups = [high[i] for i in reversed(swing_highs)
                               if high[i] >= entry + cfg.bos_tp_min_r * risk]
                        if ups:
                            tp, src = float(min(ups)), "structure"
                    meta["tp_source"] = src
                    return Setup("long", sl=sl, tp=float(tp), meta=meta)

    # ---- SHORT: a fresh close below the last confirmed swing low --------------
    if last_low >= 0:
        level = low[last_low]
        raw = close[-1] < level and close[-2] >= level and close[-1] < openp[-1]
        if raw:
            meta = {"level": float(level), "cmf": cmf_str, "structure": "break_low",
                    "tp_source": ""}
            if np.isnan(cmf) or cmf >= -cfg.bos_cmf_min:
                return Blocked("short", f"CMF {cmf_str} not < -{cfg.bos_cmf_min}", meta)
            if ma is not None and entry >= ma:
                return Blocked("short", f"above MA{cfg.bos_trend_ma}", meta)
            if last_high >= 0 and high[last_high] > entry:
                sl = float(high[last_high])
                risk = sl - entry
                if risk > 0:
                    tp, src = entry - cfg.bos_tp_r * risk, "r_multiple"
                    if cfg.bos_tp_mode == "structure":
                        dns = [low[i] for i in reversed(swing_lows)
                               if low[i] <= entry - cfg.bos_tp_min_r * risk]
                        if dns:
                            tp, src = float(max(dns)), "structure"
                    meta["tp_source"] = src
                    return Setup("short", sl=sl, tp=float(tp), meta=meta)

    return Signal.FLAT

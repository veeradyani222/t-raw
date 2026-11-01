"""Round-4: pure price-action families, one code path for every market and timeframe.

Every build_<name>(df, **params) takes any df from research.prop.harness.load() and
returns a list (len(df)) of H.Entry | None. Causal: the signal at bar i uses rows <= i
only (the harness fills at bar i's close); swing pivots count only once CONFIRMED
(k bars after the pivot bar); prior-day levels come from completed server days.

Stops sit at the structure that invalidates the idea, never closer than
max(MIN_STOP_ATR x ATR, MIN_STOP_SPREADS x spread floor) and never wider than
MAX_STOP_ATR x ATR (wider setups are skipped). Exits: R-multiple target + max_hold,
or a pivot-trailing stop (bos 'trail').

Families:
  sfp          swing failure: sweep of the N-bar high/low, close back inside -> fade
  bos          break of structure: close through the last confirmed pivot -> follow
  inside       inside-bar breakout (optional EMA trend filter)
  pin          pin bar / rejection wick at an N-bar extreme
  engulf       engulfing candle at an N-bar extreme
  nr           narrow-range (NR4 / NR7) bar, then breakout of it
  pd_sweep     intraday sweep of the prior day's high/low and close back inside
  hikkake      inside bar, false break one way, then break the other way
  double       double bottom / top on confirmed pivots, neckline break
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

MIN_STOP_SPREADS = 4.0
MIN_STOP_ATR = 0.3
MAX_STOP_ATR = 4.0
BUF = 0.1              # stop buffer beyond the structure, in ATRs
HOLD = 100             # max bars for R-target exits


# ----------------------------------------------------------------- helpers
def _a(df, k):
    return df[k].to_numpy(float)


def atr(df, n=14):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _prior_max(x, n):
    """max of x[i-n .. i-1] (excludes bar i)."""
    return pd.Series(x).rolling(n, min_periods=n).max().shift(1).to_numpy()


def _prior_min(x, n):
    return pd.Series(x).rolling(n, min_periods=n).min().shift(1).to_numpy()


def _entry(df, i, side, sl, a, r=None, max_hold=HOLD, manage=None, meta=None):
    """Entry at bar i's close with a structure stop; None if the stop is too wide."""
    c = float(df["close"].iat[i])
    if not np.isfinite(sl) or not np.isfinite(a) or a <= 0:
        return None
    ms = max(MIN_STOP_ATR * a, MIN_STOP_SPREADS * H.SPREAD_FLOOR.get(df.attrs.get("symbol", ""), 0.0))
    if side == "long":
        sl = min(sl, c - ms)
        d = c - sl
    else:
        sl = max(sl, c + ms)
        d = sl - c
    if d > MAX_STOP_ATR * a:
        return None
    tp = None if r is None else (c + r * d if side == "long" else c - r * d)
    return H.Entry(side, float(sl), None if tp is None else float(tp), max_hold, None, manage, meta or {})


def pivots(df, k):
    """Last CONFIRMED pivot high/low level as of each bar (a pivot at j is known at j+k)."""
    h, l = _a(df, "high"), _a(df, "low")
    n = len(h)
    win = 2 * k + 1
    hmax = pd.Series(h).rolling(win, center=True, min_periods=win).max().to_numpy()
    lmin = pd.Series(l).rolling(win, center=True, min_periods=win).min().to_numpy()
    ph = np.full(n, np.nan); pl = np.full(n, np.nan)
    ph_idx = np.full(n, -1); pl_idx = np.full(n, -1)
    for j in np.flatnonzero(h == hmax):
        if j + k < n: ph[j + k] = h[j]; ph_idx[j + k] = j
    for j in np.flatnonzero(l == lmin):
        if j + k < n: pl[j + k] = l[j]; pl_idx[j + k] = j
    ph = pd.Series(ph).ffill().to_numpy(); pl = pd.Series(pl).ffill().to_numpy()
    ph_idx = np.maximum.accumulate(ph_idx); pl_idx = np.maximum.accumulate(pl_idx)
    return ph, pl, ph_idx, pl_idx


# ----------------------------------------------------------------- families
def build_sfp(df, n=20, r=2.0):
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df); hi, lo = _prior_max(h, n), _prior_min(l, n)
    out = [None] * len(df)
    for i in range(n + 1, len(df)):
        up = h[i] > hi[i] and c[i] < hi[i]
        dn = l[i] < lo[i] and c[i] > lo[i]
        if up and not dn:
            out[i] = _entry(df, i, "short", h[i] + BUF * a[i], a[i], r, max_hold=3 * n)
        elif dn and not up:
            out[i] = _entry(df, i, "long", l[i] - BUF * a[i], a[i], r, max_hold=3 * n)
    return out


def build_bos(df, k=3, exit="r2"):
    c = _a(df, "close")
    a = atr(df); ph, pl, _, _ = pivots(df, k)

    def trail(d, i, pos):
        if pos["side"] == "long":
            s = pl[i] - BUF * a[i]
            return s if np.isfinite(s) and s > pos["sl"] and s < c[i] else None
        s = ph[i] + BUF * a[i]
        return s if np.isfinite(s) and s < pos["sl"] and s > c[i] else None

    out = [None] * len(df)
    for i in range(2 * k + 2, len(df)):
        L, S = ph[i - 1], pl[i - 1]
        if np.isfinite(L) and c[i] > L and c[i - 1] <= L:
            sl = pl[i] - BUF * a[i]
            out[i] = (_entry(df, i, "long", sl, a[i], 2.0) if exit == "r2"
                      else _entry(df, i, "long", sl, a[i], None, max_hold=300, manage=trail))
        elif np.isfinite(S) and c[i] < S and c[i - 1] >= S:
            sl = ph[i] + BUF * a[i]
            out[i] = (_entry(df, i, "short", sl, a[i], 2.0) if exit == "r2"
                      else _entry(df, i, "short", sl, a[i], None, max_hold=300, manage=trail))
    return out


def build_inside(df, r=2.0, trend=0):
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df); ema = _ema(c, trend) if trend else None
    inside = np.r_[False, (h[1:] < h[:-1]) & (l[1:] > l[:-1])]
    out = [None] * len(df)
    for i in range(3, len(df)):
        for back in (1, 2):                 # inside bar at i-1 or i-2, first close outside it
            j = i - back
            if not inside[j]:
                continue
            if back == 2 and (c[i - 1] > h[j] or c[i - 1] < l[j]):
                break                       # already broke on the previous bar
            if c[i] > h[j] and (ema is None or c[i] > ema[i]):
                out[i] = _entry(df, i, "long", l[j] - BUF * a[i], a[i], r)
            elif c[i] < l[j] and (ema is None or c[i] < ema[i]):
                out[i] = _entry(df, i, "short", h[j] + BUF * a[i], a[i], r)
            break
    return out


def build_pin(df, n=20, r=2.0):
    o, h, l, c = (_a(df, k) for k in ("open", "high", "low", "close"))
    a = atr(df); hi, lo = _prior_max(h, n), _prior_min(l, n)
    rng = h - l
    body = np.abs(c - o)
    lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c)
    out = [None] * len(df)
    for i in range(n + 1, len(df)):
        if rng[i] < 0.5 * a[i] or body[i] > 0.35 * rng[i]:
            continue
        if l[i] <= lo[i] and lw[i] >= 0.6 * rng[i] and c[i] > l[i] + 0.6 * rng[i]:
            out[i] = _entry(df, i, "long", l[i] - BUF * a[i], a[i], r, max_hold=5 * n)
        elif h[i] >= hi[i] and uw[i] >= 0.6 * rng[i] and c[i] < h[i] - 0.6 * rng[i]:
            out[i] = _entry(df, i, "short", h[i] + BUF * a[i], a[i], r, max_hold=5 * n)
    return out


def build_engulf(df, n=20, r=2.0):
    o, h, l, c = (_a(df, k) for k in ("open", "high", "low", "close"))
    a = atr(df); hi, lo = _prior_max(h, n), _prior_min(l, n)
    out = [None] * len(df)
    for i in range(n + 2, len(df)):
        b0, b1 = abs(c[i] - o[i]), abs(c[i - 1] - o[i - 1])
        if b0 < 0.5 * a[i] or b0 < b1:
            continue
        bull = c[i - 1] < o[i - 1] and c[i] > o[i] and c[i] >= o[i - 1] and o[i] <= c[i - 1]
        bear = c[i - 1] > o[i - 1] and c[i] < o[i] and c[i] <= o[i - 1] and o[i] >= c[i - 1]
        lo2, hi2 = min(l[i], l[i - 1]), max(h[i], h[i - 1])
        if bull and lo2 <= lo[i - 1]:
            out[i] = _entry(df, i, "long", lo2 - BUF * a[i], a[i], r, max_hold=5 * n)
        elif bear and hi2 >= hi[i - 1]:
            out[i] = _entry(df, i, "short", hi2 + BUF * a[i], a[i], r, max_hold=5 * n)
    return out


def build_nr(df, k=7, r=2.0):
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df); rng = h - l
    nr = rng <= pd.Series(rng).rolling(k, min_periods=k).min().to_numpy()
    out = [None] * len(df)
    for i in range(k + 2, len(df)):
        for back in (1, 2, 3):
            j = i - back
            if not nr[j]:
                continue
            if any(c[m] > h[j] or c[m] < l[j] for m in range(j + 1, i)):
                break                       # already broke out earlier
            if c[i] > h[j]:
                out[i] = _entry(df, i, "long", l[j] - BUF * a[i], a[i], r)
            elif c[i] < l[j]:
                out[i] = _entry(df, i, "short", h[j] + BUF * a[i], a[i], r)
            break
    return out


def build_pd_sweep(df, r=2.0):
    """Intraday only: sweep of the prior server day's high/low, close back inside."""
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df)
    day = pd.DatetimeIndex(df["time"]).normalize()
    d = pd.DataFrame({"day": day, "h": h, "l": l})
    g = d.groupby("day").agg(h=("h", "max"), l=("l", "min"))
    pdh = g.h.shift(1).reindex(day).to_numpy(); pdl = g.l.shift(1).reindex(day).to_numpy()
    first = np.r_[True, day[1:] != day[:-1]]
    out = [None] * len(df)
    hod = lod = np.nan; used_s = used_l = False
    for i in range(len(df)):
        if first[i]:
            hod, lod = h[i], l[i]; used_s = used_l = False
        else:
            hod, lod = max(hod, h[i]), min(lod, l[i])
        if not np.isfinite(pdh[i]):
            continue
        if not used_s and h[i] > pdh[i] and c[i] < pdh[i]:
            out[i] = _entry(df, i, "short", hod + BUF * a[i], a[i], r, max_hold=48); used_s = True
        elif not used_l and l[i] < pdl[i] and c[i] > pdl[i]:
            out[i] = _entry(df, i, "long", lod - BUF * a[i], a[i], r, max_hold=48); used_l = True
    return out


def build_hikkake(df, r=2.0):
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df)
    inside = np.r_[False, (h[1:] < h[:-1]) & (l[1:] > l[:-1])]
    out = [None] * len(df)
    for i in range(4, len(df)):
        for j in range(i - 3, i - 1):       # inside bar 2-3 bars back, fake-out in between
            if j < 1 or not inside[j]:
                continue
            mid = range(j + 1, i)
            fake_dn = any(c[m] < l[j] for m in mid) and not any(c[m] > h[j] for m in mid)
            fake_up = any(c[m] > h[j] for m in mid) and not any(c[m] < l[j] for m in mid)
            if fake_dn and c[i] > h[j]:
                out[i] = _entry(df, i, "long", min(l[j:i + 1]) - BUF * a[i], a[i], r)
            elif fake_up and c[i] < l[j]:
                out[i] = _entry(df, i, "short", max(h[j:i + 1]) + BUF * a[i], a[i], r)
            if out[i] is not None:
                break
    return out


def build_double(df, k=3, r=2.0, tol=0.3):
    """Two confirmed pivot lows within tol ATR, >= 2k bars apart, then close above the
    highest high between them (neckline). Mirror for tops."""
    h, l, c = _a(df, "high"), _a(df, "low"), _a(df, "close")
    a = atr(df); _, _, ph_idx, pl_idx = pivots(df, k)
    out = [None] * len(df)
    lows, highs = [], []                    # confirmed pivot bar indices, in order
    last_pl = last_ph = -1; done_b = done_t = -1
    for i in range(len(df)):
        if pl_idx[i] != last_pl and pl_idx[i] >= 0:
            last_pl = pl_idx[i]; lows.append(last_pl)
        if ph_idx[i] != last_ph and ph_idx[i] >= 0:
            last_ph = ph_idx[i]; highs.append(last_ph)
        if len(lows) >= 2 and lows[-1] != done_b:
            p1, p2 = lows[-2], lows[-1]
            if p2 - p1 >= 2 * k and abs(l[p2] - l[p1]) <= tol * a[p2]:
                neck = h[p1:p2 + 1].max()
                if c[i] > neck and c[i - 1] <= neck and i > p2:
                    out[i] = _entry(df, i, "long", min(l[p1], l[p2]) - BUF * a[i], a[i], r); done_b = p2
        if out[i] is None and len(highs) >= 2 and highs[-1] != done_t:
            p1, p2 = highs[-2], highs[-1]
            if p2 - p1 >= 2 * k and abs(h[p2] - h[p1]) <= tol * a[p2]:
                neck = l[p1:p2 + 1].min()
                if c[i] < neck and c[i - 1] >= neck and i > p2:
                    out[i] = _entry(df, i, "short", max(h[p1], h[p2]) + BUF * a[i], a[i], r); done_t = p2
    return out


# ----------------------------------------------------------------- grid
GRID = {
    "sfp":      [dict(n=n, r=r) for n in (20, 50) for r in (1.5, 3.0)],
    "bos":      [dict(k=k, exit=e) for k in (3, 5) for e in ("r2", "trail")],
    "inside":   [dict(r=r, trend=t) for r in (1.5, 2.5) for t in (0, 100)],
    "pin":      [dict(n=n, r=r) for n in (10, 30) for r in (1.5, 3.0)],
    "engulf":   [dict(n=n, r=r) for n in (10, 30) for r in (1.5, 3.0)],
    "nr":       [dict(k=k, r=r) for k in (4, 7) for r in (1.5, 3.0)],
    "pd_sweep": [dict(r=r) for r in (1.5, 3.0)],        # intraday timeframes only
    "hikkake":  [dict(r=r) for r in (1.5, 3.0)],
    "double":   [dict(k=k) for k in (3, 5)],
}
INTRADAY_ONLY = {"pd_sweep"}

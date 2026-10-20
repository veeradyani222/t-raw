"""Fast R-multiple prescreen (NOT the judge). Mirrors harness fills: entry at
bar close + max(floor, bar spread) + slip, stop-first, gap-through-stop at
open, time exit at close after `hold` bars, commission $14/lot RT expressed
in R. One position at a time. Used only to map grids before H.score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

_SPEC = {}


def _spec(sym):
    """symbol spec, read once (a background job rewrites the json file)."""
    import time
    while not _SPEC:
        try:
            _SPEC.update(H._spec())
        except ValueError:
            time.sleep(1)
    return _SPEC.get(sym, {})


def eval_r(df, sides, dist, hold, tp_r=None, cost=True):
    sym = df.attrs["symbol"]
    spec = _spec(sym)
    contract = float(spec.get("contract", 100000.0))
    point = float(spec.get("point", 0.001))
    floor = H.SPREAD_FLOOR.get(sym, 0.0)
    slip = 0.1 * H._pip(sym)
    comm = 0.0 if sym in H.INDICES else H.COMMISSION_RT
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    conv = df["conv"].to_numpy(float)
    bsp = df["spread"].to_numpy(float) * point
    n = len(df)
    idx = np.flatnonzero(sides != None)  # noqa: E711
    rs, ts, gross = [], [], []
    busy_until = -1
    for i in idx:
        if i <= busy_until or i + 1 >= n:
            continue
        s = 1.0 if sides[i] == "long" else -1.0
        d = dist[i]
        sp = max(floor, bsp[i]) if cost else 0.0
        sl_ = slip if cost else 0.0
        entry = c[i] + s * (sp + sl_)
        sl = c[i] - s * d
        tp = c[i] + s * tp_r * d if tp_r else None
        risk_px = abs(entry - sl) + sl_
        if risk_px <= 0:
            continue
        lpl = risk_px * contract * conv[i] + (comm if cost else 0)
        comm_r = (comm if cost else 0) / lpl
        end = min(i + hold, n - 1)
        exit_px = None
        j = i + 1
        while j <= end:
            if s * (o[j] - sl) <= 0:
                exit_px = o[j] - s * sl_; break
            if (s > 0 and l[j] <= sl) or (s < 0 and h[j] >= sl):
                exit_px = sl - s * sl_; break
            if tp is not None and ((s > 0 and h[j] >= tp) or (s < 0 and l[j] <= tp)):
                exit_px = tp; break
            j += 1
        if exit_px is None:
            j = end
            exit_px = c[j] - s * sl_
        r = s * (exit_px - entry) / risk_px * (1 - comm_r) - comm_r
        rs.append(r); ts.append(df.time.iat[i]); gross.append(s * (exit_px - c[i]) / d)
        busy_until = j
    return pd.DataFrame({"time": ts, "r": rs, "gross_r": gross})


def eval_r_fast(df, sides, dist, hold, cost=True):
    """Vectorised version of eval_r for at most one entry per `hold` window
    (true for single-hour session rules with hold < 24). No take-profit."""
    sym = df.attrs["symbol"]
    spec = _spec(sym)
    contract = float(spec.get("contract", 100000.0))
    point = float(spec.get("point", 0.001))
    floor = H.SPREAD_FLOOR.get(sym, 0.0)
    slip = 0.1 * H._pip(sym) if cost else 0.0
    comm = (0.0 if sym in H.INDICES else H.COMMISSION_RT) if cost else 0.0
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    conv = df["conv"].to_numpy(float)
    bsp = df["spread"].to_numpy(float) * point
    n = len(df)
    idx = np.flatnonzero(sides != None)  # noqa: E711
    idx = idx[idx + hold < n]
    if len(idx) == 0:
        return pd.DataFrame({"time": [], "r": [], "gross_r": []})
    s = np.where(sides[idx] == "long", 1.0, -1.0)
    d = dist[idx]
    sp = np.maximum(floor, bsp[idx]) if cost else 0.0
    entry = c[idx] + s * (sp + slip)
    sl = c[idx] - s * d
    W = idx[:, None] + np.arange(1, hold + 1)[None, :]
    oo, hh, ll = o[W], h[W], l[W]
    gap = (s[:, None] * (oo - sl[:, None])) <= 0
    touch = np.where(s[:, None] > 0, ll <= sl[:, None], hh >= sl[:, None])
    hit = gap | touch
    any_hit = hit.any(1)
    k = np.argmax(hit, 1)
    rows = np.arange(len(idx))
    gap_k = gap[rows, k]
    exit_px = np.where(any_hit,
                       np.where(gap_k, oo[rows, k], sl) - s * slip,
                       c[idx + hold] - s * slip)
    risk_px = np.abs(entry - sl) + slip
    lpl = risk_px * contract * conv[idx] + comm
    comm_r = comm / lpl
    r = s * (exit_px - entry) / risk_px * (1 - comm_r) - comm_r
    gross = s * (exit_px - c[idx]) / d
    return pd.DataFrame({"time": df.time.to_numpy()[idx], "r": r, "gross_r": gross})


def summarize(tr):
    if tr.empty:
        return dict(n=0, sum_r=0, mean_r=0, gross=0, yrs_pos=0, worst_yr=0)
    y = tr.groupby(tr.time.dt.year).r.sum()
    return dict(n=len(tr), sum_r=round(tr.r.sum(), 1), mean_r=round(tr.r.mean(), 3),
                gross=round(tr.gross_r.mean(), 3), yrs_pos=int((y > 0).sum()),
                n_yrs=len(y), worst_yr=round(y.min(), 1))

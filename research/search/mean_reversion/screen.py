"""Fast pre-screener (NOT the judge). Re-implements the harness fill rules
for one position in R units so thousands of variants can be ranked in
seconds; anything promising is then re-scored with research.prop.harness.

Same rules as harness.simulate: enter at close +/- spread+slip, later bars
check gap-through-stop, stop, target, then time exit, then manage-exit, all
at the bar close. Differences: no flip, no daily block, no lot rounding.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


def _ctx(df):
    sym = df.attrs["symbol"]
    spec = H._spec().get(sym, {})
    contract = float(spec.get("contract", 100000.0))
    point = float(spec.get("point", 0.01))
    comm = 0.0 if sym in H.INDICES else H.COMMISSION_RT
    slip = 0.1 * H._pip(sym)
    sp = np.maximum(H.SPREAD_FLOOR.get(sym, 0.0), df["spread"].to_numpy(float) * point)
    return contract, comm, slip, sp


def screen(df, raw):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    conv = df["conv"].to_numpy(float)
    hours = pd.DatetimeIndex(df["time"]).hour.to_numpy()
    contract, comm, slip, sp = _ctx(df)
    L, S, xl, xs, a = raw["L"], raw["S"], raw["xl"], raw["xs"], raw["atr"]
    k, tpk, mh, eh = raw["stop_atr"], raw["tp_atr"], raw["max_hold"], raw["exit_hour"]
    sig = np.flatnonzero(L | S)
    n = len(c)
    rs, ex_t = [], []
    free = 0
    for i in sig:
        if i < free:
            continue
        lg = bool(L[i])
        e = c[i] + sp[i] + slip if lg else c[i] - sp[i] - slip
        sl = c[i] - k * a[i] if lg else c[i] + k * a[i]
        tp = None if tpk is None else (c[i] + tpk * a[i] if lg else c[i] - tpk * a[i])
        d = abs(e - sl) + slip
        x = None
        j = i + 1
        while j < n:
            if lg:
                if o[j] <= sl: x = o[j] - slip; break
                if l[j] <= sl: x = sl - slip; break
                if tp is not None and h[j] >= tp: x = tp; break
            else:
                if o[j] >= sl: x = o[j] + slip; break
                if h[j] >= sl: x = sl + slip; break
                if tp is not None and l[j] <= tp: x = tp; break
            if (mh is not None and j - i >= mh) or (eh is not None and hours[j] == eh):
                x = c[j] - slip if lg else c[j] + slip; break
            if (xl[j] if lg else xs[j]):
                x = c[j] - slip if lg else c[j] + slip; break
            j += 1
        if x is None:
            j = n - 1; x = c[j]
        g = (x - e) if lg else (e - x)
        cv = conv[i]
        rs.append((g * contract * cv - comm) / (d * contract * cv + comm))
        ex_t.append(j)
        free = j + 1   # harness can re-enter on the exit bar; close enough
    rs = np.array(rs)
    if not len(rs):
        return dict(n=0, R=0.0, Ryr=0.0, ddR=0.0, wdR=0.0, wr=0.0, rdd=0.0)
    eq = np.cumsum(rs)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    days = pd.DatetimeIndex(df["time"].to_numpy()[ex_t]).normalize()
    wd = float(pd.Series(rs).groupby(days).sum().min())
    yrs = (df["time"].iloc[-1] - df["time"].iloc[0]).days / 365.25
    R = float(rs.sum())
    return dict(n=len(rs), R=round(R, 1), Ryr=round(R / yrs, 2), ddR=round(dd, 1),
                wdR=round(wd, 2), wr=round(float((rs > 0).mean()), 3),
                rdd=round(R / max(-dd, 1.0), 2), avgR=round(R / len(rs), 3))

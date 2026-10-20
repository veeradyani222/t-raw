"""Portfolio combiner for the strategy-search survivors.

For each strategy we have harness.simulate curves (per-bar 'worst' and 'close'
equity, fixed-dollar risk) at every risk level (precompute.py). A portfolio =
sum of curves on a common timeline: at a timestamp where a strategy has its
own bar we use its 'worst' value, otherwise its last 'close' (forward-fill).
The summed curve is scored with harness._metrics (same worst day / max DD /
monthly / challenge logic as score()). We also check FundedNext's 3% cap on
total OPEN risk: the sum of risk-at-stop of all simultaneously open positions
(initial stop, conservative) must stay <= $300.

Usage: python combine.py   -> grid search, writes results.json
"""
import os
import sys
import json
import pickle
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

os.environ["PROP_OOS"] = "1"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.prop import harness as H  # noqa: E402

HERE = Path(__file__).parent
CACHE = HERE / "_cache"
OPEN_RISK_CAP = 0.03 * H.BASELINE
SAFE_D = -H.SAFE_DAILY * H.BASELINE
SAFE_M = -H.SAFE_DD * H.BASELINE


def _load(name, split):
    with open(CACHE / f"{name}-{split}.pkl", "rb") as f:
        return pickle.load(f)


class Book:
    """All strategies of one split aligned on one timeline."""

    def __init__(self, names, split):
        self.names, self.split = names, split
        self.data = {n: _load(n, split) for n in names}
        times = np.unique(np.concatenate([
            self.data[n]["res"][(H.RISKS[0], 1.0)]["curve"]["time"].to_numpy() for n in names]))
        self.times = pd.DatetimeIndex(times)
        self.start = H.OOS_START if split == "oos" else None
        self.cache = {}
        d = self.times.normalize().to_numpy()
        self.day_starts = np.flatnonzero(np.r_[True, d[1:] != d[:-1]])
        self.i0 = (int(np.searchsorted(self.times.values, H.OOS_START.to_datetime64()))
                   if self.start is not None else 0)

    def aligned(self, name, risk, sm=1.0):
        k = (name, risk, sm)
        if k not in self.cache:
            cv = self.data[name]["res"][(risk, sm)]["curve"]
            idx = pd.DatetimeIndex(cv["time"])
            keep = ~idx.duplicated(keep="last")
            s_close = pd.Series(cv["close"].to_numpy()[keep], index=idx[keep])
            s_worst = pd.Series(cv["worst"].to_numpy()[keep], index=idx[keep])
            cl = s_close.reindex(self.times).ffill().fillna(0.0).to_numpy()
            own = s_worst.reindex(self.times)
            w = np.where(own.notna().to_numpy(), own.fillna(0).to_numpy(), cl)
            self.cache[k] = (w, cl)
        return self.cache[k]

    def combo_arrays(self, alloc, sm=1.0):
        w = np.zeros(len(self.times))
        cl = np.zeros(len(self.times))
        for n, r in alloc.items():
            if r:
                a, b = self.aligned(n, r, sm)
                w = w + a
                cl = cl + b
        return w, cl

    def quick(self, alloc):
        """Fast max DD / worst day / net over the scored window (same maths as _metrics)."""
        w, cl = self.combo_arrays(alloc)
        i0 = self.i0
        off = cl[i0 - 1] if i0 > 0 else 0.0
        w, cl = w[i0:] - off, cl[i0:] - off
        peak = np.maximum.accumulate(np.r_[0.0, cl])[1:]
        max_dd = float((w - peak).min())
        ds = self.day_starts[self.day_starts >= i0] - i0
        de = np.r_[ds[1:] - 1, len(cl) - 1]
        day_low = np.minimum.reduceat(w, ds)
        prev = np.r_[0.0, cl[de[:-1]]]
        worst_day = float((day_low - prev).min())
        return dict(net=float(cl[-1]), max_dd=max_dd, worst_day=worst_day,
                    safe=bool(worst_day > SAFE_D and max_dd > SAFE_M))

    def trades(self, alloc, sm=1.0):
        parts = []
        for n, r in alloc.items():
            if r:
                t = self.data[n]["res"][(r, sm)]["trades"]
                if len(t):
                    t = t.copy()
                    t["strategy"] = n
                    ru = t["risk_usd"].to_numpy(float)
                    t["risk_usd"] = np.where(np.isfinite(ru) & (ru > 0), ru, r * H.BASELINE)
                    parts.append(t)
        if not parts:
            return pd.DataFrame(columns=["entry_time", "exit_time", "profit", "risk_usd", "strategy"])
        return pd.concat(parts, ignore_index=True)

    def open_risk(self, alloc):
        t = self.trades(alloc)
        if self.start is not None and len(t):
            t = t[t.exit_time >= self.start]
        if not len(t):
            return dict(max_open_risk=0.0, max_concurrent=0, cap_breach_events=0)
        ev = pd.concat([
            pd.DataFrame({"t": t.entry_time.values, "d": t.risk_usd.values, "k": 1, "c": 1}),
            pd.DataFrame({"t": t.exit_time.values, "d": -t.risk_usd.values, "k": 0, "c": -1})])
        ev = ev.sort_values(["t", "k"], kind="stable")     # exits before entries at the same stamp
        lvl = ev["d"].cumsum().to_numpy()
        cnt = ev["c"].cumsum().to_numpy()
        return dict(max_open_risk=float(lvl.max()), max_concurrent=int(cnt.max()),
                    cap_breach_events=int(((lvl > OPEN_RISK_CAP + 1e-6) & (ev["k"].to_numpy() == 1)).sum()))

    def full(self, alloc, sm=1.0):
        w, cl = self.combo_arrays(alloc, sm)
        curve = pd.DataFrame({"time": self.times, "worst": w, "close": cl})
        m = H._metrics(curve, self.trades(alloc, sm), start=self.start)
        m.update(self.open_risk(alloc))
        return m


def fmt(alloc):
    return " + ".join(f"{n}@{r * 100:g}%" for n, r in alloc.items() if r) or "(none)"


def _strip(m):
    return {k: v for k, v in m.items() if k != "monthly"}


def search(names, label, top=15):
    books = {s: Book(names, s) for s in ("is", "oos")}
    levels = (0.0,) + tuple(H.RISKS)
    rows = []
    for combo in itertools.product(levels, repeat=len(names)):
        if not any(combo):
            continue
        alloc = dict(zip(names, combo))
        rows.append(dict(alloc=alloc, oos=books["oos"].quick(alloc), is_=books["is"].quick(alloc)))
    safe_both = sorted([r for r in rows if r["oos"]["safe"] and r["is_"]["safe"]],
                       key=lambda r: -r["oos"]["net"])
    safe_oos_only = sorted([r for r in rows if r["oos"]["safe"] and not r["is_"]["safe"]],
                           key=lambda r: -r["oos"]["net"])
    out = dict(label=label, names=names, n_combos=len(rows), n_safe_both=len(safe_both),
               n_safe_oos_only=len(safe_oos_only), top_safe_both=[], top_safe_oos_only=[])
    for key, pool in (("top_safe_both", safe_both), ("top_safe_oos_only", safe_oos_only)):
        for r in pool[:top]:
            fo = books["oos"].full(r["alloc"])
            fi = books["is"].full(r["alloc"])
            f2 = books["oos"].full(r["alloc"], sm=2.0)
            out[key].append(dict(
                combo=fmt(r["alloc"]), alloc=dict(r["alloc"]), oos=_strip(fo), oos_monthly=fo["monthly"],
                is_=_strip(fi), is_monthly=fi["monthly"],
                oos_2x_spread={k: f2[k] for k in ("net", "avg_month", "max_dd", "worst_day", "safe",
                                                 "challenge_pass", "challenge_attempts",
                                                 "challenge_pass_rate", "challenge_median_days")}))
    out["singles"] = []
    for n in names:
        for r in H.RISKS:
            a = {n: r}
            out["singles"].append(dict(combo=fmt(a), oos=_strip(books["oos"].full(a)),
                                       is_=_strip(books["is"].full(a))))
    return out


def show(v, n=8):
    print("==", v["label"], "| combos", v["n_combos"], "| safe IS+OOS", v["n_safe_both"],
          "| safe OOS only", v["n_safe_oos_only"])
    for r in v["top_safe_both"][:n]:
        o, i, x = r["oos"], r["is_"], r["oos_2x_spread"]
        print(f"{r['combo']:<62} OOS ${o['avg_month']:6.1f}/mo dd {o['max_dd']:6.0f} wd {o['worst_day']:5.0f} "
              f"chal {o['challenge_pass']}/{o['challenge_attempts']} fail {o['challenge_fail']} "
              f"med {o['challenge_median_days']} openR {o['max_open_risk']:.0f} | "
              f"IS ${i['avg_month']:6.1f}/mo dd {i['max_dd']:6.0f} wd {i['worst_day']:5.0f} | 2x ${x['avg_month']:.1f}")


if __name__ == "__main__":
    res = {"survivors": search(["de40_orb", "gold_bb", "gold_cal"], "survivors only"),
           "with_refuted_bos": search(["de40_orb", "gold_bb", "gold_cal", "gold_bos_long"],
                                      "survivors + refuted gold_bos_long (sensitivity only)", top=5)}
    with open(HERE / "results.json", "w") as f:
        json.dump(res, f, indent=1, default=str)
    for v in res.values():
        show(v)

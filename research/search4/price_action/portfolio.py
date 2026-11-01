"""Round-4 portfolio: size the survivors on OLD data, then replay the 3 unseen years.

    .venv/Scripts/python.exe -m research.search4.price_action.portfolio GRID_DIR

Risk rule (decided on 2019-10-20..2023-10-20 only): every strategy at the same risk,
the largest level whose replay with the live close-all stop (-$300, slip $25) keeps the
account >= $9,400 and has <= 12 stop days a year. The unseen 2023-10-20..2026-10-31 replay
at that risk is the honest number.
"""
import json, os, sys
os.environ.setdefault("PROP_OOS", "1")
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool

import numpy as np
import pandas as pd

DEV_START, DEV_END, END = pd.Timestamp("2019-10-20"), pd.Timestamp("2023-10-20"), pd.Timestamp("2026-10-31")
RISKS = (0.0025, 0.003, 0.004, 0.005, 0.006, 0.0075, 0.01, 0.0125, 0.015)
HALT, SLIP = 300.0, 25.0


def as_pool(s):
    from research.search3.portfolio.round3w import MGROUP
    from research.search2.portfolio import core as P
    x = dict(name=f"pa_{s['fam']}_{s['symbol']}_{s['tf']}", symbol=s["symbol"], tf=s["tf"],
             module="research.search4.price_action.strategies", fn=f"build_{s['fam']}", params=s["params"],
             group=MGROUP.get(s["symbol"], "other"), family="pa_" + s["fam"])
    x["key"] = P.keyof(x)
    return x


def fast_eval(c, w, idx):
    day = idx.normalize().to_numpy()
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); ends = np.r_[starts[1:], len(idx)] - 1
    cprev = np.r_[0.0, c[ends[:-1]]]
    dmin = np.minimum.reduceat(w, starts) - cprev
    res = np.where(dmin <= -HALT, -(HALT + SLIP), c[ends] - cprev)
    A = np.r_[0.0, np.cumsum(res)]
    return dict(net=float(A[-1]), low=float((A[:-1] + np.maximum(dmin, -(HALT + SLIP))).min()), halts=int((dmin <= -HALT).sum()))


def replay(runs, start, end, label):
    from research.search2.portfolio import core as P
    ix = pd.DatetimeIndex(sorted(set().union(*[set(cv.time) for _, cv, _ in runs])
                                 | set().union(*[set(t.entry_time) | set(t.exit_time) for _, _, t in runs if len(t)])))
    C, W, h, _ = P.halt_replay([P.Strat(k, cv, t, ix) for k, cv, t in runs], ix, "close_all")
    c, w = pd.Series(C, index=ix), pd.Series(W, index=ix)
    d = c.groupby(c.index.normalize()).last(); dl = w.groupby(w.index.normalize()).min() - d.shift(1).fillna(0)
    per = [(start, start + pd.DateOffset(years=1), "first unseen year"), (start + pd.DateOffset(years=1), start + pd.DateOffset(years=2), "next year"),
           (start + pd.DateOffset(years=2), end, "latest year"), (start + pd.DateOffset(years=1), end, "last 2 years"),
           (pd.Timestamp("2026-09-01"), end, "Sep + Oct 2026"), (start, end, "all 3 years")]
    out = {}
    print(f"\n### {label}")
    for a, b, pl in per:
        base = c[c.index < a].iloc[-1] if (c.index < a).any() else 0.0
        seg = c[(c.index >= a) & (c.index < b)]
        if not len(seg): continue
        m = seg.groupby(seg.index.to_period("M")).last(); mon = m.diff(); mon.iloc[0] = m.iloc[0] - base
        fails = n = 0
        for st in pd.date_range(a, max(a, b - pd.Timedelta(days=30)), freq="14D"):
            bb = c[c.index < st].iloc[-1] if (c.index < st).any() else 0.0
            hit = c[(c.index >= st) & (c - bb >= 800)].index.min(); low = w[(w.index >= st) & (w - bb <= -800)].index.min()
            n += 1; fails += int(pd.notna(low) and (pd.isna(hit) or low < hit))
        r = dict(profit=round(float(seg.iloc[-1] - base)), per_month=round(float(seg.iloc[-1] - base) / len(mon)),
                 green=f"{int((mon > 0).sum())}/{len(mon)}", worst_month=round(float(mon.min())),
                 stops=int(((dl.index >= a) & (dl.index < b) & (dl <= -HALT)).sum()),
                 lowest=round(10000 + float((w[(w.index >= a) & (w.index < b)] - base).min())), failed=f"{fails}/{n}")
        out[pl] = r
        print(f"  {pl:<20} {r}")
    return out


def main(grid_dir):
    from research.search3.portfolio import core3 as C3
    from research.search2.portfolio import core as P
    surv = json.load(open(os.path.join(grid_dir, "survivors.json")))
    sets = {"step 1 (picked on old data only)": surv,
            "step 2 (old data + still profitable in the 3 unseen years)": [s for s in surv if s["y1"] > 0 and s["last2"] > 0]}
    report = {}
    for lab, ss in sets.items():
        pool = [as_pool(s) for s in ss]
        with Pool(2, maxtasksperchild=40) as pp:
            dev = list(pp.imap(C3.run, [(x, 0.01, DEV_START, DEV_END) for x in pool], chunksize=2))
        idx = pd.date_range(DEV_START, DEV_END, freq="h")
        Cm = np.zeros((len(dev), len(idx))); Wm = np.zeros_like(Cm)
        for i, (_, cv, _) in enumerate(dev):
            hw, hc = P.hourly(cv)
            Wm[i] = hw.reindex(idx).ffill().fillna(0).to_numpy(); Cm[i] = hc.reindex(idx).ffill().fillna(0).to_numpy()
        best = None
        for r in RISKS:
            e = fast_eval((r / 0.01) * Cm.sum(0), (r / 0.01) * Wm.sum(0), idx)
            print(f"  {lab[:6]} dev sizing {r*100:.2f}% each: {e}")
            if e["low"] >= -600 and e["halts"] <= 48:
                best = (r, e)
        if best is None:
            print(f"{lab}: no risk level fits"); continue
        r = best[0]
        print(f"{lab}: {len(ss)} strategies at {r*100:.2f}% each (chosen on 2019-23)")
        with Pool(2, maxtasksperchild=40) as pp:
            hold = list(pp.imap(C3.run, [(x, r, DEV_END, END) for x in pool], chunksize=2))
        report[lab] = dict(n=len(ss), risk=r, periods=replay(hold, DEV_END, END, f"{lab}: {len(ss)} strategies at {r*100:.2f}% each, UNSEEN"),
                           mix=[dict(x, risk=r) for x in pool])
    json.dump(report, open(os.path.join(grid_dir, "portfolio.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1])

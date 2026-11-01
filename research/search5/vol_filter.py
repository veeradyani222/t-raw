"""Round-5 idea 3b: a volatility-regime filter on existing strategies.

build_filtered wraps any builder: entries are dropped when the market's ATR(n_fast)/ATR(n_slow)
ratio sits above the rolling hi-quantile ("skip_high") or below the lo-quantile ("skip_low") of
its own last `win` bars (causal). Test: for every strategy in the live 23 and the relaxed-rule set,
base vs the two variants, full history at 1%; a variant is "chosen" on DEV data only
(dev $/month up by >= 20% with green years not lower), then the unseen periods are reported
for base and chosen.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.vol_filter
"""
import os, sys, json, importlib
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd
from research.search2.portfolio import core as P
from research.search3.portfolio import core3 as C3
from research.search5 import core5 as K
from research.search5.pool5 import build_pool


def _atr(df, n):
    h, l, c = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def build_filtered(df, base_module, base_fn, base_params, mode="skip_high", n_fast=14, n_slow=200, lo=0.1, hi=0.9, win=500):
    fn = getattr(importlib.import_module(base_module), base_fn)
    sigs = list(P.call(fn, df, base_params))
    ratio = _atr(df, n_fast) / _atr(df, n_slow)
    if mode == "skip_high":
        q = ratio.rolling(win, min_periods=win // 2).quantile(hi)
        block = (ratio > q).to_numpy()
    else:
        q = ratio.rolling(win, min_periods=win // 2).quantile(lo)
        block = (ratio < q).to_numpy()
    return [None if block[i] else s for i, s in enumerate(sigs)]


def variant(x, mode):
    v = dict(x, name=f"{x['name']}~{mode}", module="research.search5.vol_filter", fn="build_filtered",
             params=dict(base_module=x["module"], base_fn=x["fn"], base_params=x["params"], mode=mode))
    v["key"] = P.keyof(v)
    return v


def sim(x):
    _, cv, t = C3.run((x, 0.01, K.START, K.END))
    hw, hc = P.hourly(cv)
    return (hw.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32), hc.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32), t)


def main():
    pool = build_pool()
    C, W, trades = K.load_full(pool)
    mx = json.load(open(os.path.join(K.OUT, "mixes.json")))
    names = {s["name"] + " " + s["symbol"] for s in mx["mixes"]["live23"]["strategies"]} | set(mx["rules"]["relaxed"])
    base = [x for x in pool if f"{x['name']} {x['symbol']}" in names and trades[x["i"]] is not None]
    jobs = [variant(x, m) for x in base for m in ("skip_high", "skip_low")]
    print(f"{len(base)} strategies x 2 variants = {len(jobs)} sims", flush=True)
    with Pool(2, maxtasksperchild=20) as pp:
        res = list(pp.imap(sim, jobs, chunksize=2))
    rows = []
    for x in base:
        b = K.strat_stats(x, C[x["i"]], W[x["i"]], trades[x["i"]])
        best = None
        for m in ("skip_high", "skip_low"):
            j = jobs.index(next(v for v in jobs if v["name"] == f"{x['name']}~{m}" and v["symbol"] == x["symbol"]))
            w, c, t = res[j]
            s = K.strat_stats(dict(x, name=jobs[j]["name"]), c, w, t)
            s["mode"] = m
            if s.get("dev_pm") is not None and b.get("dev_pm") is not None:
                better = s["dev_pm"] >= max(b["dev_pm"] * 1.2, b["dev_pm"] + 5) and s["pos_years_dev"] >= b["pos_years_dev"]
                if better and (best is None or s["dev_pm"] > best["dev_pm"]):
                    best = s
            rows.append(dict(strategy=x["name"], symbol=x["symbol"], variant=m, dev_pm=s.get("dev_pm"), green=f"{s.get('pos_years_dev')}/{s.get('years_dev')}",
                             y1_pm=s.get("y1_pm"), last2_pm=s.get("last2_pm"), sepoct_pm=s.get("sepoct_pm"), chosen=False))
        rows.append(dict(strategy=x["name"], symbol=x["symbol"], variant="base", dev_pm=b.get("dev_pm"), green=f"{b.get('pos_years_dev')}/{b.get('years_dev')}",
                         y1_pm=b.get("y1_pm"), last2_pm=b.get("last2_pm"), sepoct_pm=b.get("sepoct_pm"), chosen=best is None))
        if best is not None:
            for r in rows:
                if r["strategy"] == x["name"] and r["symbol"] == x["symbol"] and r["variant"] == best["mode"]:
                    r["chosen"] = True
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(K.OUT, "vol_filter.csv"), index=False)
    ch = df[df.chosen]; bs = df[df.variant == "base"]
    n_f = int((ch.variant != "base").sum())
    print(f"\nfilter chosen on dev for {n_f} of {len(bs)} strategies")
    for lab, d in (("all base", bs), ("dev-chosen (base or filtered)", ch)):
        print(f"  {lab:32} sum $/mo at 1%: dev {d.dev_pm.sum():,.0f} | unseen yr {d.y1_pm.sum():,.0f} | last2 {d.last2_pm.sum():,.0f} | Sep+Oct {d.sepoct_pm.sum():,.0f}")
    f_only = ch[ch.variant != "base"]
    b_only = bs[bs.set_index(["strategy", "symbol"]).index.isin(f_only.set_index(["strategy", "symbol"]).index)]
    if len(f_only):
        print(f"  for the {n_f} filtered ones only: base unseen yr {b_only.y1_pm.sum():,.0f} -> filtered {f_only.y1_pm.sum():,.0f}; "
              f"base last2 {b_only.last2_pm.sum():,.0f} -> {f_only.last2_pm.sum():,.0f}; base Sep+Oct {b_only.sepoct_pm.sum():,.0f} -> {f_only.sepoct_pm.sum():,.0f}")
    pd.set_option("display.width", 220)
    print(df[df.chosen & (df.variant != "base")].round(0).to_string(index=False))


if __name__ == "__main__":
    main()

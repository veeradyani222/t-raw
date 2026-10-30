"""Scorer for the crypto group. Scores on 2024-10-20..now (PROP_OOS=1, split='oos'). Pool(2).
usage: python -m research.search3.crypto.run <batch>     (batches in batches.py)"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results.jsonl"
_CACHE = {}


def clean(df):
    """Data quality: drop bars of 'flat' server days (range < 5% of the median daily range).
    Returns (df, n_dropped_bars, n_flat_days)."""
    t = pd.DatetimeIndex(df["time"]).normalize()
    g = pd.DataFrame({"k": t.to_numpy(), "h": df["high"].to_numpy(float), "l": df["low"].to_numpy(float)})
    d = g.groupby("k").agg(h=("h", "max"), l=("l", "min"))
    rng = d.h - d.l
    flat = rng.index[rng < 0.05 * rng.median()]
    mask = ~np.isin(t.to_numpy(), flat.to_numpy())
    out = df[mask].reset_index(drop=True)
    out.attrs.update(df.attrs)
    return out, int((~mask).sum()), len(flat)


def load(sym, tf):
    os.environ["PROP_OOS"] = "1"
    from research.prop import harness as H
    df = H.load(sym, tf, split="oos")
    df, _, _ = clean(df)
    return df


def _one(cfg):
    try:
        return _inner(cfg)
    except Exception as e:
        _CACHE.clear()
        return dict(name=cfg[0], symbol=cfg[1], tf=cfg[2], fn=cfg[3], params=cfg[4],
                    error=f"{type(e).__name__}: {e}")


def _inner(cfg):
    os.environ["PROP_OOS"] = "1"
    from research.prop import harness as H
    from research.search3.crypto import costs, strategies as S
    costs.apply()
    name, sym, tf, fn, params = cfg
    key = (sym, tf)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = load(sym, tf)
    df = _CACHE[key]
    t0 = time.time()
    sigs = getattr(S, fn)(df, **params)
    n_sig = sum(x is not None for x in sigs)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    return dict(name=name, symbol=sym, tf=tf, fn=fn, params=params, best_risk=s["best_risk"],
                net=round(h.get("net", 0), 1), avg_month=round(h.get("avg_month", 0), 1),
                green=round(h.get("green_months", 0), 3), max_dd=round(h.get("max_dd", 0), 1),
                worst_day=round(h.get("worst_day", 0), 1), trades=h.get("trades", 0),
                win=round(h.get("win_rate", 0), 3), chal=round(h.get("challenge_pass_rate", 0), 3),
                net_025=round(s["by_risk"]["0.0025"]["net"], 1), signals=n_sig,
                months=h.get("months"), secs=round(time.time() - t0, 1))


def main(batch):
    from research.search3.crypto import batches as B
    cfgs = B.BATCHES[batch]()
    print(f"batch {batch}: {len(cfgs)} configs", flush=True)
    with Pool(2) as p, open(OUT, "a") as f:
        for row in p.imap_unordered(_one, cfgs, chunksize=2):
            row["batch"] = batch
            f.write(json.dumps(row) + "\n")
            f.flush()
            if "error" in row:
                print("ERR", row["name"], row["symbol"], row["tf"], row["error"], flush=True)
            else:
                br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "NONE"
                print(f"{row['name']:<28}{row['symbol']:<7}{row['tf']:<4}{br:>6} net {row['net']:>8.0f} "
                      f"avg/mo {row['avg_month']:>6.0f} dd {row['max_dd']:>6.0f} wd {row['worst_day']:>6.0f} "
                      f"tr {row['trades']:>4} win {row['win']:.2f} n025 {row['net_025']:>7.0f} {row['secs']}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

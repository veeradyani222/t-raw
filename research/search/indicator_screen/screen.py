"""Stage 1 screen: every rule x {no filter, SMA200 filter} x every symbol x {H1, H4}.

Fast pass: ONE simulate at 1% risk (fixed-dollar risk => P&L scales ~linearly
with risk), estimate best_risk by scaling DD / worst day, and split the run into
halves (2015-2019 / 2020-2023). Writes screen_results.csv. Stage 2 (verify.py)
re-scores the top rows with the real H.score.
"""
from __future__ import annotations

import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.prop import harness as H  # noqa: E402
from research.search.indicator_screen import strategies as S  # noqa: E402

OUT = Path(__file__).with_name(next((a.split("=")[1] for a in sys.argv if a.startswith("--out=")), "screen_results.csv"))
SYMS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
        "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY", "CADJPY", "EURGBP",
        "EURCHF", "GBPCHF", "AUDCAD", "US30", "US500", "USTEC", "DE40"]
TFS = [a.split("=")[1] for a in sys.argv if a.startswith("--tfs=")] or ["H1", "H4"]
TFS = TFS[0].split(",") if len(TFS) == 1 and "," in TFS[0] else TFS
HALF = pd.Timestamp("2020-01-01")


def quick(df, sigs, risk=0.01):
    res = H.simulate(df, sigs, risk=risk)
    m = H._metrics(res["curve"], res["trades"])
    cv, tr = res["curve"], res["trades"]
    best = None
    for r in H.RISKS:
        k = r / risk
        if m["max_dd"] * k > -H.SAFE_DD * H.BASELINE and m["worst_day"] * k > -H.SAFE_DAILY * H.BASELINE:
            best = r
    k = (best or 0) / risk
    a = cv[cv.time < HALF]; b = cv[cv.time >= HALF]
    na = float(a.close.iloc[-1]) if len(a) else 0.0
    nb = float(cv.close.iloc[-1]) - na
    ma = max(a.time.dt.to_period("M").nunique(), 1); mb = max(b.time.dt.to_period("M").nunique(), 1)
    pf = np.nan
    if len(tr):
        g, l = tr.profit[tr.profit > 0].sum(), -tr.profit[tr.profit < 0].sum()
        pf = g / l if l > 0 else np.inf
    return dict(trades=m["trades"], win=m["win_rate"], pf=pf, net1=m["net"],
                dd1=m["max_dd"], wd1=m["worst_day"], best_risk_est=best,
                avg_month_est=m["avg_month"] * k, max_dd_est=m["max_dd"] * k,
                worst_day_est=m["worst_day"] * k, green1=m["green_months"],
                h1_avgmo=na / ma, h2_avgmo=nb / mb)


def job(args):
    try:
        return _job(args)
    except Exception as e:  # e.g. MemoryError when the box is busy -> rerun later
        return [dict(symbol=args[0], tf=args[1], rule=f"ERROR {type(e).__name__}")]


def _job(args):
    sym, tf = args
    p = H.DATA / f"{sym.lower()}-{tf.lower()}.csv"
    if not p.exists():
        return [dict(symbol=sym, tf=tf, rule="MISSING")]
    try:
        df = H.load(sym, tf, split="is")
    except Exception as e:  # conversion series missing etc.
        return [dict(symbol=sym, tf=tf, rule=f"ERROR {e}")]
    rows = []
    for rule in S.RULES:
        lg, sh = S.rule_events(df, rule)
        for trend in (False, True):
            sigs = S.events_to_entries(df, lg, sh, trend=trend)
            r = quick(df, sigs)
            r.update(symbol=sym, tf=tf, rule=rule, trend=trend)
            rows.append(r)
    return rows


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(s, t) for s in SYMS for t in TFS]
    allrows = []
    done = set()
    if OUT.exists() and "--fresh" not in sys.argv:   # resume: keep finished (sym, tf)
        old = pd.read_csv(OUT)
        old = old[~old.rule.astype(str).str.startswith(("ERROR", "MISSING"))]
        allrows = old.to_dict("records")
        done = set(zip(old.symbol, old.tf))
    jobs = [j for j in jobs if j not in done]
    nproc = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--procs=")), 3))
    if nproc == 0:   # in-process (machine short on memory / handles)
        it = map(job, jobs)
    else:
        pool = Pool(nproc, maxtasksperchild=1)
        it = pool.imap_unordered(job, jobs)
    if True:
        for rows in it:
            allrows += rows
            pd.DataFrame(allrows).to_csv(OUT, index=False)
            print(rows[0]["symbol"], rows[0]["tf"], rows[0]["rule"] if len(rows) == 1 else len(rows),
                  f"{time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(allrows).to_csv(OUT, index=False)
    print("done", len(allrows), f"{time.time()-t0:.0f}s")

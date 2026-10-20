"""Stage 2: real H.score on shortlisted screen rows + halves + neighbours.

usage: python verify.py SYMBOL TF RULE TREND [k=v ...] [sides=long|short|both]
prints the H.score summary line, both halves at best_risk, and appends a row
to verify_results.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.prop import harness as H  # noqa: E402
from research.search.indicator_screen import strategies as S  # noqa: E402

OUT = Path(__file__).with_name("verify_results.csv")
HALF = pd.Timestamp("2020-01-01")
_CACHE = {}


def get_df(sym, tf):
    if (sym, tf) not in _CACHE:
        _CACHE[(sym, tf)] = H.load(sym, tf, split="is")
    return _CACHE[(sym, tf)]


def halves(df, sigs, risk):
    res = H.simulate(df, sigs, risk=risk)
    cv, tr = res["curve"], res["trades"]
    out = {}
    a = cv[cv.time < HALF]
    ta = tr[tr.entry_time < HALF] if len(tr) else tr
    ma = H._metrics(a.reset_index(drop=True), ta)
    mb = H._metrics(cv, tr, start=HALF)
    for tag, m in (("A", ma), ("B", mb)):
        out[f"{tag}_avgmo"] = m.get("avg_month", 0); out[f"{tag}_dd"] = m.get("max_dd", 0)
        out[f"{tag}_trades"] = m.get("trades", 0)
    return out


def run(sym, tf, rule, trend=False, sides="both", tag="", **p):
    df = get_df(sym, tf)
    sigs = S.build_rule(df, rule, trend=trend, sides=sides, **p)
    name = f"{rule}{'+T' if trend else ''}{'' if sides=='both' else '/'+sides}{tag}"
    if p:
        name += " " + ",".join(f"{k}={v}" for k, v in p.items())
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    row = dict(name=name, symbol=sym, tf=tf, rule=rule, trend=trend, sides=sides,
               params=json.dumps(p), best_risk=s["best_risk"], avg_month=h.get("avg_month"),
               net=h.get("net"), green=h.get("green_months"), max_dd=h.get("max_dd"),
               worst_day=h.get("worst_day"), trades=h.get("trades"),
               chal=h.get("challenge_pass_rate"), chal_days=h.get("challenge_median_days"))
    r = s["best_risk"] or 0.0025
    row.update(halves(df, sigs, r))
    print(H.summary_line(s), f"| halves@{r*100:.2f}%: A ${row['A_avgmo']:.0f}/mo  B ${row['B_avgmo']:.0f}/mo",
          flush=True)
    pd.DataFrame([row]).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    return row, s


if __name__ == "__main__":
    a = sys.argv[1:]
    kw = {}
    for x in a[4:]:
        k, v = x.split("=")
        try:
            v = json.loads(v)
        except Exception:
            pass
        kw[k] = v
    run(a[0], a[1], a[2], a[3] in ("1", "True", "T", "true"), **kw)

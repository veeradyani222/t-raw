import os, json, random
import numpy as np
from research.prop import harness as H
from research.search.jpy_session.strategies import build_index_turn_of_month as build
SYM, TF, P, R = "US500", "H1", dict(hour=22, hold=24, sl_atr=3), 0.0125

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8), e.max_hold)

df = H.load(SYM, TF, split="is")
full = [key(e) for e in build(df, **P)]
random.seed(7); causal = True
for k in random.sample(range(500, len(df) - 10), 5):
    sub = df.iloc[:k].copy(); sub.attrs = dict(df.attrs)
    part = [key(e) for e in build(sub, **P)]
    bad = [i for i in range(k) if part[i] != full[i]]
    print("k", k, "mismatches", len(bad))
    if bad: causal = False
print("causal_ok", causal, "IS entries", sum(x is not None for x in full))

os.environ["PROP_OOS"] = "1"
od = H.load(SYM, TF, split="oos")
sigs = build(od, **P)
a = H.score(od, sigs, risks=(R,), name="tom_us500_oos"); print(H.summary_line(a))
b = H.score(od, sigs, risks=(R,), spread_mult=2.0, name="tom_us500_oos_2x"); print(H.summary_line(b))
c = H.score(od, sigs, name="tom_us500_oos_full"); print(H.summary_line(c))
out = dict(causal_ok=causal, a=a["headline"], b={k: v for k, v in b["headline"].items() if k != "monthly"}, safe=c["best_risk"])
print(json.dumps(out, default=str))

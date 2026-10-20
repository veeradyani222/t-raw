import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.published_research.strategies import build_equity_calendar as build

P = {"tom_days_before": 0}
SYM, TF, RISK = "DE40", "H1", 0.0125

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df = H.load(SYM, TF, split="is")
full = build(df, **P)
random.seed(7)
causal_ok, diffs = True, []
for k in sorted(random.sample(range(500, len(df) - 10), 5)):
    sub = df.iloc[:k].copy(); sub.attrs = dict(df.attrs)
    part = build(sub, **P)
    for i in range(k):
        if key(part[i]) != key(full[i]):
            causal_ok = False; diffs.append((k, i, key(part[i]), key(full[i]))); break
print("causal_ok", causal_ok, diffs[:5])

os.environ["PROP_OOS"] = "1"
od = H.load(SYM, TF, split="oos")
sigs = build(od, **P)
def head(s):
    h = dict(s["headline"]); return h
a = H.score(od, sigs, risks=(RISK,), name="eqcal_oos")
b = H.score(od, sigs, risks=(RISK,), spread_mult=2.0, name="eqcal_oos_2x")
c = H.score(od, sigs, name="eqcal_oos_full")
print(H.summary_line(a)); print(H.summary_line(b)); print(H.summary_line(c))
print("best_risk_full", c["best_risk"])
print(json.dumps({"is_risk": head(a), "x2": head(b), "keys": list(a.keys())}, default=str))

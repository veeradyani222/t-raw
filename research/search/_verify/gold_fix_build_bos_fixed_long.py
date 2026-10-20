import os, sys, json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["PROP_OOS"] = "1"
from research.prop import harness as H
from research.search.gold_fix.strategies import build_bos_fixed_long as build

SYM, TF, RISK = "XAUUSD", "M30", 0.005
P = dict(atrp_min=0.6, tp_min_r=2, htf=["1D", 100])

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 6), None if e.tp is None else round(float(e.tp), 6))

df_is = H.load(SYM, TF, split="is")
full = [key(e) for e in build(df_is, **P)]
random.seed(7)
n = len(df_is)
causal_ok, diffs = True, []
for k in sorted(random.sample(range(n // 5, n - 10), 5)):
    sub = df_is.iloc[:k].copy(); sub.attrs = dict(df_is.attrs)
    part = [key(e) for e in build(sub, **P)]
    bad = [i for i in range(k) if part[i] != full[i]]
    if bad: causal_ok = False; diffs.append((k, len(bad), bad[:3]))
    print("k", k, "mismatches", len(bad), "entries", sum(x is not None for x in part))
print("causal_ok", causal_ok, diffs)

df = H.load(SYM, TF, split="oos")
sigs = build(df, **P)
s1 = H.score(df, sigs, risks=(RISK,), name="oos@is_risk"); print(H.summary_line(s1))
s2 = H.score(df, sigs, risks=(RISK,), spread_mult=2.0, name="oos@is_risk 2x"); print(H.summary_line(s2))
s3 = H.score(df, sigs, name="oos full"); print(H.summary_line(s3))
def clean(h):
    return json.loads(json.dumps(h, default=str))
out = dict(causal_ok=causal_ok, a=clean(s1["headline"]), b=clean({k:v for k,v in s2["headline"].items() if k!="monthly"}),
           safe=s3["best_risk"], by_risk=s3["by_risk"])
print("JSON", json.dumps(out, default=str))

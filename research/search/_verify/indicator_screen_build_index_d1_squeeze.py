import os, sys, json, random
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.indicator_screen.strategies import build_index_d1_squeeze as build

SYM, TF, P, R = "US500", "D1", {"n": 20, "q": 0.25, "trend": True}, 0.015

def key(e):
    return None if e is None else (e.side, e.sl, e.tp)

dfi = H.load(SYM, TF, split="is")
full = build(dfi, **P)
random.seed(7)
causal = True
for k in sorted(random.sample(range(600, len(dfi)), 5)):
    sub = dfi.iloc[:k].copy(); sub.attrs.update(dfi.attrs)
    part = build(sub, **P)
    bad = [i for i in range(k) if key(part[i]) != key(full[i])]
    print("k", k, "diffs", len(bad), bad[:5])
    if bad: causal = False
print("causal_ok", causal)

df = H.load(SYM, TF, split="oos")
sigs = build(df, **P)
s1 = H.score(df, sigs, risks=(R,), name="oos_is_risk"); print(H.summary_line(s1))
s2 = H.score(df, sigs, risks=(R,), spread_mult=2.0, name="oos_2x"); print(H.summary_line(s2))
s3 = H.score(df, sigs, name="oos_full"); print(H.summary_line(s3))
def clean(h):
    return json.loads(json.dumps(h, default=str))
print("JSON", json.dumps(dict(causal=causal, at=clean(s1["headline"]), x2=clean(s2["headline"]), safe=s3["best_risk"])))

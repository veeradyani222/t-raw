import os, sys, json, random
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.public_eas.strategies import build_filtered as build
P = {"base": "bb_breakout", "dev": 2.25, "trend_n": 1000}
SYM, TF, R = "XAUUSD", "H1", 0.005

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df = H.load(SYM, TF, split="is")
full = [key(e) for e in build(df, **P)]
random.seed(7)
causal = True
for k in random.sample(range(2000, len(df) - 1), 5):
    sub = df.iloc[:k].copy(); sub.attrs = dict(df.attrs)
    part = [key(e) for e in build(sub, **P)]
    diff = sum(1 for i in range(k) if part[i] != full[i])
    print("k", k, "diffs", diff)
    if diff: causal = False
print("causal_ok", causal)

def hl(s):
    h = dict(s["headline"]); return h
odf = H.load(SYM, TF, split="oos")
sigs = build(odf, **P)
s1 = H.score(odf, sigs, risks=(R,), name="oos_is_risk"); print(H.summary_line(s1))
s2 = H.score(odf, sigs, risks=(R,), spread_mult=2.0, name="oos_2x"); print(H.summary_line(s2))
s3 = H.score(odf, sigs, name="oos_full"); print(H.summary_line(s3)); print("oos_safe_risk", s3["best_risk"])
out = {"causal_ok": causal, "is_risk": hl(s1), "x2": hl(s2), "safe_risk": s3["best_risk"]}
print(json.dumps(out, default=str))

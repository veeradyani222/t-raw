import os, sys, json, random
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.trend.strategies import build_gold_boll80 as build

P = {"n": 80, "k": 2.5, "sl_mult": 3}
SYM, TF, R = "XAUUSD", "H4", 0.0125

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df = H.load(SYM, TF, split="is")
full = [key(e) for e in build(df, **P)]
random.seed(7)
ks = sorted(random.sample(range(300, len(df) - 1), 5))
causal = True; diffs = {}
for k in ks:
    sub = df.iloc[:k].copy(); sub.attrs.update(df.attrs)
    part = [key(e) for e in build(sub, **P)]
    bad = [i for i in range(k) if part[i] != full[i]]
    diffs[k] = len(bad)
    if bad: causal = False
print("causal", causal, diffs)

o = H.load(SYM, TF, split="oos")
sigs = build(o, **P)
a = H.score(o, sigs, risks=(R,), name="gold_boll80@IS")
b = H.score(o, sigs, risks=(R,), spread_mult=2.0, name="gold_boll80@IS 2x")
c = H.score(o, sigs, name="gold_boll80 full")
for s in (a, b, c): print(H.summary_line(s))
def hd(s):
    h = s["headline"]
    return {k: h.get(k) for k in ["net","avg_month","green_months","max_dd","worst_day","trades","challenge_pass_rate","challenge_median_days","firm_breach","monthly"]}
print(json.dumps({"causal": causal, "a": hd(a), "b": hd(b), "safe": c["best_risk"]}, default=str))

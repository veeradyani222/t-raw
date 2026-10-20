import os, json, random
os.environ["PROP_OOS"] = "1"
import sys; sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
from research.prop import harness as H
from research.search.breakout.strategies import build_jpy_inside_day as build
P = dict(tp_r=3, max_hold=48, sl="far"); SYM, TF, R = "USDJPY", "H1", 0.0075

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df = H.load(SYM, TF, split="is")
full = [key(e) for e in build(df, **P)]
random.seed(7); causal = True; bad = []
for k in random.sample(range(2000, len(df) - 10), 5):
    sub = df.iloc[:k].copy(); sub.attrs.update(df.attrs)
    part = [key(e) for e in build(sub, **P)]
    diff = [j for j in range(k) if part[j] != full[j]]
    if diff: causal = False; bad.append((k, diff[:5]))
print("causal", causal, bad)

od = H.load(SYM, TF, split="oos"); sigs = build(od, **P)
def head(s):
    h = dict(s["headline"]); return {k: h.get(k) for k in ["net","avg_month","green_months","max_dd","worst_day","trades","challenge_pass_rate","challenge_median_days","firm_breach","monthly"]}
a = H.score(od, sigs, risks=(R,), name="is_risk"); print(H.summary_line(a))
b = H.score(od, sigs, risks=(R,), spread_mult=2.0, name="2x"); print(H.summary_line(b))
c = H.score(od, sigs, name="full"); print(H.summary_line(c))
print(json.dumps(dict(causal=causal, at=head(a), x2=head(b), safe=c["best_risk"]), default=str))

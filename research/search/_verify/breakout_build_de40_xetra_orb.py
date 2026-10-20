import os, sys, json, random
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from research.prop import harness as H
from research.search.breakout.strategies import build_de40_xetra_orb as build

P = {"rs":10,"re":10.5,"te":12.5,"exit_h":18,"sl_frac":0.75,"trend":"d","min_rng":0.1,"tp_r":None}
SYM, TF, RISK = "DE40", "M30", 0.005

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 6), None if e.tp is None else round(float(e.tp), 6))

dfi = H.load(SYM, TF, split="is")
full = build(dfi, **P)
random.seed(7)
causal = True; bad = []
for k in sorted(random.sample(range(len(dfi)//5, len(dfi)), 5)):
    sub = dfi.iloc[:k].copy(); sub.attrs = dict(dfi.attrs)
    part = build(sub, **P)
    for i in range(k):
        if key(full[i]) != key(part[i]):
            causal = False; bad.append((k, i, key(full[i]), key(part[i]))); break
print("causal", causal, bad[:3])

df = H.load(SYM, TF, split="oos")
sigs = build(df, **P)
def hl(s):
    h = dict(s["headline"]); h["firm_breach"] = s.get("firm_breach", h.get("firm_breach"))
    return h
a = H.score(df, sigs, risks=(RISK,), name="oos_is"); print(H.summary_line(a))
b = H.score(df, sigs, risks=(RISK,), spread_mult=2.0, name="oos_2x"); print(H.summary_line(b))
c = H.score(df, sigs, name="oos_full"); print(H.summary_line(c))
out = {"causal": causal, "a": hl(a), "b": hl(b), "safe": c["best_risk"], "keys": list(a.keys())}
print(json.dumps(out, default=str))

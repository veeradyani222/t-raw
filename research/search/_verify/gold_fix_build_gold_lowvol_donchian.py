import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian as build

P = dict(n_entry=15, n_exit=7, atr_stop=2, trail_atr=5, atrp_max=0.5, atrp_window=500, adx_min=20)
SYM, TF, RISK = "XAUUSD", "H4", 0.005

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df = H.load(SYM, TF, split="is")
full = build(df, **P)
random.seed(7)
causal = True
for k in sorted(random.sample(range(800, len(df) - 1), 5)):
    sub = df.iloc[:k].copy(); sub.attrs.update(df.attrs)
    part = build(sub, **P)
    bad = [i for i in range(k) if key(part[i]) != key(full[i])]
    print("k", k, "mismatches", len(bad), bad[:5])
    if bad: causal = False
print("causal_ok", causal)

os.environ["PROP_OOS"] = "1"
od = H.load(SYM, TF, split="oos")
sigs = build(od, **P)
out = {}
for nm, kw in [("is_risk", dict(risks=(RISK,))), ("x2", dict(risks=(RISK,), spread_mult=2.0)), ("full", {})]:
    s = H.score(od, sigs, name=nm, **kw)
    print(H.summary_line(s))
    out[nm] = dict(best_risk=s["best_risk"], headline=s["headline"])
out["causal_ok"] = causal
json.dump(out, open(os.path.join(os.path.dirname(__file__), "gold_fix_build_gold_lowvol_donchian.json"), "w"), indent=1, default=str)
print(json.dumps(out, default=str))

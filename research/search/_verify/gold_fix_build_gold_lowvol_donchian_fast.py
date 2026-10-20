import os, json, random
os.environ["PROP_OOS"] = "1"
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian_fast as build

P = {"n_entry":15,"n_exit":5,"atr_stop":2,"trail_atr":4,"atrp_max":0.5,"atrp_window":500,"adx_min":20}
SYM, TF, R = "XAUUSD", "H4", 0.0075

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 6), None if e.tp is None else round(float(e.tp), 6))

dfi = H.load(SYM, TF, split="is")
full = build(dfi, **P)
random.seed(7)
causal = True; diffs = 0
for k in random.sample(range(600, len(dfi)), 5):
    sub = dfi.iloc[:k].copy(); sub.attrs = dict(dfi.attrs)
    part = build(sub, **P)
    for i in range(k):
        if key(part[i]) != key(full[i]):
            causal = False; diffs += 1
print("causal", causal, "diffs", diffs)

def head(s):
    h = dict(s["headline"]); return h
df = H.load(SYM, TF, split="oos")
sigs = build(df, **P)
a = H.score(df, sigs, risks=(R,), name="oos@is")
b = H.score(df, sigs, risks=(R,), spread_mult=2.0, name="oos2x")
c = H.score(df, sigs, name="oosfull")
for s in (a, b, c): print(H.summary_line(s))
out = dict(causal=causal, a=head(a), b=head(b), safe=c["best_risk"], cby=c["by_risk"])
print(json.dumps(out, default=str, indent=1))

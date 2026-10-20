"""OOS verifier for gold_boll50 (trend.build_gold_boll50). Params unchanged."""
import os, sys, json, random
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.trend.strategies import build_gold_boll50 as build_nlow

SYM, TF = "XAUUSD", "H4"
P = {"n": 50, "k": 2, "sl_mult": 2}
IS_RISK = 0.005

def key(e):
    return None if e is None else (e.side, round(float(e.sl), 8), None if e.tp is None else round(float(e.tp), 8))

df_is = H.load(SYM, TF, split="is")
full = build_nlow(df_is, **P)
random.seed(7)
causal = True
for k in random.sample(range(300, len(df_is)), 5):
    sub = df_is.iloc[:k].copy(); sub.attrs = dict(df_is.attrs)
    part = build_nlow(sub, **P)
    diff = [i for i in range(k) if key(part[i]) != key(full[i])]
    print("k", k, "diffs", len(diff))
    if diff: causal = False

df = H.load(SYM, TF, split="oos")
sigs = build_nlow(df, **P)
def head(s):
    h = dict(s["headline"]); h["best_risk"] = s["best_risk"]; return h
a = H.score(df, sigs, risks=(IS_RISK,), name="boll50_oos_isrisk")
b = H.score(df, sigs, risks=(IS_RISK,), spread_mult=2.0, name="boll50_oos_2xspread")
c = H.score(df, sigs, name="boll50_oos_full")
for s in (a, b, c): print(H.summary_line(s))
out = dict(causal_ok=causal, at_is=head(a), x2=head(b), safe_risk=c["best_risk"], full_head=head(c))
print("JSON", json.dumps(out, default=str))

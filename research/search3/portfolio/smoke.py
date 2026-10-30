"""Smoke: every pool-A strategy once at 1% through core3.run; compare net to the group's own number scaled to 1%."""
import os, sys, json, time, traceback
sys.path.insert(0, os.getcwd())
from research.search3.portfolio import core3 as C
from research.search2.portfolio import core as P

pool = json.load(open("research/search3/portfolio/pool_a.json"))
sel = sys.argv[1:] 
for x in pool:
    if sel and x["group"] not in sel: continue
    x = dict(x); x["fn"] = x["build_fn"]; x["key"] = P.keyof(x)
    t0 = time.time()
    try:
        k, cv, t = C.run((x, 0.01, C.START, C.END))
        net = float(cv.close.iloc[-1]) if len(cv) else 0.0
        exp = x["avg_month"] * 24 * 0.01 / x["best_risk"]
        big = (t.profit.abs().max() / abs(t.profit.sum())) if len(t) and t.profit.sum() != 0 else 0
        print(f"{x['group']:<15}{x['name']:<30}{x['symbol']:<8}{x['tf']:<4} net1% {net:>8,.0f}  expected~{exp:>8,.0f}  trades {len(t):>4} maxlots {t.lots.max() if len(t) else 0:>8}  biggest/net {big:.2f}  {time.time()-t0:.1f}s", flush=True)
    except Exception as e:
        print(f"{x['group']:<15}{x['name']:<30} ERROR {type(e).__name__}: {e}", flush=True)
        traceback.print_exc(limit=3)

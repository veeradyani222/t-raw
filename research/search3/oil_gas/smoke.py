import inspect, time
from research.search3.oil_gas import common as C, strategies as S
import os
if os.path.exists(C.RESULTS): os.remove(C.RESULTS)
fns = [f for f in dir(S) if f.startswith("build_")]
dfs = {tf: C.load("XTIUSD", tf)[0] for tf in ("M30", "H1", "H4", "D1")}
for fn in fns:
    b = getattr(S, fn)
    for tf in ("H1", "D1"):
        df = dfs[tf]
        if fn == "build_spread_reversion" and tf == "D1": continue
        t0 = time.time()
        try:
            sig = b(df); n = sum(s is not None for s in sig)
            ok, msg = C.causal_ok(b, df, {})
            print(f"{fn:<28}{tf:<4} signals {n:>5}  causal {ok} {msg if not ok else ''}  {time.time()-t0:.1f}s")
        except Exception as e:
            import traceback; traceback.print_exc(); print("ERR", fn, tf, e)

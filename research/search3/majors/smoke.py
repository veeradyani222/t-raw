import os, sys, time
os.environ["PROP_OOS"] = "1"; sys.path.insert(0, ".")
from research.prop import harness as H
from research.search3.majors import strategies as S
sym, tf = sys.argv[1], sys.argv[2]
df = H.load(sym, tf, split="oos")
for k, f in S.BUILDERS.items():
    t = time.time(); s = f(df); n = sum(x is not None for x in s)
    r = H.score(df, s, name=k); print(H.summary_line(r), f"{time.time()-t:.1f}s sig={n}", flush=True)

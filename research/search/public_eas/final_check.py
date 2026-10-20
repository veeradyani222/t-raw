"""Final in-sample checks for the shortlisted candidates: per-year net at best
risk, 2x spread, and the summary line. python -m research.search.public_eas.final_check"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import pandas as pd
from research.prop import harness as H
from research.search.public_eas import strategies as S

CANDS = [
    ("bb_trend_gold", "XAUUSD", "H1", "filtered", {"base": "bb_breakout", "dev": 2.25, "trend_n": 1000}),
    ("bb_gold", "XAUUSD", "H1", "bb_breakout", {"dev": 2.5}),
    ("connors_gbpusd", "GBPUSD", "D1", "connors_rsi2", {}),
    ("connors_nzdusd", "NZDUSD", "D1", "connors_rsi2", {}),
    ("connors_us500", "US500", "D1", "connors_rsi2", {}),
    ("picky_gbpjpy", "GBPJPY", "D1", "picky_breakout", {}),
    ("weekly_gbpjpy", "GBPJPY", "H1", "weekly_breakout", {}),
]
if __name__ == "__main__":
    for name, sym, tf, b, p in CANDS:
        df = H.load(sym, tf, "is")
        sg = S.BUILDERS[b](df, **p)
        s = H.score(df, sg, name=name)
        s2 = H.score(df, sg, name=name + "_2xspread", spread_mult=2.0)
        print(H.summary_line(s)); print(H.summary_line(s2))
        if s["best_risk"]:
            m = pd.Series(s["headline"]["monthly"])
            yr = m.groupby(m.index.str[:4]).sum().round(0).to_dict()
            print("   by year @best:", yr, " worst month", round(m.min()), " months", len(m))

"""Summarise results.jsonl: per-batch summary, candidate ranking, full table
(markdown) -> table.md, cands.json (for causal_check.py)."""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]
ok = [r for r in rows if "error" not in r]
err = [r for r in rows if "error" in r]
df = pd.DataFrame(ok)
df["pstr"] = df.params.apply(lambda p: ", ".join(f"{k}={v}" for k, v in p.items()))
df = df.drop_duplicates("key")
print(f"scored runs: {len(df)}  errors: {len(err)}")

cand = df[df.best_risk.notna() & (df.avg_month > 0)].copy()
print(f"candidates (safe risk + avg_month>0): {len(cand)}")

print("\n== per batch: n, #positive candidates, best avg_month, median avg_month ==")
g = df.groupby("batch").agg(n=("key", "size"), pos=("avg_month", lambda x: int(((x > 0) & df.loc[x.index, "best_risk"].notna()).sum())),
                            best=("avg_month", "max"), med=("avg_month", "median"), med025=("net_025", "median"))
print(g.sort_values("best", ascending=False).round(1).to_string())

print("\n== per idea x symbol: best avg_month ==")
print(df.pivot_table(index="idea", columns="symbol", values="avg_month", aggfunc="max").round(0).to_string())

top = cand.sort_values("avg_month", ascending=False)
print("\n== top 40 candidates ==")
cols = ["batch", "symbol", "tf", "pstr", "spread_mult", "best_risk", "avg_month", "net", "green", "max_dd", "worst_day", "trades", "win", "chal"]
print(top[cols].head(40).round(3).to_string(index=False))

# full markdown table
lines = ["| batch | idea | symbol | tf | params | sm | best_risk | net | avg_month | green | max_dd | worst_day | trades | win | chal | net_025 | months |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in df.sort_values(["batch", "symbol", "tf"]).itertuples():
    br = "" if pd.isna(r.best_risk) else f"{r.best_risk*100:.2f}%"
    lines.append(f"| {r.batch} | {r.idea} | {r.symbol} | {r.tf} | {r.pstr} | {r.spread_mult} | {br} | {r.net:.0f} | {r.avg_month:.1f} | "
                 f"{r.green:.2f} | {r.max_dd:.0f} | {r.worst_day:.0f} | {r.trades} | {r.win:.2f} | {r.chal:.2f} | {r.net_025:.0f} | {r.months} |")
open(os.path.join(HERE, "table.md"), "w").write("\n".join(lines))
json.dump([dict(idea=r.idea, symbol=r.symbol, tf=r.tf, params=r.params) for r in top.head(int(sys.argv[1]) if len(sys.argv) > 1 else 30).itertuples()],
          open(os.path.join(HERE, "cands.json"), "w"), indent=1, default=str)

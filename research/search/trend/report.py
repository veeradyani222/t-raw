"""Summarise results.jsonl: python -m research.search.trend.report [filter-substring] [top]"""
import json
import sys
from pathlib import Path

import pandas as pd

rows = [json.loads(l) for l in Path(__file__).with_name("results.jsonl").read_text().splitlines() if l.strip()]
df = pd.DataFrame([r for r in rows if "error" not in r])
flt = sys.argv[1] if len(sys.argv) > 1 else ""
top = int(sys.argv[2]) if len(sys.argv) > 2 else 40
if flt:
    df = df[df.name.str.contains(flt)]
df["br"] = df.best_risk.fillna(0) * 100
df["ratio"] = df.net / (-df.max_dd).clip(lower=50)  # at headline risk (0.25% R-view is distorted by min-lot on D1)
cols = ["name", "symbol", "tf", "br", "avg_month", "max_dd", "worst_day", "trades", "net_R", "dd_R", "ratio"]
pd.set_option("display.width", 220)
print(df.sort_values("ratio", ascending=False)[cols].head(top).round(1).to_string(index=False))
print("\nby strategy (median ratio, n, n positive netR):")
g = df.groupby("name").agg(med=("ratio", "median"), n=("ratio", "size"), pos=("net_R", lambda x: (x > 0).sum()))
print(g.sort_values("med", ascending=False).round(2).to_string())
g = df.groupby(["symbol", "tf"]).agg(med=("ratio", "median"), pos=("net_R", lambda x: (x > 0).sum()), n=("ratio", "size"))
print(g.sort_values("med", ascending=False).round(2).to_string())

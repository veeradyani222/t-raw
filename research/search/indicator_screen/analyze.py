"""Print ranked screen table + per-rule summary (reads screen_results.csv)."""
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
d = pd.read_csv(Path(__file__).with_name("screen_results.csv"))
miss = d[d.trades.isna()]
d = d[d.trades.notna()].copy()
print(len(d), "runs on", d.groupby(["symbol", "tf"]).ngroups, "symbol/tf;  net>0:", (d.net1 > 0).sum(),
      " both halves>0:", ((d.h1_avgmo > 0) & (d.h2_avgmo > 0)).sum())
print("missing/error:", sorted(set(zip(miss.symbol, miss.tf, miss.rule))))
c = ["symbol", "tf", "rule", "trend", "trades", "win", "pf", "net1", "dd1", "wd1", "best_risk_est",
     "avg_month_est", "h1_avgmo", "h2_avgmo"]
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
print(d.sort_values("avg_month_est", ascending=False)[c].head(n).round(2).to_string())
g = d.groupby(["rule", "trend"]).agg(runs=("net1", "size"), mean_net=("net1", "mean"),
                                       share_pos=("net1", lambda x: (x > 0).mean()),
                                       mean_pf=("pf", "mean"))
print(g.sort_values("mean_net").round(2).to_string())
print(d.groupby("symbol").net1.agg(["mean", lambda x: (x > 0).mean()]).round(2))

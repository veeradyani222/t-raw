"""Rank results.jsonl: candidates = best_risk not None and avg_month > 0.
    python -m research.search3.commodity_fx.table [N]  -> top N + markdown table of all runs
"""
import json, sys
from pathlib import Path
import pandas as pd

P = Path(__file__).with_name("results.jsonl")
rows = [json.loads(l) for l in P.read_text().splitlines() if l.strip()]
df = pd.DataFrame(rows)
errs = df[df.get("error").notna()] if "error" in df else df.iloc[0:0]
ok = df[df.get("error").isna()] if "error" in df else df
print(f"runs {len(df)}  errors {len(errs)}")
cand = ok[(ok.best_risk.notna()) & (ok.avg_month > 0)].sort_values("avg_month", ascending=False)
print(f"candidates {len(cand)} / {len(ok)}")
cols = ["name", "symbol", "tf", "best_risk", "avg_month", "net", "max_dd", "worst_day", "trades", "green_months", "win_rate"]
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
print(cand[cols].head(n).to_string(index=False))
print("\nbest per idea:")
print(cand.groupby("build_fn").head(1)[cols].to_string(index=False))
if "--md" in sys.argv:
    out = Path(__file__).with_name("_table.md")
    t = ok.sort_values(["build_fn", "symbol", "tf", "avg_month"], ascending=[True, True, True, False])
    lines = ["| idea | run | symbol | tf | best_risk | avg/mo | net | maxDD | worst day | trades | green |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        br = "none" if pd.isna(r.best_risk) else f"{r.best_risk*100:.2f}%"
        lines.append(f"| {r.build_fn} | {r['name']} | {r.symbol} | {r.tf} | {br} | {r.avg_month:,.0f} | {r.net:,.0f} | {r.max_dd:,.0f} | {r.worst_day:,.0f} | {r.trades} | {r.green_months*100:.0f}% |")
    out.write_text("\n".join(lines))
    print("wrote", out)

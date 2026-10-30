"""Summaries of results.jsonl: top runs overall, top per idea/symbol, full table."""
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
df = pd.DataFrame(rows)
err = df[df.get("error").notna()] if "error" in df else df.iloc[0:0]
ok = df[df.get("error").isna()] if "error" in df else df
ok = ok.copy()
ok["cand"] = ok.best_risk.notna() & (ok.avg_month > 0)
ok["idea"] = ok.fn.str.replace("build_", "")
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 500)
cols = ["batch", "name", "symbol", "tf", "best_risk", "avg_month", "net", "green", "max_dd", "worst_day", "trades", "win", "chal", "net_025"]

mode = sys.argv[1] if len(sys.argv) > 1 else "top"
if mode == "top":
    print(f"runs {len(df)} errors {len(err)} candidates {int(ok.cand.sum())}")
    if len(err):
        print(err[["name", "symbol", "tf", "error"]].head(20).to_string())
    print("\n== top 40 overall by avg_month (candidates only) ==")
    print(ok[ok.cand].sort_values("avg_month", ascending=False)[cols].head(40).to_string(index=False))
    print("\n== best per idea x symbol ==")
    best = ok[ok.cand].sort_values("avg_month", ascending=False).groupby(["idea", "symbol"]).head(1)
    print(best.sort_values("avg_month", ascending=False)[["idea"] + cols].to_string(index=False))
    print("\n== idea summary: n runs, n candidates, mean avg_month, median ==")
    g = ok.groupby("idea").agg(runs=("name", "size"), cands=("cand", "sum"), mean_am=("avg_month", "mean"), med_am=("avg_month", "median"), best=("avg_month", "max"))
    print(g.sort_values("best", ascending=False).round(1).to_string())
    print("\n== per symbol: n cands, best ==")
    print(ok.groupby("symbol").agg(runs=("name", "size"), cands=("cand", "sum"), best=("avg_month", "max"), mean=("avg_month", "mean")).round(1).to_string())
elif mode == "md":
    out = ["| batch | name | symbol | tf | params | best_risk | avg_month | net | green | max_dd | worst_day | trades | win | chal | net_025 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ok.sort_values(["batch", "symbol", "tf", "name"]).itertuples():
        br = f"{r.best_risk*100:.2f}%" if pd.notna(r.best_risk) else ""
        p = json.dumps(r.params, default=str).replace("|", "/")
        out.append(f"| {r.batch} | {r.name} | {r.symbol} | {r.tf} | {p} | {br} | {r.avg_month} | {r.net} | {r.green} | {r.max_dd} | {r.worst_day} | {r.trades} | {r.win} | {r.chal} | {r.net_025} |")
    (HERE / "all_runs.md").write_text("\n".join(out), encoding="utf-8")
    print("wrote", len(out) - 2, "rows")
elif mode == "idea":
    idea = sys.argv[2]
    sub = ok[ok.idea == idea].sort_values("avg_month", ascending=False)
    print(sub[cols + ["params"]].head(int(sys.argv[3]) if len(sys.argv) > 3 else 40).to_string(index=False))

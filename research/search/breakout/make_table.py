"""Render every scored run in results.jsonl as a markdown table (for NOTES.md)."""
import json
from pathlib import Path
rows = [json.loads(l) for l in (Path(__file__).parent / "results.jsonl").open()]
ok = {json.dumps([r["name"], r["symbol"], r["tf"], r.get("params")], sort_keys=True, default=str): r
      for r in rows if "error" not in r}
rs = sorted(ok.values(), key=lambda r: (r["best_risk"] is not None, r["avg_month"]), reverse=True)
out = ["| # | name | symbol | tf | best_risk | avg_month $ | max_dd $ | worst_day $ | trades | net@0.25% $ |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for k, r in enumerate(rs, 1):
    br = f"{r['best_risk']*100:.2f}%" if r["best_risk"] else "none"
    out.append(f"| {k} | {r['name']} | {r['symbol']} | {r['tf']} | {br} | {r['avg_month']:.0f} | "
               f"{r['max_dd']:.0f} | {r['worst_day']:.0f} | {r['trades']} | {r['net_025']:.0f} |")
print("\n".join(out))

"""Print results.jsonl as a table. usage: show.py [filter-substring] [sort]"""
import json, sys
from pathlib import Path
rows = [json.loads(l) for l in (Path(__file__).parent / "results.jsonl").open()]
f = sys.argv[1] if len(sys.argv) > 1 else ""
rows = [r for r in rows if "error" not in r and f in (r["name"] + r["symbol"] + r["tf"])]
rows = list({json.dumps([r["name"], r["symbol"], r["tf"], r.get("params")], sort_keys=True): r for r in rows}.values())
if len(sys.argv) > 2:
    rows.sort(key=lambda r: (r["best_risk"] is not None, r["avg_month"]), reverse=True)
for r in rows:
    br = f"{r['best_risk']*100:.2f}" if r["best_risk"] else "NONE"
    yrs = "".join("+" if v > 0 else "-" for v in (r.get("by_year") or {}).values())
    print(f"{r['name']:<36}{r['symbol']:<7}{r['tf']:<4}{br:<6}{r['avg_month']:>6.0f}{r['max_dd']:>7.0f}"
          f"{r['worst_day']:>6.0f}{r['trades']:>6} w{r['win']:.2f} c{r['chal']:.2f} n025 {r['net_025']:>6.0f} {yrs}")
print(len(rows), "rows")

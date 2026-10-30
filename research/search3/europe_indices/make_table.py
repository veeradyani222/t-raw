"""Print the scored-run table (markdown) from results.jsonl."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
rows = [r for r in rows if "error" not in r]
seen = {}
for r in rows:
    seen[(r["name"], r["symbol"], r["tf"])] = r
rows = list(seen.values())
rows.sort(key=lambda r: (r["best_risk"] is None, -(r["avg_month"] if r["best_risk"] else -1e9)))
top = int(sys.argv[1]) if len(sys.argv) > 1 else len(rows)
print(f"{len(rows)} scored runs; {sum(1 for r in rows if r['best_risk'] and r['avg_month'] > 0)} safe and positive\n")
print("| # | builder | symbol | tf | params | best_risk | avg_month $ | net $ | max_dd $ | worst_day $ | trades | green | win% |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, r in enumerate(rows[:top], 1):
    br = f"{r['best_risk']*100:.2f}%" if r["best_risk"] else "none"
    p = json.dumps(r["params"], default=str).replace("|", "/")
    print(f"| {k} | {r['builder']} | {r['symbol']} | {r['tf']} | `{p}` | {br} | {r['avg_month']:.0f} | {r['net']:.0f} | "
          f"{r['max_dd']:.0f} | {r['worst_day']:.0f} | {r['trades']} | {r['green_months']*100:.0f}% | {r['win_rate']*100:.0f}% |")

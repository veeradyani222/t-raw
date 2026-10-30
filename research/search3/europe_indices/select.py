"""Pick candidates: safe (best_risk not None) and avg_month > 0, best run per
(builder, symbol), ranked by avg_month. UK100 is excluded (48 days of data in
the scoring window, see NOTES). Writes candidates.jsonl (top N)."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
MIN_TRADES = int(sys.argv[2]) if len(sys.argv) > 2 else 20
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
rows = [r for r in rows if "error" not in r and r["best_risk"] and r["avg_month"] > 0 and r["symbol"] != "UK100"
        and r["trades"] >= MIN_TRADES]
best = {}
for r in rows:
    k = (r["builder"], r["symbol"])
    if k not in best or r["avg_month"] > best[k]["avg_month"]:
        best[k] = r
top = sorted(best.values(), key=lambda r: -r["avg_month"])
# at most 2 per builder, at most 3 per symbol for diversity
out, nb, ns = [], {}, {}
for r in top:
    if nb.get(r["builder"], 0) >= 2 or ns.get(r["symbol"], 0) >= 3:
        continue
    out.append(r); nb[r["builder"]] = nb.get(r["builder"], 0) + 1; ns[r["symbol"]] = ns.get(r["symbol"], 0) + 1
    if len(out) >= N:
        break
with (HERE / "candidates.jsonl").open("w") as f:
    for r in out:
        f.write(json.dumps(r, default=str) + "\n")
for r in out:
    print(f"{r['builder']:<18} {r['symbol']:<6} {r['tf']:<4} risk {r['best_risk']*100:.2f}% avg/mo {r['avg_month']:7.1f} net {r['net']:8.0f} "
          f"dd {r['max_dd']:7.0f} wd {r['worst_day']:7.0f} trades {r['trades']:4d} green {r['green_months']*100:.0f}%  {r['params']}")

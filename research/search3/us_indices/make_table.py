"""Print the results table (markdown) from results.jsonl. Usage: make_table.py [top N | all]"""
import json, sys
from pathlib import Path

rows = [json.loads(l) for l in Path(__file__).with_name("results.jsonl").read_text().splitlines() if l.strip()]
rows = [r for r in rows if "error" not in r]
def key(r):
    return (r["best_risk"] is not None and (r["avg_month"] or 0) > 0, r["avg_month"] or -1e9)
rows.sort(key=key, reverse=True)
mode = sys.argv[1] if len(sys.argv) > 1 else "40"
sel = rows if mode == "all" else rows[: int(mode)]
print(f"scored runs: {len(rows)}; candidates (safe risk & avg_month>0): {sum(1 for r in rows if key(r)[0])}; causal failures: {sum(1 for r in rows if not r['causal_ok'])}\n")
print("| name | sym | tf | risk | $/mo | net | green | maxDD | worst day | trades | win | causal |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in sel:
    br = f"{r['best_risk']*100:.2f}%" if r["best_risk"] else "none"
    print(f"| {r['name']} | {r['symbol']} | {r['tf']} | {br} | {r['avg_month'] or 0:.0f} | {r['net'] or 0:.0f} | "
          f"{(r['green_months'] or 0)*100:.0f}% | {r['max_dd'] or 0:.0f} | {r['worst_day'] or 0:.0f} | {r['trades']} | "
          f"{(r['win_rate'] or 0)*100:.0f}% | {'ok' if r['causal_ok'] else 'FAIL'} |")

"""Print results.jsonl as a table (optionally filtered by tag / ea)."""
import json, sys
from pathlib import Path
rows = [json.loads(l) for l in Path(__file__).with_name("results.jsonl").read_text().splitlines()]
rows = [r for r in rows if not r.get("missing")]
args = sys.argv[1:]
for a in args:
    k, v = a.split("=")
    rows = [r for r in rows if str(r.get(k)) == v or (k == "ea~" and v in r["ea"])]
rows.sort(key=lambda r: (r["best_risk"] is not None, r["avg_month"] if r["best_risk"] else -1e9), reverse=True)
print(f"{'label':<52}{'sym':<7}{'tf':<4}{'risk':>6}{'avg/mo':>8}{'net':>8}{'maxDD':>7}{'wDay':>6}{'tr':>6}{'grn':>5}{'chal':>5}{'r.25net':>8}")
for r in rows:
    br = f"{r['best_risk']*100:.2f}" if r["best_risk"] else "none"
    print(f"{r['label'][:51]:<52}{r['symbol']:<7}{r['tf']:<4}{br:>6}{r['avg_month']:>8.0f}{r['net']:>8.0f}{r['max_dd']:>7.0f}{r['worst_day']:>6.0f}{r['trades']:>6}{r['green']*100:>5.0f}{r['chal']*100:>5.0f}{r['r025']:>8.0f}")
print(len(rows), "runs")

"""Pick the final candidates (distinct idea x market) from results.jsonl ->
cands8.json (for causal_check.py) and final.json (for the round-3 report)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]
ok = {}
for r in rows:
    if "error" not in r:
        ok[r["key"]] = r            # last write wins
rows = list(ok.values())
cand = [r for r in rows if r["best_risk"] is not None and r["avg_month"] > 0 and r["spread_mult"] == 1.0
        and r["idea"] != "rollover_dip"]
cand.sort(key=lambda r: -r["avg_month"])
picked, seen = [], set()
for r in cand:
    k = (r["idea"], r["symbol"])
    if k in seen:
        continue
    seen.add(k)
    picked.append(r)
    if len(picked) == 8:
        break
json.dump([dict(idea=r["idea"], symbol=r["symbol"], tf=r["tf"], params=r["params"]) for r in picked],
          open(os.path.join(HERE, "cands8.json"), "w"), indent=1)
json.dump(picked, open(os.path.join(HERE, "final.json"), "w"), indent=1)
for r in picked:
    print(f"{r['idea']:24s} {r['symbol']} {r['tf']} {r['params']} risk={r['best_risk']} avg/mo={r['avg_month']:.0f} "
          f"net={r['net']:.0f} dd={r['max_dd']:.0f} wd={r['worst_day']:.0f} n={r['trades']} green={r['green']:.2f}")
print("scored runs:", len(rows))

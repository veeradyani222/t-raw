import json
from pathlib import Path
rows = [json.loads(l) for l in (Path(__file__).parent / "results.jsonl").open()]
ok = {json.dumps([r["name"], r["symbol"], r["tf"], r.get("params")], sort_keys=True, default=str): r for r in rows if "error" not in r}
print(len(ok), "unique scored;", sum(r["best_risk"] is not None and r["avg_month"] > 0 for r in ok.values()), "safe & positive")
miss = {(r["symbol"], r["tf"]) for r in rows if "error" in r and r["error"].startswith("missing")}
print("missing files:", sorted(miss))

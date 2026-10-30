"""Pick up to 8 candidates: best_risk set, avg_month > 0, trades >= 30, ranked by
avg_month, at most one per (idea, symbol) and at most 3 per idea. Writes candidates.json
for causal_check.py."""
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
df = pd.DataFrame([r for r in rows if "error" not in r])
df["idea"] = df.fn.str.replace("build_", "")
c = df[df.best_risk.notna() & (df.avg_month > 0) & (df.trades >= 30)].sort_values("avg_month", ascending=False)
out, per_idea = [], {}
for r in c.itertuples():
    if any(o["build_fn"] == r.fn and o["symbol"] == r.symbol for o in out):
        continue
    if per_idea.get(r.idea, 0) >= 3:
        continue
    per_idea[r.idea] = per_idea.get(r.idea, 0) + 1
    out.append(dict(name=f"{r.name}_{r.symbol}_{r.tf}".replace(":", ""), symbol=r.symbol, tf=r.tf,
                    module="research.search3.metals.strategies", build_fn=r.fn, params=r.params,
                    idea=r.idea, exit_type=""))
    if len(out) >= 8:
        break
json.dump(out, open(HERE / "candidates.json", "w"), indent=1, default=str)
for o in out:
    print(o["name"], o["symbol"], o["tf"])

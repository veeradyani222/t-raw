"""Summarise runs.jsonl: full table (out/runs_table.md), top candidates per idea
and symbol, and a look-ahead re-check on the shortlisted ones (out/top.json)."""
from __future__ import annotations
import json, os, sys
import pandas as pd
from research.search3.oil_gas import common as C, strategies as S

HERE = os.path.dirname(__file__)
rows, bad = [], 0
for l in open(C.RESULTS):
    for piece in l.replace("}{", "}\n{").split("\n"):
        piece = piece.strip()
        if not piece:
            continue
        try:
            rows.append(json.loads(piece))
        except Exception:
            bad += 1
print("unparseable fragments (two processes appended at once):", bad)
df = pd.DataFrame(rows)
df["idea"] = df.build_fn.str[6:]
print("scored runs:", len(df), " with best_risk:", df.best_risk.notna().sum(),
      " candidates (risk & avg_month>0):", ((df.best_risk.notna()) & (df.avg_month > 0)).sum())

# full table
tab = df[["name", "symbol", "tf", "best_risk", "avg_month", "net", "max_dd", "worst_day", "trades", "win", "green"]].copy()
tab["best_risk"] = tab.best_risk.map(lambda x: "" if pd.isna(x) else f"{x*100:.2f}%")
tab = tab.sort_values("avg_month", ascending=False)
with open(os.path.join(HERE, "out", "runs_table.md"), "w") as f:
    f.write("| name | symbol | tf | best_risk | avg_month | net | max_dd | worst_day | trades | win | green |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
    for r in tab.itertuples(index=False):
        f.write("| " + " | ".join(str(x) for x in r) + " |\n")

cand = df[df.best_risk.notna() & (df.avg_month > 0)].sort_values("avg_month", ascending=False)
print("\n== best per idea x symbol ==")
best = cand.groupby(["idea", "symbol"]).head(1).sort_values("avg_month", ascending=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
print(best[["name", "symbol", "tf", "best_risk", "avg_month", "net", "max_dd", "worst_day", "trades", "win", "green"]].head(40).to_string(index=False))

# per-idea summary
print("\n== per idea: runs / candidates / best avg_month ==")
g = df.groupby("idea").agg(runs=("name", "size"), cands=("avg_month", lambda x: int(((x > 0) & df.loc[x.index, "best_risk"].notna()).sum())), best=("avg_month", "max"))
print(g.sort_values("best", ascending=False).to_string())

if "--check" in sys.argv:
    top = best.head(int(sys.argv[sys.argv.index("--check") + 1]) if len(sys.argv) > sys.argv.index("--check") + 1 else 12)
    out = []
    for r in top.itertuples(index=False):
        d, _ = C.load(r.symbol, r.tf)
        ok, msg = C.causal_ok(getattr(S, r.build_fn), d, r.params, seed=7)
        print(f"causal {r.name} {r.symbol} {r.tf}: {ok} {msg}")
        out.append(dict(r._asdict(), causal_ok=bool(ok)))
    json.dump(out, open(os.path.join(HERE, "out", "top.json"), "w"), indent=1, default=str)

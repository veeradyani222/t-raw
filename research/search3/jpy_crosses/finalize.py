"""Fill the results section of NOTES.md from results.jsonl and print the
candidate list (best run per idea/market family, ranked by avg_month).

    python -m research.search3.jpy_crosses.finalize
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from research.search3.jpy_crosses.report import df, table

HERE = Path(__file__).resolve().parent
NOTES = HERE / "NOTES.md"
START, END = "<!-- RESULTS START -->", "<!-- RESULTS END -->"

ok = df[df.ok].sort_values("avg_month", ascending=False)
ideas = df.groupby("fn").agg(runs=("name", "size"), mean_mo=("avg_month", "mean"),
                             best_mo=("avg_month", "max"), ok=("ok", "sum")).sort_values("best_mo", ascending=False)

# candidates: best run per (idea family, symbol); then at most 2 per idea family, 8 total
fam = ok[ok.fn != "build_rollover"].assign(fam=ok.fn.str.replace("build_", ""))   # rollover = spread artefact, see NOTES
best = fam.sort_values("avg_month", ascending=False).drop_duplicates(["fam", "symbol"])
cands, per_fam = [], {}
for r in best.itertuples():
    if per_fam.get(r.fam, 0) >= 2:
        continue
    per_fam[r.fam] = per_fam.get(r.fam, 0) + 1
    cands.append(r)
    if len(cands) == 8:
        break

sec = [START, "## Results", "",
       f"Scored runs: **{len(df)}** ({df.fn.nunique()} builders / ideas, {df.symbol.nunique()} symbols, "
       f"timeframes {', '.join(sorted(df.tf.unique()))}). Candidates (best_risk set and avg_month > 0): "
       f"**{int(df.ok.sum())}**. Look-ahead check failures: **{int((~df.causal_ok).sum())}**.", "",
       "### Ideas ranked by their best run (avg $/month at best_risk)", "",
       "| idea | runs | mean avg/mo | best avg/mo | candidates |", "|---|---|---|---|---|"]
for k, r in ideas.iterrows():
    sec.append(f"| {k.replace('build_', '')} | {r.runs} | {r.mean_mo:.1f} | {r.best_mo:.1f} | {int(r.ok)} |")
sec += ["", "### Top 40 candidate runs", "", table(ok.head(40)), "",
        "### Every scored run", "", table(df.sort_values(['batch', 'name', 'symbol', 'tf'])), END]
text = NOTES.read_text()
if START in text:
    pre, rest = text.split(START, 1)
    post = rest.split(END, 1)[1] if END in rest else ""
    text = pre + "\n".join(sec) + post
else:
    text = text.replace("RESULTS_PLACEHOLDER", "\n".join(sec))
NOTES.write_text(text)
print(f"NOTES.md written: {len(df)} runs")
print(json.dumps([dict(name=r.name, symbol=r.symbol, tf=r.tf, fn=r.fn, params=r.params, best_risk=r.best_risk,
                       avg_month=round(r.avg_month, 1), net=round(r.net), max_dd=round(r.max_dd), worst_day=round(r.worst_day),
                       trades=int(r.trades), green=round(r.green, 2), causal_ok=bool(r.causal_ok)) for r in cands], indent=1))

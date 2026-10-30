"""Summarise results.jsonl: top runs and the full markdown table for NOTES.md.

    python -m research.search3.jpy_crosses.report [top]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines() if l.strip()]
df = pd.DataFrame(rows)
df["ok"] = df.best_risk.notna() & (df.avg_month > 0)


def fmt(v, d=0):
    return "-" if pd.isna(v) else f"{v:.{d}f}"


def table(d):
    out = ["| # | batch | name | symbol | tf | params | best risk | net | avg/mo | green | maxDD | worst day | trades | win | causal |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(d.itertuples(), 1):
        p = ", ".join(f"{k}={v}" for k, v in r.params.items()) or "-"
        br = "none safe" if pd.isna(r.best_risk) else f"{r.best_risk*100:.2f}%"
        out.append(f"| {n} | {r.batch} | {r.name} | {r.symbol} | {r.tf} | {p} | {br} | {fmt(r.net)} | {fmt(r.avg_month, 1)} | "
                   f"{fmt(r.green*100)}% | {fmt(r.max_dd)} | {fmt(r.worst_day)} | {r.trades} | {fmt(r.win, 2)} | {'ok' if r.causal_ok else 'FAIL'} |")
    return "\n".join(out)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "top"
    if mode == "top":
        print(f"{len(df)} scored runs, {df.ok.sum()} candidates (best_risk set and avg_month>0), causal fails: {(~df.causal_ok).sum()}")
        top = df[df.ok].sort_values("avg_month", ascending=False).head(40)
        print(table(top))
        print("\nby idea (fn): mean avg_month over all runs, best run")
        g = df.groupby("fn").agg(runs=("name", "size"), mean_mo=("avg_month", "mean"), best_mo=("avg_month", "max"), ok=("ok", "sum"))
        print(g.sort_values("best_mo", ascending=False).to_string())
    else:
        print(table(df))

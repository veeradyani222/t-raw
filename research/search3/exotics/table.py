"""Summarise results.jsonl -> markdown table (all runs) + top candidates.
    python -m research.search3.exotics.table [top_n]"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def load():
    rows, bad = [], 0
    for l in (HERE / "results.jsonl").read_text().splitlines():
        if not l.strip():
            continue
        try:
            rows.append(json.loads(l))
        except json.JSONDecodeError:
            bad += 1          # two writers appended at once (interleaved line); the run is lost
    if bad:
        print(f"WARNING: {bad} unparsable result lines skipped")
    df = pd.DataFrame(rows)
    df["params_s"] = df.params.apply(lambda p: json.dumps(p, sort_keys=True))
    df = df.drop_duplicates(["build_fn", "symbol", "tf", "params_s"], keep="last")
    return df


def md_table(df):
    cols = ["build_fn", "symbol", "tf", "params_s", "best_risk", "avg_month", "net", "max_dd",
            "worst_day", "trades", "green_months", "win_rate"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df[cols].iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                v = f"{v:.3g}" if c in ("best_risk", "green_months", "win_rate") else f"{v:,.0f}"
            vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    df = load()
    ok = df[df.best_risk.notna() & (df.avg_month > 0)].sort_values("avg_month", ascending=False)
    la = [json.loads(l) for l in (HERE / "lookahead.jsonl").read_text().splitlines()] if (HERE / "lookahead.jsonl").exists() else []
    print(f"scored runs: {len(df)}; candidates (best_risk and avg_month>0): {len(ok)}; "
          f"lookahead checks: {len(la)} ({sum(not x['ok'] for x in la)} failures)")
    print("\nby builder (count / candidates / best avg_month):")
    g = df.groupby("build_fn").agg(n=("name", "size"), cands=("avg_month", lambda s: int(((s > 0) & df.loc[s.index, "best_risk"].notna()).sum())), best=("avg_month", "max"))
    print(g.sort_values("best", ascending=False).to_string())
    print("\nby symbol:")
    g2 = df.groupby("symbol").agg(n=("name", "size"), cands=("avg_month", lambda s: int(((s > 0) & df.loc[s.index, "best_risk"].notna()).sum())), best=("avg_month", "max"))
    print(g2.sort_values("best", ascending=False).to_string())
    print("\nTOP", int(sys.argv[1]) if len(sys.argv) > 1 else 40)
    print(md_table(ok.head(int(sys.argv[1]) if len(sys.argv) > 1 else 40)))
    (HERE / "results_table.md").write_text("## All scored runs (sorted by avg_month)\n\n" +
                                           md_table(df.sort_values("avg_month", ascending=False)))

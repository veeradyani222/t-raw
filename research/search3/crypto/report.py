"""Render the scored-run table + ranking for NOTES.md from results.jsonl.
usage: python -m research.search3.crypto.report > research/search3/crypto/runs_table.md"""
import json
from pathlib import Path

import pandas as pd
exec(open(__import__("pathlib").Path(__file__).with_name("_md.py")).read())

HERE = Path(__file__).resolve().parent


def load():
    rows = [json.loads(l) for l in open(HERE / "results.jsonl")]
    df = pd.DataFrame(rows)
    # keep the last scoring of each (name, symbol, tf); drop errored rows that were re-run
    ok = df[df.get("error").isna()] if "error" in df else df
    ok = ok.drop_duplicates(["name", "symbol", "tf"], keep="last")
    err = df[df.get("error").notna()] if "error" in df else df.iloc[0:0]
    err = err[~err.set_index(["name", "symbol", "tf"]).index.isin(ok.set_index(["name", "symbol", "tf"]).index)]
    return ok, err


def main():
    ok, err = load()
    ok["fam"] = ok.name.str.split("_").str[0]
    q = ok[ok.best_risk.notna() & (ok.avg_month > 0)].sort_values("avg_month", ascending=False)
    print(f"scored runs: {len(ok)} (distinct name/symbol/tf), still-errored: {len(err)}, "
          f"qualifying (best_risk set and avg_month>0): {len(q)}\n")
    print("## Top 40 by avg_month\n")
    cols = ["name", "symbol", "tf", "fn", "best_risk", "avg_month", "net", "max_dd", "worst_day", "trades", "win", "green", "months"]
    print(q[cols].head(40).to_markdown(index=False))
    print("\n## Best run per idea family\n")
    best = q.sort_values("avg_month", ascending=False).groupby("fam").head(1)
    print(best[cols].to_markdown(index=False))
    print("\n## Every scored run\n")
    allc = ["batch", "name", "symbol", "tf", "fn", "params", "best_risk", "avg_month", "net", "max_dd", "worst_day", "trades", "win", "green"]
    o = ok.sort_values(["fam", "name", "symbol", "tf"])
    o = o.assign(params=o.params.apply(json.dumps))
    print(o[allc].to_markdown(index=False))
    if len(err):
        print("\n## Still-errored configs\n")
        print(err[["name", "symbol", "tf", "error"]].to_markdown(index=False))


if __name__ == "__main__":
    main()

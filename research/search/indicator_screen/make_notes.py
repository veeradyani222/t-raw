"""Regenerate NOTES.md from the result CSVs + the narrative below."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def md(df, floatfmt=1):
    df = df.copy()
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                ff = 2 if "risk" in c else floatfmt
                cells.append("" if pd.isna(v) else f"{v:.{ff}f}")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def screen_tables():
    a = pd.read_csv(HERE / "screen_results.csv")
    b = pd.read_csv(HERE / "screen_results_d1.csv")
    v = pd.read_csv(HERE / "stage3_vote.csv")
    d = pd.concat([a, b, v], ignore_index=True)
    d = d[d.trades.notna()].copy()
    d["both_halves"] = (d.h1_avgmo > 0) & (d.h2_avgmo > 0)
    d["T"] = d.trend.map({True: "T", False: "", "True": "T", "False": ""})
    d["risk%"] = d.best_risk_est * 100
    agg = (d[d.symbol != "USTEC"].groupby(["tf", "rule", "T"])
           .agg(symbols=("net1", "size"), share_net_pos=("net1", lambda x: (x > 0).mean()),
                share_both_halves=("both_halves", "mean"), median_pf=("pf", "median"),
                sum_net_at_1pct=("net1", "sum")).reset_index()
           .sort_values(["tf", "share_both_halves"], ascending=[True, False]))
    cols = ["symbol", "tf", "rule", "T", "trades", "pf", "net1", "dd1", "wd1", "risk%",
            "avg_month_est", "h1_avgmo", "h2_avgmo"]
    ranked = d.sort_values("avg_month_est", ascending=False)[cols]
    ranked.columns = ["sym", "tf", "rule", "T", "trades", "PF", "net@1%", "maxDD@1%", "worstDay@1%",
                      "est_best_risk%", "est_avg_mo", "2015-19 $/mo@1%", "2020-23 $/mo@1%"]
    return d, agg, ranked


def verify_table():
    v = pd.read_csv(HERE / "verify_results.csv")
    v["risk%"] = v.best_risk * 100
    v = v[["name", "symbol", "tf", "risk%", "avg_month", "net", "green", "max_dd", "worst_day",
           "trades", "A_avgmo", "B_avgmo"]]
    v.columns = ["name", "sym", "tf", "best_risk%", "avg_month", "net", "green", "max_dd",
                 "worst_day", "trades", "2015-19 $/mo", "2020-23 $/mo"]
    return v


NARRATIVE = open(HERE / "notes_narrative.txt", encoding="utf-8").read() if (HERE / "notes_narrative.txt").exists() else ""

if __name__ == "__main__":
    d, agg, ranked = screen_tables()
    v = verify_table()
    parts = [NARRATIVE,
             f"## Table A - every H.score run ({len(v)} runs, real judge, in-sample 2015-2023)\n\n"
             "Halves are scored at the full-period best_risk (or 0.25% if none safe).\n\n" + md(v),
             "## Table B - rule-level summary of the fast screen (USTEC excluded: data starts 2022-07)\n\n"
             "share_both_halves is the key luck check: a zero-edge rule lands positive in both halves "
             "about 25% of the time by chance.\n\n" + md(agg, 2),
             f"## Table C - FULL ranked fast screen ({len(ranked)} runs, 1% risk sim, best risk "
             "estimated by linear scaling; ranked by est_avg_mo)\n\n" + md(ranked)]
    (HERE / "NOTES.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print("NOTES.md written", len(ranked), len(v))

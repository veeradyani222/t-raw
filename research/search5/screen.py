"""Round-5 step 1+2: screen every known strategy on long history.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.screen

Reads the full-history 1% cache (core5.build_cache) and writes
    out/strategy_stats.csv    one row per strategy: dev steadiness, $/month in every period
    out/screen.md             the tables for the report (plain language)

"dev" = 2015-01-01..2023-10-20 (what a pick may look at). "y1" = first unseen year,
"last2" = Oct 2024..Oct 2026 (the round-3 SEARCH window -> fit period for pool strategies),
"sepoct" = Sep+Oct 2026. All numbers at 1% of $10K per trade; halve for the $5K account.
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool

STEADY_MIN_YEARS = 5
STEADY_MIN_FRAC = 0.8


def main():
    pool = build_pool()
    C, W, trades = K.load_full(pool)
    rows = [K.strat_stats(x, C[x["i"]], W[x["i"]], trades[x["i"]]) for x in pool if trades[x["i"]] is not None]
    df = pd.DataFrame(rows)
    df["years_dev"] = df["years_dev"].fillna(0).astype(int)
    df["steady"] = (df.years_dev >= STEADY_MIN_YEARS) & (df.steady_dev >= STEADY_MIN_FRAC) & (df.dev_pm > 0)
    df["runs_live"] = [x["runs_live"] for x in pool if trades[x["i"]] is not None]
    df.to_csv(os.path.join(K.OUT, "strategy_stats.csv"), index=False)
    json.dump({r["i"]: r for r in rows}, open(os.path.join(K.OUT, "strategy_stats.json"), "w"), indent=1, default=str)

    def fmt(v, nd=0):
        return "-" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.{nd}f}"

    def table(d, title, cols=None):
        cols = cols or ["name", "symbol", "tf", "mixes", "first_trade", "years_dev", "pos_years_dev", "dev_pm", "y1_pm", "last2_pm", "sepoct_pm", "unseen3_worst_day", "unseen3_trades"]
        hdr = {"name": "strategy", "symbol": "market", "tf": "tf", "mixes": "in mixes", "first_trade": "data from", "years_dev": "dev years",
               "pos_years_dev": "green years", "dev_pm": "dev $/mo", "y1_pm": "unseen yr $/mo", "last2_pm": "last 2y $/mo (fit)", "sepoct_pm": "Sep+Oct $/mo",
               "unseen3_worst_day": "worst day 3y", "unseen3_trades": "trades 3y", "live_risk": "live risk"}
        lines = [f"### {title}", "", "| " + " | ".join(hdr.get(c, c) for c in cols) + " |", "|" + "---|" * len(cols)]
        for _, r in d.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if c == "live_risk":
                    cells.append("-" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2%}")
                else:
                    cells.append(fmt(v) if isinstance(v, (float, np.floating)) else ("-" if v is None or v == "" else str(v)))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines) + "\n"

    md = ["# Round-5 strategy screen (1% of $10K per trade; halve for $5K)\n",
          "dev = 2015..2023-10-20 (pick period). unseen yr = Oct 2023..Oct 2024. last 2y = Oct 2024..Oct 2026 = the window the "
          "round-3 pool and the 66 were SEARCHED on, so it is a fit period for every strategy here. Sep+Oct = 2026-09-01..10-31.\n"]
    live = df[df.in24].sort_values("y1_pm", ascending=False)
    md.append(table(live, f"The live 24 on long history ({len(live)} rows)", cols=["name", "symbol", "tf", "live_risk", "first_trade", "years_dev", "pos_years_dev", "dev_pm", "y1_pm", "last2_pm", "sepoct_pm", "unseen3_worst_day"]))
    tot = {k: live[k].sum() for k in ("dev_pm", "y1_pm", "last2_pm", "sepoct_pm")}
    md.append(f"Sum of the 24 at 1% each (no account stop): dev ${tot['dev_pm']:,.0f}/mo, unseen yr ${tot['y1_pm']:,.0f}/mo, last 2y ${tot['last2_pm']:,.0f}/mo, Sep+Oct ${tot['sepoct_pm']:,.0f}/mo\n")
    cand = df[(~df.in24) & df.offered & (df.years_dev >= 3)].copy()
    md.append(table(cand.sort_values("dev_pm", ascending=False), f"Not in the 24, judged on dev data, ranked by dev $/month ({len(cand)} rows with >= 3 dev years)"))
    st = df[df.steady & df.offered].sort_values("dev_pm", ascending=False)
    md.append(table(st, f"Steady screen: >= {STEADY_MIN_YEARS} dev years, >= {STEADY_MIN_FRAC:.0%} green, dev $/month > 0 ({len(st)} rows)"))
    for lab, d in (("steady & not in 24", st[~st.in24]), ("steady & in 24", st[st.in24])):
        if len(d):
            md.append(f"{lab}: {len(d)} strategies; sum $/mo at 1% each: dev ${d.dev_pm.sum():,.0f}, unseen yr ${d.y1_pm.sum():,.0f}, "
                      f"last 2y ${d.last2_pm.sum():,.0f}, Sep+Oct ${d.sepoct_pm.sum():,.0f}; green in unseen yr {int((d.y1_pm > 0).sum())}/{len(d)}\n")
    short = df[(df.years_dev < 3) & df.offered]
    md.append(f"\n{len(short)} strategies cannot be judged on long history (data starts after 2020): " +
              ", ".join(sorted({f'{r.symbol}' for r in short.itertuples()})) + "\n")
    open(os.path.join(K.OUT, "screen.md"), "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()

"""Round-4 selection. Step 1 uses ONLY trades closed before DEV_END; step 2 adds
"still works": positive in the first unseen year AND in the last two years.

    .venv/Scripts/python.exe -m research.search4.price_action.select GRID_DIR

Writes GRID_DIR/survivors.json (step 1, with unseen-period results attached) and prints
the honest unseen numbers of the step-1 picks.
"""
import glob, json, os, sys
import numpy as np
import pandas as pd

DEV_END = pd.Timestamp("2023-10-20")
Y1_END = pd.Timestamp("2024-10-20")          # first unseen year
END = pd.Timestamp("2026-10-31")
MIN_TRADES = {"M30": 60, "H1": 50, "H4": 30, "D1": 20}
MIN_YEARS = 3.0
MIN_PF = 1.2
MIN_POS_YEARS = 0.6
MIN_RET_DD = 0.5                             # yearly dev profit / max closed-trade drawdown


def dev_stats(t):
    d = t[pd.to_datetime(t.exit_time) < DEV_END]
    if len(d) == 0:
        return None
    et = pd.to_datetime(d.exit_time)
    years = (DEV_END - pd.to_datetime(d.entry_time).min()).days / 365.25
    win, loss = d.profit[d.profit > 0].sum(), -d.profit[d.profit < 0].sum()
    eq = d.profit.cumsum().to_numpy()
    dd = float((eq - np.maximum.accumulate(np.r_[0.0, eq])[1:]).min())
    by_year = d.groupby(et.dt.year).profit.agg(["sum", "count"])
    by_year = by_year[by_year["count"] >= 5]
    net = float(d.profit.sum())
    return dict(n=len(d), years=years, net=net, pf=(win / loss if loss > 0 else np.inf),
                pos_years=(float((by_year["sum"] > 0).mean()) if len(by_year) else 0.0), n_years=len(by_year),
                ret_dd=(net / max(years, 1e-9)) / max(-dd, 1.0), dd=dd)


def unseen(t):
    x = t.assign(xt=pd.to_datetime(t.exit_time))
    y1 = x[(x.xt >= DEV_END) & (x.xt < Y1_END)].profit.sum()
    l2 = x[(x.xt >= Y1_END) & (x.xt < END)].profit.sum()
    so = x[(x.xt >= pd.Timestamp("2026-09-01")) & (x.xt < END)].profit.sum()
    return dict(y1=float(y1), last2=float(l2), sepoct=float(so), n_unseen=int((x.xt >= DEV_END).sum()))


def main(grid_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(grid_dir, "grid_*.pkl"))):
        for r in pd.read_pickle(p):
            s = dev_stats(r["trades"]) if len(r["trades"]) else None
            if s is None:
                continue
            rows.append(dict(symbol=r["symbol"], tf=r["tf"], fam=r["fam"], params=r["params"],
                             pkey=json.dumps(r["params"], sort_keys=True), **s, **unseen(r["trades"])))
    df = pd.DataFrame(rows)
    print(f"configs with dev trades: {len(df)}")
    # plateau: share of the family's grid on this market/timeframe that made money in dev
    df["plateau"] = df.groupby(["symbol", "tf", "fam"]).net.transform(lambda s: float((s > 0).mean()))
    ok = (df.n >= df.tf.map(MIN_TRADES)) & (df.years >= MIN_YEARS) & (df.net > 0) & (df.pf >= MIN_PF) \
         & (df.pos_years >= MIN_POS_YEARS) & (df.n_years >= 3) & (df.ret_dd >= MIN_RET_DD) & (df.plateau >= 0.5)
    step1 = df[ok].sort_values("ret_dd", ascending=False).groupby(["symbol", "fam"], as_index=False).head(1)
    print(f"step 1 (old data only): {len(step1)} survivors from {len(df)} configs")
    for lab, col in (("first unseen year (Oct 23-Oct 24)", "y1"), ("last 2 years (Oct 24-Oct 26)", "last2"), ("Sep+Oct 2026", "sepoct")):
        v = step1[col]
        print(f"  {lab:<36} total ${v.sum():>9,.0f} at 1% each | profitable {int((v > 0).sum())}/{len(v)}")
    step2 = step1[(step1.y1 > 0) & (step1.last2 > 0)]
    print(f"step 2 (also profitable in the first unseen year AND the last 2 years): {len(step2)}")
    print("\nfamily mix of step 1:", step1.fam.value_counts().to_dict())
    print("market mix of step 1:", step1.symbol.value_counts().head(25).to_dict())
    step1.drop(columns=["pkey"]).to_json(os.path.join(grid_dir, "survivors.json"), orient="records", indent=1)
    pd.set_option("display.width", 220)
    cols = ["symbol", "tf", "fam", "params", "n", "net", "pf", "pos_years", "ret_dd", "y1", "last2", "sepoct"]
    print(step1[cols].round(2).head(60).to_string(index=False))
    return step1, step2


if __name__ == "__main__":
    main(sys.argv[1])

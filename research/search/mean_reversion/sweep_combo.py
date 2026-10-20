"""Screen build_dip_combo on index pairs. Writes combo_idx.csv."""
import itertools, json, sys
from pathlib import Path
import pandas as pd
from research.prop import harness as H
from research.search.mean_reversion import strategies as S, screen as SC

HERE = Path(__file__).resolve().parent
HOLD = {"H1": (24, 48), "H4": (6, 12, 24), "D1": (4, 8, 16)}
rows = []
for pt in sys.argv[1:]:
    sym, tf = pt.split(":")
    df = H.load(sym, tf, split="is")
    for wn, wl, nn, il, need, ex, tr, st, mh in itertools.product(
            (7, 10, 14), (-90, -80), (5, 10), (0.1, 0.2), (1, 2, 3), ("prev_high", "wpr"),
            (0, 200), (3.0, 6.0), HOLD[tf]):
        p = dict(wpr_n=wn, wpr_lo=wl, nlow_n=nn, ibs_lo=il, need=need, exit_mode=ex,
                 trend=tr, stop_atr=st, max_hold=mh)
        r = SC.screen(df, S.build_dip_combo(df, _raw=True, **p))
        rows.append(dict(name="dip_combo", symbol=sym, tf=tf, params=json.dumps(p), **r))
    print("done", pt, flush=True)
out = HERE / "combo_idx.csv"
pd.DataFrame(rows).to_csv(out, mode="a", header=not out.exists(), index=False)

"""Print the strongest hour pairs from the session scan whatever the gates (diagnostic)."""
import sys, os
sys.path.insert(0, os.getcwd())
import pandas as pd
from research.search5 import session_scan as S
from research.search5 import core5 as K

if __name__ == "__main__":
    rows = []
    for sym in S.MARKETS:
        _, r = S.scan_market(sym)
        if r:
            rows += S.plateau(r)
    df = pd.DataFrame(rows)
    df.to_pickle(os.path.join(K.OUT, "session_all.pkl"))
    print("tested", len(df), "max t", round(df.t.max(), 2), "t>=3:", int((df.t >= 3).sum()),
          " t>=3 & green>=.7:", int(((df.t >= 3) & (df.green >= .7)).sum()),
          " + plateau>=1.5:", int(((df.t >= 3) & (df.green >= .7) & (df.plateau_t >= 1.5)).sum()))
    pd.set_option("display.width", 200)
    print(df.sort_values("t", ascending=False).head(25)[["symbol", "side", "h_in", "h_out", "n", "mean", "t", "years", "green", "plateau_t"]].round(2).to_string(index=False))

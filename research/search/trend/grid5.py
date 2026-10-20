"""Grid 5: Bollinger-breakout neighbourhood (best gold-H4 entry in grid 4,
and the AUDJPY-H4 hit in grid 1) across the H4 trend symbols."""
from research.search.trend.run import run


def configs():
    g = []
    for sym in ("XAUUSD", "AUDJPY", "GBPJPY", "USDJPY", "US30"):
        for n in (20, 50, 80):
            for k in (1.5, 2.0, 2.5):
                for slm in (2.0, 3.0):
                    g.append((f"boll{n}_{k}_sl{slm}", "build_bollinger_bo", sym, "H4",
                              dict(n=n, k=k, sl_mult=slm)))
    return g


if __name__ == "__main__":
    cf = configs()
    print(len(cf), "configs")
    run(cf)

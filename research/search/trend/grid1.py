"""Grid 1: broad screen, default params, every strategy x symbol x tf."""
from pathlib import Path

from research.search.trend.run import run

SYMS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD",
        "USDCAD", "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY",
        "CADJPY", "EURGBP", "EURCHF", "GBPCHF", "AUDCAD", "US30", "US500", "USTEC", "DE40"]
DATA = Path(__file__).resolve().parents[3] / "data" / "search"

STRATS = [
    ("ema20_100", "build_ma_cross", dict(fast=20, slow=100)),
    ("donch55_20", "build_donchian", dict(n_entry=55, n_exit=20)),
    ("supertrend10_3", "build_supertrend", dict()),
    ("keltner20_2", "build_keltner_bo", dict()),
    ("boll20_2", "build_bollinger_bo", dict()),
    ("macd_zero", "build_macd", dict()),
    ("ichimoku", "build_ichimoku", dict()),
    ("psar", "build_psar", dict()),
    ("tsmom50", "build_tsmom", dict(lookback=50)),
    ("adx_di25", "build_adx_di", dict()),
]

if __name__ == "__main__":
    import sys
    syms = sys.argv[1].split(",") if len(sys.argv) > 1 else SYMS
    tfs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["H1", "H4", "D1"]
    cfgs = []
    for tf in tfs:
        for sym in syms:
            if not (DATA / f"{sym.lower()}-{tf.lower()}.csv").exists():
                print("skip missing", sym, tf)
                continue
            for name, fn, p in STRATS:
                cfgs.append((name, fn, sym, tf, p))
    print(len(cfgs), "runs")
    run(cfgs)

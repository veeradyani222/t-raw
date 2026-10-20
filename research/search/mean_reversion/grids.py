"""Parameter grids for run.py. Each returns a list of (builder, symbol, tf, params)."""
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "search"
ALL = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
       "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY", "CADJPY", "EURGBP",
       "EURCHF", "GBPCHF", "AUDCAD", "US30", "US500", "USTEC", "DE40"]


def have(sym, tf):
    return (DATA / f"{sym.lower()}-{tf.lower()}.csv").exists()


TF_DEF = {"H1": dict(max_hold=24, stop_atr=2.5), "H4": dict(max_hold=12, stop_atr=2.5),
          "D1": dict(max_hold=8, stop_atr=3.0)}
BASE = {"rsi2": {}, "crsi": {}, "bb_fade": {}, "zscore": {}, "ibs": {}, "nlow": {},
        "wpr": {}, "stoch": {}}


def g1():
    jobs = []
    for sym in ALL:
        for tf in ("H1", "H4", "D1"):
            if not have(sym, tf):
                continue
            for b, p in BASE.items():
                for sides in ("long", "both"):
                    jobs.append((b, sym, tf, dict(p, sides=sides, **TF_DEF[tf])))
            if tf == "H1":
                for sides in ("long", "both"):
                    jobs.append(("vwap", sym, tf, dict(sides=sides, max_hold=12, stop_atr=2.5)))
    return jobs

"""Fetch BTCUSDT / ETHUSDT hourly klines from Binance's public API into data/search as
btcusd-h1.csv / ethusd-h1.csv (+ H4, D1 built from H1). Times are UTC, shifted to the
broker's EET (+3h, matching the other files roughly; crypto trades 24/7 so the day
boundary is what matters for the daily-loss rule).

    python -m research.crypto_fetch
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path("data/search")
URL = "https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&startTime={a}&limit=1000"
PAIRS = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT"}


def klines(sym):
    rows, a = [], int(pd.Timestamp("2017-08-17").timestamp() * 1000)
    end = int(pd.Timestamp("2026-10-30").timestamp() * 1000)
    while a < end:
        req = urllib.request.Request(URL.format(s=sym, a=a), headers={"User-Agent": "Mozilla/5.0"})
        for _ in range(5):
            try:
                data = json.loads(urllib.request.urlopen(req, timeout=30).read()); break
            except Exception:
                time.sleep(3)
        else:
            raise SystemExit("binance unreachable")
        if not data:
            break
        rows += data
        a = data[-1][0] + 3600_000
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tb", "tq", "x"])
    df = df[["t", "open", "high", "low", "close", "vol"]].astype(float)
    df["time"] = pd.to_datetime(df.t, unit="ms") + pd.Timedelta(hours=3)
    df = df.drop(columns="t").rename(columns={"vol": "tick_volume"})
    df["spread"] = 0
    return df[["time", "open", "high", "low", "close", "tick_volume", "spread"]].drop_duplicates("time").sort_values("time")


def resample(df, rule):
    g = df.set_index("time").resample(rule, label="left", closed="left")
    out = g.agg(dict(open="first", high="max", low="min", close="last", tick_volume="sum", spread="max")).dropna().reset_index()
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    specs_path = OUT / "symbol_specs.json"
    specs = json.loads(specs_path.read_text()) if specs_path.exists() else {}
    for name, bsym in PAIRS.items():
        h1 = klines(bsym)
        h1.to_csv(OUT / f"{name.lower()}-h1.csv", index=False)
        resample(h1, "4h").to_csv(OUT / f"{name.lower()}-h4.csv", index=False)
        resample(h1, "1D").to_csv(OUT / f"{name.lower()}-d1.csv", index=False)
        # FundedNext-style CFD specs: 1 lot = 1 coin, USD quoted, 0.01 lot steps
        specs[name] = dict(digits=2, point=0.01, contract=1.0, profit_ccy="USD", vol_min=0.01, vol_step=0.01, vol_max=100.0)
        print(name, len(h1), h1.time.min(), "->", h1.time.max(), flush=True)
    specs_path.write_text(json.dumps(specs, indent=1))

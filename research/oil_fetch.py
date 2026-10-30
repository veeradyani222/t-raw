"""Fetch Brent and WTI hourly history from Dukascopy's free feed into data/search as
ukousd-h1.csv / usousd-h1.csv (+ H4/D1), FundedNext's symbol names. Dukascopy serves one
.bi5 file per day of 1-minute BID candles; we aggregate to H1 and shift UTC -> EET (+3h).
Slow (thousands of small files); run in the background. Resumable via the raw cache.

    python -m research.oil_fetch [start_year]
"""
import datetime as dt
import json
import lzma
import struct
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

OUT = Path("data/search")
RAW = Path("data/dukascopy_raw")
SYMS = {"UKOUSD": ("BRENT.CMDUSD", 1e3), "USOUSD": ("LIGHT.CMDUSD", 1e3)}
START = dt.date(int(sys.argv[1]) if len(sys.argv) > 1 else 2017, 1, 1)
END = dt.date(2026, 10, 29)


def fetch_day(dsym, d):
    cache = RAW / f"{dsym}-{d}.bi5"
    if cache.exists():
        return cache.read_bytes()
    url = f"https://datafeed.dukascopy.com/datafeed/{dsym}/{d.year}/{d.month-1:02d}/{d.day:02d}/BID_candles_min_1.bi5"
    for k in range(5):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
            cache.write_bytes(raw)
            return raw
        except Exception:
            time.sleep(2 + 3 * k)
    return None


def parse(raw, d, div):
    if not raw:
        return []
    base = dt.datetime(d.year, d.month, d.day)
    return [(base + dt.timedelta(seconds=t), o / div, h / div, l / div, c / div, v)
            for t, o, c, l, h, v in struct.iter_unpack(">5if", lzma.decompress(raw))]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    days = [START + dt.timedelta(n) for n in range((END - START).days + 1) if (START + dt.timedelta(n)).weekday() != 5]
    specs_path = OUT / "symbol_specs.json"
    specs = json.loads(specs_path.read_text()) if specs_path.exists() else {}
    for name, (dsym, div) in SYMS.items():
        t0 = time.time()
        with ThreadPoolExecutor(8) as ex:
            raws = list(ex.map(lambda d: (d, fetch_day(dsym, d)), days))
        missing = sum(1 for _, r in raws if r is None)
        rows = [x for d, r in raws for x in parse(r, d, div)]
        m1 = pd.DataFrame(rows, columns=["utc", "open", "high", "low", "close", "tick_volume"])
        m1 = m1[m1.tick_volume > 0].sort_values("utc")
        m1["time"] = m1.utc + pd.Timedelta(hours=3)
        g = m1.set_index("time")
        for tf, rule in (("h1", "1h"), ("h4", "4h"), ("d1", "1D")):
            bars = g.resample(rule, label="left", closed="left").agg(
                dict(open="first", high="max", low="min", close="last", tick_volume="sum")).dropna().reset_index()
            bars["spread"] = 0
            bars.to_csv(OUT / f"{name.lower()}-{tf}.csv", index=False)
        specs[name] = dict(digits=2, point=0.01, contract=100.0, profit_ccy="USD", vol_min=0.01, vol_step=0.01, vol_max=100.0)
        print(f"{name}: {len(m1)} M1 bars, {m1.time.min()} -> {m1.time.max()}, missing days {missing}, {time.time()-t0:.0f}s", flush=True)
    specs_path.write_text(json.dumps(specs, indent=1))

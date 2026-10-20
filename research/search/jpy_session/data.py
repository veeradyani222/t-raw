"""Loader for the jpy_session family.

Uses research.prop.harness.load() when data/search/<sym>-<tf>.csv exists.
Several JPY crosses were not (yet) in data/search when this family ran, so
for H1 we fall back to the older broker-feed exports already in data/
(same MT5 feed / same broker timestamps: verified identical USDJPY closes on
every overlapping bar). The fallback applies the SAME in-sample cut
(< 2024-01-01) and the same USD conversion as the harness. Read-only.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from research.prop import harness as H

ROOT = H.ROOT / "data"
FALLBACK = {
    "CHFJPY": ["session-chfjpy-h1-screen-20260913.csv"],
    "NZDJPY": ["session-nzdjpy-h1-screen-20260913.csv"],
    "EURJPY": ["session-eurjpy-h1-screen-20260913.csv"],
    "GBPJPY": ["session-gbpjpy-h1-screen-20260913.csv"],
    "AUDJPY": ["session-audjpy-h1-older-20260913.csv", "audjpy-h1.csv"],
}


CACHE = Path(__file__).with_name("_cache")


def load(symbol: str, tf: str = "H1") -> pd.DataFrame:
    """In-sample bars only (2015..2023), pickled locally (the machine is
    memory-starved; CSV parsing kept failing)."""
    symbol = symbol.upper()
    CACHE.mkdir(exist_ok=True)
    pk = CACHE / f"{symbol}-{tf.upper()}-is.pkl"
    if pk.exists():
        df = pd.read_pickle(pk)
        return df
    df = _load(symbol, tf)
    df.to_pickle(pk)
    return df


def _load(symbol: str, tf: str = "H1") -> pd.DataFrame:
    if (H.DATA / f"{symbol.lower()}-{tf.lower()}.csv").exists():
        df = H.load(symbol, tf, split="is")
        df.attrs["source"] = "data/search"
        return df
    if tf.upper() != "H1" or symbol not in FALLBACK:
        raise FileNotFoundError(f"{symbol} {tf} not available")
    parts = []
    for f in FALLBACK[symbol]:
        p = pd.read_csv(ROOT / f, parse_dates=["time"])
        parts.append(p[p.time < H.OOS_START])
    df = pd.concat(parts, ignore_index=True)
    if "spread" not in df:
        df["spread"] = 0
    df["spread"] = df["spread"].fillna(0)
    df = df[["time", "open", "high", "low", "close", "tick_volume", "spread"]]
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df = H._attach_conv(df, symbol, tf)
    df = df.reset_index(drop=True)
    df.attrs.update(symbol=symbol, tf=tf, split="is", score_from=None,
                    source="data/ fallback")
    return df

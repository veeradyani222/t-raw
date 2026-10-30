"""Shared setup for the europe_indices search: cost model for symbols the
harness does not know, data-quality filter, loader."""
from __future__ import annotations
import os
os.environ["PROP_OOS"] = "1"
import numpy as np
import pandas as pd
from research.prop import harness as H

# Realistic IC Markets / FundedNext style spreads in PRICE units (task brief).
EXTRA_SPREAD = {"UK100": 2.0, "FRA40": 1.5, "F40": 1.5, "STOXX50": 1.5,
                "SWI20": 3.0, "IT40": 10.0, "ESP35": 5.0, "DE40": 1.5}
SYMBOLS = ["UK100", "FRA40", "IT40", "DE40"]   # STOXX50 / SWI20: no data file (see NOTES)
FILE_ALIAS = {"F40": "FRA40"}


def patch():
    H.SPREAD_FLOOR.update(EXTRA_SPREAD)
    H.INDICES.update(EXTRA_SPREAD.keys())   # indices: no commission, pip = 1.0


patch()


def quality_mask(df: pd.DataFrame, flat_frac: float = 0.25, stale_frac: float = 0.30) -> tuple[np.ndarray, dict]:
    """True where the bar is usable. Drops zero-volume bars, bars with a zero
    range, and whole days that look like a stale feed: day range < flat_frac
    (25%) of the median daily range, OR more than stale_frac (30%) of the day's
    bars have zero range (price stuck, ticks still arriving - seen on DE40
    2024-11-28..12-03). Returns the mask and counts."""
    t = pd.DatetimeIndex(df.time)
    day = t.normalize()
    g = df.groupby(day.values)
    rng = g.apply(lambda x: x.high.max() - x.low.min())
    med = rng.median()
    zr_bar = ((df.high - df.low) <= 0)
    zr_frac = zr_bar.groupby(day.values).mean()
    nbar = g.size()
    flat_days = set(rng[(rng < flat_frac * med) | ((zr_frac > stale_frac) & (nbar >= 4))].index)
    zero_vol = (df.tick_volume <= 0).to_numpy()
    zero_rng = zr_bar.to_numpy()
    flat = np.isin(day.values, list(flat_days)) if flat_days else np.zeros(len(df), bool)
    bad = zero_vol | zero_rng | flat
    gaps = t.to_series().diff().dt.total_seconds().div(3600)
    long_gaps = int((gaps > 72).sum())   # > a weekend
    return ~bad, dict(rows=len(df), zero_volume=int(zero_vol.sum()), zero_range=int(zero_rng.sum()),
                      flat_days=len(flat_days), flat_day_bars=int(flat.sum()), dropped=int(bad.sum()),
                      gaps_over_72h=long_gaps, median_day_range=round(float(med), 1))


def load(symbol: str, tf: str, clean: bool = True):
    symbol = FILE_ALIAS.get(symbol.upper(), symbol.upper())
    df = H.load(symbol, tf, split="oos")
    if clean:
        m, _ = quality_mask(df)
        attrs = dict(df.attrs)
        df = df[m].reset_index(drop=True)
        df.attrs.update(attrs)
    return df

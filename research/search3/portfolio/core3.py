"""Round-3 portfolio stage: shared pieces.

Reuses research.search2.portfolio.core (LP, exact greedy, close-all replay, report)
and adds (a) every round-3 group's cost patches so new symbols are costed exactly as
the groups scored them, (b) each group's data-quality cleaner, applied to the simulated
frame, and (c) a group-aware run() for the Pool(2) workers.
PROP_OOS=1 is allowed in this stage only.
"""
import os, json, importlib
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search2.portfolio import core as P

START = pd.Timestamp("2024-10-20")
END = pd.Timestamp("2026-10-31")          # "now": new markets end 2026-10-30, the original 23 on 2026-10-20
LAST12 = pd.Timestamp("2025-10-20")
LEVELS = P.LEVELS
WARM = P.WARM

CRYPTO = {"BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD", "ADAUSD", "BNBUSD", "DOTUSD"}
_patched = False


def patch_all():
    """Apply every group's harness patch once (idempotent). Order matters for the
    _attach_conv chain: commodity_fx first (it does not fall back), then the wrappers."""
    global _patched
    if _patched:
        return
    import research.search3.commodity_fx.run              # noqa: F401  patch() at import (AUD/NZD conv, cross floors)
    from research.search3.asia_indices import strategies as asia
    asia.patch_harness()                                  # JPN225/HK50/CHINA50/AUS200 spreads, HKD/AUD conv
    from research.search3.exotics import strategies as exo
    exo.patch_harness()                                   # exotic floors, quote conv, 5-digit specs
    import research.search3.europe_indices.common         # noqa: F401  UK100/FRA40/ESP35/... spreads, indices
    import research.search3.oil_gas.common                # noqa: F401  energies: spreads, no commission, pips
    import research.search3.us_indices.strategies         # noqa: F401  US2000
    from research.search3.crypto import costs
    costs.apply()                                         # crypto spreads/pips, no commission, max_lots lifted
    # crypto's patch lifts max_lots for every symbol; keep the harness default elsewhere
    _sim = H.simulate

    def simulate(df, signals, **kw):
        sym = df.attrs.get("symbol", "")
        kw.setdefault("max_lots", 1e9 if sym in CRYPTO else 50.0)
        return _sim(df, signals, **kw)
    H.simulate = simulate
    # metals: XPTUSD/XPDUSD floors, no commission, pip 0.1 and the bad-wick clamp (runner.py), these two only
    H.SPREAD_FLOOR.update({"XPTUSD": 2.0, "XPDUSD": 3.0})
    H.INDICES.update({"XPTUSD", "XPDUSD"})
    _pip = H._pip

    def pip(symbol):
        return 0.1 if symbol in ("XPTUSD", "XPDUSD") else _pip(symbol)
    H._pip = pip
    _patched = True


def clamp_wicks(df):
    body_hi = np.maximum(df["open"], df["close"]); body_lo = np.minimum(df["open"], df["close"])
    bad_lo = df["low"] < 0.9 * body_lo; bad_hi = df["high"] > 1.1 * body_hi
    if bad_lo.any() or bad_hi.any():
        df = df.copy()
        df.loc[bad_lo, "low"] = body_lo[bad_lo]; df.loc[bad_hi, "high"] = body_hi[bad_hi]
    return df


def flat_clean(df, zero_vol=True, frac=0.05):
    """Drop bars of flat/stale server days (day range < frac of the median day range)
    and, optionally, zero-volume bars. Same rule the crypto/oil/commodity_fx/exotics groups used."""
    attrs = dict(df.attrs)
    day = pd.DatetimeIndex(df.time).normalize()
    drng = df.groupby(day.values).high.max() - df.groupby(day.values).low.min()
    flat_days = set(drng[drng < frac * drng.median()].index)
    bad = np.isin(day.values, list(flat_days)) if flat_days else np.zeros(len(df), bool)
    if zero_vol and "tick_volume" in df:
        bad |= (df.tick_volume.to_numpy() <= 0)
    out = df[~bad].reset_index(drop=True)
    out.attrs.update(attrs)
    return out


# DE40 feed was stale 2024-11-28..2024-12-05 (near-zero ranges / volume, see europe_indices/common.py
# and us_indices EXCLUDE_DAYS). Those bars produced 10+ lot trades worth $3k-$11k in round 2 and in the
# live mix. Excluded for every DE40 strategy, live ones included.
BAD_DAYS = {"DE40": pd.to_datetime(["2024-11-28", "2024-11-29", "2024-12-02", "2024-12-03", "2024-12-04", "2024-12-05"])}


def drop_bad_days(df, symbol):
    if symbol not in BAD_DAYS:
        return df
    attrs = dict(df.attrs)
    day = pd.DatetimeIndex(df.time).normalize()
    out = df[~day.isin(BAD_DAYS[symbol])].reset_index(drop=True)
    out.attrs.update(attrs)
    return out


def group_clean(df, group, symbol):
    df = drop_bad_days(df, symbol)
    if group in ("crypto",):
        return flat_clean(df, zero_vol=False)
    if group in ("oil_gas", "commodity_fx", "exotics"):
        return flat_clean(df, zero_vol=True)
    if group == "europe_indices":
        from research.search3.europe_indices.common import quality_mask
        m, _ = quality_mask(df)
        attrs = dict(df.attrs); out = df[m].reset_index(drop=True); out.attrs.update(attrs)
        return out
    if group == "metals" and symbol in ("XPTUSD", "XPDUSD"):
        return clamp_wicks(df)
    return df   # asia / us / jpy / majors / live mix: cleaning (if any) lives inside the builders


def keyof(m):
    return P.keyof(m)


def run(args):
    """(strategy, risk, start, end) -> (key, curve(time, worst, close) from start, trades)."""
    patch_all()
    x, risk, start, end = args
    full = H.load(x["symbol"], x["tf"], split="all")
    full = full[full.time < end].reset_index(drop=True)
    i0 = int(np.searchsorted(full.time.values, start.to_datetime64()))
    df = full.iloc[max(0, i0 - WARM):].reset_index(drop=True)
    df.attrs.update(symbol=x["symbol"], tf=x["tf"], split="all", score_from=None)
    df = group_clean(df, x.get("group", "live"), x["symbol"])
    j0 = int(np.searchsorted(df.time.values, start.to_datetime64()))
    fn = getattr(importlib.import_module(x["module"]), x["fn"])
    sigs = list(P.call(fn, df, x["params"]))
    sigs[:j0] = [None] * j0
    res = H.simulate(df, sigs, risk=risk)
    cv = res["curve"]
    cv = cv[cv.time >= start].reset_index(drop=True)
    t = res["trades"]
    if len(t):
        t = t[t.entry_time >= start].reset_index(drop=True)
    return x["key"], cv, t

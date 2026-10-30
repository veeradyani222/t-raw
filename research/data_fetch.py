"""Fetch MT5 history for extra markets into data/search (yearly chunks; the terminal
caps a single request at 100k bars and returns 0 until a cold symbol has synced).

    python -m research.data_fetch SYM1 SYM2 ...        (cwd = repo root, MT5 logged in)
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import MetaTrader5 as m
import pandas as pd

OUT = Path("data/search")
TFS = {"H1": m.TIMEFRAME_H1, "H4": m.TIMEFRAME_H4, "D1": m.TIMEFRAME_D1, "M30": m.TIMEFRAME_M30}


def fetch(sym, tf, code, start=dt.datetime(2015, 1, 1), end=dt.datetime(2026, 10, 31)):
    parts = []
    a = start
    step = 12 if tf != "M30" else 6
    while a < end:
        b = min(dt.datetime(a.year + (a.month - 1 + step) // 12, (a.month - 1 + step) % 12 + 1, 1), end)
        r = None
        for _ in range(4):
            r = m.copy_rates_range(sym, code, a, b)
            if r is not None and len(r):
                break
            time.sleep(1.0)
        if r is not None and len(r):
            parts.append(pd.DataFrame(r))
        a = b
    if not parts:
        return None
    df = pd.concat(parts)
    df["time"] = pd.to_datetime(df.time, unit="s")
    return df.drop_duplicates("time").sort_values("time")


def env_creds():
    """MT5_LOGIN / MT5_PASSWORD / MT5_SERVER from .env, if present (never printed)."""
    p = Path(".env")
    if not p.exists():
        return {}
    kv = dict(l.strip().split("=", 1) for l in p.read_text().splitlines() if "=" in l and not l.startswith("#"))
    if kv.get("MT5_LOGIN") and kv.get("MT5_PASSWORD") and kv.get("MT5_SERVER"):
        return dict(login=int(kv["MT5_LOGIN"]), password=kv["MT5_PASSWORD"], server=kv["MT5_SERVER"])
    return {}


if __name__ == "__main__":
    creds = env_creds()
    assert m.initialize(timeout=120000, **creds), m.last_error()
    acct = m.account_info()
    print("connected:", acct.server if acct else m.last_error(), "| symbols:", m.symbols_total(), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    specs_path = OUT / "symbol_specs.json"
    specs = json.loads(specs_path.read_text()) if specs_path.exists() else {}
    for sym in sys.argv[1:]:
        i = m.symbol_info(sym)
        if i is None:
            print(sym, "not found"); continue
        m.symbol_select(sym, True)
        time.sleep(2)  # let the terminal start syncing
        specs[sym] = dict(digits=i.digits, point=i.point, contract=i.trade_contract_size, profit_ccy=i.currency_profit,
                          vol_min=i.volume_min, vol_step=i.volume_step, vol_max=i.volume_max)
        for tf, code in TFS.items():
            df = fetch(sym, tf, code)
            if df is None:
                print(sym, tf, "NO DATA"); continue
            df.to_csv(OUT / f"{sym.lower()}-{tf.lower()}.csv", index=False)
            print(sym, tf, len(df), df.time.min().date(), "->", df.time.max().date(), "median spread", int(df.spread.median()), flush=True)
        specs_path.write_text(json.dumps(specs, indent=1))

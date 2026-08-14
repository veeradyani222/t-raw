"""One-off: backtest XAUUSD 'yesterday' (2026-08-13, broker server time) on
every intraday timeframe, 1% risk, structure-TP setup (reward >= 1x risk).

Pulls fresh bars from the MT5 terminal by position (avoids UTC/server-time
range mismatches), feeds each timeframe enough prior history for the ORB box +
fractal-swing warmup, then keeps only the trades ENTERED on the target day.
Each trade is normalized to a flat $10k @ 1% risk via its R-multiple so the
day stands alone regardless of warmup-day P/L drift.
"""
import MetaTrader5 as mt5
import pandas as pd

from trader.config import Config
from trader.sim import run_backtest

DAY = pd.Timestamp("2026-08-13")
EQUITY = 10_000.0
RISK = 0.01
GOLD = dict(pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0)

# timeframe -> (mt5 const, bars to pull for ~10 trading days of warmup)
TFS = [
    ("M1", mt5.TIMEFRAME_M1, 20000),
    ("M5", mt5.TIMEFRAME_M5, 6000),
    ("M15", mt5.TIMEFRAME_M15, 2500),
    ("M30", mt5.TIMEFRAME_M30, 1400),
    ("H1", mt5.TIMEFRAME_H1, 800),
    ("H4", mt5.TIMEFRAME_H4, 300),
]

mt5.initialize()
print(f"=== XAUUSD | day={DAY:%Y-%m-%d} | risk={RISK:.0%} of ${EQUITY:,.0f} | "
      f"structure TP (reward >= 1x risk) ===\n")

grand = 0.0
for name, const, nbars in TFS:
    rates = mt5.copy_rates_from_pos("XAUUSD", const, 0, nbars)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    # feed ALL bars through the latest available (08-14 morning) so trades
    # entered on the target day resolve at their real SL/TP instead of being
    # force-closed at the day boundary. We still only REPORT trades entered on
    # the target day; later bars just let those trades play out live-style.
    df = df.reset_index(drop=True)
    df = df[["time", "open", "high", "low", "close", "tick_volume"]]

    cfg = Config(symbol="XAUUSD", timeframe=name, strategy="orb",
                 pip_size=GOLD["pip_size"], pip_value_per_lot=GOLD["pip_value_per_lot"],
                 spread_pips=GOLD["spread_pips"],
                 orb_tp_mode="structure", orb_structure_filter=True,
                 orb_vol_filter=False, risk_per_trade=RISK)
    res = run_backtest(df, cfg, starting_equity=EQUITY)

    tl = res["trade_log"]
    ev = res["events"]
    day_tr = tl[pd.to_datetime(tl["entry_time"]).dt.normalize() == DAY] if not tl.empty else tl
    day_ev = ev[pd.to_datetime(ev["time"]).dt.normalize() == DAY] if not ev.empty else ev

    print(f"----- {name} -----  (bars fed: {len(df)}, last: {df['time'].max()})")
    if day_tr.empty:
        reasons = ""
        if not day_ev.empty:
            reasons = " | signals-but-no-trade: " + ", ".join(
                f"{k} x{v}" for k, v in day_ev["reason"].str.split(":").str[0].value_counts().items())
        print(f"  no trades entered on {DAY:%Y-%m-%d}{reasons}\n")
        continue

    tf_pl = 0.0
    for _, t in day_tr.iterrows():
        risk_dist = abs(t["entry"] - t["sl"])
        rr = abs(t["tp"] - t["entry"]) / risk_dist if risk_dist else float("nan")
        r_mult = t["r_multiple"]
        pl_10k = r_mult * (RISK * EQUITY)  # normalize to flat $10k @1%
        tf_pl += pl_10k
        print(f"  {t['entry_time']:%H:%M} {t['side']:>5}  entry {t['entry']:.2f}  "
              f"SL {t['sl']:.2f}  TP {t['tp']:.2f}  setupRR 1:{rr:.2f}  "
              f"-> {t['reason']:>3} @ {t['exit']:.2f}  R={r_mult:+.2f}  "
              f"P/L ${pl_10k:+.2f}")
    grand += tf_pl
    print(f"  {name} day P/L (norm $10k @1%): ${tf_pl:+.2f}  "
          f"({len(day_tr)} trade{'s' if len(day_tr)!=1 else ''})\n")

print(f"=== combined across timeframes: ${grand:+.2f} on $10k @1% risk ===")
mt5.shutdown()

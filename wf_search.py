"""Walk-forward strategy search for EURUSD H1 — ISOLATED research harness.

Does NOT touch engine.py / sim.py / live. It reuses the real cost/risk model
(entry at close +- spread, SL/TP filled against later bars' high/low with SL
winning ties, sizing via trader.risk.position_size_lots at 1% risk) and adds a
time-based exit that the live engine lacks, for the session strategy.

Before its new-strategy numbers are trusted, `python wf_search.py validate`
reproduces a known ORB backtest number from trader.sim.run_backtest on the same
data — the same validation the scaleout/trailing scripts used.

    python wf_search.py validate            # prove the cost model matches the engine
    python wf_search.py session             # walk-forward the session strategy
    python wf_search.py meanrev             # walk-forward the mean-reversion strategy
    python wf_search.py orb                 # walk-forward ORB (the losing control)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from trader.config import Config
from trader.risk import position_size_lots
import backtest as bt

# Symbol via WF_SYM env var (default EURUSD): run any pair without code edits,
# e.g. `WF_SYM=GBPJPY python wf_search.py meanrev`.
SYM = os.environ.get("WF_SYM", "EURUSD").upper()
# Entry hour for the session commands (session_prop/dd/spread), broker server time.
HOUR = int(os.environ.get("WF_HOUR", "0"))
PRESET = bt.SYMBOLS[SYM]
PIP = PRESET["pip_size"]
PIP_VALUE = PRESET["pip_value_per_lot"]
SPREAD = PRESET["spread_pips"]
RISK = 0.01
START_EQUITY = 10_000.0
MIN_LOT, MAX_LOT = 0.01, 1.0


# --------------------------------------------------------------------------- #
# Data                                                                        #
# --------------------------------------------------------------------------- #
def load_h1(start="2017-01-01", end="2026-08-21") -> pd.DataFrame:
    return load_tf("H1", start, end)


def load_tf(tf, start="2017-01-01", end="2026-08-21") -> pd.DataFrame:
    cfg = Config(symbol=SYM, timeframe=tf, strategy="orb",
                 pip_size=PIP, pip_value_per_lot=PIP_VALUE, spread_pips=SPREAD)
    df = bt.load_history(cfg, pd.Timestamp(start), pd.Timestamp(end), None,
                         need_volume=False)
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Faithful fill/cost model                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class Entry:
    """What a strategy asks the harness to open on this bar."""
    side: str                     # "long" | "short"
    sl: float                     # stop PRICE (required — used for sizing)
    tp: float | None = None       # target PRICE, or None to exit only by time/stop
    max_hold: int | None = None   # close at entry_bar + max_hold (bars), or None
    exit_hour: int | None = None  # close at the first later bar whose hour == this
    meta: dict = field(default_factory=dict)


def simulate(df: pd.DataFrame, signal_fn, *, allow_flip=False,
             spread=SPREAD, pip=PIP, pip_value=PIP_VALUE, risk=RISK,
             start_equity=START_EQUITY, daily_halt=0.0, loss_baseline=0.0,
             total_halt=0.0, max_dd=0.0) -> dict:
    """Mirror of trader.sim: cursor advances bar by bar; stops on the new bar
    are filled BEFORE a fresh signal is computed at that bar's close.

    signal_fn(df, i) -> Entry | None, where i is the latest CLOSED bar. It sees
    df.iloc[:i+1] only (the harness passes the whole frame; strategies must not
    peek past i).

    Prop rails (all default 0 = off, preserving the validated behavior): when
    set, the SAME trader.risk.RiskGuard the live bot uses gates entries — daily
    loss halt, and permanent total-loss / max-drawdown halt.
    """
    from trader.risk import RiskGuard
    # RiskGuard treats daily_loss_halt=0.0 as a 0% threshold (halts immediately),
    # not "off" — so only engage the guard when a rail is actually set.
    rails_on = daily_halt > 0 or loss_baseline > 0 or total_halt > 0 or max_dd > 0
    guard = RiskGuard(1, daily_halt, max_dd, loss_baseline, total_halt)
    blown_at = None
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    openp = df["open"].values
    times = df["time"].values
    hours = pd.DatetimeIndex(df["time"]).hour.values
    n = len(df)

    equity = start_equity
    pos = None  # dict: side, entry, sl, tp, lots, risk_amt, entry_bar, exit_hour, max_hold, meta
    trades = []
    spread_p = spread * pip

    def settle(price, reason, exit_bar):
        nonlocal equity, pos
        pips = (price - pos["entry"]) / pip
        if pos["side"] == "short":
            pips = -pips
        profit = pips * pip_value * pos["lots"]
        equity += profit
        trades.append({
            "entry_time": times[pos["entry_bar"]], "exit_time": times[exit_bar],
            "side": pos["side"], "entry": pos["entry"], "exit": price,
            "sl": pos["sl"], "tp": pos["tp"], "lots": pos["lots"],
            "profit": profit, "reason": reason,
            "bars_held": exit_bar - pos["entry_bar"],
            "r_multiple": profit / pos["risk_amt"] if pos["risk_amt"] > 0 else np.nan,
            "equity_after": equity, **pos["meta"],
        })
        pos = None

    for i in range(n):
        # 1) fill stops/targets/time-exit against THIS bar (position opened <= i-1)
        if pos is not None:
            hit = False
            if pos["side"] == "long":
                if low[i] <= pos["sl"]:
                    settle(pos["sl"], "sl", i); hit = True
                elif pos["tp"] is not None and high[i] >= pos["tp"]:
                    settle(pos["tp"], "tp", i); hit = True
            else:
                if high[i] >= pos["sl"]:
                    settle(pos["sl"], "sl", i); hit = True
                elif pos["tp"] is not None and low[i] <= pos["tp"]:
                    settle(pos["tp"], "tp", i); hit = True
            if not hit and pos is not None:
                time_up = (pos["max_hold"] is not None
                           and i - pos["entry_bar"] >= pos["max_hold"])
                hour_up = (pos["exit_hour"] is not None and hours[i] == pos["exit_hour"])
                if time_up or hour_up:
                    settle(close[i], "time", i)

        # prop rails: refresh the daily/total halt state with current equity
        if rails_on:
            guard.on_new_bar(pd.Timestamp(times[i]).date(), equity)
            if guard.blown and blown_at is None:
                blown_at = pd.Timestamp(times[i])

        # 2) compute a fresh signal at this bar's close
        sig = signal_fn(df, i)
        if sig is None:
            continue

        # 3) opposite-signal flip closes the open position first (engine parity)
        if pos is not None and allow_flip and sig.side != pos["side"]:
            settle(close[i], "signal", i)

        if pos is not None:  # max 1 position
            continue

        # prop rails: daily/total halt blocks new entries (never force-closes)
        if rails_on and not guard.may_open(0)[0]:
            continue

        price = close[i]
        entry = price + spread_p if sig.side == "long" else price - spread_p
        # engine's levels-valid check
        if sig.side == "long":
            valid = sig.sl < price and (sig.tp is None or price < sig.tp)
        else:
            valid = sig.sl > price and (sig.tp is None or price > sig.tp)
        if not valid:
            continue
        # Engine parity: size from the raw close->SL distance (engine.py sizes
        # off `price`, the close), but measure realized risk from the actual
        # spread-adjusted entry (sim.open_position does).
        sl_pips = abs(price - sig.sl) / pip
        lots = position_size_lots(equity, risk, sl_pips, pip_value, MIN_LOT, MAX_LOT)
        if lots <= 0:
            continue
        pos = {"side": sig.side, "entry": entry, "sl": sig.sl, "tp": sig.tp,
               "lots": lots, "risk_amt": abs(entry - sig.sl) / pip * pip_value * lots,
               "entry_bar": i, "exit_hour": sig.exit_hour, "max_hold": sig.max_hold,
               "meta": sig.meta}

    if pos is not None:
        settle(close[-1], "end", n - 1)

    t = pd.DataFrame(trades)
    if t.empty:
        return dict(trades=0, wins=0, win_rate=0.0, net=0.0, max_dd=0.0,
                    final_equity=start_equity, trade_log=t, blown_at=blown_at)
    eq = start_equity + t["profit"].cumsum()
    return dict(
        trades=len(t), wins=int((t["profit"] > 0).sum()),
        win_rate=float((t["profit"] > 0).mean()),
        net=float(t["profit"].sum()),
        max_dd=float((eq - eq.cummax()).min()),
        final_equity=float(eq.iloc[-1]), trade_log=t, blown_at=blown_at)


# --------------------------------------------------------------------------- #
# ORB signal wrapper (for validation + as the losing control)                 #
# --------------------------------------------------------------------------- #
def make_orb_signal(cfg: Config):
    from trader.strategies import orb
    from trader.strategy import Setup
    L = orb.lookback(cfg)

    def sig(df, i):
        window = df.iloc[max(0, i + 1 - L):i + 1]
        r = orb.compute_signal(window, cfg)
        if isinstance(r, Setup):
            return Entry(r.side, sl=r.sl, tp=r.tp, meta=dict(r.meta or {}))
        return None
    return sig


def validate():
    """Harness cost model must reproduce trader.sim.run_backtest on ORB."""
    from trader.sim import run_backtest
    df = load_h1("2025-08-11", "2026-08-11")
    cfg = Config(symbol=SYM, timeframe="H1", strategy="orb",
                 pip_size=PIP, pip_value_per_lot=PIP_VALUE, spread_pips=SPREAD,
                 orb_session_start_hour=1, orb_box_candles=3, orb_tp_mode="r_multiple",
                 orb_tp_r=3.0, orb_structure_filter=False, orb_vol_filter=False,
                 risk_per_trade=RISK, daily_loss_halt=1.0)  # halt off for parity
    engine = run_backtest(df, cfg, starting_equity=START_EQUITY)
    mine = simulate(df, make_orb_signal(cfg), allow_flip=True)
    E = engine["trade_log"].reset_index(drop=True)
    M = mine["trade_log"].reset_index(drop=True)
    print("VALIDATION — ORB EURUSD H1 2025-08-11..2026-08-11, v1 3R, halts off")
    print(f"  engine : trades={engine['trades']:<4} net={engine['net_profit']:+.2f}")
    print(f"  harness: trades={mine['trades']:<4} net={mine['net']:+.2f}")
    # The real correctness gate: identical decisions and fill prices. A few
    # trades may differ by one 0.01 lot step (an equity-path truncation artifact
    # worth a few dollars total); that is expected and not a modeling error.
    same_n = engine["trades"] == mine["trades"]
    reason_diff = int((E["reason"].values != M["reason"].values).sum()) if same_n else -1
    exit_diff = int((np.abs(E["exit"].values - M["exit"].values) > 1e-9).sum()) if same_n else -1
    lots_diff = int((np.abs(E["lots"].values - M["lots"].values) > 1e-9).sum()) if same_n else -1
    ok = same_n and reason_diff == 0 and exit_diff == 0
    print(f"  decisions: reason_diff={reason_diff} exit_price_diff={exit_diff} "
          f"(lot-rounding-only diffs: {lots_diff}, net gap ${abs(engine['net_profit']-mine['net']):.2f})")
    print(f"  -> {'VALIDATED — identical decisions & fills' if ok else 'MISMATCH'}")
    return ok


# --------------------------------------------------------------------------- #
# Indicators (no lookahead: value at i uses only bars <= i)                    #
# --------------------------------------------------------------------------- #
def atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    high, low, close = df["high"], df["low"], df["close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev).abs(), (low - prev).abs()],
                   axis=1).max(axis=1)
    return tr.rolling(n).mean().values


# --------------------------------------------------------------------------- #
# Candidate 1: SESSION time-of-day                                            #
# Enter at a fixed hour, hold a fixed number of bars, exit by time (or a wide  #
# ATR disaster-stop). Direction/hour/hold are the only knobs.                  #
# --------------------------------------------------------------------------- #
def make_session_signal(df, *, entry_hour, hold, side, stop_mult=2.0, atr_n=14):
    hours = pd.DatetimeIndex(df["time"]).hour.values
    close = df["close"].values
    a = atr(df, atr_n)

    def sig(_df, i):
        if hours[i] != entry_hour or np.isnan(a[i]) or a[i] <= 0:
            return None
        stop = stop_mult * a[i]
        price = close[i]
        sl = price - stop if side == "long" else price + stop
        return Entry(side, sl=sl, tp=None, max_hold=hold,
                     meta={"entry_hour": entry_hour})
    return sig


SESSION_GRID = [dict(entry_hour=h, hold=hold, side=s)
                for h in range(24) for hold in (3, 6, 12) for s in ("long", "short")]


def session_search(train_df, min_trades=25):
    best, best_net = None, -1e18
    for p in SESSION_GRID:
        r = simulate(train_df, make_session_signal(train_df, **p))
        if r["trades"] >= min_trades and r["net"] > best_net:
            best, best_net = p, r["net"]
    return best


# --------------------------------------------------------------------------- #
# Candidate 2: MEAN-REVERSION (z-score fade back to the mean)                  #
# Enter when close is >= entry_z std from its SMA; stop beyond the extreme     #
# (ATR-based), target = the SMA at entry (static). Cap the hold.               #
# --------------------------------------------------------------------------- #
def efficiency_ratio(close: np.ndarray, m: int) -> np.ndarray:
    """Kaufman ER over m bars: |net move| / sum(|bar moves|). ~0 = choppy/
    ranging (good for fading), ~1 = clean trend. value at i uses bars <= i."""
    s = pd.Series(close)
    net = s.diff(m).abs()
    vol = s.diff().abs().rolling(m).sum()
    return (net / vol).values


def make_meanrev_signal(df, *, n, entry_z, stop_mult, max_hold, atr_n=14,
                        er_window=0, er_max=None):
    close = df["close"].values
    sma = pd.Series(close).rolling(n).mean().values
    std = pd.Series(close).rolling(n).std().values
    a = atr(df, atr_n)
    er = efficiency_ratio(close, er_window) if er_max is not None else None

    def sig(_df, i):
        if np.isnan(sma[i]) or np.isnan(std[i]) or std[i] <= 0 or np.isnan(a[i]):
            return None
        if er is not None and (np.isnan(er[i]) or er[i] > er_max):
            return None  # regime filter: only fade when the market is ranging
        z = (close[i] - sma[i]) / std[i]
        price = close[i]
        stop = stop_mult * a[i]
        if z <= -entry_z:
            return Entry("long", sl=price - stop, tp=float(sma[i]),
                         max_hold=max_hold, meta={"z": round(float(z), 2)})
        if z >= entry_z:
            return Entry("short", sl=price + stop, tp=float(sma[i]),
                         max_hold=max_hold, meta={"z": round(float(z), 2)})
        return None
    return sig


MEANREV_GRID = [dict(n=n, entry_z=z, stop_mult=sm, max_hold=mh)
                for n in (20, 50, 100) for z in (1.5, 2.0, 2.5)
                for sm in (1.5, 2.5) for mh in (12, 24, 48)]


def meanrev_search(train_df, min_trades=25):
    best, best_net = None, -1e18
    for p in MEANREV_GRID:
        r = simulate(train_df, make_meanrev_signal(train_df, **p))
        if r["trades"] >= min_trades and r["net"] > best_net:
            best, best_net = p, r["net"]
    return best


# --------------------------------------------------------------------------- #
# Walk-forward driver                                                         #
# --------------------------------------------------------------------------- #
def folds(df, train_years=2, test_months=6, step_months=6):
    out = []
    t0 = df["time"].min().normalize()
    end = df["time"].max()
    tr_start = t0
    while True:
        tr_end = tr_start + pd.DateOffset(years=train_years)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if te_end > end + pd.Timedelta(days=1):
            break
        train = df[(df["time"] >= tr_start) & (df["time"] < tr_end)]
        test = df[(df["time"] >= tr_end) & (df["time"] < te_end)]
        out.append((train.reset_index(drop=True), test.reset_index(drop=True),
                    f"{tr_end:%Y-%m}..{te_end:%Y-%m}"))
        tr_start = tr_start + pd.DateOffset(months=step_months)
    return out


def walk_forward(name, df, search_fn, build_fn, **fold_kw):
    fs = folds(df, **fold_kw)
    print(f"\n=== WALK-FORWARD: {name} === ({len(fs)} OOS test folds, "
          f"train={fold_kw.get('train_years', 2)}yr / "
          f"test={fold_kw.get('test_months', 6)}mo)")
    print(f"{'test window':<18}{'trades':>7}{'win%':>7}{'net$':>10}{'maxDD$':>10}  params")
    rows = []
    for train, test, label in fs:
        p = search_fn(train)
        if p is None:
            print(f"{label:<18}{'-- no params cleared min-trades on train --':>34}")
            continue
        r = simulate(test, build_fn(test, **p))
        rows.append(r)
        pstr = ",".join(f"{k}={v}" for k, v in p.items())
        print(f"{label:<18}{r['trades']:>7}{r['win_rate']*100:>6.1f}%"
              f"{r['net']:>+10.0f}{r['max_dd']:>+10.0f}  {pstr}")
    if rows:
        net = sum(r["net"] for r in rows)
        tot = sum(r["trades"] for r in rows)
        pos = sum(1 for r in rows if r["net"] > 0)
        big = [r for r in rows if r["trades"] >= 20]
        pos_big = sum(1 for r in big if r["net"] > 0)
        print(f"{'-'*60}")
        print(f"AGGREGATE OOS: net={net:+.0f}  trades={tot}  "
              f"folds positive={pos}/{len(rows)}  "
              f"(folds >=20 trades: {pos_big}/{len(big)} positive)")
    return rows


BUILDERS = {"session": (session_search, make_session_signal),
            "meanrev": (meanrev_search, make_meanrev_signal)}


def per_year(name, df, build_fn):
    """Evaluate ONE fixed (a-priori) config over the whole history, no training.
    Nothing is fit, so the entire span is a fair test."""
    r = simulate(df, build_fn(df))
    t = r["trade_log"]
    print(f"\n=== FIXED CONFIG (no per-fold tuning): {name} ===")
    print(f"{'year':<6}{'trades':>7}{'win%':>7}{'net$':>10}")
    if not t.empty:
        t = t.copy()
        t["year"] = pd.DatetimeIndex(t["entry_time"]).year
        for y, g in t.groupby("year"):
            print(f"{y:<6}{len(g):>7}{(g['profit']>0).mean()*100:>6.1f}%{g['profit'].sum():>+10.0f}")
    yrs = t["entry_time"].dt.year.nunique() if not t.empty else 0
    pos_years = 0
    if not t.empty:
        by = t.groupby(pd.DatetimeIndex(t["entry_time"]).year)["profit"].sum()
        pos_years = int((by > 0).sum())
    print(f"{'-'*30}")
    print(f"TOTAL net={r['net']:+.0f}  trades={r['trades']}  win={r['win_rate']*100:.1f}%  "
          f"maxDD={r['max_dd']:+.0f}  positive years={pos_years}/{yrs}")
    return r


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "validate":
        validate()
    elif cmd in BUILDERS:
        df = load_h1()
        search_fn, build_fn = BUILDERS[cmd]
        walk_forward(cmd, df, search_fn, build_fn)
    elif cmd == "session_spread":
        # Make-or-break: does the edge survive realistic Tokyo-open spreads?
        # Entry fires at the widest-spread minute, so stress it hard.
        risk = float(sys.argv[2]) if len(sys.argv) > 2 else 0.007
        df = load_h1()
        yr = df[df["time"] >= df["time"].max() - pd.DateOffset(months=12)].reset_index(drop=True)
        print(f"\n=== {SYM} Tokyo-open long — SPREAD STRESS (risk {risk*100:.2f}%) ===")
        print(f"base preset spread = {SPREAD} pips. Testing wider entry spreads:")
        print(f"{'spread(pips)':>12}{'12mo net$':>12}{'12mo win%':>11}{'12mo DDstart%':>15}{'10yr net$':>12}")
        for sp in [SPREAD, 4.0, 6.0, 8.0, 10.0]:
            r12 = simulate(yr, make_session_signal(yr, entry_hour=HOUR, hold=12, side="long"),
                           start_equity=10_000.0, risk=risk, spread=sp)
            rall = simulate(df, make_session_signal(df, entry_hour=HOUR, hold=12, side="long"),
                            start_equity=10_000.0, risk=risk, spread=sp)
            t = r12["trade_log"]
            dd_start = 0.0
            if not t.empty:
                eq = 10_000 + t["profit"].cumsum()
                dd_start = float(((eq - 10_000) / 10_000 * 100).min())
            print(f"{sp:>12.1f}{r12['net']:>+12.0f}{r12['win_rate']*100:>10.1f}%"
                  f"{dd_start:>+14.2f}%{rall['net']:>+12.0f}")
        print("(DDstart% = worst dip below the $10k start = what your STATIC 8% rule watches)")
    elif cmd == "session_dd":
        # Did the Tokyo-open strat ever breach the firm's 4% daily / 8% total
        # drawdown? Measured with rails OFF so nothing masks the true excursion.
        risk = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
        df = load_h1()
        print(f"(risk per trade = {risk*100:.2f}%)")
        for label, sub in [("LAST 12 MONTHS", df[df["time"] >= df["time"].max() - pd.DateOffset(months=12)].reset_index(drop=True)),
                           ("FULL HISTORY (all regimes)", df)]:
            r = simulate(sub, make_session_signal(sub, entry_hour=HOUR, hold=12, side="long"),
                         start_equity=10_000.0, risk=risk)  # rails off
            t = r["trade_log"].copy()
            t["day"] = pd.DatetimeIndex(t["entry_time"]).date
            # daily realized P&L as % of equity at the day's start
            daily = t.groupby("day").agg(pnl=("profit", "sum"),
                                         eq_end=("equity_after", "last"))
            daily["eq_start"] = daily["eq_end"] - daily["pnl"]
            daily["pct"] = daily["pnl"] / daily["eq_start"] * 100
            worst_day = daily["pct"].min()
            days_over_4 = int((daily["pct"] <= -4).sum())
            # total drawdown on the realized equity curve
            eq = 10_000 + t["profit"].cumsum()
            peak = eq.cummax()
            dd_peak = ((eq - peak) / peak * 100).min()          # trailing DD
            dd_base = ((eq - 10_000) / 10_000 * 100).min()      # from starting balance
            print(f"\n=== {SYM} Tokyo-open long — DRAWDOWN vs prop limits ({label}) ===")
            print(f"  trades: {len(t)}   net: {r['net']:+.0f}")
            print(f"  worst single DAY:        {worst_day:+.2f}%   (limit -4%)  "
                  f"-> days breaching: {days_over_4}")
            print(f"  max total DD from PEAK:  {dd_peak:+.2f}%   (limit -8% if TRAILING)")
            print(f"  max total DD from START: {dd_base:+.2f}%   (limit -8% if STATIC)")
            print(f"  NOTE: realized-equity basis; intraday floating adds ~<=1% "
                  f"(one 1%-risk trade/day), so daily can't approach -4%.")
    elif cmd == "session_prop":
        # Tokyo-open long (hour 0, hold 12) under the live bot's PROP rails.
        months = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        risk = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
        df = load_h1()
        end = df["time"].max()
        start = end - pd.DateOffset(months=months)
        sub = df[df["time"] >= start].reset_index(drop=True)
        # Firm rule is STATIC 8% total / 4% daily; run at the firm's real limits.
        RAILS = dict(risk=risk, daily_halt=0.04, loss_baseline=10_000.0,
                     total_halt=0.08)
        r = simulate(sub, make_session_signal(sub, entry_hour=HOUR, hold=12, side="long"),
                     start_equity=10_000.0, **RAILS)
        t = r["trade_log"]
        print(f"\n=== {SYM} Tokyo-open long (hour0, hold12) — PROP RULES, last {months} months ===")
        print(f"span: {sub['time'].min():%Y-%m-%d} -> {sub['time'].max():%Y-%m-%d}  ({len(sub)} H1 bars)")
        print(f"rails: {risk*100:.2f}% risk/trade, daily halt -4% (static), total halt -8% (static), $10k start")
        print(f"trades:       {r['trades']}")
        print(f"win rate:     {r['win_rate']:.1%}")
        print(f"net profit:   {r['net']:+.2f}")
        print(f"max drawdown: {r['max_dd']:+.2f}")
        print(f"final equity: {r['final_equity']:.2f}")
        print(f"prop breach:  {'YES @ '+str(r['blown_at']) if r['blown_at'] else 'no (survived)'}")
        if not t.empty:
            t = t.copy(); t["month"] = pd.DatetimeIndex(t["entry_time"]).to_period("M")
            print(f"\n{'month':<9}{'trades':>7}{'wins':>6}{'net$':>10}{'equity':>10}")
            for m, g in t.groupby("month"):
                print(f"{str(m):<9}{len(g):>7}{int((g['profit']>0).sum()):>6}"
                      f"{g['profit'].sum():>+10.2f}{g['equity_after'].iloc[-1]:>10.2f}")
            worst = t.nsmallest(3, "profit")[["entry_time", "profit", "reason"]]
            print("\nworst 3 trades:")
            for _, w in worst.iterrows():
                print(f"  {w['entry_time']:%Y-%m-%d %H:%M}  {w['profit']:+.2f}  ({w['reason']})")
    elif cmd == "session_hours":
        # Decisive test: is entry_hour=0 long special (real time-of-day edge),
        # or does EVERY hour make similar money (just long-bias / trend capture)?
        df = load_h1()
        px = df["close"].iloc[-1] / df["close"].iloc[0] - 1
        print(f"\n{SYM} price {df['time'].min().date()}->{df['time'].max().date()}: "
              f"{px*100:+.0f}% (buy&hold context)")
        print("all configs: side=long, hold=12, fixed over full history")
        print(f"{'hour':>4}{'trades':>8}{'win%':>7}{'net$':>9}{'posYrs':>8}")
        best = []
        for h in range(24):
            r = simulate(df, make_session_signal(df, entry_hour=h, hold=12, side="long"))
            t = r["trade_log"]
            py = 0
            if not t.empty:
                by = t.groupby(pd.DatetimeIndex(t["entry_time"]).year)["profit"].sum()
                py = int((by > 0).sum()); ny = len(by)
            print(f"{h:>4}{r['trades']:>8}{r['win_rate']*100:>6.1f}%{r['net']:>+9.0f}{py:>5}/{ny}")
            best.append((r["net"], h))
        # And the winning fold config per-year, plus its short mirror.
        for side in ("long", "short"):
            per_year(f"hour=0 {side} hold=12", df,
                     lambda d, s=side: make_session_signal(d, entry_hour=0, hold=12, side=s))
    elif cmd == "meanrev_wf":
        tf = sys.argv[2] if len(sys.argv) > 2 else "H4"
        df = load_tf(tf)
        walk_forward(f"meanrev {tf}", df, meanrev_search, make_meanrev_signal,
                     train_years=3, test_months=12, step_months=12)
    elif cmd == "meanrev_fixed":
        df = load_h1()
        # A-priori deep-fade configs chosen from theory (fade only strong
        # extremes), NOT tuned per fold. All shown — no cherry-picking.
        for p in [dict(n=100, entry_z=2.5, stop_mult=2.5, max_hold=24),
                  dict(n=100, entry_z=2.5, stop_mult=2.5, max_hold=12),
                  dict(n=50, entry_z=2.5, stop_mult=2.5, max_hold=24),
                  dict(n=100, entry_z=3.0, stop_mult=3.0, max_hold=24)]:
            per_year(f"meanrev {p}", df,
                     lambda d, p=p: make_meanrev_signal(d, **p))
    elif cmd == "meanrev_regime":
        df = load_h1()
        # Deep-fade + ranging-regime filter (er_max). A-priori configs, all shown.
        for p in [dict(n=100, entry_z=2.5, stop_mult=2.5, max_hold=24, er_window=24, er_max=0.3),
                  dict(n=100, entry_z=2.0, stop_mult=2.5, max_hold=24, er_window=24, er_max=0.3),
                  dict(n=100, entry_z=2.5, stop_mult=2.5, max_hold=24, er_window=48, er_max=0.25),
                  dict(n=50, entry_z=2.0, stop_mult=2.5, max_hold=24, er_window=24, er_max=0.35)]:
            per_year(f"meanrev+regime {p}", df,
                     lambda d, p=p: make_meanrev_signal(d, **p))
    elif cmd == "meanrev_tf":
        # Cost-drag hypothesis: the same deep-fade on higher timeframes, where
        # the ~1-pip spread is tiny vs the bar's range. A-priori configs, all shown.
        for tf, cfgs in [
            ("D1", [dict(n=20, entry_z=2.0, stop_mult=2.5, max_hold=10),
                    dict(n=20, entry_z=2.5, stop_mult=2.5, max_hold=10),
                    dict(n=10, entry_z=2.0, stop_mult=2.0, max_hold=8)]),
            ("H4", [dict(n=30, entry_z=2.0, stop_mult=2.5, max_hold=18),
                    dict(n=30, entry_z=2.5, stop_mult=2.5, max_hold=18),
                    dict(n=50, entry_z=2.5, stop_mult=2.5, max_hold=24)]),
        ]:
            df = load_tf(tf)
            print(f"\n############ TIMEFRAME {tf}  ({len(df)} bars) ############")
            for p in cfgs:
                per_year(f"{tf} meanrev {p}", df,
                         lambda d, p=p: make_meanrev_signal(d, **p))
    elif cmd == "orb":
        # ORB control: fixed v1 3R, no per-fold search.
        df = load_h1()
        cfg = Config(symbol=SYM, timeframe="H1", strategy="orb", pip_size=PIP,
                     pip_value_per_lot=PIP_VALUE, spread_pips=SPREAD,
                     orb_session_start_hour=1, orb_box_candles=3,
                     orb_tp_mode="r_multiple", orb_tp_r=3.0,
                     orb_structure_filter=False, orb_vol_filter=False)
        walk_forward("orb (control)", df, lambda tr: {},
                     lambda te: make_orb_signal(cfg))
    else:
        print(f"unknown command {cmd!r}; try: validate | session | meanrev | orb")

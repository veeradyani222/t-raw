"""Parameterized backtest CLI — no new script per experiment.

    python backtest.py XAUUSD H1 --from 2026-05-01 --to 2026-08-11
    python backtest.py XAUUSD H1 --from 2025-08-11 --to 2026-08-11 \
        --tp-mode structure --tp-r 3
    python backtest.py XAUUSD H1 --from 2026-05-01 --to 2026-08-11 \
        --no-vol-filter --no-structure-filter --tp-mode r_multiple   # v1 behavior

Data comes from data/<symbol>-<tf>.csv when the cache covers the range;
otherwise it is fetched from the MT5 terminal (chunked) and merged into the
cache. MT5 is only imported when a fetch is actually needed, so cache-served
runs work without the terminal.

Every run writes a per-trade CSV log to logs/ — one row per trade (entry,
exit, why it exited, R multiple, box and filter diagnostics) and one row per
signal that was blocked or skipped, with the reason.
"""
import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from trader.config import Config
from trader.sim import run_backtest

log = logging.getLogger("trader")

# Per-symbol market constants. pip_value_per_lot holds for USD-quoted
# symbols on a USD account; add entries (or use the flags) for anything else.
SYMBOLS = {
    "XAUUSD": dict(pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0),
    "EURUSD": dict(pip_size=0.0001, pip_value_per_lot=10.0, spread_pips=1.0),
    "GBPUSD": dict(pip_size=0.0001, pip_value_per_lot=10.0, spread_pips=1.5),
    # JPY-quoted: pip = 0.01. Risk-normalized backtest P&L is invariant to the
    # exact JPY->USD pip value (lots scale as 1/pip_value, profit as pip_value),
    # so pip_value_per_lot=10 is fine; only pip_size and spread matter.
    "GBPJPY": dict(pip_size=0.01, pip_value_per_lot=10.0, spread_pips=2.5),
    "USDJPY": dict(pip_size=0.01, pip_value_per_lot=10.0, spread_pips=1.0),
    "AUDJPY": dict(pip_size=0.01, pip_value_per_lot=10.0, spread_pips=2.0),
    "EURJPY": dict(pip_size=0.01, pip_value_per_lot=10.0, spread_pips=1.5),
}

LOG_COLUMNS = [
    "kind", "date", "weekday", "time", "side", "entry", "sl", "tp", "lots",
    "box_high", "box_low", "box_size", "vol_ratio", "structure", "tp_source",
    "exit_time", "exit_price", "exit_reason", "bars_held", "profit",
    "r_multiple", "equity_after", "note",
]


def fetch_mt5(cfg: Config, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Chunked copy_rates_range pull (one-shot requests above the terminal's
    bar limit fail with 'Invalid params'). Imports MT5 lazily."""
    from datetime import timedelta, timezone

    from trader import broker_mt5

    mt5 = broker_mt5.mt5
    broker_mt5.connect(cfg)
    try:
        frames = []
        t0 = start.to_pydatetime().replace(tzinfo=timezone.utc)
        t_end = end.to_pydatetime().replace(tzinfo=timezone.utc) + timedelta(days=1)
        step = timedelta(days=15)
        while t0 < t_end:
            t1 = min(t0 + step, t_end)
            rates = mt5.copy_rates_range(
                cfg.symbol, broker_mt5.TIMEFRAMES[cfg.timeframe], t0, t1)
            if rates is not None and len(rates):
                frames.append(pd.DataFrame(rates))
            t0 = t1
    finally:
        broker_mt5.shutdown()
    if not frames:
        raise SystemExit(f"MT5 returned no {cfg.symbol} {cfg.timeframe} history "
                         f"for {start:%Y-%m-%d} -> {end:%Y-%m-%d}")
    df = pd.concat(frames).drop_duplicates(subset="time").sort_values("time")
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close", "tick_volume"]].reset_index(drop=True)


def load_history(cfg: Config, start: pd.Timestamp, end: pd.Timestamp,
                 data_file: str | None, need_volume: bool) -> pd.DataFrame:
    """Serve the range from the per-symbol cache, fetching from MT5 only when
    the cache is missing, doesn't cover the range, or lacks needed volume."""
    if data_file:
        df = pd.read_csv(data_file, parse_dates=["time"])
    else:
        cache = Path(f"data/{cfg.symbol.lower()}-{cfg.timeframe.lower()}.csv")
        cached = pd.read_csv(cache, parse_dates=["time"]) if cache.exists() else None
        # Weekends/holidays mean the first bar can lag the requested start by
        # a few days; 4 days of slack keeps that from forcing a refetch.
        slack = pd.Timedelta(days=4)
        covered = cached is not None \
            and cached["time"].min() <= start + slack \
            and cached["time"].max() >= end - slack \
            and (not need_volume or "tick_volume" in cached.columns)
        if covered:
            df = cached
        else:
            print(f"cache {'missing' if cached is None else 'insufficient'} — "
                  f"fetching {cfg.symbol} {cfg.timeframe} from MT5 ...")
            df = fetch_mt5(cfg, start, end)
            if cached is not None and "tick_volume" in cached.columns:
                df = (pd.concat([cached, df]).drop_duplicates(subset="time")
                      .sort_values("time").reset_index(drop=True))
            cache.parent.mkdir(exist_ok=True)
            df.to_csv(cache, index=False)
            print(f"cached {len(df)} bars -> {cache}")

    df = df[(df["time"] >= start) & (df["time"] < end + pd.Timedelta(days=1))]
    if df.empty:
        raise SystemExit(f"no bars in {start:%Y-%m-%d} -> {end:%Y-%m-%d} "
                         f"(data spans {data_file or 'cache'})")
    return df.reset_index(drop=True)


def build_trade_log(result: dict) -> pd.DataFrame:
    """One row per trade plus one per blocked/skipped signal, time-ordered."""
    rows = []
    trades = result["trade_log"]
    for _, tr in trades.iterrows():
        entry_time = tr.get("entry_time") or tr["time"]
        rows.append({
            "kind": "trade",
            "date": f"{entry_time:%Y-%m-%d}", "weekday": f"{entry_time:%A}",
            "time": f"{entry_time:%H:%M}",
            "side": tr["side"], "entry": tr["entry"], "sl": tr.get("sl"),
            "tp": tr.get("tp"), "lots": tr["lots"],
            "box_high": tr.get("box_high"), "box_low": tr.get("box_low"),
            "box_size": tr.get("box_size"), "vol_ratio": tr.get("vol_ratio"),
            "structure": tr.get("structure"), "tp_source": tr.get("tp_source"),
            "exit_time": tr["time"], "exit_price": tr["exit"],
            "exit_reason": tr["reason"], "bars_held": tr.get("bars_held"),
            "profit": round(tr["profit"], 2),
            "r_multiple": round(tr["r_multiple"], 2) if pd.notna(tr.get("r_multiple")) else None,
            "equity_after": round(tr["equity_after"], 2) if pd.notna(tr.get("equity_after")) else None,
            "note": "",
            "_sort": entry_time,
        })
    events = result["events"]
    for _, ev in events.iterrows():
        meta = ev.get("meta") or {}
        rows.append({
            "kind": ev["kind"],
            "date": f"{ev['time']:%Y-%m-%d}", "weekday": f"{ev['time']:%A}",
            "time": f"{ev['time']:%H:%M}", "side": ev["side"],
            "box_high": meta.get("box_high"), "box_low": meta.get("box_low"),
            "box_size": meta.get("box_size"), "vol_ratio": meta.get("vol_ratio"),
            "structure": meta.get("structure"),
            "note": ev["reason"],
            "_sort": ev["time"],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=LOG_COLUMNS)
    return (df.sort_values("_sort").drop(columns="_sort")
            .reindex(columns=LOG_COLUMNS).reset_index(drop=True))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Backtest a strategy over a date range.")
    p.add_argument("symbol", help="e.g. XAUUSD")
    p.add_argument("timeframe", help="M1 M5 M15 M30 H1 H4 D1")
    p.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    p.add_argument("--strategy", default="orb")
    p.add_argument("--tp-mode", choices=["structure", "r_multiple"], default="structure")
    p.add_argument("--tp-r", type=float, default=3.0)
    p.add_argument("--vol-filter", action="store_true",
                   help="opt-in: backtested worse at every threshold tried")
    p.add_argument("--no-vol-filter", action="store_true",
                   help="(default; kept for compatibility)")
    p.add_argument("--vol-mult", type=float, default=1.2)
    p.add_argument("--vol-lookback", type=int, default=20)
    p.add_argument("--no-structure-filter", action="store_true")
    p.add_argument("--box-candles", type=int, default=3)
    p.add_argument("--session-start-hour", type=int, default=1)
    p.add_argument("--equity", type=float, default=10_000.0)
    p.add_argument("--risk", type=float, default=0.01,
                   help="fraction of equity risked per trade (default 0.01)")
    p.add_argument("--daily-halt", type=float, default=0.03,
                   help="stop trading for the day at this loss fraction")
    p.add_argument("--max-dd-halt", type=float, default=0.0,
                   help="PERMANENT stop this far below the equity peak (0 = off)")
    p.add_argument("--loss-baseline", type=float, default=0.0,
                   help="prop mode: fixed $ base the daily/total limits are "
                        "measured against, e.g. 10000 (0 = legacy %% mode)")
    p.add_argument("--total-loss-halt", type=float, default=0.0,
                   help="prop mode: PERMANENT stop this fraction below the fixed "
                        "baseline (static), e.g. 0.06 for -$600 on a $10k base")
    p.add_argument("--monthly", action="store_true",
                   help="print a month-by-month P/L table")
    p.add_argument("--spread-pips", type=float, default=None)
    p.add_argument("--pip-size", type=float, default=None)
    p.add_argument("--pip-value", type=float, default=None)
    p.add_argument("--data", default=None, help="CSV to use instead of cache/MT5")
    p.add_argument("--log-dir", default="logs")
    p.add_argument("--quiet", action="store_true", help="suppress per-bar engine logging")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    preset = SYMBOLS.get(args.symbol.upper(), {})
    if not preset and (args.pip_size is None or args.pip_value is None):
        raise SystemExit(f"unknown symbol {args.symbol!r}: pass --pip-size and "
                         f"--pip-value (known: {', '.join(sorted(SYMBOLS))})")
    cfg = Config(
        symbol=args.symbol.upper(), timeframe=args.timeframe.upper(),
        strategy=args.strategy,
        pip_size=args.pip_size if args.pip_size is not None else preset["pip_size"],
        pip_value_per_lot=args.pip_value if args.pip_value is not None else preset["pip_value_per_lot"],
        spread_pips=args.spread_pips if args.spread_pips is not None else preset.get("spread_pips", 1.0),
        orb_session_start_hour=args.session_start_hour,
        orb_box_candles=args.box_candles,
        orb_tp_r=args.tp_r, orb_tp_mode=args.tp_mode,
        orb_vol_filter=args.vol_filter and not args.no_vol_filter,
        orb_vol_mult=args.vol_mult, orb_vol_lookback=args.vol_lookback,
        orb_structure_filter=not args.no_structure_filter,
        risk_per_trade=args.risk, daily_loss_halt=args.daily_halt,
        max_drawdown_halt=args.max_dd_halt,
        loss_baseline=args.loss_baseline, total_loss_halt=args.total_loss_halt,
    )

    start = pd.Timestamp(args.date_from)
    end = pd.Timestamp(args.date_to)
    history = load_history(cfg, start, end, args.data, need_volume=cfg.orb_vol_filter)
    if cfg.orb_vol_filter and "tick_volume" not in history.columns:
        print("NOTE: data has no tick_volume column — volume filter auto-passes.")

    result = run_backtest(history, cfg, starting_equity=args.equity)

    trade_log = build_trade_log(result)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / (f"backtest-{cfg.symbol.lower()}-{cfg.timeframe.lower()}"
                          f"-{start:%Y%m%d}-{end:%Y%m%d}-{run_id}.csv")
    trade_log.to_csv(log_path, index=False)

    span = f"{history['time'].min():%Y-%m-%d} -> {history['time'].max():%Y-%m-%d}"
    blocked = trade_log[trade_log["kind"] == "blocked"]
    skipped = trade_log[trade_log["kind"] == "skipped"]
    print(f"\n=== {cfg.symbol} {cfg.timeframe} {span} | strategy={cfg.strategy} "
          f"tp_mode={cfg.orb_tp_mode} tp_r={cfg.orb_tp_r} "
          f"vol_filter={cfg.orb_vol_filter} structure_filter={cfg.orb_structure_filter} ===")
    print(f"bars:          {result['bars']}")
    print(f"trades:        {result['trades']}  (blocked: {len(blocked)}, "
          f"skipped: {len(skipped)})")
    print(f"win rate:      {result['win_rate']:.1%}")
    print(f"net profit:    {result['net_profit']:+.2f}")
    print(f"max drawdown:  {result['max_drawdown']:+.2f}")
    print(f"final equity:  {result['final_equity']:.2f} (from {args.equity:.2f})")
    if not blocked.empty:
        counts = blocked["note"].str.split(":").str[0].str.split(" ").str[0].value_counts()
        print("blocked by:    " + ", ".join(f"{k} x{v}" for k, v in counts.items()))
    if result["blown_at"] is not None:
        print(f"*** ACCOUNT RULES BREACHED {result['blown_at']:%Y-%m-%d %H:%M} — "
              f"equity fell {cfg.max_drawdown_halt:.0%} below its peak; "
              f"no trades opened after this point. ***")
    if args.monthly:
        trades = result["trade_log"]
        if trades.empty:
            print("\nno trades to break down by month")
        else:
            t = trades.copy()
            t["month"] = t["time"].dt.to_period("M")
            print(f"\n{'month':<9}{'trades':>7}{'wins':>6}{'net':>10}{'equity':>10}")
            for month, g in t.groupby("month"):
                print(f"{str(month):<9}{len(g):>7}{int((g['profit'] > 0).sum()):>6}"
                      f"{g['profit'].sum():>+10.2f}{g['equity_after'].iloc[-1]:>10.2f}")
    print(f"trade log:     {log_path}")


if __name__ == "__main__":
    main()

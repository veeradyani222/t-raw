"""Demo forward test vs backtest, one server day at a time.

    python compare_demo.py --date 2026-10-21            # print the report
    python compare_demo.py --date 2026-10-21 --telegram # ...and send the summary

For the server day D (broker time, EET like the research bars):
  LIVE      the demo account's deals, grouped per position, keyed by magic
            number (one per strategy), for positions opened or closed on D.
  BACKTEST  for every strategy, the same rolling window the bot uses (the
            last WINDOW_BARS bars of its symbol/timeframe ending at D 24:00,
            fetched from the SAME terminal) through research/prop/harness.simulate
            at the strategy's portfolio risk; trades opened or closed on D.
Then, per strategy: trades live vs backtest, entry / exit price differences,
P&L difference, and account totals. Honest by construction: the backtest
side is re-run on the real bars, not read from the research results.

Caveats printed with the report: the backtest window starts WINDOW_BARS
earlier than the bot did, so a backtest position opened before the bot's
first start has no live twin; strategies whose symbol is untradable on this
account are shown as NOT TRADED LIVE; a day that is not over yet is marked.
Output is also written to logs/compare/<date>.txt and .json.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

# Windows consoles default to cp1252; the reports carry emoji and arrows.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("PROP_OOS", "1")           # a forward test IS the verification stage

from research.prop import harness as H                     # noqa: E402
from trader import mt5_market                             # noqa: E402
from trader.alerts import send_alert                      # noqa: E402
from trader.config import CONFIG                          # noqa: E402
from trader.multi import (BASE_MAGIC, MIX_PATH, WINDOW_BARS, StrategySpec, attach_conv,  # noqa: E402
                          conv_pair_for, load_mix, load_symbol_map)
from trader.mt5_market import MT5Market                   # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "logs" / "compare"
log = logging.getLogger("trader")


# --------------------------------------------------------------------------- #
# live side                                                                    #
# --------------------------------------------------------------------------- #
def live_trades(market: MT5Market, specs: list[StrategySpec], t0: pd.Timestamp,
                t1: pd.Timestamp) -> dict[int, list[dict]]:
    """magic -> trades (positions) opened or closed in [t0, t1)."""
    import MetaTrader5 as mt5
    magics = {s.magic: s for s in specs}
    deals = market.deals_between(t0 - pd.Timedelta(days=45), t1)
    by_pos: dict[int, dict] = {}
    for d in deals:
        if d.magic not in magics or d.type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
            continue
        p = by_pos.setdefault(d.position_id, dict(magic=d.magic, symbol=d.symbol, entry_time=None,
                                                  exit_time=None, side=None, lots=0.0, entry=None,
                                                  exit=None, pnl=0.0, comment=""))
        t = pd.to_datetime(d.time, unit="s")
        if d.entry == mt5.DEAL_ENTRY_IN:
            p.update(entry_time=t, entry=d.price, lots=p["lots"] + d.volume,
                     side="long" if d.type == mt5.DEAL_TYPE_BUY else "short")
        elif d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT, mt5.DEAL_ENTRY_OUT_BY):
            p.update(exit_time=t, exit=d.price, comment=d.comment)
        p["pnl"] += d.profit + d.swap + d.commission
    out: dict[int, list[dict]] = {}
    for p in by_pos.values():
        in_day = lambda t: t is not None and t0 <= t < t1       # noqa: E731
        if in_day(p["entry_time"]) or in_day(p["exit_time"]):
            out.setdefault(p["magic"], []).append(p)
    for v in out.values():
        v.sort(key=lambda p: (p["entry_time"] or t0))
    return out


# --------------------------------------------------------------------------- #
# backtest side                                                                #
# --------------------------------------------------------------------------- #
def backtest_trades(market: MT5Market, spec: StrategySpec, symbol_map: dict, t0: pd.Timestamp,
                    t1: pd.Timestamp) -> tuple[list[dict], int]:
    bsym = symbol_map.get(spec.symbol, spec.symbol)
    end = t1 - pd.Timedelta(seconds=1)
    df = market.rates_until(bsym, spec.tf, end, WINDOW_BARS)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    pair = conv_pair_for(spec.symbol)
    pair_df = market.rates_until(symbol_map.get(pair[0], pair[0]), spec.tf, end, WINDOW_BARS) if pair else None
    df = attach_conv(df, spec.symbol, pair_df)
    df.attrs.update(symbol=spec.symbol, tf=spec.tf)
    res = H.simulate(df, spec.build(df), risk=spec.risk)
    t = res["trades"]
    rows = []
    if len(t):
        t = t[t.reason != "end"]
        sel = t[((t.entry_time >= t0) & (t.entry_time < t1)) | ((t.exit_time >= t0) & (t.exit_time < t1))]
        for _, r in sel.iterrows():
            rows.append(dict(entry_bar=r.entry_time, exit_bar=r.exit_time, side=r.side, lots=r.lots,
                             entry=r.entry, exit=r.exit, sl0=r.sl0, pnl=r.profit, reason=r.reason))
    return rows, len(df)


# --------------------------------------------------------------------------- #
# report                                                                       #
# --------------------------------------------------------------------------- #
def _fmt_t(t):
    return "-" if t is None or pd.isna(t) else pd.Timestamp(t).strftime("%m-%d %H:%M")


def compare(date: str, market: MT5Market, specs: list[StrategySpec], symbol_map: dict,
            disabled: dict[int, str]) -> dict:
    t0 = pd.Timestamp(date).normalize()
    t1 = t0 + pd.Timedelta(days=1)
    now = market.tick_time(symbol_map.get("EURUSD", "EURUSD"))
    partial = now is not None and now < t1
    live = live_trades(market, specs, t0, t1)
    per = []
    tot_live = tot_bt = 0.0
    n_live = n_bt = 0
    for s in specs:
        log.info("backtest %s", s.name)
        bt, nbars = backtest_trades(market, s, symbol_map, t0, t1)
        lv = live.get(s.magic, [])
        if not bt and not lv:
            continue
        pairs = []
        for k in range(max(len(bt), len(lv))):
            b = bt[k] if k < len(bt) else None
            l = lv[k] if k < len(lv) else None
            pairs.append(dict(
                live=l, bt=b,
                d_entry=(l["entry"] - b["entry"]) if l and b and l["entry"] and b["entry"] else None,
                d_exit=(l["exit"] - b["exit"]) if l and b and l["exit"] and b["exit"] else None,
                d_pnl=(l["pnl"] - b["pnl"]) if l and b else None,
                side_match=(l["side"] == b["side"]) if l and b else None))
        pl = sum(p["pnl"] for p in lv if p["exit_time"] is not None and t0 <= p["exit_time"] < t1)
        pb = sum(b["pnl"] for b in bt if t0 <= b["exit_bar"] < t1)
        tot_live += pl
        tot_bt += pb
        n_live += len(lv)
        n_bt += len(bt)
        per.append(dict(idx=s.idx, name=s.name, disabled=disabled.get(s.idx), bars=nbars,
                        live_n=len(lv), bt_n=len(bt), live_pnl=pl, bt_pnl=pb, pairs=pairs))
    equity, balance = market.account()
    return dict(date=date, partial=partial, per_strategy=per, live_trades=n_live, bt_trades=n_bt,
                live_pnl=tot_live, bt_pnl=tot_bt, equity=equity, balance=balance,
                disabled=len(disabled), strategies=len(specs))


def render(rep: dict, full: bool = True) -> str:
    L = [f"\U0001F4CA demo vs backtest — server day {rep['date']}" + (" (DAY NOT OVER YET)" if rep["partial"] else ""),
         f"live: {rep['live_trades']} trades, realised {rep['live_pnl']:+.2f} | backtest: {rep['bt_trades']} trades, "
         f"{rep['bt_pnl']:+.2f} | diff {rep['live_pnl'] - rep['bt_pnl']:+.2f}",
         f"account now: equity {rep['equity']:.2f} balance {rep['balance']:.2f} | "
         f"{rep['strategies'] - rep['disabled']}/{rep['strategies']} strategies live"]
    if not rep["per_strategy"]:
        L.append("no trades on either side.")
    for s in rep["per_strategy"]:
        tag = " [NOT TRADED LIVE: " + s["disabled"] + "]" if s["disabled"] else ""
        L.append(f"\n{s['name']}{tag}: live {s['live_n']} ({s['live_pnl']:+.2f}) vs backtest {s['bt_n']} "
                 f"({s['bt_pnl']:+.2f})")
        if not full:
            continue
        for p in s["pairs"]:
            l, b = p["live"], p["bt"]
            ls = (f"live {l['side']} {l['lots']:.2f} in {_fmt_t(l['entry_time'])} @ {l['entry']:.5g} "
                  f"out {_fmt_t(l['exit_time'])} @ {l['exit'] if l['exit'] else '-'} pnl {l['pnl']:+.2f}") if l else "live: (none)"
            bs = (f"bt {b['side']} {b['lots']:.2f} in {_fmt_t(b['entry_bar'])}bar @ {b['entry']:.5g} "
                  f"out {_fmt_t(b['exit_bar'])} @ {b['exit']:.5g} ({b['reason']}) pnl {b['pnl']:+.2f}") if b else "bt: (none)"
            d = ""
            if l and b:
                d = (f" | Δentry {p['d_entry']:+.5g}" if p["d_entry"] is not None else "") + \
                    (f" Δexit {p['d_exit']:+.5g}" if p["d_exit"] is not None else "") + \
                    f" ΔP&L {p['d_pnl']:+.2f}" + ("" if p["side_match"] else " SIDE MISMATCH")
            L.append(f"   {ls}\n   {bs}{d}")
    L.append("\nnotes: entry bar = open time of the bar whose close triggered the trade; a backtest "
             "trade with no live twin that started before the bot was running is expected; live P&L "
             "includes broker commission/swap, backtest reserves $14/lot and a 0.1-pip slip.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="server day YYYY-MM-DD (default: yesterday, broker time)")
    ap.add_argument("--telegram", action="store_true", help="send the summary to Telegram")
    ap.add_argument("--mix", default=str(MIX_PATH))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    mt5_market.connect(CONFIG)
    try:
        market = MT5Market()
        specs = load_mix(a.mix)
        symbol_map = load_symbol_map()
        _, problems = mt5_market.preflight([s.symbol for s in specs], symbol_map)
        disabled = {s.idx: problems[s.symbol] for s in specs if s.symbol in problems}
        date = a.date
        if not date:
            now = market.tick_time(symbol_map.get("EURUSD", "EURUSD")) or pd.Timestamp.utcnow().tz_localize(None)
            date = str((now.normalize() - pd.Timedelta(days=1)).date())
        rep = compare(date, market, specs, symbol_map, disabled)
    finally:
        mt5_market.shutdown()
    text = render(rep, full=True)
    print(text)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{date}.txt").write_text(text, encoding="utf-8")
    (OUT / f"{date}.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    if a.telegram:
        short = render(rep, full=False)
        if len(short) > 3800:
            short = short[:3700] + "\n… (full report in logs/compare/)"
        send_alert(CONFIG, short)
        detail = text if len(text) <= 3800 else text[:3700] + "\n… (truncated; see logs/compare/)"
        if detail != short:
            send_alert(CONFIG, detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())

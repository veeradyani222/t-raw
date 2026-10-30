"""Parameter sweeps for the oil_gas group. Usage:
    python research/search3/oil_gas/search.py [block ...]
Blocks: calendar report orb session gap spread trend reversion levels intraday night misc
Every scored run is appended to runs.jsonl (common.log_run)."""
from __future__ import annotations
import sys, itertools, traceback
from research.search3.oil_gas import common as C
from research.search3.oil_gas import strategies as S

OIL = ("XTIUSD", "XBRUSD")
ALL = ("XTIUSD", "XBRUSD", "XNGUSD")


def grid(**kw):
    keys = list(kw)
    for vals in itertools.product(*kw.values()):
        yield dict(zip(keys, vals))


def sweep(block, syms, tfs, fn_name, grids, tag=None):
    build = getattr(S, fn_name)
    n = 0
    for sym in syms:
        for tf in tfs:
            try:
                df, _ = C.load(sym, tf)
            except FileNotFoundError:
                print("missing", sym, tf); continue
            for p in grids:
                name = f"{tag or fn_name[6:]}:" + ",".join(f"{k}={v}" for k, v in p.items())
                try:
                    C.run(df, build, fn_name, name[:120], **p); n += 1
                except Exception as e:
                    print("ERR", name, sym, tf, e); traceback.print_exc()
    return n


BLOCKS = {}
def block(name):
    def deco(f):
        BLOCKS[name] = f; return f
    return deco


@block("calendar")
def _calendar():
    n = 0
    # Thursday effect: long Wed close (D1) / Wed 23:00 (H1), various holds; also Fri
    n += sweep("calendar", ALL, ["D1"], "build_weekday_hold",
               list(grid(enter_wd=[2, 3, 4, 0], hold_bars=[1, 2], side=["long", "short"], sl_atr=[1.5, 2.5])))
    n += sweep("calendar", ALL, ["H1"], "build_weekday_hold",
               list(grid(enter_wd=[2, 3], enter_hour=[23, 16, 10], hold_bars=[23, 46], side=["long"], sl_atr=[2.0, 3.0]))
               + list(grid(enter_wd=[0, 4], enter_hour=[23, 16], hold_bars=[23], side=["short"], sl_atr=[2.0])))
    n += sweep("calendar", ALL, ["D1"], "build_week_structure",
               list(grid(short_wd=[0, 4], short_hold=[1, 2], long_wd=[2, 3], long_hold=[1, 2], sl_atr=[2.0, 3.0]))
               + [dict(use_short=False, long_wd=2, long_hold=2, sl_atr=2.0), dict(use_long=False, short_wd=0, short_hold=2, sl_atr=2.0)])
    return n


@block("report")
def _report():
    n = 0
    for sym, wd in (("XTIUSD", 2), ("XBRUSD", 2), ("XNGUSD", 3)):
        n += sweep("report", [sym], ["M30", "H1"], "build_report_momentum",
                   list(grid(report_wd=[wd], exit_hour=[21, 23], sl_atr=[1.0, 1.5, 2.5], min_move_atr=[0.0, 0.5], direction=["follow", "fade"])))
        n += sweep("report", [sym], ["M30", "H1"], "build_report_breakout",
                   list(grid(report_wd=[wd], pre_bars=[4, 8], window_bars=[4, 8], sl_mode=["range", "atr"], tp_r=[1.5, 2.5], exit_hour=[21, 23])))
    # crude also reacts to the Thursday gas number? and gas to Wed EIA (petroleum) -> cross test
    n += sweep("report", OIL, ["M30"], "build_report_momentum", list(grid(report_wd=[3], exit_hour=[21], sl_atr=[1.5], direction=["follow", "fade"])))
    n += sweep("report", ["XNGUSD"], ["M30"], "build_report_momentum", list(grid(report_wd=[2], exit_hour=[21], sl_atr=[1.5], direction=["follow", "fade"])))
    return n


@block("orb")
def _orb():
    n = 0
    n += sweep("orb", ALL, ["M30"], "build_pit_orb",
               list(grid(open_hour=[16], range_bars=[1, 2, 3], cutoff_hour=[19, 21], sl_mode=["mid", "range", "atr"], tp_r=[1.5, 2.5, 4.0], exit_hour=[23])))
    n += sweep("orb", ALL, ["H1"], "build_pit_orb",
               list(grid(open_hour=[16, 10], range_bars=[1, 2], cutoff_hour=[20], sl_mode=["mid", "atr"], tp_r=[1.5, 3.0], exit_hour=[23])))
    return n


@block("session")
def _session():
    return sweep("session", ALL, ["M30", "H1"], "build_session_range_break",
                 list(grid(range_start=[1, 3, 10], range_end=[15], trade_start=[16], trade_end=[19, 21],
                           sl_mode=["mid", "atr"], tp_r=[1.0, 2.0, 3.0], exit_hour=[23])))


@block("gap")
def _gap():
    return sweep("gap", ALL, ["M30", "H1"], "build_gap",
                 list(grid(mode=["fade", "follow"], min_gap_atr=[0.15, 0.3, 0.5], max_gap_atr=[2.0], sl_atr=[1.0, 2.0],
                           exit_hour=[10, 16, 21])))


@block("spread")
def _spread():
    n = 0
    n += sweep("spread", ["XTIUSD"], ["H1", "H4"], "build_spread_reversion",
               list(grid(other=["XBRUSD"], lookback=[100, 200, 400], z_in=[1.5, 2.0, 2.5], z_out=[0.0, 0.5], sl_atr=[2.0, 3.0], max_hold=[48, 120], mode=["ratio", "diff"])))
    n += sweep("spread", ["XBRUSD"], ["H1", "H4"], "build_spread_reversion",
               list(grid(other=["XTIUSD"], lookback=[200, 400], z_in=[2.0, 2.5], z_out=[0.0], sl_atr=[2.5], max_hold=[72], mode=["ratio", "diff"])))
    return n


@block("trend")
def _trend():
    n = 0
    n += sweep("trend", ALL, ["H1", "H4", "D1"], "build_donchian",
               list(grid(n=[20, 55, 160], trail_atr=[2.0, 3.0, 5.0], sl_atr=[2.0], side=["both"])))
    n += sweep("trend", ALL, ["H4", "D1"], "build_donchian", list(grid(n=[55, 160], trail_atr=[3.0], sl_atr=[2.0], side=["long", "short"])))
    n += sweep("trend", ALL, ["H4", "D1"], "build_ema_pullback",
               list(grid(fast=[10, 20], slow=[50, 100], sl_atr=[1.5, 2.5], trail_atr=[2.5, 4.0], side=["both"])))
    n += sweep("trend", ALL, ["D1"], "build_tsmom",
               list(grid(mom_n=[10, 20, 60, 120], vol_filter=["none", "low", "high"], hold=[1, 5], sl_atr=[2.0, 3.5], side=["both"])))
    n += sweep("trend", ALL, ["H4"], "build_squeeze",
               list(grid(bb_n=[20], bw_lookback=[120, 250], bw_pct=[0.15, 0.3], trail_atr=[2.5, 4.0], sl_atr=[2.0])))
    n += sweep("trend", ALL, ["D1"], "build_squeeze", list(grid(bb_n=[20], bw_lookback=[60, 120], bw_pct=[0.2, 0.35], trail_atr=[3.0], sl_atr=[2.0])))
    return n


@block("reversion")
def _reversion():
    n = 0
    n += sweep("reversion", ALL, ["H4", "D1"], "build_trend_pullback",
               list(grid(ma_n=[100, 200], rsi_n=[2], rsi_lo=[10, 20], rsi_hi=[80, 90], sl_atr=[2.0, 3.0], max_hold=[4, 8], side=["both"])))
    n += sweep("reversion", ALL, ["D1"], "build_trend_pullback", list(grid(ma_n=[100], rsi_n=[2], rsi_lo=[10], rsi_hi=[90], sl_atr=[2.5], max_hold=[6], side=["long", "short"])))
    n += sweep("reversion", ALL, ["H1", "H4", "D1"], "build_rsi_reversion",
               list(grid(rsi_n=[2, 14], lo=[15, 25], hi=[75, 85], sl_atr=[2.5], max_hold=[12, 40], side=["both"])))
    n += sweep("reversion", ["XNGUSD"], ["H4", "D1"], "build_rsi_reversion", list(grid(rsi_n=[5, 14], lo=[20], hi=[80], sl_atr=[2.5], max_hold=[20], side=["short", "long"])))
    return n


@block("levels")
def _levels():
    n = 0
    n += sweep("levels", ALL, ["M30", "H1"], "build_pdhl_sweep",
               list(grid(trade_start=[10, 16], trade_end=[21], tp_mode=["mid", "r"], tp_r=[1.5, 2.5], sl_buf_atr=[0.1, 0.3], exit_hour=[23], level=["day", "week"])))
    n += sweep("levels", ALL, ["M30", "H1"], "build_nr_breakout",
               list(grid(nr_n=[4, 7], sl_mode=["range", "mid", "atr"], tp_r=[1.5, 3.0], exit_hour=[23], inside_only=[False, True])))
    for sym, step in (("XTIUSD", 1.0), ("XBRUSD", 1.0), ("XNGUSD", 0.1)):
        n += sweep("levels", [sym], ["M30", "H1"], "build_round_number",
                   list(grid(step=[step], buf=[0.2], sl_atr=[1.0, 1.5], tp_r=[1.0, 2.0], mode=["bounce", "break"], trade_start=[16], exit_hour=[23])))
    return n


@block("intraday")
def _intraday():
    n = 0
    n += sweep("intraday", ALL, ["H1"], "build_intraday_momentum",
               list(grid(signal_hour=[17, 19, 20], exit_hour=[21, 23], ref=["dopen"], sl_atr=[1.0, 2.0], min_move_atr=[0.0, 0.5], direction=["follow", "fade"])))
    n += sweep("intraday", ALL, ["H1"], "build_time_drift",
               list(grid(enter_hour=[1, 10, 16, 18], exit_hour=[10, 16, 21, 23], side=["long", "short"], sl_atr=[1.5])))
    n += sweep("intraday", ALL, ["H1"], "build_london_fade",
               list(grid(london_hour=[10, 11], exit_hour=[16], min_move_atr=[0.3, 0.7], sl_atr=[1.0, 2.0], direction=["fade", "follow"])))
    return n


@block("night")
def _night():
    return sweep("night", ALL, ["H1"], "build_settlement_overnight",
                 list(grid(settle_hour=[21, 23], exit_hour=[10, 16], ref=["dopen", "pc"], direction=["follow", "fade"], sl_atr=[1.0, 2.0], min_move_atr=[0.0, 0.5])))


if __name__ == "__main__":
    want = sys.argv[1:] or list(BLOCKS)
    tot = 0
    for b in want:
        print(f"\n===== {b} =====", flush=True)
        tot += BLOCKS[b]()
    print("\nscored runs:", tot)

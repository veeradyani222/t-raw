"""Second sweep for oil_gas: ideas added after the market study (settlement-bar
drift, afternoon weakness, gas Wed/Thu shape, EIA fade with targets, MA cross,
prior-day H/L breakout, inside bar, big-bar fade). Usage like search.py."""
from __future__ import annotations
import sys
from research.search3.oil_gas.search import sweep, grid, ALL, OIL, BLOCKS, block


@block("drift2")
def _drift2():
    n = 0
    # settlement bar 21:00 is +5..9bp on all three symbols; 14-16h negative
    n += sweep("drift2", ALL, ["H1"], "build_time_drift",
               list(grid(enter_hour=[20, 21], exit_hour=[22, 23], side=["long", "short"], sl_atr=[1.0, 2.0]))
               + list(grid(enter_hour=[13, 14], exit_hour=[16, 17], side=["short", "long"], sl_atr=[1.0, 2.0]))
               + list(grid(enter_hour=[16, 17], exit_hour=[19], side=["long"], sl_atr=[1.0, 2.0])))
    n += sweep("drift2", ALL, ["H1"], "build_time_drift",
               list(grid(enter_hour=[21], exit_hour=[23], side=["long"], sl_atr=[1.5], weekdays=[(2, 3), (3,), (0, 1, 2, 3)])))
    n += sweep("drift2", ALL, ["H1"], "build_intraday_momentum",
               list(grid(signal_hour=[21], exit_hour=[23], ref=["dopen", "pc"], sl_atr=[1.0, 2.0], min_move_atr=[0.0, 0.5], direction=["follow"])))
    return n


@block("calendar2")
def _calendar2():
    n = 0
    n += sweep("calendar2", ["XNGUSD"], ["D1"], "build_weekday_hold",
               list(grid(enter_wd=[1, 2], hold_bars=[1], side=["long", "short"], sl_atr=[1.5, 2.5, 4.0], tp_r=[None, 1.0])))
    n += sweep("calendar2", OIL, ["D1"], "build_weekday_hold",
               list(grid(enter_wd=[2], hold_bars=[1, 2], side=["long"], sl_atr=[1.0, 1.5, 2.5, 4.0], tp_r=[None, 1.0, 2.0])))
    n += sweep("calendar2", ["XNGUSD"], ["D1"], "build_week_structure",
               list(grid(short_wd=[2], short_hold=[1], long_wd=[1], long_hold=[1], sl_atr=[2.0, 3.0])))
    n += sweep("calendar2", OIL, ["H1"], "build_weekday_hold",
               list(grid(enter_wd=[2], enter_hour=[21, 23], hold_bars=[16, 20, 23], side=["long"], sl_atr=[1.5, 2.5])))
    return n


@block("report2")
def _report2():
    n = 0
    for sym, wd in (("XTIUSD", 2), ("XBRUSD", 2), ("XNGUSD", 3)):
        n += sweep("report2", [sym], ["M30", "H1"], "build_report_momentum",
                   list(grid(report_wd=[wd], exit_hour=[19, 21, 23], sl_atr=[1.0, 1.5, 2.0], min_move_atr=[0.3, 0.6, 1.0], tp_r=[None, 1.0, 1.5], direction=["fade"])))
    n += sweep("report2", ["XNGUSD"], ["M30", "H1"], "build_report_momentum",
               list(grid(report_wd=[2], exit_hour=[21, 23], sl_atr=[1.0, 1.5], min_move_atr=[0.3, 0.6], tp_r=[None, 1.0], direction=["fade"])))
    return n


@block("macross")
def _macross():
    n = 0
    n += sweep("macross", ALL, ["M30", "H1"], "build_ma_cross",
               list(grid(fast=[15, 30], slow=[70, 140], sl_atr=[1.5, 3.0], tp_r=[None, 3.0], trail_atr=[None, 3.0])))
    n += sweep("macross", ALL, ["H4", "D1"], "build_ma_cross",
               list(grid(fast=[5, 10, 20], slow=[30, 50, 100], sl_atr=[2.0, 3.0], trail_atr=[None, 3.0])))
    return n


@block("levels2")
def _levels2():
    n = 0
    n += sweep("levels2", ALL, ["M30", "H1"], "build_pdhl_breakout",
               list(grid(trade_start=[10, 16], trade_end=[19, 21], sl_mode=["mid", "atr"], sl_atr=[1.0], tp_r=[1.5, 2.5, 4.0], exit_hour=[23], level=["day", "week"], min_dist_atr=[0.0, 0.2])))
    n += sweep("levels2", ALL, ["H4", "D1"], "build_inside_bar",
               list(grid(sl_mode=["range", "atr"], sl_atr=[1.5], tp_r=[1.5, 2.5, 4.0], max_hold=[4, 10])))
    n += sweep("levels2", ALL, ["D1"], "build_close_fade",
               list(grid(min_move_atr=[1.0, 1.5, 2.0], sl_atr=[1.5, 2.5], max_hold=[1, 2, 4], tp_r=[None, 1.0], side=["both"])))
    n += sweep("levels2", ALL, ["H4"], "build_close_fade",
               list(grid(min_move_atr=[1.5, 2.0], sl_atr=[2.0], max_hold=[2, 6], side=["both"])))
    return n


if __name__ == "__main__":
    want = sys.argv[1:] or ["drift2", "calendar2", "report2", "macross", "levels2"]
    tot = 0
    for b in want:
        print(f"\n===== {b} =====", flush=True)
        tot += BLOCKS[b]()
    print("\nscored runs:", tot)

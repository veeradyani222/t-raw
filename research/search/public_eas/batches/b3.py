"""Batch 3: neighbourhoods of the b2 leaders + trend/side fixes."""
from research.search.public_eas.run import run
JPY = ["USDJPY","EURJPY","GBPJPY","AUDJPY","CHFJPY","NZDJPY","CADJPY"]
def lab(b, tf, p): return f"{b}_{tf}_" + "_".join(f"{k}{v}" for k, v in p.items())
jobs = []
def add(b, tf, p, syms):
    for s in syms: jobs.append((lab(b, tf, p), b, s, tf, p))
# BB breakout gold neighbourhood
for per in (150, 200, 250):
    for dev in (2.25, 2.5, 2.75, 3.0):
        if (per, dev) != (200, 2.5) or True:
            add("bb_breakout", "H1", {"period": per, "dev": dev}, ["XAUUSD"])
for sl, tp in [(1.0, 2.5), (2.0, 5.0), (1.5, 2.0), (1.5, 6.0)]:
    add("bb_breakout", "H1", {"dev": 2.5, "sl": sl, "tp": tp}, ["XAUUSD"])
add("bb_breakout", "H1", {"dev": 2.5}, ["XAGUSD","US500","US30","DE40"] + JPY + ["EURUSD","GBPUSD","AUDUSD"])
add("bb_breakout", "H4", {"dev": 2.5}, ["XAUUSD","XAGUSD","USDJPY"])
add("bb_breakout", "M30", {"dev": 2.5}, ["XAUUSD"])
add("filtered", "H1", {"base": "bb_breakout", "dev": 2.5, "side": "long"}, ["XAUUSD"])
add("filtered", "H1", {"base": "bb_breakout", "dev": 2.5, "trend_n": 1000}, ["XAUUSD","USDJPY","GBPJPY"])
# weekly breakout on JPY crosses
add("weekly_breakout", "H1", {}, ["CHFJPY","NZDJPY","CADJPY"])
add("weekly_breakout", "H1", {"period": "D"}, ["AUDJPY","GBPJPY","EURJPY"])
add("weekly_breakout", "H1", {"fri_hour": 16}, ["AUDJPY","GBPJPY","XAUUSD"])
add("weekly_breakout", "H1", {"sl_mode": "atr", "sl": 3.0}, ["AUDJPY","GBPJPY"])
add("weekly_breakout", "H1", {"side": "long"}, ["AUDJPY","GBPJPY"])
add("weekly_breakout", "H1", {"side": "short"}, ["AUDJPY","GBPJPY"])
add("filtered", "H1", {"base": "weekly_breakout", "trend_n": 1000}, ["XAUUSD","AUDJPY","GBPJPY","EURJPY","USDJPY"])
# picky breakout JPY crosses
add("picky_breakout", "D1", {}, ["CHFJPY","NZDJPY","CADJPY"])
for p in [{"lookup": 5}, {"lookup": 12}, {"hold": 3}, {"hold": 8}, {"sl": 3.0}]:
    add("picky_breakout", "D1", p, ["GBPJPY","AUDJPY"])
# Connors on US500 neighbourhood
for p in [{"buy_lvl": 3, "sell_lvl": 97}, {"exit_n": 3}, {"exit_n": 10}, {"sl": 3.0}, {"trend_n": 100}, {"rsi_n": 3}]:
    add("connors_rsi2", "D1", p, ["US500","GBPUSD","NZDUSD"])
if __name__ == "__main__":
    run(jobs, procs=4, tag="b3")

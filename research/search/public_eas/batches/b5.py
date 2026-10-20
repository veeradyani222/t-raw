"""Batch 5: neighbourhoods of the 3 survivors + cost stress."""
from research.search.public_eas.run import run
def lab(b, tf, p): return f"{b}_{tf}_" + "_".join(f"{k}{v}" for k, v in p.items())
jobs = []
def add(b, tf, p, syms):
    for s in syms: jobs.append((lab(b, tf, p), b, s, tf, p))
F = "filtered"
base = {"base": "bb_breakout", "dev": 2.25, "trend_n": 1000}
for sl, tp in [(1.25, 3.1), (1.5, 3.0), (1.5, 4.5), (2.0, 5.0), (1.0, 3.75)]:
    add(F, "H1", {**base, "sl": sl, "tp": tp}, ["XAUUSD"])
for per in (150, 250):
    add(F, "H1", {**base, "period": per}, ["XAUUSD"])
for tn in (750, 1500):
    add(F, "H1", {**base, "trend_n": tn}, ["XAUUSD"])
add(F, "H1", {**base, "dev": 2.0}, ["XAUUSD"])
add(F, "H1", {**base, "_spread": 2.0}, ["XAUUSD"])
add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "_spread": 2.0}, ["XAUUSD"])
add(F, "H1", {**base}, ["XAGUSD", "USDJPY", "GBPJPY", "EURUSD", "US30", "DE40"])
add(F, "H4", {**base, "trend_n": 250}, ["XAUUSD"])
cr = {"trend_n": 1200}
add("connors_rsi2", "H4", cr, ["EURUSD", "USDCAD", "AUDUSD"])
for p in [{"buy_lvl": 10, "sell_lvl": 90}, {"exit_n": 10}, {"trend_n": 600}, {"trend_n": 2400}, {"sl": 3.0}, {"_spread": 2.0}]:
    add("connors_rsi2", "H4", {**cr, **p}, ["GBPUSD"])
add("connors_rsi2", "H1", {"trend_n": 4800}, ["GBPUSD", "EURGBP", "EURUSD"])
add("connors_rsi2", "D1", {"_spread": 2.0}, ["GBPUSD"])
add("turtle", "D1", {"side": "long", "entry_n": 55, "exit_n": 20}, ["US500", "US30", "DE40"])
add("turtle", "D1", {"side": "long"}, ["US30", "DE40"])
if __name__ == "__main__":
    run(jobs, procs=4, tag="b5")

"""Batch 4: remaining EAs on other TFs/symbols + gold BB fixes."""
from research.search.public_eas.run import run
def lab(b, tf, p): return f"{b}_{tf}_" + "_".join(f"{k}{v}" for k, v in p.items())
jobs = []
def add(b, tf, p, syms):
    for s in syms: jobs.append((lab(b, tf, p), b, s, tf, p))
F = "filtered"
for h in [(12, 19), (13, 20), (8, 20)]:
    add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "hours": h}, ["XAUUSD"])
    add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "hours": h, "trend_n": 1000}, ["XAUUSD"])
for tn in (500, 2000):
    add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "trend_n": tn}, ["XAUUSD"])
for dev in (2.25, 2.75):
    add(F, "H1", {"base": "bb_breakout", "dev": dev, "trend_n": 1000}, ["XAUUSD"])
add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "trend_n": 1000, "sl": 1.5, "tp": 2.5}, ["XAUUSD"])
add(F, "H1", {"base": "bb_breakout", "dev": 2.5, "trend_n": 1000}, ["XAGUSD", "US500", "DE40", "AUDJPY"])
add("turtle", "H4", {}, ["XAUUSD", "USDJPY", "GBPJPY"])
add("turtle", "H4", {"entry_n": 55, "exit_n": 20}, ["XAUUSD", "USDJPY"])
add("turtle", "D1", {}, ["GBPJPY", "AUDJPY", "US500", "XAGUSD"])
add("turtle", "D1", {"side": "long"}, ["XAUUSD", "US500"])
add("ichimoku_chikou", "H4", {}, ["XAUUSD", "USDJPY"])
add("ichimoku_chikou", "D1", {}, ["GBPJPY", "AUDJPY", "EURJPY", "US500", "XAGUSD"])
for p in [{"pct": 0.002}, {"pct": 0.005}, {"bars": 2}, {"bars": 5}, {"sl_mode": "atr", "sl": 2.0}]:
    add("spike_trader", "D1", p, ["XAUUSD"])
add("spike_trader", "D1", {}, ["AUDJPY", "GBPJPY", "US500", "XAGUSD"])
add("macd_sample", "H4", {}, ["XAGUSD", "AUDUSD", "USDCAD", "NZDUSD"])
add("macd_sample", "H4", {"use_trail": False}, ["USDJPY", "XAUUSD"])
add("macd_sample", "D1", {}, ["USDJPY", "XAUUSD", "GBPJPY"])
add("persistent_anti", "D1", {}, ["XAUUSD", "USDJPY", "GBPUSD"])
add("persistent_anti", "W1", {"reverse": False}, ["XAUUSD", "USDJPY"])
add("connors_rsi2", "H4", {"trend_n": 1200}, ["GBPUSD", "XAUUSD", "NZDUSD", "USDJPY"])
add("alligator", "D1", {}, ["XAUUSD", "USDJPY", "GBPJPY"])
add("alligator", "H4", {}, ["XAUUSD", "USDJPY"])
add("moving_average", "D1", {}, ["XAUUSD", "USDJPY", "GBPUSD", "GBPJPY"])
for pat, osc in [("hammer", "rsi"), ("engulfing", "rsi"), ("soldiers", "cci"), ("harami", "stoch")]:
    add("free_robot", "H4", {"pattern": pat, "osc": osc}, ["XAUUSD", "USDJPY"])
    add("free_robot", "D1", {"pattern": pat, "osc": osc}, ["XAUUSD"])
if __name__ == "__main__":
    run(jobs, procs=4, tag="b4")

"""Batch 2: cross-symbol sweep of the less-bad defaults + Free Robots matrix + neighbours."""
from research.search.public_eas.run import run
ALL = ["XAUUSD","XAGUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF","EURJPY","GBPJPY",
       "AUDJPY","CHFJPY","NZDJPY","CADJPY","EURGBP","EURCHF","GBPCHF","AUDCAD","US30","US500","USTEC","DE40"]
OTHERS = ["XAGUSD","US30","US500","USTEC","DE40","EURJPY","GBPJPY","AUDJPY"]
def lab(b, tf, p): return f"{b}_{tf}_" + "_".join(f"{k}{v}" for k, v in p.items())
jobs = []
def add(b, tf, p, syms):
    for s in syms: jobs.append((lab(b, tf, p), b, s, tf, p))
add("connors_rsi2", "D1", {}, [s for s in ALL if s not in ("EURUSD","GBPUSD","USDJPY","XAUUSD")])
add("connors_rsi2", "D1", {"side": "long"}, ["US30","US500","USTEC","DE40","XAUUSD"])
add("connors_rsi2", "D1", {"buy_lvl": 10, "sell_lvl": 90}, ["GBPUSD","EURUSD","US500","XAUUSD"])
add("connors_rsi2", "H4", {}, ["XAUUSD","GBPUSD","EURUSD","USDJPY"])
for pat in ["engulfing","harami","hammer","star","soldiers","darkcloud","meetinglines"]:
    for osc in ["rsi","cci","mfi","stoch"]:
        add("free_robot", "H1", {"pattern": pat, "osc": osc}, ["XAUUSD"])
add("weekly_breakout", "H1", {}, OTHERS)
add("weekly_breakout", "H1", {"side": "long"}, ["XAUUSD"])
add("weekly_breakout", "H1", {"sl_mode": "atr", "sl": 3.0}, ["XAUUSD","USDJPY"])
add("weekly_breakout", "H1", {"period": "D"}, ["XAUUSD","USDJPY","US500"])
add("bb_breakout", "H1", {}, OTHERS)
for per, dev in [(100, 2.0), (300, 2.0), (200, 1.5), (200, 2.5)]:
    add("bb_breakout", "H1", {"period": per, "dev": dev}, ["XAUUSD"])
add("picky_breakout", "D1", {}, OTHERS)
for p in [{"lookup": 5}, {"lookup": 12}, {"hold": 3}, {"hold": 8}, {"days": (0,1,2,3,4)}]:
    add("picky_breakout", "D1", p, ["XAUUSD"])
if __name__ == "__main__":
    run(jobs, procs=4, tag="b2")

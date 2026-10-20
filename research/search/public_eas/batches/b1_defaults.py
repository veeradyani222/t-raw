"""Batch 1: every EA at source defaults on its native-ish TF, 4 symbols."""
from research.search.public_eas.run import run
SYMS = ["XAUUSD", "USDJPY", "EURUSD", "GBPUSD"]
plan = [
    ("macd_sample", "H4", {}), ("macd_sample", "H1", {}),
    ("moving_average", "H1", {}), ("moving_average", "H4", {}),
    ("free_robot", "H1", {"pattern": "engulfing", "osc": "rsi"}),
    ("spike_trader", "D1", {}),
    ("ichimoku_chikou", "D1", {}),
    ("weekly_breakout", "H1", {}),
    ("bb_breakout", "H1", {}),
    ("picky_breakout", "D1", {}),
    ("persistent_anti", "W1", {}),
    ("turtle", "D1", {}), ("turtle", "D1", {"entry_n": 55, "exit_n": 20}),
    ("connors_rsi2", "D1", {}),
    ("alligator", "H1", {}),
]
jobs = [(f"{b}_{tf}_{'_'.join(f'{k}{v}' for k,v in p.items())}", b, s, tf, p)
        for b, tf, p in plan for s in SYMS]
if __name__ == "__main__":
    run(jobs, tag="b1")

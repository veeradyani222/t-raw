"""Simulate every portfolio candidate at every harness risk level on IS and OOS.
Saves curves + trades to _cache/<name>-<split>.pkl. PROP_OOS=1 is set here
(portfolio/report stage is allowed to read OOS)."""
import os, sys, pickle, importlib
from pathlib import Path
os.environ["PROP_OOS"] = "1"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.prop import harness as H

CANDS = {
    # survivors (passed OOS verify AND skeptic)
    "de40_orb": dict(sym="DE40", tf="M30", mod="research.search.breakout.strategies",
                     fn="build_de40_xetra_orb",
                     p={"rs": 10, "re": 10.5, "te": 12.5, "exit_h": 18, "sl_frac": 0.75,
                        "trend": "d", "min_rng": 0.1, "tp_r": None}, survivor=True),
    "gold_bb": dict(sym="XAUUSD", tf="H1", mod="research.search.public_eas.strategies",
                    fn="build_filtered", p={"base": "bb_breakout", "dev": 2.25, "trend_n": 1000},
                    survivor=True),
    "gold_cal": dict(sym="XAUUSD", tf="H1", mod="research.search.published_research.strategies",
                     fn="build_gold_calendar", p={"tom_days_before": 0, "tom_hold": 4, "fomc_sl": 1.5},
                     survivor=True),
    # sensitivity only: passed OOS verify but REFUTED by skeptic (edge = gold beta)
    "gold_bos_long": dict(sym="XAUUSD", tf="M30", mod="research.search.gold_fix.strategies",
                          fn="build_bos_fixed_long", p={"atrp_min": 0.6, "tp_min_r": 2.0, "htf": ("1D", 100)},
                          survivor=False),
}

def run(name):
    c = CANDS[name]
    build = getattr(importlib.import_module(c["mod"]), c["fn"])
    out = Path(__file__).parent / "_cache"; out.mkdir(exist_ok=True)
    for split in ("is", "oos"):
        f = out / f"{name}-{split}.pkl"
        if f.exists():
            continue
        df = H.load(c["sym"], c["tf"], split=split)
        sigs = build(df, **c["p"])
        res = {}
        for r in H.RISKS:
            for sm in (1.0, 2.0):
                s = H.simulate(df, sigs, risk=r, spread_mult=sm)
                t = s["trades"]
                keep = [k for k in ("entry_time", "exit_time", "side", "profit", "r", "lots", "reason") if k in t]
                tt = t[keep].copy() if len(t) else t
                if len(t):
                    # risk at entry = r * loss/lot recomputed: profit/r
                    tt["risk_usd"] = (t["profit"] / t["r"]).abs()
                res[(r, sm)] = dict(curve=s["curve"], trades=tt)
        pickle.dump(dict(meta=c, score_from=df.attrs.get("score_from"), res=res), open(f, "wb"))
        print("saved", f.name, flush=True)

if __name__ == "__main__":
    for n in (sys.argv[1:] or CANDS):
        run(n)

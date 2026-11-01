"""Round-5 candidate pool = round-3 pool (146) + round-4 price-action survivors (16, picked on
data before 2023-10-20 only) + two time-of-day holds from the round-5 session scan (weak,
carried for the record). Extras get stable indices 146.. so the full-history cache works."""
import os, sys, json
sys.path.insert(0, os.getcwd())
from research.search2.portfolio import core as P
from research.search3.portfolio.round3w import MGROUP
from research.search5 import core5 as K

HERE = os.path.dirname(os.path.abspath(__file__))
CROSS_SYMBOL = {"build_spread_reversion", "build_ratio_z", "build_lag_catchup"}   # need a second market's bars: cannot run live

TOD = [dict(symbol="FRA40", side="long", h_in=6, h_out=12), dict(symbol="EURCHF", side="long", h_in=0, h_out=8)]


def extras():
    out = []
    for s in json.load(open(os.path.join(HERE, "round4_survivors.json"))):
        out.append(dict(name=f"pa_{s['fam']}_{s['symbol']}_{s['tf']}", symbol=s["symbol"], tf=s["tf"],
                        module="research.search4.price_action.strategies", fn=f"build_{s['fam']}", params=s["params"],
                        group=MGROUP.get(s["symbol"], "live"), family="pa_" + s["fam"], src="round4"))
    for t in TOD:
        out.append(dict(name=f"tod_{t['side']}_{t['h_in']}-{t['h_out']}", symbol=t["symbol"], tf="H1",
                        module="research.search3.metals.strategies", fn="build_session_hold",
                        params=dict(side=t["side"], h_in=t["h_in"], h_out=t["h_out"], stop_atr=3.0, max_hold=30),
                        group=MGROUP.get(t["symbol"], "live"), family="r5_tod", src="r5_tod"))
    return out


def build_pool():
    pool = K.build_pool()
    n = len(pool)
    for j, x in enumerate(extras()):
        x["key"] = P.keyof(x); x["i"] = n + j; x["mixes"] = []; x["live_risk"] = None; x["mgroup"] = MGROUP.get(x["symbol"], "other")
        pool.append(x)
    for x in pool:
        x["runs_live"] = x["fn"] not in CROSS_SYMBOL and x["symbol"] not in K.NOT_OFFERED
    return pool


if __name__ == "__main__":
    pool = build_pool()
    print(len(pool), "strategies;", sum(not x["runs_live"] for x in pool), "cannot run live")
    K.build_cache(pool)

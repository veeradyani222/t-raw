"""Round 6 step 4: judge every extracted spec on ITS OWN market and timeframe, full history at 1%,
with the round-5 judge (dev 2015..2023-10-20 / unseen yr / last 2y / Sep+Oct). Writes out/spec_stats.csv
and out/spec_results.md.

    cd mt5-trader && python -m research.search6.run_specs out/specs.json
"""
import os, sys, json, time
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd
from research.search2.portfolio import core as P
from research.search3.portfolio import core3 as C3
from research.search3.portfolio.round3w import MGROUP
from research.search5 import core5 as K

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
SYMS = {"GOLD": "XAUUSD", "SILVER": "XAGUSD", "BTC": "BTCUSD", "ETH": "ETHUSD", "NAS100": "USTEC", "SPX500": "US500", "GER40": "DE40", "WTI": "XTIUSD", "OIL": "XTIUSD"}


def _start(sym, t):
    p = f"data/search/{sym.lower()}-{t.lower()}.csv"
    if not os.path.exists(p):
        return None
    with open(p) as f:
        f.readline(); return f.readline()[:10]


def pick_tf(sym, tf):
    """The video's timeframe when we have LONG data for it (bars from 2019 or earlier); otherwise the finest
    coarser timeframe with long data (M1/M5/M15 -> M30 for most markets). Never a finer one."""
    order = ["M15", "M30", "H1", "H4", "D1"]
    tf = tf.upper(); tf = {"M1": "M15", "M5": "M15", "W1": "D1"}.get(tf, tf)
    if tf not in order:
        tf = "H1"
    long_ok = [t for t in order if (_start(sym, t) or "9999") <= "2019-01-01"]
    if not long_ok:                                       # market itself is young (EURUSD, USTEC, exotics): take what exists
        have = [t for t in order if _start(sym, t)]
        return (tf if tf in have else have[0]), tf not in have
    for t in order[order.index(tf):]:
        if t in long_ok:
            return t, t != tf
    return long_ok[-1], True


def as_entry(s, j):
    sym = SYMS.get(s["market"].upper(), s["market"].upper())
    if not os.path.exists(f"data/search/{sym.lower()}-h1.csv"):
        return None
    tf, moved = pick_tf(sym, s.get("tf", "H1"))
    spec = {k: s[k] for k in ("side", "trend", "entry", "session", "days", "stop", "target", "max_hold") if k in s and s[k] is not None}
    x = dict(name=f"yt{j}_{s['name']}"[:48], symbol=sym, tf=tf, module="research.search6.engine", fn="build_spec", params=dict(spec=spec),
             group=MGROUP.get(sym, "live"), family="yt", src=s.get("src", "youtube"), video_id=s.get("video_id"), claimed=s.get("claimed", ""),
             tf_moved=moved, tf_asked=s.get("tf"), i=j, mixes=[], live_risk=None, mgroup=MGROUP.get(sym, "other"))
    x["key"] = P.keyof(x)
    return x


def sim(x):
    try:
        _, cv, t = C3.run((x, 0.01, K.START, K.END))
    except Exception as e:  # noqa: BLE001
        return x["i"], None, None, f"{type(e).__name__}: {e}"
    hw, hc = P.hourly(cv)
    return x["i"], (hw.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32), hc.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32)), t, None


def main(path):
    specs = json.load(open(path))
    ents = [e for e in (as_entry(s, j) for j, s in enumerate(specs)) if e]
    print(f"{len(specs)} specs, {len(ents)} runnable (market data present)", flush=True)
    t0 = time.time(); rows = []; errs = []
    with Pool(2, maxtasksperchild=20) as pp:
        for i, cw, t, err in pp.imap_unordered(sim, ents, chunksize=2):
            x = next(e for e in ents if e["i"] == i)
            if err:
                errs.append((x["name"], err)); continue
            w, c = cw
            s = K.strat_stats(x, c, w, t)
            s.update(video_id=x["video_id"], claimed=x["claimed"], tf_asked=x["tf_asked"], tf_moved=x["tf_moved"], spec=json.dumps(x["params"]["spec"]))
            rows.append(s)
            np.savez_compressed(os.path.join(OUT, "curves", f"{i}.npz"), w=w, c=c)
    print(f"{len(rows)} simulated in {time.time() - t0:.0f}s; {len(errs)} errors", flush=True)
    for n, e in errs[:20]:
        print("  ERR", n, e)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "spec_stats.csv"), index=False)
    ok = df[(df.years_dev.fillna(0) >= 4)]
    good = ok[(ok.dev_pm > 0) & (ok.steady_dev >= 0.5) & (ok.dev_trades >= 60)]
    print(f"\n{len(ok)} with >= 4 dev years; {len(good)} pass the relaxed dev rule (dev $/mo > 0, >= 50% green years, >= 60 trades)")
    cols = ["name", "symbol", "tf", "first_trade", "years_dev", "pos_years_dev", "dev_pm", "y1_pm", "last2_pm", "sepoct_pm", "unseen3_worst_day", "dev_trades", "claimed"]
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 40)
    print(good.sort_values("dev_pm", ascending=False)[cols].round(0).to_string(index=False))
    print("\nTop 15 by dev $/mo regardless of rule:")
    print(ok.sort_values("dev_pm", ascending=False)[cols].round(0).head(15).to_string(index=False))
    print(f"\nAll runnable specs summed at 1% each: dev ${ok.dev_pm.sum():,.0f}/mo, unseen yr ${ok.y1_pm.sum():,.0f}, last2 ${ok.last2_pm.sum():,.0f}; "
          f"profitable on dev {int((ok.dev_pm > 0).sum())}/{len(ok)}, unseen yr {int((ok.y1_pm > 0).sum())}/{len(ok)}")
    if len(good):
        print(f"Relaxed-rule passers summed at 1%: dev ${good.dev_pm.sum():,.0f}/mo, unseen yr ${good.y1_pm.sum():,.0f}, last2 ${good.last2_pm.sum():,.0f}, Sep+Oct ${good.sepoct_pm.sum():,.0f}; "
              f"profitable in unseen yr {int((good.y1_pm > 0).sum())}/{len(good)}")


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "curves"), exist_ok=True)
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "specs.json"))

"""Build (and cache) the exact per-strategy runs of the live mix.

    python -m research.overlays.runs <cache_dir> [A|B|both] [k1,k2,...]

Cache: <cache_dir>/<window>/<n>.pkl holding {k: (curve, trades)} per strategy,
in mix order. Pool(2) and float32 curves: the laptop has little free RAM.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MIX_PATH = ROOT / "docs" / "board" / "portfolio-lp300-66.json"
END = pd.Timestamp("2026-10-21")
WINDOWS = {"A": pd.Timestamp("2024-10-20"), "B": pd.Timestamp("2023-10-20")}
KS = (0.0, 0.15, 0.25, 0.35)


def load_mix(path=MIX_PATH):
    mix = json.load(open(path))["mix"]
    for i, m in enumerate(mix):
        m["idx"] = i
        m["key"] = "|".join((m["module"], m["fn"], json.dumps(m["params"], sort_keys=True),
                             m["symbol"], m["tf"]))
    return mix


def _job(args):
    x, start, out, ks = args
    from research.overlays import sim
    t0 = time.time()
    try:
        res = sim.run_strategy(x, x["risk"], start, END, ks=ks)
        pickle.dump(res, open(out, "wb"))
        return x["idx"], x["name"], time.time() - t0, None
    except Exception as e:  # keep the batch going; report at the end
        return x["idx"], x["name"], time.time() - t0, repr(e)[:300]


def build(cache: Path, windows=("A", "B"), ks=KS, procs=2):
    mix = load_mix()
    jobs = []
    for w in windows:
        d = cache / w
        d.mkdir(parents=True, exist_ok=True)
        for x in mix:
            out = d / f"{x['idx']:02d}.pkl"
            if not out.exists():
                jobs.append((x, WINDOWS[w], out, ks))
    print(f"{len(jobs)} jobs", flush=True)
    errs = []
    with Pool(procs, maxtasksperchild=8) as pp:
        for i, (idx, name, dt, err) in enumerate(pp.imap_unordered(_job, jobs, chunksize=1)):
            print(f"[{i+1}/{len(jobs)}] {idx:02d} {name} {dt:.0f}s {err or ''}", flush=True)
            if err:
                errs.append((idx, name, err))
    print("errors:", errs)
    return errs


def load(cache: Path, window: str, mix=None):
    """[{k: (curve, trades)}] in mix order."""
    mix = mix or load_mix()
    return [pickle.load(open(cache / window / f"{x['idx']:02d}.pkl", "rb")) for x in mix]


if __name__ == "__main__":
    os.environ["PROP_OOS"] = "1"
    cache = Path(sys.argv[1])
    wins = ("A", "B") if len(sys.argv) < 3 or sys.argv[2] == "both" else (sys.argv[2],)
    ks = tuple(float(k) for k in sys.argv[3].split(",")) if len(sys.argv) > 3 else KS
    build(cache, wins, ks)

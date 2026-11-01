"""Round-5 report tables from out/mixes.json and out/strategy_stats.csv -> docs/2026-11-01-round5-results.md (body tables only;
the prose is written by hand around them).

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.report
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import pandas as pd
from research.search5 import core5 as K

PER = [("y1", "unseen yr Oct23-Oct24"), ("last2", "last 2y Oct24-Oct26 (fit)"), ("sepoct", "Sep+Oct 2026"), ("unseen3", "all 3 unseen yrs")]


def cell(r):
    if r is None:
        return "-"
    return f"${r['per_month']:,}/mo, fail {r['failed']}/{r['failed'] + r['passed'] + r['unfinished']}, low ${r['lowest_balance']:,}, stops {r['stop_days']}"


def main():
    mx = json.load(open(os.path.join(K.OUT, "mixes.json")))
    st = pd.read_csv(os.path.join(K.OUT, "strategy_stats.csv"))
    out = []
    for ak, acct in K.ACCTS.items():
        out.append(f"\n### Mixes on the {acct['label']} account (exact replay with the live daily stop)\n")
        out.append("| mix | strategies | dev 2015-23 (fast model) | " + " | ".join(l for _, l in PER) + " |")
        out.append("|---|---|---|" + "---|" * len(PER))
        for name, m in mx["mixes"].items():
            a = m["accounts"][ak]; d = a["dev_fast"]
            dev = f"${d['per_month']:,}/mo, low ${d['lowest_balance']:,}, stops {d['stop_days']} in {d['years']}y"
            out.append(f"| {name} | {m['n']} | {dev} | " + " | ".join(cell(a["unseen"].get(k)) for k, _ in PER) + " |")
        out.append(f"\nSame mixes with the equity regime switch (half size while the mix's 20-day mean equity is under its 60-day mean), {acct['label']}:\n")
        out.append("| mix | half-size share of days | " + " | ".join(l for _, l in PER) + " |")
        out.append("|---|---|" + "---|" * len(PER))
        for name, m in mx["mixes"].items():
            a = m["accounts"][ak]
            out.append(f"| {name} | {a['switch_share']:.0%} | " + " | ".join(cell(a["regime_switch"].get(k)) for k, _ in PER) + " |")
    # per-strategy contribution in the recommended-style mixes ($5K)
    for name in ("live23", "honest", "strict", "pruned+adds"):
        m = mx["mixes"][name]; ps = m["accounts"]["5k"]["per_strategy"]
        out.append(f"\n### Per-strategy profit inside '{name}', $5K account, exact replay\n")
        out.append("| strategy | market | tf | risk ($10K fraction) | " + " | ".join(l for _, l in PER) + " |")
        out.append("|---|---|---|---|" + "---|" * len(PER))
        keys = list(ps.keys())
        for s, k in zip(m["strategies"], keys):
            v = ps[k]
            out.append(f"| {s['name']} | {s['symbol']} | {s['tf']} | {s['risk']:.2%} | " + " | ".join(f"${v[p]:,}" for p, _ in PER) + " |")
    open("docs/2026-11-01-round5-tables.md", "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()

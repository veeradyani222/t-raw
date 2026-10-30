"""Mandatory look-ahead check for candidates: build(df) vs build(df.iloc[:k])
for 5 random k; every Entry at index < k must be identical. Also re-scores
each candidate (fresh process, same patched costs) and prints monthly P&L.

Usage: python research/search3/metals/causal_check.py candidates.json
"""
import json, random, sys
from research.search3.metals import runner  # patches harness costs / bad ticks
from research.prop import harness as H
from research.search3.metals import strategies as S


def same(a, b):
    if (a is None) != (b is None):
        return False
    if a is None:
        return True
    tp_eq = (a.tp is None and b.tp is None) or (a.tp is not None and b.tp is not None and abs(a.tp - b.tp) < 1e-9)
    return (a.side == b.side and abs(a.sl - b.sl) < 1e-9 and tp_eq and a.max_hold == b.max_hold
            and a.exit_hour == b.exit_hour and (a.manage is None) == (b.manage is None))


cands = json.loads(open(sys.argv[1]).read())
random.seed(11)
out = []
for c in cands:
    df = H.load(c["symbol"], c["tf"], split="oos")
    build = getattr(S, c["build_fn"])
    full = build(df, **c["params"])
    ks = sorted(random.sample(range(len(df) // 3, len(df) - 5), 5))
    diffs = {}
    for k in ks:
        part = df.iloc[:k].copy(); part.attrs.update(df.attrs)
        sub = build(part, **c["params"])
        diffs[k] = sum(1 for i in range(k) if not same(full[i], sub[i]))
    ents = [e for e in full if e is not None]
    exits = all((e.tp is not None) or (e.max_hold is not None) or (e.exit_hour is not None) or (e.manage is not None) for e in ents)
    s = H.score(df, full, name=c["name"])
    h = s["headline"]
    ok = all(v == 0 for v in diffs.values())
    print(f"{c['name']:<40} {c['symbol']} {c['tf']}  causal_ok={ok} diffs={diffs} entries={len(ents)} all_have_exit={exits}")
    print("   ", H.summary_line(s))
    print("    monthly:", h.get("monthly"))
    c.update(causal_ok=ok, trades=h.get("trades"), net=round(h.get("net", 0), 1), avg_month=round(h.get("avg_month", 0), 1),
             max_dd=round(h.get("max_dd", 0), 1), worst_day=round(h.get("worst_day", 0), 1), green_months=round(h.get("green_months", 0), 3),
             best_risk=s["best_risk"], monthly=h.get("monthly"))
    out.append(c)
json.dump(out, open(sys.argv[1].replace(".json", "_checked.json"), "w"), indent=1, default=str)

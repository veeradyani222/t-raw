"""Builds NOTES.md from results.jsonl + study_out.txt + the hand-written sections in notes_text.md.
Run: python research/search3/asia_indices/gen_notes.py"""
from __future__ import annotations
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
# merge the two scorer outputs (run.py ... results_a.jsonl / results_b.jsonl) into results.jsonl
parts = [p for p in (HERE / "results_a.jsonl", HERE / "results_b.jsonl") if p.exists()]
if parts:
    seen = set(); merged = []
    for p in parts:
        for l in p.read_text().splitlines():
            r = json.loads(l)
            if r["key"] not in seen and "error" not in r:
                seen.add(r["key"]); merged.append(r)
    (HERE / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in merged))
rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
rows = [r for r in rows if "error" not in r]
ok = [r for r in rows if r.get("best_risk") and (r.get("avg_month") or 0) > 0]
ok.sort(key=lambda r: -r["avg_month"])


def fmt(r):
    p = json.dumps(r["params"], sort_keys=True).replace("|", "/")
    br = f"{r['best_risk']*100:.2f}%" if r.get("best_risk") else "none"
    am = r.get("avg_month") or 0
    return (f"| {r['build_fn'][6:]} | {r['symbol']} | {r['tf']} | {br} | {am:.0f} | {r.get('net') or 0:.0f} | "
            f"{r.get('max_dd') or 0:.0f} | {r.get('worst_day') or 0:.0f} | {r.get('trades') or 0} | "
            f"{(r.get('green_months') or 0)*100:.0f}% | `{p}` |")


hdr = ("| idea | symbol | tf | best_risk | avg/mo $ | net $ | maxDD $ | worst day $ | trades | green mo | params |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|")
text = (HERE / "notes_text.md").read_text()
text = text.replace("{{N_RUNS}}", str(len(rows))).replace("{{N_OK}}", str(len(ok)))
# by idea: runs / passing / best passing run
by = {}
for r in rows:
    d = by.setdefault(r["build_fn"], dict(n=0, ok=0, best=None))
    d["n"] += 1
    if r.get("best_risk") and (r.get("avg_month") or 0) > 0:
        d["ok"] += 1
        if d["best"] is None or r["avg_month"] > d["best"]["avg_month"]:
            d["best"] = r
bi = ["| idea | runs | passing | best passing run (symbol tf, avg/mo $, trades, best_risk) |", "|---|---|---|---|"]
for fn, d in sorted(by.items(), key=lambda kv: -(kv[1]["best"]["avg_month"] if kv[1]["best"] else -1e9)):
    b = d["best"]
    bs = f"{b['symbol']} {b['tf']}, {b['avg_month']:.0f}, {b['trades']}, {b['best_risk']*100:.2f}%" if b else "none"
    bi.append(f"| {fn[6:]} | {d['n']} | {d['ok']} | {bs} |")
text = text.replace("{{BY_IDEA}}", "\n".join(bi))
cp = HERE / "candidates.json"
if cp.exists():
    cands = json.load(open(cp))
    ct = [hdr] + [fmt(r) for r in cands]
    text = text.replace("{{CANDIDATES}}", "\n".join(ct))
out = [text, "\n\n## Top 40 passing runs (best_risk set and avg_month > 0), ranked by avg_month\n", hdr]
out += [fmt(r) for r in ok[:40]]
out += ["\n\n## Every scored run (%d)\n" % len(rows), hdr]
for r in sorted(rows, key=lambda r: (r["build_fn"], r["symbol"], r["tf"], -(r.get("avg_month") or -1e9))):
    out.append(fmt(r))
out += ["\n\n## Appendix: market study output (study.py, verbatim)\n", "```", (HERE / "study_out.txt").read_text(), "```"]
(HERE / "NOTES.md").write_text("\n".join(out), encoding="utf-8")
print("NOTES.md written:", len(rows), "runs,", len(ok), "passing")

"""Turn out/round3w_results.json into docs/2026-10-30-round3-results.md (plain language, for the owner).

    .venv/Scripts/python.exe -m research.search3.portfolio.report3w
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "out", "round3w_results.json")))
POOL_A = json.load(open(os.path.join(HERE, "pool_a.json")))
MIX_LABELS = {"current66": "Current 66 (live)", "mix_2y": "Mix-2y", "mix_3y": "Mix-3y", "mix_5y": "Mix-5y"}
SPANS = {"2y": "2 years (2024-10-20..)", "3y": "3 years (2023-10-20..)", "5y": "5 years (2021-10-20..)", "last12": "last 12 months"}
YEARS = ["2022", "2023", "2024", "2025", "2026"]
GROUP_NAMES = {"crypto": "Crypto", "oil_gas": "Oil & gas", "asia_indices": "Asia indices", "europe_indices": "Europe indices",
               "us_indices": "US indices", "metals": "Metals", "jpy_crosses": "JPY crosses", "commodity_fx": "Commodity FX",
               "exotics": "Exotic FX", "majors": "Majors", "other": "Other"}


def money(v):
    return f"${v:,.0f}" if v >= 0 else f"-${-v:,.0f}"


def cell(rep):
    s = rep["close_all"]["summary"]
    return f"{money(s['net'])} / {money(s['worst_day'])} / {money(s['lowest_equity'])} / {int(s['halts'])}"


def cross_table():
    rows = ["| Mix | " + " | ".join(SPANS.values()) + " |", "|---|" + "---|" * len(SPANS)]
    for lab, name in MIX_LABELS.items():
        rows.append(f"| **{name}** | " + " | ".join(cell(R["cross"][lab][sp]) for sp in SPANS) + " |")
    return "\n".join(rows)


def year_table():
    rows = ["| Mix | " + " | ".join(f"{y}" + (" (to 10-30)" if y == "2026" else "") for y in YEARS) + " |", "|---|" + "---|" * len(YEARS)]
    for lab, name in MIX_LABELS.items():
        rows.append(f"| **{name}** | " + " | ".join(cell(R["cross"][lab][y]) for y in YEARS) + " |")
    return "\n".join(rows)


def stats_table():
    hdr = ["Mix", "strategies (new)", "window built on", "avg/month (own window)", "green months", "max $ at risk at once",
           "challenges passed / failed (own window)", "avg/month 5y", "green months 5y", "challenges 5y"]
    rows = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for lab, name in MIX_LABELS.items():
        if lab == "current66":
            n, nn, own = 66, 0, "2y"
        else:
            W = R["windows"][lab[4:]]; n, nn, own = len(W["mix"]), W["summary"]["n_new"], lab[4:]
        o = R["cross"][lab][own]["close_all"]["summary"]; f = R["cross"][lab]["5y"]["close_all"]["summary"]
        mor = max(R["cross"][lab][sp]["max_open_risk"] for sp in SPANS)
        rows.append(f"| **{name}** | {n} ({nn}) | {own} | {money(o['avg_month'])} | {o['green'] * 100:.0f}% | {money(mor)} | "
                    f"{int(o['challenge_pass'])} / {int(o['challenge_fail'])} | {money(f['avg_month'])} | {f['green'] * 100:.0f}% | "
                    f"{int(f['challenge_pass'])} / {int(f['challenge_fail'])} |")
    return "\n".join(rows)


def group_table():
    groups = sorted({g for lab in MIX_LABELS for sp in ("2y", "5y") for g in R["cross"][lab][sp]["by_group"]},
                    key=lambda g: -sum(R["cross"][lab]["5y"]["by_group"].get(g, 0) for lab in MIX_LABELS))
    rows = ["| Market group | " + " | ".join(f"{n} 2y / 5y" for n in MIX_LABELS.values()) + " |", "|---|" + "---|" * len(MIX_LABELS)]
    for g in groups:
        rows.append(f"| {GROUP_NAMES.get(g, g)} | " + " | ".join(
            f"{money(R['cross'][lab]['2y']['by_group'].get(g, 0))} / {money(R['cross'][lab]['5y']['by_group'].get(g, 0))}" for lab in MIX_LABELS) + " |")
    return "\n".join(rows)


def mix_table(tag):
    W = R["windows"][tag]
    rows = ["| Strategy | Market | TF | Risk | Net (window) | Trades | Biggest trade | Max lots | New? |", "|---|---|---|---|---|---|---|---|---|"]
    for m in sorted(W["mix"], key=lambda m: -m["net_window"]):
        rows.append(f"| {m['name']} | {m['symbol']} | {m['tf']} | {m['risk'] * 100:.2f}% | {money(m['net_window'])} | {m['trades_window']} | "
                    f"{money(m['biggest_trade'])} ({(m['biggest_share'] or 0) * 100:.0f}%) | {m['max_lots']:.2f} | {'new' if m['src'] == 'new' else 'live'} |")
    return "\n".join(rows)


def ranked_candidates():
    """Every pool-A candidate: its own group score, 1% solo facts per window, and which mixes took it."""
    byk = {p["key"]: p for p in R["pool"]}
    import importlib
    from research.search2.portfolio.core import keyof
    rows = ["| # | Candidate | Market | TF | Group | Group score avg/mo | Solo 1% net 2y / 3y / 5y | Trades 2y / 5y | In mix 2y / 3y / 5y (risk) |",
            "|---|---|---|---|---|---|---|---|---|"]
    recs = []
    for a in POOL_A:
        k = keyof(dict(a, fn=a["build_fn"]))
        sol = {t: R["windows"][t]["solo"].get(k) for t in ("2y", "3y", "5y")}
        inmix = {t: next((m["risk"] for m in R["windows"][t]["mix"] if keyof(m) == k), None) for t in ("2y", "3y", "5y")}
        recs.append((a, sol, inmix))
    recs.sort(key=lambda r: -(r[1]["2y"]["net_1pct"] if r[1]["2y"] else -1e9))
    for i, (a, sol, inmix) in enumerate(recs, 1):
        nets = " / ".join(money(sol[t]["net_1pct"]) if sol[t] else "n/a" for t in ("2y", "3y", "5y"))
        tr = f"{sol['2y']['trades_1pct'] if sol['2y'] else 0} / {sol['5y']['trades_1pct'] if sol['5y'] else 0}"
        im = " / ".join(f"{inmix[t] * 100:.2f}%" if inmix[t] else "-" for t in ("2y", "3y", "5y"))
        rows.append(f"| {i} | {a['name']} | {a['symbol']} | {a['tf']} | {a['group']} | {money(a['avg_month'])} | {nets} | {tr} | {im} |")
    return "\n".join(rows)


def lists(tag):
    W = R["windows"][tag]
    new_in = ", ".join(f"{m['name']} ({m['symbol']} {m['tf']}, {m['risk'] * 100:.2f}%)" for m in W["new_in"]) or "none"
    dropped = ", ".join(f"{m['name']} ({m['symbol']} {m['tf']})" for m in W["dropped_live"]) or "none"
    changed = ", ".join(f"{m['name']} ({m['symbol']}: {m['old_risk'] * 100:.2f}% -> {m['new_risk'] * 100:.2f}%)" for m in W["kept_live_changed"]) or "none"
    flags = "\n".join(f"- {f}" for f in W["flags"]) or "- none"
    return new_in, dropped, changed, flags


def flat_notes():
    out = []
    for lab in MIX_LABELS:
        fb = R["cross"][lab]["5y"].get("flat_before", [])
        if fb:
            out.append(f"- {MIX_LABELS[lab]}: flat at the start of the 5-year window (data begins later): {', '.join(fb)}")
    return "\n".join(out) or "- none"


if __name__ == "__main__":
    verdict = open(os.path.join(HERE, "verdict.md")).read() if os.path.exists(os.path.join(HERE, "verdict.md")) else "_(verdict pending)_"
    md = f"""# Strategy search, round 3 results (2026-10-30)

Written for Veer. Plain language. Round 3 was a from-scratch, per-market search (ten market groups,
80 candidates returned) with no loyalty to the 66 strategies running live and no statistical gates
other than the look-ahead check and the 300/800 rule. This document is the PORTFOLIO stage: the full
pool (80 new + 66 live = 146 strategies) was rebuilt into three mixes, one sized on the last 2 years,
one on 3 years and one on 5 years, and all four mixes (the live 66 included) were then tested on every
window and every calendar year.

Rules the mixes had to keep at every hour: combined floating loss on the server day never worse than
-$300 (the firm's limit is -$400), combined equity never below $9,200 from a fresh $10k start. In the
tables below every cell is **net / worst day / lowest equity / stop fires** after replaying the account
with the live close-all stop at -$300 (slip $25). Each window or year starts fresh at $10,000.

## The short version

{verdict}

## Cross-evaluation: every mix on every window

Each cell: net profit / worst server day / lowest equity / number of close-all stop fires. Fresh $10k
start at the beginning of each window. Risk is fixed-dollar per trade (not compounding), as live.

{cross_table()}

## Calendar years, each a fresh $10k start

{year_table()}

## Mix statistics

{stats_table()}

## Where the profit comes from (by market group, 2 years / 5 years)

{group_table()}

## Mix-2y (sized on 2024-10-20..now)

New strategies in: {lists('2y')[0]}

Live strategies dropped: {lists('2y')[1]}

Live strategies kept at a different risk: {lists('2y')[2]}

Things that look like data artefacts or thin edges:
{lists('2y')[3]}

{mix_table('2y')}

## Mix-3y (sized on 2023-10-20..now)

New strategies in: {lists('3y')[0]}

Live strategies dropped: {lists('3y')[1]}

Live strategies kept at a different risk: {lists('3y')[2]}

Things that look like data artefacts or thin edges:
{lists('3y')[3]}

{mix_table('3y')}

## Mix-5y (sized on 2021-10-20..now)

New strategies in: {lists('5y')[0]}

Live strategies dropped: {lists('5y')[1]}

Live strategies kept at a different risk: {lists('5y')[2]}

Things that look like data artefacts or thin edges:
{lists('5y')[3]}

{mix_table('5y')}

## Ranked table of all 80 round-3 candidates

"Group score" is what the market group reported on the 2-year window at its best risk. "Solo 1% net" is
the exact portfolio-stage simulation at 1% risk from a fresh start on each window (a strategy whose data
begins later is simply flat until then). The last column says which mixes picked it and at what risk.

{ranked_candidates()}

## Data notes

- Strategies whose data begins after a window start are flat until their data begins:
{flat_notes()}
- Windows are slices of one five-year simulation per strategy (fixed-dollar risk makes P&L path-independent); a
  position open across a window boundary is counted in the curve but not in the window's trade list. Not material.
- Costs: each market group's own cost patch (spread floors, no commission on indices/crypto, pip sizes, quote
  conversions) and data cleaner (flat/stale days, zero-volume bars, the DE40 stale week of 2024-11-28..12-05)
  were applied exactly as in the group scoring, see research/search3/portfolio/core3.py.
- Files: docs/board/portfolio-round3-2y.json, portfolio-round3-3y.json, portfolio-round3-5y.json (same format
  as portfolio-lp300-66.json plus the cross-evaluation); raw numbers in research/search3/portfolio/out/round3w_results.json.
"""
    open("docs/2026-10-30-round3-results.md", "w", encoding="utf-8").write(md)
    print("wrote docs/2026-10-30-round3-results.md")

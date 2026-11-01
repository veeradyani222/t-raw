"""Scoreboard: every strategy ever judged by the round-5 judge, one row each, honest columns only.
Merges research/search5/out/strategy_stats.csv (round-3 pool + round-4 survivors + round-5 holds) and
research/search6/out/spec_stats.csv (YouTube / written specs). Writes docs/board/scoreboard.csv and
docs/board/scoreboard.md, and a one-page card for every strategy that passes the relaxed dev rule
(knowledge/strategies/<slug>.md).

    cd mt5-trader && python -m research.search6.scoreboard
"""
import os, sys, json, re
sys.path.insert(0, os.getcwd())
import pandas as pd

COLS = ["name", "symbol", "tf", "source", "first_trade", "years_dev", "pos_years_dev", "dev_pm", "y1_pm", "last2_pm", "sepoct_pm", "unseen3_worst_day", "dev_trades", "relaxed", "strict", "claimed", "spec", "video_id"]


def load():
    frames = []
    p5 = "research/search5/out/strategy_stats.csv"
    if os.path.exists(p5):
        d = pd.read_csv(p5); d["source"] = d["src"].map({"live66": "round1-2 live 66", "new": "round-3 pool", "round4": "round-4 price action", "r5_tod": "round-5 time-of-day"}).fillna(d["src"])
        frames.append(d)
    p6 = "research/search6/out/spec_stats.csv"
    if os.path.exists(p6):
        d = pd.read_csv(p6); d["source"] = d["src"].map({"youtube": "round-6 YouTube", "written": "round-6 written"}).fillna("round-6")
        frames.append(d)
    df = pd.concat(frames, ignore_index=True, sort=False)
    for c in COLS:
        if c not in df:
            df[c] = None
    df["years_dev"] = df["years_dev"].fillna(0).astype(int)
    df["relaxed"] = (df.years_dev >= 4) & (df.steady_dev >= 0.5) & (df.dev_pm > 0) & (df.dev_trades.fillna(0) >= 60)
    df["strict"] = (df.years_dev >= 5) & (df.steady_dev >= 0.8) & (df.dev_pm > 0)
    return df


def card(r):
    slug = re.sub(r"[^a-z0-9]+", "-", f"{r['name']}-{r['symbol']}-{r['tf']}".lower()).strip("-")
    yrs = r.get("yearly")
    lines = [f"# {r['name']} on {r['symbol']} {r['tf']}", "", f"Source: {r['source']}" + (f" (video {r['video_id']})" if isinstance(r.get('video_id'), str) else ""),
             f"Data from: {r['first_trade']}. Dev years {r['years_dev']}, green {r['pos_years_dev']}. Rule: {'strict' if r['strict'] else 'relaxed'}.", "",
             "| period | $/month at 1% of $10K |", "|---|---|",
             f"| dev 2015..2023-10 | {r['dev_pm']:,.0f} |", f"| unseen yr Oct23..Oct24 | {r['y1_pm']:,.0f} |",
             f"| last 2y Oct24..Oct26 | {r['last2_pm']:,.0f} |", f"| Sep+Oct 2026 | {r['sepoct_pm']:,.0f} |", ""]
    if isinstance(r.get("claimed"), str) and r["claimed"]:
        lines.append(f"Author's claim: {r['claimed']}")
    if isinstance(r.get("spec"), str) and r["spec"]:
        lines += ["", "Spec:", "```json", r["spec"], "```"]
    if isinstance(yrs, str):
        lines += ["", f"Yearly at 1%: {yrs}"]
    return slug, "\n".join(lines) + "\n"


def main():
    df = load()
    df.to_csv("docs/board/scoreboard.csv", index=False, columns=[c for c in COLS if c in df] + ["yearly"] if "yearly" in df else COLS)
    os.makedirs("knowledge/strategies", exist_ok=True)
    good = df[df.relaxed].sort_values("dev_pm", ascending=False)
    for _, r in good.iterrows():
        slug, txt = card(r); open(f"knowledge/strategies/{slug}.md", "w", encoding="utf-8").write(txt)
    md = ["# Scoreboard: every strategy judged on long history\n",
          f"{len(df)} strategies. dev = 2015..2023-10-20 (pick period), unseen yr = Oct 2023..Oct 2024, last 2y = Oct 2024..Oct 2026 "
          "(fit period for the round-3 pool and the live mixes), Sep+Oct = 2026. All $/month at 1% of $10K per trade; halve for $5K.\n",
          f"Pass the relaxed dev rule (4+ years, half green, dev > 0, 60+ trades): **{int(df.relaxed.sum())}**. Strict (5+ years, 80% green): **{int(df.strict.sum())}**.\n",
          "| source | tested | relaxed | strict | profitable in unseen yr |", "|---|---|---|---|---|"]
    for src, g in df.groupby("source"):
        md.append(f"| {src} | {len(g)} | {int(g.relaxed.sum())} | {int(g.strict.sum())} | {int((g.y1_pm > 0).sum())} |")
    md += ["", "## Relaxed-rule passers, ranked by dev $/month\n", "| strategy | market | tf | source | dev yrs | green | dev $/mo | unseen yr | last 2y (fit?) | Sep+Oct | worst day 3y |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in good.iterrows():
        md.append(f"| {r['name']} | {r['symbol']} | {r['tf']} | {r['source']} | {r['years_dev']} | {r['pos_years_dev']} | {r['dev_pm']:,.0f} | {r['y1_pm']:,.0f} | {r['last2_pm']:,.0f} | {r['sepoct_pm']:,.0f} | {r['unseen3_worst_day']:,.0f} |")
    open("docs/board/scoreboard.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[:12])); print(f"... {len(good)} cards in knowledge/strategies/")


if __name__ == "__main__":
    main()

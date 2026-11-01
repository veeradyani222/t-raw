"""Round 6 wider YouTube collection (search only; captions are pulled by collect.py's loop or fetch_subs.py):
prop-firm passes, backtest series, "rules" videos, plus every video of channels known to state rules.
Merges into out/videos.json (keeps existing tags).

    cd mt5-trader && python -m research.search6.collect_more
"""
import os, json, time, subprocess
from research.search6.collect import MARKETS, search, OUT, MIN_SEC, MAX_SEC

TEMPLATES = ["{m} strategy I backtested 100 times", "how I passed prop firm challenge {m} strategy", "{m} strategy exact entry exit rules",
             "{m} price action strategy rules stop loss take profit", "{m} ICT strategy rules", "{m} supply and demand strategy rules"]
GENERIC = {"EURUSD": ["forex strategy backtested 100 times", "forex strategy exact rules stop loss take profit", "prop firm challenge passed strategy rules",
                      "simple forex strategy rules beginners backtest", "mean reversion forex strategy rules", "breakout forex strategy rules session"],
           "XAUUSD": ["gold scalping strategy exact rules", "XAUUSD strategy backtested 100 times", "gold prop firm strategy rules"],
           "BTCUSD": ["bitcoin strategy backtested rules", "crypto trading strategy exact rules backtest"],
           "USTEC": ["NAS100 strategy backtested rules", "nasdaq futures strategy exact rules"]}
CHANNEL_QUERIES = ["backtesting trading strategy episode", "I tested this trading strategy 100 times", "trading strategy results after 100 trades"]


def main():
    path = os.path.join(OUT, "videos.json")
    vids = {v["id"]: dict(v, markets=set(v["markets"])) for v in json.load(open(path))} if os.path.exists(path) else {}
    n0 = len(vids); t0 = time.time()

    def add(mkt, q, rows):
        for r in rows:
            if not (MIN_SEC <= r["duration"] <= MAX_SEC):
                continue
            v = vids.setdefault(r["id"], dict(r, markets=set(), queries=[]))
            v["markets"].add(mkt); v["queries"].append(q)
    for mkt, names in MARKETS.items():
        for tpl in TEMPLATES:
            q = tpl.format(m=names[0]); add(mkt, q, search(q))
        print(f"{mkt}: {len(vids)} total ({time.time() - t0:.0f}s)", flush=True)
    for mkt, qs in GENERIC.items():
        for q in qs:
            add(mkt, q, search(q))
    for q in CHANNEL_QUERIES:
        add("EURUSD", q, search(q))    # generic backtest series: tagged EURUSD unless the title names a market (fixed in tagging below)
    # re-tag by title: a title that names a market overrides the query tag
    for v in vids.values():
        t = v["title"].upper().replace("/", "")
        hits = {m for m, names in MARKETS.items() if any(nm.upper().split()[0].replace("/", "") in t for nm in names) or m in t}
        for extra, m in (("GOLD", "XAUUSD"), ("BITCOIN", "BTCUSD"), ("BTC", "BTCUSD"), ("NAS100", "USTEC"), ("NASDAQ", "USTEC"), ("US30", "US30"), ("DOW", "US30"),
                         ("SPX", "US500"), ("S&P", "US500"), ("ES ", "US500"), ("DAX", "DE40"), ("GER40", "DE40"), ("OIL", "XTIUSD"), ("ETH", "ETHUSD"), ("SILVER", "XAGUSD")):
            if extra in t:
                hits.add(m)
        if hits:
            v["markets"] = hits
    for v in vids.values():
        v["markets"] = sorted(v["markets"])
    json.dump(list(vids.values()), open(path, "w"), indent=1)
    print(f"{len(vids)} videos ({len(vids) - n0} new) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

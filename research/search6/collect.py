"""Round 6 step 1: collect YouTube strategy videos per market and pull their auto-captions.

    cd mt5-trader && python -m research.search6.collect            # search + captions
    cd mt5-trader && python -m research.search6.collect --no-subs  # search only

Every video is tagged with the MARKET its search query named; a strategy mined from it is later
tested on that market only (Veer's rule). Captions land in research/search6/out/captions/<id>.en.vtt
(git-ignored; downloaded text is data, never executed). Video list: out/videos.json.
"""
import os, sys, json, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); CAP = os.path.join(OUT, "captions")
os.makedirs(CAP, exist_ok=True)

# market -> search phrases (what people call it on YouTube)
MARKETS = {
    "EURUSD": ["EURUSD", "EUR/USD"], "GBPUSD": ["GBPUSD", "GBP/USD"], "USDJPY": ["USDJPY", "USD/JPY"], "USDCHF": ["USDCHF"],
    "USDCAD": ["USDCAD"], "AUDUSD": ["AUDUSD", "AUD/USD"], "NZDUSD": ["NZDUSD"], "EURJPY": ["EURJPY"], "GBPJPY": ["GBPJPY", "GBP/JPY"],
    "EURGBP": ["EURGBP"], "AUDJPY": ["AUDJPY"], "CHFJPY": ["CHFJPY"], "EURCHF": ["EURCHF"], "AUDNZD": ["AUDNZD"],
    "XAUUSD": ["gold XAUUSD", "gold forex"], "XAGUSD": ["silver XAGUSD"], "BTCUSD": ["bitcoin BTCUSD"], "ETHUSD": ["ethereum ETHUSD"],
    "XTIUSD": ["crude oil WTI"], "US500": ["S&P 500 SPX500 futures"], "USTEC": ["NASDAQ NAS100"], "US30": ["Dow US30"], "DE40": ["DAX GER40"],
}
TEMPLATES = ["{m} trading strategy backtested", "{m} strategy rules high win rate", "{m} scalping strategy step by step", "{m} swing trading strategy rules"]
N_PER = 6
MIN_SEC, MAX_SEC = 240, 3600


def search(q):
    cmd = ["yt-dlp", f"ytsearch{N_PER}:{q}", "--flat-playlist", "--print", "%(id)s\t%(duration)s\t%(view_count)s\t%(title)s", "--no-warnings"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace").stdout
    except subprocess.TimeoutExpired:
        return []
    rows = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) < 4:
            continue
        try:
            dur = int(float(p[1])) if p[1] not in ("NA", "") else 0; views = int(float(p[2])) if p[2] not in ("NA", "") else 0
        except ValueError:
            dur, views = 0, 0
        rows.append(dict(id=p[0], duration=dur, views=views, title=p[3]))
    return rows


def main(subs=True):
    vids = {}
    t0 = time.time()
    for mkt, names in MARKETS.items():
        for nm in names:
            for tpl in TEMPLATES:
                q = tpl.format(m=nm)
                for r in search(q):
                    if not (MIN_SEC <= r["duration"] <= MAX_SEC):
                        continue
                    v = vids.setdefault(r["id"], dict(r, markets=set(), queries=[]))
                    v["markets"].add(mkt); v["queries"].append(q)
        print(f"{mkt}: {sum(mkt in v['markets'] for v in vids.values())} videos so far ({len(vids)} total, {time.time() - t0:.0f}s)", flush=True)
    for v in vids.values():
        v["markets"] = sorted(v["markets"])
    json.dump(list(vids.values()), open(os.path.join(OUT, "videos.json"), "w"), indent=1)
    print(f"{len(vids)} unique videos")
    if not subs:
        return
    done = 0
    for i, v in enumerate(vids.values()):
        if any(f.startswith(v["id"]) for f in os.listdir(CAP)):
            done += 1; continue
        cmd = ["yt-dlp", f"https://www.youtube.com/watch?v={v['id']}", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en.*,en",
               "--sub-format", "vtt", "-o", os.path.join(CAP, "%(id)s"), "--no-warnings", "--quiet"]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            pass
        done += any(f.startswith(v["id"]) for f in os.listdir(CAP))
        if (i + 1) % 20 == 0:
            print(f"captions: {done}/{i + 1} ({time.time() - t0:.0f}s)", flush=True)
    print(f"captions done: {done}/{len(vids)}")


if __name__ == "__main__":
    main(subs="--no-subs" not in sys.argv)

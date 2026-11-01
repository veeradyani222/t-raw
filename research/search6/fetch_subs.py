"""Pull English auto-captions for every video in out/videos.json that has none yet (resumable).

    cd mt5-trader && python -m research.search6.fetch_subs
"""
import os, sys, json, time, subprocess
from research.search6.collect import OUT, CAP


def main():
    vids = json.load(open(os.path.join(OUT, "videos.json")))
    TXT = os.path.join(OUT, "transcripts")
    have = {f.split(".")[0] for f in os.listdir(CAP)} | ({f[:-4] for f in os.listdir(TXT)} if os.path.isdir(TXT) else set())
    todo = [v for v in vids if v["id"] not in have]
    if "--reverse" in sys.argv:
        todo = todo[::-1]
    print(f"{len(vids)} videos, {len(have)} with captions, {len(todo)} to fetch", flush=True)
    t0 = time.time(); got = 0
    for i, v in enumerate(todo):
        if any(f.startswith(v["id"]) for f in os.listdir(CAP)):
            got += 1; continue
        cmd = ["yt-dlp", f"https://www.youtube.com/watch?v={v['id']}", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en.*,en",
               "--sub-format", "vtt", "-o", os.path.join(CAP, "%(id)s"), "--no-warnings", "--quiet"]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            pass
        got += any(f.startswith(v["id"]) for f in os.listdir(CAP))
        if (i + 1) % 25 == 0:
            print(f"  {got}/{i + 1} fetched ({time.time() - t0:.0f}s)", flush=True)
    print(f"done: {got}/{len(todo)} new caption files in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

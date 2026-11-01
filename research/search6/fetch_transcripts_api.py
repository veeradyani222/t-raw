"""Captions through youtube-transcript-api (HTTP only, ~0.5 s a video) for every video in out/videos.json
that has neither a .vtt in out/captions nor a .txt in out/transcripts. Writes out/transcripts/<id>.txt
directly (TITLE / MARKETS header + text). Resumable; 4 threads.

    cd mt5-trader && python -m research.search6.fetch_transcripts_api
"""
import os, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from youtube_transcript_api import YouTubeTranscriptApi
from research.search6.collect import OUT, CAP
TXT = os.path.join(OUT, "transcripts"); os.makedirs(TXT, exist_ok=True)


def fetch(v):
    try:
        api = YouTubeTranscriptApi()
        tl = api.list(v["id"])
        try:
            tr = tl.find_transcript(["en", "en-US", "en-GB"])
        except Exception:  # noqa: BLE001
            tr = tl.find_generated_transcript(["en"])
        parts = tr.fetch()
        text = " ".join(p.text.replace("\n", " ").strip() for p in parts if p.text.strip())
        if len(text.split()) < 300:
            return v["id"], "short"
        open(os.path.join(TXT, f"{v['id']}.txt"), "w", encoding="utf-8").write(f"TITLE: {v['title']}\nMARKETS: {', '.join(v['markets'])}\n\n{text}")
        return v["id"], "ok"
    except Exception as e:  # noqa: BLE001
        return v["id"], f"{type(e).__name__}"


def main():
    vids = json.load(open(os.path.join(OUT, "videos.json")))
    have = {f.split(".")[0] for f in os.listdir(CAP)} | {f.split(".")[0] for f in os.listdir(TXT)}
    todo = [v for v in vids if v["id"] not in have]
    print(f"{len(vids)} videos, {len(have)} already have text, {len(todo)} to fetch", flush=True)
    t0 = time.time(); stats = {}
    with ThreadPoolExecutor(4) as ex:
        for n, fut in enumerate(as_completed([ex.submit(fetch, v) for v in todo]), 1):
            _, st = fut.result(); stats[st] = stats.get(st, 0) + 1
            if n % 50 == 0:
                print(f"  {n}/{len(todo)} {stats} ({time.time() - t0:.0f}s)", flush=True)
    print(f"done in {time.time() - t0:.0f}s: {stats}")


if __name__ == "__main__":
    main()

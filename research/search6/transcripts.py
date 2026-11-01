"""Round 6 step 2: captions -> clean plain-text transcripts (out/transcripts/<id>.txt) and a manifest
(out/manifest.json: id, title, markets, words, path). Two caption sources feed this: yt-dlp .vtt files in
out/captions (converted here) and youtube-transcript-api text written straight into out/transcripts by
fetch_transcripts_api.py. Caption files are downloaded data: parsed as text only.

    cd mt5-trader && python -m research.search6.transcripts
"""
import os, re, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); CAP = os.path.join(OUT, "captions"); TXT = os.path.join(OUT, "transcripts")
os.makedirs(TXT, exist_ok=True)
TAG = re.compile(r"<[^>]+>")


def vtt_to_text(path):
    lines = []
    for raw in open(path, encoding="utf-8", errors="replace"):
        s = raw.strip()
        if not s or s.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or "-->" in s or s.isdigit():
            continue
        s = TAG.sub("", s).replace("&nbsp;", " ").replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").strip()
        if s and (not lines or s != lines[-1]):
            lines.append(s)
    out = []
    for s in lines:   # rolling-window repeats: drop a line that is a prefix/suffix of its neighbour
        if out and (out[-1].endswith(s) or s.startswith(out[-1])):
            out[-1] = s if s.startswith(out[-1]) else out[-1]
            continue
        out.append(s)
    return " ".join(out)


def main():
    vids = {v["id"]: v for v in json.load(open(os.path.join(OUT, "videos.json")))}
    seen = set()
    for p in sorted(glob.glob(os.path.join(CAP, "*.vtt"))):
        vid = os.path.basename(p).split(".")[0]
        tp = os.path.join(TXT, f"{vid}.txt")
        if vid not in vids or vid in seen or os.path.exists(tp):
            continue
        seen.add(vid)
        txt = vtt_to_text(p)
        if len(txt.split()) < 300:
            continue
        header = "TITLE: " + vids[vid]["title"] + "\nMARKETS: " + ", ".join(vids[vid]["markets"]) + "\n\n"
        open(tp, "w", encoding="utf-8").write(header + txt)
    man = []
    for tp in sorted(glob.glob(os.path.join(TXT, "*.txt"))):
        vid = os.path.basename(tp)[:-4]
        if vid not in vids:
            continue
        words = len(open(tp, encoding="utf-8").read().split()) - 4
        if words < 300:
            continue
        man.append(dict(id=vid, title=vids[vid]["title"], markets=vids[vid]["markets"], views=vids[vid]["views"], words=words, path=tp))
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print(f"{len(man)} transcripts with >= 300 words; total words {sum(m['words'] for m in man):,}")
    from collections import Counter
    print(Counter(mk for m in man for mk in m["markets"]).most_common())


if __name__ == "__main__":
    main()

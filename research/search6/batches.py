"""Assign unread transcripts to reader batches (out/batches/batch_<n>.txt = list of transcript paths,
<= MAX_WORDS words each). Re-run as more transcripts arrive; already-assigned ids are skipped.
Then: python -m research.search6.batches merge  -> out/specs.json from out/specs/batch_*.json (+ written_specs.json)

    cd mt5-trader && python -m research.search6.transcripts && python -m research.search6.batches
"""
import os, sys, json, glob
from research.search6.collect import OUT
BATCH = os.path.join(OUT, "batches"); SPECS = os.path.join(OUT, "specs")
os.makedirs(BATCH, exist_ok=True); os.makedirs(SPECS, exist_ok=True)
MAX_WORDS = 45_000


def assigned():
    ids = set()
    for p in glob.glob(os.path.join(BATCH, "batch_*.txt")):
        ids |= {os.path.basename(l.strip()).split(".")[0] for l in open(p) if l.strip()}
    return ids


def make():
    man = json.load(open(os.path.join(OUT, "manifest.json")))
    done = assigned()
    todo = sorted([m for m in man if m["id"] not in done], key=lambda m: m["markets"][0])
    n = len(glob.glob(os.path.join(BATCH, "batch_*.txt")))
    cur, words, made = [], 0, []
    for m in todo:
        if cur and words + m["words"] > MAX_WORDS:
            n += 1; p = os.path.join(BATCH, f"batch_{n:03d}.txt"); open(p, "w").write("\n".join(cur) + "\n"); made.append(p); cur, words = [], 0
        cur.append(m["path"]); words += m["words"]
    if cur:
        n += 1; p = os.path.join(BATCH, f"batch_{n:03d}.txt"); open(p, "w").write("\n".join(cur) + "\n"); made.append(p)
    for p in made:
        print(p, sum(1 for _ in open(p)), "transcripts")
    if not made:
        print("nothing new to assign")


def merge():
    specs = []
    for p in sorted(glob.glob(os.path.join(SPECS, "batch_*.json"))):
        try:
            batch = json.load(open(p, encoding="utf-8"))
        except json.JSONDecodeError as e:
            print("BAD JSON", p, e); continue
        for s in batch:
            s["src"] = "youtube"; specs.append(s)
    wp = os.path.join(OUT, "written_specs.json")
    if os.path.exists(wp):
        for s in json.load(open(wp, encoding="utf-8")):
            s["src"] = "written"; s.setdefault("video_id", s.get("source_url")); specs.append(s)
    json.dump(specs, open(os.path.join(OUT, "specs.json"), "w"), indent=1)
    from collections import Counter
    print(len(specs), "specs;", Counter(s["src"] for s in specs), Counter(s["market"] for s in specs).most_common(12))


if __name__ == "__main__":
    merge() if "merge" in sys.argv else make()

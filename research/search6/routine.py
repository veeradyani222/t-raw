"""The strategy-search gear, one command. Each stage is resumable and skips what is already done.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search6.routine [stage ...]

Stages (default: all except "read"):
    collect   search YouTube per market (collect.py + collect_more.py) -> out/videos.json
    captions  youtube-transcript-api, then yt-dlp for the leftovers -> out/transcripts, out/captions
    text      manifest of clean transcripts -> out/manifest.json
    batch     assign unread transcripts to reader batches -> out/batches/batch_NNN.txt
    read      (needs an LLM) one reader agent per batch, following .claude/skills/strategy-reader/SKILL.md,
              writes out/specs/batch_NNN.json. Without an API key this is done by Claude Code sub-agents;
              the routine prints the batch files that still lack a specs file and stops.
    merge     out/specs/*.json + out/written_specs.json -> out/specs.json
    judge     run every spec on its own market, dev then unseen -> out/spec_stats.csv
    board     docs/board/scoreboard.{csv,md} + knowledge/strategies cards
"""
import os, sys, glob, subprocess
PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")


def run(mod, *args):
    print(f"\n### {mod} {' '.join(args)}", flush=True)
    r = subprocess.run([PY, "-m", mod, *args], cwd=os.getcwd())
    if r.returncode:
        print(f"!! {mod} exited {r.returncode}", flush=True)


def main(stages):
    if "collect" in stages:
        run("research.search6.collect", "--no-subs"); run("research.search6.collect_more")
    if "captions" in stages:
        run("research.search6.fetch_transcripts_api"); run("research.search6.fetch_subs")
    if "text" in stages:
        run("research.search6.transcripts")
    if "batch" in stages:
        run("research.search6.batches")
    if "read" in stages:
        pending = [b for b in sorted(glob.glob(os.path.join(OUT, "batches", "batch_*.txt")))
                   if not os.path.exists(os.path.join(OUT, "specs", os.path.basename(b)[:-4] + ".json"))]
        if pending:
            print("\nbatches waiting for a reader (launch one sub-agent per file with the strategy-reader skill):")
            for b in pending:
                print("  ", b)
            return
    if "merge" in stages:
        run("research.search6.batches", "merge")
    if "judge" in stages:
        run("research.search6.run_specs", os.path.join(OUT, "specs.json"))
    if "board" in stages:
        run("research.search6.scoreboard")


if __name__ == "__main__":
    st = sys.argv[1:] or ["collect", "captions", "text", "batch", "read", "merge", "judge", "board"]
    main(st)

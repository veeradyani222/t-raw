"""Export the live account's ground truth to files the repo can carry.

Run on the trading box (see ops/daily_export.ps1, which schedules it). Writes:

  ops/state/deals-YYYY-MM-DD.csv   every filled deal in the trailing window
  ops/state/status.json            account + open positions + the commit running

The point is reconciliation without RDP: `trader.log` says what the bot DECIDED,
these files say what the broker actually FILLED. Comparing the two is how you
tell a strategy problem from an execution problem.

The MT5 calls live in main(); everything above it is pure so the shaping logic
is testable without a terminal (see tests/test_export_state.py).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEAL_FIELDS = ["ticket", "order", "position_id", "time", "symbol", "type",
               "entry", "volume", "price", "commission", "swap", "profit",
               "magic", "comment"]

# mt5.DEAL_TYPE_* / DEAL_ENTRY_* are small ints; spell them out so a CSV read
# months later doesn't need the MT5 constants to make sense.
DEAL_TYPE = {0: "buy", 1: "sell"}
DEAL_ENTRY = {0: "in", 1: "out", 2: "inout", 3: "out_by"}


def deal_rows(deals) -> list[dict]:
    """Shape raw MT5 deal namedtuples into flat, self-describing dict rows."""
    rows = []
    for d in deals or []:
        raw = d._asdict() if hasattr(d, "_asdict") else dict(d)
        row = {k: raw.get(k) for k in DEAL_FIELDS}
        row["time"] = datetime.fromtimestamp(
            raw["time"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        row["type"] = DEAL_TYPE.get(raw.get("type"), raw.get("type"))
        row["entry"] = DEAL_ENTRY.get(raw.get("entry"), raw.get("entry"))
        rows.append(row)
    return rows


def status_payload(account, positions, commit: str, now: datetime) -> dict:
    """The daily 'what is this box actually doing' snapshot."""
    return {
        "exported_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "commit": commit,
        "account": {
            "login": getattr(account, "login", None),
            "server": getattr(account, "server", None),
            "balance": getattr(account, "balance", None),
            "equity": getattr(account, "equity", None),
        },
        "open_positions": [
            {"ticket": p.ticket, "symbol": p.symbol,
             "type": DEAL_TYPE.get(p.type, p.type), "volume": p.volume,
             "price_open": p.price_open, "sl": p.sl, "tp": p.tp,
             "profit": p.profit}
            for p in (positions or [])
        ],
    }


def current_commit(project_dir: Path) -> str:
    """The commit this box is running — the fastest answer to 'is it stale?'."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_dir,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_csv(rows: list[dict], path: Path) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DEAL_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(days: int = 30) -> int:
    project_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_dir))
    from trader import broker_mt5
    from trader.config import Config

    cfg = Config(symbol="XAUUSD", timeframe="M30", strategy="bos")
    broker_mt5.connect(cfg)
    mt5 = broker_mt5.mt5
    try:
        now = datetime.now(timezone.utc)
        deals = mt5.history_deals_get(now - timedelta(days=days),
                                      now + timedelta(days=1))
        rows = deal_rows(deals)
        state = project_dir / "ops" / "state"
        write_csv(rows, state / f"deals-{now:%Y-%m-%d}.csv")

        payload = status_payload(mt5.account_info(), mt5.positions_get(),
                                 current_commit(project_dir), now)
        state.mkdir(parents=True, exist_ok=True)
        (state / "status.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")
    finally:
        broker_mt5.shutdown()
    print(f"exported {len(rows)} deals + status.json")
    return 0


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=30,
                    help="how many days of deal history to export (default 30)")
    raise SystemExit(main(ap.parse_args().days))

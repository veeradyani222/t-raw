"""Offline monthly cash withdrawals with unchanged BOS decisions and risk rails."""
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from run_live import GOLD
from trader.engine import on_bar
from trader.risk import RiskGuard
from trader.sim import SimBroker
from trader.strategies import bos

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs/bos-monthly-withdrawals-20260912"
START = pd.Timestamp("2025-09-12")
END = pd.Timestamp("2026-09-12")


def withdrawal_amount(balance, month_start_balance, policy):
    if policy == "none":
        return 0.
    threshold = 10000. if policy == "above_baseline" else month_start_balance
    if policy not in ("above_baseline", "positive_month"):
        raise ValueError(policy)
    return round(max(0., balance - threshold), 2)


class CashflowBroker(SimBroker):
    withdrawn = 0.

    def _settle(self, pos, price, reason):
        result = super()._settle(pos, price, reason)
        self.trades[-1]["withdrawn_to_date"] = self.withdrawn
        return result

    def withdraw(self, amount):
        assert 0 <= amount <= self._equity
        self._equity -= amount
        self.withdrawn += amount


def replay(df, policy, *, quiet=False):
    broker = CashflowBroker(df, GOLD, 10000.)
    guard = RiskGuard(GOLD.max_open_positions, GOLD.daily_loss_halt,
                      GOLD.max_drawdown_halt, GOLD.loss_baseline, GOLD.total_loss_halt)
    months, blown_at = [], None
    for month in range(12):
        start = START + pd.DateOffset(months=month)
        if start >= END:
            break
        end = min(START + pd.DateOffset(months=month + 1), END)
        indices = np.flatnonzero(((df.time >= start) & (df.time < end)).to_numpy())
        if not len(indices):
            raise ValueError(f"No bars in {start} to {end}")
        opening = broker.equity()
        trade_start = len(broker.trades)
        for i in indices:
            broker.cursor = int(i)
            broker.check_stops()
            event = on_bar(broker, guard, GOLD)
            if guard.blown and blown_at is None:
                blown_at = df.time.iloc[i]
            if event is not None and event["kind"] == "open":
                broker.attach_meta(event["ticket"], event.get("meta", {}))
        # Carry positions over monthly boundaries; same terminal mark as baseline.
        if end == END:
            for pos in list(broker.positions):
                broker._settle(pos, df.close.iloc[indices[-1]], "end")
        before_withdrawal = broker.equity()
        gain = before_withdrawal - opening
        amount = withdrawal_amount(before_withdrawal, opening, policy)
        open_positions = len(broker.positions)
        broker.withdraw(amount)
        row = dict(start=str(start), end_exclusive=str(end), opening_balance=opening,
                   trading_pnl=gain, before_withdrawal=before_withdrawal,
                   withdrawal=amount, ending_balance=broker.equity(),
                   cumulative_withdrawals=broker.withdrawn,
                   trades=len(broker.trades) - trade_start,
                   open_positions_at_withdrawal=open_positions, permanently_halted=guard.blown)
        assert abs(sum(t["profit"] for t in broker.trades[trade_start:]) - gain) < 1e-6
        assert abs(opening + gain - amount - broker.equity()) < 1e-6
        months.append(row)
        if not quiet:
            print(policy, start.date(), "pnl", round(gain, 2), "withdraw", amount,
                  "balance", round(broker.equity(), 2), flush=True)
    trades = pd.DataFrame(broker.trades)
    assert ((10000 + trades.profit.cumsum() - trades.withdrawn_to_date - trades.equity_after).abs() < 1e-6).all()
    total_net = float(trades.profit.sum())
    assert abs(10000 + total_net - broker.withdrawn - broker.equity()) < 1e-6
    summary = dict(policy=policy, trading_pnl=total_net, withdrawals=broker.withdrawn,
                   final_balance=broker.equity(), combined_cash_and_balance=broker.withdrawn + broker.equity(),
                   trades=len(trades), wins=int((trades.profit > 0).sum()), blown_at=blown_at,
                   monthly=months)
    trades.to_csv(OUT / f"{policy}-trades.csv", index=False)
    pd.DataFrame(months).to_csv(OUT / f"{policy}-monthly.csv", index=False)
    return summary, trades


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/xauusd-m30-volume-20260912.csv"
    df = pd.read_csv(source, parse_dates=["time"])
    assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
    original_signal = bos.compute_signal
    cache = {}

    def cached_signal(candles, cfg):
        # These decisions depend only on the same visible candle window/config,
        # not on positions or equity. Keep actual engine execution in every run.
        key = candles.time.iloc[-1]
        if key not in cache:
            cache[key] = original_signal(candles, cfg)
        return cache[key]

    results = []
    with patch.object(bos, "compute_signal", cached_signal):
        baseline, trades = replay(df, "none")
        saved = pd.read_csv(ROOT / "logs/m30-close-baseline-2025-09-12-trades.csv")
        assert len(trades) == len(saved)
        for column in ("profit", "entry", "exit", "lots", "sl", "tp"):
            np.testing.assert_allclose(trades[column], saved[column], atol=1e-8, rtol=0)
        assert baseline["wins"] == 128 and abs(baseline["trading_pnl"] - 3104.21) < 1e-6
        results.append(baseline)
        for policy in ("above_baseline", "positive_month"):
            result, _ = replay(df, policy)
            results.append(result)
    config = {k: v for k, v in asdict(GOLD).items() if not k.startswith(("mt5_", "telegram_"))}
    manifest = dict(config=config, data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (Path(__file__), ROOT/"run_live.py", ROOT/"trader/sim.py",
                                             ROOT/"trader/engine.py", ROOT/"trader/risk.py",
                                             ROOT/"trader/strategies/bos.py", ROOT/"trader/strategies/structure.py")},
                    signal_bars_cached=len(cache), baseline_trade_parity=True, results=results)
    (OUT / "results.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    lines = ["# BOS monthly profit withdrawals — 12 September 2026", "",
             "Same local live BOS M30 settings and data as the prior one-year replay: $10,000 start, 1% of remaining account equity per trade, $300 daily / $600 static total risk guard, periods from the 12th through the following 11th. Withdrawals occur after the final available candle of each period and affect subsequent sizing. Losses carry forward without deposits; the guard's permanent-halt state is never reset.", "",
             "Two interpretations are shown: withdraw only balance above the original $10,000 (recover losses first), or withdraw every positive month's net gain even below $10,000. The latter is a mathematical cash-flow scenario; actual payout eligibility has not been established. All amounts are gross account withdrawals before any firm profit split, payout fees or taxes. No actual withdrawal was requested or performed.", "",
             "Open positions carry across monthly boundaries, with original size/stops/targets. Withdrawal amounts use realized cash balance and ignore floating P&L. The final open position is marked to the final close as in the earlier replay. A real firm's requirement to close positions or use equity for payouts could change these results. Midnight daily anchors use the post-withdrawal balance on the next trading day; payouts are not booked as trading losses. The static $9,400 floor remains fixed as a model assumption; actual post-payout drawdown rules remain unverified.", ""]
    for result in results[1:]:
        title = "Recover $10,000 first, withdraw the excess" if result["policy"] == "above_baseline" else "Withdraw every positive month's gain"
        lines += ["## " + title, "", "| Period start | Trading P&L | Withdrawn | Balance after withdrawal |", "|---|---:|---:|---:|"]
        for row in result["monthly"]:
            lines.append(f"| {row['start'][:10]} | ${row['trading_pnl']:+.2f} | ${row['withdrawal']:.2f} | ${row['ending_balance']:.2f} |")
        lines += ["", f"Total withdrawn: ${result['withdrawals']:.2f}. Remaining account: ${result['final_balance']:.2f}. Combined: ${result['combined_cash_and_balance']:.2f}; net gain after the starting $10,000: ${result['trading_pnl']:+.2f}. Trades: {result['trades']}. Permanent halt: {result['blown_at'] or 'No'}.", ""]
    lines += ["## Verification and limitations", "",
              "The no-withdrawal control reproduced all 266 baseline trades' entries, exits, sizes, stops, targets and profits, with 128 winners and +$3,104.21. Signals were calculated by the original production signal function and cached by candle timestamp for reuse; each scenario still ran the production decision engine, position sizing, opposite-signal closes and risk guard. All monthly and trade-level accounting identities reconcile, including cumulative withdrawals.", "",
              "These are hypothetical backtest cash balances. The inherited simulator has fixed spread, signal-close fills, stop-first OHLC ties, exact stop fills across gaps, closed-balance risk checks and no commission/swap/slippage/latency. Live uses floating equity. This analysis does not verify prop payout eligibility or guarantee future earnings. No production behavior, configuration or live orders changed.", "",
              "Reproduce: `.venv\\Scripts\\python.exe -m research.bos_monthly_withdrawals`. Raw monthly tables, trade logs, source/data hashes, sanitized config and results are in `logs/bos-monthly-withdrawals-20260912/`.", ""]
    path = ROOT / "docs/2026-09-12-bos-monthly-withdrawals.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(path, flush=True)


if __name__ == "__main__":
    main()

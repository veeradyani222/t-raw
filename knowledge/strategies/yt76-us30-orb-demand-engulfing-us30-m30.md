# yt76_us30_orb_demand_engulfing on US30 M30

Source: round-6 YouTube (video DmRFA0cZ0C8)
Data from: 2018-02-27. Dev years 5, green 3.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 36 |
| unseen yr Oct23..Oct24 | -41 |
| last 2y Oct24..Oct26 | -7 |
| Sep+Oct 2026 | -187 |

Author's claim: Rules lift ORB win rate to 81% backtested

Spec:
```json
{"side": "both", "entry": [{"type": "order_block", "k": 3}, {"type": "engulfing"}], "session": {"h0": 16, "h1": 20}, "stop": {"type": "candle", "buf_atr": 0.1}, "target": {"type": "rr", "r": 2}, "max_hold": 80}
```

Yearly at 1%: {'2019': 701, '2020': 954, '2021': -261, '2022': 614, '2023': -10, '2024': -468, '2025': -282, '2026': 107}

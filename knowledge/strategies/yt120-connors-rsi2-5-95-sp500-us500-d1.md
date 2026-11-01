# yt120_connors_rsi2_5_95_sp500 on US500 D1

Source: round-6 written (video https://backtrex.com/en/backtests/connors-rsi-2-sp-500)
Data from: 2015-10-12. Dev years 8, green 5.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 0 |
| unseen yr Oct23..Oct24 | 12 |
| last 2y Oct24..Oct26 | 5 |
| Sep+Oct 2026 | 3 |

Author's claim: 71% win rate, PF 1.43, +18% in 10y, 73 trades

Spec:
```json
{"side": "both", "trend": {"type": "sma", "n": 200}, "entry": {"type": "rsi", "n": 2, "lo": 5, "hi": 95, "mode": "level"}, "stop": {"type": "pct", "pct": 5.0}, "target": {"type": "ema_cross_back", "fast": 1, "slow": 5}, "max_hold": 10}
```

Yearly at 1%: {'2016': 25, '2017': 19, '2018': -124, '2019': -31, '2020': -83, '2021': 67, '2022': 144, '2023': 36, '2024': 140, '2025': 25, '2026': 105}

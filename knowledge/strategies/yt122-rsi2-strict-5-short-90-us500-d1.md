# yt122_rsi2_strict_5_short_90 on US500 D1

Source: round-6 YouTube (video https://www.luxalgo.com/library/concept/rsi-2/)
Data from: 2015-10-08. Dev years 8, green 5.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 1 |
| unseen yr Oct23..Oct24 | 14 |
| last 2y Oct24..Oct26 | 22 |
| Sep+Oct 2026 | 7 |

Author's claim: Stricter 5/90 bands; scale out on RSI-2 spike above 90

Spec:
```json
{"side": "both", "trend": {"type": "sma", "n": 200}, "entry": {"type": "rsi", "n": 2, "lo": 5, "hi": 90, "mode": "level"}, "stop": {"type": "atr", "mult": 3}, "target": {"type": "time", "bars": 5}, "max_hold": 10}
```

Yearly at 1%: {'2016': 137, '2017': 94, '2018': -231, '2019': 9, '2020': -50, '2021': 123, '2022': -43, '2023': 43, '2024': 541, '2025': 92, '2026': 134}

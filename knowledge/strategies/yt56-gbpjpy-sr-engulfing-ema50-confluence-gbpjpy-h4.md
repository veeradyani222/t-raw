# yt56_gbpjpy_sr_engulfing_ema50_confluence on GBPJPY H4

Source: round-6 YouTube (video P4pHJaDGkHU)
Data from: 2015-02-20. Dev years 8, green 7.0. Rule: strict.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 12 |
| unseen yr Oct23..Oct24 | -2 |
| last 2y Oct24..Oct26 | -3 |
| Sep+Oct 2026 | -48 |

Author's claim: One trade made about 70k, otherwise no stats

Spec:
```json
{"side": "both", "trend": {"type": "ema", "n": 50}, "entry": [{"type": "sr_bounce", "k": 5, "tol_atr": 0.3}, {"type": "engulfing"}], "stop": {"type": "candle", "buf_atr": 0.1}, "target": {"type": "rr", "r": 2}, "max_hold": 200}
```

Yearly at 1%: {'2016': 87, '2017': -145, '2018': 221, '2019': 721, '2020': 345, '2021': 55, '2022': 225, '2023': 151, '2024': 163, '2025': -400, '2026': 133}

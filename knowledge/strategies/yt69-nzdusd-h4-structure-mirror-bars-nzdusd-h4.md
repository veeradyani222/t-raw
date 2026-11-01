# yt69_nzdusd_h4_structure_mirror_bars on NZDUSD H4

Source: round-6 YouTube (video hU98oQ41tWM)
Data from: 2015-02-03. Dev years 9, green 6.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 11 |
| unseen yr Oct23..Oct24 | 36 |
| last 2y Oct24..Oct26 | -38 |
| Sep+Oct 2026 | -63 |

Author's claim: single winning swing trade, 3:1 reward to risk

Spec:
```json
{"side": "both", "entry": [{"type": "sr_bounce", "k": 5, "tol_atr": 0.3}, {"type": "engulfing"}], "stop": {"type": "pips", "pips": 60}, "target": {"type": "rr", "r": 3}, "max_hold": 200}
```

Yearly at 1%: {'2015': -606, '2016': 375, '2017': -515, '2018': 359, '2019': 964, '2020': 326, '2021': 593, '2022': -49, '2023': 430, '2024': -525, '2025': -244, '2026': -462}

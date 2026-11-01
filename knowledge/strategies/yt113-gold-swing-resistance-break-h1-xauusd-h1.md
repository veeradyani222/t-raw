# yt113_gold_swing_resistance_break_h1 on XAUUSD H1

Source: round-6 YouTube (video lmHCH00-ehc)
Data from: 2015-03-26. Dev years 8, green 4.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 1 |
| unseen yr Oct23..Oct24 | 181 |
| last 2y Oct24..Oct26 | 104 |
| Sep+Oct 2026 | -94 |

Author's claim: No stats; qualitative swing-buy plan with global gold uptrend

Spec:
```json
{"side": "long", "trend": {"type": "htf_ema", "n": 50, "tf_mult": 24}, "entry": {"type": "donchian", "n": 20}, "stop": {"type": "swing", "n": 10, "buf_atr": 0.1}, "target": {"type": "rr", "r": 2}, "max_hold": 300}
```

Yearly at 1%: {'2016': -79, '2017': 543, '2018': -62, '2019': 479, '2020': 913, '2021': -475, '2022': -168, '2023': 246, '2024': 1611, '2025': 2095, '2026': 605}

# yt130_tsg_bb_bounce_rsi_gbpusd_h4 on GBPUSD H4

Source: round-6 written (video https://tradingstrategyguides.com/bollinger-bands-bounce-trading-strategy/)
Data from: 2015-03-19. Dev years 8, green 5.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 9 |
| unseen yr Oct23..Oct24 | 6 |
| last 2y Oct24..Oct26 | -6 |
| Sep+Oct 2026 | -33 |

Author's claim: Trend pullback to band with RSI 30-50 rising; stop 30-50 pips

Spec:
```json
{"side": "both", "trend": {"type": "ema", "n": 50}, "entry": {"type": "bb", "n": 20, "k": 2, "mode": "fade"}, "stop": {"type": "pips", "pips": 40}, "target": {"type": "bb_mid"}, "max_hold": 40}
```

Yearly at 1%: {'2016': 935, '2017': 52, '2018': -421, '2019': 215, '2020': -157, '2021': 644, '2022': -104, '2023': 348, '2024': -297, '2025': 93, '2026': -148}

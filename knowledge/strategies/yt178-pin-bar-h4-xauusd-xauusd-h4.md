# yt178_pin_bar_h4_xauusd on XAUUSD H4

Source: round-6 YouTube (video https://therighttrader.com/learn/trading-strategies/pin-bar-trading-strategy)
Data from: 2015-01-26. Dev years 9, green 5.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 6 |
| unseen yr Oct23..Oct24 | -7 |
| last 2y Oct24..Oct26 | 38 |
| Sep+Oct 2026 | 271 |

Author's claim: Page allows 4-hour bars with same wick ratios; optional 50 MA filter

Spec:
```json
{"side": "both", "trend": {"type": "ema", "n": 50}, "entry": {"type": "pinbar", "n": 10}, "stop": {"type": "candle", "buf_atr": 0.05}, "target": {"type": "rr", "r": 2}, "max_hold": 10}
```

Yearly at 1%: {'2015': 302, '2016': 366, '2017': 790, '2018': 63, '2019': -454, '2020': -178, '2021': -143, '2022': 103, '2023': -138, '2024': 15, '2025': 788, '2026': -31}

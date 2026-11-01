# yt80_us500_daily_dip_buy_marubozu on US500 D1

Source: round-6 YouTube (video yjSioAXcYwg)
Data from: 2015-03-12. Dev years 8, green 7.0. Rule: strict.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 12 |
| unseen yr Oct23..Oct24 | 13 |
| last 2y Oct24..Oct26 | -6 |
| Sep+Oct 2026 | 16 |

Author's claim: 72% win, profit factor ~2.5, max drawdown 6.9% on S&P daily

Spec:
```json
{"side": "long", "entry": {"type": "bb", "n": 20, "k": 1.5, "mode": "fade"}, "stop": {"type": "atr", "mult": 3}, "target": {"type": "bb_mid"}, "max_hold": 40}
```

Yearly at 1%: {'2016': 79, '2017': 159, '2018': 148, '2019': 48, '2020': -109, '2021': 405, '2022': 210, '2023': 196, '2024': 216, '2025': -144, '2026': -40}

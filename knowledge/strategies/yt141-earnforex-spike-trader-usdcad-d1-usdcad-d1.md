# yt141_earnforex_spike_trader_usdcad_d1 on USDCAD D1

Source: round-6 written (video https://www.earnforex.com/metatrader-expert-advisors/Spike-Trader/)
Data from: 2015-03-26. Dev years 8, green 5.0. Rule: relaxed.

| period | $/month at 1% of $10K |
|---|---|
| dev 2015..2023-10 | 4 |
| unseen yr Oct23..Oct24 | 27 |
| last 2y Oct24..Oct26 | -22 |
| Sep+Oct 2026 | -15 |

Author's claim: 16.3% profit, 14% DD, 120 trades, 57.5% winners over 9 years

Spec:
```json
{"side": "both", "entry": {"type": "pinbar", "n": 3}, "stop": {"type": "atr", "mult": 2}, "target": {"type": "time", "bars": 11}, "max_hold": 11}
```

Yearly at 1%: {'2016': 46, '2017': 41, '2018': -222, '2019': -156, '2020': -103, '2021': 373, '2022': 55, '2023': 317, '2024': -283, '2025': 157, '2026': -416}

# FundedNext $10,000 two-phase MT5 assumptions

Checked September 17, 2026 against first-party pages. The user said a $10,000
two-level account; exact product, purchase status, phase and EA add-on have not
been confirmed. Stellar Lite also has two phases, so this does not uniquely
identify Stellar 2-Step. A clarification was requested. Do not substitute one
product's fees or rules for the other.

## Completed configuration change

CHFJPY alone remains selected. `session_hour=0`, `session_entry_at_open=False`
restores entry on completion of the hour-0 H1 candle, normally near 01:00 in
the MT5 data clock. Exit remains 12 elapsed hours after actual entry, normally
near 13:00. Stop is 2×ATR14, no target. No bot/terminal process was running at
inspection and none was started. Session/live regression suite: 63 passed.

Internal controls remain 1% equity per trade, maximum 1 lot and one account-wide
position, $300 daily/$600 static entry halts based on $10,000. The commission
reserve remains $14/lot round trip pending account verification.

## Product-dependent rules

| Item | Stellar 2-Step | Stellar Lite |
|---|---|---|
| Daily allowance on $10,000 | $500 (5%) | $400 (4%) |
| Static maximum loss | $1,000 (10%); $9,000 floor | $800 (8%); $9,200 floor |
| Phase 1 target | $800 (8%) | $800 (8%) |
| Phase 2 target | $500 (5%) | $400 (4%) |
| Minimum trading days | 5 each phase | 5 each phase |

Sources: [2-Step rules](https://help.fundednext.com/en/articles/8021076-what-rules-do-i-need-to-follow-in-the-stellar-2-step-challenge),
[2-Step targets](https://help.fundednext.com/en/articles/8021071-what-is-the-profit-target-of-the-stellar-2-step-challenge),
[Lite rules](https://help.fundednext.com/en/articles/9094072-what-rules-do-i-need-to-follow-in-the-stellar-lite-challenge),
[Lite targets](https://help.fundednext.com/en/articles/9133001-what-is-the-profit-target-in-fundednext-stellar-lite).
The current 2-Step target page lists $6k/$15k and larger example accounts, not
$10k; this is another reason to confirm the actual account label rather than
assert current $10k 2-Step availability. Dollar values above are arithmetic for
the user's stated balance, not a verified purchase specification.

## Costs and clock

- [Published conditions](https://fundednext.com/general-rules/cfds/symbols-and-conditions)
  say commissions are per side and list $5 forex for 2-Step versus $7 for Lite.
  That suggests $10 versus $14 per lot round trip, subject to verifying the
  volume basis and actual entry/exit charges on the user's account. The existing
  $14 reserve is conservative relative to the stated 2-Step schedule, not a
  measured commission. Both models list 1:100 forex leverage.
- The 2.5-pip CHFJPY spread and 0.1-pip slippage assumptions remain unverified.
  Raw spreads starting at zero do not establish CHFJPY costs near 01:00/13:00.
  Need timestamped bid/ask observations, symbol contract/lot/tick specifications,
  and commission records from the actual FundedNext server. Prior local research
  identified MetaQuotes-Demo, not the user's FundedNext account.
- [Daily loss accounting](https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit)
  includes realized and floating P/L, commission, fees and swap, resetting at
  server midnight. Server clock is GMT+3 during DST and GMT+2 otherwise. The
  historical data clock has not been aligned to that server clock; do not call
  its historical hour-0 result verified FundedNext timing.
- A normal same-day 01:00–13:00 hold should avoid midnight rollover, conditional
  on confirming actual server/rollover timing and successful exit. Overnight
  delays and recovered positions can incur swaps. Swap is not in the replay.

## Automation and readiness gaps

[EA policy](https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext)
allows MT4/MT5 bots on accounts below $50,000 with a paid EA usage add-on, requires
distinct/customized strategies, and prohibits EAs incorporating third-party apps
such as Telegram/WhatsApp. The runner has Telegram alerts and inbound commands;
credentials may leave these dormant, but the integration still needs removal or
explicit clarification from FundedNext before claiming eligibility. Python order
automation is still a bot. Add-on purchase/activation has not been verified.

After funding, [risk limits](https://help.fundednext.com/en/articles/14702245-what-are-the-risk-limits-on-a-fundednext-account)
generally cap concurrent risk at 3% of initial balance; commissions/swaps are
excluded from this separate metric. One 1%-equity trade is about $100 at the
starting balance, but that fraction grows with equity. Current live sizing does
not explicitly enforce this separate initial-balance cap or account reclassification.

[News treatment for 2-Step](https://help.fundednext.com/en/articles/10701685-is-news-trading-allowed-in-the-stellar-2-step-account):
challenge has no news profit adjustment; once funded, qualifying entries/exits
within ±5 minutes of listed high-impact news count only 40% of winning profit,
while losses count fully. SL/TP triggers count. The backtests do not model this
adjustment, phase transitions, fee refunds, profit splits or withdrawals.

The live daily anchor is sampled in memory, not reconstructed from account deal
history at restart; existing equity entry halts are not exact firm-rule accounting.
The research simulator additionally uses headroom checks/synthetic guard exits
absent from live. Conservative numerical buffers alone do not prove compliance.

Conclusion: timing restored, public conditions checked, but broker costs, exact
product/add-on and operational rule parity remain unverified. No new profitability
claim or readiness claim follows from the FundedNext name alone.

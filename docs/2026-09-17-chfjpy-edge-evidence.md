# CHFJPY session strategy: rationale and evidence

Research checked September 17, 2026. No trading settings, account state or orders changed.

## Assessment

Time-of-day FX trading is an established research topic with public practitioner use. That supports a testable hypothesis, but does not independently validate our exact CHFJPY rule. The available evidence cannot separate its recent profit into broad long exposure, an incremental timing advantage, stop/risk-path effects, and selection noise. A claim that the strategy is dependable without an uptrend would be unsupported.

The deployed selection is long-only. The strategy code has no trend filter, trend reversal detector or short signal. It buys after a completed H1 candle labelled hour 0, normally near 01:00 on the broker-data clock. The timed exit is 12 hours after actual entry, normally near 13:00, unless the stop closes it first. The stop is twice simple ATR14; it adjusts the stop distance to recent movement, rather than establishing why the next 12 hours should rise. Broker clock/DST mapping to named market sessions remains unverified. Sources: [signal](../trader/strategies/session.py), [runner](../run_live.py), [timed exit](../trader/live.py).

## Published rationale

Breedon and Ranaldo examine ten years of high-frequency FX data and report local-trading-hour return and order-flow patterns. Their proposed explanation is that local participants tend to buy foreign currencies during their own business hours. This supplies a possible economic rationale for researching clock-based signals; it does not prescribe CHFJPY hour 0 / hold 12 / ATR2. [SNB Working Paper 2011-04](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04).

Krohn, Mueller and Whelan study intraday reversals around benchmark fixes. Their 2024 Journal of Finance paper finds U.S.-dollar appreciation before major fixes and reversals afterward, with evidence consistent with dealer inventory risk. This is another reason timing may matter, but a USD-based benchmark-fixing pattern cannot be transferred mechanically to a CHFJPY cross or an arbitrary broker timezone. [Published paper](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13306); [authors' Bank of Canada summary](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/).

The mechanism is plausible because trading demand can recur at scheduled times and dealers must absorb it. The hypothesis for our specific rule would need to be more precise: during the exact implemented window, CHF must tend to strengthen against JPY by enough to cover trading costs, beyond what comparable long exposure already earns. No source located establishes that proposition for our parameters.

## Do people trade this family?

Spectra Markets' April 24, 2025 article describes firsthand use during 2009-2017 of systematic EURUSD and USDJPY positions that changed direction by session. The author also describes a historical change in USDJPY's time-of-day behavior. This is evidence of practitioner use of the architecture, not an independently audited record or proof for our instrument/hours. [TOD Flipper and Supply Pains](https://www.spectramarkets.com/amfx/tod-flipper-and-supply-pains/).

A bounded search for CHFJPY with time-of-day, midnight, hour 0, 12-hour and ATR terms did not locate independently verified performance for our exact rules. Different pairs, filters, scalpers, or entry times are not exact replications. Failure to locate a match is not proof nobody trades it.

## Local provenance and regime evidence

The archived `665430a:wf_search.py` contains 144 hour/holding-period/direction configurations (24 hours x 3 holds x 2 directions). ATR14 and its 2x multiplier are fixed in that search. The recorded original deployment was USDJPY hour 6, while later research transferred the hour-0 long/12-hour candidate across several JPY pairs without retuning those timing parameters per pair. Picking CHFJPY after seeing the pair results still creates a selection issue. The surviving files do not fully establish which earlier fold selected hour 0 for the AUDJPY reference. See the [local provenance and trend audit](2026-09-17-chfjpy-provenance-and-trend.md).

Trying many variants and retaining a strong historical result can produce an apparent edge even when its future performance is poor. This is the backtest-overfitting problem studied by Bailey and colleagues; a generic time-of-day explanation does not eliminate it. [Authors' paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

Our later $10,000 cost-and-guard study has four profitable calendar years out of ten and six losing/headroom-limited years. Its annual arithmetic mean is +$157.05, versus +$5,294.44 in the strong latest twelve months. Calendar 2025 underlying CHFJPY rose about 14.02%, but the fresh annual strategy run lost $532.96 and stopped fitting new trades into its remaining static headroom in early February. The full-year chart therefore is not the same exposure as the account's executed trades. These observations neither prove a causal trend explanation nor refute a possible intraday effect. [Account study](2026-09-13-jpy-account-comparison.md).

## What would distinguish the hypotheses

These are research requirements, not results already established:

1. Fix the broker-to-UTC/session/DST mapping and compare the same executable hours across feeds.
2. Compare the locked rule with exposure- and risk-matched long benchmarks, the complementary window, and predeclared alternate windows. Do not select another winner from the same data and call that validation.
3. Report costs, returns and drawdowns separately in rising, falling and sideways conditions defined from information available before entry. Future trend labels may be used descriptively, never as an executable signal.
4. Preserve every tried configuration and evaluate statistical uncertainty accounting for selection. Treat reused historical data as research, not untouched validation.
5. Freeze the rule and evaluate genuinely subsequent demo trades, including realized spreads, slippage, rejects and clock alignment. Define review/loss criteria before seeing the new results.

The currently supported conclusion is a researched strategy family and a locally selected, still-unproven CHFJPY implementation. Its long-only rule can keep buying in a downtrend until entry controls intervene; a stop or account loss rail does not certify that its expected return remains positive.

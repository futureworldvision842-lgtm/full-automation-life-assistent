# MQ3 Evidence-First Trading Engine Research

Updated: 2026-08-19

## Outcome

The platform should not attempt to become “expert” by copying every public bot or stacking every indicator. Most technical indicators are correlated transformations of the same price and volume series. Counting them as independent confirmations creates false confidence, while copying an unverified repository imports unknown assumptions, licensing risk, security risk, and potentially severe lookahead bias.

The implemented direction is a smaller, auditable pipeline:

1. Obtain attributable broker quotes and completed OHLCV bars.
2. Check timestamp freshness, spread, and minimum warm-up history.
3. Compute causal indicator families and market regime.
4. Generate a conditional research candidate from closed bars.
5. Use the indicator ensemble only as an explanation and conflict blocker.
6. Require independent calendar, validation, drawdown, account, authorization, and broker gates.
7. Record the owner's decision without treating it as permission to bypass a failed gate.
8. Keep a durable audit trail; never invent missing market evidence.

No indicator, AI response, public context feed, or owner “YES” can directly authorize an order in the current build.

## Platforms and libraries reviewed

### Freqtrade

Useful ideas adopted:

- Explicit separation of backtest, dry-run, and live stages.
- Lookahead-analysis and recursive-analysis checks.
- Protections such as cooldown, max-drawdown, stop-loss guard, and low-profit-pair locks.
- Backtests must model fees and cannot replace forward/dry-run testing.

Not copied wholesale: MQ3 is MT5/fleet-oriented and already has its own admission and account-risk layers. Importing a second execution framework would duplicate state and create conflicting order authority.

Sources:

- <https://docs.freqtrade.io/en/stable/lookahead-analysis/>
- <https://www.freqtrade.io/en/stable/strategy-101/>
- <https://docs.freqtrade.io/en/stable/plugins/>
- <https://www.freqtrade.io/en/stable/backtesting/>

### QuantConnect LEAN

Useful idea adopted: event-driven separation of data, signal/alpha, portfolio construction, risk management, execution, and brokerage. MQ3 now follows the same general separation at a smaller scale: sources → diagnostics → candidate → validation/risk/admission → broker/audit.

Source: <https://github.com/QuantConnect/Lean>

### vectorbt

Useful idea retained for the next validation phase: fast parameter and portfolio experiments, with vectorized and event-driven simulation paths. It supports common indicator families and TA-Lib integration. It is a research tool, not evidence that a strategy is profitable.

Sources:

- <https://vectorbt.dev/>
- <https://vectorbt.dev/getting-started/features/>

### TA-Lib

TA-Lib documents a large catalog of indicators. Its value is consistent indicator implementation, not an automatic strategy. It also documents unstable/warm-up periods for some functions. MQ3 therefore requires at least 220 completed bars for the EMA-200 ensemble and exposes the exact warm-up failure instead of silently filling missing values.

Sources:

- <https://ta-lib.github.io/>
- <https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html>
- <https://ta-lib.github.io/d_api/d_api.html>

## Implemented indicator design

The engine deliberately groups indicators by information family so related transforms are not counted as independent probabilities.

### Trend family

- EMA 20/50/200 alignment
- MACD 12/26/9 histogram normalized by ATR
- DMI direction
- ADX strength damping

### Momentum family

- RSI 14
- Stochastic 14/3
- Ten-bar rate of change normalized by ATR percentage

### Price-structure family

- Prior 20-bar Donchian channel, shifted by one bar to avoid using the current bar to define its own breakout
- Closed-candle range position
- Closed-candle body normalized by ATR

### Activity family

- Twenty-bar tick-volume z-score
- Candle-direction × tick-volume activity proxy

This is explicitly not true aggressor CVD, global order flow, or named-participant activity. Broker tick volume cannot identify a bank, fund, “whale,” or insider.

### Regime detection

The engine classifies:

- `TRENDING_NORMAL`
- `TRENDING_HIGH_VOL`
- `RANGE_NORMAL`
- `RANGE_LOW_VOL`
- `TRANSITION_MIXED`
- `VOLATILITY_SHOCK`

It uses ADX, Kaufman efficiency ratio, ATR relative to its 100-bar median, and Bollinger width relative to its 100-bar median. A volatility shock or cross-family conflict becomes an execution blocker; neither state manufactures a counter-trade.

## Bias and overfitting controls

Academic evidence supports systematic testing of technical patterns, but it also shows why backtest results need skepticism. Lo, Mamaysky, and Wang studied automated recognition of technical patterns; that does not turn patterns into guarantees. Bailey and co-authors developed a probability-of-backtest-overfitting framework. The large-scale “Replicating Anomalies” study found that many reported effects weaken or disappear under more rigorous assumptions and multiple-testing hurdles.

Sources:

- <https://www.nber.org/papers/w7613>
- <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253>
- <https://academic.oup.com/rfs/article/33/5/2019/5236964>

Required validation sequence for any strategy before considering funded live use:

1. Point-in-time data and completed bars only.
2. Explicit spread, commission, swap, slippage, gaps, partial fills, and broker minimum-distance rules.
3. Lookahead and recursive-indicator tests.
4. Purged chronological train/validation/test splits; never random row shuffling.
5. Walk-forward evaluation across multiple market regimes.
6. Parameter-stability checks and a report of every trial, including failed variants.
7. Multiple-testing/selection-bias controls, preferably including PBO-style analysis.
8. Frozen strategy version and reproducible validation receipt.
9. Shadow mode, then broker demo forward test.
10. Only after adequate sample size: a tightly capped canary account, if the operator deliberately authorizes it and all independent gates pass.

Buying four prop accounts does not diversify a single correlated strategy. If the same model trades all accounts, one failure mode can hit all four simultaneously. Account sizing and copier allocation must therefore be downstream of portfolio-level exposure and correlation limits.

## Retired or prohibited claims

The final evidence UI retires these unsupported surfaces:

- Synthetic “market weather” probabilities.
- Maritime/DEFCON scores without a connected attributable source.
- “Dark pool,” named bank/fund/whale, or insider attribution from OHLCV.
- True CVD/DOM claims without trade-side/order-book data.
- Arbitrary Wyckoff or “Judas” intent labels derived from one candle.
- Synthetic future/ghost candles presented beside observations.
- Any win-rate, profit, or risk-free promise without an out-of-sample calibration artifact.

Official/public context (for example, CFTC positioning, official policy releases, or single-venue crypto depth) remains clearly labelled by source, timestamp, scope, and execution role. It is display-only unless a separately validated strategy explicitly includes it.

## Current readiness boundary

The current system is suitable for evidence display, conditional signal research, what-if sensitivity analysis, WhatsApp review/command workflows, demo telemetry, and continued validation. It is not ready for unattended funded execution because the complete upcoming high-impact calendar, attributable cross-market/order-flow data, and a current strategy-validation receipt are not connected. The correct behavior is to show those gaps and block—not replace them with invented data.


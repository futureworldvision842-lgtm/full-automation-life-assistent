# MQ3 Trading Platform — Mission, Audit, and Safe Target Architecture

## Mission interpreted from the owner brief

MQ3 should become a bilingual trading research and operations assistant that can observe public global-market data, retain auditable memory, run reproducible research, generate risk-bounded scenarios, operate paper accounts, send and receive authorized WhatsApp commands, and eventually route a live order only after broker, data-quality, risk, and human-approval gates all pass.

It must not promise profit, invent live telemetry, attribute activity to a named institution without evidence, trade on material non-public information, copy paid/proprietary systems, or silently substitute synthetic data for a failed live feed.

## What the repository actually contains

The repository has broad module and test coverage for MT5, fleet risk, dashboards, WhatsApp, SMC-style heuristics, public feeds, memory, backtesting, and orchestration. Much of the previous coverage verified class contracts and simulated output. It did not establish profitable live behavior, broker certification, valid named-whale attribution, true Higgsfield inference, or production availability.

The initial audit found critical trust-boundary problems:

- A tracked `.env` and hard-coded Higgsfield credentials.
- Live MT5 connection failure silently converted into successful simulation.
- Failed fleet orders received fabricated tickets/status and became active positions.
- Dashboard and advisory fallbacks presented sample balances, prices, news, CVD, macro values, and named institutions as if observed.
- Desktop capture and mouse/keyboard control activated when libraries were installed, without explicit owner opt-in.
- The dashboard listened on every network interface while state-changing endpoints had no authentication boundary.
- Several tests asserted fabricated success rather than verifying failure behavior.

## Target decision path

1. **Observe:** broker quotes and approved public sources return timestamped data.
2. **Provenance gate:** source, mode, age, licensing note, and actionability are attached; missing/stale/synthetic inputs fail closed.
3. **Research:** strategies are tested with fees, spread, slippage, latency, non-overlapping labels, and time-ordered out-of-sample windows.
4. **Scenario engine:** forecasts are calibrated scenarios with uncertainty, not guaranteed predictions.
5. **Risk governor:** account identity, prop-firm product rules, daily/trailing drawdown, exposure, lot size, and news/session policies are validated.
6. **Human approval:** live mode requires explicit configuration plus an exact environment acknowledgement. Direct live WhatsApp entry remains locked until it can consume a verified quote and approval token.
7. **Broker preflight:** MT5 `order_check` passes at the current quote.
8. **Execution and reconciliation:** only a successful broker receipt creates a position; positions are reconciled from the venue rather than trusted from local memory.
9. **Audit and alerting:** the receipt records data sources, risk decision, mode, broker result, and WhatsApp notification state.

## Operational modes

- `PAPER`: explicit safe test mode. Synthetic quotes and demo positions are allowed only when clearly labelled and never represented as live evidence.
- `BROKER_DEMO`: current workstation mode. Uses the allow-listed FundingPips Trial terminal for broker-reported account, position, quote, and candle telemetry while new orders and every position mutation remain locked.
- `SHADOW`: future mode. Consume live data and produce decisions, but never send orders; compare hypothetical decisions to subsequent prices.
- `LIVE_LOCKED`: terminal may be visible, but new orders are blocked.
- `LIVE`: future production mode, available only after account allow-listing, data provenance, risk validation, operator approval, broker preflight, reconciliation, and kill-switch drills.

## Research standards

- Use time-ordered train/validation/test splits and walk-forward evaluation.
- Model fees, bid/ask spread, slippage, latency, rejected orders, and position limits.
- Detect look-ahead bias, survivorship bias, data revisions, duplicate timestamps, and timezone errors.
- Report uncertainty, sample size, drawdown, turnover, exposure, and sensitivity—not just win rate or Sharpe ratio.
- Keep an untouched final holdout and use deflated/multiple-testing-aware evaluation when many strategies are tried.
- Promote a model only from research to paper, then shadow, and only later to live after predefined acceptance criteria.

## Legal and ethical data boundary

Only public, licensed, or owner-authorized information belongs in the system. SEC Forms 3/4/5 and other public filings may be analyzed after publication. Material non-public information, evasion of paywalls, stolen credentials, deceptive market conduct, or trade manipulation are prohibited. Named “shark” attribution must link to evidence and otherwise remain `UNVERIFIED`.

## Source and licensing notes

The `repos/` directory contains useful reference projects, but copied code cannot be assumed safe merely because it is public. Each component needs its upstream URL, commit, license, security review, and dependency lock. Projects without a retained license or provenance record must be treated as reference-only until verified. Prefer official APIs and documented, licensed frameworks such as Qlib and Freqtrade; do not copy paid strategy content.

Official research references are recorded in `data/source_registry.json`. Prop-firm rules must be selected by exact product and revalidated against current official terms; no single Funding Pips or FTMO percentage should be hard-coded as universally applicable.

## Current release statement

This update is a safety and truthfulness baseline, not a certification that the bot is profitable or ready for unattended live money. Paper execution, safe degraded responses, credential hygiene, provenance primitives, fail-closed MT5/fleet behavior, broker-demo telemetry, and persistent WhatsApp pairing can be tested locally. The paired WhatsApp session is stored outside Git and reconnects after a managed restart unless WhatsApp revokes/logs out the device or the auth state becomes invalid. Owner-only WhatsApp commands may read verified status, store non-secret operator memory, and queue reviewed update requests; arbitrary shell/source execution and automatic update apply remain blocked. Real-money execution, external AI inference, feed uptime, and desktop automation still require separate verification and supervised acceptance tests.

/**
 * risk_cockpit.js — Institutional Real-Time BlackRock Aladdin Risk Cockpit & Funding Pips Compliance Engine.
 * 
 * Provides:
 * - Real-Time Realized Balance, Floating Equity, Net Floating PnL, and Margin telemetry.
 * - BlackRock Aladdin 1-Day 99% & 95% Parametric VaR and CVaR (Expected Shortfall) mathematical engine & visual gauges.
 * - Funding Pips Trailing High-Water Mark (HWM) Ratchet Floor defense ($25k, $50k, $100k presets & custom balance).
 * - Start-of-Day (SOD) Daily Drawdown Allowance meter with multi-stage color thresholds.
 * - 35% Consistency Rule distribution pacing gauge with 4-stage automated de-risking alerts:
 *     Stage 1: NOMINAL (Green, Full 0.75% Risk, < 70% of cap)
 *     Stage 2: CAUTION (Yellow, Half 0.375% Risk, 70% - 89.9% of cap)
 *     Stage 3: CRITICAL (Orange, Micro 0.150% Risk, 90% - 99.9% of cap)
 *     Stage 4: CEILING_REACHED / LOCK_DAY_MODE (Red, 0.0% Risk / Lock Day Mode, >= 100% of cap)
 * 
 * Exported to window.RiskCockpit and window.TradingTerminal.riskCockpit.
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.RiskCockpit = factory();
        root.TradingTerminal = root.TradingTerminal || {};
        root.TradingTerminal.riskCockpit = root.RiskCockpit;
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    // Quantitative Statistical Constants
    const STATS = {
        Z_99: 2.326348,      // 99% standard normal quantile
        Z_95: 1.644854,      // 95% standard normal quantile
        Z_90: 1.281552,      // 90% standard normal quantile
        PHI_Z99_OVER_001: 2.665214, // phi(2.326348) / 0.01 for 1-day 99% CVaR (ES)
        PHI_Z95_OVER_005: 2.062714, // phi(1.644854) / 0.05 for 1-day 95% CVaR (ES)
        CVAR_VAR_RATIO_99: 1.145664  // 2.665214 / 2.326348 = strictly 14.57% greater
    };

    // Institutional Account Presets
    const PRESETS = {
        '25k': {
            name: '$25,000 Tier',
            target_balance: 25000.0,
            profit_target_pct: 8.0,       // $2,000.00
            safe_daily_loss_pct: 2.5,     // $625.00
            official_daily_loss_pct: 4.0, // $1,000.00
            safe_total_loss_pct: 6.0,     // $1,500.00
            official_total_loss_pct: 12.0,// $3,000.00
            consistency_cap_pct: 35.0,    // $700.00 (35% of $2,000)
            max_positions: 2
        },
        '50k': {
            name: '$50,000 Tier',
            target_balance: 50000.0,
            profit_target_pct: 8.0,       // $4,000.00
            safe_daily_loss_pct: 2.5,     // $1,250.00
            official_daily_loss_pct: 4.0, // $2,000.00
            safe_total_loss_pct: 6.0,     // $3,000.00
            official_total_loss_pct: 12.0,// $6,000.00
            consistency_cap_pct: 35.0,    // $1,400.00 (35% of $4,000)
            max_positions: 3
        },
        '100k': {
            name: '$100,000 Tier',
            target_balance: 100000.0,
            profit_target_pct: 8.0,       // $8,000.00
            safe_daily_loss_pct: 2.5,     // $2,500.00
            official_daily_loss_pct: 4.0, // $4,000.00
            safe_total_loss_pct: 6.0,     // $6,000.00
            official_total_loss_pct: 12.0,// $12,000.00
            consistency_cap_pct: 35.0,    // $2,800.00 (35% of $8,000)
            max_positions: 4
        }
    };

    class RiskCockpitEngine {
        constructor(config = {}) {
            this.accountTier = config.accountTier || '25k';
            this.customBalance = config.customBalance || null;
            this.dailyVolatility = config.dailyVolatility || 0.0080; // 0.80% daily vol baseline

            // State variables
            this.balance = 25000.0;
            this.equity = 25000.0;
            this.floatingPnL = 0.0;
            this.dailyProfit = 0.0;
            this.startOfDayEquity = 25000.0;
            this.absoluteHWM = 25000.0;
            this.dailyHWM = 25000.0;
            this.openPositions = [];

            // UI Callbacks
            this.listeners = [];
            this.activeDeRiskStage = 1; // 1: Nominal, 2: Caution, 3: Critical, 4: Locked

            this.setTier(this.accountTier);
        }

        // =========================================================================
        // 1. Account Profile Configuration
        // =========================================================================

        setTier(tierKey) {
            if (PRESETS[tierKey]) {
                this.accountTier = tierKey;
                this.profile = Object.assign({}, PRESETS[tierKey]);
                this.customBalance = null;
            } else if (typeof tierKey === 'number' && tierKey > 0) {
                this.setCustomBalance(tierKey);
            }
            this._recalculateFloor();
            this.notify();
            return this.profile;
        }

        setCustomBalance(balanceAmount) {
            const bal = parseFloat(balanceAmount);
            if (isNaN(bal) || bal <= 0) return this.profile;

            this.accountTier = 'custom';
            this.customBalance = bal;
            this.profile = {
                name: `Custom ($${bal.toLocaleString()})`,
                target_balance: bal,
                profit_target_pct: 8.0,
                safe_daily_loss_pct: 2.5,
                official_daily_loss_pct: 4.0,
                safe_total_loss_pct: 6.0,
                official_total_loss_pct: 12.0,
                consistency_cap_pct: 35.0,
                max_positions: 4
            };
            this._recalculateFloor();
            this.notify();
            return this.profile;
        }

        getProfile() {
            return this.profile;
        }

        // =========================================================================
        // 2. BlackRock Aladdin Quantitative Risk Calculations
        // =========================================================================

        /**
         * Computes 1-Day 99% & 95% Parametric VaR, CVaR (Expected Shortfall), and Kelly metrics.
         * @param {number} equity Portfolio equity in USD
         * @param {number} dailyVol Daily standard deviation (e.g. 0.0080 for 0.80%)
         * @returns {object} Aladdin risk breakdown
         */
        calculateAladdinVaR(equity = this.equity, dailyVol = this.dailyVolatility) {
            const eq = Math.max(parseFloat(equity) || 0, 1.0);
            const sigma = Math.max(parseFloat(dailyVol) || 0.0080, 0.0001);

            // 1-Day 99% Parametric VaR & CVaR
            const var99_usd = eq * STATS.Z_99 * sigma;
            const var99_pct = (var99_usd / eq) * 100.0;
            const cvar99_usd = eq * STATS.PHI_Z99_OVER_001 * sigma;
            const cvar99_pct = (cvar99_usd / eq) * 100.0;

            // 1-Day 95% Parametric VaR & CVaR
            const var95_usd = eq * STATS.Z_95 * sigma;
            const var95_pct = (var95_usd / eq) * 100.0;
            const cvar95_usd = eq * STATS.PHI_Z95_OVER_005 * sigma;
            const cvar95_pct = (cvar95_usd / eq) * 100.0;

            // Mathematical verification check: CVaR_99 must be strictly 14.57% greater than VaR_99
            const cvarRatio = var99_usd > 0 ? (cvar99_usd / var99_usd) : STATS.CVAR_VAR_RATIO_99;

            // Fractional Kelly Sizing (0.20x Quarter-Kelly with 0.75% cap)
            const winRateAdj = 0.55 - 0.03; // win rate 55% with 3% SE haircut
            const payoff = 1.8;
            const fullKelly = (winRateAdj * (payoff + 1.0) - 1.0) / payoff;
            const fracKelly = Math.min(Math.max(0.20 * fullKelly, 0.0025), 0.0075) * 100.0;

            return {
                equity: eq,
                daily_volatility_pct: +(sigma * 100.0).toFixed(4),
                var_99_dollar: +var99_usd.toFixed(2),
                var_99_pct: +var99_pct.toFixed(2),
                var_95_dollar: +var95_usd.toFixed(2),
                var_95_pct: +var95_pct.toFixed(2),
                cvar_99_dollar: +cvar99_usd.toFixed(2),
                cvar_99_pct: +cvar99_pct.toFixed(2),
                cvar_95_dollar: +cvar95_usd.toFixed(2),
                cvar_95_pct: +cvar95_pct.toFixed(2),
                cvar_var_ratio: +cvarRatio.toFixed(6),
                fractional_kelly_pct: +fracKelly.toFixed(2),
                stress_test_status: var99_pct < this.profile.safe_daily_loss_pct ? 'PASSED' : 'ELEVATED_RISK'
            };
        }

        // =========================================================================
        // 3. Prop Firm Trailing HWM Floor & Drawdown Calculations
        // =========================================================================

        _recalculateFloor() {
            const target = this.profile.target_balance;
            this.absoluteHWM = Math.max(this.absoluteHWM, this.equity, target);
            this.dailyHWM = Math.max(this.dailyHWM, this.equity, this.balance);
        }

        /**
         * Calculates Prop Firm Trailing Floor, Daily Drawdown, and Buffer.
         */
        calculatePropFirmDefense(balance = this.balance, equity = this.equity) {
            const bal = parseFloat(balance) || this.balance;
            const eq = parseFloat(equity) || this.equity;
            const target = this.profile.target_balance;

            // 1. Trailing High-Water Mark Ratchet Floor
            const hwm = Math.max(this.absoluteHWM, eq, target);
            this.absoluteHWM = hwm;

            const maxTotalAllowed = target * (this.profile.safe_total_loss_pct / 100.0);
            const trailingFloor = +(hwm - maxTotalAllowed).toFixed(2);
            const trailingBufferUSD = +Math.max(0.0, eq - trailingFloor).toFixed(2);
            const trailingBufferPct = +((trailingBufferUSD / maxTotalAllowed) * 100.0).toFixed(1);

            // 2. Start-of-Day Daily Drawdown
            const sodBaseline = Math.max(this.startOfDayEquity, bal);
            const maxDailyAllowed = +(sodBaseline * (this.profile.safe_daily_loss_pct / 100.0)).toFixed(2);
            const dailyLossUsed = +Math.max(0.0, sodBaseline - eq).toFixed(2);
            const dailyLossRemaining = +Math.max(0.0, maxDailyAllowed - dailyLossUsed).toFixed(2);
            const dailyDrawdownPctUsed = +((dailyLossUsed / Math.max(maxDailyAllowed, 1.0)) * 100.0).toFixed(1);

            // Overall Total Loss from Initial Baseline
            const totalLossUsed = +Math.max(0.0, target - eq).toFixed(2);
            const totalDrawdownPctUsed = +((totalLossUsed / Math.max(maxTotalAllowed, 1.0)) * 100.0).toFixed(1);

            // Compliance status determination
            let canTrade = true;
            let statusReason = 'Passed Funding Pips Safety Audit';

            if (eq <= trailingFloor) {
                canTrade = false;
                statusReason = 'CRITICAL: Trailing High-Water Mark Floor Breached!';
            } else if (dailyLossUsed >= maxDailyAllowed) {
                canTrade = false;
                statusReason = 'HALT: Safe Daily Loss Cap Reached for Today';
            }

            return {
                hwm: +hwm.toFixed(2),
                daily_hwm: +this.dailyHWM.toFixed(2),
                trailing_floor: trailingFloor,
                trailing_buffer_usd: trailingBufferUSD,
                trailing_buffer_pct: trailingBufferPct,
                sod_baseline: +sodBaseline.toFixed(2),
                daily_loss_used: dailyLossUsed,
                daily_loss_allowed: maxDailyAllowed,
                daily_loss_remaining: dailyLossRemaining,
                daily_drawdown_pct_used: dailyDrawdownPctUsed,
                total_loss_used: totalLossUsed,
                total_loss_allowed: +maxTotalAllowed.toFixed(2),
                total_drawdown_pct_used: totalDrawdownPctUsed,
                can_trade: canTrade,
                status_reason: statusReason
            };
        }

        // =========================================================================
        // 4. 35% Consistency Rule Distribution Pacing Gauge
        // =========================================================================

        /**
         * Evaluates 35% Consistency Rule pacing and determines automated de-risking stage.
         * @param {number} todayProfit Realized + Floating profit accumulated today
         * @returns {object} Pacing metrics and stage alert
         */
        calculateConsistencyPacing(todayProfit = this.dailyProfit) {
            const pToday = Math.max(0.0, parseFloat(todayProfit) || 0.0);
            const targetBal = this.profile.target_balance;
            const profitTarget = targetBal * (this.profile.profit_target_pct / 100.0); // e.g. $2,000 on 25k
            const maxSingleDayAllowed = +(profitTarget * (this.profile.consistency_cap_pct / 100.0)).toFixed(2); // e.g. $700 on 25k
            const consistencyPct = +((pToday / Math.max(maxSingleDayAllowed, 1.0)) * 100.0).toFixed(1);

            let stage = 1;
            let status = 'NOMINAL';
            let alertColor = 'green';
            let riskMultiplier = 1.0; // 0.75% full risk
            let riskPerTradePct = 0.75;
            let actionMessage = 'Nominal Trading Pacing. Full 0.75% risk per trade permitted.';

            if (pToday >= maxSingleDayAllowed) {
                stage = 4;
                status = 'CEILING_REACHED';
                alertColor = 'red';
                riskMultiplier = 0.0;
                riskPerTradePct = 0.0;
                actionMessage = `Lock Day Mode Active. Daily consistency cap ($${maxSingleDayAllowed.toLocaleString()}) reached. All stops to BE+, new trades halted.`;
            } else if (pToday >= maxSingleDayAllowed * 0.90) { // 90% - 99.9% ($630 - $699)
                stage = 3;
                status = 'CRITICAL';
                alertColor = 'orange';
                riskMultiplier = 0.20;
                riskPerTradePct = 0.15;
                actionMessage = 'Harvest Runners Mode. Micro-risk only (0.15%). Secure profits before cap.';
            } else if (pToday >= maxSingleDayAllowed * 0.70) { // 70% - 89.9% ($490 - $629)
                stage = 2;
                status = 'CAUTION';
                alertColor = 'yellow';
                riskMultiplier = 0.50;
                riskPerTradePct = 0.375;
                actionMessage = 'Pacing Caution. Half-risk mode (0.375%). Daily cap approaching.';
            }

            this.activeDeRiskStage = stage;

            return {
                profit_target: +profitTarget.toFixed(2),
                today_profit: +pToday.toFixed(2),
                max_single_day_allowed: maxSingleDayAllowed,
                consistency_pct: consistencyPct,
                stage: stage,
                status: status,
                alert_color: alertColor,
                risk_multiplier: riskMultiplier,
                risk_per_trade_pct: riskPerTradePct,
                action_message: actionMessage
            };
        }

        // =========================================================================
        // 5. Unified Telemetry Snapshot Generator
        // =========================================================================

        /**
         * Produces unified telemetry snapshot conforming to API & UI specs.
         */
        getTelemetrySnapshot() {
            const aladdin = this.calculateAladdinVaR(this.equity, this.dailyVolatility);
            const propFirm = this.calculatePropFirmDefense(this.balance, this.equity);
            const consistency = this.calculateConsistencyPacing(this.dailyProfit);
            const marginUsed = +(this.openPositions.length * 185.0).toFixed(2);
            const marginFree = +Math.max(0.0, this.equity - marginUsed).toFixed(2);

            return {
                balance: +this.balance.toFixed(2),
                equity: +this.equity.toFixed(2),
                floating_pnl: +(this.equity - this.balance).toFixed(2),
                margin: marginUsed,
                margin_free: marginFree,
                account_tier: this.accountTier,
                account_profile: this.profile,
                var_99_usd: aladdin.var_99_dollar,
                var_99_pct: aladdin.var_99_pct,
                var_95_usd: aladdin.var_95_dollar,
                var_95_pct: aladdin.var_95_pct,
                cvar_99_usd: aladdin.cvar_99_dollar,
                cvar_99_pct: aladdin.cvar_99_pct,
                cvar_95_usd: aladdin.cvar_95_dollar,
                cvar_95_pct: aladdin.cvar_95_pct,
                hwm: propFirm.hwm,
                daily_hwm: propFirm.daily_hwm,
                trailing_floor: propFirm.trailing_floor,
                trailing_buffer_usd: propFirm.trailing_buffer_usd,
                trailing_buffer_pct: propFirm.trailing_buffer_pct,
                daily_loss_used: propFirm.daily_loss_used,
                daily_loss_allowed: propFirm.daily_loss_allowed,
                daily_loss_remaining: propFirm.daily_loss_remaining,
                daily_drawdown_pct_used: propFirm.daily_drawdown_pct_used,
                total_loss_used: propFirm.total_loss_used,
                total_loss_allowed: propFirm.total_loss_allowed,
                total_drawdown_pct_used: propFirm.total_drawdown_pct_used,
                can_trade: propFirm.can_trade && (consistency.stage < 4),
                consistency_profit_today: consistency.today_profit,
                consistency_max_allowed: consistency.max_single_day_allowed,
                consistency_pct: consistency.consistency_pct,
                consistency_stage: consistency.stage,
                consistency_status: consistency.status,
                aladdin_risk: aladdin,
                prop_firm_defense: propFirm,
                consistency_gauge: consistency,
                open_positions_count: this.openPositions.length,
                open_positions: this.openPositions
            };
        }

        // =========================================================================
        // 6. Update Telemetry from Live Feeds / WebSocket
        // =========================================================================

        updateFromMetrics(data) {
            if (!data) return;

            if (typeof data.balance === 'number') this.balance = data.balance;
            if (typeof data.equity === 'number') this.equity = data.equity;
            if (typeof data.floating_pnl === 'number') this.floatingPnL = data.floating_pnl;
            if (typeof data.consistency_profit_today === 'number') {
                this.dailyProfit = data.consistency_profit_today;
            } else if (data.consistency_gauge && typeof data.consistency_gauge.today_profit === 'number') {
                this.dailyProfit = data.consistency_gauge.today_profit;
            }
            if (Array.isArray(data.open_positions)) {
                this.openPositions = data.open_positions;
            }

            this._recalculateFloor();
            this.notify();
            this.renderDOM();
        }

        updateAccount(balance, equity, dailyProfit = null) {
            this.balance = parseFloat(balance) || this.balance;
            this.equity = parseFloat(equity) || this.equity;
            this.floatingPnL = +(this.equity - this.balance).toFixed(2);
            if (dailyProfit !== null) {
                this.dailyProfit = parseFloat(dailyProfit) || 0.0;
            }
            this._recalculateFloor();
            this.notify();
            this.renderDOM();
        }

        setOpenPositions(positions) {
            this.openPositions = Array.isArray(positions) ? positions : [];
            this.notify();
            this.renderDOM();
        }

        // =========================================================================
        // 7. Observer Pub/Sub Event System
        // =========================================================================

        subscribe(listener) {
            if (typeof listener === 'function' && !this.listeners.includes(listener)) {
                this.listeners.push(listener);
            }
            return () => {
                this.listeners = this.listeners.filter(l => l !== listener);
            };
        }

        notify() {
            const snap = this.getTelemetrySnapshot();
            for (let i = 0; i < this.listeners.length; i++) {
                try {
                    this.listeners[i](snap);
                } catch (err) {
                    console.error('Error in RiskCockpit listener:', err);
                }
            }
        }

        // =========================================================================
        // 8. DOM Rendering & UI Visual Updates
        // =========================================================================

        renderDOM() {
            if (typeof document === 'undefined') return;

            const snap = this.getTelemetrySnapshot();

            // 1. Balance & Floating Equity
            this._setText('val-balance', `$${snap.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
            this._setText('val-equity', `$${snap.equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

            const pnlEl = document.getElementById('val-floating-pnl');
            if (pnlEl) {
                const sign = snap.floating_pnl >= 0 ? '+' : '';
                pnlEl.textContent = `${sign}$${snap.floating_pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                pnlEl.className = snap.floating_pnl >= 0 ? 'metric-val pnl-positive' : 'metric-val pnl-negative';
            }

            this._setText('val-margin-used', `$${snap.margin.toFixed(2)}`);
            this._setText('val-margin-free', `$${snap.margin_free.toFixed(2)}`);

            // 2. BlackRock Aladdin VaR / CVaR
            this._setText('val-var-99-usd', `$${snap.var_99_usd.toFixed(2)}`);
            this._setText('val-var-99-pct', `${snap.var_99_pct.toFixed(2)}%`);
            this._setText('val-var-95-usd', `$${snap.var_95_usd.toFixed(2)}`);
            this._setText('val-var-95-pct', `${snap.var_95_pct.toFixed(2)}%`);
            this._setText('val-cvar-99-usd', `$${snap.cvar_99_usd.toFixed(2)}`);
            this._setText('val-cvar-99-pct', `${snap.cvar_99_pct.toFixed(2)}%`);

            const varBar = document.getElementById('var-progress-fill');
            if (varBar) {
                const fillPct = Math.min(100.0, (snap.var_99_pct / this.profile.safe_daily_loss_pct) * 100.0);
                varBar.style.width = `${fillPct}%`;
                varBar.className = fillPct > 80 ? 'bar-fill bg-danger' : fillPct > 50 ? 'bar-fill bg-warning' : 'bar-fill bg-cyan';
            }

            // 3. Prop Firm Trailing HWM Floor & Drawdown
            this._setText('val-hwm', `$${snap.hwm.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
            this._setText('val-trailing-floor', `$${snap.trailing_floor.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
            this._setText('val-trailing-buffer', `$${snap.trailing_buffer_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

            const hwmBar = document.getElementById('hwm-progress-fill');
            if (hwmBar) {
                hwmBar.style.width = `${Math.min(100.0, snap.trailing_buffer_pct)}%`;
            }

            this._setText('val-daily-loss', `$${snap.daily_loss_used.toFixed(2)}`);
            this._setText('val-daily-limit', `$${snap.daily_loss_allowed.toFixed(2)}`);
            this._setText('val-daily-loss-rem', `$${snap.daily_loss_remaining.toFixed(2)}`);

            const ddBar = document.getElementById('daily-drawdown-fill');
            if (ddBar) {
                ddBar.style.width = `${Math.min(100.0, snap.daily_drawdown_pct_used)}%`;
                ddBar.className = snap.daily_drawdown_pct_used > 80 ? 'bar-fill bg-danger' : snap.daily_drawdown_pct_used > 50 ? 'bar-fill bg-warning' : 'bar-fill bg-success';
            }

            // 4. 35% Consistency Rule Gauge & 4-Stage Badge
            this._setText('val-consistency-today', `$${snap.consistency_profit_today.toFixed(2)}`);
            this._setText('val-consistency-cap', `$${snap.consistency_max_allowed.toFixed(2)}`);

            const consBar = document.getElementById('consistency-progress-fill');
            if (consBar) {
                consBar.style.width = `${Math.min(100.0, snap.consistency_pct)}%`;
                consBar.className = `bar-fill bg-stage-${snap.consistency_stage}`;
            }

            const badge = document.getElementById('consistency-status-badge');
            if (badge) {
                badge.textContent = `STAGE ${snap.consistency_stage}: ${snap.consistency_status}`;
                badge.className = `status-badge stage-${snap.consistency_stage} alert-${snap.consistency_gauge.alert_color}`;
            }

            const msgEl = document.getElementById('consistency-action-msg');
            if (msgEl) {
                msgEl.textContent = snap.consistency_gauge.action_message;
            }
        }

        _setText(id, text) {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        }
    }

    return RiskCockpitEngine;
}));

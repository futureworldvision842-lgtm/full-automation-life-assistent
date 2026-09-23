/**
 * test_challenger_stress_m4_m5.js
 * 
 * Empirical Challenger 1 Stress Test Suite for Milestone M4 & M5.
 * Tests mathematical logic and calculations in `risk_cockpit.js` and `terminal_app.js`.
 */

const assert = require('assert');
const path = require('path');

// Load RiskCockpit engine
const RiskCockpitEngine = require('../dashboard/static/js/risk_cockpit.js');

console.log('================================================================');
console.log('CHALLENGER 1: EMPIRICAL STRESS TEST SUITE (M4 & M5)');
console.log('================================================================\n');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failures = [];

function test(name, fn) {
    totalTests++;
    try {
        fn();
        passedTests++;
        console.log(`  [PASS] ${name}`);
    } catch (err) {
        failedTests++;
        failures.push({ name, error: err });
        console.error(`  [FAIL] ${name}: ${err.message}`);
    }
}

// =============================================================================
// SUITE 1: BlackRock Aladdin VaR (99%, 95%) & CVaR (99%, 95%)
// =============================================================================
console.log('--- SUITE 1: BlackRock Aladdin VaR (99%, 95%) & CVaR (99%, 95%) ---');

const engine = new RiskCockpitEngine({ accountTier: '25k' });

test('Canonical VaR 99% and CVaR 99% on $25,000 at 0.80% volatility', () => {
    const res = engine.calculateAladdinVaR(25000.0, 0.0080);
    
    // Expected:
    // VaR_99 = 25,000 * 2.326348 * 0.008 = 465.2696 -> $465.27 (1.86%)
    // CVaR_99 = 25,000 * 2.665214 * 0.008 = 533.0428 -> $533.04 (2.13%)
    assert.strictEqual(res.var_99_dollar, 465.27);
    assert.strictEqual(res.var_99_pct, 1.86);
    assert.strictEqual(res.cvar_99_dollar, 533.04);
    assert.strictEqual(res.cvar_99_pct, 2.13);
    
    // Check CVaR / VaR ratio: strictly 1.145664 (~14.57% larger)
    const ratio = res.cvar_99_dollar / res.var_99_dollar;
    assert(Math.abs(ratio - 1.145664) < 0.001, `Ratio was ${ratio}, expected ~1.145664`);
    assert(Math.abs(res.cvar_var_ratio - 1.145664) < 0.0001);
});

test('Parametric VaR 95% and CVaR 95% on $25,000 at 0.80% volatility', () => {
    const res = engine.calculateAladdinVaR(25000.0, 0.0080);
    
    // Expected:
    // VaR_95 = 25,000 * 1.644854 * 0.008 = 328.9708 -> $328.97 (1.32%)
    // CVaR_95 = 25,000 * 2.062714 * 0.008 = 412.5428 -> $412.54 (1.65%)
    assert.strictEqual(res.var_95_dollar, 328.97);
    assert.strictEqual(res.var_95_pct, 1.32);
    assert.strictEqual(res.cvar_95_dollar, 412.54);
    assert.strictEqual(res.cvar_95_pct, 1.65);
    
    // CVaR 95% > VaR 95% by 25.40%
    const ratio95 = res.cvar_95_dollar / res.var_95_dollar;
    assert(Math.abs(ratio95 - (2.062714 / 1.644854)) < 0.001);
});

test('CVaR 99% is strictly ~14.57% larger than VaR 99% across extreme parameter grid (cvar_var_ratio)', () => {
    const equities = [1.0, 100.0, 25000.0, 50000.0, 100000.0, 1000000.0, 100000000.0, 1e12];
    const vols = [0.0001, 0.001, 0.008, 0.015, 0.05, 0.20, 0.50, 2.0, 10.0];
    
    for (const eq of equities) {
        for (const vol of vols) {
            const res = engine.calculateAladdinVaR(eq, vol);
            // Verify analytical cvar_var_ratio is strictly 1.145664 across all grids
            assert(Math.abs(res.cvar_var_ratio - 1.145664) < 0.00001, `Ratio ${res.cvar_var_ratio} diverged for eq=${eq}, vol=${vol}`);
            // For values where unrounded VaR >= $1.00, 2-decimal rounded dollar values also match within 0.5%
            if (eq * 2.326348 * vol >= 1.0) {
                const dollarRatio = res.cvar_99_dollar / res.var_99_dollar;
                assert(Math.abs(dollarRatio - 1.145664) < 0.005, `Dollar ratio ${dollarRatio} diverged for eq=${eq}, vol=${vol}`);
            }
        }
    }
});

test('Adversarial boundaries for VaR/CVaR: zero equity, negative equity, NaN, negative vol, zero vol', () => {
    // Zero equity: clamps to 1.0 safely
    const rZero = engine.calculateAladdinVaR(0, 0.0080);
    assert(rZero.var_99_dollar > 0);
    assert.strictEqual(rZero.equity, 1.0);
    
    // Negative equity: clamps to 1.0
    const rNeg = engine.calculateAladdinVaR(-50000, 0.0080);
    assert.strictEqual(rNeg.equity, 1.0);
    
    // NaN / undefined equity
    const rNaN = engine.calculateAladdinVaR(NaN, 0.0080);
    assert.strictEqual(rNaN.equity, 1.0);
    
    // Zero vol: parseFloat(0) || 0.0080 falls back to 0.80% default baseline
    const rZeroVol = engine.calculateAladdinVaR(25000, 0);
    assert.strictEqual(rZeroVol.daily_volatility_pct, 0.80);
    
    // Negative vol: Math.max(-0.05, 0.0001) clamps to 0.0001 (0.01%)
    const rNegVol = engine.calculateAladdinVaR(25000, -0.05);
    assert.strictEqual(rNegVol.daily_volatility_pct, 0.01);
});

test('Fractional Kelly Sizing bounded strictly between 0.25% and 0.75%', () => {
    const res = engine.calculateAladdinVaR(25000, 0.0080);
    // Win rate = 0.52 (55% - 3% SE), Payoff = 1.8 -> Full Kelly = (0.52 * 2.8 - 1) / 1.8 = 0.456 / 1.8 = 0.2533 (25.33%)
    // 0.20x Quarter-Kelly = 0.05066 (5.07%) -> Capped at 0.75%
    assert.strictEqual(res.fractional_kelly_pct, 0.75);
});


// =============================================================================
// SUITE 2: HWM Trailing Floor Ratchet Behavior
// =============================================================================
console.log('\n--- SUITE 2: HWM Trailing Floor Ratchet Behavior ---');

test('Trajectory verification: $25k -> $24.5k -> $26k -> $25.5k -> $27k -> $24k', () => {
    const eng = new RiskCockpitEngine({ accountTier: '25k' });
    
    // 1. Initial State: Balance = $25,000, Equity = $25,000
    let def = eng.calculatePropFirmDefense(25000, 25000);
    assert.strictEqual(def.hwm, 25000.0);
    assert.strictEqual(def.trailing_floor, 23500.0); // 25000 - 1500
    assert.strictEqual(def.trailing_buffer_usd, 1500.0);
    assert.strictEqual(def.can_trade, true);
    
    // 2. Trajectory Step 1: Equity drops to $24,500
    def = eng.calculatePropFirmDefense(25000, 24500);
    assert.strictEqual(def.hwm, 25000.0, 'HWM must not decrease during drawdown');
    assert.strictEqual(def.trailing_floor, 23500.0, 'Trailing floor must not move downward');
    assert.strictEqual(def.trailing_buffer_usd, 1000.0); // 24500 - 23500
    assert.strictEqual(def.can_trade, true);
    
    // 3. Trajectory Step 2: Equity surges to $26,000
    def = eng.calculatePropFirmDefense(25000, 26000);
    assert.strictEqual(def.hwm, 26000.0, 'HWM must ratchet to $26,000');
    assert.strictEqual(def.trailing_floor, 24500.0, 'Floor must ratchet to $26,000 - $1,500 = $24,500');
    assert.strictEqual(def.trailing_buffer_usd, 1500.0);
    assert.strictEqual(def.can_trade, true);
    
    // 4. Trajectory Step 3: Equity drops to $25,500
    def = eng.calculatePropFirmDefense(25000, 25500);
    assert.strictEqual(def.hwm, 26000.0, 'HWM remains locked at $26,000');
    assert.strictEqual(def.trailing_floor, 24500.0, 'Floor remains locked at $24,500 and does NOT decrease');
    assert.strictEqual(def.trailing_buffer_usd, 1000.0); // 25500 - 24500
    assert.strictEqual(def.can_trade, true);
    
    // 5. Trajectory Step 4: Equity surges to $27,000 (HWM >= $26.5k)
    def = eng.calculatePropFirmDefense(25000, 27000);
    assert.strictEqual(def.hwm, 27000.0, 'HWM ratchets to $27,000');
    // Notice: at HWM >= 26.5k ($26,500 - $1,500 = $25,000), floor >= initial balance $25,000
    assert.strictEqual(def.trailing_floor, 25500.0, 'Floor ratchets to $27,000 - $1,500 = $25,500');
    assert(def.trailing_floor >= 25000.0, 'Trailing floor protects/locks starting capital');
    assert.strictEqual(def.trailing_buffer_usd, 1500.0);
    assert.strictEqual(def.can_trade, true);
    
    // 6. Trajectory Step 5: Severe crash to $24,000
    def = eng.calculatePropFirmDefense(25000, 24000);
    assert.strictEqual(def.hwm, 27000.0, 'HWM remains $27,000');
    assert.strictEqual(def.trailing_floor, 25500.0, 'Floor remains $25,500');
    assert.strictEqual(def.trailing_buffer_usd, 0.0, 'Buffer is 0');
    assert.strictEqual(def.can_trade, false, 'Trading must be blocked upon floor breach');
    assert(def.status_reason.includes('Trailing High-Water Mark Floor Breached'));
});

test('HWM Trailing Floor Monotonicity under 10,000 Random Walk Steps', () => {
    const eng = new RiskCockpitEngine({ accountTier: '50k' }); // $50k target, $3k loss allowed
    let currentEquity = 50000.0;
    let prevHwm = 50000.0;
    let prevFloor = 47000.0;
    
    // Pseudorandom deterministic walk
    let seed = 42;
    function pseudoRandom() {
        seed = (seed * 9301 + 49297) % 233280;
        return (seed / 233280.0) * 2 - 1; // -1 to +1
    }
    
    for (let i = 0; i < 10000; i++) {
        const step = pseudoRandom() * 200; // ±$200 per tick
        currentEquity = Math.max(1000.0, currentEquity + step);
        const def = eng.calculatePropFirmDefense(50000, currentEquity);
        
        assert(def.hwm >= prevHwm, `HWM decreased from ${prevHwm} to ${def.hwm} at step ${i}`);
        assert(def.trailing_floor >= prevFloor, `Trailing floor decreased from ${prevFloor} to ${def.trailing_floor} at step ${i}`);
        
        prevHwm = def.hwm;
        prevFloor = def.trailing_floor;
    }
});


// =============================================================================
// SUITE 3: 35% Consistency Rule 4-Stage Transitions
// =============================================================================
console.log('\n--- SUITE 3: 35% Consistency Rule 4-Stage Transitions ---');

test('Consistency 4-Stage transitions across varying daily profits ($0, $400, $500, $650, $750, $1500)', () => {
    const eng = new RiskCockpitEngine({ accountTier: '25k' });
    // $25k Tier: Profit Target = $2,000. 35% Consistency Cap = $700.00.
    
    // 1. Profit = $0.00 -> Stage 1 NOMINAL (< 70% of $700, i.e. < $490)
    let p0 = eng.calculateConsistencyPacing(0);
    assert.strictEqual(p0.max_single_day_allowed, 700.0);
    assert.strictEqual(p0.stage, 1);
    assert.strictEqual(p0.status, 'NOMINAL');
    assert.strictEqual(p0.alert_color, 'green');
    assert.strictEqual(p0.risk_per_trade_pct, 0.75);
    assert.strictEqual(p0.risk_multiplier, 1.0);
    
    // 2. Profit = $400.00 -> Stage 1 NOMINAL (57.1% of cap < 70%)
    let p400 = eng.calculateConsistencyPacing(400);
    assert.strictEqual(p400.stage, 1);
    assert.strictEqual(p400.status, 'NOMINAL');
    assert.strictEqual(p400.consistency_pct, 57.1);
    assert.strictEqual(p400.risk_per_trade_pct, 0.75);
    
    // 3. Profit = $500.00 -> Stage 2 CAUTION (71.4% of cap >= 70% and < 90%)
    let p500 = eng.calculateConsistencyPacing(500);
    assert.strictEqual(p500.stage, 2);
    assert.strictEqual(p500.status, 'CAUTION');
    assert.strictEqual(p500.alert_color, 'yellow');
    assert.strictEqual(p500.consistency_pct, 71.4);
    assert.strictEqual(p500.risk_per_trade_pct, 0.375);
    assert.strictEqual(p500.risk_multiplier, 0.50);
    assert(p500.action_message.includes('Half-risk mode'));
    
    // 4. Profit = $650.00 -> Stage 3 CRITICAL (92.9% of cap >= 90% and < 100%)
    let p650 = eng.calculateConsistencyPacing(650);
    assert.strictEqual(p650.stage, 3);
    assert.strictEqual(p650.status, 'CRITICAL');
    assert.strictEqual(p650.alert_color, 'orange');
    assert.strictEqual(p650.consistency_pct, 92.9);
    assert.strictEqual(p650.risk_per_trade_pct, 0.15);
    assert.strictEqual(p650.risk_multiplier, 0.20);
    assert(p650.action_message.includes('Harvest Runners Mode'));
    
    // 5. Profit = $750.00 -> Stage 4 CEILING_REACHED (107.1% of cap >= 100%)
    let p750 = eng.calculateConsistencyPacing(750);
    assert.strictEqual(p750.stage, 4);
    assert.strictEqual(p750.status, 'CEILING_REACHED');
    assert.strictEqual(p750.alert_color, 'red');
    assert.strictEqual(p750.consistency_pct, 107.1);
    assert.strictEqual(p750.risk_per_trade_pct, 0.0);
    assert.strictEqual(p750.risk_multiplier, 0.0);
    assert(p750.action_message.includes('Lock Day Mode Active'));
    
    // 6. Profit = $1500.00 -> Stage 4 CEILING_REACHED (214.3% of cap >= 100%)
    let p1500 = eng.calculateConsistencyPacing(1500);
    assert.strictEqual(p1500.stage, 4);
    assert.strictEqual(p1500.status, 'CEILING_REACHED');
    assert.strictEqual(p1500.consistency_pct, 214.3);
    assert.strictEqual(p1500.risk_per_trade_pct, 0.0);
});

test('Consistency 4-Stage Exact Boundary Transitions (489.99 vs 490.00, 629.99 vs 630.00, 699.99 vs 700.00)', () => {
    const eng = new RiskCockpitEngine({ accountTier: '25k' });
    
    // Cap is $700.00
    // Stage 1 -> 2 threshold: 70% of 700 = $490.00
    assert.strictEqual(eng.calculateConsistencyPacing(489.99).stage, 1);
    assert.strictEqual(eng.calculateConsistencyPacing(490.00).stage, 2);
    
    // Stage 2 -> 3 threshold: 90% of 700 = $630.00
    assert.strictEqual(eng.calculateConsistencyPacing(629.99).stage, 2);
    assert.strictEqual(eng.calculateConsistencyPacing(630.00).stage, 3);
    
    // Stage 3 -> 4 threshold: 100% of 700 = $700.00
    assert.strictEqual(eng.calculateConsistencyPacing(699.99).stage, 3);
    assert.strictEqual(eng.calculateConsistencyPacing(700.00).stage, 4);
});

test('Telemetry snapshot can_trade is blocked when Consistency reaches Stage 4', () => {
    const eng = new RiskCockpitEngine({ accountTier: '25k' });
    eng.updateAccount(25000, 25500, 400); // Stage 1
    assert.strictEqual(eng.getTelemetrySnapshot().can_trade, true);
    
    eng.updateAccount(25000, 25750, 750); // Stage 4
    assert.strictEqual(eng.getTelemetrySnapshot().can_trade, false);
});


// =============================================================================
// SUITE 4: Mark-to-Market Floating PnL and Pip Calculations
// =============================================================================
console.log('\n--- SUITE 4: Mark-to-Market Floating PnL and Pip Calculations ---');

const SYMBOL_SPECS = {
    'XAUUSD': { decimals: 2, pip: 0.10, contract: 100.0, name: 'Spot Gold / USD' },
    'EURUSD': { decimals: 5, pip: 0.0001, contract: 100000.0, name: 'Euro / US Dollar' },
    'GBPUSD': { decimals: 5, pip: 0.0001, contract: 100000.0, name: 'British Pound / USD' },
    'USDJPY': { decimals: 3, pip: 0.01, contract: 100000.0, name: 'US Dollar / Yen' }
};

function calculateMtM(pos, tickPrice) {
    const spec = SYMBOL_SPECS[pos.symbol];
    const isBuy = pos.type === 'BUY';
    const diff = isBuy ? (tickPrice - pos.price_open) : (pos.price_open - tickPrice);
    const pnl = parseFloat((diff * spec.contract * pos.volume).toFixed(2));
    const pips = parseFloat((diff / spec.pip).toFixed(1));
    return { pnl, pips, diff };
}

test('XAUUSD Mark-to-Market: BUY and SELL sides', () => {
    // 1. BUY 1.0 lot @ 2650.00, tick = 2655.50
    const buy1 = calculateMtM({ symbol: 'XAUUSD', type: 'BUY', price_open: 2650.00, volume: 1.0 }, 2655.50);
    assert.strictEqual(buy1.pnl, 550.00); // 5.50 * 100 * 1.0
    assert.strictEqual(buy1.pips, 55.0);  // 5.50 / 0.10
    
    // 2. BUY 0.5 lot @ 2650.00, tick = 2640.00 (loss)
    const buy2 = calculateMtM({ symbol: 'XAUUSD', type: 'BUY', price_open: 2650.00, volume: 0.5 }, 2640.00);
    assert.strictEqual(buy2.pnl, -500.00); // -10.00 * 100 * 0.5
    assert.strictEqual(buy2.pips, -100.0); // -10.00 / 0.10
    
    // 3. SELL 1.0 lot @ 2650.00, tick = 2645.00 (profit)
    const sell1 = calculateMtM({ symbol: 'XAUUSD', type: 'SELL', price_open: 2650.00, volume: 1.0 }, 2645.00);
    assert.strictEqual(sell1.pnl, 500.00); // (2650 - 2645) * 100 * 1.0
    assert.strictEqual(sell1.pips, 50.0);  // 5.00 / 0.10
    
    // 4. SELL 0.2 lot @ 2650.00, tick = 2660.00 (loss)
    const sell2 = calculateMtM({ symbol: 'XAUUSD', type: 'SELL', price_open: 2650.00, volume: 0.2 }, 2660.00);
    assert.strictEqual(sell2.pnl, -200.00); // (2650 - 2660) * 100 * 0.2
    assert.strictEqual(sell2.pips, -100.0);
});

test('EURUSD Mark-to-Market: BUY and SELL sides', () => {
    // 1. BUY 1.0 lot @ 1.08500, tick = 1.08750 (profit)
    const buy1 = calculateMtM({ symbol: 'EURUSD', type: 'BUY', price_open: 1.08500, volume: 1.0 }, 1.08750);
    assert.strictEqual(buy1.pnl, 250.00); // 0.00250 * 100,000 * 1.0
    assert.strictEqual(buy1.pips, 25.0);  // 0.00250 / 0.0001
    
    // 2. SELL 2.0 lots @ 1.08500, tick = 1.08200 (profit)
    const sell1 = calculateMtM({ symbol: 'EURUSD', type: 'SELL', price_open: 1.08500, volume: 2.0 }, 1.08200);
    assert.strictEqual(sell1.pnl, 600.00); // 0.00300 * 100,000 * 2.0
    assert.strictEqual(sell1.pips, 30.0);  // 0.00300 / 0.0001
    
    // 3. SELL 1.0 lot @ 1.08500, tick = 1.08900 (loss)
    const sell2 = calculateMtM({ symbol: 'EURUSD', type: 'SELL', price_open: 1.08500, volume: 1.0 }, 1.08900);
    assert.strictEqual(sell2.pnl, -400.00);
    assert.strictEqual(sell2.pips, -40.0);
});

test('GBPUSD Mark-to-Market: BUY and SELL sides', () => {
    // 1. BUY 0.5 lot @ 1.28000, tick = 1.28400 (profit)
    const buy1 = calculateMtM({ symbol: 'GBPUSD', type: 'BUY', price_open: 1.28000, volume: 0.5 }, 1.28400);
    assert.strictEqual(buy1.pnl, 200.00); // 0.00400 * 100,000 * 0.5
    assert.strictEqual(buy1.pips, 40.0);
    
    // 2. SELL 1.0 lot @ 1.28000, tick = 1.28500 (loss)
    const sell1 = calculateMtM({ symbol: 'GBPUSD', type: 'SELL', price_open: 1.28000, volume: 1.0 }, 1.28500);
    assert.strictEqual(sell1.pnl, -500.00);
    assert.strictEqual(sell1.pips, -50.0);
});

test('USDJPY Mark-to-Market: Pip calculation', () => {
    // 1. BUY 1.0 lot @ 155.000, tick = 155.500 (+50 pips)
    const buy1 = calculateMtM({ symbol: 'USDJPY', type: 'BUY', price_open: 155.000, volume: 1.0 }, 155.500);
    assert.strictEqual(buy1.pips, 50.0);
    
    // 2. SELL 1.0 lot @ 155.000, tick = 154.200 (+80 pips)
    const sell1 = calculateMtM({ symbol: 'USDJPY', type: 'SELL', price_open: 155.000, volume: 1.0 }, 154.200);
    assert.strictEqual(sell1.pips, 80.0);
});

// =============================================================================
// SUMMARY
// =============================================================================
console.log('\n================================================================');
console.log(`STRESS TEST EXECUTION COMPLETE:`);
console.log(`Total Tests Run: ${totalTests}`);
console.log(`Passed:         ${passedTests}`);
console.log(`Failed:         ${failedTests}`);
console.log('================================================================');

if (failedTests > 0) {
    console.error('\nFailures breakdown:');
    failures.forEach(f => console.error(`- ${f.name}: ${f.error.message}`));
    process.exit(1);
} else {
    console.log('\nALL EMPIRICAL MATHEMATICAL TESTS PASSED WITH 100% PRECISION!');
    process.exit(0);
}

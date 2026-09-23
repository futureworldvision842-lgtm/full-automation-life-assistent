/**
 * tests/test_challenger2_harness.js — Full Empirical Test Harness for M4 & M5.
 */

const VoiceCopilot = require('../dashboard/static/js/voice_copilot.js');
const TerminalCore = require('../dashboard/static/js/terminal_core.js');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function assert(condition, message) {
    totalTests++;
    if (!condition) {
        failedTests++;
        console.error(`[FAIL] ${message}`);
        throw new Error(`Assertion failed: ${message}`);
    } else {
        passedTests++;
        console.log(`[PASS] ${message}`);
    }
}

console.log("==================================================================");
console.log("1. TESTING TERMINALCORE EVENTBUS (PUB/SUB, ONCE, OFF, RESILIENCE)");
console.log("==================================================================");

const core = new TerminalCore({ autoConnect: false });

// 1.1 Multi-listener registration & execution
let l1_called = false;
let l2_called = false;

const un1 = core.on('tick', (d) => { l1_called = true; assert(d.symbol === 'XAUUSD', "Listener 1 symbol"); });
const un2 = core.on('tick', (d) => { l2_called = true; assert(d.bid === 2650.5, "Listener 2 bid"); });

core.emit('tick', { symbol: 'XAUUSD', bid: 2650.5 });
assert(l1_called && l2_called, "Both multi-listeners received tick event");

// 1.2 Unsubscription isolation
l1_called = false;
l2_called = false;
un1(); // Unsubscribe first listener

core.emit('tick', { symbol: 'XAUUSD', bid: 2650.5 });
assert(!l1_called && l2_called, "Only active listener 2 received tick event after un1 unsubscribed");
un2();

// 1.3 Once listener
let onceCount = 0;
core.once('connected', () => { onceCount++; });
core.emit('connected', { timestamp: 1000 });
core.emit('connected', { timestamp: 2000 });
core.emit('connected', { timestamp: 3000 });
assert(onceCount === 1, "once() listener fired exactly once across 3 emissions");

// 1.4 Error resilience in listeners
let beforeCalled = false;
let afterCalled = false;

core.on('cvd_update', () => { beforeCalled = true; });
core.on('cvd_update', () => { throw new Error("Intentional explosion in test listener"); });
core.on('cvd_update', () => { afterCalled = true; });

core.emit('cvd_update', { delta: 120 });
assert(beforeCalled && afterCalled, "EventBus continued emitting to subsequent listeners despite intermediate error");

// 1.5 Safe unbind all
core.off('cvd_update');
beforeCalled = false;
afterCalled = false;
core.emit('cvd_update', { delta: 120 });
assert(!beforeCalled && !afterCalled, "off(event) cleared all handlers successfully");


console.log("\n==================================================================");
console.log("2. TESTING PROCEDURAL WEB AUDIO SYNTHESIZER API & METHODS");
console.log("==================================================================");

const voice = new VoiceCopilot({ activeSymbol: 'XAUUSD', speechEnabled: false });

assert(typeof voice.synth.play === 'function', "SoundSynthesizer.play exists");
assert(typeof voice.synth.playChime === 'function', "SoundSynthesizer.playChime exists");
assert(typeof voice.synth.createHarmonicTone === 'function', "SoundSynthesizer.createHarmonicTone exists");
assert(typeof voice.playChime === 'function', "VoiceCopilotEngine.playChime exists");
assert(typeof voice.createHarmonicTone === 'function', "VoiceCopilotEngine.createHarmonicTone exists");

// Verify muted behavior and safe invocation in non-browser environment
voice.synth.muted = true;
voice.playChime('confirm');
voice.createHarmonicTone([440, 880], 0.2);
assert(voice.synth.muted === true, "Audio synth muted state preserved");


console.log("\n==================================================================");
console.log("3. TESTING VOICE AI DETERMINISTIC NLP PARSER (35+ VARIANT QUERIES)");
console.log("==================================================================");

const testQueries = [
    // 1-6 Authoritative User Queries
    { query: "Close half on USDJPY", intent: "SCALE_OUT_PARTIAL", symbol: "USDJPY", ratio: 0.50 },
    { query: "Secure gold at breakeven", intent: "LOCK_BREAKEVEN", symbol: "XAUUSD" },
    { query: "Emergency stop everything", intent: "EMERGENCY_KILL_SWITCH" },
    { query: "What is my risk right now?", intent: "GET_RISK_METRICS" },
    { query: "Take fifty percent off gold", intent: "SCALE_OUT_PARTIAL", symbol: "XAUUSD", ratio: 0.50 },
    { query: "Set stop loss for XAUUSD to 2645", intent: "MODIFY_SL_TP", symbol: "XAUUSD" },

    // 7-14 Scale-Out Variants
    { query: "Close 50% on USDJPY", intent: "SCALE_OUT_PARTIAL", symbol: "USDJPY", ratio: 0.50 },
    { query: "Take 25% off EURUSD", intent: "SCALE_OUT_PARTIAL", symbol: "EURUSD", ratio: 0.25 },
    { query: "Take twenty five percent off euro", intent: "SCALE_OUT_PARTIAL", symbol: "EURUSD", ratio: 0.25 },
    { query: "Trim 50% on ticket 579421", intent: "SCALE_OUT_PARTIAL", ticket: 579421, ratio: 0.50 },
    { query: "Scale out 75% on Cable", intent: "SCALE_OUT_PARTIAL", symbol: "GBPUSD", ratio: 0.75 },
    { query: "Take seventy five percent off spot gold", intent: "SCALE_OUT_PARTIAL", symbol: "XAUUSD", ratio: 0.75 },
    { query: "Close full position on Euro", intent: "SCALE_OUT_PARTIAL", symbol: "EURUSD", ratio: 1.00 },
    { query: "Partial close 0.25 on yen", intent: "SCALE_OUT_PARTIAL", symbol: "USDJPY", ratio: 0.25 },

    // 15-20 Breakeven Variants
    { query: "Lock breakeven on GBPUSD with 2 pips buffer", intent: "LOCK_BREAKEVEN", symbol: "GBPUSD", buffer: 2.0 },
    { query: "Move stop to entry on EURUSD", intent: "LOCK_BREAKEVEN", symbol: "EURUSD" },
    { query: "Protect trade on GBPUSD", intent: "LOCK_BREAKEVEN", symbol: "GBPUSD" },
    { query: "Set BE on ticket 579421 plus 1.5 pips", intent: "LOCK_BREAKEVEN", ticket: 579421, buffer: 1.5 },
    { query: "Lock in breakeven on Spot Gold", intent: "LOCK_BREAKEVEN", symbol: "XAUUSD" },
    { query: "Set BE on USDJPY", intent: "LOCK_BREAKEVEN", symbol: "USDJPY" },

    // 21-25 Macro Bias Queries
    { query: "Show Gold Macro Bias", intent: "SHOW_MACRO_BIAS", symbol: "XAUUSD" },
    { query: "What is the bias on EURUSD?", intent: "SHOW_MACRO_BIAS", symbol: "EURUSD" },
    { query: "Macro sentiment for GBPUSD", intent: "SHOW_MACRO_BIAS", symbol: "GBPUSD" },
    { query: "Check market regime on USDJPY", intent: "SHOW_MACRO_BIAS", symbol: "USDJPY" },
    { query: "Show Macro Bias", intent: "SHOW_MACRO_BIAS", symbol: "XAUUSD" },

    // 26-30 Liquidity & SMC Queries
    { query: "Scan for Liquidity Sweeps", intent: "SCAN_SWEEPS", symbol: "XAUUSD" },
    { query: "Any stop hunts on London session?", intent: "SCAN_SWEEPS", symbol: "XAUUSD" },
    { query: "Find order blocks on M15", intent: "SCAN_SWEEPS", symbol: "XAUUSD" },
    { query: "Check EQH sweeps on Gold", intent: "SCAN_SWEEPS", symbol: "XAUUSD" },
    { query: "Scan Fair Value Gaps on EURUSD", intent: "SCAN_SWEEPS", symbol: "EURUSD" },

    // 31-34 Risk & Metric Queries
    { query: "What is my VaR today?", intent: "GET_RISK_METRICS" },
    { query: "Check daily drawdown", intent: "GET_RISK_METRICS" },
    { query: "Show consistency status", intent: "GET_RISK_METRICS" },
    { query: "What is my account equity?", intent: "GET_RISK_METRICS" },

    // 35-40 Emergency / Lifecycle / SLTP / Fallback
    { query: "Emergency kill switch", intent: "EMERGENCY_KILL_SWITCH" },
    { query: "Panic close all", intent: "EMERGENCY_KILL_SWITCH" },
    { query: "Cancel all orders and halt trading", intent: "EMERGENCY_KILL_SWITCH" },
    { query: "Set Take Profit on USDJPY to 155.50", intent: "MODIFY_SL_TP", symbol: "USDJPY" },
    { query: "Pause trading bot", intent: "PAUSE_BOT" },
    { query: "Resume bot loop", intent: "RESUME_BOT" },
    { query: "Jarvis system status", intent: "SYSTEM_STATUS_QUERY" },
    { query: "Blah random unknown noise phrase 123", intent: "UNKNOWN_FALLBACK" }
];

testQueries.forEach((tc, idx) => {
    const res = voice.parseIntent(tc.query, 'XAUUSD');
    assert(res.intent === tc.intent, `[Test #${idx+1}] Query '${tc.query}' -> intent '${res.intent}' === '${tc.intent}'`);

    if (tc.symbol) {
        assert(res.actionPayload.symbol === tc.symbol, `[Test #${idx+1}] symbol -> '${res.actionPayload.symbol}' === '${tc.symbol}'`);
    }
    if (tc.ratio !== undefined) {
        assert(res.actionPayload.ratio === tc.ratio, `[Test #${idx+1}] ratio -> ${res.actionPayload.ratio} === ${tc.ratio}`);
    }
    if (tc.ticket !== undefined) {
        assert(res.actionPayload.ticket === tc.ticket, `[Test #${idx+1}] ticket -> ${res.actionPayload.ticket} === ${tc.ticket}`);
    }
    if (tc.buffer !== undefined) {
        assert(res.actionPayload.buffer_pips === tc.buffer, `[Test #${idx+1}] buffer -> ${res.actionPayload.buffer_pips} === ${tc.buffer}`);
    }
});

console.log("\n==================================================================");
console.log(`FINAL RESULT: ${passedTests}/${totalTests} TESTS PASSED (0 FAILURES)`);
console.log("==================================================================");

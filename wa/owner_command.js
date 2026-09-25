'use strict';

const TRADING_PATTERNS = [
  /^(?:buy|sell|long|short)\s+(?:gold|xau|xauusd|eurusd|btcusd|btc)\b/i,
  /^(?:close\s*all|close|liquidate)\b/i,
  /^(?:breakeven|be\s*lock|be)\b/i,
  /^(?:status|positions|trades|market|signals|setups|gold|portfolio|telemetry|vitals)\b/i,
  /^(?:vm\s+status|vm\s+start|vm\s+stop)\b/i,
  /^(?:haath\s*rok|saari\s*trades\s*band|sona\s*khareedo|sona\s*becho|gold\s*khareedo|gold\s*becho)\b/i,
  /https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+/i,
  /^(?:assimilate|clone|learn|use\s*repo|repo)\b/i,
  /^(?:help|commands)\b/i
];

function isTradingSignalOrCommand(text) {
  const clean = String(text || '').trim();
  return TRADING_PATTERNS.some(pat => pat.test(clean));
}

// Message content is parsed: explicit prefix, bang/slash, or direct trading signals in trading groups
function extractOwnerCommand(value, isEliteGroup = false) {
  const text = String(value || '').trim();
  if (!text) return null;

  // 1. Explicit jarvis prefix: "jarvis buy gold 0.01", "jarvis status"
  if (/^jarvis(?:[,:\s]|$)/i.test(text)) {
    return text.replace(/^jarvis[,:\s]*/i, '').trim() || 'status';
  }

  // 2. Bang or slash prefix: "!buy gold 0.01", "/status"
  if (/^[!/]\w+/i.test(text)) {
    return text.slice(1).trim();
  }

  // 3. Direct trading command, vision, history, or status in Elite Trade group
  if (isEliteGroup) {
    if (isTradingSignalOrCommand(text) || /(?:history|trads|trades|vision|screen|tasweer|report|vitals|gold|funded|account|mt5|pc)/i.test(text)) {
      return text;
    }
  }

  return null;
}

module.exports = { extractOwnerCommand, isTradingSignalOrCommand };


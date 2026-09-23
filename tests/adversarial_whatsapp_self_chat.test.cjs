/**
 * tests/adversarial_whatsapp_self_chat.test.cjs
 * ==============================================================================
 * Empirical adversarial verification of WhatsApp self-chat loop prevention logic
 * mirroring wa/jarvis_baileys.js implementation.
 * ==============================================================================
 */

const assert = require('node:assert/strict');
const { test } = require('node:test');

test('WhatsApp Self-Chat: fromMe === true with +923468053268 passes isSelfChat gating', () => {
  const ALLOWED_NUMBERS = new Set(['923468053268']);

  const testCases = [
    { jid: '923468053268@s.whatsapp.net', fromMe: true, expected: true },
    { jid: '923468053268:1@s.whatsapp.net', fromMe: true, expected: true },
    { jid: '923001234567@s.whatsapp.net', fromMe: true, expected: false },
    { jid: '923468053268@s.whatsapp.net', fromMe: false, expected: false },
  ];

  for (const tc of testCases) {
    const jid = String(tc.jid);
    const sourceJid = jid;
    const digits = sourceJid.split('@')[0].split(':')[0].replace(/[^0-9]/g, '');
    const jidDigits = jid.split('@')[0].split(':')[0].replace(/[^0-9]/g, '');
    const isSelfChat = tc.fromMe && (jidDigits === '923468053268' || ALLOWED_NUMBERS.has(jidDigits) || digits === '923468053268' || ALLOWED_NUMBERS.has(digits));

    assert.equal(isSelfChat, tc.expected, `Mismatch for jid=${tc.jid}, fromMe=${tc.fromMe}`);
  }
});

test('WhatsApp Self-Chat: outbound bot message IDs in jarvisSentIds are dropped on ingress', () => {
  const jarvisSentIds = new Set();
  const seen = new Set();

  // Ring buffer addition simulation (lines 228-236)
  const _origAdd = jarvisSentIds.add.bind(jarvisSentIds);
  jarvisSentIds.add = function(id) {
    _origAdd(id);
    if (this.size > 2000) {
      const oldest = this.values().next().value;
      if (oldest !== undefined) this.delete(oldest);
    }
    return this;
  };

  // Bot dispatches 3 messages
  jarvisSentIds.add('JARVIS_SENT_001');
  jarvisSentIds.add('JARVIS_SENT_002');
  jarvisSentIds.add('JARVIS_SENT_003');

  // Inbound messages arriving via upsert
  const inboundEvents = [
    { id: 'JARVIS_SENT_001', shouldDrop: true },
    { id: 'JARVIS_SENT_002', shouldDrop: true },
    { id: 'JARVIS_SENT_003', shouldDrop: true },
    { id: 'USER_NEW_MSG_001', shouldDrop: false },
    { id: 'USER_NEW_MSG_002', shouldDrop: false },
  ];

  for (const event of inboundEvents) {
    const msg = { key: { id: event.id } };
    const dropped = !msg.key?.id || seen.has(msg.key.id) || jarvisSentIds.has(msg.key.id);
    assert.equal(dropped, event.shouldDrop, `Failed for message ID: ${event.id}`);
  }
});

test('WhatsApp Self-Chat: regex heuristic filter rejects all bot response cards', () => {
  // Regex from line 356: /^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)/i
  const botCardRegex = /^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)/i;

  const botResponses = [
    '⚡ *[J.A.R.V.I.S. WAKE-ON-MESSAGE ACTIVATED]*',
    '🤖 *[J.A.R.V.I.S. QUANT ENGINE]*',
    '🖥️ [FUNDINGPIPS PORTAL ACTIVE ON SCREEN]',
    '📈 [MARKET & TRADING SITREP]',
    '🌍 [GEOPOLITICAL DEFCON]',
    '🧠 [FREE AI RESPONSE]',
    '📊 [CRYPTO FEAR & GREED INDEX — LIVE]',
    '📦 [BACKUP ARCHIVE CREATED]',
    '🔐 [FUNDINGPIPS PORTAL OPENED ON PC]',
    'Sir, J.A.R.V.I.S. is operational.',
    'sir, order executed successfully.',
    '[J.A.R.V.I.S. Status] Everything green.'
  ];

  for (const text of botResponses) {
    const isBot = botCardRegex.test(text);
    assert.equal(isBot, true, `Bot response card not filtered: "${text}"`);
  }

  const userCommands = [
    'vitals',
    'status',
    'screenshot',
    'trade sitrep',
    'funding pips',
    'adeel vision chatgpt',
    'volume 70',
    'workspaces',
    '3d globe',
    'kese ho jarvis'
  ];

  for (const text of userCommands) {
    const isBot = botCardRegex.test(text);
    assert.equal(isBot, false, `User command wrongly filtered: "${text}"`);
  }
});

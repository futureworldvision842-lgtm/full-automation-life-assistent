/**
 * tests/test_adversarial_m4_node.js
 * Direct Node.js empirical stress test for WhatsApp Bridge whitelist security & parity.
 */

import { isAuthorizedContact } from '../whatsapp_bridge/server.js';
import assert from 'assert';

console.log('--- RUNNING NODE.JS ADVERSARIAL WHITELIST SECURITY TESTS ---');

let passed = 0;
let total = 0;

function test(name, fn) {
  total++;
  try {
    fn();
    passed++;
    console.log(`  ✅ [PASS] ${name}`);
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
  }
}

// 1. Spoofed JID Tests
const spoofedJids = [
  '9234680532681@s.whatsapp.net',
  '1923468053268@s.whatsapp.net',
  '923468053269@s.whatsapp.net',
  'attacker@s.whatsapp.net',
  '923468053268@evil.com',
  'status@broadcast',
  'broadcast@s.whatsapp.net',
  '120363999999999999@g.us',
  '923468053268@g.us',
  'random_attacker@lid',
  '999999999999@lid'
];

spoofedJids.forEach(jid => {
  test(`Reject spoofed JID: ${jid}`, () => {
    assert.strictEqual(isAuthorizedContact(jid, null), false);
  });
});

// 2. Malformed / Injection JID Tests
const malformedJids = [
  null,
  undefined,
  '',
  '   ',
  '923468053268\x00@s.whatsapp.net',
  '923468053268\r\n@s.whatsapp.net',
  '923468053268\x1b[31m@s.whatsapp.net',
  '923468053268:abc@s.whatsapp.net',
  '923468053268:0:1@s.whatsapp.net'
];

malformedJids.forEach(jid => {
  test(`Reject malformed/injection JID: ${JSON.stringify(jid)}`, () => {
    assert.strictEqual(isAuthorizedContact(jid, null), false);
  });
});

// 3. Valid Master Owner Formats
const validJids = [
  '923468053268@s.whatsapp.net',
  '923468053268:0@s.whatsapp.net',
  '923468053268:12@s.whatsapp.net',
  '+923468053268@s.whatsapp.net',
  '+92-346-8053268@s.whatsapp.net',
  '03468053268@s.whatsapp.net',
  '00923468053268@s.whatsapp.net',
  '923468053268',
  '120363401615322542@g.us'
];

validJids.forEach(jid => {
  test(`Accept valid authorized format: ${jid}`, () => {
    assert.strictEqual(isAuthorizedContact(jid, null), true);
  });
});

// 4. Verified Owner LID
test('Accept verified active owner LID', () => {
  const activeLid = '274819284719283:0@lid';
  assert.strictEqual(isAuthorizedContact(activeLid, null, activeLid), true);
  assert.strictEqual(isAuthorizedContact('274819284719283:1@lid', null, activeLid), true);
  assert.strictEqual(isAuthorizedContact('999999999999999:0@lid', null, activeLid), false);
});

// 5. Bot Self Message Bypass
test('Accept messages where fromMe is true', () => {
  assert.strictEqual(isAuthorizedContact('unknown@s.whatsapp.net', { key: { fromMe: true } }), true);
});

console.log(`\nNode.js Adversarial Test Results: ${passed}/${total} Passed.`);
if (passed !== total) {
  process.exit(1);
}

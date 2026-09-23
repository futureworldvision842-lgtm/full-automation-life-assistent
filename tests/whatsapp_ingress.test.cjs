const assert = require('node:assert/strict');
const { test } = require('node:test');
const { extractOwnerCommand } = require('../wa/owner_command');

test('explicit prefixes accept spaces, newlines and punctuation', () => {
  for (const value of ['jarvis status', 'Jarvis: status', 'jarvis, status', 'JARVIS\nstatus', 'jarvis']) {
    assert.equal(extractOwnerCommand(value), 'status');
  }
});
test('ordinary text and lookalike prefixes are never commands', () => {
  for (const value of ['status', 'hello jarvis status', 'jarviss status', 'jarvis\\status', null]) {
    assert.equal(extractOwnerCommand(value), null);
  }
});

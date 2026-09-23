import type { AuditEvent } from './types';

const GENESIS_HASH = 'gaigs:genesis:v1';

// Deterministic, portable demo hash. Production Function code uses SHA-256.
export function stableHash(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `demo-${(hash >>> 0).toString(16).padStart(8, '0')}`;
}

export function appendAuditEvent(
  events: AuditEvent[],
  input: Omit<AuditEvent, 'id' | 'previousHash' | 'hash' | 'occurredAt'> & { occurredAt?: string }
): AuditEvent {
  const previousHash = events.at(-1)?.hash ?? GENESIS_HASH;
  const occurredAt = input.occurredAt ?? new Date().toISOString();
  const id = `audit-${events.length + 1}-${occurredAt.slice(11, 19).replaceAll(':', '')}`;
  const raw = JSON.stringify({ id, previousHash, occurredAt, ...input });
  return { ...input, id, occurredAt, previousHash, hash: stableHash(raw) };
}

export function verifyAuditChain(events: AuditEvent[]): { valid: boolean; brokenAt?: string } {
  for (let index = 0; index < events.length; index += 1) {
    const event = events[index];
    if (event.previousHash !== (events[index - 1]?.hash ?? GENESIS_HASH)) return { valid: false, brokenAt: event.id };
    const { id, previousHash, occurredAt, hash: _hash, ...input } = event;
    const expected = stableHash(JSON.stringify({ id, previousHash, occurredAt, ...input }));
    if (event.hash !== expected) return { valid: false, brokenAt: event.id };
  }
  return { valid: true };
}

import { createHash } from 'node:crypto';
import { FieldValue, type Firestore, type Transaction } from 'firebase-admin/firestore';

const HEAD_PATH = 'integrity/auditHead';
const GENESIS_HASH = 'gaigs:genesis:v1';

export async function appendAuditEvent(
  transaction: Transaction,
  database: Firestore,
  input: { action: string; actorId: string; entityType: string; entityId: string; payload: Record<string, unknown>; supersedes?: string }
) {
  const head = database.doc(HEAD_PATH);
  const headSnapshot = await transaction.get(head);
  const previousHash = headSnapshot.exists ? String(headSnapshot.data()?.hash) : GENESIS_HASH;
  const occurredAt = new Date().toISOString();
  const eventRef = database.collection('auditEvents').doc();
  const event = { id: eventRef.id, previousHash, occurredAt, ...input };
  const hash = sha256(stableStringify(event));
  transaction.set(eventRef, { ...event, hash, createdAt: FieldValue.serverTimestamp() });
  transaction.set(head, { hash, eventId: eventRef.id, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
  return { ...event, hash };
}

export function sha256(value: string) {
  return createHash('sha256').update(value).digest('hex');
}

export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(',')}}`;
}

import { describe, expect, it } from 'vitest';
import { appendAuditEvent, verifyAuditChain } from '../domain/audit';
import { createDemoState } from '../domain/seed';

describe('append-only audit chain', () => {
  it('verifies legitimate audit history and detects mutation', () => {
    const state = createDemoState();
    const event = appendAuditEvent(state.audit, { action: 'proposal.drafted', entityType: 'proposal', entityId: 'p-1', actorId: 'u-amina', actorName: 'Amina', payload: { cost: 400 } });
    const chain = [...state.audit, event];
    expect(verifyAuditChain(chain)).toEqual({ valid: true });
    const altered = chain.map((item, index) => index === 1 ? { ...item, action: 'silently.edited' } : item);
    expect(verifyAuditChain(altered)).toMatchObject({ valid: false });
  });
});

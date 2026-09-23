import { describe, expect, it } from 'vitest';
import { createLocalDemoActor } from '../domain/identity';
import { addEvidenceForReview, calculateAvailableBalance, privacySafeLocation, transitionMembership, validateSandboxEntry } from '../domain/operations';
import { createDemoState, demoAccounts } from '../domain/seed';

describe('identity, privacy, marketplace-adjacent and operational guardrails', () => {
  it('creates a local account with a safe profile and validates email', () => {
    expect(createLocalDemoActor({ name: 'Samira Khan', email: 'SAMIRA@example.org', city: '', country: '', skills: ['Design'], interests: ['Water'] }, 'u-samira')).toMatchObject({ id: 'u-samira', email: 'samira@example.org', avatar: 'SK', roles: ['member'] });
    expect(() => createLocalDemoActor({ name: 'Samira', email: 'invalid', city: '', country: '', skills: [], interests: [] })).toThrow('valid email');
  });

  it('enforces role boundaries for membership and project verification', () => {
    const state = createDemoState();
    const pending = state.memberships.find((item) => item.state === 'pending')!;
    expect(() => transitionMembership(pending, demoAccounts[0], 'active')).toThrow('authorized');
    expect(transitionMembership(pending, demoAccounts[3], 'active').state).toBe('active');
    expect(() => addEvidenceForReview(demoAccounts[0], state.projects[1], 'milestone-water-quote')).toThrow('authorized');
    expect(addEvidenceForReview(demoAccounts[3], state.projects[1], 'milestone-water-quote').milestones[1].state).toBe('awaiting_verification');
  });

  it('keeps a sandbox treasury balanced and suppresses exact residential addresses', () => {
    const state = createDemoState();
    const treasury = state.treasuries[0];
    expect(calculateAvailableBalance(treasury, state.ledger)).toBe(66600);
    expect(() => validateSandboxEntry(demoAccounts[0], treasury, state.ledger, 'expense', 10)).toThrow('finance-authorized');
    expect(() => validateSandboxEntry(demoAccounts[3], treasury, state.ledger, 'expense', 70000)).toThrow('insufficient');
    expect(privacySafeLocation({ country: 'Pakistan', city: 'Islamabad', neighborhood: 'G-11', exactAddress: 'House 42' }, 'global')).toBe('Islamabad, Pakistan');
  });
});

import type { Actor, LedgerEntry, Membership, Project, Role, ScopeLevel, Treasury } from './types';

const communityAdministrators: Role[] = ['admin', 'committee', 'founder'];
const financeAdministrators: Role[] = ['admin', 'committee', 'founder'];

export function hasCommunityRole(actor: Actor, roles: Role[]) {
  return actor.roles.some((role) => roles.includes(role));
}

export function canApproveMembership(actor: Actor) {
  return hasCommunityRole(actor, communityAdministrators);
}

export function canRecordSandboxFinance(actor: Actor) {
  return hasCommunityRole(actor, financeAdministrators);
}

export function canAttachProjectEvidence(actor: Actor) {
  return hasCommunityRole(actor, [...communityAdministrators, 'auditor']);
}

export function transitionMembership(membership: Membership, actor: Actor, decision: 'active' | 'rejected'): Membership {
  if (!canApproveMembership(actor)) throw new Error('Only an authorized community administrator can decide a membership request.');
  if (membership.state !== 'pending') throw new Error('Only a pending request can be decided.');
  return { ...membership, state: decision };
}

export function calculateAvailableBalance(treasury: Treasury, entries: LedgerEntry[]) {
  return entries.filter((entry) => entry.treasuryId === treasury.id).reduce((balance, entry) => {
    // An allocation is a project commitment, not a second cash debit; the later expense is the cash movement.
    if (entry.type === 'allocation') return balance;
    return entry.type === 'income' ? balance + entry.amount : balance - entry.amount;
  }, treasury.openingBalance);
}

export function validateSandboxEntry(actor: Actor, treasury: Treasury, entries: LedgerEntry[], type: LedgerEntry['type'], amount: number) {
  if (!canRecordSandboxFinance(actor)) throw new Error('Only a finance-authorized community role may create a ledger entry.');
  if (treasury.status !== 'SANDBOX') throw new Error('This helper supports explicitly labelled sandbox funds only.');
  if (!Number.isFinite(amount) || amount <= 0) throw new Error('A ledger amount must be positive.');
  if (type !== 'income' && amount > calculateAvailableBalance(treasury, entries)) throw new Error('The sandbox treasury has insufficient available balance.');
}

export function addEvidenceForReview(actor: Actor, project: Project, milestoneId: string): Project {
  if (!canAttachProjectEvidence(actor)) throw new Error('Only an authorized project role can attach verification evidence.');
  const found = project.milestones.some((milestone) => milestone.id === milestoneId);
  if (!found) throw new Error('The milestone does not exist on this project.');
  return { ...project, milestones: project.milestones.map((milestone) => milestone.id === milestoneId ? { ...milestone, state: 'awaiting_verification', evidence: [...milestone.evidence, 'Evidence package pending review'] } : milestone) };
}

/** Never publish a precise residence in feed, map, or search results. */
export function privacySafeLocation(location: { country: string; city: string; neighborhood?: string; exactAddress?: string }, scope: ScopeLevel) {
  if (scope === 'personal') return `${location.neighborhood ?? location.city}, ${location.country}`;
  if (scope === 'community' || scope === 'city') return location.neighborhood ? `${location.neighborhood}, ${location.city}` : location.city;
  return `${location.city}, ${location.country}`;
}

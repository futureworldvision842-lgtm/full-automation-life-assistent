import { initializeApp } from 'firebase-admin/app';
import { FieldValue, getFirestore } from 'firebase-admin/firestore';
import { HttpsError, onCall } from 'firebase-functions/v2/https';
import { logger } from 'firebase-functions';
import { appendAuditEvent } from './audit.js';
import { calculateDeterministicResult } from './governance.js';
import { buildJarvisDraftRequest } from './jarvis.js';
import type { BallotDocument, MemberRole, MembershipDocument, ProposalDocument, TreasuryDocument, VoteChoice } from './models.js';

initializeApp();
const database = getFirestore();
const privilegedFinanceRoles: MemberRole[] = ['admin', 'committee', 'founder'];
const membershipRoles: MemberRole[] = ['admin', 'committee', 'founder'];

/**
 * A vote is a server-owned command. No result is ever calculated by an LLM or
 * accepted from a client payload; eligibility is taken from the frozen snapshot.
 */
export const castBallot = onCall({ enforceAppCheck: true }, async (request) => {
  const uid = requireUid(request.auth?.uid);
  const proposalId = requireString(request.data?.proposalId, 'proposalId');
  const choice = validateChoice(request.data?.choice);
  const proposalRef = database.collection('proposals').doc(proposalId);
  const ballotRef = proposalRef.collection('ballots').doc(uid);

  await database.runTransaction(async (transaction) => {
    const [proposalSnapshot, ballotSnapshot] = await Promise.all([transaction.get(proposalRef), transaction.get(ballotRef)]);
    if (!proposalSnapshot.exists) throw new HttpsError('not-found', 'Proposal not found.');
    const proposal = proposalSnapshot.data() as ProposalDocument;
    if (proposal.stage !== 'active_vote') throw new HttpsError('failed-precondition', 'This proposal is not open for voting.');
    if (new Date(proposal.rules.closesAt).getTime() <= Date.now()) throw new HttpsError('failed-precondition', 'Voting has closed.');
    if (!proposal.rules.eligibleVoterIds.includes(uid)) throw new HttpsError('permission-denied', 'The caller is not in this frozen eligibility snapshot.');
    if (ballotSnapshot.exists) throw new HttpsError('already-exists', 'A ballot is already recorded for this user.');

    const ballot: BallotDocument = { voterId: uid, choice, submittedAt: new Date().toISOString() };
    transaction.create(ballotRef, ballot);
    transaction.update(proposalRef, { ballotCount: FieldValue.increment(1), updatedAt: FieldValue.serverTimestamp() });
    await appendAuditEvent(transaction, database, { action: 'ballot.recorded', actorId: uid, entityType: 'proposal', entityId: proposalId, payload: { choice, publicBallot: proposal.rules.publicBallot } });
  });
  return { ok: true };
});

/** Close an eligible proposal. Idempotent result creation happens inside one transaction. */
export const closeProposal = onCall({ enforceAppCheck: true }, async (request) => {
  const uid = requireUid(request.auth?.uid);
  const proposalId = requireString(request.data?.proposalId, 'proposalId');
  const proposalRef = database.collection('proposals').doc(proposalId);
  await database.runTransaction(async (transaction) => {
    const proposalSnapshot = await transaction.get(proposalRef);
    if (!proposalSnapshot.exists) throw new HttpsError('not-found', 'Proposal not found.');
    const proposal = proposalSnapshot.data() as ProposalDocument;
    await assertCommunityRole(transaction, proposal.communityId, uid, membershipRoles);
    if (proposal.result) return;
    if (proposal.stage !== 'active_vote') throw new HttpsError('failed-precondition', 'Proposal is not in an active vote state.');
    if (new Date(proposal.rules.closesAt).getTime() > Date.now()) throw new HttpsError('failed-precondition', 'The vote close time has not yet passed.');
    const ballotSnapshots = await transaction.get(proposalRef.collection('ballots'));
    const ballots = ballotSnapshots.docs.map((document) => document.data() as BallotDocument);
    const result = calculateDeterministicResult(proposal, ballots);
    transaction.update(proposalRef, { stage: result.outcome, result, closedAt: FieldValue.serverTimestamp(), updatedAt: FieldValue.serverTimestamp() });
    transaction.create(database.collection('results').doc(proposalId), { proposalId, ...result, immutable: true, createdAt: FieldValue.serverTimestamp() });
    await appendAuditEvent(transaction, database, { action: 'vote.result.recorded', actorId: uid, entityType: 'proposal', entityId: proposalId, payload: { outcome: result.outcome, validBallots: result.validBallots, turnoutPercent: result.turnoutPercent } });
  });
  return { ok: true };
});

/** Sandbox ledger command. Real money requires a separate regulated-provider adapter and compliance controls. */
export const recordSandboxLedgerEntry = onCall({ enforceAppCheck: true }, async (request) => {
  const uid = requireUid(request.auth?.uid);
  const treasuryId = requireString(request.data?.treasuryId, 'treasuryId');
  const amount = Number(request.data?.amount);
  const type = request.data?.type;
  if (!Number.isFinite(amount) || amount <= 0) throw new HttpsError('invalid-argument', 'amount must be a positive number.');
  if (!['income', 'allocation', 'expense', 'reserve'].includes(type)) throw new HttpsError('invalid-argument', 'Unsupported ledger type.');
  const treasuryRef = database.collection('treasuries').doc(treasuryId);
  await database.runTransaction(async (transaction) => {
    const treasurySnapshot = await transaction.get(treasuryRef);
    if (!treasurySnapshot.exists) throw new HttpsError('not-found', 'Treasury not found.');
    const treasury = treasurySnapshot.data() as TreasuryDocument;
    await assertCommunityRole(transaction, treasury.communityId, uid, privilegedFinanceRoles);
    if (treasury.mode !== 'sandbox') throw new HttpsError('failed-precondition', 'This command only supports an explicit sandbox treasury.');
    const debit = type === 'income' ? 0 : amount;
    if (debit > treasury.availableBalance) throw new HttpsError('failed-precondition', 'Insufficient available sandbox balance.');
    const entryRef = database.collection('ledgerEntries').doc();
    transaction.create(entryRef, { treasuryId, type, amount, currency: treasury.currency, title: requireString(request.data?.title, 'title'), category: requireString(request.data?.category, 'category'), status: 'pending', mode: 'sandbox', createdBy: uid, createdAt: FieldValue.serverTimestamp() });
    transaction.update(treasuryRef, { availableBalance: FieldValue.increment(type === 'income' ? amount : -amount), updatedAt: FieldValue.serverTimestamp() });
    await appendAuditEvent(transaction, database, { action: 'sandboxLedger.entry_recorded', actorId: uid, entityType: 'treasury', entityId: treasuryId, payload: { entryId: entryRef.id, type, amount, currency: treasury.currency } });
  });
  return { ok: true };
});

export const resolveJoinRequest = onCall({ enforceAppCheck: true }, async (request) => {
  const uid = requireUid(request.auth?.uid);
  const joinRequestId = requireString(request.data?.joinRequestId, 'joinRequestId');
  const decision = request.data?.decision;
  if (!['approved', 'rejected'].includes(decision)) throw new HttpsError('invalid-argument', 'decision must be approved or rejected.');
  const requestRef = database.collection('joinRequests').doc(joinRequestId);
  await database.runTransaction(async (transaction) => {
    const joinSnapshot = await transaction.get(requestRef);
    if (!joinSnapshot.exists) throw new HttpsError('not-found', 'Join request not found.');
    const join = joinSnapshot.data() as { communityId: string; userId: string; state: string };
    await assertCommunityRole(transaction, join.communityId, uid, membershipRoles);
    if (join.state !== 'pending') throw new HttpsError('failed-precondition', 'This request is not pending.');
    transaction.update(requestRef, { state: decision, decisionBy: uid, decisionReason: String(request.data?.reason ?? ''), decidedAt: FieldValue.serverTimestamp() });
    if (decision === 'approved') transaction.set(database.collection('communities').doc(join.communityId).collection('memberships').doc(join.userId), { userId: join.userId, role: 'member', state: 'active', approvedBy: uid, createdAt: FieldValue.serverTimestamp() });
    await appendAuditEvent(transaction, database, { action: `membership.${decision}`, actorId: uid, entityType: 'joinRequest', entityId: joinRequestId, payload: { communityId: join.communityId, userId: join.userId } });
  });
  return { ok: true };
});

/** A conservative response used when no configured model provider is available. */
export const jarvisSafetyStatus = onCall({ enforceAppCheck: true }, async (request) => {
  requireUid(request.auth?.uid);
  logger.info('JARVIS safety status requested');
  return { provider: 'not-configured', canDraft: true, canPublishWithoutConfirmation: false, canDecideVotes: false, canMoveFunds: false };
});

/** Provider-neutral RAG request preparation. A configured provider runs only outside this endpoint's client trust boundary. */
export const prepareJarvisDraft = onCall({ enforceAppCheck: true }, async (request) => {
  const uid = requireUid(request.auth?.uid);
  const permissionLevel = Number(request.data?.permissionLevel ?? 0);
  const contexts = Array.isArray(request.data?.contexts) ? request.data.contexts : [];
  const prepared = buildJarvisDraftRequest({ userPrompt: String(request.data?.prompt ?? ''), contexts, permissionLevel });
  logger.info('JARVIS draft prepared', { uid, contextCount: prepared.contexts.length, permissionLevel });
  return { provider: 'not-configured', prepared, warning: 'No live provider was invoked. Configure a server-side provider adapter and secret before pilot use.' };
});

async function assertCommunityRole(transaction: FirebaseFirestore.Transaction, communityId: string, uid: string, allowed: MemberRole[]) {
  const membershipRef = database.collection('communities').doc(communityId).collection('memberships').doc(uid);
  const membershipSnapshot = await transaction.get(membershipRef);
  const membership = membershipSnapshot.data() as MembershipDocument | undefined;
  if (!membershipSnapshot.exists || membership?.state !== 'active' || !allowed.includes(membership.role)) throw new HttpsError('permission-denied', 'The caller does not hold the required community role.');
}
function requireUid(uid: string | undefined) { if (!uid) throw new HttpsError('unauthenticated', 'Sign in is required.'); return uid; }
function requireString(value: unknown, label: string) { if (typeof value !== 'string' || !value.trim()) throw new HttpsError('invalid-argument', `${label} is required.`); return value.trim(); }
function validateChoice(choice: unknown): VoteChoice { if (choice === 'yes' || choice === 'no' || choice === 'abstain') return choice; throw new HttpsError('invalid-argument', 'Unsupported ballot choice.'); }

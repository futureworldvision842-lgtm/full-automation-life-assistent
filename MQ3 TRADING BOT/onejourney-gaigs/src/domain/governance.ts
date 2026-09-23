import type { Ballot, Proposal, VoteResult } from './types';

export class GovernanceError extends Error {}

export function calculateVoteResult(proposal: Proposal, now = new Date()): VoteResult {
  const ballots = proposal.ballots;
  const eligibleCount = proposal.rules.eligibleVoterIds.length;
  const yesVotes = ballots.filter((ballot) => ballot.choice === 'yes').length;
  const noVotes = ballots.filter((ballot) => ballot.choice === 'no').length;
  const abstentions = ballots.filter((ballot) => ballot.choice === 'abstain').length;
  const validBallots = ballots.length;
  const turnoutPercent = eligibleCount === 0 ? 0 : round((validBallots / eligibleCount) * 100);
  const decisiveVotes = yesVotes + noVotes;
  const approvalPercent = decisiveVotes === 0 ? 0 : round((yesVotes / decisiveVotes) * 100);
  const quorumMet = turnoutPercent >= proposal.rules.quorumPercent;
  const thresholdMet = approvalPercent >= proposal.rules.majorityPercent;
  const closed = new Date(proposal.rules.closesAt).getTime() <= now.getTime();

  return {
    validBallots,
    eligibleCount,
    turnoutPercent,
    yesVotes,
    noVotes,
    abstentions,
    approvalPercent,
    quorumMet,
    thresholdMet,
    outcome: !closed ? 'pending' : quorumMet && thresholdMet ? 'approved' : 'rejected',
    calculatedAt: now.toISOString()
  };
}

export function validateAndAppendBallot(proposal: Proposal, voterId: string, choice: Ballot['choice'], now = new Date()): Proposal {
  if (proposal.stage !== 'active_vote') throw new GovernanceError('This proposal is not open for voting.');
  if (new Date(proposal.rules.closesAt).getTime() <= now.getTime()) throw new GovernanceError('Voting has closed.');
  if (!proposal.rules.eligibleVoterIds.includes(voterId)) throw new GovernanceError('You are not in the frozen eligibility snapshot.');
  if (proposal.ballots.some((ballot) => ballot.voterId === voterId)) throw new GovernanceError('A ballot already exists for this voter.');

  return {
    ...proposal,
    ballots: [...proposal.ballots, { voterId, choice, submittedAt: now.toISOString() }]
  };
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}

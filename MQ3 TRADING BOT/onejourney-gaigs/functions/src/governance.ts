import type { BallotDocument, ProposalDocument, VoteResult } from './models.js';

export function calculateDeterministicResult(proposal: ProposalDocument, ballots: BallotDocument[], closedAt = new Date()): VoteResult {
  const validBallots = ballots.length;
  const eligibleCount = proposal.rules.eligibleVoterIds.length;
  const yesVotes = ballots.filter((ballot) => ballot.choice === 'yes').length;
  const noVotes = ballots.filter((ballot) => ballot.choice === 'no').length;
  const abstentions = ballots.filter((ballot) => ballot.choice === 'abstain').length;
  const turnoutPercent = percent(validBallots, eligibleCount);
  const approvalPercent = percent(yesVotes, yesVotes + noVotes);
  const quorumMet = turnoutPercent >= proposal.rules.quorumPercent;
  const thresholdMet = approvalPercent >= proposal.rules.majorityPercent;
  return {
    validBallots, eligibleCount, turnoutPercent, yesVotes, noVotes, abstentions, approvalPercent, quorumMet, thresholdMet,
    outcome: quorumMet && thresholdMet ? 'approved' : 'rejected', calculatedAt: closedAt.toISOString()
  };
}

function percent(numerator: number, denominator: number) {
  return denominator === 0 ? 0 : Math.round((numerator / denominator) * 1000) / 10;
}

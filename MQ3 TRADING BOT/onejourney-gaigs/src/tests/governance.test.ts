import { describe, expect, it } from 'vitest';
import { GovernanceError, calculateVoteResult, validateAndAppendBallot } from '../domain/governance';
import { createDemoState } from '../domain/seed';

describe('deterministic governance engine', () => {
  it('rejects a duplicate ballot and protects the frozen eligibility snapshot', () => {
    const proposal = createDemoState().proposals.find((item) => item.id === 'prop-water')!;
    expect(() => validateAndAppendBallot(proposal, 'u-sara', 'yes')).toThrow(GovernanceError);
    expect(() => validateAndAppendBallot(proposal, 'unlisted-user', 'yes')).toThrow('frozen eligibility');
  });

  it('calculates approval only after close, with quorum and threshold', () => {
    const proposal = createDemoState().proposals.find((item) => item.id === 'prop-water')!;
    const withMemberVote = validateAndAppendBallot(proposal, 'u-amina', 'yes');
    const beforeClose = calculateVoteResult(withMemberVote, new Date());
    expect(beforeClose.outcome).toBe('pending');
    const afterClose = calculateVoteResult(withMemberVote, new Date(new Date(proposal.rules.closesAt).getTime() + 1));
    expect(afterClose).toMatchObject({ validBallots: 5, quorumMet: true, thresholdMet: true, outcome: 'approved' });
  });
});

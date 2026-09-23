export type VoteChoice = 'yes' | 'no' | 'abstain';
export type MemberRole = 'member' | 'provider' | 'committee' | 'admin' | 'auditor' | 'city_operator' | 'global_operator' | 'founder';

export interface BallotDocument {
  voterId: string;
  choice: VoteChoice;
  submittedAt: string;
}

export interface ProposalDocument {
  communityId: string;
  stage: 'discussion' | 'draft' | 'active_vote' | 'approved' | 'rejected' | 'implemented';
  rules: {
    eligibleVoterIds: string[];
    quorumPercent: number;
    majorityPercent: number;
    closesAt: string;
    publicBallot: boolean;
  };
  ballotCount?: number;
  result?: VoteResult;
  estimatedCost?: number;
  title?: string;
}

export interface VoteResult {
  validBallots: number;
  eligibleCount: number;
  turnoutPercent: number;
  yesVotes: number;
  noVotes: number;
  abstentions: number;
  approvalPercent: number;
  quorumMet: boolean;
  thresholdMet: boolean;
  outcome: 'approved' | 'rejected';
  calculatedAt: string;
}

export interface MembershipDocument {
  userId: string;
  state: 'pending' | 'active' | 'rejected';
  role: MemberRole;
}

export interface TreasuryDocument {
  communityId: string;
  currency: string;
  availableBalance: number;
  mode: 'sandbox' | 'regulated';
}

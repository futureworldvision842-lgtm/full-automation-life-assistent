export type ScopeLevel = 'personal' | 'community' | 'city' | 'country' | 'global';
export type RealityStatus = 'LIVE PILOT' | 'INTERACTIVE DEMO' | 'SANDBOX' | 'ROADMAP';
export type Role = 'member' | 'provider' | 'committee' | 'admin' | 'auditor' | 'city_operator' | 'global_operator' | 'founder';
export type ProposalStage = 'discussion' | 'draft' | 'active_vote' | 'approved' | 'rejected' | 'implemented';
export type VoteChoice = 'yes' | 'no' | 'abstain';

export interface Actor {
  id: string;
  name: string;
  email: string;
  city: string;
  country: string;
  roles: Role[];
  skills: string[];
  interests: string[];
  impactPoints: number;
  avatar: string;
  privacy: 'public' | 'community' | 'private';
}

export interface Community {
  id: string;
  name: string;
  shortName: string;
  scope: ScopeLevel;
  location: string;
  verified: boolean;
  memberCount: number;
  admins: string[];
  description: string;
  status: RealityStatus;
  tags: string[];
}

export interface Membership {
  id: string;
  userId: string;
  communityId: string;
  role: Role;
  state: 'pending' | 'active' | 'rejected';
  requestedAt: string;
  decisionReason?: string;
}

export interface FeedPost {
  id: string;
  author: string;
  authorId: string;
  scope: ScopeLevel;
  communityId?: string;
  type: 'problem' | 'update' | 'evidence' | 'emergency' | 'learning' | 'service';
  title: string;
  body: string;
  createdAt: string;
  reactions: number;
  comments: number;
  evidenceCount?: number;
  status?: RealityStatus;
  linkedProposalId?: string;
}

export interface Ballot {
  voterId: string;
  choice: VoteChoice;
  submittedAt: string;
}

export interface VoteRules {
  eligibleVoterIds: string[];
  quorumPercent: number;
  majorityPercent: number;
  closesAt: string;
  publicBallot: boolean;
}

export interface Proposal {
  id: string;
  title: string;
  summary: string;
  originalText: string;
  scope: ScopeLevel;
  communityId: string;
  stage: ProposalStage;
  authorId: string;
  createdAt: string;
  estimatedCost: number;
  currency: string;
  evidence: string[];
  argumentsFor: number;
  argumentsAgainst: number;
  rules: VoteRules;
  ballots: Ballot[];
  result?: VoteResult;
  jarvisSummary: string;
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
  outcome: 'approved' | 'rejected' | 'pending';
  calculatedAt: string;
}

export interface LedgerEntry {
  id: string;
  treasuryId: string;
  type: 'income' | 'allocation' | 'expense' | 'reserve';
  amount: number;
  currency: string;
  category: string;
  title: string;
  date: string;
  projectId?: string;
  receiptId?: string;
  status: 'verified' | 'pending' | 'disputed';
  statusLabel: RealityStatus;
}

export interface Treasury {
  id: string;
  communityId: string;
  name: string;
  currency: string;
  openingBalance: number;
  status: RealityStatus;
}

export interface ProjectMilestone {
  id: string;
  title: string;
  state: 'completed' | 'in_progress' | 'awaiting_verification' | 'planned';
  evidence: string[];
  dueDate: string;
}

export interface Project {
  id: string;
  proposalId?: string;
  communityId: string;
  title: string;
  summary: string;
  completion: number;
  funding: number;
  provider: string;
  verifier: string;
  status: 'planned' | 'active' | 'awaiting_verification' | 'complete';
  milestones: ProjectMilestone[];
  statusLabel: RealityStatus;
}

export interface ServiceOffer {
  id: string;
  provider: string;
  category: string;
  description: string;
  location: string;
  priceLabel: string;
  rating: number;
  availability: 'available' | 'busy';
  verified: boolean;
  status: RealityStatus;
}

export interface ServiceRequest {
  id: string;
  title: string;
  description: string;
  category: string;
  budget: number;
  location: string;
  status: 'open' | 'assigned' | 'complete';
  createdBy: string;
  offers: number;
}

export interface EmergencyIncident {
  id: string;
  title: string;
  type: 'flood' | 'fire' | 'medical' | 'food_shortage';
  location: string;
  severity: 1 | 2 | 3 | 4 | 5;
  verified: boolean;
  needs: string[];
  peopleReached: number;
  status: 'active' | 'monitoring' | 'resolved';
  statusLabel: RealityStatus;
}

export interface LabChallenge {
  id: string;
  title: string;
  category: string;
  description: string;
  participants: number;
  progress: number;
  reward: string;
  status: RealityStatus;
}

export interface AuditEvent {
  id: string;
  action: string;
  actorId: string;
  actorName: string;
  entityType: string;
  entityId: string;
  occurredAt: string;
  payload: Record<string, unknown>;
  previousHash: string;
  hash: string;
  supersedes?: string;
}

export interface JarvisMessage {
  id: string;
  role: 'user' | 'jarvis';
  content: string;
  createdAt: string;
  citations?: { label: string; entity: string }[];
  confidence?: 'high' | 'medium' | 'low';
  actionLevel?: 0 | 1 | 2 | 3 | 4;
}

export interface DemoState {
  version: number;
  viewer: Actor | null;
  communities: Community[];
  memberships: Membership[];
  posts: FeedPost[];
  proposals: Proposal[];
  treasuries: Treasury[];
  ledger: LedgerEntry[];
  projects: Project[];
  services: ServiceOffer[];
  serviceRequests: ServiceRequest[];
  emergencies: EmergencyIncident[];
  challenges: LabChallenge[];
  audit: AuditEvent[];
  jarvisMessages: JarvisMessage[];
  completedTourSteps: string[];
}

export type DemoAction =
  | { type: 'SET_VIEWER'; viewer: Actor }
  | { type: 'RESET' }
  | { type: 'REQUEST_MEMBERSHIP'; communityId: string }
  | { type: 'APPROVE_MEMBERSHIP'; membershipId: string }
  | { type: 'CREATE_POST'; post: FeedPost }
  | { type: 'CAST_BALLOT'; proposalId: string; choice: VoteChoice }
  | { type: 'CREATE_PROPOSAL'; proposal: Proposal }
  | { type: 'ADD_MILESTONE_EVIDENCE'; projectId: string; milestoneId: string }
  | { type: 'CREATE_SERVICE_REQUEST'; request: ServiceRequest }
  | { type: 'SEND_JARVIS'; content: string }
  | { type: 'COMPLETE_TOUR_STEP'; step: string };

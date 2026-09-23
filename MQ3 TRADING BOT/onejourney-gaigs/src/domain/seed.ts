import { appendAuditEvent } from './audit';
import { calculateVoteResult } from './governance';
import type { Actor, DemoState, Proposal } from './types';

const now = new Date();
const isoHours = (hours: number) => new Date(now.getTime() + hours * 60 * 60 * 1000).toISOString();
const isoDays = (days: number) => new Date(now.getTime() + days * 24 * 60 * 60 * 1000).toISOString();

const member: Actor = {
  id: 'u-amina',
  name: 'Amina Rahman',
  email: 'amina.demo@onejourney.local',
  city: 'Islamabad',
  country: 'Pakistan',
  roles: ['member'],
  skills: ['Video editing', 'Community research'],
  interests: ['Water access', 'Learning', 'Local work'],
  impactPoints: 248,
  avatar: 'AR',
  privacy: 'community'
};

function completedProposal(): Proposal {
  const proposal: Proposal = {
    id: 'prop-lights',
    title: 'Solar lighting for the north entrance',
    summary: 'Replace the unlit north entrance with solar lights and publish installation evidence.',
    originalText: 'Allocate sandbox funds for six solar fixtures, local installation, and a public completion record.',
    scope: 'community',
    communityId: 'community-nabvi',
    stage: 'approved',
    authorId: 'u-sara',
    createdAt: isoDays(-25),
    estimatedCost: 72000,
    currency: 'PKR',
    evidence: ['Night-time safety walk, 12 July', 'Three supplier quotations'],
    argumentsFor: 26,
    argumentsAgainst: 3,
    rules: {
      eligibleVoterIds: ['u-amina', 'u-sara', 'u-bilal', 'u-huda', 'u-1', 'u-2', 'u-3', 'u-4', 'u-5', 'u-6'],
      quorumPercent: 40,
      majorityPercent: 55,
      closesAt: isoDays(-15),
      publicBallot: true
    },
    ballots: [
      { voterId: 'u-amina', choice: 'yes', submittedAt: isoDays(-16) },
      { voterId: 'u-sara', choice: 'yes', submittedAt: isoDays(-16) },
      { voterId: 'u-bilal', choice: 'yes', submittedAt: isoDays(-16) },
      { voterId: 'u-huda', choice: 'no', submittedAt: isoDays(-16) },
      { voterId: 'u-1', choice: 'yes', submittedAt: isoDays(-16) },
      { voterId: 'u-2', choice: 'yes', submittedAt: isoDays(-16) }
    ],
    jarvisSummary: 'The proposal met its 40% quorum and 55% approval threshold. It is now an evidence-backed project in the sandbox ledger.'
  };
  return { ...proposal, result: calculateVoteResult(proposal, new Date()) };
}

function pilotState(): DemoState {
  const lighting = completedProposal();
  const waterProposal: Proposal = {
    id: 'prop-water',
    title: 'Repair the community water-pressure line',
    summary: 'Fund a survey, repairs and a transparent verification test for the low-pressure north block.',
    originalText: 'The committee shall allocate up to PKR 180,000 from the maintenance reserve after a qualified provider submits a scoped quote. The completed pressure test and all receipts shall be public to members.',
    scope: 'community',
    communityId: 'community-nabvi',
    stage: 'active_vote',
    authorId: 'u-sara',
    createdAt: isoDays(-7),
    estimatedCost: 180000,
    currency: 'PKR',
    evidence: ['Pressure readings from 18 homes', 'Civil engineer field note', 'Two vendor estimates'],
    argumentsFor: 18,
    argumentsAgainst: 4,
    rules: {
      eligibleVoterIds: ['u-amina', 'u-sara', 'u-bilal', 'u-huda', 'u-1', 'u-2', 'u-3', 'u-4', 'u-5', 'u-6'],
      quorumPercent: 50,
      majorityPercent: 60,
      closesAt: isoHours(4),
      publicBallot: true
    },
    ballots: [
      { voterId: 'u-sara', choice: 'yes', submittedAt: isoHours(-6) },
      { voterId: 'u-bilal', choice: 'yes', submittedAt: isoHours(-5) },
      { voterId: 'u-huda', choice: 'no', submittedAt: isoHours(-4) },
      { voterId: 'u-1', choice: 'yes', submittedAt: isoHours(-3) }
    ],
    jarvisSummary: 'This proposal addresses a verified local service issue. Cost estimates remain within the maintenance reserve, but the provider scope should be confirmed before an allocation is released.'
  };
  const accessibilityProposal: Proposal = {
    id: 'prop-ramp',
    title: 'Accessible entrance ramp and handrail',
    summary: 'Draft proposal awaiting a completed accessibility survey.',
    originalText: 'Create an accessible path with community review of the final design.',
    scope: 'community',
    communityId: 'community-nabvi',
    stage: 'discussion',
    authorId: 'u-amina',
    createdAt: isoDays(-2),
    estimatedCost: 95000,
    currency: 'PKR',
    evidence: ['Two member testimonies'],
    argumentsFor: 7,
    argumentsAgainst: 1,
    rules: { eligibleVoterIds: [], quorumPercent: 50, majorityPercent: 60, closesAt: isoDays(7), publicBallot: true },
    ballots: [],
    jarvisSummary: 'The idea has early support. Before it can become a vote, add measurements, access requirements and at least one independent cost estimate.'
  };

  let audit = [] as DemoState['audit'];
  const seedEvent = (action: string, entityType: string, entityId: string, actorName: string, payload: Record<string, unknown>) => {
    const event = appendAuditEvent(audit, { action, entityType, entityId, actorId: 'system-seed', actorName, payload, occurredAt: isoDays(-20 + audit.length) });
    audit = [...audit, event];
  };
  seedEvent('community.seeded', 'community', 'community-nabvi', 'OneJourney pilot seed', { status: 'INTERACTIVE DEMO' });
  seedEvent('vote.result.recorded', 'proposal', 'prop-lights', 'Community rules engine', { outcome: 'approved', validBallots: 6 });
  seedEvent('ledger.expense.verified', 'ledgerEntry', 'ledger-light-install', 'Huda Qureshi', { amount: 68400, currency: 'PKR' });
  seedEvent('milestone.verified', 'project', 'project-lights', 'Huda Qureshi', { milestone: 'Installation and safety check' });

  return {
    version: 1,
    viewer: null,
    communities: [
      {
        id: 'community-nabvi', name: 'Jamia Masjid Nabvi Qureshi Hashmi', shortName: 'Nabvi Hub', scope: 'community',
        location: 'G-11, Islamabad', verified: true, memberCount: 486, admins: ['u-bilal'],
        description: 'A community unity hub for worship, welfare, learning and transparent local action.', status: 'INTERACTIVE DEMO',
        tags: ['Community welfare', 'Learning', 'Water access']
      },
      {
        id: 'community-igc', name: 'Islamabad Green Collective', shortName: 'Green Collective', scope: 'city',
        location: 'Islamabad', verified: true, memberCount: 1270, admins: [],
        description: 'Neighbourhood climate, tree cover and clean-water volunteers.', status: 'INTERACTIVE DEMO', tags: ['Climate', 'Volunteering']
      },
      {
        id: 'community-makers', name: 'Pakistan Makers Network', shortName: 'Makers', scope: 'country',
        location: 'Pakistan', verified: false, memberCount: 812, admins: [],
        description: 'A learning and maker network for practical scientific challenges.', status: 'INTERACTIVE DEMO', tags: ['Robotics', 'Education']
      }
    ],
    memberships: [
      { id: 'membership-amina', userId: 'u-amina', communityId: 'community-nabvi', role: 'member', state: 'active', requestedAt: isoDays(-140) },
      { id: 'membership-farhan', userId: 'u-farhan', communityId: 'community-nabvi', role: 'provider', state: 'active', requestedAt: isoDays(-90) },
      { id: 'membership-sara', userId: 'u-sara', communityId: 'community-nabvi', role: 'committee', state: 'active', requestedAt: isoDays(-240) },
      { id: 'membership-bilal', userId: 'u-bilal', communityId: 'community-nabvi', role: 'admin', state: 'active', requestedAt: isoDays(-300) },
      { id: 'membership-nadia', userId: 'u-nadia', communityId: 'community-nabvi', role: 'member', state: 'pending', requestedAt: isoDays(-1) }
    ],
    posts: [
      { id: 'post-water', author: 'Sara Iqbal', authorId: 'u-sara', scope: 'community', communityId: 'community-nabvi', type: 'problem', title: 'Water pressure is still low in the north block', body: 'We logged readings from 18 homes and attached a civil engineer’s field note. The repair proposal is open for a member vote.', createdAt: isoHours(-2), reactions: 31, comments: 14, evidenceCount: 3, status: 'INTERACTIVE DEMO', linkedProposalId: 'prop-water' },
      { id: 'post-job', author: 'Noman Studio', authorId: 'u-noman', scope: 'city', type: 'service', title: 'Short video editor needed for a youth event', body: 'Paid local assignment. Share a portfolio and a simple fixed-price quote by Friday.', createdAt: isoHours(-5), reactions: 8, comments: 5, status: 'INTERACTIVE DEMO' },
      { id: 'post-receipt', author: 'Treasury verifier', authorId: 'u-huda', scope: 'community', communityId: 'community-nabvi', type: 'evidence', title: 'Solar entrance lighting receipt verified', body: 'The supplier invoice, installation photos and night-time safety check are available in the completed project record.', createdAt: isoDays(-2), reactions: 47, comments: 8, evidenceCount: 3, status: 'SANDBOX' },
      { id: 'post-lab', author: 'Humanity Lab', authorId: 'system', scope: 'global', type: 'learning', title: 'Clean-water challenge: prototype a low-cost turbidity sensor', body: 'Join a team, inspect the test data and submit a simulation-backed approach. This is a public learning challenge.', createdAt: isoDays(-1), reactions: 64, comments: 19, status: 'INTERACTIVE DEMO' }
    ],
    proposals: [waterProposal, lighting, accessibilityProposal],
    treasuries: [{ id: 'treasury-nabvi', communityId: 'community-nabvi', name: 'Nabvi Hub community treasury', currency: 'PKR', openingBalance: 120000, status: 'SANDBOX' }],
    ledger: [
      { id: 'ledger-donation', treasuryId: 'treasury-nabvi', type: 'income', amount: 195000, currency: 'PKR', category: 'Community donations', title: 'July community contribution round', date: isoDays(-18), status: 'verified', statusLabel: 'SANDBOX' },
      { id: 'ledger-light-allocate', treasuryId: 'treasury-nabvi', type: 'allocation', amount: 72000, currency: 'PKR', category: 'Project allocation', title: 'Solar lighting project allocation', date: isoDays(-14), projectId: 'project-lights', status: 'verified', statusLabel: 'SANDBOX' },
      { id: 'ledger-light-install', treasuryId: 'treasury-nabvi', type: 'expense', amount: 68400, currency: 'PKR', category: 'Public safety', title: 'Solar lighting supplier invoice', date: isoDays(-10), projectId: 'project-lights', receiptId: 'receipt-lights', status: 'verified', statusLabel: 'SANDBOX' },
      { id: 'ledger-water-reserve', treasuryId: 'treasury-nabvi', type: 'reserve', amount: 180000, currency: 'PKR', category: 'Maintenance reserve', title: 'Water-line proposal reserve', date: isoDays(-1), projectId: 'prop-water', status: 'pending', statusLabel: 'SANDBOX' }
    ],
    projects: [
      { id: 'project-lights', proposalId: 'prop-lights', communityId: 'community-nabvi', title: 'Solar lighting at north entrance', summary: 'Approved local safety project with verified supplier evidence.', completion: 100, funding: 72000, provider: 'Farhan Electrical Works', verifier: 'Huda Qureshi', status: 'complete', statusLabel: 'SANDBOX', milestones: [
        { id: 'milestone-light-scope', title: 'Scope and supplier comparison', state: 'completed', evidence: ['Three quotations', 'Conflict declaration'], dueDate: isoDays(-13) },
        { id: 'milestone-light-install', title: 'Installation and safety check', state: 'completed', evidence: ['Invoice', 'Installation photos', 'Night-time safety check'], dueDate: isoDays(-9) }
      ] },
      { id: 'project-water-survey', proposalId: 'prop-water', communityId: 'community-nabvi', title: 'Water pressure survey', summary: 'Draft project: created only for planning and cannot spend until the vote concludes.', completion: 20, funding: 0, provider: 'Provider not selected', verifier: 'Community verifier', status: 'planned', statusLabel: 'SANDBOX', milestones: [
        { id: 'milestone-water-data', title: 'Collect pressure readings', state: 'completed', evidence: ['18 anonymised readings'], dueDate: isoDays(-2) },
        { id: 'milestone-water-quote', title: 'Independent scope review', state: 'awaiting_verification', evidence: [], dueDate: isoDays(3) }
      ] }
    ],
    services: [
      { id: 'service-farhan', provider: 'Farhan Electrical Works', category: 'Repairs', description: 'Licensed electrical repairs and solar-fixture fitting for local homes and community projects.', location: 'Islamabad · 3.2 km', priceLabel: 'From PKR 3,500', rating: 4.9, availability: 'available', verified: true, status: 'INTERACTIVE DEMO' },
      { id: 'service-ayesha', provider: 'Ayesha Visuals', category: 'Editing', description: 'Short-form video editing and event documentation.', location: 'Islamabad · 4.1 km', priceLabel: 'From PKR 5,000', rating: 4.8, availability: 'available', verified: true, status: 'INTERACTIVE DEMO' },
      { id: 'service-kashif', provider: 'Kashif Kitchen', category: 'Food & delivery', description: 'Home-cooked family meals and welfare-distribution logistics.', location: 'Islamabad · 2.5 km', priceLabel: 'PKR 450 / meal', rating: 4.7, availability: 'busy', verified: true, status: 'INTERACTIVE DEMO' }
    ],
    serviceRequests: [
      { id: 'request-video', title: 'Edit a 90-second youth-event recap', description: 'Use supplied clips and add Urdu/English captions.', category: 'Editing', budget: 7500, location: 'Islamabad', status: 'open', createdBy: 'Noman Studio', offers: 3 },
      { id: 'request-electrical', title: 'Community hall lighting inspection', description: 'Need a scoped inspection before a safety maintenance proposal.', category: 'Repairs', budget: 5000, location: 'G-11, Islamabad', status: 'assigned', createdBy: 'Nabvi Hub', offers: 4 }
    ],
    emergencies: [
      { id: 'emergency-flood', title: 'Monsoon flood-relief coordination', type: 'flood', location: 'Upper Sindh, Pakistan', severity: 5, verified: true, needs: ['Clean water kits', 'Temporary shelter', 'Volunteer drivers'], peopleReached: 1280, status: 'active', statusLabel: 'INTERACTIVE DEMO' },
      { id: 'emergency-food', title: 'Heat-wave food distribution', type: 'food_shortage', location: 'Islamabad', severity: 3, verified: true, needs: ['Meal sponsors', 'Delivery volunteers'], peopleReached: 146, status: 'monitoring', statusLabel: 'INTERACTIVE DEMO' }
    ],
    challenges: [
      { id: 'lab-water', title: 'Low-cost clean-water sensor', category: 'Water', description: 'Build a testable turbidity-sensor concept with reproducible calibration evidence.', participants: 418, progress: 62, reward: 'Impact credential + pilot review', status: 'INTERACTIVE DEMO' },
      { id: 'lab-heat', title: 'Neighbourhood heat refuge mapper', category: 'Cities', description: 'Map safe spaces and develop an equitable referral approach for heat alerts.', participants: 173, progress: 38, reward: 'City challenge recognition', status: 'INTERACTIVE DEMO' }
    ],
    audit,
    jarvisMessages: [],
    completedTourSteps: []
  };
}

export function createDemoState(): DemoState {
  return pilotState();
}

export const demoAccounts: Actor[] = [
  { ...member, roles: ['member'] },
  { id: 'u-farhan', name: 'Farhan Malik', email: 'farhan.provider@onejourney.local', city: 'Islamabad', country: 'Pakistan', roles: ['provider'], skills: ['Electrical repairs', 'Solar fitting'], interests: ['Local work'], impactPoints: 420, avatar: 'FM', privacy: 'public' },
  { id: 'u-sara', name: 'Sara Iqbal', email: 'sara.committee@onejourney.local', city: 'Islamabad', country: 'Pakistan', roles: ['committee'], skills: ['Community coordination'], interests: ['Water access'], impactPoints: 812, avatar: 'SI', privacy: 'community' },
  { id: 'u-bilal', name: 'Bilal Qureshi', email: 'bilal.admin@onejourney.local', city: 'Islamabad', country: 'Pakistan', roles: ['admin'], skills: ['Community operations'], interests: ['Public welfare'], impactPoints: 1190, avatar: 'BQ', privacy: 'community' },
  { id: 'u-huda', name: 'Huda Qureshi', email: 'huda.audit@onejourney.local', city: 'Islamabad', country: 'Pakistan', roles: ['auditor'], skills: ['Audit', 'Evidence review'], interests: ['Transparency'], impactPoints: 925, avatar: 'HQ', privacy: 'community' },
  { id: 'u-founder', name: 'OneJourney Founder (Demo)', email: 'founder.demo@onejourney.local', city: 'Islamabad', country: 'Pakistan', roles: ['founder', 'global_operator'], skills: ['Systems design'], interests: ['Humanity Lab'], impactPoints: 9999, avatar: 'OJ', privacy: 'private' }
];

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react';
import { appendAuditEvent } from '../domain/audit';
import { validateAndAppendBallot } from '../domain/governance';
import { createLocalDemoActor } from '../domain/identity';
import { canApproveMembership, canAttachProjectEvidence, transitionMembership } from '../domain/operations';
import { createDemoState, demoAccounts } from '../domain/seed';
import type { Actor, DemoState, FeedPost, Membership, Proposal, ServiceRequest, VoteChoice } from '../domain/types';
import { localJarvisReply } from '../services/jarvis';

const STORAGE_KEY = 'onejourney-gaigs-demo-state-v1';

type Store = {
  state: DemoState;
  error: string | null;
  isOnline: boolean;
  loginDemo: (email: string) => boolean;
  createAccount: (input: Pick<Actor, 'name' | 'email' | 'city' | 'country' | 'skills' | 'interests'>) => void;
  logout: () => void;
  reset: () => void;
  clearError: () => void;
  requestMembership: (communityId: string) => void;
  approveMembership: (membershipId: string) => void;
  createPost: (input: Pick<FeedPost, 'title' | 'body' | 'scope' | 'type' | 'communityId'>) => void;
  castBallot: (proposalId: string, choice: VoteChoice) => void;
  createProposal: (input: Pick<Proposal, 'title' | 'summary' | 'originalText' | 'estimatedCost' | 'communityId'>) => void;
  addMilestoneEvidence: (projectId: string, milestoneId: string) => void;
  createServiceRequest: (input: Pick<ServiceRequest, 'title' | 'description' | 'category' | 'budget' | 'location'>) => void;
  askJarvis: (content: string) => void;
  completeTourStep: (step: string) => void;
};

const OneJourneyContext = createContext<Store | null>(null);

function loadState(): DemoState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return createDemoState();
    return JSON.parse(stored) as DemoState;
  } catch {
    return createDemoState();
  }
}

export function OneJourneyProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<DemoState>(loadState);
  const [error, setError] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener('online', online);
    window.addEventListener('offline', offline);
    return () => {
      window.removeEventListener('online', online);
      window.removeEventListener('offline', offline);
    };
  }, []);

  const run = useCallback((operation: (previous: DemoState) => DemoState) => {
    setError(null);
    setState((previous) => {
      try {
        return operation(previous);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'That action could not be completed.');
        return previous;
      }
    });
  }, []);

  const addAudit = (snapshot: DemoState, action: string, entityType: string, entityId: string, payload: Record<string, unknown>): DemoState => {
    const viewer = requireViewer(snapshot);
    return {
      ...snapshot,
      audit: [...snapshot.audit, appendAuditEvent(snapshot.audit, {
        action, entityType, entityId, payload, actorId: viewer.id, actorName: viewer.name
      })]
    };
  };

  const value = useMemo<Store>(() => ({
    state,
    error,
    isOnline,
    clearError: () => setError(null),
    loginDemo: (email) => {
      const account = demoAccounts.find((candidate) => candidate.email === email);
      if (!account) {
        setError('Use one of the listed demo accounts, or create a local account.');
        return false;
      }
      run((previous) => {
        const next = { ...previous, viewer: { ...account, roles: [...account.roles], skills: [...account.skills], interests: [...account.interests] } as Actor };
        return addAudit(next, 'auth.demo_sign_in', 'user', account.id, { mode: 'interactive_demo' });
      });
      return true;
    },
    createAccount: (input) => run((previous) => {
      if (!input.name.trim() || !input.email.includes('@')) throw new Error('Add a name and a valid email address.');
      const viewer: Actor = createLocalDemoActor(input);
      const next = { ...previous, viewer };
      return addAudit(next, 'auth.local_account_created', 'user', viewer.id, { mode: 'interactive_demo', verified: false });
    }),
    logout: () => setState((previous) => ({ ...previous, viewer: null })),
    reset: () => {
      localStorage.removeItem(STORAGE_KEY);
      setError(null);
      setState(createDemoState());
    },
    requestMembership: (communityId) => run((previous) => {
      const viewer = requireViewer(previous);
      if (previous.memberships.some((membership) => membership.communityId === communityId && membership.userId === viewer.id)) throw new Error('You already have a membership or request for this community.');
      const membership: Membership = { id: `membership-${Date.now()}`, userId: viewer.id, communityId, role: 'member', state: 'pending', requestedAt: new Date().toISOString() };
      const next = { ...previous, memberships: [...previous.memberships, membership] };
      return addAudit(next, 'membership.requested', 'membership', membership.id, { communityId });
    }),
    approveMembership: (membershipId) => run((previous) => {
      const viewer = requireViewer(previous);
      const membership = previous.memberships.find((candidate) => candidate.id === membershipId);
      if (!membership || membership.state !== 'pending') throw new Error('This membership request is no longer pending.');
      if (!canApproveMembership(viewer)) throw new Error('Only an authorized community administrator can approve membership.');
      const approved = transitionMembership(membership, viewer, 'active');
      const next = { ...previous, memberships: previous.memberships.map((candidate) => candidate.id === membershipId ? approved : candidate) };
      return addAudit(next, 'membership.approved', 'membership', membershipId, { communityId: membership.communityId });
    }),
    createPost: (input) => run((previous) => {
      const viewer = requireViewer(previous);
      if (!input.title.trim() || !input.body.trim()) throw new Error('Give your update both a title and some useful context.');
      const post: FeedPost = { id: `post-${Date.now()}`, author: viewer.name, authorId: viewer.id, scope: input.scope, communityId: input.communityId, type: input.type, title: input.title.trim(), body: input.body.trim(), createdAt: new Date().toISOString(), reactions: 0, comments: 0, evidenceCount: input.type === 'problem' ? 1 : 0, status: 'INTERACTIVE DEMO' };
      const next = { ...previous, posts: [post, ...previous.posts], viewer: { ...viewer, impactPoints: viewer.impactPoints + 3 } };
      return addAudit(next, 'post.created', 'post', post.id, { scope: post.scope, type: post.type });
    }),
    castBallot: (proposalId, choice) => run((previous) => {
      const viewer = requireViewer(previous);
      const proposal = previous.proposals.find((candidate) => candidate.id === proposalId);
      if (!proposal) throw new Error('The proposal could not be found.');
      const updatedProposal = validateAndAppendBallot(proposal, viewer.id, choice);
      const next = { ...previous, proposals: previous.proposals.map((candidate) => candidate.id === proposalId ? updatedProposal : candidate), viewer: { ...viewer, impactPoints: viewer.impactPoints + 12 } };
      return addAudit(next, 'ballot.recorded', 'proposal', proposalId, { choice, eligibilitySnapshot: proposal.rules.eligibleVoterIds.length });
    }),
    createProposal: (input) => run((previous) => {
      const viewer = requireViewer(previous);
      if (!input.title.trim() || input.estimatedCost < 0) throw new Error('Include a clear title and a valid estimated cost.');
      const proposal: Proposal = {
        id: `prop-${Date.now()}`, title: input.title.trim(), summary: input.summary.trim(), originalText: input.originalText.trim(), scope: 'community', communityId: input.communityId,
        stage: 'discussion', authorId: viewer.id, createdAt: new Date().toISOString(), estimatedCost: input.estimatedCost, currency: 'PKR', evidence: [], argumentsFor: 0, argumentsAgainst: 0,
        rules: { eligibleVoterIds: [], quorumPercent: 50, majorityPercent: 60, closesAt: new Date(Date.now() + 7 * 86400000).toISOString(), publicBallot: true }, ballots: [],
        jarvisSummary: 'JARVIS draft review: add independent evidence, a defined scope, conflict declarations, and a proposed voting schedule before opening a vote.'
      };
      const next = { ...previous, proposals: [proposal, ...previous.proposals] };
      return addAudit(next, 'proposal.drafted', 'proposal', proposal.id, { estimatedCost: proposal.estimatedCost, stage: proposal.stage });
    }),
    addMilestoneEvidence: (projectId, milestoneId) => run((previous) => {
      const viewer = requireViewer(previous);
      if (!canAttachProjectEvidence(viewer)) throw new Error('Evidence verification is limited to authorized project roles.');
      const project = previous.projects.find((candidate) => candidate.id === projectId);
      if (!project) throw new Error('Project not found.');
      const hasMilestone = project.milestones.some((milestone) => milestone.id === milestoneId);
      if (!hasMilestone) throw new Error('Project milestone not found.');
      const next = {
        ...previous,
        projects: previous.projects.map((candidate) => candidate.id === projectId ? {
          ...candidate,
          milestones: candidate.milestones.map((milestone) => milestone.id === milestoneId ? { ...milestone, state: 'awaiting_verification' as const, evidence: [...milestone.evidence, 'Demo evidence package attached'] } : milestone)
        } : candidate)
      };
      return addAudit(next, 'milestone.evidence_attached', 'project', projectId, { milestoneId, reviewRequired: true });
    }),
    createServiceRequest: (input) => run((previous) => {
      const viewer = requireViewer(previous);
      if (!input.title.trim() || input.budget <= 0) throw new Error('Add a clear request and a positive sandbox budget.');
      const request: ServiceRequest = { id: `request-${Date.now()}`, title: input.title.trim(), description: input.description.trim(), category: input.category, budget: input.budget, location: input.location.trim() || viewer.city, status: 'open', createdBy: viewer.name, offers: 0 };
      const next = { ...previous, serviceRequests: [request, ...previous.serviceRequests] };
      return addAudit(next, 'marketplace.request_created', 'serviceRequest', request.id, { category: request.category, budget: request.budget });
    }),
    askJarvis: (content) => run((previous) => {
      const viewer = requireViewer(previous);
      if (!content.trim()) throw new Error('Ask JARVIS a question first.');
      const userMessage = { id: `user-${Date.now()}`, role: 'user' as const, content: content.trim(), createdAt: new Date().toISOString() };
      const withQuestion = { ...previous, jarvisMessages: [...previous.jarvisMessages, userMessage] };
      const answer = localJarvisReply(withQuestion, content);
      const next = { ...withQuestion, jarvisMessages: [...withQuestion.jarvisMessages, answer] };
      return addAudit(next, 'ai.assistant_session', 'assistantSession', answer.id, { actionLevel: answer.actionLevel ?? 0, localDemo: true, actor: viewer.id });
    }),
    completeTourStep: (step) => run((previous) => previous.completedTourSteps.includes(step) ? previous : { ...previous, completedTourSteps: [...previous.completedTourSteps, step] })
  }), [state, error, isOnline, run]);

  return <OneJourneyContext.Provider value={value}>{children}</OneJourneyContext.Provider>;
}

function requireViewer(state: DemoState): Actor {
  if (!state.viewer) throw new Error('Sign in before taking an action.');
  return state.viewer;
}

export function useOneJourney() {
  const context = useContext(OneJourneyContext);
  if (!context) throw new Error('useOneJourney must be used inside OneJourneyProvider');
  return context;
}

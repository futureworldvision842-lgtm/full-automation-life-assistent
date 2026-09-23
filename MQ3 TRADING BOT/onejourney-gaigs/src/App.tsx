import { useState, type CSSProperties, type FormEvent, type ReactNode } from 'react';
import {
  AlertTriangle, ArrowRight, BadgeCheck, Banknote, Bell, Bot, BrainCircuit, BriefcaseBusiness, Building2,
  Check, ChevronRight, CircleHelp, ClipboardCheck, Compass, FileCheck2, FileText, Flag, Globe2, HandHeart,
  HeartPulse, House, Landmark, Layers3, Lightbulb, LockKeyhole, Map, MapPin, Menu, MessageCircleMore, Mic,
  Network, PackageCheck, Plus, ReceiptText, Search, Send, ShieldCheck, Sparkles, Target, Users, Vote, WalletCards,
  Waves, X, Zap
} from 'lucide-react';
import { calculateVoteResult } from './domain/governance';
import type { FeedPost, Proposal, ScopeLevel, ServiceRequest, VoteChoice } from './domain/types';
import { useOneJourney } from './store/OneJourneyStore';

type Page = 'home' | 'world' | 'action' | 'market' | 'jarvis' | 'profile';

const scopeLabel: Record<ScopeLevel, string> = {
  personal: 'Personal', community: 'Community', city: 'City', country: 'Country', global: 'Global'
};

function App() {
  const { state } = useOneJourney();
  return state.viewer ? <AuthenticatedApp /> : <Welcome />;
}

function Welcome() {
  const { loginDemo, createAccount, error, clearError } = useOneJourney();
  const [mode, setMode] = useState<'sign-in' | 'join'>('sign-in');
  const [email, setEmail] = useState('amina.demo@onejourney.local');

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === 'sign-in') loginDemo(email);
    else {
      const data = new FormData(event.currentTarget);
      createAccount({
        name: String(data.get('name') ?? ''), email: String(data.get('email') ?? ''), city: String(data.get('city') ?? ''), country: String(data.get('country') ?? ''),
        skills: String(data.get('skills') ?? '').split(',').map((entry) => entry.trim()), interests: String(data.get('interests') ?? '').split(',').map((entry) => entry.trim())
      });
    }
  };

  return <main className="welcome-shell">
    <section className="welcome-hero">
      <div className="earth-orbit orbit-one" /><div className="earth-orbit orbit-two" /><div className="earth-core"><Network size={44} /></div>
      <div className="eyebrow"><Sparkles size={14} /> GAIGS / ONEJOURNEY</div>
      <h1>A shared operating system for <span>real-world action.</span></h1>
      <p>Find your community, understand an issue, make a transparent decision, and see the outcome together.</p>
      <div className="principle-row"><span>Justice</span><span>Consultation</span><span>Trust</span><span>Human welfare</span></div>
      <p className="welcome-note"><ShieldCheck size={16} /> A people-first civic platform. Inclusive by design. Never a replacement for lawful public institutions.</p>
    </section>
    <section className="auth-card">
      <div className="brand-lockup"><div className="brand-mark"><Network size={21} /></div><div><strong>OneJourney</strong><small>Turn attention into action</small></div></div>
      <div className="segmented"><button className={mode === 'sign-in' ? 'selected' : ''} onClick={() => { setMode('sign-in'); clearError(); }}>Sign in</button><button className={mode === 'join' ? 'selected' : ''} onClick={() => { setMode('join'); clearError(); }}>Create account</button></div>
      <form onSubmit={submit} className="auth-form">
        {mode === 'join' && <><Field label="Full name" name="name" placeholder="Your full name" required /><div className="two-fields"><Field label="City" name="city" placeholder="Islamabad" /><Field label="Country" name="country" placeholder="Pakistan" /></div></>}
        <Field label="Email address" name="email" type="email" value={email} onChange={setEmail} placeholder="you@example.org" required />
        {mode === 'sign-in' && <Field label="Demo password" name="password" type="password" value="DemoMember2026!" readOnly />}
        {mode === 'join' && <><Field label="Skills" name="skills" placeholder="e.g. tutoring, design" /><Field label="Interests" name="interests" placeholder="e.g. water, learning" /></>}
        {error && <div className="form-error"><AlertTriangle size={16} /> {error}</div>}
        <button className="primary-button wide" type="submit">{mode === 'sign-in' ? 'Continue securely' : 'Start your journey'} <ArrowRight size={17} /></button>
      </form>
      {mode === 'sign-in' && <div className="demo-login"><p><Sparkles size={15} /> Interactive demo — no real account or funds</p><div className="demo-buttons"><button onClick={() => loginDemo('amina.demo@onejourney.local')}>Member</button><button onClick={() => loginDemo('bilal.admin@onejourney.local')}>Admin</button><button onClick={() => loginDemo('founder.demo@onejourney.local')}>Founder</button></div></div>}
      <p className="legal-note">By continuing, you agree to participate respectfully. Your exact address is never public by default.</p>
    </section>
  </main>;
}

function AuthenticatedApp() {
  const { state, error, clearError, isOnline } = useOneJourney();
  const [page, setPage] = useState<Page>('home');
  const [scope, setScope] = useState<ScopeLevel>('community');
  const [showMenu, setShowMenu] = useState(false);
  const viewer = state.viewer!;
  const unread = state.proposals.filter((proposal) => proposal.stage === 'active_vote' && !proposal.ballots.some((ballot) => ballot.voterId === viewer.id)).length;

  const navigate = (next: Page) => { setPage(next); setShowMenu(false); };
  return <div className="app-shell">
    <header className="topbar">
      <button className="brand-button" aria-label="Go to home" onClick={() => navigate('home')}><span className="brand-mark small"><Network size={18} /></span><span className="brand-name">OneJourney</span></button>
      <div className="top-actions"><span className={`connection ${isOnline ? '' : 'offline'}`}>{isOnline ? 'Synced locally' : 'Offline queue'}</span><button className="icon-button" aria-label="Notifications" onClick={() => navigate('action')}><Bell size={20} />{unread > 0 && <i>{unread}</i>}</button><button className="avatar-button" aria-label="Open profile" onClick={() => navigate('profile')}>{viewer.avatar}</button></div>
    </header>
    <div className="scope-strip"><MapPin size={15} /><button onClick={() => setScope('personal')} className={scope === 'personal' ? 'active' : ''}>You</button><button onClick={() => setScope('community')} className={scope === 'community' ? 'active' : ''}>Nabvi Hub</button><button onClick={() => setScope('city')} className={scope === 'city' ? 'active' : ''}>Islamabad</button><button onClick={() => setScope('global')} className={scope === 'global' ? 'active' : ''}>World</button><span className="scope-status">{scopeLabel[scope]}</span></div>
    <main className="page-content">
      {page === 'home' && <HomePage scope={scope} setPage={setPage} />}
      {page === 'world' && <WorldPage scope={scope} setScope={setScope} setPage={setPage} />}
      {page === 'action' && <ActionPage />}
      {page === 'market' && <MarketPage />}
      {page === 'jarvis' && <JarvisPage />}
      {page === 'profile' && <ProfilePage />}
    </main>
    <nav className="bottom-nav" aria-label="Primary navigation">
      <NavButton active={page === 'home'} onClick={() => navigate('home')} label="Home" icon={<House size={21} />} />
      <NavButton active={page === 'world'} onClick={() => navigate('world')} label="World" icon={<Globe2 size={21} />} />
      <NavButton active={page === 'action'} onClick={() => navigate('action')} label="Action" icon={<Target size={21} />} badge={unread} />
      <NavButton active={page === 'market'} onClick={() => navigate('market')} label="Market" icon={<BriefcaseBusiness size={21} />} />
      <NavButton active={page === 'jarvis'} onClick={() => navigate('jarvis')} label="JARVIS" icon={<Bot size={21} />} />
    </nav>
    <button className="floating-menu" aria-label="Open quick actions" onClick={() => setShowMenu(!showMenu)}>{showMenu ? <X size={21} /> : <Plus size={23} />}</button>
    {showMenu && <div className="quick-menu"><button onClick={() => { navigate('action'); }}><Flag size={17} /> Raise an issue</button><button onClick={() => { navigate('market'); }}><BriefcaseBusiness size={17} /> Request a service</button><button onClick={() => { navigate('jarvis'); }}><Bot size={17} /> Ask JARVIS</button></div>}
    {error && <div className="toast" role="alert"><AlertTriangle size={18} /><span>{error}</span><button onClick={clearError}><X size={17} /></button></div>}
  </div>;
}

function HomePage({ scope, setPage }: { scope: ScopeLevel; setPage: (page: Page) => void }) {
  const { state, completeTourStep } = useOneJourney();
  const viewer = state.viewer!;
  const activeVote = state.proposals.find((proposal) => proposal.stage === 'active_vote');
  const project = state.projects.find((candidate) => candidate.status === 'active') ?? state.projects.find((candidate) => candidate.status === 'planned');
  const hasVoted = activeVote?.ballots.some((ballot) => ballot.voterId === viewer.id);
  const [showComposer, setShowComposer] = useState(false);

  return <div className="page-stack">
    <section className="hero-card">
      <div className="hero-top"><div><p className="overline">{scopeLabel[scope]} view · {scope === 'community' ? 'Nabvi Hub' : viewer.city}</p><h1>Good morning, {viewer.name.split(' ')[0]}.</h1></div><StatusPill status="INTERACTIVE DEMO" /></div>
      <div className="jarvis-brief"><div className="jarvis-orb"><Bot size={21} /></div><div><span>JARVIS daily briefing</span><p>{activeVote ? `Your community water proposal closes in about ${hoursLeft(activeVote.rules.closesAt)} hours. ` : ''}A video-editing request matches your skills, and a verified flood-relief mission needs attention.</p></div><button aria-label="Ask JARVIS" onClick={() => setPage('jarvis')}><ChevronRight size={19} /></button></div>
      <div className="hero-metrics"><Metric icon={<Vote size={17} />} value={String(state.proposals.filter((item) => item.stage === 'active_vote').length)} label="votes open" /><Metric icon={<Waves size={17} />} value="1" label="local issue" /><Metric icon={<HeartPulse size={17} />} value={String(state.emergencies.filter((item) => item.status === 'active').length)} label="verified alert" /></div>
    </section>
    <section className="quick-grid"><button onClick={() => setShowComposer(true)}><Flag size={20} /><span>Raise issue</span></button><button onClick={() => setPage('action')}><Vote size={20} /><span>Vote</span></button><button onClick={() => setPage('market')}><BriefcaseBusiness size={20} /><span>Find work</span></button><button onClick={() => setPage('world')}><Map size={20} /><span>Explore map</span></button></section>
    {activeVote && <section className="attention-card vote-attention"><div className="attention-icon"><Vote size={20} /></div><div><p className="overline">Action needed · {hoursLeft(activeVote.rules.closesAt)}h remaining</p><h2>{activeVote.title}</h2><p>{hasVoted ? 'Your ballot has been recorded in the audit trail.' : 'Review the evidence and make your member vote.'}</p><div className="mini-progress"><span style={{ width: `${Math.min((activeVote.ballots.length / activeVote.rules.eligibleVoterIds.length) * 100, 100)}%` }} /></div><small>{activeVote.ballots.length}/{activeVote.rules.eligibleVoterIds.length} eligible members have voted · {activeVote.rules.quorumPercent}% quorum</small></div><button className="outlined-button" onClick={() => { setPage('action'); completeTourStep('vote'); }}>{hasVoted ? 'Review' : 'Vote'} <ArrowRight size={16} /></button></section>}
    {project && <section className="section"><SectionHeading title="Projects in motion" action="See all" onClick={() => setPage('action')} /><ProjectCard project={project} /></section>}
    <section className="section"><SectionHeading title="Around you" action="Filter" /><div className="feed-stack">{state.posts.filter((post) => scope === 'global' || post.scope === scope || post.scope === 'community').slice(0, 4).map((post) => <PostCard key={post.id} post={post} onAction={() => post.linkedProposalId ? setPage('action') : setShowComposer(true)} />)}</div></section>
    <section className="demo-tour"><div className="tour-visual"><Compass size={25} /></div><div><p className="overline">Guided demo tour</p><h3>Follow an issue from report to verified outcome</h3><p>{state.completedTourSteps.length}/6 key actions completed in this local pilot.</p></div><button onClick={() => { completeTourStep('discover'); setPage('world'); }}><ArrowRight size={18} /></button></section>
    {showComposer && <PostComposer onClose={() => setShowComposer(false)} />}
  </div>;
}

function WorldPage({ scope, setScope, setPage }: { scope: ScopeLevel; setScope: (scope: ScopeLevel) => void; setPage: (page: Page) => void }) {
  const { state } = useOneJourney();
  const [selectedLayer, setSelectedLayer] = useState<'communities' | 'projects' | 'emergencies' | 'lab'>('communities');
  const emergency = state.emergencies.find((item) => item.status === 'active')!;
  const pins = {
    communities: state.communities.map((community, index) => ({ id: community.id, label: community.shortName, x: 26 + index * 27, y: 55 - index * 13, color: 'teal' })),
    projects: state.projects.map((project, index) => ({ id: project.id, label: project.title, x: 42 + index * 25, y: 48 - index * 13, color: 'gold' })),
    emergencies: state.emergencies.map((item, index) => ({ id: item.id, label: item.title, x: 61 + index * 15, y: 34 + index * 33, color: 'red' })),
    lab: state.challenges.map((item, index) => ({ id: item.id, label: item.title, x: 30 + index * 42, y: 28 + index * 48, color: 'purple' }))
  }[selectedLayer];
  return <div className="page-stack">
    <section className="page-heading"><div><p className="overline">Planet → country → city → community</p><h1>World map</h1><p>Explore visible public activity. Personal addresses and beneficiary details remain protected.</p></div><StatusPill status="INTERACTIVE DEMO" /></section>
    <div className="map-view">
      <div className="map-grid" />
      <div className="map-glow one" /><div className="map-glow two" />
      <div className="map-label label-1">Islamabad</div><div className="map-label label-2">Pakistan</div><div className="map-label label-3">Global pulse</div>
      {pins.map((pin) => <button className={`map-pin ${pin.color}`} key={pin.id} style={{ left: `${pin.x}%`, top: `${pin.y}%` }} title={pin.label} onClick={() => selectedLayer === 'emergencies' ? setPage('action') : selectedLayer === 'projects' ? setPage('action') : undefined}><span /><small>{pin.label}</small></button>)}
      <div className="map-legend"><MapPin size={14} /> OpenStreetMap-ready map adapter · demo visual layer</div>
    </div>
    <div className="layer-tabs"><button className={selectedLayer === 'communities' ? 'active' : ''} onClick={() => setSelectedLayer('communities')}><Building2 size={16} /> Communities</button><button className={selectedLayer === 'projects' ? 'active' : ''} onClick={() => setSelectedLayer('projects')}><Target size={16} /> Projects</button><button className={selectedLayer === 'emergencies' ? 'active' : ''} onClick={() => setSelectedLayer('emergencies')}><AlertTriangle size={16} /> Alerts</button><button className={selectedLayer === 'lab' ? 'active' : ''} onClick={() => setSelectedLayer('lab')}><BrainCircuit size={16} /> Lab</button></div>
    <section className="scope-cards"><button onClick={() => setScope('community')} className={scope === 'community' ? 'selected' : ''}><Building2 /><span><strong>Community</strong><small>Members, treasury & local action</small></span><ChevronRight /></button><button onClick={() => setScope('city')} className={scope === 'city' ? 'selected' : ''}><MapPin /><span><strong>City</strong><small>Shared projects & services</small></span><ChevronRight /></button><button onClick={() => setScope('global')} className={scope === 'global' ? 'selected' : ''}><Globe2 /><span><strong>Global</strong><small>Relief, science & public pulse</small></span><ChevronRight /></button></section>
    <section className="emergency-banner"><div className="severity">S{emergency.severity}</div><div><p className="overline"><BadgeCheck size={13} /> Verified emergency</p><h2>{emergency.title}</h2><p>{emergency.location} · Needs {emergency.needs.slice(0, 2).join(' and ')}</p></div><button onClick={() => setPage('action')}><ArrowRight size={18} /></button></section>
  </div>;
}

function ActionPage() {
  const { state } = useOneJourney();
  const [tab, setTab] = useState<'proposals' | 'projects' | 'treasury' | 'emergency'>('proposals');
  const [showProposal, setShowProposal] = useState(false);
  return <div className="page-stack">
    <section className="page-heading"><div><p className="overline">Understand → decide → build → verify</p><h1>Action center</h1><p>Every outcome has a visible trail from issue to evidence.</p></div><button className="primary-button compact" onClick={() => setShowProposal(true)}><Plus size={16} /> Proposal</button></section>
    <div className="action-lifecycle"><span className="done">Issue</span><ArrowRight /><span className="done">Discuss</span><ArrowRight /><span className="current">Vote</span><ArrowRight /><span>Fund</span><ArrowRight /><span>Verify</span></div>
    <div className="tab-row"><button className={tab === 'proposals' ? 'active' : ''} onClick={() => setTab('proposals')}>Proposals</button><button className={tab === 'projects' ? 'active' : ''} onClick={() => setTab('projects')}>Projects</button><button className={tab === 'treasury' ? 'active' : ''} onClick={() => setTab('treasury')}>Treasury</button><button className={tab === 'emergency' ? 'active' : ''} onClick={() => setTab('emergency')}>Emergency</button></div>
    {tab === 'proposals' && <ProposalView />}
    {tab === 'projects' && <ProjectsView />}
    {tab === 'treasury' && <TreasuryView />}
    {tab === 'emergency' && <EmergencyView />}
    {showProposal && <ProposalComposer onClose={() => setShowProposal(false)} />}
  </div>;
}

function ProposalView() {
  const { state } = useOneJourney();
  const [expanded, setExpanded] = useState<string | null>('prop-water');
  return <div className="proposal-list">{state.proposals.map((proposal) => <article className={`proposal-card ${expanded === proposal.id ? 'expanded' : ''}`} key={proposal.id}>
    <button className="proposal-summary" onClick={() => setExpanded(expanded === proposal.id ? null : proposal.id)}><div><div className="proposal-meta"><StatusPill status={proposal.stage === 'active_vote' ? 'INTERACTIVE DEMO' : proposal.stage === 'approved' ? 'SANDBOX' : 'ROADMAP'} /><span>{stageLabel(proposal.stage)}</span></div><h2>{proposal.title}</h2><p>{proposal.summary}</p></div><ChevronRight /></button>
    {expanded === proposal.id && <ProposalDetails proposal={proposal} />}
  </article>)}</div>;
}

function ProposalDetails({ proposal }: { proposal: Proposal }) {
  const { state, castBallot, completeTourStep } = useOneJourney();
  const viewer = state.viewer!;
  const hasVoted = proposal.ballots.some((ballot) => ballot.voterId === viewer.id);
  const projected = calculateVoteResult(proposal, new Date(new Date(proposal.rules.closesAt).getTime() + 1));
  const cast = (choice: VoteChoice) => { castBallot(proposal.id, choice); completeTourStep('vote'); };
  return <div className="proposal-details"><div className="detail-grid"><Detail label="Estimated cost" value={`${formatMoney(proposal.estimatedCost)} ${proposal.currency}`} /><Detail label="Rule" value={`${proposal.rules.quorumPercent}% quorum · ${proposal.rules.majorityPercent}% approval`} /><Detail label="Deadline" value={proposal.stage === 'active_vote' ? `${hoursLeft(proposal.rules.closesAt)}h remaining` : stageLabel(proposal.stage)} /></div><div className="plain-language"><Bot size={18} /><div><strong>JARVIS neutral summary</strong><p>{proposal.jarvisSummary}</p></div></div><div className="evidence-box"><div><FileCheck2 size={17} /><strong>Evidence ({proposal.evidence.length})</strong></div><ul>{proposal.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div><div className="argument-row"><span>For <b>{proposal.argumentsFor}</b></span><span>Against <b>{proposal.argumentsAgainst}</b></span><span>Ballots <b>{proposal.ballots.length}/{proposal.rules.eligibleVoterIds.length}</b></span></div>
    {proposal.stage === 'active_vote' ? <>{hasVoted ? <div className="confirmed-action"><Check size={18} /> Your ballot is recorded. It cannot be replaced in this demo.</div> : <div className="vote-options"><p>Cast a ballot — recorded with your demo identity and audit event.</p><button onClick={() => cast('yes')}><Check size={17} /> Yes</button><button onClick={() => cast('no')}><X size={17} /> No</button><button onClick={() => cast('abstain')}><CircleHelp size={17} /> Abstain</button></div>}<div className="projection">If voting closed now: <b>{projected.outcome}</b> · turnout {projected.turnoutPercent}% · approval {projected.approvalPercent}%</div></> : proposal.result ? <div className="result-card"><Check size={19} /><div><strong>Deterministic result: {proposal.result.outcome}</strong><p>{proposal.result.validBallots} ballots · {proposal.result.turnoutPercent}% turnout · audit trail available</p></div></div> : <div className="draft-note"><Lightbulb size={17} /> Discussion phase: more evidence is needed before eligibility and a vote date can be frozen.</div>}</div>;
}

function ProjectsView() {
  const { state, addMilestoneEvidence } = useOneJourney();
  const viewer = state.viewer!;
  const canVerify = viewer.roles.some((role) => ['admin', 'committee', 'auditor', 'founder'].includes(role));
  return <div className="project-list">{state.projects.map((project) => <article key={project.id} className="project-detail-card"><div className="project-header"><div><StatusPill status={project.statusLabel} /><h2>{project.title}</h2><p>{project.summary}</p></div><div className="completion-ring" style={{ '--progress': `${project.completion * 3.6}deg` } as CSSProperties}><span>{project.completion}%</span></div></div><div className="funding-row"><span><WalletCards size={16} /> {formatMoney(project.funding)} PKR sandbox allocation</span><span><ShieldCheck size={16} /> Verifier: {project.verifier}</span></div><div className="milestone-list">{project.milestones.map((milestone) => <div key={milestone.id} className="milestone"><span className={`milestone-state ${milestone.state}`}><Check size={14} /></span><div><strong>{milestone.title}</strong><p>{milestone.evidence.length ? milestone.evidence.join(' · ') : 'Evidence required before verification'}</p></div>{canVerify && milestone.state !== 'completed' && <button className="text-button" onClick={() => addMilestoneEvidence(project.id, milestone.id)}>Attach demo evidence</button>}</div>)}</div></article>)}</div>;
}

function TreasuryView() {
  const { state } = useOneJourney();
  const treasury = state.treasuries[0];
  const totals = state.ledger.reduce((all, entry) => ({ ...all, [entry.type]: (all[entry.type] ?? 0) + entry.amount }), {} as Record<string, number>);
  const available = treasury.openingBalance + (totals.income ?? 0) - (totals.expense ?? 0) - (totals.reserve ?? 0);
  return <div className="treasury-view"><section className="treasury-hero"><div><p className="overline"><LockKeyhole size={13} /> Transparent sandbox treasury</p><h2>{formatMoney(available)} <small>{treasury.currency} available</small></h2><p>Demo balance only. No payment processor or custodial wallet is connected.</p></div><StatusPill status="SANDBOX" /></section><div className="treasury-stats"><Metric icon={<Banknote size={17} />} value={formatMoney(totals.income ?? 0)} label="received" /><Metric icon={<Landmark size={17} />} value={formatMoney(totals.reserve ?? 0)} label="reserved" /><Metric icon={<ReceiptText size={17} />} value={formatMoney(totals.expense ?? 0)} label="receipted" /></div><div className="ledger-list"><SectionHeading title="Ledger trail" action="Verify chain" /><div className="integrity-strip"><ShieldCheck size={17} /><span>Append-only demo audit chain intact</span><small>{state.audit.length} signed-style events</small></div>{state.ledger.slice().reverse().map((entry) => <div className="ledger-row" key={entry.id}><div className={`ledger-icon ${entry.type}`}><ReceiptText size={16} /></div><div><strong>{entry.title}</strong><p>{entry.category} · {entry.status}</p></div><div className="ledger-amount"><b className={entry.type === 'income' ? 'positive' : ''}>{entry.type === 'income' ? '+' : '−'}{formatMoney(entry.amount)}</b><StatusPill status={entry.statusLabel} /></div></div>)}</div></div>;
}

function EmergencyView() {
  const { state } = useOneJourney();
  return <div className="emergency-list">{state.emergencies.map((incident) => <article className="emergency-card" key={incident.id}><div className={`severity-badge s${incident.severity}`}>S{incident.severity}</div><div className="emergency-body"><div className="proposal-meta"><StatusPill status={incident.statusLabel} />{incident.verified && <span className="verified"><BadgeCheck size={14} /> Verified</span>}</div><h2>{incident.title}</h2><p><MapPin size={15} /> {incident.location}</p><div className="need-tags">{incident.needs.map((need) => <span key={need}>{need}</span>)}</div><div className="emergency-footer"><span><Users size={15} /> {incident.peopleReached.toLocaleString()} people reached</span><button className="outlined-button">View accountable relief <ArrowRight size={15} /></button></div></div></article>)}</div>;
}

function MarketPage() {
  const { state } = useOneJourney();
  const [showRequest, setShowRequest] = useState(false);
  const [filter, setFilter] = useState('All');
  const categories = ['All', ...new Set(state.services.map((service) => service.category))];
  const visibleServices = state.services.filter((service) => filter === 'All' || service.category === filter);
  return <div className="page-stack"><section className="page-heading"><div><p className="overline">Skills → offers → milestones → proof</p><h1>Local market</h1><p>Work, services, delivery and community procurement — with clear sandbox status.</p></div><button className="primary-button compact" onClick={() => setShowRequest(true)}><Plus size={16} /> Request</button></section><div className="market-search"><Search size={18} /><input placeholder="Search skills, services, food or rides" /><button><MapPin size={17} /> Near me</button></div><div className="filter-chips">{categories.map((category) => <button key={category} className={filter === category ? 'active' : ''} onClick={() => setFilter(category)}>{category}</button>)}</div><section><SectionHeading title="Trusted local providers" action="Map view" /> <div className="service-scroller">{visibleServices.map((service) => <article className="service-card" key={service.id}><div className="service-top"><div className="service-avatar">{service.provider.split(' ').map((name) => name[0]).join('').slice(0, 2)}</div><div><h3>{service.provider}</h3><p>{service.category} · {service.location}</p></div>{service.verified && <BadgeCheck className="verified-icon" size={18} />}</div><p>{service.description}</p><div className="service-bottom"><span>★ {service.rating}</span><strong>{service.priceLabel}</strong></div><button className="outlined-button wide">View profile <ArrowRight size={15} /></button></article>)}</div></section><section className="section"><SectionHeading title="Open requests" action="See all" /><div className="request-list">{state.serviceRequests.map((request) => <RequestCard key={request.id} request={request} />)}</div></section><section className="food-strip"><PackageCheck size={28} /><div><p className="overline">Food & welfare delivery</p><h3>Local meals with dignity-preserving distribution</h3><p>Orders and welfare delivery operate in a clearly labelled demo workflow.</p></div><button className="text-button">Explore <ArrowRight size={16} /></button></section>{showRequest && <ServiceRequestComposer onClose={() => setShowRequest(false)} />}</div>;
}

function JarvisPage() {
  const { state, askJarvis } = useOneJourney();
  const [prompt, setPrompt] = useState('');
  const send = (event: FormEvent) => { event.preventDefault(); askJarvis(prompt); setPrompt(''); };
  const quickPrompts = ['What needs my attention today?', 'Explain the water proposal simply', 'Where did community donations go?', 'Show verified flood emergencies'];
  return <div className="jarvis-page"><section className="jarvis-hero"><div className="hero-orb"><div className="orb-ring" /><Bot size={32} /></div><div><p className="overline">Your contextual intelligence layer</p><h1>JARVIS</h1><p>Read authorized context, prepare useful work, and show its limits.</p></div><StatusPill status="INTERACTIVE DEMO" /></section><div className="ai-safety"><ShieldCheck size={18} /><p><b>Permission-aware by design.</b> JARVIS can explain and draft. Publishing requires confirmation; votes, security changes and money always require explicit human authorization and deterministic checks.</p></div><div className="conversation">{state.jarvisMessages.length === 0 && <div className="empty-conversation"><BrainCircuit size={29} /><h2>How can I help?</h2><p>I can connect your personal, community and public context without pretending that an AI decides for people.</p></div>}{state.jarvisMessages.map((message) => <article key={message.id} className={`message ${message.role}`}><div className="message-avatar">{message.role === 'jarvis' ? <Bot size={16} /> : state.viewer?.avatar}</div><div><p>{message.content}</p>{message.citations && message.citations.length > 0 && <div className="citation-row">{message.citations.map((citation) => <span key={citation.entity}><FileText size={12} /> {citation.label}</span>)}</div>}{message.role === 'jarvis' && <div className="message-meta"><span>Confidence: {message.confidence}</span><span>Autonomy level {message.actionLevel ?? 0}</span></div>}</div></article>)}</div><div className="quick-prompts">{quickPrompts.map((item) => <button key={item} onClick={() => askJarvis(item)}>{item}</button>)}</div><form className="jarvis-input" onSubmit={send}><button type="button" aria-label="Voice input is planned" title="Voice input adapter is ready for a future provider"><Mic size={20} /></button><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask about a proposal, project, service or alert" /><button className="send" type="submit" aria-label="Send to JARVIS"><Send size={19} /></button></form><p className="ai-disclaimer">Responses are generated by the local demo adapter, not a live model. Sources above point to known platform records.</p></div>;
}

function ProfilePage() {
  const { state, logout, reset, approveMembership } = useOneJourney();
  const viewer = state.viewer!;
  const auditTail = state.audit.slice(-5).reverse();
  const isAdmin = viewer.roles.some((role) => ['admin', 'committee', 'founder'].includes(role));
  const pending = state.memberships.filter((membership) => membership.state === 'pending');
  return <div className="page-stack"><section className="profile-hero"><div className="large-avatar">{viewer.avatar}</div><div><StatusPill status="INTERACTIVE DEMO" /><h1>{viewer.name}</h1><p><MapPin size={15} /> {viewer.city}, {viewer.country} · {viewer.privacy} profile</p><div className="role-tags">{viewer.roles.map((role) => <span key={role}>{role.replace('_', ' ')}</span>)}</div></div><button className="icon-button"><Menu size={20} /></button></section><section className="impact-grid"><Metric icon={<Sparkles size={18} />} value={String(viewer.impactPoints)} label="impact points" /><Metric icon={<Users size={18} />} value={String(state.memberships.filter((membership) => membership.userId === viewer.id && membership.state === 'active').length)} label="communities" /><Metric icon={<ClipboardCheck size={18} />} value={String(state.audit.filter((event) => event.actorId === viewer.id).length)} label="verified actions" /></section><section className="profile-card"><SectionHeading title="Trust graph" action="Privacy: community" /><div className="trust-graph"><div className="graph-line one" /><div className="graph-line two" /><div className="graph-node person"><Users size={17} /><small>You</small></div><div className="graph-node community"><Building2 size={17} /><small>Community</small></div><div className="graph-node decision"><Vote size={17} /><small>Decisions</small></div><div className="graph-node project"><Target size={17} /><small>Outcomes</small></div></div><p>People → Communities → Decisions → Funds → Projects → Contributions → Outcomes → Reputation</p></section><section className="profile-card"><SectionHeading title="Skills & causes" action="Edit" /><div className="tag-cloud">{[...viewer.skills, ...viewer.interests].map((tag) => <span key={tag}>{tag}</span>)}</div></section>{isAdmin && <section className="profile-card"><SectionHeading title="Community operations" action={`${pending.length} pending`} />{pending.length ? pending.map((membership) => <div className="membership-request" key={membership.id}><div><strong>New member request</strong><p>Request #{membership.id.slice(-6)} · {membership.requestedAt.slice(0, 10)}</p></div><button className="outlined-button" onClick={() => approveMembership(membership.id)}>Approve <Check size={15} /></button></div>) : <p className="muted">No pending membership requests.</p>}</section>}<section className="profile-card"><SectionHeading title="Recent audit activity" action="Verify all" /><div className="audit-list">{auditTail.map((event) => <div key={event.id}><ShieldCheck size={15} /><span><b>{event.action.replaceAll('.', ' ')}</b><small>{event.entityType} · {event.occurredAt.slice(0, 10)}</small></span><code>{event.hash.slice(-8)}</code></div>)}</div></section><section className="founder-note"><Sparkles size={20} /><div><h3>Demo mode is transparent</h3><p>All money, votes, data and status labels in this pilot are simulated unless explicitly marked LIVE PILOT.</p></div></section><div className="profile-actions"><button onClick={logout}>Sign out</button><button onClick={reset}>Reset pilot world</button></div></div>;
}

function PostComposer({ onClose }: { onClose: () => void }) {
  const { createPost } = useOneJourney();
  const [type, setType] = useState<FeedPost['type']>('problem');
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); createPost({ title: String(data.get('title') ?? ''), body: String(data.get('body') ?? ''), type, scope: String(data.get('scope') ?? 'community') as ScopeLevel, communityId: 'community-nabvi' }); onClose(); };
  return <Modal title="Raise an issue or share an update" onClose={onClose}><form className="composer-form" onSubmit={submit}><label>Post type<div className="type-picker">{(['problem', 'evidence', 'update'] as const).map((item) => <button type="button" key={item} className={type === item ? 'selected' : ''} onClick={() => setType(item)}>{item}</button>)}</div></label><Field label="Clear title" name="title" placeholder="What needs attention?" required /><label>Useful context<textarea name="body" placeholder="Describe what happened, why it matters, and what evidence you can share." required /></label><label>Visibility<select name="scope" defaultValue="community"><option value="community">Community</option><option value="city">City</option><option value="country">Country (advisory)</option><option value="global">Global</option></select></label><div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" type="submit">Publish demo post <Send size={16} /></button></div></form></Modal>;
}

function ProposalComposer({ onClose }: { onClose: () => void }) {
  const { createProposal } = useOneJourney();
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); createProposal({ title: String(data.get('title') ?? ''), summary: String(data.get('summary') ?? ''), originalText: String(data.get('text') ?? ''), estimatedCost: Number(data.get('cost') ?? 0), communityId: 'community-nabvi' }); onClose(); };
  return <Modal title="Draft a community proposal" onClose={onClose}><div className="ai-safety compact-safety"><Bot size={18} /><p>JARVIS will only prepare this as a discussion draft. Evidence, eligibility and a vote schedule must be configured by the community’s rules.</p></div><form className="composer-form" onSubmit={submit}><Field label="Proposal title" name="title" placeholder="A concise, actionable title" required /><label>Plain-language summary<textarea name="summary" required placeholder="What change is proposed and who benefits?" /></label><label>Original text<textarea name="text" required placeholder="State the scope, limits, implementation and verification requirements." /></label><Field label="Estimated sandbox cost (PKR)" name="cost" type="number" min="0" placeholder="0" required /><div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" type="submit">Save discussion draft <FileText size={16} /></button></div></form></Modal>;
}

function ServiceRequestComposer({ onClose }: { onClose: () => void }) {
  const { createServiceRequest } = useOneJourney();
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); createServiceRequest({ title: String(data.get('title') ?? ''), description: String(data.get('description') ?? ''), category: String(data.get('category') ?? 'Custom service'), budget: Number(data.get('budget') ?? 0), location: String(data.get('location') ?? '') }); onClose(); };
  return <Modal title="Request a local service" onClose={onClose}><form className="composer-form" onSubmit={submit}><Field label="What do you need?" name="title" placeholder="e.g. Repair a leaking tap" required /><label>Details<textarea name="description" required placeholder="Explain scope, timing and any safety constraints." /></label><div className="two-fields"><Field label="Category" name="category" placeholder="Repairs" /><Field label="Sandbox budget (PKR)" name="budget" type="number" min="1" required /></div><Field label="Area" name="location" placeholder="Islamabad" /><div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" type="submit">Post request <BriefcaseBusiness size={16} /></button></div></form></Modal>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) { return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}><header><h2>{title}</h2><button className="icon-button" onClick={onClose}><X size={19} /></button></header>{children}</section></div>; }

function PostCard({ post, onAction }: { post: FeedPost; onAction: () => void }) { const icons: Record<FeedPost['type'], ReactNode> = { problem: <Flag size={16} />, update: <MessageCircleMore size={16} />, evidence: <FileCheck2 size={16} />, emergency: <AlertTriangle size={16} />, learning: <BrainCircuit size={16} />, service: <BriefcaseBusiness size={16} /> }; return <article className="post-card"><div className="post-author"><div className="post-avatar">{post.author.split(' ').map((name) => name[0]).join('').slice(0, 2)}</div><div><strong>{post.author}</strong><p><span>{icons[post.type]}</span> {scopeLabel[post.scope]} · {relativeTime(post.createdAt)}</p></div><StatusPill status={post.status ?? 'INTERACTIVE DEMO'} /></div><h3>{post.title}</h3><p>{post.body}</p>{post.evidenceCount && <div className="evidence-chip"><FileCheck2 size={14} /> {post.evidenceCount} evidence items attached</div>}<footer><span>♥ {post.reactions}</span><span>◌ {post.comments}</span><button onClick={onAction}>{post.linkedProposalId ? 'See proposal' : 'Respond'} <ArrowRight size={14} /></button></footer></article>; }

function ProjectCard({ project }: { project: { title: string; summary: string; completion: number; provider: string; statusLabel: string } }) { return <article className="project-card"><div className="project-icon"><Target size={20} /></div><div className="project-main"><div className="project-title"><StatusPill status={project.statusLabel as 'SANDBOX'} /><span>{project.completion}% complete</span></div><h3>{project.title}</h3><p>{project.summary}</p><div className="project-progress"><span style={{ width: `${project.completion}%` }} /></div><small>Provider: {project.provider}</small></div><ChevronRight /></article>; }

function RequestCard({ request }: { request: ServiceRequest }) { return <article className="request-card"><div><span className="category-icon"><BriefcaseBusiness size={17} /></span><div><h3>{request.title}</h3><p>{request.category} · {request.location} · {request.offers} offers</p></div></div><div><strong>{formatMoney(request.budget)} PKR</strong><small className={`request-state ${request.status}`}>{request.status}</small></div></article>; }
function Field({ label, name, type = 'text', placeholder, required, value, onChange, readOnly, min }: { label: string; name: string; type?: string; placeholder?: string; required?: boolean; value?: string; onChange?: (value: string) => void; readOnly?: boolean; min?: string }) { return <label>{label}<input name={name} type={type} placeholder={placeholder} required={required} value={value} onChange={(event) => onChange?.(event.target.value)} readOnly={readOnly} min={min} /></label>; }
function StatusPill({ status }: { status: 'LIVE PILOT' | 'INTERACTIVE DEMO' | 'SANDBOX' | 'ROADMAP' }) { return <span className={`status-pill ${status.toLowerCase().replaceAll(' ', '-')}`}>{status}</span>; }
function Metric({ icon, value, label }: { icon: ReactNode; value: string; label: string }) { return <div className="metric"><span>{icon}</span><b>{value}</b><small>{label}</small></div>; }
function SectionHeading({ title, action, onClick }: { title: string; action: string; onClick?: () => void }) { return <div className="section-heading"><h2>{title}</h2><button onClick={onClick}>{action} <ChevronRight size={15} /></button></div>; }
function Detail({ label, value }: { label: string; value: string }) { return <div><small>{label}</small><strong>{value}</strong></div>; }
function NavButton({ active, onClick, label, icon, badge }: { active: boolean; onClick: () => void; label: string; icon: ReactNode; badge?: number }) { return <button className={active ? 'active' : ''} onClick={onClick}><span>{icon}{badge ? <i>{badge}</i> : null}</span><small>{label}</small></button>; }

function formatMoney(value: number) { return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(value); }
function hoursLeft(iso: string) { return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 3600000)); }
function relativeTime(iso: string) { const hours = Math.round((Date.now() - new Date(iso).getTime()) / 3600000); return hours < 1 ? 'just now' : hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`; }
function stageLabel(stage: Proposal['stage']) { return ({ discussion: 'Discussion', draft: 'Draft', active_vote: 'Vote open', approved: 'Approved', rejected: 'Rejected', implemented: 'Implemented' } as const)[stage]; }

export default App;

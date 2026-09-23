import type { DemoState, JarvisMessage } from '../domain/types';

const contextWords = (state: DemoState) => ({
  vote: state.proposals.find((proposal) => proposal.stage === 'active_vote'),
  emergency: state.emergencies.find((incident) => incident.status === 'active'),
  challenge: state.challenges[0],
  treasuryEntries: state.ledger.filter((entry) => entry.status === 'verified').length
});

export function localJarvisReply(state: DemoState, prompt: string): JarvisMessage {
  const input = prompt.toLowerCase();
  const { vote, emergency, challenge, treasuryEntries } = contextWords(state);
  let content = '';
  let citations: JarvisMessage['citations'] = [];
  let actionLevel: JarvisMessage['actionLevel'] = 0;

  if (input.includes('attention') || input.includes('brief')) {
    content = `Three things may need your attention: “${vote?.title}” closes in about four hours; a local editing request matches your profile; and the verified ${emergency?.title.toLowerCase()} remains active. I can explain any item or prepare a draft action.`;
    citations = [{ label: 'Active vote', entity: vote?.id ?? '' }, { label: 'Verified emergency', entity: emergency?.id ?? '' }];
  } else if (input.includes('vote') || input.includes('proposal') || input.includes('water')) {
    content = `The water-line proposal is a member vote with a frozen eligibility list, 50% quorum and 60% approval threshold. Four of ten eligible members have voted so far. I can summarise evidence or prepare an argument, but only the deterministic rules engine can record a result.`;
    citations = [{ label: 'Water-line proposal', entity: vote?.id ?? '' }];
    actionLevel = 1;
  } else if (input.includes('treasury') || input.includes('money') || input.includes('donation')) {
    content = `The Nabvi Hub treasury is labelled Sandbox. I found ${treasuryEntries} verified ledger records, including the solar-lighting receipt. Demo balances are not real money; a finance role and a trusted backend command are required for any real provider integration.`;
    citations = [{ label: 'Treasury audit trail', entity: 'treasury-nabvi' }];
  } else if (input.includes('emergency') || input.includes('flood')) {
    content = `The Upper Sindh flood-relief alert is verified in this demo and marked severity 5. Current needs are clean-water kits, temporary shelter and volunteer drivers. I can help you find a matching volunteer task; publishing a public commitment would require confirmation.`;
    citations = [{ label: 'Flood relief incident', entity: emergency?.id ?? '' }];
    actionLevel = 2;
  } else if (input.includes('lab') || input.includes('science') || input.includes('challenge')) {
    content = `The featured Humanity Lab challenge is “${challenge?.title}.” It has ${challenge?.participants} participants and asks for reproducible calibration evidence, not just a concept. I can help make a learning plan or a simulation submission draft.`;
    citations = [{ label: 'Humanity Lab challenge', entity: challenge?.id ?? '' }];
    actionLevel = 1;
  } else if (input.includes('post') || input.includes('publish')) {
    content = `I can prepare a clear, evidence-aware post for your selected scope. Publishing is a level 3 external action, so you will always review and confirm before it becomes visible.`;
    actionLevel = 3;
  } else {
    content = `I can help connect information to action: explain a rule, inspect evidence, prepare a proposal, find a service, or summarize an emergency. I’ll label demo data, uncertainty, and any action that needs your confirmation.`;
  }

  return {
    id: `jarvis-${Date.now()}`,
    role: 'jarvis',
    content,
    createdAt: new Date().toISOString(),
    citations,
    confidence: 'high',
    actionLevel
  };
}

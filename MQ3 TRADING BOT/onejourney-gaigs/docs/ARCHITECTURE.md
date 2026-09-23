# Architecture and data boundaries

## Runtime topology

The mobile app is a React + Capacitor client. In demo mode, `OneJourneyStore` persists a normalized pilot state in local storage and provides the same command boundary that the production repository uses. The Firebase Cloud Functions package is the trusted production boundary. Firebase Authentication identifies the caller, Firestore stores documents, Cloud Functions validate commands, and Firestore listeners supply real-time updates.

## Collections

Core collections are intentionally explicit: `users`, `profiles`, `devices`, `privacySettings`, `geographicScopes`, `communities`, `memberships`, `joinRequests`, `communityRules`, `constitutions`, `posts`, `comments`, `evidence`, `issues`, `proposals`, `arguments`, `eligibilitySnapshots`, `ballots`, `delegations`, `results`, `treasuries`, `ledgerEntries`, `receipts`, `integrityCheckpoints`, `projects`, `projectTasks`, `verificationEvents`, `serviceProfiles`, `requests`, `offers`, `jobs`, `ratings`, `incidents`, `needs`, `reliefReports`, `challenges`, `teams`, `submissions`, `assistantSessions`, `toolCalls`, `conversations`, `messages`, `notifications`, and `auditEvents`.

All documents include a `scope` (`personal`, `community`, `city`, `country`, or `global`) and an owning community or organization when applicable. Exact residential locations, private beneficiaries, credentials, recovery details and raw identity evidence reside in restricted collections and are never copied to public records or chains.

## Trusted command paths

| Command | Trusted handler responsibility |
| --- | --- |
| `castBallot` | Validate caller, frozen eligibility snapshot, open window, ballot uniqueness, secret/public setting and append audit event. |
| `closeProposal` | Calculate quorum and threshold deterministically, atomically write immutable result, create draft project only when rules allow. |
| `recordLedgerEntry` | Verify finance role, sandbox/regulated provider mode, balance invariant and receipt relationship. |
| `resolveJoinRequest` | Validate community role, status transition and appeal policy; append audit event. |
| `verifyMilestone` | Verify evidence requirements and permitted verifier role before updating project completion. |

LLM calls go through an allowlisted tool gateway. They receive only authorization-filtered context; external content is treated as untrusted reference material. JARVIS may prepare a draft, but level 3 public actions require confirmation and level 4 governance/security/financial actions always use a human-authorized, deterministic command.

## Audit integrity

Every protected operation receives a monotonically ordered event with the previous event hash and a deterministic payload hash. Corrections are new `supersedes` events, not deletions. A scheduled worker can anchor batches to a configured Ethereum-compatible testnet; identity and sensitive fields remain off-chain.

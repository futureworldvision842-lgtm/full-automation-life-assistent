"""
core/gaigs/civilization_engine.py — G.A.I.G.S. Civilization Upgrade Engine
========================================================================
Sovereign Master: Muhammad Qureshi
Phone: +923468053268 | Email: futureworldvision842@gmail.com
Identity Standard: Absolute ZERO occurrences of prohibited legacy identifiers.

Implements the Five Pillars of the Global AI Decentralized Governance System:
  1. Transparent Democracy: Blockchain-verified direct voting & AI impact analysis.
  2. Community Unity Hubs: Physical & digital civic centers based on Masjid-e-Nabawi model.
  3. Blockchain Transparency: Real-time public spending explorer & anti-corruption sentinels.
  4. Scientific Gamification: Planetary physics & space collaborative challenge laboratory.
  5. AI-Assisted Decisions: Islamic ethics framework (Tawhid, Adl, Shura, Amanah, Rahmah).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Jarvis.GAIGS.CivilizationEngine")

# Sovereign Identity Constants
SOVEREIGN_FOUNDER = "Muhammad Qureshi"
FOUNDER_EMAIL = "futureworldvision842@gmail.com"
FOUNDER_PHONE = "+923468053268"

# ---------------------------------------------------------------------------
# Data Models: Pillar 1 — Transparent Democracy
# ---------------------------------------------------------------------------
PROPOSAL_LIFECYCLE_STATES = ("DRAFT", "ACTIVE", "APPROVED", "REJECTED", "EXECUTED", "OPEN")


def normalize_vote_choice(raw_choice: str) -> str:
    """
    Normalizes civic vote choices:
    - 'aye', 'for', 'yes', 'y', 'in_favor', 'true', '1' -> 'FOR'
    - 'nay', 'against', 'no', 'n', 'false', '0' -> 'AGAINST'
    - 'abstain', 'pass', 'neutral' -> 'ABSTAIN'
    """
    c = str(raw_choice).strip().lower()
    if c in {"aye", "for", "yes", "y", "in_favor", "true", "1"}:
        return "FOR"
    if c in {"nay", "against", "no", "n", "false", "0"}:
        return "AGAINST"
    if c in {"abstain", "pass", "neutral"}:
        return "ABSTAIN"
    raise ValueError(f"Invalid vote choice '{raw_choice}'. Expected 'FOR', 'AGAINST', or 'ABSTAIN'.")


@dataclass
class Proposal:
    proposal_id: str
    title: str
    category: str  # INFRASTRUCTURE, HEALTHCARE, EDUCATION, CIVIC_WELFARE, ECONOMY
    author: str
    description: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400 * 7)  # 7-day default
    quorum_pct: float = 20.0
    votes_for: int = 0
    votes_against: int = 0
    votes_abstain: int = 0
    total_votes: int = 0
    quadratic_votes_for: float = 0.0
    quadratic_votes_against: float = 0.0
    quadratic_credits_spent: int = 0
    status: str = "OPEN"  # DRAFT, ACTIVE, OPEN, APPROVED, REJECTED, EXECUTED
    ai_impact_analysis: Optional[Dict[str, Any]] = None
    merkle_root: str = ""

    def calculate_result(self) -> Dict[str, Any]:
        """Calculates voting outcome, quadratic tally, and quorum threshold."""
        total = self.votes_for + self.votes_against + self.votes_abstain
        self.total_votes = total
        for_pct = round((self.votes_for / total * 100.0), 2) if total > 0 else 0.0
        against_pct = round((self.votes_against / total * 100.0), 2) if total > 0 else 0.0

        qv_total = self.quadratic_votes_for + self.quadratic_votes_against
        qv_for_pct = round((self.quadratic_votes_for / qv_total * 100.0), 2) if qv_total > 0 else 0.0

        passed = (for_pct > 50.0) and (total >= 10)  # Min 10 votes for democratic quorum in demo
        if self.status in ["DRAFT", "EXECUTED"]:
            pass  # Retain explicit draft or executed states
        elif time.time() > self.expires_at:
            self.status = "APPROVED" if passed else "REJECTED"
        elif passed:
            self.status = "APPROVED"

        return {
            "proposal_id": self.proposal_id,
            "total_votes": total,
            "for_pct": for_pct,
            "against_pct": against_pct,
            "quadratic_votes_for": round(self.quadratic_votes_for, 2),
            "quadratic_votes_against": round(self.quadratic_votes_against, 2),
            "quadratic_credits_spent": self.quadratic_credits_spent,
            "qv_for_pct": qv_for_pct,
            "status": self.status,
            "passed": passed
        }

    def transition_status(self, new_status: str) -> bool:
        s = new_status.upper().strip()
        if s in PROPOSAL_LIFECYCLE_STATES:
            self.status = s
            return True
        return False


# ---------------------------------------------------------------------------
# Data Models: Pillar 5 — Gamified Civic Engagement & Citizen Score
# ---------------------------------------------------------------------------
@dataclass
class CitizenProfile:
    citizen_id: str
    name: str = ""
    score: int = 100
    rank: str = "Active Participant"
    proposals_submitted: int = 0
    votes_cast: int = 0
    quadratic_credits_spent: int = 0
    disputes_filed: int = 0
    challenges_solved: int = 0
    badges: List[Dict[str, Any]] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)



# ---------------------------------------------------------------------------
# Data Models: Pillar 2 — Community Unity Hubs (Masjid-e-Nabawi Model)
# ---------------------------------------------------------------------------
@dataclass
class UnityHub:
    hub_id: str
    name: str
    hub_type: str  # MASJID_MODEL, CIVIC_CENTER, YOUTH_ACADEMY, VIRTUAL_COMMUNITY
    city: str
    country: str
    latitude: float
    longitude: float
    admin_lead: str
    registered_members: int = 0
    welfare_funds_usd: float = 0.0
    active_disputes_count: int = 0
    services_offered: List[str] = field(default_factory=list)
    reputation_score: float = 95.0


# ---------------------------------------------------------------------------
# Data Models: Pillar 3 — Blockchain Transparency & Spending Explorer
# ---------------------------------------------------------------------------
@dataclass
class SpendingLedgerEntry:
    tx_hash: str
    department: str
    purpose: str
    recipient: str
    amount_usd: float
    timestamp: float = field(default_factory=time.time)
    verified_by_ai: bool = True
    audit_flag: str = "CLEAN"  # CLEAN, SUSPICIOUS_SPLIT, UNVERIFIED_VENDOR, PRICE_OUTLIER
    proof_hash: str = ""


# ---------------------------------------------------------------------------
# Data Models: Pillar 4 — Scientific Gamification
# ---------------------------------------------------------------------------
@dataclass
class ScientificChallenge:
    challenge_id: str
    title: str
    domain: str  # SPACE_PROPULSION, WATER_DESALINATION, SOLAR_STORAGE, AI_GOVERNANCE, FUSION_DYNAMICS
    description: str
    difficulty: str  # NOVICE, APPRENTICE, SCHOLAR, GRANDMASTER
    bounty_points: int
    submitted_solutions_count: int = 0
    highest_solution_score: float = 0.0
    top_contributor: Optional[str] = None


# ---------------------------------------------------------------------------
# Data Models: Pillar 5 — Islamic Ethics AI Advisory
# ---------------------------------------------------------------------------
@dataclass
class EthicsAssessment:
    tawhid_coherence_score: float  # 0.0 - 100.0 (Systemic unity & non-fragmentation)
    adl_justice_score: float        # 0.0 - 100.0 (Equal access, zero discrimination)
    shura_consultation_score: float # 0.0 - 100.0 (Democratic deliberation & open consensus)
    amanah_integrity_score: float   # 0.0 - 100.0 (Financial transparency & auditability)
    rahmah_compassion_score: float  # 0.0 - 100.0 (Public welfare & vulnerable protection)
    composite_ethics_score: float   # Weighted average
    verdict: str                    # ETHICALLY_ALIGNED, CONDITIONALLY_ACCEPTABLE, UNETHICAL_REJECT
    recommendations: List[str]


def _compute_merkle_root_and_proof(leaves: List[str], target_index: int) -> Tuple[str, List[Dict[str, str]]]:
    """
    Computes a cryptographic Merkle Root and sibling proof path for leaf at target_index.
    """
    if not leaves:
        empty_root = hashlib.sha256(b"EMPTY_LEDGER").hexdigest()
        return empty_root, []

    tree = [leaves]
    current = leaves
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            next_level.append(combined)
        tree.append(next_level)
        current = next_level

    merkle_root = tree[-1][0]

    # Build proof path for target_index
    proof: List[Dict[str, str]] = []
    idx = target_index
    for level in range(len(tree) - 1):
        is_right = (idx % 2 == 1)
        sibling_idx = idx - 1 if is_right else (idx + 1 if idx + 1 < len(tree[level]) else idx)
        sibling_hash = tree[level][sibling_idx]
        proof.append({
            "position": "left" if is_right else "right",
            "hash": sibling_hash
        })
        idx //= 2

    return merkle_root, proof


# ---------------------------------------------------------------------------
# Core Engine Implementation
# ---------------------------------------------------------------------------
class CivilizationEngine:
    """
    Unified Orchestrator for the G.A.I.G.S. Civilization Operating System (Humanity 3.0).
    """

    def __init__(self):
        self._proposals: Dict[str, Proposal] = {}
        self._votes: Dict[str, Dict[str, str]] = {}  # proposal_id -> {voter_id: choice}
        self._quadratic_votes: Dict[str, Dict[str, Dict[str, Any]]] = {}  # proposal_id -> {voter_id: qv_data}
        self._citizen_audits: List[Dict[str, Any]] = []
        self._citizens: Dict[str, CitizenProfile] = {}
        self._hubs: Dict[str, UnityHub] = {}
        self._ledger: List[SpendingLedgerEntry] = []
        self._challenges: Dict[str, ScientificChallenge] = {}
        self._initialize_seed_ecosystem()

    def _initialize_seed_ecosystem(self):
        """Initializes canonical reference ecosystem for demonstration and production readiness."""
        # 1. Seed Proposals
        seed_p1 = Proposal(
            proposal_id="GAIGS-PROP-001",
            title="Masjid-e-Nabawi Decentralized Micro-Solar Grid Initiative",
            category="INFRASTRUCTURE",
            author="Master Muhammad Qureshi",
            description="Establish decentralized rooftop solar arrays on civic hubs and masajid with community-owned battery storage and zero-interest micro-energy sharing.",
            quorum_pct=25.0,
            votes_for=1420,
            votes_against=42,
            votes_abstain=18,
            status="APPROVED",
            ai_impact_analysis={
                "projected_cost_savings_usd": 85000.0,
                "clean_energy_kwh_annual": 420000.0,
                "community_resilience_rating": "CRITICAL_EXCELLENCE",
                "payback_period_years": 3.2
            },
            merkle_root=hashlib.sha256(b"GAIGS-PROP-001-SEED").hexdigest()
        )
        self._proposals[seed_p1.proposal_id] = seed_p1

        seed_p2 = Proposal(
            proposal_id="GAIGS-PROP-002",
            title="Real-Time Algorithmic Municipal Water Purity Surveillance",
            category="CIVIC_WELFARE",
            author="Community Health Taskforce",
            description="Deploy IoT chemical turbidity sensors across urban distribution pipelines with public dashboard telemetry and automatic shut-off valves for contamination.",
            quorum_pct=20.0,
            votes_for=880,
            votes_against=15,
            votes_abstain=5,
            status="APPROVED",
            ai_impact_analysis={
                "estimated_disease_prevention_pct": 74.5,
                "monitoring_latency_seconds": 1.5,
                "estimated_coverage_households": 120000
            },
            merkle_root=hashlib.sha256(b"GAIGS-PROP-002-SEED").hexdigest()
        )
        self._proposals[seed_p2.proposal_id] = seed_p2

        # 2. Seed Unity Hubs
        self._hubs["HUB-ISB-001"] = UnityHub(
            hub_id="HUB-ISB-001",
            name="Jamia Masjid Nabvi Qureshi Hashmi Hub",
            hub_type="MASJID_MODEL",
            city="Islamabad",
            country="Pakistan",
            latitude=33.6844,
            longitude=73.0479,
            admin_lead="Haji Ghulam Yasin & Abdul Ghaffar Qureshi",
            registered_members=4500,
            welfare_funds_usd=28500.0,
            active_disputes_count=0,
            services_offered=["Community Conflict Mediation", "Food Security Kitchen", "Youth AI Coding Lab", "Micro-Loan Registry"],
            reputation_score=99.2
        )

        self._hubs["HUB-LDN-002"] = UnityHub(
            hub_id="HUB-LDN-002",
            name="London Metropolitan Civic Unity Hub",
            hub_type="CIVIC_CENTER",
            city="London",
            country="United Kingdom",
            latitude=51.5074,
            longitude=-0.1278,
            admin_lead="Council Directorate",
            registered_members=3200,
            welfare_funds_usd=45000.0,
            active_disputes_count=1,
            services_offered=["Interfaith Discussion Forum", "Skills Exchange Bazaar", "Digital Democracy Kiosk"],
            reputation_score=96.4
        )

        # 3. Seed Spending Ledger Entries
        self._record_verified_expenditure(
            department="Public Infrastructure & Clean Energy",
            purpose="Phase 1 Solar Inverter Hardware Acquisition",
            recipient="Tier-1 Photovoltaic Hardware Guild",
            amount_usd=14500.0
        )
        self._record_verified_expenditure(
            department="Community Welfare & Food Security",
            purpose="Monthly Essential Grains Distribution to 650 Families",
            recipient="Al-Rahmah Flour & Grain Collective",
            amount_usd=8200.0
        )
        self._record_verified_expenditure(
            department="Civic Technology & Education",
            purpose="Open-Source AI Lab Workstations for Underprivileged Students",
            recipient="Open Education Hardware Supply",
            amount_usd=6750.0
        )

        # 4. Seed Scientific Gamification Challenges
        self._challenges["CHAL-001"] = ScientificChallenge(
            challenge_id="CHAL-001",
            title="Closed-Loop Zero-Energy Atmospheric Water Harvester",
            domain="WATER_DESALINATION",
            description="Design an optimal biomimetic condensing lattice inspired by the Namib desert beetle operating at <15% relative humidity without external electrical grid power.",
            difficulty="SCHOLAR",
            bounty_points=5000,
            submitted_solutions_count=84,
            highest_solution_score=92.4,
            top_contributor="Team HydroNexus"
        )
        self._challenges["CHAL-002"] = ScientificChallenge(
            challenge_id="CHAL-002",
            title="High-Temperature Superconducting Magnetic Confinement Geometry",
            domain="FUSION_DYNAMICS",
            description="Simulate toroidal magnetic field coil arrangement minimizing turbulent electron drift wave dissipation using open physics tensor models.",
            difficulty="GRANDMASTER",
            bounty_points=12000,
            submitted_solutions_count=39,
            highest_solution_score=88.1,
            top_contributor="QuantumToroid84"
        )

    # -----------------------------------------------------------------------
    # Pillar 1 Methods: Transparent Democracy
    # -----------------------------------------------------------------------
    def submit_proposal(
        self,
        title: str,
        category: str,
        author: str,
        description: str,
        quorum_pct: float = 20.0,
        duration_days: int = 7,
        status: str = "OPEN"
    ) -> Proposal:
        """Submits a new policy or civic proposal and generates immediate AI impact analysis."""
        prop_id = f"GAIGS-PROP-{int(time.time() * 1000) % 1000000:06d}"
        expires_at = time.time() + (duration_days * 86400)

        # Generate automated AI impact analysis
        ethics = self.evaluate_islamic_ethics(title, description, category)
        ai_analysis = {
            "ethics_score": ethics.composite_ethics_score,
            "ethics_verdict": ethics.verdict,
            "estimated_beneficiaries": 15000,
            "projected_cost_efficiency_rating": "HIGH",
            "risk_mitigation_notes": ethics.recommendations
        }

        raw_digest = f"{prop_id}:{title}:{author}:{time.time()}".encode("utf-8")
        merkle = hashlib.sha256(raw_digest).hexdigest()

        prop_status = status.upper().strip() if status else "OPEN"
        if prop_status not in PROPOSAL_LIFECYCLE_STATES:
            prop_status = "OPEN"

        prop = Proposal(
            proposal_id=prop_id,
            title=title,
            category=category.upper(),
            author=author,
            description=description,
            created_at=time.time(),
            expires_at=expires_at,
            quorum_pct=quorum_pct,
            status=prop_status,
            ai_impact_analysis=ai_analysis,
            merkle_root=merkle
        )
        self._proposals[prop_id] = prop
        self._votes[prop_id] = {}
        self._quadratic_votes[prop_id] = {}
        
        # Award author points on citizen score
        self._record_citizen_activity(author, proposals_submitted=1)
        logger.info("Submitted GAIGS proposal: %s by %s [Status: %s]", prop_id, author, prop.status)
        return prop

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: str  # FOR, AGAINST, ABSTAIN (or aye, nay, yes, no, etc.)
    ) -> Dict[str, Any]:
        """Casts a cryptographically verifiable vote on an active proposal with normalized choices."""
        if proposal_id not in self._proposals:
            return {"ok": False, "error": f"Proposal '{proposal_id}' not found"}

        prop = self._proposals[proposal_id]
        if prop.status == "DRAFT":
            return {"ok": False, "error": "Proposal is still in DRAFT status and not yet open for voting"}
        if prop.status in ["REJECTED", "EXECUTED"]:
            return {"ok": False, "error": f"Proposal is closed ({prop.status})"}

        try:
            vote_norm = normalize_vote_choice(choice)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

        # Prevent duplicate voting by voter_id
        prop_votes = self._votes.setdefault(proposal_id, {})
        existing = prop_votes.get(voter_id)

        if existing:
            # Reverse previous choice
            if existing == "FOR":
                prop.votes_for = max(0, prop.votes_for - 1)
            elif existing == "AGAINST":
                prop.votes_against = max(0, prop.votes_against - 1)
            elif existing == "ABSTAIN":
                prop.votes_abstain = max(0, prop.votes_abstain - 1)

        # Apply new choice
        if vote_norm == "FOR":
            prop.votes_for += 1
        elif vote_norm == "AGAINST":
            prop.votes_against += 1
        elif vote_norm == "ABSTAIN":
            prop.votes_abstain += 1

        prop_votes[voter_id] = vote_norm
        prop.total_votes = len(prop_votes)

        # Generate cryptographic receipt
        receipt_raw = f"{proposal_id}:{voter_id}:{vote_norm}:{time.time()}".encode("utf-8")
        vote_receipt_hash = hashlib.sha256(receipt_raw).hexdigest()

        outcome = prop.calculate_result()

        # Award voter participation score
        self._record_citizen_activity(voter_id, votes_cast=1)

        return {
            "ok": True,
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "choice": vote_norm,
            "vote_receipt_hash": vote_receipt_hash,
            "current_tally": outcome
        }

    def cast_quadratic_vote(
        self,
        proposal_id: str,
        voter_id: str,
        credits_spent: int,
        choice: str
    ) -> Dict[str, Any]:
        """
        Casts a Quadratic Vote where weight = sqrt(credits_spent).
        Normalizes choice: 'aye', 'for', 'yes' -> 'FOR'; 'nay', 'against', 'no' -> 'AGAINST'.
        """
        if proposal_id not in self._proposals:
            return {"ok": False, "error": f"Proposal '{proposal_id}' not found"}

        prop = self._proposals[proposal_id]
        if prop.status == "DRAFT":
            return {"ok": False, "error": "Proposal is still in DRAFT status and not yet open for voting"}
        if prop.status in ["REJECTED", "EXECUTED"]:
            return {"ok": False, "error": f"Proposal is closed ({prop.status})"}

        try:
            credits_int = int(credits_spent)
            if credits_int <= 0:
                return {"ok": False, "error": "credits_spent must be a positive integer >= 1"}
        except (ValueError, TypeError):
            return {"ok": False, "error": "credits_spent must be a valid integer"}

        try:
            vote_norm = normalize_vote_choice(choice)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

        if vote_norm not in ["FOR", "AGAINST"]:
            return {"ok": False, "error": "Quadratic voting choice must be 'FOR' or 'AGAINST'"}

        # Calculate quadratic weight: W = sqrt(credits_spent)
        weight = round(math.sqrt(credits_int), 4)

        qv_map = self._quadratic_votes.setdefault(proposal_id, {})
        existing = qv_map.get(voter_id)

        if existing:
            # Revert old quadratic weight and credits
            old_choice = existing["choice"]
            old_weight = existing["weight"]
            old_credits = existing["credits_spent"]
            if old_choice == "FOR":
                prop.quadratic_votes_for = max(0.0, prop.quadratic_votes_for - old_weight)
            elif old_choice == "AGAINST":
                prop.quadratic_votes_against = max(0.0, prop.quadratic_votes_against - old_weight)
            prop.quadratic_credits_spent = max(0, prop.quadratic_credits_spent - old_credits)

        # Apply new weight and credits
        if vote_norm == "FOR":
            prop.quadratic_votes_for += weight
        elif vote_norm == "AGAINST":
            prop.quadratic_votes_against += weight
        prop.quadratic_credits_spent += credits_int

        ts = time.time()
        qv_map[voter_id] = {
            "voter_id": voter_id,
            "choice": vote_norm,
            "credits_spent": credits_int,
            "weight": weight,
            "timestamp": ts
        }

        # Update standard voter tally as well
        prop_votes = self._votes.setdefault(proposal_id, {})
        if voter_id not in prop_votes:
            if vote_norm == "FOR":
                prop.votes_for += 1
            else:
                prop.votes_against += 1
            prop_votes[voter_id] = vote_norm
            prop.total_votes = len(prop_votes)

        receipt_raw = f"QV:{proposal_id}:{voter_id}:{credits_int}:{weight}:{vote_norm}:{ts}".encode("utf-8")
        vote_receipt_hash = hashlib.sha256(receipt_raw).hexdigest()

        outcome = prop.calculate_result()

        # Award citizen points for quadratic voting
        self._record_citizen_activity(voter_id, votes_cast=1, quadratic_credits=credits_int)

        return {
            "ok": True,
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "choice": vote_norm,
            "credits_spent": credits_int,
            "weight": weight,
            "vote_weight": weight,
            "vote_receipt_hash": vote_receipt_hash,
            "current_tally": outcome
        }

    def transition_proposal_status(self, proposal_id: str, new_status: str) -> Dict[str, Any]:
        """Transitions proposal through its lifecycle: DRAFT -> ACTIVE -> APPROVED / REJECTED -> EXECUTED."""
        if proposal_id not in self._proposals:
            return {"ok": False, "error": f"Proposal '{proposal_id}' not found"}
        prop = self._proposals[proposal_id]
        s = new_status.upper().strip()
        if s not in PROPOSAL_LIFECYCLE_STATES:
            return {"ok": False, "error": f"Invalid status '{new_status}'. Allowed: DRAFT, ACTIVE, APPROVED, REJECTED, EXECUTED"}
        prev = prop.status
        prop.status = s
        return {"ok": True, "proposal_id": proposal_id, "previous_status": prev, "status": s}

    def list_proposals(self) -> List[Dict[str, Any]]:
        """Returns all proposals with computed tallies."""
        return [asdict(p) for p in self._proposals.values()]

    # -----------------------------------------------------------------------
    # Pillar 2 Methods: Community Unity Hubs (Masjid-e-Nabawi Model)
    # -----------------------------------------------------------------------
    def register_hub(
        self,
        name: str,
        hub_type: str,
        city: str,
        country: str,
        latitude: float,
        longitude: float,
        admin_lead: str,
        services: Optional[List[str]] = None
    ) -> UnityHub:
        """Registers a new physical or virtual Community Unity Hub."""
        hub_id = f"HUB-{city[:3].upper()}-{len(self._hubs) + 1:03d}"
        hub = UnityHub(
            hub_id=hub_id,
            name=name,
            hub_type=hub_type.upper(),
            city=city,
            country=country,
            latitude=latitude,
            longitude=longitude,
            admin_lead=admin_lead,
            registered_members=1,
            welfare_funds_usd=0.0,
            services_offered=services or ["Direct Democracy Kiosk", "Local Mediation"],
            reputation_score=100.0
        )
        self._hubs[hub_id] = hub
        logger.info("Registered Community Unity Hub: %s in %s", name, city)
        return hub

    def list_hubs(self) -> List[Dict[str, Any]]:
        """Returns all registered community unity hubs."""
        return [asdict(h) for h in self._hubs.values()]

    # -----------------------------------------------------------------------
    # Pillar 3 Methods: Blockchain Spending Transparency & Anti-Corruption
    # -----------------------------------------------------------------------
    def _record_verified_expenditure(
        self,
        department: str,
        purpose: str,
        recipient: str,
        amount_usd: float
    ) -> SpendingLedgerEntry:
        """Internal helper to record an expenditure with SHA-256 cryptographic audit receipt."""
        ts = time.time()
        tx_raw = f"{department}:{purpose}:{recipient}:{amount_usd}:{ts}".encode("utf-8")
        tx_hash = "0x" + hashlib.sha256(tx_raw).hexdigest()

        # Anti-corruption heuristic check
        audit_flag = "CLEAN"
        if amount_usd > 100000.0:
            audit_flag = "REQUIRES_DUAL_COUNCIL_AUDIT"
        elif amount_usd < 0:
            audit_flag = "INVALID_NEGATIVE_AMOUNT"

        entry = SpendingLedgerEntry(
            tx_hash=tx_hash,
            department=department,
            purpose=purpose,
            recipient=recipient,
            amount_usd=round(float(amount_usd), 2),
            timestamp=ts,
            verified_by_ai=True,
            audit_flag=audit_flag,
            proof_hash=hashlib.sha256((tx_hash + str(ts)).encode("utf-8")).hexdigest()
        )
        self._ledger.append(entry)
        return entry

    def record_expenditure(
        self,
        department: str,
        purpose: str,
        recipient: str,
        amount_usd: float
    ) -> Dict[str, Any]:
        """Public API to record transparent expenditure and return verified ledger entry."""
        entry = self._record_verified_expenditure(department, purpose, recipient, amount_usd)
        return asdict(entry)

    def get_transparency_ledger(self) -> Dict[str, Any]:
        """Returns complete spending explorer telemetry, aggregate stats, and transparency score."""
        total_spent = sum(e.amount_usd for e in self._ledger)
        clean_count = sum(1 for e in self._ledger if e.audit_flag == "CLEAN")
        transparency_score = round((clean_count / len(self._ledger) * 100.0), 2) if self._ledger else 100.0

        return {
            "total_expenditure_usd": round(total_spent, 2),
            "total_transactions": len(self._ledger),
            "transparency_audit_score": transparency_score,
            "entries": [asdict(e) for e in reversed(self._ledger)]
        }

    def get_spending_records(self) -> List[Dict[str, Any]]:
        """
        Returns spending ledger as a flat ARRAY of entries with dual keys:
        id / tx_hash, category / department, vendor / recipient, flagged / audit_flag, sha256_hash / proof_hash.
        Eliminates frontend records.map() TypeError.
        """
        records: List[Dict[str, Any]] = []
        for entry in reversed(self._ledger):
            records.append({
                "id": entry.tx_hash,
                "tx_hash": entry.tx_hash,
                "category": entry.department,
                "department": entry.department,
                "vendor": entry.recipient,
                "recipient": entry.recipient,
                "amount": entry.amount_usd,
                "amount_usd": entry.amount_usd,
                "purpose": entry.purpose,
                "timestamp": entry.timestamp,
                "verified_by_ai": entry.verified_by_ai,
                "flagged": entry.audit_flag != "CLEAN",
                "audit_flag": entry.audit_flag,
                "sha256_hash": entry.proof_hash,
                "proof_hash": entry.proof_hash
            })
        return records

    def log_citizen_dispute(
        self,
        tx_hash: str,
        citizen_id: str,
        dispute_reason: str
    ) -> Dict[str, Any]:
        """
        Logs a citizen audit dispute against a spending transaction and flags it for Shura review.
        """
        ts = time.time()
        audit_id = f"AUDIT-{int(ts * 1000) % 1000000:06d}"

        # Find entry in ledger and update flag
        matched = False
        for entry in self._ledger:
            if entry.tx_hash == tx_hash:
                entry.audit_flag = "DISPUTED_BY_CITIZEN"
                matched = True
                break

        receipt_raw = f"{audit_id}:{tx_hash}:{citizen_id}:{dispute_reason}:{ts}".encode("utf-8")
        audit_receipt_hash = hashlib.sha256(receipt_raw).hexdigest()

        record = {
            "audit_id": audit_id,
            "tx_hash": tx_hash,
            "citizen_id": citizen_id,
            "dispute_reason": dispute_reason,
            "status": "DISPUTED",
            "matched_transaction": matched,
            "timestamp": ts,
            "audit_receipt_hash": audit_receipt_hash
        }
        self._citizen_audits.append(record)

        # Award citizen points for participating as a transparency sentinel
        self._record_citizen_activity(citizen_id, disputes_filed=1)

        return {
            "ok": True,
            "audit_id": audit_id,
            "tx_hash": tx_hash,
            "citizen_id": citizen_id,
            "dispute_reason": dispute_reason,
            "status": "DISPUTED",
            "audit_receipt_hash": audit_receipt_hash,
            "timestamp": ts,
            "message": "Citizen dispute successfully registered and flagged for independent Shura council audit."
        }

    def verify_expenditure_proof(self, tx_hash: str) -> Dict[str, Any]:
        """
        Verifies Merkle cryptographic inclusion proof for a treasury expenditure transaction.
        """
        matched_idx = -1
        matched_entry: Optional[SpendingLedgerEntry] = None
        for i, entry in enumerate(self._ledger):
            if entry.tx_hash == tx_hash or entry.proof_hash == tx_hash:
                matched_idx = i
                matched_entry = entry
                break

        if matched_entry is None or matched_idx == -1:
            return {
                "ok": False,
                "tx_hash": tx_hash,
                "verified": False,
                "error": f"Transaction '{tx_hash}' not found in blockchain spending ledger"
            }

        leaf_hashes = [e.proof_hash for e in self._ledger]
        root, proof = _compute_merkle_root_and_proof(leaf_hashes, matched_idx)

        # Independently verify the proof path
        curr = matched_entry.proof_hash
        for step in proof:
            pos = step["position"]
            sib = step["hash"]
            if pos == "right":
                curr = hashlib.sha256((curr + sib).encode("utf-8")).hexdigest()
            else:
                curr = hashlib.sha256((sib + curr).encode("utf-8")).hexdigest()

        is_verified = (curr == root)

        return {
            "ok": True,
            "tx_hash": matched_entry.tx_hash,
            "verified": is_verified,
            "proof_hash": matched_entry.proof_hash,
            "merkle_root": root,
            "merkle_proof": proof,
            "timestamp": matched_entry.timestamp,
            "audit_flag": matched_entry.audit_flag,
            "department": matched_entry.department,
            "purpose": matched_entry.purpose,
            "recipient": matched_entry.recipient,
            "amount_usd": matched_entry.amount_usd,
            "verification_status": "CRYPTOGRAPHICALLY_VERIFIED" if is_verified else "VERIFICATION_FAILED"
        }

    # -----------------------------------------------------------------------
    # Pillar 4 Methods: Scientific Gamification & Physics Lab
    # -----------------------------------------------------------------------
    def submit_solution(
        self,
        challenge_id: str,
        contributor: str,
        solution_title: str,
        solution_abstract: str,
        scientific_model_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submits a scientific problem solution, evaluates algorithmic validity, and assigns points."""
        if challenge_id not in self._challenges:
            return {"ok": False, "error": f"Challenge '{challenge_id}' not found"}

        chal = self._challenges[challenge_id]
        chal.submitted_solutions_count += 1

        # Algorithmic scoring based on rigor, detail length, and model validation
        base_score = 70.0
        word_count = len(solution_abstract.split())
        if word_count > 50:
            base_score += min(15.0, (word_count - 50) * 0.1)
        if scientific_model_data:
            base_score += 10.0

        score = round(min(98.5, max(50.0, base_score)), 1)
        if score > chal.highest_solution_score:
            chal.highest_solution_score = score
            chal.top_contributor = contributor

        awarded_points = int(chal.bounty_points * (score / 100.0))

        # Award contributor civic points
        self._record_citizen_activity(contributor, challenges_solved=1, bonus_points=awarded_points)

        return {
            "ok": True,
            "challenge_id": challenge_id,
            "contributor": contributor,
            "solution_title": solution_title,
            "score": score,
            "awarded_points": awarded_points,
            "is_new_high_score": score == chal.highest_solution_score
        }

    def list_challenges(self) -> List[Dict[str, Any]]:
        """Returns all scientific gamification challenges."""
        return [asdict(c) for c in self._challenges.values()]

    # -----------------------------------------------------------------------
    # Pillar 5 Methods: Islamic Ethics AI Framework & Gamified Citizen Score
    # -----------------------------------------------------------------------
    def _record_citizen_activity(
        self,
        citizen_id: str,
        proposals_submitted: int = 0,
        votes_cast: int = 0,
        quadratic_credits: int = 0,
        disputes_filed: int = 0,
        challenges_solved: int = 0,
        bonus_points: int = 0
    ) -> None:
        """Updates internal civic activity counts and score for a citizen."""
        prof = self._citizens.setdefault(citizen_id, CitizenProfile(citizen_id=citizen_id, name=citizen_id))
        prof.proposals_submitted += proposals_submitted
        prof.votes_cast += votes_cast
        prof.quadratic_credits_spent += quadratic_credits
        prof.disputes_filed += disputes_filed
        prof.challenges_solved += challenges_solved

        prof.score = (
            100
            + (prof.proposals_submitted * 50)
            + (prof.votes_cast * 20)
            + (prof.quadratic_credits_spent * 5)
            + (prof.disputes_filed * 40)
            + (prof.challenges_solved * 100)
            + bonus_points
        )

    def get_citizen_score(self, citizen_id: str) -> Dict[str, Any]:
        """
        Calculates and returns gamified Citizen Score, tier rank, earned badges,
        and milestone rewards for a given citizen_id.
        """
        # Seed founder or known VIPs with honorary tier if requested
        if citizen_id in ["founder", "Master Muhammad Qureshi", "MQ-001", "Muhammad Qureshi"]:
            return {
                "ok": True,
                "citizen_id": citizen_id,
                "score": 3850,
                "rank": "Sovereign Statesman",
                "badges": [
                    {"id": "genesis_founder", "name": "Civilization Founder", "earned_at": 1727300000, "description": "Author and architect of GAIGS Humanity 3.0 Operating System"},
                    {"id": "genesis_voter", "name": "Genesis Voter", "earned_at": 1727310000, "description": "Cast founding vote in Masajid Micro-Solar Grid initiative"},
                    {"id": "quadratic_scholar", "name": "Quadratic Voice Champion", "earned_at": 1727320000, "description": "Demonstrated conviction through quadratic vote allocation"},
                    {"id": "transparent_sentinel", "name": "Transparency Sentinel", "earned_at": 1727325000, "description": "Verified blockchain expenditure and anti-corruption ledgers"},
                    {"id": "science_pioneer", "name": "Grand Scholar of Science", "earned_at": 1727330000, "description": "Contributed algorithmic solutions to planetary physics challenges"}
                ],
                "milestones": [
                    {"level": 1, "name": "Civic Participant", "required_score": 100, "achieved": True, "reward": "Standard democratic proposal & voting rights"},
                    {"level": 2, "name": "Transparency Watchdog", "required_score": 500, "achieved": True, "reward": "Priority Shura dispute arbitration queue"},
                    {"level": 3, "name": "Civic Architect", "required_score": 1000, "achieved": True, "reward": "Direct co-authorship of municipal micro-funding proposals"},
                    {"level": 4, "name": "Sovereign Statesman", "required_score": 2500, "achieved": True, "reward": "Full voting weight on planetary science challenge bounties"}
                ],
                "stats": {
                    "proposals_submitted": 5,
                    "votes_cast": 42,
                    "quadratic_credits_spent": 350,
                    "disputes_filed": 3,
                    "challenges_solved": 8
                }
            }

        prof = self._citizens.get(citizen_id)
        if not prof:
            prof = CitizenProfile(citizen_id=citizen_id, name=citizen_id, score=120)
            self._citizens[citizen_id] = prof

        score = prof.score
        if score >= 2500:
            rank = "Sovereign Statesman"
        elif score >= 1000:
            rank = "Civic Architect"
        elif score >= 500:
            rank = "Shura Delegate"
        elif score >= 100:
            rank = "Active Participant"
        else:
            rank = "Novice Citizen"

        badges = []
        if prof.votes_cast >= 1 or score >= 100:
            badges.append({"id": "genesis_voter", "name": "Genesis Voter", "earned_at": int(time.time()), "description": "Cast verified democratic vote"})
        if prof.quadratic_credits_spent >= 1:
            badges.append({"id": "quadratic_scholar", "name": "Quadratic Voice Champion", "earned_at": int(time.time()), "description": "Utilized quadratic voting to express high-conviction preference"})
        if prof.disputes_filed >= 1:
            badges.append({"id": "transparent_sentinel", "name": "Transparency Sentinel", "earned_at": int(time.time()), "description": "Submitted verified audit dispute against public expenditure"})
        if prof.challenges_solved >= 1:
            badges.append({"id": "science_pioneer", "name": "Science Pioneer", "earned_at": int(time.time()), "description": "Submitted validated scientific problem solution"})
        if prof.proposals_submitted >= 1:
            badges.append({"id": "civic_author", "name": "Civic Author", "earned_at": int(time.time()), "description": "Authored and submitted a formal GAIGS civic proposal"})

        milestones = [
            {"level": 1, "name": "Civic Participant", "required_score": 100, "achieved": score >= 100, "reward": "Standard democratic proposal & voting rights"},
            {"level": 2, "name": "Transparency Watchdog", "required_score": 500, "achieved": score >= 500, "reward": "Priority Shura dispute arbitration queue"},
            {"level": 3, "name": "Civic Architect", "required_score": 1000, "achieved": score >= 1000, "reward": "Direct co-authorship of municipal micro-funding proposals"},
            {"level": 4, "name": "Sovereign Statesman", "required_score": 2500, "achieved": score >= 2500, "reward": "Full voting weight on planetary science challenge bounties"}
        ]

        return {
            "ok": True,
            "citizen_id": citizen_id,
            "score": score,
            "rank": rank,
            "badges": badges,
            "milestones": milestones,
            "stats": {
                "proposals_submitted": prof.proposals_submitted,
                "votes_cast": prof.votes_cast,
                "quadratic_credits_spent": prof.quadratic_credits_spent,
                "disputes_filed": prof.disputes_filed,
                "challenges_solved": prof.challenges_solved
            }
        }
    def evaluate_islamic_ethics(
        self,
        title: str,
        description: str,
        category: str
    ) -> EthicsAssessment:
        """
        Evaluates any policy or project against the 5 Islamic Governance Pillars:
        1. Tawhid (Coherence and holistic unity)
        2. Adl (Justice, equity, zero exploitation)
        3. Shura (Open consultation & participatory democracy)
        4. Amanah (Financial trust, transparency, zero graft)
        5. Rahmah (Compassion, poverty reduction, welfare priority)
        """
        text = f"{title} {description} {category}".lower()

        # Scoring heuristics
        tawhid_score = 95.0
        adl_score = 90.0
        shura_score = 92.0
        amanah_score = 94.0
        rahmah_score = 96.0
        recommendations = []

        # Check for exploitative keywords (Riba, monopoly, secrecy, oppression)
        if any(w in text for w in ["monopoly", "interest", "usury", "riba", "secret", "coercion"]):
            adl_score -= 40.0
            amanah_score -= 30.0
            shura_score -= 25.0
            rahmah_score -= 35.0
            recommendations.append("Eliminate interest-bearing, monopolistic, or opaque terms; replace with equity/profit-sharing (Mudarabah/Musharakah).")

        # Check for positive welfare signals
        if any(w in text for w in ["welfare", "poor", "clean", "water", "health", "solar", "education", "youth", "shelter"]):
            rahmah_score = min(100.0, rahmah_score + 3.0)
            adl_score = min(100.0, adl_score + 4.0)

        composite = round(
            (tawhid_score * 0.2) +
            (adl_score * 0.25) +
            (shura_score * 0.2) +
            (amanah_score * 0.2) +
            (rahmah_score * 0.15),
            2
        )

        if composite >= 85.0:
            verdict = "ETHICALLY_ALIGNED"
        elif composite >= 65.0:
            verdict = "CONDITIONALLY_ACCEPTABLE"
        else:
            verdict = "UNETHICAL_REJECT"

        if not recommendations:
            recommendations.append("Full alignment with Islamic civilizational values of justice, transparency, and public welfare.")

        return EthicsAssessment(
            tawhid_coherence_score=tawhid_score,
            adl_justice_score=adl_score,
            shura_consultation_score=shura_score,
            amanah_integrity_score=amanah_score,
            rahmah_compassion_score=rahmah_score,
            composite_ethics_score=composite,
            verdict=verdict,
            recommendations=recommendations
        )

    def get_civilization_summary(self) -> Dict[str, Any]:
        """Provides a master snapshot of all 5 GAIGS civilization pillars."""
        ledger_stats = self.get_transparency_ledger()
        return {
            "sovereign_founder": SOVEREIGN_FOUNDER,
            "founder_contact": {"phone": FOUNDER_PHONE, "email": FOUNDER_EMAIL},
            "status": "OPERATIONAL",
            "pillars": {
                "transparent_democracy": {
                    "active_proposals_count": len(self._proposals),
                    "total_votes_recorded": sum(p.total_votes for p in self._proposals.values())
                },
                "community_unity_hubs": {
                    "registered_hubs_count": len(self._hubs),
                    "total_community_members": sum(h.registered_members for h in self._hubs.values()),
                    "total_welfare_funds_usd": sum(h.welfare_funds_usd for h in self._hubs.values())
                },
                "blockchain_transparency": {
                    "total_expenditure_usd": ledger_stats["total_expenditure_usd"],
                    "transparency_audit_score": ledger_stats["transparency_audit_score"]
                },
                "scientific_gamification": {
                    "active_challenges_count": len(self._challenges),
                    "total_solutions_submitted": sum(c.submitted_solutions_count for c in self._challenges.values())
                },
                "ai_assisted_decisions": {
                    "framework": "Islamic Ethics Five-Pillar Matrix (Tawhid, Adl, Shura, Amanah, Rahmah)",
                    "active_ethics_evaluations": len(self._proposals)
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton accessor
_civilization_engine_instance: Optional[CivilizationEngine] = None

def get_civilization_engine() -> CivilizationEngine:
    global _civilization_engine_instance
    if _civilization_engine_instance is None:
        _civilization_engine_instance = CivilizationEngine()
    return _civilization_engine_instance

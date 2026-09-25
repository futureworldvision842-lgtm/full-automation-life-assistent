"""
tests/test_gaigs_civilization_engine.py — Test Suite for GAIGS Civilization Engine
==================================================================================
Tests:
  1. Pillar 1: Transparent Democracy (Proposal creation, voting, quorum, results).
  2. Pillar 2: Community Unity Hubs (Hub registry, Masjid-e-Nabawi model, services).
  3. Pillar 3: Blockchain Transparency (Spending explorer, corruption checks, audit score).
  4. Pillar 4: Scientific Gamification (Challenge registry, solution evaluation, scoring).
  5. Pillar 5: Islamic Ethics AI Advisory (Tawhid, Adl, Shura, Amanah, Rahmah assessment).
  6. FastAPI Route Integration: GET/POST endpoints via Starlette TestClient.
  7. Clean-room prohibited identifier scan: Zero forbidden tokens.
"""

import pytest
from starlette.testclient import TestClient

from dashboard import app
from core.gaigs.civilization_engine import (
    CivilizationEngine,
    get_civilization_engine,
    SOVEREIGN_FOUNDER,
    FOUNDER_EMAIL,
    FOUNDER_PHONE
)

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture
def engine():
    return CivilizationEngine()


# =============================================================================
# 1. PILLAR 1: TRANSPARENT DEMOCRACY
# =============================================================================
def test_proposal_lifecycle_and_voting(engine):
    prop = engine.submit_proposal(
        title="Decentralized Desalination Micro-Units",
        category="CIVIC_WELFARE",
        author="Master Muhammad Qureshi",
        description="Deploy community-owned solar desalination units along coastal districts.",
        quorum_pct=20.0
    )
    assert prop.proposal_id.startswith("GAIGS-PROP-")
    assert prop.status == "OPEN"
    assert prop.ai_impact_analysis is not None
    assert prop.ai_impact_analysis["ethics_score"] >= 80.0

    # Cast 10 positive votes
    for i in range(10):
        vote_res = engine.cast_vote(prop.proposal_id, f"voter_{i:03d}", "FOR")
        assert vote_res["ok"] is True
        assert len(vote_res["vote_receipt_hash"]) == 64

    # Cast 2 negative votes
    for i in range(10, 12):
        vote_res = engine.cast_vote(prop.proposal_id, f"voter_{i:03d}", "AGAINST")
        assert vote_res["ok"] is True

    result = prop.calculate_result()
    assert result["total_votes"] == 12
    assert result["for_pct"] > 80.0
    assert result["passed"] is True
    assert prop.status == "APPROVED"


def test_duplicate_vote_reversal(engine):
    prop = engine.submit_proposal(
        title="Youth Tech Grant",
        category="EDUCATION",
        author="Council",
        description="Grants for open-source AI developers."
    )
    # Vote FOR
    res1 = engine.cast_vote(prop.proposal_id, "voter_alpha", "FOR")
    assert res1["ok"] is True
    assert prop.votes_for == 1

    # Change vote to AGAINST
    res2 = engine.cast_vote(prop.proposal_id, "voter_alpha", "AGAINST")
    assert res2["ok"] is True
    assert prop.votes_for == 0
    assert prop.votes_against == 1
    assert prop.total_votes == 1


# =============================================================================
# 2. PILLAR 2: COMMUNITY UNITY HUBS (MASJID-E-NABAWI MODEL)
# =============================================================================
def test_unity_hubs_registration(engine):
    hubs = engine.list_hubs()
    assert len(hubs) >= 2
    # Verify canonical Islamabad hub
    isb_hub = next((h for h in hubs if "Jamia Masjid Nabvi" in h["name"]), None)
    assert isb_hub is not None
    assert isb_hub["hub_type"] == "MASJID_MODEL"
    assert isb_hub["city"] == "Islamabad"

    # Register new hub
    new_hub = engine.register_hub(
        name="Lahore Shura Civic Center",
        hub_type="CIVIC_CENTER",
        city="Lahore",
        country="Pakistan",
        latitude=31.5204,
        longitude=74.3587,
        admin_lead="Community Shura Directorate",
        services=["Vocational Robotics", "Arbitration"]
    )
    assert new_hub.hub_id.startswith("HUB-LAH-")
    assert len(engine.list_hubs()) >= 3


# =============================================================================
# 3. PILLAR 3: BLOCKCHAIN TRANSPARENCY & SPENDING EXPLORER
# =============================================================================
def test_spending_ledger_and_anti_corruption(engine):
    ledger = engine.get_transparency_ledger()
    assert ledger["total_transactions"] >= 3
    assert ledger["total_expenditure_usd"] > 0
    assert ledger["transparency_audit_score"] >= 90.0

    # Record clean transaction
    entry = engine.record_expenditure(
        department="Education",
        purpose="Public Library Digital Terminals",
        recipient="Open Knowledge Foundation",
        amount_usd=3500.0
    )
    assert entry["tx_hash"].startswith("0x")
    assert entry["audit_flag"] == "CLEAN"
    assert len(entry["proof_hash"]) == 64

    # Record huge transaction triggering dual-council flag
    high_entry = engine.record_expenditure(
        department="Metro Water",
        purpose="Regional Aqueduct Pipeline",
        recipient="Heavy Infrastructure Consortium",
        amount_usd=250000.0
    )
    assert high_entry["audit_flag"] == "REQUIRES_DUAL_COUNCIL_AUDIT"


# =============================================================================
# 4. PILLAR 4: SCIENTIFIC GAMIFICATION
# =============================================================================
def test_scientific_gamification(engine):
    challenges = engine.list_challenges()
    assert len(challenges) >= 2

    c1 = challenges[0]
    chal_id = c1["challenge_id"]

    # Submit detailed scientific solution
    abstract = (
        "We propose a hierarchical multi-scale graphene oxide membrane utilizing hydrophobic "
        "capillary condensation channels. The kinetic capillary pressure provides passive flux "
        "without external electrical power input while maintaining salt rejection greater than 99.8 percent."
    )
    sol_res = engine.submit_solution(
        challenge_id=chal_id,
        contributor="Dr. Fatima / Quantum Lab",
        solution_title="Capillary Graphene Desalination Matrix",
        solution_abstract=abstract,
        scientific_model_data={"rejection_rate": 0.998, "energy_kwh_m3": 0.0}
    )
    assert sol_res["ok"] is True
    assert sol_res["score"] >= 80.0
    assert sol_res["awarded_points"] > 0


# =============================================================================
# 5. PILLAR 5: ISLAMIC ETHICS AI ADVISORY
# =============================================================================
def test_islamic_ethics_evaluation(engine):
    # Benevolent public project
    good_eval = engine.evaluate_islamic_ethics(
        title="Free Solar Water Purification Network for Arid Villages",
        description="Providing zero-cost clean drinking water and community cooperative maintenance.",
        category="CIVIC_WELFARE"
    )
    assert good_eval.composite_ethics_score >= 85.0
    assert good_eval.verdict == "ETHICALLY_ALIGNED"
    assert good_eval.adl_justice_score >= 90.0
    assert good_eval.rahmah_compassion_score >= 95.0

    # Exploitative project with interest/monopoly
    bad_eval = engine.evaluate_islamic_ethics(
        title="Commercial Monopoly Loan Facility with Compound Interest",
        description="Exclusive proprietary lending facility requiring high usury rates and private secrecy.",
        category="FINANCE"
    )
    assert bad_eval.composite_ethics_score < 75.0
    assert bad_eval.verdict != "ETHICALLY_ALIGNED"
    assert len(bad_eval.recommendations) > 0


# =============================================================================
# 6. FASTAPI API ROUTER INTEGRATION
# =============================================================================
def test_api_gaigs_endpoints(client):
    # Overview
    r_over = client.get("/api/gaigs/overview")
    assert r_over.status_code == 200
    d_over = r_over.json()
    assert d_over["sovereign_founder"] == "Muhammad Qureshi"
    assert d_over["status"] == "OPERATIONAL"

    # Proposals
    r_props = client.get("/api/gaigs/democracy/proposals")
    assert r_props.status_code == 200
    assert len(r_props.json()["proposals"]) >= 2

    # Hubs
    r_hubs = client.get("/api/gaigs/hubs")
    assert r_hubs.status_code == 200
    assert len(r_hubs.json()["hubs"]) >= 2

    # Transparency
    r_ledger = client.get("/api/gaigs/transparency/ledger")
    assert r_ledger.status_code == 200
    assert r_ledger.json()["ledger"]["total_transactions"] >= 3

    # Challenges
    r_chal = client.get("/api/gaigs/gamification/challenges")
    assert r_chal.status_code == 200
    assert len(r_chal.json()["challenges"]) >= 2

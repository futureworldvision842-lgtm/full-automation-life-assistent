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
    return get_civilization_engine()


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


# =============================================================================
# 7. PILLAR 1: QUADRATIC VOTING & LIFECYCLE TESTS
# =============================================================================
def test_quadratic_voting_formula_and_endpoint(client, engine):
    prop = engine.submit_proposal(
        title="Decentralized Desalination Micro-Units",
        category="CIVIC_WELFARE",
        author="Master Muhammad Qureshi",
        description="Deploy community-owned solar desalination units along coastal districts.",
        quorum_pct=20.0
    )

    # 1. Formula check: 100 credits -> weight = 10.0
    r1 = engine.cast_quadratic_vote(prop.proposal_id, "qv_voter_100", 100, "FOR")
    assert r1["ok"] is True
    assert r1["weight"] == 10.0
    assert r1["credits_spent"] == 100

    # 2. Formula check: 25 credits -> weight = 5.0
    r2 = engine.cast_quadratic_vote(prop.proposal_id, "qv_voter_25", 25, "FOR")
    assert r2["ok"] is True
    assert r2["weight"] == 5.0

    # 3. Formula check: 1 credit -> weight = 1.0
    r3 = engine.cast_quadratic_vote(prop.proposal_id, "qv_voter_1", 1, "AGAINST")
    assert r3["ok"] is True
    assert r3["weight"] == 1.0

    tally = prop.calculate_result()
    assert tally["quadratic_votes_for"] == 15.0
    assert tally["quadratic_votes_against"] == 1.0
    assert tally["quadratic_credits_spent"] == 126

    # 4. API Endpoint check: POST /api/gaigs/democracy/quadratic-vote
    api_resp = client.post("/api/gaigs/democracy/quadratic-vote", json={
        "proposal_id": prop.proposal_id,
        "voter_id": "api_voter_64",
        "credits_spent": 64,
        "choice": "aye"
    })
    assert api_resp.status_code == 200
    d = api_resp.json()
    assert d["ok"] is True
    assert d["weight"] == 8.0
    assert d["choice"] == "FOR"


def test_vote_choice_normalization(client, engine):
    prop = engine.submit_proposal(
        title="Civic Youth Tech Program",
        category="EDUCATION",
        author="Civic Council",
        description="Funding for young software and AI innovators."
    )

    # Affirmative variants: aye, for, yes
    for choice in ["aye", "for", "yes", "YES", "Aye"]:
        res = engine.cast_vote(prop.proposal_id, f"voter_{choice}", choice)
        assert res["ok"] is True
        assert res["choice"] == "FOR"

    # Negative variants: nay, against, no
    for choice in ["nay", "against", "no", "NO", "Nay"]:
        res = engine.cast_vote(prop.proposal_id, f"voter_{choice}", choice)
        assert res["ok"] is True
        assert res["choice"] == "AGAINST"

    # API endpoints normalization
    r_dem = client.post("/api/gaigs/democracy/vote", json={
        "proposal_id": prop.proposal_id,
        "voter_id": "api_norm_voter_1",
        "choice": "aye"
    })
    assert r_dem.status_code == 200
    assert r_dem.json()["choice"] == "FOR"

    r_alias = client.post("/api/gaigs/vote", json={
        "proposal_id": prop.proposal_id,
        "voter_id": "api_norm_voter_2",
        "choice": "nay"
    })
    assert r_alias.status_code == 200
    assert r_alias.json()["choice"] == "AGAINST"


def test_proposal_lifecycle_states(client, engine):
    # 1. Create proposal in DRAFT
    prop = engine.submit_proposal(
        title="Draft Smart Irrigation Bill",
        category="INFRASTRUCTURE",
        author="Irrigation Board",
        description="Draft stage automated water management proposal.",
        status="DRAFT"
    )
    assert prop.status == "DRAFT"

    # 2. Voting on DRAFT must fail
    res_vote = engine.cast_vote(prop.proposal_id, "voter_01", "FOR")
    assert res_vote["ok"] is False
    assert "DRAFT" in res_vote["error"]

    # 3. Transition to ACTIVE
    res_trans = engine.transition_proposal_status(prop.proposal_id, "ACTIVE")
    assert res_trans["ok"] is True
    assert prop.status == "ACTIVE"

    # 4. Voting now succeeds
    res_vote2 = engine.cast_vote(prop.proposal_id, "voter_01", "FOR")
    assert res_vote2["ok"] is True

    # 5. Transition to EXECUTED via API
    r_api_trans = client.patch(f"/api/gaigs/democracy/proposals/{prop.proposal_id}/status", json={
        "status": "EXECUTED"
    })
    assert r_api_trans.status_code == 200
    assert r_api_trans.json()["status"] == "EXECUTED"

    # 6. Voting on EXECUTED must fail
    res_vote3 = engine.cast_vote(prop.proposal_id, "voter_02", "FOR")
    assert res_vote3["ok"] is False
    assert "closed" in res_vote3["error"]


# =============================================================================
# 8. PILLAR 3: CITIZEN AUDIT & MERKLE VERIFICATION & SPENDING FIX
# =============================================================================
def test_citizen_audit_and_merkle_verification(client):
    # Fetch spending to get a live tx_hash
    r_spend = client.get("/api/gaigs/transparency/spending")
    assert r_spend.status_code == 200
    records = r_spend.json()["records"]
    assert len(records) > 0
    target_tx = records[0]["tx_hash"]

    # 1. Log citizen audit dispute
    r_audit = client.post("/api/gaigs/transparency/audit", json={
        "tx_hash": target_tx,
        "citizen_id": "auditor_citizen_007",
        "dispute_reason": "Inconsistent component pricing for solar inverter batch."
    })
    assert r_audit.status_code == 200
    audit_data = r_audit.json()
    assert audit_data["ok"] is True
    assert audit_data["status"] == "DISPUTED"
    assert audit_data["tx_hash"] == target_tx

    # 2. Verify transaction via Merkle Proof
    r_verify = client.get(f"/api/gaigs/transparency/verify/{target_tx}")
    assert r_verify.status_code == 200
    v_data = r_verify.json()
    assert v_data["ok"] is True
    assert v_data["verified"] is True
    assert len(v_data["merkle_root"]) == 64
    assert len(v_data["merkle_proof"]) >= 1
    assert v_data["verification_status"] == "CRYPTOGRAPHICALLY_VERIFIED"


def test_transparency_spending_records_array_format(client):
    r = client.get("/api/gaigs/transparency/spending")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    records = data["records"]

    # Must be an ARRAY (list) so that frontend records.map() succeeds without TypeError
    assert isinstance(records, list)
    assert len(records) >= 3

    # Test frontend map compatibility: records.map(r => r.id)
    mapped_ids = [r["id"] for r in records]
    assert len(mapped_ids) == len(records)

    # Check dual keys on every entry
    for entry in records:
        assert "id" in entry and "tx_hash" in entry
        assert entry["id"] == entry["tx_hash"]

        assert "category" in entry and "department" in entry
        assert entry["category"] == entry["department"]

        assert "vendor" in entry and "recipient" in entry
        assert entry["vendor"] == entry["recipient"]

        assert "flagged" in entry and "audit_flag" in entry
        assert isinstance(entry["flagged"], bool)
        assert isinstance(entry["audit_flag"], str)

        assert "sha256_hash" in entry and "proof_hash" in entry
        assert entry["sha256_hash"] == entry["proof_hash"]


# =============================================================================
# 9. PILLAR 5: CITIZEN SCORE & MILESTONE REWARDS
# =============================================================================
def test_citizen_score_and_milestones_endpoint(client):
    # 1. Founder Citizen Profile
    r_founder = client.get("/api/gaigs/gamification/citizen-score/Master%20Muhammad%20Qureshi")
    assert r_founder.status_code == 200
    fd = r_founder.json()
    assert fd["ok"] is True
    assert fd["score"] >= 2500
    assert fd["rank"] == "Sovereign Statesman"
    assert len(fd["badges"]) >= 4
    assert len(fd["milestones"]) >= 4

    # 2. Dynamic citizen profile
    r_user = client.get("/api/gaigs/gamification/citizen-score/citizen_khalid_99")
    assert r_user.status_code == 200
    ud = r_user.json()
    assert ud["ok"] is True
    assert ud["citizen_id"] == "citizen_khalid_99"
    assert ud["score"] >= 100
    assert "badges" in ud
    assert "milestones" in ud


# =============================================================================
# 10. MULTI-CHANNEL MEDIA ENGINE & "THE LIVING TIMELINE"
# =============================================================================
def test_media_channels_array_and_living_timeline(client):
    from core.gaigs.social_media_automation import MASTER_CHANNELS

    # 1. Verify MASTER_CHANNELS has The Living Timeline on Instagram & TikTok
    assert "instagram_living_timeline" in MASTER_CHANNELS
    assert MASTER_CHANNELS["instagram_living_timeline"]["handle"] == "@the_living_timeline"

    assert "tiktok_living_timeline" in MASTER_CHANNELS
    assert MASTER_CHANNELS["tiktok_living_timeline"]["handle"] == "@thelivingtimeline1"

    # 2. Verify GET /api/media/channels returns ARRAY of channel objects
    r = client.get("/api/media/channels")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    channels = data["channels"]
    assert isinstance(channels, list)

    # Test frontend map compatibility: channels.map(c => c.name)
    names = [c["name"] for c in channels]
    assert len(names) == len(channels)

    # Check channels have id, name, handle, target_audience
    living_tl = [c for c in channels if "@the_living_timeline" in c.get("handle", "") or "Living Timeline" in c.get("name", "")]
    assert len(living_tl) >= 1
    for c in channels:
        assert "id" in c
        assert "name" in c
        assert "handle" in c
        assert "target_audience" in c


def test_media_script_approval_yeh_dabao(client):
    r_scripts = client.get("/api/media/scripts")
    assert r_scripts.status_code == 200
    scripts = r_scripts.json()["scripts"]
    assert len(scripts) > 0
    sid = scripts[0]["script_id"]

    r_app = client.post("/api/media/approve_script", json={"script_id": sid})
    assert r_app.status_code == 200
    app_data = r_app.json()
    assert app_data["ok"] is True
    assert app_data["status"] == "APPROVED_YEH_DABAO"
    assert app_data["script"]["status"] == "APPROVED_YEH_DABAO"


def test_media_crosspost_endpoint(client):
    r_post = client.post("/api/media/crosspost", json={
        "script_id": "SCRIPT-ENG-002",
        "platforms": ["YouTube", "Instagram", "TikTok", "X (Twitter)"]
    })
    assert r_post.status_code == 200
    xp = r_post.json()
    assert xp["ok"] is True
    assert xp["status"] == "STAGED"
    assert len(xp["webhook_receipts"]) == 4
    for rcpt in xp["webhook_receipts"]:
        assert rcpt["status"] == "STAGED_DISPATCH"
        assert len(rcpt["payload_digest"]) == 64


# =============================================================================
# 11. MISSION DOCUMENT SYNCHRONIZATION
# =============================================================================
def test_mission_docs_synchronization(client):
    r = client.get("/api/gaigs/mission-docs")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] >= 17
    documents = data["documents"]
    assert len(documents) >= 17

    doc_titles = [d["title"] for d in documents]
    assert any("Civilization Upgrade" in t for t in doc_titles)
    assert any("Humanity 3.0" in t for t in doc_titles)
    assert any("Civic Operating System" in t for t in doc_titles)

    assert any(d["file_size_bytes"] > 1000000 for d in documents)

    for doc in documents:
        assert "title" in doc
        assert "file_size_bytes" in doc
        assert doc["file_size_bytes"] >= 0
        assert "file_size_formatted" in doc
        assert "primary_pillar" in doc
        assert "five_pillar_alignments" in doc
        assert len(doc["five_pillar_alignments"]) >= 1


# =============================================================================
# 12. CLEAN-ROOM PROHIBITED IDENTIFIER SCAN
# =============================================================================
def test_clean_room_prohibited_identity_scan():
    import os
    banned = "".join(["adeel", "qureshi", "99"])
    files_to_check = [
        "core/gaigs/civilization_engine.py",
        "core/gaigs/social_media_automation.py",
        "core/gaigs/gaigs_api_router.py",
        "tests/test_gaigs_civilization_engine.py"
    ]
    for rel_path in files_to_check:
        full_path = os.path.join("F:\\Jarvis Command Center", rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert banned not in content.lower(), f"Prohibited identifier found in {rel_path}"


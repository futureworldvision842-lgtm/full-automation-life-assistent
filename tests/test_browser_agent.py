"""
tests/test_browser_agent.py
============================
Verification for Autonomous Browser Agent & CDP Web Problem Solver.
"""

import pytest
from actions.autonomous_browser_agent import AutonomousBrowserAgent, get_browser_agent

class TestAutonomousBrowserAgent:
    def test_search_solution_symlink_heuristic(self):
        agent = get_browser_agent()
        res = agent.search_solution("PermissionError: [WinError 5] Access is denied: pytest-current symlink")
        assert res.success is True
        assert "symlink" in res.diagnosis.lower()
        assert len(res.code_snippets) >= 1
        assert "sandbox" in res.recommended_solution.lower() or "fixture" in res.recommended_solution.lower()

    def test_search_solution_scipy_spearman(self):
        agent = get_browser_agent()
        res = agent.search_solution("Spearman rank correlation method requires SciPy package")
        assert res.success is True
        assert "scipy" in res.diagnosis.lower()
        assert "rank().corr" in res.recommended_solution

    def test_search_solution_ffmpeg_mp4(self):
        agent = get_browser_agent()
        res = agent.search_solution("ffmpeg binary missing during mp4 rendering")
        assert res.success is True
        assert "ffmpeg" in res.diagnosis.lower()
        assert "opencv" in res.recommended_solution.lower() or "videowriter" in res.recommended_solution.lower()

    def test_search_solution_meme_honeypot(self):
        agent = get_browser_agent()
        res = agent.search_solution("Audit meme coin honeypot and rug risk")
        assert res.success is True
        assert "meme" in res.diagnosis.lower()
        assert "honeypot" in res.recommended_solution.lower()
        assert "lp_locked" in res.code_snippets[0]


    def test_research_github_repo_opendroid(self):
        agent = get_browser_agent()
        res = agent.research_github_repo("https://github.com/yashab-cyber/opendroid.git")
        assert res["success"] is True
        assert res["repo"] == "opendroid"
        assert "Android accessibility" in res["architecture_role"]
        assert res["verified_for_master"] == "Master Muhammad Qureshi"

    def test_research_github_repo_higgsfield(self):
        agent = get_browser_agent()
        res = agent.research_github_repo("https://github.com/higgsfield/higgsfield.git")
        assert res["success"] is True
        assert res["repo"] == "higgsfield"
        assert "visual AI" in res["architecture_role"]

    def test_zero_prohibited_identifer(self):
        agent = get_browser_agent()
        res = agent.search_solution("Test query for security audit")
        d = res.to_dict()
        dump = str(d).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump

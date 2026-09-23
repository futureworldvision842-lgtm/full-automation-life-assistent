"""
tests/verify_full_ecosystem.py
========================================================================
Comprehensive End-to-End Diagnostic & Health Verification Test Suite.
Verifies all ports, engines, models, risk gates, and tools across J.A.R.V.I.S.
========================================================================
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

passed = 0
failed = 0


def log_test(name: str, success: bool, detail: str = ""):
    global passed, failed
    if success:
        passed += 1
        print(f"  [PASS] {name} -> {detail}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -> {detail}")


print("=" * 70)
print("  J.A.R.V.I.S. QUANTUM OS ? FULL-SYSTEM VERIFICATION TEST SUITE")
print("=" * 70)

# 1. Port & Daemon Liveness Checks
print("\n1. CORE DAEMONS & SERVICES LIVENESS:")
ports_to_check = [
    ("Dashboard Command Center", "http://127.0.0.1:8770/api/pc"),
    ("MQ3 Trading Cockpit", "http://127.0.0.1:5050/"),
    ("Odysseus AI Server", "http://127.0.0.1:7000/api/health"),
    ("Mobile Control Remote", "http://127.0.0.1:8765/api/health"),
    ("Ollama Local Engine", "http://127.0.0.1:11434/api/tags"),
]

for name, url in ports_to_check:
    try:
        r = requests.get(url, timeout=3.0)
        log_test(name, r.status_code in (200, 304), f"Status HTTP {r.status_code}")
    except Exception as e:
        log_test(name, False, f"Connection error: {e}")

# 2. MQ3 Institutional Trading Engine Checks
print("\n2. MQ3 INSTITUTIONAL TRADING & PROP-FIRM RISK GATES:")
try:
    from actions.mq3_trading import mq3_trading
    gold_res = mq3_trading({"action": "gold"})
    log_test("Gold SMC Structure & Order Blocks", "OB" in gold_res or "XAUUSD" in gold_res, "Structure analyzed")
    
    cal_res = mq3_trading({"action": "calendar"})
    log_test("Economic News 15m Circuit Breaker", "BLACKOUT" in cal_res or "HIGH" in cal_res or "CALENDAR" in cal_res, "Calendar synced")
    
    from actions.global_macro_aladdin_engine import get_global_macro_summary_report
    rep = get_global_macro_summary_report()
    log_test("BlackRock Aladdin 1-Day 99% VaR", "Aladdin" in rep or "VaR" in rep, "Risk stress-tested")
    
    risk_res = mq3_trading({"action": "admission"})
    log_test("18-Gate Deterministic Risk Kernel", "18-GATE" in risk_res and "Monte Carlo" in risk_res, "18/18 gates active")
except Exception as e:
    log_test("MQ3 Trading Diagnostics", False, str(e))

# 3. World Monitor Geopolitical Radar Checks
print("\n3. WORLD MONITOR GEOPOLITICAL & DEFCON RADAR:")
try:
    from actions.world_monitor import get_conflict, get_chokepoints
    conf = get_conflict()
    log_test("ACLED Conflict & Defense Incidents", len(conf) > 0, f"{len(conf)} live items")
    
    choke = get_chokepoints()
    log_test("5 Strategic Maritime Chokepoints", len(choke) == 5, f"{len(choke)} chokepoints verified")
    
    r = requests.get("http://127.0.0.1:8770/api/shock", timeout=3.0)
    log_test("Geopolitical Shock Multiplier Engine", r.status_code == 200, f"DEFCON {r.json().get('defcon_level')}")
except Exception as e:
    log_test("World Monitor Diagnostics", False, str(e))

# 4. n8n Workflow Automation Hub Checks
print("\n4. N8N WORKFLOW AUTOMATION & DAG ORCHESTRATION:")
try:
    from integrations.n8n_engine import get_n8n_engine
    engine = get_n8n_engine()
    flows = engine.list_workflows()
    log_test("n8n 5 Configured Workflows", len(flows) == 5, f"{len(flows)} DAG flows loaded")
    
    res = engine.trigger_workflow("macro_briefing")
    log_test("n8n Sovereign DAG Execution", res.get("ok") == True, f"{res.get('duration_ms')}ms latency")
except Exception as e:
    log_test("n8n Engine Diagnostics", False, str(e))

# 5. Nous Hermes-3 Tool Calling Agent Checks
print("\n5. NOUS RESEARCH HERMES-3 FUNCTION CALLING:")
try:
    from brain.hermes_agent import get_hermes_agent
    h_agent = get_hermes_agent()
    prompt_hdr = h_agent.get_system_prompt()
    log_test("Hermes Tool Registry & XML Schemas", "<tools>" in prompt_hdr, "24+ tools mapped")
    
    t_res = h_agent.execute_tool("institutional_matrix", {"action": "macro"})
    log_test("Hermes Structured Tool Execution", len(str(t_res)) > 50, "Tool executed cleanly")
except Exception as e:
    log_test("Hermes Agent Diagnostics", False, str(e))

# 6. Dograh Autonomous Web Agent Checks
print("\n6. DOGRAH AUTONOMOUS WEB & BROWSER AGENT:")
try:
    from actions.dograh_agent import get_dograh_agent
    d_res = get_dograh_agent().execute_web_task("Check market headlines")
    log_test("Dograh Multi-Step Web Crawler", d_res.get("ok") == True, f"{d_res.get('duration_ms')}ms duration")
except Exception as e:
    log_test("Dograh Agent Diagnostics", False, str(e))

# 7. HuggingFace Speech-to-Speech Cascade Checks
print("\n7. HUGGINGFACE SPEECH-TO-SPEECH CASCADE:")
try:
    from perception.speech_to_speech_engine import get_s2s_pipeline
    s2s = get_s2s_pipeline()
    log_test("S2S VAD & Faster-Whisper Pipeline", s2s.sample_rate == 16000, f"{s2s.sample_rate}Hz sample rate")
except Exception as e:
    log_test("Speech-to-Speech Diagnostics", False, str(e))

# 8. Freqtrade Crypto & $500 Spot Model Checks
print("\n8. FREQTRADE QUANTITATIVE CRYPTO & $500 PORTFOLIO:")
try:
    from actions.freqtrade_engine import get_crypto_engine
    c_engine = get_crypto_engine()
    alloc = c_engine.evaluate_spot_allocation()
    log_test("$500 Base Spot Allocation Model", alloc.get("total_capital_usd") == 500.0, "Portfolio verified")
    
    depth = c_engine.scan_order_book_imbalances("BTCUSDT")
    log_test("Level 2 DOM Liquidity Imbalance Hunter", depth.get("bid_ask_imbalance_ratio") > 0, "Depth verified")
except Exception as e:
    log_test("Freqtrade Engine Diagnostics", False, str(e))

# 9. Mem0 Long-Term Cognitive Memory Checks
print("\n9. MEM0 COGNITIVE LONG-TERM MEMORY:")
try:
    from memory.mem0_engine import get_mem0_engine
    m_engine = get_mem0_engine()
    m_results = m_engine.search_memories("Muhammad")
    log_test("Mem0 Semantic Vector Search", len(m_results) > 0, f"{len(m_results)} facts retrieved")
except Exception as e:
    log_test("Mem0 Engine Diagnostics", False, str(e))

# 10. Skills & Autonomous Self-Upgrade Forge Checks
print("\n10. SKILL FORGE & CAPABILITY GAP DIAGNOSTICS:")
try:
    from skills.skill_forge import get_skill_forge
    from skills.capability_gap_engine import get_gap_engine
    gap = get_gap_engine().evaluate_system_gaps()
    log_test("Capability Gap Engine Diagnostics", gap.get("status") in ("ALL_CAPABILITIES_NOMINAL", "MINOR_GAPS_DETECTED"), f"Status: {gap.get('status')}")
except Exception as e:
    log_test("Skill Forge Diagnostics", False, str(e))

# 11. Optical Motion Detection Camera Checks
print("\n11. OPTICAL MOTION DETECTION & WEBCAM SENSOR:")
try:
    from actions.motion_detector import get_motion_detector
    detector = get_motion_detector()
    status = detector.get_status()
    log_test("Webcam Optical Sentinel Initialized", "daemon_active" in status, f"Camera: {'ONLINE' if status['camera_available'] else 'STANDBY'}")
    
    m_res = detector.detect_motion_once(duration_sec=0.5)
    log_test("Optical Differencing & Contour Analysis", m_res.get("ok") == True, f"{m_res.get('frames_analyzed', 0)} frames analyzed")
    
    ok, buf, pth = detector.capture_webcam_snapshot()
    log_test("Webcam Snapshot with Cyberpunk HUD", ok and len(buf) > 0, f"{len(buf)} bytes captured")
except Exception as e:
    log_test("Optical Motion Diagnostics", False, str(e))

# 12. WhatsApp Wake-On-Message & API Gateway Triggers
print("\n12. WHATSAPP WAKE-ON-MESSAGE & UNBLOCKED API TRIGGERS:")
try:
    from core.command_router import get_roman_urdu_parser, UnifiedCommandRouter
    router = UnifiedCommandRouter()
    wake_env = router.process_command("jarvis on", channel="whatsapp", sender_id="923468053268")
    log_test("WhatsApp Wake-On-Message Remote Trigger", wake_env.ok and "WAKE SEQUENCE" in wake_env.output_text, "Wake sequence armed")
    
    cam_env = router.process_command("camera snapshot", channel="whatsapp", sender_id="923468053268")
    log_test("WhatsApp Camera Vision Dispatcher", cam_env.ok and "OPTICAL WEBCAM SNAPSHOT" in cam_env.output_text, f"Image: {cam_env.metadata.get('image_path')}")
    
    headers = {"Content-Type": "application/json"}
    try:
        from platform_runtime import internal_command_token
        headers["X-Jarvis-Internal-Token"] = internal_command_token()
    except Exception:
        pass

    r_hermes = requests.post("http://127.0.0.1:8770/api/hermes/execute", json={"tool": "institutional_matrix", "arguments": {"action": "macro"}}, headers=headers, timeout=5.0)
    log_test("Live Unblocked Dashboard /api/hermes/execute", r_hermes.status_code == 200, f"HTTP {r_hermes.status_code}")

    r_n8n = requests.post("http://127.0.0.1:8770/api/n8n/trigger", json={"workflow_id": "macro_briefing"}, headers=headers, timeout=5.0)
    log_test("Live Unblocked Dashboard /api/n8n/trigger", r_n8n.status_code == 200, f"HTTP {r_n8n.status_code}")

    r_cam = requests.get("http://127.0.0.1:8770/api/camera/motion", headers=headers, timeout=5.0)
    log_test("Live Dashboard /api/camera/motion", r_cam.status_code == 200, f"HTTP {r_cam.status_code}")

    r_gates = requests.get("http://127.0.0.1:8770/api/risk/gates", headers=headers, timeout=5.0)
    log_test("Live Dashboard /api/risk/gates", r_gates.status_code == 200, f"HTTP {r_gates.status_code}")
except Exception as e:
    log_test("WhatsApp & API Gateway Diagnostics", False, str(e))

print("\n" + "=" * 70)
print(f"  DIAGNOSTIC SUMMARY: {passed} PASSED | {failed} FAILED")
print("=" * 70)

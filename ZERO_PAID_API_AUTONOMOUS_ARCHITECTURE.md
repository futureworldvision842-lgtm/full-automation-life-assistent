# 🎙️ J.A.R.V.I.S. ZERO-PAID-API SOVEREIGN ARCHITECTURE
========================================================================================
**System Directive:** 100% Free, Autonomous & Sovereign Operation without Paid API Keys  
**Primary Hub:** `F:\Jarvis Command Center` (SSD Drive `F:\`)  
**Core Pillars:** Local Voice Ingress, Free Neural Speech, Autonomous Browser LLM Agent, Local LLM Node, 3,315 Dense Vector Memory Hub  
========================================================================================

---

## 1. EXECUTIVE ZERO-API ARCHITECTURAL OVERVIEW

J.A.R.V.I.S. does **not require paid API keys** to listen, understand, speak, think, write code, or execute commands. The ecosystem operates through a resilient **4-Pillar Zero-Paid-API Hierarchy**:

```
+---------------------------------------------------------------------------------------+
|                       J.A.R.V.I.S. SOVEREIGN ZERO-API ARCHITECTURE                     |
+---------------------------------------------------------------------------------------+
            |                                  |                                  |
            v                                  v                                  v
+-----------------------+          +-----------------------+          +-----------------------+
|  1. FREE VOICE INGRESS|          | 2. LOCAL INTEL & MEM  |          | 3. AUTONOMOUS BROWSER |
|  - Faster-Whisper     |          | - Ollama (11434)      |          | - Playwright Chromium |
|  - SpeechRecognition  |          | - Odysseus AI (7000)  |          | - ChatGPT / DeepSeek  |
|  - Web Speech API     |          | - 3,315 Vectors (DB)  |          | - Claude / HuggingFace|
+-----------------------+          +-----------------------+          +-----------------------+
            |                                  |                                  |
            +----------------------------------+----------------------------------+
                                               |
                                               v
+---------------------------------------------------------------------------------------+
|                   4. FREE HIGH-FIDELITY NEURAL SPEECH SYNTHESIS (TTS)                 |
|                   - Edge-TTS (Ryan / Asad Neural Voices - 100% Free)                  |
|                   - Windows Native SAPI5 COM (100% Offline Fallback)                  |
+---------------------------------------------------------------------------------------+
```

---

## 2. PILLAR 1: ZERO-API VOICE INGRESS (HEARING & UNDERSTANDING)

J.A.R.V.I.S. captures spoken speech through three 100% free and open-source methods:

### A. Local Faster-Whisper / SpeechRecognition Engine
- **Module:** `actions/zero_api_voice.py`
- **Mechanism:** Captures microphone PCM audio stream, performs ambient noise calibration, and transcribes English & Roman Urdu speech locally or via free endpoints.
- **Latency:** <250ms audio chunk inference.

### B. Full-Duplex Web Speech Recognition
- **Integration:** Master Command Center HUD (`http://127.0.0.1:8770`) & Neural Terminal.
- **Action:** 1-Click interactive 🎙️ mic button captures voice directly in browser with zero server CPU overhead.

### C. Bilingual Natural Language Intent Parser (`core/roman_urdu_parser.py`)
- Automatically parses intent into structured parameters:
  - *"Gold kharido"* ➔ `trading_operation: {action: buy, symbol: XAUUSD, lots: 0.01}`
  - *"Lock breakeven"* ➔ `trading_operation: {action: breakeven}`
  - *"CapCut kholo"* ➔ `os_app_control: {app: capcut, action: launch}`
  - *"Screenshot lo"* ➔ `os_screenshot`
  - *"PC vitals dikhao"* ➔ `system_diagnostics`

---

## 3. PILLAR 2: ZERO-API HIGH-FIDELITY NEURAL VOICE (SPEAKING)

J.A.R.V.I.S. speaks back to you with natural, human-grade neural voices without any API bills:

### A. Microsoft Edge-TTS (100% Free High-Definition Neural Audio)
- **Module:** `actions/voice_synthesizer.py`
- **Voices Available:**
  - `en-GB-RyanNeural`: Classic J.A.R.V.I.S. British persona.
  - `ur-PK-AsadNeural`: Bilingual Urdu/English persona.
  - `en-US-GuyNeural`: American male neural voice.
  - `en-US-AriaNeural`: Expressive female neural voice.
- **Cost:** **$0.00** (Uses Microsoft's free edge audio protocol).

### B. Windows Native SAPI5 COM Interface (100% Offline Fallback)
- **Implementation:** `win32com.client.Dispatch("SAPI.SpVoice")`
- **Reliability:** Works completely offline without any internet connection.

---

## 4. PILLAR 3: AUTONOMOUS WEB BROWSER AGENT (ZERO-API REASONING)

When direct API keys are absent or when you want deep reasoning, J.A.R.V.I.S. acts like a human sitting at your computer:

### A. Playwright Chromium Web Navigator (`perception/web_navigator.py`)
- **Supported Web LLMs:**
  1. **ChatGPT Web (`https://chatgpt.com`)**
  2. **DeepSeek Web (`https://chat.deepseek.com`)** (DeepSeek R1 reasoning extraction)
  3. **Claude Web (`https://claude.ai/new`)**
  4. **HuggingFace Chat (`https://huggingface.co/chat`)**
  5. **GitHub & StackOverflow code search**
- **Session Persistence:** Saves login session cookies in `data/browser_profile/storage_state.json` so you only log in once and it stays logged in permanently.
- **Extraction:** Automatically enters your prompt into the web textarea, waits for the streaming completion via DOM quiescence detection, cleans the markdown, and extracts code blocks.

---

## 5. PILLAR 4: LOCAL LLM NODE & 3,315 DENSE VECTOR MEMORY

### A. Local Ollama Node (`http://127.0.0.1:11434`)
- **Storage:** Dedicated model weights stored on SSD `F:\data\ollama\models`.
- **Supported Local Models:** `qwen2.5:1.5b`, `llama3.2:1b`, `deepseek-r1:1.5b`, `mistral:7b`.
- **Function:** Runs 100% locally on your CPU/GPU with zero latency and zero data leakage.

### B. 3,315 Dense Vector Semantic Memory Hub
- **Database:** `F:\Jarvis Command Center\memory\mission_memory.db`
- **Ingested Literature:**
  - **85 World Books (`W:\desktop deta`):** Ray Dalio (*Principles*), Benjamin Graham (*Intelligent Investor*), Morgan Housel (*Psychology of Money*), Daniel Kahneman (*Thinking, Fast and Slow*), James Clear (*Atomic Habits*).
  - **Founder Personal Works & Missions (`P:\Vision Point Work` & `F:\Muhammad's platforms`):** *A New Dawn for Humanity*, *The Last System*, *THE LAST HOPE*, *Masjid-e-Nabawi Governance Model*, *GAIGS Interactive Technical Plan v3*.
- **Sub-50ms Recall:** Automatically injects relevant excerpts into the local prompt.

---

## 6. TOP OPEN-SOURCE GITHUB REPOSITORIES FOR FUTURE EXPANSION

| Category | Repository Name | GitHub URL | Integration Role in J.A.R.V.I.S. |
|---|---|---|---|
| **STT Voice** | `SYSTRAN/faster-whisper` | [github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 4x faster local speech-to-text on CPU/GPU. |
| **Neural TTS** | `rany2/edge-tts` | [github.com/rany2/edge-tts](https://github.com/rany2/edge-tts) | Zero-cost high-fidelity neural voice synthesis. |
| **Offline TTS** | `rhasspy/piper` | [github.com/rhasspy/piper](https://github.com/rhasspy/piper) | Ultra-fast local neural TTS running on Raspberry Pi & Windows. |
| **Browser Agent** | `browser-use/browser-use` | [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use) | Autonomous web agent controlling browsers via Playwright. |
| **Computer-Use** | `lavague-ai/LaVague` | [github.com/lavague-ai/LaVague](https://github.com/lavague-ai/LaVague) | Large Action Model (LAM) for automated browser execution. |
| **Local LLM** | `ollama/ollama` | [github.com/ollama/ollama](https://github.com/ollama/ollama) | Local model orchestration node. |
| **Open Higgsfield** | `Autom8AI/Open-Higgsfield-AI` | [github.com/Autom8AI/Open-Higgsfield-AI](https://github.com/Autom8AI/Open-Higgsfield-AI) | Open-source self-hosted alternative to Higgsfield creative pipelines. |

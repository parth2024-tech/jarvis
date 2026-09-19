# Project J.A.R.V.I.S. (Hermes Edition) — Industrial Architecture

## 1. Directory Structure
```
/home/thor/Desktop/JARVIS/
├── ADR.md                 # Architecture Decision Record
├── core/
    └── server.py          # FastAPI Backend (Intent Routing & SQLite Persistence)
├── ui/
    └── hud.html           # Cinematic Stark HUD with Real-time Two-Way Voice
├── tests/
    └── test_core.py       # Comprehensive Unit and Integration Test Suite
└── memory/
    └── jarvis_state.db    # Relational Audit & Interaction Log
```

## 2. Core Subsystems
- **Voice Pipeline:** Web Speech API streaming full-duplex communication with auto-turn detection and voice-animated Stark helmet eyes.
- **Intelligence Engine:** FastAPI backend routing queries with intent classification and telemetry tracking.
- **Persistent Memory:** SQLite relational logging paired with LanceDB vector storage for context recall.
- **Verification & Testing:** Automated test suite (`python3 -m unittest discover tests`) verifying backend readiness and telemetry.

## 3. Quickstart Instructions
1. **Start the Core Intelligence Server:**
   ```bash
   python3 /home/thor/Desktop/JARVIS/core/server.py
   ```
2. **Run the Test Suite:**
   ```bash
   python3 -m unittest discover -s /home/thor/Desktop/JARVIS/tests
   ```
3. **Launch the HUD Interface:**
   Open `/home/thor/Desktop/JARVIS/ui/hud.html` in Google Chrome or Microsoft Edge. Click **ACTIVATE MIC** or type your directive to initiate two-way voice conversation.

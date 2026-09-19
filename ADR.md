# ARCHITECTURE DECISION RECORD: PROJECT J.A.R.V.I.S. (HERMES EDITION)

## 1. Executive Summary
Project J.A.R.V.I.S. is an industrial-grade autonomous personal AI assistant built as an AI operating layer for the host machine. It combines low-latency duplex voice interaction, intelligent model routing, layered memory (LanceDB/SQLite), secure tool execution, web research, and a cinematic HUD.

## 2. Subsystem Selections & Ecosystem Research

### A. Voice & Speech Pipeline
- **Selected Component:** Web Speech API (Browser-native STT/TTS) + Fallback to local Piper/Whisper where required.
- **Rationale:** Zero external cost, instantaneous streaming turn-detection, robust browser integration, avoids heavy C++ dependency compilation friction while guaranteeing real-time responsiveness.

### B. Intelligence & Model Routing
- **Selected Component:** Multi-provider Model Router (Ollama local fallback + Cloud API support).
- **Rationale:** Balances privacy, local resource constraints (VRAM/RAM limits), and high-reasoning coding capability. Fast models handle trivial status queries; heavyweight models handle architecture and complex reasoning.

### C. Memory Architecture
- **Selected Component:** Layered Hybrid Memory (SQLite for relational context/audit + LanceDB for vector semantic memory).
- **Rationale:** Combines ultra-fast relational lookup with hybrid vector+FTS recall, matching the user's existing memory infrastructure.

### D. Tool Execution & Security
- **Selected Component:** Sandboxed Python Tool Executive with Least Privilege + Confirmation Gates.
- **Rationale:** Ensures safety during computer control and file system operations, preventing unintended destructive side effects.

### E. Interface
- **Selected Component:** Cinematic HTML/CSS/JS Stark Industries HUD with Two-Way Voice Loop.
- **Rationale:** Provides zero-latency visual telemetry and natural conversational flow.

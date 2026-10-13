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

---

## 3. Autonomous Agent Architecture: Meta Muse & Open Dots Paradigm

To evolve J.A.R.V.I.S. from an interactive assistant into an always-on autonomous agent layer, we adopt core architectural blueprints synthesized from **Meta Muse** (enterprise ephemeral microVM agent) and **Open Dots** (open-source self-hosted agent workspace).

### Architectural Comparison Matrix

| Capability | Meta Muse Paradigm | Open Dots Paradigm | J.A.R.V.I.S. Convergence Strategy |
| :--- | :--- | :--- | :--- |
| **Execution Sandbox** | Firecracker MicroVM / systemd-nspawn | Docker / Rootless Podman with tmpfs | Rootless Podman container with ephemeral tmpfs overlay and capability drops (`--cap-drop ALL`, `--read-only`). |
| **State Machine** | Event queue + cloud checkpointing | PostgreSQL `SKIP LOCKED` worker queues | SQLite WAL durable task registry + pause/resume checkpoints across core server restarts. |
| **Security Sentinel** | Out-of-band biometric auth daemon | Human-in-the-loop CLI / Web approval gates | 3-Tier Security Guard + Out-of-band confirmation registry with challenge-response gates for mutating actions. |
| **Web Automation** | Sandboxed Chromium with CDP stream | Headless Playwright / Puppeteer | Sandboxed Playwright instance returning stripped accessibility tree/DOM to conserve context tokens. |
| **Multi-Client Ingress** | WhatsApp, Instagram, Messenger | Telegram Bot API + Web Dashboard | Unified FastAPI router serving Stark HUD (WebSocket/SSE) and Telegram webhook gateway. |

---

## 4. Core Subsystem Architectural Decisions

### A. Durable State Machine & Queue Polling
- **Decision:** Decouple agent task lifecycle from the frontend connection.
- **Mechanism:**
  - Tasks persist status transitions (`queued`, `running`, `waiting_approval`, `paused`, `completed`, `failed`).
  - Scheduled and recurring tasks use transactional locking (PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` or SQLite atomic state transitions) to guarantee exactly-once execution across horizontal workers.
  - LLM iterations (message logs, intermediate tool responses, and partial plans) persist to SQLite/LanceDB checkpoints to enable instant pause and resumption across process restarts.

### B. Ephemeral Containerized Sandboxing
- **Decision:** Prohibit arbitrary direct host execution for untrusted multi-step agent actions.
- **Mechanism:**
  - Standard command execution runs inside ephemeral rootless Podman/Docker containers.
  - Strict resource constraints: `--memory 1g`, `--cpus 1.0`, `--pids-limit 100`, read-only root with disposable `tmpfs /workspace:rw,size=256m`.
  - Network isolation: `--network none` by default, or egress filtered through an authenticated egress proxy.

### C. Out-of-Band Action Sentinel
- **Decision:** Isolate sensitive operations (credential usage, account modifications, destructive shell commands, git push) from raw LLM autonomous execution.
- **Mechanism:**
  - Tool classification into three risk categories: `safe` (read-only), `confirm_required` (mutating/external), and `forbidden`.
  - When an action triggers `confirm_required`, execution suspends into `waiting_approval` status.
  - The Sentinel dispatches an out-of-band prompt to the user (via Stark HUD modal or Telegram inline keyboard), and only resumes upon explicit confirmation.

### D. Reverse-Engineering & Forensic Analysis via REA (`rea-agents`)
- **Decision:** Standardize diagnostic inspection and reverse-engineering of agent systems using the REA toolkit.
- **Workflow:**
  - **Client Applications:** `npx rea-agents analyze-javascript-application <path>` to extract ASAR bundles, IPC bridges, and internal state stores.
  - **Streaming APIs:** `analyze_web_network_capture` to inspect SSE/WebSocket thought-streaming and tool dispatch protocols.
  - **Storage:** `inspect_sqlite_database` to dump schemas, task execution queues, and vector index tables.
  - **Runtime Behavior:** `capture_process_behavior` to trace child process trees, sandbox escapes, and file descriptors.

---

## 5. Autonomous Evolution Roadmap

1. **Phase 1 (Durable State Registry):** Implement `tasks`, `scheduled_tasks`, and `approval_requests` tables in `memory/jarvis_state.db` with checkpoint recovery.
2. **Phase 2 (Podman Ephemeral Sandbox):** Augment `core/sandbox.py` with an optional rootless container runner for untrusted scripts.
3. **Phase 3 (In-Sandbox Playwright Runner):** Expose accessibility-filtered CDP browsing tools within the container environment.
4. **Phase 4 (Out-of-Band Sentinel Bridge):** Wire multi-client approval notifications to HUD and Telegram gateways.

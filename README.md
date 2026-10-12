# J.A.R.V.I.S. (Iron Man Edition) — On-Demand AI Operating Layer

[![Architecture](https://img.shields.io/badge/Architecture-KDE%20Plasma%20%2F%20Wayland-00d2ff.svg)](https://kde.org)
[![Security](https://img.shields.io/badge/Security-Bearer%20Auth%20%7C%20Allowlist%20Sandbox%20%7C%20CSWSH%20Guard-success.svg)](#security-architecture)
[![Testing](https://img.shields.io/badge/Tests-48%2F48%20Passing-brightgreen.svg)](#verification--testing)
[![Python](https://img.shields.io/badge/Python-3.12%2B%20%2F%20FastAPI-blue.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

An on-demand, industrial-grade AI operating layer for Arch Linux (optimized for KDE Plasma / Wayland), inspired by Tony Stark's J.A.R.V.I.S. Operates strictly on-demand following least-privilege principles, integrating local Ollama cognition, neural speech synthesis, hardware telemetry, Wayland desktop controls, screen OCR text extraction, and a cinematic Stark HUD.

---

## Key Capabilities

- **Stark Tactical HUD (`ui/hud.html`)**:
  - Fullscreen reactive interface served directly from the backend server (`http://127.0.0.1:8090/hud`) under strict same-origin execution (blocking cross-site framing and eliminating `Origin: null` trust).
  - 3D audio-reactive Iron Man helmet canvas, holographic particle mesh, live circular gauge telemetry, and dynamic waveform visualizers.
  - Complete HTML entity escaping across all dynamic logs, OCR previews, clipboard buffers, and task cards to eliminate cross-site scripting (XSS).
  - **Slide-out Tactical Mission Drawer** featuring 6 dedicated control tabs:
    1. **Tasks**: Interactive mission objective task board with full CRUD, priority badges, and purge actions.
    2. **Timers**: One-click countdown presets (+1m, +5m, +15m, +30m), custom timer creation (bounded to 50 active timers, <= 86,400s), and live ticking countdown badges.
    3. **Display & Power**: Backlight illumination slider (1–100%), quick presets, workstation lock switch, and battery/AC power cell telemetry with graceful desktop fallback.
    4. **Weather**: Atmospheric telemetry card with 10-minute bounded caching to prevent API rate limiting.
    5. **Network**: Uplink diagnostic metrics (Wi-Fi SSID, internal egress IP, I/O bandwidth counters) and ICMP ping tool with RFC 1123 validation.
    6. **Screen OCR**: Single-click optical capture scanning active desktop displays with extracted text preview.

- **Neural Voice & Speech Processing**:
  - Natural speech synthesis via Microsoft Edge-TTS cloud service (`edge-tts`) supporting British Jarvis (`en-GB-RyanNeural`), Alexa (`en-US-JennyNeural`), and Friday (`en-US-AriaNeural`). *Note: Edge-TTS streams neural audio from Microsoft endpoints and requires internet connectivity.*
  - Speech input pipeline using the browser Web Speech API with wake-word filtering ("Alexa" / "Jarvis") and strict half-duplex pause gating during TTS playback to prevent acoustic feedback and self-confirmation loops.

- **Optical Screen OCR Pipeline (`core/vision.py`)**:
  - Desktop screen capture utilizing native KDE `spectacle` on Plasma Wayland (where `wlr-screencopy` is unavailable under KWin), with fallback to `grim` on wlroots-based compositors.
  - Image preprocessing: PIL grayscale conversion and contrast enhancement (1.8x) optimized for small fonts and dark IDE themes.
  - Optical character recognition via native Tesseract OCR (`--psm 6`) with a strict 4.0-second timeout limit.
  - Text-based screen query reasoning: extracted text is quarantined and piped into the text LLM to answer questions about terminal outputs, error traces, or open files. *(Note: This is an OCR-to-text pipeline; models process extracted ASCII text, not direct multimodal image pixels).*

- **Display Illumination & Session Locking (`core/power_display.py`)**:
  - Machine-readable backlight auto-detection via `brightnessctl -m` (supports hybrid GPU configurations such as `intel_backlight` and `amdgpu_bl*`). Gracefully falls back on desktop monitors without DDC/backlight controls.
  - Workstation session locking via `loginctl lock-session` with fallback to FreeDesktop ScreenSaver DBus interfaces (`qdbus` / `dbus-send`).

- **Productivity & State Persistence (`core/productivity.py`)**:
  - **Persistent Countdown Timers**: Backed by SQLite in WAL mode (`PRAGMA journal_mode=WAL`). Absolute timestamps (`expires_at`) eliminate client drift. Active timers rehydrate across core server restarts; expired timers are automatically cleaned up with desktop notifications. Concurrency is capped at 50 active timers to prevent thread starvation.
  - **Mission Objective Task Board**: Full CRUD lifecycle (`add`, `get`, `update`, `complete`, `delete`, `clear_completed`).
  - **Wayland Clipboard Bridge**: Safe system clipboard read and write using `wl-paste` and `wl-copy`.

- **Atmospheric & Network Intelligence (`core/weather_search.py`, `core/network_tools.py`)**:
  - Atmospheric weather telemetry via `wttr.in` with an in-memory bounded cache (max 100 entries, 10-minute TTL).
  - Instant encyclopedia search using DuckDuckGo Instant Answer API with in-memory bounded caching.
  - Multi-target connectivity verification: combined TCP handshake probe to Cloudflare DNS port 53 (`1.1.1.1:53`) and HTTP 204 endpoint to confirm egress connectivity without relying solely on filtered ICMP packets.
  - Network interface inspection via `nmcli` and `psutil`, plus ICMP ping latency testing.

- **Hardware Telemetry & Arc Reactor Stability (`core/system_telemetry.py`)**:
  - Real-time CPU percent, logical core counts, load averages, RAM allocation, disk capacity, temperature sensors, and top process inspection.
  - **Arc Reactor Stability Index**: A synthetic composite system health indicator computed deterministically from CPU and RAM pressure:
    $$\text{Stability} = \text{clamp}\left(50.0,\, 99.9,\, 100.0 - (0.15 \cdot \text{CPU}_{\%} + 0.10 \cdot \max(0,\, \text{RAM}_{\%} - 20))\right)$$

---

## Security Architecture

J.A.R.V.I.S. enforces a defense-in-depth security model designed against localhost privilege escalation, browser CSRF, cross-site WebSocket hijacking, and prompt injection breakouts:

```
+-------------------------------------------------------------------------+
|                              STARK HUD                                  |
|   (Served via Same-Origin http://127.0.0.1:8090/hud | XSS HTML-Escaped) |
+------------------------------------+------------------------------------+
                                     |
                [Bearer Auth Header / First-Frame WS Auth]
                                     |
                                     v
+------------------------------------+------------------------------------+
|                       SECURITY GATEWAY & ASGI                           |
|  - HostValidationMiddleware (blocks DNS rebinding)                      |
|  - OriginValidationMiddleware (rejects external web origins & 'null')   |
|  - CSWSH Guard (validates WebSocket handshake Origin & Host)            |
|  - 256-Bit Bearer Auth (~/.jarvis_auth_token, 0600, constant-time hmac)  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                  3-TIER ACTION SAFETY PROTOCOL                          |
|  - Tier 1: Informational / Read-Only (Unrestricted once authenticated)  |
|  - Tier 2: Reversible Controls (Immediate execution + audit log)       |
|  - Tier 3: Sensitive / Destructive (Strict two-step voice / confirm=true)|
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                 ISOLATION & EXECUTION ENVIRONMENT                       |
|  - Quarantine Tagging (<untrusted_external_content> with XML escapes)   |
|  - Allowlist Sandbox (echo, git, uptime, uname, df, free, date, whoami) |
|  - 100% Zero Shell Subprocess Invocations (shell=False, argv lists)     |
|  - Argument Injection Defense (-- separator, RFC 1123 hostname regex)   |
|  - SQLite WAL Relational Database & File Audit Trail                    |
+-------------------------------------------------------------------------+
```

### 1. 256-Bit Bearer Token Authentication (`core/security_guard.py`)
- Automatically generates a cryptographically secure 256-bit token stored at `~/.jarvis_auth_token` with restrictive POSIX permissions (`0600`).
- Constant-time verification using `hmac.compare_digest` to prevent timing side-channel attacks.
- Sensitive endpoints require valid authentication (`require_auth`). Unauthenticated requests are rejected with `401 Unauthorized`.
- **Zero Unauthenticated Token Discovery**: The open `/api/auth/token` endpoint has been removed. The HUD receives credentials either via secure launcher injection (e.g. `http://127.0.0.1:8090/hud#token=<token>`, stripped immediately from browser history) or via a one-time session prompt stored in `localStorage`.

### 2. DNS Rebinding & Cross-Origin CSRF Defense
- `HostValidationMiddleware`: Rejects requests with unexpected `Host` headers (`403 Forbidden`) to prevent DNS rebinding attacks.
- `OriginValidationMiddleware`: Blocks cross-site origins. `Origin: null` is strictly forbidden to prevent sandboxed iframe bypasses. Only legitimate loopback origins (`http://127.0.0.1:8090`, `http://localhost:8090`) are permitted.

### 3. Cross-Site WebSocket Hijacking (CSWSH) Defense
- `verify_websocket_connection`: The `/ws/stream` handshake verifies both `Origin` and `Host` headers before connection acceptance, blocking CSWSH attacks from external browser tabs.
- WebSocket authentication accepts credentials via first-frame authentication payload (`{"type": "auth", "token": "..."}`) with a 3.0-second timeout, avoiding query-string token leaks in access logs.

### 4. Explicit 3-Tier Action Safety & Confirmation Protocol
Actions are categorized into three distinct security tiers:
- **Tier 1 (Informational / Read-Only)**: Real-time hardware telemetry, weather reports, network status, and clipboard reads. Accessible immediately upon token authentication.
- **Tier 2 (Reversible / Operational Controls)**: Audio volume, display brightness, task board creation, and timer scheduling. Executed immediately with audit logging.
- **Tier 3 (Sensitive / Destructive Operations)**: Workstation session locking (`lock_session`), clearing all completed tasks (`clear_completed_todos`), and sandboxed execution. Requires explicit two-step user confirmation:
  - In natural language / voice: triggers a 60-second challenge (`PENDING_CONFIRMATIONS`). Unsolicited confirmations without an active challenge are rejected.
  - In REST API: requires an explicit confirmation payload (`{"confirm": true}`) to prevent accidental invocation.

### 5. Allowlist Execution Sandbox & Zero Shell Invocation (`core/sandbox.py`)
- Replaces naive blocklists with an explicit **binary allowlist policy** (`ALLOWED_BINARIES = {"echo", "git", "uptime", "uname", "df", "free", "date", "whoami", "ls"}`).
- Zero shell execution (`shell=False`) across all invocations, parsing command strings safely via `shlex.split`.
- Secondary regex defense against destructive patterns (`rm -rf`, `mkfs`, raw block device writes, fork bombs).
- All command executions, exits, and security exceptions are recorded to `memory/audit_trail.log`.

### 6. Subprocess Argument Injection Defense
- 100% of subprocess executions across the entire codebase utilize strict argv argument lists with `shell=False`:
  - Display & session: `brightnessctl`, `loginctl`, `qdbus`, `dbus-send`
  - Screen capture & OCR: `spectacle`, `grim`, `tesseract`
  - Audio & notifications: `pactl`, `playerctl`, `notify-send`
  - Clipboard & networking: `wl-copy`, `wl-paste`, `ping`, `nmcli`
- Hostname validation in network tools uses strict RFC 1123, IPv4, and IPv6 regex rejecting leading hyphens (`-`) and newlines (`\n`), with `--` argument isolation to prevent command-line option injection.

### 7. Quarantine Isolation Framing (`core/vision.py`, `core/llm_agent.py`)
- Untrusted external content (OCR scans, encyclopedia abstracts, clipboard text) is framed inside `<untrusted_external_content>` tags.
- Closing delimiter variants (e.g. `</untrusted_external_content>`, uppercase variants, and spaced tags) are escaped to `&lt;/untrusted_external_content&gt;` using case-insensitive regex to prevent prompt escaping.
- The system prompt instructs the cognitive model to treat quarantined content strictly as inert reference data. Least-privilege confirmation gating serves as the primary enforcement barrier against unauthorized actions.

### 8. Acoustic Feedback & Speech Echo Prevention
- The HUD speech pipeline enforces half-duplex operation: whenever neural TTS speech playback begins (`speak()`), speech recognition is automatically paused (`stopListening()`).
- Recognition is only re-engaged after speech concludes (`audio.onended`) with an acoustic grace period (400ms) to ensure ambient mic feedback does not self-confirm sensitive directives.

---

## Directory Structure & Subsystem Roles

```
/home/thor/Desktop/JARVIS/
├── core/
│   ├── app_controller.py        # Application launcher and desktop notification dispatcher
│   ├── heartbeat.py             # Proactive background monitoring daemon (30s cadence)
│   ├── llm_agent.py             # Cognitive routing, safety tiers, and Ollama integration
│   ├── media_controller.py      # Volume control and playback management (pactl / playerctl)
│   ├── network_tools.py         # Multi-target connectivity probe, status, ping latency
│   ├── power_display.py         # Backlight calibration, session lock, power telemetry
│   ├── productivity.py          # Persistent timers, SQLite task board CRUD, clipboard bridge
│   ├── reflection.py            # Long-term cognitive reflection and trajectory logging
│   ├── sandbox.py               # Allowlist command execution sandbox with audit trail
│   ├── security_guard.py        # Bearer token auth, Host/Origin/CSWSH security middleware
│   ├── server.py                # FastAPI ASGI backend (REST endpoints + WebSocket stream)
│   ├── system_capabilities.py   # Subsystem binary detection and capability matrix
│   ├── system_telemetry.py      # CPU, RAM, disk, thermals, and Arc Reactor stability metrics
│   ├── vector_memory.py         # Semantic memory embedding and LanceDB vector recall
│   ├── vision.py                # Desktop screen capture, contrast preprocessing, Tesseract OCR
│   ├── voice_engine.py          # Microsoft Edge-TTS neural speech synthesis engine
│   └── weather_search.py        # Weather telemetry and DuckDuckGo encyclopedia lookup
├── ui/
│   └── hud.html                 # Cinematic Stark HUD & Tactical Mission Drawer
├── tests/
│   ├── test_heartbeat.py        # Server heartbeat lifecycle test
│   ├── test_media_controller.py # Volume and media controls test
│   ├── test_network_tools.py    # Network status, RFC hostname validation, ping latency test
│   ├── test_power_display.py    # Display illumination and battery status test
│   ├── test_productivity.py     # SQLite timer persistence, rehydration, task CRUD tests
│   ├── test_sandbox.py          # Allowlist sandbox execution, blocked binaries, audit log test
│   ├── test_telemetry.py        # Hardware telemetry and Arc Reactor metrics test
│   ├── test_unified.py          # End-to-end integration, auth gating, and health probe tests
│   ├── test_unit_capabilities.py# Subsystem binary detection unit test
│   ├── test_unit_security.py    # Bearer auth, CSWSH guard, prompt injection, confirmation tests
│   ├── test_vector_memory.py    # Vector semantic memory test
│   ├── test_vision.py           # Screen capture, preprocessing, and OCR test
│   ├── test_voice_engine.py     # Neural voice synthesis test
│   └── test_weather_search.py   # Atmospheric telemetry and encyclopedia cache test
├── memory/
│   ├── jarvis_state.db          # SQLite relational database (interactions, todos, timers)
│   └── audit_trail.log          # Sandboxed command execution audit trail
└── ADR.md                       # Architectural Decision Records
```

### Relational Database Schema (`memory/jarvis_state.db`)
- `interactions`: Logs every user directive, speaker identifier, timestamp, and classified intent.
- `telemetry`: Periodic snapshots of system resource utilization.
- `reflections`: Stores post-task cognitive reflections, trajectory evaluations, and lessons learned.
- `todos`: Mission tasks with `id`, `task` (<= 500 chars), `status` (`pending`, `completed`), `priority`, and timestamps.
- `timers`: Active and historical countdown timers with `id`, `label`, `duration_seconds`, `expires_at`, and `status`.

---

## REST & WebSocket API Reference

The backend operates on `http://127.0.0.1:8090` by default (`JARVIS_PORT`).

| Method | Endpoint | Auth Required | Safety Tier | Description & Validation Bounds |
|---|---|:---:|:---:|---|
| `GET` | `/api/health` | No | — | Minimal health probe (`status: healthy`, no system metrics leaked) |
| `GET` | `/api/heartbeat` | No | — | Health probe alias for daemon heartbeat monitoring |
| `GET` | `/hud` or `/` | No | — | Serves the Stark Tactical HUD interface directly under same-origin |
| `GET` | `/api/telemetry` | Yes | Tier 1 | Real-time CPU, RAM, disk, thermals, and Arc Reactor stability metrics |
| `GET` | `/api/system/capabilities` | Yes | Tier 1 | Inspects host binaries, Wayland support, and Ollama status |
| `POST` | `/api/command` | Yes | Tier 1–3 | Natural language directive router (`query: 1-2000 chars`) |
| `GET` | `/api/system/brightness` | Yes | Tier 1 | Reads current screen brightness percentage |
| `POST` | `/api/system/brightness` | Yes | Tier 2 | Calibrates screen brightness (`percent: 1-100`) |
| `POST` | `/api/system/lock` | Yes | Tier 3 | Locks workstation session (`{"confirm": true}` required) |
| `GET` | `/api/system/power` | Yes | Tier 1 | Reads battery charge, AC status, and estimated runtime |
| `GET` | `/api/productivity/todos` | Yes | Tier 1 | Lists mission tasks (`?include_completed=true`) |
| `POST` | `/api/productivity/todos` | Yes | Tier 2 | Adds mission task (`task: 1-500 chars, priority: low\|normal\|high`) |
| `GET` | `/api/productivity/todos/{id}`| Yes | Tier 1 | Retrieves task by integer identifier |
| `PUT` | `/api/productivity/todos/{id}`| Yes | Tier 2 | Updates task description, priority, or status |
| `POST` | `/api/productivity/todos/{id}/complete` | Yes | Tier 2 | Marks mission task as completed |
| `DELETE` | `/api/productivity/todos/completed` | Yes | Tier 3 | Clears all completed tasks (declared before dynamic ID route) |
| `DELETE` | `/api/productivity/todos/{id}` | Yes | Tier 2 | Deletes a task from the registry |
| `GET` | `/api/productivity/timers` | Yes | Tier 1 | Lists active countdown timers with live remaining seconds |
| `POST` | `/api/productivity/timers` | Yes | Tier 2 | Starts persistent timer (`seconds: 1-86400, label: <= 100 chars`) |
| `DELETE` | `/api/productivity/timers/{id}` | Yes | Tier 2 | Cancels an active countdown timer |
| `GET` | `/api/productivity/clipboard` | Yes | Tier 1 | Reads system clipboard contents via `wl-paste` |
| `POST` | `/api/productivity/clipboard` | Yes | Tier 2 | Sets system clipboard contents via `wl-copy` (`text: <= 64KB`) |
| `GET` | `/api/weather` | Yes | Tier 1 | Atmospheric conditions via `wttr.in` (10-minute bounded cache) |
| `GET` | `/api/knowledge` or `/api/search` | Yes | Tier 1 | DuckDuckGo encyclopedia abstract lookup (10-minute bounded cache) |
| `GET` | `/api/network/status` | Yes | Tier 1 | Active network interface, IP, Wi-Fi SSID, and I/O metrics |
| `GET` | `/api/network/connectivity` | Yes | Tier 1 | Multi-target socket (`1.1.1.1:53`) and HTTP 204 connectivity check |
| `POST` | `/api/network/ping` | Yes | Tier 1 | ICMP ping latency check (`host: RFC 1123 / IPv4 / IPv6`) |
| `GET` | `/api/screen/capture` | Yes | Tier 1 | Captures active display screenshot to memory buffer |
| `POST` | `/api/screen/ocr` | Yes | Tier 1 | Performs Tesseract OCR text extraction and optional LLM query |
| `GET` | `/api/voice/profiles` | No | Tier 1 | Lists available Edge-TTS neural voice profiles |
| `GET` | `/api/voice/tts` | Token | Tier 1 | Streams synthesized MP3 audio for HTML5 audio elements |
| `POST` | `/api/voice/tts` | Yes | Tier 1 | Synthesizes speech from JSON request body |
| `WS` | `/ws/stream` | Token | Tier 1–3 | Real-time telemetry stream and directive channel with CSWSH guard |

---

## Installation & Setup

### 1. System Requirements (Arch Linux / KDE Plasma)

Install required system packages:

```bash
sudo pacman -S --needed brightnessctl tesseract tesseract-data-eng \
  spectacle grim wl-clipboard libnotify playerctl
```

### 2. Python Dependencies

```bash
pip install fastapi uvicorn psutil pillow requests edge-tts
```

### 3. Local Cognitive Engine (Ollama)

Ensure [Ollama](https://ollama.ai) is running locally with the target model:

```bash
ollama run llama3.2:latest
```

---

## Running J.A.R.V.I.S.

### 1. Start the Core Intelligence Server

```bash
python3 /home/thor/Desktop/JARVIS/core/server.py
```

The server binds to `127.0.0.1:8090` and logs active capabilities.

### 2. Launch the Cinematic HUD

Open the HUD directly through the local server:

```bash
xdg-open "http://127.0.0.1:8090/hud#token=$(cat ~/.jarvis_auth_token)"
```

- If launched without `#token=`, the HUD prompts once for the token located at `~/.jarvis_auth_token` and saves it securely to `localStorage`.
- Click **ACTIVATE MIC** or press `Enter` to issue voice or text directives.
- Click the **TACTICAL DRAWER** button on the bottom toolbar to access the Mission Drawer.

---

## Verification & Testing

Execute the hermetic test suite covering security hardening, sandbox policy, capabilities, productivity persistence, and unified integration:

```bash
python3 -m unittest discover -s tests
```

```
Ran 48 tests in 17.903s

OK
```

All 48 tests execute without external network dependencies:
- **Security Hardening (`tests/test_unit_security.py`)**: Bearer auth validation, Host/Origin rejection (no `null` allowed), CSWSH WebSocket validation, shell/argument injection defense, prompt injection delimiter escaping, and two-step confirmation gating.
- **Sandbox Security (`tests/test_sandbox.py`)**: Binary allowlist policy, rejection of unauthorized and destructive binaries, timeout enforcement, and audit trail logging.
- **Capability Matrix (`tests/test_unit_capabilities.py`)**: Subsystem binary checks, Wayland detection, and Ollama status.
- **Productivity & Persistence (`tests/test_productivity.py`)**: SQLite timer rehydration, task CRUD lifecycle, and clipboard bridge.
- **Unified Integration (`tests/test_unified.py`)**: End-to-end FastAPI server, unauthenticated health probe verification, authenticated telemetry enforcement, and command dispatch.

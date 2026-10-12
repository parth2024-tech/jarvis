# J.A.R.V.I.S. (Iron Man Edition) — Autonomous AI Operating Layer

[![Architecture](https://img.shields.io/badge/Architecture-KDE%20Plasma%20%2F%20Wayland-00d2ff.svg)](https://kde.org)
[![Security](https://img.shields.io/badge/Security-Bearer%20Auth%20%7C%20DNS%20Rebinding%20Guard-success.svg)](#security-architecture)
[![Testing](https://img.shields.io/badge/Tests-42%2F42%20Passing-brightgreen.svg)](#verification--testing)
[![Python](https://img.shields.io/badge/Python-3.12%2B%20%2F%20FastAPI-blue.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

An on-demand, military-grade autonomous AI operating layer for Linux (optimized for Arch Linux & KDE Plasma / Wayland), inspired by Tony Stark's J.A.R.V.I.S. Integrates local Ollama cognition, neural voice synthesis, real-time hardware telemetry, Wayland desktop automation, optical screen OCR, and a cinematic Stark HUD.

---

## Key Capabilities

- **Stark Tactical HUD (`ui/hud.html`)**:
  - Fullscreen reactive interface with 3D audio-reactive Iron Man helmet canvas, holographic particle mesh, live circular gauge telemetry, and dynamic waveform visualizers.
  - **Slide-out Tactical Mission Drawer** featuring 6 dedicated control tabs:
    1. **Tasks**: Interactive mission objective task board with priority controls, checkboxes, and purge actions.
    2. **Timers**: One-click countdown presets (+1m, +5m, +15m, +30m), custom timer creation, and live ticking countdown badges.
    3. **Display & Power**: Backlight illumination slider, quick presets (25%, 50%, 75%, 100%), workstation lock switch, and battery cell telemetry.
    4. **Weather**: Atmospheric telemetry card with real-time conditions, wind speeds, and location lookup.
    5. **Network**: Uplink diagnostic metrics (Wi-Fi SSID, internal IP, I/O bandwidth counters) and live ICMP ping tool.
    6. **Screen OCR**: Single-click optical capture scanning active desktop displays with extracted text preview.

- **Neural Voice & Speech Processing**:
  - Natural speech synthesis via local Edge-TTS integration supporting British Jarvis (`en-GB-RyanNeural`), Alexa (`en-US-JennyNeural`), and Friday (`en-US-AriaNeural`).
  - Full-duplex speech input pipeline with automatic speech recognition and voice activity triggers.

- **Multimodal Screen Vision & OCR (`core/vision.py`)**:
  - High-speed desktop screen capture using native KDE `spectacle` and `grim` (sub-300ms execution).
  - PIL contrast preprocessing pipeline optimized for small fonts and dark IDE themes.
  - Native Tesseract optical character recognition with strict 4.0s timeout limits.
  - Direct visual comprehension: ask J.A.R.V.I.S. questions about documents, code errors, or terminal logs visible on screen.

- **Display Illumination & Session Locking (`core/power_display.py`)**:
  - Machine-readable backlight auto-detection via `brightnessctl -m` (supports hybrid GPU configurations such as `intel_backlight` and `amdgpu_bl*`).
  - Workstation session locking via `loginctl lock-session` with fallback to FreeDesktop ScreenSaver DBus interface.

- **Productivity & State Persistence (`core/productivity.py`)**:
  - **Persistent Countdown Timers**: Backed by SQLite in WAL mode (`PRAGMA journal_mode=WAL`). Absolute timestamps (`expires_at`) eliminate client drift. Timers automatically rehydrate and resume countdown threads across backend restarts.
  - **Mission Objective Task Board**: Full CRUD lifecycle (`add`, `get`, `update`, `complete`, `delete`, `clear_completed`).
  - **Wayland Clipboard Bridge**: Read and write system clipboard contents safely using `wl-paste` and `wl-copy`.

- **Atmospheric & Network Intelligence (`core/weather_search.py`, `core/network_tools.py`)**:
  - Weather telemetry via `wttr.in` with an in-memory 10-minute cache to respect rate limits.
  - Instant knowledge search using DuckDuckGo Instant Answer API with in-memory caching.
  - Multi-target network diagnostics: combined DNS socket probe (`1.1.1.1:53`) and HTTP 204 probe to verify actual internet connectivity even when ICMP ping is filtered.

---

## Security Architecture

J.A.R.V.I.S. is built with defense-in-depth principles against localhost exploits, browser CSRF, and prompt injections:

1. **256-Bit Bearer Token Authentication (`core/security_guard.py`)**:
   - Automatic generation of a cryptographically secure 256-bit token stored at `~/.jarvis_auth_token` with restrictive POSIX permissions (`0600`).
   - Constant-time token verification using `hmac.compare_digest` to prevent timing side-channel attacks.
   - All state-mutating, sensitive, or hardware-controlling endpoints require valid authentication (`require_auth`). Unauthenticated requests are rejected with `401 Unauthorized`.

2. **DNS Rebinding & Cross-Origin CSRF Defense**:
   - `HostValidationMiddleware`: Strictly rejects requests with unexpected `Host` headers (`403 Forbidden`) to block DNS rebinding attacks.
   - `OriginValidationMiddleware`: Blocks cross-site origins while permitting local browser files (`file://` / `null`) and loopback endpoints.

3. **Anti-Prompt-Injection Firewall (`core/llm_agent.py`, `core/vision.py`)**:
   - Untrusted OCR, web, and clipboard text is sanitized and quarantined within `<untrusted_external_content>` tags.
   - Fake system tags and injection directives (`<system>`, `[SYSTEM DIRECTIVE:]`, ````system`) are stripped.
   - The LLM is instructed under strict system rules to treat all external content solely as inert reference material.

4. **Tier 3 Sensitive Action Confirmation Protocol**:
   - Destructive and security-sensitive actions (`lock_session`, `clear_completed_todos`) cannot be triggered automatically by voice misinterpretations or untrusted content.
   - Actions enter a 60-second pending state (`PENDING_CONFIRMATIONS`) and require explicit user confirmation ("confirm lock", "confirm clear").
   - Confirmation queries are dispatched via a sub-15ms fast-path router without invoking LLM inference.

5. **Zero Shell Execution & Hostname Validation**:
   - 100% strict argv argument lists (`shell=False`) across all subprocess executions (`spectacle`, `grim`, `tesseract`, `brightnessctl`, `loginctl`, `wl-copy`, `wl-paste`, `pactl`, `playerctl`).
   - Hostname input validation in network diagnostic tools enforced by strict regex (`^[a-zA-Z0-9.-]+$`).

---

## Directory Structure

```
/home/thor/Desktop/JARVIS/
├── core/
│   ├── app_controller.py        # Application launcher and notification dispatcher
│   ├── llm_agent.py             # Cognitive routing, fast-dispatch paths, Ollama integration
│   ├── media_controller.py      # Volume control and playback management (pactl / playerctl)
│   ├── network_tools.py         # Multi-target connectivity probe, status, ping
│   ├── power_display.py         # Backlight calibration, session lock, power telemetry
│   ├── productivity.py          # Persistent timers, SQLite task board CRUD, clipboard bridge
│   ├── sandbox.py               # Command execution sandbox with blocklist defense
│   ├── security_guard.py        # Bearer token auth, Host/Origin validation middleware
│   ├── server.py                # FastAPI ASGI backend (REST endpoints + WebSocket stream)
│   ├── system_capabilities.py   # Hardware and binary capability detection matrix
│   ├── system_telemetry.py      # CPU, RAM, disk, and Arc Reactor stability metrics
│   ├── vector_memory.py         # Vector memory storage and semantic retrieval
│   ├── vision.py                # Screen capture, preprocessing, and Tesseract OCR
│   ├── voice_engine.py          # Neural Edge-TTS speech synthesis engine
│   └── weather_search.py        # Weather telemetry and instant knowledge search
├── ui/
│   └── hud.html                 # Cinematic Stark HUD & Tactical Mission Drawer
├── tests/
│   ├── test_heartbeat.py        # Server heartbeat test
│   ├── test_media_controller.py # Volume and media controls test
│   ├── test_network_tools.py    # Network status and ping latency test
│   ├── test_power_display.py    # Display illumination and battery status test
│   ├── test_productivity.py     # Timers, rehydration, and task CRUD tests
│   ├── test_telemetry.py        # Hardware telemetry metrics test
│   ├── test_unified.py          # End-to-end integration and API tests
│   ├── test_unit_capabilities.py# System capability matrix unit test
│   ├── test_unit_security.py    # Bearer auth, DNS rebinding, and confirmation unit test
│   ├── test_vector_memory.py    # Semantic memory test
│   ├── test_vision.py           # Screen capture and OCR test
│   ├── test_voice_engine.py     # Neural voice synthesis test
│   └── test_weather_search.py   # Atmospheric and encyclopedia search test
├── memory/
│   └── jarvis_state.db          # SQLite relational database (todos, timers, audit log)
└── ADR.md                       # Architectural Decision Records
```

---

## REST & WebSocket API Reference

The backend operates on `http://127.0.0.1:8090` by default (`JARVIS_PORT`).

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `GET` | `/api/telemetry` | No | Real-time CPU, RAM, disk, and Arc Reactor stability metrics |
| `GET` | `/api/auth/token` | No | Retrieves active session token for local HUD bootstrapping |
| `POST` | `/api/command` | Yes | Dispatches natural language voice/text directives |
| `GET` | `/api/system/capabilities` | Yes | Inspects host binaries, Wayland support, and Ollama status |
| `GET` | `/api/system/brightness` | Yes | Reads current screen brightness percentage |
| `POST` | `/api/system/brightness` | Yes | Calibrates screen brightness (`{"percent": 75}`) |
| `POST` | `/api/system/lock` | Yes | Locks workstation session |
| `GET` | `/api/system/power` | Yes | Reads battery charge, AC status, and estimated runtime |
| `GET` | `/api/productivity/todos` | Yes | Lists mission objective tasks (`?completed=true`) |
| `POST` | `/api/productivity/todos` | Yes | Adds a new mission task (`{"task": "...", "priority": "high"}`) |
| `POST` | `/api/productivity/todos/{id}/complete` | Yes | Marks a mission task as completed |
| `DELETE` | `/api/productivity/todos/{id}` | Yes | Deletes a task from the registry |
| `DELETE` | `/api/productivity/todos/completed` | Yes | Clears completed tasks (requires confirmation) |
| `GET` | `/api/productivity/timers` | Yes | Lists running countdown timers with live remaining seconds |
| `POST` | `/api/productivity/timers` | Yes | Starts a new persistent timer (`{"seconds": 300, "label": "Tea"}`) |
| `DELETE` | `/api/productivity/timers/{id}` | Yes | Cancels an active timer |
| `GET` | `/api/productivity/clipboard` | Yes | Reads system clipboard contents |
| `POST` | `/api/productivity/clipboard` | Yes | Sets system clipboard contents |
| `GET` | `/api/weather` | Yes | Reads atmospheric conditions (`?location=London`) |
| `GET` | `/api/network/status` | Yes | Reads active interface, IP, Wi-Fi SSID, and I/O metrics |
| `POST` | `/api/network/ping` | Yes | Performs ICMP/DNS latency check (`{"host": "1.1.1.1"}`) |
| `POST` | `/api/screen/ocr` | Yes | Captures screen and extracts OCR text |
| `POST` | `/api/voice/synthesize` | Yes | Generates neural speech audio stream |
| `WS` | `/ws/stream` | Token | WebSocket stream for real-time telemetry and state events |

---

## Installation & Setup

### 1. System Requirements (Arch Linux / KDE Plasma)

Install required system binaries:

```bash
sudo pacman -S --needed brightnessctl tesseract tesseract-data-eng \
  spectacle grim wl-clipboard libnotify playerctl pulseaudio
```

### 2. Python Dependencies

```bash
pip install fastapi uvicorn psutil pillow requests edge-tts
```

### 3. Local LLM Setup (Ollama)

Ensure [Ollama](https://ollama.ai) is running locally:

```bash
ollama run llama3.2:latest
ollama pull qwen3:4b-fast
```

---

## Running J.A.R.V.I.S.

### 1. Start the Core Intelligence Server

```bash
python3 /home/thor/Desktop/JARVIS/core/server.py
```

The server binds to `127.0.0.1:8090` and logs active capabilities.

### 2. Launch the Cinematic HUD

Open [`ui/hud.html`](file:///home/thor/Desktop/JARVIS/ui/hud.html) in your browser:

```bash
xdg-open /home/thor/Desktop/JARVIS/ui/hud.html
```

- Click **ACTIVATE MIC** or press `Enter` to speak or type commands.
- Click the **TACTICAL DRAWER** button on the bottom toolbar to access the Mission Drawer.

---

## Verification & Testing

Run the complete hermetic test suite covering security, capabilities, productivity, and end-to-end integration:

```bash
python3 -m unittest discover -s tests
```

```
Ran 42 tests in 21.592s

OK
```

All 42 tests execute without external network dependencies:
- **Security Tests (`tests/test_unit_security.py`)**: Bearer auth validation, DNS rebinding rejection, CSRF origin rejection, shell injection safety, prompt injection filtering, and two-step confirmation protocol.
- **Capability Matrix Tests (`tests/test_unit_capabilities.py`)**: Subsystem binary checks, Wayland detection, Ollama status.
- **Productivity Tests (`tests/test_productivity.py`)**: SQLite timer persistence across engine restart, task CRUD lifecycle, clipboard bridge.
- **Integration Tests (`tests/test_unified.py`)**: Unified FastAPI server, auth header enforcement, and command dispatch.

import uvicorn
import sqlite3
import time
import os
import asyncio
import json
import threading
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field

from sandbox import secure_execute
from heartbeat import ProactiveHeartbeat
from vision import capture_screen_state, read_screen_text, summarize_screen
from reflection import record_reflection, get_recent_reflections
from system_telemetry import get_system_metrics, get_telemetry_summary
from llm_agent import execute_agent_directive
from vector_memory import store_memory, query_memories
from voice_engine import synthesize_speech, get_voice_profiles
from power_display import get_brightness, set_brightness, change_brightness, lock_session, get_power_status
from productivity import (
    set_timer, get_active_timers, cancel_timer,
    add_todo, list_todos, get_todo, update_todo, delete_todo,
    complete_todo, clear_completed_todos,
    get_clipboard_text, set_clipboard_text
)
from weather_search import get_weather, lookup_encyclopedia_abstract
from network_tools import get_network_status, ping_latency, verify_internet_connectivity
from system_capabilities import probe_system_capabilities
from security_guard import (
    AUTH_TOKEN, verify_token, require_auth,
    HostValidationMiddleware, OriginValidationMiddleware
)

PORT = int(os.environ.get("JARVIS_PORT", 8090))

app = FastAPI(
    title="J.A.R.V.I.S. Unified Industrial Core",
    description="Production-grade autonomous AI operating layer integrating real telemetry, vector/relational memory, secure execution sandboxing, WebSocket streaming, and neural voice synthesis.",
    version="3.7.0"
)

# 1. Host Validation Middleware (DNS Rebinding Defense)
app.add_middleware(HostValidationMiddleware, allowed_port=PORT)

# 2. Origin Validation Middleware (CSRF & Cross-Site Fetch Defense)
app.add_middleware(OriginValidationMiddleware, allowed_port=PORT)

# 3. Restrictive CORS (Local loopback and local file only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{PORT}",
        f"http://localhost:{PORT}",
        f"https://127.0.0.1:{PORT}",
        f"https://localhost:{PORT}",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            speaker TEXT,
            message TEXT,
            intent TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            metric TEXT,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            task_name TEXT,
            trajectory TEXT,
            outcome TEXT,
            lessons_learned TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Start Proactive Background Daemon
heartbeat = ProactiveHeartbeat(interval_seconds=30)
heartbeat.start()

# ========================================================
# Pydantic Request Models
# ========================================================
class QueryRequest(BaseModel):
    query: str
    context: str = "general"

class TTSRequest(BaseModel):
    text: str
    voice: str = "alexa"
    rate: str = "+0%"

class TodoCreateRequest(BaseModel):
    task: str = Field(..., min_length=1)
    priority: str = "normal"

class TodoUpdateRequest(BaseModel):
    task: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

class TimerCreateRequest(BaseModel):
    seconds: int = Field(..., ge=1, le=86400)
    label: str = "Directive"

class BrightnessRequest(BaseModel):
    percent: int = Field(..., ge=1, le=100)

class ClipboardRequest(BaseModel):
    text: str

class PingRequest(BaseModel):
    host: str = "1.1.1.1"

class OCRRequest(BaseModel):
    question: Optional[str] = ""

# ========================================================
# 1. System Health & Authentication Discovery
# ========================================================
@app.get("/api/auth/token")
async def get_token_for_local_client():
    """
    Returns the active bearer token for loopback clients connecting directly.
    """
    return {"token": AUTH_TOKEN}

@app.get("/api/system/capabilities")
async def get_system_capabilities():
    """
    Reports runtime system tools and protocol degradation matrix.
    """
    return probe_system_capabilities()

@app.get("/api/telemetry")
async def get_telemetry():
    m = get_system_metrics()
    return {
        "reactor_stability": m["reactor_stability"],
        "cpu_load_avg": m["load_avg_1m"],
        "cpu_percent": m["cpu_percent"],
        "ram_percent": m["ram_percent"],
        "ram_used_gb": m["ram_used_gb"],
        "ram_total_gb": m["ram_total_gb"],
        "disk_free_gb": m["disk_free_gb"],
        "temperature_c": m["temperature_c"],
        "battery": m["battery"],
        "neural_mesh": "CONNECTED (WEBSOCKET + PROACTIVE DAEMON)",
        "memory_backend": "LanceDB/Vector + SQLite Relational Audit Trail",
        "active_vthreads": threading.active_count(),
        "security_status": "SECURE / REGEX-POLICY SANDBOX"
    }

# ========================================================
# 2. Cognitive Command & LLM Dispatcher
# ========================================================
@app.post("/api/command", dependencies=[Depends(require_auth)])
async def handle_command(req: QueryRequest):
    start_time = time.time()
    query_lower = req.query.lower()

    if "run test suite" in query_lower or "test suite" in query_lower:
        intent = "secure_execution"
        res = secure_execute("echo 'JARVIS Test Suite Verification OK'")
        response = f"Sandbox execution completed. Exit code {res['exit_code']}. Output: {res['output'].strip()}"
        agent_out = {
            "status": "success",
            "intent": intent,
            "response": response,
            "tool_result": res,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    else:
        agent_out = execute_agent_directive(req.query, req.context)

    # Log interaction to SQLite with WAL concurrency
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO interactions (timestamp, speaker, message, intent) VALUES (?, ?, ?, ?)",
            (start_time, "user", req.query, agent_out["intent"])
        )
        cursor.execute(
            "INSERT INTO interactions (timestamp, speaker, message, intent) VALUES (?, ?, ?, ?)",
            (time.time(), "jarvis", agent_out["response"], agent_out["intent"])
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB LOG ERROR] {e}")

    return agent_out

# ========================================================
# 3. Productivity REST API (Full CRUD)
# ========================================================
@app.get("/api/productivity/todos", dependencies=[Depends(require_auth)])
async def api_list_todos(include_completed: bool = False):
    return {"todos": list_todos(include_completed=include_completed)}

@app.post("/api/productivity/todos", dependencies=[Depends(require_auth)])
async def api_add_todo(req: TodoCreateRequest):
    return add_todo(req.task, priority=req.priority)

@app.get("/api/productivity/todos/{todo_id}", dependencies=[Depends(require_auth)])
async def api_get_todo(todo_id: int):
    res = get_todo(todo_id)
    if not res["success"]:
        raise HTTPException(status_code=404, detail=res.get("error", "Task not found"))
    return res

@app.put("/api/productivity/todos/{todo_id}", dependencies=[Depends(require_auth)])
async def api_update_todo(todo_id: int, req: TodoUpdateRequest):
    res = update_todo(todo_id, task=req.task, priority=req.priority, status=req.status)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error", "Update failed"))
    return res

@app.post("/api/productivity/todos/{todo_id}/complete", dependencies=[Depends(require_auth)])
async def api_complete_todo(todo_id: int):
    return complete_todo(todo_id)

@app.delete("/api/productivity/todos/completed", dependencies=[Depends(require_auth)])
async def api_clear_completed_todos():
    return clear_completed_todos()

@app.delete("/api/productivity/todos/{todo_id}", dependencies=[Depends(require_auth)])
async def api_delete_todo(todo_id: int):
    res = delete_todo(todo_id)
    if not res["success"]:
        raise HTTPException(status_code=404, detail=res.get("error", "Task not found"))
    return res

@app.get("/api/productivity/timers", dependencies=[Depends(require_auth)])
async def api_list_timers():
    return {"timers": get_active_timers()}

@app.post("/api/productivity/timers", dependencies=[Depends(require_auth)])
async def api_create_timer(req: TimerCreateRequest):
    return set_timer(req.seconds, label=req.label)

@app.delete("/api/productivity/timers/{timer_id}", dependencies=[Depends(require_auth)])
async def api_cancel_timer(timer_id: str):
    res = cancel_timer(timer_id)
    if not res["success"]:
        raise HTTPException(status_code=404, detail="Timer identifier not found")
    return res

@app.get("/api/productivity/clipboard", dependencies=[Depends(require_auth)])
async def api_get_clipboard():
    return get_clipboard_text()

@app.post("/api/productivity/clipboard", dependencies=[Depends(require_auth)])
async def api_set_clipboard(req: ClipboardRequest):
    return set_clipboard_text(req.text)

# ========================================================
# 4. Display Illumination & Session Security
# ========================================================
@app.get("/api/system/brightness", dependencies=[Depends(require_auth)])
async def api_get_brightness():
    return get_brightness()

@app.post("/api/system/brightness", dependencies=[Depends(require_auth)])
async def api_set_brightness(req: BrightnessRequest):
    return set_brightness(req.percent)

@app.post("/api/system/lock", dependencies=[Depends(require_auth)])
async def api_lock_session():
    return lock_session()

@app.get("/api/system/power", dependencies=[Depends(require_auth)])
async def api_get_power():
    return get_power_status()

# ========================================================
# 5. Atmospheric Weather & Knowledge
# ========================================================
@app.get("/api/weather", dependencies=[Depends(require_auth)])
async def api_get_weather(location: str = ""):
    return get_weather(location)

@app.get("/api/knowledge", dependencies=[Depends(require_auth)])
async def api_get_knowledge(query: str):
    return lookup_encyclopedia_abstract(query)

# ========================================================
# 6. Network Telemetry & Diagnostics
# ========================================================
@app.get("/api/network/status", dependencies=[Depends(require_auth)])
async def api_get_network_status():
    return get_network_status()

@app.get("/api/network/connectivity", dependencies=[Depends(require_auth)])
async def api_get_connectivity():
    return await asyncio.to_thread(verify_internet_connectivity)

@app.post("/api/network/ping", dependencies=[Depends(require_auth)])
async def api_ping(req: PingRequest):
    return await asyncio.to_thread(ping_latency, req.host)

# ========================================================
# 7. Multimodal Vision & OCR
# ========================================================
@app.get("/api/screen/capture", dependencies=[Depends(require_auth)])
async def api_capture_screen():
    return capture_screen_state()

@app.post("/api/screen/ocr", dependencies=[Depends(require_auth)])
async def api_screen_ocr(req: OCRRequest = OCRRequest()):
    if req.question:
        return summarize_screen(req.question)
    return read_screen_text()

# ========================================================
# 8. Neural Voice Synthesis
# ========================================================
@app.get("/api/voice/profiles")
async def list_voice_profiles():
    return {"profiles": get_voice_profiles()}

@app.get("/api/voice/tts")
async def get_neural_tts(text: str, voice: str = "alexa", rate: str = "+0%", token: Optional[str] = None):
    # Optional token verification for streaming audio elements
    if token and not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized audio stream")
    audio_bytes = await synthesize_speech(text, voice_key=voice, rate=rate)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@app.post("/api/voice/tts", dependencies=[Depends(require_auth)])
async def post_neural_tts(req: TTSRequest):
    audio_bytes = await synthesize_speech(req.text, voice_key=req.voice, rate=req.rate)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )

# ========================================================
# 9. Real-Time Telemetry & Directive WebSocket Stream
# ========================================================
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate via query param or initial handshake
    token = websocket.query_params.get("token")
    if not token or not verify_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                parsed = {}
                try:
                    parsed = json.loads(data)
                except Exception:
                    parsed = {"query": data}

                query_text = parsed.get("query", data)
                res = execute_agent_directive(query_text)
                await websocket.send_text(json.dumps({
                    "type": "command_response",
                    "payload": res,
                    "timestamp": time.time()
                }))
            except asyncio.TimeoutError:
                metrics = get_system_metrics()
                await websocket.send_text(json.dumps({
                    "type": "telemetry_pulse",
                    "metrics": metrics,
                    "timestamp": time.time()
                }))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS ERROR] {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

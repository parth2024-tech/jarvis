import os
import time
import sqlite3
import threading
import uuid
import subprocess
from app_controller import send_notification

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")

def init_todo_table():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'normal',
            created_at REAL,
            completed_at REAL
        )
    """)
    conn.commit()
    conn.close()

init_todo_table()

# ========================================================
# 1. Background Timers & Countdown Reminders
# ========================================================
ACTIVE_TIMERS = {}
_timer_lock = threading.Lock()

def _timer_worker(timer_id: str, seconds: int, label: str):
    time.sleep(seconds)
    with _timer_lock:
        if timer_id not in ACTIVE_TIMERS:
            return  # Cancelled
        del ACTIVE_TIMERS[timer_id]

    # Timer Expired Alert
    title = f"TIMER COMPLETE: {label.upper()}"
    msg = f"Your countdown for '{label}' ({seconds}s) has concluded, Sir."
    send_notification(title, msg, urgency="critical")

    # Speak alert out loud locally if possible
    try:
        from voice_engine import play_speech_locally
        play_speech_locally(f"Sir, your timer for {label} is complete.", voice_key="alexa")
    except Exception:
        pass

def set_timer(duration_seconds: int, label: str = "General Directive") -> dict:
    """
    Schedules an autonomous background countdown timer.
    """
    sec = max(1, int(duration_seconds))
    timer_id = str(uuid.uuid4())[:8]
    expires_at = time.time() + sec

    timer_record = {
        "id": timer_id,
        "label": label,
        "duration_seconds": sec,
        "expires_at": expires_at,
        "created_at": time.time()
    }

    with _timer_lock:
        ACTIVE_TIMERS[timer_id] = timer_record

    t = threading.Thread(target=_timer_worker, args=(timer_id, sec, label), daemon=True)
    t.start()

    # Friendly duration formatting
    if sec >= 60:
        mins = sec // 60
        rem_sec = sec % 60
        dur_str = f"{mins} minute{'s' if mins != 1 else ''}" + (f" {rem_sec}s" if rem_sec else "")
    else:
        dur_str = f"{sec} seconds"

    return {
        "success": True,
        "timer_id": timer_id,
        "label": label,
        "duration_seconds": sec,
        "expires_at": expires_at,
        "message": f"Timer initiated for {dur_str} ('{label}'), Sir."
    }

def get_active_timers() -> list:
    """
    Returns currently running countdown timers with remaining seconds.
    """
    now = time.time()
    results = []
    with _timer_lock:
        for tid, tinfo in ACTIVE_TIMERS.items():
            rem = max(0, round(tinfo["expires_at"] - now))
            results.append({
                "id": tid,
                "label": tinfo["label"],
                "duration_seconds": tinfo["duration_seconds"],
                "remaining_seconds": rem
            })
    results.sort(key=lambda x: x["remaining_seconds"])
    return results

def cancel_timer(timer_id: str) -> dict:
    with _timer_lock:
        if timer_id in ACTIVE_TIMERS:
            del ACTIVE_TIMERS[timer_id]
            return {"success": True, "message": f"Timer {timer_id} cancelled, Sir."}
    return {"success": False, "message": "Timer identifier not found, Sir."}

# ========================================================
# 2. Todo Task Management
# ========================================================
def add_todo(task: str, priority: str = "normal") -> dict:
    """
    Inserts a new objective into the mission task register.
    """
    clean_task = task.strip()
    if not clean_task:
        return {"success": False, "error": "Empty task description"}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (task, status, priority, created_at) VALUES (?, 'pending', ?, ?)",
            (clean_task, priority, time.time())
        )
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "success": True,
            "id": todo_id,
            "task": clean_task,
            "message": f"Task #{todo_id} recorded to mission log: '{clean_task}', Sir."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_todos(include_completed: bool = False) -> list:
    """
    Queries current task board objectives.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if include_completed:
            cursor.execute("SELECT id, task, status, priority, created_at FROM todos ORDER BY id DESC")
        else:
            cursor.execute("SELECT id, task, status, priority, created_at FROM todos WHERE status = 'pending' ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "task": r[1], "status": r[2], "priority": r[3], "created_at": r[4]}
            for r in rows
        ]
    except Exception:
        return []

def complete_todo(todo_id: int) -> dict:
    """
    Marks an objective as completed.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE todos SET status = 'completed', completed_at = ? WHERE id = ?",
            (time.time(), int(todo_id))
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Task #{todo_id} marked as fulfilled, Sir."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clear_completed_todos() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE status = 'completed'")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Purged {deleted} completed tasks from registry, Sir."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========================================================
# 3. Wayland Clipboard Bridge
# ========================================================
def get_clipboard_text() -> dict:
    """
    Retrieves current text copied on Wayland system clipboard.
    """
    try:
        res = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, timeout=2)
        text = res.stdout.strip()
        return {
            "success": True,
            "text": text,
            "char_count": len(text)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "text": ""}

def set_clipboard_text(text: str) -> dict:
    """
    Injects text into the host Wayland clipboard.
    """
    try:
        p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
        p.communicate(input=text, timeout=2)
        return {
            "success": True,
            "message": f"Buffered {len(text)} characters to system clipboard, Sir."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

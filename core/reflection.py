import sqlite3
import os
import time

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")

def init_reflection_table():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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

init_reflection_table()

def record_reflection(task_name: str, trajectory: str, outcome: str, lessons_learned: str):
    """
    Stores execution trajectories and self-improving reflections in SQLite/LanceDB memory
    so J.A.R.V.I.S. can adapt to user workflows over time.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reflections (timestamp, task_name, trajectory, outcome, lessons_learned) VALUES (?, ?, ?, ?, ?)",
            (time.time(), task_name, trajectory, outcome, lessons_learned)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[REFLECTION ERROR] {e}")
        return False

def get_recent_reflections(limit: int = 5):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT task_name, lessons_learned FROM reflections ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"task": r[0], "lesson": r[1]} for r in rows]
    except Exception:
        return []

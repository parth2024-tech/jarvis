import sqlite3
import os
import time
import requests
import numpy as np

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

def init_memory_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            category TEXT,
            content TEXT,
            embedding BLOB
        )
    """)
    conn.commit()
    conn.close()

init_memory_tables()

def get_embedding(text: str) -> np.ndarray:
    """
    Retrieves dense vector embeddings using local Ollama nomic-embed-text model.
    """
    try:
        res = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=15
        )
        if res.status_code == 200:
            vec = res.json().get("embedding", [])
            if vec:
                arr = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                return arr
    except Exception as e:
        print(f"[EMBEDDING NOTICE] {e}")
    return None

def store_memory(content: str, category: str = "general") -> dict:
    """
    Indexes and stores a memory or directive with its semantic vector embedding.
    """
    if not content or not content.strip():
        return {"success": False, "error": "Empty memory content"}

    emb = get_embedding(content)
    emb_blob = emb.tobytes() if emb is not None else None

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO semantic_memories (timestamp, category, content, embedding) VALUES (?, ?, ?, ?)",
            (time.time(), category, content.strip(), emb_blob)
        )
        mem_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "success": True,
            "id": mem_id,
            "content": content,
            "category": category,
            "vector_indexed": emb is not None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def query_memories(query: str, top_k: int = 3, min_similarity: float = 0.40) -> list:
    """
    Performs semantic vector recall using cosine similarity over indexed memories.
    Falls back to keyword matching if vector service is unavailable.
    """
    q_emb = get_embedding(query)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, category, content, embedding FROM semantic_memories")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        scored = []
        for r_id, r_ts, r_cat, r_content, r_blob in rows:
            score = 0.0
            if q_emb is not None and r_blob is not None:
                doc_vec = np.frombuffer(r_blob, dtype=np.float32)
                score = float(np.dot(q_emb, doc_vec))
            else:
                q_words = set(query.lower().split())
                doc_words = set(r_content.lower().split())
                overlap = len(q_words.intersection(doc_words))
                score = overlap / max(len(q_words), 1)

            if score >= min_similarity:
                scored.append({
                    "id": r_id,
                    "score": round(score, 3),
                    "category": r_cat,
                    "content": r_content,
                    "timestamp": r_ts
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
    except Exception as e:
        print(f"[VECTOR MEMORY ERROR] {e}")
        return []

def get_relevant_context(query: str, top_k: int = 3) -> str:
    """
    Returns formatted memory context to enrich J.A.R.V.I.S. reasoning.
    """
    memories = query_memories(query, top_k=top_k)
    if not memories:
        return ""
    lines = ["[RECALLED MEMORIES & PROTOCOLS]"]
    for m in memories:
        lines.append(f"- ({m['category'].upper()}) {m['content']}")
    return "\n".join(lines)

# storage.py
import sqlite3
from datetime import datetime

DB_PATH = "era_experiments.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            problem   TEXT NOT NULL,
            model     TEXT NOT NULL,
            status    TEXT NOT NULL DEFAULT 'RUNNING',
            metric    TEXT,
            dataset_filename TEXT,
            dataset_preview TEXT,
            started_at TEXT NOT NULL
        )
    """)

    # Migrations for older databases
    try: c.execute("ALTER TABLE experiments ADD COLUMN status TEXT NOT NULL DEFAULT 'RUNNING'")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE experiments ADD COLUMN metric TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE experiments ADD COLUMN dataset_filename TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE experiments ADD COLUMN dataset_preview TEXT")
    except sqlite3.OperationalError: pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,
            parent_id     INTEGER,
            iteration     INTEGER NOT NULL,
            code          TEXT NOT NULL,
            score         REAL NOT NULL,
            stdout        TEXT,
            stderr        TEXT,
            exit_code     INTEGER,
            reasoning     TEXT,
            created_at    TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id)
        )
    """)

    # Migration for nodes
    try: c.execute("ALTER TABLE nodes ADD COLUMN reasoning TEXT")
    except sqlite3.OperationalError: pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id   INTEGER NOT NULL,
            node_id         INTEGER NOT NULL,
            problem_summary TEXT NOT NULL,
            algorithm_tags  TEXT NOT NULL,
            code_snippet    TEXT NOT NULL,
            score           REAL NOT NULL,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id),
            FOREIGN KEY (node_id) REFERENCES nodes(id)
        )
    """)

    conn.commit()
    conn.close()

def create_experiment(problem: str, model: str, metric: str = None, dataset_filename: str = None, dataset_preview: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO experiments (problem, model, started_at, status, metric, dataset_filename, dataset_preview) VALUES (?, ?, ?, 'RUNNING', ?, ?, ?)",
        (problem, model, datetime.utcnow().isoformat(), metric, dataset_filename, dataset_preview)
    )
    exp_id = c.lastrowid
    conn.commit()
    conn.close()
    return exp_id

def update_experiment_status(exp_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE experiments SET status = ? WHERE id = ?", (status, exp_id))
    conn.commit()
    conn.close()

def save_node(experiment_id, iteration, code, score, stdout, stderr, exit_code, parent_id=None, reasoning=None) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO nodes (experiment_id, parent_id, iteration, code, score, stdout, stderr, exit_code, reasoning, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (experiment_id, parent_id, iteration, code, score, stdout, stderr, exit_code, reasoning, datetime.utcnow().isoformat()))
    node_id = c.lastrowid
    conn.commit()
    conn.close()
    return node_id

def get_best_node(experiment_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE experiment_id = ? ORDER BY score DESC LIMIT 1", (experiment_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_experiment_history(experiment_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT iteration, score, exit_code, created_at FROM nodes WHERE experiment_id = ? ORDER BY iteration ASC", (experiment_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_experiment_tree(experiment_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, parent_id, iteration, score FROM nodes WHERE experiment_id = ? ORDER BY id ASC", (experiment_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_experiments() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, problem, status, started_at, metric, dataset_filename FROM experiments ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_experiment_details(exp_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_node_details(node_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_experiment(exp_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM nodes WHERE experiment_id = ?", (exp_id,))
    c.execute("DELETE FROM memory WHERE experiment_id = ?", (exp_id,))
    c.execute("DELETE FROM experiments WHERE id = ?", (exp_id,))
    conn.commit()
    conn.close()

def save_memory(experiment_id, node_id, problem_summary, algorithm_tags, code_snippet, score) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO memory (experiment_id, node_id, problem_summary, algorithm_tags, code_snippet, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (experiment_id, node_id, problem_summary, algorithm_tags, code_snippet, score, datetime.utcnow().isoformat()))
    mem_id = c.lastrowid
    conn.commit()
    conn.close()
    return mem_id

def retrieve_memory(query_tags: list[str], limit: int = 3) -> list[dict]:
    # FIX: If no tags are extracted, return empty list to avoid SQL syntax error
    if not query_tags:
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    conditions = " OR ".join(["algorithm_tags LIKE ?"] * len(query_tags))
    params = [f"%{tag}%" for tag in query_tags]
    params.append(limit)
    c.execute(f"""
        SELECT problem_summary, algorithm_tags, code_snippet, score FROM memory 
        WHERE {conditions} ORDER BY score DESC, created_at DESC LIMIT ?
    """, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]



def get_experiment_status(exp_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM experiments WHERE id = ?", (exp_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "UNKNOWN"
import os
import sqlite3
from pathlib import Path
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = str(BASE_DIR / "reddit_automation.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

def now_local():
    return datetime.now(pytz.timezone(TIMEZONE))

def get_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                subreddit TEXT NOT NULL,
                scheduled_time TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                reddit_post_id TEXT UNIQUE,
                score INTEGER DEFAULT 0,
                num_comments INTEGER DEFAULT 0,
                upvote_ratio REAL DEFAULT 0,
                last_synced_at TEXT,
                error_log TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

def log_event(level, message):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO system_logs(level, message, created_at) VALUES (?, ?, ?)",
                (level, str(message)[:2000], now_local().isoformat(timespec="seconds"))
            )
    except Exception:
        pass

def save_post(title, body, subreddit, scheduled_time=None, status="draft"):
    allowed = {"draft", "scheduled", "published", "failed", "needs_review"}
    if status not in allowed:
        raise ValueError(f"Unsupported initial status: {status}")
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO posts(title, body, subreddit, scheduled_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), body.strip(), subreddit.strip(), scheduled_time, status,
              now_local().isoformat(timespec="seconds")))
        return cur.lastrowid

def get_posts(status=None):
    with get_connection() as conn:
        if status and status != "All":
            return conn.execute("SELECT * FROM posts WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        return conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()

def claim_due_posts():
    """Atomically claim due posts. A crash during submission is sent to manual review on restart."""
    now_text = now_local().strftime("%Y-%m-%d %H:%M:%S")
    claimed = []
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("""
            SELECT * FROM posts
            WHERE status='scheduled' AND scheduled_time <= ?
            ORDER BY scheduled_time, id
        """, (now_text,)).fetchall()
        for row in rows:
            cur = conn.execute(
                "UPDATE posts SET status='publishing' WHERE id=? AND status='scheduled'",
                (row["id"],)
            )
            if cur.rowcount:
                claimed.append(dict(row))
    return claimed

def mark_published(post_id, reddit_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE posts SET status='published', reddit_post_id=?, error_log=NULL
            WHERE id=?
        """, (reddit_id, post_id))

def mark_status(post_id, status, error=None):
    with get_connection() as conn:
        conn.execute("UPDATE posts SET status=?, error_log=? WHERE id=?", (status, error, post_id))

def recover_interrupted_posts():
    with get_connection() as conn:
        conn.execute("""
            UPDATE posts SET status='needs_review',
            error_log='Worker stopped during publish attempt. Check Reddit manually before retrying.'
            WHERE status='publishing'
        """)

def update_metrics(reddit_id, score, num_comments, upvote_ratio):
    with get_connection() as conn:
        conn.execute("""
            UPDATE posts SET score=?, num_comments=?, upvote_ratio=?, last_synced_at=?
            WHERE reddit_post_id=?
        """, (score, num_comments, upvote_ratio,
              now_local().isoformat(timespec="seconds"), reddit_id))

def get_logs(limit=100):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()

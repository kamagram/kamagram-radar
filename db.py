import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "tenders.db")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            organization TEXT,
            deadline TEXT,
            link TEXT UNIQUE,
            source TEXT,
            sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_tender(t):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO tenders (title, organization, deadline, link, source)
            VALUES (?, ?, ?, ?, ?)
        """, (t["title"], t["org"], t["deadline"], t["link"], t["source"]))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_unsent():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, title, organization, deadline, link, source FROM tenders WHERE sent = 0")
    rows = c.fetchall()
    conn.close()
    return rows


def mark_sent(ids):
    if not ids:
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.executemany("UPDATE tenders SET sent = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()


def get_all_tenders():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM tenders ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

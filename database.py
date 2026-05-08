import sqlite3
import json
from datetime import datetime

DB_PATH = "pac.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_text TEXT NOT NULL,
            debit_account TEXT NOT NULL,
            credit_account TEXT NOT NULL,
            amount REAL NOT NULL,
            narration TEXT,
            rule_applied TEXT,
            entry_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_entry(entry: dict) -> int:
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO journal_entries
            (transaction_text, debit_account, credit_account, amount, narration, rule_applied, entry_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["transaction"],
        entry["debit"]["account"],
        entry["credit"]["account"],
        entry["amount"],
        entry.get("narration", ""),
        entry.get("rule_applied", ""),
        json.dumps(entry),
    ))
    conn.commit()
    entry_id = cursor.lastrowid
    conn.close()
    return entry_id


def get_recent_entries(limit: int = 10):
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, transaction_text, debit_account, credit_account, amount,
               narration, rule_applied, created_at
        FROM journal_entries
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_entry(entry_id: int) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def clear_all_entries():
    conn = get_connection()
    conn.execute("DELETE FROM journal_entries")
    conn.commit()
    conn.close()

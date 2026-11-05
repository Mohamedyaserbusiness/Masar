"""App-state store (SQLite; Postgres in production) + hash-chained audit log."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone

from .config import SQLITE_PATH

_lock = threading.Lock()
con = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
con.row_factory = sqlite3.Row
con.execute("PRAGMA journal_mode=WAL")
con.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, role TEXT, customer_id INTEGER,
  full_name TEXT, created_at TEXT, failed_attempts INTEGER DEFAULT 0, locked_until TEXT);
CREATE TABLE IF NOT EXISTS consents(user_id INTEGER, data_processing INTEGER, ai_assistant INTEGER, marketing INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS login_events(id INTEGER PRIMARY KEY, user_id INTEGER, email TEXT, ts TEXT, ip TEXT, user_agent TEXT,
  device_hash TEXT, success INTEGER, risk_score INTEGER, reasons TEXT);
CREATE TABLE IF NOT EXISTS known_devices(user_id INTEGER, device_hash TEXT, first_seen TEXT, PRIMARY KEY(user_id, device_hash));
CREATE TABLE IF NOT EXISTS risk_profiles(user_id INTEGER PRIMARY KEY, band INTEGER, answers TEXT, notes TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS live_transactions(id INTEGER PRIMARY KEY, ts TEXT, customer_id INTEGER, amount REAL, merchant TEXT,
  category TEXT, channel TEXT, governorate TEXT, risk_score INTEGER, flagged INTEGER);
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, customer_id INTEGER, risk_score INTEGER,
  title TEXT, reasons TEXT, payload TEXT, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, ts TEXT, actor TEXT, role TEXT, action TEXT, target TEXT,
  details TEXT, prev_hash TEXT, hash TEXT);
""")
con.commit()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def q(sql: str, args=()) -> list[dict]:
    with _lock:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def x(sql: str, args=()) -> int:
    with _lock:
        cur = con.execute(sql, args); con.commit()
        return cur.lastrowid


def audit(actor: str, role: str, action: str, target: str = "", details: dict | None = None) -> None:
    with _lock:
        row = con.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else "GENESIS"
        ts = now(); d = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(f"{prev}|{ts}|{actor}|{role}|{action}|{target}|{d}".encode()).hexdigest()
        con.execute("INSERT INTO audit_log(ts,actor,role,action,target,details,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?)",
                    (ts, actor, role, action, target, d, prev, h))
        con.commit()


def verify_audit_chain() -> dict:
    rows = q("SELECT * FROM audit_log ORDER BY id")
    prev = "GENESIS"
    for r in rows:
        h = hashlib.sha256(f"{prev}|{r['ts']}|{r['actor']}|{r['role']}|{r['action']}|{r['target']}|{r['details']}".encode()).hexdigest()
        if r["prev_hash"] != prev or r["hash"] != h:
            return {"intact": False, "broken_at": r["id"], "entries": len(rows)}
        prev = h
    return {"intact": True, "entries": len(rows), "head": prev[:16]}

"""Authentication (Argon2id + JWT in httpOnly cookie), RBAC, login-risk scoring."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request

from . import store
from .config import COOKIE_NAME, JWT_HOURS, JWT_SECRET

ph = PasswordHasher()
ROLES = {"customer", "advisor", "compliance", "admin"}


def hash_pw(p: str) -> str:
    return ph.hash(p)


def verify_pw(h: str, p: str) -> bool:
    try:
        return ph.verify(h, p)
    except VerifyMismatchError:
        return False


def password_issues(p: str) -> list[str]:
    issues = []
    if len(p) < 8: issues.append("at least 8 characters")
    if not re.search(r"[A-Z]", p): issues.append("an uppercase letter")
    if not re.search(r"[a-z]", p): issues.append("a lowercase letter")
    if not re.search(r"\d", p): issues.append("a digit")
    if p.lower() in {"password1", "12345678a", "qwerty123", "egypt2026"}: issues.append("not a common password")
    return issues


def make_token(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_HOURS)
    return jwt.encode({"sub": str(user["id"]), "role": user["role"], "cid": user["customer_id"], "exp": exp}, JWT_SECRET, algorithm="HS256")


def decode(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def current_user(request: Request) -> dict:
    tok = request.cookies.get(COOKIE_NAME)
    claims = decode(tok) if tok else None
    if not claims:
        raise HTTPException(401, "Not signed in")
    rows = store.q("SELECT id,email,role,customer_id,full_name FROM users WHERE id=?", (int(claims["sub"]),))
    if not rows:
        raise HTTPException(401, "Unknown user")
    return rows[0]


def require(*roles: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            store.audit(user["email"], user["role"], "ACCESS_DENIED", ",".join(roles))
            raise HTTPException(403, "Insufficient role")
        return user
    return dep


def csrf_guard(request: Request) -> None:
    """Cross-site forms cannot set custom headers; require one on state-changing calls."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.headers.get("x-requested-with") != "masar":
        raise HTTPException(403, "CSRF check failed")


# ---- simple per-IP rate limit for auth endpoints ----
_hits: dict[str, list[float]] = {}


def rate_limit(ip: str, limit: int = 20, window: int = 60) -> None:
    t = time.time()
    h = [x for x in _hits.get(ip, []) if t - x < window]
    h.append(t); _hits[ip] = h
    if len(h) > limit:
        raise HTTPException(429, "Too many attempts, slow down")


def login_risk(user_id: int, ip: str, ua: str) -> tuple[int, list[str], str]:
    dev = hashlib.sha256((ua or "").encode()).hexdigest()[:16]
    reasons, score = [], 0
    known = store.q("SELECT 1 FROM known_devices WHERE user_id=? AND device_hash=?", (user_id, dev))
    seen_any = store.q("SELECT 1 FROM known_devices WHERE user_id=? LIMIT 1", (user_id,))
    if seen_any and not known:
        score += 40; reasons.append("New device")
    hour = datetime.now().hour
    if 0 <= hour <= 5:
        score += 20; reasons.append(f"Unusual hour ({hour:02d}:00)")
    since = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    fails = store.q("SELECT COUNT(*) n FROM login_events WHERE user_id=? AND success=0 AND ts>?", (user_id, since))[0]["n"]
    if fails >= 3:
        score += 30; reasons.append(f"{fails} failed attempts in the last 15 min")
    last_ip = store.q("SELECT ip FROM login_events WHERE user_id=? AND success=1 ORDER BY id DESC LIMIT 1", (user_id,))
    if last_ip and last_ip[0]["ip"] != ip:
        score += 10; reasons.append("IP address changed")
    return min(score, 100), reasons, dev


def record_login(user: dict | None, email: str, ip: str, ua: str, success: bool) -> dict:
    uid = user["id"] if user else None
    score, reasons, dev = login_risk(uid, ip, ua) if uid else (0, [], "")
    store.x("INSERT INTO login_events(user_id,email,ts,ip,user_agent,device_hash,success,risk_score,reasons) VALUES(?,?,?,?,?,?,?,?,?)",
            (uid, email, store.now(), ip, (ua or "")[:200], dev, int(success), score, json.dumps(reasons)))
    if success and uid:
        store.x("INSERT OR IGNORE INTO known_devices VALUES(?,?,?)", (uid, dev, store.now()))
        if score >= 40:
            store.x("INSERT INTO alerts(ts,kind,customer_id,risk_score,title,reasons,payload) VALUES(?,?,?,?,?,?,?)",
                    (store.now(), "login", user["customer_id"], score, f"Risky sign-in for {email}", json.dumps(reasons), json.dumps({"ip": ip})))
    return {"risk_score": score, "reasons": reasons}

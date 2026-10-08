"""Create-account / log-in / log-out endpoints.

The session is a signed, HttpOnly cookie (Starlette SessionMiddleware) holding only the user id.
password_hash never leaves this module: no response, log line or agent tool returns it.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from backend.db import get_db, get_db_rw
from backend.security import (
    EMAIL_RE,
    hash_password,
    login_failures_by_account,
    login_failures_by_ip,
    normalize_email,
    password_problem,
    signups_by_ip,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_LOGIN_ERROR = "Incorrect email or password."
MAX_NAME = 50


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


def _user_out(row: sqlite3.Row) -> UserOut:
    # first_name/last_name are nullable (added by ALTER TABLE); fall back to the required name.
    first, _, last = (row["name"] or "").partition(" ")
    return UserOut(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        email=row["email"],
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _clean_name(value: str, label: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} is required.")
    if len(name) > MAX_NAME or any(ord(ch) < 32 for ch in name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} must be at most {MAX_NAME} characters.")
    return name


def _start_session(request: Request, user_id: int) -> None:
    request.session.clear()  # drop anything from before login (no session fixation)
    request.session["uid"] = user_id


def current_user_id(request: Request) -> int | None:
    uid = request.session.get("uid")
    return uid if isinstance(uid, int) else None


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, request: Request, conn: sqlite3.Connection = Depends(get_db_rw)) -> UserOut:
    ip = _client_ip(request)
    wait = signups_by_ip.retry_after(ip)
    if wait:
        raise HTTPException(429, "Too many new accounts from this network. Please try again later.",
                            headers={"Retry-After": str(wait)})

    first = _clean_name(body.first_name, "First name")
    last = _clean_name(body.last_name, "Last name")
    email = normalize_email(body.email)
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please enter a valid email address.")
    if body.confirm_password is not None and body.confirm_password != body.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords do not match.")
    problem = password_problem(body.password, email)
    if problem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)

    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Try logging in.")
    signups_by_ip.hit(ip)

    row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    _start_session(request, row["id"])
    return _user_out(row)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, conn: sqlite3.Connection = Depends(get_db_rw)) -> UserOut:
    email = normalize_email(body.email)
    ip = _client_ip(request)
    account_key = f"{ip}|{email}"
    wait = max(login_failures_by_account.retry_after(account_key), login_failures_by_ip.retry_after(ip))
    if wait:
        raise HTTPException(429, "Too many failed attempts. Please wait a few minutes and try again.",
                            headers={"Retry-After": str(wait)})

    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    ok, needs_rehash = verify_password(row["password_hash"] if row else None, body.password[:256])
    if not row or not ok:
        login_failures_by_account.hit(account_key)
        login_failures_by_ip.hit(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, GENERIC_LOGIN_ERROR)

    login_failures_by_account.reset(account_key)
    if needs_rehash:  # upgrade legacy or outdated hashes to current Argon2id settings
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["id"]))
        conn.commit()
    _start_session(request, row["id"])
    return _user_out(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> UserOut:
    uid = current_user_id(request)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
    if row is None:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return _user_out(row)

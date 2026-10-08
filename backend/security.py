"""Password hashing, password rules and login rate limiting.

Passwords are never stored or logged in plain text. New hashes use Argon2id (memory-hard, so
GPU/ASIC guessing is slow and expensive) with a random 16-byte salt per password. The hash string
carries its own parameters, e.g. $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2-cffi defaults follow RFC 9106's recommended profile: Argon2id, t=3, m=64 MiB, p=4.
_hasher = PasswordHasher()

# The 3 seeded accounts use an older 'pbkdf2_sha256$<salt>$<hex>' format that does not record its
# iteration count. If the course provides it, set LEGACY_PBKDF2_ITERATIONS so those users can log in;
# a successful legacy login is upgraded to Argon2id straight away.
LEGACY_ITERATIONS = int(os.environ.get("LEGACY_PBKDF2_ITERATIONS", "0") or 0)

MIN_PASSWORD = 8
MAX_PASSWORD = 128  # caps hashing work per request
COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyuiop", "iloveyou", "letmein1", "welcome1", "admin123", "abc12345",
    "football", "baseball", "sunshine", "princess", "11111111", "00000000", "yale1701",
    "bulldogs", "handsomedan", "boolaboola", "newhaven", "campuscustoms",
}
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


# Verifying against this when an email is unknown keeps login timing the same for real and fake
# accounts, so response time does not reveal which emails are registered.
_DUMMY_HASH = hash_password("timing-equalizer-not-a-real-password")


def verify_password(stored_hash: str | None, password: str) -> tuple[bool, bool]:
    """Return (matches, needs_rehash). Unknown or malformed hashes never match."""
    if not stored_hash:
        _safe_dummy_verify(password)
        return False, False
    if stored_hash.startswith("$argon2"):
        try:
            _hasher.verify(stored_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False, False
        return True, _hasher.check_needs_rehash(stored_hash)
    if stored_hash.startswith("pbkdf2_sha256$"):
        return _verify_legacy(stored_hash, password), True
    _safe_dummy_verify(password)
    return False, False


def _safe_dummy_verify(password: str) -> None:
    try:
        _hasher.verify(_DUMMY_HASH, password)
    except VerifyMismatchError:
        pass


def _verify_legacy(stored_hash: str, password: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) != 3 or not LEGACY_ITERATIONS:
        _safe_dummy_verify(password)
        return False
    _, salt, digest = parts
    computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), LEGACY_ITERATIONS).hex()
    return hmac.compare_digest(computed, digest)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def password_problem(password: str, email: str = "") -> str | None:
    """Return a shopper-friendly reason the password is too weak, or None if it is acceptable."""
    if len(password) < MIN_PASSWORD:
        return f"Password must be at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Password must be at most {MAX_PASSWORD} characters."
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS or len(set(lowered)) < 4:
        return "That password is too easy to guess. Try a longer phrase or mix in other words."
    local = email.split("@")[0].lower()
    if len(local) >= 4 and local in lowered:
        return "Password should not contain your email address."
    return None


class RateLimiter:
    """In-memory sliding-window limiter: at most `limit` events per key within `window` seconds."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        while events and now - events[0] > self.window:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until the key may try again (0 = allowed now)."""
        with self._lock:
            now = time.monotonic()
            events = self._prune(key, now)
            if len(events) < self.limit:
                return 0
            return max(1, int(self.window - (now - events[0])) + 1)

    def hit(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


# Failed logins: 5 per email+IP and 20 per IP in 15 minutes. Sign-ups: 10 per IP per hour.
login_failures_by_account = RateLimiter(limit=5, window=15 * 60)
login_failures_by_ip = RateLimiter(limit=20, window=15 * 60)
signups_by_ip = RateLimiter(limit=10, window=60 * 60)

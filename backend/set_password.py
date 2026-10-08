"""Admin tool: set a user's password (stored as an Argon2id hash).

Used to move the seed test user off its legacy pbkdf2 hash, whose iteration count is not recorded.
The password is read from stdin so it never appears in the command line or shell history.

Run from the HW4 folder:
    .venv/Scripts/python backend/set_password.py test@campuscustoms.yale.edu < password.txt
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import DB_PATH  # noqa: E402
from backend.security import hash_password, normalize_email, password_problem  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: set_password.py <email>   (password on stdin)")
    email = normalize_email(sys.argv[1])
    password = sys.stdin.readline().rstrip("\r\n")
    if not password:
        sys.exit("No password given on stdin.")
    problem = password_problem(password, email)
    if problem:
        # Admin resets may use course-provided test passwords; sign-up still enforces the rules.
        print(f"Note: this password would be rejected at sign-up ({problem})")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hash_password(password), email))
    conn.commit()
    if cur.rowcount != 1:
        sys.exit(f"No user with email {email}.")
    scheme = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()[0].rsplit("$", 2)[0]
    conn.close()
    print(f"Updated {email}: password_hash now {scheme}$… (salt and hash not shown)")


if __name__ == "__main__":
    main()

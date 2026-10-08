"""Startup checks for the local data pack.

1. The data pack must be in place: data/campus_customs.db and data/products/.
2. The course test account (test@campuscustoms.yale.edu, password "password", given in the assignment)
   ships with a legacy "pbkdf2_sha256$salt$hex" hash that does not record its iteration count, so it
   cannot be verified. On startup, if that account still has the legacy hash, it is re-hashed with
   Argon2id from the documented test password (an admin reset with known course credentials).
   Every other account is left untouched. Set RESET_COURSE_TEST_USER=0 in .env to skip this.
"""

from __future__ import annotations

import os
import sqlite3

from backend.db import DB_PATH, IMAGES_DIR
from backend.security import hash_password

COURSE_TEST_EMAIL = "test@campuscustoms.yale.edu"
COURSE_TEST_PASSWORD = "password"  # published in the assignment for this one test account


def check_data_pack() -> None:
    if not DB_PATH.exists() or not IMAGES_DIR.is_dir():
        raise SystemExit(
            "\nData pack missing. Put the course data pack in the HW4 folder as:\n"
            "  data/campus_customs.db\n  data/products/   (product images)\n"
            f"Looked for: {DB_PATH}\n"
        )


def reset_course_test_user() -> None:
    if os.environ.get("RESET_COURSE_TEST_USER", "1") != "1":
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (COURSE_TEST_EMAIL,)).fetchone()
        if row and row[0].startswith("pbkdf2_sha256$"):
            with conn:
                conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                             (hash_password(COURSE_TEST_PASSWORD), COURSE_TEST_EMAIL))
            print(f"Startup: re-hashed {COURSE_TEST_EMAIL} with Argon2id (legacy hash had no iteration count).")
    finally:
        conn.close()


def startup_checks() -> None:
    check_data_pack()
    reset_course_test_user()

"""Campus Customs backend package. Loads settings from .env before any module reads them.

HW4/.env comes first (SESSION_SECRET, optional overrides); the course folder's shared .env supplies
PORTKEY_API_KEY if HW4/.env does not. Neither file is committed.
"""

from pathlib import Path

from dotenv import load_dotenv

_HW4 = Path(__file__).resolve().parents[1]
load_dotenv(_HW4 / ".env")
load_dotenv(_HW4.parent.parent / ".env")  # AI Foundations yo/.env (does not override values already set)

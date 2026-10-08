"""Campus Customs API (run this file with Uvicorn).

- Problem 3: read-only product catalogue, stock by size and product images.
- Problem 4: create account / log in / log out (backend/auth.py).
- Problem 5: POST /api/chat, the PydanticAI shop agent (prompts/prompt.md, agent.py, tools.py, models.py).

Run from the backend/ folder (with the HW4 .venv active):
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import secrets
import sqlite3
import sys
from pathlib import Path

# Run either from backend/ (`uvicorn main:app --reload --port 8000`) or from HW4 (`uvicorn backend.main:app`):
# make the HW4 folder importable so `backend.*` modules resolve the same way in both cases.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from backend.agent import AgentUnavailable, run_chat
from backend.auth import current_user_id
from backend.auth import router as auth_router
from backend.catalogue import CATEGORIES, CATEGORY_BY_KEY, SIZE_ORDER, category_counts, list_summaries, product_detail
from backend.db import DB_PATH, IMAGES_DIR, get_db, read_only_connection, writable_connection
from backend.guardrails import redact
from backend.memory import load_for_widget, load_turns, save_turn
from backend.models import (
    CategoryCount, ChatRequest, ChatResponse, ProductDetail, ProductResults, ProductSummary, SavedMessage, ShopDeps,
)
from backend.security import RateLimiter
from backend.seed import startup_checks

__all__ = ["app", "DB_PATH", "SIZE_ORDER"]

log = logging.getLogger("campus_customs")

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    # Without a configured secret every restart signs out all shoppers; set SESSION_SECRET in .env.
    print("WARNING: SESSION_SECRET not set; using a random secret for this run.")
    SESSION_SECRET = secrets.token_urlsafe(32)

MAX_CARDS = 6
MAX_PAGE_RESULTS = 24  # cards sent for the page grid; total_matches still counts all
# Each chat turn costs model calls: 15 messages per minute per shopper (session or IP).
chat_limiter = RateLimiter(limit=15, window=60)

startup_checks()  # data pack present; course test account usable with the documented password

app = FastAPI(title="Campus Customs API", version="1.0.0")
# The browser reaches the API through the Vite proxy (same origin), so no CORS is configured.
# Session cookie: signed (tamper-proof), HttpOnly (no JavaScript access), SameSite=Lax (no cross-site POSTs).
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="cc_session",
    max_age=7 * 24 * 60 * 60,
    same_site="lax",
    https_only=os.environ.get("COOKIE_SECURE") == "1",
)
app.include_router(auth_router)


class ProductImages(StaticFiles):
    """StaticFiles that answers 404 (not 500) for file names Windows cannot stat (<>:"|?*, > 255 chars)."""

    def lookup_path(self, path: str):
        try:
            return super().lookup_path(path)
        except OSError:
            return "", None


# Serve only the product photos, never the whole data/ folder (it holds the database).
app.mount("/media/products", ProductImages(directory=IMAGES_DIR), name="product-images")


# --- Products ---


@app.get("/api/health")
def health(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    count = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count}


@app.get("/api/categories", response_model=list[CategoryCount])
def categories(conn: sqlite3.Connection = Depends(get_db)) -> list[CategoryCount]:
    return category_counts(conn)


@app.get("/api/products", response_model=list[ProductSummary])
def list_products(category: str | None = None, conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    key = (category or "").strip().lower()
    if key in ("", "all"):
        return list_summaries(conn)
    if key not in CATEGORY_BY_KEY:
        raise HTTPException(status_code=400, detail="Unknown category. Use one of: " + ", ".join(CATEGORIES))
    return list_summaries(conn, CATEGORY_BY_KEY[key])


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    detail = product_detail(conn, product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return detail


# --- Chat (Problem 5) ---


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """One message from the website's chat widget -> the agent's reply plus product cards."""
    user_id = current_user_id(request)
    limiter_key = f"user:{user_id}" if user_id else f"ip:{request.client.host if request.client else 'unknown'}"
    wait = chat_limiter.retry_after(limiter_key)
    if wait:
        raise HTTPException(429, "You're sending messages quickly. Please wait a moment.", headers={"Retry-After": str(wait)})
    chat_limiter.hit(limiter_key)

    deps = ShopDeps()
    history = body.history  # guests: the widget sends the conversation so far
    with read_only_connection() as conn:
        if user_id:
            # Who is chatting comes from the session + users table (never from the request body).
            row = conn.execute(
                "SELECT first_name, last_name, name, email, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row:
                first, _, last = (row["name"] or "").partition(" ")
                deps.user_id, deps.email, deps.member_since = user_id, row["email"], row["created_at"][:10]
                deps.first_name, deps.last_name = row["first_name"] or first, row["last_name"] or last
                history = load_turns(conn, user_id)  # logged in: memory comes from the database
        if body.current_product_id:
            page = product_detail(conn, body.current_product_id)
            if page:
                deps.current_product_id, deps.current_product_name = page["product_id"], page["name"]
                colors = f"comes only in {page['garment_color']}" if page["garment_color"] else "colors not listed"
                extra = f"; print/trim colors: {', '.join(page['design_colors'])}" if page["design_colors"] else ""
                deps.current_product_facts = (f"{page['category']} ({page['garment_type']}); {colors}{extra}; "
                                              f"description: {page['description'] or 'none written yet'}")

    # Problem 9 guardrail: strip card numbers / SSNs / passwords before the model, DB or audit see them.
    message, removed = redact(body.message.strip())
    if removed:
        message += ("\n\n[Note to assistant: the shopper's message contained sensitive details "
                    f"({', '.join(sorted(set(removed)))}) that were removed. Remind them not to share these in chat.]")

    try:
        reply = await run_chat(message, history, deps, user_id)
    except AgentUnavailable:
        raise HTTPException(503, "The shop assistant is offline right now. Please try again later.")
    except UsageLimitExceeded:
        raise HTTPException(503, "That question took too many steps. Could you ask it a simpler way?")
    except ModelHTTPError as exc:
        if "content_filter" not in str(exc.body):
            log.exception("chat failed")
            raise HTTPException(502, "Sorry, the shop assistant hit a problem. Please try again.")
        # The model provider's safety filter blocked the message (e.g. a jailbreak attempt): refuse politely.
        # The audit trail already has an 'error: ModelHTTPError ... content_filter' record for this turn.
        return ChatResponse(reply="Sorry, I can't help with that. I'm the Campus Customs shop assistant, so I can "
                                  "help you find Yale gear, check prices and sizes, or answer shop questions.")
    except Exception:
        log.exception("chat failed")
        raise HTTPException(502, "Sorry, the shop assistant hit a problem. Please try again.")

    # Product cards are rebuilt from the live database, so the page never shows a made-up price.
    cards: list[dict] = []
    with read_only_connection() as conn:
        by_id = {p["product_id"]: p for p in list_summaries(conn)}
    for pid in dict.fromkeys(i.strip().lower() for i in reply.product_ids):
        if pid in by_id and len(cards) < MAX_CARDS:
            cards.append(by_id[pid])

    # Problem 7: if the agent searched for a type of item, send every match for the page's results grid.
    results = None
    if deps.search_ids and reply.results_title:
        matches = [by_id[i] for i in deps.search_ids if i in by_id]
        results = ProductResults(title=reply.results_title, query=deps.search_query or "",
                                 total_matches=len(matches), products=matches[:MAX_PAGE_RESULTS])
    if deps.user_id:  # Problem 8: remember this exchange for the shopper's next visit
        with writable_connection() as conn:
            save_turn(conn, deps.user_id, redact(body.message.strip())[0], reply.reply,
                      [c["product_id"] for c in cards])
    return ChatResponse(reply=reply.reply, products=cards, results=results)


@app.get("/api/chat/history", response_model=list[SavedMessage])
def chat_history(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    """The logged-in shopper's saved chat (last 50 messages), so the widget can reload it."""
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(401, "Log in to see your saved chats.")
    return load_for_widget(conn, user_id)

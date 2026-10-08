"""Customer memory (Problem 8): logged-in shoppers' chats are saved in the chat_messages table.

chat_messages(id, user_id -> users.id, role 'user'|'assistant', content, products_json, created_at)
- One user row + one assistant row per turn, written after the agent replies.
- products_json stores only the product ids shown with the reply; cards are rebuilt from the live
  catalogue when history is loaded, so old prices or stock are never shown.
- History is always read by the session's user id, so a shopper only ever sees their own chats.
"""

from __future__ import annotations

import json
import sqlite3

from backend.catalogue import list_summaries
from backend.models import ChatTurn

HISTORY_FOR_AGENT = 20  # turns replayed to the model
HISTORY_FOR_WIDGET = 50  # messages shown when the shopper returns


def _product_ids(products_json: str | None) -> list[str]:
    if not products_json:
        return []
    try:
        items = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    # Older rows stored whole product objects; new rows store {"product_id": ...} only.
    return [i["product_id"] for i in items if isinstance(i, dict) and "product_id" in i]


def load_turns(conn: sqlite3.Connection, user_id: int, limit: int = HISTORY_FOR_AGENT) -> list[ChatTurn]:
    """Most recent turns for the agent, oldest first."""
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
    ).fetchall()
    return [ChatTurn(role=r["role"], content=r["content"][:4000]) for r in reversed(rows) if r["role"] in ("user", "assistant")]


def load_for_widget(conn: sqlite3.Connection, user_id: int, limit: int = HISTORY_FOR_WIDGET) -> list[dict]:
    """Saved messages for the chat widget, with product cards rebuilt from the live catalogue."""
    rows = conn.execute(
        "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    by_id = {p["product_id"]: p for p in list_summaries(conn)}
    messages = []
    for r in reversed(rows):
        cards = [by_id[i] for i in _product_ids(r["products_json"]) if i in by_id][:6]
        messages.append({"role": r["role"], "content": r["content"], "products": cards, "created_at": r["created_at"]})
    return messages


def save_turn(conn: sqlite3.Connection, user_id: int, message: str, reply: str, product_ids: list[str]) -> None:
    """Store one exchange (user message + assistant reply) in a single transaction."""
    with conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, json.dumps([{"product_id": pid} for pid in product_ids])),
        )


def count_messages(conn: sqlite3.Connection, user_id: int) -> int:
    return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]

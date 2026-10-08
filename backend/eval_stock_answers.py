"""Problem 6 check: the agent answers description / price / stock-by-size questions from the database.

Sends real questions to POST /api/chat (live model), then compares every $price and stock number in
each reply with campus_customs.db, and checks that sold-out sizes are called out.
Run from the HW4 folder:
    .venv/Scripts/python backend/eval_stock_answers.py
Writes output/screenshots/problem6/stock_answers.json
"""

from __future__ import annotations

import json
import sqlite3
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*httpx.*")
HW4 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HW4))

from fastapi.testclient import TestClient  # noqa: E402

from backend.agent import AUDIT_PATH, _stated_prices, _stated_quantities  # noqa: E402
from backend.main import app  # noqa: E402

OUT = HW4 / "output" / "screenshots" / "problem6" / "stock_answers.json"
db = sqlite3.connect(f"file:{(HW4 / 'data' / 'campus_customs.db').as_posix()}?mode=ro", uri=True)


def stock(pid: str) -> dict[str, int]:
    return dict(db.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (pid,)).fetchall())


def price(pid: str) -> float:
    return db.execute("SELECT price FROM catalogue WHERE product_id = ?", (pid,)).fetchone()[0]


# (question, product page open or None, product it is about, size asked or None)
CASES = [
    ("Tell me about this hoodie. What's it like and how much is it?", "basic-hoodie-big-yale", "basic-hoodie-big-yale", None),
    ("How many do you have left in medium?", "basic-hoodie-big-yale", "basic-hoodie-big-yale", "M"),
    ("Is the Tri-Blend Sports Hockey T-Shirt available in a large?", None, "tri-blend-sports-hockey-t-shirt", "L"),
    ("How many Champion Reverse Weave Hoodies are left in XL?", None, "champion-reverse-weave-hoodie-1", "XL"),
    ("What does the Saybrook College Crewneck cost, and is XXL in stock?", None, "saybrook-college-crewneck", "XXL"),
]

client = TestClient(app).__enter__()  # one event loop for all requests, like the real server
history: list[dict] = []
results = []
for question, page, pid, size in CASES:
    audit_before = len(json.loads(AUDIT_PATH.read_text(encoding="utf-8"))) if AUDIT_PATH.exists() else 0
    r = client.post("/api/chat", json={"message": question, "history": history, "current_product_id": page})
    body = r.json()
    reply = body.get("reply") or body.get("detail", "")
    new_rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))[audit_before:] if r.status_code == 200 else []
    audit = {"tool_calls": [c for row in new_rows for c in row["tool_calls"]]}
    sizes = stock(pid)
    known_prices = {price(pid)}
    stated_p, stated_q = _stated_prices(reply), _stated_quantities(reply)
    checks = {
        "http_ok": r.status_code == 200,
        "used_db_tools": bool(audit.get("tool_calls")),
        "prices_match_db": stated_p <= known_prices,
        "quantities_match_db": stated_q <= set(sizes.values()) | {sum(sizes.values())},
    }
    if size:
        if sizes[size] == 0:
            checks["sold_out_said_clearly"] = "sold out" in reply.lower() or "out of stock" in reply.lower()
        else:
            checks["exact_quantity_given"] = str(sizes[size]) in reply
    results.append({
        "question": question, "page": page, "reply": reply,
        "tools_called": [f"{c['tool']}({', '.join(f'{k}={v}' for k, v in c['args'].items())})" for c in audit.get("tool_calls", [])],
        "db_truth": {"price": price(pid), "stock": sizes, "size_asked": size},
        "checks": checks, "pass": all(checks.values()),
    })
    history += [{"role": "user", "content": question}, {"role": "assistant", "content": reply}]
    print(("PASS " if results[-1]["pass"] else "FAIL ") + question, "->", reply[:140].replace("\n", " "))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"passed": sum(r["pass"] for r in results), "total": len(results), "results": results},
                          indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{sum(r['pass'] for r in results)}/{len(results)} passed -> {OUT.relative_to(HW4)}")

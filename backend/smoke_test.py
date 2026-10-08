"""Smoke test: the API must report exactly what the database holds.

Run from the HW4 folder:
    .venv/Scripts/python backend/smoke_test.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*httpx.*")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import DB_PATH, SIZE_ORDER, app  # noqa: E402

client = TestClient(app)
db = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
failures: list[str] = []


def check(ok: bool, message: str) -> None:
    if not ok:
        failures.append(message)


products = client.get("/api/products").json()
check(len(products) == 102, f"expected 102 products, got {len(products)}")
check(sum(c["count"] for c in client.get("/api/categories").json()) == 102, "category counts do not sum to 102")

for card in products:
    pid = card["product_id"]
    row = db.execute("SELECT * FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
    stock = {r["size"]: r["quantity"] for r in db.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (pid,))}
    detail = client.get(f"/api/products/{pid}").json()
    colors = json.loads(row["colors"])

    check(card["price"] == row["price"] == detail["price"], f"{pid}: price mismatch")
    check(card["image_url"] == f"/media/{row['image_file_path']}", f"{pid}: image path mismatch")
    check(client.get(card["image_url"]).status_code == 200, f"{pid}: image not served")
    check([s["size"] for s in detail["inventory"]] == SIZE_ORDER, f"{pid}: sizes not XS..XXL")
    check({s["size"]: s["quantity"] for s in detail["inventory"]} == stock, f"{pid}: stock mismatch")
    check(card["total_stock"] == sum(stock.values()), f"{pid}: total stock mismatch")
    check(card["sizes_in_stock"] == [s for s in SIZE_ORDER if stock[s] > 0], f"{pid}: sizes_in_stock mismatch")
    check(detail["garment_color"] == (colors[0] if colors else None), f"{pid}: garment color mismatch")
    check(detail["design_colors"] == colors[1:], f"{pid}: design colors mismatch")
    if "filename-based stub" in row["description"]:
        check(detail["description"] is None, f"{pid}: placeholder description leaked")
    else:
        check(detail["description"] == row["description"], f"{pid}: description mismatch")

# Safety: the database file must never be reachable through the image route.
for path in ["/media/campus_customs.db", "/media/products/../campus_customs.db",
             "/media/products/%2e%2e/campus_customs.db", "/media/products/..%2fcampus_customs.db"]:
    check(client.get(path).status_code == 404, f"{path} should be 404")
check(client.get("/api/products/does-not-exist").status_code == 404, "unknown product should be 404")
check(client.get("/api/products?category=Nope").status_code == 400, "unknown category should be 400")

print(f"checked {len(products)} products against the database: {len(failures)} failures")
for f in failures:
    print("FAIL", f)
sys.exit(1 if failures else 0)

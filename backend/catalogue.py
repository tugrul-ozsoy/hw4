"""Catalogue helpers shared by the API routes (main.py) and the agent's tools (tools.py).

Everything here reads the live database; nothing is cached, so prices and stock are always current.
"""

from __future__ import annotations

import json
import re
import sqlite3

from backend.models import CategoryCount, SizeStock

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK_MAX = 5  # 1-5 units left counts as low stock
STUB_MARKER = "filename-based stub"  # 3 catalogue rows have a placeholder description

# garment_type has 22 spellings; map them to the 6 shop categories (first match wins).
CATEGORY_RULES = [
    ("Quarter-Zips", ("quarter-zip",)),
    ("Hoodies", ("hood",)),
    ("Jackets & Fleece", ("jacket", "fleece")),
    ("Long Sleeve", ("long-sleeve",)),
    ("T-Shirts", ("t-shirt",)),
    ("Crewnecks", ("crewneck", "mockneck", "sweatshirt")),
]
CATEGORIES = ["T-Shirts", "Crewnecks", "Hoodies", "Quarter-Zips", "Jackets & Fleece", "Long Sleeve"]  # display order
CATEGORY_BY_KEY = {c.lower(): c for c in CATEGORIES}

# Names are generated from file slugs ("School Of Art 1 4 Zip"); tidy them for display.
NAME_FIXES = [
    (r"\b1 4 Zip\b", "1/4 Zip"),
    (r"\bT Shirt\b", "T-Shirt"),
    (r"\bTri Blend\b", "Tri-Blend"),
    (r"\bFull Zip\b", "Full-Zip"),
    (r"\bL S 2 0\b", "L/S 2.0"),
    (r"^Ua\b", "UA"),
    (r"\bMens\b", "Men's"),
    (r"\bVit\b", "VIT"),
    (r"\bCreqneck\b", "Crewneck"),
    (r"\bTrack Field\b", "Track & Field"),
    (r"\bTrack And Field\b", "Track & Field"),
    (r"\bVs\b", "vs."),
    (r"(?<=\w )Of\b", "of"),
    (r"(?<=\w )And\b", "and"),
    (r" 1$", ""),
]
# Two catalogue names contradict their own photo, garment_type and price; fix the display name only.
NAME_OVERRIDES = {
    "school-of-architecture-crewneck": "School of Architecture 1/4 Zip",
    "squash-left-chest-tennis": "Squash Left Chest Crewneck",
}
# Words that read badly at the end of a shortened card description.
DANGLING_WORDS = {"a", "an", "the", "and", "or", "of", "with", "on", "in", "to", "featuring", "across", "above"}


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for name, keys in CATEGORY_RULES:
        if any(k in g for k in keys):
            return name
    return "Other"


def display_name(raw: str, product_id: str | None = None) -> str:
    if product_id in NAME_OVERRIDES:
        return NAME_OVERRIDES[product_id]
    name = raw
    for pattern, repl in NAME_FIXES:
        name = re.sub(pattern, repl, name)
    return name


def clean_description(text: str) -> str | None:
    return None if STUB_MARKER in text else text


def short_description(text: str | None, limit: int = 110, slack: int = 15) -> str | None:
    if not text:
        return None
    # First sentence only; "EST. 1701" is not a sentence end, so require lowercase + period + capital.
    first = re.split(r"(?<=[a-z]\.)\s+(?=[A-Z])", text, maxsplit=1)[0]
    if len(first) <= limit + slack:
        return first
    words = first[:limit].rsplit(" ", 1)[0].split()
    while words and words[-1].lower().strip(",;") in DANGLING_WORDS:
        words.pop()
    return " ".join(words).rstrip(",;") + "…"


def stock_status(quantity: int) -> str:
    if quantity == 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_MAX else "in_stock"


def load_inventory(conn: sqlite3.Connection, product_id: str | None = None) -> dict[str, list[SizeStock]]:
    sql = "SELECT product_id, size, quantity FROM inventory"
    rows = conn.execute(sql + " WHERE product_id = ?", (product_id,)) if product_id else conn.execute(sql)
    stock: dict[str, list[SizeStock]] = {}
    for r in rows:
        stock.setdefault(r["product_id"], []).append(
            SizeStock(size=r["size"], quantity=r["quantity"], status=stock_status(r["quantity"]))
        )
    for sizes in stock.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))
    return stock


def to_summary(row: sqlite3.Row, sizes: list[SizeStock]) -> dict:
    description = clean_description(row["description"])
    return {
        "product_id": row["product_id"],
        "name": display_name(row["name"], row["product_id"]),
        "category": category_for(row["garment_type"]),
        "garment_type": row["garment_type"],
        "price": row["price"],
        "short_description": short_description(description),
        "image_url": f"/media/{row['image_file_path']}",
        "total_stock": sum(s.quantity for s in sizes),
        "sizes_in_stock": [s.size for s in sizes if s.quantity > 0],
    }


def category_counts(conn: sqlite3.Connection) -> list[CategoryCount]:
    counts = {name: 0 for name in CATEGORIES}
    for (garment_type,) in conn.execute("SELECT garment_type FROM catalogue"):
        cat = category_for(garment_type)
        counts[cat] = counts.get(cat, 0) + 1
    return [CategoryCount(name=n, count=c) for n, c in counts.items()]


def list_summaries(conn: sqlite3.Connection, category: str | None = None) -> list[dict]:
    """Product cards sorted by display name, optionally filtered to one shop category."""
    stock = load_inventory(conn)
    rows = conn.execute("SELECT * FROM catalogue").fetchall()
    products = sorted(
        (to_summary(r, stock.get(r["product_id"], [])) for r in rows), key=lambda p: p["name"].casefold()
    )
    if category:
        products = [p for p in products if p["category"] == category]
    return products


def product_detail(conn: sqlite3.Connection, product_id: str) -> dict | None:
    """Full product record with stock per size, or None if the id is unknown."""
    product_id = product_id.strip().lower()
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return None
    sizes = load_inventory(conn, product_id).get(product_id, [])
    colors = json.loads(row["colors"])
    return {
        **to_summary(row, sizes),
        "description": clean_description(row["description"]),
        "garment_color": colors[0] if colors else None,
        "design_colors": colors[1:],
        "search_tags": json.loads(row["search_tags"]),
        "inventory": sizes,
    }

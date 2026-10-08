"""Problem 2: profile data/campus_customs.db (read-only).

Run from the HW4 folder:
    python db_analysis/analyze_db.py

Writes db_analysis/db_profile.json (every number below is computed, not typed).
Password hashes are never printed: only their structure is described.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path

HW4 = Path(__file__).resolve().parents[1]
DB_PATH = HW4 / "data" / "campus_customs.db"
DATA_DIR = HW4 / "data"
OUT = Path(__file__).resolve().parent / "db_profile.json"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SHOPPER_KEYWORDS = [
    "hoodie", "crewneck", "t-shirt", "quarter-zip", "1/4 zip", "fleece", "jacket",
    "long sleeve", "bulldog", "handsome dan", "champion", "brooks brothers",
    "hockey", "football", "crew", "sailing", "harvard", "law school", "medicine",
    "pink", "red", "shorts", "pants", "hat", "mug", "women", "kids", "youth",
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def q(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def column_profile(conn, table: str, mask: set[str] = frozenset()) -> list[dict]:
    cols = q(conn, f"PRAGMA table_info({table})")
    out = []
    for c in cols:
        name = c["name"]
        stats = conn.execute(
            f"SELECT COUNT(DISTINCT {name}), "
            f"SUM({name} IS NULL), SUM(TRIM(CAST({name} AS TEXT)) = '') FROM {table}"
        ).fetchone()
        examples = [r[0] for r in conn.execute(
            f"SELECT DISTINCT {name} FROM {table} WHERE {name} IS NOT NULL LIMIT 3")]
        if name in mask:
            examples = ["<masked>"]
        else:
            examples = [str(e)[:120] for e in examples]
        out.append({
            "name": name,
            "declared_type": c["type"],
            "not_null": bool(c["notnull"]),
            "primary_key": bool(c["pk"]),
            "default": c["dflt_value"],
            "distinct": stats[0],
            "nulls": stats[1] or 0,
            "empty_strings": stats[2] or 0,
            "examples": examples,
        })
    return out


def profile_catalogue(conn) -> dict:
    rows = q(conn, "SELECT * FROM catalogue")
    colors, tags, bad_json, empty_colors = Counter(), Counter(), [], []
    for r in rows:
        for field, counter in (("colors", colors), ("search_tags", tags)):
            try:
                vals = json.loads(r[field])
            except json.JSONDecodeError:
                bad_json.append((r["product_id"], field))
                continue
            counter.update(v.lower() for v in vals)
            if field == "colors" and not vals:
                empty_colors.append(r["product_id"])

    images = {f"products/{f}" for f in os.listdir(DATA_DIR / "products")}
    paths = [r["image_file_path"] for r in rows]

    def hits(kw: str) -> int:
        pattern = re.compile(rf"\b{re.escape(kw.lower())}\b")
        return sum(
            bool(pattern.search(" ".join(str(r[k]) for k in ("name", "garment_type", "description", "colors", "search_tags")).lower()))
            for r in rows
        )

    return {
        "row_count": len(rows),
        "columns": column_profile(conn, "catalogue"),
        "garment_type_counts": dict(Counter(r["garment_type"] for r in rows).most_common()),
        "garment_type_case_insensitive_distinct": len({r["garment_type"].lower() for r in rows}),
        "price_levels": dict(sorted(Counter(r["price"] for r in rows).items())),
        "price_min_max_avg": [min(r["price"] for r in rows), max(r["price"] for r in rows),
                              round(sum(r["price"] for r in rows) / len(rows), 2)],
        "color_vocabulary": dict(colors.most_common()),
        "search_tag_distinct": len(tags),
        "top_search_tags": dict(tags.most_common(20)),
        "json_parse_failures": bad_json,
        "products_with_empty_colors": empty_colors,
        "stub_descriptions": [r["product_id"] for r in rows if "stub" in r["description"].lower()],
        "product_id_equals_slug_of_image": sum(
            r["image_file_path"] == f"products/{r['product_id']}.jpg" for r in rows),
        "images_missing_on_disk": sorted(set(paths) - images),
        "images_not_in_catalogue": sorted(images - set(paths)),
        "names_with_digits": [r["name"] for r in rows if any(ch.isdigit() for ch in r["name"])],
        "shopper_keyword_hits": {kw: hits(kw) for kw in SHOPPER_KEYWORDS},
        "base_color_counts (colors[0])": dict(Counter(
            json.loads(r["colors"])[0] for r in rows if json.loads(r["colors"])).most_common()),
        "garment_types_with_more_than_one_price": [
            g for g in {r["garment_type"] for r in rows}
            if len({r2["price"] for r2 in rows if r2["garment_type"] == g}) > 1],
    }


def profile_inventory(conn) -> dict:
    totals = q(conn, "SELECT product_id, SUM(quantity) AS total, SUM(quantity = 0) AS sold_out_sizes "
                     "FROM inventory GROUP BY product_id")
    return {
        "row_count": conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0],
        "columns": column_profile(conn, "inventory"),
        "size_counts": {r["size"]: r["n"] for r in q(conn, "SELECT size, COUNT(*) n FROM inventory GROUP BY size")},
        "size_display_order": SIZE_ORDER,
        "products_with_all_6_sizes": sum(
            1 for r in q(conn, "SELECT COUNT(*) n FROM inventory GROUP BY product_id") if r["n"] == 6),
        "quantity_value_counts": {r["quantity"]: r["n"] for r in
                                  q(conn, "SELECT quantity, COUNT(*) n FROM inventory GROUP BY quantity")},
        "zero_quantity_rows": conn.execute("SELECT COUNT(*) FROM inventory WHERE quantity = 0").fetchone()[0],
        "total_units": conn.execute("SELECT SUM(quantity) FROM inventory").fetchone()[0],
        "per_product_total_min_max": [min(t["total"] for t in totals), max(t["total"] for t in totals)],
        "products_fully_sold_out": [t["product_id"] for t in totals if t["total"] == 0],
        "products_by_sold_out_sizes": dict(sorted(Counter(t["sold_out_sizes"] for t in totals).items())),
        "most_sold_out": sorted(totals, key=lambda t: (-t["sold_out_sizes"], t["total"]))[:5],
        "sold_out_by_size": {r["size"]: r["n"] for r in
                             q(conn, "SELECT size, SUM(quantity = 0) n FROM inventory GROUP BY size")},
        "low_stock_rows_1_to_5": conn.execute(
            "SELECT COUNT(*) FROM inventory WHERE quantity BETWEEN 1 AND 5").fetchone()[0],
        "products_with_gaps_between_in_stock_sizes": products_with_size_gaps(conn),
    }


def products_with_size_gaps(conn) -> int:
    """Products where a sold-out size sits between two in-stock sizes (e.g. S, L in stock but M is 0)."""
    stock = {}
    for r in q(conn, "SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    gaps = 0
    for sizes in stock.values():
        flags = [sizes[s] > 0 for s in SIZE_ORDER]
        first, last = flags.index(True), len(flags) - 1 - flags[::-1].index(True)
        gaps += not all(flags[first:last + 1])
    return gaps


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[0]}***@{domain}"


def profile_users(conn) -> dict:
    rows = q(conn, "SELECT * FROM users")
    hash_shapes = []
    for r in rows:
        parts = r["password_hash"].split("$")
        hash_shapes.append({
            "user_id": r["id"],
            "segments": len(parts),
            "algorithm_label": parts[0],
            "salt_length": len(parts[1]) if len(parts) > 1 else None,
            "digest_length_hex": len(parts[-1]),
            "digest_is_hex": all(ch in "0123456789abcdef" for ch in parts[-1]),
        })
    return {
        "row_count": len(rows),
        "columns": column_profile(conn, "users", mask={"password_hash", "email"}),
        "accounts": [{"id": r["id"], "name": r["name"], "email": mask_email(r["email"]),
                      "created_at": r["created_at"],
                      "name_matches_first_last": r["name"] == f"{r['first_name']} {r['last_name']}"}
                     for r in rows],
        "password_hash_structure": hash_shapes,
        "create_sql": conn.execute("SELECT sql FROM sqlite_master WHERE name = 'users'").fetchone()[0],
    }


def profile_chat(conn) -> dict:
    rows = q(conn, "SELECT * FROM chat_messages ORDER BY id")
    keys, drift = Counter(), []
    cat = {r["product_id"]: r for r in q(conn, "SELECT product_id, price FROM catalogue")}
    inv = {(r["product_id"], r["size"]): r["quantity"] for r in q(conn, "SELECT * FROM inventory")}
    for r in rows:
        for p in json.loads(r["products_json"] or "[]"):
            keys.update(p.keys())
            if p["price"] != cat[p["product_id"]]["price"]:
                drift.append((r["id"], p["product_id"], "price"))
            for s in p.get("inventory", []):
                if s["quantity"] != inv[(p["product_id"], s["size"])]:
                    drift.append((r["id"], p["product_id"], s["size"]))
    return {
        "row_count": len(rows),
        "columns": column_profile(conn, "chat_messages"),
        "messages_per_user": {r["user_id"]: r["n"] for r in
                              q(conn, "SELECT user_id, COUNT(*) n FROM chat_messages GROUP BY user_id")},
        "role_counts": dict(Counter(r["role"] for r in rows)),
        "assistant_rows_with_products": sum(1 for r in rows if r["role"] == "assistant" and r["products_json"]
                                            and json.loads(r["products_json"])),
        "product_object_keys": dict(keys),
        "snapshot_vs_current_drift": drift,
        "rows_with_U+FFFD": sum("�" in r["content"] for r in rows),
    }


def profile_integrity(conn) -> dict:
    return {
        "sqlite_master": q(conn, "SELECT type, name, tbl_name FROM sqlite_master ORDER BY type, name"),
        "row_counts": {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                       for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")},
        "sqlite_sequence": q(conn, "SELECT * FROM sqlite_sequence"),
        "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_key_violations": q(conn, "PRAGMA foreign_key_check"),
        "foreign_keys_enforced_by_default": bool(conn.execute("PRAGMA foreign_keys").fetchone()[0]),
        "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
        "file_size_bytes": DB_PATH.stat().st_size,
    }


def main() -> None:
    conn = connect()
    profile = {
        "database": "data/campus_customs.db",
        "catalogue": profile_catalogue(conn),
        "inventory": profile_inventory(conn),
        "users": profile_users(conn),
        "chat_messages": profile_chat(conn),
        "integrity": profile_integrity(conn),
    }
    OUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    c, i, u = profile["catalogue"], profile["inventory"], profile["users"]
    print(f"catalogue {c['row_count']} rows | inventory {i['row_count']} rows "
          f"({i['zero_quantity_rows']} sold-out size rows) | users {u['row_count']} | "
          f"chat_messages {profile['chat_messages']['row_count']}")
    print(f"wrote {OUT.relative_to(HW4)}")


if __name__ == "__main__":
    main()

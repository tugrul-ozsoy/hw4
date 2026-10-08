# Campus Customs DB: data dictionary

Source: `data/campus_customs.db` (SQLite, 172 KB, opened read-only).
The numbers come from `db_analysis/analyze_db.py`, which writes `db_profile.json`. A multi-agent check re-ran the queries to confirm them.

| Table | Rows | One row = |
|---|---|---|
| `catalogue` | 102 | one product (style) |
| `inventory` | 612 | one product × size (6 sizes × 102 products) |
| `users` | 3 | one shopper account |
| `chat_messages` | 22 | one chat turn (user or assistant). This table is not mentioned in the brief |
| `sqlite_sequence` | 3 | AUTOINCREMENT counters: inventory 612, users 3, chat 22 |

Relationships: `inventory.product_id → catalogue.product_id` and `chat_messages.user_id → users.id`.
Foreign keys are declared but not enforced, because `PRAGMA foreign_keys` defaults to 0. Integrity check: ok, with 0 orphan rows.

## catalogue

| Field | Type | Meaning | Notes |
|---|---|---|---|
| `product_id` | TEXT PK | Stable key: a lowercase slug of the image filename | `image_file_path = products/<product_id>.jpg` for 102/102. Some slugs are irregular (`yale-sports-creqneck-field-hockey`, `champion-reverse-weave-hoodie-1`) |
| `name` | TEXT | Display name | Generated from the slug (title-case words), so names read badly: "1 4 Zip", "Ua Mens Tech L S 2 0", "Hoodie 1". The front end needs a display cleaner |
| `garment_type` | TEXT | Garment category written by a vision model | 22 spellings (21 ignoring case), e.g. `short-sleeve T-shirt` vs `t-shirt`. Collapses to 7 groups: tee 25, crewneck 28, hoodie 27, quarter-zip 11, jacket/fleece 8, long-sleeve 2, mockneck 1 |
| `description` | TEXT | 1–2 sentence description of the photo | 3 are stubs ("Vision blocked; filename-based stub"): `benjamin-franklin-t-shirt`, `berkeley-sweater-fleece-jacket`, `timothy-dwight-college-crewneck` |
| `colors` | TEXT (JSON array) | `colors[0]` = garment color; the rest = print, crest or trim colors | This is not a list of colors you can buy: every product comes in one colorway. "navy" and "navy blue" are both used. The 3 stubs store `[]` |
| `search_tags` | TEXT (JSON array) | Keyword tags (brand, school, sport, style) | 930 tags, 264 distinct ignoring case, mixed case. Only some items carry "hoodie" or "fleece" as tags, so search all fields |
| `image_file_path` | TEXT | Photo path relative to `data/` | All 102 files exist and none are orphans. Serve at `/media/` + path |
| `price` | REAL | Unit price in USD, the same for every size | Whole dollars. $32×25, $45×5, $58×28, $68×23, $72×11, $88×2, $98×8. Price is fixed by `garment_type` (no type has 2 prices) |

## inventory

| Field | Type | Meaning | Notes |
|---|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Row id | 1–612, in blocks of 6 per product |
| `product_id` | TEXT FK → catalogue | Which product | Every product has exactly 6 rows |
| `size` | TEXT | XS, S, M, L, XL, XXL | `UNIQUE(product_id, size)`. Exact, case-sensitive match. Sort by an XS→XXL rank, not alphabetically |
| `quantity` | INTEGER | Units on hand. 0 = sold out | Values 0/2/5/8/12/15/20/25. Total 5,920 units. **145 rows are 0**, and 77 products have ≥1 sold-out size, but no product is fully sold out. 115 rows are low (1–5). 62 products have gaps, e.g. S and L in stock but M = 0 |

## users

| Field | Type | Meaning | Notes |
|---|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | User id | Next id is 4 |
| `name` | TEXT NOT NULL | Full name, "First Last" | Repeats first + last name |
| `email` | TEXT NOT NULL UNIQUE | Login id | UNIQUE is case-sensitive, so lowercase emails on sign-up and login |
| `password_hash` | TEXT NOT NULL | `pbkdf2_sha256$<salt>$<64-hex digest>` | PBKDF2-HMAC-SHA256 with a 32-byte digest. The salt is used as text: id 1 has a readable salt, ids 2–3 have 16 hex characters. **The iteration count is not stored**, so new hashes must use the same fixed count as the original app |
| `created_at` | TEXT DEFAULT `datetime('now')` | Sign-up time (UTC) | `YYYY-MM-DD HH:MM:SS` with no timezone |
| `first_name`, `last_name` | TEXT (nullable) | Split name | Added later via `ALTER TABLE`. Filled in on all 3 rows |

Accounts: Test User (id 1), Ada Lovelace (id 2) and Tauhid Zaman (id 3). The brief says only one test user is there.

## chat_messages (not in the brief)

| Field | Type | Meaning | Notes |
|---|---|---|---|
| `id` | INTEGER PK | Message order | Odd = user turn, even = assistant reply |
| `user_id` | INTEGER FK → users | Owner of the thread | One thread per user. Users 1 and 3 have messages |
| `role` | TEXT | `user` / `assistant` | 11 each |
| `content` | TEXT | Message text | Assistant replies are Markdown. No encoding damage is stored |
| `products_json` | TEXT (JSON) | Product cards shown with the reply | NULL on user rows. Only 5 replies carry cards (33 cards, 23 products). The card shape is: `product_id, name, garment_type, description, colors[], search_tags[], image_file_path, image_url (/media/...), price, inventory[{size, quantity}], total_stock` |
| `created_at` | TEXT | UTC time | A user turn and its reply share the same second, so order by `id` |

## What this means for the build

- **Price and stock must come from live queries** that join `catalogue.price` to `inventory.quantity` by size. Never answer from memory or old `products_json`.
- **Gaps the bot must admit:** 0 shorts, pants, hats/caps, mugs, women's or kids' items, and no "Handsome Dan" text (map it to the bulldog items). There are also no other colorways.
- **Search** must ignore case, check whole words and use synonyms across name, type, description and tags. Plain substring matching misfires: "shirt" matches "sweatshirt", "crew" matches "crewneck".
- **Data quirks to handle:** JSON stored as TEXT (`json.loads`), 3 stub products with no colors or details, rough names, and a size order that isn't alphabetical.
- **Auth:** keep the 3-segment hash format, lowercase emails, return 409 on a duplicate email, and never expose `password_hash`.
- **Don't commit** `data/` or `data.zip`. The app writes to the DB (sign-ups, chats).

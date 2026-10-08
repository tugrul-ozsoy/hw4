"""Tools the shop agent can call.

Every tool reads the live catalogue/inventory through a READ-ONLY connection. No tool can touch the
users or chat tables, write anything, or run free-form SQL, so the agent cannot leak accounts or
password hashes even if a shopper tries to talk it into it.
"""

from __future__ import annotations

import json
import re

from pydantic_ai import ModelRetry, RunContext

from backend.catalogue import (
    CATEGORIES,
    CATEGORY_BY_KEY,
    SIZE_ORDER,
    category_for,
    display_name,
    load_inventory,
    product_detail,
    short_description,
    clean_description,
)
from backend.db import read_only_connection
from backend.models import (
    CatalogueOverview,
    CategoryOverview,
    ProductDetail,
    PriceAndStock,
    ShopperProfile,
    SimilarProducts,
    ProductMatch,
    SearchResult,
    ShopDeps,
    StockAnswer,
)

MAX_RESULTS = 12

# Words that carry no product meaning in shopper questions ("do you have any yale hoodies?").
STOPWORDS = {
    "a", "an", "the", "do", "does", "you", "your", "have", "has", "got", "any", "anything", "something", "some",
    "with", "for", "me", "my", "i", "im", "show", "find", "looking", "look", "want", "need", "is", "are", "there",
    "what", "which", "in", "on", "of", "to", "and", "or", "it", "that", "this", "these", "those", "please", "can",
    "item", "items", "gear", "merch", "stuff", "apparel", "clothing", "clothes", "options", "yale", "campus",
    "customs", "shop", "store", "sell", "selling", "available", "buy", "get", "like", "one", "ones", "that's",
    "under", "below", "less", "than", "over", "above", "cheap", "cheaper", "cheapest", "price", "prices", "dollars",
    "usd", "most", "expensive", "budget", "size", "sizes", "stock", "color", "colors", "colour", "new", "cool", "nice",
}
# Garment words must match the product's own name or garment type, not a stray tag or description word
# (e.g. a quarter-zip tagged "fleece" is not a fleece).
GARMENT_WORDS = {
    "hoodie", "hoodies", "hoody", "sweatshirt", "sweatshirts", "crewneck", "crewnecks", "tee", "tees", "tshirt",
    "t-shirt", "t-shirts", "shirt", "shirts", "quarter-zip", "quarter-zips", "jacket", "jackets", "coat",
    "outerwear", "fleece", "fleeces", "long-sleeve", "longsleeve", "zip", "mockneck", "bomber", "pullover",
}
GENDER_WORDS = {"women", "womens", "women's", "woman", "ladies", "lady", "girls", "men", "mens", "men's", "guys", "unisex"}

# Shopper words -> the words the catalogue actually uses. A product matches a concept if any alternative
# appears as a whole word in its name, type, category, description, colors or tags.
SYNONYMS: dict[str, list[str]] = {
    "handsome dan": ["bulldog", "bulldogs"],
    "dan": ["bulldog", "bulldogs"],
    "mascot": ["bulldog", "bulldogs"],
    "dog": ["bulldog", "bulldogs"],
    "bulldog": ["bulldog", "bulldogs"],
    "bulldogs": ["bulldog", "bulldogs"],
    "hoodie": ["hoodie", "hooded", "hood"],
    "hoodies": ["hoodie", "hooded", "hood"],
    "hoody": ["hoodie", "hooded", "hood"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie", "hooded", "quarter-zip", "mockneck"],
    "sweatshirts": ["sweatshirt", "crewneck", "hoodie", "hooded", "quarter-zip", "mockneck"],
    "crewneck": ["crewneck", "crew neck", "crew-neck"],
    "crewnecks": ["crewneck", "crew neck", "crew-neck"],
    "tee": ["t-shirt", "tee"],
    "tees": ["t-shirt", "tee"],
    "tshirt": ["t-shirt"],
    "t-shirt": ["t-shirt"],
    "t-shirts": ["t-shirt"],
    "shirt": ["t-shirt", "performance shirt"],
    "shirts": ["t-shirt", "performance shirt"],
    "quarter-zip": ["quarter-zip", "quarter zip", "1/4 zip"],
    "quarter-zips": ["quarter-zip", "quarter zip", "1/4 zip"],
    "zip": ["zip", "zipper", "full-zip", "quarter-zip"],
    "jacket": ["jacket", "bomber"],
    "jackets": ["jacket", "bomber"],
    "coat": ["jacket", "fleece"],
    "outerwear": ["jacket", "fleece"],
    "fleece": ["fleece"],
    "fleeces": ["fleece"],
    "long-sleeve": ["long-sleeve", "long sleeve"],
    "longsleeve": ["long-sleeve", "long sleeve"],
    "grey": ["gray", "grey"],
    "gray": ["gray", "grey"],
    "navy": ["navy"],
    "game": ["the game", "harvard"],
    "harvard": ["harvard"],
    "rowing": ["crew"],
    "college": ["college"],
    "colleges": ["college"],
}

# Things shoppers ask for that this catalogue (102 tops) simply does not have.
NOT_CARRIED = {
    "shorts": "shorts", "short": None, "pants": "pants", "sweatpants": "sweatpants", "joggers": "joggers",
    "leggings": "leggings", "hat": "hats", "hats": "hats", "cap": "caps", "caps": "caps", "beanie": "beanies",
    "beanies": "beanies", "mug": "mugs", "mugs": "mugs", "cup": "cups", "bottle": "water bottles",
    "socks": "socks", "scarf": "scarves", "bag": "bags", "bags": "bags", "sticker": "stickers", "decal": "decals",
    "polo": "polos", "polos": "polos", "dress": "dresses", "skirt": "skirts", "pink": "pink items",
    "purple": "purple items", "kids": "kids' sizes", "kid": "kids' sizes", "youth": "youth sizes",
    "toddler": "toddler sizes", "baby": "baby sizes", "infant": "infant sizes", "onesie": "onesies",
    "pennant": "pennants", "blanket": "blankets", "keychain": "keychains", "jewelry": "jewelry",
}

SIZE_ALIASES = {
    "xs": "XS", "x-small": "XS", "xsmall": "XS", "extra small": "XS", "extra-small": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "x-large": "XL", "xlarge": "XL", "extra large": "XL", "extra-large": "XL",
    "xxl": "XXL", "2xl": "XXL", "2x": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "2x-large": "XXL",
}


def normalize_size(size: str) -> str | None:
    return SIZE_ALIASES.get(" ".join(size.lower().replace("size", "").split()))


def _normalize_query(text: str) -> str:
    q = text.lower().replace("’", "'").replace("¼", "1/4")
    q = re.sub(r"\b(1/4|1 4|quarter)[\s-]*zips?\b", "quarter-zip", q)
    q = re.sub(r"\bt[\s-]?shirts?\b", "t-shirt", q)
    q = re.sub(r"\blong[\s-]sleeves?\b", "long-sleeve", q)
    q = re.sub(r"\bhandsome\s+dan\b", "handsome-dan", q)
    return q


def _concepts(query: str) -> tuple[list[tuple[str, list[str], bool]], list[str], bool]:
    """Split a shopper query into concepts (word, acceptable words, is-garment), not-carried items, gender words."""
    concepts, missing, gendered = [], [], False
    for word in re.findall(r"[a-z0-9][a-z0-9'/-]*", _normalize_query(query)):
        word = word.strip("'")
        if word in STOPWORDS or len(word) < 2 or (word.isdigit() and len(word) < 4):
            continue
        if word in GENDER_WORDS:
            gendered = True
            continue
        if word in NOT_CARRIED:
            if NOT_CARRIED[word]:
                missing.append(NOT_CARRIED[word])
            continue
        if word == "handsome-dan":
            word = "handsome dan"
        alternatives = SYNONYMS.get(word) or SYNONYMS.get(word.rstrip("s")) or [word.rstrip("s") if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word]
        concepts.append((word, alternatives, word in GARMENT_WORDS))
    return concepts, sorted(set(missing)), gendered


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?:s|es)?(?![a-z0-9])", text) is not None


def _documents(conn) -> list[dict]:
    stock = load_inventory(conn)
    docs = []
    for row in conn.execute("SELECT * FROM catalogue"):
        colors = json.loads(row["colors"])
        tags = json.loads(row["search_tags"])
        description = clean_description(row["description"])
        name = display_name(row["name"], row["product_id"])
        category = category_for(row["garment_type"])
        sizes = stock.get(row["product_id"], [])
        docs.append({
            "match": ProductMatch(
                product_id=row["product_id"], name=name, category=category, garment_type=row["garment_type"],
                price=row["price"], garment_color=colors[0] if colors else None, design_colors=colors[1:],
                sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
                sold_out_sizes=[s.size for s in sizes if s.quantity == 0],
                short_description=short_description(description),
            ),
            # Weighted text fields: a hit in the name/type counts more than one in the description.
            "strong": f"{name} {row['name']} {row['garment_type']}".lower(),
            "medium": " ".join(tags + colors).lower(),
            "weak": (description or "").lower(),
        })
    return docs


def _score(doc: dict, alternatives: list[str], garment: bool = False) -> int:
    best = 0
    for alt in alternatives:
        if _has_word(doc["strong"], alt):
            best = max(best, 3)
        elif garment:
            continue  # garment words only count in the name or garment type
        elif _has_word(doc["medium"], alt):
            best = max(best, 2)
        elif _has_word(doc["weak"], alt):
            best = max(best, 1)
    return best


def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    category: str | None = None,
    max_price: float | None = None,
    in_stock_size: str | None = None,
    sort_by: str = "relevance",
    limit: int = 8,
) -> SearchResult:
    """Search the live catalogue. Use this before naming, recommending or pricing any product.

    Args:
        query: Shopper words, e.g. "navy hoodie", "Saybrook", "hockey", "Handsome Dan". Leave empty to
            list everything in a category.
        category: Optional shop category: T-Shirts, Crewnecks, Hoodies, Quarter-Zips, Jackets & Fleece, Long Sleeve.
        max_price: Optional price ceiling in USD.
        in_stock_size: Optional size (XS, S, M, L, XL, XXL); keeps only products with that size in stock.
        sort_by: "relevance" (default), "price_low" or "price_high".
        limit: How many products to return (1-12). total_matches always counts all of them.
    """
    concepts, missing, gendered = _concepts(query)
    notes = []
    if gendered:
        notes.append("Products are not sold by gender; apart from 3 items labeled men's, nothing is gender-specific.")
    cat = None
    if category:
        key = category.strip().lower()
        cat = CATEGORY_BY_KEY.get(key) or next(
            (c for k, c in CATEGORY_BY_KEY.items() if k.rstrip("s") == key.rstrip("s")), None)
        if cat is None:
            raise ModelRetry(f"Unknown category {category!r}. Use one of: {', '.join(CATEGORIES)}, or leave it empty.")
    size = None
    if in_stock_size:
        size = normalize_size(in_stock_size)
        if size is None:
            notes.append(f"The shop only carries sizes {', '.join(SIZE_ORDER)}; size {in_stock_size!r} is not offered.")

    with read_only_connection() as conn:
        docs = _documents(conn)

    def passes_filters(m: ProductMatch) -> bool:
        return (cat is None or m.category == cat) and (max_price is None or m.price <= max_price)

    scored = []
    for doc in docs:
        if not passes_filters(doc["match"]):
            continue
        scores = [_score(doc, alts, garment) for _, alts, garment in concepts]
        scored.append((doc["match"], scores))

    full = [(m, sum(s)) for m, s in scored if all(s)]  # every concept matched
    if missing and not concepts:
        full = []  # the shopper only asked for things we don't carry
    partial = False
    if not full and len(concepts) > 1:
        full = [(m, sum(s) + 10 * sum(1 for x in s if x)) for m, s in scored if any(s)]
        partial = bool(full)
    if missing:
        notes.append(f"Not carried: {', '.join(missing)}. The catalogue has only tees, long sleeves, crewnecks, "
                     "hoodies, quarter-zips, fleece and jackets, in sizes XS-XXL.")
    if partial:
        notes.append("No product matches every word; these are the closest partial matches. Say so to the shopper.")
    if not full:
        notes.append("Nothing matched. Do not suggest items that are not in a tool result.")

    if size and full:
        in_size = [(m, sc) for m, sc in full if size in m.sizes_in_stock]
        if in_size:
            full = in_size
        else:  # keep the matches so the agent can say clearly that this size is sold out
            notes.append(f"SOLD OUT in {size}: none of these matches has {size} in stock. Tell the shopper "
                         f"clearly, and give the sizes that are in stock.")
            size = None  # the size filter was not applied to the list below
    if sort_by == "price_low":
        full.sort(key=lambda t: (t[0].price, t[0].name))
    elif sort_by == "price_high":
        full.sort(key=lambda t: (-t[0].price, t[0].name))
    else:
        full.sort(key=lambda t: (-t[1], t[0].name))

    if ctx is not None:  # remember every match so the website can show them all on the page
        ctx.deps.search_query = query or (cat or "")
        ctx.deps.search_ids = [m.product_id for m, _ in full]
    limit = max(1, min(limit, MAX_RESULTS))
    shown = [m for m, _ in full[:limit]]
    prices = [m.price for m, _ in full]
    if len(full) > len(shown):
        notes.append(f"Showing {len(shown)} of {len(full)} matches; tell the shopper there are more.")
    filters = [f for f in (cat and f"category={cat}", max_price is not None and f"max_price={max_price}",
                           size and f"in stock in {size}") if f]
    if filters:
        notes.append("Filters: " + ", ".join(filters) + ".")
    return SearchResult(
        query=query, total_matches=len(full), products=shown,
        price_range=(min(prices), max(prices)) if prices else None,
        note=" ".join(notes) or "All matches shown.",
    )


def get_product_details(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetail:
    """Full facts for one product: description, price, garment and print colors, and stock per size (XS-XXL).

    Args:
        product_id: An id from search_products or the page the shopper is viewing, e.g. "basic-hoodie-big-yale".
    """
    with read_only_connection() as conn:
        detail = product_detail(conn, product_id)
    if detail is None:
        raise ModelRetry(f"No product with id {product_id!r}. Use search_products to find the right id.")
    return ProductDetail(**detail)


def get_price_and_stock(ctx: RunContext[ShopDeps], product_id: str) -> PriceAndStock:
    """Price and live stock for every size of one product. Use for "how much?" and "what sizes are left?".

    Args:
        product_id: The product's id (from search_products or the page the shopper is viewing).
    """
    with read_only_connection() as conn:
        detail = product_detail(conn, product_id)
    if detail is None:
        raise ModelRetry(f"No product with id {product_id!r}. Use search_products to find the right id.")
    stock = detail["inventory"]
    return PriceAndStock(
        product_id=detail["product_id"], name=detail["name"], price=detail["price"], stock=stock,
        total_stock=detail["total_stock"], sizes_in_stock=[s.size for s in stock if s.quantity > 0],
        sold_out_sizes=[s.size for s in stock if s.quantity == 0],
    )


def check_size(ctx: RunContext[ShopDeps], product_id: str, size: str) -> StockAnswer:
    """Is one product in stock in one size right now? Returns the live quantity for that size.

    Args:
        product_id: The product's id.
        size: The size the shopper asked about, in any form ("large", "L", "2XL", "x-small").
    """
    with read_only_connection() as conn:
        detail = product_detail(conn, product_id)
    if detail is None:
        raise ModelRetry(f"No product with id {product_id!r}. Use search_products to find the right id.")
    in_stock = [s.size for s in detail["inventory"] if s.quantity > 0]
    sold_out = [s.size for s in detail["inventory"] if s.quantity == 0]
    base = dict(product_id=detail["product_id"], name=detail["name"], price=detail["price"], size_asked=size,
                sizes_in_stock=in_stock, sold_out_sizes=sold_out)
    code = normalize_size(size)
    if code is None:
        return StockAnswer(**base, size=None, in_stock=False, quantity=None, status=None,
                           note=f"Size {size!r} is not carried; the shop only stocks {', '.join(SIZE_ORDER)}.")
    row = next(s for s in detail["inventory"] if s.size == code)
    note = {"sold_out": f"{code} is sold out.", "low_stock": f"Only {row.quantity} left in {code}.",
            "in_stock": f"{row.quantity} in stock in {code}."}[row.status]
    return StockAnswer(**base, size=code, in_stock=row.quantity > 0, quantity=row.quantity, status=row.status,
                       note=note)


def catalogue_overview(ctx: RunContext[ShopDeps]) -> CatalogueOverview:
    """What the shop carries: product count, categories with price ranges, sizes, and what is NOT carried."""
    with read_only_connection() as conn:
        rows = conn.execute("SELECT garment_type, price FROM catalogue").fetchall()
    by_cat: dict[str, list[float]] = {}
    for garment_type, price in rows:
        by_cat.setdefault(category_for(garment_type), []).append(price)
    return CatalogueOverview(
        total_products=len(rows),
        categories=[CategoryOverview(name=c, count=len(by_cat.get(c, [])), min_price=min(by_cat.get(c, [0])),
                                     max_price=max(by_cat.get(c, [0]))) for c in CATEGORIES],
        sizes_offered=SIZE_ORDER,
        not_carried=["shorts, pants and other bottoms", "hats, caps and beanies", "mugs, bottles and other gifts",
                     "polos", "kids', youth and baby sizes", "sizes beyond XS-XXL",
                     "other colorways (each product comes in one color)", "custom or personalized orders"],
    )


def get_shopper_profile(ctx: RunContext[ShopDeps]) -> ShopperProfile:
    """The logged-in shopper's own name, email, member-since date and saved-chat count.

    Only ever returns the person chatting right now (from their login session); there is no way to
    look up anyone else.
    """
    d = ctx.deps
    if not d.user_id:
        return ShopperProfile(logged_in=False)
    from backend.memory import count_messages  # local import keeps tools -> memory one-way

    with read_only_connection() as conn:
        saved = count_messages(conn, d.user_id)
    return ShopperProfile(logged_in=True, first_name=d.first_name, last_name=d.last_name, email=d.email,
                          member_since=d.member_since, saved_messages=saved)


_TOPIC_STOP = {"yale", "campus", "customs", "college", "apparel", "merch", "sweatshirt", "hoodie", "crewneck",
               "t-shirt", "shirt", "pullover", "long", "sleeve", "navy", "blue", "gray", "heather", "white"}


def _topic_words(doc: dict) -> set[str]:
    words = set(re.findall(r"[a-z][a-z-]{2,}", f"{doc['strong']} {doc['medium']}"))
    return words - _TOPIC_STOP - STOPWORDS


def find_similar_products(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None,
                          limit: int = 4) -> SimilarProducts:
    """Alternatives to one product: same category, ranked by shared school/sport/theme, similar price and color.

    Use when an item is sold out in the shopper's size, doesn't come in the color they want, or they
    ask for "something similar". Pass `size` to get only alternatives that have that size in stock.

    Args:
        product_id: The product to find alternatives for.
        size: Optional size the alternatives must have in stock (XS, S, M, L, XL, XXL or words like "large").
        limit: How many alternatives (1-8).
    """
    with read_only_connection() as conn:
        docs = _documents(conn)
    base = next((d for d in docs if d["match"].product_id == product_id.strip().lower()), None)
    if base is None:
        raise ModelRetry(f"No product with id {product_id!r}. Use search_products to find the right id.")
    code = normalize_size(size) if size else None
    b, base_words = base["match"], _topic_words(base)
    ranked = []
    for d in docs:
        m = d["match"]
        if m.product_id == b.product_id or m.category != b.category:
            continue
        if code and code not in m.sizes_in_stock:
            continue
        score = 3 * len(base_words & _topic_words(d)) - abs(m.price - b.price) / 10
        score += 2 if m.garment_color and m.garment_color == b.garment_color else 0
        ranked.append((score, m))
    ranked.sort(key=lambda t: (-t[0], t[1].name))
    picks = [m for _, m in ranked[: max(1, min(limit, 8))]]
    if ctx is not None:  # lets the page show them as a results grid if the agent sets results_title
        ctx.deps.search_query, ctx.deps.search_ids = f"similar to {b.name}", [m.product_id for m in picks]
    if size and not code:
        note = f"Size {size!r} is not carried (XS-XXL only); alternatives are shown without a size filter."
    elif not picks:
        note = f"No other {b.category.lower()} has {code} in stock." if code else "No close alternatives found."
    else:
        note = f"{len(picks)} {b.category.lower()} similar to {b.name}" + (f", all in stock in {code}." if code else ".")
    return SimilarProducts(base_product_id=b.product_id, base_name=b.name, size=code, products=picks, note=note)


TOOLS = [search_products, get_product_details, get_price_and_stock, check_size, find_similar_products,
         catalogue_overview, get_shopper_profile]

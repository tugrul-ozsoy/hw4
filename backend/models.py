"""Pydantic / PydanticAI structured types for the Campus Customs API and shop agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

StockStatus = Literal["in_stock", "low_stock", "sold_out"]

# --- Catalogue (API responses and agent tool results) ---


class SizeStock(BaseModel):
    """Live stock for one size of one product (one inventory row)."""

    size: str = Field(description="XS, S, M, L, XL or XXL.")
    quantity: int = Field(description="Units on hand right now (inventory.quantity). 0 = sold out.")
    status: StockStatus = Field(description="sold_out (0), low_stock (1-5) or in_stock (6+), so wording is consistent.")


class ProductSummary(BaseModel):
    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    short_description: str | None
    image_url: str
    total_stock: int
    sizes_in_stock: list[str]


class ProductDetail(ProductSummary):
    description: str | None
    garment_color: str | None
    design_colors: list[str]
    search_tags: list[str]
    inventory: list[SizeStock]


class CategoryCount(BaseModel):
    name: str
    count: int


# --- Chat API ---


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, description="Earlier turns, oldest first, excluding `message`.")
    current_product_id: str | None = Field(default=None, description="Product page the shopper is looking at, if any.")


class ProductCard(BaseModel):
    """A product shown as a clickable card under a chat reply (built from the live DB, never by the model)."""

    product_id: str
    name: str
    category: str
    price: float
    image_url: str
    short_description: str | None
    sizes_in_stock: list[str]


class ProductResults(BaseModel):
    """Search matches the website shows on the page as a product-card grid (Problem 7)."""

    title: str = Field(description="Heading for the grid, e.g. 'Hoodies' or 'Bulldog designs'.")
    query: str = Field(description="What the agent searched for.")
    total_matches: int = Field(description="All matches, even if fewer cards are sent.")
    products: list[ProductCard] = Field(description="Matches in the agent's search order, built from the live DB.")


class ChatResponse(BaseModel):
    reply: str = Field(description="The agent's reply in Markdown.")
    products: list[ProductCard] = Field(default_factory=list, description="Cards for the products the reply talks about.")
    results: ProductResults | None = Field(
        default=None, description="When the agent searched for a type of item: every match, for the page's results grid.")


# --- Agent ---


@dataclass
class ShopDeps:
    """Per-request context the agent can see. Never holds emails, passwords or other users' data."""

    # Who is chatting (logged-in shoppers only; guests leave these empty).
    user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = None
    # Page context: the product page the shopper has open, with facts for "this one" questions.
    current_product_id: str | None = None
    current_product_name: str | None = None
    current_product_facts: str | None = None
    # Filled in by search_products during the run: every matching id, in ranked order.
    search_query: str | None = None
    search_ids: list[str] = field(default_factory=list)


class ShopReply(BaseModel):
    """The agent's final answer."""

    reply: str = Field(description="Reply to the shopper in friendly, concise Markdown. Prices and stock only from tool results.")
    results_title: str | None = Field(
        default=None,
        description="When you used search_products for a type of item, a short heading for the matches the website "
        "shows on the page (e.g. 'Hoodies', 'Saybrook gear', 'Bulldog designs'). null if no search was relevant.",
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id of each item the reply recommends or discusses, in the order mentioned (max 6). "
        "Use only ids returned by tools in this conversation; [] when no specific product is discussed.",
    )


class ProductMatch(BaseModel):
    """One search hit, with just enough facts to answer most questions."""

    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    garment_color: str | None = Field(description="Color of the garment itself (the product comes only in this colorway).")
    design_colors: list[str] = Field(description="Print, crest or trim colors; NOT other colorways for sale.")
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]
    short_description: str | None


class SearchResult(BaseModel):
    query: str
    total_matches: int = Field(description="How many products match in total (may be more than are listed).")
    products: list[ProductMatch]
    price_range: tuple[float, float] | None = Field(description="Lowest and highest price among ALL matches.")
    note: str = Field(description="How to read this result: truncation, filters applied, or why nothing matched.")


class PriceAndStock(BaseModel):
    """Lean answer for "how much is it?" / "what sizes do you have?" (no long description text)."""

    product_id: str
    name: str = Field(description="Display name to use in the reply.")
    price: float = Field(description="catalogue.price in USD; the same for every size.")
    stock: list[SizeStock] = Field(description="Every size XS-XXL in order, with live quantity and status.")
    total_stock: int = Field(description="Sum of all sizes.")
    sizes_in_stock: list[str] = Field(description="Sizes with quantity > 0, in size order.")
    sold_out_sizes: list[str] = Field(description="Sizes with quantity 0; say these are sold out.")


class SimilarProducts(BaseModel):
    """Alternatives to one product: same category, closest match first (Problem 9)."""

    base_product_id: str
    base_name: str
    size: str | None = Field(description="If given, every alternative has this size in stock.")
    products: list[ProductMatch] = Field(description="Best alternatives first (shared school/sport/theme, price, color).")
    note: str


class StockAnswer(BaseModel):
    """Answer for one product in one size ("Do you have it in L?")."""

    product_id: str
    name: str
    price: float = Field(description="catalogue.price in USD, so a price can be quoted in the same reply.")
    size_asked: str = Field(description="The size exactly as the shopper said it (e.g. 'large', '2XL').")
    size: str | None = Field(description="The size code that was checked, or None if the shop does not carry that size.")
    in_stock: bool = Field(description="True if at least one unit is on hand in that size.")
    quantity: int | None = Field(description="Units on hand in that size (None if the size is not carried).")
    status: StockStatus | None
    sizes_in_stock: list[str] = Field(description="Other sizes that are available, to suggest instead.")
    sold_out_sizes: list[str]
    note: str = Field(description="One ready-made sentence, e.g. 'XL is sold out.' or 'Only 2 left in M.'")


class CategoryOverview(BaseModel):
    name: str
    count: int
    min_price: float
    max_price: float


class CatalogueOverview(BaseModel):
    total_products: int
    categories: list[CategoryOverview]
    sizes_offered: list[str]
    not_carried: list[str] = Field(description="Things shoppers ask for that the catalogue does not have.")


class ShopperProfile(BaseModel):
    """The logged-in shopper's own account basics (never anyone else's, never the password hash)."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = Field(default=None, description="Account creation date (UTC).")
    saved_messages: int = Field(default=0, description="How many chat messages are saved for this shopper.")


class SavedMessage(BaseModel):
    """One message from a logged-in shopper's saved chat history."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list, description="Cards rebuilt from the live catalogue.")
    created_at: str


# --- Audit trail (one record per chat turn) ---


class AuditToolCall(BaseModel):
    tool: str
    args: dict[str, Any]
    result: str | None = Field(description="Short preview of what the tool returned, or its retry/error message.")


class AuditEntry(BaseModel):
    """One agent-loop iteration: what the model asked for, what the tools returned, and why the step ended."""

    run_id: str = Field(description="Same id for every iteration of one chat turn.")
    iteration: int
    time: str = Field(description="UTC, ISO 8601.")
    model: str
    user_id: int | None = Field(description="Logged-in user id, or None for guests. No names or emails are stored.")
    page_product_id: str | None
    message: str = Field(description="Shopper message (already redacted), truncated.")
    tool_calls: list[AuditToolCall]
    reply: str | None = Field(description="Reply preview when this iteration ended the run.")
    product_ids: list[str] = Field(default_factory=list)
    stop_reason: str = Field(description="Why this iteration ended: tool results sent back, a retry, the final answer, or an error.")
    input_tokens: int = 0
    output_tokens: int = 0

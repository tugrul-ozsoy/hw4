# Usability improvements: Campus Customs shop

Four improvements: two on the website and two in the agent and backend. Each one has a "How to see it"
line so you can find it in the running app.

To start the app, run each in its own terminal:

```bash
cd backend && ../.venv/Scripts/uvicorn main:app --reload --port 8000
```

```bash
npm --prefix frontend run dev
```

Then open http://localhost:5173.

---

## 1. Products toolbar: search, sort and "in stock in my size" (front end)

**What I added**
- A toolbar above the product grid on the **Products** page with:
  - a **search box** that matches name, category, garment type and description, e.g. "Saybrook", "hockey", "bulldog", "navy";
  - an **"In stock in" size picker** (XS–XXL) that shows only products with that size available right now;
  - a **sort** menu: name, price low → high, price high → low.
- A live result count ("20 products in Hoodies with L in stock") and a **Clear filters** link.
- The filters are saved in the URL (`/products?category=Hoodies&size=L&sort=price_high`), so the browser's Back button and shared links keep the same view.

**Why it helps**
- **Shopper:** 102 products is a lot to scroll. A student who wears an L can hide everything sold out in L, and a parent on a budget can sort cheapest first. Someone looking for their residential college or team finds it by typing its name.
- **Business:** fewer dead ends. Shoppers don't click into an item only to find their size is gone. A shared link ("hoodies in L under $70") keeps working, which helps word-of-mouth and group orders.

**How to see it:** go to **Products** and type "saybrook" (3 results). Then pick **Hoodies**, set **In stock in = L**, and sort **Price: high to low** (20 results, starting at $88). Click **Clear filters** to get all 102 back.

---

## 2. "Ask about this item" and product-aware chat suggestions (front end)

**What I added**
- A blue **"Ask about this item"** button on every product page, next to "Back to all products". It opens the chat.
- On a product page, the chat shows **one-click questions about that product**:
  - "Is this in stock in M?"
  - "What colors does it come in?"
  - "Show me something similar"
- The chat already knows which product page is open (Problem 8), so "this" means the item on screen.

**Why it helps**
- **Shopper:** questions come up while looking at an item ("does it come in my size?", "anything like this?"). One click answers them without typing or naming the product, which also helps on phones.
- **Business:** the assistant is easy to find at the moment a shopper is deciding. Size and "similar item" answers keep them shopping when the first choice doesn't fit.

**How to see it:** open any product, e.g. **Products → Tri-Blend Sports Hockey T-Shirt**. Click **Ask about this item**. The chat opens with the three product questions above the input box.

---

## 3. New agent tool: `find_similar_products` (agent / backend: better answers)

**What I added**
- A new tool in `backend/tools.py`: `find_similar_products(product_id, size)`. It returns up to 4 alternatives from the **same category**.
- They are ranked by shared school, sport or theme (from names and tags), then closer price, then the same garment color.
- When a size is given, **every alternative has that size in stock**, read live from `inventory`.
- The system prompt tells the agent to use it after a "sold out" answer, after a "wrong color" answer, or when a shopper asks for "something similar".

**Why it helps**
- **Shopper:** "Sorry, L is sold out" used to be the end of the conversation. Now the shopper also hears "…but the Baseball, Basketball and Football tri-blend tees are in stock in L", all real items in their size.
- **Business:** a sold-out size or a missing color becomes a sale of a similar item instead of a lost customer. The suggestions are always in stock, so there are no disappointing follow-ups.

**How to see it:** on the **Tri-Blend Sports Hockey T-Shirt** page, ask "Is this in stock in L?" (or click **Show me something similar**). The reply says L is sold out and names similar tees that have L. The audit trail (`output/chat_audit_trail.jsonl`) shows `check_size` and then `find_similar_products`.

---

## 4. Privacy guardrails for the chat (agent / backend: safer)

**What I added** (`backend/guardrails.py`, used in `main.py` and the agent's output check)
- **Input:**
  - Card numbers (checked with the Luhn checksum, so order numbers aren't caught), US Social Security numbers, and phrases like "my password is …" are **removed from the shopper's message before** it reaches the AI model, the saved chat history (`chat_messages`) or the audit log.
  - The agent is told something was removed and reminds the shopper not to share it.
- **Output:** the agent's reply is checked before it is sent. If it contains **any email address other than the shopper's own or the store's** (orderdept@campuscustoms.com), it is rejected and the agent must rewrite it. So no other customer's email can leak.

**Why it helps**
- **Shopper:** people do paste card numbers or passwords into chat boxes. Here those details never get stored or sent to the AI provider, and the shopper gets a friendly reminder that the shop never takes payment in chat.
- **Business:** it keeps card data and passwords out of logs and databases (less PCI and privacy risk), and it protects other customers' data even if someone tries to trick the bot.

**How to see it:** open the chat and type "Can I just pay here? My card is 4111 1111 1111 1111." The reply says the shop can't take card details in chat and asks you not to share them. In `output/chat_audit_trail.jsonl`, that message is stored as "My card is [card number removed]".

---

## Checked in the running app

| Improvement | Evidence (`output/screenshots/problem9/`) |
|---|---|
| 1. Products toolbar | `01_products_toolbar.png`, `toolbar_test.json`: "saybrook" → 3; Hoodies + L + price high→low → 20 starting at $88; Clear filters → 102 |
| 2. Ask about this item | `02_ask_about_item_sold_out_alternatives.png`, `improvements_test.json`: chat opened with the 3 product questions |
| 3. `find_similar_products` | `improvements_test.json`: "Sorry, L is sold out… Baseball, Basketball, and Football tri-blend tees are in stock in L"; the tools called were `check_size` → `find_similar_products` |
| 4. Privacy guardrails | `03_card_number_redacted.png`: audit trail line "My card is [card number removed]" and a "please don't share card numbers here" reply |

**Final check of the current build** (`final_feature_check.json`, `04_final_check_similar.png`), following the "How to see it" steps above:
1. The toolbar is visible, and "saybrook" → 3 products.
2. The "Ask about this item" button is visible. It opened the chat with the 3 product questions.
3. "Show me something similar" → 4 same-style tri-blend tees, with 4 cards.
4. Card number → "We can't take payment or process card details in chat—please don't share card numbers here."

No page errors.

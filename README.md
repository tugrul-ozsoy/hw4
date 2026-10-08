# HW4 — Campus Customs Shop + Chatbot

A Campus Customs (Yale Bulldog Blue) storefront with a shop assistant chatbot:

- **Front end:** React + Vite + TypeScript (`frontend/`).
- **Back end:** Python FastAPI (`backend/main.py`). Its brain is a **PydanticAI agent** that answers from
  the local SQLite catalogue: honest prices and stock by size, product search cards that appear on the
  page, saved chats for logged-in shoppers, and safety guardrails.

## 1. Place the data pack (not in git)

The database and product images are **not** in this repo. Unzip the course `data.zip` so the folder looks
like this:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # images referenced by the catalogue
```

## 2. Back end (FastAPI + agent)

Requires Python 3.12+ (tested on 3.14). From the `hw4/` folder:

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Edit `.env` and set:

- `PORTKEY_API_KEY`: your key (the course setup uses OpenAI models through Portkey; the default model is `gpt-5.6-luna`). You can use `OPENAI_API_KEY` instead and set `CHAT_MODEL`.
- `SESSION_SECRET`: any long random string.

Then start the API (it serves products, images, accounts and `/api/chat`):

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check http://localhost:8000/api/health. It should report `{"status":"ok","products":102}`.

## 3. Front end (React + Vite)

Requires Node 20+ (tested on 24). In a second terminal, from the `hw4/` folder:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/media` to the back end on port 8000, so keep
both running.

## 4. Try it

- **Products** → search, filter "In stock in" a size, sort. Click any card for the full product page.
- **Chat** (bottom right): try "What hoodies do you have?" (cards appear on the page), "Is this in stock in
  XL?" on a product page, or "Show me something similar".
- **Log in** with the course test account `test@campuscustoms.yale.edu` / `password`, or create an account.
  Logged-in chats are saved and come back on your next visit.
  - The test account's original hash doesn't record its iteration count. On first start the back end
    re-hashes that one account with Argon2id so the published password works (`backend/seed.py`).

## What's where

| Path | What it is |
|---|---|
| `backend/main.py` | FastAPI app: products, images, accounts, `POST /api/chat`, chat history |
| `backend/prompts/prompt.md` | Agent system prompt: voice, safety rules, tool guide |
| `backend/agent.py` | Agent wiring (Portkey model, context, output checks, audit trail) |
| `backend/tools.py` | Agent tools: search, product details, price/stock, size check, similar items, overview, profile |
| `backend/models.py` | Pydantic / PydanticAI types (API, agent output, tool results, audit) |
| `backend/auth.py`, `security.py` | Sign-up / login (Argon2id hashes, sessions, rate limits) |
| `backend/memory.py`, `guardrails.py`, `catalogue.py`, `db.py`, `seed.py` | Chat memory, privacy guardrails, catalogue helpers, DB access, startup checks |
| `frontend/src/` | Pages (Home bento, Products, product page, About, Log in, Create account) and the chat widget |
| `output/harness.md` | How the system works: data, model fields, tools, safety, specs |
| `output/design.md`, `output/usability.md` | Design and usability write-ups |
| `output/app_check.html` | Live-site check with screenshots (`output/app_check_images/`) |
| `output/audit_trail.json` | Append-only log of agent-loop activity |
| `AI_prompts.md` | The prompts used to build this |

## Optional checks (back end, from `hw4/`)

```bash
python backend/smoke_test.py          # API vs database for all 102 products (no AI calls)
python backend/eval_stock_answers.py  # agent price/stock honesty (uses the model)
python backend/check_audit_safety.py  # safety replies + append-only audit trail (uses the model)
```

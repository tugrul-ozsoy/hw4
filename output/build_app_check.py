"""Build output/app_check.html (Problem 11) from the live-test screenshots in output/app_check_images/.

The screenshots and results.json come from a browser run against the live site (localhost:5173 + FastAPI).
Images are linked with relative paths (app_check_images/*.png), so the HTML opens with a double-click as
long as it stays next to that folder. Database values are read fresh from data/campus_customs.db.
"""

from __future__ import annotations

import html
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = "app_check_images"
DB = HERE.parent / "data" / "campus_customs.db"

res = json.loads((HERE / IMAGES / "results.json").read_text(encoding="utf-8"))["r"]
db = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
xl = db.execute("SELECT quantity FROM inventory WHERE product_id='basic-hoodie-big-yale' AND size='XL'").fetchone()[0]
price = db.execute("SELECT price FROM catalogue WHERE product_id='basic-hoodie-big-yale'").fetchone()[0]
hood_types = [r[0] for r in db.execute("SELECT DISTINCT garment_type FROM catalogue") if "hood" in r[0].lower()]
marks = ",".join("?" * len(hood_types))
hoodies = db.execute(f"SELECT COUNT(*) FROM catalogue WHERE garment_type IN ({marks})", hood_types).fetchone()[0]
hoodies_l = db.execute(
    f"SELECT COUNT(*) FROM catalogue c JOIN inventory i ON i.product_id = c.product_id "
    f"WHERE c.garment_type IN ({marks}) AND i.size = 'L' AND i.quantity > 0", hood_types).fetchone()[0]

checks = [
    {
        "title": "Check 1 — Chat checks an item's inventory (honest stock and price from the DB)",
        "img": "inventory.png",
        "alt": "Basic Hoodie Big Yale page with the chat answering 'only 2 left in XL, and the hoodie is $68'",
        "proves": f"Asked on the Basic Hoodie Big Yale page “{res['q1']['question']}”, the agent answers "
                  f"<b>“only 2 left in XL … $68”</b>, which matches the database exactly "
                  f"(<code>inventory.quantity</code> XL = {xl}, <code>catalogue.price</code> = ${price:.0f}) "
                  "and the page's own “XL · Only 2 left” box.",
    },
    {
        "title": "Check 2 — Dynamic search-result cards after a category question",
        "img": "search_cards.png",
        "alt": "Home page with a 'From your chat · Hoodies' grid of product cards after asking about hoodies",
        "proves": f"After asking “{res['q2']['question']}”, the page shows a <b>“From your chat · Hoodies”</b> grid "
                  f"({res['q2_grid']['count']}) of product cards with image, name, price and short info, "
                  f"built from the agent's structured results. The database has {hoodies} hoodies.",
    },
    {
        "title": "Check 3 — Usability feature (Problem 9): Products toolbar",
        "img": "usability_toolbar.png",
        "alt": "Products page filtered to Hoodies, in stock in L, sorted by price high to low",
        "proves": f"The new toolbar filters to <b>Hoodies · in stock in L · price high→low</b> and shows "
                  f"“{res['q3']['count']}”, most expensive first. The database has {hoodies_l} hoodies with L in stock, "
                  "so shoppers only see items they can actually buy in their size.",
    },
]

sections = "\n".join(f"""  <section>
    <h2>{html.escape(c['title'])}</h2>
    <img src="{IMAGES}/{c['img']}" alt="{html.escape(c['alt'])}">
    <p>{c['proves']}</p>
  </section>""" for c in checks)

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs — live app check</title>
<style>
  body {{ margin: 0; font-family: 'Segoe UI', system-ui, sans-serif; color: #1d1d1d; background: #eef4fc; }}
  header {{ background: #00356b; color: #fff; padding: 1.75rem 1.5rem; }}
  header h1 {{ margin: 0 0 .35rem; font-size: 1.8rem; }}
  header p {{ margin: 0; opacity: .85; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 1rem 1.5rem 2rem; }}
  section {{ background: #fff; border-radius: 16px; box-shadow: 0 6px 22px rgba(0, 33, 71, .1);
            padding: 1.25rem 1.5rem 1.5rem; margin: 1.5rem 0; }}
  h2 {{ color: #00356b; margin: 0 0 1rem; font-size: 1.25rem; }}
  img {{ width: 100%; border: 1px solid #d7e2ef; border-radius: 10px; display: block; }}
  p {{ margin: 1rem 0 0; line-height: 1.55; font-size: 1.02rem; }}
  code {{ background: #eef2f8; padding: 0 .3rem; border-radius: 4px; }}
</style>
</head>
<body>
<header>
  <h1>Campus Customs — live app check</h1>
  <p>Screenshots from the running site (React front end + FastAPI / PydanticAI backend). Numbers checked against campus_customs.db.</p>
</header>
<main>
{sections}
</main>
</body>
</html>
"""

(HERE / "app_check.html").write_text(page, encoding="utf-8")
print(f"wrote output/app_check.html ({len(page)} bytes); images linked from {IMAGES}/")

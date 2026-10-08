# AI Prompts Log — Homework 4: Campus Customs Shop + Chatbot

Log of the prompts I typed to the vibe coder. Code and outputs are the evidence of the completed work.

## Setup

**Prompt:**
> Hey. Put Everything we are going to work on now in the hw4 folder.

**Prompt:**
> ONLY SHORT AND CLEAR ANSWERS in this chat ok?

**Prompt:**
> Today we're gonna work on this problem. I put the data in that folder. unzip that and understand the problem VERY DEEPLY

**Prompt:**
> Your running site, database writes, and screenshots are the evidence -- you do not need an extra proof essay beyond these prompts.  
> /workflow-authoring

**Prompt:**
> Make sure everything we talked chat previously is ready in the folder, we'll move on solving problem

## Problem 1: Vibe coder prompts

**Prompt:**
> Now Create AI_prompts.md at the start of the assignment and keep it updated as we work. This is the log of what I typed to the vibe coder.  Also put one section for each problem: each section must include:
>
> the problem number and title  
> at least one prompt I typed here  
> One follow-up prompt if we needed it (and one sentence on what was lacking after the first)

**Follow-up:** none needed.

## Problem 2: Analyze the database

**Prompt:**
> Problem 2: Analyze the database
>
> Look at the database data/campus_customs.db and understand the fields of each table. 
>
> At a minimum you should understand catalogue, inventory, and users.

**Prompt:**
> Start the file output/harness.md. wriite down each table and its fields, and one short line on why each field matters for the shop or the chatbot. you will keep growing this harness file in later problems (models, tools, safety, specs)

**Follow-up:** none needed.

## Problem 3: Build the Campus Customs website

**Prompt:**
> Problem 3: build the campus customes website
>
> Scaffold a React + Vite + TypeScript front end for Campus Customs. put a nav bar at the top that links to the main pages:
> - Home
> - Product
> - About Us
> - Log in
> - Create account
>
> Pull Campus Customs-style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice (do not copy the original site text)

**Prompt:**
> On the products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description)
>
> Make each product open a single-item page (large image on one side, full product text on the other -- description, price, sizes/stock when you have them). Clicking a card on products should take the shopper there.
>
> Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk an agent yet -- a stub that will call your backend later is enough for this problem.
>
> You will need a small API soon to read the database. It is fine to start a simple fastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5

**Follow-up:**
> It should end at some point

**Follow-up** (my answer when asked what should end; I typed it instead of picking a listed option):
> Your running tasks

*What was lacking:* The backend and front-end dev servers were left running in the background after the problem was finished, instead of being stopped.

## Problem 4: Create account and login

**Prompt:**
> Problem 4: create account and login
>
> Build a normal create-account / login flow.
>
> - Create account: first name, last name, email, password (confirm password is a nice touch)
>
> - Log in: email and password
>
> New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them.

**Prompt:**
> The seed database already has a test user you can use while building:
>
> - Email: test@campuscustoms.yale.edu
> - Password: password
>
> Confirm you can log in as that user, and that a brand-new account you create also works.
>
> Update output/harness.md with how auth works (what you store for a user and how password are protected)

**Follow-up** (asked how to handle the test user's old hash, which has no stored iteration count; I picked the listed option):
> Re-hash test user (Recommended)

*What was lacking:* The seed test user's `pbkdf2_sha256$salt$hex` hash doesn't record its PBKDF2 iteration count, so the first attempt couldn't log in with the given password.

## Problem 5: PydanticAI agent backend

**Prompt:**
> Problem 5: pydanticai agent backend
>
> build the shop chatbot as a pydanticai agent behind fastapi, plugged into your front-end chat widget. Put the API app in backend/main.py -- that is the file you run with Uvicorn. Keep the agent as these four files next to it (same idea as Homework 3):
>
> - backend/prompts/prompt.md -- system prompt (grow this same file later)
> - backend/agent.py -- agent entry / wiring
> - backend/tools.py -- tools the agent can call
> - backend/models.py -- pydantic / pydanticai structured types
>
> In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need your AI model API key for the agent

**Prompt:**
> Put campus customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update types in models.py for chat replies / product cards as needed.
>
> In output/harness.md, note how the front end talks to fastapi and how the agent is loaded (prompt file + model).
>
> Make sure the backend runs from the backend/ folder like this:
>
> uvicorn main:app --reload --port 8000

**Follow-up:** none needed.

## Problem 6: Tools: product info and stock

**Prompt:**
> Problem 6: Tools: product info and stock
>
> Give the agent tools that look up real information from campus_customs.db
>
> - Product description
> - Price
> - how many are in stock (by size when the customer asks)
>
> the agent must use the database -- it should not invent prices or quantitites. If a size is out of stock, say so clearly.

**Prompt:**
> Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py
>
> In output/harness.md, list each tool and explain which model fields you chose for lookup results and why.

**Follow-up:** none needed.

## Problem 7: Chat search that updates the page

**Prompt:**
> Problem 7: chat search that updates the page
>
> Now we will add a neat feature to the site. When a customer asks about a type of item -- for example "what hoodies do you have?" -- the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info).
>
> This is an API contract: the agent returns structured product matches and then the front end renders them on the website.

**Prompt:**
> After the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior you built in Problem 3 still works: each product -- including the ones the chat just put on the page -- should still open that detail view (large image + full info) when clicked. 
>
> Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page

**Follow-up:** none needed.

## Problem 8: Customer memory

**Prompt:**
> Problem 8: customer memory
>
> When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) -- put that agent deps (or an equivalent clear pattern) and/or tools the agent can call.
>
> Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean. Hint: you can put code into the agent context.

**Prompt:**
> Guests can still chat, but history only needs to persist for logged-in users. 
>
> Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed

**Follow-up:** none needed.

## Problem 9: Usability improvements

**Prompt:**
> Problem 9: usability improvements
>
> Now that the core shop works, improve it. Choose and implement:
>
> - 2 front-end usability improvements
> - 2 agent/backend usability improvements
>
> Front-end improvements are things that make the site look better and make it easier to use.
>
> Agent / backend improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper.

**Prompt:**
> Write output/usability.md before or as you build. For each of the improvements, say:
>
> -What you added
> -Why it helps a campus customes shopper or the business
>
> Then make sure all improvements actually show up in the running app. Graders will read the write-up and look for the features.

**Follow-up:** none needed.

## Problem 10: Style the website

**Prompt:**
> Problem 10: style the website
>
> Add creative design so the site feels like a real campus customes storefront -- fonts, color, hierarchy, motion, product presentation, chat feel. 
>
> Make the design a cool combination of Bento Grid + Glassmorphism with a focus on Yale Blue

**Prompt:**
> Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short

**Follow-up:**
> Increase the effect of glassmorphims on design. It doesn't seem cool enough

*What was lacking:* The glass panels were too opaque over a pale background, so the frosted see-through effect barely showed.

## Problem 11: Live site check

**Prompt:**
> Problem 11:
>
> Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for:
>
> 1. Chat checking the inventory level of an item (honest stock/price from the DB)
> 2. The dynamic search-result cards appearing after a category question (e.g., hoodies)
> 3. One of the usability features you added in Problem 9

**Follow-up:**
> Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

*What was lacking:* The first page embedded the images inside the HTML and used longer captions, instead of separate image files with relative links and short "what this proves" sentences.

## Problem 12: Audit trail, safety, finish harness

**Prompt:**
> Problem 12: audit trail, safety, finish harness
>
> Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/results, stop reasons). Do not wipe it between runs.
>
> Also, think of some safety rules to give the agent and put them in prompts/prompt.md

**Prompt:**
> Finish output/harness.md so it is clear how the systems works.
>
> - Model fields in models.py and why you chose them
> - Tools and abilities
> - Safety rules
> - Specs (loop limits, result caps, models, how run front + back)

**Follow-up:** none needed.

## Problem 13: Push to GitHub and submit the URL

**Prompt** (with a screenshot of the Problem 13 instructions attached):
> CHECK REALLY WELL before generating .zip for us to download and submit that. I don't want that the points took off because of any missing files or last minute errors.

**Prompt:**
> push it to github for me https://github.com/tugrul-ozsoy

**Follow-up:** none needed.

# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches secondhanding listing datasets and returns items that match the user's inputted description. The description can include size, price, colors. The description parses through dta and organizes each listing by how many keywords appear in its field. Result sorted by relevance, score, highest core. 
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...natural language keywords describing the item the user searches (ex: "large graphic tee") Tokenized and matched against listed fields. 
- `size` (str): ...Clothing size to filter by (ex: "S","M","L") Case sensitive
- `max_price` (float): ...Maximum price in USD

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
-List: matching listings sorted by relevance score
-each contains id (string), the title of the item (string), description (string), price (float), brand (string), and other factors 
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
It returns empty results, it'll send out an error message 
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
earches the mock secondhand listings dataset and returns items that match the user's description, optional size, and optional price ceiling. It tokenizes the description and scores each listing by how many tokens appear in its searchable fields (title, description, category, brand, style_tags, colors). Results are sorted by relevance score, highest first.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...The user's item they are considering buying. Using for title, category, colors, style, condition, price, and the platform
- `wardrobe` (dict): ...each item has title, category, colors, style 

**What it returns:**
<!-- Describe the return value -->
1–2 outfit suggestions with a specific styling tip
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
empty boxes, and error messages 
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Calls the Groq LLM at high temperature (1.1) to generate a short, shareable social-media-style caption (2–3 sentences, ~60 words max) for the thrifted outfit. Runs differently each time due to the high temperature setting.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...the outfit suggestion (string) returned by 'suggest_outfit'
- -'new_item': used for otem title,price, and platform 

**What it returns:**
<!-- Describe the return value -->
2-3 sentence caption 
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
 Empty or whitespace-only
---

#

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
After `_parse_query()` extracts description, size, and max_price from the raw query:

1. results = search_listings(description, size, max_price)
   IF results == []:
       session["error"] = "<specific message naming filters + suggestions>"
       RETURN session  ← suggest_outfit never called

2. session["selected_item"] = results[0]

3. outfit = suggest_outfit(selected_item, wardrobe)
   session["outfit_suggestion"] = outfit
   IF outfit.startswith("Error:"):
       session["error"] = outfit
       RETURN session  ← create_fit_card never called

4. fit_card = create_fit_card(outfit, selected_item)
   session["fit_card"] = fit_card

5. RETURN session



## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
After parsing the query, the description, size, and max price go into parsed. When search_listings runs, its results are saved in search_results and the top item is pulled out into selected_item. That same item object gets passed directly into suggest_outfit and then create_fit_card — no copying, no reformatting. The outfit suggestion gets saved as outfit_suggestion and flows straight into create_fit_card. If anything fails at any step, an error key gets set and the session returns early.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | Returns `[]` (no matches) | Sets `session["error"]` with the specific filters applied (e.g. "size M and under $30") and three concrete suggestions: remove size filter, raise price limit, use simpler keywords. Returns session early — `suggest_outfit` is never called. |
| `suggest_outfit` | Wardrobe is empty | Handled gracefully — switches to a general styling advice prompt. No error returned; the agent continues to `create_fit_card` normally. |
| `suggest_outfit` | `new_item` is empty dict | Returns `"Error: No item provided to suggest_outfit..."` string. Agent checks `outfit.startswith("Error:")`, sets `session["error"]`, returns early. |
| `create_fit_card` | Outfit input is missing or empty | Returns `"Error: No outfit description provided to create_fit_card..."` string. Agent sets `session["error"]`. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
User query (natural language)
        │
        ▼
  _parse_query(query)
  → parsed: {description, size, max_price}
        │
        ├─ stored in session["parsed"]
        ▼
  search_listings(description, size, max_price)
        │
        ├── results == []  ────────────────────────────────────────────┐
        │                                                              │
        │   results = [item, ...]                                     │
        ▼                                                              │
  session["selected_item"] = results[0]                               │
        │                                                              │
        ▼                                                              │
  suggest_outfit(selected_item, wardrobe)                             │
        │                                                              │
        ├── outfit.startswith("Error:") ───────────────────────────── ┤
        │                                                              │
        │   outfit = "Pair this with..."                              │
        ▼                                                              │
  session["outfit_suggestion"] = outfit                               │
        │                                                              │
        ▼                                                              │
  create_fit_card(outfit, selected_item)                              │
        │                                                              │
        ▼                                                              │
  session["fit_card"] = fit_card                                      │
        │                                                              │
        └─────────────────────────────────────────────────────────────┘
                                                    ▼
                                         session["error"] set
                                         return session early
        ▼
  return complete session
        │
        ▼
  app.py: handle_query() maps session → 3 Gradio output panels
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For `search_listings`: I gave Claude the Tool 1 spec block (inputs with types, return value fields, failure mode) plus the `load_listings()` function signature. Expected output: a function filtering by all three parameters with keyword scoring. Before using: verified it handles all three filter params, returns empty list (not exception) on no match, and that each result dict includes the required fields. Tested with 3 queries covering happy path, empty result, and price filter.

For `suggest_outfit`: I gave Claude the Tool 2 spec block plus the wardrobe schema structure from `wardrobe_schema.json`. Expected output: a function with two separate prompt paths (empty vs. populated wardrobe). Before using: verified two distinct prompt paths exist in code and that empty wardrobe path does not return an error string. Tested with populated wardrobe, empty wardrobe, and empty `new_item`.

For `create_fit_card`: I gave Claude the Tool 3 spec block with the caption style rules (lowercase, emojis, no hashtags, mention price/platform once). Expected output: LLM call at temperature ≥ 1.0 with empty-outfit guard. Before using: checked temperature is ≥ 1.0, empty-string guard runs before the LLM call, and ran it 3 times on the same input to confirm variation.
**Milestone 4 — Planning loop and state management:**

I gave Claude the full architecture diagram above plus the Planning Loop and State Management sections. Expected output: `run_agent()` with the two conditional early-return branches and the session dict populated at each step. Before using: checked that empty results triggers early return (not a crash), that `session["selected_item"]` is `results[0]` (not a copy), and that `outfit.startswith("Error:")` is checked before calling `create_fit_card`.
---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Parse query:**
`_parse_query()` extracts: `description = "I'm looking for a vintage graphic tee I mostly wear baggy jeans and chunky sneakers What's out there and how would I style it"` → cleaned to `"looking for a vintage graphic tee mostly wear baggy jeans and chunky sneakers"`, `size = None` (no size mentioned), `max_price = 30.0`. Stored in `session["parsed"]`.

**Step 2 — search_listings:**
Called with `("looking for a vintage graphic tee...", None, 30.0)`. Loads all 40 listings, drops any over $30 (no size filter). Scores remaining listings by token overlap. "vintage", "graphic", "tee" all hit on listings tagged with those terms. Returns e.g. `[{"title": "Faded Band Tee – Nirvana", "price": 22.0, "size": "M", ...}, {"title": "Vintage Graphic Tee – University", "price": 15.0, ...}]`. Results not empty → continue.

**Step 3 — Select item:**
`session["selected_item"] = results[0]` → the Nirvana tee dict.

**Step 4 — suggest_outfit:**
Called with the Nirvana tee dict and the example wardrobe (which has wide-leg jeans, chunky sneakers, platform Docs, etc.). Wardrobe is not empty → wardrobe-specific prompt. LLM returns: `"Try this faded Nirvana tee with your wide-leg jeans and platform Docs for a full 90s grunge moment. Roll the sleeves once and tuck just the front hem for shape. Alternatively, layer it under your flannel over the black mini for a grungier layered look."` Stored in `session["outfit_suggestion"]`. Does not start with "Error:" → continue.

**Step 5 — create_fit_card:**
Called with the outfit suggestion and Nirvana tee dict. LLM at temperature 1.1 generates: `"thrifted this faded nirvana tee off depop for $22 and honestly it was made for wide-legs 🖤 full 90s grunge era, no notes"`. Stored in `session["fit_card"]`.

**Final output to user:**
- **Listing panel:** "Found 2 matches — top result: Faded Band Tee – Nirvana / $22.00 | Good | Depop / Size: M | Colors: black, grey / Tags: vintage, grunge, graphic, 90s"
- **Outfit panel:** The suggest_outfit text above.
- **Fit card panel:** The caption above.
- **Status:** No error.

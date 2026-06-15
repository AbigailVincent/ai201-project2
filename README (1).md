# FitFindr

An AI thrift shopping agent that takes a natural language query, searches a secondhand listings dataset, suggests outfits using your existing wardrobe, and writes a shareable Instagram caption — all in one shot.

---

## Setup

```bash
# 1. Clone your fork
git clone <your-fork-url>
cd fitfindr

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key
copy .env.example .env
# Edit .env: GROQ_API_KEY=your_key_here
# Free key at https://console.groq.com

# 5. Run the app
python app.py
# Open http://localhost:7860
```

---

## Tool Inventory

### `search_listings(description, size, max_price)`

| Parameter | Type | Purpose |
|-----------|------|---------|
| `description` | `str` | Natural language keywords describing the item (e.g. "vintage graphic tee") |
| `size` | `str \| None` | Clothing size to filter by (e.g. "M"). `None` = no filter |
| `max_price` | `float \| None` | Maximum price in USD. `None` = no filter |

**Returns:** `list[dict]` — matching listings sorted by relevance. Each dict contains `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Returns `[]` if nothing matches — never raises an exception.

**Purpose:** Filters the mock secondhand dataset by tokenizing the description and scoring each listing by keyword overlap, then applying size and price filters.

---

### `suggest_outfit(new_item, wardrobe)`

| Parameter | Type | Purpose |
|-----------|------|---------|
| `new_item` | `dict` | A listing dict from `search_listings` — the item to style |
| `wardrobe` | `dict` | Dict with `items` (list of wardrobe pieces) and `style_notes` (str). May be empty. |

**Returns:** `str` — 1–2 outfit suggestions with a specific styling tip (~130 words). Returns an `"Error: ..."` string if `new_item` is empty or the LLM call fails. An empty wardrobe is handled gracefully — general styling advice is returned instead of an error.

**Purpose:** Calls the Groq LLM (llama-3.3-70b-versatile) to suggest outfits. Uses a different prompt depending on whether the wardrobe is populated or empty.

---

### `create_fit_card(outfit, new_item)`

| Parameter | Type | Purpose |
|-----------|------|---------|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit` |
| `new_item` | `dict` | The listing dict — item name, price, and platform used in the caption |

**Returns:** `str` — a 2–3 sentence lowercase Instagram-style caption with 1–2 emojis, no hashtags, mentioning the item name, price, and platform once each. Returns an `"Error: ..."` string if outfit is empty or the LLM fails.

**Purpose:** Generates a shareable caption at LLM temperature 1.1 so each call produces a distinct, human-sounding result.

---

## How the Planning Loop Works

The loop runs inside `run_agent()` in `agent.py`. It does not call all three tools unconditionally — it checks the result of each step before deciding whether to continue.

First, `_parse_query()` uses regex to extract a description, size, and max price from the raw query. Then `search_listings()` is called. **If it returns an empty list**, the agent sets `session["error"]` with a message naming the exact filters applied and three specific suggestions for broadening the search, then returns early — `suggest_outfit` is never called with empty input.

If results are found, the top result is stored as `selected_item` and passed into `suggest_outfit()`. **If suggest_outfit returns a string starting with `"Error:"`**, the agent sets `session["error"]` and returns early — `create_fit_card` is never called.

If suggest_outfit succeeds, its output goes directly into `create_fit_card()`. The result is stored and the completed session is returned.

The key decision point is after `search_listings`: a query that finds nothing exits immediately with a helpful message, while a query that finds results continues through all three tools.

---

## State Management

All state is stored in a session dict that gets initialized at the start of every run. Each tool writes its result into the dict, and the next tool reads from it — no re-entry needed.

After parsing the query, the description, size, and max price go into `parsed`. When `search_listings` runs, its results are saved in `search_results` and the top item is pulled out into `selected_item`. That same item object gets passed directly into `suggest_outfit` and then `create_fit_card` — no copying, no reformatting. The outfit suggestion gets saved as `outfit_suggestion` and flows straight into `create_fit_card`. If anything fails at any step, an `error` key gets set and the session returns early.

| Key | Set when | Used by |
|-----|----------|---------|
| `parsed` | After `_parse_query()` | Arguments to `search_listings` |
| `search_results` | After `search_listings` | Error message + top result selection |
| `selected_item` | `= results[0]` | `suggest_outfit`, `create_fit_card` |
| `outfit_suggestion` | After `suggest_outfit` | `create_fit_card` |
| `fit_card` | After `create_fit_card` | UI fit card panel |
| `error` | On any failure | Early return + UI status display |

---

## Error Handling

### `search_listings` — no results
**Failure mode:** Returns `[]` when no listings match the query, size, and price filters.

**Agent response:** Sets `session["error"]` with a specific message naming the filters that were applied and three concrete suggestions. Example from testing:

Running `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`. The agent responds: *"No listings found for 'designer ballgown' with size XXS and under $5. Try broadening your search: remove the size filter, raise the price limit, or use simpler keywords."* The outfit and fit card panels stay blank — `suggest_outfit` is never called.

---

### `suggest_outfit` — empty wardrobe
**Failure mode:** `wardrobe["items"]` is an empty list.

**Agent response:** Handled gracefully — the function switches to a different prompt that asks the LLM for general styling advice instead of wardrobe-specific combinations. No error is returned and the agent continues to `create_fit_card` normally. Example from testing:

Calling `suggest_outfit(item, get_empty_wardrobe())` returns: *"Without a wardrobe on file, here are some directions: pair this faded band tee with wide-leg or straight-leg denim for a 90s grunge feel. Chunky boots or platform sneakers complete the look."*

---

### `create_fit_card` — empty outfit input
**Failure mode:** `outfit` is an empty string or whitespace only.

**Agent response:** Returns `"Error: No outfit description provided to create_fit_card. Cannot generate a caption without outfit details."` — no exception raised. The agent sets `session["error"]` and surfaces it in the status panel.

Example from testing: `create_fit_card("", item)` returns the error string immediately without making an LLM call.

---

## Spec Reflection

**One way the spec helped:** Writing the planning loop as explicit conditional pseudocode in `planning.md` before touching any code made the implementation almost line-for-line translation. The "IF results == [] → early return" branch was clearly defined before I wrote it, so I didn't accidentally call `suggest_outfit` with empty input.

**One way implementation diverged from the spec:** The original spec described `_parse_query()` as stripping size and price patterns from the description, but the first implementation left filler phrases like "I'm looking for" in the description, which hurt keyword matching for full-sentence queries. I added a second cleanup pass to handle this — it wasn't in the original spec but became necessary after testing with natural conversational queries.

---

## AI Usage

### Instance 1: `search_listings` implementation
I gave Claude the Tool 1 spec block from `planning.md` — the input types, return value description, and failure mode — along with the `load_listings()` function signature. It generated a working function but used `item['size'] == size` for size comparison, which was case-sensitive and failed when the user typed "m" instead of "M". I revised the comparison to use `.upper()` on both sides. I also changed the token splitting from a simple `split(" ")` to `re.split(r"[\s\-,/]+", description)` so hyphenated tags like "wide-leg" would match the query "wide leg".

### Instance 2: Planning loop in `run_agent()`
I gave Claude the full architecture diagram from `planning.md` plus the Planning Loop and State Management sections. It generated `run_agent()` with the correct session dict structure and also produced `_parse_query()` which I had planned to write separately. However, the generated loop only checked `if not outfit` after calling `suggest_outfit` — this would pass through an error string that still had content. I revised it to check `outfit.startswith("Error:")` instead, which correctly catches API failures that return a non-empty error message.

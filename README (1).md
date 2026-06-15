# FitFindr

An AI agent that helps you find secondhand clothes and style them. You type what you're looking for, it finds a listing, suggests an outfit, and writes your caption.

## Setup

```
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file:
```
GROQ_API_KEY=your_key_here
```

Run it:
```
python app.py
```

Then open http://localhost:7860

---

## Tools

### search_listings(description, size, max_price)

- description (str): what you're looking for, like "vintage graphic tee"
- size (str or None): size filter like "M", or None to skip
- max_price (float or None): price ceiling like 30.0, or None to skip

Returns a list of matching listing dicts sorted by relevance. Each one has id, title, description, category, style_tags, size, condition, price, colors, brand, and platform. Returns an empty list if nothing matches, never crashes.

### suggest_outfit(new_item, wardrobe)

- new_item (dict): the listing you want to style
- wardrobe (dict): has an items list and style_notes string, can be empty

Returns a string with 1-2 outfit ideas and a styling tip. If the wardrobe is empty it gives general advice instead of crashing. Returns an error string if new_item is missing.

### create_fit_card(outfit, new_item)

- outfit (str): the suggestion from suggest_outfit
- new_item (dict): the listing, used for the item name, price, and platform

Returns a short lowercase Instagram caption with 1-2 emojis and no hashtags. Returns an error string if outfit is empty.

---

## How the planning loop works

The agent parses your query to pull out a description, size, and price. Then it calls search_listings. If that comes back empty it stops and tells you what to try differently — it does not keep going with nothing. If results come back it picks the top one and passes it to suggest_outfit. If suggest_outfit returns an error string it stops there too. Otherwise it passes the outfit into create_fit_card and returns everything.

So the agent only moves to the next tool if the previous one worked. It never calls all three unconditionally.

---

## State management

Everything lives in one session dict that gets created at the start of each run. The parsed query goes in first, then search results, then the selected item, then the outfit suggestion, then the fit card. Each tool just reads from and writes to that dict so nothing has to be re-entered between steps. The selected_item that comes out of search_listings is the exact same object that goes into suggest_outfit and create_fit_card.

---

## Error handling

**search_listings** — if nothing matches, returns []. The agent sets an error message that names the filters it tried (like "size M and under $30") and gives three specific suggestions: remove the size filter, raise the price, or use simpler keywords. Tested by searching "designer ballgown size XXS under $5" which returns empty and shows that message without calling the other tools.

**suggest_outfit** — if the wardrobe is empty it switches to a general styling prompt instead of erroring. Tested with get_empty_wardrobe() and it returned real advice about what kinds of pieces pair well. If new_item is an empty dict it returns an error string immediately without calling the LLM.

**create_fit_card** — if outfit is empty or just whitespace it returns an error string right away without calling the LLM. Tested by passing an empty string and confirmed it returns the error message instead of crashing.

---

## Spec reflection

The planning.md spec helped a lot because writing out the conditional logic before coding meant the loop almost wrote itself. Having "if results == [] return early" written down meant I didn't have to figure that out mid-implementation.

One thing that diverged: the query parser in the spec was supposed to clean up the description but it left in filler words like "I'm looking for" which hurt the keyword matching. I added an extra cleanup step that wasn't in the original plan after noticing full sentence queries returned fewer results than short keyword ones.

---

## AI usage

**Instance 1:** I gave Claude the Tool 1 spec from planning.md and asked it to implement search_listings using load_listings(). It generated a working function but the size comparison was case-sensitive so "m" wouldn't match "M". I fixed it by adding .upper() to both sides. I also changed the token splitting to handle hyphens so "wide-leg" in the tags would match "wide leg" in the query.

**Instance 2:** I gave Claude the architecture diagram and planning loop section and asked it to implement run_agent(). It got the structure right but the error check after suggest_outfit only checked if the string was empty. That would miss API errors that return a non-empty error message. I changed it to check if the string starts with "Error:" instead.

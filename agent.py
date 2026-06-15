"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re
 
from tools import search_listings, suggest_outfit, create_fit_card
 
 
# ── session state ─────────────────────────────────────────────────────────────
 
def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }
 
 
# ── query parser ──────────────────────────────────────────────────────────────
 
def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex. Returns a dict with keys: description, size, max_price.
 
    Examples:
        "vintage graphic tee under $30, size M"
        → {description: "vintage graphic tee", size: "M", max_price: 30.0}
 
        "90s track jacket"
        → {description: "90s track jacket", size: None, max_price: None}
    """
    # Extract size: "size M", "size XL", "size 8", etc.
    size_match = re.search(r"\bsize\s+([A-Za-z]{1,3}|\d{1,2})\b", query, re.IGNORECASE)
    size = size_match.group(1).upper() if size_match else None
 
    # Extract max price: "under $30", "less than $40", "max $25", "up to $50", "under 30"
    price_match = re.search(
        r"\b(?:under|less than|max|up to|<)\s*\$?(\d+(?:\.\d+)?)",
        query, re.IGNORECASE
    )
    max_price = float(price_match.group(1)) if price_match else None
 
    # Clean description: strip size + price phrases, punctuation, extra whitespace
    desc = re.sub(r"\bsize\s+[A-Za-z]{1,3}\b", "", query, flags=re.IGNORECASE)
    desc = re.sub(
        r"\b(?:under|less than|max|up to|<)\s*\$?\d+(?:\.\d+)?",
        "", desc, flags=re.IGNORECASE
    )
    desc = re.sub(r"[,\.!?]+", " ", desc)
    desc = re.sub(r"\s{2,}", " ", desc).strip()
 
    return {"description": desc, "size": size, "max_price": max_price}
 
 
# ── planning loop ─────────────────────────────────────────────────────────────
 
def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
 
    Planning loop logic:
        1. Initialize session with _new_session().
        2. Parse query → description, size, max_price. Store in session["parsed"].
        3. Call search_listings(). Store results in session["search_results"].
           IF results == [] → set session["error"] (helpful message), return early.
           suggest_outfit and create_fit_card are NOT called on empty input.
        4. session["selected_item"] = results[0]
        5. Call suggest_outfit(selected_item, wardrobe).
           Store in session["outfit_suggestion"].
           IF result starts with "Error:" → set session["error"], return early.
        6. Call create_fit_card(outfit_suggestion, selected_item).
           Store in session["fit_card"].
        7. Return session.
 
    Args:
        query:    Natural language user request
        wardrobe: User's wardrobe dict
 
    Returns:
        Completed session dict. Check session["error"] first — if not None,
        outfit_suggestion and fit_card will be None.
    """
    # Step 1: initialize session
    session = _new_session(query, wardrobe)
 
    # Step 2: parse query
    parsed = _parse_query(query)
    session["parsed"] = parsed
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]
 
    # Step 3: search listings
    results = search_listings(description, size, max_price)
    session["search_results"] = results
 
    if not results:
        # Build a specific, actionable error message
        applied = []
        if size:
            applied.append(f"size {size}")
        if max_price is not None:
            applied.append(f"under ${max_price:.0f}")
        filter_desc = f" with {' and '.join(applied)}" if applied else ""
 
        session["error"] = (
            f"No listings found for '{description}'{filter_desc}. "
            "Try broadening your search: remove the size filter, raise the price limit, "
            "or use simpler keywords (e.g. 'graphic tee' instead of 'vintage 90s band shirt')."
        )
        return session  # ← early exit: suggest_outfit never called
 
    # Step 4: select top result
    session["selected_item"] = results[0]
 
    # Step 5: suggest outfit
    outfit = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit
 
    if outfit.startswith("Error:"):
        session["error"] = outfit
        return session  # ← early exit: create_fit_card never called
 
    # Step 6: create fit card
    fit_card = create_fit_card(outfit, session["selected_item"])
    session["fit_card"] = fit_card
 
    if fit_card.startswith("Error:"):
        session["error"] = fit_card
 
    # Step 7: return session
    return session
 
 
# ── CLI test ──────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
 
    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
 
    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")e: {session2['error']}")

"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
 
from dotenv import load_dotenv
from groq import Groq
 
from utils.data_loader import load_listings
 
load_dotenv()
 
 
# ── Groq client ───────────────────────────────────────────────────────────────
 
def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)
 
 
MODEL = "llama-3.3-70b-versatile"
 
 
# ── Tool 1: search_listings ───────────────────────────────────────────────────
 
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
 
    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "m").
        max_price:   Maximum price (inclusive), or None to skip price filtering.
 
    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.
 
    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    # Step 1: load all listings
    all_listings = load_listings()
 
    # Step 2: filter by max_price and size
    filtered = []
    for item in all_listings:
        if max_price is not None and item.get("price", 0) > max_price:
            continue
        if size is not None and item.get("size", "").upper() != size.upper():
            continue
        filtered.append(item)
 
    # Step 3: score by keyword overlap with description
    tokens = [t.lower() for t in re.split(r"[\s\-,/]+", description) if len(t) > 1]
 
    scored = []
    for item in filtered:
        searchable = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            item.get("brand", ""),
            " ".join(item.get("style_tags", [])),
            " ".join(item.get("colors", [])),
        ]).lower()
 
        score = sum(1 for t in tokens if t in searchable)
 
        # Step 4: drop zero-score items
        if score > 0:
            scored.append((score, item))
 
    # Step 5: sort by score descending, return just the dicts
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]
 
 
# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────
 
def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
 
    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.
 
    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offers general styling advice.
        Returns a descriptive error string (not an exception) if new_item is empty.
    """
    if not new_item:
        return "Error: No item provided to suggest_outfit. Cannot generate outfit suggestions without an item."
 
    item_summary = (
        f"Item: {new_item.get('title', 'unknown')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Price: ${new_item.get('price', '?')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}"
    )
 
    wardrobe_items = wardrobe.get("items", [])
 
    # Step 1: check whether wardrobe is empty
    if not wardrobe_items:
        # Step 2: empty wardrobe — general styling advice
        prompt = f"""You are a personal stylist. A shopper is considering buying this secondhand item:
 
{item_summary}
 
They haven't shared their wardrobe yet. Give them 1–2 outfit ideas: what kinds of pieces pair well with this item, 
what vibe or aesthetic it suits, and one specific styling tip (e.g., how to tuck, layer, or accessorise it). 
Keep it conversational and under 120 words."""
    else:
        # Step 3: wardrobe available — specific combinations
        wardrobe_lines = "\n".join(
            f"- {w.get('title', 'item')} ({w.get('category', 'unknown')}, "
            f"colors: {', '.join(w.get('colors', []))}, "
            f"tags: {', '.join(w.get('style_tags', []))})"
            for w in wardrobe_items
        )
        style_notes = wardrobe.get("style_notes", "")
        wardrobe_block = f"Their wardrobe:\n{wardrobe_lines}"
        if style_notes:
            wardrobe_block += f"\n\nStyle notes: {style_notes}"
 
        prompt = f"""You are a personal stylist. A shopper is considering buying this secondhand item:
 
{item_summary}
 
{wardrobe_block}
 
Suggest 1–2 complete outfit combinations using this new item paired with specific pieces from their wardrobe. 
Name the actual wardrobe pieces. Include one styling tip. Keep it conversational and under 130 words."""
 
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300,
        )
        # Step 4: return the LLM's response
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating outfit suggestion: {e}"
 
 
# ── Tool 3: create_fit_card ───────────────────────────────────────────────────
 
def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
 
    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.
 
    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, returns a descriptive error message
        string — does NOT raise an exception.
    """
    # Step 1: guard against empty outfit
    if not outfit or not outfit.strip():
        return "Error: No outfit description provided to create_fit_card. Cannot generate a caption without outfit details."
 
    if not new_item:
        return "Error: No item provided to create_fit_card. Cannot generate a caption without item details."
 
    item_ref = (
        f"{new_item.get('title', 'thrifted piece')} "
        f"(${new_item.get('price', '?')} on {new_item.get('platform', 'a secondhand app')})"
    )
 
    # Step 2: build prompt with item details and outfit
    prompt = f"""Write an Instagram caption for a thrift outfit post. It should sound like a real person, not a brand.
 
Item: {item_ref}
Outfit: {outfit}
 
Rules:
- 2–3 sentences max, under 60 words total
- All lowercase
- Mention the item name, price, and platform once each, naturally
- 1–2 emojis placed naturally (no trailing emoji wall)
- No hashtags
- Capture the specific vibe of this outfit
- Sound excited about the find without being generic ("omg obsessed" is too generic)"""
 
    try:
        client = _get_groq_client()
        # Step 3: high temperature for variation across calls
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating fit card: {e}"

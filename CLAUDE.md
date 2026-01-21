# Decker

Tools for creating and modifying Magic: The Gathering decks.

## Setup

This is a Python project managed with `uv`. To install dependencies:

```bash
uv sync
```

## Fetching Decks from Moxfield

To fetch a deck from Moxfield and save it locally:

```bash
uv run python deck.py <moxfield_id_or_url> <deck_name>
```

Example:
```bash
uv run python deck.py https://moxfield.com/decks/Smh7ryekIUeOQd9mlYjBXA tannuk
```

This creates a directory `decks/<deck_name>/` containing:
- `deck.json` - Full Moxfield API response with all card details
- `cards.json` - Simplified card list
- `decklist.txt` - Human-readable decklist

## Using the Deck Module

```python
from deck import Deck

# Fetch from Moxfield
deck = Deck.from_moxfield("https://moxfield.com/decks/Smh7ryekIUeOQd9mlYjBXA")

# Or load from saved directory
deck = Deck.load("decks/tannuk")

# Access deck info
print(deck.name)           # Deck name
print(deck.format)         # Format (commander, modern, etc.)
print(deck.commanders)     # List of commander Card objects
print(deck.mainboard)      # List of mainboard Card objects
print(deck.total_cards)    # Total card count

# Save to directory
deck.save("decks/my_deck")
```

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

## Getting Card Recommendations

Get card recommendations from EDHREC for any commander:

```bash
# By commander name
uv run python recommendations.py "Tannuk, Memorial Ensign"

# For an existing deck (suggests cards not already in the deck)
uv run python recommendations.py --deck decks/tannuk
```

Using the module in code:

```python
from recommendations import RecommendationEngine
from deck import Deck

engine = RecommendationEngine()

# Get high-synergy cards for a commander
recs = engine.get_recommendations_for_commander("Tannuk, Memorial Ensign")
for rec in recs:
    print(f"{rec.name}: {rec.synergy:.0%} synergy")

# Get suggestions for an existing deck (excludes cards already in deck)
deck = Deck.load("decks/tannuk")
suggestions = engine.suggest_additions(deck, limit=20)

# Get all recommendation categories
all_recs = engine.get_all_recommendations("Tannuk, Memorial Ensign")
# Returns: high_synergy, top_cards, creatures, instants, sorceries,
#          artifacts, enchantments, lands, utility_lands, mana_artifacts
```

## Analyzing Decks for Potential Cuts

Identify cards that might be worth removing:

```bash
uv run python recommendations.py --analyze decks/tannuk
```

This shows:
- **EDHREC coverage** - what % of your cards appear in EDHREC recommendations
- **Low synergy cards** - cards with <5% synergy (excluding staples like Sol Ring)
- **Off-theme cards** - cards not in EDHREC's top lists for your commander

Note: "Off-theme" doesn't always mean bad - it might be hidden tech that others haven't discovered. Use judgment.

```python
from recommendations import DeckAnalyzer
from deck import Deck

analyzer = DeckAnalyzer()
deck = Deck.load("decks/tannuk")

analysis = analyzer.analyze_deck(deck)
print(f"Coverage: {analysis['edhrec_coverage']:.0%}")

for cut in analysis["low_synergy"]:
    print(f"{cut.synergy:+.0%} {cut.name}")
```

## Getting Card Prices

Check card prices from the Mana Pool API:

```bash
# Single card (shows all printings)
uv run python prices.py "Sol Ring"

# Full deck pricing (cheapest printing per card)
uv run python prices.py --deck decks/tannuk
```

- Prices are fetched from `manapool.com` and cached locally for 24 hours
- Deck pricing uses the cheapest available printing for each card
- Shows per-card and total deck cost

```python
from prices import PriceChecker

checker = PriceChecker()

# Get all printings of a card (sorted cheapest first)
printings = checker.get_printings("Sol Ring")
for p in printings:
    print(f"[{p.set_code}] ${p.price_usd:.2f}")

# Get just the cheapest printing
cheapest = checker.get_cheapest_printing("Sol Ring")
print(f"Cheapest: ${cheapest.price_usd:.2f}")

# Price an entire deck
from deck import Deck
deck = Deck.load("decks/tannuk")
results = checker.price_deck(deck)
total = sum(r.total_price_usd for r in results if r.total_price_usd)
print(f"Deck total: ${total:.2f}")
```

## Finding Primers and Guides

Find articles, deck techs, and primers for a commander:

```bash
uv run python guides.py "Tannuk, Memorial Ensign"
uv run python guides.py --deck decks/tannuk
```

This returns links to:
- EDHREC deck tech articles
- EDHREC commander page (stats, recommendations)
- Moxfield search for community primers

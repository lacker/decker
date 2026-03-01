"""Fetch card prices from the Mana Pool API."""

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import cloudscraper


CACHE_FILE = ".price_cache.json"
CACHE_MAX_AGE = 24 * 60 * 60  # 24 hours in seconds


@dataclass
class CardPrice:
    """Price data for a single card printing."""
    name: str
    set_code: str
    price_cents: Optional[int]
    price_cents_foil: Optional[int]
    price_market: Optional[int]
    url: str

    @property
    def price_usd(self) -> Optional[float]:
        """Cheapest available price in USD."""
        prices = [p for p in [self.price_cents, self.price_cents_foil, self.price_market] if p is not None]
        if not prices:
            return None
        return min(prices) / 100.0


@dataclass
class DeckPriceResult:
    """Price result for a card in a deck."""
    card_name: str
    quantity: int
    cheapest_printing: Optional[CardPrice]
    unit_price_usd: Optional[float]
    total_price_usd: Optional[float]


class PriceChecker:
    """Fetches and caches card prices from the Mana Pool API."""

    def __init__(self):
        self._price_data: Optional[dict[str, list[CardPrice]]] = None

    def _cache_is_fresh(self) -> bool:
        """Check if the cache file exists and is less than 24 hours old."""
        if not os.path.exists(CACHE_FILE):
            return False
        age = time.time() - os.path.getmtime(CACHE_FILE)
        return age < CACHE_MAX_AGE

    def _load_cache(self) -> list[dict]:
        """Load cached price data from disk."""
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    def _save_cache(self, data: list[dict]) -> None:
        """Save price data to disk cache."""
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)

    def _fetch_prices(self) -> list[dict]:
        """Fetch bulk price data from the Mana Pool API."""
        if self._cache_is_fresh():
            return self._load_cache()

        scraper = cloudscraper.create_scraper()
        response = scraper.get("https://manapool.com/api/v1/prices/singles", timeout=30)
        response.raise_for_status()

        raw = response.json()
        data = raw.get("data", [])
        self._save_cache(data)
        return data

    def _ensure_loaded(self) -> dict[str, list[CardPrice]]:
        """Load price data if not already loaded, indexed by lowercase card name."""
        if self._price_data is not None:
            return self._price_data

        raw_data = self._fetch_prices()
        self._price_data = {}

        for entry in raw_data:
            name = entry.get("name", "")
            card_price = CardPrice(
                name=name,
                set_code=entry.get("set_code", ""),
                price_cents=entry.get("price_cents"),
                price_cents_foil=entry.get("price_cents_foil"),
                price_market=entry.get("price_market"),
                url=entry.get("url", ""),
            )
            key = name.lower()
            if key not in self._price_data:
                self._price_data[key] = []
            self._price_data[key].append(card_price)

        # Sort each card's printings by cheapest first
        for key in self._price_data:
            self._price_data[key].sort(key=lambda p: p.price_usd if p.price_usd is not None else float("inf"))

        return self._price_data

    def get_printings(self, card_name: str) -> list[CardPrice]:
        """Get all printings of a card, sorted cheapest first."""
        data = self._ensure_loaded()
        return data.get(card_name.lower(), [])

    def get_cheapest_printing(self, card_name: str) -> Optional[CardPrice]:
        """Get the cheapest printing of a card, or None if not found."""
        printings = self.get_printings(card_name)
        return printings[0] if printings else None

    def price_deck(self, deck) -> list[DeckPriceResult]:
        """Price all cards in a deck (commanders + mainboard)."""
        results = []
        for card in deck.commanders + deck.mainboard:
            cheapest = self.get_cheapest_printing(card.name)
            unit_price = cheapest.price_usd if cheapest else None
            total_price = unit_price * card.quantity if unit_price is not None else None
            results.append(DeckPriceResult(
                card_name=card.name,
                quantity=card.quantity,
                cheapest_printing=cheapest,
                unit_price_usd=unit_price,
                total_price_usd=total_price,
            ))
        return results


def print_card_prices(card_name: str, printings: list[CardPrice]) -> None:
    """Pretty print prices for a single card."""
    if not printings:
        print(f"\nNo prices found for: {card_name}")
        return

    print(f"\nPrices for {card_name} ({len(printings)} printings):\n")
    for p in printings:
        price_str = f"${p.price_usd:.2f}" if p.price_usd is not None else "N/A"
        foil_str = f"  Foil: ${p.price_cents_foil / 100:.2f}" if p.price_cents_foil else ""
        print(f"  [{p.set_code.upper()}] {price_str}{foil_str}  {p.url}")


def print_deck_prices(results: list[DeckPriceResult]) -> None:
    """Pretty print deck pricing results."""
    print(f"\n{'Card':<40} {'Qty':>3}  {'Each':>8}  {'Total':>8}  Set")
    print("-" * 75)

    deck_total = 0.0
    missing = []

    for r in sorted(results, key=lambda r: r.total_price_usd or 0, reverse=True):
        if r.unit_price_usd is not None:
            set_code = r.cheapest_printing.set_code.upper() if r.cheapest_printing else ""
            print(f"  {r.card_name:<38} {r.quantity:>3}  ${r.unit_price_usd:>7.2f}  ${r.total_price_usd:>7.2f}  {set_code}")
            deck_total += r.total_price_usd
        else:
            missing.append(r.card_name)

    print("-" * 75)
    print(f"  {'TOTAL':<38}      {'':>8}  ${deck_total:>7.2f}")

    if missing:
        print(f"\n  {len(missing)} cards not found: {', '.join(missing[:5])}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prices.py <card_name>")
        print("       python prices.py --deck <deck_dir>")
        print()
        print("Examples:")
        print("  python prices.py 'Sol Ring'")
        print("  python prices.py --deck decks/tannuk")
        sys.exit(1)

    checker = PriceChecker()

    if sys.argv[1] == "--deck":
        from deck import Deck
        deck_dir = sys.argv[2]
        deck = Deck.load(deck_dir)
        print(f"Pricing deck: {deck}")
        results = checker.price_deck(deck)
        print_deck_prices(results)
    else:
        card_name = sys.argv[1]
        printings = checker.get_printings(card_name)
        print_card_prices(card_name, printings)

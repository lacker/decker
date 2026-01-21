"""Deck management for Magic: The Gathering decks."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

import cloudscraper


@dataclass
class Card:
    """A single card entry in a deck."""
    name: str
    quantity: int
    board: str  # 'commander', 'mainboard', 'sideboard', etc.
    type_line: str
    mana_cost: str
    cmc: float


@dataclass
class Deck:
    """A Magic: The Gathering deck."""
    name: str
    format: str
    moxfield_id: str
    description: str = ""
    cards: list[Card] = field(default_factory=list)
    raw_data: Optional[dict] = field(default=None, repr=False)

    @classmethod
    def from_moxfield(cls, moxfield_id: str) -> "Deck":
        """Fetch a deck from Moxfield by its ID or URL."""
        # Extract ID from URL if needed
        if "moxfield.com/decks/" in moxfield_id:
            moxfield_id = moxfield_id.split("moxfield.com/decks/")[-1].split("/")[0]

        url = f"https://api2.moxfield.com/v3/decks/all/{moxfield_id}"

        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        response.raise_for_status()

        data = response.json()
        return cls._from_moxfield_data(data, moxfield_id)

    @classmethod
    def _from_moxfield_data(cls, data: dict, moxfield_id: str) -> "Deck":
        """Create a Deck from Moxfield API response data."""
        cards = []

        # Process each board type
        boards = data.get("boards", {})
        for board_name, board_data in boards.items():
            if not isinstance(board_data, dict):
                continue
            board_cards = board_data.get("cards", {})
            for card_id, card_entry in board_cards.items():
                card_info = card_entry.get("card", {})
                cards.append(Card(
                    name=card_info.get("name", "Unknown"),
                    quantity=card_entry.get("quantity", 1),
                    board=board_name,
                    type_line=card_info.get("type_line", ""),
                    mana_cost=card_info.get("mana_cost", ""),
                    cmc=card_info.get("cmc", 0),
                ))

        return cls(
            name=data.get("name", "Unknown Deck"),
            format=data.get("format", "unknown"),
            moxfield_id=moxfield_id,
            description=data.get("description", ""),
            cards=cards,
            raw_data=data,
        )

    @classmethod
    def load(cls, deck_dir: str) -> "Deck":
        """Load a deck from a directory."""
        deck_json_path = os.path.join(deck_dir, "deck.json")
        with open(deck_json_path, "r") as f:
            raw_data = json.load(f)

        # Extract moxfield_id from publicId or directory name
        moxfield_id = raw_data.get("publicId", os.path.basename(deck_dir))
        return cls._from_moxfield_data(raw_data, moxfield_id)

    def save(self, deck_dir: str) -> None:
        """Save the deck to a directory."""
        os.makedirs(deck_dir, exist_ok=True)

        # Save raw data if available
        if self.raw_data:
            with open(os.path.join(deck_dir, "deck.json"), "w") as f:
                json.dump(self.raw_data, f, indent=2)

        # Save simplified card list
        cards_data = [asdict(card) for card in self.cards]
        with open(os.path.join(deck_dir, "cards.json"), "w") as f:
            json.dump(cards_data, f, indent=2)

        # Save human-readable decklist
        with open(os.path.join(deck_dir, "decklist.txt"), "w") as f:
            f.write(f"# {self.name}\n")
            f.write(f"# Format: {self.format}\n")
            if self.description:
                f.write(f"# {self.description}\n")
            f.write("\n")

            # Group cards by board
            boards = {}
            for card in self.cards:
                if card.board not in boards:
                    boards[card.board] = []
                boards[card.board].append(card)

            # Output in a sensible order
            board_order = ["commanders", "mainboard", "sideboard", "maybeboard"]
            for board_name in board_order:
                if board_name in boards and boards[board_name]:
                    f.write(f"## {board_name.title()}\n")
                    for card in sorted(boards[board_name], key=lambda c: c.name):
                        f.write(f"{card.quantity} {card.name}\n")
                    f.write("\n")

            # Any remaining boards
            for board_name, board_cards in boards.items():
                if board_name not in board_order and board_cards:
                    f.write(f"## {board_name.title()}\n")
                    for card in sorted(board_cards, key=lambda c: c.name):
                        f.write(f"{card.quantity} {card.name}\n")
                    f.write("\n")

    @property
    def commanders(self) -> list[Card]:
        """Get commander cards."""
        return [c for c in self.cards if c.board == "commanders"]

    @property
    def mainboard(self) -> list[Card]:
        """Get mainboard cards."""
        return [c for c in self.cards if c.board == "mainboard"]

    @property
    def total_cards(self) -> int:
        """Total number of cards (counting quantities)."""
        return sum(c.quantity for c in self.cards)

    def __str__(self) -> str:
        commanders = ", ".join(c.name for c in self.commanders)
        return f"{self.name} ({self.format}) - {self.total_cards} cards - Commander: {commanders}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python deck.py <moxfield_id_or_url> <deck_name>")
        print("Example: python deck.py Smh7ryekIUeOQd9mlYjBXA tannuk")
        sys.exit(1)

    moxfield_id = sys.argv[1]
    deck_name = sys.argv[2]

    print(f"Fetching deck from Moxfield: {moxfield_id}")
    deck = Deck.from_moxfield(moxfield_id)
    print(f"Loaded: {deck}")

    deck_dir = os.path.join("decks", deck_name)
    deck.save(deck_dir)
    print(f"Saved to: {deck_dir}/")

"""Get card recommendations from EDHREC for Commander decks."""

import json
from dataclasses import dataclass
from typing import Optional

from pyedhrec.pyedhrec import EDHRec

from deck import Deck, Card


@dataclass
class Recommendation:
    """A recommended card with synergy data."""
    name: str
    synergy: float  # Synergy score (0-1)
    num_decks: int  # Number of decks playing this card
    inclusion_rate: float  # Percentage of decks that include this card
    in_deck: bool = False  # Whether the card is already in the deck


class RecommendationEngine:
    """Fetches card recommendations from EDHREC."""

    def __init__(self):
        self.edh = EDHRec()

    def get_recommendations_for_commander(
        self,
        commander_name: str,
        deck: Optional[Deck] = None,
        limit: int = 50,
    ) -> list[Recommendation]:
        """
        Get card recommendations for a commander.

        If a deck is provided, marks which recommendations are already in the deck.
        """
        # Get cards already in deck
        deck_cards = set()
        if deck:
            deck_cards = {card.name.lower() for card in deck.cards}

        recommendations = []

        # Get high synergy cards
        synergy_data = self.edh.get_high_synergy_cards(commander_name)
        for card in synergy_data.get("High Synergy Cards", []):
            potential = card.get("potential_decks", 1)
            recommendations.append(Recommendation(
                name=card["name"],
                synergy=card.get("synergy", 0),
                num_decks=card.get("num_decks", 0),
                inclusion_rate=card.get("num_decks", 0) / potential if potential else 0,
                in_deck=card["name"].lower() in deck_cards,
            ))

        # Sort by synergy descending
        recommendations.sort(key=lambda r: r.synergy, reverse=True)

        return recommendations[:limit]

    def get_top_cards_for_commander(
        self,
        commander_name: str,
        deck: Optional[Deck] = None,
        limit: int = 50,
    ) -> list[Recommendation]:
        """
        Get top played cards for a commander (by inclusion rate, not synergy).
        """
        deck_cards = set()
        if deck:
            deck_cards = {card.name.lower() for card in deck.cards}

        recommendations = []

        top_data = self.edh.get_top_cards(commander_name)
        for card in top_data.get("Top Cards", []):
            potential = card.get("potential_decks", 1)
            recommendations.append(Recommendation(
                name=card["name"],
                synergy=card.get("synergy", 0),
                num_decks=card.get("num_decks", 0),
                inclusion_rate=card.get("num_decks", 0) / potential if potential else 0,
                in_deck=card["name"].lower() in deck_cards,
            ))

        # Sort by inclusion rate descending
        recommendations.sort(key=lambda r: r.inclusion_rate, reverse=True)

        return recommendations[:limit]

    def get_all_recommendations(
        self,
        commander_name: str,
        deck: Optional[Deck] = None,
    ) -> dict[str, list[Recommendation]]:
        """
        Get all recommendation categories for a commander.

        Returns a dict with keys like 'high_synergy', 'top_cards', 'creatures', etc.
        """
        deck_cards = set()
        if deck:
            deck_cards = {card.name.lower() for card in deck.cards}

        def parse_cards(data: dict, key: str) -> list[Recommendation]:
            recs = []
            for card in data.get(key, []):
                potential = card.get("potential_decks", 1)
                recs.append(Recommendation(
                    name=card["name"],
                    synergy=card.get("synergy", 0),
                    num_decks=card.get("num_decks", 0),
                    inclusion_rate=card.get("num_decks", 0) / potential if potential else 0,
                    in_deck=card["name"].lower() in deck_cards,
                ))
            return recs

        results = {}

        # High synergy cards
        results["high_synergy"] = parse_cards(
            self.edh.get_high_synergy_cards(commander_name),
            "High Synergy Cards"
        )

        # Top cards by category
        results["top_cards"] = parse_cards(
            self.edh.get_top_cards(commander_name),
            "Top Cards"
        )
        results["creatures"] = parse_cards(
            self.edh.get_top_creatures(commander_name),
            "Creatures"
        )
        results["instants"] = parse_cards(
            self.edh.get_top_instants(commander_name),
            "Instants"
        )
        results["sorceries"] = parse_cards(
            self.edh.get_top_sorceries(commander_name),
            "Sorceries"
        )
        results["artifacts"] = parse_cards(
            self.edh.get_top_artifacts(commander_name),
            "Artifacts"
        )
        results["enchantments"] = parse_cards(
            self.edh.get_top_enchantments(commander_name),
            "Enchantments"
        )
        results["lands"] = parse_cards(
            self.edh.get_top_lands(commander_name),
            "Lands"
        )
        results["utility_lands"] = parse_cards(
            self.edh.get_top_utility_lands(commander_name),
            "Utility Lands"
        )
        results["mana_artifacts"] = parse_cards(
            self.edh.get_top_mana_artifacts(commander_name),
            "Mana Artifacts"
        )

        return results

    def suggest_additions(
        self,
        deck: Deck,
        limit: int = 20,
    ) -> list[Recommendation]:
        """
        Suggest cards to add to a deck based on its commander.

        Returns high-synergy cards that are NOT already in the deck,
        combining data from all categories.
        """
        if not deck.commanders:
            raise ValueError("Deck has no commander")

        commander_name = deck.commanders[0].name
        all_recs = self.get_all_recommendations(commander_name, deck)

        # Combine all recommendations, deduplicating by name
        seen = set()
        suggestions = []
        for category, recs in all_recs.items():
            for rec in recs:
                if not rec.in_deck and rec.name not in seen:
                    seen.add(rec.name)
                    suggestions.append(rec)

        # Sort by synergy descending
        suggestions.sort(key=lambda r: r.synergy, reverse=True)

        return suggestions[:limit]


def print_recommendations(recs: list[Recommendation], title: str = "Recommendations"):
    """Pretty print a list of recommendations."""
    print(f"\n{title}")
    print("=" * len(title))
    for rec in recs:
        status = "[IN DECK]" if rec.in_deck else ""
        print(f"  {rec.name}: {rec.synergy:.0%} synergy, in {rec.num_decks} decks {status}")


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python recommendations.py <commander_name>")
        print("       python recommendations.py --deck <deck_dir>")
        print()
        print("Examples:")
        print("  python recommendations.py 'Tannuk, Memorial Ensign'")
        print("  python recommendations.py --deck decks/tannuk")
        sys.exit(1)

    engine = RecommendationEngine()

    if sys.argv[1] == "--deck":
        # Load deck and suggest additions
        deck_dir = sys.argv[2]
        deck = Deck.load(deck_dir)
        print(f"Loaded deck: {deck}")

        commander = deck.commanders[0].name if deck.commanders else "Unknown"
        print(f"Commander: {commander}")

        suggestions = engine.suggest_additions(deck, limit=20)
        print_recommendations(suggestions, f"Suggested additions for {deck.name}")

    else:
        # Just get recommendations for a commander
        commander = sys.argv[1]
        recs = engine.get_recommendations_for_commander(commander, limit=20)
        print_recommendations(recs, f"High synergy cards for {commander}")

"""Fetch primers and guides for commanders."""

import re
from dataclasses import dataclass
from urllib.parse import quote

import cloudscraper


@dataclass
class Guide:
    """A primer or guide for a commander."""
    title: str
    url: str
    source: str  # 'edhrec', 'moxfield', 'tcgplayer', etc.
    summary: str = ""


class GuideFetcher:
    """Fetches primers and guides from various sources."""

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    def _format_commander_name(self, name: str) -> str:
        """Format commander name for URLs (lowercase, hyphenated)."""
        # Remove commas and special chars, replace spaces with hyphens
        formatted = name.lower()
        formatted = re.sub(r"[,']", "", formatted)
        formatted = re.sub(r"\s+", "-", formatted)
        return formatted

    def get_edhrec_article_url(self, commander_name: str) -> str:
        """Get the EDHREC deck tech article URL for a commander."""
        formatted = self._format_commander_name(commander_name)
        return f"https://edhrec.com/articles/{formatted}-commander-deck-tech"

    def get_edhrec_page_url(self, commander_name: str) -> str:
        """Get the main EDHREC commander page URL."""
        formatted = self._format_commander_name(commander_name)
        return f"https://edhrec.com/commanders/{formatted}"

    def fetch_edhrec_article(self, commander_name: str) -> Guide | None:
        """Fetch the EDHREC deck tech article if it exists."""
        url = self.get_edhrec_article_url(commander_name)

        try:
            response = self.scraper.get(url, timeout=10)
            if response.status_code == 200 and "article" in response.text.lower():
                # Extract a summary from the article
                # Look for the first paragraph after the intro
                text = response.text

                # Try to find article content
                summary = ""
                # Look for meta description
                match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', text)
                if match:
                    summary = match.group(1)

                return Guide(
                    title=f"{commander_name} Commander Deck Tech",
                    url=url,
                    source="edhrec",
                    summary=summary,
                )
        except Exception:
            pass

        return None

    def get_moxfield_search_url(self, commander_name: str) -> str:
        """Get a Moxfield search URL to find decks with primers for this commander."""
        formatted = quote(f'"{commander_name}" primer')
        return f"https://moxfield.com/decks/search?q={formatted}&fmt=commander"

    def get_all_guides(self, commander_name: str) -> list[Guide]:
        """Get all available guides for a commander."""
        guides = []

        # EDHREC article
        edhrec = self.fetch_edhrec_article(commander_name)
        if edhrec:
            guides.append(edhrec)

        # Always add EDHREC main page as a resource
        guides.append(Guide(
            title=f"{commander_name} on EDHREC",
            url=self.get_edhrec_page_url(commander_name),
            source="edhrec",
            summary="Card recommendations, synergies, and deck statistics",
        ))

        # Moxfield search link (since API doesn't filter well)
        guides.append(Guide(
            title=f"Search Moxfield for {commander_name} primers",
            url=self.get_moxfield_search_url(commander_name),
            source="moxfield",
            summary="Search for community deck primers on Moxfield",
        ))

        return guides


def print_guides(guides: list[Guide]):
    """Pretty print a list of guides."""
    print(f"\nFound {len(guides)} guides/resources:\n")
    for i, guide in enumerate(guides, 1):
        print(f"{i}. [{guide.source.upper()}] {guide.title}")
        print(f"   {guide.url}")
        if guide.summary:
            # Truncate long summaries
            summary = guide.summary[:150] + "..." if len(guide.summary) > 150 else guide.summary
            print(f"   {summary}")
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python guides.py <commander_name>")
        print("       python guides.py --deck <deck_dir>")
        print()
        print("Examples:")
        print("  python guides.py 'Tannuk, Memorial Ensign'")
        print("  python guides.py --deck decks/tannuk")
        sys.exit(1)

    fetcher = GuideFetcher()

    if sys.argv[1] == "--deck":
        from deck import Deck
        deck_dir = sys.argv[2]
        deck = Deck.load(deck_dir)
        if not deck.commanders:
            print("Deck has no commander")
            sys.exit(1)
        commander = deck.commanders[0].name
    else:
        commander = sys.argv[1]

    print(f"Searching for guides: {commander}")
    guides = fetcher.get_all_guides(commander)
    print_guides(guides)

"""Entry point: python3 -m nba2.v4  (writes the v4 pages into site/)."""

from .build import build

if __name__ == "__main__":
    pages = build()
    print(f"built {len(pages)} pages: {', '.join(pages)}")

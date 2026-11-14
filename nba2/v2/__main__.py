"""Entry point: python3 -m nba2.v2"""
import json, sys
from .build import build

if __name__ == "__main__":
    pages, summary = build()
    print(f"built {len(pages)} pages:", ", ".join(pages))
    print(f"{len(summary['lines'])} lines, {len(summary['teams'])} teams")

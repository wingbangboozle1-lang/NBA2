"""Entry point: python3 -m nba2.v3  (build the v3 pages into site/)."""
from .build import build

if __name__ == "__main__":
    pages, summary = build()
    print(f"built {len(pages)} pages: {', '.join(pages)}")
    g = summary["gates"]
    print(f"gates: {g['n_pass']} pass / {g['n_fail']} fail, publishable={g['publishable']}")
    print(f"seal: {summary['seal']['file']}  {summary['seal']['n']} rows  "
          f"{summary['seal']['digest'][:16]}")

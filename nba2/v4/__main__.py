"""``python -m nba2.v4`` — measure the capture and print the gates.

The gates are the point of the v4 surface: a capture is only worth publishing if the
mean of its rows reproduces the rates the official page prints for the same player.
This is the command that says whether it does, and it exits non-zero if it does not,
so a scheduled run fails loudly instead of quietly shipping a wrong number.
"""

from __future__ import annotations

import sys

from . import gamelog as GL
from . import official as O


def main() -> int:
    players = GL.players()
    gates = GL.gates()
    failures = [g for g in gates if g["status"] != "PASS"]

    print(f"nba2.v4 — player-level capture ({O.GAMELOGS.parent.name})")
    print(f"  {len(players)} player(s), "
          f"{sum(len(p['games']) for p in players)} official player-game(s)")
    print(f"  {len(gates)} gate(s) measured, {len(gates) - len(failures)} pass, "
          f"{len(failures)} fail")
    for g in gates:
        print(f"  [{g['status']}] {g['id']} {g['player']}: {g['name']} — {g['measurement']}")
    if failures:
        print("\nFAILED — the capture does not reproduce the official rates; "
              "nothing about it should be published.")
        return 1
    print("\nOK — every captured player reproduces the official rates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Settlement rules (adopted before any bet is placed)

This file is policy, not code output. It exists so that how a bet is graded is
decided before there is a result to argue about. Changing it is an owner decision,
and any change applies only to bets placed after the change.

## moneyline
- **win** — the selected club has more points in the official final score
- **loss** — the other club has more points in the official final score
- **push** — impossible; an official final score is never tied (games go to overtime)
- **source** — official final score, nba.com/game/<slug>

## spread
- **win** — selected side's margin plus its handicap is strictly greater than zero
- **loss** — selected side's margin plus its handicap is strictly less than zero
- **push** — the result lands exactly on the handicap; the bet is void and removed from both the numerator and the denominator of every rate
- **source** — official final score, nba.com/game/<slug>

## total
- **win** — the official combined score is strictly on the side taken (over or under) of the reference total named in the bet record
- **loss** — the official combined score is strictly on the other side
- **push** — the official combined score equals the reference exactly; void and removed
- **source** — official final score, nba.com/game/<slug>

## parlay
- **win** — every leg wins; the parlay pays as one bet
- **loss** — any leg loses; the parlay loses as one bet regardless of the other legs
- **push** — one or more legs push and none lose: the parlay is REDUCED (pushed legs are removed and the price is recomputed on the remainder) and is recorded as a reduced bet, never as a win
- **source** — the official final score of every game named by a leg

## player_prop
- **win** — the player's official box-score figure is strictly on the side taken
- **loss** — the figure is strictly on the other side
- **push** — the figure equals the line exactly, OR the player does not appear in the official box score for that game (a non-appearance voids the bet)
- **source** — official box score, nba.com/game/<slug>/box-score

## When a bet is graded
- a bet is graded after the game's official status is FINAL and the result has been read off two official surfaces; a game with only one captured surface is not settled

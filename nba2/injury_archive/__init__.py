"""Official NBA injury-report archive: parse stored PDF bytes, diff consecutive releases.

Session arena/3a56251c-nba2 (task 3A-03). Reads only bytes already stored in
``data/raw/pdf/``; never fetches over the network and never invents a cell.
"""

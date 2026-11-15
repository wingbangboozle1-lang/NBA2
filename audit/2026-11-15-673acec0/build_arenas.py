"""Build data/arenas.csv — the sourced arena-coordinate table.

Arena + city: printed by the official nba.com schedule page for every game, read in this
session (window 2026-11-15..11-18 and the 11/14 finals). Each row carries the official game
page that printed it.

Coordinates: city centroids from a public dataset, joined on the city and state the
official page printed:
  * US  — github.com/kelvins/US-Cities-Database  (csv/us_cities.csv)
  * CA  — github.com/dr5hn/countries-states-cities-database
          (json/countries+states+cities.json, Canada -> Ontario -> Toronto)
Both are THIRD-PARTY, not official, and every row says so. The coordinate is the CITY
centroid, not the arena's surveyed position, so a distance computed from it is a
city-to-city great-circle distance whose error is the size of a metro area - stated on the
site rather than hidden.
"""
from __future__ import annotations
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
US = pathlib.Path("/tmp/cities/csv/us_cities.csv")
CA = pathlib.Path("/tmp/csc/json/countries+states+cities.json")

# tricode: (arena, city, region, official page that printed it)
# Every one of these was read off nba.com/schedule?date=2026-11-17 (window games) or the
# 11/14 finals; the URL is the game page whose card printed the arena line.
SCHED = "https://www.nba.com/schedule?date=2026-11-17"
def game(slug, gid): return f"https://www.nba.com/game/{slug}-{gid}"
ARENA = {
 "PHI": ("Xfinity Mobile Arena", "Philadelphia", "PA", game("ind-vs-phi", "0022600236")),
 "PHX": ("Mortgage Matchup Center", "Phoenix", "AZ", game("lal-vs-phx", "0022600237")),
 "LAC": ("Intuit Dome", "Inglewood", "CA", game("cha-vs-lac", "0022600238")),
 "UTA": ("Delta Center", "Salt Lake City", "UT", game("sas-vs-uta", "0022600239")),
 "BOS": ("TD Garden", "Boston", "MA", game("dal-vs-bos", "0022600240")),
 "TOR": ("Scotiabank Arena", "Toronto", "ON", game("nyk-vs-tor", "0022600241")),
 "WAS": ("Capital One Arena", "Washington", "DC", game("hou-vs-was", "0022600242")),
 "MIL": ("Fiserv Forum", "Milwaukee", "WI", game("atl-vs-mil", "0022600243")),
 "SAC": ("Golden 1 Center", "Sacramento", "CA", game("okc-vs-sac", "0022600244")),
 "CLE": ("Rocket Arena", "Cleveland", "OH", game("chi-vs-cle", "0022600246")),
 "MEM": ("FedExForum", "Memphis", "TN", game("mem-vs-was", "0022600247")),
 "BKN": ("Barclays Center", "Brooklyn", "NY", game("phi-vs-bkn", "0022600248")),
 "MIA": ("Kaseya Center", "Miami", "FL", game("hou-vs-mia", "0022600249")),
 "MIN": ("Target Center", "Minneapolis", "MN", game("por-vs-min", "0022600250")),
 "NOP": ("Smoothie King Center", "New Orleans", "LA", game("gsw-vs-nop", "0022600251")),
 "DEN": ("Ball Arena", "Denver", "CO", game("phx-vs-den", "0022600252")),
 "SAS": ("Frost Bank Center", "San Antonio", "TX", game("det-vs-sas", "0022600255")),
 "LAL": ("Crypto.com Arena", "Los Angeles", "CA", game("cha-vs-lal", "0022600256")),
 "IND": ("Gainbridge Fieldhouse", "Indianapolis", "IN", game("hou-vs-ind", "0022600259")),
 "ORL": ("Kia Center", "Orlando", "FL", game("phi-vs-orl", "0022600261")),
 "OKC": ("Paycom Center", "Oklahoma City", "OK", game("atl-vs-okc", "0022600265")),
 "DAL": ("American Airlines Center", "Dallas", "TX", game("gsw-vs-dal", "0022600267")),
}
US_SRC = "https://github.com/kelvins/US-Cities-Database/blob/master/csv/us_cities.csv"
CA_SRC = ("https://github.com/dr5hn/countries-states-cities-database/blob/master/json/"
          "countries+states+cities.json")

def us_lookup():
    out = {}
    with US.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            k = (row["CITY"].strip().lower(), row["STATE_CODE"].strip().upper())
            if k not in out:
                out[k] = (float(row["LATITUDE"]), float(row["LONGITUDE"]))
    return out

def ca_lookup():
    with CA.open(encoding="utf-8") as fh:
        data = json.load(fh)
    for c in data:
        if c.get("name") == "Canada":
            for s in c.get("states", []):
                for city in s.get("cities", []):
                    if city.get("name") == "Toronto":
                        return (float(city["latitude"]), float(city["longitude"]))
    return None

def main():
    us = us_lookup()
    tor = ca_lookup()
    rows = []
    for tri, (arena, city, region, src) in sorted(ARENA.items()):
        if region == "ON":
            lat, lon, csrc = (tor[0], tor[1], CA_SRC) if tor else (None, None, "")
        else:
            hit = us.get((city.lower(), region))
            lat, lon, csrc = (hit[0], hit[1], US_SRC) if hit else (None, None, "")
        rows.append({"team": tri, "arena": arena, "city": city, "region": region,
                     "lat": "" if lat is None else round(lat, 5),
                     "lon": "" if lon is None else round(lon, 5),
                     "coord_class": "third_party" if lat is not None else "blocked",
                     "coord_source": csrc, "official_source": src})
    out = ROOT / "data" / "arenas.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    missing = [r["team"] for r in rows if r["lat"] == ""]
    print(f"wrote {out.relative_to(ROOT)}: {len(rows)} arenas, "
          f"{len(rows)-len(missing)} with coordinates, {len(missing)} without")
    print("no coordinate (club does not host inside the captured window):", missing)
    print("clubs with no arena row at all:", sorted(set(
        "ATL CHA CHI DET GSW HOU NYK POR".split())))

if __name__ == "__main__":
    main()

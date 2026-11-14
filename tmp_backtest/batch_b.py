import json, re, pathlib

# (date, slug, away_pts, home_pts, ot, away_rec_post, home_rec_post)
# records = the official W-L printed on each nba.com card AFTER that game
RAW = """
2026-11-01,bos-vs-orl-0022600154,108,97,0,5-1,2-4
2026-11-01,bkn-vs-ind-0022600155,98,90,0,1-5,2-5
2026-11-01,lac-vs-gsw-0022600156,112,124,0,1-5,4-3
2026-11-01,tor-vs-lal-0022600157,125,131,0,3-3,5-2
2026-11-02,okc-vs-cle-0022600158,117,112,0,5-2,4-3
2026-11-02,chi-vs-phi-0022600163,107,126,0,1-6,7-1
2026-11-02,atl-vs-ind-0022600160,108,104,0,4-4,2-6
2026-11-02,bkn-vs-nyk-0022600161,90,103,0,1-6,3-4
2026-11-02,was-vs-orl-0022600162,103,94,0,4-3,2-5
2026-11-02,dal-vs-cha-0022600159,124,91,0,6-1,3-5
2026-11-02,sac-vs-dal-0022600164,115,100,0,1-6,4-3
2026-11-02,mil-vs-min-0022600166,100,112,0,1-6,5-3
2026-11-02,nop-vs-mem-0022600165,135,134,1,3-4,6-1
2026-11-02,bos-vs-hou-0022600167,93,109,0,5-2,7-1
2026-11-02,uta-vs-sas-0022600168,97,119,0,1-6,5-2
2026-11-02,por-vs-den-0022600169,118,110,0,5-1,3-3
2026-11-02,tor-vs-lac-0022600171,125,118,0,4-3,1-6
2026-11-02,phx-vs-gsw-0022600170,113,116,0,1-4,5-3
2026-11-02,mia-vs-lal-0022600172,117,138,0,2-5,6-2
"""

games, rec = [], []
for line in RAW.strip().splitlines():
    date, slug, a, h, ot, ar, hr = line.split(",")
    m = re.fullmatch(r"([a-z]{3})-vs-([a-z]{3})-(\d{10})", slug); assert m, slug
    games.append({"game_id": m.group(3), "date": date, "away": m.group(1).upper(),
                  "home": m.group(2).upper(), "away_pts": int(a), "home_pts": int(h),
                  "ot": bool(int(ot)),
                  "source_url": f"https://www.nba.com/game/{slug}",
                  "list_url": f"https://www.nba.com/games?date={date}"})
    for side, team, r in (("away", m.group(1).upper(), ar), ("home", m.group(2).upper(), hr)):
        w, l = r.split("-")
        rec.append({"game_id": m.group(3), "date": date, "team": team, "side": side,
                    "wins": int(w), "losses": int(l),
                    "source_url": f"https://www.nba.com/game/{slug}",
                    "list_url": f"https://www.nba.com/games?date={date}"})

games.sort(key=lambda g: (g["date"], g["game_id"]))
doc = {"schema": "nba2.games-history.v1",
       "meta": {"captured_utc": "2026-11-14",
                "source": "https://www.nba.com/games?date=YYYY-MM-DD (official final scores)",
                "date_range": [games[0]["date"], games[-1]["date"]],
                "n_games": len(games),
                "note": "Every game carries its own nba.com/game/{id} URL."},
       "games": games}
pathlib.Path("data/raw/history/games_2026-11-01_to_2026-11-02.json").write_text(json.dumps(doc, indent=1)+"\n")
rdoc = {"schema": "nba2.postgame-records.v1",
        "meta": {"captured_utc": "2026-11-14",
                 "meaning": "Official team W-L printed on the nba.com game card immediately after that game. Used to CHECK a reconstruction of records from final scores; never used as a model input.",
                 "n_rows": len(rec)},
        "rows": rec}
pathlib.Path("data/raw/history/postgame_records_2026-11-01_to_2026-11-02.json").write_text(json.dumps(rdoc, indent=1)+"\n")
print("games", len(games), "record rows", len(rec))

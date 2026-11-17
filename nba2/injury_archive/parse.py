"""Coordinate-based parser for official NBA injury-report PDFs (GemBox output).

Method
------
pypdf's visitor gives each text fragment's text matrix *and* the page's current
transformation matrix (CTM). The CTM of these PDFs flips y (cm = [1,0,0,-1,0,H]), so the
true visual position is ``x = tm[4]*cm[0] + tm[5]*cm[2] + cm[4]`` and
``y_top = H - (tm[4]*cm[1] + tm[5]*cm[3] + cm[5])`` (top of the page = 0).

Columns are fixed x-ranges measured from the page-1 header words (Game Date 23, Game Time
120, Matchup 200, Team 264, Player 426, Current Status 586, Reason 667). Reason text wraps
onto lines above and below its player row; each reason fragment is attached to the nearest
player row on the same page, and a fragment that is not clearly closest to one row is
recorded as a parse problem, never guessed. Game date / time / matchup and team names are
read from their own lines in reading order.

Every value is a substring of the PDF's extracted text; nothing is inferred.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

STATUSES = {"Out", "Available", "Questionable", "Probable", "Doubtful"}
RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_TIME = re.compile(r"^\d{2}:\d{2}$")
RE_MATCHUP = re.compile(r"^[A-Z]{3}@[A-Z]{3}$")
RE_HEADER_LINE = re.compile(r"^(Injury Report:|Page \d+ of \d+$|Game Date Game Time)")
NOT_SUBMITTED = "NOT YET SUBMITTED"

COL_DATE_MAX = 100.0      # game date column: x < 100
COL_TIME_MIN, COL_TIME_MAX = 100.0, 190.0
COL_MATCHUP_MIN, COL_MATCHUP_MAX = 190.0, 250.0
COL_TEAM_MIN, COL_TEAM_MAX = 250.0, 415.0
COL_PLAYER_MIN, COL_PLAYER_MAX = 415.0, 575.0
COL_STATUS_MIN, COL_STATUS_MAX = 575.0, 660.0
COL_REASON_MIN = 660.0
MAX_ROW_DISTANCE_PT = 12.0
TOP_OF_PAGE_Y = 100.0  # fragments above this y_top, before the first row, are page-break carry-over


def _fragments(pdf_path: Path):
    """Per page: list of (y_top, x, text) in visual coordinates, plus page height."""
    import pypdf  # optional dependency: needed only to regenerate the archive

    reader = pypdf.PdfReader(str(pdf_path))
    out = []
    for page in reader.pages:
        height = float(page.mediabox.height)
        frags: list[tuple[float, float, str]] = []

        def visitor(text, cm, tm, font_dict, font_size, _f=frags, _h=height):
            t = text.strip()
            if not t:
                return
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y_up = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            _f.append((round(_h - y_up, 1), round(x, 1), t))

        page.extract_text(visitor_text=visitor)
        out.append((height, frags))
    return out


def _lines(frags):
    """Group fragments into visual lines (y_top within 2 pt), reading order (top first, left first)."""
    groups: list[list] = []
    for f in sorted(frags, key=lambda f: (f[0], f[1])):
        if groups and abs(groups[-1][0][0] - f[0]) <= 2.0:
            groups[-1].append(f)
        else:
            groups.append([f])
    return [sorted(g, key=lambda f: f[1]) for g in groups]


def parse_pdf(pdf_path: Path) -> dict:
    problems: list[str] = []
    header_stamp = None
    events = []  # (page, y_top, order, kind, payload)
    player_rows: list[dict] = []
    pages = _fragments(pdf_path)
    prev_page_last_row: dict | None = None

    for pno, (_, frags) in enumerate(pages, start=1):
        lines = []
        for line in _lines(frags):
            text = " ".join(t for _, _, t in line)
            if RE_HEADER_LINE.match(text):
                m = re.search(r"Injury Report: (\d{2}/\d{2}/\d{2}) (\d{2}:\d{2} [AP]M)", text)
                if m and header_stamp is None:
                    header_stamp = (m.group(1), m.group(2))
                continue
            lines.append((line[0][0], line))

        page_rows = []
        for y, line in lines:
            status_frags = [f for f in line if COL_STATUS_MIN <= f[1] < COL_STATUS_MAX and f[2] in STATUSES]
            if status_frags:
                if len(status_frags) != 1:
                    problems.append(f"p{pno} y={y}: {len(status_frags)} status words on one line")
                    continue
                name = " ".join(f[2] for f in line if COL_PLAYER_MIN <= f[1] < COL_PLAYER_MAX)
                if not name:
                    problems.append(f"p{pno} y={y}: status with no player name")
                    continue
                reason_here = " ".join(f[2] for f in line if f[1] >= COL_REASON_MIN)
                row = {"page": pno, "y": y, "player": name, "status": status_frags[0][2], "reason_parts": []}
                if reason_here:
                    row["reason_parts"].append((y, reason_here))
                row["tail_parts"] = []
                page_rows.append(row)
                events.append((pno, y, 1, "row", len(player_rows)))
                player_rows.append(row)

            # game-context line
            ctx = {}
            for _, x, t in line:
                if x < COL_DATE_MAX and RE_DATE.match(t):
                    ctx["date"] = t
                elif COL_TIME_MIN <= x < COL_TIME_MAX and RE_TIME.match(t):
                    ctx["time"] = t
                elif COL_MATCHUP_MIN <= x < COL_MATCHUP_MAX and RE_MATCHUP.match(t):
                    ctx["matchup"] = t
            if ctx:
                events.append((pno, y, 0, "game", ctx))

            # team-name line (team column text, not a player row)
            team_text = " ".join(t for _, x, t in line if COL_TEAM_MIN <= x < COL_TEAM_MAX)
            reason_text = " ".join(t for _, x, t in line if x >= COL_REASON_MIN)
            if team_text and not status_frags:
                if reason_text == NOT_SUBMITTED:
                    events.append((pno, y, 0, "team", (team_text, NOT_SUBMITTED)))
                else:
                    events.append((pno, y, 0, "team", (team_text, None)))
            elif team_text and status_frags:
                events.append((pno, y, 0, "team", (team_text, None)))

        # continuation fragments: reason text on lines with no status word
        for y, line in lines:
            if any(COL_STATUS_MIN <= f[1] < COL_STATUS_MAX and f[2] in STATUSES for f in line):
                continue
            frags_r = [f for f in line if f[1] >= COL_REASON_MIN]
            if not frags_r:
                continue
            if " ".join(f[2] for f in frags_r) == NOT_SUBMITTED:
                continue
            text = " ".join(f[2] for f in frags_r)
            if not page_rows:
                problems.append(f"p{pno} y={y}: reason text with no player row on page: {text!r}")
                continue
            dists = sorted((abs(r["y"] - y), i) for i, r in enumerate(page_rows))
            if len(dists) > 1 and dists[0][0] == dists[1][0]:
                problems.append(f"p{pno} y={y}: ambiguous reason continuation {text!r}")
                continue
            if dists[0][0] > MAX_ROW_DISTANCE_PT:
                # A reason that wraps over the page break: a fragment above the first row of a
                # page belongs to the last row of the previous page (confirmed against the
                # flattened text, e.g. "Soreness" after "Kessler, Walker ... Injury/Illness - Right Lower Leg").
                first_row_y = min(r["y"] for r in page_rows)
                if y < first_row_y and prev_page_last_row is not None and y < TOP_OF_PAGE_Y:
                    prev_page_last_row["tail_parts"].append((y, text))
                    prev_page_last_row["crossed_page"] = True
                    continue
                problems.append(f"p{pno} y={y}: reason continuation {text!r} is {dists[0][0]:.1f}pt from nearest row")
                continue
            page_rows[dists[0][1]]["reason_parts"].append((y, text))
        if page_rows:
            prev_page_last_row = max(page_rows, key=lambda r: (r["y"]))

    # resolve the document-order stream
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    rows_out, teams_out = [], []
    game = {"date": None, "time": None, "matchup": None}
    team = None
    game_started = False
    for pno, y, _, kind, payload in events:
        if kind == "game":
            # a new game line: take date/time/matchup it carries; date carries forward within the release
            new = {"date": payload.get("date", game["date"]), "time": payload.get("time"), "matchup": payload.get("matchup", game["matchup"])}
            if "date" not in payload and game["date"] is not None:
                new["date_carried"] = True
            game = new
            team = None
            game_started = True
        elif kind == "team":
            name, marker = payload
            if not game_started:
                problems.append(f"p{pno} y={y}: team {name!r} before any game line")
            team = name
            if marker == NOT_SUBMITTED:
                teams_out.append({"game_date": game["date"], "time_et": game["time"], "matchup": game["matchup"],
                                  "team": name, "status_line": NOT_SUBMITTED, "page": pno})
                team = None
        else:
            r = player_rows[payload]
            # own reason lines (reading order), then any tail that wrapped onto the next page
            reason = " ".join(t for _, t in sorted(r["reason_parts"], key=lambda p: p[0]) + sorted(r["tail_parts"], key=lambda p: p[0]))
            crossed = bool(r.get("crossed_page"))
            if team is None:
                problems.append(f"p{pno} y={y}: player {r['player']!r} has no team line above it")
            if game["matchup"] is None:
                problems.append(f"p{pno} y={y}: player {r['player']!r} has no game line above it")
            rows_out.append({
                "game_date": game["date"], "time_et": game["time"], "matchup": game["matchup"],
                "date_carried": bool(game.get("date_carried")),
                "team": team, "player": r["player"], "status": r["status"], "reason": reason,
                "page": r["page"],
                "reason_crossed_page_break": crossed,
            })

    return {
        "header_stamp": header_stamp,
        "page_count": len(pages),
        "status_tokens": len(player_rows),
        "rows": rows_out,
        "team_not_submitted": teams_out,
        "problems": problems,
    }

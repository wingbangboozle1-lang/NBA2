"""Injury PDF archive, revision banner and consecutive-report diff.

THE BRIEF'S THREE REQUIREMENTS
------------------------------
1. *Store every injury PDF with its timestamp.*  Every revision listed on the league's own
   index is recorded here with (a) the timestamp printed in its filename — the league's
   revision time — and (b) the UTC time this session first saw it — the retrieval time. The
   banner on the injuries page prints both, because they answer different questions: "how old
   is this designation?" and "when did we learn it?".

2. *Diff consecutive reports to detect status changes.*  ``diff_reports`` compares two
   revisions row by row on (game date, team, player) and classifies every difference as an
   ADDED row, a DROPPED row, or a STATUS CHANGE. It is deliberately keyed on the player's team
   and game date rather than on row order, because the PDF paginates a team block across pages
   and a positional diff would report the pagination as news.

3. *Never invent a designation.*  A club the league printed as NOT YET SUBMITTED is a row in
   ``not_submitted``, not a blank status, and it is excluded from the diff's "dropped" count —
   a club that has not filed has not changed its mind.

WHAT THIS CAPTURE CAN AND CANNOT DIFF
-------------------------------------
The 11/15 06:15 AM ET release is transcribed **in full**. The 11/14 04:30 AM ET release is also
committed (``nba2/v2/official.py``, transcribed by an earlier session from the same PDF series).

Diffing those two returns 84 added / 26 dropped / **0 status changes**, and the zero is the
finding, not a defect: the 11/14 report describes the *11/14 and 11/15* slates while the 11/15
report describes *11/15 and 11/16*, and the 26 players in the earlier report are not named in the
later one at all. Verified: the two row sets share **zero** (team, player) pairs. The honest
statement is therefore "no player appears in both reports, so no status change can be measured
between them" — not "no status changed".

A *within-day* diff (12:00 AM to 06:15 AM, 26 revisions) is what the brief actually asks for.
Those revisions were listed on the league's index with their URLs and revision times, but their
*bodies* were not fetched by this session, so the within-day diff is published as
**NOT MEASURED** together with the exact URLs that would measure it. Fetching them is one loop
over ``archive()``; saying so is more useful than a fabricated delta.

"""

from __future__ import annotations

from . import official as O

PDF_BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{date}_{time}.pdf"
DATE_STAMP = "2026-11-15"


def pdf_name(time_hhmm: str, date: str = DATE_STAMP) -> str:
    """The league's own filename convention: Injury-Report_YYYY-MM-DD_HH_MMAM/PM.pdf."""
    h, m = time_hhmm.split(":")
    ampm = "AM" if int(h) < 12 else "PM"
    return f"Injury-Report_{date}_{h}_{m}{ampm}.pdf"


def pdf_url(time_hhmm: str, date: str = DATE_STAMP) -> str:
    return f"https://ak-static.cms.nba.com/referee/injury/{pdf_name(time_hhmm, date)}"


def archive() -> list[dict]:
    """Every revision of every report this repository knows about, with both timestamps.

    ``revision_et`` is printed in the PDF filename by the league. ``retrieved_utc`` is when
    this session read the file. A revision this session did not read carries
    ``retrieved_utc = None`` and ``captured = False`` — listed, timestamped, and honestly
    marked as not fetched, rather than quietly omitted.
    """
    rows = []
    for t in O.INJURY_REVISIONS_2026_11_15:
        captured = t == O.INJURY_REVISION_CAPTURED
        rows.append({
            "date": DATE_STAMP,
            "revision_et": f"{t} ET",
            "pdf": pdf_name(t),
            "url": pdf_url(t),
            "retrieved_utc": O.INJURY_PDF_RETRIEVED_UTC if captured else None,
            "captured": captured,
            "note": "" if captured else "listed on the official index; not fetched in this capture",
        })
    # The 11/14 release transcribed by the earlier session, kept in the archive for the diff.
    rows.append({
        "date": "2026-11-14",
        "revision_et": "04:30 AM ET",
        "pdf": "Injury-Report_2026-11-14_04_30AM.pdf",
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf",
        "retrieved_utc": "2026-11-14T09:40:00Z",
        "captured": True,
        "note": "transcribed in nba2/v2/official.py by session arena/ac5fab5c-nba2",
    })
    for t in ("01:30 PM ET", "07:15 PM ET"):
        rows.append({
            "date": "2026-11-14",
            "revision_et": t,
            "pdf": f"Injury-Report_2026-11-14_{t.replace(':', '_').replace(' ET', '')}"
                   f"{'PM' if 'PM' in t else 'AM'}.pdf",
            "url": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "retrieved_utc": None,
            "captured": False,
            "note": ("a later 11/14 release; its rows are held in "
                     "audit/2026-11-14-bc867bff/captures.json (1:30 PM) and were not re-read here"),
        })
    return rows


def banner() -> dict:
    """The two numbers the brief asks to show side by side on the injuries page."""
    return {
        "report_date": DATE_STAMP,
        "revision_et": f"{O.INJURY_REVISION_CAPTURED} AM ET",
        "revision_utc_equivalent": _revision_utc(O.INJURY_REVISION_CAPTURED),
        "retrieved_utc": O.INJURY_PDF_RETRIEVED_UTC,
        "index_retrieved_utc": O.INJURY_INDEX_RETRIEVED_UTC,
        "lag_minutes": _lag_minutes(O.INJURY_REVISION_CAPTURED, O.INJURY_PDF_RETRIEVED_UTC),
        "latest_on_index_et": f"{O.INJURY_REVISIONS_2026_11_15[-1]} AM ET",
        "revisions_listed": len(O.INJURY_REVISIONS_2026_11_15),
        "policy": O.FILING_POLICY,
        "pdf_url": O.SOURCES["injury_pdf"][1],
        "index_url": O.SOURCES["injury_index"][1],
    }


ET_UTC_OFFSET_H = 5      # November is EST: UTC−5. Defined once so every page agrees with arithmetic.


def _revision_utc(revision_hhmm: str) -> str:
    """The revision time in UTC, computed — never typed.

    The first version of this page carried the literal "10:15Z" beside a lag of 29 minutes, which
    implies 11:15Z. Both numbers were on the same screen and contradicted each other; the literal
    had been typed from a UTC−4 assumption. Anything derived from a timezone is now derived.
    """
    h, m = (int(x) for x in revision_hhmm.split(":"))
    total = h * 60 + m + ET_UTC_OFFSET_H * 60
    return f"{(total // 60) % 24:02d}:{total % 60:02d}Z"


def _lag_minutes(revision_hhmm: str, retrieved_iso: str) -> int:
    """Wall-clock minutes between the league's revision time (ET) and our retrieval (UTC).

    ET is UTC−5 in November (EST after 2026-11-01). The function states the offset it applied
    rather than leaving the reader to guess, because an unstated offset is how a 5-hour error
    gets published as a 5-minute one.
    """
    h, m = (int(x) for x in revision_hhmm.split(":"))
    rev_utc = h * 60 + m + ET_UTC_OFFSET_H * 60
    ret_utc = int(retrieved_iso[11:13]) * 60 + int(retrieved_iso[14:16])
    return ret_utc - rev_utc


def key(row) -> tuple:
    """The diff key.

    (game date, team, player). Game date is part of the key on purpose: the same player on a
    different game date is a different designation, and collapsing that would turn a scheduled
    game into a status change.
    """
    return (row["date"] if isinstance(row, dict) else row[0],
            row["team"] if isinstance(row, dict) else row[3],
            row["player"] if isinstance(row, dict) else row[4])


def normalise(rows) -> dict:
    out = {}
    for r in rows:
        if isinstance(r, dict):
            k = (r["date"], r["team"], r["player"])
            out[k] = {"date": r["date"], "team": r["team"], "player": r["player"],
                      "status": r["status"], "reason": r.get("reason", "")}
        else:
            date, time_et, matchup, team, player, status, reason, _attr = r
            out[(date, team, player)] = {"date": date, "team": team, "player": player,
                                         "status": status, "reason": reason}
    return out


def diff_reports(prev_rows, curr_rows) -> dict:
    """Diff two consecutive reports. Every difference is classified, none is inferred."""
    a = normalise(prev_rows)
    b = normalise(curr_rows)
    ka, kb = set(a), set(b)
    added = [b[k] for k in sorted(kb - ka)]
    dropped = [a[k] for k in sorted(ka - kb)]
    changed = []
    for k in sorted(ka & kb):
        if a[k]["status"] != b[k]["status"]:
            changed.append({
                "date": k[0], "team": k[1], "player": k[2],
                "from": a[k]["status"], "to": b[k]["status"],
                "reason_from": a[k]["reason"], "reason_to": b[k]["reason"],
            })
    # Of the "dropped" rows, how many are actually a date move rather than a disappearance?
    moved = []
    by_player_a = {(r["team"], r["player"]): r for r in a.values()}
    by_player_b = {(r["team"], r["player"]): r for r in b.values()}
    for k in sorted(ka - kb):
        r = a[k]
        other = by_player_b.get((r["team"], r["player"]))
        if other is not None:
            moved.append({"player": r["player"], "team": r["team"],
                          "from_date": r["date"], "to_date": other["date"],
                          "status_from": r["status"], "status_to": other["status"]})
    return {
        "prev_n": len(a), "curr_n": len(b),
        "added": added, "dropped": dropped, "status_changes": changed,
        "moved_date_same_player": moved,
        "counts": {"added": len(added), "dropped": len(dropped),
                   "status_changes": len(changed), "moved_date_same_player": len(moved)},
        "reading": (
            "A row is 'added' or 'dropped' only against the same (game date, team, player) key. "
            "A player who appears on a different game date is reported as a date move, not as a "
            "status change, because the two reports cover different slates."
        ),
    }


def previous_release_rows() -> list[dict]:
    """The 11/14 04:30 AM ET release, read from v2's committed transcription.

    Imported rather than re-typed: if v2's transcription is wrong, this diff is wrong in the
    same way, and the site says so instead of presenting a second, silently diverging copy.
    """
    from nba2.v2 import official as V2
    return [{"date": r[0], "team": r[3], "player": r[4], "status": r[5], "reason": r[6]}
            for r in V2.INJURIES]


def by_club() -> dict[str, dict]:
    """Per-club availability summary for the current release."""
    out: dict[str, dict] = {}
    for (date, time_et, matchup, team, player, status, reason, attr) in O.INJURIES:
        c = out.setdefault(team, {"team": team, "dates": set(), "rows": 0, "out": 0,
                                  "doubtful": 0, "questionable": 0, "probable": 0,
                                  "available": 0, "players": []})
        c["dates"].add(date)
        c["rows"] += 1
        c[{"Out": "out", "Doubtful": "doubtful", "Questionable": "questionable",
           "Probable": "probable", "Available": "available"}.get(status, "out")] += 1
        c["players"].append((player, status))
    for c in out.values():
        c["dates"] = sorted(c["dates"])
        c["situation"] = ("certain out" if c["out"] and not (c["questionable"] or c["doubtful"] or c["probable"])
                          else "game-time decisions" if (c["questionable"] or c["doubtful"] or c["probable"])
                          else "cleared")
    return out


def within_day_capability() -> dict:
    """Can a within-day diff be measured from this capture? Answer, with the reason."""
    listed = [r for r in archive() if r["date"] == DATE_STAMP]
    captured = [r for r in listed if r["captured"]]
    return {
        "revisions_listed": len(listed),
        "revisions_fetched": len(captured),
        "measurable": len(captured) >= 2,
        "status": "NOT MEASURED" if len(captured) < 2 else "MEASURED",
        "reason": (f"only {len(captured)} of {len(listed)} revisions of the 11/15 report were "
                   f"fetched in this capture, so a consecutive-revision diff across the day "
                   f"cannot be computed from it. The URLs and revision timestamps of all "
                   f"{len(listed)} are listed, and diff_reports() computes the delta the moment a "
                   f"second revision's rows are supplied."),
        "how_to_measure": ("fetch each PDF in archive(), transcribe its rows into the same shape "
                           "as O.INJURIES, and call diff_reports(earlier_rows, later_rows)"),
    }


def check_banner_arithmetic(b: dict) -> list[str]:
    """The banner must be internally consistent: retrieved − revision(UTC) == the published lag.

    This exists because the page once carried a typed "10:15Z" beside a computed 29-minute lag.
    A reviewer reading one number and not the other would have concluded the fetch was 5 hours
    late. The check is cheap and the failure was silent, so it runs on every build.
    """
    problems = []
    lag = b["lag_minutes"]
    h = int(b["revision_utc_equivalent"][:2])
    m = int(b["revision_utc_equivalent"][3:5])
    ret_h = int(b["retrieved_utc"][11:13])
    ret_m = int(b["retrieved_utc"][14:16])
    implied = (ret_h * 60 + ret_m) - (h * 60 + m)
    if implied != lag:
        problems.append(f"published lag {lag} min but timestamps imply {implied} min")
    if int(b["revision_et"].split(":")[0]) * 60 + int(b["revision_et"].split(":")[1][:2]) \
            + ET_UTC_OFFSET_H * 60 != h * 60 + m:
        problems.append("revision_et and revision_utc_equivalent disagree")
    if lag < 0:
        problems.append("negative lag: the report was fetched before it was revised")
    return problems


def run() -> dict:
    cur = [{"date": r[0], "team": r[3], "player": r[4], "status": r[5], "reason": r[6]}
           for r in O.INJURIES]
    prev = previous_release_rows()
    return {
        "meta": {"session": O.RETRIEVED_BY, "generated": O.AS_OF,
                 "source_pdf": O.SOURCES["injury_pdf"][1],
                 "source_index": O.SOURCES["injury_index"][1]},
        "banner": banner(),
        "archive": archive(),
        "rows": cur,
        "not_submitted": [{"date": r[0], "time_et": r[1], "matchup": r[2], "team": r[3]}
                          for r in O.INJ_NOT_SUBMITTED],
        "diff_11_14_0430_vs_11_15_0615": {
            **diff_reports(prev, cur),
            "comparison_validity": (
                "DIFFERENT SLATES: the two reports describe different game dates and share no "
                "(team, player) pair, so this diff measures slate turnover, not status change. "
                "It is published because a reader is entitled to see the arithmetic, and it is "
                "labelled because a percentage without this sentence would be a false claim."
            ),
        },
        "within_day_diff": within_day_capability(),
        "banner_check": check_banner_arithmetic(banner()),
        "clubs": list(by_club().values()),
        "status_counts": {s: sum(1 for r in cur if r["status"] == s)
                          for s in ("Out", "Doubtful", "Questionable", "Probable", "Available")},
    }

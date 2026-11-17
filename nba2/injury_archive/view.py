"""Render the official injury-report archive for the Injuries page (stdlib only: reads archive.json)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "injuries" / "archive" / "archive.json"


def load() -> dict:
    return json.loads(ARCHIVE.read_text())


def _et_label(iso: str | None) -> str:
    """'2026-11-17T09:45:00-05:00' -> '2026-11-17 09:45 AM ET'."""
    if not iso:
        return "not recorded"
    import datetime as dt
    return dt.datetime.fromisoformat(iso).strftime("%Y-%m-%d %I:%M %p ET")


def _utc_label(iso: str | None) -> str:
    return iso if iso else "not recorded in the repository"


def banner_html(arch: dict, esc, srclink) -> str:
    latest = arch["releases"][-1]
    rel_link = srclink(latest["pdf_url"], latest["pdf_file"].split("/")[-1])
    return (
        '<div class="note bad"><b>Newest official injury release stored in this repository: '
        f'{esc(latest["report_stamp_et"])} ET.</b> '
        f'Revision time: <b>{esc(_et_label(latest["revision_time_et"]))}</b> '
        f'(the PDF\'s own creation time, {esc(latest["pdf_creation_time"])}, agrees with it). '
        f'Retrieval time: <b>{esc(_utc_label(latest["retrieved_at_utc"]))}</b>. '
        f'Source: {rel_link}. '
        'The table below this banner is the <b>11/15 06:15 AM ET</b> capture and is older than the release named here; it is '
        'not replaced by it. '
        f'Gap, flagged and not inferred: {esc(arch["latest_release_gap"])}</div>'
    )


def _release_rows(arch: dict, esc, srclink, badge):
    rows = []
    for r in arch["releases"]:
        c = r["checks"]
        ok = (c["parse_problems"] == 0 and c["status_count_matches_plain_text"]
              and c["not_yet_submitted_matches_plain_text"] and c["every_player_name_in_plain_text"]
              and c["pdf_creation_utc_matches_header"])
        txt = ("stored .txt matches" if c.get("stored_txt_matches_parsed") else
               ("no stored .txt" if not c.get("stored_txt_present") else "stored .txt DIFFERS"))
        rows.append({"id": r["release_id"], "cells": [
            esc(r["report_stamp_et"]),
            esc(_et_label(r["revision_time_et"])),
            esc(_et_label(r["pdf_creation_time"])),
            esc(_utc_label(r["retrieved_at_utc"])) if r["retrieved_at_utc"] else
            '<span class="blank">not recorded in the repository</span>',
            esc(str(len(r["rows"]))),
            esc(str(len(r["team_not_submitted"]))),
            badge("PASS" if ok else "CHECK", "ok" if ok else "bad") + " " + esc(
                f"{c['status_rows_parsed']} status rows = plain text {c['status_words_plain_text']}; "
                f"NOT YET SUBMITTED {c['not_yet_submitted_parsed']} = {c['not_yet_submitted_plain_text']}; {txt}"),
            esc(f"sha256 {r['pdf_sha256'][:16]}… · {r['pdf_bytes']:,} bytes"),
            srclink(r["pdf_url"], r["pdf_file"].split("/")[-1]),
        ]})
    return rows


def _diff_block(d: dict, arch: dict, esc, srclink, table, badge) -> str:
    by_id = {r["release_id"]: r for r in arch["releases"]}
    to_url = by_id[d["to"]]["pdf_url"]
    to_name = by_id[d["to"]]["pdf_file"].split("/")[-1]
    c = d["counts"]
    head = (f'<h3>{esc(by_id[d["from"]]["report_stamp_et"])} ET → {esc(by_id[d["to"]]["report_stamp_et"])} ET</h3>'
            f'<p class="lede">Added {c["added"]} · removed {c["removed"]} · status changed {c["status_changed"]} · '
            f'reason changed {c["reason_changed"]} · team newly NOT YET SUBMITTED {c["team_newly_not_submitted"]} · '
            f'team newly submitted {c["team_newly_submitted"]}.</p>')
    chg = []
    for x in d["status_changed"]:
        k = x["key"]
        chg.append({"id": f"{d['to']}-s-{k[1]}-{k[3]}".replace(" ", "-").replace(",", ""), "cells": [
            esc(k[0]), esc(k[1]), esc(k[2]), esc(k[3]), esc(x["from"]), badge(x["to"], "bad" if x["to"] == "Out" else "warn"),
            esc(x["reason_to"]), srclink(to_url, to_name)]})
    for x in d["reason_changed"]:
        k = x["key"]
        chg.append({"id": f"{d['to']}-r-{k[1]}-{k[3]}".replace(" ", "-").replace(",", ""), "cells": [
            esc(k[0]), esc(k[1]), esc(k[2]), esc(k[3]), esc(x["status"]), esc(f"reason: {x['from']} → {x['to']}"),
            esc(x["to"]), srclink(to_url, to_name)]})
    out = [head]
    if chg:
        out.append(table(["Game date", "Matchup", "Team", "Player", "Status before", "Status / change after",
                          "Reason (after)", "Source"], chg,
                         f"Changed rows, {d['from']} → {d['to']}", idcol="id"))
    else:
        out.append('<p class="blank">No status or reason changed between these two releases.</p>')
    add = []
    for x in d["added"]:
        k = x["key"]
        add.append({"id": f"{d['to']}-a-{k[1]}-{k[3]}".replace(" ", "-").replace(",", ""), "cells": [
            esc(k[0]), esc(k[1]), esc(k[2]), esc(k[3]), esc(x["status"]), esc(x["reason"]), srclink(to_url, to_name)]})
    rem = []
    for x in d["removed"]:
        k = x["key"]
        rem.append({"id": f"{d['to']}-x-{k[1]}-{k[3]}".replace(" ", "-").replace(",", ""), "cells": [
            esc(k[0]), esc(k[1]), esc(k[2]), esc(k[3]), esc(x["status"]), esc(x["reason"]),
            srclink(by_id[d["from"]]["pdf_url"], by_id[d["from"]]["pdf_file"].split("/")[-1])]})
    out.append("<details><summary><b>Added rows</b> (" + str(len(add)) + ")</summary>" +
               (table(["Game date", "Matchup", "Team", "Player", "Status", "Reason", "Source"], add,
                      f"Rows added in {d['to']}", idcol="id") if add else "<p>None.</p>") + "</details>")
    out.append("<details><summary><b>Rows absent from the later release</b> (" + str(len(rem)) + ")</summary>" +
               '<p class="lede">The report prints no reason for absence. For a game dated before the later release, '
               'absence reflects the game date passing (the game is no longer listed), not a cleared status.</p>' +
               (table(["Game date", "Matchup", "Team", "Player", "Status (earlier)", "Reason (earlier)", "Source"], rem,
                      f"Rows absent from {d['to']}", idcol="id") if rem else "<p>None.</p>") + "</details>")
    return "\n".join(out)


def section_html(arch: dict, esc, srclink, table, badge) -> str:
    rel_rows = _release_rows(arch, esc, srclink, badge)
    parts = [
        '<h2>Official injury-report archive: every stored PDF, timestamped, and diffed release-to-release</h2>',
        '<p class="lede">Each PDF in <code>data/raw/pdf/</code> was parsed from its page coordinates. Every player row was '
        'checked against an independent extraction of the same PDF (pypdf plain text, and the stored <code>.txt</code> where '
        'one exists). Times the PDF does not print stay blank; they are not borrowed from another game. Machine-readable: '
        '<code>data/injuries/archive/archive.json</code>; parser and checks: <code>nba2/injury_archive/</code>.</p>',
        table(["Release (as printed)", "Revision time", "PDF creation time", "Retrieval time", "Player rows",
               "Teams NOT YET SUBMITTED", "Checks", "File", "Source"], rel_rows,
              "Stored official releases, oldest first", num_cols=(4, 5), idcol="id"),
        '<div class="note warn"><b>Irregularities flagged for review.</b> (1) The 11/17 09:45 AM release prints the NYK@TOR game '
        'with Toronto Raptors rows only; no New York Knicks line appears anywhere in that PDF. Not inferred. '
        '(2) Some blocks print no game time (MEM@WAS, ORL@BOS, PHI@BKN, POR@MIN on 11/16; eight blocks on 11/17). The time is '
        'left blank. (3) Date cells are printed once per date group and carried to the rows below; those rows are marked '
        '<code>date_carried</code> in the JSON. (4) The row "Nurkic, Jusuf" in the 11/17 release reads "Right Right Foot; '
        '2nd Plantar Plate Tear" as printed; it is shown verbatim.</div>',
    ]
    for d in arch["diffs"]:
        parts.append(_diff_block(d, arch, esc, srclink, table, badge))
    return "\n".join(parts)

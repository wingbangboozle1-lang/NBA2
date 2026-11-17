"""Render a committed markdown analysis file as an HTML page body (stdlib only).

Supports the subset the analysis files use: headings, paragraphs, bullet and numbered lists,
pipe tables, **bold**, `code`, and bare https links. A backticked token that names an existing
repository file or directory becomes a link to that path on GitHub, so every table row carries
an https source link (the v2 checker requires one per row). A row with no such token gets a link
to the document itself.
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_BLOB = "https://github.com/wingbangboozle1-lang/NBA2/blob/main/"
REPO_TREE = "https://github.com/wingbangboozle1-lang/NBA2/tree/main/"
PATHLIKE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _code(tok: str) -> str:
    raw = tok.strip().rstrip("/")
    if PATHLIKE.match(raw) and not raw.startswith("http") and os.path.exists(ROOT / raw):
        href = (REPO_TREE if os.path.isdir(ROOT / raw) else REPO_BLOB) + raw + ("/" if os.path.isdir(ROOT / raw) else "")
        return f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener"><code>{html.escape(tok)}</code></a>'
    return f"<code>{html.escape(tok)}</code>"


def _inline(text: str) -> str:
    out = []
    for i, seg in enumerate(re.split(r"`", text)):
        if i % 2 == 1:
            out.append(_code(seg))
            continue
        s = html.escape(seg)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(https://[^\s<)]+)", lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
        out.append(s)
    return "".join(out)


def _table(lines: list[str], doc_href: str) -> str:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    head, body = rows[0], [r for r in rows[2:]]
    out = ['<div class="scroll"><table>', "<thead><tr>"]
    out += [f"<th scope=\"col\">{_inline(h)}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        cells = [_inline(c) if c else '<span class="blank">—</span>' for c in r]
        joined_html = " ".join(cells)
        if "href=" not in joined_html:
            cells[0] = cells[0] + f' <a href="{html.escape(doc_href, quote=True)}" target="_blank" rel="noopener">[source document]</a>'
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def render(md_path: Path, doc_href: str) -> str:
    lines = md_path.read_text().splitlines()
    out: list[str] = []
    i = 0
    para: list[str] = []

    def flush():
        nonlocal para
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para = []

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*-", lines[i + 1]):
            flush()
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(_table(block, doc_href))
            continue
        m = re.match(r"^(#{1,3}) (.*)", ln)
        if m:
            flush()
            lvl = len(m.group(1)) + 1  # md '#' -> h2 (the page title is h1 below)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^\s*([-*]|\d+\.) ", ln):
            flush()
            ordered = bool(re.match(r"^\s*\d+\.", ln))
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>")
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                item = re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i])
                out.append(f"<li>{_inline(item)}</li>")
                i += 1
            out.append(f"</{tag}>")
            continue
        if not ln.strip():
            flush()
            i += 1
            continue
        para.append(ln.strip())
        i += 1
    flush()
    return "\n".join(out)

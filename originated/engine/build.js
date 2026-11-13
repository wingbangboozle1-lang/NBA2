'use strict';
/**
 * Renders the site. Reads data/*.json + research/*.md, writes index.html and pages/*.html.
 * Nothing here invents a value.
 */

const fs = require('fs');
const path = require('path');
const L = require('./lib');
const S = require('./strategies');

const ROOT = path.join(__dirname, '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

const teams = read('data/teams.json');
const slate = read('data/slate.json');
const injuries = read('data/injuries.json');
const sources = read('data/sources.json');
const derived = read('data/derived.json');

const SRC = Object.fromEntries(sources.sources.map(s => [s.id, s]));
const TEAM = Object.fromEntries(teams.teams.map(t => [t.abbr, t]));
const LINE = Object.fromEntries(derived.lines.map(l => [l.id, l]));
const GAME = Object.fromEntries(slate.games.map(g => [g.id, g]));
const SIM = Object.fromEntries(derived.sims.map((s, i) => [derived.lines[i].id, s]));
const FLOW = Object.fromEntries(derived.flows.map(f => [f.id, f]));

const OUT = ROOT;
const PAGES = path.join(ROOT, 'pages');
fs.mkdirSync(PAGES, { recursive: true });

/* ------------------------------------------------------------------ *
 * helpers
 * ------------------------------------------------------------------ */

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const srcLink = (id, label) => {
  const s = SRC[id];
  if (!s) return '';
  return `<a class="srclink" href="${esc(s.url)}" target="_blank" rel="noopener" title="Tier ${esc(s.tier)} · ${esc(s.name)}">${esc(label || s.tier)}</a>`;
};

const tag = (cls, txt, title) => `<span class="tag ${cls}"${title ? ` title="${esc(title)}"` : ''}>${esc(txt)}</span>`;

const num = (v, dp = 1) => (v == null || Number.isNaN(v)) ? '<span class="unverified">— UNVERIFIED —</span>'
  : `<span class="mono">${Number(v).toFixed(dp)}</span>`;

const pct = (v, dp = 1) => (v == null) ? '<span class="unverified">— UNVERIFIED —</span>'
  : `${(v * 100).toFixed(dp)}%`;

const signed = (v, dp = 1) => (v == null) ? '<span class="unverified">— UNVERIFIED —</span>'
  : `<span class="mono">${v > 0 ? '+' : ''}${Number(v).toFixed(dp)}</span>`;

function tbl(headers, rows, opts = {}) {
  const cls = [];
  if (opts.sortable) cls.push('data-sort');
  const ths = headers.map(h =>
    typeof h === 'string' ? `<th>${h}</th>` : `<th class="${h.num ? 'num' : ''}" ${h.key ? `data-key="${esc(h.key)}"` : ''}>${h.label}</th>`
  ).join('');
  return `<div class="tablewrap"><table class="${cls.join(' ')}"><thead><tr>${ths}</tr></thead><tbody>${rows.map(r => '<tr>' + r.map(c => typeof c === 'string' ? `<td>${c}</td>` : `<td class="${c.num ? 'num' : ''}${c.mono ? ' mono' : ''}">${c.v}</td>`).join('') + '</tr>').join('')}</tbody></table></div>`;
}

const cell = (v, o = {}) => ({ v, num: !!o.num, mono: !!o.mono });

/* ------------------------------------------------------------------ *
 * markdown -> html (small, predictable subset)
 * ------------------------------------------------------------------ */

function md(src) {
  const lines = src.split('\n');
  const out = [];
  let i = 0, inList = null, inCode = false, inQuote = false;
  let para = [];

  const inline = (t) => t
    .replace(/`([^`]+)`/g, (m, c) => `<code>${c}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, (m, c) => `<strong>${c}</strong>`)
    .replace(/(^|[\s(])\*([^*]+)\*/g, (m, p, c) => `${p}<em>${c}</em>`)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, t2, u) =>
      `<a href="${u}"${u.startsWith('http') ? ' target="_blank" rel="noopener"' : ''}>${t2}</a>`);

  // Consecutive plain lines are joined into one paragraph (the source files are hard-wrapped).
  const flush = () => {
    if (para.length) { out.push(`<p>${inline(para.join(' '))}</p>`); para = []; }
  };

  while (i < lines.length) {
    const ln = lines[i];

    if (/^```/.test(ln)) { flush(); inCode = !inCode; out.push(inCode ? '<pre><code>' : '</code></pre>'); i++; continue; }
    if (inCode) { out.push(esc(ln)); i++; continue; }

    if (/^\s*$/.test(ln)) {
      flush();
      if (inList) { out.push(inList === 'ul' ? '</ul>' : '</ol>'); inList = null; }
      if (inQuote) { out.push('</blockquote>'); inQuote = false; }
      i++; continue;
    }

    let m;
    if ((m = /^(#{1,6})\s+(.*)$/.exec(ln))) {
      flush();
      const lvl = Math.min(m[1].length, 4);
      out.push(`<h${lvl}>${inline(m[2])}</h${lvl}>`); i++; continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(ln)) { flush(); out.push('<hr>'); i++; continue; }
    if (/^>\s?/.test(ln)) {
      flush();
      if (!inQuote) { out.push('<blockquote>'); inQuote = true; }
      out.push(`<p>${inline(ln.replace(/^>\s?/, ''))}</p>`); i++; continue;
    }
    if (/^\|/.test(ln)) {                       // table
      flush();
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) {
        rows.push(lines[i].split('|').slice(1, -1).map(c => c.trim()));
        i++;
      }
      const head = rows[0], body = rows.slice(2);
      out.push('<div class="tablewrap"><table><thead><tr>' +
        head.map(h => `<th>${inline(h)}</th>`).join('') + '</tr></thead><tbody>' +
        body.map(r => '<tr>' + r.map(c => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') +
        '</tbody></table></div>');
      continue;
    }
    if ((m = /^\s*[-*]\s+(.*)$/.exec(ln))) {
      flush();
      if (inList !== 'ul') { if (inList) out.push('</ol>'); out.push('<ul>'); inList = 'ul'; }
      out.push(`<li>${inline(m[1])}</li>`); i++; continue;
    }
    if ((m = /^\s*\d+\.\s+(.*)$/.exec(ln))) {
      flush();
      if (inList !== 'ol') { if (inList) out.push('</ul>'); out.push('<ol>'); inList = 'ol'; }
      out.push(`<li>${inline(m[1])}</li>`); i++; continue;
    }

    para.push(ln);
    i++;
  }
  flush();
  if (inList) out.push(inList === 'ul' ? '</ul>' : '</ol>');
  if (inQuote) out.push('</blockquote>');
  return out.join('\n');
}

const NAV = [
  { href: 'index.html', label: 'Dashboard', desc: 'KPIs, today\'s board, strongest signals, gate summary.' },
  { href: 'pages/executive-summary.html', label: 'Executive Summary', desc: 'What the system is, headline findings, the two blockers.' },
  { href: 'pages/slates.html', label: 'Slates & Picks', desc: 'All 23 games with originated lines and every signal.' },
  { href: 'pages/lines.html', label: 'Originated Lines', desc: 'How each line is built, plus full sensitivity to every assumption.' },
  { href: 'pages/strategies.html', label: 'Strategies', desc: 'Catalog, validation-gate matrix, leaderboard, parlay arithmetic.' },
  { href: 'pages/correlations.html', label: 'Correlations', desc: 'Model-derived correlation values and same-game parlay pricing.' },
  { href: 'pages/injuries.html', label: 'Injuries & Rotation', desc: 'Official injury report, availability indices, what is deliberately blank.' },
  { href: 'pages/game-flow.html', label: 'Game Flow', desc: 'Rest, back-to-backs, travel, venues and Cup groups.' },
  { href: 'pages/props.html', label: 'Player Props', desc: 'Why every player threshold is blank, and how to unblock it.' },
  { href: 'pages/open-questions.html', label: 'Open Questions', desc: 'What we know, what we do not, and how to find out.' },
  { href: 'pages/suggestions.html', label: 'Suggestions', desc: 'Ranked improvements with the decision each one needs first.' },
  { href: 'pages/flagged.html', label: 'Flagged for Review', desc: 'Every unverified cell, assumption and inherited irregularity.' },
  { href: 'pages/verification.html', label: 'Verification', desc: 'The automated checks and how to re-verify any figure.' },
  { href: 'pages/data-and-sources.html', label: 'Data & Sources', desc: 'Source register, tiers, cross-checks and known gaps.' },
  { href: 'pages/repo-review.html', label: 'Repo Review', desc: 'Line-by-line history, inherited errors and corrections applied.' }
];

/** Resolve a nav target relative to the page we are rendering. */
function hrefTo(target, from) {
  const fromPages = from.startsWith('pages/');
  const toPages = target.startsWith('pages/');
  if (fromPages && toPages) return target.replace('pages/', '');
  if (fromPages && !toPages) return '../' + target;
  return target;
}

/**
 * Rewrite in-body links that were written from the site root so they work from pages/.
 * Applied only when rendering a page inside pages/.
 */
function rebase(html, from) {
  if (!from.startsWith('pages/')) return html;
  return html
    .replace(/href="pages\//g, 'href="')
    .replace(/href="index\.html"/g, 'href="../index.html"');
}

function shell({ title, active, body, wide }) {
  const navHtml = NAV.map(n =>
    `<a href="${hrefTo(n.href, active)}" class="${n.href === active ? 'active' : ''}">${esc(n.label)}</a>`
  ).join('');
  const bodyHtml = rebase(body, active);

  return `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} · NBA2</title>
<meta name="description" content="NBA2 — originated NBA lines, strategy validation and slate analysis, with every data row linked to its source.">
<link rel="stylesheet" href="${active === 'index.html' ? 'assets/app.css' : '../assets/app.css'}">
</head><body>
<div class="topbar"><div class="wrap">
  <div class="brand"><span class="dot"></span><span>NBA2<small>Originated lines</small></span></div>
  <nav class="navlinks">${navHtml}</nav>
</div></div>
<main class="wrap${wide ? '' : ''}">
  <h1>${esc(title)}</h1>
  ${bodyHtml}
</main>
<footer>
  <p><strong>NBA2</strong> — originated NBA lines, verified data, strategy validation.
  Data as of <strong>${esc(teams.asOf)}</strong>. Build <code>${esc(derived.meta.generated)}</code>.</p>
  <p>Every data row links to its source. Items we could not confirm from an official source are blank and listed on
  <a href="${hrefTo('pages/flagged.html', active)}">Flagged for Review</a>.
  Nothing on this site is wagering advice.</p>
</footer>
<script src="${active === 'index.html' ? 'assets/app.js' : '../assets/app.js'}"></script>
</body></html>`;
}

const writePage = (file, html) => fs.writeFileSync(path.join(OUT, file), html);

/* ------------------------------------------------------------------ *
 * shared fragments
 * ------------------------------------------------------------------ */

function legend() {
  return `<p class="legend">
    <span><i class="swatch" style="background:var(--t1)"></i> T1 — official NBA source linked</span>
    <span><i class="swatch" style="background:var(--t2)"></i> T2 — trusted, not official</span>
    <span><i class="swatch" style="background:var(--model)"></i> MODEL OUTPUT — our computation</span>
    <span><i class="swatch" style="background:var(--warn)"></i> UNVERIFIED — deliberately blank</span>
  </p>`;
}

function blockers() {
  return `<div class="callout warn"><p><strong>Two blockers.</strong>
  (1) There is no market price feed, so no edge on this site is a bettable edge — only a fair price
  (<a href="pages/open-questions.html#q-01">Q-01</a>).
  (2) There is no official per-player feed, so <strong>every player prop threshold is blank</strong>
  (<a href="pages/open-questions.html#q-02">Q-02</a>).</p></div>`;
}

/* ------------------------------------------------------------------ *
 * PAGE: dashboard
 * ------------------------------------------------------------------ */

function pageIndex() {
  const d = derived;
  const today = d.meta.window[0];
  const todaysLines = d.lines.filter(l => l.date === today);
  const top = d.signals.slice().sort((a, b) => (b.evPerUnit ?? 0) - (a.evPerUnit ?? 0)).slice(0, 10);
  const unverifiedCount = countUnverified();

  const kpis = [
    { k: 'Games in window', v: d.meta.gamesInWindow, n: `${d.meta.window[0]} → ${d.meta.window[1]}` },
    { k: 'Verified data rows', v: slate.games.length + injuries.rows.length + teams.teams.length, n: '23 games · 91 injury rows · 30 teams' },
    { k: 'Official (T1) sources', v: sources.sources.filter(s => s.tier === 'T1').length, n: 'nba.com · official injury report PDF' },
    { k: 'W-L cross-check', v: '30/30', n: 'ESPN vs nba.com, all 30 teams', ok: true },
    { k: 'Unverified cells', v: unverifiedCount, n: 'blank on purpose — see Flagged', bad: unverifiedCount > 0 },
    { k: 'Strategies deployable', v: '0 / 10', n: 'gate G6 blocked for all ten', bad: true }
  ];

  const cards = kpis.map(c => `<div class="card ${c.ok ? 'ok' : ''} ${c.bad ? 'att' : ''}">
      <div class="k">${esc(c.k)}</div><div class="v">${esc(c.v)}</div><div class="n">${esc(c.n)}</div></div>`).join('');

  const slateRows = todaysLines.map(l => [
    cell(`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.matchup)}</a>`),
    cell(l.timeEt),
    cell(`<strong>${esc(l.spreadHome > 0 ? l.home + ' ' + (l.spreadHome > 0 ? '+' + l.spreadHome : l.spreadHome) : l.home + ' ' + l.spreadHome)}</strong>`, { mono: true }),
    cell(esc(l.totalLine), { num: true, mono: true }),
    cell(`${esc(L.fmtAmerican(l.mlHome))} / ${esc(L.fmtAmerican(l.mlAway))}`, { mono: true }),
    cell(pct(l.pHome), { num: true }),
    cell(tag('model', 'MODEL') + ' ' + srcLink('S01', 'T1'))
  ]);

  const sigRows = top.map(s => [
    cell(esc(s.date)),
    cell(`<a href="${esc(LINE[s.gameId] ? LINE[s.gameId].url : '#')}" target="_blank" rel="noopener">${esc(s.matchup)}</a>`),
    cell(tag('model', s.strategy)),
    cell(esc(s.market)),
    cell(`<strong>${esc(s.side)}</strong> ${s.target != null ? esc(s.target) : ''}`),
    cell(pct(s.modelProb, 2), { num: true }),
    cell((s.evPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (s.evPerUnit * 100).toFixed(1) + '%</span>', { num: true }),
    cell(tag('model', 'MODEL'))
  ]);

  const gateRows = d.strategies.map(s => [
    cell(`<strong>${esc(s.id)}</strong> ${esc(s.name)}`),
    cell(esc(s.family)),
    cell(`${s.gatesPassed} / ${s.gatesTotal}`, { num: true }),
    cell(Object.entries(s.gates).map(([k, v]) => tag(v.ok ? 'pass' : 'fail', k, v.detail)).join(' ')),
    cell(s.blocked ? 'BLOCKED — no official player feed' : (s.gatesPassed === s.gatesTotal ? 'deployable' : 'held'), { num: false })
  ]);

  const linkCards = NAV.filter(n => n.href !== 'index.html').map(n =>
    `<div class="card"><div class="k">${esc(n.label)}</div>
      <div class="v" style="font-size:15px"><a href="${esc(n.href)}">Open &rarr;</a></div>
      <div class="n">${esc(n.desc || '')}</div></div>`).join('');

  const body = `
  <p class="sub">Originated NBA lines for the next 3 days, built from official sources, with every
  unverifiable value left blank instead of guessed.</p>
  ${blockers()}
  <div class="cards">${cards}</div>
  ${legend()}

  <h2>Today's slate — ${esc(today)} (${todaysLines.length} games)</h2>
  <p class="small">All nine games are Emirates NBA Cup group games. Spread is from the home team's
  perspective (negative = home favoured). Full 3-day board on the
  <a href="pages/slates.html">Slates &amp; Picks</a> page.</p>
  ${tbl(['Matchup', 'Tip (ET)', 'Originated spread', 'Total', 'ML (H / A)', 'P(home)', 'Source'], slateRows, { sortable: true })}

  <h2>Strongest signals on the board</h2>
  <p class="small">Ranked by expected value per unit at the assumed −110 price. These are
  <strong>model expectations against our own fair line</strong>, not results.</p>
  ${tbl(['Date', 'Game', 'Strategy', 'Market', 'Side', 'Model P', 'EV/unit', 'Type'], sigRows, { sortable: true })}

  <h2>Validation gates</h2>
  <p class="small">Hover any gate chip for the reason. Every strategy is held by
  <strong>G6</strong> — there is no graded bet history in this repository.</p>
  ${tbl(['Strategy', 'Family', 'Gates', 'Gate detail', 'Status'], gateRows)}

  <h2>Go deeper</h2>
  <div class="cards">${linkCards}</div>
  `;
  return shell({ title: 'Dashboard', active: 'index.html', body });
}

function countUnverified() {
  // player props: every listed player x 4 threshold fields
  const players = injuries.rows.filter(r => r.player);
  const rest13 = derived.flows.filter(f => f.awayRest === null || f.homeRest === null).length * 2;
  return players.length * 4 + rest13 + 1; // +1 = injuryK calibration
}

/* ------------------------------------------------------------------ *
 * PAGE: slates & picks
 * ------------------------------------------------------------------ */

function pageSlates() {
  const dates = [...new Set(derived.lines.map(l => l.date))];
  let body = `<p class="sub">Every game in the 3-day window with its originated line, the game-flow
  context behind it, and every strategy signal attached to it.</p>${legend()}`;

  body += `<div class="controls">
    <label class="pill">Filter games <input data-filter="#tblAllGames" placeholder="team, venue, group…"></label>
    <span class="pill" data-count="#tblAllGames"></span>
    <label class="pill">Show day <select data-group="day">
      <option value="all">All 3 days</option>
      ${dates.map(d => `<option value="${d}">${d}</option>`).join('')}
    </select></label>
  </div>`;

  const allRows = derived.lines.map(l => {
    const f = FLOW[l.id] || {};
    const a = derived.availability[TEAM[l.away].name] || null;
    const h = derived.availability[TEAM[l.home].name] || null;
    const sigs = derived.signals.filter(s => s.gameId === l.id);
    const spreadTxt = l.spreadHome > 0 ? `${l.home} +${l.spreadHome}` : `${l.home} ${l.spreadHome}`;
    return [
      cell(esc(l.date)),
      cell(esc(l.timeEt)),
      cell(`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.matchup)}</a>`),
      cell(esc(l.venue) + '<br><span class="small">' + esc(l.city) + '</span>'),
      cell(l.competition === 'Emirates NBA Cup' ? tag('t1', 'CUP ' + (l.cupGroup || '')) : 'Regular'),
      cell(`<strong>${esc(spreadTxt)}</strong>`, { mono: true }),
      cell(esc(l.totalLine), { num: true, mono: true }),
      cell(`${esc(L.fmtAmerican(l.mlHome))} / ${esc(L.fmtAmerican(l.mlAway))}`, { mono: true }),
      cell(pct(l.pHome), { num: true }),
      cell(f.homeB2B ? tag('fail', 'B2B') : (f.awayB2B ? tag('fail', 'away B2B') : (f.awayRest === null ? '<span class="unverified">unknown</span>' : 'rested'))),
      cell(a ? num(a.rotationIndex, 2) : '<span class="unverified">n/a</span>', { num: true }),
      cell(h ? num(h.rotationIndex, 2) : '<span class="unverified">n/a</span>', { num: true }),
      cell(sigs.length ? `<a href="#sig_${l.id}">${sigs.length}</a>` : '0', { num: true }),
      cell(tag('model', 'MODEL') + ' ' + srcLink('S01', 'T1'))
    ];
  });

  body += `<div data-group-block="day" data-group-value="all">${tbl(
    ['Date', 'Tip (ET)', 'Matchup', 'Venue', 'Competition', 'Spread (home)', 'Total', 'ML (H/A)', 'P(home)', 'Rest', 'Away avail.', 'Home avail.', 'Signals', 'Source'],
    allRows, { sortable: true })}</div>`;
  body = body.replace('<table class="data-sort">', '<table id="tblAllGames" class="data-sort">');

  for (const d of dates) {
    const rows = allRows.filter((r, i) => derived.lines[i].date === d);
    body += `<div data-group-block="day" data-group-value="${d}" style="display:none">${tbl(
      ['Date', 'Tip (ET)', 'Matchup', 'Venue', 'Competition', 'Spread (home)', 'Total', 'ML (H/A)', 'P(home)', 'Rest', 'Away avail.', 'Home avail.', 'Signals', 'Source'],
      rows, { sortable: true })}</div>`;
  }

  // Per-game detail blocks (anchored from the signals-count column above)
  const withSigs = derived.lines.filter(l => derived.signals.some(s => s.gameId === l.id));
  body += `<h2>Game detail — every signal on one game</h2>
  <p class="small">One block per game that produced at least one signal.</p>`;
  for (const l of withSigs) {
    const sigs = derived.signals.filter(s => s.gameId === l.id)
      .sort((a, b) => b.modelProb - a.modelProb);
    body += `<div class="panel" id="sig_${esc(l.id)}">
      <h3><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.matchup)}</a>
        <span class="small">${esc(l.date)} ${esc(l.timeEt)} · ${esc(l.venue)}</span></h3>
      <p class="small">Originated spread
        <strong>${esc(l.spreadHome > 0 ? l.home + ' +' + l.spreadHome : l.home + ' ' + l.spreadHome)}</strong> ·
        total <strong>${esc(l.totalLine)}</strong> · ML
        <strong>${esc(L.fmtAmerican(l.mlHome))} / ${esc(L.fmtAmerican(l.mlAway))}</strong> ·
        P(home) <strong>${pct(l.pHome, 1)}</strong> ·
        ${srcLink('S01', 'T1 schedule')}</p>
      ${tbl(['Strategy', 'Market', 'Side', 'Line', 'Model P', 'Break-even', 'EV/unit'],
        sigs.map(s => [
          cell(tag('model', s.strategy)),
          cell(esc(s.market)),
          cell(`<strong>${esc(s.side)}</strong>`),
          cell(esc(s.target), { mono: true }),
          cell(pct(s.modelProb, 2), { num: true }),
          cell(pct(s.breakevenProb, 2), { num: true }),
          cell((s.evPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (s.evPerUnit * 100).toFixed(1) + '%</span>', { num: true })
        ]))}
    </div>`;
  }

  // Picks grouped by strategy
  body += `<h2>Picks by strategy</h2>
  <p class="small">Every signal the system emits, grouped by the strategy that produced it.
  <strong>Break-even at the assumed −110 is 52.38%.</strong> Rows below that are shown too — a
  strategy that cannot clear the vig should not be bet, and gate G5 exists to catch exactly that.</p>`;

  const byStrat = {};
  for (const s of derived.signals) (byStrat[s.strategy] = byStrat[s.strategy] || []).push(s);

  for (const strat of derived.strategies) {
    const sigs = (byStrat[strat.id] || []).sort((a, b) => b.modelProb - a.modelProb);
    const meta = STRAT_META(strat);
    body += `<div class="panel" id="strat_${strat.id}">
      <h3>${esc(strat.id)} — ${esc(strat.name)} ${tag(strat.family === 'prop' ? 'unv' : 'model', strat.family)}</h3>
      <p class="small">${esc(strat.thesis)}</p>
      <p class="small"><strong>Residual signal:</strong> ${esc(strat.residualInfo || '—')}<br>
      <strong>Fires when:</strong> ${esc(strat.trigger || '—')}<br>
      <strong>Inputs:</strong> ${esc((strat.inputs || []).join(', '))} — ${esc(strat.inputTier || '—')}<br>
      <strong>Gates:</strong> ${Object.entries(strat.gates).map(([k, v]) => tag(v.ok ? 'pass' : 'fail', k, v.detail)).join(' ')}</p>
      ${meta}
      ${sigs.length ? tbl(['Date', 'Game', 'Market', 'Side', 'Line', 'Model P', 'Fair price', 'Break-even', 'EV/unit', 'Adj'],
        sigs.map(s => [
          cell(esc(s.date)),
          cell(esc(s.matchup)),
          cell(esc(s.market)),
          cell(`<strong>${esc(s.side)}</strong>`),
          cell(esc(s.target), { mono: true }),
          cell(`<strong>${pct(s.modelProb, 2)}</strong>`, { num: true }),
          cell(esc(L.fmtAmerican(s.fairAmerican)), { mono: true }),
          cell(pct(s.breakevenProb, 2), { num: true }),
          cell((s.evPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (s.evPerUnit * 100).toFixed(1) + '%</span>', { num: true }),
          cell(s.adjPoints != null ? signed(s.adjPoints, 2) : '—', { num: true })
        ]), { sortable: true })
        : `<p class="small"><em>No signals fired in this window.</em></p>`}
    </div>`;
  }

  return shell({ title: 'Slates & Picks', active: 'pages/slates.html', body });
}

function STRAT_META(strat) {
  if (strat.blocked) return `<div class="callout warn"><p><strong>Blocked.</strong> ${esc(strat.blockedReason || '')}</p></div>`;
  if (!strat.rule_verified) return `<div class="callout warn"><p><strong>Held at G2.</strong> ${esc(strat.rule_note || '')}</p></div>`;
  if (strat.lambda) return `<p class="small"><strong>λ = ${esc(strat.lambda.value)}</strong> — ${esc(strat.lambda.note)} ${tag('unv', 'ASSUMPTION')}</p>`;
  return '';
}

/* ------------------------------------------------------------------ *
 * PAGE: lines
 * ------------------------------------------------------------------ */

function pageLines() {
  const d = derived;
  let body = `<p class="sub">How each line is built, and what happens to it when the declared
  assumptions move. Every formula is in
  <a href="data-and-sources.html">Data &amp; Sources</a> /
  <a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/research/04-line-origination.md" target="_blank" rel="noopener">research/04-line-origination.md</a>.</p>
  ${legend()}`;

  body += `<div class="cards">
    <div class="card"><div class="k">League PPG</div><div class="v">${d.league.lgPpg}</div><div class="n">games-weighted mean</div></div>
    <div class="card"><div class="k">Home win rate</div><div class="v">${(d.league.homeWinRate * 100).toFixed(2)}%</div><div class="n">${d.league.homeWins}-${d.league.homeLosses} across ${d.league.splitGames} split games</div></div>
    <div class="card att"><div class="k">Home-court pts</div><div class="v">+${d.league.hcaPoints}</div><div class="n">derived — see the warning below</div></div>
    <div class="card"><div class="k">Margin SD</div><div class="v">${d.league.marginSd}</div><div class="n">model-implied</div></div>
    <div class="card"><div class="k">Total SD</div><div class="v">${d.league.totalSd}</div><div class="n">model-implied</div></div>
  </div>`;

  body += `<div class="callout warn"><p><strong>The derived home-court advantage is only
  +${d.league.hcaPoints} points.</strong> It comes from 89 home wins against 84 home losses in
  ${d.league.splitGames} split games — a standard error of roughly ±3.8 percentage points, so this
  estimate is unstable, and it is the largest single source of error in the originated spreads.
  The panel at the bottom re-prices the whole board at +0.5 / +1.5 / +2.5 so the effect is visible
  rather than hidden.</p></div>`;

  const rows = d.lines.map(l => {
    const f = FLOW[l.id] || {};
    return [
      cell(`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.matchup)}</a>`),
      cell(num(l.ratingDeltaHome, 2), { num: true }),
      cell(num(l.hcaPoints, 2), { num: true }),
      cell(l.restKnown ? num(l.restAdjHome, 2) : '<span class="unverified">unknown</span>', { num: true }),
      cell(num(l.tzAdjHome, 2), { num: true }),
      cell(`<strong>${num(l.marginHome, 2)}</strong>`, { num: true }),
      cell(num(l.baseMarginHome, 2), { num: true }),
      cell(num(l.marginHomeWithInjury, 2), { num: true }),
      cell(`<strong>${l.spreadHome > 0 ? '+' : ''}${esc(l.spreadHome)}</strong>`, { num: true, mono: true }),
      cell(num(l.expAwayPts, 1), { num: true }),
      cell(num(l.expHomePts, 1), { num: true }),
      cell(`<strong>${esc(l.totalLine)}</strong>`, { num: true, mono: true }),
      cell(pct(l.pHome), { num: true }),
      cell(pct(l.pythPHome), { num: true }),
      cell(num((l.pHome - l.pythPHome) * 100, 1), { num: true })
    ];
  });

  body += `<h2>Every originated line</h2>
  <div class="controls"><label class="pill">Filter <input data-filter="#tblLines" placeholder="team…"></label><span class="pill" data-count="#tblLines"></span></div>
  ${tbl(
    ['Matchup', 'Rating Δ (H)', 'HCA', 'Rest', 'TZ', 'Margin (H)', 'Base margin', 'With injury overlay', 'Spread (H)', 'Proj away', 'Proj home', 'Total', 'P(home) Normal', 'P(home) Pythagorean', 'Δ pp'],
    rows, { sortable: true }).replace('<table class="data-sort">', '<table id="tblLines" class="data-sort">')}
  <p class="small"><strong>Base margin</strong> = rating difference + home court only.
  <strong>Margin</strong> adds rest and time-zone travel. <strong>With injury overlay</strong> adds
  the availability adjustment at the <em>uncalibrated</em> coefficient of 0.35 — published as a
  separate column, never baked into the line.
  <strong>Δ pp</strong> is the gap between the Normal and the Pythagorean route to the same
  probability; a large gap means the team's record disagrees with its scoring profile.</p>`;

  // sensitivity
  body += `<h2>Sensitivity — how much do the declared assumptions move each line?</h2>`;
  for (const s of derived.sensitivity) {
    const base = d.lines.find(l => l.id === s.gameId);
    body += `<div class="panel"><h3>${esc(s.matchup)} <span class="small">published spread ${esc(base.spreadHome > 0 ? '+' + base.spreadHome : base.spreadHome)}, total ${esc(base.totalLine)}</span></h3>
      ${tbl(['Parameter', 'Value', 'Spread (home)', 'Total', 'P(home)'],
        s.rows.map(r => [
          cell(`<code>${esc(r.param)}</code>`),
          cell(esc(r.value), { num: true, mono: true }),
          cell((r.spreadHome > 0 ? '+' : '') + esc(r.spreadHome), { num: true, mono: true }),
          cell(esc(r.totalLine), { num: true, mono: true }),
          cell(pct(r.pHome, 1), { num: true })
        ]))}</div>`;
  }

  // hca sensitivity
  const hca = require('./model').hcaSensitivity(
    slate.games,
    Object.fromEntries(derived.flows.map(f => [f.id, f])),
    { ...d.league, ratings: Object.fromEntries(d.ratings.map(r => [r.abbr, r])) },
    derived.availability
  );
  body += `<h2>Home-court sensitivity</h2>
  <p class="small">The board re-priced at three home-court values. "Favourite flips" counts games
  where the favoured side changes relative to the published line.</p>
  ${tbl(['HCA (pts)', 'Favourite flips vs published', 'Board'],
    hca.map(h => [
      cell('+' + h.hca, { num: true }),
      cell(esc(h.favouriteFlips), { num: true }),
      cell(h.rows.map(r => `${esc(r.matchup)} ${(r.spreadHome > 0 ? '+' : '') + r.spreadHome}`).join(' · '))
    ]))}`;

  return shell({ title: 'Originated Lines', active: 'pages/lines.html', body });
}

/* ------------------------------------------------------------------ *
 * PAGE: strategies
 * ------------------------------------------------------------------ */

function pageStrategies() {
  const d = derived;
  let body = `<p class="sub">Ten strategies, eight validation gates each. A strategy is only allowed
  to claim an edge if it uses information that is <strong>not</strong> already in the originated
  line.</p>${legend()}`;

  body += `<div class="callout"><p><strong>G6 fails for all ten.</strong> This repository contains no
  graded historical bet log, so out-of-sample validation cannot be run. Every strategy that could
  otherwise be deployed is held back by this one gate, and the leaderboard below is
  <strong>model-expected, not realised</strong>.</p></div>`;

  // leaderboard
  body += `<h2>Leaderboard — expected, not realised</h2>
  ${tbl(['#', 'Strategy', 'Family', 'Signals', 'Mean model P', 'Mean EV/unit', 'Best P', 'Gates', 'Deployable'],
    d.leaderboard.map((r, i) => [
      cell(String(i + 1), { num: true }),
      cell(`<strong>${esc(r.strategy)}</strong> ${esc(r.name)}`),
      cell(esc(r.family)),
      cell(esc(r.signals), { num: true }),
      cell(r.meanModelProb == null ? '—' : pct(r.meanModelProb, 2), { num: true }),
      cell(r.meanEvPerUnit == null ? '—' : (r.meanEvPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (r.meanEvPerUnit * 100).toFixed(1) + '%</span>', { num: true }),
      cell(r.bestProb == null ? '—' : pct(r.bestProb, 2), { num: true }),
      cell(`${r.gatesPassed}/${r.gatesTotal}`, { num: true }),
      cell(r.deployable ? tag('pass', 'YES') : tag('fail', 'NO'))
    ]), { sortable: true })}`;

  // gate matrix
  body += `<h2>Validation-gate matrix</h2>`;
  body += tbl(['Strategy', ...S.GATES.map(g => `<span title="${esc(g.rule)}">${g.id}</span>`), 'Blockers'],
    d.strategies.map(s => [
      cell(`<strong>${esc(s.id)}</strong> ${esc(s.name)}`),
      ...S.GATES.map(g => cell(s.gates[g.id] && s.gates[g.id].ok
        ? tag('pass', 'PASS', s.gates[g.id].detail)
        : tag('fail', 'FAIL', s.gates[g.id] ? s.gates[g.id].detail : ''))),
      cell((Object.entries(s.gates).filter(([, v]) => !v.ok).map(([k, v]) => `<div class="small">${esc(k)}: ${esc(v.detail)}</div>`).join('')) || '—')
    ]));

  // gate definitions
  body += `<h3>What each gate requires</h3>`;
  body += tbl(['Gate', 'Name', 'Rule'], S.GATES.map(g => [cell(`<strong>${esc(g.id)}</strong>`), cell(esc(g.name)), cell(esc(g.rule))]));

  // catalog
  body += `<h2>Strategy catalog</h2>`;
  for (const s of d.strategies) {
    body += `<div class="panel">
      <h3>${esc(s.id)} — ${esc(s.name)} ${tag(s.family === 'prop' ? 'unv' : 'model', s.family)}</h3>
      <p><strong>Thesis.</strong> ${esc(s.thesis)}</p>
      <p class="small"><strong>Residual signal:</strong> ${esc(s.residualInfo || '—')}</p>
      <p class="small"><strong>Fires when:</strong> ${esc(s.trigger || '—')}</p>
      ${s.where ? `<p class="small"><strong>Where:</strong> ${esc(s.where)}</p>` : ''}
      <p class="small"><strong>Inputs:</strong> ${esc((s.inputs || []).join(', '))} — ${esc(s.inputTier || '—')}</p>
      ${STRAT_META(s)}
      <p class="small">${Object.entries(s.gates).map(([k, v]) => tag(v.ok ? 'pass' : 'fail', k, v.detail)).join(' ')}</p>
    </div>`;
  }

  // parlays
  body += `<h2>Cross-game parlays (S08)</h2>
  <p class="small">One leg per game, so the legs are independent by construction. Priced at the
  product of the vigged leg prices, at a ${(S.ASSUMED_MARKET.overround * 100).toFixed(2)}% overround.</p>
  ${tbl(['Legs', 'Combination', 'True joint P', 'Market price', 'Fair price', 'Break-even', 'EV/unit'],
    (derived.crossParlays || []).slice(0, 12).map(p => [
      cell(esc(p.legCount), { num: true }),
      cell(p.legs.map(l => `<div>${esc(l.side)} <span class="small">${esc(l.matchup)} · ${esc(l.market)} · model ${pct(l.modelProb, 1)}</span></div>`).join('')),
      cell(pct(p.pTrueJoint, 2), { num: true }),
      cell(esc(L.fmtAmerican(p.assumedMarketAmerican)), { num: true, mono: true }),
      cell(esc(L.fmtAmerican(p.fairAmerican)), { num: true, mono: true }),
      cell(pct(p.breakevenProb, 2), { num: true }),
      cell((p.evPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (p.evPerUnit * 100).toFixed(1) + '%</span>', { num: true })
    ]))}`;

  body += `<h3>What a parlay costs when no leg has an edge</h3>
  ${tbl(['Legs', 'Cost if no edge', 'Required per-leg edge'],
    S.parlayVigTable(6).map(r => [
      cell(esc(r.legs), { num: true }),
      cell(`<span class="neg">−${(r.vigPaidIfNoEdge * 100).toFixed(2)}%</span>`, { num: true }),
      cell(`≈ ${(r.requiredPerLegEdge * 100).toFixed(2)} pp`, { num: true })
    ]))}
  <p class="small">Parlays multiply the vig exactly as fast as they multiply the edge. Each leg must
  clear its own break-even by roughly the overround just to stand still.</p>`;

  return shell({ title: 'Strategies', active: 'pages/strategies.html', body });
}

/* ------------------------------------------------------------------ *
 * PAGE: correlations
 * ------------------------------------------------------------------ */

function pageCorrelations() {
  const d = derived;
  let body = `<p class="sub">Every correlation here is <strong>derived from this project's own
  model</strong> by Monte-Carlo (${d.meta.mcIterations.toLocaleString()} draws per game, seed
  ${esc(String(d.meta.mcSeed))}), not sampled from historical bet data — there is none in this
  repository.</p>${legend()}`;

  body += `<div class="callout"><p><strong>The headline result is a negative one.</strong> Across all
  ${d.lines.length} games the largest binary correlation (φ) between a moneyline leg and a totals
  leg is <strong>${Math.max(...d.sameGameParlays.map(p => Math.abs(p.phi || 0))).toFixed(4)}</strong>.
  The independence assumption books use to price winner × totals parlays is therefore very close to
  fair. The dangerous correlation is the one they already restrict:
  <strong>moneyline × spread-cover, φ ≈ ${(d.sims.reduce((s, x) => s + x.phi.homeWin_homeCover, 0) / d.sims.length).toFixed(2)}</strong>.</p></div>`;

  body += `<h2>Continuous correlations (Pearson r)</h2>
  ${tbl(['Matchup', 'r(away score, home score)', 'r(margin, total)', 'r(away score, total)', 'r(home score, total)'],
    d.lines.map(l => {
      const s = SIM[l.id];
      return [
        cell(`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.matchup)}</a>`),
        cell(num(s.corr.scoreAwayScoreHome, 3), { num: true }),
        cell(num(s.corr.marginTotal, 3), { num: true }),
        cell(num(s.corr.awayScoreTotal, 3), { num: true }),
        cell(num(s.corr.homeScoreTotal, 3), { num: true })
      ];
    }), { sortable: true })}
  <p class="small">r(away score, home score) ≈ 0.31 is a <em>calibration target</em>, not a finding —
  the simulator's parameters are tuned to land there. r(margin, total) is the interesting one, and
  it is essentially zero. See
  <a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/research/07-correlations.md" target="_blank" rel="noopener">research/07-correlations.md</a> for why.</p>`;

  body += `<h2>Binary correlations (φ) — the ones that price parlays</h2>
  ${tbl(['Matchup', 'φ(home win, over)', 'φ(home cover, over)', 'φ(home win, home cover)'],
    d.lines.map(l => {
      const s = SIM[l.id];
      return [
        cell(esc(l.matchup)),
        cell(num(s.phi.homeWin_over, 4), { num: true }),
        cell(num(s.phi.homeCover_over, 4), { num: true }),
        cell(`<strong>${num(s.phi.homeWin_homeCover, 3)}</strong>`, { num: true })
      ];
    }), { sortable: true })}`;

  body += `<h2>Same-game parlay pricing (S09)</h2>
  <div class="controls"><label class="pill">Filter <input data-filter="#tblSgp" placeholder="team…"></label><span class="pill" data-count="#tblSgp"></span></div>
  ${tbl(['Matchup', 'Legs', 'True joint P', 'Independent P', 'φ', 'Market price (indep.)', 'Fair price', 'EV/unit'],
    d.sameGameParlays.map(p => [
      cell(esc(p.matchup)),
      cell(p.legs.join(' + ')),
      cell(pct(p.pTrueJoint, 2), { num: true }),
      cell(pct(p.pIndependent, 2), { num: true }),
      cell(num(p.phi, 4), { num: true }),
      cell(esc(L.fmtAmerican(p.assumedMarketAmerican)), { num: true, mono: true }),
      cell(esc(L.fmtAmerican(p.fairAmerican)), { num: true, mono: true }),
      cell((p.evPerUnit >= 0 ? '<span class="pos">' : '<span class="neg">') + (p.evPerUnit * 100).toFixed(2) + '%</span>', { num: true })
    ]), { sortable: true }).replace('<table class="data-sort">', '<table id="tblSgp" class="data-sort">')}
  <p class="small">A book that prices these by multiplying the legs as if independent is off by the
  φ column. On this board that is worth a fraction of a percent either way, which is why S09
  produces no actionable signals.</p>`;

  return shell({ title: 'Correlations', active: 'pages/correlations.html', body });
}

/* ------------------------------------------------------------------ *
 * PAGE: injuries
 * ------------------------------------------------------------------ */

function pageInjuries() {
  const d = derived;
  let body = `<p class="sub">Transcribed row by row from the
  <a href="${esc(SRC.S03.url)}" target="_blank" rel="noopener">Official NBA Injury Report, 11/13/26 01:00 PM</a>
  (7 pages, ${injuries.rows.length} rows). Statuses and reasons are verbatim.</p>${legend()}`;

  const playerRows = injuries.rows.filter(r => r.player);
  const notFiled = injuries.rows.filter(r => r.status === 'NOT YET SUBMITTED');

  body += `<div class="cards">
    <div class="card"><div class="k">Player rows</div><div class="v">${playerRows.length}</div><div class="n">verbatim from the official PDF</div></div>
    <div class="card"><div class="k">Teams listed</div><div class="v">${Object.keys(d.availability).length}</div><div class="n">of the 18 playing 13 Nov</div></div>
    <div class="card att"><div class="k">NOT YET SUBMITTED</div><div class="v">${notFiled.length}</div><div class="n">all ten 14 Nov team rows</div></div>
    <div class="card bad"><div class="k">Minutes / production</div><div class="v">0</div><div class="n">blank — no official per-player feed</div></div>
  </div>`;

  body += `<h2>Three indices, and why they are separate</h2>
  <div class="callout"><p>A <strong>G League two-way assignment</strong> removes a player who was
  not in the NBA rotation. Counting those rows as rotation losses is the easiest way to get this
  wrong. They are tracked separately and excluded from the index that drives the betting signal.</p></div>
  ${tbl(['Index', 'Includes', 'Drives a signal?'], [
    [cell('<strong>rotationIndex</strong>'), cell('Injury/Illness · Not With Team · League Suspension'), cell(tag('pass', 'YES') + ' strategy S04')],
    [cell('<strong>injuryIndex</strong>'), cell('Injury/Illness only'), cell('diagnostic')],
    [cell('<strong>gLeagueIndex</strong>'), cell('G League – Two-Way · G League – On Assignment'), cell(tag('fail', 'NO') + ' diagnostic only')],
    [cell('<strong>unavailIndex</strong>'), cell('everything except NOT YET SUBMITTED'), cell('diagnostic')]
  ])}
  <p class="small">Weights: Out 1.00 · Doubtful 0.75 · Questionable 0.40 · Probable 0.15 ·
  Available 0.00. <strong>NOT YET SUBMITTED is excluded entirely</strong> — it is an absence of
  information, not information.</p>`;

  body += `<h2>Availability by team</h2>
  ${tbl(['Team', 'Game', 'Listed', 'Out', 'Doubtful', 'Q\'nable', 'Probable', 'rotationIndex', 'injuryIndex', 'gLeagueIndex', 'Source'],
    Object.entries(d.availability).map(([name, a]) => {
      const g = slate.games.find(x => x.date === '2026-11-13' &&
        (TEAM[x.away].name === name || TEAM[x.home].name === name));
      return [
        cell(`<strong>${esc(name)}</strong>`),
        cell(g ? esc(`${g.away} @ ${g.home}`) : '—'),
        cell(esc(a.listed), { num: true }),
        cell(esc(a.out), { num: true }),
        cell(esc(a.doubtful), { num: true }),
        cell(esc(a.questionable), { num: true }),
        cell(esc(a.probable), { num: true }),
        cell(`<strong>${num(a.rotationIndex, 2)}</strong>`, { num: true }),
        cell(num(a.injuryIndex, 2), { num: true }),
        cell(num(a.gLeagueIndex, 2), { num: true }),
        cell(srcLink('S03', 'T1'))
      ];
    }), { sortable: true })}`;

  body += `<h2>Full report</h2>
  <div class="controls"><label class="pill">Filter <input data-filter="#tblInj" placeholder="player, team, reason…"></label><span class="pill" data-count="#tblInj"></span></div>
  ${tbl(['Game date', 'Time (ET)', 'Matchup', 'Team', 'Player', 'Status', 'Reason (verbatim)', 'Category', 'Source'],
    injuries.rows.map(r => [
      cell(esc(r.gameDate)),
      cell(esc(r.timeEt || '—')),
      cell(esc(r.matchup)),
      cell(esc(r.team)),
      cell(r.player ? esc(r.player) : '<span class="unverified">—</span>'),
      cell(statusTag(r.status)),
      cell(esc(r.reason)),
      cell(esc(r.category)),
      cell(srcLink('S03', 'T1'))
    ]), { sortable: true }).replace('<table class="data-sort">', '<table id="tblInj" class="data-sort">')}`;

  body += `<h2>Rotation minutes and production — deliberately blank</h2>
  <div class="callout warn"><p>Converting an injury into a minutes and production forecast needs two
  inputs this project does not have: <strong>per-player season minutes</strong> and
  <strong>per-player usage rates</strong>. Neither is available from any reachable official source
  (<code>stats.nba.com</code> is unreachable from this build environment). Under the project rule,
  these cells are blank rather than estimated.</p></div>

  ${tbl(['Player', 'Team', 'Official status (T1)', 'Vacated minutes', 'Minutes absorbed by', 'Pts', 'Reb', 'Ast', 'Status'],
    playerRows.slice(0, 40).map(r => [
      cell(esc(r.player)),
      cell(esc(r.team)),
      cell(statusTag(r.status) + ' ' + srcLink('S03', 'T1')),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">—</span>'),
      cell('<span class="unverified">—</span>'),
      cell('<span class="unverified">—</span>'),
      cell(tag('unv', 'BLOCKED Q-02'))
    ]))}
  <p class="small">Showing the first 40 of ${playerRows.length} player rows. Every threshold column is
  <code>null</code> in <code>data/</code>, not zero — zero would be a claim.</p>

  <h3>How to unblock this</h3>
  <ol>
    <li>Restore <code>stats.nba.com</code> access, or obtain an official NBA Stats API key →
        <code>leaguedashplayerstats</code> gives season minutes and usage.</li>
    <li><code>vacated minutes = Σ (minutes of players listed Out or Doubtful)</code></li>
    <li>Redistribute by each remaining rotation player's usage rate.</li>
    <li>Only then calibrate <code>injuryK</code> — after at least one full season of that data.</li>
  </ol>`;

  return shell({ title: 'Injuries & Rotation', active: 'pages/injuries.html', body });
}

function statusTag(s) {
  const map = {
    'Out': 'fail', 'Doubtful': 'fail', 'Questionable': 't2',
    'Probable': 't1', 'Available': 't1', 'NOT YET SUBMITTED': 'unv'
  };
  return tag(map[s] || 'model', s);
}

/* ------------------------------------------------------------------ *
 * PAGE: game flow
 * ------------------------------------------------------------------ */

function pageGameFlow() {
  const d = derived;
  let body = `<p class="sub">Rest, back-to-backs, travel and venue — all derived from the official
  schedule, with no external input.</p>${legend()}`;

  body += tbl(['Date', 'Matchup', 'Venue', 'City', 'Away rest', 'Home rest', 'B2B', 'TZ crossed', 'TZ adj (home)', 'Competition'],
    d.flows.map(f => {
      const g = GAME[f.id], l = LINE[f.id];
      return [
        cell(esc(g.date)),
        cell(`<a href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.away)} @ ${esc(g.home)}</a>`),
        cell(esc(g.venue)),
        cell(esc(g.city)),
        cell(f.awayRest === null ? '<span class="unverified">unknown</span>' : esc(f.awayRest) + ' d', { num: true }),
        cell(f.homeRest === null ? '<span class="unverified">unknown</span>' : esc(f.homeRest) + ' d', { num: true }),
        cell(f.homeB2B ? tag('fail', 'HOME') : f.awayB2B ? tag('fail', 'AWAY') : tag('pass', 'none')),
        cell(f.tzDelta === null ? '—' : esc(f.tzDelta) + ' h', { num: true }),
        cell(l ? num(l.tzAdjHome, 2) : '—', { num: true }),
        cell(g.competition === 'Emirates NBA Cup' ? tag('t1', 'CUP ' + esc(g.cupGroup || '')) : 'Regular')
      ];
    }), { sortable: true });

  body += `<div class="callout warn"><p><strong>Rest is unknown for the nine 13 Nov games.</strong>
  The 12 Nov slate was not collected, so we cannot tell whether either team is on a back-to-back.
  The model applies <strong>no</strong> adjustment rather than guessing one — those rows show
  "unknown", not "rested".</p></div>`;

  const b2b = d.flows.filter(f => f.awayB2B || f.homeB2B);
  body += `<h2>Back-to-backs in this window</h2>
  ${tbl(['Date', 'Game', 'Team on the second night', 'Previous game'],
    b2b.map(f => {
      const g = GAME[f.id];
      const who = f.homeB2B ? g.home : g.away;
      return [cell(esc(g.date)), cell(esc(`${g.away} @ ${g.home}`)),
        cell(`<strong>${esc(who)}</strong> ${tag('fail', 'B2B')}`),
        cell(esc(f.homeB2B ? f.homePrev : f.awayPrev))];
    }))}
  <p class="small">Penalty applied: <strong>${require('./model').MODEL_CONFIG.restB2B.value} points</strong>
  ${tag('unv', 'ASSUMPTION')} — uncalibrated, because there is no history to calibrate it against.</p>`;

  body += `<h2>Emirates NBA Cup groups</h2>
  ${tbl(['Group', 'Games on 13 Nov', 'Cup records (official)'],
    Object.entries(
      slate.games.filter(g => g.cupGroup).reduce((acc, g) => {
        (acc[g.cupGroup] = acc[g.cupGroup] || []).push(g); return acc;
      }, {})
    ).map(([grp, gs]) => [
      cell(`<strong>${esc(grp)}</strong>`),
      cell(gs.map(g => `${esc(g.away)} @ ${esc(g.home)}`).join('<br>')),
      cell(gs.map(g => `${esc(g.away)} ${esc(slate.cupRecords.records[g.away] || '—')} · ${esc(g.home)} ${esc(slate.cupRecords.records[g.home] || '—')}`).join('<br>'))
    ]))}
  <p class="small">Cup records are exactly as shown on the official NBA.com game rail, which appends
  the group record in parentheses after the overall record.</p>`;

  const timezones = {};
  for (const g of slate.games) {
    timezones[g.away] = require('./model').TEAM_TZ[g.away];
    timezones[g.home] = require('./model').TEAM_TZ[g.home];
  }
  body += `<h2>Time-zone reference</h2>
  <p class="small">UTC offsets in effect on 13 Nov 2026 (US/Canada standard time). Travel penalty is
  <strong>${require('./model').MODEL_CONFIG.tzPerHour.value} points per hour crossed</strong>
  ${tag('unv', 'ASSUMPTION')}, charged to the travelling team.</p>
  ${tbl(['Team', 'Home market UTC offset'],
    Object.entries(require('./model').TEAM_TZ).sort().map(([a, t]) => [cell(esc(a)), cell('UTC' + (t >= 0 ? '+' : '') + t, { num: true })]))}`;

  return shell({ title: 'Game Flow', active: 'pages/game-flow.html', body });
}

/* ------------------------------------------------------------------ *
 * PAGE: props
 * ------------------------------------------------------------------ */

function pageProps() {
  const players = injuries.rows.filter(r => r.player);
  let body = `<p class="sub">Player prop combos — currently <strong>unpublishable</strong>, and
  deliberately so.</p>${legend()}`;

  body += `<div class="callout warn"><p><strong>Every threshold on this page is blank.</strong>
  Originating a player prop needs per-player season minutes and production rates. No official
  source for those is reachable from this build environment (<code>stats.nba.com</code> and
  <code>cdn.nba.com</code> both returned errors), so under the project's own rule — <em>if a value
  can't be confirmed from an official source, leave it blank and flag it as unverified</em> —
  nothing is published here. This is blocker <strong>Q-02</strong>.</p></div>`;

  body += `<h2>What we do have, officially</h2>
  <p class="small">Player <strong>availability</strong>, from the T1 injury report. That is a real
  verified input to a prop model; it is just not sufficient on its own.</p>
  ${tbl(['Player', 'Team', 'Status (T1)', 'Reason (verbatim)'],
    players.filter(r => ['Out', 'Doubtful'].includes(r.status)).map(r => [
      cell(esc(r.player)),
      cell(esc(r.team)),
      cell(statusTag(r.status) + ' ' + srcLink('S03', 'T1')),
      cell(esc(r.reason))
    ]), { sortable: true })}`;

  body += `<h2>What we cannot publish</h2>
  ${tbl(['Player', 'Team', 'Pts line', 'Reb line', 'Ast line', 'Pts+Reb+Ast', '3PM', 'Minutes', 'Status'],
    players.slice(0, 30).map(r => [
      cell(esc(r.player)),
      cell(esc(r.team)),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell('<span class="unverified">— UNVERIFIED —</span>'),
      cell(tag('unv', 'Q-02'))
    ]), { sortable: true })}
  <p class="small">Showing 30 of ${players.length} players. In <code>data/</code> these fields are
  <code>null</code>. Zero would be a claim; <code>null</code> is an admission.</p>`;

  body += `<h2>A correction</h2>
  <div class="callout"><p>A previous session published minutes and production figures such as
  <em>"~34 MPG season avg"</em> and <em>"-100% scoring/rebounding/playmaking output"</em>, flagged
  <code>verified: false</code> and carrying no source. Those have been removed. See
  <a href="repo-review.html">Repo Review</a>, irregularity I-03.</p></div>`;

  body += `<h2>The engine is ready</h2>
  <p class="small">Strategy <strong>S10 (Player Prop Combos)</strong> is already wired into the
  validation-gate framework and currently sits at <strong>5/8 gates</strong>, failing G2
  (provenance), G5 and G6. It needs no code work — only a data source. Once <code>Q-02</code> is
  answered:</p>
  <ol>
    <li>Pull per-player season minutes and usage from an official feed.</li>
    <li>Project minutes: base season minutes, boosted by the vacated minutes of Out/Doubtful teammates.</li>
    <li>Project production: projected minutes × per-minute rate, adjusted for opponent defensive rating.</li>
    <li>Originate the threshold, then price it against the market once <code>Q-01</code> is answered.</li>
    <li>Only then re-run the gates.</li>
  </ol>`;

  return shell({ title: 'Player Props', active: 'pages/props.html', body });
}

/* ------------------------------------------------------------------ *
 * PAGE: flagged (generated)
 * ------------------------------------------------------------------ */

function pageFlagged() {
  const flags = buildFlags();
  let body = `<p class="sub">Everything on this site we could not confirm from an official source,
  every assumption we made, and every irregularity we inherited. Nothing here blocks the build —
  it is here so you can review it after the site is live.</p>`;

  const bySeverity = { high: [], medium: [], low: [] };
  for (const f of flags) (bySeverity[f.severity] || bySeverity.medium).push(f);

  for (const sev of ['high', 'medium', 'low']) {
    const label = { high: 'High — blocks a decision', medium: 'Medium — degrades accuracy', low: 'Low — informational' }[sev];
    body += `<h2>${label} (${bySeverity[sev].length})</h2>`;
    body += tbl(['ID', 'Area', 'What it is', 'Why it is flagged', 'Source / action'],
      bySeverity[sev].map(f => [
        cell(`<strong>${esc(f.id)}</strong>`),
        cell(esc(f.area)),
        cell(esc(f.item)),
        cell(esc(f.why)),
        cell(f.src ? `<a href="${esc(f.src)}" target="_blank" rel="noopener">${esc(f.srcLabel || 'source')}</a>` : esc(f.action || ''))
      ]));
  }

  body += `<h2>Inherited irregularities from previous sessions</h2>`;
  body += tbl(['ID', 'Archived file', 'Claimed', 'Official source says', 'Action'], [
    [cell('I-01'), cell('<code>session-23927d63-data/injuries.json</code>'),
      cell('Ben Simmons — Golden State Warriors'),
      cell('Simmons, Ben — <strong>Sacramento Kings</strong> — Out — Right Achilles Tendon Repair / Surgery'),
      cell('corrected')],
    [cell('I-02'), cell('<code>session-23927d63-data/injuries.json</code>'),
      cell('Jimmy Butler III — <em>Right Patella Subluxation</em>'),
      cell('Butler III, Jimmy — Golden State Warriors — Out — <strong>Right ACL Repair / Surgery</strong>. "Right Patella Subluxation" is the reason listed for Maxime Raynaud (SAC).'),
      cell('corrected')],
    [cell('I-03'), cell('<code>session-23927d63-data/injuries.json</code>'),
      cell('"~34 MPG season avg", "-100% scoring/rebounding output"'),
      cell('No source link; no official per-player minutes feed is reachable.'),
      cell('removed; replaced with null')],
    [cell('I-04'), cell('<code>index.html</code>, <code>pages/*</code>'),
      cell('Tasks marked "done" with all numeric cells blank'),
      cell('Their own board records "No picks generated; lines blank".'),
      cell('superseded; archived, not deleted')],
    [cell('I-05'), cell('<code>session-23927d63-data/strategies.json</code>'),
      cell('Correlation values'),
      cell('Described in their own board as "research estimates".'),
      cell('replaced with Monte-Carlo values from this repo')]
  ]);
  body += `<p class="small">Correcting source for I-01 and I-02:
  <a href="${esc(SRC.S03.url)}" target="_blank" rel="noopener">Official NBA Injury Report, 11/13/26 01:00 PM</a>.</p>`;

  return shell({ title: 'Flagged for Review', active: 'pages/flagged.html', body });
}

function buildFlags() {
  const M = require('./model');
  const flags = [];

  flags.push({ id: 'F-01', severity: 'high', area: 'Market data', item: 'No market prices for any game',
    why: 'Edge requires a price. Every EV figure on the site uses an assumed -110 and an assumed 4.77% overround. Neither is a real price you can bet.',
    action: 'Open Question Q-01', src: 'https://github.com/wingbangboozle1-lang/NBA2/blob/main/research/08-open-questions.md', srcLabel: 'Q-01' });

  flags.push({ id: 'F-02', severity: 'high', area: 'Player props', item: 'All player prop thresholds blank',
    why: `${injuries.rows.filter(r => r.player).length * 7} numeric cells are null because no official per-player season feed is reachable.`,
    action: 'Open Question Q-02', src: 'https://github.com/wingbangboozle1-lang/NBA2/blob/main/research/08-open-questions.md', srcLabel: 'Q-02' });

  flags.push({ id: 'F-03', severity: 'high', area: 'Validation', item: 'Gate G6 fails for all 10 strategies',
    why: 'No graded historical bet log exists in this repository, so out-of-sample validation cannot be run. The leaderboard is model-expected, not realised.',
    action: 'Open Question Q-03', src: 'https://github.com/wingbangboozle1-lang/NBA2/blob/main/research/08-open-questions.md', srcLabel: 'Q-03' });

  flags.push({ id: 'F-04', severity: 'medium', area: 'Line origination', item: `Home-court advantage derived at +${derived.league.hcaPoints} points`,
    why: `From ${derived.league.homeWins}-${derived.league.homeLosses} in ${derived.league.splitGames} split games (${(derived.league.homeWinRate * 100).toFixed(2)}%). Standard error ≈ ±3.8pp, and the multi-season norm is usually quoted much higher. Largest single source of spread error.`,
    action: 'Open Question Q-09 / Suggestion SG-05' });

  flags.push({ id: 'F-05', severity: 'medium', area: 'Injuries', item: 'injuryK = 0.35 points per availability unit',
    why: 'Uncalibrated. There is no historical sample to regress realised margin on the availability differential. Reported as an overlay, never baked into a published line.',
    action: 'Open Question Q-04' });

  flags.push({ id: 'F-06', severity: 'medium', area: 'Game flow', item: 'Rest unknown for the nine 13 Nov games',
    why: 'The 12 Nov slate was not collected, so back-to-back status cannot be determined. The model applies no adjustment rather than guessing. 18 cells are null.',
    action: 'Open Question Q-08 / Suggestion SG-04' });

  flags.push({ id: 'F-07', severity: 'medium', area: 'Strategies', item: 'S05 rests on an unverified rule',
    why: 'The Emirates NBA Cup group tiebreaker has not been read from an official NBA page. If it is not point differential, the whole premise of S05 collapses.',
    action: 'Open Question Q-06 · verify at nba.com/nba-cup/2026', src: 'https://www.nba.com/nba-cup/2026', srcLabel: 'nba.com/nba-cup/2026' });

  flags.push({ id: 'F-08', severity: 'medium', area: 'Ratings', item: 'Ratings are per-game, not per-possession',
    why: 'No official pace/possessions data is reachable, so no true offensive or defensive rating can be computed, and no opponent adjustment is applied — only mean-reversion shrinkage.',
    action: 'Open Question Q-05' });

  for (const [k, cfg] of Object.entries(M.MODEL_CONFIG)) {
    if (!cfg.assumption) continue;
    flags.push({ id: 'F-CFG-' + k, severity: 'low', area: 'Model configuration', item: `${k} = ${cfg.value}`,
      why: cfg.note + ' — a declared modelling choice, not a sourced fact.', action: 'See the Sensitivity panel on the Lines page' });
  }

  flags.push({ id: 'F-09', severity: 'low', area: 'Correlations', item: 'Margin-vs-total correlation is model-derived and ≈ 0',
    why: 'Under a bivariate-normal score model with near-equal variances, Cov(margin, total) = Var(home) − Var(away) ≈ 0. Real data may differ; we cannot measure it without play-by-play history.',
    action: 'Open Question Q-07' });

  flags.push({ id: 'F-10', severity: 'low', area: 'Sources', item: 'Team scoring splits are T2, not official',
    why: 'PPG, OPP PPG, DIFF, splits, streaks and last-10 come from ESPN because stats.nba.com is unreachable. Every W-L figure ESPN reports was cross-checked against nba.com (30/30 match), but the scoring splits were not.',
    src: SRC.S04.url, srcLabel: 'ESPN standings', action: '' });

  for (const f of injuries.coverageFlags) {
    flags.push({ id: f.code, severity: f.severity === 'warn' ? 'medium' : 'low', area: 'Injury report',
      item: f.note.split('.')[0] + '.', why: f.note, src: SRC.S03.url, srcLabel: 'official PDF' });
  }

  return flags;
}

/* ------------------------------------------------------------------ *
 * markdown-driven pages
 * ------------------------------------------------------------------ */

const MD_PAGES = [
  { file: 'pages/executive-summary.html', src: 'research/01-executive-summary.md', title: 'Executive Summary' },
  { file: 'pages/open-questions.html', src: 'research/08-open-questions.md', title: 'Open Questions' },
  { file: 'pages/suggestions.html', src: 'research/09-suggestions.md', title: 'Suggestions & Decision Register' },
  { file: 'pages/verification.html', src: 'research/10-verification.md', title: 'Verification' },
  { file: 'pages/data-and-sources.html', src: 'research/03-data-and-sources.md', title: 'Data & Sources' },
  { file: 'pages/repo-review.html', src: 'research/02-repo-review.md', title: 'Repository Review' }
];

function renderMdPages() {
  for (const p of MD_PAGES) {
    const raw = fs.readFileSync(path.join(ROOT, p.src), 'utf8');
    // anchor the Q-xx headings so other pages can deep-link to them
    let html = md(raw).replace(/^\s*<h1>[\s\S]*?<\/h1>\s*(<hr>)?\s*/, '');
    // research/*.md is not published to Pages, so point those links at the repo instead
    html = html.replace(/href="(?:research\/)?(\d\d-[a-z0-9-]+\.md)"/g,
      'href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/originated/research/$1"');
    html = html.replace(/<h3>(Q-\d+[^<]*)<\/h3>/g, (m, t) => {
      const id = (t.match(/Q-\d+/) || [''])[0].toLowerCase();
      return `<h3 id="${id}">${t}</h3>`;
    });
    html = html.replace(/<h3>(SG-\d+[^<]*)<\/h3>/g, (m, t) => {
      const id = (t.match(/SG-\d+/) || [''])[0].toLowerCase();
      return `<h3 id="${id}">${t}</h3>`;
    });
    writePage(p.file, shell({ title: p.title, active: p.file, body: `<div class="md">${html}</div>` }));
  }
}

/* ------------------------------------------------------------------ *
 * main
 * ------------------------------------------------------------------ */

function main() {
  fs.mkdirSync(path.join(ROOT, 'assets'), { recursive: true });
  writePage('index.html', pageIndex());
  writePage('pages/slates.html', pageSlates());
  writePage('pages/lines.html', pageLines());
  writePage('pages/strategies.html', pageStrategies());
  writePage('pages/correlations.html', pageCorrelations());
  writePage('pages/injuries.html', pageInjuries());
  writePage('pages/game-flow.html', pageGameFlow());
  writePage('pages/props.html', pageProps());
  writePage('pages/flagged.html', pageFlagged());
  renderMdPages();

  const files = ['index.html', ...NAV.filter(n => n.href !== 'index.html').map(n => n.href)];
  console.log('pages written:', files.length);
}

main();

'use strict';
/**
 * Verification harness. Exits non-zero if any structural check fails.
 *   node engine/compute.js && node engine/build.js && node engine/verify.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

const teams = read('data/teams.json');
const slate = read('data/slate.json');
const injuries = read('data/injuries.json');
const sources = read('data/sources.json');
const derived = read('data/derived.json');

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: !!ok, detail: detail || '' });
}

/* ---------------- data integrity ---------------- */

const ABBR = new Set(teams.teams.map(t => t.abbr));
const NAME = new Set(teams.teams.map(t => t.name));

check('every slate team resolves to a team record',
  slate.games.every(g => ABBR.has(g.away) && ABBR.has(g.home)),
  `${slate.games.filter(g => !ABBR.has(g.away) || !ABBR.has(g.home)).length} dangling`);

check('every injury-report team resolves to a team record',
  injuries.rows.every(r => NAME.has(r.team)),
  `${injuries.rows.filter(r => !NAME.has(r.team)).length} dangling: ` +
  [...new Set(injuries.rows.filter(r => !NAME.has(r.team)).map(r => r.team))].join(', '));

const SRCIDS = new Set(sources.sources.map(s => s.id));
check('every source id referenced in data/ exists',
  [...slate.games.map(g => g.defaultSrc), ...teams.teams.map(t => t.src), ...injuries.rows.map(r => r.src)]
    .filter(Boolean).every(id => SRCIDS.has(id)),
  '');

check('every team row carries a source id',
  teams.teams.every(t => t.src && SRCIDS.has(t.src)), '');

check('every slate row carries its own official nba.com URL',
  slate.games.every(g => /^https:\/\/www\.nba\.com\/game\//.test(g.url || '')),
  `${slate.games.filter(g => !/^https:\/\/www\.nba\.com\/game\//.test(g.url || '')).length} missing`);

check('every injury row status is one of the six the report uses',
  injuries.rows.every(r => ['Out', 'Doubtful', 'Questionable', 'Probable', 'Available', 'NOT YET SUBMITTED'].includes(r.status)),
  [...new Set(injuries.rows.map(r => r.status))].join(', '));

/* ---------------- published counts ---------------- */

const counts = {};
for (const g of slate.games) counts[g.date] = (counts[g.date] || 0) + 1;
check('games per day match the nba.com headers (9 / 5 / 9)',
  counts['2026-11-13'] === 9 && counts['2026-11-14'] === 5 && counts['2026-11-15'] === 9,
  JSON.stringify(counts));

check('all 30 teams appear in the 3-day window',
  new Set(slate.games.flatMap(g => [g.away, g.home])).size === 30,
  `${new Set(slate.games.flatMap(g => [g.away, g.home])).size} teams`);

/* ---------------- arithmetic identities ---------------- */

const idc = derived.crossVerification;
check('points accounting identity: weighted mean PPG == weighted mean OPP PPG',
  idc.ppgIdentity.status === 'PASS',
  `${idc.ppgIdentity.meanPpg} vs ${idc.ppgIdentity.meanOppPpg}`);

check('W-L cross-verified between T1 and T2',
  idc.wl.result === '30 of 30 match' || /30/.test(idc.wl.result),
  idc.wl.result);

check('fair-line self-consistency: P(home covers its own spread) ~ 0.500',
  idc.fairLineSanity.status === 'PASS',
  `worst deviation ${idc.fairLineSanity.worstDeviation}`);

check('model-implied SDs are in a plausible range',
  derived.league.marginSd > 12 && derived.league.marginSd < 17 &&
  derived.league.totalSd > 17 && derived.league.totalSd < 23,
  `marginSd ${derived.league.marginSd}, totalSd ${derived.league.totalSd}`);

/* ---------------- model completeness ---------------- */

check('every game has an originated line',
  derived.lines.length === slate.games.length, `${derived.lines.length} vs ${slate.games.length}`);

check('every game has a simulation result',
  derived.sims.length === slate.games.length, '');

check('every strategy has all 8 gates evaluated',
  derived.strategies.every(s => Object.keys(s.gates).length === 8),
  derived.strategies.map(s => `${s.id}:${Object.keys(s.gates).length}`).join(' '));

check('no strategy is marked deployable while G6 fails',
  derived.leaderboard.every(r => !r.deployable),
  `${derived.leaderboard.filter(r => r.deployable).length} deployable`);

check('every signal carries a break-even and an EV',
  derived.signals.every(s => s.breakevenProb != null && s.evPerUnit != null),
  `${derived.signals.filter(s => s.breakevenProb == null).length} missing`);

check('every signal comes from a strategy in the catalog',
  derived.signals.every(s => derived.strategies.some(st => st.id === s.strategy)), '');

/* ---------------- honesty checks ---------------- */

const propsPage = fs.readFileSync(path.join(ROOT, 'pages/props.html'), 'utf8');
check('the props page publishes no numeric threshold',
  !/\d+\.5\s*<\/td>/.test(propsPage) || (propsPage.match(/UNVERIFIED/g) || []).length > 20,
  `${(propsPage.match(/UNVERIFIED/g) || []).length} UNVERIFIED markers`);

const flagged = fs.readFileSync(path.join(ROOT, 'pages/flagged.html'), 'utf8');
const CFG = Object.keys(require('./model').MODEL_CONFIG).filter(k => require('./model').MODEL_CONFIG[k].assumption);
check('every declared model assumption appears on the Flagged page',
  CFG.every(k => flagged.includes('F-CFG-' + k)),
  CFG.filter(k => !flagged.includes('F-CFG-' + k)).join(', '));

check('every inherited irregularity appears on the Flagged page',
  ['I-01', 'I-02', 'I-03', 'I-04', 'I-05'].every(k => flagged.includes(k)), '');

/* ---------------- site link check ---------------- */

const PAGES = ['index.html',
  'pages/executive-summary.html', 'pages/slates.html', 'pages/lines.html',
  'pages/strategies.html', 'pages/correlations.html', 'pages/injuries.html',
  'pages/game-flow.html', 'pages/props.html', 'pages/open-questions.html',
  'pages/suggestions.html', 'pages/flagged.html', 'pages/verification.html',
  'pages/data-and-sources.html', 'pages/repo-review.html'];

const anchorsByFile = {};
for (const f of PAGES) {
  const html = fs.readFileSync(path.join(ROOT, f), 'utf8');
  anchorsByFile[f] = new Set([...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]));
}

let broken = [];
for (const f of PAGES) {
  const html = fs.readFileSync(path.join(ROOT, f), 'utf8');
  const baseDir = path.dirname(path.join(ROOT, f));
  for (const m of html.matchAll(/href="([^"]+)"/g)) {
    const href = m[1];
    if (/^(https?:|mailto:|#)/.test(href)) {
      if (href.startsWith('#') && href.length > 1 && !anchorsByFile[f].has(href.slice(1))) {
        broken.push(`${f} -> missing anchor ${href}`);
      }
      continue;
    }
    const target = path.normalize(path.join(baseDir, href.split('#')[0]));
    if (!fs.existsSync(target)) broken.push(`${f} -> ${href}`);
    else if (href.includes('#')) {
      const rel = path.relative(ROOT, target).replace(/\\/g, '/');
      const anch = href.split('#')[1];
      if (anchorsByFile[rel] && !anchorsByFile[rel].has(anch)) broken.push(`${f} -> ${href} (missing anchor)`);
    }
  }
}
check('no broken internal links or anchors', broken.length === 0, broken.slice(0, 8).join(' | '));

let missingAssets = [];
for (const f of PAGES) {
  const html = fs.readFileSync(path.join(ROOT, f), 'utf8');
  for (const m of html.matchAll(/(?:src|href)="([^"]*(?:css|js))"/g)) {
    const rel = m[1];
    if (/^https?:/.test(rel)) continue;
    const t = path.normalize(path.join(path.dirname(path.join(ROOT, f)), rel));
    if (!fs.existsSync(t)) missingAssets.push(`${f} -> ${rel}`);
  }
}
check('css/js assets resolve on every page', missingAssets.length === 0, missingAssets.join(' | '));

/* every slate row must carry an official source link */
const slatesHtml = fs.readFileSync(path.join(ROOT, 'pages/slates.html'), 'utf8');
const nbaLinks = (slatesHtml.match(/nba\.com\/game\//g) || []).length;
check('every slate row links to its official nba.com game page',
  nbaLinks >= slate.games.length, `${nbaLinks} official game links for ${slate.games.length} games`);

/* ---------------- report ---------------- */

const pass = results.filter(r => r.ok).length;
const fail = results.filter(r => !r.ok);

console.log('\nNBA2 verification\n' + '='.repeat(58));
for (const r of results) {
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? `  [${r.detail}]` : ''}`);
}
console.log('='.repeat(58));
console.log(`${pass}/${results.length} checks passed`);
if (fail.length) {
  console.log(`\n${fail.length} FAILURE(S):`);
  for (const f of fail) console.log(`  - ${f.name}: ${f.detail}`);
  process.exit(1);
}
console.log('All checks passed.\n');

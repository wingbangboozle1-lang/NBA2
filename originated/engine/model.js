'use strict';
/**
 * Line origination + ratings + rotation + game flow.
 *
 * HARD RULE for this file: every number is either
 *   (a) copied from data/*.json (which carries a source id + tier), or
 *   (b) computed by a formula written out in research/04-line-origination.md.
 * Anything that is a judgement constant lives in MODEL_CONFIG with `assumption: true`
 * and is surfaced on the Flagged for Review page.
 */

const L = require('./lib');

/* ------------------------------------------------------------------ *
 * Model configuration. Items flagged `assumption: true` are NOT sourced
 * from any official feed; they are declared modelling choices.
 * ------------------------------------------------------------------ */
const MODEL_CONFIG = {
  priorGames:   { value: 12,   assumption: true, note: 'Shrinkage prior: a team is pulled toward 0 net rating with the weight of 12 league-average games.' },
  priorMov:     { value: 0,    assumption: true, note: 'Prior mean net rating is league average (0).' },
  kTotal:       { value: 0.85, assumption: true, note: 'Shrinkage applied to the team-vs-opponent points expectation (1.00 = no shrinkage).' },
  sdScore:      { value: 11.5, assumption: true, note: 'Standard deviation of the idiosyncratic component of one team\'s score, in points. Tuned so the realised single-team score SD lands near 12.7 and the game-margin SD near 14.5.' },
  rhoScore:     { value: 0.20, assumption: true, note: 'Correlation between the two teams\' idiosyncratic score shocks. Combined with the pace shock below this produces a realised score correlation of roughly 0.31.' },
  paceSd:       { value: 0.04, assumption: true, note: 'Standard deviation of a multiplicative pace/possessions shock applied to BOTH scores. This is the only mechanism in the model that couples the total to team quality.' },
  pythagExp:    { value: 13.91, assumption: true, note: 'Pythagorean win-expectation exponent (Morey / Basketball-Reference constant).' },
  restB2B:      { value: -1.6, assumption: true, note: 'Points added to a team\'s expected margin when playing the second night of a back-to-back.' },
  rest3Plus:    { value: 0.25, assumption: true, note: 'Points added for 3+ days of rest.' },
  tzPerHour:    { value: -0.15, assumption: true, note: 'Points per hour of time-zone crossed, applied to the travelling team.' },
  injuryK:      { value: 0.35, assumption: true, note: 'Points of team strength lost per 1.0 unit of the unavailability index. UNCALIBRATED - reported but not applied to published lines.' },
  mcIterations: { value: 200000, assumption: true, note: 'Monte-Carlo draws per game used for the correlation matrix.' },
  mcSeed:       { value: 20261113, assumption: true, note: 'PRNG seed, so every published figure is reproducible.' }
};

/** UTC offsets for each team's home market (US/Canada standard time, in effect on 2026-11-13). */
const TEAM_TZ = {
  ATL: -5, BOS: -5, BKN: -5, CHA: -5, CHI: -6, CLE: -5, DAL: -6, DEN: -7, DET: -5,
  GSW: -8, HOU: -6, IND: -5, LAC: -8, LAL: -8, MEM: -6, MIA: -5, MIL: -6, MIN: -6,
  NOP: -6, NYK: -5, OKC: -6, ORL: -5, PHI: -5, PHX: -7, POR: -8, SAC: -8, SAS: -6,
  TOR: -5, UTA: -7, WSH: -5
};

/** Weight of each official injury-report status in the availability indices. */
const STATUS_WEIGHT = {
  'Out': 1.00,
  'Doubtful': 0.75,
  'Questionable': 0.40,
  'Probable': 0.15,
  'Available': 0.00,
  'NOT YET SUBMITTED': null   // explicitly excluded - it is an absence of information, not information
};

/* ------------------------------------------------------------------ *
 * 1. League context + power ratings
 * ------------------------------------------------------------------ */

function buildLeague(teams) {
  const n = teams.length;
  // Games-weighted league averages. The unweighted mean over teams does NOT satisfy
  // mean(PPG) == mean(OPP PPG) because teams have played different numbers of games;
  // the games-weighted mean does (every point scored is a point allowed).
  let totalGames = 0, wPpg = 0, wOpp = 0;
  for (const t of teams) {
    const gp = t.wins + t.losses;
    totalGames += gp; wPpg += t.ppg * gp; wOpp += t.oppPpg * gp;
  }
  const lgPpg = wPpg / totalGames;
  const lgOppPpg = wOpp / totalGames;

  // League-wide home win rate, derived from the home/away splits (source S04).
  let hw = 0, hl = 0;
  for (const t of teams) {
    const [a, b] = t.home.split('-').map(Number);
    hw += a; hl += b;
  }
  const homeWinRate = hw / (hw + hl);

  // Model-implied SDs, including the pace term (which inflates the total's variance because
  // it scales with the combined score, but barely moves the margin because it scales with
  // the difference, which is small).
  const s2 = Math.pow(MODEL_CONFIG.sdScore.value, 2);
  const rho = MODEL_CONFIG.rhoScore.value;
  const pace = MODEL_CONFIG.paceSd.value;
  const marginSd = Math.sqrt(2 * s2 * (1 - rho));
  const totalSd = Math.sqrt(2 * s2 * (1 + rho) + Math.pow(pace * 2 * lgPpg, 2));

  // Home-court advantage expressed in points, implied by the league home win rate.
  const hcaPoints = marginSd * L.normalPpf(homeWinRate);

  const ratings = {};
  for (const t of teams) {
    const gp = t.wins + t.losses;
    const mov = t.ppg - t.oppPpg;
    const pg = MODEL_CONFIG.priorGames.value, pm = MODEL_CONFIG.priorMov.value;
    const shrunkMov = (gp * mov + pg * pm) / (gp + pg);
    const pyth = L.pythagoreanWinPct(t.ppg, t.oppPpg, MODEL_CONFIG.pythagExp.value);
    const actual = t.wins / gp;
    ratings[t.abbr] = {
      abbr: t.abbr, name: t.name, conf: t.conf, gp, mov,
      shrunkMov,
      pythWinPct: pyth,
      actualWinPct: actual,
      luck: actual - pyth,                       // +ve = winning more than the scoring profile implies
      offRating: t.ppg - lgPpg,
      defRating: lgPpg - t.oppPpg,
      src: t.src
    };
  }

  return {
    lgPpg, lgOppPpg, homeWinRate, homeWins: hw, homeLosses: hl,
    marginSd, totalSd, hcaPoints, ratings,
    teamCount: n, totalGames, splitGames: hw + hl
  };
}

/* ------------------------------------------------------------------ *
 * 2. Availability / rotation indices (official injury report only)
 * ------------------------------------------------------------------ */

function buildAvailability(injuries) {
  const byTeam = {};
  for (const r of injuries.rows) {
    const w = STATUS_WEIGHT[r.status];
    if (w === null || w === undefined) continue;           // NOT YET SUBMITTED
    const key = r.team;
    byTeam[key] = byTeam[key] || {
      rows: [], injuryIndex: 0, unavailIndex: 0, rotationIndex: 0, gLeagueIndex: 0, counts: {}
    };
    byTeam[key].rows.push(r);
    byTeam[key].counts[r.status] = (byTeam[key].counts[r.status] || 0) + 1;
    byTeam[key].unavailIndex += w;
    if (r.category === 'Injury/Illness') byTeam[key].injuryIndex += w;
    // A G League two-way assignment or G League assignment removes a player who was not
    // part of the NBA rotation. Counting it as a rotation loss would be wrong, so it is
    // tracked separately and excluded from the index that drives the availability strategy.
    if (r.category && r.category.startsWith('G League')) byTeam[key].gLeagueIndex += w;
    else byTeam[key].rotationIndex += w;   // Injury/Illness, Not With Team, League Suspension
  }
  for (const k of Object.keys(byTeam)) {
    byTeam[k].injuryIndex = round4(byTeam[k].injuryIndex);
    byTeam[k].unavailIndex = round4(byTeam[k].unavailIndex);
    byTeam[k].rotationIndex = round4(byTeam[k].rotationIndex);
    byTeam[k].gLeagueIndex = round4(byTeam[k].gLeagueIndex);
    byTeam[k].listed = byTeam[k].rows.length;
    byTeam[k].out = byTeam[k].counts['Out'] || 0;
    byTeam[k].doubtful = byTeam[k].counts['Doubtful'] || 0;
    byTeam[k].questionable = byTeam[k].counts['Questionable'] || 0;
    byTeam[k].probable = byTeam[k].counts['Probable'] || 0;
  }
  return byTeam;
}

/** Map an official team display name ("Orlando Magic") to an availability bucket. */
function availabilityForTeam(avail, teamName) {
  return avail[teamName] || null;
}

/* ------------------------------------------------------------------ *
 * 3. Game flow: rest, back-to-back, travel
 * ------------------------------------------------------------------ */

function buildScheduleContext(slate) {
  const games = [...slate.games].sort((a, b) =>
    a.date.localeCompare(b.date) || a.etSort - b.etSort);
  const lastPlayed = {};   // abbr -> date of most recent game inside the window
  const out = [];
  for (const g of games) {
    const awayPrev = lastPlayed[g.away] || null;
    const homePrev = lastPlayed[g.home] || null;
    const awayRest = awayPrev ? daysBetween(awayPrev, g.date) - 1 : null;
    const homeRest = homePrev ? daysBetween(homePrev, g.date) - 1 : null;
    out.push({
      id: g.id, date: g.date, away: g.away, home: g.home,
      awayPrev, homePrev, awayRest, homeRest,
      awayB2B: awayRest === 0, homeB2B: homeRest === 0,
      tzAway: TEAM_TZ[g.away] ?? null,
      tzHome: TEAM_TZ[g.home] ?? null,
      tzDelta: (TEAM_TZ[g.away] != null && TEAM_TZ[g.home] != null)
        ? Math.abs(TEAM_TZ[g.home] - TEAM_TZ[g.away]) : null
    });
    lastPlayed[g.away] = g.date;
    lastPlayed[g.home] = g.date;
  }
  return out;
}

function daysBetween(a, b) {
  const da = Date.parse(a + 'T00:00:00Z'), db = Date.parse(b + 'T00:00:00Z');
  return Math.round((db - da) / 86400000);
}

function restPoints(rest) {
  if (rest === null) return { pts: 0, known: false };
  if (rest === 0) return { pts: MODEL_CONFIG.restB2B.value, known: true };
  if (rest >= 3) return { pts: MODEL_CONFIG.rest3Plus.value, known: true };
  return { pts: 0, known: true };
}

/* ------------------------------------------------------------------ *
 * 4. Originated lines
 * ------------------------------------------------------------------ */

/**
 * Originate a fair line for one game.
 * Returns base (data-only), gameflow-adjusted (published) and an injury-overlay variant.
 */
function originate(game, flow, league, availByName) {
  const A = league.ratings[game.away], H = league.ratings[game.home];
  const lg = league.lgPpg, k = MODEL_CONFIG.kTotal.value;

  // Points expectation: league average + shrinkage * mean of (my offence, their defence).
  // Expected points = league average + shrinkage * (my offence - their defence) / 2.
  // defRating is defined as (league avg - oppPpg), so a STRONG defence has a POSITIVE
  // defRating and must be SUBTRACTED from the opponent's expectation.
  const eA = lg + k * (A.offRating - H.defRating) / 2;
  const eH = lg + k * (H.offRating - A.defRating) / 2;

  const total = eA + eH;

  // Margin from the HOME team's point of view.
  const ratingDelta = H.shrunkMov - A.shrunkMov;
  const baseMargin = ratingDelta + league.hcaPoints;

  const rA = restPoints(flow.awayRest), rH = restPoints(flow.homeRest);
  const tzPts = flow.tzDelta == null ? 0 : -MODEL_CONFIG.tzPerHour.value * flow.tzDelta; // applied against the traveller (away)
  const gameflowAdj = (rH.pts - rA.pts) + (-tzPts);
  const publishedMargin = baseMargin + gameflowAdj;

  const aIdx = availByName[A.name] || null;
  const hIdx = availByName[H.name] || null;
  const injuryAdj = MODEL_CONFIG.injuryK.value *
    ((aIdx ? aIdx.unavailIndex : 0) - (hIdx ? hIdx.unavailIndex : 0));
  const injuryMargin = publishedMargin + injuryAdj;

  const pHomeBase = L.normalCdf(baseMargin / league.marginSd);
  const pHome = L.normalCdf(publishedMargin / league.marginSd);

  // Pythagorean / log5 cross-check (no Normal assumption, no home-court term).
  const pythPHome = L.log5(H.pythWinPct, A.pythWinPct);

  return {
    id: game.id,
    away: game.away, home: game.home,
    expAwayPts: r2(eA), expHomePts: r2(eH), expTotal: r2(total),
    ratingDeltaHome: r2(ratingDelta),
    hcaPoints: r2(league.hcaPoints),
    restAdjHome: r2(rH.pts - rA.pts),
    tzAdjHome: r2(-tzPts),
    gameflowAdjHome: r2(gameflowAdj),
    baseMarginHome: r2(baseMargin),
    marginHome: r2(publishedMargin),
    injuryAdjHome: r2(injuryAdj),
    marginHomeWithInjury: r2(injuryMargin),
    spreadHome: -L.snapHalf(publishedMargin),          // home spread (negative = home favoured)
    spreadHomeBase: -L.snapHalf(baseMargin),
    spreadHomeInjury: -L.snapHalf(injuryMargin),
    totalLine: L.snapHalf(total),
    pHomeBase, pHome, pAway: 1 - pHome,
    pythPHome,
    mlHome: L.americanFromProb(pHome),
    mlAway: L.americanFromProb(1 - pHome),
    restKnown: rA.known && rH.known,
    awayRest: flow.awayRest, homeRest: flow.homeRest,
    awayB2B: flow.awayB2B, homeB2B: flow.homeB2B,
    tzDelta: flow.tzDelta
  };
}

/* ------------------------------------------------------------------ *
 * 5. Monte-Carlo: correlations and correlation-aware parlay pricing
 * ------------------------------------------------------------------ */

function simulateGame(line, league, iterations) {
  const rho = MODEL_CONFIG.rhoScore.value, s = MODEL_CONFIG.sdScore.value;
  const paceSd = MODEL_CONFIG.paceSd.value;
  const rng = L.makeRng(MODEL_CONFIG.mcSeed.value + hashStr(line.id));
  const nrm = L.makeNormalPair(rng);
  const n = iterations;

  // Anchor the simulator to the PUBLISHED line, not to the raw points model:
  //   mean(H) - mean(A) == the originated margin, and mean(H) + mean(A) == the originated total.
  // Without this the spread and the simulator disagree and P(cover) drifts off 0.500.
  const mA = (line.expTotal - line.marginHome) / 2;
  const mH = (line.expTotal + line.marginHome) / 2;

  const aScore = new Float64Array(n), hScore = new Float64Array(n);
  const margin = new Float64Array(n), total = new Float64Array(n);
  const homeWin = new Float64Array(n), homeCover = new Float64Array(n), over = new Float64Array(n);

  const spreadHome = line.spreadHome;     // e.g. -6.5
  const totalLine = line.totalLine;

  for (let i = 0; i < n; i++) {
    const z1 = nrm(), z2 = nrm();
    // Correlate the two team scores with coefficient rho.
    const xa = z1;
    const xh = rho * z1 + Math.sqrt(1 - rho * rho) * z2;
    // Multiplicative pace shock: more possessions raises BOTH scores, which is what
    // makes a big expected margin translate into a positive margin-vs-total correlation.
    const pace = 1 + paceSd * nrm();
    const a = (mA + s * xa) * pace, h = (mH + s * xh) * pace;
    aScore[i] = a; hScore[i] = h;
    const m = h - a, t = h + a;
    margin[i] = m; total[i] = t;
    homeWin[i] = m > 0 ? 1 : 0;
    homeCover[i] = (m + spreadHome) > 0 ? 1 : 0;   // home covers when margin + spread > 0
    over[i] = t > totalLine ? 1 : 0;
  }

  const p = (arr) => { let c = 0; for (let i = 0; i < n; i++) c += arr[i]; return c / n; };

  const binary = {
    homeWin: Array.from(homeWin, v => v),
    homeCover: Array.from(homeCover, v => v),
    over: Array.from(over, v => v)
  };

  return {
    n,
    pHomeWinMC: p(homeWin),
    pHomeCoverMC: p(homeCover),
    pOverMC: p(over),
    corr: {
      scoreAwayScoreHome: L.pearson(Array.from(aScore), Array.from(hScore)),
      marginTotal: L.pearson(Array.from(margin), Array.from(total)),
      awayScoreTotal: L.pearson(Array.from(aScore), Array.from(total)),
      homeScoreTotal: L.pearson(Array.from(hScore), Array.from(total))
    },
    phi: {
      homeWin_over: L.phi(binary.homeWin, binary.over),
      homeCover_over: L.phi(binary.homeCover, binary.over),
      homeWin_homeCover: L.phi(binary.homeWin, binary.homeCover)
    },
    binary
  };
}

/**
 * Home court is derived from this season's splits, not assumed - but it is derived from a
 * small sample, so re-price the whole board at alternative values to show how much it moves.
 */
function hcaSensitivity(games, flowsById, league, availByName) {
  const out = [];
  for (const hca of HCA_ALTERNATIVES) {
    const lg2 = { ...league, hcaPoints: hca };
    let favFlips = 0;
    const rows = games.map(g => {
      const line = originate(g, flowsById[g.id], lg2, availByName);
      const base = originate(g, flowsById[g.id], league, availByName);
      if (Math.sign(line.spreadHome) !== Math.sign(base.spreadHome)) favFlips++;
      return {
        id: g.id, matchup: `${g.away} @ ${g.home}`,
        spreadHome: line.spreadHome, pHome: r2(line.pHome)
      };
    });
    out.push({ hca, rows, favouriteFlips: favFlips });
  }
  return out;
}

function hashStr(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

/* ------------------------------------------------------------------ *
 * 6. Sensitivity: how much do the declared assumptions move the line?
 * ------------------------------------------------------------------ */

const SENSITIVITY_GRID = [
  { key: 'rhoScore', values: [-0.10, 0.10, 0.30, 0.50] },
  { key: 'sdScore', values: [10.0, 12.0, 14.0] },
  { key: 'kTotal', values: [0.70, 0.85, 1.00] }
];

/** Home court is derived, not assumed - but it is derived from a small sample, so we
 *  re-price the board at alternative values to show how much it matters. */
const HCA_ALTERNATIVES = [0.5, 1.5, 2.5];

function sensitivity(game, flow, league, availByName) {
  const out = [];
  for (const g of SENSITIVITY_GRID) {
    for (const v of g.values) {
      const orig = MODEL_CONFIG[g.key].value;
      MODEL_CONFIG[g.key].value = v;
      const lg2 = g.key === 'sdScore' || g.key === 'rhoScore'
        ? { ...league, marginSd: MODEL_CONFIG.sdScore.value * Math.sqrt(2 * (1 - MODEL_CONFIG.rhoScore.value)) }
        : league;
      const line = originate(game, flow, lg2, availByName);
      out.push({ param: g.key, value: v, spreadHome: line.spreadHome, totalLine: line.totalLine, pHome: line.pHome });
      MODEL_CONFIG[g.key].value = orig;
    }
  }
  return out;
}

/* ---------- helpers ---------- */
const r2 = (x) => Math.round(x * 100) / 100;
const round4 = (x) => Math.round(x * 10000) / 10000;

module.exports = {
  MODEL_CONFIG, TEAM_TZ, STATUS_WEIGHT, SENSITIVITY_GRID,
  buildLeague, buildAvailability, availabilityForTeam,
  buildScheduleContext, daysBetween, restPoints,
  originate, simulateGame, sensitivity, hcaSensitivity, HCA_ALTERNATIVES,
  r2
};

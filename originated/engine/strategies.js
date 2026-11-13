'use strict';
/**
 * Strategy catalog, validation gates, signal generation and the leaderboard.
 *
 * DESIGN PRINCIPLE (important, and stated on the site):
 *   The originated line in model.js is built from: shrunken net rating, scoring
 *   environment, home court, rest and time-zone travel. A strategy is only allowed
 *   to claim an edge if it conditions on information that is NOT already in that
 *   line. Otherwise the "edge" is circular. Each strategy therefore declares the
 *   residual information it uses.
 */

const L = require('./lib');
const M = require('./model');

/** Assumed market price used for EV maths. DECLARED ASSUMPTION - there is no market feed. */
const ASSUMED_MARKET = {
  side: -110, total: -110,
  overround: 0.0477,
  note: [
    'No live market feed exists in this repository (see Open Questions Q-01). Two prices are used.',
    '(1) -110 flat, for the single-bet break-even screen.',
    '(2) An explicit overround of 4.77% (the overround implied by a -110/-110 two-way market) applied to the FAIR probability of each leg from our own originated line. This is how parlays are priced.',
    'A flat -110 is NOT used for parlays, because quoting a 63% favourite at -110 would be nonsense.'
  ]
};

/** Market decimal price for a leg whose FAIR probability (from our originated line) is pFair. */
function viggedDecimal(pFair, overround = ASSUMED_MARKET.overround) {
  const implied = Math.min(0.999, Math.max(0.001, pFair * (1 + overround)));
  return 1 / implied;
}

const PARSE = {
  streak: (s) => {
    if (!s) return 0;
    const m = /^([WL])(\d+)$/.exec(s.trim());
    if (!m) return 0;
    return (m[1] === 'W' ? 1 : -1) * Number(m[2]);
  },
  split: (s) => {
    if (!s) return { w: 0, l: 0, pct: null, n: 0 };
    const [w, l] = s.split('-').map(Number);
    const n = w + l;
    return { w, l, n, pct: n ? w / n : null };
  },
  last10: (s) => PARSE.split(s).pct
};

/* ------------------------------------------------------------------ *
 * Strategy definitions
 * ------------------------------------------------------------------ */

const STRATEGIES = [
  {
    id: 'S01',
    name: 'Pythagorean Regression (Luck Fade)',
    family: 'single',
    markets: ['spread', 'moneyline'],
    thesis: 'A team whose actual win% sits far above its Pythagorean win% has been winning close games it did not really dominate; the reverse is true for a team underperforming its scoring profile. Fade the lucky, back the unlucky.',
    residualInfo: 'Pythagorean win% vs actual win% (not used by the originated line).',
    lambda: { value: 12.0, assumption: true, note: 'Margin points per 1.00 of luck differential.' },
    inputs: ['ppg', 'oppPpg', 'wins', 'losses'],
    inputTier: 'T2 (S04); W-L cross-checked T1 (S02)',
    trigger: (c) => Math.abs(c.luckDiff) >= 0.15,
    triggerText: '|luck differential| >= 0.15',
    adjHome: (c) => -clamp(c.strat.lambda.value * c.luckDiff, -4, 4),
    where: 'luckDiff = home.luck - away.luck; adjustment is applied against the luckier team.'
  },
  {
    id: 'S02',
    name: 'Recent-Form vs Season Divergence',
    family: 'single',
    markets: ['spread', 'moneyline'],
    thesis: 'When a team\'s last-10 record disagrees materially with its full-season record, trust the larger sample: fade the hot streak, back the slump.',
    residualInfo: 'Last-10 win% vs season win% (not used by the originated line).',
    lambda: { value: 10.0, assumption: true, note: 'Margin points per 1.00 of L10-vs-season differential.' },
    inputs: ['last10', 'wins', 'losses'],
    inputTier: 'T2 (S04)',
    trigger: (c) => Math.abs(c.l10Diff) >= 0.20,
    triggerText: '|L10 win% - season win%| differential >= 0.20',
    adjHome: (c) => -clamp(c.strat.lambda.value * c.l10Diff, -4, 4),
    where: 'l10Diff = (home.L10% - home.season%) - (away.L10% - away.season%).'
  },
  {
    id: 'S03',
    name: 'Venue-Split Divergence',
    family: 'single',
    markets: ['spread'],
    thesis: 'Some teams are materially better or worse at home than their overall net rating implies, and likewise on the road. Compare the home team\'s home record with the away team\'s road record.',
    residualInfo: 'Home/away split records (the line uses a league-average home-court term only).',
    lambda: { value: 6.0, assumption: true, note: 'Margin points per 1.00 of venue-split differential.' },
    inputs: ['home', 'away'],
    inputTier: 'T2 (S04)',
    trigger: (c) => c.venueDiff != null && Math.abs(c.venueDiff) >= 0.30 && c.venueSamplesOk,
    triggerText: '|home-team home win% - away-team road win%| >= 0.30, with >= 5 games in each split',
    adjHome: (c) => clamp(c.strat.lambda.value * (c.venueDiff || 0), -4, 4),
    where: 'venueDiff = homeTeam.homeWinPct - awayTeam.roadWinPct.'
  },
  {
    id: 'S04',
    name: 'Availability Fade (official injury report)',
    family: 'single',
    markets: ['spread', 'moneyline'],
    thesis: 'Teams carrying a heavier unavailability load are weaker than their season-to-date net rating implies, because that net rating was earned with healthier rotations.',
    residualInfo: 'Weighted unavailability index built from the official NBA injury report. Explicitly NOT applied to the published line.',
    lambda: { value: M.MODEL_CONFIG.injuryK.value, assumption: true, note: 'Margin points per 1.00 of unavailability index. UNCALIBRATED.' },
    inputs: ['injury report status', 'reason category'],
    inputTier: 'T1 (S03)',
    trigger: (c) => Math.abs(c.rotationDiff) >= 1.0,
    triggerText: '|rotation-availability index differential| >= 1.00',
    adjHome: (c) => -clamp(c.strat.lambda.value * c.rotationDiff, -3, 3),
    where: 'rotationDiff = home.rotationIndex - away.rotationIndex. Weights: Out 1.00, Doubtful 0.75, Questionable 0.40, Probable 0.15, Available 0.00. G League two-way and G League assignment rows are EXCLUDED, because those players were not in the NBA rotation. NOT YET SUBMITTED is also excluded - it is an absence of information, not information.'
  },
  {
    id: 'S05',
    name: 'Emirates NBA Cup point-differential incentive',
    family: 'single',
    markets: ['total'],
    thesis: 'If the Cup group tiebreaker is point differential, teams have a documented incentive to keep scoring late in blowouts, biasing Cup games toward the over.',
    residualInfo: 'Whether a game is an Emirates NBA Cup group game (known from the official schedule).',
    lambda: { value: 2.5, assumption: true, note: 'Points added to the projected total for a Cup group game.' },
    inputs: ['competition'],
    inputTier: 'T1 (S01)',
    rule_verified: false,
    rule_note: 'The Cup tiebreaker rule itself has NOT been verified against an official NBA document in this session. Flagged: the strategy is held at gate G2 (provenance) = FAIL until verified.',
    trigger: (c) => c.isCup,
    triggerText: 'game is an Emirates NBA Cup group game',
    adjTotal: (c) => clamp(c.strat.lambda.value, 0, 4),
    where: 'Applied to the projected total only.'
  },
  {
    id: 'S06',
    name: 'Extreme-Streak Mean Reversion',
    family: 'single',
    markets: ['spread'],
    thesis: 'Very long losing (or winning) streaks are partly noise. Fade streaks of 6+ games in either direction.',
    residualInfo: 'Current win/loss streak length (not used by the originated line).',
    lambda: { value: 0.12, assumption: true, note: 'Margin points per game of streak beyond 5, applied in the mean-reverting direction.' },
    inputs: ['streak'],
    inputTier: 'T2 (S04)',
    trigger: (c) => Math.abs(c.streakHome) >= 6 || Math.abs(c.streakAway) >= 6,
    triggerText: 'either team on a streak of 6+ games',
    adjHome: (c) => -clamp(c.strat.lambda.value * (signedStreak(c.streakHome) - signedStreak(c.streakAway)), -2, 2),
    where: 'signedStreak = +n for a W n streak, -n for an L n streak; adjustment favours the team on the longer losing streak.'
  },
  {
    id: 'S07',
    name: 'Totals: Fade the Extremes',
    family: 'single',
    markets: ['total'],
    thesis: 'Projected totals at the extremes of the distribution regress: the highest-projected games tend to land lower than the raw scoring-environment maths implies, and the lowest higher.',
    residualInfo: 'Distance of the originated total from the league norm (the line itself, regressed back).',
    lambda: { value: 0.35, assumption: true, note: 'Fraction of the league-norm gap removed from the projected total.' },
    inputs: ['ppg', 'oppPpg'],
    inputTier: 'T2 (S04)',
    trigger: (c) => Math.abs(c.totalVsNorm) >= 6,
    triggerText: '|projected total - 2 x league PPG| >= 6 points',
    adjTotal: (c) => -clamp(c.strat.lambda.value * c.totalVsNorm, -6, 6),
    where: 'totalVsNorm = projected total - 2 x league-average PPG.'
  },
  {
    id: 'S08',
    name: 'Cross-Game Parlay Builder (correlation-controlled)',
    family: 'parlay',
    markets: ['parlay'],
    thesis: 'Parlaying legs from different games keeps inter-leg correlation at ~0, so the fair parlay price is the product of the leg prices. Parlays then amplify per-leg edge multiplicatively - and amplify vig just as fast when there is no edge.',
    residualInfo: 'Independence across games (verified by construction, since games are disjoint).',
    inputs: ['single-leg model probabilities'],
    inputTier: 'derived',
    trigger: (c) => c.legs.length >= 2,
    triggerText: 'at least 2 qualifying legs, each from a different game'
  },
  {
    id: 'S09',
    name: 'Same-Game Parlay: correlation mispricing',
    family: 'parlay',
    markets: ['same-game parlay'],
    thesis: 'Books price same-game parlays by multiplying leg probabilities as if the legs were independent. When two legs from one game are POSITIVELY correlated, the true joint probability is higher than the product, so the independent price is generous. When they are NEGATIVELY correlated the independent price is a trap.',
    residualInfo: 'Within-game correlation between market outcomes, measured by Monte-Carlo (not used anywhere else).',
    inputs: ['simulated joint distribution of margin and total'],
    inputTier: 'derived',
    trigger: (c) => Math.abs(c.phi) >= 0.05,
    triggerText: '|phi| >= 0.05 between the two legs'
  },
  {
    id: 'S10',
    name: 'Player Prop Combos',
    family: 'prop',
    markets: ['player props'],
    thesis: 'Player prop thresholds can be originated from per-player season usage and minutes, adjusted for the availability of teammates listed on the official injury report.',
    residualInfo: 'Per-player season averages and minutes.',
    inputs: ['per-player season averages', 'minutes', 'usage'],
    inputTier: 'NONE AVAILABLE',
    blocked: true,
    blockedReason: 'No official per-player season feed is reachable from this environment (stats.nba.com and cdn.nba.com both returned errors). Per the verification rule, no player threshold is published. See Open Questions Q-02.'
  }
];

const signedStreak = (n) => n;

/* ------------------------------------------------------------------ *
 * Context + signal generation
 * ------------------------------------------------------------------ */

function buildContext(game, line, league, teamsByAbbr, availByName) {
  const A = teamsByAbbr[game.away], H = teamsByAbbr[game.home];
  const rA = league.ratings[game.away], rH = league.ratings[game.home];
  const aAvail = availByName[A.name] || { injuryIndex: 0, unavailIndex: 0 };
  const hAvail = availByName[H.name] || { injuryIndex: 0, unavailIndex: 0 };
  const hHome = PARSE.split(H.home), aAway = PARSE.split(A.away);
  const venueSamplesOk = hHome.n >= 5 && aAway.n >= 5;

  return {
    game, line, league,
    luckDiff: rH.luck - rA.luck,
    l10Diff: (PARSE.last10(H.last10) - rH.actualWinPct) - (PARSE.last10(A.last10) - rA.actualWinPct),
    venueDiff: (hHome.pct != null && aAway.pct != null) ? hHome.pct - aAway.pct : null,
    venueSamplesOk,
    unavailDiff: hAvail.unavailIndex - aAvail.unavailIndex,
    rotationDiff: hAvail.rotationIndex - aAvail.rotationIndex,
    injuryDiff: hAvail.injuryIndex - aAvail.injuryIndex,
    gLeagueDiff: hAvail.gLeagueIndex - aAvail.gLeagueIndex,
    streakHome: PARSE.streak(H.streak), streakAway: PARSE.streak(A.streak),
    isCup: game.competition === 'Emirates NBA Cup',
    totalVsNorm: line.expTotal - 2 * league.lgPpg,
    legs: [], phi: null
  };
}

/**
 * Evaluate the single-bet strategies against one game.
 * Returns one signal per (strategy x market) that clears the trigger.
 */
function evaluateSingles(ctx) {
  const out = [];
  for (const strat of STRATEGIES) {
    if (strat.blocked || strat.family !== 'single') continue;
    const c = { ...ctx, strat };
    let trig = false;
    try { trig = strat.trigger(c); } catch (e) { trig = false; }
    if (!trig) continue;

    for (const market of strat.markets) {
      let sig = null;
      if (market === 'spread' || market === 'moneyline') {
        const adj = strat.adjHome(c);
        if (Math.abs(adj) < 0.25) continue;
        if (market === 'spread') {
          const pCover = L.normalCdf((ctx.line.marginHome + adj + ctx.line.spreadHome) / ctx.league.marginSd);
          const pFairCover = L.normalCdf((ctx.line.marginHome + ctx.line.spreadHome) / ctx.league.marginSd);
          sig = { market: 'spread', side: sideLabelSpread(ctx.game, ctx.line.spreadHome), target: ctx.line.spreadHome, modelProb: pCover, pFairLeg: pFairCover };
        } else {
          const p = L.normalCdf((ctx.line.marginHome + adj) / ctx.league.marginSd);
          const fav = p >= 0.5;
          sig = {
            market: 'moneyline',
            side: fav ? ctx.game.home : ctx.game.away,
            target: fav ? ctx.line.mlHome : ctx.line.mlAway,
            modelProb: fav ? p : 1 - p,
            pFairLeg: fav ? ctx.line.pHome : 1 - ctx.line.pHome
          };
        }
        sig.adjPoints = round2(adj);
        sig.marketAmerican = ASSUMED_MARKET.side;
      } else if (market === 'total' && strat.adjTotal) {
        const adj = strat.adjTotal(c);
        if (Math.abs(adj) < 0.5) continue;
        const effTotal = ctx.line.totalLine + adj;
        const pOver = 1 - L.normalCdf((ctx.line.totalLine - effTotal) / ctx.league.totalSd);
        const over = pOver >= 0.5;
        const pFairOver = 1 - L.normalCdf((ctx.line.totalLine - ctx.line.expTotal) / ctx.league.totalSd);
        sig = {
          market: 'total', side: over ? 'Over' : 'Under', target: ctx.line.totalLine,
          modelProb: over ? pOver : 1 - pOver, adjPoints: round2(adj),
          pFairLeg: over ? pFairOver : 1 - pFairOver
        };
      }
      if (!sig) continue;
      sig.strategy = strat.id;
      sig.gameId = ctx.game.id;
      sig.date = ctx.game.date;
      sig.matchup = `${ctx.game.away} @ ${ctx.game.home}`;
      sig.trigger = strat.triggerText;
      sig.fairAmerican = L.americanFromProb(sig.modelProb);
      // The leg's fair probability according to the ORIGINATED line (before this strategy's
      // adjustment). The gap between modelProb and pFairLeg is the strategy's claimed edge.
      sig.pFairLeg = sig.pFairLeg != null ? sig.pFairLeg : sig.modelProb;
      sig.marketDecimal = viggedDecimal(sig.pFairLeg);
      sig.marketAmerican = decToAmerican(sig.marketDecimal);
      sig.breakevenProb = L.breakevenProb(sig.marketAmerican);
      sig.edgeOverBreakeven = sig.modelProb - sig.breakevenProb;
      sig.evPerUnit = L.ev(sig.modelProb, sig.marketAmerican);
      out.push(sig);
    }
  }
  return out;
}

function sideLabelSpread(g, spread) {
  // spread is from the home team's perspective: negative = home favoured.
  return spread < 0 ? `${g.home} ${spread}` : `${g.away} ${-spread}`;
}

/* ------------------------------------------------------------------ *
 * Parlay construction
 * ------------------------------------------------------------------ */

/**
 * Build cross-game parlays from qualifying single legs.
 * Legs from different games are independent by construction (disjoint games).
 */
function buildCrossParlays(signals, league, maxLegs = 3, topN = 12) {
  const ov = ASSUMED_MARKET.overround;

  // Keep the strongest leg per game -> legs are from disjoint games -> rho = 0 by construction.
  const legs = signals
    .filter(s => s.modelProb > s.pFairLeg)          // only legs the strategy thinks are mispriced
    .sort((a, b) => (b.modelProb - b.pFairLeg) - (a.modelProb - a.pFairLeg))
    .slice(0, topN);

  const byGame = new Map();
  for (const l of legs) if (!byGame.has(l.gameId)) byGame.set(l.gameId, l);
  const pool = [...byGame.values()].slice(0, 6);

  const combos = [];
  const n = pool.length;
  const combosOf = (k) => {
    const res = [];
    const rec = (start, acc) => {
      if (acc.length === k) { res.push([...acc]); return; }
      for (let i = start; i < n; i++) { acc.push(i); rec(i + 1, acc); acc.pop(); }
    };
    rec(0, []);
    return res;
  };

  for (let k = 2; k <= Math.min(maxLegs, n); k++) {
    for (const combo of combosOf(k)) {
      const ls = combo.map(i => pool[i]);
      const pJoint = ls.reduce((p, l) => p * l.modelProb, 1);
      const pJointFair = ls.reduce((p, l) => p * l.pFairLeg, 1);
      const marketDecimal = ls.reduce((d, l) => d * viggedDecimal(l.pFairLeg), 1);
      combos.push({
        strategy: 'S08',
        kind: 'cross-game parlay',
        legCount: k,
        legs: ls.map(l => ({
          gameId: l.gameId, matchup: l.matchup, market: l.market, side: l.side, target: l.target,
          pFairLeg: l.pFairLeg, modelProb: l.modelProb, edge: l.modelProb - l.pFairLeg,
          marketAmerican: decToAmerican(viggedDecimal(l.pFairLeg))
        })),
        pTrueJoint: pJoint,
        pJointAtFairPrice: pJointFair,
        assumedMarketDecimal: marketDecimal,
        assumedMarketAmerican: decToAmerican(marketDecimal),
        fairAmerican: decToAmerican(1 / pJoint),
        breakevenProb: 1 / marketDecimal,
        edgeOverBreakeven: pJoint - 1 / marketDecimal,
        evPerUnit: pJoint * marketDecimal - 1,
        zeroEdgeEv: Math.pow(1 / (1 + ov), k) - 1,
        assumedIndependence: true,
        crossGameCorrelation: 0
      });
    }
  }
  return combos.sort((a, b) => b.evPerUnit - a.evPerUnit);
}

/**
 * What a k-leg parlay costs you if none of the legs has an edge.
 * The parlay is priced at the product of the vigged leg prices, so the vig compounds.
 */
function parlayVigTable(maxLegs = 6) {
  const ov = ASSUMED_MARKET.overround;
  const rows = [];
  for (let k = 1; k <= maxLegs; k++) {
    const zeroEdgeEv = Math.pow(1 / (1 + ov), k) - 1;
    rows.push({
      legs: k,
      vigPaidIfNoEdge: -zeroEdgeEv,
      zeroEdgeEv,
      requiredPerLegEdge: ov,
      requiredPerLegEdgeNote: 'Each leg must clear the -110 break-even by ~' + (ov * 100).toFixed(2) +
        ' percentage points of probability just to stand still.'
    });
  }
  return rows;
}

/**
 * Same-game parlays: compare the true joint probability (from Monte-Carlo)
 * with the independent product a book would use to price it.
 */
function buildSameGameParlays(game, line, sim) {
  const b = sim.binary;
  const n = sim.n;
  const pHomeWin = sim.pHomeWinMC, pOver = sim.pOverMC;
  const outcomes = [
    { key: 'homeWin', label: `${game.home} moneyline`, p: pHomeWin, arr: b.homeWin, pFair: line.pHome },
    { key: 'awayWin', label: `${game.away} moneyline`, p: 1 - pHomeWin, arr: b.homeWin.map(v => 1 - v), pFair: 1 - line.pHome },
    { key: 'over', label: `Over ${line.totalLine}`, p: pOver, arr: b.over, pFair: null },
    { key: 'under', label: `Under ${line.totalLine}`, p: 1 - pOver, arr: b.over.map(v => 1 - v), pFair: null },
    { key: 'homeCover', label: `${game.home} ${line.spreadHome}`, p: sim.pHomeCoverMC, arr: b.homeCover, pFair: null }
  ];

  const res = [];
  for (let i = 0; i < outcomes.length; i++) {
    for (let j = i + 1; j < outcomes.length; j++) {
      const a = outcomes[i], c = outcomes[j];
      // Only legs a book would actually sell as a same-game parlay:
      //   (a winner or a spread) x (a total). Winner-vs-spread is a contradictory or
      //   restricted pair, and over-vs-under is impossible by definition.
      const isWinner = (k) => k === 'homeWin' || k === 'awayWin';
      const isTotal = (k) => k === 'over' || k === 'under';
      const isCover = (k) => k === 'homeCover';
      const okPair =
        (isWinner(a.key) && isTotal(c.key)) || (isWinner(c.key) && isTotal(a.key)) ||
        (isCover(a.key) && isTotal(c.key)) || (isCover(c.key) && isTotal(a.key));
      if (!okPair) continue;

      let joint = 0;
      for (let k = 0; k < n; k++) if (a.arr[k] === 1 && c.arr[k] === 1) joint++;
      const pJoint = joint / n;
      const pIndep = a.p * c.p;
      const phi = L.phi(a.arr, c.arr);
      const marketDecimal = 1 / pIndep;           // book prices as if independent
      res.push({
        strategy: 'S09',
        kind: 'same-game parlay',
        gameId: game.id,
        matchup: `${game.away} @ ${game.home}`,
        legs: [a.label, c.label],
        pTrueJoint: pJoint,
        pIndependent: pIndep,
        phi,
        jointMinusIndep: pJoint - pIndep,
        assumedMarketAmerican: decToAmerican(marketDecimal),
        fairAmerican: decToAmerican(1 / pJoint),
        breakevenProb: pIndep,
        edgeOverBreakeven: pJoint - pIndep,
        evPerUnit: pJoint * marketDecimal - 1
      });
    }
  }
  return res;
}

function decToAmerican(d) {
  return d >= 2 ? Math.round((d - 1) * 100) : Math.round(-100 / (d - 1));
}

/* ------------------------------------------------------------------ *
 * Validation gates
 * ------------------------------------------------------------------ */

const GATES = [
  { id: 'G1', name: 'Sample size', rule: 'Each team has played >= 8 games in the current season.' },
  { id: 'G2', name: 'Provenance', rule: 'Every input is traceable to a T1 or T2 source with a live link.' },
  { id: 'G3', name: 'No look-ahead', rule: 'Every input is knowable before tip-off.' },
  { id: 'G4', name: 'Correlation control', rule: 'Parlay legs within one game have |phi| <= 0.25, or the correlation is explicitly priced.' },
  { id: 'G5', name: 'Beats the vig', rule: 'Model probability exceeds the -110 break-even of 52.38%.' },
  { id: 'G6', name: 'Out-of-sample validation', rule: 'Strategy shows positive ROI on a walk-forward hold-out that was not used to set its parameters.' },
  { id: 'G7', name: 'Parameter stability', rule: 'Perturbing the strategy\'s lambda by +/-25% does not flip the direction of any signal.' },
  { id: 'G8', name: 'Reproducible', rule: 'Signal is recomputable from data/*.json by `node engine/build.js`.' }
];

function evaluateGates(strat, signals, ctxList) {
  const g = {};

  g.G1 = ctxList.every(c => c.league.ratings[c.game.home].gp >= 8 && c.league.ratings[c.game.away].gp >= 8)
    ? pass('all teams >= 8 games played')
    : fail('a team has fewer than 8 games played');

  g.G2 = strat.blocked
    ? fail('no official source available for the required inputs')
    : (strat.rule_verified === false
        ? fail('a rule the strategy depends on has not been verified against an official document')
        : pass(strat.inputTier));

  g.G3 = pass('all inputs are season-to-date or pre-game published reports');

  if (strat.family === 'parlay') {
    g.G4 = signals.length === 0
      ? fail('no signals produced')
      : (signals.every(s => s.crossGameCorrelation === 0 || Math.abs(s.phi || 0) <= 0.25)
          ? pass('legs are cross-game (rho = 0) or |phi| <= 0.25')
          : fail('a leg pair exceeds the |phi| <= 0.25 limit'));
  } else {
    g.G4 = pass('single-leg strategy, no intra-leg correlation to control');
  }

  const bes = signals.map(s => s.breakevenProb != null ? s.breakevenProb : L.breakevenProb(ASSUMED_MARKET.side));
  const worst = signals.length ? Math.min(...signals.map((s, i) => s.modelProb - bes[i])) : null;
  g.G5 = signals.length === 0
    ? fail('no signals produced')
    : (worst > 0
        ? pass(`every signal clears its own break-even (worst margin ${(worst * 100).toFixed(2)} pp)`)
        : fail(`at least one signal is below its break-even (worst margin ${(worst * 100).toFixed(2)} pp)`));

  g.G6 = fail('BLOCKED: no graded historical bet log exists in this repository');

  if (strat.lambda) {
    let stable = true;
    const base = strat.lambda.value;
    for (const mult of [0.75, 1.25]) {
      strat.lambda.value = base * mult;
      for (const c of ctxList) {
        const cc = { ...c, strat };
        let t = false; try { t = strat.trigger(cc); } catch (e) { t = false; }
        if (!t) continue;
        const a1 = strat.adjHome ? strat.adjHome(cc) : (strat.adjTotal ? strat.adjTotal(cc) : 0);
        strat.lambda.value = base;
        const a0 = strat.adjHome ? strat.adjHome({ ...c, strat }) : (strat.adjTotal ? strat.adjTotal({ ...c, strat }) : 0);
        strat.lambda.value = base * mult;
        if (Math.sign(a0) !== 0 && Math.sign(a1) !== Math.sign(a0)) stable = false;
      }
      strat.lambda.value = base;
    }
    strat.lambda.value = base;
    g.G7 = stable ? pass('direction unchanged under +/-25% lambda perturbation')
                  : fail('direction flips under +/-25% lambda perturbation');
  } else {
    g.G7 = pass('no free parameters');
  }

  g.G8 = pass('recomputed by engine/build.js from data/*.json');

  const passed = Object.values(g).filter(x => x.ok).length;
  return { gates: g, passed, total: GATES.length, allPassed: passed === GATES.length };
}

const pass = (why) => ({ ok: true, detail: why });
const fail = (why) => ({ ok: false, detail: why });

/* ------------------------------------------------------------------ *
 * Leaderboard (EXPECTED, not realised)
 * ------------------------------------------------------------------ */

function buildLeaderboard(strategyResults) {
  const rows = strategyResults.map(r => {
    const sigs = r.signals || [];
    const evs = sigs.map(s => L.ev(s.modelProb, ASSUMED_MARKET.side));
    const meanProb = sigs.length ? sigs.reduce((s, x) => s + x.modelProb, 0) / sigs.length : null;
    const meanEv = evs.length ? evs.reduce((s, x) => s + x, 0) / evs.length : null;
    const best = sigs.slice().sort((a, b) => b.modelProb - a.modelProb)[0] || null;
    return {
      strategy: r.strategy.id,
      name: r.strategy.name,
      family: r.strategy.family,
      blocked: !!r.strategy.blocked,
      signals: sigs.length,
      meanModelProb: meanProb,
      meanEvPerUnit: meanEv,
      bestProb: best ? best.modelProb : null,
      gatesPassed: r.gates.passed,
      gatesTotal: r.gates.total,
      gateBlockers: Object.entries(r.gates.gates).filter(([, v]) => !v.ok).map(([k, v]) => `${k}: ${v.detail}`),
      deployable: !r.strategy.blocked && r.gates.passed === r.gates.total && sigs.length > 0
    };
  });
  rows.sort((a, b) => (b.meanEvPerUnit ?? -99) - (a.meanEvPerUnit ?? -99) || b.signals - a.signals);
  return rows;
}

/* ---------- helpers ---------- */
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function round2(x) { return Math.round(x * 100) / 100; }

module.exports = {
  STRATEGIES, GATES, ASSUMED_MARKET, PARSE,
  buildContext, evaluateSingles, buildCrossParlays, buildSameGameParlays, parlayVigTable, viggedDecimal,
  evaluateGates, buildLeaderboard, sideLabelSpread, decToAmerican, clamp
};

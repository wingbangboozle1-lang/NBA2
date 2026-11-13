'use strict';
/**
 * Runs the whole pipeline and writes data/derived.json.
 * Nothing here invents a value: every input comes from data/*.json and every
 * formula is documented in research/.
 */

const fs = require('fs');
const path = require('path');
const L = require('./lib');
const M = require('./model');
const S = require('./strategies');

const ROOT = path.join(__dirname, '..');
const DATA = path.join(ROOT, 'data');

const read = (f) => JSON.parse(fs.readFileSync(path.join(DATA, f), 'utf8'));

function run() {
  const teams = read('teams.json');
  const slate = read('slate.json');
  const injuries = read('injuries.json');
  const sources = read('sources.json');

  const league = M.buildLeague(teams.teams);
  const avail = M.buildAvailability(injuries);
  const flows = M.buildScheduleContext(slate);
  const flowById = Object.fromEntries(flows.map(f => [f.id, f]));

  const teamsByAbbr = Object.fromEntries(teams.teams.map(t => [t.abbr, t]));
  const srcById = Object.fromEntries(sources.sources.map(s => [s.id, s]));

  const games = [...slate.games].sort((a, b) => a.date.localeCompare(b.date) || a.etSort - b.etSort);

  const lines = [], sims = [], ctxs = [], allSignals = [], sgpAll = [];
  for (const g of games) {
    const line = M.originate(g, flowById[g.id], league, avail);
    const sim = M.simulateGame(line, league, M.MODEL_CONFIG.mcIterations.value);
    const ctx = S.buildContext(g, line, league, teamsByAbbr, avail);

    line.matchup = `${g.away} @ ${g.home}`;
    line.date = g.date;
    line.timeEt = g.timeEt;
    line.venue = g.venue;
    line.city = g.city;
    line.url = g.url;
    line.competition = g.competition;
    line.cupGroup = g.cupGroup;

    const signals = S.evaluateSingles(ctx);
    const sgp = S.buildSameGameParlays(g, line, sim);

    ctxs.push({ game: g, ctx, line, sim, signals });
    lines.push(line);
    sims.push(sim);
    allSignals.push(...signals);
    sgpAll.push(...sgp);
  }

  // Per-strategy gate evaluation
  const strategyResults = S.STRATEGIES.map(strat => {
    if (strat.blocked) {
      return {
        strategy: strat,
        signals: [],
        gates: S.evaluateGates(strat, [], [])
      };
    }
    if (strat.id === 'S08') {
      const legs = allSignals.filter(s => s.modelProb > L.breakevenProb(S.ASSUMED_MARKET.side));
      const parlays = S.buildCrossParlays(legs, league);
      const top = parlays.slice(0, 10);
      return {
        strategy: strat,
        signals: top.map(p => ({
          market: 'parlay', side: p.legs.map(l => l.side).join(' + '),
          target: p.assumedMarketAmerican, modelProb: p.pTrueJoint,
          evPerUnit: p.evPerUnit, crossGameCorrelation: 0, phi: 0
        })),
        parlays: top,
        gates: S.evaluateGates(strat, top.map(p => ({ modelProb: p.pTrueJoint, crossGameCorrelation: 0, phi: 0 })), [])
      };
    }
    if (strat.id === 'S09') {
      const top = sgpAll.filter(p => Math.abs(p.phi) >= 0.05)
        .sort((a, b) => b.evPerUnit - a.evPerUnit).slice(0, 10);
      return {
        strategy: strat,
        signals: top.map(p => ({
          market: 'same-game parlay', side: p.legs.join(' + '),
          target: p.assumedMarketAmerican, modelProb: p.pTrueJoint,
          evPerUnit: p.evPerUnit, crossGameCorrelation: null, phi: p.phi
        })),
        parlays: top,
        gates: S.evaluateGates(strat, top.map(p => ({ modelProb: p.pTrueJoint, crossGameCorrelation: null, phi: p.phi })), [])
      };
    }
    const triggeredCtx = ctxs
      .filter(c => { const cc = { ...c.ctx, strat }; try { return strat.trigger(cc); } catch (e) { return false; } })
      .map(c => ({ ...c.ctx, strat }));
    const sigs = allSignals.filter(s => s.strategy === strat.id);
    return { strategy: strat, signals: sigs, gates: S.evaluateGates(strat, sigs, triggeredCtx) };
  });

  const leaderboard = S.buildLeaderboard(strategyResults);

  // Sensitivity for each game (declared assumptions -> how much does the line move?)
  const sensitivity = games.slice(0, 9).map(g => ({
    gameId: g.id, matchup: `${g.away} @ ${g.home}`,
    rows: M.sensitivity(g, flowById[g.id], league, avail)
  }));

  const derived = {
    meta: {
      generated: new Date().toISOString(),
      season: slate.season,
      asOf: teams.asOf,
      gamesInWindow: games.length,
      window: [games[0].date, games[games.length - 1].date],
      mcIterations: M.MODEL_CONFIG.mcIterations.value,
      mcSeed: M.MODEL_CONFIG.mcSeed.value,
      note: 'All figures labelled MODEL OUTPUT are computed by engine/model.js. All figures labelled VERIFIED are transcribed from an official or trusted source listed in data/sources.json.'
    },
    league: {
      lgPpg: r2(league.lgPpg), lgOppPpg: r2(league.lgOppPpg),
      homeWins: league.homeWins, homeLosses: league.homeLosses,
      homeWinRate: r4(league.homeWinRate),
      hcaPoints: r2(league.hcaPoints),
      marginSd: r2(league.marginSd), totalSd: r2(league.totalSd),
      teamCount: league.teamCount
    },
    ratings: Object.values(league.ratings).sort((a, b) => b.shrunkMov - a.shrunkMov),
    availability: avail,
    flows,
    lines,
    sims: sims.map(s => ({
      n: s.n, pHomeWinMC: r4(s.pHomeWinMC), pHomeCoverMC: r4(s.pHomeCoverMC), pOverMC: r4(s.pOverMC),
      corr: Object.fromEntries(Object.entries(s.corr).map(([k, v]) => [k, v == null ? null : r4(v)])),
      phi: Object.fromEntries(Object.entries(s.phi).map(([k, v]) => [k, v == null ? null : r4(v)]))
    })),
    signals: allSignals.map(s => ({ ...s, modelProb: r4(s.modelProb) })),
    sameGameParlays: sgpAll.map(p => ({
      ...p, pTrueJoint: r4(p.pTrueJoint), pIndependent: r4(p.pIndependent),
      phi: p.phi == null ? null : r4(p.phi), jointMinusIndep: r4(p.jointMinusIndep), evPerUnit: r4(p.evPerUnit)
    })),
    crossParlays: (strategyResults.find(r => r.strategy.id === 'S08')?.parlays || []).map(p => ({
      ...p, pTrueJoint: r4(p.pTrueJoint), evPerUnit: r4(p.evPerUnit),
      legs: p.legs.map(l => ({ ...l, modelProb: r4(l.modelProb) }))
    })),
    strategies: strategyResults.map(r => ({
      id: r.strategy.id, name: r.strategy.name, family: r.strategy.family,
      thesis: r.strategy.thesis, residualInfo: r.strategy.residualInfo,
      markets: r.strategy.markets, inputs: r.strategy.inputs, inputTier: r.strategy.inputTier,
      trigger: r.strategy.triggerText, where: r.strategy.where || null,
      blocked: !!r.strategy.blocked, blockedReason: r.strategy.blockedReason || null,
      rule_verified: r.strategy.rule_verified !== false,
      rule_note: r.strategy.rule_note || null,
      lambda: r.strategy.lambda ? { value: r.strategy.lambda.value, assumption: true, note: r.strategy.lambda.note } : null,
      gates: r.gates.gates, gatesPassed: r.gates.passed, gatesTotal: r.gates.total,
      signalCount: r.signals.length
    })),
    leaderboard,
    sensitivity,
    crossVerification: {
      wl: teams.crossVerification,
      ppgIdentity: {
        check: 'mean(PPG) across all 30 teams must equal mean(OPP PPG), because every point scored is a point allowed',
        meanPpg: r2(league.lgPpg), meanOppPpg: r2(league.lgOppPpg),
        status: Math.abs(league.lgPpg - league.lgOppPpg) < 0.05 ? 'PASS' : 'FAIL'
      },
      fairLineSanity: {
        check: 'Monte-Carlo P(home covers its own originated spread) must be ~0.500, otherwise the line and the simulator disagree',
        worstDeviation: r4(Math.max(...sims.map(s => Math.abs(s.pHomeCoverMC - 0.5)))),
        status: Math.max(...sims.map(s => Math.abs(s.pHomeCoverMC - 0.5))) < 0.01 ? 'PASS' : 'REVIEW'
      }
    }
  };

  fs.writeFileSync(path.join(DATA, 'derived.json'), JSON.stringify(derived, null, 2));
  return { derived, teams, slate, injuries, sources, srcById, teamsByAbbr, league, games, lines, sims };
}

const r2 = (x) => Math.round(x * 100) / 100;
const r4 = (x) => Math.round(x * 10000) / 10000;

module.exports = { run };

if (require.main === module) {
  const out = run();
  const d = out.derived;
  console.log('league avg PPG      :', d.league.lgPpg, '| OPP', d.league.lgOppPpg);
  console.log('home win rate       :', d.league.homeWinRate, '-> HCA', d.league.hcaPoints, 'pts');
  console.log('margin sd / total sd:', d.league.marginSd, '/', d.league.totalSd);
  console.log('games               :', d.meta.gamesInWindow, d.meta.window.join(' .. '));
  console.log('signals             :', d.signals.length);
  console.log('ppg identity        :', d.crossVerification.ppgIdentity.status);
  console.log('fair-line sanity    :', d.crossVerification.fairLineSanity.status, d.crossVerification.fairLineSanity.worstDeviation);
  console.log('\nsample lines:');
  for (const l of d.lines.slice(0, 5)) {
    console.log(`  ${l.date} ${l.matchup.padEnd(10)} spread ${String(l.spreadHome).padStart(6)}  total ${String(l.totalLine).padStart(6)}  pHome ${(l.pHome * 100).toFixed(1)}%  ML ${L.fmtAmerican(l.mlHome)}/${L.fmtAmerican(l.mlAway)}`);
  }
  console.log('\nleaderboard:');
  for (const r of d.leaderboard) {
    console.log(`  ${r.strategy} ${r.name.slice(0, 42).padEnd(44)} sig=${String(r.signals).padStart(3)} gates=${r.gatesPassed}/${r.gatesTotal} meanP=${r.meanModelProb ? r.meanModelProb.toFixed(3) : '  -  '} deploy=${r.deployable}`);
  }
}

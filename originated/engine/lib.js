'use strict';
// Pure math / odds helpers. No data, no I/O.

/* ---------- normal distribution ---------- */

function erf(x) {
  // Abramowitz & Stegun 7.1.26
  const s = x < 0 ? -1 : 1;
  x = Math.abs(x);
  const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741;
  const a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
  const t = 1 / (1 + p * x);
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return s * y;
}

function normalCdf(z) { return 0.5 * (1 + erf(z / Math.SQRT2)); }

function normalPpf(p) {
  // Acklam's inverse normal CDF, |rel error| < 1.15e-9
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
  const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01];
  const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
  const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00];
  const pl = 0.02425;
  let q, r, x;
  if (p < pl) {
    q = Math.sqrt(-2 * Math.log(p));
    x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else if (p <= 1 - pl) {
    q = p - 0.5; r = q * q;
    x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  } else {
    q = Math.sqrt(-2 * Math.log(1 - p));
    x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
         ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  return x;
}

/* ---------- odds ---------- */

/** Fair (zero-vig) American odds from a probability. >0 for dogs, <0 for favs. */
function americanFromProb(p) {
  if (p <= 0 || p >= 1) return null;
  return p >= 0.5 ? Math.round(-100 * p / (1 - p)) : Math.round(100 * (1 - p) / p);
}

function probFromAmerican(o) {
  if (o == null) return null;
  return o > 0 ? 100 / (o + 100) : -o / (-o + 100);
}

/** Decimal odds from American. */
function decimalFromAmerican(o) { return o > 0 ? 1 + o / 100 : 1 + 100 / -o; }

/** Break-even win probability at a given American price. */
function breakevenProb(o) { return 1 / decimalFromAmerican(o); }

/** Expected value per 1 unit staked at price `o` with true probability p. */
function ev(p, o) { return p * decimalFromAmerican(o) - 1; }

/**
 * De-vig a two-way market: strip the book's overround by proportional normalisation.
 * Returns {pA, pB} summing to 1.
 */
function devigTwoWay(oddsA, oddsB) {
  const a = probFromAmerican(oddsA), b = probFromAmerican(oddsB);
  const s = a + b;
  return { pA: a / s, pB: b / s, overround: s - 1 };
}

/* ---------- win-expectation estimators ---------- */

/**
 * Pythagorean win expectation.
 * exponent 13.91 is the Daryl Morey / Basketball-Reference constant for NBA points.
 * NOTE: this is a published modelling constant, NOT an official NBA figure.
 */
const PYTHAG_EXPONENT = 13.91;
function pythagoreanWinPct(pointsFor, pointsAgainst, exp = PYTHAG_EXPONENT) {
  const pf = Math.pow(pointsFor, exp), pa = Math.pow(pointsAgainst, exp);
  return pf / (pf + pa);
}

/**
 * Bill James log5: probability A beats B given each team's (context-neutral) win rate.
 */
function log5(pA, pB) {
  const d = pA + pB - 2 * pA * pB;
  return d === 0 ? 0.5 : (pA - pA * pB) / d;
}

/* ---------- correlation / simulation ---------- */

/** Deterministic PRNG (mulberry32) so every number on the site is reproducible. */
function makeRng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Box-Muller standard normal pair from a uniform generator. */
function makeNormalPair(rng) {
  let cached = null;
  return function () {
    if (cached !== null) { const v = cached; cached = null; return v; }
    let u = 0, v = 0;
    while (u === 0) u = rng();
    while (v === 0) v = rng();
    const r = Math.sqrt(-2 * Math.log(u)), th = 2 * Math.PI * v;
    cached = r * Math.sin(th);
    return r * Math.cos(th);
  };
}

/** Pearson correlation of two equal-length arrays. */
function pearson(xs, ys) {
  const n = xs.length;
  if (n < 2) return null;
  let sx = 0, sy = 0;
  for (let i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; }
  const mx = sx / n, my = sy / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
  }
  const den = Math.sqrt(sxx * syy);
  return den === 0 ? null : sxy / den;
}

/** Phi coefficient (Pearson r on 0/1 variables) = correlation of two binary outcomes. */
function phi(xs, ys) { return pearson(xs, ys); }

/* ---------- formatting ---------- */

function fmtSigned(n, dp = 1) {
  if (n == null || Number.isNaN(n)) return '—';
  const v = Number(n);
  return (v > 0 ? '+' : '') + v.toFixed(dp);
}

function fmtPct(p, dp = 1) {
  if (p == null || Number.isNaN(p)) return '—';
  return (p * 100).toFixed(dp) + '%';
}

function fmtAmerican(o) {
  if (o == null) return '—';
  return o > 0 ? '+' + o : String(o);
}

/** NBA lines are quoted in half-points; snap to the nearest 0.5. */
function snapHalf(x) { return Math.round(x * 2) / 2; }

module.exports = {
  erf, normalCdf, normalPpf,
  americanFromProb, probFromAmerican, decimalFromAmerican, breakevenProb, ev, devigTwoWay,
  PYTHAG_EXPONENT, pythagoreanWinPct, log5,
  makeRng, makeNormalPair, pearson, phi,
  fmtSigned, fmtPct, fmtAmerican, snapHalf
};

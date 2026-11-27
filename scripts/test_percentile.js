#!/usr/bin/env node
/*
 * test_percentile.js - the P/E percentile has to be right, because "the 30th percentile of its
 * sector" is a claim a reader will act on.
 *
 * The function is read out of docs/index.html rather than re-implemented here, so this tests the
 * code that actually ships. A re-implementation would pass while the page stayed wrong.
 */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'index.html'), 'utf8');
const m = html.match(/function pePercentile\([\s\S]*?\n\}/);
if (!m) { console.error('FAIL: pePercentile not found in docs/index.html'); process.exit(1); }
eval(m[0]);

function eq(a, b, what) {
  if (a !== b) { console.error(`FAIL ${what}: got ${a}, expected ${b}`); process.exitCode = 1; return false; }
  return true;
}

// a hand-made sector: P/Es 10, 20, 30, 40, 50
const all = {};
[10, 20, 30, 40, 50].forEach((pe, i) => {
  all['S' + i] = { sector: 'Test Sector', fund: { pe } };
});

const mid = pePercentile(30, 'Test Sector', all);
eq(mid && mid.n, 5, 'peer count');
eq(mid && mid.pct, 40, 'percentile of the middle value (2 of 5 below)');
eq(mid && mid.median, 30, 'sector median');

eq(pePercentile(10, 'Test Sector', all).pct, 0, 'lowest value is the 0th percentile');
eq(pePercentile(50, 'Test Sector', all).pct, 80, 'highest value is the 80th percentile');

// guards
eq(pePercentile(null, 'Test Sector', all), null, 'null P/E returns null');
eq(pePercentile(-5, 'Test Sector', all), null, 'negative P/E returns null');
eq(pePercentile(30, 'Unknown Sector', all), null, 'unknown sector returns null');

// too few peers to make a claim
const thin = { A: { sector: 'Thin', fund: { pe: 10 } }, B: { sector: 'Thin', fund: { pe: 20 } } };
eq(pePercentile(15, 'Thin', thin), null, 'fewer than 3 peers returns null');

// stocks with no P/E must not be counted
const mixed = { A: { sector: 'Mix', fund: { pe: 10 } }, B: { sector: 'Mix', fund: { pe: 20 } },
                C: { sector: 'Mix', fund: { pe: 30 } }, D: { sector: 'Mix', fund: {} },
                E: { sector: 'Mix', fund: { pe: null } } };
const mx = pePercentile(20, 'Mix', mixed);
eq(mx && mx.n, 3, 'stocks without a P/E are excluded from the peer count');
eq(mx && mx.pct, 33, 'percentile computed over the 3 that do report');

if (!process.exitCode) console.log('PASS  pePercentile: 10 assertions');

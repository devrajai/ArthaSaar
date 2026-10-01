const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Read the treemap.js file
const code = fs.readFileSync(path.join(__dirname, '../treemap.js'), 'utf8');

// The file has an IIFE which keeps everything scoped.
// To test chgColor, we extract the function string and evaluate it.
const chgColorMatch = code.match(/function chgColor\(p\) \{[\s\S]*?\n  \}/);

if (!chgColorMatch) {
    throw new Error("Could not find chgColor function in treemap.js");
}

const chgColorCode = chgColorMatch[0];

// Evaluate the function in the current scope
eval(chgColorCode);

// Write basic assertions
function runTests() {
    console.log("Running tests for chgColor...");

    // Test null/undefined
    assert.strictEqual(chgColor(null), "rgba(255,255,255,.08)", "null input should return faint white");
    assert.strictEqual(chgColor(undefined), "rgba(255,255,255,.08)", "undefined input should return faint white");

    // Test zero
    assert.strictEqual(chgColor(0), "rgba(47,122,68,0.25)", "0 should return base green");

    // Test positive small (p < 3)
    assert.strictEqual(chgColor(1.5), "rgba(47,122,68,0.63)", "1.5 should return mid green");

    // Test positive max (p >= 3)
    assert.strictEqual(chgColor(3), "rgba(47,122,68,1.00)", "3 should return max green");
    assert.strictEqual(chgColor(5), "rgba(47,122,68,1.00)", "5 should return max green");

    // Test negative small (p > -3)
    assert.strictEqual(chgColor(-1.5), "rgba(163,74,74,0.63)", "-1.5 should return mid red");

    // Test negative max (p <= -3)
    assert.strictEqual(chgColor(-3), "rgba(163,74,74,1.00)", "-3 should return max red");
    assert.strictEqual(chgColor(-5), "rgba(163,74,74,1.00)", "-5 should return max red");

    console.log("All tests passed successfully! ✅");
}

runTests();

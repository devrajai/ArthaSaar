const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

test('getKey error handling', async (t) => {
  const code = fs.readFileSync(path.join(__dirname, '../journal.js'), 'utf8');

  // Extract the function using regex to test it in isolation
  const match = code.match(/function getKey\(\)\s*\{([\s\S]*?return k;\s*\n\s*\})/);
  if (!match) throw new Error("Could not find getKey function");

  const funcStr = match[0];

  await t.test('handles localStorage.getItem error by generating new key', () => {
    let getItemCalled = false;
    let setItemCalled = false;
    let setItemArgs = null;

    const evalSandbox = {
      KEYN: "wlj:key",
      localStorage: {
        getItem: (key) => {
          getItemCalled = true;
          assert.strictEqual(key, "wlj:key");
          throw new Error("SecurityError: Access to localStorage is denied");
        },
        setItem: (key, value) => {
          setItemCalled = true;
          setItemArgs = { key, value };
        }
      },
      Math: Math
    };

    vm.createContext(evalSandbox);
    const result = vm.runInContext(`
      var KEYN = "wlj:key";
      ${funcStr}
      getKey();
    `, evalSandbox);

    assert.strictEqual(getItemCalled, true);
    assert.strictEqual(typeof result, 'string');
    assert.ok(result.length > 20);
    assert.strictEqual(setItemCalled, true);
    assert.strictEqual(setItemArgs.key, "wlj:key");
    assert.strictEqual(setItemArgs.value, result);
  });

  await t.test('handles localStorage.setItem error when generating new key', () => {
    const sandbox = {
      KEYN: "wlj:key",
      localStorage: {
        getItem: () => {
          return null; // Force key generation
        },
        setItem: () => {
          throw new Error("QuotaExceededError");
        }
      },
      Math: Math
    };

    vm.createContext(sandbox);
    const result = vm.runInContext(`
      var KEYN = "wlj:key";
      ${funcStr}
      getKey();
    `, sandbox);

    assert.strictEqual(typeof result, 'string');
    assert.ok(result.length > 0);
  });
});

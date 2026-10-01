/**
 * @jest-environment jsdom
 */

const fs = require('fs');
const path = require('path');

describe('journal.js save() functionality', () => {
  let originalSetItem;
  let journalCode;

  beforeAll(() => {
    journalCode = fs.readFileSync(path.resolve(__dirname, '../journal.js'), 'utf8');
  });

  beforeEach(() => {
    originalSetItem = Storage.prototype.setItem;
    localStorage.clear();
    // Mock fetch for the loadPx function inside journal.js
    window.fetch = jest.fn(() => Promise.resolve({
      json: () => Promise.resolve({})
    }));
  });

  afterEach(() => {
    Storage.prototype.setItem = originalSetItem;
    jest.restoreAllMocks();
    delete window.fetch;
  });

  it('save() should handle errors gracefully when localStorage.setItem throws', () => {
    // Setup the mock to throw an error
    Storage.prototype.setItem = jest.fn((key, value) => {
      // Intentionally throw an error simulating QuotaExceededError or disabled cookies
      throw new Error('QuotaExceededError');
    });

    // We can evaluate journal.js directly. It is an IIFE. We'll replace the line before
    // it registers `loadPx` to extract the internal `save` function to test it.
    // We also expose the internally used constant DATAN and getKey to verify exactly what was passed.
    const testCode = journalCode.replace(
      'function loadPx()',
      'window.save_test = save; window.getKey_test = getKey; window.DATAN_test = DATAN; function loadPx()'
    );

    // Set up minimal DOM for journal.js to mount successfully
    document.body.innerHTML = `
      <section id="home"><div class="homegrid"></div></section>
      <footer></footer>
    `;

    // Execute the code
    eval(testCode);

    // Make sure our mock is active by asserting that directly calling setItem throws
    expect(() => { localStorage.setItem('test_key', 'test_val'); }).toThrow('QuotaExceededError');

    // Call the exposed save function
    // It shouldn't throw an error despite setItem throwing
    expect(() => {
      window.save_test({ test: 123 });
    }).not.toThrow();

    // Verify it attempted to save
    expect(Storage.prototype.setItem).toHaveBeenCalled();
    // It should have tried to save the 'wlj:data' (which is DATAN)
    expect(Storage.prototype.setItem).toHaveBeenCalledWith(window.DATAN_test, expect.any(String));
  });
});

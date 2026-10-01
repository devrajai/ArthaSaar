const { squarify } = require('../treemap');

describe('squarify', () => {
  it('should handle an empty array', () => {
    const out = [];
    squarify([], 0, 0, 100, 100, out);
    expect(out).toEqual([]);
  });

  it('should handle a single item', () => {
    const out = [];
    const items = [{ s: 'A', v: 100 }];
    squarify(items, 0, 0, 100, 100, out);
    expect(out).toEqual([
      [{ s: 'A', v: 100 }, 0, 0, 100, 100]
    ]);
  });

  it('should divide width proportionally when w >= h', () => {
    const out = [];
    const items = [{ s: 'A', v: 50 }, { s: 'B', v: 50 }];
    squarify(items, 0, 0, 100, 50, out);
    expect(out).toEqual([
      [{ s: 'A', v: 50 }, 0, 0, 50, 50],
      [{ s: 'B', v: 50 }, 50, 0, 50, 50]
    ]);
  });

  it('should divide height proportionally when h > w', () => {
    const out = [];
    const items = [{ s: 'A', v: 50 }, { s: 'B', v: 50 }];
    squarify(items, 0, 0, 50, 100, out);
    expect(out).toEqual([
      [{ s: 'A', v: 50 }, 0, 0, 50, 50],
      [{ s: 'B', v: 50 }, 0, 50, 50, 50]
    ]);
  });

  it('should handle uneven divisions', () => {
    const out = [];
    const items = [{ s: 'A', v: 60 }, { s: 'B', v: 40 }];
    squarify(items, 0, 0, 100, 100, out);
    expect(out).toEqual([
      [{ s: 'A', v: 60 }, 0, 0, 60, 100],
      [{ s: 'B', v: 40 }, 60, 0, 40, 100]
    ]);
  });

  it('should handle recursive divisions for multiple items', () => {
    const out = [];
    const items = [
      { s: 'A', v: 40 },
      { s: 'B', v: 30 },
      { s: 'C', v: 20 },
      { s: 'D', v: 10 }
    ];
    squarify(items, 0, 0, 100, 100, out);

    expect(out.length).toBe(4);

    // Check sums of areas
    let totalArea = 0;
    out.forEach(rect => {
      const w = rect[3];
      const h = rect[4];
      totalArea += w * h;
    });
    // Expected total area = 100 * 100 = 10000.
    expect(totalArea).toBeCloseTo(10000, 1);

    // Check specific rect coordinates to ensure layout rules
    const rectA = out.find(r => r[0].s === 'A');
    expect(rectA[1]).toBe(0); // x
    expect(rectA[2]).toBe(0); // y
    expect(rectA[3]).toBe(70); // w
    expect(rectA[4]).toBeCloseTo(57.14, 2); // h
  });
});

  it('should handle extreme skew where first item exceeds half but reaches end of array', () => {
    const out = [];
    const items = [{ s: 'A', v: 90 }, { s: 'B', v: 10 }];
    squarify(items, 0, 0, 100, 100, out);
    // Total = 100, Half = 50
    // i=0, v=90. acc=90, k=1. acc >= 50, break.
    // k is 1. Not >= items.length.
    // What if we have a situation where k >= items.length?
    // Let's analyze: for (var i = 0; i < items.length; i++) { acc += items[i].v; k = i + 1; if (acc >= half) break; }
    // If the loop reaches the end, k will be items.length. Then `if (k >= items.length) k = items.length - 1;` kicks in.
    // This happens if the sum of all elements somehow doesn't exceed `half` (which is impossible since half = total / 2 and total > 0).
    // Or if `acc` calculation is slightly off due to float precision?
    // Or simply, if there are 2 items and the first one is smaller than half, so it goes to second item.
    // Total = 100, Half = 50.
    // items: A=40, B=60.
    // i=0: acc=40, k=1. Not >= 50.
    // i=1: acc=100, k=2. >= 50, break.
    // Then k=2, which is items.length (2).
    // `if (k >= items.length) k = items.length - 1` -> k becomes 1.
    // This perfectly hits the edge case line!
  });
  it('should hit the k >= items.length edgecase', () => {
    const out = [];
    const items = [{ s: 'A', v: 40 }, { s: 'B', v: 60 }];
    squarify(items, 0, 0, 100, 100, out);
    expect(out.length).toBe(2);
    // Since k becomes 1, A is separated from B.
    // A gets 40 width, B gets 60 width.
    expect(out[0][0].s).toBe('A');
    expect(out[0][3]).toBe(40);
  });

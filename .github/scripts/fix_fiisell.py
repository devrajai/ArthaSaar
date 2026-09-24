#!/usr/bin/env python3
# fix_fiisell.py v2 - telegram_brain.py me FII/DII ke +/- ki jagah BUY/SELL words
# (v2: quote-safe - double quotes chr(34) se bante hain, JSON push safe)
TB = 'scripts/telegram_brain.py'
Q = chr(34)
NL = chr(10)


def main():
    s = open(TB, encoding='utf-8').read()
    changed = []
    if 'def bs(' not in s:
        anchor = ('return f' + Q + '+\u20b9{v:,.0f} Cr' + Q
                  + ' if v >= 0 else f' + Q + '\u2212\u20b9{abs(v):,.0f} Cr' + Q + NL)
        assert anchor in s, 'cr anchor missing'
        bsfn = (anchor + NL
                + 'def bs(v):' + NL
                + '    # FII/DII ke liye: Buy/Sell word (Dev ka rule: sirf +/- nahi)' + NL
                + '    try:' + NL
                + '        v = float(v)' + NL
                + '    except (TypeError, ValueError):' + NL
                + '        return ' + Q + '?' + Q + NL
                + '    return f' + Q + 'Buy \u20b9{v:,.0f} Cr' + Q
                + ' if v >= 0 else f' + Q + 'Sell \u20b9{abs(v):,.0f} Cr' + Q + NL)
        s = s.replace(anchor, bsfn)
        changed.append('bs() added')
    for old, new in [('cr(fii)', 'bs(fii)'), ('cr(dii)', 'bs(dii)'), ('cr(f.get(', 'bs(f.get(')]:
        if old in s:
            s = s.replace(old, new)
            changed.append(old)
    open(TB, 'w', encoding='utf-8').write(s)
    print('telegram_brain.py:', ', '.join(changed) if changed else 'already patched')


main()

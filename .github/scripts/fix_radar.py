#!/usr/bin/env python3
# fix_radar.py - globals.js emoji escape fix (one-shot, idempotent)
# GLOBAL->INDIA ENGINE header ka compass emoji: \uD83E\uDED (galath) -> \uD83E\uDDED (sahi)
# quote-safe style: sirf single quotes
P = 'globals.js'

s = open(P, encoding='utf-8').read()
if '\\uD83E\\uDED ' in s and '\\uD83E\\uDDED ' not in s:
    s = s.replace('\\uD83E\\uDED ', '\\uD83E\\uDDED ')
    open(P, 'w', encoding='utf-8').write(s)
    print('globals.js: emoji escape fixed')
else:
    print('globals.js: already ok')

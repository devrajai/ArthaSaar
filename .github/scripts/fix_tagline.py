# fix_tagline.py - market-brain: tagline se 'Dev' s personal terminal hatao.
# Bas counts rehte hai: stocks/indices/crypto/IPO. Idempotent one-shot.
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
old = 'Dev' + chr(39) + 's personal terminal ' + chr(183) + ' '
n = s.count(old)
if n == 0:
    old = 'Dev' + chr(39) + 's personal terminal'
    n = s.count(old)
if n:
    s = s.replace(old, '')
    p.write_text(s, encoding='utf-8')
    print('tagline cleaned:', n)
else:
    print('tagline not found (already fixed?)')

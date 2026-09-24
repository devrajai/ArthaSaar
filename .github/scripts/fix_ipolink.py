# fix_ipolink.py - market-brain: IPO tile ka link github.io (dead) se Vercel pe shift.
# devrajai bhi URL me se gaya. Idempotent one-shot.
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
old = 'https://devrajai.github.io/ipo-terminal/'
new = 'https://ipo-terminal.vercel.app/'
n = s.count(old)
if n:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('ipo tile link updated:', n)
else:
    print('ipo link not found (already fixed?)')

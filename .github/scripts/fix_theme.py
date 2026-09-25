# fix_theme.py - app.js cache version bump for calm theme launch
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
old = 'app.js?v=25sep26a41'
new = 'app.js?v=25sep26a42'
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('bumped:', old, '->', new)
else:
    import re
    print('tag not found; current:', re.findall(r'app\.js\?v=\S+', s))

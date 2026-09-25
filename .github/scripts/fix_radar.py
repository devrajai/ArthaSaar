# fix_radar.py - app.js cache version bump for radars launch
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
old = 'app.js?v=21sep26a40'
new = 'app.js?v=25sep26a41'
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('bumped:', old, '->', new)
else:
    print('tag not found (already bumped?): current tags:')
    import re
    print(re.findall(r'app\.js\?v=\S+', s))

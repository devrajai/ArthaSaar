# fix_brand2.py - rebrand leftovers: data files, TG alert text, APK cert, brandfix tagline.
from pathlib import Path

def sub(path, pairs):
    p = Path(path)
    if not p.exists():
        print('missing:', path)
        return
    s = p.read_text(encoding='utf-8')
    o = s
    for a, b in pairs:
        s = s.replace(a, b)
    if s != o:
        p.write_text(s, encoding='utf-8')
        print('updated:', path)
    else:
        print('no change:', path)

# 1) brandfix.js: privacy leak - tagline "Dev's personal terminal" wapas overwrite hota tha
sub('brandfix.js', [("Dev's personal terminal", '2,305 stocks · 139 indices · crypto · IPO')])

# 2) data/*.json: card headers/descriptions me "Market Brain"
import glob
for f in glob.glob('data/*.json'):
    sub(f, [('Market Brain', 'ArthaSaar'), ('MARKET BRAIN', 'ARTHASAAR'),
            ('MarketBrain', 'ArthaSaar'), ('simple English for Dev.', 'simple English.')])

# 3) test_alert.py: TG message identity
sub('.github/scripts/test_alert.py', [('Market Brain by Dev', 'ArthaSaar')])

# 4) apk.yml: signing cert name + commit msg (passwords untouched - signing continuity)
sub('.github/workflows/apk.yml', [
    ('CN=Market Brain, OU=Dev, O=Dev Raj', 'CN=ArthaSaar, OU=ArthaSaar, O=ArthaSaar'),
    ('build: Market Brain Android APK', 'build: ArthaSaar Android APK')])

# 5) mbscore.yml: workflow display name
sub('.github/workflows/mbscore.yml', [('name: Market Brain Score', 'name: ArthaSaar Score')])

print('DONE')

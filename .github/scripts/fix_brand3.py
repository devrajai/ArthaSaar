# fix_brand3.py - 'Dev' name removal round 3: site UI + data files + comments + TG alert.
# Saari targeted replacements - company-name false positives (brain-screener/universe/companies) untouched.
# NOTE: is script me .github/workflows/*.yml ko touch NAHI karte (GITHUB_TOKEN push limit).
import re
from pathlib import Path

def sub(fp, pairs, regex=False):
    p = Path(fp)
    if not p.exists():
        print(f'SKIP missing: {fp}')
        return
    s = p.read_text(encoding='utf-8')
    total = 0
    for old, new in pairs:
        if regex:
            s2, n = re.subn(old, new, s)
        else:
            n = s.count(old)
            s2 = s.replace(old, new)
        if n:
            print(f'  {fp}: {old[:44]!r} -> x{n}')
            total += n
        s = s2
    if total:
        p.write_text(s, encoding='utf-8')
    return total

print('== 1. Site UI (visible) ==')
sub('index.html', [
    ("ARTHASAAR — Dev's Terminal", 'ARTHASAAR — Market Intelligence Terminal'),
    ('My Notes — Dev\u2019s course notes (Advance.pdf)', 'My Notes — Course Notes (Advance.pdf)'),
    ("My Notes — Dev's course notes (Advance.pdf)", 'My Notes — Course Notes (Advance.pdf)'),
])
sub('bank.js', [
    ('Dev ke personal notebook ke rules', 'personal notebook ke rules'),
    ('Dev ke notebook rules', 'notebook rules'),
])
sub('learnadd.js', [
    ('written in simple English for Dev.', 'written in simple English.'),
])
sub('index.html', [
    ('Personal market intelligence terminal of Dev.', 'Personal market intelligence terminal.'),
])
sub('oldapp.js', [
    ("Dev\\'s collected library", 'Collected library'),
])
sub('oldapp.js', [
    ("from Dev's own handwritten study", 'from the handwritten study notes'),
])

print('== 2. Data files (visible text) ==')
sub('data/banks.json', [
    ('Rules: Dev ke personal notebook se', 'Rules: personal notebook se'),
])
sub('data/devs_notes_digest.json', [
    ("FULL digest of Dev's 3 study PDFs", 'FULL digest of 3 study PDFs'),
    ("= Dev's own Sensex year-by-year study", '= Sensex year-by-year study'),
    ('"Warning written by Dev: ', '"Warning: '),
    ("Dev's own handwritten Sensex study (Oct 2024)", 'Handwritten Sensex study (Oct 2024)'),
])
sub('data/education.json', [
    ("Dev's market education library", 'Market education library'),
    ("Dev's main playlist source", 'main playlist source'),
    ("Dev's curated 'Inspiring Traders' playlist", "Curated 'Inspiring Traders' playlist"),
    ('saved by Dev 18/09/26', 'saved 18/09/26'),
    ("Dev's course notes (Advance.pdf)", 'course notes (Advance.pdf)'),
    ('market analysis videos Dev follows', 'market analysis videos'),
    ("Dev's course playlists", 'Course playlists'),
])
sub('data/members.json', [
    ('"name": "Dev Raj"', '"name": "Dev"'),
])

print('== 3. TG alert text ==')
sub('scripts/stress.py', [
    ('(ArthaSaar by Dev)', '(ArthaSaar)'),
])

print('== 4. Code comments (repo public hai) ==')
sub('style.css', [
    ('/* MARKET BRAIN — Liquid Glass terminal (Dev\u2019s personal TX3)', '/* ARTHASAAR — Liquid Glass terminal'),
    ("/* MARKET BRAIN — Liquid Glass terminal (Dev's personal TX3)", '/* ARTHASAAR — Liquid Glass terminal'),
])
sub('globals.js', [("(Dev's Bloomberg)", '(ArthaSaar)')])
sub('learnfix.js', [("Dev's Notebook (Advance.pdf", 'Notebook (Advance.pdf')])
sub('stage.js', [('4-Stage (Dev ke notebook rules)', '4-Stage (notebook rules)')])
sub('tools5.js', [('(Dev request)', '(request)')])
sub('scripts/bankscan.py', [('(Dev ke notebook rules)', '(notebook rules)')])
sub('scripts/bigplayer.py', [('Dev ka idea, Manish podcast framework', 'Manish podcast framework')])
sub('scripts/global.py', [("(Dev's Bloomberg Phase 1)", '(ArthaSaar Phase 1)')])
sub('scripts/newsdigest.py', [('(Dev ka rule: sirf sach, no masala)', '(rule: sirf sach, no masala)')])
sub('scripts/rotpts.py', [('(Dev ka rule)', '(rule)')])
sub('scripts/smart_brain.py', [('Dev ka auto-analyst', 'auto-analyst')])
sub('scripts/stages.py', [('(Dev ke notebook ke 4-Stage rules)', '(notebook 4-Stage rules)')])
sub('scripts/stress.py', [("(Dev's Bloomberg)", '(ArthaSaar)')])
sub('scripts/telegram_brain.py', [
    ("Dev's personal market bot", 'market bot'),
    ("Dev's chat id", 'owner chat id'),
    ('(Dev ka rule: sirf +/- nahi)', '(rule: sirf +/- nahi)'),
])
sub('scripts/timesfm_forecast.py', [("(Dev's TimesFM 3.0 wishlist)", '(TimesFM 3.0 wishlist)')])
sub('scripts/fix_notoolkit.py', [('(Dev request)', '(request)')])

print('== 5. README + PROJECT_BRAIN ==')
sub('README.md', [
    ("ArthaSaar — Dev's personal stock screener + budget-day study engine",
     'ArthaSaar — stock screener + budget-day study engine'),
])
# PROJECT_BRAIN.md: generic name removal
pb = Path('PROJECT_BRAIN.md')
if pb.exists():
    s = pb.read_text(encoding='utf-8')
    before = s
    s = s.replace('Nandan pithadiya (@Dev_pithadiya) + Hemant (____Hemant) + Solanki (@Rahul3573)', 'Nandan + Hemant + Rahul + Vidhi + Jems Bonda')
    s = s.replace('Dev Raj', 'owner')
    s = s.replace('Dev\u2019s', 'the').replace("Dev's", 'the')
    s = s.replace(' by Dev', '')
    s = re.sub(r'\bDev\b', 'owner', s)
    if s != before:
        pb.write_text(s, encoding='utf-8')
        print('  PROJECT_BRAIN.md: Dev mentions -> owner/the')

print('== FINAL CHECK (bacche hue traces) ==')
left = []
for f in ['index.html', 'bank.js', 'learnadd.js', 'oldapp.js', 'globals.js', 'learnfix.js',
          'stage.js', 'tools5.js', 'style.css', 'README.md', 'PROJECT_BRAIN.md',
          'data/banks.json', 'data/devs_notes_digest.json', 'data/education.json',
          'scripts/stress.py', 'scripts/telegram_brain.py']:
    p = Path(f)
    if not p.exists():
        continue
    for i, ln in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if re.search(r'\bDev\b|Dev\u2019s|Dev\u2019 ka', ln):
            left.append(f'{f}:{i}: {ln.strip()[:80]}')
if left:
    print(f'{len(left)} lines still have Dev:')
    for l in left[:12]:
        print('  ', l)
else:
    print('CLEAN - koi Dev trace nahi bacha (in files me)')

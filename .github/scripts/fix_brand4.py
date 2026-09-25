# fix_brand4.py - final sweep: test_alert.py TG text + ipo/PROJECT_BRAIN.md (Dev ka poora doc).
# NOTE: .github/workflows/*.yml ko touch NAHI karta.
import re
from pathlib import Path

# 1) test_alert.py - TG test message me 'Dev's Bloomberg' + comment
p = Path('.github/scripts/test_alert.py')
s = p.read_text(encoding='utf-8')
s = s.replace("test message Dev + Jems Bonda ko", 'test message 2 members ko')
s = s.replace("MARKET STRESS METER (Dev's Bloomberg)", 'MARKET STRESS METER (ArthaSaar)')
s = s.replace('MARKET STRESS METER (Dev\u2019s Bloomberg)', 'MARKET STRESS METER (ArthaSaar)')
p.write_text(s, encoding='utf-8')
print('test_alert.py cleaned')

# 2) ipo/PROJECT_BRAIN.md - Owner: Dev, handles, Dev's/Dev mentions
p = Path('ipo/PROJECT_BRAIN.md')
if p.exists():
    s = p.read_text(encoding='utf-8')
    before = s
    s = s.replace('(Dev + Nandan @Dev_pithadiya + Hemant ____Hemant + Solanki @Rahul3573)', '(Nandan + Hemant + Rahul)')
    s = s.replace('Nandan (@Dev_pithadiya, chat id', 'Nandan (chat id')
    s = s.replace('Nandan (@Dev_pithadiya', 'Nandan')
    s = s.replace('Owner: Dev (mobile-only user, Android Chrome)', 'Owner: mobile-only user (Android Chrome)')
    s = s.replace('Dev Raj', 'owner')
    s = s.replace('Dev\u2019s', 'the').replace("Dev's", 'the')
    s = s.replace(' by Dev', '')
    s = re.sub(r'\bDev\b', 'owner', s)
    if s != before:
        p.write_text(s, encoding='utf-8')
        print('ipo/PROJECT_BRAIN.md cleaned')

# final check
left = []
for f in ['.github/scripts/test_alert.py', 'ipo/PROJECT_BRAIN.md']:
    for i, ln in enumerate(Path(f).read_text(encoding='utf-8').splitlines(), 1):
        if re.search(r"\bDev\b|Dev\u2019s", ln):
            left.append(f'{f}:{ln}: {ln.strip()[:70]}')
print('REMAINING:', len(left))
for l in left[:5]:
    print(' ', l)

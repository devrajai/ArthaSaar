# rename_artha.py - rebrand: Market Brain -> ArthaSaar (sirf dikhane wala naam).
# File paths / URLs / repo-name ('market-brain' kebab-case) ko NAHI chhedta.
# Quote-safe: sirf single quotes. Idempotent one-shot.
from pathlib import Path

REPL = [('Market Brain', 'ArthaSaar'), ('MARKET BRAIN', 'ARTHASAAR'),
        ('Market brain', 'ArthaSaar'), ('MarketBrain', 'ArthaSaar'),
        ('market brain', 'ArthaSaar')]
SKIP_DIRS = {'.git', '.github', 'data', 'node_modules'}
EXTS = {'.html', '.js', '.json', '.py', '.md'}
SKIP_FILES = {'market-brain.apk'}

root = Path('.')
changed = 0
for p in sorted(root.rglob('*')):
    if not p.is_file():
        continue
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    if p.name in SKIP_FILES or p.suffix not in EXTS:
        continue
    try:
        s = p.read_text(encoding='utf-8')
    except Exception:
        continue
    orig = s
    for a, b in REPL:
        s = s.replace(a, b)
    if s != orig:
        p.write_text(s, encoding='utf-8')
        changed += 1
        print('updated:', p)
print('total files updated:', changed)

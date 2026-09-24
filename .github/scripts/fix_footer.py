# fix_footer.py - market-brain: 'Market Brain By : Dev Raj with Sarvam Ai' footer line
# remove + version bump a39->a40 (index.html change). Idempotent one-shot.
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
out = []
removed = 0
for ln in s.split(chr(10)):
    if 'Market Brain By' in ln:
        removed += 1
        continue
    out.append(ln)
s2 = chr(10).join(out)
s2 = s2.replace('v=21sep26a39', 'v=21sep26a40')
p.write_text(s2, encoding='utf-8')
print('footer lines removed:', removed, '| version bumped a40' if 'a40' in s2 else '| no version change')

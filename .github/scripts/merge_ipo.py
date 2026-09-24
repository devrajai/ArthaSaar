# merge_ipo.py - market-brain: IPO terminal site ko ipo/ folder me merge karo.
# Source: devrajai/ipo-terminal (public). Tile link bhi in-site kar do.
# Quote-safe: sirf single quotes. Idempotent one-shot.
import shutil
import subprocess
from pathlib import Path

subprocess.run(['rm', '-rf', '/tmp/iposrc'], check=False)
subprocess.run(['git', 'clone', '--depth', '1',
                'https://github.com/devrajai/ipo-terminal.git', '/tmp/iposrc'], check=True)

src = Path('/tmp/iposrc')
dst = Path('ipo')
if dst.exists():
    shutil.rmtree(dst)
dst.mkdir()
copied = 0
for item in sorted(src.iterdir()):
    if item.name in ('.git', '.github', 'archive'):
        continue
    if item.is_dir():
        shutil.copytree(item, dst / item.name)
    else:
        shutil.copy2(item, dst / item.name)
    copied += 1
print('copied entries:', copied)

idx = Path('index.html')
s = idx.read_text(encoding='utf-8')
old = 'https://ipo-terminal.vercel.app/'
n = s.count(old)
if n:
    s = s.replace(old, 'ipo/')
    idx.write_text(s, encoding='utf-8')
print('tile links updated to in-site ipo/:', n)

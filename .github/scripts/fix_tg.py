#!/usr/bin/env python3
# fix_tg.py - TG schedule v2 (25/09/26, Dev ka plan):
# 9:15 AM IPO+preopen (morning-brain.yml), 4 PM Day Analysis Close (telegram.yml),
# 9:15 PM Night unified (news+stress+GTI+levels). Purane duplicates dispatch-only.
import pathlib

def rep(p, old, new):
    s = pathlib.Path(p).read_text()
    assert old in s, 'MISSING in %s: %r' % (p, old[:60])
    pathlib.Path(p).write_text(s.replace(old, new, 1))

# ---------- naye files ----------
pathlib.Path('scripts/morning_ipo.py').write_text(r'''#!/usr/bin/env python3
# morning_ipo.py - 9:15 AM IST: IPO digest + Pre-open breadth (EK message)
# Dev format (25/09): CLOSES TODAY / ALLOTMENT TODAY / LISTS TODAY / OPEN NOW /
# OPENING SOON + pre-open breadth. Data: ipo/data/ipo-data.json + data/preopen.json
import sys, os, datetime
sys.path.insert(0, 'scripts')
from tghelp import jload, send

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
today = now.date()

IPOD = jload('ipo/data/ipo-data.json')
IPJ = jload('ipo/data/ipos.json')
PRE = jload('data/preopen.json')

# ipos.json lookup (allotment_date etc.)
BYNAME = {}
for it in (IPJ if isinstance(IPJ, list) else IPJ.get('data') or IPJ.get('ipos') or []):
    if isinstance(it, dict) and it.get('name'):
        BYNAME[it['name'].strip().lower()] = it

def pdate(s):
    s = str(s or '').strip()
    if not s or s.startswith('\u2014') or s == '-':
        return None
    for f in ('%d/%m/%y', '%d/%m/%Y', '%b %d, %Y', '%d %b %Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(s, f).date()
        except Exception:
            pass
    return None

def nm(x):
    n = str(x.get('name') or '?')
    for suf in (' (India) Limited', ' Limited', ' Ltd', ' Limited.'):
        if n.endswith(suf):
            n = n[:-len(suf)]
            break
    return n.strip()

def val(x, *keys):
    for k in keys:
        v = x.get(k)
        if v not in (None, '', '\u2014', '-'):
            return v
    return None

ipos = IPOD.get('ipos') or []
closes, allot, lists_, open_now, soon = [], [], [], [], []
for x in ipos:
    o = pdate(x.get('open'))
    c = pdate(x.get('close'))
    l = pdate(x.get('listing'))
    if c == today:
        closes.append(x)
    if l == today:
        lists_.append(x)
    else:
        jit = BYNAME.get(str(x.get('name') or '').strip().lower()) or {}
        ad = pdate(jit.get('allotment_date')) or pdate(jit.get('listing_date'))
        if ad == today:
            allot.append(x)
    if o and o <= today and (c is None or c >= today) and l != today:
        if c != today:
            open_now.append(x)
    if o and today < o <= today + datetime.timedelta(days=7) and x not in soon:
        soon.append(x)

def line(x, extra_open=False):
    parts = [nm(x)]
    lot = val(x, 'lot')
    sub = val(x, 'sub')
    gmp = val(x, 'gmp')
    if lot and lot != '\u2014':
        parts.append('lot %s' % lot)
    if sub and sub != '\u2014':
        parts.append('sub %s' % sub)
    if gmp and gmp not in ('\u2014',):
        parts.append('GMP %s*' % str(gmp).replace('\u20b9', ''))
    return '\u2022 ' + ' \u2022 '.join(parts)

L = []
L.append('\U0001F680 <b>ArthaSaar \u2014 IPO & Pre-open</b>')
L.append(now.strftime('%A, %d %b %Y'))
L.append('')

def sect(emo, title, arr):
    if not arr:
        return
    L.append('%s <b>%s</b>' % (emo, title))
    for x in arr[:6]:
        L.append(line(x))
    L.append('')

sect('\U0001F534', 'CLOSES TODAY (5 PM)', closes)
sect('\U0001F39F', 'ALLOTMENT TODAY', allot)
sect('\U0001F680', 'LISTS TODAY', lists_)
sect('\U0001F7E2', 'OPEN NOW', open_now)
if soon:
    L.append('\U0001F550 <b>OPENING SOON</b>')
    for x in soon[:6]:
        o = pdate(x.get('open'))
        ds = o.strftime('%d/%m') if o else '?'
        L.append('\u2022 %s \u2022 opens %s' % (nm(x), ds))
    L.append('')

gb = PRE.get('gainer_buckets') or {}
lb = PRE.get('loser_buckets') or {}
n = PRE.get('stocks')
if n or gb.get('up_ge_1pct') is not None:
    L.append('\u2600 <b>Pre-open (9:15 IST, %s stocks)</b>' % ('{:,}'.format(n) if n else 'NSE'))
    L.append('Breadth: %s up \u22651%% vs %s down \u22651%%' % (
        gb.get('up_ge_1pct', '-'), lb.get('down_ge_1pct', '-')))
    tg = (PRE.get('top20_gainers') or [])[:3]
    tl = (PRE.get('top20_losers') or [])[:3]
    if tg:
        L.append('\U0001F7E2 ' + ' \u2022 '.join(
            '%s %+.1f%%' % (g.get('symbol'), g.get('change_pct') or 0) for g in tg))
    if tl:
        L.append('\U0001F7E0 ' + ' \u2022 '.join(
            '%s %+.1f%%' % (g.get('symbol'), g.get('change_pct') or 0) for g in tl))
    L.append('')

L.append('*GMP unofficial hai - grey market se, verify karo. (ArthaSaar \U0001F60E)')
send('\n'.join(L))
''')
pathlib.Path('scripts/night_unified.py').write_text(r'''#!/usr/bin/env python3
# night_unified.py - 9:15 PM IST: EK night message
# (news digest + market stress meter + GTI zone alert + night brief merged)
import sys, os, datetime
sys.path.insert(0, 'scripts')
from tghelp import jload, send

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))

stress = jload('data/stress.json')
gti = (jload('data/gti.json').get('symbols') or {}).get('NIFTY 50', {})
x = jload('data/xray.json')
oi = (jload('data/oi-gti.json').get('symbols') or {}).get('NIFTY 50', {})
news = ''
try:
    news = open('data/night-news.txt').read().strip()
except Exception:
    pass

L = []
L.append('\U0001F319 <b>ArthaSaar \u2014 Night Brief</b>')
L.append(now.strftime('%A, %d %b %Y'))
L.append('')

# ---------- 1) news digest (21:00 wala, newsdigest.py ne save kiya) ----------
if news:
    # headline + first lines only (message 4096 limit)
    lines = [l for l in news.split('\n') if l.strip()]
    keep, ln = [], 0
    for l in lines[:60]:
        keep.append(l)
        ln += len(l) + 1
        if ln > 1600:
            break
    L.extend(keep)
    L.append('')
    L.append('(poora news digest site pe: NEWS section)')
    L.append('')

# ---------- 2) market stress meter (radar.yml 6:20 PM data) ----------
if stress.get('score') is not None:
    c = stress.get('comp') or {}
    L.append('\U0001F9D8 <b>Market Stress: %s/100 (%s)</b>' % (
        stress.get('score'), str(stress.get('band') or '?').upper()))
    bits = []
    if 'dma' in c:
        d = c['dma']
        bits.append('NIFTY %s DMA %s%s%%' % ('200-', 'neeche ' if d['d'] < 0 else 'ooper ', abs(d['d'])))
    if 'vix' in c:
        bits.append('VIX %s' % c['vix']['v'])
    if 's4' in c:
        bits.append('Stage-4 %s%%' % c['s4']['p'])
    if 'fii' in c:
        bits.append('FII beche %s din' % c['fii']['n'])
    if bits:
        L.append(' \u2022 '.join(bits))
    if (stress.get('score') or 0) >= 60:
        L.append('\u26A0 stress high \u2014 position chhota rakho!')
    L.append('')

# ---------- 3) GTI zone alert ----------
if gti.get('nearest'):
    near = (gti.get('nearest') or ['?'])[0]
    comp = (gti.get('compression') or {}).get('compressed')
    L.append('\U0001F3AF <b>GTI zone</b>')
    L.append('NIFTY nearest: %s%s' % (near, ' (COMPRESSED!)' if comp else ''))
    dz = (gti.get('day_zones') or {})
    sd = dz.get('SD') or [None, None]
    sc = dz.get('SC') or [None, None]
    sup = [v for v in (sd[0], sc[0], oi.get('put_wall')) if v]
    res = [v for v in (sc[1], sd[1], oi.get('call_wall')) if v]
    def fmt(v):
        v2 = round(v) if isinstance(v, float) else v
        return str(v2)
    if sup:
        L.append('Support: %s' % ' / '.join(fmt(v) for v in sup[:3]))
    if res:
        L.append('Resistance: %s' % ' / '.join(fmt(v) for v in res[:3]))
    L.append('')

# ---------- 4) night brief (xray: kal ke levels) ----------
sd = ((gti.get('day_zones') or {}).get('SD') or [None, None])
spot = oi.get('spot') or (x.get('headline') or '').split()[-1] if x else None
if spot or oi.get('put_wall'):
    L.append('\U0001F4C6 <b>Kal ke Levels</b>')
    if spot:
        L.append('NIFTY %s | %s' % (spot, (x.get('verdict') or '').split(' - ')[0]))
    if oi.get('put_wall'):
        L.append('Support 1: %s (Put wall)' % oi.get('put_wall'))
    if sd[0]:
        L.append('Support 2: %s (GTI SD zone)' % round(sd[0]))
    if oi.get('call_wall'):
        L.append('Resistance 1: %s (Call wall)' % oi.get('call_wall'))
    if sd[1]:
        L.append('Resistance 2: %s (GTI SD zone upar)' % round(sd[1]))
    L.append('')
    L.append('SL rule: level break hua to trade mat pakdo, SL strict rakhna.')

msg = '\n'.join(L)
if len(msg) > 3900:
    msg = msg[:3850] + '\n...'
send(msg)
''')
pathlib.Path('.github/workflows/night-unified.yml').write_text(r'''name: Night Unified Brief
on:
  schedule:
    - cron: '15 15 * * *'  # 9:15 PM IST daily
  workflow_dispatch:
permissions:
  contents: read
jobs:
  night:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python3 scripts/night_unified.py
        env:
          TG_TOKEN: ${{ secrets.TG_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
''')

# ---------- morning-brain.yml: 9:15 + IPO message ----------
rep('.github/workflows/morning-brain.yml', "cron: '50 3 * * 1-5'", "cron: '45 3 * * 1-5'  # 9:15 AM IST")
_p = pathlib.Path('.github/workflows/morning-brain.yml')
_s = _p.read_text()
if 'morning_ipo' not in _s:
    _p.write_text(_s.rstrip('\n') + '\n      - run: python3 scripts/morning_ipo.py\n        env:\n          TG_TOKEN: ${{ secrets.TG_TOKEN }}\n          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}\n')

# ---------- purane workflows: dispatch-only ----------
rep('.github/workflows/telegram-ipo.yml', "    - cron: '15 3 * * *'", "    # merged into morning-brain.yml 9:15 AM message (2026-09-25)")
rep('.github/workflows/telegram.yml', '    - cron: "50 3 * * 1-5"    # 09:20 IST \u2014 market open summary\n', '    # 09:20 market open removed \u2014 9:15 IPO+preopen (morning-brain.yml)\n')
rep('.github/workflows/telegram-day.yml', "    - cron: '15 10 * * 1-5'", "    # merged into 4 PM Day Analysis Close (telegram.yml) 2026-09-25")
rep('.github/workflows/night.yml', "    - cron: '30 16 * * 1-5'", "    # merged into night-unified.yml 9:15 PM message 2026-09-25")

# ---------- gti.yml: TG alert hata (night message me merge) ----------
rep('.github/workflows/gti.yml', '      - run: python3 scripts/gti.py\n        env:\n          TG_TOKEN: ${{ secrets.TG_TOKEN }}\n          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}', '      - run: python3 scripts/gti.py  # TG alert removed - night-unified.yml me merge ho gaya')

# ---------- newsdigest.py: TG_MERGE ----------
rep('scripts/newsdigest.py', "    if len(msg) > 3900:\n        msg = msg[:3850] + NL + '...'\n\n    tok = os.environ.get('TG_TOKEN')", "    if len(msg) > 3900:\n        msg = msg[:3850] + NL + '...'\n\n    if os.environ.get('TG_MERGE') == '1':\n        (DATA / 'night-news.txt').write_text(msg, encoding='utf-8')\n        print('TG_MERGE: night-news.txt saved (send night-unified.py karega)')\n        return\n\n    tok = os.environ.get('TG_TOKEN')")

# ---------- newsdigest.yml: TG_MERGE + commit txt ----------
rep('.github/workflows/newsdigest.yml', '      - run: python3 scripts/newsdigest.py\n', "      - run: python3 scripts/newsdigest.py  # TG_MERGE=1: message file me save\n        env:\n          TG_MERGE: '1'\n      - run: |\n")
rep('.github/workflows/newsdigest.yml', 'git add data/news-digest.json', 'git add data/news-digest.json data/night-news.txt')

print('fix_tg done')

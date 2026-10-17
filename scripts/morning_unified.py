#!/usr/bin/env python3
# morning_unified.py - 8:30 AM IST: EK merged morning message
# (7AM AI brief + Morning Digest + Pre-open brief -> single 8:30 AM message)
# duplicates removed: FII/DII aur Global sirf EK baar
# v2: rotation me LEVEL + OI multi-line (Dev ke Monday paste ke hisaab se)
# quote-safe style: sirf single quotes
import sys, os, json, datetime
sys.path.insert(0, 'scripts')
from tghelp import jload, send, crash_score, status
from rotpts import rotline

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
today = now.strftime('%Y-%m-%d')

mood = jload('data/mood.json')
sb = jload('data/smart-brain.json')
tf = jload('data/timesfm_forecasts.json')
fd = jload('data/fii-dii.json')
ev = jload('data/events.json')
radar = jload('data/radar.json')
gti = (jload('data/gti.json').get('symbols') or {}).get('NIFTY 50', {})
oi = (jload('data/oi-gti.json').get('symbols') or {}).get('NIFTY 50', {})
ind = jload('data/indices-all.json').get('indices') or []
nif_idx = next((x for x in ind if x.get('index') == 'NIFTY 50'), {})
glo = jload('data/global.json').get('items') or []

score, _pts = crash_score({'tf': tf, 'fu': jload('data/futures.json'), 'fd': fd,
                           'br': jload('data/breadth.json'), 'sb': sb})
st, _m = status(score)
HINT = {'SAB CLEAR': 'sab shaant, tension nahi',
        'CAUTION': 'thoda dar, control me',
        'ALERT': 'sambhal ke - risk high',
        'DANGER': 'bahut dar - position tight karo'}

nif = None
for f in (tf.get('forecasts') or []):
    if f.get('symbol') == '^NSEI':
        nif = f

# ---------- fii-history save (digest.py se aaya) ----------
fii = ((fd.get('categories') or {}).get('FII/FPI') or {}).get('net_cr')
dii = ((fd.get('categories') or {}).get('DII') or {}).get('net_cr')
try:
    hist = jload('data/fii-history.json')
    if not isinstance(hist, list):
        hist = []
    hday = fd.get('date') or now.strftime('%d-%b-%Y')
    if not hist or hist[-1].get('date') != hday:
        hist.append({'date': hday, 'fii': fii, 'dii': dii})
        hist = hist[-90:]
        os.makedirs('data', exist_ok=True)
        with open('data/fii-history.json', 'w') as fh:
            json.dump(hist, fh)
except Exception as e:
    print('fii-history skip:', str(e)[:60])

# ---------- message ----------
L = []
L.append('Good Morning \U0001F324\uFE0F')
L.append('')
L.append('\U0001F305 <b>ArthaSaar</b>')
L.append(now.strftime('%A, %d/%m/%y') + ' \u00b7 \U0001F5FE')
L.append('8.30 AM Morning Brief')
L.append('')
L.append('\U0001F4AC Mood: %s/100 (%s)' % (mood.get('overall', '-'), mood.get('tag', '-')))
L.append('')
L.append('\U0001F6A8 Crash score: %d/100 - %s' % (score, HINT.get(st, st)))
L.append('')
if nif and nif.get('median_chg_pct') is not None:
    cls = nif.get('as_of_last_close')
    cls_s = ('{:,.0f}'.format(cls) if isinstance(cls, (int, float)) else '-')
    L.append('\U0001F916 TimesFM Nifty %s | 21-din: %+.1f%%' % (cls_s, nif['median_chg_pct']))
    L.append('')
bull = (sb.get('bull') or [])[:3]
if bull:
    L.append('\U0001F42C AI Bull:')
    for b in bull:
        L.append(str(b.get('symbol', '?')) + ',')
    L[-1] = L[-1].rstrip(',')
    L.append('')
evs = [e for e in (ev.get('week') or []) if e.get('date_ist') == today and e.get('impact') in ('High', 'Medium')]
if evs:
    L.append('\U0001F4C5 Aaj ke events:')
    for e in evs[:4]:
        L.append('\u2022 %s (%s, %s)' % (e.get('title', '?'), e.get('impact'), e.get('time_ist', '')))
    L.append('')
earn = [e for e in (ev.get('earnings') or []) if str(e.get('date') or '') == today]
if earn:
    L.append('\U0001F4BC Aaj results: ' + ', '.join(str(e.get('symbol') or '?') for e in earn[:6]))
    L.append('')

# global cues - overnight (sirf yahan, neeche duplicate nahi)
GL = [('S&P 500', '\U0001F1FA\U0001F1F8 S&P 500'), ('Hang Seng', '\U0001F1ED\U0001F1F0 Hang Seng'),
      ('Crude Oil WTI', '\U0001F6E2\uFE0F Crude WTI'), ('Dollar Index (DXY)', '\U0001F4B5 Dollar Idx')]
glines = []
for nm, lbl in GL:
    g = next((x for x in glo if x.get('name') == nm), None)
    if g and isinstance(g.get('price'), (int, float)):
        p = g['price']
        ps = '{:,.0f}'.format(p) if p >= 100 else '{:,.2f}'.format(p)
        glines.append('%s: %s (%+.2f%%)' % (lbl, ps, g.get('chg_pct', 0) or 0))
if glines:
    L.append('\U0001F30D Global cues (overnight)')
    for g in glines:
        L.append(g)
    L.append('')

# fii/dii (kal) - sirf yahan
if fii is not None or dii is not None:
    def bs(v):
        if v is None:
            return '-'
        if v >= 0:
            return 'Buy \u20B9{:,.0f} Cr'.format(v)
        return 'Sell \u20B9{:,.0f} Cr'.format(abs(v))
    L.append('\U0001F4B8 FII/DII (kal)')
    L.append('FII: %s | DII: %s' % (bs(fii), bs(dii)))
    L.append('')

# corp actions (sirf fresh pre-open data me)
try:
    po = jload('data/preopen.json')
    alerts = po.get('corporate_action_alerts') or []
    upd = str(po.get('updated') or '')[:10]
    if alerts and upd == today:
        L.append('\u26A0\uFE0F Corp actions: ' + ', '.join(
            '%s %s' % (a.get('type') or '', a.get('symbol') or '') for a in alerts[:5]))
        L.append('')
except Exception:
    pass

g = (sb.get('guess') or {})
if g.get('verdict'):
    L.append('\U0001F9E0 Smart Brain call: %s (score %s/100)' % (g['verdict'], g.get('score', '?')))
    L.append('')
rot3 = (tf.get('rotation') or [])[:2]
if rot3:
    lvl = {}
    for f in (tf.get('forecasts') or []):
        if f.get('symbol') and f.get('as_of_last_close'):
            lvl[f['symbol']] = f['as_of_last_close']
    L.append('\U0001F52E TimesFM 21-day rotation')
    for r in rot3:
        nm = r.get('name') or '?'
        p = r.get('chg30') or 0
        lv = lvl.get(r.get('sym'))
        lvs = '{:,.1f}'.format(lv) if isinstance(lv, (int, float)) else ''
        pts = ''
        if lv and p:
            try:
                pts = ' (%+.0f pts)' % (lv - lv / (1.0 + p / 100.0))
            except ZeroDivisionError:
                pass
        head = '\u2022 %s' % nm + ((' ' + lvs) if lvs else '')
        L.append(head)
        L.append('%+.1f%%%s (conf %s%%)' % (p, pts, r.get('conf', '?')))
    L.append('')

# ---------- digest block ----------
pc = nif_idx.get('change_pct')
cp = nif_idx.get('price')
if cp is not None:
    L.append('NIFTY: %s | %s' % ('{:+.2f}%'.format(pc) if pc is not None else '-',
                                 '{:,.2f}'.format(cp)))
near = (gti.get('nearest') or ['?'])[0]
comp = (gti.get('compression') or {}).get('compressed')
L.append('GTI nearest zone: %s%s' % (near, ' (COMPRESSED!)' if comp else ''))
if oi:
    L.append('OI:')
    L.append('max pain %s' % oi.get('max_pain', '-'))
    L.append('PCR %s' % oi.get('pcr', '-'))
    L.append('Put wall %s' % oi.get('put_wall', '-'))
    L.append('Call wall %s' % oi.get('call_wall', '-'))
acc = (radar.get('accumulation') or [])[:2]
if acc:
    L.append('Radar top accumulation:')
    L.append(',\n'.join('%s (%s%% deliv)' % (a['sym'], a.get('deliv', '?')) for a in acc))
L.append('')
L.append('Rule of the day:')
L.append('pehle zone, phir trade - zone ke bina trade = lottery.')

send('\n'.join(L))

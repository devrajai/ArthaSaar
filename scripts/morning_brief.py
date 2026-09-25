#!/usr/bin/env python3
# morning_brief.py - 7:00 IST daily: mood + crash + top bull + rotation (points ke saath) + events/results
# (quote-safe style: sirf single quotes, JSON push safe)
import sys, datetime
sys.path.insert(0, 'scripts')
from tghelp import jload, send, crash_score, status
from rotpts import rotline

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
mood = jload('data/mood.json')
sb = jload('data/smart-brain.json')
score, _pts = crash_score({'tf': jload('data/timesfm_forecasts.json'), 'fu': jload('data/futures.json'),
                          'fd': jload('data/fii-dii.json'), 'br': jload('data/breadth.json'), 'sb': sb})
st, _ = status(score)
tf = jload('data/timesfm_forecasts.json')
nif = None
for f in (tf.get('forecasts') or []):
    if f.get('symbol') == '^NSEI':
        nif = f

L = ['\U0001F305 <b>ArthaSaar - 7AM AI Brief</b>', now.strftime('%A, %d %b %Y'), '']
L.append('\U0001F4AC Mood: %s/100 (%s)' % (mood.get('overall', '-'), mood.get('tag', '-')))
L.append('\U0001F6A8 Crash score: %d/100 - %s' % (score, st))
if nif and nif.get('median_chg_pct') is not None:
    L.append('\U0001F916 TimesFM Nifty 21-din: %+.1f%%' % nif['median_chg_pct'])
bull = (sb.get('bull') or [])[:3]
if bull:
    L.append('\U0001F42C AI Bull: ' + ' - '.join('%s (%s)' % (b.get('symbol'), b.get('score')) for b in bull))
rot = (tf.get('rotation') or [])[:3]
if rot:
    L.append('\U0001F504 Rotation: ' + ' - '.join(rotline(r, tf) for r in rot))
ev = jload('data/events.json')
today = now.strftime('%Y-%m-%d')
evs = [e for e in (ev.get('week') or []) if e.get('date_ist') == today and e.get('impact') in ('High', 'Medium')]
if evs:
    L.append('')
    L.append('\U0001F4C5 Aaj ke events:')
    for e in evs[:4]:
        L.append('- %s (%s, %s %s)' % (e.get('title', '?'), e.get('impact'), e.get('time_ist', ''), e.get('country', '')))
earn = [e for e in (ev.get('earnings') or []) if str(e.get('date_ist') or e.get('date') or '') == today]
if earn:
    L.append('\U0001F4BC Aaj results: ' + ', '.join(str(e.get('symbol') or e.get('name') or '?') for e in earn[:6]))
L.append('')
L.append('sirf data, analysis nahi - khud verify karo')
send('\n'.join(L))

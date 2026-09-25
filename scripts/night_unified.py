#!/usr/bin/env python3
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

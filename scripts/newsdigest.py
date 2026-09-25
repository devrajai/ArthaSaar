#!/usr/bin/env python3
# newsdigest.py - DAILY AUTHENTIC NEWS DIGEST (rule: sirf sach, no masala)
# Free source: Google News RSS (koi API key nahi).
# AUTHENTIC ka matlab: (1) trusted outlets whitelist (2) cross-verify = same story 2+ alag outlets
# (3) clickbait/sensational words EXCLUDED (TV wala masala nahi - Sumeet Jain style).
# Output: data/news-digest.json + TG message sabhi members ko (data/members.json se).
# Quote-safe style: sirf single quotes (JSON push safe).
import json
import os
import re
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
DATA = Path(__file__).resolve().parents[1] / 'data'
TGS = 'https://api.telegram.org/bot{}/sendMessage'

TRUSTED = ['reuters', 'bloomberg', 'economictimes', 'moneycontrol', 'livemint',
           'business-standard', 'business standard', 'hindustantimes', 'thehindu',
           'financialexpress', 'financial express', 'cnbctv18', 'cnbc-tv18', 'businessline',
           'ndtv profit', 'pib', 'timesofindia', 'indianexpress', 'theprint',
           'new york times', 'nytimes', 'cnbc', 'nbc news', 'the economist',
           'wall street journal', 'wsj', 'financial times', 'ft.com',
           'associated press', 'south china morning post', 'scmp']
TOP_TIER = ['reuters', 'bloomberg', 'pib']

MASALA = ['shocking', 'sensational', 'bombshell', 'you wont believe', 'must watch',
          'viral', 'stunned', 'jaw-dropping', 'exposed the truth', 'big breaking',
          'chaukanewali', 'chaukane wali', 'chowkanewali']

QUERIES = [
    ('INDIA MARKETS', 'nifty OR sensex OR stock market India'),
    ('ECONOMY/POLICY', 'RBI OR repo rate OR inflation OR GDP India economy'),
    ('GLOBAL', 'US Fed OR wall street OR crude oil price OR gold price'),
    ('GEOPOLITICS', 'trade war OR tariff OR sanctions OR OPEC OR China economy'),
    ('AUTHENTIC WIRE', 'site:reuters.com India OR markets'),
]

STOP = set('india indian market markets stock stocks says say said new news report reports live updates today daily after over amid ahead from with that this will would about more most best top'.split())


def clean_title(t, src):
    t = re.sub(r'\s+', ' ', t or '').strip()
    suf = ' - ' + src
    if t.endswith(suf):
        t = t[:-len(suf)]
    return t.strip()


def toks(t):
    return set(w for w in re.findall(r'[a-z]{4,}', t.lower()) if w not in STOP)


def trusted(src):
    s = src.lower()
    return any(d in s for d in TRUSTED)


def fetch(q):
    url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(q) + '&hl=en-IN&gl=IN&ceid=IN:en'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        root = ET.fromstring(r.read().decode('utf-8'))
    out = []
    for it in root.findall('.//item')[:22]:
        t = clean_title(it.findtext('title') or '', it.findtext('source') or '')
        src = (it.findtext('source') or '').strip()
        try:
            dt = parsedate_to_datetime(it.findtext('pubDate') or '')
            age_h = (NOW - dt).total_seconds() / 3600.0
        except Exception:
            age_h = 999.0
        if not t or not src:
            continue
        low = t.lower()
        if any(m in low for m in MASALA):
            continue
        if age_h > 36:
            continue
        out.append({'t': t, 'src': src, 'age': age_h})
    return out


def group_stories(items):
    # cross-verify: same story = 50%+ token overlap. Alag outlets count karo.
    groups = []
    for it in items:
        tk = toks(it['t'])
        if not tk:
            continue
        placed = False
        for g in groups:
            ov = len(tk & g['tk']) / float(min(len(tk), len(g['tk'])) or 1)
            if ov >= 0.5:
                g['srcs'].add(it['src'])
                if it['src'] not in [x['src'] for x in g['items']]:
                    g['items'].append(it)
                if it['age'] < g['best_age']:
                    g['best_age'] = it['age']
                    g['t'] = it['t']
                placed = True
                break
        if not placed:
            groups.append({'t': it['t'], 'tk': tk, 'srcs': {it['src']},
                           'items': [it], 'best_age': it['age']})
    return groups


def xray():
    # MARKET X-RAY (video-style): Nifty open/close pattern + FII/DII ka Puppato game
    x = {}
    try:
        req = urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=5d&interval=1d', headers=UA)
        j = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
        r = j['chart']['result'][0]
        q = r['indicators']['quote'][0]
        rows = [(r['timestamp'][i], q['open'][i], q['high'][i], q['low'][i], q['close'][i])
                for i in range(len(r['timestamp'])) if q['open'][i] and q['close'][i]]
        if len(rows) >= 2:
            t, o, h, l, c = rows[-1]
            pt, po, ph, pl, pc = rows[-2]
            chg = round((c - pc) / pc * 100, 2)
            gap_up = o >= pc
            red_close = c < o
            if gap_up and red_close:
                pat = 'gap-up open, RED close - opening strength gayab, sellers jeete'
            elif (not gap_up) and (c > o):
                pat = 'gap-down open, GREEN close - dar bech ke wapas khareeda gaya'
            elif gap_up and (not red_close):
                pat = 'gap-up open, green close - bulls ka din'
            else:
                pat = 'gap-down open, red close - pure selling pressure'
            x = {'o': round(o), 'h': round(h), 'l': round(l), 'c': round(c), 'chg': chg, 'pattern': pat}
    except Exception as e:
        print('WARN xray nifty fail', e)
    # FII/DII + streak
    try:
        fd = json.loads((DATA / 'fii-dii.json').read_text(encoding='utf-8'))
        cats = fd.get('categories') or {}
        x['fii'] = round((cats.get('FII/FPI') or {}).get('net_cr') or 0)
        x['dii'] = round((cats.get('DII') or {}).get('net_cr') or 0)
    except Exception as e:
        print('WARN xray fii fail', e)
    try:
        fh = json.loads((DATA / 'fii-history.json').read_text(encoding='utf-8'))
        last5 = fh[-5:]
        neg = 0
        for row in reversed(last5):
            if (row.get('fii') or 0) < 0:
                neg += 1
            else:
                break
        x['fii_streak'] = neg
        if last5:
            x['puppato'] = 1 if (last5[-1].get('fii') or 0) < 0 and (last5[-1].get('dii') or 0) > 0 else 0
    except Exception as e:
        print('WARN xray history fail', e)
    return x


def main():
    cats = []
    used_tk = []
    for name, q in QUERIES:
        try:
            items = [x for x in fetch(q) if trusted(x['src'])]
        except Exception as e:
            print('WARN fetch fail', name, e)
            items = []
        stories = []
        for g in group_stories(items):
            dup = False
            for u in used_tk:
                if len(g['tk'] & u) / float(min(len(g['tk']), len(u)) or 1) >= 0.55:
                    dup = True
                    break
            if dup:
                continue
            n = len(g['srcs'])
            st = g['t']
            if n >= 2:
                stories.append({'t': st, 'n': n, 'srcs': sorted(g['srcs']),
                                'age': round(g['best_age'], 1), 'x': 1, 'tk': g['tk']})
            elif any(d in ' '.join(g['srcs']).lower() for d in TOP_TIER):
                stories.append({'t': st, 'n': 1, 'srcs': sorted(g['srcs']),
                                'age': round(g['best_age'], 1), 'x': 0, 'tk': g['tk']})
        stories.sort(key=lambda s: (-s['n'], s['age']))
        for s_ in stories[:4]:
            used_tk.append(s_['tk'])
        cats.append({'name': name, 'stories': stories[:4]})
        time.sleep(1)

    for c in cats:
        for s_ in c['stories']:
            s_.pop('tk', None)
    X = xray()
    out = {'u': NOW.strftime('%d %b %Y, %H:%M IST'), 'cats': cats, 'xray': X}
    DATA.mkdir(exist_ok=True)
    (DATA / 'news-digest.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('news-digest.json written')

    # TG message
    NL = chr(10)
    msg = '*ARTHASAAR NEWS*' + NL + NOW.strftime('%A, %d %b') + ' - sirf sach, no masala' + NL
    if X.get('c') is not None:
        gr = X['chg'] >= 0
        msg += NL + '*MARKET X-RAY*' + NL
        msg += 'NIFTY ' + str(X['c']) + ' (' + ('+' if gr else '') + str(X['chg']) + '%) - O ' + str(X['o']) + ' | H ' + str(X['h']) + ' | L ' + str(X['l']) + NL
        msg += X.get('pattern') or ''
        msg += NL + 'FII: ' + ('Buy ' if (X.get('fii') or 0) >= 0 else 'Sell ') + chr(8377) + str(abs(X.get('fii') or 0)) + ' Cr | DII: ' + ('Buy ' if (X.get('dii') or 0) >= 0 else 'Sell ') + chr(8377) + str(abs(X.get('dii') or 0)) + ' Cr'
        if (X.get('fii_streak') or 0) >= 3:
            msg += NL + 'FII ne lagatar ' + str(X['fii_streak']) + ' din becha' + (' - DII sara maal le raha hai (Puppato)' if X.get('puppato') else '')
        msg += NL
    EMO = {'INDIA MARKETS': '\U0001F1EE\U0001F1F3', 'ECONOMY/POLICY': '\U0001F4B9',
           'GLOBAL': '\U0001F30D', 'GEOPOLITICS': '\U0001F6A8', 'AUTHENTIC WIRE': '\U0001F9F5'}
    for c in cats:
        if not c['stories']:
            continue
        msg += NL + EMO.get(c['name'], '\U0001F4B8') + ' *' + c['name'] + '*' + NL
        for s in c['stories'][:3]:
            mark = (' [' + str(s['n']) + ' outlets]' if s['x'] else ' [wire]')
            msg += '\u2022 ' + s['t'][:110] + ' (' + ' + '.join(s['srcs'][:2]) + ')' + mark + NL
    msg += NL + 'Cross-verified = 2+ alag outlets me same khabar. Wire = Reuters/Bloomberg/PIB direct. TV ka masala EXCLUDED.' + NL + 'Free sources: Google News RSS. khud verify karo - sirf data hai, analysis nahi.'
    if len(msg) > 3900:
        msg = msg[:3850] + NL + '...'

    if os.environ.get('TG_MERGE') == '1':
        (DATA / 'night-news.txt').write_text(msg, encoding='utf-8')
        print('TG_MERGE: night-news.txt saved (send night-unified.py karega)')
        return

    tok = os.environ.get('TG_TOKEN')
    if not tok:
        print('no TG_TOKEN - skip send (digest file written)')
        return
    try:
        members = json.loads((DATA / 'members.json').read_text(encoding='utf-8'))
    except Exception:
        members = []
    for m in members:
        cid = m.get('chat_id')
        if not cid:
            continue
        try:
            data = json.dumps({'chat_id': cid, 'text': msg, 'parse_mode': 'Markdown',
                               'disable_web_page_preview': True}).encode()
            req = urllib.request.Request(TGS.format(tok), data=data,
                                          headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=20)
            print('sent to', m.get('name'))
        except Exception as e:
            print('send fail', m.get('name'), e)


main()

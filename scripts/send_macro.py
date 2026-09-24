#!/usr/bin/env python3
# send_macro.py - MACRO PULSE TG message (oil/DXY/10Y/gold + verdict)
# FII line hatayi gayi - wo Market Brain Morning me Buy/Sell words ke saath aata hai (duplicate avoid)
# (quote-safe style: sirf single quotes, JSON push safe)
import json, os, urllib.request


def main():
    d = {}
    try:
        with open('data/macro.json') as f:
            d = json.load(f)
    except Exception:
        return
    t = d.get('today', {})
    tok = os.environ.get('TG_TOKEN')
    ids = os.environ.get('TG_CHAT_ID', '')
    if not tok or not ids:
        print('no TG env, skip')
        return
    streak = d.get('streak_fii_sell_days', 0)
    NL = chr(10)
    msg = ('*MACRO PULSE*' + NL
           + 'Oil: $' + str(t.get('crude', '-')) + ' | DXY: ' + str(t.get('dxy', '-')) + NL
           + '10Y: ' + str(t.get('us10y', '-')) + '% | Rs: ' + str(t.get('usdinr', '-')) + ' | Gold: $' + str(t.get('gold', '-')) + NL
           + ('FII ' + str(streak) + ' din se bech rahe' + NL if streak >= 3 else '')
           + 'Verdict (' + str(d.get('score', 0)) + '/10): ' + d.get('verdict', '-'))
    for cid in [x.strip() for x in ids.split(',') if x.strip()]:
        try:
            data = json.dumps({'chat_id': cid, 'text': msg, 'parse_mode': 'Markdown'}).encode()
            req = urllib.request.Request('https://api.telegram.org/bot' + tok + '/sendMessage', data=data,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=20)
        except Exception as e:
            print('send fail', cid, e)


main()

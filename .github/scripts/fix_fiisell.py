#!/usr/bin/env python3
"""fix_fiisell.py - Ek baar ka patch (one-shot):
1) telegram_brain.py: FII/DII ke +/- ki jagah BUY/SELL words (bs() helper)
2) send_macro.py: MACRO PULSE se duplicate FII line hatayi (Morning me Buy/Sell ke saath aata hai)"""

TB = "scripts/telegram_brain.py"
SM = "scripts/send_macro.py"

NEW_SM = '''#!/usr/bin/env python3
"""send_macro.py - MACRO PULSE TG message (oil/DXY/10Y/gold + verdict).
FII line hata di gayi - wo Market Brain Morning me Buy/Sell ke saath aata hai (duplicate avoid)."""
import json, os, urllib.request

TG = "https://api.telegram.org/bot{}/sendMessage"

def main():
    d = {}
    try:
        with open("data/macro.json") as f:
            d = json.load(f)
    except Exception:
        return
    t = d.get("today", {})
    tok = os.environ.get("TG_TOKEN")
    ids = os.environ.get("TG_CHAT_ID", "")
    if not tok or not ids:
        print("no TG env, skip")
        return
    streak = d.get("streak_fii_sell_days", 0)
    msg = "*MACRO PULSE*" + chr(10) \
        + "Oil: $" + str(t.get("crude", "-")) + " | DXY: " + str(t.get("dxy", "-")) + chr(10) \
        + "10Y: " + str(t.get("us10y", "-")) + "% | Rs: " + str(t.get("usdinr", "-")) + " | Gold: $" + str(t.get("gold", "-")) + chr(10) \
        + (("FII " + str(streak) + " din se bech rahe" + chr(10)) if streak >= 3 else "") \
        + "Verdict (" + str(d.get("score", 0)) + "/10): " + d.get("verdict", "-")
    for cid in [x.strip() for x in ids.split(",") if x.strip()]:
        try:
            data = json.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
            req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage", data=data,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20)
        except Exception as e:
            print("send fail", cid, e)

if __name__ == "__main__":
    main()
'''

def main():
    s = open(TB, encoding="utf-8").read()
    changed = []
    if "def bs(" not in s:
        anchor = 'return f"+\u20b9{v:,.0f} Cr" if v >= 0 else f"\u2212\u20b9{abs(v):,.0f} Cr"\n'
        assert anchor in s, "cr() anchor missing"
        bsfn = anchor + '\n\ndef bs(v):\n    """FII/DII ke liye: Buy/Sell word (Dev ka rule: sirf +/- nahi)"""\n    try:\n        v = float(v)\n    except (TypeError, ValueError):\n        return "?"\n    return f"Buy \u20b9{v:,.0f} Cr" if v >= 0 else f"Sell \u20b9{abs(v):,.0f} Cr"\n'
        s = s.replace(anchor, bsfn)
        changed.append("bs() added")
    for old, new in [
        ('f"FII: <b>{cr(fii)}</b>  |  DII: <b>{cr(dii)}</b>")', 'f"FII: <b>{bs(fii)}</b>  |  DII: <b>{bs(dii)}</b>")'),
        ("f\"FII: <b>{cr(f.get('FII/FPI'))}</b>  |  DII: <b>{cr(f.get('DII'))}</b>")", "f\"FII: <b>{bs(f.get('FII/FPI'))}</b>  |  DII: <b>{bs(f.get('DII'))}</b>")"),
    ]:
        if old in s and new not in s:
            s = s.replace(old, new)
            changed.append("buy/sell line")
    open(TB, "w", encoding="utf-8").write(s)
    open(SM, "w", encoding="utf-8").write(NEW_SM)
    print("telegram_brain.py:", ", ".join(changed) if changed else "already patched")
    print("send_macro.py rewritten (duplicate FII removed)")

if __name__ == "__main__":
    main()

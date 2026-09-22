#!/usr/bin/env python3
"""panchak.py - Manish ka panchak/amavasya calendar: TG reminder + market note."""
import os, datetime, urllib.request

# 2026 dates (Manish podcast se). Format: (start, end, type)
EVENTS = [
    ("2026-10-03", "2026-10-03", "Panchak"),
    ("2026-10-21", "2026-10-21", "Amavasya"),
    ("2026-11-20", "2026-11-20", "Amavasya"),
    ("2026-11-27", "2026-12-01", "Panchak"),
    ("2026-12-19", "2026-12-19", "Amavasya + Panchak (confusing day - sirf trap trading)"),
]

def send(tok, ids, msg):
    import json as j
    for cid in [x.strip() for x in ids.split(",") if x.strip()]:
        try:
            data = j.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
            req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage",
                                         data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20).read()
        except Exception as e:
            print("fail", cid, str(e)[:50])

def main():
    tok = os.environ.get("TG_TOKEN", "")
    ids = os.environ.get("TG_CHAT_ID", "")
    if not tok or not ids:
        print("no TG env"); return
    today = datetime.date.today()
    for start, end, typ in EVENTS:
        s = datetime.date.fromisoformat(start)
        e = datetime.date.fromisoformat(end)
        if today == s - datetime.timedelta(days=2):
            send(tok, ids, "*PANCHAK ALERT* \u26A0\n" + typ + " 2 din baad shuru: " + start +
                 "\nManish rule: correction aata hai (~75% win rate). Bottom par ho to up-correction, " +
                 "mid-range par fake breakout phir girna, top par ~500-pt fall.")
        elif s <= today <= e:
            day_n = (today - s).days + 1
            send(tok, ids, "*PANCHAK CALENDAR* \u26A0\nAaj " + typ + " hai (din " + str(day_n) + ")" +
                 ("" if today == e else ", " + end + " tak") +
                 "\nOption buyers sambhal ke. " +
                 "Price action + zones hi final, ye sirf pointer hai.")
    print("panchak check done", today.isoformat())

if __name__ == "__main__":
    main()

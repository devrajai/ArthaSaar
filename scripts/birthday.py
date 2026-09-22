#!/usr/bin/env python3
"""birthday.py - members.json se aaj ke birthday walo ko TG wish bhejo."""
import json, os, datetime, urllib.request

def send(tok, cid, msg):
    data = json.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage",
                                 data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()

def main():
    tok = os.environ.get("TG_TOKEN", "")
    if not tok:
        print("no TG_TOKEN"); return
    today = datetime.date.today().strftime("%d-%m")
    try:
        members = json.load(open("data/members.json"))
    except Exception:
        print("no members.json"); return
    for m in members:
        bd = (m.get("birthdate") or "").strip()
        if bd == today:
            name = m.get("name", "dost")
            try:
                send(tok, m["chat_id"],
                     "*HAPPY BIRTHDAY " + name.upper() + "!* \U0001F382\U0001F389\n"
                     "Market Brain family aapko bahut saari badhai deti hai!\n"
                     "Aapka naya saal full of profits aur green candles ho! \U0001F680\U0001F4B8")
                print("bday wish sent:", name)
            except Exception as e:
                print("fail", name, str(e)[:50])
    print("birthday check done for", today)

if __name__ == "__main__":
    main()

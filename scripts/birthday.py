#!/usr/bin/env python3
"""birthday.py - members.json se aaj ke birthday walo ko TG wish bhejo.
v2: 'joined' date se 'Market Brain member since X' line bhi wish mein."""
import json, os, datetime, urllib.request

def send(tok, cid, msg):
    data = json.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage",
                                 data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()

def member_since_line(joined):
    if not joined:
        return ""
    try:
        j = datetime.datetime.strptime(joined, "%d-%m-%Y").date()
    except ValueError:
        return ""
    days = (datetime.date.today() - j).days
    if days >= 365:
        return "\nMarket Brain member: " + str(days // 365) + " saal se!"
    if days >= 30:
        return "\nMarket Brain member: " + str(days // 30) + " mahine se!"
    if days >= 1:
        return "\nMarket Brain member: " + str(days) + " din se!"
    return ""

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
                     "Aapka naya saal full of profits aur green candles ho! \U0001F680\U0001F4B8"
                     + member_since_line(m.get("joined", "")))
                print("bday wish sent:", name)
            except Exception as e:
                print("fail", name, str(e)[:50])
    print("birthday check done for", today)

if __name__ == "__main__":
    main()

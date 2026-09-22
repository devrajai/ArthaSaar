#!/usr/bin/env python3
"""xray_tg.py - Night Brief: 10 PM IST TG message with GTI support/resistance + OI walls + SL levels.
Sends to ALL members (members.json chat_ids). Compact - one message per day."""
import json, os, urllib.request

TG = "https://api.telegram.org/bot{}/sendMessage"

def load(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def send(tok, chat, text):
    data = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(TG.format(tok), data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
        return True
    except Exception as e:
        print("send fail", chat, e)
        return False

def main():
    x = load("data/xray.json", {})
    oi = load("data/oi-gti.json", {}).get("symbols", {})
    gti = load("data/gti.json", {}).get("symbols", {})
    members = load("data/members.json", [])
    tok = os.environ.get("TG_TOKEN")
    if not tok:
        print("no token"); return

    nifty_oi = (oi.get("NIFTY 50") or {})
    nifty_g = None
    for k in ("NIFTY 50", "NIFTY", "^NSEI"):
        if k in gti:
            nifty_g = gti[k]; break
    sd = ((nifty_g or {}).get("day_zones") or {}).get("SD") or [None, None]
    near = (nifty_g or {}).get("nearest") or ["?", 0]

    put_w = nifty_oi.get("put_wall")
    call_w = nifty_oi.get("call_wall")
    spot = nifty_oi.get("spot") or (x.get("headline") or "").split()[-1]

    L = []
    L.append("NIGHT BRIEF - " + (x.get("date") or ""))
    L.append("NIFTY {} | {}".format(spot, (x.get("verdict") or "").split(" - ")[0]))
    L.append("")
    L.append("Kal ke Levels:")
    if put_w: L.append("Support 1: {} (Put wall)".format(put_w))
    if sd[0]: L.append("Support 2: {} (GTI SD zone)".format(round(sd[0])))
    if call_w: L.append("Resistance 1: {} (Call wall{})".format(call_w, ", Max pain" if nifty_oi.get("max_pain") == call_w else ""))
    if sd[1]: L.append("Resistance 2: {} (GTI SD zone upar)".format(round(sd[1])))
    L.append("GTI nearest: {} | Blood bath: {}".format(near[0], round(sd[0]) if sd[0] else "-"))
    L.append("")
    L.append("SL rule: level break hua to trade mat pakdo, SL strict rakhna.")
    msg = "\n".join(L)
    print(msg)

    chats = [m.get("chat_id") for m in members if m.get("chat_id")]
    extra = os.environ.get("TG_CHAT_ID")
    if extra and extra not in chats:
        chats.append(extra)
    ok = 0
    for c in chats:
        if send(tok, c, msg):
            ok += 1
    print("sent to", ok, "of", len(chats))

if __name__ == "__main__":
    main()

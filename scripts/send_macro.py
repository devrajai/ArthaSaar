#!/usr/bin/env python3
"""send_macro.py - Macro Pulse Telegram message to all members."""
import json, os, urllib.request

def main():
    with open("data/macro.json") as f:
        d = json.load(f)
    t = d.get("today", {})
    tok = os.environ.get("TG_TOKEN", "")
    ids = os.environ.get("TG_CHAT_ID", "")
    if not tok or not ids:
        print("no TG env, skip")
        return
    streak = d.get("streak_fii_sell_days", 0)
    msg = "*MACRO PULSE*\n" \
        + "Oil: $" + str(t.get("crude", "-")) + " | DXY: " + str(t.get("dxy", "-")) + "\n" \
        + "10Y: " + str(t.get("us10y", "-")) + "% | Rs: " + str(t.get("usdinr", "-")) + " | Gold: $" + str(t.get("gold", "-")) + "\n" \
        + "FII aaj: Rs " + str(t.get("fii_net_cr", "-")) + " cr" \
        + (" | FII " + str(streak) + " din se bech rahe" if streak >= 3 else "") + "\n\n" \
        + "Verdict (" + str(d.get("score", 0)) + "/10): " + d.get("verdict", "-")
    for cid in [x.strip() for x in ids.split(",") if x.strip()]:
        try:
            data = json.dumps({"chat_id": cid, "text": msg, "parse_mode": "Markdown"}).encode()
            req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage", data=data,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20).read()
        except Exception as e:
            print("send fail", cid, str(e)[:60])
    print("macro TG sent")

if __name__ == "__main__":
    main()

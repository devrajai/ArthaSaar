#!/usr/bin/env python3
"""test_send.py - new member verify: test message NAYE member + Dev dono ko (sabko nahi)."""
import os, json, urllib.request, urllib.parse
TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("TEST_CHAT_ID", "")
DEV = "1392604324"  # Dev ko hamesha test message jata hai
if not CHAT:
    print("TEST_CHAT_ID empty"); raise SystemExit(0)
msg = ("\U0001F9EA <b>ArthaSaar - Test Message</b>\n\n"
       "Ye test hai - agar ye dikh raha hai to aapke daily updates sahi aa rahe hain: "
       "8:30 AM Morning Brief, 9:15 AM IPO & Pre-open, hourly Alerts, "
       "4 PM Day Analysis Close, 9:15 PM Night Brief (news + stress + GTI zones + levels), "
       "Sunday Report Card.\n\n"
       "Bot: @ArthaSaarbot \U0001F44D")
for cid in dict.fromkeys([CHAT, DEV]):
    try:
        data = urllib.parse.urlencode({"chat_id": cid, "text": msg, "parse_mode": "HTML"}).encode()
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data), timeout=30).read())
        print("sent:", r.get("ok"), "to", cid)
    except Exception as e:
        print("send fail", cid, str(e)[:80])

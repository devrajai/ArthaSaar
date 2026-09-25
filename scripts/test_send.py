#!/usr/bin/env python3
"""test_send.py - new member verify: test message sirf EK chat ko (sabko nahi)."""
import os, json, urllib.request, urllib.parse
TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("TEST_CHAT_ID", "")
if not CHAT:
    print("TEST_CHAT_ID empty"); raise SystemExit(0)
msg = ("\U0001F9EA <b>ArthaSaar - Test Message</b>\n\n"
       "Ye test hai - agar ye dikh raha hai to aapke daily updates sahi aa rahe hain: "
       "7AM AI Brief, Market Open/Close, hourly Alerts, 9:10 PM Digest, Sunday Report Card, "
       "IPO digest.\n\n"
       "Bot: @DevArthaSaarbot \U0001F44D")
data = urllib.parse.urlencode({"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}).encode()
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    "https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data), timeout=30).read())
print("sent:", r.get("ok"), "to", CHAT)

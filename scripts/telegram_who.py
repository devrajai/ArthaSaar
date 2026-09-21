#!/usr/bin/env python3
"""
TELEGRAM WHO — lists the chat IDs of everyone who recently messaged the bot.

When someone opens the bot and taps START (or sends any message), run this
script (via the "Telegram Who" workflow on GitHub Actions) to see their
chat id, then add that id to the TG_CHAT_ID and/or TG_CHAT_ID_IPO secrets.

Usage: python3 scripts/telegram_who.py
"""
import json
import os
from urllib.request import Request, urlopen

TOKEN = os.environ.get("TG_TOKEN")
if not TOKEN:
    print("Missing TG_TOKEN")
    raise SystemExit(1)

req = Request("https://api.telegram.org/bot%s/getUpdates" % TOKEN,
              headers={"User-Agent": "telegram-who"})
with urlopen(req, timeout=25) as r:
    data = json.loads(r.read().decode())

seen = {}
for upd in data.get("result", []):
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat = msg.get("chat") or {}
    cid = chat.get("id")
    if cid is None:
        continue
    who = chat.get("first_name") or chat.get("title") or chat.get("username") or "?"
    seen[cid] = (who, chat.get("username"), chat.get("type"))

if not seen:
    print("No messages yet. Ask the person to open the bot and tap START, then run this again.")
else:
    print("People who messaged the bot:")
    for cid, (who, uname, typ) in seen.items():
        line = f"chat_id: {cid}  name: {who}  type: {typ}"
        if uname:
            line += f"  (@{uname})"
        print(line)

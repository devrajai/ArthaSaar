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
import re
from urllib.request import Request, urlopen

TOKEN = re.sub(r"\s+", "", os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "")
if not TOKEN:
    print("Missing TG_TOKEN")
    raise SystemExit(1)

req = Request("https://api.telegram.org/bot%s/getUpdates" % TOKEN,
              headers={"User-Agent": "telegram-who"})
with urlopen(req, timeout=25) as r:
    data = json.loads(r.read().decode())

# ---- diagnostics -------------------------------------------------------------------
# getUpdates returning nothing has two very different causes, and the plain message could
# not tell them apart: either nobody has messaged the bot, or a WEBHOOK is set, which makes
# Telegram refuse to hand messages to getUpdates at all. Print which bot the token belongs
# to as well, because "I sent hi" is usually "I sent it to a different bot".
def api(method):
    try:
        with urlopen(Request("https://api.telegram.org/bot%s/%s" % (TOKEN, method),
                             headers={"User-Agent": "telegram-who"}), timeout=25) as rr:
            return json.loads(rr.read().decode())
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:120])}

me = api("getMe")
if me.get("ok"):
    b_ = me["result"]
    print("Bot: @%s  (name: %s, id: %s)" % (b_.get("username"), b_.get("first_name"), b_.get("id")))
else:
    print("Could not read the bot identity:", me.get("error") or me.get("description"))

wh = api("getWebhookInfo")
if wh.get("ok"):
    info = wh["result"]
    url_ = info.get("url") or ""
    if url_:
        print("!! A WEBHOOK IS SET: %s" % url_)
        print("   While a webhook is set, getUpdates returns nothing. Delete it with:")
        print("   curl https://api.telegram.org/bot<TOKEN>/deleteWebhook")
        print("   pending_update_count: %s" % info.get("pending_update_count"))
    else:
        print("Webhook: none (getUpdates is the active method - good)")
        print("pending_update_count: %s" % info.get("pending_update_count"))

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

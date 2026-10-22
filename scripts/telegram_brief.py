#!/usr/bin/env python3
"""Post the daily brief to Telegram (Task 21b).

WHY THIS EXISTS
---------------
`morning_unified.py` was written against the OLD ArthaSaar data layout. It reads
data/mood.json, smart-brain.json, radar.json, gti.json, oi-gti.json, indices-all.json,
breadth.json, preopen.json and events.json. Nine of those ten do not exist in this repo,
and fetch_arthasaar_data.py fails SOFT when it cannot find them - so the morning brief
would have gone out nearly empty with no error anywhere.

Rather than pretend those files exist, this builds the morning message from the data this
repo actually produces: docs/brief.json, plus the index levels and the news headlines.

Missing secrets are a clean skip, never a crash.
"""
import json, os, sys, urllib.request, urllib.parse

TOKEN = os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or ""
CHATS = [c.strip() for c in (os.environ.get("TG_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").split(",") if c.strip()]
DRY = "--dry" in sys.argv


def jload(p):
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return None


def esc(s):
    """Real escaping. Telegram parses HTML, so a bare < or & drops the whole message."""
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build():
    brief = jload("docs/brief.json")
    idx = jload("docs/indices.json")
    data = jload("docs/data.json")
    lines = ["<b>ArthaSaar — morning brief</b>"]

    if brief and brief.get("headline"):
        lines.append("")
        lines.append("<b>%s</b>" % esc(brief["headline"]))
        for b in (brief.get("bullets") or []):
            lines.append("• " + esc(b))
    else:
        lines.append("")
        lines.append("No brief was generated. docs/brief.json is built by "
                     "scripts/build_daily_brief.py in the pipeline.")

    # a couple of index levels, if present
    if idx:
        want = {"nifty50": "NIFTY", "sensex": "SENSEX", "niftybank": "BANKNIFTY"}
        bits = []
        for x in (idx.get("indices") or []):
            if x.get("id") in want and x.get("level") and x.get("chg_pct") is not None:
                bits.append("%s %s (%s%.2f%%)" % (want[x["id"]], f"{x['level']:,.0f}",
                                                  "+" if x["chg_pct"] >= 0 else "", x["chg_pct"]))
        if bits:
            lines.append("")
            lines.append(" · ".join(bits))

    # two headlines, no more - the point is the summary, not a news dump
    if data and (data.get("news") or {}).get("rows"):
        cols = [str(c).strip().lower() for c in (data["news"].get("columns") or [])]
        ti = cols.index("title") if "title" in cols else 1   # NOT index 0: that is the source
        lines.append("")
        lines.append("<b>Headlines</b>")
        for r in data["news"]["rows"][:2]:
            try:
                lines.append("• " + esc(str(r[ti])[:130]))
            except Exception:
                continue

    lines.append("")
    lines.append("What moved, not why. Built from ArthaSaar's own data.")
    return "\n".join(lines)


def main():
    msg = build()
    print("brief length=%d chats=%d" % (len(msg), len(CHATS)))
    print(msg)
    if DRY:
        print("[dry run — not sent]")
        return 0
    if not TOKEN or not CHATS:
        # A clean skip. The workflow must not go red just because the owner has not added
        # the secrets yet - that is a configuration step, not a failure.
        print("TG_TOKEN / TG_CHAT_ID not set — skipping the send (this is not an error)")
        return 0
    sent = 0
    for chat in CHATS:
        try:
            payload = urllib.parse.urlencode({
                "chat_id": chat, "text": msg,
                "parse_mode": "HTML", "disable_web_page_preview": "true",
            }).encode()
            req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=payload)
            r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
            print("sent to %s: %s" % (chat, r.get("ok")))
            sent += 1
        except Exception as e:
            print("send fail %s: %s" % (chat, str(e)[:90]))
    return 0 if sent or not CHATS else 1


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)

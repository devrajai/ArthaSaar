#!/usr/bin/env python3
"""Read a public Telegram channel's web preview and pull PCR numbers out of it.

HOW THIS WORKS, AND WHY IT NEEDS NO API KEY
Telegram publishes a plain HTML preview of every PUBLIC channel at https://t.me/s/<name>.
It needs no login, no bot token, no phone number and no API credentials - it is the same page
a logged-out browser sees. That makes it the only clean way to read a channel you do not own.

A BOT CANNOT DO THIS. The Bot API only delivers messages from channels the bot has been added
to as an admin. A user-account library like Telethon could read any public channel, but it
needs your phone number and a login session, which is not something to put in a CI job.

WHAT IT DOES NOT DO
It does not verify the numbers. A channel is somebody's post, not an exchange feed. Every
value is stored with the channel name and the message text it came from, and it is presented
as a third-party claim - never mixed into the PCR computed from NSE's own bhavcopy.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/telegram_pcr.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}

# How a channel might phrase it. Deliberately loose, but every hit is kept with its source
# text so a wrong parse is visible rather than silent.
PATTERNS = [
    r"pcr[^0-9]{0,18}(\d{1,2}\.\d{1,2})",
    r"put\s*call\s*ratio[^0-9]{0,18}(\d{1,2}\.\d{1,2})",
    r"p\s*/\s*c\s*ratio[^0-9]{0,18}(\d{1,2}\.\d{1,2})",
]
# A channel that posts option data usually posts max pain too. Same rule applies: the
# number is stored with the sentence it came from, never on its own.
MAXPAIN = [
    r"max\s*pain[^0-9]{0,20}(\d{4,6})",
    r"maxpain[^0-9]{0,20}(\d{4,6})",
]

# SEBI's social-media requirement, carried with the data so the card cannot show a
# third-party claim without it.
DISCLAIMER = ("ALL CHARTS & DATA SHARED HERE ARE ONLY WITH THE MOTIVE OF EDUCATIONAL PURPOSE. "
              "IT'S NOT A RECOMMENDATION OR CALL. CONSULT YOUR FINANCIAL ADVISOR BEFORE TAKING "
              "ANY POSITION")


def channels():
    raw = os.environ.get("TELEGRAM_CHANNELS", "").strip()
    if raw:
        return [c.strip().lstrip("@") for c in raw.split(",") if c.strip()]
    try:
        cfg = json.load(open("docs/config.json"))
        return [c.strip().lstrip("@") for c in (cfg.get("telegram_channels") or []) if c.strip()]
    except Exception:
        return []


def fetch(handle):
    url = "https://t.me/s/%s" % handle
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def messages(html):
    """Message bodies in page order, oldest first, as plain text."""
    out = []
    for block in re.findall(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S):
        txt = re.sub(r"<br\s*/?>", "\n", block)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = (txt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
        txt = re.sub(r"[ \t]+", " ", txt).strip()
        if txt:
            out.append(txt)
    return out


def find_max_pain(text):
    for pat in MAXPAIN:
        m = re.search(pat, text, re.I)
        if m:
            try:
                v = float(m.group(1))
            except Exception:
                continue
            if 1000 <= v <= 100000:
                return v
    return None


def find_pcr(text):
    for pat in PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            try:
                v = float(m.group(1))
            except Exception:
                continue
            if 0.05 <= v <= 20:          # a plausible put/call ratio
                return v
    return None


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "channels": {}, "note": ""}

    chans = channels()
    if not chans:
        out["note"] = ("No channel configured. Set TELEGRAM_CHANNELS (comma separated, without "
                       "the @) or add \"telegram_channels\" to docs/config.json.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("telegram: no channel configured")
        return 0

    for ch in chans:
        try:
            html = fetch(ch)
        except Exception as e:
            print("  %-28s unreachable (%s)" % (ch, type(e).__name__))
            out["channels"][ch] = {"error": type(e).__name__, "readings": []}
            continue

        msgs = messages(html)
        readings = []
        pains = []
        for m in msgs:
            v = find_pcr(m)
            if v is not None:
                readings.append({"pcr": v, "text": m[:280]})
            mp = find_max_pain(m)
            if mp is not None:
                pains.append({"max_pain": mp, "text": m[:280]})
        # newest last in the page, so reverse for newest-first
        readings = readings[::-1]
        pains = pains[::-1]
        print("  %-28s %d messages, %d with a PCR" % (ch, len(msgs), len(readings)))
        out["channels"][ch] = {
            "latest": readings[0]["pcr"] if readings else None,
            "latest_text": readings[0]["text"] if readings else None,
            "readings": readings[:20],
            "max_pain": pains[0]["max_pain"] if pains else None,
            "max_pain_text": pains[0]["text"] if pains else None,
            "messages_seen": len(msgs),
            # The first run against a new channel tells you what it actually posts. Three
            # raw posts, trimmed, so the extraction can be tuned to the channel instead of
            # guessed at.
            "sample": [m[:200] for m in msgs[-3:]],
        }

    out["disclaimer"] = DISCLAIMER
    out["count"] = sum(1 for c in out["channels"].values() if c.get("latest") is not None)
    out["note"] = ("PCR and max pain as posted by public Telegram channels, read from Telegram's own web "
                   "preview. This is somebody's post, not an exchange feed, and it is not "
                   "verified - it is kept separate from the PCR computed from NSE bhavcopy.")
    out["cautions"] = {
        "third_party": "A channel post, not an exchange number. Shown as a claim, not a fact.",
        "method": ("Put-call ratio can mean OI-based or volume-based; channels rarely say "
                   "which, so two numbers labelled PCR may not be comparable."),
        "not_advice": "Included for reference only.",
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB  |  %d channel(s) with a reading"
          % (OUT, os.path.getsize(OUT) / 1024, out["count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Collect messages from PUBLIC Telegram channels. No bot token, no phone number.

HOW THIS WORKS
Telegram publishes a plain HTML preview of every public channel at https://t.me/s/<name>.
It needs no login and no credentials - it is the same page a logged-out browser sees. That
makes it the only clean way to read a channel you do not own.

WHY NOT A BOT
The Bot API only delivers messages from channels the bot has been added to as an admin. A
user-account library like Telethon could read any public channel, but it needs a phone number
and a login session, which should never sit in a CI job.

THE ONE HARD REQUIREMENT
The channel owner must have "Show a preview of posts on the web" enabled in the channel
settings. Without it, t.me/s/<name> serves a landing page with no messages, and there is no
way around that from outside. The collector detects this case and says so per channel rather
than silently recording zero.

WHAT IT STORES
data/telegram/messages.parquet - append-only, de-duplicated on (channel, msg_id), so running
it twice never duplicates a message and a partial run is safe to repeat.

docs/telegram.json - a small summary for the site: per channel, how many messages, the latest
post date, and the most recent messages. The full archive stays out of the repo.

WHAT IT DOES NOT DO
It does not judge the content. A channel is somebody's post, not an exchange feed. Every row
keeps the channel name and the exact text so a claim can always be traced to who said it.
"""
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
ARCHIVE = "data/telegram/messages.parquet"
OUT = "docs/telegram.json"
MAX_MESSAGES_PER_CHANNEL = 200


def configured_channels():
    raw = os.environ.get("TELEGRAM_CHANNELS", "").strip()
    if raw:
        return [c.strip().lstrip("@") for c in raw.split(",") if c.strip()]
    for path in ("docs/config.json", "config/telegram_channels.json"):
        try:
            cfg = json.load(open(path))
            chans = cfg.get("telegram_channels") or cfg.get("channels") or []
            out = []
            for c in chans:
                if isinstance(c, dict):
                    h = c.get("handle") or c.get("name")
                    if h and c.get("active", True):
                        out.append(str(h).lstrip("@"))
                elif c:
                    out.append(str(c).lstrip("@"))
            if out:
                return out
        except Exception:
            continue
    return []


def fetch(handle, timeout=45, retries=3):
    url = "https://t.me/s/%s" % handle
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "channel not found (404)"
            last = "HTTP %s" % e.code
        except Exception as e:
            last = type(e).__name__
        time.sleep(attempt * 2)
    return None, last or "unreachable"


def clean(fragment):
    """HTML fragment -> plain text, keeping line breaks."""
    txt = re.sub(r"<br\s*/?>", "\n", fragment)
    txt = re.sub(r"</?a\b[^>]*>", "", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    return htmllib.unescape(txt).strip()


def parse(html, handle):
    """Messages in page order (oldest first), plus a flag for the no-preview case."""
    # each message is a div carrying data-post="channel/123"
    blocks = re.findall(
        r'<div class="tgme_widget_message[^"]*"[^>]*data-post="([^"]+)"[\s\S]*?(?=<div class="tgme_widget_message[^"]*"[^>]*data-post=|\Z)',
        html)
    if not blocks:
        # no data-post attribute at all -> either no preview or an empty page
        preview = "tgme_widget_message" in html
        return [], (not preview)

    out = []
    # re-split keeping the whole block this time
    parts = re.split(r'(?=<div class="tgme_widget_message[^"]*"[^>]*data-post=)', html)
    for part in parts:
        m = re.search(r'data-post="([^"]+)"', part)
        if not m:
            continue
        post = m.group(1)
        try:
            chan, msg_id = post.rsplit("/", 1)
            msg_id = int(msg_id)
        except Exception:
            continue

        dt = None
        t = re.search(r'<time[^>]*datetime="([^"]+)"', part)
        if t:
            dt = t.group(1)

        body = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)</div>', part)
        text = clean(body.group(1)) if body else ""

        views = None
        v = re.search(r'class="tgme_widget_message_views"[^>]*>([^<]+)<', part)
        if v:
            raw = v.group(1).strip().upper().replace(",", "")
            try:
                if raw.endswith("K"):
                    views = int(float(raw[:-1]) * 1000)
                elif raw.endswith("M"):
                    views = int(float(raw[:-1]) * 1_000_000)
                else:
                    views = int(float(raw))
            except Exception:
                views = None

        links = re.findall(r'href="(https?://[^"]+)"', part)
        links = [l for l in links if "t.me" not in l][:5]

        if not text and views is None:
            continue
        out.append({"channel": handle, "msg_id": msg_id, "datetime": dt,
                    "text": text, "views": views, "links": links})

    return out, False


def load_existing():
    try:
        import pandas as pd
        if os.path.exists(ARCHIVE):
            return pd.read_parquet(ARCHIVE)
    except Exception:
        pass
    return None


def main():
    summary = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": 0, "channels": [], "note": ""}

    chans = configured_channels()
    if not chans:
        summary["note"] = ("No channel configured. Set TELEGRAM_CHANNELS (comma separated, no "
                           "@) or add \"telegram_channels\" to docs/config.json.")
        os.makedirs("docs", exist_ok=True)
        json.dump(summary, open(OUT, "w"), ensure_ascii=False)
        print("telegram: no channel configured")
        return 0

    print("channels: %s" % ", ".join(chans))
    rows, problems = [], []
    for handle in chans:
        html, err = fetch(handle)
        if html is None:
            problems.append({"channel": handle, "problem": err})
            print("  %-24s FAILED  %s" % (handle, err))
            continue
        msgs, no_preview = parse(html, handle)
        if no_preview:
            problems.append({"channel": handle,
                             "problem": "no web preview - the channel owner must enable "
                                        "\"Show a preview of posts on the web\""})
            print("  %-24s NO PREVIEW" % handle)
            continue
        msgs = msgs[-MAX_MESSAGES_PER_CHANNEL:]
        rows.extend(msgs)
        latest = max((m["datetime"] for m in msgs if m["datetime"]), default=None)
        print("  %-24s %3d messages  latest %s" % (handle, len(msgs), (latest or "-")[:19]))
        summary["channels"].append({
            "channel": handle,
            "messages": len(msgs),
            "latest": latest,
            "recent": [{"date": m["datetime"], "text": m["text"][:400], "views": m["views"]}
                       for m in sorted(msgs, key=lambda x: (x["datetime"] or ""))[-8:]],
        })

    if rows:
        import pandas as pd
        new = pd.DataFrame(rows)
        old = load_existing()
        if old is not None and len(old):
            both = pd.concat([old, new], ignore_index=True)
            before = len(both)
            both = both.drop_duplicates(subset=["channel", "msg_id"], keep="last")
            print("\nmerge: %d existing + %d new -> %d after de-dup"
                  % (len(old), len(new), len(both)))
        else:
            both = new
            print("\nnew archive: %d rows" % len(both))
        os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
        both.to_parquet(ARCHIVE, index=False)
        summary["count"] = int(len(both))
        print("-> %s  %.2f MB" % (ARCHIVE, os.path.getsize(ARCHIVE) / 1e6))

    if problems:
        summary["problems"] = problems
    summary["note"] = ("Public channel messages read from Telegram's own web preview - no bot "
                       "token and no login. A channel is somebody's post, not an exchange feed: "
                       "every message is kept with the channel it came from so a claim can be "
                       "traced to who said it.")
    os.makedirs("docs", exist_ok=True)
    json.dump(summary, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %d KB  |  %d messages across %d channels"
          % (OUT, os.path.getsize(OUT) / 1024, summary["count"], len(summary["channels"])))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("::warning title=Telegram collection failed::%s: %s"
              % (type(e).__name__, str(e)[:120]))
        sys.exit(0)

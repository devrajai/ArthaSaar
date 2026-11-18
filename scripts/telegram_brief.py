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
import json, os, re, sys, urllib.request, urllib.parse
import datetime as dt

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# Overnight context. Free, keyless, and the thing a reader actually wants at 08:30.
OVERNIGHT = [("S&P 500", "^GSPC"), ("Brent", "BZ=F"), ("USD/INR", "INR=X")]

# A brief whose market_date is older than this is not "morning news", it is history.
MAX_STALE_DAYS = 4

TOKEN = re.sub(r"\s+", "", os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "")
CHATS = [c.strip() for c in (os.environ.get("TG_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip().split(",") if c.strip()]
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


def _overnight():
    """Last close and % change for the three things an Indian reader checks first."""
    out = []
    for name, sym in OVERNIGHT:
        try:
            u = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d"
                 % urllib.parse.quote(sym))
            d = json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read())
            r = d["chart"]["result"][0]
            m = r["meta"]
            cl = [c for c in ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [] if c]
            px = m.get("regularMarketPrice")
            pc = cl[-2] if len(cl) >= 2 else m.get("chartPreviousClose")
            if px and pc:
                out.append((name, px, (px / pc - 1.0) * 100.0))
        except Exception:
            continue
    return out


def _next_expiry():
    """The next expiry that has NOT already passed.

    The chain file is dated, so its nearest expiry can be one that settled yesterday. Saying
    "0 days away" about a date in the past is the same class of error as the stale close.
    """
    d = jload("docs/oi_by_expiry.json") or {}
    nif = ((d.get("indices") or {}).get("NIFTY")) or {}
    today = dt.datetime.now(IST).strftime("%Y-%m-%d")
    best = None
    for e in (nif.get("expiries") or []):
        exp = str(e.get("expiry") or "")
        if not exp or exp < today:
            continue
        dte = e.get("days_out")
        if dte is None:
            continue
        if best is None or dte < best[0]:
            best = (dte, exp)
    return best


def _plain_words(brief):
    """One sentence a beginner can read. No jargon, no direction call."""
    try:
        h = str(brief.get("headline") or "")
        m = re.search(r"([+-]?\d+(?:\.\d+)?)%", h)
        pct = float(m.group(1)) if m else None
        bullets = " ".join(str(b) for b in (brief.get("bullets") or [])).lower()
        adv = re.search(r"advances\s+(\d+)\s+to\s+(\d+)", bullets)
        if pct is None:
            return None
        if pct > 0.3:
            move = "rose"
        elif pct < -0.3:
            move = "fell"
        else:
            move = "barely moved"
        s2 = "The index %s %s." % (move, ("%.2f%%" % abs(pct)))
        if adv:
            a, d2 = int(adv.group(1)), int(adv.group(2))
            s2 += (" More stocks rose than fell (%d to %d)." % (a, d2) if a > d2
                   else " More stocks fell than rose (%d to %d)." % (a, d2))
        return s2
    except Exception:
        return None


def build():
    brief = jload("docs/brief.json")
    idx = jload("docs/indices.json")
    data = jload("docs/data.json")
    now = dt.datetime.now(IST)

    # THE SESSION THE FIGURES COME FROM, in the title. The old message said "morning brief"
    # with no date and was once sent at 22:39 quoting a close two sessions old.
    mdate = (brief or {}).get("market_date") or (brief or {}).get("as_of")
    title = "ArthaSaar — morning brief"
    if mdate:
        try:
            d0 = dt.datetime.strptime(str(mdate)[:10], "%Y-%m-%d").date()
            age = (now.date() - d0).days
            title += " · %s" % d0.strftime("%a %d %b %Y")
        except Exception:
            age = None
    else:
        age = None

    lines = ["<b>%s</b>" % esc(title)]
    lines.append("<i>Market data and descriptions only. Not investment advice.</i>")

    if age is not None and age > MAX_STALE_DAYS:
        lines.append("")
        lines.append("<b>Not sending a market summary.</b> The newest brief is %d days old "
                     "(%s). A stale close presented as today's is worse than no message."
                     % (age, esc(str(mdate)[:10])))
        lines.append("")
        lines.append("<i>Data health: docs/brief.json dated %s, stale flag = %s.</i>"
                     % (esc(str(mdate)[:10]), esc(str((brief or {}).get("stale")))))
        return "\n".join(lines)

    if brief and brief.get("headline"):
        lines.append("")
        lines.append("<b>%s</b>" % esc(brief["headline"]))
        for b in (brief.get("bullets") or []):
            lines.append("• " + esc(b))
        plain = _plain_words(brief)
        if plain:
            lines.append("")
            lines.append("<b>In plain words:</b> " + esc(plain))
    else:
        lines.append("")
        lines.append("No brief was generated. docs/brief.json is built by "
                     "scripts/build_daily_brief.py in the pipeline.")

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

    # next expiry - the single most useful forward-looking fact for an options reader
    nx = _next_expiry()
    if nx:
        lines.append("")
        lines.append("Next Nifty expiry: <b>%s</b> · %d day(s) away" % (esc(str(nx[1])), nx[0]))

    ov = _overnight()
    if ov:
        lines.append("")
        lines.append("<b>Overnight</b> (last close)")
        for nm, px, ch in ov:
            lines.append("%s %s (%+.2f%%)" % (esc(nm), f"{px:,.2f}", ch))

    if data and (data.get("news") or {}).get("rows"):
        cols = [str(c).strip().lower() for c in (data["news"].get("columns") or [])]
        ti = cols.index("title") if "title" in cols else 1
        lines.append("")
        lines.append("<b>Headlines</b>")
        for r in data["news"]["rows"][:2]:
            try:
                lines.append("• " + esc(str(r[ti])[:130]))
            except Exception:
                continue

    # a data-health line on every message, so a reader can see what they are reading
    health = []
    health.append("session %s" % (esc(str(mdate)[:10]) if mdate else "unknown"))
    if (brief or {}).get("stale"):
        health.append("brief flagged stale")
    health.append("sent %s IST" % now.strftime("%d %b %H:%M"))
    lines.append("")
    lines.append("<i>Data health: %s.</i>" % ", ".join(health))
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

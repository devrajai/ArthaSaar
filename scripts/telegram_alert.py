#!/usr/bin/env python3
"""telegram_alert.py — daily open/close summary to Dev's Telegram (free Bot API).
Reads data/*.json collected by other workflows + live Yahoo quotes,
sends one compact HTML message. Mode auto-detected from IST hour (>=15 -> close)."""
import json, os, sys, urllib.request, urllib.parse, datetime as dt

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = os.environ.get("TG_CHAT_ID", "")
DRY = os.environ.get("TG_DRY") == "1"
mode = sys.argv[1] if len(sys.argv) > 1 else None

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
now = dt.datetime.now(IST)
if not mode:
    mode = "close" if now.hour >= 15 else "open"


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}


def http_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))
    except Exception:
        return None


def yahoo(sym):
    d = http_json("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d" % sym)
    try:
        m = d["chart"]["result"][0]["meta"]
        return m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")
    except Exception:
        return None, None


def esc(s):
    return str(s).replace("&", "&").replace("<", "<").replace(">", ">")


def pct(p, pc):
    if p and pc:
        return (p / pc - 1) * 100.0
    return None


nifty, npc = yahoo("%5ENSEI")
sensex, spc = yahoo("%5EBSESN")
sb = jload("data/smart-brain.json")
br = jload("data/breadth.json")
fd = jload("data/fii-dii.json")
mt = jload("data/mf-top.json")

L = []
if mode == "open":
    L.append("\U0001F305 <b>Market Brain — Good Morning</b>")
else:
    L.append("\U0001F306 <b>Market Brain — Market Close</b>")
L.append(esc(now.strftime("%A, %d %b %Y")))
L.append("")

row = []
if nifty:
    c = pct(nifty, npc)
    row.append("NIFTY %s (%s%.2f%%)" % ("{:,.0f}".format(nifty), "+" if (c or 0) >= 0 else "", c or 0))
if sensex:
    c = pct(sensex, spc)
    row.append("SENSEX %s (%s%.2f%%)" % ("{:,.0f}".format(sensex), "+" if (c or 0) >= 0 else "", c or 0))
if row:
    L.append(" | ".join(row))

g = (sb.get("guess") or {})
if g:
    L.append("")
    L.append("\U0001F9E0 <b>Smart Brain: %s (%s/100)</b>" % (esc(g.get("verdict") or "—"), g.get("score")))
    for p in (g.get("points") or [])[:3]:
        L.append("• " + esc(p))

if br:
    L.append("")
    L.append("\U0001F4C8 Breadth: %s%% stocks EMA200 ke upar" % br.get("above_ema200_pct", "—"))
if fd:
    cats = fd.get("categories") or {}
    fii = (cats.get("FII/FPI") or {}).get("net_cr")
    dii = (cats.get("DII") or {}).get("net_cr")
    if fii is not None or dii is not None:
        L.append("\U0001F4B8 FII %s Cr | DII %s Cr" % (
            ("%+.0f" % fii) if fii is not None else "—",
            ("%+.0f" % dii) if dii is not None else "—"))

bench = (mt.get("bench") or {})
gold = (bench.get("gold") or {}).get("r1")
silver = (bench.get("silver") or {}).get("r1")
if gold is not None or silver is not None:
    L.append("\U0001F3C6 Gold 1Y %s | Silver 1Y %s" % (
        ("%+.1f%%" % gold) if gold is not None else "—",
        ("%+.1f%%" % silver) if silver is not None else "—"))

bull = (sb.get("bull") or [])[:3]
bear = (sb.get("bear") or [])[:3]
if bull:
    L.append("")
    L.append("\U0001F42C <b>Bull:</b> " + " · ".join("%s %s" % (esc(b.get("symbol")), b.get("score")) for b in bull))
if bear:
    L.append("\U0001F428 <b>Bear:</b> " + " · ".join("%s %s" % (esc(b.get("symbol")), b.get("score")) for b in bear))

L.append("")
L.append('<a href="https://devrajai.github.io/market-brain/">\U0001F4A5 poora terminal yahan</a>')

msg = "\n".join(L)
print("mode=%s len=%d" % (mode, len(msg)))
print(msg)

if DRY:
    print("[dry run — not sent]")
    sys.exit(0)

if not TOKEN or not CHAT:
    print("TG_TOKEN / TG_CHAT_ID missing")
    sys.exit(1)

data = urllib.parse.urlencode({
    "chat_id": CHAT,
    "text": msg,
    "parse_mode": "HTML",
    "disable_web_page_preview": "true",
}).encode()
req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data)
r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
print("sent:", r.get("ok"), r.get("result", {}).get("message_id"))

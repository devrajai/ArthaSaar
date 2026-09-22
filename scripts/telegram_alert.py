#!/usr/bin/env python3
"""telegram_alert.py v2 — morning (9:20 IST) open + evening (16:00 IST) close summaries.
Live Nifty/Sensex + live F&O stock movers (Yahoo) + OI build-up (futures.json) +
volume movers (brain-screener.json) + Smart Brain + breadth + FII/DII + gold/silver.
Supports multiple chat ids in TG_CHAT_ID (comma-separated)."""
import json, os, sys, time, urllib.request, urllib.parse, datetime as dt

TOKEN = os.environ.get("TG_TOKEN", "")
CHATS = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
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

def sgn(v):
    return "+" if v >= 0 else ""

sb = jload("data/smart-brain.json")
br = jload("data/breadth.json")
fd = jload("data/fii-dii.json")
mt = jload("data/mf-top.json")
fu = jload("data/futures.json")
sc = jload("data/brain-screener.json")

# ---- live quotes: indices ----
nifty, npc = yahoo("%5ENSEI")
sensex, spc = yahoo("%5EBSESN")

# ---- live movers: top F&O stocks by OI (max 22) ----
fst = (fu.get("stocks") or [])
top_oi = sorted(fst, key=lambda s: -(s.get("oi") or 0))[:22]
movers = []
for s in top_oi:
    p, pc2 = yahoo(s["symbol"] + ".NS")
    c = pct(p, pc2)
    if c is not None:
        movers.append((s["symbol"], c, s.get("oi_chg")))
    time.sleep(0.15)
movers.sort(key=lambda x: -x[1])
up = movers[:5]
dn = sorted(movers, key=lambda x: x[1])[:5]

# ---- volume movers from screener (EOD) ----
vols = sorted((sc.get("stocks") or []), key=lambda s: -(s.get("vol_vs_avg20") or 0) * (1 if (s.get("change_pct") or 0) > 0 else 0))[:4]

# ---- OI build-up (relative % change) ----
def oi_pct(s):
    oi, ch = s.get("oi") or 0, s.get("oi_chg") or 0
    base = oi - ch
    if base <= 0 or ch == 0:
        return 0.0
    return ch / base * 100.0

oi_up = [s for s in fst if (s.get("oi_chg") or 0) != 0]
oi_up.sort(key=lambda s: -abs(oi_pct(s)))
oi_up = oi_up[:4]
pcr = fu.get("pcr") or {}

L = []
if mode == "open":
    L.append("\U0001F305 <b>Market Brain — Market Open</b>")
else:
    L.append("\U0001F306 <b>Market Brain — Market Close</b>")
L.append(esc(now.strftime("%A, %d %b %Y")))
L.append("")

row = []
if nifty:
    c = pct(nifty, npc)
    row.append("NIFTY %s (%s%.2f%%)" % ("{:,.0f}".format(nifty), sgn(c or 0), c or 0))
if sensex:
    c = pct(sensex, spc)
    row.append("SENSEX %s (%s%.2f%%)" % ("{:,.0f}".format(sensex), sgn(c or 0), c or 0))
if row:
    L.append(" | ".join(row))
if pcr.get("nifty_pcr_oi") is not None:
    L.append("\U0001F3AF Nifty PCR %s | Max Pain %s" % (pcr.get("nifty_pcr_oi"), pcr.get("nifty_max_pain")))

if up:
    L.append("")
    L.append("\U0001F534 <b>Top movers (live F&O):</b>")
    L.append("\u25B2 " + " \u00b7 ".join("%s %s%.1f%%" % (m[0], sgn(m[1]), m[1]) for m in up))
    L.append("\u25BC " + " \u00b7 ".join("%s %s%.1f%%" % (m[0], sgn(m[1]), m[1]) for m in dn))

if oi_up:
    L.append("")
    L.append("\U0001F4E6 <b>OI build-up:</b> " + " \u00b7 ".join("%s %s%.1f%%" % (o["symbol"], sgn(oi_pct(o)), oi_pct(o)) for o in oi_up))

if vols:
    L.append("\U0001F4C9 <b>Volume garam:</b> " + " \u00b7 ".join("%s %s%.0f%% (%.1fx vol)" % (v["symbol"], sgn(v.get("change_pct") or 0), v.get("change_pct") or 0, v.get("vol_vs_avg20") or 0) for v in vols))

g = (sb.get("guess") or {})
if g:
    L.append("")
    L.append("\U0001F9E0 <b>Smart Brain: %s (%s/100)</b>" % (esc(g.get("verdict") or "—"), g.get("score")))
    for p in (g.get("points") or [])[:2]:
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
    L.append("\U0001F42C <b>Bull:</b> " + " \u00b7 ".join("%s %s" % (esc(b.get("symbol")), b.get("score")) for b in bull))
if bear:
    L.append("\U0001F428 <b>Bear:</b> " + " \u00b7 ".join("%s %s" % (esc(b.get("symbol")), b.get("score")) for b in bear))

L.append("")

msg = "\n".join(L)
print("mode=%s len=%d chats=%d" % (mode, len(msg), len(CHATS)))
print(msg)

if DRY:
    print("[dry run — not sent]")
    sys.exit(0)

if not TOKEN or not CHATS:
    print("TG_TOKEN / TG_CHAT_ID missing")
    sys.exit(1)

for chat in CHATS:
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data)
        r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        print("sent to %s: %s" % (chat, r.get("ok")))
    except Exception as e:
        print("send fail %s: %s" % (chat, str(e)[:80]))

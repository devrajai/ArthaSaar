#!/usr/bin/env python3
"""telegram_alert.py v2 — morning (9:20 IST) open + evening (16:00 IST) close summaries.
Live Nifty/Sensex + live F&O stock movers (Yahoo) + OI build-up (futures.json) +
volume movers (brain-screener.json) + Smart Brain + breadth + FII/DII + gold/silver.
Supports multiple chat ids in TG_CHAT_ID (comma-separated).
"""
import json, os, re, sys, time, urllib.request, urllib.parse, datetime as dt
import re

TOKEN = re.sub(r"\s+", "", os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "")
CHATS = [c.strip() for c in (os.environ.get("TG_CHAT_ID") or "").strip().split(",") if c.strip()]
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
        r = d["chart"]["result"][0]
        m = r["meta"]
        # FIX: chartPreviousClose = 5-din-purana close (galat). Last bar ka prev = dusra-aakhri bar.
        closes = [c for c in ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [] if c]
        pc = closes[-2] if len(closes) >= 2 else (m.get("chartPreviousClose") or m.get("previousClose"))
        return (m.get("regularMarketPrice"), pc,
                m.get("regularMarketDayHigh"), m.get("regularMarketDayLow"))
    except Exception:
        return None, None, None, None

def esc(s):
    # These were HTML entities that had been decoded, so each replace() was a no-op:
    # "&" -> "&", "<" -> "<". Any symbol or headline containing <, > or & therefore broke
    # Telegram's HTML parse mode and the alert was dropped with no error anywhere.
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def pct(p, pc):
    if p and pc:
        return (p / pc - 1) * 100.0
    return None

def sgn(v):
    return "+" if v >= 0 else ""

# THESE READ THE OLD LAYOUT. Every one of these paths was data/*.json, from a previous
# codebase; this repository publishes to docs/*.json. So six reads failed on every run,
# eleven "MISSING" lines printed, and the evening message went out with whatever survived -
# live Yahoo quotes and a PCR figure. The workflow was green the whole time.
#
# Remapped to what this repo actually publishes. data.json already carries the futures open
# interest, the put-call ratio and FII/DII in one file, so most of it comes from there.
_d = jload("docs/data.json") or {}
_fno = (_d.get("fno") or {})
sb = (_d.get("brain") or {})
br = jload("docs/breadth.json") or {}
fd = (_d.get("fii_dii") or {})
mt = jload("docs/mf.json") or {}
fu = {"stocks": _fno.get("top_oi") or [], "pcr": _fno.get("pcr") or {}}
sc = jload("docs/screener.json") or {}
if not _d:
    print("docs/data.json missing - the evening message will be thin")

# ---- live quotes: indices ----
nifty, npc, nhi, nlo = yahoo("%5ENSEI")
sensex, spc, shi, slo = yahoo("%5EBSESN")

# ---- live movers: top F&O stocks by OI (max 22) ----
fst = (fu.get("stocks") or [])
top_oi = sorted(fst, key=lambda s: -(s.get("oi") or 0))[:22]
movers = []
for s in top_oi:
    p, pc2, _, _ = yahoo(s["symbol"] + ".NS")
    c = pct(p, pc2)
    if c is not None:
        movers.append((s["symbol"], c, s.get("oi_chg")))
    time.sleep(0.15)
movers.sort(key=lambda x: -x[1])
up = [m for m in movers if m[1] > 0][:5]   # only real gains
dn = sorted([m for m in movers if m[1] < 0], key=lambda x: x[1])[:5]   # only real falls

# ---- volume movers from screener (EOD) ----
# No volume-vs-average column exists in this repo's screener.json, so this used to emit four
# rows of "+0% (0.0x vol)". Only keep stocks that actually carry a ratio above zero.
vols = [x for x in (sc.get("rows") or [])
        if (x.get("vol_vs_avg20") or 0) > 0 and (x.get("change_pct") or 0) > 0]
vols.sort(key=lambda x: -(x.get("vol_vs_avg20") or 0))
vols = vols[:4]

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

# ---- sector scoreboard (live, close mode) ----
SECTORS = [("IT", "%5ECNXIT"), ("BANK", "%5ENSEBANK"), ("AUTO", "%5ECNXAUTO"),
           ("PHARMA", "%5ECNXPHARMA"), ("FMCG", "%5ECNXFMCG"), ("METAL", "%5ECNXMETAL"),
           ("REALTY", "%5ECNXREALTY"), ("ENERGY", "%5ECNXENERGY")]
sec_rows = []
for lbl, sy in SECTORS:
    p2, c2, _, _ = yahoo(sy)
    ch = pct(p2, c2)
    if ch is not None:
        sec_rows.append((lbl, ch))
    time.sleep(0.12)
sec_rows.sort(key=lambda r: -r[1])

# ---- FII/DII today (cash, live from NSE; fallback file) ----
fii_today = dii_today = None
live = http_json("https://www.nseindia.com/api/fiidiiTradeReact")
if isinstance(live, list) and not live:
    live = None
if isinstance(live, list) and fii_today == 0 and dii_today == 0:
    fii_today = dii_today = None
if isinstance(live, list):
    for r in live:
        try:
            if r.get("category") == "FII/FPI":
                fii_today = float(r.get("netValue", 0)) / 1e7
            elif r.get("category") == "DII":
                dii_today = float(r.get("netValue", 0)) / 1e7
        except Exception:
            pass

L = []
if mode == "open":
    L.append("\U0001F305 <b>ArthaSaar — Market Open</b>")
else:
    L.append("\U0001F4CA <b>ArthaSaar — Day Analysis Close</b>")
L.append(esc(now.strftime("%A, %d %b %Y")))
L.append("")
if mode != "open":
    L.append("\U0001F3AF Close (15:30 IST)")

row = []
if nifty:
    c = pct(nifty, npc)
    p = (nifty - npc) if npc else None
    row.append("NIFTY %s (%s%.0f pts, %s%.2f%%)" % ("{:,.0f}".format(nifty), sgn(p or 0), p or 0, sgn(c or 0), c or 0))
if sensex:
    c = pct(sensex, spc)
    p = (sensex - spc) if spc else None
    row.append("SENSEX %s (%s%.0f pts, %s%.2f%%)" % ("{:,.0f}".format(sensex), sgn(p or 0), p or 0, sgn(c or 0), c or 0))
if row:
    L.append(" | ".join(row))
    # aaj ka swing points me — trading me jitna dekhna aasan
if mode != "open":
    sw = []
    if nifty and npc and nhi and nlo:
        sw.append("NIFTY: %+.0f se %+.0f pts (swing %.0f)" % (nlo - npc, nhi - npc, nhi - nlo))
    if sensex and spc and shi and slo:
        sw.append("SENSEX: %+.0f se %+.0f pts (swing %.0f)" % (slo - spc, shi - spc, shi - slo))
    if sw:
        L.append("\U0001F9ED <b>Aaj ka swing</b> (prev close se)")
        L.append(" · ".join(sw))
if mode != "open" and sec_rows:
    picks = (sec_rows[:2] + sec_rows[-2:]) if len(sec_rows) > 2 else sec_rows
    L.append("\U0001F3ED Sector scoreboard")
    L.append(" ".join(("%s %s: %s%.1f%%" % ("\U0001F7E2" if c >= 0 else "\U0001F534", l, sgn(c), c)) for l, c in picks))
if mode != "open" and (fii_today is not None or dii_today is not None):
    L.append("\U0001F4B8 FII/DII today (cash)")
    L.append("FII: %s | DII: %s" % (
        ("Sell \u20B9%s Cr" % "{:,.0f}".format(abs(fii_today)) if fii_today < 0
         else "Buy \u20B9%s Cr" % "{:,.0f}".format(fii_today)) if fii_today is not None else "\u2014",
        ("Sell \u20B9%s Cr" % "{:,.0f}".format(abs(dii_today)) if dii_today < 0
         else "Buy \u20B9%s Cr" % "{:,.0f}".format(dii_today)) if dii_today is not None else "\u2014"))
if pcr.get("nifty_pcr_oi") is not None:
    # "25000.0" reads like a price. A strike is a round number - print it as one.
    _mp = pcr.get("nifty_max_pain")
    _mps = ("{:,}".format(int(round(_mp))) if isinstance(_mp, (int, float)) else (str(_mp) if _mp else "\u2014"))
    L.append("\U0001F3AF Nifty PCR %s | Max Pain %s" % (pcr.get("nifty_pcr_oi"), _mps))

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
    L.append("\U0001F9E0 <b>Smart Brain: %s (%s/100)</b>" % (esc(g.get("verdict") or "\u2014"), g.get("score")))
    for p in (g.get("points") or [])[:2]:
        L.append("\u2022 " + esc(p))

if br:
    L.append("")
    L.append("\U0001F4C8 Breadth: %s%% stocks EMA200 ke upar" % (br.get("above_200") if br.get("above_200") is not None else br.get("above_ema200_pct", "\u2014")))
if fd:
    cats = fd.get("categories") or {}
    fii = (cats.get("FII/FPI") or {}).get("net_cr")
    dii = (cats.get("DII") or {}).get("net_cr")
    if (fii is not None or dii is not None) and (mode == "open" or fii_today is None):
        L.append("\U0001F4B8 FII %s Cr | DII %s Cr" % (
            ("%+.0f" % fii) if fii is not None else "\u2014",
            ("%+.0f" % dii) if dii is not None else "\u2014"))

bench = (mt.get("bench") or {})
gold = (bench.get("gold") or {}).get("r1")
silver = (bench.get("silver") or {}).get("r1")
if gold is not None or silver is not None:
    L.append("\U0001F3C6 Gold 1Y %s | Silver 1Y %s" % (
        ("%+.1f%%" % gold) if gold is not None else "\u2014",
        ("%+.1f%%" % silver) if silver is not None else "\u2014"))

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

import os, json, urllib.request, urllib.parse
import datetime as _dt
IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))
TOKEN = os.environ.get("TG_TOKEN", "")
CHATS = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
DRY = os.environ.get("TG_DRY") == "1"

def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}

def yahoo(sym, rng="5d"):
    try:
        u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng)
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))
        m = d["chart"]["result"][0]["meta"]
        return m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")
    except Exception:
        return None, None

def send(msg):
    if DRY:
        print("[DRY]", msg[:400]); return True
    if not TOKEN or not CHATS:
        print("no token/chats"); return False
    ok = True
    for chat in CHATS:
        try:
            data = urllib.parse.urlencode({"chat_id": chat, "text": msg, "parse_mode": "HTML",
                                           "disable_web_page_preview": "true"}).encode()
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                "https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data), timeout=30).read())
            if not r.get("ok"): ok = False
        except Exception as e:
            print("send fail", str(e)[:60]); ok = False
    return ok

def crash_score(d):
    score, pts = 0, []
    tf, fu, fd, br, sb = d.get("tf") or {}, d.get("fu") or {}, d.get("fd") or {}, d.get("br") or {}, d.get("sb") or {}
    vix = None; nif = None
    for f in (tf.get("forecasts") or []):
        if f.get("symbol") == "^INDIAVIX": vix = f.get("as_of_last_close")
        if f.get("symbol") == "^NSEI": nif = f
    if vix is not None:
        score += 30 if vix >= 20 else (20 if vix >= 16 else (10 if vix >= 14 else 0))
        pts.append("India VIX %.1f" % vix)
    pc = ((fu.get("pcr") or {}).get("nifty_pcr_oi"))
    if pc is not None:
        score += 20 if pc < 0.85 else (12 if pc < 1.0 else 0)
        if pc > 1.3: score -= 5
        pts.append("Nifty PCR %s" % pc)
    cats = (fd.get("categories") or {})
    fii = ((cats.get("FII/FPI") or {}).get("net_cr"))
    if fii is not None:
        score += 20 if fii <= -4000 else (12 if fii <= -1500 else (6 if fii <= -500 else 0))
        if fii >= 1000: score -= 5
        pts.append("FII %+.0f Cr" % fii)
    brd = br.get("above_ema200_pct")
    if brd is not None:
        score += 15 if brd < 35 else (8 if brd < 45 else 0)
        pts.append("Breadth %s%%" % brd)
    gs = ((sb.get("guess") or {}).get("score"))
    if gs is not None:
        score += 10 if gs < 35 else (5 if gs < 45 else (-5 if gs > 65 else 0))
    mc = nif.get("median_chg_pct") if nif else None
    if mc is not None:
        score += 8 if mc < -2 else (4 if mc < -1 else (-5 if mc > 2 else 0))
    dii = ((cats.get("DII") or {}).get("net_cr"))
    if dii is not None and dii >= 2000: score -= 5
    return max(0, min(100, score)), pts

def status(score):
    if score < 25: return "SAB CLEAR", "+"
    if score < 50: return "CAUTION", "+/-"
    if score < 75: return "ALERT", "-"
    return "DANGER", "!!"

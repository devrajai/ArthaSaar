#!/usr/bin/env python3
"""
TELEGRAM BRAIN — market bot.

Two daily messages to Telegram from ArthaSaar's own data (no new APIs, no deps):

  morning    ~9:25 AM IST, right after morning-brain workflow commits
             pre-open + FII/DII + global cues + Smart Brain call + TimesFM rotation
  afternoon  ~3:45 PM IST, after market close (15:30)
             fresh close snapshot (NSE allIndices live fetch) + sector scoreboard
             + final FII/DII flows

Usage:
  python3 scripts/telegram_brain.py morning
  python3 scripts/telegram_brain.py afternoon
  python3 scripts/telegram_brain.py morning --dry    (print, don't send)

Secrets (GitHub Actions env or local shell):
  TELEGRAM_BOT_TOKEN  — from @BotFather
  TELEGRAM_CHAT_ID    — owner chat id (get via /start to the bot + getUpdates)

Self-healing: every section fails independently — one bad JSON never kills
the whole message. Telegram hard limit is 4096 chars/msg, so long messages
are split into chunks.
"""
import json
import os
import sys
import time
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from rotpts import rotline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = "https://devrajai.github.io/market-brain/"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 25

# sector indices for the afternoon scoreboard (subset of NSE 139)
SECTORS = [
    "NIFTY AUTO", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY FMCG",
    "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
    "NIFTY PSU BANK", "NIFTY PRIVATE BANK", "NIFTY REALTY",
    "NIFTY OIL & GAS", "NIFTY CONSUMER DURABLES", "NIFTY HEALTHCARE",
    "NIFTY CAPITAL MARKETS", "NIFTY ENERGY",
]
HEADLINE = ["NIFTY 50", "NIFTY BANK", "BSE SENSEX", "NIFTY MIDCAP 100",
            "NIFTY SMALLCAP 100", "NIFTY IT", "INDIA VIX"]

GLOBAL_ALIAS = {  # name in global.json -> display label
    "S&P 500": "🇺🇸 S&P 500", "Nasdaq Composite": "🇺🇸 Nasdaq",
    "Dow Jones": "🇺🇸 Dow", "Nikkei 225": "🇯🇵 Nikkei",
    "Hang Seng": "🇭🇰 Hang Seng", "FTSE 100": "🇬🇧 FTSE",
    "DAX": "🇩🇪 DAX", "Gold": "🥇 Gold", "Crude Oil WTI": "🛢️ Crude WTI",
    "Brent Oil": "🛢️ Brent", "US Dollar Index": "💵 Dollar Idx",
    "Bitcoin": "₿ Bitcoin", "US 10Y": "🇺🇸 US 10Y",
    "Fear & Greed": "😱 F&G",
}


def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def load(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"WARN {name} unreadable: {e}")
        return {}


def ist_now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))


def pct(v):
    """signed, compact percent string"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    return f"+{v:.2f}%" if v >= 0 else f"−{abs(v):.2f}%"


def cr(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    return f"+₹{v:,.0f} Cr" if v >= 0 else f"−₹{abs(v):,.0f} Cr"

def bs(v):
    # FII/DII ke liye: Buy/Sell word (rule: sirf +/- nahi)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "?"
    return f"Buy ₹{v:,.0f} Cr" if v >= 0 else f"Sell ₹{abs(v):,.0f} Cr"


# ---------------------------------------------------------------- data fetch
def _sensex_yfinance():
    """Yahoo blocks plain urllib on datacenter IPs (per PROJECT_BRAIN) —
    yfinance handles cookies/crumb. Returns a Sensex row or None."""
    try:
        import yfinance as yf  # noqa: PLC0415
        t = yf.Ticker("^BSESN")
        p = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
        prev = t.fast_info.get("previousClose") or t.fast_info.get("previous_close")
        if p and prev:
            return {"index": "BSE SENSEX", "price": round(float(p), 2),
                    "change_pct": round((float(p) - float(prev)) / float(prev) * 100, 2)}
    except Exception as e:  # noqa: BLE001
        print("WARN Sensex yfinance failed:", e)
    return None


def fetch_indices_live():
    """fresh NSE allIndices + Sensex — for the afternoon close snapshot"""
    rows = []
    try:
        for d in get_json("https://www.nseindia.com/api/allIndices").get("data", []):
            if d.get("last") is None:
                continue
            rows.append({"index": d.get("index"), "price": d.get("last"),
                         "change_pct": d.get("percentChange")})
    except Exception as e:  # noqa: BLE001
        print("WARN NSE allIndices failed:", e)
    try:
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
               + quote("^BSESN") + "?range=1d&interval=1d")
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=TIMEOUT) as r:
            j = json.loads(r.read().decode())
        meta = j["chart"]["result"][0]["meta"]
        p, prev = meta.get("regularMarketPrice"), \
            meta.get("chartPreviousClose") or meta.get("previousClose")
        if p and prev:
            rows.append({"index": "BSE SENSEX", "price": round(float(p), 2),
                         "change_pct": round((float(p) - float(prev)) / float(prev) * 100, 2)})
    except Exception as e:  # noqa: BLE001
        print("WARN Sensex plain urllib failed:", e)
        row = _sensex_yfinance()
        if row:
            rows.append(row)
    return {r["index"]: r for r in rows}


def fetch_fii_dii_live():
    """final FII/DII of the day (NSE keeps updating till evening)"""
    out = {}
    try:
        for r in get_json("https://www.nseindia.com/api/fiidiiTradeReact"):
            out[r.get("category")] = float(r.get("netValue", 0))
    except Exception as e:  # noqa: BLE001
        print("WARN fii/dii live failed:", e)
    return out


# ---------------------------------------------------------------- sections
def sec_global():
    g = load("global.json")
    lines = ["🌍 <b>Global cues (overnight)</b>"]
    for it in g.get("items", []):
        label = GLOBAL_ALIAS.get(it.get("name")) or it.get("name", "?")
        lines.append(f"{label}: <b>{it.get('price', '?'):,.0f}</b> "
                     f"({pct(it.get('chg_pct'))})" if isinstance(it.get("price"), (int, float))
                     else f"{label}: {pct(it.get('chg_pct'))}")
        if len(lines) >= 9:
            break
    return "\n".join(lines) if len(lines) > 1 else None


def sec_fii_dii(prefix="yesterday"):
    f = load("fii-dii.json").get("categories", {})
    fii = f.get("FII/FPI", {}).get("net_cr")
    dii = f.get("DII", {}).get("net_cr")
    if fii is None and dii is None:
        return None
    return (f"💸 <b>FII/DII ({prefix})</b>\n"
            f"FII: <b>{bs(fii)}</b>  |  DII: <b>{bs(dii)}</b>")


def sec_preopen():
    p = load("preopen.json")
    if not p.get("stocks"):
        return None
    gb, lb = p.get("gainer_buckets", {}), p.get("loser_buckets", {})
    lines = [f"☀️ <b>Pre-open (9:15 IST, {p.get('stocks', 0):,} stocks)</b>",
             f"Breadth: {gb.get('up_ge_1pct', 0)} up ≥1% vs "
             f"{lb.get('down_ge_1pct', 0)} down ≥1%"]
    tg = p.get("top20_gainers", [])[:5]
    tl = p.get("top20_losers", [])[:5]
    if tg:
        lines.append("🔴 Top: " + ", ".join(
            f"{s['symbol']} {pct(s.get('change_pct'))}" for s in tg))
    if tl:
        lines.append("🟠 Weak: " + ", ".join(
            f"{s['symbol']} {pct(s.get('change_pct'))}" for s in tl))
    alerts = p.get("corporate_action_alerts", [])
    if alerts:
        lines.append("⚠️ Corp actions: " + ", ".join(
            a["symbol"] for a in alerts[:5]))
    return "\n".join(lines)


def sec_smart_brain():
    sb = load("smart-brain.json")
    g = sb.get("guess", {})
    if not g.get("verdict"):
        return None
    lines = [f"🧠 <b>Smart Brain call: {g['verdict']}</b> "
             f"(score {g.get('score', '?')}/100)"]
    for pt in g.get("points", [])[:5]:
        lines.append(f"• {pt}")
    return "\n".join(lines)


def sec_timesfm():
    tf = load("timesfm_forecasts.json")
    rot = tf.get("rotation", [])[:4]
    if not rot:
        return None
    return ("🔮 <b>TimesFM 21-day rotation</b>\n" + "\n".join(
        f"• {rotline(r, tf)} (conf {r.get('conf', '?')}%)"
        for r in rot))


def sec_index_changes():
    ch = load("index-changes.json")
    a, r = ch.get("added", []), ch.get("removed", [])
    if not a and not r:
        return None
    parts = []
    if a:
        parts.append("➕ In: " + ", ".join(a))
    if r:
        parts.append("➖ Out: " + ", ".join(r))
    return "🔔 <b>Nifty 500 index change!</b>\n" + "\n".join(parts)


def sec_close(idx=None):
    idx = idx if idx is not None else fetch_indices_live()
    if not idx:
        return None
    lines = ["🎯 <b>Close (15:30 IST)</b>"]
    for name in HEADLINE:
        r = idx.get(name)
        if not r:
            continue
        label = name.title().replace("Bse Sensex", "Sensex") \
            .replace("Nifty It", "Nifty IT").replace("India Vix", "India VIX")
        lines.append(f"{label}: "
                     f"<b>{r['price']:,.2f}</b> ({pct(r.get('change_pct'))})")
    return "\n".join(lines)


def sec_sector_board(idx=None):
    idx = idx if idx is not None else fetch_indices_live()
    rows = [r for n, r in ((n, idx.get(n)) for n in SECTORS) if r
            and r.get("change_pct") is not None]
    if not rows:
        return None
    rows.sort(key=lambda x: float(x["change_pct"]))
    lines = ["🏭 <b>Sector scoreboard</b>"]
    def _lbl(n):
        return n.replace("NIFTY ", "").title().replace("It", "IT").replace("Psu", "PSU")
    for r in reversed(rows[-3:]):
        lines.append(f"🟢 {_lbl(r['index'])}: {pct(r['change_pct'])}")
    for r in rows[:3]:
        lines.append(f"🔴 {_lbl(r['index'])}: {pct(r['change_pct'])}")
    return "\n".join(lines)


def sec_fii_dii_today():
    f = fetch_fii_dii_live()
    if "FII/FPI" not in f and "DII" not in f:
        return None
    return (f"💸 <b>FII/DII today (cash)</b>\n"
            f"FII: <b>{bs(f.get('FII/FPI'))}</b>  |  DII: <b>{bs(f.get('DII'))}</b>")



# ---------------------------------------------------------------- crash alert
CRASH_PCT = -1.0  # Nifty ya Bank Nifty isse zyada gire -> crash mode

def _cp(r):
    try:
        return float(r.get("change_pct"))
    except (TypeError, ValueError):
        return None

def sec_crash_alert(idx):
    """Big red day -> focused CRASH section on top of the day analysis."""
    if not idx:
        return None
    nifty, bank = idx.get("NIFTY 50"), idx.get("NIFTY BANK")
    np_, bp = _cp(nifty or {}), _cp(bank or {})
    trigger = None
    if np_ is not None and np_ <= CRASH_PCT:
        trigger = ("Nifty 50", np_, nifty)
    if bp is not None and bp <= CRASH_PCT and (trigger is None or bp < trigger[1]):
        trigger = ("Bank Nifty", bp, bank)
    if trigger is None:
        return None

    name, cp = trigger[0], trigger[1]
    lines = [f"\U0001F6A8 <b>CRASH ALERT \u2014 {name} {pct(cp)}</b>"]

    if nifty and np_ is not None:
        price = float(nifty["price"])
        prev = price / (1 + np_ / 100)
        lines.append(f"Nifty 50: <b>{price:,.2f}</b> ({price - prev:+,.0f} pts)")
    if bank and bp is not None:
        lines.append(f"Bank Nifty: {pct(bp)}")

    rows = [r for n, r in idx.items() if n in SECTORS and _cp(r) is not None]
    if rows:
        rows.sort(key=lambda r: _cp(r))
        def _lbl(n):
            return n.replace("NIFTY ", "").title().replace("It", "IT").replace("Psu", "PSU")
        red = [r for r in rows if _cp(r) < 0]
        if red:
            hit = ", ".join(f"{_lbl(r['index'])} {pct(_cp(r))}" for r in rows[:3])
            lines.append(f"Sectors: {len(red)}/{len(rows)} red \u2014 worst: {hit}")
        else:
            lines.append(f"Sectors: 0/{len(rows)} red")

    vix = idx.get("INDIA VIX")
    if vix and _cp(vix) is not None:
        lines.append(f"India VIX: {pct(_cp(vix))}" + (" \u2014 fear spike" if _cp(vix) > 5 else ""))
    mid, small = idx.get("NIFTY MIDCAP 100"), idx.get("NIFTY SMALLCAP 100")
    mp, sp = _cp(mid or {}), _cp(small or {})
    if mp is not None and sp is not None:
        lines.append(f"Midcap {pct(mp)} \u00b7 Smallcap {pct(sp)}")

    lines.append("")
    lines.append("\U0001F9ED <b>Playbook</b>")
    lines.append("\u2022 Sell-off on KNOWN fears (US yields, FII outflow, crude) = 1 yr tricky, 3 yr+ opportunity zone")
    lines.append("\u2022 Panic day \u2260 exit day \u2014 stagger entries at supports, SIPs on autopilot")
    lines.append("\u2022 Watch recent swing lows (Sep / Apr) \u2014 hold ya break, site charts pe clear")
    return "\n".join(lines)

# ---------------------------------------------------------------- send
def send(token, chat_id, text):
    for attempt in range(3):
        try:
            body = json.dumps({"chat_id": chat_id, "text": text,
                               "parse_mode": "HTML",
                               "disable_web_page_preview": True}).encode()
            req = Request(f"https://api.telegram.org/bot{token}/sendMessage",
                          data=body, headers={"Content-Type": "application/json",
                                              "User-Agent": UA})
            with urlopen(req, timeout=TIMEOUT) as r:
                ok = json.loads(r.read().decode()).get("ok")
            if ok:
                return True
        except Exception as e:  # noqa: BLE001
            print(f"WARN send attempt {attempt + 1} failed: {e}")
            time.sleep(3 * (attempt + 1))
    return False


def chunk(text, limit=3800):
    """split a long message into <=limit chunks at line boundaries"""
    if len(text) <= limit:
        return [text]
    out, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            out.append(cur)
            cur = line
        else:
            cur = (cur + "\n" + line) if cur else line
    if cur:
        out.append(cur)
    return out


def deliver(sections, footer_note, title):
    now = ist_now()
    head = (f"<b>{title}</b> — "
            f"{now.strftime('%a')}, {now.strftime('%d/%m/%y')}"
            f" · 🗾 ArthaSaar")
    body = "\n\n".join(s for s in sections if s)
    if not body:
        body = "(no data sections survived — check workflows)"
    tail = (f"\n\n{footer_note}\n🔗 {SITE}\n"
            f"<i>Educational data, not investment advice.</i>")
    return chunk(f"{head}\n\n{body}{tail}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    dry = "--dry" in sys.argv
    if mode == "morning":
        sections = [sec_global(), sec_fii_dii("yesterday"), sec_preopen(),
                    sec_smart_brain(), sec_timesfm(), sec_index_changes()]
        footer = "☕ Pre-open brief — market opens 9:30 IST"
        title = "MORNING BRIEF"
    elif mode == "afternoon":
        idx = fetch_indices_live()
        sections = [sec_crash_alert(idx), sec_close(idx), sec_sector_board(idx),
                    sec_fii_dii_today()]
        footer = "📊 Day analysis — post-close"
        title = "DAY ANALYSIS"
    else:
        print("usage: telegram_brain.py morning|afternoon [--dry]")
        sys.exit(2)

    messages = deliver(sections, footer, title)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")

    if dry:
        for m in messages:
            print(m, end="\n" + "-" * 40 + "\n")
        print(f"[dry] would send {len(messages)} message(s)")
        return

    if not token or not chat:
        print("ERROR: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        sys.exit(1)

    sent = sum(send(token, chat, m) for m in messages)
    print(f"telegram {mode}: {sent}/{len(messages)} message(s) sent")
    if sent < len(messages):
        sys.exit(1)


if __name__ == "__main__":
    main()

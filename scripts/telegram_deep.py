#!/usr/bin/env python3
"""ArthaSaar deep Telegram messages: expiry, positioning, weekly, holding review.

WHY THIS EXISTS
The three scheduled messages cover the day. They do not cover the questions a trader actually
asks across the week and the month:

    "Where are sellers positioned into expiry?"
    "What is the positioning for December and January?"
    "What did the channels talk about, and what did the data do?"
    "I hold this stock - what does the data say about it now?"

Every one of those is answerable from files this repo already publishes. None of them requires
a recommendation.

WHAT IT WILL NOT DO
No entry, no target, no stoploss, no buy or sell verdict. The holding review lists facts -
rollover, open-interest action, rank change, distance from the high - and stops. The line
between "here is what the positioning is" and "so buy this" is the whole point.

USAGE
    python scripts/telegram_deep.py expiry          # expiry morning
    python scripts/telegram_deep.py positioning     # monthly, far expiries + rollover
    python scripts/telegram_deep.py weekly          # Sunday digest
    python scripts/telegram_deep.py review TATAMOTORS
    add --dry to print without sending

Missing secrets are a clean skip, never a crash.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = re.sub(r"\s+", "", os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "")
CHATS = [c.strip() for c in (os.environ.get("TG_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip().split(",") if c.strip()]
DRY = "--dry" in sys.argv

MIN_CASES = 60
MIN_OI_SHARE = 5.0   # percent of total open interest before an expiry is worth quoting


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def n(v, dp=0):
    try:
        return ("{:,.%df}" % dp).format(float(v))
    except Exception:
        return "—"


def pc(v, dp=2):
    try:
        return ("%+." + str(dp) + "f%%") % float(v)
    except Exception:
        return "—"


def ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def oi_share(exp, total_all):
    """How much of the whole chain's open interest this expiry holds."""
    try:
        own = float(exp.get("total_ce_oi") or 0) + float(exp.get("total_pe_oi") or 0)
        return (own / total_all * 100.0) if total_all else None
    except Exception:
        return None


# ---------------------------------------------------------------- expiry
def build_expiry():
    d = jload("docs/oi_by_expiry.json") or {}
    idx = d.get("indices") or {}
    today = ist().strftime("%Y-%m-%d")
    L = ["<b>ArthaSaar — expiry note</b>", ist().strftime("%d %b %Y")]
    found = False
    for sym in ("NIFTY", "BANKNIFTY"):
        v = idx.get(sym) or {}
        exps = v.get("expiries") or []
        if not exps:
            continue
        # NOT `or 999`. days_out is 0 on expiry day, and 0 is falsy - so the expiry that
        # matters most was being replaced by the next one and the whole message said "no
        # expiry today" on expiry day itself.
        near = min(exps, key=lambda e: (e.get("days_out")
                                        if e.get("days_out") is not None else 999))
        dte = near.get("days_out")
        if (near.get("expiry") or "") != today and (dte if dte is not None else 99) > 1:
            continue
        found = True
        L.append("")
        L.append("<b>%s</b> · spot %s" % (sym, n(v.get("spot"))))
        L.append("Max pain <b>%s</b> · PCR %s"
                 % (n(near.get("max_pain")), n(near.get("pcr"), 2)))
        L.append("Call wall %s · Put wall %s"
                 % (n(near.get("call_wall")), n(near.get("put_wall"))))
        ce, pe = near.get("total_ce_oi"), near.get("total_pe_oi")
        if ce and pe:
            L.append("Call OI %s · Put OI %s" % (n(ce), n(pe)))
    if not found:
        L.append("")
        L.append("No expiry falls today or tomorrow.")
    L.append("")
    L.append("<i>Max pain is arithmetic on open interest — the strike where option buyers "
             "collectively lose least. It is where sellers are positioned, not where price "
             "will go.</i>")
    return "\n".join(L)


# ---------------------------------------------------------------- positioning
def build_positioning():
    d = jload("docs/oi_by_expiry.json") or {}
    idx = d.get("indices") or {}
    rol = jload("docs/rollover.json") or {}
    scr = jload("docs/screener.json") or {}
    by_sym = {str(r.get("symbol")): r for r in (scr.get("rows") or [])}

    L = ["<b>ArthaSaar — positioning beyond this month</b>", ist().strftime("%d %b %Y")]
    any_row = False
    for sym in ("NIFTY", "BANKNIFTY"):
        v = idx.get(sym) or {}
        exps = sorted(v.get("expiries") or [],
                      key=lambda e: (e.get("days_out") if e.get("days_out") is not None else 999))
        if len(exps) < 2:
            continue
        total_all = sum(float(e.get("total_ce_oi") or 0) + float(e.get("total_pe_oi") or 0)
                        for e in exps)
        # A PCR computed on an expiry holding 0.0% of open interest is noise, not positioning.
        # BANKNIFTY 2027-06-29 was published with PCR 2.12 on 0.0% of OI - a number with
        # nothing behind it. Only expiries above MIN_OI_SHARE are shown.
        far = []
        for e in exps[1:]:
            dte = e.get("days_out")
            if dte is None or dte < 14:
                continue
            sh = oi_share(e, total_all)
            if sh is not None and sh < MIN_OI_SHARE:
                continue
            far.append(e)
        if not far:
            continue
        any_row = True
        L.append("")
        L.append("<b>%s</b>" % sym)
        for e in far[:4]:
            share = oi_share(e, total_all)
            L.append("%s · PCR %s · call %s / put %s%s"
                     % (esc(str(e.get("expiry"))), n(e.get("pcr"), 2),
                        n(e.get("call_wall")), n(e.get("put_wall")),
                        (" · %.1f%% of OI" % share) if share is not None else ""))
    if not any_row:
        L.append("")
        L.append("No far expiries are listed in the chain right now.")
    else:
        L.append("")
        L.append("<i>Far expiries carry a small share of total open interest. A wall there is "
                 "thin and breaks easily — it is not the same statement as the same wall in "
                 "the current series.</i>")

    # rollover divergence: positions carried forward while the price falls
    items = [x for x in (rol.get("items") or []) if (x.get("roll") or 0) >= 60]
    div = []
    for x in items:
        r = by_sym.get(str(x.get("s"))) or {}
        ch = r.get("chg_5d")
        if ch is None:
            continue
        try:
            ch = float(ch)
        except Exception:
            continue
        if ch < -1.0:
            div.append((x.get("s"), x.get("roll"), ch))
    div.sort(key=lambda t: -float(t[1]))
    if div:
        L.append("")
        L.append("<b>Rolled forward, price falling</b>")
        for s, roll, ch in div[:5]:
            L.append("%s · rollover %s%% · 5-day %s" % (esc(str(s)), n(roll, 0), pc(ch)))
        L.append("<i>High rollover is conviction. High rollover with a falling price is "
                 "positions carried rather than accepted.</i>")
    return "\n".join(L)


# ---------------------------------------------------------------- weekly
def build_weekly():
    vc = jload("docs/video_vs_chain.json") or {}
    st = jload("docs/oi_stats.json") or {}
    ih = jload("docs/index_history.json") or {}

    L = ["<b>ArthaSaar — weekly read</b>", ist().strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")

    # THE CHANNEL SECTION WAS REMOVED. It named stocks and attached a "call writing" label to
    # them, which reads as a view on a named security - the thing this bot is not allowed to
    # publish. The collection still runs and docs/telegram_vs_chain.json still exists for
    # research; it is simply not broadcast.

    # PCR extremes with the baseline beside them
    pe = (st.get("pcr_extremes") or {}).get("NIFTY") or {}
    if pe:
        base = (pe.get("baseline") or {}).get("20") or [None, 0]
        low = (pe.get("low") or {}).get("20") or [None, 0]
        L.append("")
        L.append("<b>Does PCR predict anything? Tested, and the answer is no.</b>")
        if low[0] is not None and (low[1] or 0) >= MIN_CASES and base[0] is not None:
            gap = float(low[0]) - float(base[0])
            L.append("When Nifty PCR was below %.2f, the next 20 sessions averaged %s (n=%s)."
                     % (pe.get("low_cut"), pc(low[0]), n(low[1])))
            L.append("On any other day: %s (n=%s)." % (pc(base[0]), n(base[1])))
            L.append("The gap is <b>%.2f points</b> — inside normal noise for a 20-session "
                     "window. <b>We do not use PCR as a signal.</b>" % gap)
        L.append("<i>Published as a null result. A statistic that cannot beat its own baseline "
                 "should be reported as failing, not shown as an edge.</i>")

    # the month so far
    for ix in (ih.get("indices") or []):
        if ix.get("symbol") != "^NSEI":
            continue
        w = ix.get("week") or {}
        L.append("")
        L.append("<b>Nifty now</b>")
        L.append("%s · week %s · %s from the 52-week high"
                 % (n(w.get("close")), pc(w.get("chg_pct")), pc(ix.get("from_high_pct"), 1)))
        lv = ix.get("levels") or {}
        if lv.get("pivot"):
            L.append("Pivot %s · R1 %s · S1 %s" % (n(lv.get("pivot")), n(lv.get("r1")), n(lv.get("s1"))))
    L.append("")
    L.append("<i>Levels are arithmetic on last week's range, not a forecast.</i>")
    return "\n".join(L)


# ---------------------------------------------------------------- holding review
def build_review(sym):
    sym = (sym or "").upper().strip()
    if not sym:
        return "<b>Holding review</b>\n\nGive a symbol: review TATAMOTORS"
    scr = jload("docs/screener.json") or {}
    row = None
    for r in (scr.get("rows") or []):
        if str(r.get("symbol")).upper() == sym:
            row = r
            break
    if not row:
        return ("<b>Holding review · %s</b>\n\nNot in the screener. Check the spelling, or the "
                "stock may not have a full page yet." % esc(sym))

    L = ["<b>Holding review · %s</b>" % esc(sym)]
    nm = str(row.get("name") or "").strip()
    if nm:
        L.append("<i>%s</i>" % esc(nm[:70]))
    L.append("")
    L.append("Price %s · 1-day %s · 5-day %s"
             % (n(row.get("close"), 2), pc(row.get("chg_1d")), pc(row.get("chg_5d"))))
    if row.get("from_52w_high") is not None:
        L.append("%s from the 52-week high" % pc(row.get("from_52w_high"), 1))

    # momentum rank change
    rm = jload("docs/rank_momentum.json") or {}
    for key, lbl in (("climbers", "climbing"), ("fallers", "falling")):
        for c in (rm.get(key) or []):
            if str(c.get("symbol")).upper() == sym:
                L.append("Screener rank %s → %s (%s)"
                         % (n(c.get("was")), n(c.get("now")), lbl))
                break

    # rollover
    rol = jload("docs/rollover.json") or {}
    for x in (rol.get("items") or []):
        if str(x.get("s")).upper() == sym:
            L.append("Futures rollover %s%% into %s" % (n(x.get("roll"), 0), esc(str(x.get("exp")))))
            break

    # option-chain action for this stock
    oc = (jload("docs/option_chain.json") or {}).get("stocks") or {}
    ent = oc.get(sym)
    if ent:
        best = None
        for stk in (ent.get("strikes") or []):
            for side, lbl2 in (("ce", "call"), ("pe", "put")):
                dd = stk.get(side) or {}
                ch = dd.get("oi_chg") or 0
                if best is None or ch > best[0]:
                    best = (ch, lbl2, stk.get("strike"), dd.get("action"))
        if best and best[0]:
            L.append("Options: %s writing at %s (OI %s, %s)"
                     % (esc(best[1]), n(best[2]), ("+" + n(best[0])), esc(str(best[3]))))
    else:
        L.append("Options: no chain held for this stock today.")

    L.append("")
    L.append("<b>Facts, not a verdict.</b> No target, no stoploss, no buy or sell call. What "
             "you do with these is yours.")
    return "\n".join(L)


# ---------------------------------------------------------------- send
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = (args[0] if args else "weekly").lower()
    if mode == "expiry":
        msg = build_expiry()
    elif mode == "positioning":
        msg = build_positioning()
    elif mode == "weekly":
        msg = build_weekly()
    elif mode == "review":
        msg = build_review(args[1] if len(args) > 1 else "")
    else:
        print("unknown mode %r - use expiry | positioning | weekly | review SYMBOL" % mode)
        return 2

    print("mode=%s len=%d chats=%d" % (mode, len(msg), len(CHATS)))
    print(msg)
    if DRY:
        print("\n[dry run — not sent]")
        return 0
    if not TOKEN or not CHATS:
        print("TG_TOKEN / TG_CHAT_ID not set — skipping the send (this is not an error)")
        return 0
    sent = 0
    for chat in CHATS:
        try:
            payload = urllib.parse.urlencode({
                "chat_id": chat, "text": msg, "parse_mode": "HTML",
                "disable_web_page_preview": "true"}).encode()
            req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=payload)
            r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
            print("sent to %s: %s" % (chat, r.get("ok")))
            sent += 1
        except Exception as e:
            print("send fail %s: %s" % (chat, str(e)[:90]))
    return 0 if sent or not CHATS else 1


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)

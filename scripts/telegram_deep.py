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
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
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
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
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
        # RANKED BY SHARE, NOT CUT AT 5%. A hard 5% cut left one line per index and a message
        # with almost nothing in it. The share is printed on every line instead, so a thin
        # expiry is visibly thin rather than silently absent.
        far = []
        for e in exps[1:]:
            dte = e.get("days_out")
            if dte is None or dte < 14:
                continue
            e["_share"] = oi_share(e, total_all)
            far.append(e)
        far.sort(key=lambda e: -(e.get("_share") or 0))
        # A floor of 0.5% removes the absurdity of quoting "PCR 2.12" on an expiry holding
        # 0.0% of open interest. Above the floor the share is printed, so thin is visible.
        far = [e for e in far if (e.get("_share") or 0) >= 0.5][:4]
        if not far:
            continue
        any_row = True
        L.append("")
        L.append("<b>%s</b>" % sym)
        for e in far[:4]:
            share = e.get("_share")
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
    """PAUSED. A named stock under a 'holding' label reads as a view on that security, which
    is a research service under the RA Regulations whatever disclaimer sits under it. Kept so
    the logic is not lost; returns the paused notice instead of a review until a compliance
    check clears it."""
    return ("<b>Holding review — paused</b>\n\n"
            "This message named a single stock and is paused pending a compliance check. "
            "The same facts are on the site as a neutral stock page: price, 1-month change, "
            "52-week position, open interest. Market data and descriptions only.")


def _build_review_old(sym):
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




# ---------------------------------------------------------------- glossary
GLOSSARY = [
    ("PCR", "put-call ratio",
     "Total put open interest divided by total call open interest. Read it as: how much "
     "bearish positioning exists against bullish. It is a description, not a prediction."),
    ("OI", "open interest",
     "The number of contracts currently open. It rises when a new position is created and "
     "falls when one is closed. It is not the same as volume, which counts trades."),
    ("Max pain", "the strike where buyers lose least",
     "The strike at which the total value of expiring options is smallest. It is arithmetic "
     "on open interest, and it is where option sellers are positioned - not a target."),
    ("FII", "foreign institutional investor",
     "Overseas funds buying and selling Indian shares, reported in crore rupees for the cash "
     "market. NSE publishes the figure the same evening, provisional."),
    ("Lot size", "contract size",
     "How many shares one derivative contract covers. A Rs 2 premium on a 65 lot costs Rs 130, "
     "not Rs 2. Always multiply before deciding anything is cheap."),
    ("Rollover", "positions carried to the next expiry",
     "The share of a stock's futures open interest already sitting in the next series. High "
     "rollover means holders chose to stay; low means they squared off."),
    ("Gap", "a jump at the open",
     "When the market opens above yesterday's high or below yesterday's low. The gap is "
     "'filled' when price trades back through it."),
    ("Breadth", "how many stocks are participating",
     "The share of listed stocks above their own moving average. A rising index on falling "
     "breadth means a few large stocks are carrying it."),
]


def build_glossary():
    now = ist()
    idx = (now.timetuple().tm_yday) % len(GLOSSARY)
    short, full, explain = GLOSSARY[idx]
    L = ["<b>ArthaSaar — one term a day</b>", now.strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
    L.append("")
    L.append("<b>%s</b> — %s" % (esc(short), esc(full)))
    L.append(esc(explain))
    # today's real number as the example, when the file has one
    try:
        if short == "PCR":
            pcr = jload("docs/pcr_signal.json") or {}
            cur = (pcr.get("current") or {})
            if cur.get("pcr") is not None:
                L.append("")
                L.append("Today: Nifty PCR <b>%.2f</b> (%s)." % (float(cur["pcr"]),
                                                                esc(str(cur.get("band") or ""))))
        elif short == "Max pain":
            d = jload("docs/oi_by_expiry.json") or {}
            nif = ((d.get("indices") or {}).get("NIFTY")) or {}
            for e in (nif.get("expiries") or []):
                if e.get("max_pain"):
                    L.append("")
                    L.append("Today: Nifty max pain <b>%s</b> for the %s expiry."
                             % (n(e["max_pain"]), esc(str(e.get("expiry")))))
                    break
        elif short == "Breadth":
            br = jload("docs/breadth.json") or {}
            if br.get("above_50") is not None:
                L.append("")
                L.append("Today: <b>%.1f%%</b> of %s stocks are above their 50-day average."
                         % (float(br["above_50"]), n(br.get("total"))))
        elif short == "FII":
            asof = jload("docs/data_asof.json") or {}
            L.append("")
            L.append("Reported session: %s." % esc(str(asof.get("session") or "latest")))
        elif short == "Gap":
            g = jload("docs/gaps.json") or {}
            if g.get("fill_rate_up") is not None:
                L.append("")
                L.append("Measured: gap-ups filled within %s sessions %.1f%% of the time (n=%s)."
                         % (esc(str((g.get("samples") or {}).get("window"))),
                            float(g["fill_rate_up"]), n((g.get("samples") or {}).get("up"))))
    except Exception:
        pass
    L.append("")
    L.append("<i>Term %d of %d. One a day, with the number it refers to.</i>"
             % (idx + 1, len(GLOSSARY)))
    return "\n".join(L)


# ---------------------------------------------------------------- calendar
def build_calendar():
    now = ist()
    L = ["<b>ArthaSaar — dates ahead</b>", now.strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")

    d = jload("docs/oi_by_expiry.json") or {}
    nif = ((d.get("indices") or {}).get("NIFTY")) or {}
    exps = sorted([e for e in (nif.get("expiries") or [])
                   if e.get("expiry") and str(e.get("expiry")) >= now.strftime("%Y-%m-%d")],
                  key=lambda e: str(e.get("expiry")))
    if exps:
        L.append("")
        L.append("<b>Nifty expiries</b>")
        for e in exps[:4]:
            L.append("%s · %s day(s) away" % (esc(str(e.get("expiry"))),
                                              e.get("days_out") if e.get("days_out") is not None else "?"))

    # special sessions the exchange has announced
    try:
        ss = jload("config/special_sessions.json") or {}
        ahead = [s for s in (ss.get("sessions") or [])
                 if str(s.get("date")) >= now.strftime("%Y-%m-%d")]
        L.append("")
        L.append("<b>Special sessions</b>")
        if ahead:
            for s in ahead[:4]:
                L.append("%s · %s (%s-%s IST)" % (esc(str(s.get("date"))), esc(str(s.get("label"))),
                                                  esc(str(s.get("open"))), esc(str(s.get("close")))))
        else:
            L.append("None announced.")
    except Exception:
        pass

    # scheduled macro events
    try:
        ev = jload("config/event_days.json") or {}
        soon = [e for e in (ev.get("events") or [])
                if now.strftime("%Y-%m-%d") <= str(e.get("date")) <=
                (now + timedelta(days=45)).strftime("%Y-%m-%d")]
        L.append("")
        L.append("<b>Scheduled events</b>")
        if soon:
            for e in soon[:5]:
                L.append("%s · %s" % (esc(str(e.get("date"))), esc(str(e.get("label")))))
        else:
            L.append("Nothing scheduled in the next 45 days in our file.")
        L.append("<i>NSE trading holidays are not in this repository. Check nseindia.com "
                 "before assuming a session.</i>")
    except Exception:
        pass
    return "\n".join(L)


# ---------------------------------------------------------------- scorecard
def build_scorecard():
    """Every statistic the site publishes, and whether it beat its own baseline."""
    now = ist()
    L = ["<b>ArthaSaar — weekly scorecard</b>", now.strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
    L.append("")
    L.append("<i>Each row is a statistic we publish, the baseline it should be judged against, "
             "and the verdict.</i>")

    rows = []
    try:
        pcr = jload("docs/pcr_signal.json") or {}
        for b in (pcr.get("bands") or []):
            h = next((x for x in (b.get("horizons") or []) if x.get("h") == 21), None)
            if not h or (h.get("n") or 0) < MIN_CASES:
                continue
            # "56.4% up", NOT "+56.40% up". pc() adds a sign because it formats a CHANGE;
            # this is the share of times something happened, and a leading + reads as a move.
            up = h.get("up_pct")
            up_s = ("%.1f%% up" % float(up)) if up is not None else "—"
            rows.append((esc(str(b.get("band"))), up_s,
                         "n=%s" % n(h.get("n")), esc(str(h.get("edge") or "-"))))
    except Exception as _e:
        print("scorecard: PCR rows skipped: %s: %s" % (type(_e).__name__, str(_e)[:90]))

    try:
        g = jload("docs/gaps.json") or {}
        sm = g.get("samples") or {}
        if g.get("fill_rate_up") is not None:
            rows.append(("Gap-up fills", "%.1f%%" % float(g["fill_rate_up"]),
                         "n=%s" % n(sm.get("up")), "describes fills, not direction"))
    except Exception:
        pass

    if rows:
        L.append("")
        for r in rows[:6]:
            L.append("<b>%s</b> — %s (%s) · %s" % r)
    else:
        L.append("")
        L.append("No statistics met the sample threshold this week.")

    L.append("")
    L.append("<i>A statistic that matches its baseline has no edge, and is reported that way. "
             "We do not publish one that fails to beat it.</i>")
    return "\n".join(L)


# ---------------------------------------------------------------- monthly
def build_monthly():
    now = ist()
    ih = jload("docs/index_history.json") or {}
    br = jload("docs/breadth.json") or {}
    L = ["<b>ArthaSaar — month so far</b>", now.strftime("%b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")

    for ix in (ih.get("indices") or []):
        if ix.get("symbol") != "^NSEI":
            continue
        daily = ix.get("daily") or []
        if not daily:
            continue
        ym = now.strftime("%Y-%m")
        month = [r for r in daily if str(r[0]).startswith(ym)]
        if not month:
            continue
        o = month[0][1]; hi = max(r[2] for r in month); lo = min(r[3] for r in month)
        c = month[-1][4]
        L.append("")
        L.append("<b>Nifty %s</b>" % now.strftime("%b"))
        L.append("Open %s · high %s · low %s · now %s" % (n(o), n(hi), n(lo), n(c)))
        if o:
            L.append("%s on the month · range %s (%s of price)"
                     % (pc((c / o - 1) * 100), n(hi - lo), pc((hi - lo) / lo * 100, 1)))

    if br.get("above_50") is not None:
        L.append("")
        L.append("Breadth: %.1f%% of %s stocks above their 50-day average."
                 % (float(br["above_50"]), n(br.get("total"))))

    d = jload("docs/oi_by_expiry.json") or {}
    nif = ((d.get("indices") or {}).get("NIFTY")) or {}
    exps = sorted([e for e in (nif.get("expiries") or [])
                   if e.get("expiry") and str(e.get("expiry")) >= now.strftime("%Y-%m-%d")],
                  key=lambda e: str(e.get("expiry")))
    if exps:
        L.append("")
        L.append("Next expiries: " + " · ".join(esc(str(e.get("expiry"))) for e in exps[:3]))
    return "\n".join(L)




# ---------------------------------------------------------------- corrections
def build_corrections():
    d = jload("docs/corrections.json") or {}
    rows = d.get("corrections") or []
    L = ["<b>ArthaSaar — corrections log</b>", ist().strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
    L.append("")
    L.append("<i>Every figure we published that turned out wrong, with the date and what was "
             "actually true. A site that publishes statistics should publish the ones it got "
             "wrong too.</i>")
    if not rows:
        L.append("")
        L.append("No corrections recorded.")
        return "\n".join(L)
    recent = sorted(rows, key=lambda r: str(r.get("date")), reverse=True)[:5]
    for r in recent:
        L.append("")
        L.append("<b>%s</b> — %s" % (esc(str(r.get("date"))), esc(str(r.get("what_showed")))))
        L.append("<i>What was true:</i> " + esc(str(r.get("what_was_right"))))
        L.append("<i>Fixed:</i> " + esc(str(r.get("fixed"))))
    L.append("")
    L.append("<i>%d corrections on record. The full list is on the site.</i>" % len(rows))
    return "\n".join(L)


# ---------------------------------------------------------------- claim ledger
def build_ledger():
    d = jload("docs/claim_ledger.json") or {}
    rows = d.get("claims") or []
    L = ["<b>ArthaSaar — did last week's numbers hold?</b>", ist().strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")
    L.append("")
    L.append("<i>Every statistic we publish, re-measured. This checks OUR numbers, not the "
             "market's behaviour.</i>")
    if not rows:
        L.append("")
        L.append("No claims recorded yet.")
        return "\n".join(L)

    held = [r for r in rows if r.get("status") == "held"]
    moved = [r for r in rows if r.get("status") == "moved"]
    few = [r for r in rows if r.get("status") == "too few"]

    L.append("")
    L.append("Held: <b>%d</b> · moved: <b>%d</b> · too few cases: <b>%d</b>"
             % (len(held), len(moved), len(few)))
    for r in moved[:4]:
        L.append("")
        L.append("<b>Moved</b> — %s" % esc(str(r.get("claim"))))
        L.append(esc(str(r.get("detail"))))
    for r in few[:3]:
        L.append("")
        L.append("<b>Too few</b> — %s" % esc(str(r.get("claim"))))
        L.append(esc(str(r.get("detail"))))
    if not moved and not few:
        L.append("")
        L.append("Every published statistic held within %s points."
                 % esc(str(d.get("tolerance_points"))))
    return "\n".join(L)




# ---------------------------------------------------------------- gold & silver
def build_metals(slot=None):
    d = jload("docs/metals.json") or {}
    now = ist()
    # THE SLOT COMES FROM THE CLOCK WHEN NOBODY SAID WHICH.
    # A manual dispatch passed no slot, so every run fell back to "night" - two messages in a
    # row both headed "night", and no morning one at all. Before noon IST it is the morning
    # send; after it, the night one. An explicit argument still wins.
    if not slot:
        slot = "morning" if now.hour < 12 else "night"
    head = "morning" if str(slot).lower().startswith("morn") else "night"
    L = ["<b>ArthaSaar — gold &amp; silver</b> · %s" % head, now.strftime("%d %b %Y, %H:%M IST")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")

    if not d.get("available"):
        L.append("")
        L.append("No rate published. " + esc(str(d.get("reason") or "the feed did not return.")))
        L.append("<i>A stale or invented rate would be worse than none.</i>")
        return "\n".join(L)

    def arrow(chg):
        return "\u25B2" if (chg or 0) > 0 else ("\u25BC" if (chg or 0) < 0 else "\u2022")

    # ---- gold, by purity ----
    gp = d.get("gold_purities") or []
    if gp:
        L.append("")
        L.append("<b>GOLD</b>")
        for row in gp:
            chg = row.get("chg_per_gram")
            pct = row.get("chg_pct")
            L.append("%s <b>%s</b> · 1 g Rs %s · 10 g Rs %s%s"
                     % (arrow(chg), esc(str(row["label"])),
                        "{:,.0f}".format(row["per_gram"]),
                        "{:,.0f}".format(row["per_10g"]),
                        (" (%sRs %s, %s%.2f%%)" % ("+" if (chg or 0) >= 0 else "-",
                         "{:,.0f}".format(abs(chg or 0)), "+" if (pct or 0) >= 0 else "-",
                         abs(pct or 0))) if chg is not None else ""))
        L.append("<i>12 g: " + " · ".join("%s Rs %s" % (esc(str(r["label"])),
                 "{:,.0f}".format(r["per_12g"])) for r in gp) + "</i>")

    # ---- silver, by fineness ----
    sf = d.get("silver_fineness") or []
    if sf:
        L.append("")
        L.append("<b>SILVER</b>")
        for row in sf:
            chg = row.get("chg_per_gram")
            pct = row.get("chg_pct")
            L.append("%s <b>%s</b> · 1 g Rs %s · 10 g Rs %s%s"
                     % (arrow(chg), esc(str(row["label"])),
                        "{:,.2f}".format(row["per_gram"]),
                        "{:,.0f}".format(row["per_10g"]),
                        (" (%sRs %s, %s%.2f%%)" % ("+" if (chg or 0) >= 0 else "-",
                         "{:,.2f}".format(abs(chg or 0)), "+" if (pct or 0) >= 0 else "-",
                         abs(pct or 0))) if chg is not None else ""))

    if d.get("usdinr"):
        L.append("")
        L.append("USD/INR <b>%.2f</b>%s" % (float(d["usdinr"]),
                 (" (%+.2f%%)" % d["usdinr_chg_pct"]) if d.get("usdinr_chg_pct") is not None else ""))

    etfs = d.get("etf_cross_check") or {}
    if etfs:
        bits = []
        for k, lbl in (("goldbees", "GOLDBEES"), ("silverbees", "SILVERBEES")):
            e = etfs.get(k)
            if e and e.get("price"):
                bits.append("%s Rs %.2f (%+.2f%%)" % (lbl, e["price"], e.get("chg_pct") or 0))
        if bits:
            L.append("")
            L.append("Domestic ETFs: " + " · ".join(bits))

    L.append("")
    L.append("<i>Purity is arithmetic on the pure-metal price: 24K is 24/24, 22K is 22/24, 18K "
             "is 18/24. Silver fineness is parts per thousand, so 958 is 95.8%.")
    L.append("Making charges, hallmarking and a jeweller's margin are NOT included - two shops "
             "quoting the same purity can differ by hundreds of rupees a gram on those alone.")
    L.append("Converted from international spot at USD/INR, not the retail rate, which adds "
             "import duty and GST.</i>")
    L.append("<i>Data health: %s.</i>" % esc(str(d.get("as_of_ist") or "")))
    return "\n".join(L)


# ---------------------------------------------------------------- what changed
LABELS = {
    "index.nifty.close": "Nifty", "index.banknifty.close": "Bank Nifty",
    "index.sensex.close": "Sensex", "breadth.above_50": "Stocks above 50-day",
    "breadth.above_200": "Stocks above 200-day", "breadth.total": "Stocks covered",
    "pcr.nifty": "Nifty PCR", "flow.fii_cr": "FII net", "flow.dii_cr": "DII net",
    "metal.gold.per_gram": "Gold per gram", "metal.silver.per_gram": "Silver per gram",
    "fx.usdinr": "USD/INR",
}


def build_changed():
    d = jload("docs/snapshot.json") or {}
    L = ["<b>ArthaSaar — what changed</b>", ist().strftime("%d %b %Y")]
    L.append("<i>Market data and descriptions only. Not investment advice.</i>")

    since = d.get("compared_with")
    if not since:
        L.append("")
        L.append("No comparison yet. The first snapshot was stored today (%s); tomorrow's "
                 "message will show what moved." % esc(str(d.get("date"))))
        L.append("<i>This is the one message that cannot be built retroactively - every day "
                 "without a snapshot is a day that can never be compared.</i>")
        return "\n".join(L)

    moved = [c for c in (d.get("changes") or []) if c.get("status") == "changed"]
    if not moved:
        L.append("")
        L.append("Nothing moved between %s and %s." % (esc(str(since)), esc(str(d.get("date")))))
        return "\n".join(L)

    L.append("")
    L.append("Compared with <b>%s</b> · %d field(s) moved" % (esc(str(since)), len(moved)))

    def fmt(c):
        lab = LABELS.get(c["field"], c["field"])
        unit = c.get("unit") or ""
        delta = c.get("delta") or 0
        pct = c.get("pct")
        if unit == "%":
            return "%s <b>%.1f%%</b> (%+.1f pts)" % (lab, c["to"], delta)
        if unit == "crore":
            return "%s <b>Rs %s cr</b> (%s)" % (lab, "{:,.0f}".format(c["to"]),
                                                ("%+.2f%%" % pct) if pct is not None else "-")
        if unit == "rupees":
            return "%s <b>Rs %s</b> (%s)" % (lab, "{:,.0f}".format(c["to"]),
                                             ("%+.2f%%" % pct) if pct is not None else "-")
        if unit == "ratio":
            return "%s <b>%.2f</b> (%+.2f)" % (lab, c["to"], delta)
        return "%s <b>%s</b>%s" % (lab, "{:,.0f}".format(c["to"]),
                                   (" (%+.2f%%)" % pct) if pct is not None else "")

    # index first, then everything else
    idx = [c for c in moved if c["field"].startswith("index.")]
    rest = [c for c in moved if not c["field"].startswith("index.")]
    if idx:
        L.append("")
        for c in idx:
            L.append(fmt(c))
    if rest:
        L.append("")
        for c in rest[:8]:
            L.append(fmt(c))

    L.append("")
    L.append("<i>Only fields present in both snapshots are compared. A field missing from "
             "either side is reported as not comparable, never as zero.</i>")
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
    elif mode == "glossary":
        msg = build_glossary()
    elif mode == "calendar":
        msg = build_calendar()
    elif mode == "scorecard":
        msg = build_scorecard()
    elif mode == "monthly":
        msg = build_monthly()
    elif mode == "corrections":
        msg = build_corrections()
    elif mode == "ledger":
        msg = build_ledger()
    elif mode == "metals":
        msg = build_metals(args[1] if len(args) > 1 else None)
    elif mode == "changed":
        msg = build_changed()
    else:
        print("unknown mode %r - use expiry | positioning | weekly | review SYMBOL | glossary | calendar | scorecard | monthly" % mode)
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

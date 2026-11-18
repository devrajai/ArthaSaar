#!/usr/bin/env python3
"""Post "what the data says about tomorrow" to Telegram, after the close.

WHY THIS EXISTS
A trading channel posts "TOMORROW 5% GAP UP — BUY UPL 600CE @2.40, TARGET 8". That is a
specific buy call to the public, which needs SEBI research-analyst or adviser registration,
and it is constructed to be unfalsifiable: no sample size, no base rate, no record.

This sends the same subject matter with the one thing those messages never carry - the
evidence, and how much of it there is.

RULES THIS MESSAGE FOLLOWS
  - every number carries its sample size (n)
  - where the history is too short, it says so instead of printing a number
  - no target, no entry, no "buy", no urgency
  - one line at the end stating what it is not

Missing secrets are a clean skip, never a crash.
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

TOKEN = re.sub(r"\s+", "", os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "")
CHATS = [c.strip() for c in (os.environ.get("TG_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip().split(",") if c.strip()]
DRY = "--dry" in sys.argv

# A base rate below this many cases is noise dressed as a statistic. The site already
# withholds results under 20 matches; this is the stricter bar for a number that goes out
# as a message.
MIN_CASES = 60


def jload(p):
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return None


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def pct(v, dp=1):
    try:
        return ("%." + str(dp) + "f%%") % float(v)
    except Exception:
        return "—"


def rs(v):
    try:
        return "Rs %s" % f"{float(v):,.0f}"
    except Exception:
        return "—"


def ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def build():
    gaps = jload("docs/gaps.json")
    pcr = jload("docs/pcr_signal.json")
    aff = jload("docs/affordable.json")
    asof = jload("docs/data_asof.json") or {}

    day = ist_now().strftime("%d %b %Y")
    lines = ["<b>ArthaSaar — what the data says</b>",
             "%s · after close" % day]
    sess = asof.get("session")
    if sess:
        lines.append("figures from the %s session" % esc(str(sess)))

    # ---------- gaps ----------
    if gaps and gaps.get("fill_rate_up") is not None:
        up = gaps.get("fill_rate_up")
        dn = gaps.get("fill_rate_down")
        sm = gaps.get("samples") or {}
        nu, nd = sm.get("up"), sm.get("down")
        win = sm.get("window")
        lines.append("")
        lines.append("<b>Gaps</b>")
        if nu and nu >= MIN_CASES:
            lines.append("After a gap-up, price came back through the gap within %s sessions "
                         "%s of the time (n=%s)" % (win, pct(up), f"{nu:,}"))
        if nd and nd >= MIN_CASES:
            lines.append("After a gap-down: %s (n=%s)" % (pct(dn), f"{nd:,}"))
        lines.append("<i>A gap is a jump at the open. \"Filled\" means price traded back through "
                     "it. This is what has happened, not what will.</i>")

    # ---------- PCR ----------
    # current is an OBJECT: {date, pcr, band}. The band label is already computed, so this
    # reads it rather than re-deriving it from ranges.
    cur_obj = (pcr or {}).get("current") or {}
    cur = cur_obj.get("pcr")
    if cur is not None:
        trend = (pcr or {}).get("trend") or {}
        lines.append("")
        lines.append("<b>Put-call ratio</b>")
        bits = ["Nifty PCR %.2f" % float(cur)]
        if trend.get("direction_5"):
            bits.append("5-session trend %s" % esc(str(trend["direction_5"])))
        lines.append(" · ".join(bits))

        band_label = cur_obj.get("band")
        band = None
        for b in ((pcr or {}).get("bands") or []):
            if str(b.get("band")) == str(band_label):
                band = b
                break
        if band:
            h21 = next((h for h in (band.get("horizons") or []) if h.get("h") == 21), None)
            if h21 and (h21.get("n") or 0) >= MIN_CASES:
                lines.append("Band <i>%s</i> over 21 sessions: %s up, %s average (n=%s)"
                             % (esc(str(band.get("band"))), pct(h21.get("up_pct")),
                                pct(h21.get("mean_pct"), 2), f"{h21['n']:,}"))
                edge = str(h21.get("edge") or "").strip()
                if edge:
                    lines.append("vs a random session: <b>%s</b>" % esc(edge))
            else:
                lines.append("Not enough history for this band — no number published.")

        # the PCR file itself can be days old; say so rather than let it read as today's
        pdate = str(cur_obj.get("date") or "")
        if pdate:
            try:
                age = (ist_now().date() - datetime.strptime(pdate, "%Y-%m-%d").date()).days
                if age > 3:
                    lines.append("<i>PCR is from %s — %d days old, not this session.</i>"
                                 % (esc(pdate), age))
            except Exception:
                pass

    # ---------- cheap options: PAUSED ----------
    # This listed named strikes with premiums, which reads as a pick. Replaced below with the
    # cost of one lot and what a 1% index move means in rupees - no names, no ranking.
    if False and aff and aff.get("buckets"):   # PAUSED: named strikes with prices
        br = aff.get("base_rates") or {}
        exp = aff.get("nearest_expiry")
        lines.append("")
        lines.append("<b>Cheapest liquid options</b>" + (" · %s expiry" % esc(str(exp)) if exp else ""))
        picked = []
        for bucket in aff["buckets"][:2]:
            rows = [r for r in (bucket.get("rows") or [])
                    if r.get("expiry_known") and (r.get("oi") or 0) > 0]
            rows.sort(key=lambda r: -(r.get("oi") or 0))
            picked.extend(rows[:2])
        for r in picked[:4]:
            lines.append("%s %s %s · premium Rs %s × lot %s = <b>%s</b> per lot"
                         % (esc(r.get("symbol")), f"{r.get('strike'):,.0f}", esc(r.get("type")),
                            r.get("premium"), r.get("lot"), rs(r.get("cost_per_lot"))))
        if br.get("insufficient_history"):
            lines.append("<i>Doubling rate withheld: only %s sessions stored, %s needed. "
                         "A cheap premium is not a discount — it is the market's price for "
                         "likely expiring worthless.</i>"
                         % (br.get("sessions"), br.get("needed")))
        else:
            lines.append("<i>A cheap premium is not a discount.</i>")

    # ---------- what one lot costs, without naming a strike ----------
    # This replaced a list of named strikes with premiums. That list read as a pick; a lot-size
    # calculation does not. No names, no ranking, no "cheapest".
    try:
        aff2 = jload("docs/affordable.json") or {}
        lot = None
        for b in (aff2.get("buckets") or []):
            if b.get("min_cost") == 0:
                for row in (b.get("rows") or []):
                    if str(row.get("symbol")) == "NIFTY" and row.get("lot"):
                        lot = row
                        break
            if lot:
                break
        if lot:
            lotn = float(lot.get("lot") or 0)
            prem = float(lot.get("premium") or 0)
            lines.append("")
            lines.append("<b>What a lot costs</b>")
            lines.append("One Nifty lot is <b>%s</b> shares. At a premium of Rs %s that is "
                         "<b>Rs %s</b> leaving your account, not Rs %s."
                         % (int(lotn), prem, "{:,.0f}".format(prem * lotn), prem))
            lines.append("<i>Options can lose the whole premium. A low price is not a discount "
                         "- it is the market's estimate of expiring worthless.</i>")
    except Exception as _e:
        print("lot-cost section skipped: %s: %s" % (type(_e).__name__, str(_e)[:90]))

    # ---------- the line that makes it honest ----------
    lines.append("")
    lines.append("<b>Not a call.</b> No target, no entry, no recommendation. Every figure "
                 "carries its sample size, and where history is too short this message says so "
                 "instead of printing a number. Educational only.")

    return "\n".join(lines)


def main():
    msg = build()
    print("message length=%d chats=%d" % (len(msg), len(CHATS)))
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
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)

#!/usr/bin/env python3
"""Investor presentations and concalls - where capacity, volumes and segment data live.

WHY THIS EXISTS
A price chart says a stock fell. Quarterly results say margin slipped. Neither says WHY. The
answer is usually in the company's own investor presentation: new capacity coming, a segment
shrinking, a plant commissioning date, a volume number.

This is the layer that turns "margins fell" into "margins fell while 15 lakh tonnes of new
capacity was being commissioned" - which is the difference between a data page and an analysis.

SOURCE
NSE corporate announcements. In a typical four-day window there are ~3,500 filings, of which
roughly 260 are investor presentations and 670 are analyst or concall updates. Each carries a
PDF link on nsearchives, and the text extracts cleanly.

WHAT IT EXTRACTS
Not the whole document - that would be noise. It pulls SENTENCES that contain both a quantity
and a capacity-style unit: tonnes, MT, lakh tonnes, MW, GW, sq ft, stores, units, KL, MTPA.
Each is stored with the company, the filing date and the PDF link, so any claim can be traced
back to the page it came from.

WHAT IT DOES NOT DO
It does not summarise or interpret. It does not merge these figures into our own computed
numbers, because a company's statement about its own capacity is a claim, not a measurement.
Every row is presented as the company's words.
"""
import io, json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*",
      "Referer": "https://www.nseindia.com/"}
ANN = ("https://www.nseindia.com/api/corporate-announcements"
       "?index=equities&from_date=%s&to_date=%s")
ARCHIVE = "data/presentations/facts.parquet"
OUT = "docs/presentations.json"

WANT = ("investor presentation", "analyst", "con. call", "concall", "earnings call",
        "investor meet", "presentation")

# a quantity followed by a capacity-style unit, or a unit followed by a quantity
UNIT = (r"(lakh\s*(?:tonnes?|tons?|mtpa)|million\s*(?:tonnes?|tons?|mtpa)|mtpa|"
        r"tonnes?\s*per\s*annum|tonnes?|tons?|mega\s*watts?|mw|giga\s*watts?|gw|"
        r"sq\.?\s*ft|square\s*feet|kilolitres?|kl|stores?|outlets?|screens?|"
        r"crore\s*units|lakh\s*units|units?\s*per\s*annum)")
PATTERNS = [
    re.compile(r"[^.\n]{0,220}?\b\d[\d,\.]*\s*(?:%s)\b[^.\n]{0,220}" % UNIT, re.I),
    re.compile(r"[^.\n]{0,220}?\b%s\b[^.\n]{0,40}?\d[\d,\.]*[^.\n]{0,220}" % UNIT, re.I),
]
KEYWORDS = ("capacity", "capacit", "commission", "expansion", "greenfield", "brownfield",
            "plant", "volume", "production", "installed", "store", "outlet", "order book")


def nse_get(url, timeout=45, retries=3):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            time.sleep(attempt * 2)
    return None


def announcements(days_back=7):
    to_d = datetime.now(timezone.utc).date()
    from_d = to_d - timedelta(days=days_back)
    url = ANN % (from_d.strftime("%d-%m-%Y"), to_d.strftime("%d-%m-%Y"))
    raw = nse_get(url, timeout=90)
    if not raw:
        return []
    try:
        return json.loads(raw.decode("utf-8", "replace")) or []
    except Exception:
        return []


def extract_text(pdf_bytes, max_pages=40):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pages = min(doc.page_count, max_pages)
        return "\n".join(doc[i].get_text() for i in range(pages))
    except Exception:
        return None


def facts_from(text, symbol, date, pdf):
    """Sentences that pair a quantity with a capacity-style unit AND a capacity keyword."""
    out, seen = [], set()
    for para in re.split(r"(?<=[.!?])\s+|\n{2,}", text):
        p = re.sub(r"\s+", " ", para).strip()
        if not (12 < len(p) < 420):
            continue
        low = p.lower()
        if not any(k in low for k in KEYWORDS):
            continue
        if not any(pat.search(p) for pat in PATTERNS):
            continue
        key = p[:90].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"symbol": symbol, "date": date, "pdf": pdf, "sentence": p})
        if len(out) >= 12:
            break
    return out


def main():
    import pandas as pd

    limit = int(os.environ.get("PRESENTATION_LIMIT", "40"))
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "by_company": [], "recent": [], "note": ""}

    anns = announcements(int(os.environ.get("ANNOUNCEMENT_DAYS", "7")))
    if not anns:
        out["note"] = "NSE announcements returned nothing - the endpoint may have changed."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("presentations: no announcements")
        return 0

    picks = []
    for a in anns:
        desc = str(a.get("desc") or a.get("attchmntText") or "").lower()
        if not any(w in desc for w in WANT):
            continue
        pdf = a.get("attchmntFile")
        if not pdf or not str(pdf).lower().endswith(".pdf"):
            continue
        # a real deck, not a one-page letter: "investor presentation" ranks above a meet
        # intimation, and anything under 20 KB is almost certainly a cover note
        rank = 0 if "investor presentation" in desc else 1
        try:
            size = float(str(a.get("attFileSize") or "0").split()[0])
        except Exception:
            size = 0
        if size and size < 20:
            continue
        picks.append((rank, size, a))
    picks.sort(key=lambda t: (t[0], -t[1]))
    picks = [a for _, _, a in picks]
    print("announcements: %d, of which presentations/con-calls with a PDF: %d"
          % (len(anns), len(picks)))

    seen_pdf, rows, done = set(), [], 0
    for a in picks:
        if done >= limit:
            break
        pdf = a["attchmntFile"]
        if pdf in seen_pdf:
            continue
        seen_pdf.add(pdf)
        raw = nse_get(pdf, timeout=60)
        if not raw:
            continue
        text = extract_text(raw)
        done += 1
        if done % 10 == 0:
            print("  %d/%d processed, %d facts" % (done, limit, len(rows)))
        if not text:
            continue
        f = facts_from(text, a.get("symbol") or "?", str(a.get("an_dt") or "")[:11], pdf)
        rows.extend(f)
        time.sleep(0.3)

    if not rows:
        out["note"] = ("No capacity-style sentences found. The PDFs may be image-only, or the "
                       "filing window had no presentations with figures.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("presentations: no facts extracted from %d PDFs" % done)
        return 0

    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    df = pd.DataFrame(rows)
    if os.path.exists(ARCHIVE):
        try:
            df = pd.concat([pd.read_parquet(ARCHIVE), df], ignore_index=True)
            df = df.drop_duplicates(subset=["symbol", "sentence"])
        except Exception:
            pass
    df.to_parquet(ARCHIVE, index=False)
    print("-> %s  %d rows" % (ARCHIVE, len(df)))

    by = {}
    for r in rows:
        by.setdefault(r["symbol"], []).append(r)
    for sym, fs in sorted(by.items(), key=lambda x: -len(x[1]))[:20]:
        out["by_company"].append({"symbol": sym, "facts": len(fs),
                                  "examples": [f["sentence"][:300] for f in fs[:3]]})
    out["recent"] = [{"symbol": r["symbol"], "date": r["date"], "sentence": r["sentence"][:300]}
                     for r in rows[:20]]
    out["count"] = len(rows)
    out["note"] = ("Sentences lifted from investor presentations and concall filings, each with "
                   "the PDF it came from. A company's statement about its own capacity is a "
                   "claim, not a measurement, and is never merged into our computed figures.")
    out["cautions"] = {
        "claim": "These are the company's own words, not verified by us.",
        "coverage": ("Only filings in the last few days, and only PDFs with machine-readable "
                     "text - image-only decks yield nothing."),
        "extraction": ("Pattern matching on sentences containing a capacity keyword and a unit. "
                       "It can pick up a wrong sentence; the PDF link is stored so it can be checked."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB  |  %d facts from %d companies"
          % (OUT, os.path.getsize(OUT) / 1024, out["count"], len(by)))
    for c in out["by_company"][:4]:
        print("   %-12s %d facts | %s" % (c["symbol"], c["facts"], c["examples"][0][:90]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("::warning title=Presentations failed::%s: %s" % (type(e).__name__, str(e)[:120]))
        sys.exit(0)

#!/usr/bin/env python3
"""
build_wikidata.py - founders, founding year, subsidiaries and parent, from Wikidata.

Yahoo's profile has the current officers and a business description but no founder and no
acquisition history. Wikidata has both as structured statements:
    P112  founded by            P571  inception
    P355  subsidiary            P749  parent organisation
    P1830 owner of              P159  headquarters

Resolution is by Wikipedia search first, because Wikidata's English label is often longer than
the name we hold ("Reliance Industries Limited" vs "Reliance Industries"). The search picks the
article, and the article's wikibase_item is the entity.

Honest limits: Wikidata is community-edited, so a fact can be missing, stale or wrong, and it is
cited as a source rather than presented as verified. Its CEO field in particular lags reality -
Yahoo's officer list is used for that instead. Subsidiary lists are the ones editors recorded,
which is not the same as a complete list of acquisitions.

Usage
-----
  python scripts/build_wikidata.py
  python scripts/build_wikidata.py --limit 80 --sleep 0.3

Output: docs/company_origin.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/company_origin.json"
STOCKS = "docs/stocks.json"
FUND = "docs/fundamentals.json"
SCREENER = "docs/screener.json"
INDICES = "docs/indices.json"
UA = {"User-Agent": "ArthaSaar/1.0 (educational project; arthasaar.app)"}
WD = "https://query.wikidata.org/sparql"
WP = "https://en.wikipedia.org/w/api.php"

SUFFIX = ("LIMITED", "LTD", "PRIVATE", "PVT", "INDIA", "INDUSTRIES", "INDUSTRIAL",
          "SERVICES", "TECHNOLOGIES", "TECHNOLOGY", "CORPORATION", "CORP", "COMPANY",
          "ENTERPRISES", "HOLDINGS", "GROUP", "AND", "&")


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def _get(url, timeout=45):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                             timeout=timeout).read())


def _sparql(query, timeout=60):
    return _get(WD + "?" + urllib.parse.urlencode({"format": "json", "query": query}), timeout=timeout)


def _search(name, india=False):
    """EntitySearch on Wikidata itself - one endpoint, so no Wikipedia rate limit."""
    esc = name.replace('"', '\\"')
    q = '''SELECT DISTINCT ?item ?itemLabel ?desc WHERE {
      SERVICE wikibase:mwapi {
        bd:serviceParam wikibase:api "EntitySearch" ;
                        wikibase:endpoint "www.wikidata.org" ;
                        mwapi:search "%s" ;
                        mwapi:language "en" .
        ?item wikibase:apiOutputItem mwapi:item .
      }
      ?item wdt:P31/wdt:P279* wd:Q43229 .
      OPTIONAL { ?item schema:description ?desc . FILTER(lang(?desc)="en") }
      %s
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    } LIMIT 15''' % (esc, "?item wdt:P17 wd:Q668 ." if india else "")
    try:
        d = _sparql(q)
    except Exception:
        return []
    out = []
    for b in d["results"]["bindings"]:
        out.append({
            "qid": b["item"]["value"].split("/")[-1],
            "label": b.get("itemLabel", {}).get("value", ""),
            "desc": (b.get("desc", {}).get("value", "") or "").lower(),
        })
    return out


BAD = ("subsidiary", "foundation", "consulting", "trust", "charity", "award", "river",
       "musician", "film", "village", "city", "town")


def resolve(name):
    """Company name -> Wikidata QID, choosing the entity whose label actually matches.

    EntitySearch happily returns 'Infosys Consulting' and 'Infosys Foundation' ahead of
    'Infosys' itself, and 'Trent' as a river in Ontario. So the result is scored: an exact label
    match wins, then a label that starts with the name, and anything described as a subsidiary,
    foundation or place is pushed down."""
    target = name.lower().strip()
    for india in (False, True):
        hits = _search(name, india=india)
        if not hits:
            continue
        def score(h):
            lab = (h["label"] or "").lower().strip()
            s = 0
            if lab == target:
                s += 100
            elif lab.startswith(target):
                s += 60 - min(40, len(lab) - len(target))
            elif target in lab:
                s += 30
            if any(b in h["desc"] for b in BAD):
                s -= 70
            return s
        hits.sort(key=score, reverse=True)
        best = hits[0]
        if score(best) >= 30:
            return best["qid"], best["label"]
    return None, None


def facts(qid):
    sparql = '''SELECT
     (GROUP_CONCAT(DISTINCT ?fL; separator="|") AS ?founders)
     (GROUP_CONCAT(DISTINCT ?sL; separator="|") AS ?subs)
     (GROUP_CONCAT(DISTINCT ?pL; separator="|") AS ?parents)
     (GROUP_CONCAT(DISTINCT ?oL; separator="|") AS ?owns)
     (SAMPLE(?inc) AS ?inception)
     (SAMPLE(?hqL) AS ?hq)
    WHERE {
     OPTIONAL { wd:%(q)s wdt:P112 ?f . ?f rdfs:label ?fL . FILTER(lang(?fL)="en") }
     OPTIONAL { wd:%(q)s wdt:P355 ?s . ?s rdfs:label ?sL . FILTER(lang(?sL)="en") }
     OPTIONAL { wd:%(q)s wdt:P749 ?p . ?p rdfs:label ?pL . FILTER(lang(?pL)="en") }
     OPTIONAL { wd:%(q)s wdt:P1830 ?o . ?o rdfs:label ?oL . FILTER(lang(?oL)="en") }
     OPTIONAL { wd:%(q)s wdt:P571 ?inc }
     OPTIONAL { wd:%(q)s wdt:P159 ?hq . ?hq rdfs:label ?hqL . FILTER(lang(?hqL)="en") }
    }''' % {"q": qid}
    try:
        d = _get(WD + "?" + urllib.parse.urlencode({"format": "json", "query": sparql}), timeout=60)
        b = d["results"]["bindings"][0]
    except Exception:
        return None
    def g(k):
        v = b.get(k, {}).get("value")
        return v if v else None
    def split(k):
        v = g(k)
        return [x.strip() for x in v.split("|") if x.strip()] if v else []
    inc = g("inception")
    return {
        "qid": qid,
        "founders": split("founders")[:6],
        "subsidiaries": split("subs")[:12],
        "parents": split("parents")[:4],
        "owns": split("owns")[:8],
        "inception": inc[:10] if inc else None,
        "hq": g("hq"),
    }


def summary(title):
    """The article's opening paragraph - the history in prose."""
    try:
        d = _get("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                 urllib.parse.quote(title.replace(" ", "_")), timeout=30)
        return (d.get("extract") or "")[:600] or None
    except Exception:
        return None


def clean(name):
    """'Tata Consultancy Services Limited' -> 'Tata Consultancy Services'."""
    n = str(name or "").strip()
    n = re.sub(r"\s+(LIMITED|LTD\.?|PRIVATE|PVT\.?|LIM\.?)$", "", n, flags=re.I)
    n = re.sub(r"\s+(INDIA|INDUSTRIES|INDUSTRIAL|SERVICES|TECHNOLOGIES|CORPORATION|CORP\.?)$", "", n, flags=re.I)
    return n.strip(" ,.-")


def pick(limit):
    """Order matters. The Nifty 50 first, because a large listed company is the one most likely
    to have a Wikipedia article and the one a reader is most likely to open. Small caps come
    last - most of them have no article at all, and a run that starts with them wastes every
    request."""
    names = {}
    ix = _load(INDICES) or {}
    for i in (ix.get("indices") or []):
        if i.get("id") == "nifty50":
            for c in (i.get("constituents") or []):
                if c.get("symbol"):
                    names[c["symbol"] + ".NS"] = c.get("name") or c["symbol"]
            break
    st = _load(STOCKS) or {}
    for k, v in (st.get("stocks") or {}).items():
        if v and v.get("name"):
            names.setdefault(v.get("symbol") or k, v["name"])
    scr = _load(SCREENER) or {}
    for r in sorted((scr.get("rows") or []), key=lambda r: -(r.get("mcap") or 0)):
        if r.get("symbol") and r.get("name"):
            names.setdefault(r["symbol"] + ".NS", r["name"])

    out = [(s, clean(n)) for s, n in names.items() if n and len(clean(n)) > 3]
    return out[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=90)
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    pairs = pick(args.limit)
    print(f"resolving {len(pairs)} company name(s)")

    out, failed = {}, []
    for i, (sym, name) in enumerate(pairs, 1):
        qid, title = resolve(name)
        if not qid:
            failed.append(sym)
            continue
        f = facts(qid)
        if f and (f.get("founders") or f.get("inception") or f.get("subsidiaries")):
            f["title"] = title
            f["history"] = summary(title)
            out[sym] = f
        else:
            failed.append(sym)
        import time as _t; _t.sleep(args.sleep)
        if i % 20 == 0:
            print(f"  {i}/{len(pairs)} kept {len(out)}")

    if not out:
        print("nothing resolved - leaving the existing file alone")
        return 0

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(out),
        "note": ("Founders, founding date, subsidiaries and parent organisation from Wikidata, "
                 "with the Wikipedia article's opening paragraph as the history. Wikidata is "
                 "community-edited: a fact can be missing, stale or wrong, and its CEO field in "
                 "particular lags reality - current officers come from Yahoo, not here. The "
                 "subsidiary list is what editors recorded, which is not a complete list of "
                 "acquisitions."),
        "source": "Wikidata (CC0) and Wikipedia (CC BY-SA)",
        "failed": failed[:40],
        "companies": out,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"\n-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(out)} companies")
    return 0


if __name__ == "__main__":
    sys.exit(main())

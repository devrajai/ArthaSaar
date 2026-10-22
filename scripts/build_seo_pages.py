#!/usr/bin/env python3
"""Shareable per-stock pages, sitemap and robots (Task 12).

Each stock gets docs/stock/<SYMBOL>.html with its own title, description and Open Graph
tags so it can be shared and indexed. The pages read ../stocks.json at runtime instead of
duplicating the data into every file, so they stay small.

Each page also renders its core facts with NO JavaScript, so a crawler that does not run
scripts still sees a real title, price and link rather than an empty shell.
"""
import json, os, sys, html
from urllib.parse import quote
from datetime import datetime, timezone

SITE = "https://devrajai.github.io/ArthaSaar/"
OUTDIR = "docs/stock"


def esc(t):
    return html.escape(str(t if t is not None else ""), quote=True)


def money(v):
    try:
        return "{:,.2f}".format(float(v))
    except Exception:
        return ""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="ArthaSaar">
<meta name="twitter:card" content="summary">
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f7f8fa;color:#111827}}
.wrap{{max-width:760px;margin:0 auto;padding:24px}}
a{{color:#1d4ed8}}
h1{{font-size:24px;margin:0 0 4px}}
.sub{{color:#6b7280;font-size:14px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden}}
td{{padding:9px 12px;border-bottom:1px solid #eef0f3;font-size:14px}}
td:first-child{{color:#6b7280;width:44%}}
.back{{display:inline-block;margin-top:18px;font-size:14px}}
</style>
</head>
<body>
<div class="wrap">
  <h1>{name}</h1>
  <div class="sub">{sym} &middot; {sector}</div>
  <table>
    <tr><td>Last close</td><td><b>{close}</b></td></tr>
    <tr><td>Day change</td><td>{chg}</td></tr>
    <tr><td>Data as of</td><td>{asof}</td></tr>
  </table>
  <a class="back" href="../index.html#stocks">&larr; Back to ArthaSaar</a>
</div>
<script>
// Progressive enhancement only: the table above already carries the facts for crawlers.
fetch("../stocks.json").then(function(r){{return r.json();}}).then(function(d){{
  var s=(d.stocks||{{}})["{key}"]; if(!s) return;
  var rows=document.querySelectorAll("table tr");
  var t=s.tech||{{}};
  Object.keys(t).slice(0,6).forEach(function(k){{
    var tr=document.createElement("tr");
    tr.innerHTML="<td>"+k.replace(/_/g," ")+"</td><td>"+t[k]+"</td>";
    document.querySelector("table").appendChild(tr);
  }});
}}).catch(function(){{}});
</script>
</body>
</html>
"""


def main():
    try:
        stocks = json.load(open("docs/stocks.json"))["stocks"]
    except Exception:
        print("seo pages: no stocks.json")
        return 0
    asof = ""
    try:
        asof = json.load(open("docs/data.json")).get("generated_utc", "")[:10]
    except Exception:
        pass

    os.makedirs(OUTDIR, exist_ok=True)
    urls = []
    n = 0
    for key, st in stocks.items():
        sym = st.get("symbol") or key.split(".")[0]
        name = st.get("name") or sym
        chg = st.get("chg_pct")
        title = "%s share price and technicals - ArthaSaar" % sym
        desc = ("%s (%s): last close %s, day change %s. Technicals, fundamentals and sector "
                "context, from free NSE and Yahoo data." % (name, sym, money(st.get("close")),
                ("%+.2f%%" % chg) if isinstance(chg, (int, float)) else "n/a"))
        # M&MFIN, M&M and J&KBANK contain "&", which is illegal raw in a URL and in XML.
        # Percent-encode the path segment, and XML-escape the whole URL when it is written.
        url = SITE + "stock/" + quote(sym, safe="") + ".html"
        body = PAGE.format(
            title=esc(title), desc=esc(desc), url=esc(url), name=esc(name), sym=esc(sym),
            sector=esc(st.get("sector") or "—"), key=esc(key),
            close=esc(money(st.get("close"))) or "—",
            chg=esc(("%+.2f%%" % chg) if isinstance(chg, (int, float)) else "—"),
            asof=esc(asof or "—"))
        with open(os.path.join(OUTDIR, sym + ".html"), "w", encoding="utf-8") as fh:
            fh.write(body)
        urls.append((url, asof))
        n += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          "  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(SITE), now)]
    for u, d in urls:
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(u), d or now))
    sm.append("</urlset>")
    with open("docs/sitemap.xml", "w", encoding="utf-8") as fh:
        fh.write("\n".join(sm))
    with open("docs/robots.txt", "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % SITE)
    print("seo: %d stock pages + sitemap (%d urls) + robots.txt" % (n, len(urls) + 1))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)

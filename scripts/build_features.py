#!/usr/bin/env python3
"""
ARTHASAAR - feature data builder (free sources only).

Produces, into docs/:
  sector_rotation.json  (8) sector relative strength vs Nifty, 1/3/6/12 months
  rebalance.json        (5) Next-50 -> Nifty-50 promotion watch (liquidity + momentum)
  rollover.json         (4) stock-futures rollover % (next expiry share of OI)
  corp_actions.json     (3) splits / dividends for the Nifty 50 (chart adjustment)
  delivery.json         (1) delivery % + accumulation score

Sources: NSE bhavcopy (CM + FO), NSE sec_bhavdata_full, NSE index CSVs, Yahoo Finance.
Every block is wrapped so one dead feed never kills the rest.
"""
import csv, io, json, urllib.request, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOCS = Path("docs")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
NOW = datetime.now(timezone.utc)


def http(url, timeout=45):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    return urllib.request.urlopen(r, timeout=timeout).read()


def last_days(n=10):
    d = []
    for i in range(n):
        d.append((NOW - timedelta(days=i)).strftime("%Y%m%d"))
    return d


def delivery_rows():
    """sec_bhavdata_full - has DELIV_QTY / DELIV_PER."""
    for d in last_days(6):
        dd = f"{d[6:8]}{d[4:6]}{d[0:4]}"
        try:
            raw = http(f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}.csv").decode("utf-8", "replace")
            return list(csv.DictReader(io.StringIO(raw))), dd
        except Exception as e:
            print("  delivery skip", dd, e)
    return [], None


def fo_rows():
    """FO bhavcopy - has XpryDt + OpnIntrst for FUTSTK."""
    for d in last_days(4):
        try:
            raw = http(f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip")
            z = zipfile.ZipFile(io.BytesIO(raw))
            name = [n for n in z.namelist() if n.endswith(".csv")][0]
            return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8", "replace")))), d
        except Exception as e:
            print("  fo skip", d, e)
    return [], None


def nse_list(name):
    """NSE index constituent CSV -> list of symbols."""
    try:
        raw = http(f"https://nsearchives.nseindia.com/content/indices/ind_{name}list.csv").decode("utf-8", "replace")
        out = []
        for row in csv.DictReader(io.StringIO(raw)):
            s = (row.get("Symbol") or "").strip()
            if s:
                out.append(s)
        return out
    except Exception as e:
        print("  list fail", name, e)
        return []


# ---------------------------------------------------------------- 1) delivery
def build_delivery(rows, dd):
    if not rows:
        return
    items = []
    for r in rows:
        try:
            if (r.get(" SERIES") or r.get("SERIES") or "").strip() != "EQ":
                continue
            sym = (r.get("SYMBOL") or "").strip()
            deliv = float((r.get(" DELIV_PER") or r.get("DELIV_PER") or "0").strip() or 0)
            close = float((r.get(" CLOSE_PRICE") or r.get("CLOSE_PRICE") or "0").strip() or 0)
            prev = float((r.get(" PREV_CLOSE") or r.get("PREV_CLOSE") or "0").strip() or 0)
            turn = float((r.get(" TURNOVER_LACS") or r.get("TURNOVER_LACS") or "0").strip() or 0)
            if not sym or close <= 0 or prev <= 0 or turn <= 0:
                continue
            chg = (close - prev) / prev * 100
            items.append({"s": sym, "c": round(close, 2), "chg": round(chg, 2),
                          "d": round(deliv, 1), "t": round(turn, 1)})
        except Exception:
            continue
    if not items:
        return
    turns = sorted(x["t"] for x in items)
    hi = turns[int(len(turns) * 0.8)] if turns else 0
    for x in items:
        sc = 0
        d = x["d"]
        sc += 4 if d >= 60 else 3 if d >= 40 else 2 if d >= 25 else 1 if d >= 15 else 0
        c = x["chg"]
        sc += 3 if c > 2 else 2 if c > 0 else 0
        sc += 3 if x["t"] >= hi else 1 if x["t"] >= hi * 0.5 else 0
        x["score"] = sc
    items.sort(key=lambda x: (-x["score"], -x["d"]))
    json.dump({"updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "date": dd,
               "count": len(items), "items": items,
               "note": "Delivery % = share of traded quantity that actually changed hands (taken for delivery). Score 0-10 = delivery weight + price direction + turnover rank. High delivery with a rising price is the cleanest accumulation read; a low-delivery spike is usually intraday churn."},
              open(DOCS / "delivery.json", "w"), separators=(",", ":"))
    print("delivery:", len(items), "symbols")


# ---------------------------------------------------------------- 4) rollover
def build_rollover(rows, d):
    if not rows:
        return
    by = {}
    for r in rows:
        try:
            if (r.get("FinInstrmTp") or "") not in ("STF","FUTSTK"):
                continue
            sym = r.get("TckrSymb")
            exp = r.get("XpryDt")
            oi = float(r.get("OpnIntrst") or 0)
            if not sym or not exp:
                continue
            by.setdefault(sym, {})[exp] = by.setdefault(sym, {}).get(exp, 0) + oi
        except Exception:
            continue
    out = []
    for sym, exps in by.items():
        ks = sorted(exps)
        if len(ks) < 2:
            continue
        near, nxt = exps[ks[0]], exps[ks[1]]
        tot = near + nxt
        if tot <= 0:
            continue
        out.append({"s": sym, "near": round(near / 1e5, 1), "next": round(nxt / 1e5, 1),
                    "roll": round(nxt / tot * 100, 1), "exp": ks[0]})
    out.sort(key=lambda x: -x["roll"])
    if not out:
        return
    json.dump({"updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "date": d, "count": len(out),
               "items": out[:60],
               "note": "Rollover % = share of a stock's futures open interest already sitting in the next expiry. High rollover means positions are being carried forward with conviction; low rollover means they are being squared off."},
              open(DOCS / "rollover.json", "w"), separators=(",", ":"))
    print("rollover:", len(out), "symbols")


# ---------------------------------------------------------------- 8) sectors
def build_rotation():
    try:
        import yfinance as yf
    except Exception as e:
        print("  no yfinance", e); return
    syms = {"^NSEI": "NIFTY", "^NSEBANK": "BANK", "^CNXIT": "IT", "^CNXAUTO": "AUTO",
            "^CNXPHARMA": "PHARMA", "^CNXFMCG": "FMCG", "^CNXMETAL": "METAL",
            "^CNXENERGY": "ENERGY", "^CNXREALTY": "REALTY", "^CNXINFRA": "INFRA"}
    try:
        df = yf.download(list(syms.keys()), period="14mo", interval="1d",
                         group_by="ticker", threads=True, progress=False, auto_adjust=True)
    except Exception as e:
        print("  yf fail", e); return
    def ret(k, n):
        try:
            c = df[k]["Close"].dropna()
            if len(c) < n + 1: return None
            return (float(c.iloc[-1]) / float(c.iloc[-1 - n]) - 1) * 100
        except Exception:
            return None
    rows = []
    base = {n: ret("^NSEI", n) for n in (21, 63, 126, 252)}
    for k, nm in syms.items():
        if nm == "NIFTY":
            continue
        r = {f"r{n}": ret(k, n) for n in (21, 63, 126, 252)}
        if r["r63"] is None:
            continue
        rs = {n: (r[f"r{n}"] - base[n]) if (r[f"r{n}"] is not None and base[n] is not None) else None
              for n in (21, 63, 126, 252)}
        rows.append({"s": nm, "r1": r["r21"], "r3": r["r63"], "r6": r["r126"], "r12": r["r252"],
                     "rs1": rs[21], "rs3": rs[63], "rs6": rs[126], "rs12": rs[252]})
    rows.sort(key=lambda x: -(x["rs3"] or -999))
    json.dump({"updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "bench": "NIFTY 50",
               "bench_r": {"1m": base[21], "3m": base[63], "6m": base[126], "12m": base[252]},
               "count": len(rows), "items": rows,
               "note": "Relative strength = sector return minus Nifty return over the same window. Positive means the sector is beating the index. Leaders on 3m with improving 1m are usually early in a rotation; leaders fading on 1m are late."},
              open(DOCS / "sector_rotation.json", "w"), separators=(",", ":"))
    print("rotation:", len(rows), "sectors")


# ---------------------------------------------------------------- 3) corp actions
def build_corp_actions():
    try:
        import yfinance as yf
    except Exception:
        return
    syms = nse_list("nifty50")
    if not syms:
        print("  no nifty50 list"); return
    out = []
    for s in syms:
        try:
            t = yf.Ticker(s + ".NS")
            h = t.history(period="2y", interval="1d", auto_adjust=False)
            if h is None or not len(h):
                continue
            for idx, row in h.iterrows():
                sp = row.get("Stock Splits", 0) or 0
                dv = row.get("Dividends", 0) or 0
                if sp and sp > 0:
                    out.append({"s": s, "d": str(idx.date()), "k": "split", "v": round(float(sp), 4)})
                if dv and dv > 0:
                    out.append({"s": s, "d": str(idx.date()), "k": "dividend", "v": round(float(dv), 2)})
        except Exception:
            continue
    out.sort(key=lambda x: x["d"], reverse=True)
    json.dump({"updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": len(out),
               "items": out[:200],
               "note": "Splits and dividends for the Nifty 50 over 2 years, from Yahoo's own corporate-action fields. A split ratio of 10 means 1 share became 10, so older prices must be divided by 10 before you compare them - otherwise every chart and backtest across that date is wrong."},
              open(DOCS / "corp_actions.json", "w"), separators=(",", ":"))
    print("corp actions:", len(out))


# ---------------------------------------------------------------- 5) rebalance
def build_rebalance():
    try:
        import yfinance as yf
    except Exception:
        return
    cand = nse_list("niftynext50")
    if not cand:
        print("  no next50 list"); return
    try:
        df = yf.download([s + ".NS" for s in cand], period="7mo", interval="1d",
                         group_by="ticker", threads=True, progress=False, auto_adjust=True)
    except Exception as e:
        print("  yf fail", e); return
    rows = []
    for s in cand:
        k = s + ".NS"
        try:
            c = df[k]["Close"].dropna()
            v = df[k]["Volume"].dropna()
            if len(c) < 100: continue
            r6 = (float(c.iloc[-1]) / float(c.iloc[0]) - 1) * 100
            adtv = float((c.tail(120) * v.tail(120)).mean()) / 1e7  # Rs crore
            rows.append({"s": s, "r6": round(r6, 1), "adtv": round(adtv, 1),
                         "turn": round(adtv * 1.0, 1)})
        except Exception:
            continue
    if not rows:
        return
    rows.sort(key=lambda x: -(x["adtv"]))
    for i, x in enumerate(rows):
        x["lq"] = i + 1
    rows.sort(key=lambda x: -((x["r6"] or 0) * 0.5 + (x["adtv"] or 0) * 0.5))
    json.dump({"updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": len(rows),
               "items": rows[:40],
               "note": "Promotion watch, not a prediction: candidates ranked by 6-month return and average daily traded value (liquidity). NSE's actual review also uses free-float market cap, which no free feed gives cleanly - so treat this as 'who is knocking on the door', not a guaranteed inclusion list."},
              open(DOCS / "rebalance.json", "w"), separators=(",", ":"))
    print("rebalance:", len(rows))


def main():
    DOCS.mkdir(exist_ok=True)
    for name, fn in [("delivery", None), ("rollover", None), ("rotation", build_rotation),
                     ("corp", build_corp_actions), ("rebalance", build_rebalance)]:
        try:
            if name == "delivery":
                rows, dd = delivery_rows(); build_delivery(rows, dd)
            elif name == "rollover":
                rows, d = fo_rows(); build_rollover(rows, d)
            else:
                fn()
        except Exception as e:
            print("FAILED", name, e)


if __name__ == "__main__":
    main()

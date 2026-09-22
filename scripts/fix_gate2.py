#!/usr/bin/env python3
"""fix_gate2.py - remove market-hours extension: plain 6h validity everywhere.
During 9-3:30, if 6h elapsed, gate asks once (then valid again for 6h). Idempotent."""

OLD = '''  var SIX_H = 6 * 3600 * 1000;
  function gateExp(t) {
    var e = t + SIX_H, d = new Date(e), m = d.getHours() * 60 + d.getMinutes();
    if (m >= 540 && m <= 930) { d.setHours(15); d.setMinutes(31); d.setSeconds(0); d.setMilliseconds(0); e = d.getTime(); }
    return e;
  }
  var ok = false;
  try { var gt = parseInt(localStorage.getItem("mb-gate-ts") || "0", 10); if (gt) ok = Date.now() < gateExp(gt); } catch (e) {}'''
NEW = '''  var SIX_H = 6 * 3600 * 1000;
  var ok = false;
  try { var gt = parseInt(localStorage.getItem("mb-gate-ts") || "0", 10); if (gt) ok = (Date.now() - gt) < SIX_H; } catch (e) {}'''

OLD_GUIDE = '"Market hours (9 AM - 3:30 PM) me kabhi dobara nahi poochta - ek entry me poora market session chalta hai.",'
NEW_GUIDE = '"Har 6 ghante me ek baar poochta hai - market time (9-3:30) me bhi agar 6 ghante ho gaye to ek baar pooch lega, phir wapas 6 ghante chalu.",'


def main():
    s = open("index.html", encoding="utf-8").read()
    if OLD in s:
        s = s.replace(OLD, NEW)
        if "21sep26a7" in s:
            s = s.replace("21sep26a7", "21sep26a8")
        open("index.html", "w", encoding="utf-8").write(s)
        print("index.html: plain 6h rule, bumped to a8")
    elif "(Date.now() - gt) < SIX_H" in s:
        print("index.html: already plain 6h")
    else:
        print("WARN: anchor not found")
    g = open("mbguide.js", encoding="utf-8").read()
    if OLD_GUIDE in g:
        g = g.replace(OLD_GUIDE, NEW_GUIDE)
        open("mbguide.js", "w", encoding="utf-8").write(g)
        print("mbguide.js: updated")
    elif "Har 6 ghante me ek baar" in g:
        print("mbguide.js: already updated")
    else:
        print("WARN: guide anchor not found")


if __name__ == "__main__":
    main()

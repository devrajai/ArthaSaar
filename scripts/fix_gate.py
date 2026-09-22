#!/usr/bin/env python3
"""fix_gate.py - single password (SHA-256) + 6h re-entry + market-hours single entry. Idempotent."""

OLD_HASHES = '''  var HASHES = {"Mon":"7184d2d400b396ecaa14869ccd83ebee2b3fdb7acf16c58dbc0f5142fa671ee3","Tue":"d42a7655afd29f3a6e9f72c1dcb9c2f684d1a95f4206cb9b45658bb9e3177043","Wed":"630dce059f5cd2cbadfd39f3574fb7949aca80f0098c5190f8c84c796730a50f","Thu":"fca347c997c97633d45abd220122fcc2626bdcff938864d4a672a087e7754531","Fri":"c10757fab8cbffce19db48ad56ab4fa6d67e8129eebe09fcd695663fa59f8b94","Sat":"fa969388cf79d5c9e9990d84cbfaea0590150448f02ab144016fcd0ef87ed43c","Sun":"988db4661fc7114ed31a8c910e0b49bd15d75d65230f6395b4061d6f3d236d0e"};
  var HASH = HASHES[["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][new Date().getDay()]];
  var ok = false;
  try { ok = localStorage.getItem("mb-gate") === new Date().toDateString(); } catch (e) {}
  try { if (location.hash.indexOf("lock") !== -1) { localStorage.removeItem("mb-gate"); ok = false; } } catch (e) {}'''
NEW_HASHES = '''  var HASH = "c79a400771acb2dc2c6102ac7fc6c666e4ab79971d5b0e24d0e8c9802c5d1737";
  var SIX_H = 6 * 3600 * 1000;
  function gateExp(t) {
    var e = t + SIX_H, d = new Date(e), m = d.getHours() * 60 + d.getMinutes();
    if (m >= 540 && m <= 930) { d.setHours(15); d.setMinutes(31); d.setSeconds(0); d.setMilliseconds(0); e = d.getTime(); }
    return e;
  }
  var ok = false;
  try { var gt = parseInt(localStorage.getItem("mb-gate-ts") || "0", 10); if (gt) ok = Date.now() < gateExp(gt); } catch (e) {}
  try { if (location.hash.indexOf("lock") !== -1) { localStorage.removeItem("mb-gate-ts"); localStorage.removeItem("mb-gate"); ok = false; } } catch (e) {}'''
OLD_SET = 'try { localStorage.setItem("mb-gate", new Date().toDateString()); } catch (e) {}'
NEW_SET = 'try { localStorage.setItem("mb-gate-ts", String(Date.now())); } catch (e) {}'
OLD_GUIDE = '"Password din ke hisaab se badalta hai - shaam tak wahi rehta hai. Din me ek baar poochta hai, phir yaad rakhta hai.",\n      "Format: Devisbest + number + day. Jaise Monday = Devisbest1Mon, Sunday = Devisbest7Sun.",'
NEW_GUIDE = '"Password har roz same rehta hai. Ek baar daalo - 6 ghante tak yaad rakhta hai, phir dobara poochta hai.",\n      "Market hours (9 AM - 3:30 PM) me kabhi dobara nahi poochta - ek entry me poora market session chalta hai.",'


def main():
    s = open("index.html", encoding="utf-8").read()
    changed = False
    if OLD_HASHES in s:
        s = s.replace(OLD_HASHES, NEW_HASHES); changed = True
        print("index.html: gate logic replaced")
    elif "gateExp" in s:
        print("index.html: gate already patched")
    else:
        print("WARN: gate anchor not found")
    if OLD_SET in s:
        s = s.replace(OLD_SET, NEW_SET); changed = True
        print("index.html: success handler patched")
    if "21sep26a6" in s:
        s = s.replace("21sep26a6", "21sep26a7"); changed = True
        print("index.html: bumped to 21sep26a7")
    elif "21sep26a7" in s:
        print("index.html: version already a7")
    if changed:
        open("index.html", "w", encoding="utf-8").write(s)
    g = open("mbguide.js", encoding="utf-8").read()
    if OLD_GUIDE in g:
        g = g.replace(OLD_GUIDE, NEW_GUIDE)
        open("mbguide.js", "w", encoding="utf-8").write(g)
        print("mbguide.js: login text updated")
    elif "6 ghante tak yaad" in g:
        print("mbguide.js: already updated")
    else:
        print("WARN: guide anchor not found")


if __name__ == "__main__":
    main()

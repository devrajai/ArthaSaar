#!/usr/bin/env python3
"""fix_guide2.py - remove password-behavior lines from Learn guide card (keep only #lock logout). Idempotent."""

OLD = '''    h += block("LOGIN / PASSWORD", [
      "Password har roz same rehta hai. Ek baar daalo - 6 ghante tak yaad rakhta hai, phir dobara poochta hai.",
      "Har 6 ghante me ek baar poochta hai - market time (9-3:30) me bhi agar 6 ghante ho gaye to ek baar pooch lega, phir wapas 6 ghante chalu.",
      "Logout karne ke liye top par #lock button."
    ], "rgba(240,180,41,.7)");'''
NEW = '''    h += block("LOGOUT", [
      "Logout karne ke liye top par #lock button."
    ], "rgba(240,180,41,.7)");'''


def main():
    g = open("mbguide.js", encoding="utf-8").read()
    if OLD in g:
        g = g.replace(OLD, NEW)
        open("mbguide.js", "w", encoding="utf-8").write(g)
        print("mbguide.js: password lines removed")
    elif 'block("LOGOUT"' in g:
        print("mbguide.js: already removed")
    else:
        print("WARN: anchor not found")
    s = open("index.html", encoding="utf-8").read()
    if "21sep26a8" in s:
        s = s.replace("21sep26a8", "21sep26a9")
        open("index.html", "w", encoding="utf-8").write(s)
        print("index.html: bumped to a9")
    elif "21sep26a9" in s:
        print("index.html: already a9")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()

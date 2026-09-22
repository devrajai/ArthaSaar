#!/usr/bin/env python3
"""one-shot: remove 'poora terminal yahan' link line from scripts/telegram_alert.py"""
import io
s = io.open("scripts/telegram_alert.py", encoding="utf-8").read()
lines = s.split("\n")
out = [l for l in lines if "poora terminal yahan" not in l]
assert len(out) < len(lines), "nothing removed - already patched?"
s = "\n".join(out).replace("\n\n\n", "\n\n")
io.open("scripts/telegram_alert.py", "w", encoding="utf-8").write(s)
import ast; ast.parse(s)
print("telegram_alert.py patched: link removed")

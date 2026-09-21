import io
Q = chr(34)
A = chr(39)
NL = chr(10)

# 1) oldapp.js router fix: re-query sections on every showView
s = io.open("oldapp.js", encoding="utf-8").read()
marker = "function showView(id) {" + NL + "  let found = false;"
patched = "function showView(id) {" + NL + "  var views = document.querySelectorAll(" + Q + "section[id]" + Q + ");" + NL + "  let found = false;"
if "var views = document.querySelectorAll" not in s:
    assert marker in s, "showView block not found"
    s = s.replace(marker, patched, 1)
io.open("oldapp.js", "w", encoding="utf-8").write(s)
print("router: patched")

# 2) mft.js: fix one wrong closing quote + section guard for static section
s = io.open("mft.js", encoding="utf-8").read()
bad = "Best for SIP.<br>" + Q + " +"
good = "Best for SIP.<br>" + A + " +"
if bad in s:
    s = s.replace(bad, good, 1)
    print("mft: quote repaired")
old_sec = "  var sec = document.createElement(" + Q + "section" + Q + ");" + NL + "  sec.id = " + Q + "mf" + Q + "; sec.style.display = " + Q + "none" + Q + ";"
new_sec = ("  var sec = document.getElementById(" + Q + "mf" + Q + ");" + NL +
           "  if (sec) sec.style.display = " + Q + "none" + Q + ";" + NL +
           "  if (!sec) {" + NL +
           "    sec = document.createElement(" + Q + "section" + Q + ");" + NL +
           "    sec.id = " + Q + "mf" + Q + "; sec.style.display = " + Q + "none" + Q + ";")
if ("var sec = document.getElementById(" + Q + "mf" + Q + ")") not in s:
    assert old_sec in s, "mft sec block not found"
    s = s.replace(old_sec, new_sec, 1)
old_ins = "  if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);"
new_ins = old_ins + NL + "  }"
if s.count(old_ins) == 1:
    s = s.replace(old_ins, new_ins, 1)
io.open("mft.js", "w", encoding="utf-8").write(s)
print("mft: patched")

# 3) index.html: static #mf section skeleton before footer + version bump k
MF_SEC = ('<section id="mf" style="display:none"><a class="backbtn" href="#home">Home</a>'
          '<h2>MF Tracker</h2>'
          '<div class="card"><div class="subhead">Fund dhoondo - naam ya code</div>'
          '<input id="mfQ" placeholder="e.g. bluechip / hdfc / 120502" style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px">'
          '<div id="mfRes" style="margin-top:8px" class="note">MF data load ho raha hai...</div></div>'
          '<div class="card" id="mfCard"></div>'
          '<div class="card" id="mfTop"></div>'
          '<div class="card" id="mfSip"></div>'
          '<div class="card" id="mfPf"></div>'
          '<div class="card" id="mfGuide"></div></section>')
s = io.open("index.html", encoding="utf-8").read()
if ('id=' + Q + 'mf' + Q) not in s:
    i = s.find("<footer")
    assert i > 0, "footer not found"
    s = s[:i] + MF_SEC + s[i:]
    print("index: static mf section added")
s = s.replace("app.js?v=21sep26j", "app.js?v=21sep26k")
io.open("index.html", "w", encoding="utf-8").write(s)
print("index: patched")

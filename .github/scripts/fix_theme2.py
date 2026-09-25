import pathlib

ix = pathlib.Path("index.html")
s = ix.read_text()
if 'calm.css?v=as2' not in s:
    old = '<link rel="stylesheet" href="style.css?v=as1">'
    assert old in s, "style.css link not found"
    s = s.replace(old, old + '\n<link rel="stylesheet" href="calm.css?v=as2">')
if 'themefix.js?v=25sep26a43' not in s:
    old = '<script src="app.js?v=25sep26a42"></script>'
    assert old in s, "app.js a42 tag not found"
    s = s.replace(old, '<script src="app.js?v=25sep26a43"></script>\n<script src="themefix.js?v=25sep26a43"></script>')
ix.write_text(s)
print("index.html OK:", 'calm.css?v=as2' in s and 'themefix.js?v=25sep26a43' in s)

tf = pathlib.Path("themefix.js")
t = tf.read_text()
old = 'function boot() { apply(); statusbar(); ticker(); }'
if old in t and 'MB_LOCKED' not in t:
    t = t.replace(old, 'function boot() { if (window.MB_LOCKED) return; apply(); statusbar(); ticker(); }')
tf.write_text(t)
print("themefix.js OK:", 'MB_LOCKED' in t)

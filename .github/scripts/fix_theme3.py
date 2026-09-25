import pathlib

CSS = r"""/* ============================================================
   calm.css v2 — ARTHASAAR CALM TERMINAL "full clothes" (v3 approved mockup)
   Light blue = calm · light green = growth · amber = action · red = risk
   Panels + hairlines + Space Grotesk / IBM Plex Mono. Same data, naye kapde.
   Overlay hai — purane class names kaam karte rahenge.
   NO backdrop-filter, NO position:sticky (locked rules)
   ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root{
  --bg0:#0a0f14; --panel:#0f151d; --panel2:#131b25;
  --hair:rgba(160,215,255,.09); --hair2:rgba(160,215,255,.055);
  --text:#e2eaf2; --dim:#93a4b5; --faint:#5e707f;
  --up:#7ce3a8; --up-dim:rgba(124,227,168,.12);
  --down:#ff7a80; --down-dim:rgba(255,122,128,.11);
  --amber:#ffd27a; --amber-dim:rgba(255,210,122,.11);
  --blue:#7cc4ff; --blue-dim:rgba(124,196,255,.12);
  --vio:#b3a1ff; --vio-dim:rgba(179,161,255,.12);
  --glass:var(--panel); --glass2:var(--panel2);
  --border:var(--hair); --border2:rgba(160,215,255,.16);
  --shadow:0 8px 24px rgba(2,6,14,.4);
  --font:'Space Grotesk','IBM Plex Sans',system-ui,sans-serif;
  --mono:'IBM Plex Mono','SF Mono',monospace;
}
[data-theme="light"]{
  --bg0:#f0f5fa; --panel:#ffffff; --panel2:#f2f7fb;
  --hair:rgba(20,60,100,.13); --hair2:rgba(20,60,100,.075);
  --text:#132330; --dim:#4d6275; --faint:#8296a8;
  --up:#0f9d58; --up-dim:rgba(15,157,88,.11);
  --down:#d63940; --down-dim:rgba(214,57,64,.10);
  --amber:#a96f00; --amber-dim:rgba(169,111,0,.11);
  --blue:#1f7ac2; --blue-dim:rgba(31,122,194,.10);
  --vio:#6a4fe0; --vio-dim:rgba(106,79,224,.11);
  --shadow:0 8px 22px rgba(30,60,100,.10);
}

body{
  font-family:var(--font);font-size:13px;line-height:1.5;
  background-image:
  radial-gradient(900px 440px at 85% -120px, rgba(124,196,255,.07), transparent 70%),
  radial-gradient(700px 380px at 0% 25%, rgba(124,227,168,.05), transparent 70%) !important;
  padding-bottom:34px;
}

/* ---------- header ---------- */
header h1{font-family:'Space Grotesk',var(--font);font-weight:700;letter-spacing:.045em;font-size:1.5em}
header h1 em{font-style:normal;color:var(--blue)}
header .logo{background:none !important;border:none !important;color:transparent !important;font-size:0 !important;
  width:44px;height:50px;padding:0 !important;display:flex;align-items:center;box-shadow:none !important}
header .logo svg{width:44px;height:50px}
header .tagline{color:var(--faint);letter-spacing:.06em;font-size:9.5px}
#clock{font-family:var(--mono);font-size:15px;font-weight:600;letter-spacing:.02em}
#clockdate{font-size:9px;color:var(--faint);font-family:var(--mono)}
.meta-row{color:var(--faint);font-size:9.5px}
.pill{font-family:var(--mono);font-size:9px;letter-spacing:.08em;padding:5px 9px;border-radius:6px;
  background:var(--panel);border:1px solid var(--hair);color:var(--dim)}
.dot{width:6px;height:6px}
.dot.open{background:var(--up);box-shadow:0 0 6px var(--up)}
.dot.closed{background:var(--down)}
.dot.pre{background:var(--amber)}
#themeBtn{font-family:var(--mono);font-size:13px;width:34px;height:34px;border-radius:8px;
  background:var(--panel);border:1px solid var(--hair);color:var(--dim)}
#refreshBtn{font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;padding:5px 10px;border-radius:7px;
  background:var(--panel);border:1px solid var(--hair);color:var(--dim)}
#themeBtn:active,#refreshBtn:active{border-color:var(--blue)}

/* ---------- gradient line + ticker (v1) ---------- */
.as-rline{height:2px;border-radius:2px;margin:2px 0 10px;
  background:linear-gradient(90deg,var(--blue),var(--up))}
.as-tape{overflow:hidden;background:var(--panel);border:1px solid var(--hair);border-radius:9px;
  margin:10px 0;padding:8px 0}
.as-tape-in{display:flex;gap:26px;white-space:nowrap;animation:asmv 28s linear infinite;
  font-family:var(--mono);font-size:10.5px;width:max-content}
@keyframes asmv{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.as-tape-in b{color:var(--dim);font-weight:500;letter-spacing:.05em}
.as-tape-in .t{font-weight:600}
.as-tape-in .u{color:var(--up)}.as-tape-in .d{color:var(--down)}

/* ---------- home grid ---------- */
.homegrid{gap:9px}
.hgroup{font-size:9.5px;letter-spacing:.22em;color:var(--faint);font-weight:600;font-family:var(--mono);margin:18px 0 3px}
.tile{background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:13px 10px;gap:5px;
  box-shadow:none}
.tile:active{border-color:var(--blue)}
.t-ic{font-size:19px;line-height:1}
.t-nm{font-size:12.5px;font-weight:600;line-height:1.25}
.t-sb{font-size:9.5px;color:var(--faint);line-height:1.35;font-family:var(--mono);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.backbtn{font-family:var(--mono);font-size:10px;letter-spacing:.06em;padding:7px 12px;border-radius:7px;
  border:1px solid var(--hair);background:var(--panel);color:var(--dim);font-weight:500}

/* ---------- sections / cards ---------- */
section h2{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--dim);
  text-transform:uppercase;margin-bottom:11px}
section h2::before{content:"";width:8px;height:8px;border-radius:2px;transform:none;
  background:linear-gradient(135deg,var(--blue),var(--up))}
.card{background:var(--panel);border:1px solid var(--hair);border-radius:13px;
  box-shadow:none;padding:13px;margin-bottom:11px}
.card.flat{box-shadow:none}
.subhead{font-family:var(--mono);font-size:9px;color:var(--faint);letter-spacing:.14em;text-transform:uppercase}
.note{font-size:11.5px;color:var(--dim)}
footer{border-top:1px solid var(--hair);color:var(--faint)}
.footer-note{font-size:9.5px;font-family:var(--mono);color:var(--faint)}

/* ---------- kpi ---------- */
.kpi{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:11px 8px;text-align:center}
.kpi .k-name{font-family:var(--mono);font-size:8px;color:var(--faint);letter-spacing:.14em;font-weight:500}
.kpi .k-val{font-family:var(--mono);font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin:4px 0 2px}
.kpi .k-chg{font-family:var(--mono);font-size:10.5px;font-weight:600}

/* ---------- controls / buttons ---------- */
.controls input,.controls select{font-family:var(--mono);font-size:11.5px;padding:9px 11px;
  border-radius:8px;border:1px solid var(--hair);background:var(--panel2);color:var(--text)}
.controls input:focus,.controls select:focus{border-color:var(--blue)}
.chip{font-family:var(--mono);font-size:10.5px;padding:8px 13px;border-radius:7px;
  border:1px solid var(--hair);background:var(--panel);color:var(--dim);font-weight:500;letter-spacing:.03em}
.chip.on{background:var(--blue-dim);color:var(--blue);border-color:var(--blue)}
.morebtn{font-family:var(--mono);font-size:10.5px;letter-spacing:.04em;padding:11px;border-radius:9px;
  border:1px dashed var(--border2);background:var(--panel);color:var(--dim)}
nav .tab{font-family:var(--mono);font-size:11px;padding:8px 13px;border-radius:9px;
  border:1px solid var(--hair);background:var(--panel);color:var(--dim);font-weight:500}
nav .tab.active{color:var(--text);background:var(--panel2);border-color:var(--blue)}
.hchip{font-family:var(--mono);font-size:10.5px;padding:9px 13px;border-radius:8px;
  background:var(--panel);border:1px solid var(--hair);font-weight:500}
.hchip:active{background:var(--panel2);border-color:var(--blue)}

/* ---------- tables ---------- */
.tblwrap{border:1px solid var(--hair);border-radius:9px}
table{font-family:var(--mono);font-size:11.5px}
th{font-size:8.5px;letter-spacing:.1em;color:var(--dim);background:var(--panel2);
  padding:9px 10px;border-bottom:1px solid var(--hair2)}
td{padding:9px 10px;font-weight:500;border-bottom:1px solid var(--hair2);font-variant-numeric:tabular-nums}
td:first-child{font-weight:600}
.sym{font-size:11px}
.cname{font-size:9px;color:var(--faint)}
.chg-badge{font-family:var(--mono);font-size:10px;font-weight:600;padding:2px 7px;border-radius:6px}
.chg-badge.pos{background:var(--up-dim);color:var(--up)}
.chg-badge.neg{background:var(--down-dim);color:var(--down)}
.badge-tier{font-size:8px;padding:1px 6px;border-radius:4px}

/* ---------- meters / bars ---------- */
.meter{height:7px;border-radius:4px;background:var(--hair2)}
.meter i{border-radius:4px;background:linear-gradient(90deg,var(--blue),var(--up))}
.statline{font-family:var(--mono);font-size:10px;color:var(--dim)}
.statline b{color:var(--text)}
.fg-marker{background:var(--text)}
.yearbar .yb-bar.g{background:var(--up)}
.yearbar .yb-bar.r{background:var(--down)}

/* ---------- details / lists / misc ---------- */
details.gl{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:11px 13px}
details.gl summary{font-size:12.5px}
details.gl summary::before{color:var(--blue)}
.kv span:nth-child(odd){color:var(--dim);font-size:9.5px;letter-spacing:.04em}
.co-res{background:var(--panel);border:1px solid var(--hair);border-radius:10px;font-size:12px}
.co-res b{font-family:var(--mono)}
.loading{font-family:var(--mono);font-size:10.5px;color:var(--faint)}
a{color:var(--blue)}
.pos{color:var(--up)} .neg{color:var(--down)} .neu{color:var(--dim)}

/* ---------- status bar (v1) ---------- */
.as-status{position:fixed;left:0;right:0;bottom:0;display:flex;z-index:60;
  font-family:var(--mono);font-size:8.5px;letter-spacing:.05em;color:#fff;opacity:.95}
.as-status i{flex:1;padding:5px 4px;text-align:center;font-style:normal}
.as-status .s1{background:var(--down)}
.as-status .s2{background:var(--amber);color:#231a00}
.as-status .s3{background:var(--up);color:#0a2617}
.as-status .s4{background:var(--blue);color:#0a1b2e}
"""

p = pathlib.Path("calm.css")
p.write_text(CSS)
assert "as-status" in p.read_text() and "Space Grotesk" in p.read_text()

ix = pathlib.Path("index.html")
s = ix.read_text()
if 'calm.css?v=as2' in s:
    s = s.replace('calm.css?v=as2', 'calm.css?v=as3')
ix.write_text(s)
print("calm.css v2 written:", len(CSS), "bytes; index:", 'as3' in s)

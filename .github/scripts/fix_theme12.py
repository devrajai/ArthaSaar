#!/usr/bin/env python3
# fix_theme12.py — v11: 1) header single-line (small pills, line near text)
# 2) Event tile -> TRADING group next to IPO  3) IPO site Decision section fix
import pathlib

def rep(p, old, new, cnt=1):
    s = p.read_text()
    assert old in s, "MISSING in %s: %r" % (p.name, old[:70])
    p.write_text(s.replace(old, new, cnt))

# ---------- 1) calm.css ----------
c = pathlib.Path("calm.css")
rep(c, "header{border-bottom:1px solid var(--hair);padding:15px 0 12px}",
       "header{border-bottom:1px solid var(--hair);padding:10px 0 6px}\n"
       "header .brand-row{flex-wrap:nowrap}\n"
       "header .brand-row>div:nth-child(2){min-width:0}\n"
       "header h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}")
rep(c, ".header-right{align-self:flex-start;margin-top:3px}",
       ".header-right{align-self:center;margin-top:0;flex:0 0 auto;gap:6px}")
rep(c, ".pill{font-family:var(--mono);font-size:8.5px;letter-spacing:.1em;padding:5px 9px;border-radius:6px;",
       ".pill{font-family:var(--mono);font-size:7px;letter-spacing:.08em;padding:3px 7px;border-radius:6px;")
rep(c, ".dot{width:6px;height:6px}", ".dot{width:5px;height:5px}")
rep(c, "#themeBtn{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.08em;width:auto;\n"
       "  height:32px;padding:0 13px;border-radius:8px;border:none;",
       "#themeBtn{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.06em;width:auto;\n"
       "  height:24px;padding:0 10px;border-radius:7px;border:none;")
rep(c, ".as-rline{height:2px;border-radius:2px;margin:2px 0 10px;",
       ".as-rline{height:2px;border-radius:2px;margin:0 0 8px;")
rep(c, "calm.css v10 — ARTHASAAR PREMIUM (no brand underline)",
       "calm.css v11 — ARTHASAAR PREMIUM (one-line header)")

# ---------- 2) themefix.js: Event tile beside IPO ----------
t = pathlib.Path("themefix.js")
rep(t,
    '    /* existing Events tile: only the word "Event", moved to TOP of homegrid */\n'
    '    var tile = document.querySelector(\'a.tile[href="#events"]\');\n'
    '    var hg = document.querySelector("section#home .homegrid");\n'
    '    if (tile) {\n'
    '      var nm = tile.querySelector(".t-nm");\n'
    '      if (nm) nm.textContent = "Event";\n'
    '      if (hg) {\n'
    '        tile.style.cssText = "grid-column:1/-1;flex-direction:row;align-items:center;gap:12px";\n'
    '        hg.insertBefore(tile, hg.firstChild);\n'
    '      }\n'
    '    }',
    '    /* existing Events tile: only the word "Event", placed in TRADING group NEXT TO IPO tile */\n'
    '    var tile = document.querySelector(\'a.tile[href="#events"]\');\n'
    '    var hg = document.querySelector("section#home .homegrid");\n'
    '    if (tile) {\n'
    '      var nm = tile.querySelector(".t-nm");\n'
    '      if (nm) nm.textContent = "Event";\n'
    '      tile.style.cssText = "";\n'
    '      var ipo = document.querySelector(\'a.tile[href="ipo/"]\');\n'
    '      if (hg && ipo && ipo.parentNode === hg) hg.insertBefore(tile, ipo.nextSibling);\n'
    '    }')

# ---------- 3) index.html: version bumps ----------
i = pathlib.Path("index.html")
rep(i, 'calm.css?v=as11', 'calm.css?v=as12')
rep(i, 'themefix.js?v=25sep26a50', 'themefix.js?v=25sep26a52')

# ---------- 4) ipo/index.html: Decision section + render ----------
ip = pathlib.Path("ipo/index.html")

SEC = ('<section id="section-decision" class="section glass">'
       '<div class="section-title"><span>\U0001F9E0 IPO Decision — Apply / Wait / Avoid</span>'
       '<button class="close" data-close="decision">\u2715 Close</button></div>'
       '<div id="decision-list" class="content"></div></section>\n')
rep(ip, '<button data-section="decision">\U0001F9E0 Decision</button>',
       '<button data-section="allinone">\U0001F9E0 Smart Tools</button><button data-section="decision">\U0001F9E0 Decision</button>')
rep(ip, '<section id="section-tips"', SEC + '<section id="section-tips"')

JS = (
"function renderDecision(){const el=document.getElementById('decision-list');if(!el)return;"
"const g=groups();"
"const mny=v=>Number.isFinite(v)?('\u20B9'+Math.round(v).toLocaleString('en-IN')):'\u2014';"
"const VC={gn:'#22c55e',rd:'#ef4444',wt:'#f59e0b'};const today=new Date();today.setHours(0,0,0,0);"
"const rows=[...g.open,...g.upcoming].map(x=>{"
"const gv=gmpRupees(x),pctRaw=gmpPctOf(x),p=(pctRaw==null||pctRaw==='\u2014')?null:parseFloat(pctRaw),lo=bandLow(x),lots=Number(x.lot_size)||null;"
"const cost=(lo!=null&&lots)?lo*lots:null;const est=(gv!=null&&lo!=null)?lo+gv:null;"
"let verdict,cls,why;"
"if(p==null){verdict='\u26AA WAIT';cls='wt';why='GMP data nahi mila \u2014 grey market ka wait karo'}"
"else if(p>=25){verdict='\U0001F7E2 STRONG APPLY';cls='gn';why='GMP '+p+'% \u2014 historically strong zone (25%+)'}"
"else if(p>=10){verdict='\U0001F7E2 APPLY';cls='gn';why='GMP '+p+'% \u2014 decent premium, day 1-2 apply karo'}"
"else if(p>0){verdict='\U0001F7E1 WAIT';cls='wt';why='GMP '+p+'% \u2014 thin premium, day-2 subscription dekho'}"
"else{verdict='\U0001F534 AVOID';cls='rd';why='GMP negative ('+p+'%) \u2014 listing loss ka risk'}"
"const cd=parseDate(x.close_date,true);const days=cd?Math.ceil((cd-today)/86400000):null;"
"const sub=findSub(x.name);const subTxt=sub?(' \u00B7 Sub RII '+(sub.rii||'—')+'x'):'';"
"const sme=String(x.board||'').toUpperCase().includes('SME');"
"const timeLeft=(days!=null&&days>=0)?(' \u23F3 '+(days===0?'AAJ last day':days+' din baaki')):'';"
"return `<div class=\"card glass\"><b>${x.name}</b> <span style=\"float:right;color:${VC[cls]};font-weight:850\">${verdict}</span>"
"<p style=\"margin:6px 0 2px;font-size:13px;opacity:.75\">${sme?'SME':'Mainboard'} \u00B7 ${status(x)} \u00B7 band ${x.price_band||'\u2014'}${lots?' \u00B7 lot '+lots:''}${cost?' ('+mny(cost)+'/lot)':''}${timeLeft}</p>"
"<p style=\"margin:4px 0;font-size:13px\">GMP: <b>${gv!=null?mny(gv):'\u2014'}</b> (${p!=null?p+'%':'\u2014'}) \u00B7 Est listing: <b>${est!=null?mny(est):'\u2014'}</b>${subTxt}</p>"
"<p style=\"margin:0;font-size:13px;opacity:.85\">${why}${sme?' \u00B7 SME: Rule of 5 \u2014 half position':''}</p></div>`}).join('');"
"el.innerHTML=rows||'<div class=\"empty\">No open or upcoming IPO right now.</div>'}\n")
rep(ip, "async function load(){", JS + "async function load(){")
rep(ip, "renderDocs();renderGmp()}", "renderDocs();renderGmp();renderDecision()}")

# ---------- 5) merge-tools.js: Decision ko Smart Tools hijack se azad ----------
m = pathlib.Path("ipo/scripts/merge-tools.js")
rep(m, "nav: 'decision', label: '\\u{1F9E0} Smart Tools', def: 'allinone', hide: ['coach'],",
       "nav: 'allinone', label: '\\u{1F9E0} Smart Tools', def: 'allinone', hide: ['coach'],")

print("v11 applied | header:", "one-line" if "flex-wrap:nowrap" in c.read_text() else "?",
      "| event tile:", "TRADING" if "NEXT TO IPO" in t.read_text() else "?",
      "| decision:", "OK" if "renderDecision" in ip.read_text() else "?",
      "| merge:", "OK" if "nav: 'allinone'" in m.read_text() else "?")

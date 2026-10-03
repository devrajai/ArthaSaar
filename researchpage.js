(function(){
"use strict";

var STATE={radar:null,stocks:{},delivery:{},futures:{},filings:[],results:{},historyCache:{},alerts:null,health:null,marketHistory:null,signalHistory:null,candles:{},candlesUpdated:null};

function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":">","\"":"&quot;"}[c];});}
function n(x){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:2});}
function p(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
function pct0(x){return x==null||isNaN(x)?"—":Number(x).toFixed(1)+"%";}
function safeDate(x){return x?String(x).replace("T"," ").replace("Z",""): "—";}

function ageHours(updated){
  if(!updated)return null;
  var t=Date.parse(updated);
  if(isNaN(t))return null;
  return Math.max(0,(Date.now()-t)/3600000);
}
function freshness(updated){
  var h=ageHours(updated);
  if(h==null)return {label:"SNAPSHOT",cls:"neutral"};
  if(h<=30)return {label:"FRESH",cls:"fresh"};
  if(h<=72)return {label:"RECENT",cls:"recent"};
  return {label:"STALE",cls:"stale"};
}
function sourceBadge(source,updated){
  var f=freshness(updated);
  return '<span class="rr-badge rr-source">'+esc(source||"PUBLIC")+'</span><span class="rr-badge '+f.cls+'">'+f.label+'</span>';
}
function row(a,b,cl){
  return '<div class="zrow"><span>'+esc(a)+'</span><b class="'+(cl||"")+'">'+esc(b)+'</b></div>';
}
function stockRow(a,b,cl){
  return '<button class="zrow rr-stock-row" data-symbol="'+esc(String(a||"").toUpperCase())+'"><span>'+esc(a==null?"—":a)+'</span><b class="'+(cl||"")+'">'+esc(b==null?"—":b)+'</b></button>';
}
function rows(arr,akey,bkey,clsFn,limit){
  var list=(arr||[]).slice(0,limit||8);
  if(!list.length)return '<div class="mut">No snapshot rows.</div>';
  return list.map(function(x){
    var a=x[akey],b=x[bkey],cl=clsFn?clsFn(x):"";
    if((akey==="symbol"||akey==="sym") && a) return stockRow(a,b,cl);
    return row(a==null?"—":a,b==null?"—":b,cl);
  }).join("");
}
function itemList(arr,fn,limit){return (arr||[]).slice(0,limit||6).map(fn).join("")||'<div class="mut">No snapshot rows.</div>';}

function card(num,title,body,source,updated,wide){
  var meta=sourceBadge(source||"ArthaSaar",updated||((STATE.radar||{}).updated));
  return '<div class="card rr-card '+(wide?'rr-wide':'')+'"><div class="sh2 rr-head"><span>'+num+' · '+esc(title)+'</span><span class="rr-badges">'+meta+'</span></div>'+body+'</div>';
}

function installCSS(){
  if(document.getElementById("rr-mobile-css"))return;
  var st=document.createElement("style");st.id="rr-mobile-css";
  st.textContent=[
    "#research-radar{width:100%;max-width:100%;overflow:hidden}",
    "#research-radar .rr-command,#research-radar .rr-panel,#research-radar .rr-card{box-sizing:border-box;max-width:100%}",
    "#research-radar .rr-command{margin-left:auto;margin-right:auto}",
    "#research-radar .rr-tabs{display:flex;gap:7px;overflow-x:auto;scrollbar-width:none;padding:8px 2px;position:sticky;top:0;z-index:5;background:var(--bg,#050505)}",
    "#research-radar .rr-tabs::-webkit-scrollbar{display:none}",
    "#research-radar .rr-tab{flex:0 0 auto;white-space:nowrap}",
    "#research-radar .rr-grid{grid-template-columns:repeat(2,minmax(0,1fr))}",
    "#research-radar .rr-wide{grid-column:1/-1}",
    "#research-radar .rr-card{min-width:0;overflow:hidden}",
    "#research-radar .rr-card table{display:block;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}",
    "#research-radar .rr-card td,#research-radar .rr-card th{white-space:nowrap}",
    "@media(max-width:720px){#research-radar{padding:0!important}",
    "#research-radar .rr-command{border-radius:16px;margin:8px 0}",
    "#research-radar .rr-title{font-size:26px!important;line-height:1.05}",
    "#research-radar .rr-subtitle{font-size:9px!important;line-height:1.5}",
    "#research-radar .rr-command-top{display:block!important}",
    "#research-radar .rr-statusline{margin-top:10px;display:flex;flex-wrap:wrap;gap:5px}",
    "#research-radar .rr-hero-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}",
    "#research-radar .rr-hero-kpi{padding:10px!important;min-width:0}",
    "#research-radar .rr-hero-kpi b{font-size:16px!important}",
    "#research-radar .rr-source-strip{grid-template-columns:1fr 1fr!important}",
    "#research-radar .rr-grid{grid-template-columns:1fr!important;gap:9px!important}",
    "#research-radar .rr-wide{grid-column:auto!important}",
    "#research-radar .rr-card{border-radius:13px!important}",
    "#research-radar .rr-head{font-size:10px!important}",
    "#research-radar .rr-kicker{font-size:8px!important;line-height:1.45}",
    "#research-radar .rr-row{grid-template-columns:minmax(0,1fr) auto!important}",
    "#research-radar .rr-cols{grid-template-columns:1fr!important}",
    "#research-radar .rr-lab-grid{grid-template-columns:1fr!important}",
    "#research-radar .rr-tool-grid{grid-template-columns:1fr!important}",
    "#research-radar .rr-search{display:flex!important;gap:5px!important}",
    "#research-radar .rr-search input{min-width:0!important}",
    "#research-radar .rr-btn{white-space:nowrap}",
    "#research-radar .rr-metric-grid{grid-template-columns:1fr 1fr!important}",
    "#research-radar .rr-note{display:none!important}",
    "}",
    "@media(max-width:380px){#research-radar .rr-hero-kpis{grid-template-columns:1fr!important}.rr-source-strip{grid-template-columns:1fr!important}}"
  ].join("");
  document.head.appendChild(st);

  if(document.getElementById("rr44-style"))return;
  var s=document.createElement("style");s.id="rr44-style";
  s.textContent=[
    ".rr-shell{margin-top:8px}.rr-command{border:1px solid var(--border2);background:linear-gradient(180deg,var(--surface),var(--bg2));border-radius:14px;padding:12px;box-shadow:var(--shadow)}",
    ".rr-command-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.rr-eyebrow{font:700 8px var(--mono);letter-spacing:.18em;color:var(--faint);text-transform:uppercase}.rr-title{font-size:20px;line-height:1.15;margin-top:3px}.rr-subtitle{font:400 9px var(--mono);color:var(--dim);margin-top:4px}.rr-statusline{display:flex;gap:5px;align-items:center;flex-wrap:wrap;justify-content:flex-end}",
    ".rr-hero-kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin-top:10px}.rr-hero-kpi{border:1px solid var(--border);background:color-mix(in srgb,var(--bg2) 84%,transparent);border-radius:10px;padding:8px 9px;min-width:0}.rr-hero-kpi small{display:block;color:var(--faint);font:600 7.5px var(--mono);letter-spacing:.12em}.rr-hero-kpi b{display:block;margin-top:4px;font:700 14px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".rr-tabs{position:sticky;top:0;z-index:20;display:flex;gap:5px;overflow:auto;scrollbar-width:none;padding:8px 0 6px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(12px)}.rr-tabs::-webkit-scrollbar{display:none}.rr-tab{flex:0 0 auto;border:1px solid var(--border);background:var(--surface);color:var(--dim);border-radius:999px;padding:7px 11px;cursor:pointer;font:700 8.5px var(--mono);letter-spacing:.06em}.rr-tab:hover{color:var(--text);border-color:var(--accent)}.rr-tab.on{background:var(--accent);color:var(--bg);border-color:var(--accent)}",
    ".rr-panel{display:none}.rr-panel.on{display:block;animation:vi .18s ease}.rr-panel-head{display:flex;align-items:end;justify-content:space-between;gap:8px;margin:9px 0 7px}.rr-panel-head h3{font:700 12px var(--mono);letter-spacing:.12em;text-transform:uppercase}.rr-panel-head small{font:400 8px var(--mono);color:var(--faint)}",
    ".rr-module-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.rr-module-grid .rr-wide{grid-column:1/-1}.rr-card{border-radius:11px}.rr-card .sh2{padding:8px 10px}.rr-card .zrow{padding:6px 10px;font-size:10px}.rr-card .ni{padding:7px 10px}.rr-card .rr-kicker{padding:7px 10px 3px;font-size:8px}",
    ".rr-empty{padding:10px;color:var(--faint);font:500 9px var(--mono);border:1px dashed var(--border);border-radius:8px;background:color-mix(in srgb,var(--bg2) 70%,transparent)}.rr-source-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:8px}.rr-source-box{padding:8px;border:1px solid var(--border);border-radius:9px;background:var(--bg2)}.rr-source-box small{display:block;color:var(--faint);font:600 7px var(--mono);text-transform:uppercase}.rr-source-box b{display:block;margin-top:4px;font:600 9px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".rr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}",
    ".rr-card{min-width:0}.rr-wide{grid-column:1/-1}",
    ".rr-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.rr-badges{display:flex;gap:4px;align-items:center;flex-wrap:wrap;justify-content:flex-end}",
    ".rr-badge{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:2px 6px;font:500 8px var(--mono);letter-spacing:.04em;white-space:nowrap}",
    ".rr-source{color:var(--dim)}.rr-badge.fresh{color:var(--up);border-color:color-mix(in srgb,var(--up) 45%,transparent);background:color-mix(in srgb,var(--up) 9%,transparent)}",
    ".rr-badge.recent{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent);background:color-mix(in srgb,var(--accent) 9%,transparent)}",
    ".rr-badge.stale{color:var(--down);border-color:color-mix(in srgb,var(--down) 45%,transparent);background:color-mix(in srgb,var(--down) 9%,transparent)}",
    ".rr-badge.neutral{color:var(--faint)}",
    ".rr-cols{display:grid;grid-template-columns:1fr 1fr;gap:8px}",
    ".rr-sub{font:600 9px var(--mono);letter-spacing:.14em;color:var(--faint);padding:9px 12px 3px;text-transform:uppercase}",
    ".rr-note{margin:12px 2px 20px;padding:10px 12px;border:1px dashed var(--border2);border-radius:10px;color:var(--dim);font:400 9.5px var(--mono);line-height:1.55}",
    ".mut{padding:12px 14px;color:var(--faint);font:400 10px var(--mono)}",
    ".rr-kicker{padding:10px 12px 2px;color:var(--faint);font:500 9px var(--mono);line-height:1.5}",
    ".rr-stock-row{width:100%;font:inherit;color:var(--text);cursor:pointer;background:transparent;border-left:0;border-right:0;border-top:0;text-align:left}.rr-stock-row:hover{background:color-mix(in srgb,var(--border) 13%,transparent);color:var(--text)}",
    ".rr-lab{margin-top:10px}.rr-lab-grid{display:grid;grid-template-columns:1.35fr .65fr;gap:10px}.rr-search{display:flex;gap:7px}.rr-search input{flex:1;min-width:0;border-radius:10px;border:1px solid var(--border2);background:var(--surface);padding:10px 12px;color:var(--text);font:500 12px var(--font);outline:none}.rr-search input:focus{border-color:var(--accent)}",
    ".rr-btn{border:1px solid var(--border);background:var(--surface);color:var(--dim);border-radius:9px;padding:8px 10px;cursor:pointer;font:600 9px var(--mono)}.rr-btn:hover{border-color:var(--accent);color:var(--text)}",
    ".rr-results{margin-top:7px;display:flex;flex-direction:column;gap:4px}.rr-result{display:flex;justify-content:space-between;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg2);cursor:pointer;text-align:left;color:var(--text)}.rr-result:hover{border-color:var(--accent)}.rr-result small{color:var(--faint);font:400 9px var(--mono)}",
    ".rr-chiprow{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}.rr-chip{border:1px solid var(--border);background:var(--surface);color:var(--dim);border-radius:999px;padding:5px 8px;cursor:pointer;font:500 8.5px var(--mono)}.rr-chip:hover{border-color:var(--accent);color:var(--text)}",
    ".rr-lab-table{width:100%;border-collapse:collapse;font-size:10px}.rr-lab-table th,.rr-lab-table td{padding:7px 8px;border-bottom:1px solid var(--border)}.rr-lab-table th{position:static;text-align:left}.rr-lab-table td.numr{text-align:right;font-family:var(--mono)}",
    ".rr-history{max-height:250px;overflow:auto}",
    ".rr-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:120;display:none;align-items:flex-start;justify-content:center;padding:7vh 10px 20px}.rr-overlay.open{display:flex}.rr-modal{width:min(760px,96vw);max-height:86vh;overflow:auto;background:var(--surface);border:1px solid var(--border2);border-radius:16px;box-shadow:var(--shadow)}.rr-modal-head{position:sticky;top:0;z-index:2;background:color-mix(in srgb,var(--surface) 94%,transparent);backdrop-filter:blur(10px);display:flex;justify-content:space-between;gap:8px;padding:12px 14px;border-bottom:1px solid var(--border)}.rr-modal-title b{display:block;font-size:15px}.rr-modal-title small{display:block;margin-top:3px;color:var(--faint);font:400 9px var(--mono)}.rr-modal-body{padding:12px}.rr-metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.rr-metric{padding:9px 10px;background:var(--bg2);border:1px solid var(--border);border-radius:9px}.rr-metric small{display:block;color:var(--faint);font:500 8px var(--mono);letter-spacing:.08em}.rr-metric b{display:block;margin-top:3px;font:600 12px var(--mono)}.rr-detail-section{margin-top:10px;border:1px solid var(--border);border-radius:10px;overflow:hidden}.rr-detail-section .sh2{border-bottom:1px solid var(--border)}",
    "@media(max-width:900px){.rr-lab-grid{grid-template-columns:1fr}.rr-metric-grid{grid-template-columns:1fr 1fr}}",
    ".rr-tool-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}",
    ".rr-tools input,.rr-tools select,.rr-tools textarea{width:100%;border:1px solid var(--border2);background:var(--surface);color:var(--text);border-radius:9px;padding:8px 10px;font:500 10px var(--mono);outline:none}",
    ".rr-tools textarea{min-height:70px;resize:vertical}.rr-tools label{display:block;color:var(--faint);font:600 8px var(--mono);letter-spacing:.1em;margin:8px 0 4px;text-transform:uppercase}",
    ".rr-mini-table{width:100%;border-collapse:collapse;font-size:9.5px}.rr-mini-table th,.rr-mini-table td{padding:6px 7px;border-bottom:1px solid var(--border)}.rr-mini-table th{position:static}.rr-mini-table td.numr{text-align:right;font-family:var(--mono)}",
    ".rr-alert{padding:8px 10px;border-bottom:1px solid var(--border)}.rr-alert:last-child{border:0}.rr-alert b{display:block;font-size:10px}.rr-alert small{display:block;color:var(--faint);font:400 8.5px var(--mono);margin-top:2px}",
    ".rr-pill-ok{color:var(--up)}.rr-pill-bad{color:var(--down)}",
    ".rr-note-save{margin-top:7px}.rr-watch{display:flex;gap:5px;flex-wrap:wrap;margin:7px 0}.rr-watch-item{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--border);border-radius:999px;padding:4px 7px;font:600 8px var(--mono)}.rr-watch-item button{border:0;background:none;color:var(--faint);cursor:pointer}",
    ".rr-replay-body{margin-top:7px;padding:9px;background:var(--bg2);border:1px solid var(--border);border-radius:9px}",

    "@media(max-width:980px){.rr-module-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.rr-hero-kpis{grid-template-columns:repeat(3,1fr)}}",
    "@media(max-width:720px){.rr-grid{grid-template-columns:1fr}.rr-wide{grid-column:auto}.rr-module-grid{grid-template-columns:1fr}.rr-cols{grid-template-columns:1fr}.rr-head{align-items:flex-start;flex-direction:column}.rr-badges{justify-content:flex-start}.rr-metric-grid{grid-template-columns:1fr 1fr}.rr-command-top{flex-direction:column}.rr-statusline{justify-content:flex-start}.rr-hero-kpis{grid-template-columns:1fr 1fr}.rr-source-strip{grid-template-columns:1fr 1fr}}",
    "@media(max-width:720px){html,body{width:100%;max-width:100%;overflow-x:hidden}#v-research,#v-research.on,main{width:100%;max-width:100%;min-width:0}#v-research{padding-left:0;padding-right:0}#v-research .fshead{padding:0 10px;align-items:flex-start}#v-research .fshead h2{font-size:15px;line-height:1.2;max-width:calc(100% - 86px);overflow-wrap:anywhere}#v-research .xbtn{padding:7px 10px;font-size:10px}#research-radar,.rr-shell{width:100%;min-width:0}.rr-command{border-radius:12px;padding:10px;width:100%;overflow:hidden}.rr-title{font-size:18px;overflow-wrap:anywhere}.rr-subtitle{font-size:8px;line-height:1.45;overflow-wrap:anywhere}.rr-statusline{gap:4px;max-width:100%}.rr-badge{font-size:7px;padding:3px 5px;max-width:100%;overflow:hidden;text-overflow:ellipsis}.rr-hero-kpis{gap:6px;margin-top:8px}.rr-hero-kpi{padding:7px 8px}.rr-hero-kpi small{font-size:7px}.rr-hero-kpi b{font-size:12px}.rr-source-strip{gap:5px}.rr-source-box{padding:6px 7px}.rr-source-box b{font-size:8px;white-space:normal;line-height:1.25}.rr-tabs{margin:0;padding:7px 2px;gap:4px}.rr-tab{padding:7px 9px;font-size:8px}.rr-panel-head{padding:0 2px;margin:8px 0 6px}.rr-panel-head h3{font-size:10px}.rr-module-grid,.rr-grid,.rr-lab-grid,.rr-tool-grid{width:100%;grid-template-columns:1fr;min-width:0;gap:7px}.rr-card,.rr-wide{width:100%;min-width:0;border-radius:10px}.rr-card .sh2{padding:8px 9px;font-size:9px}.rr-card .zrow{padding:6px 9px;font-size:9.5px}.rr-head{gap:5px}.rr-cols{display:block}.rr-cols>div+div{border-top:1px solid var(--border);margin-top:4px;padding-top:4px}.rr-lab-table,.rr-mini-table{display:block;overflow-x:auto;white-space:nowrap;font-size:8.5px}.rr-lab-table th,.rr-lab-table td,.rr-mini-table th,.rr-mini-table td{padding:6px}.rr-history{max-height:220px;overflow:auto}.rr-search{gap:5px}.rr-search input{font-size:11px;padding:9px}.rr-btn{padding:7px 8px;font-size:8px}.rr-chiprow{gap:4px}.rr-chip{font-size:7.5px;padding:5px 7px}.rr-tools input,.rr-tools select,.rr-tools textarea{font-size:9px}.rr-metric-grid{gap:5px}.rr-metric{padding:7px 8px}.rr-metric small{font-size:7px}.rr-metric b{font-size:10.5px}.rr-modal{width:100%;max-width:100%;max-height:94vh;border-radius:12px}.rr-overlay{padding:3vh 6px 8px}.rr-modal-body{padding:9px}.rr-modal-head{padding:9px 10px}.rr-kicker{font-size:7.5px;padding:7px 9px}.rr-alert{padding:7px 9px}.rr-alert b{font-size:9px}.rr-alert small{font-size:7.5px}}" /* genuinely mobile-first */
  ].join("");
  document.head.appendChild(s);
}

function eventBody(arr){
  return itemList(arr,function(x){
    var sym=x.symbol||x.sym||"—";
    var clickable=sym&&sym!=="—" ? '<button class="rr-stock-link rr-btn" data-symbol="'+esc(sym.toUpperCase())+'">'+esc(sym)+'</button>' : esc(sym);
    return '<div class="ni"><b>'+clickable+' · '+esc(x.kind||x.category||"Event")+'</b><small>'+esc(x.date||"")+' · '+esc(x.subject||x.expected||"")+'</small></div>';
  },6);
}

function parseCSV(text){
  var rows=[],line="",q=false,cur=[],cols=[];
  for(var i=0;i<text.length;i++){
    var ch=text[i];
    if(ch==='"'){
      if(q && text[i+1]==='"'){line+='"';i++;}else q=!q;
    }else if(ch===','&&!q){cur.push(line);line="";}
    else if((ch==='\n'||ch==='\r')&&!q){
      if(ch==='\r'&&text[i+1]==='\n')i++;
      cur.push(line);line="";
      if(cols.length===0){cols=cur;cur=[];}else if(cur.length===cols.length){var o={};cols.forEach(function(k,j){o[k]=cur[j];});rows.push(o);cur=[];}
    }else line+=ch;
  }
  if(line.length||cur.length){cur.push(line);if(!cols.length)cols=cur;else if(cur.length===cols.length){var o={};cols.forEach(function(k,j){o[k]=cur[j];});rows.push(o);}}
  return rows;
}
function numv(x){var v=parseFloat(String(x==null?"":x).replace(/,/g,""));return isNaN(v)?null:v;}

function stockUniverseSearch(q){
  q=String(q||"").trim().toUpperCase();
  if(!q)return [];
  var arr=Object.keys(STATE.stocks).map(function(k){return STATE.stocks[k];});
  return arr.filter(function(x){return String(x.symbol||"").toUpperCase().indexOf(q)>=0||String(x.company||"").toUpperCase().indexOf(q)>=0;}).slice(0,10);
}

function openDetail(symbol){
  symbol=String(symbol||"").toUpperCase().trim();if(!symbol)return;
  var profile=STATE.stocks[symbol]||{};
  var host=document.getElementById("rr-overlay");
  if(!host)return;
  host.classList.add("open");
  host.innerHTML='<div class="rr-modal"><div class="rr-modal-head"><div class="rr-modal-title"><b>'+esc(symbol)+'</b><small>Loading stock research profile…</small></div><button class="rr-btn" data-close-rr>✕ CLOSE</button></div><div class="rr-modal-body"><div class="mut">Loading history, filings and F&O context…</div></div></div>';
  var histUrl="data/history/"+encodeURIComponent(symbol)+".json?v="+Date.now();
  Promise.all([
    fetch(histUrl,{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("history "+r.status);return r.json();}).catch(function(){return[];}),
    fetch("data/history/NIFTY.json?v="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.json():[];}).catch(function(){return[];})
  ]).then(function(vals){
    var hist=vals[0]||[];
    var niftyHist=vals[1]||[];
    STATE.historyCache[symbol]=hist;
    var r=profile;
    var del=STATE.delivery[symbol];
    var fo=null;
    ((STATE.futures||{}).stocks||[]).some(function(x){if(String(x.symbol||"").toUpperCase()===symbol){fo=x;return true;}return false;});
    var filings=STATE.filings.filter(function(x){return String(x.symbol||"").toUpperCase()===symbol;}).slice(0,8);
    var next=Object.keys(STATE.results).length?STATE.results[symbol]:null;
    var last=hist.length?hist[hist.length-1]:null;
    var prev=hist.length>1?hist[hist.length-2]:null;
    var ret5=(hist.length>5&&numv(hist[hist.length-6].close))?((numv(last.close)/numv(hist[hist.length-6].close)-1)*100):null;
    var ret20=(hist.length>20&&numv(hist[hist.length-21].close))?((numv(last.close)/numv(hist[hist.length-21].close)-1)*100):null;
    var nifty20=(niftyHist.length>20&&numv(niftyHist[niftyHist.length-21].close))?((numv(niftyHist[niftyHist.length-1].close)/numv(niftyHist[niftyHist.length-21].close)-1)*100):null;
    var rel20=ret20!=null&&nifty20!=null?ret20-nifty20:null;
    var reasons=[];
    if(numv(r.from_52w_high_pct)!=null&&numv(r.from_52w_high_pct)>=-1)reasons.push("within 1% of 52W high");
    if(numv(r.vol_vs_avg20)!=null&&numv(r.vol_vs_avg20)>=2)reasons.push("volume >= 2x 20D average");
    if(String(r.above_ema200)==="true")reasons.push("above 200D EMA");
    if(numv(r.rsi14)!=null&&numv(r.rsi14)>=60)reasons.push("RSI >= 60");
    if(del!=null&&numv(del)>=60)reasons.push("delivery >= 60%");
    if(fo&&fo.oi_chg>0&&numv(r.change_pct)>0)reasons.push("long-build style F&O snapshot");
    if(fo&&fo.oi_chg>0&&numv(r.change_pct)<0)reasons.push("short-build style F&O snapshot");
    if(!reasons.length)reasons.push("no special trigger in the stored snapshot; profile is descriptive");
    var body='<div class="rr-metric-grid">'+
      '<div class="rr-metric"><small>PRICE</small><b>'+n(r.price||last&&last.close)+'</b></div>'+
      '<div class="rr-metric"><small>1D</small><b class="'+(numv(r.change_pct)>=0?"up":"dn")+'">'+p(r.change_pct)+'</b></div>'+
      '<div class="rr-metric"><small>5D</small><b class="'+(ret5>=0?"up":"dn")+'">'+p(ret5)+'</b></div>'+
      '<div class="rr-metric"><small>20D</small><b class="'+(ret20>=0?"up":"dn")+'">'+p(ret20)+'</b></div>'+
      '<div class="rr-metric"><small>52W HIGH</small><b>'+n(r.high_52w)+'</b></div>'+
      '<div class="rr-metric"><small>RSI14</small><b>'+n(r.rsi14)+'</b></div>'+
      '<div class="rr-metric"><small>EMA200</small><b>'+n(r.ema200)+'</b></div>'+
      '<div class="rr-metric"><small>DELIVERY</small><b>'+pct0(del)+'</b></div>'+
      '</div>';
    body+='<div class="rr-detail-section"><div class="sh2">WHY THIS STOCK IS IN RESEARCH CONTEXT</div>'+reasons.map(function(x){return'<div class="ni"><b>'+esc(x)+'</b></div>';}).join("")+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">TREND / MOMENTUM</div>'+
      row("20D return",p(ret20))+row("60D return",p(r.return_60d))+row("Relative strength vs NIFTY",p(rel20))+row("MACD histogram",n(r.macd_hist))+row("20D volume ratio",n(r.vol_vs_avg20))+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">F&O</div>'+
      row("Expiry",fo?fo.expiry:"Not available")+row("OI",fo?n(fo.oi):"—")+row("OI change",fo?n(fo.oi_chg):"—")+row("Basis",fo?p(fo.basis_pct):"—")+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">CORPORATE / RESULTS</div>'+eventBody(filings)+
      (next?'<div class="ni"><b>Next result / event: '+esc(next.date||"—")+'</b><small>'+esc(next.company||"")+'</small></div>':"")+'</div>';
    var nb0=notebook(),isWatched=(nb0.watch||[]).indexOf(symbol)>=0,note0=(nb0.notes||{})[symbol]||"";
    body+='<div class="rr-detail-section"><div class="sh2">RESEARCH NOTEBOOK</div><div style="padding:10px 12px"><button class="rr-btn" data-toggle-watch="'+esc(symbol)+'">'+(isWatched?"REMOVE FROM WATCHLIST":"ADD TO WATCHLIST")+'</button><textarea id="rr-modal-note" style="width:100%;margin-top:7px;min-height:65px" placeholder="Browser-local research note…">'+esc(note0)+'</textarea><button class="rr-btn" style="margin-top:6px" data-save-modal-note="'+esc(symbol)+'">SAVE NOTE</button></div></div>';
    body+='<div class="rr-detail-section"><div class="sh2">DATA SOURCE</div>'+row("Screener","ArthaSaar brain-screener snapshot")+row("Historical","ArthaSaar history file")+row("Corporate","NSE/public filings snapshot")+row("Research timestamp",safeDate((STATE.radar||{}).updated))+'</div>';
    host.innerHTML='<div class="rr-modal"><div class="rr-modal-head"><div class="rr-modal-title"><b>'+esc(symbol)+' · '+esc(r.company||"")+'</b><small>'+esc(r.industry||"")+'</small></div><button class="rr-btn" data-close-rr>✕ CLOSE</button></div><div class="rr-modal-body">'+body+'</div></div>';
  });
}


function localGet(key, fallback){
  try{var v=localStorage.getItem(key);return v?JSON.parse(v):fallback;}catch(e){return fallback;}
}
function localSet(key,val){try{localStorage.setItem(key,JSON.stringify(val));}catch(e){}}

function candleDayRows(sym){
  var x=(STATE.candles||{})[sym]||{}, z=x["5m"]||{}, t=z.t||[],o=z.o||[],h=z.h||[],l=z.l||[],cl=z.c||[];
  var map={};
  for(var i=0;i<t.length;i++){
    var dt=new Date(Number(t[i])*1000),day=dt.getUTCFullYear()+"-"+String(dt.getUTCMonth()+1).padStart(2,"0")+"-"+String(dt.getUTCDate()).padStart(2,"0");
    if(!map[day])map[day]=[];
    map[day].push({t:Number(t[i]),o:numv(o[i]),h:numv(h[i]),l:numv(l[i]),c:numv(cl[i])});
  }
  var days=Object.keys(map).sort();
  return {days:days,map:map};
}
function candleGapRows(){
  var out=[];
  Object.keys(STATE.candles||{}).forEach(function(sym){
    var x=candleDayRows(sym),days=x.days;if(days.length<2)return;
    var lastDay=days[days.length-1],prevDay=days[days.length-2],a=x.map[lastDay]||[],p0=x.map[prevDay]||[];
    var open=a.length?a[0].o:null,prevClose=p0.length?p0[p0.length-1].c:null;
    if(open!=null&&prevClose){out.push({symbol:sym,gap_pct:(open/prevClose-1)*100,open:open,previous_close:prevClose,date:lastDay});}
  });
  out.sort(function(a,b){return Math.abs(b.gap_pct)-Math.abs(a.gap_pct);});
  return out;
}
function candleRangeRows(){
  var out=[];
  Object.keys(STATE.candles||{}).forEach(function(sym){
    var x=candleDayRows(sym),days=x.days;if(!days.length)return;
    var a=x.map[days[days.length-1]]||[];if(!a.length)return;
    var hi=Math.max.apply(null,a.map(function(z){return z.h==null?-Infinity:z.h;})),lo=Math.min.apply(null,a.map(function(z){return z.l==null?Infinity:z.l;})),op=a[0].o;
    if(isFinite(hi)&&isFinite(lo)&&op){out.push({symbol:sym,session_range_pct:(hi-lo)/op*100,date:days[days.length-1]});}
  });
  out.sort(function(a,b){return b.session_range_pct-a.session_range_pct;});
  return out;
}


function exportCSV(rows, filename){
  rows=rows||[];
  if(!rows.length){alert("No rows to export.");return;}
  var keys=[],seen={};
  rows.forEach(function(r){Object.keys(r||{}).forEach(function(k){if(!seen[k]){seen[k]=1;keys.push(k);}});});
  function cell(v){var s=v==null?"":String(v);return '"'+s.replace(/"/g,'""')+'"';}
  var csv=keys.map(cell).join(",")+"\n"+rows.map(function(r){return keys.map(function(k){return cell(r[k]);}).join(",");}).join("\n");
  var blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=filename||"arthasaar-export.csv";document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},0);
}

function compareProfile(sym){
  var p=STATE.stocks[String(sym||"").toUpperCase()]||{};
  return {symbol:String(sym||"").toUpperCase(),company:p.company||"",price:numv(p.price),change_pct:numv(p.change_pct),return_20d:numv(p.return_20d),return_60d:numv(p.return_60d),rsi14:numv(p.rsi14),ema200:numv(p.ema200),vol_vs_avg20:numv(p.vol_vs_avg20),above_ema200:String(p.above_ema200)==="true",industry:p.industry||""};
}
function renderCompare(a,b){
  var x=compareProfile(a),y=compareProfile(b);
  function diff(v1,v2){if(v1==null||v2==null)return "—";var d=v1-v2;return (d>=0?"+":"")+d.toFixed(2);}
  return '<div class="rr-mini-table-wrap"><table class="rr-mini-table"><thead><tr><th>Metric</th><th>'+esc(x.symbol)+'</th><th>'+esc(y.symbol)+'</th><th>Δ A-B</th></tr></thead><tbody>'+
    [["Price",x.price,y.price,n],["1D %",x.change_pct,y.change_pct,p],["20D %",x.return_20d,y.return_20d,p],["60D %",x.return_60d,y.return_60d,p],["RSI",x.rsi14,y.rsi14,n],["EMA200",x.ema200,y.ema200,n],["Volume / 20D",x.vol_vs_avg20,y.vol_vs_avg20,n],["Above EMA200",x.above_ema200?"YES":"NO",y.above_ema200?"YES":"NO",function(){return"—";}],["Sector",x.industry||"—",y.industry||"—",function(){return x.industry===y.industry?"same":"different";}]]
    .map(function(r){var fmt=r[3];return'<tr><td>'+esc(r[0])+'</td><td class="numr">'+esc(typeof fmt==="function"&&r[1]!==null&&r[1]!==undefined?fmt(r[1]):r[1])+'</td><td class="numr">'+esc(typeof fmt==="function"&&r[2]!==null&&r[2]!==undefined?fmt(r[2]):r[2])+'</td><td class="numr">'+esc(diff(r[1],r[2]))+'</td></tr>';}).join("")+
    '</tbody></table></div>';
}
function sectorRows(sector){
  var arr=Object.keys(STATE.stocks).map(function(k){return STATE.stocks[k];}).filter(function(x){return String(x.industry||"Other")===sector;});
  arr.sort(function(a,b){return numv(b.return_20d||b.change_pct)-numv(a.return_20d||a.change_pct);});
  return arr.slice(0,12);
}
function renderSectorPick(sector){
  var host=document.getElementById("rr-sector-result");if(!host)return;
  var rows=sectorRows(sector);
  host.innerHTML=rows.length?'<table class="rr-mini-table"><thead><tr><th>Symbol</th><th>Company</th><th>1D</th><th>20D</th><th>RSI</th></tr></thead><tbody>'+rows.map(function(x){return'<tr><td><button class="rr-btn" data-symbol="'+esc(x.symbol)+'">'+esc(x.symbol)+'</button></td><td>'+esc(x.company||"")+'</td><td class="numr">'+p(numv(x.change_pct))+'</td><td class="numr">'+p(numv(x.return_20d))+'</td><td class="numr">'+n(numv(x.rsi14))+'</td></tr>';}).join("")+'</tbody></table>':'<div class="mut">No stock rows for this sector.</div>';
}
function marketReplay(date){
  var hist=(STATE.marketHistory||{}).daily||[];
  return hist.find(function(x){return x.date===date;})||null;
}
function renderReplay(date){
  var host=document.getElementById("rr-replay-body");if(!host)return;
  var x=marketReplay(date);
  if(!x){host.innerHTML='<div class="mut">No market replay snapshot for this date.</div>';return;}
  host.innerHTML=row("Advancers",n(x.breadth&&x.breadth.advancers))+row("Decliners",n(x.breadth&&x.breadth.decliners))+row("Advance ratio",pct0(x.breadth&&x.breadth.advance_ratio_pct))+row("EMA200 participation",pct0(x.breadth&&x.breadth.ema200_pct))+row("New-high zone",n(x.high_low&&x.high_low.new_high_zone),"up")+row("New-low zone",n(x.high_low&&x.high_low.new_low_zone),"dn")+row("Regime",x.regime&&x.regime.label||"—")+row("NIFTY change",p(x.regime&&x.regime.nifty_change_pct))+row("FII net",n(x.regime&&x.regime.fii_net_cr))+
    '<div class="rr-sub">Sector leaders</div>'+rows(x.sector_top||[],"sector","avg_1d_pct",function(){return"up";},6)+'<div class="rr-sub">Sector laggards</div>'+rows(x.sector_bottom||[],"sector","avg_1d_pct",function(){return"dn";},6);
}
function notebook(){
  var obj=localGet("artha_research_notebook_v1",{watch:[],notes:{}});
  return obj&&obj.watch?obj:{watch:[],notes:{}};
}
function toggleWatch(sym){
  var nb=notebook(),s=String(sym||"").toUpperCase();
  nb.watch=nb.watch||[];var i=nb.watch.indexOf(s);
  if(i>=0)nb.watch.splice(i,1);else nb.watch.unshift(s);
  localSet("artha_research_notebook_v1",nb);
  return nb;
}
function saveNote(sym,textv){
  var nb=notebook();nb.notes=nb.notes||{};nb.notes[String(sym||"").toUpperCase()]=textv||"";localSet("artha_research_notebook_v1",nb);
}
function maybeNotifyAlerts(payload){
  if(!payload||!("Notification" in window)||Notification.permission!=="granted")return;
  var last=localGet("artha_research_last_alert_update","");
  if(last===payload.updated)return;
  var top=(payload.alerts||[]).slice(0,3);
  if(top.length){try{new Notification("ArthaSaar Research Alerts",{body:top.map(function(x){return (x.symbol?x.symbol+" · ":"")+x.title;}).join("\n")});}catch(e){}}
  localSet("artha_research_last_alert_update",payload.updated||"");
}
function enableBrowserAlerts(){
  if(!("Notification" in window)){alert("Browser notifications are not supported here.");return;}
  Notification.requestPermission().then(function(p){alert(p==="granted"?"Browser alerts enabled for this session/browser.":"Notification permission was not granted.");});
}
function alertsBody(){
  var arr=(STATE.alerts||{}).alerts||[];
  return arr.slice(0,18).map(function(x){return'<div class="rr-alert"><b>'+esc(x.symbol||"")+' · '+esc(x.title||x.kind||"Alert")+'</b><small>'+esc(x.detail||"")+' · '+esc(x.source||"")+'</small></div>';}).join("")||'<div class="mut">No alerts in the latest committed snapshot.</div>';
}
function renderDataHealth(){
  var h=STATE.health||{};var s=h.summary||{};
  return row("Feeds OK",n(s.ok)+"/"+n(s.total),s.problems?"dn":"up")+row("Problems",n(s.problems),s.problems?"dn":"up")+row("Health updated",safeDate(h.updated))+
    '<div class="rr-history"><table class="rr-mini-table"><thead><tr><th>Feed</th><th>Status</th><th>Age</th><th>Coverage</th><th>Source</th></tr></thead><tbody>'+
    (h.feeds||[]).map(function(x){return'<tr><td>'+esc(x.label||x.id)+'</td><td class="'+(x.status==="ok"?"up":"dn")+'">'+esc(String(x.status||"").toUpperCase())+'</td><td class="numr">'+(x.age_hours==null?"—":n(x.age_hours)+"h")+'</td><td>'+esc(x.coverage||"—")+'</td><td>'+esc(x.source||"")+'</td></tr>';}).join("")+
    '</tbody></table></div>';
}
function signalOutcomeBody(){
  var sh=STATE.signalHistory||{},agg=sh.aggregate||{},keys=Object.keys(agg);
  return '<div style="overflow:auto"><table class="rr-mini-table"><thead><tr><th>Signal</th><th>Events</th><th>5D avg</th><th>5D +%</th><th>20D avg</th><th>20D +%</th></tr></thead><tbody>'+
    keys.map(function(k){var x=agg[k]||{};return'<tr><td>'+esc(k.replace(/_/g," ").toUpperCase())+'</td><td class="numr">'+n(x.observations)+'</td><td class="numr">'+p(x.next5_mean_pct)+'</td><td class="numr">'+pct0(x.next5_positive_pct)+'</td><td class="numr">'+p(x.next20_mean_pct)+'</td><td class="numr">'+pct0(x.next20_positive_pct)+'</td></tr>';}).join("")+
    '</tbody></table></div><div class="rr-kicker">Outcome tracker is based only on prices after each stored signal date. Pending signals are excluded from completed statistics.</div>';
}

function renderResearchLab(d){
  var lab=d.research_lab||{},bt=(lab.backtests||{}).signals||{},daily=lab.daily_history||[],mh=(lab.market_replay||{}).daily||[],surv=lab.survivorship||{},fresh=lab.freshness||{};
  var signals=Object.keys(bt);
  var back='<div style="overflow:auto"><table class="rr-lab-table"><thead><tr><th>Signal</th><th>Events</th><th>Next 5D avg</th><th>5D positive</th><th>Next 20D avg</th><th>20D positive</th></tr></thead><tbody>'+
    (signals.map(function(k){var x=bt[k]||{};return'<tr><td><b>'+esc(k.replace(/_/g," ").toUpperCase())+'</b></td><td class="numr">'+n(x.observations)+'</td><td class="numr">'+p(x.next5_mean_pct)+'</td><td class="numr">'+pct0(x.next5_positive_pct)+'</td><td class="numr">'+p(x.next20_mean_pct)+'</td><td class="numr">'+pct0(x.next20_positive_pct)+'</td></tr>';}).join("")||'<tr><td colspan="6">No backtest observations yet.</td></tr>')+
    '</tbody></table></div><div class="rr-kicker">'+esc((lab.backtests||{}).method||"")+' · scanned '+n((lab.backtests||{}).history_files_scanned)+' history files.</div>';
  var hist='<div class="rr-history"><table class="rr-lab-table"><thead><tr><th>Date</th><th>Advancers</th><th>Decliners</th><th>Advance ratio</th><th>High zone</th><th>Low zone</th></tr></thead><tbody>'+
    daily.slice(-20).reverse().map(function(x){return'<tr><td>'+esc(x.date)+'</td><td class="numr">'+n(x.advancers)+'</td><td class="numr">'+n(x.decliners)+'</td><td class="numr">'+pct0(x.advance_ratio_pct)+'</td><td class="numr">'+n(x.new_high_zone_count)+'</td><td class="numr">'+n(x.new_low_zone_count)+'</td></tr>';}).join("")+
    '</tbody></table></div>';
  var sectors=(d.features&&d.features.sector_matrix&&d.features.sector_matrix.sectors)||[];
  var sectorOptions=sectors.map(function(x){return'<option value="'+esc(x.sector)+'">'+esc(x.sector)+'</option>';}).join("");
  var replayOptions=mh.slice(-120).reverse().map(function(x){return'<option value="'+esc(x.date)+'">'+esc(x.date)+'</option>';}).join("");
  var nb=notebook(),notesHtml=(nb.watch||[]).slice(0,12).map(function(s){return'<span class="rr-watch-item">'+esc(s)+'<button data-unwatch="'+esc(s)+'">×</button></span>';}).join("")||'<span class="mut">No saved stocks yet.</span>';
  var alertCount=(STATE.alerts||{}).count||0;
  var health=(STATE.health||{}).summary||{};
  return '<div class="rr-lab-grid">'+
    '<div class="card rr-card"><div class="sh2">RESEARCH LAB · STOCK DRILL-DOWN</div><div style="padding:10px 12px"><div class="rr-search"><input id="rr-stock-search" type="search" placeholder="Search symbol or company…"><button class="rr-btn" id="rr-clear-search">CLEAR</button><button class="rr-btn" id="rr-export-search">EXPORT CSV</button></div><div id="rr-search-results"></div><div class="rr-chiprow"><button class="rr-chip" data-symbol="RELIANCE">RELIANCE</button><button class="rr-chip" data-symbol="HDFCBANK">HDFCBANK</button><button class="rr-chip" data-symbol="ICICIBANK">ICICIBANK</button><button class="rr-chip" data-symbol="TCS">TCS</button><button class="rr-chip" data-symbol="INFY">INFY</button></div></div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">RESEARCH LAB · COVERAGE</div>'+row("Universe searchable",n(lab.search_universe))+row("Radar modules",n(lab.module_count))+row("Alerts",n(alertCount))+row("Feeds OK",n(health.ok)+"/"+n(health.total))+row("Source policy","Free/public only")+row("Updated",safeDate(d.updated))+'<div class="rr-kicker">NSE/public exchange snapshots · ArthaSaar calculations · Yahoo historical backup.</div></div>'+
    '<div class="card rr-card rr-wide rr-tools"><div class="sh2">MARKET REPLAY</div><div style="padding:10px 12px"><label>Select historical date</label><select id="rr-replay-select">'+replayOptions+'</select><div id="rr-replay-body" class="rr-replay-body"></div></div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">COMPARE TWO STOCKS</div><div style="padding:10px 12px"><label>Stock A</label><input id="rr-compare-a" value="RELIANCE"><label>Stock B</label><input id="rr-compare-b" value="ONGC"><button class="rr-btn" id="rr-compare-go" style="margin-top:7px">COMPARE</button><div id="rr-compare-body" style="margin-top:8px"></div><div class="rr-kicker">Comparison uses the same EOD snapshot and historical methods for both symbols.</div></div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">SECTOR → STOCK DRILL-DOWN</div><div style="padding:10px 12px"><label>Sector</label><select id="rr-sector-select">'+sectorOptions+'</select><div id="rr-sector-result" style="margin-top:8px"></div></div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">RESEARCH NOTEBOOK</div><div style="padding:10px 12px"><div class="rr-watch">'+notesHtml+'</div><label>Note for stock</label><div class="rr-search"><input id="rr-note-symbol" value="'+esc((nb.watch||[])[0]||"RELIANCE")+'"><button class="rr-btn" id="rr-note-watch">WATCH</button></div><textarea id="rr-note-text" placeholder="Private browser-local research note…">'+esc(((nb.notes||{})[(nb.watch||[])[0]||"RELIANCE"]||""))+'</textarea><button class="rr-btn rr-note-save" id="rr-note-save">SAVE NOTE</button><div class="rr-kicker">Stored only in this browser via localStorage. Nothing is sent to GitHub.</div></div></div>'+
    '<div class="card rr-card rr-wide rr-tools"><div class="sh2">SIGNAL OUTCOME TRACKER</div><div style="padding:10px 12px">'+signalOutcomeBody()+'</div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">SIGNAL HISTORY / BACKTEST</div>'+back+'<div class="rr-kicker"><button class="rr-btn" id="rr-export-backtest">EXPORT BACKTEST CSV</button></div></div>'+
    '<div class="card rr-card rr-tools"><div class="sh2">DATA QUALITY CENTER</div><div style="padding:10px 12px">'+renderDataHealth()+'<div class="rr-kicker">Survivorship status: '+esc(surv.status||"tracking")+' · membership-history days: '+n(surv.membership_history_days)+'</div></div></div>'+
    '<div class="card rr-card rr-wide rr-tools"><div class="sh2">ALERT CENTER</div><div class="rr-kicker">Latest committed public-data signals. <button class="rr-btn" id="rr-browser-alerts">ENABLE BROWSER ALERTS</button> <button class="rr-btn" id="rr-export-alerts">EXPORT ALERTS CSV</button></div>'+alertsBody()+'</div>'+
    '<div class="card rr-card rr-wide rr-tools"><div class="sh2">BREADTH HISTORY</div>'+hist+'</div>'+
    '</div>';
}

function wireLab(){
  var activeTab=localGet("artha_research_active_tab","overview");
  function setTab(tab){
    document.querySelectorAll("[data-rr-tab]").forEach(function(b){b.classList.toggle("on",b.getAttribute("data-rr-tab")===tab);});
    document.querySelectorAll("[data-rr-panel]").forEach(function(p){p.classList.toggle("on",p.getAttribute("data-rr-panel")===tab);});
    localSet("artha_research_active_tab",tab);
    if(tab==="lab"){setTimeout(function(){var rs=document.getElementById("rr-replay-select");if(rs)renderReplay(rs.value);},0);}
  }
  document.querySelectorAll("[data-rr-tab]").forEach(function(b){b.addEventListener("click",function(){setTab(b.getAttribute("data-rr-tab"));});});
  if(document.querySelector('[data-rr-tab="'+activeTab+'"]'))setTab(activeTab);else setTab("overview");

  var input=document.getElementById("rr-stock-search"),res=document.getElementById("rr-search-results");
  function paint(q){
    if(!res)return;
    var arr=stockUniverseSearch(q);
    if(!q){res.innerHTML="";return;}
    res.innerHTML='<div class="rr-results">'+(arr.length?arr.map(function(x){return'<button class="rr-result" data-symbol="'+esc(String(x.symbol).toUpperCase())+'"><b>'+esc(x.symbol)+'</b><small>'+esc(x.company||"")+'</small></button>';}).join(""):'<div class="mut">No matching stock.</div>')+'</div>';
  }
  if(input)input.addEventListener("input",function(){paint(input.value);});
  var exs=document.getElementById("rr-export-search");if(exs)exs.addEventListener("click",function(){exportCSV(stockUniverseSearch(input&&input.value),"arthasaar-stock-search.csv");});
  var clear=document.getElementById("rr-clear-search");
  if(clear)clear.addEventListener("click",function(){if(input)input.value="";paint("");if(input)input.focus();});

  var replay=document.getElementById("rr-replay-select");
  if(replay){renderReplay(replay.value);replay.addEventListener("change",function(){renderReplay(replay.value);});}
  var ca=document.getElementById("rr-compare-a"),cb=document.getElementById("rr-compare-b"),cg=document.getElementById("rr-compare-go"),cp=document.getElementById("rr-compare-body");
  function doCompare(){
    if(!cp)return;
    var a=String(ca&&ca.value||"").toUpperCase(),b=String(cb&&cb.value||"").toUpperCase();
    cp.innerHTML='<div class="mut">Loading comparison history…</div>';
    Promise.all([
      fetch("data/history/"+encodeURIComponent(a)+".json?v="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.json():[];}).catch(function(){return[];}),
      fetch("data/history/"+encodeURIComponent(b)+".json?v="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.json():[];}).catch(function(){return[];})
    ]).then(function(v){
      [a,b].forEach(function(sym,i){
        var arr=v[i]||[];
        if(arr.length){
          var last=arr[arr.length-1],p20=arr.length>20?numv(arr[arr.length-21].close):null,q=STATE.stocks[sym]||{};
          q.return_20d=p20&&numv(last.close)?((numv(last.close)/p20-1)*100):null;STATE.stocks[sym]=q;
        }
      });
      cp.innerHTML=renderCompare(a,b);
    });
  }
  if(cg)cg.addEventListener("click",doCompare);doCompare();

  var ss=document.getElementById("rr-sector-select");if(ss){renderSectorPick(ss.value);ss.addEventListener("change",function(){renderSectorPick(ss.value);});}

  var nb=notebook(),ns=document.getElementById("rr-note-symbol"),nt=document.getElementById("rr-note-text"),nw=document.getElementById("rr-note-watch"),nsv=document.getElementById("rr-note-save");
  if(nw)nw.addEventListener("click",function(){toggleWatch(ns.value);render(STATE.radar);});
  if(nsv)nsv.addEventListener("click",function(){saveNote(ns.value,nt.value);alert("Saved in this browser.");});
  if(ns)ns.addEventListener("change",function(){var x=notebook();if(nt)nt.value=(x.notes||{})[String(ns.value).toUpperCase()]||"";});

  var ex=document.getElementById("rr-export-backtest");if(ex)ex.addEventListener("click",function(){var bt=(STATE.radar.research_lab||{}).backtests||{};var rows=Object.keys(bt.signals||{}).map(function(k){return Object.assign({signal:k},bt.signals[k]);});exportCSV(rows,"arthasaar-backtest.csv");});
  var ea=document.getElementById("rr-export-alerts");if(ea)ea.addEventListener("click",function(){exportCSV((STATE.alerts||{}).alerts||[],"arthasaar-alerts.csv");});
  var en=document.getElementById("rr-browser-alerts");if(en)en.addEventListener("click",enableBrowserAlerts);

  document.querySelectorAll("[data-unwatch]").forEach(function(el){el.addEventListener("click",function(){var x=notebook();x.watch=(x.watch||[]).filter(function(v){return v!==el.getAttribute("data-unwatch");});localSet("artha_research_notebook_v1",x);render(STATE.radar);});});
}

function render(d){
  STATE.radar=d;installCSS();
  var host=document.getElementById("research-radar");if(!host)return;
  var f=d.features||{};
  var w=f.week52||{},br=f.breadth_history||{},ix=f.index_changes||{},ma=f.rbi_macro||{},bb=f.bulk_block||{},re=f.results||{},se=f.sector_rotation||{},rg=f.market_regime||{},dr=f.data_resilience||{},ca=f.corporate_actions||{};
  var h=f.breakout_radar||{},vs=f.volume_shock||{},dc=f.delivery_conviction||{},ad=f.accumulation_distribution||{},gap=f.gap_radar||{};
  var rs=f.relative_strength||{},sm=f.sector_matrix||{},ve=f.volatility_expansion||{},rx=f.range_expansion||{};
  var mo=f.momentum_dashboard||{},th=f.trend_health||{},cross=f.dma_cross_radar||{},dm=f.distance_map||{};
  var es=f.earnings_surprise||{},pi=f.promoter_insider||{},pl=f.pledge_watch||{},cc=f.corporate_calendar||{};
  var dv=f.dividend_radar||{},bo=f.buyback_open_offer||{},foi=f.fo_oi_change||{},op=f.option_pulse||{};
  var fm=f.futures_basis||{},fb=f.fo_buildup||{},bt=f.bulk_followthrough||{},iflow=f.institutional_flow_trend||{};
  var bm=f.breadth_momentum||{},hlb=f.high_low_breadth||{},mc=f.market_concentration||{},nl=f.nifty_leadership||{};
  var ib=f.index_bucket_breadth||{},ls=f.liquidity_stress||{},rel=f.data_reliability||{},rdd=f.data_resilience_detail||{};
  var ds=d.daily_status||{};
  var hs=dr.summary||{};
  var alertCount=(STATE.alerts||{}).count||0, health=(STATE.health||{}).summary||{}, healthReady=(health.total||0)>0, healthProblems=health.problems||0;
  var source=ds.membership_source||"public snapshots";

  function grid(a){return '<div class="rr-module-grid">'+a.filter(Boolean).join("")+'</div>';}
  function empty(msg,meta){return '<div class="rr-empty"><b>'+esc(msg)+'</b>'+(meta?'<div style="margin-top:3px">'+esc(meta)+'</div>':"")+'</div>';}
  function panelHead(title,sub){return '<div class="rr-panel-head"><h3>'+esc(title)+'</h3><small>'+esc(sub||"")+'</small></div>';}
  function concBody(){
    if(!(mc.indices||[]).length)return empty("Concentration weights unavailable","The current free constituents snapshot has membership but no index weights. No synthetic weights are shown.");
    var rows=mc.indices.map(function(x){return x.available?row(x.index,"Top 10 "+n(x.top10_weight_pct)+"%"):row(x.index,"Weights unavailable");}).join("");
    return rows || empty("No concentration snapshot","");
  }
  function leaderBody(){
    if(!(nl.leaders||[]).length)return empty("NIFTY leadership waiting","The latest membership fallback is still settling. The daily constituent collector will repopulate this module.");
    return rows(nl.leaders,"symbol","relative_strength_20d",function(){return"up";},12);
  }
  function unavailableBody(title,reason){return empty(title,reason||"This module is not populated by the current free public snapshot.");}

  var regimeClass=(rg.label||"").indexOf("RISK-OFF")>=0?"dn":(rg.label||"").indexOf("RISK-ON")>=0?"up":"";
  var radarAge=freshness(d.updated);
  var sourceStrip=[
    ["Market brain",ds.market_data_updated],
    ["Delivery",ds.delivery_updated],
    ["F&O",ds.futures_updated],
    ["Research radar",d.updated],
  ].map(function(x){var fr=freshness(x[1]);return'<div class="rr-source-box"><small>'+esc(x[0])+'</small><b>'+esc(fr.label)+' · '+esc(safeDate(x[1]))+'</b></div>';}).join("");

  var hero='<div class="rr-command">'+
    '<div class="rr-command-top"><div><div class="rr-eyebrow">ARTHASAAR · RESEARCH TERMINAL</div><div class="rr-title">Daily Market Research</div><div class="rr-subtitle">44 free-data modules · '+esc(source)+' · generated '+esc(safeDate(d.updated))+'</div></div>'+
    '<div class="rr-statusline">'+sourceBadge("GitHub Actions",d.updated)+'<span class="rr-badge '+(healthReady?(healthProblems?"stale":"fresh"):"neutral")+'">'+esc(healthReady?(healthProblems?String(healthProblems)+" data issues":"DATA HEALTH OK"):"HEALTH SNAPSHOT PENDING")+'</span><span class="rr-badge rr-source">'+n(alertCount)+" alerts"+'</span></div></div>'+
    '<div class="rr-hero-kpis">'+
      '<div class="rr-hero-kpi"><small>REGIME</small><b class="'+regimeClass+'">'+esc(rg.label||"—")+'</b></div>'+
      '<div class="rr-hero-kpi"><small>NIFTY 50</small><b class="'+((rg.nifty_change_pct||0)>=0?"up":"dn")+'">'+p(rg.nifty_change_pct)+'</b></div>'+
      '<div class="rr-hero-kpi"><small>BREADTH</small><b>'+p(rg.advance_ratio_pct)+'</b></div>'+
      '<div class="rr-hero-kpi"><small>EMA200</small><b>'+pct0(rg.ema200_pct)+'</b></div>'+
      '<div class="rr-hero-kpi"><small>FII NET</small><b class="'+((rg.fii_net_cr||0)>=0?"up":"dn")+'">'+n(rg.fii_net_cr)+'</b></div>'+
      '<div class="rr-hero-kpi"><small>UNIVERSE</small><b>'+n(rel.stocks||0)+'</b></div>'+
    '</div>'+
    '<div class="rr-source-strip">'+sourceStrip+'</div>'+
  '</div>';

  var tabs=[
    ["overview","Overview"],["signals","Signals"],["events","Events"],["derivatives","Derivatives"],["structure","Structure"],["lab","Research Lab"]
  ];
  var nav='<div class="rr-tabs">'+tabs.map(function(x){return'<button class="rr-tab" data-rr-tab="'+x[0]+'">'+esc(x[1])+'</button>';}).join("")+'</div>';

  var overview=grid([
    card("09","MARKET REGIME",row("Regime",rg.label||"—",regimeClass)+row("Composite",n(rg.score)+"/4")+row("Breadth",p(rg.advance_ratio_pct))+row("NIFTY 50",p(rg.nifty_change_pct),(rg.nifty_change_pct||0)>=0?"up":"dn"),"Derived, descriptive",d.updated),
    card("03","MARKET BREADTH",row("Advancers",n((br.today||{}).advancers),"up")+row("Decliners",n((br.today||{}).decliners),"dn")+row("Advance ratio",p((br.today||{}).advance_ratio_pct))+row("200D EMA",pct0((br.today||{}).ema200_pct)),"Derived universe",d.updated),
    card("02","52-WEEK MAP",row("Near high zone",n(w.new_high_zone_count),"up")+row("Near low zone",n(w.new_low_zone_count),"dn")+rows(w.near_highs,"symbol","from_high_pct",function(){return"up";},3)+rows(w.near_lows,"symbol","from_low_pct",function(){return"dn";},3),"ArthaSaar screener",d.updated),
    card("08","SECTOR ROTATION",rows(se.sectors,"sector","avg_1d_pct",function(x){return(x.avg_1d_pct||0)>=0?"up":"dn";},7),"Derived sectors",d.updated),
    card("36","INSTITUTIONAL FLOWS",row("FII current",n((iflow.current||{}).net_cr),(iflow.current&&iflow.current.net_cr||0)>=0?"up":"dn")+row("DII current",n((iflow.dii_current||{}).net_cr),(iflow.dii_current&&iflow.dii_current.net_cr||0)>=0?"up":"dn")+row("FII sell days",n(iflow.fii_sell_days),(iflow.fii_sell_days||0)>0?"dn":"up"),"FII/DII snapshot",d.updated),
    card("04","INDEX / MEMBERSHIP",Object.keys(ix.membership_changes||{}).map(function(k){var z=ix.membership_changes[k]||{};return row(k,(z.added||[]).length+" in · "+(z.removed||[]).length+" out");}).join("")+row("Indices tracked",n(ix.indices_count))+row("Membership source",source),"NSE/public",d.updated),
    card("05","RBI / MACRO PULSE",itemList(ma.indicators,function(x){return'<div class="ni"><b>'+esc(x.name||"Macro")+'</b><small>'+esc(x.value||"—")+' · '+esc(x.date||"")+'</small></div>';},5),"RBI/public macro",ma.macro_updated||d.updated),
    card("10","DATA RESILIENCE",row("Feeds OK",n((hs.ok||rdd.health_summary&&rdd.health_summary.ok))+"/"+n((hs.total||rdd.health_summary&&rdd.health_summary.total)))+row("Problems",n((hs.problems||rdd.health_summary&&rdd.health_summary.problems)),((hs.problems||rdd.health_summary&&rdd.health_summary.problems)||0)?"dn":"up")+row("Fallback","NSE → Yahoo → last valid"),"Data health",dr.health_updated||rdd.health_updated||d.updated),
    card("43","DATA RELIABILITY",row("Coverage",pct0(rel.coverage_score_pct))+row("History ≥200D",pct0(rel.history_ge_200d_pct))+row("EMA200 coverage",pct0(rel.ema200_coverage_pct))+row("Delivery rows",n(rel.delivery_coverage)),"Repo coverage",d.updated),

  ]);

  var signals=grid([
    card("11","52W BREAKOUT RADAR",row("Candidates",n(h.count),"up")+rows(h.rows,"symbol","distance_252_high_pct",function(){return"up";},7),"Derived 252D",d.updated),
    card("12","VOLUME SHOCK",rows(vs.rows,"symbol","vol_vs_avg20",function(){return"up";},7),"NSE/Yahoo history",d.updated),
    card("13","DELIVERY CONVICTION",row("Coverage",n(dc.coverage))+row("Avg delivery",pct0(dc.avg_delivery_pct))+rows(dc.high_delivery_up,"symbol","delivery_pct",function(){return"up";},4),"NSE delivery",ds.delivery_updated||d.updated),
    card("14","ACCUMULATION / DISTRIBUTION",'<div class="rr-cols"><div><div class="rr-sub">Accumulation</div>'+rows(ad.accumulation,"symbol","volume_ratio",function(){return"up";},4)+'</div><div><div class="rr-sub">Distribution</div>'+rows(ad.distribution,"symbol","volume_ratio",function(){return"dn";},4)+'</div></div>',"Derived",d.updated),
    card("15","GAP RADAR",candleGapRows().length?'<div class="rr-kicker">Intraday OHLC coverage · '+n(Object.keys(STATE.candles||{}).length)+' symbols</div>'+rows(candleGapRows(),"symbol","gap_pct",function(x){return(x.gap_pct||0)>=0?"up":"dn";},8):unavailableBody("Intraday OHLC snapshot unavailable","No candle snapshot is available for the current published run."),"Candles · intraday subset",(STATE.candlesUpdated||d.updated)),
    card("16","RELATIVE STRENGTH",row("NIFTY 20D",p(rs.benchmark_return_20d_pct))+rows(rs.leaders,"symbol","relative_strength_20d",function(){return"up";},5)+rows(rs.laggards,"symbol","relative_strength_20d",function(){return"dn";},5),"Derived",d.updated),
    card("18","VOLATILITY EXPANSION",rows(ve.rows,"symbol","vol_expansion",function(x){return(x.vol_expansion||0)>=1?"up":"";},7),"ArthaSaar history",d.updated),
    card("19","RANGE EXPANSION",candleRangeRows().length?'<div class="rr-kicker">Session high-low range · intraday subset</div>'+rows(candleRangeRows(),"symbol","session_range_pct",function(){return"up";},8):unavailableBody("Intraday range snapshot unavailable","Close-to-close volatility proxy remains available in the Radar."),"Candles · intraday subset",((STATE.candles&&STATE.candles.updated)||d.updated)),
    card("20","MOMENTUM DASHBOARD",row("RSI >60",n((mo.rsi_high||[]).length),"up")+row("RSI <40",n((mo.rsi_low||[]).length),"dn")+row("MACD positive",n((mo.macd_positive||[]).length),"up")+rows(mo.roc_leaders,"symbol","return_20d",function(){return"up";},5),"RSI/MACD/ROC",d.updated),
    card("21","TREND HEALTH",row("Above EMA200",pct0(th.above_ema200_pct))+rows(th.above_ema200,"symbol","return_20d",function(){return"up";},4)+rows(th.below_ema200,"symbol","return_20d",function(){return"dn";},4),"Derived trend",d.updated),
    card("22","GOLDEN / DEATH CROSS",row("Golden",n(cross.golden_cross_count),"up")+row("Death",n(cross.death_cross_count),"dn")+rows(cross.golden_candidates,"symbol","return_20d",function(){return"up";},3)+rows(cross.death_candidates,"symbol","return_20d",function(){return"dn";},3),"50D / 200D",d.updated),
    card("23","52W DISTANCE MAP",rows(dm.near_high_200d,"symbol","distance_252_high_pct",function(){return"up";},4)+rows(dm.near_low_200d,"symbol","distance_252_low_pct",function(){return"dn";},4),"252D history",d.updated),
    card("37","BREADTH MOMENTUM",row("3D up streak",n(bm.three_day_up),"up")+row("3D down streak",n(bm.three_day_down),"dn")+row("Volume >2×",n(bm.volume_spike_2x)),"Universe",d.updated),
    card("38","NEW HIGH / LOW BREADTH",row("New-high zone",n(hlb.new_high_zone),"up")+row("New-low zone",n(hlb.new_low_zone),"dn")+rows(hlb.near_highs,"symbol","change_pct",function(){return"up";},3)+rows(hlb.near_lows,"symbol","change_pct",function(){return"dn";},3),"Universe",d.updated),
    card("42","LIQUIDITY STRESS",row("Low volume <0.5×",n(ls.low_volume_lt_0_5x),"dn")+row("High volume >2×",n(ls.high_volume_gt_2x),"up")+row("History <60D",n(ls.illiquid_history_lt_60d),"dn")+row("Universe",n(ls.coverage)),"ArthaSaar coverage",d.updated)
  ]);

  var events=grid([
    card("01","CORPORATE ACTIONS",eventBody(ca.events),"NSE filings",d.updated),
    card("06","BULK / BLOCK DEALS",'<div class="rr-cols"><div>'+rows(bb.bulk,"s","t",null,4)+'</div><div>'+rows(bb.block,"s","t",null,4)+'</div></div>',"NSE-derived",bb.updated||d.updated),
    card("07","RESULTS CALENDAR",rows(re.items,"sym","date",null,7),re.quarter||"Public results",re.updated||d.updated),
    card("24","EARNINGS SURPRISE",row("Standardized surprise","Unavailable")+row("Upcoming results",n((es.upcoming_results||[]).length))+eventBody(es.results_filing_events),"Public coverage",d.updated),
    card("25","PROMOTER / INSIDER",row("Events",n(pi.count))+eventBody(pi.events),"NSE/public filings",d.updated),
    card("26","PLEDGE / ENCUMBRANCE",row("Events",n(pl.count))+eventBody(pl.events),"NSE/public filings",d.updated),
    card("27","CORPORATE CALENDAR",rows(cc.next_results,"sym","date",null,8),"Results/filings",re.updated||d.updated),
    card("28","DIVIDEND RADAR",row("Events",n(dv.count))+eventBody(dv.events),"NSE/public filings",d.updated),
    card("29","BUYBACK / OPEN OFFER",row("Events",n(bo.count))+eventBody(bo.events),"NSE/public filings",d.updated),
    card("35","BULK FOLLOW-THROUGH",rows(bt.rows,"symbol","change_pct",function(x){return(x.change_pct||0)>=0?"up":"dn";},8),"NSE bulk deals",bb.updated||d.updated)
  ]);

  var derivatives=grid([
    card("30","F&O OI CHANGE",rows(foi.rows,"symbol","oi_change_pct",function(x){return(x.oi_change_pct||0)>=0?"up":"dn";},9),"NSE futures",ds.futures_updated||d.updated),
    card("31","OI × PRICE MATRIX",row("Long build",n((fb.counts||{})["LONG BUILD"]),"up")+row("Short build",n((fb.counts||{})["SHORT BUILD"]),"dn")+row("Short cover",n((fb.counts||{})["SHORT COVER"]),"up")+row("Long unwind",n((fb.counts||{})["LONG UNWIND"]),"dn"),"NSE futures",ds.futures_updated||d.updated),
    card("32","PUT / CALL + MAX PAIN",row("PCR OI",n(op.nifty_pcr_oi))+row("PCR volume",n(op.nifty_pcr_vol))+row("Max pain",n(op.max_pain))+row("Expiry",op.expiry||"—")+row("Spot",n(op.spot)),"NSE options",ds.futures_updated||d.updated),
    card("33","FUTURES BASIS",rows(fm.rows,"symbol","basis_pct",function(x){return(x.basis_pct||0)>=0?"up":"dn";},9),"NSE futures",ds.futures_updated||d.updated),
    card("34","LONG / SHORT BUILDUP",'<div class="rr-cols"><div>'+rows(fb.long_build,"symbol","oi_change_pct",function(){return"up";},4)+rows(fb.short_cover,"symbol","oi_change_pct",function(){return"up";},4)+'</div><div>'+rows(fb.short_build,"symbol","oi_change_pct",function(){return"dn";},4)+rows(fb.long_unwind,"symbol","oi_change_pct",function(){return"dn";},4)+'</div></div>',"NSE futures",ds.futures_updated||d.updated),
    '<div class="card rr-card rr-wide"><div class="sh2 rr-head"><span>DERIVATIVES DATA NOTE</span><span class="rr-badges">'+sourceBadge("NSE EOD",ds.futures_updated||d.updated)+'</span></div>'+row("Coverage",n(foi.coverage))+row("Snapshot date",(STATE.futures||{}).date||"—")+row("Live socket","Not used")+row("Policy","EOD public data only")+'</div>'
  ]);

  var structure=grid([
    card("17","SECTOR STRENGTH MATRIX",rows(sm.sectors,"sector","avg_20d_pct",function(x){return(x.avg_20d_pct||0)>=0?"up":"dn";},10),"Derived",d.updated),
    card("39","MARKET CONCENTRATION",concBody(),"NSE weights when available",d.updated),
    card("40","NIFTY LEADERSHIP",leaderBody(),"NIFTY 50 + derived RS",d.updated),
    card("41","INDEX BUCKET BREADTH",rows(ib.buckets,"bucket","breadth_pct",function(x){return(x.breadth_pct||0)>=50?"up":"dn";},4),"NSE/public membership",d.updated),
    card("43","DATA COVERAGE",row("History files",n(rdd.history_files))+row("History ≥200D",pct0(rdd.history_ge_200d_pct))+row("EMA200",pct0(rdd.ema200_coverage_pct))+row("Delivery",n(rdd.delivery_coverage))+row("Futures",n(rdd.futures_stock_coverage)),"System coverage",rdd.health_updated||d.updated),
    card("44","DATA RESILIENCE DETAIL",row("Coverage score",pct0(rdd.coverage_score_pct))+row("Health snapshot",healthReady?"READY":"PENDING",healthReady?(healthProblems?"dn":"up"):"")+row("Membership source",source)+row("EOD fallback","NSE → Yahoo → last valid"),"System health",rdd.health_updated||d.updated)
  ]);

  var lab='<div class="rr-panel-content">'+renderResearchLab(d)+'</div>';

  host.innerHTML=hero+nav+
    '<section class="rr-panel on" data-rr-panel="overview">'+panelHead("Market overview","Start here for the daily research brief")+overview+'</section>'+
    '<section class="rr-panel" data-rr-panel="signals">'+panelHead("Signals & technical context","Derived from committed EOD/history snapshots")+signals+'</section>'+
    '<section class="rr-panel" data-rr-panel="events">'+panelHead("Events & corporate research","Exchange filings, results and deal context")+events+'</section>'+
    '<section class="rr-panel" data-rr-panel="derivatives">'+panelHead("Derivatives terminal","Futures, OI build-up, basis and index options")+derivatives+'</section>'+
    '<section class="rr-panel" data-rr-panel="structure">'+panelHead("Market structure","Sectors, index buckets and leadership")+structure+'</section>'+
    '<section class="rr-panel" data-rr-panel="lab">'+panelHead("Research Lab","Replay, stock drill-down, compare, notebook, backtests and data health")+lab+'</section>'+
    '';
  wireLab();
}

function optionalJSON(path,def){
  return fetch(path+"?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(path+" "+r.status);return r.json();}).catch(function(){return def;});
}
function loadSupport(){
  var csvP=fetch("data/brain-screener.csv?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("csv "+r.status);return r.text();}).catch(function(){return"";});
  return Promise.all([
    csvP,
    optionalJSON("data/delivery.json",{}),
    optionalJSON("data/futures.json",{}),
    optionalJSON("data/filings.json",{}),
    optionalJSON("data/results.json",{}),
    optionalJSON("data/research-alerts.json",{}),
    optionalJSON("data/data-health.json",{}),
    optionalJSON("data/research-market-history.json",{}),
    optionalJSON("data/research-signal-history.json",{}),
    optionalJSON("data/candles.json",{})
  ]).then(function(vals){
    parseCSV(vals[0]).forEach(function(x){var sym=String(x.symbol||"").trim().toUpperCase();if(sym){x.return_20d=numv(x.return_20d);STATE.stocks[sym]=x;}});
    var d=vals[1]||{};STATE.delivery=d.d||{};
    STATE.futures=vals[2]||{};
    STATE.filings=(vals[3]||{}).filings||[];
    var rr=vals[4]||{};STATE.results={};(rr.results||[]).forEach(function(x){if(x.sym)STATE.results[String(x.sym).toUpperCase()]=x;});
    STATE.alerts=vals[5]||{};STATE.health=vals[6]||{};STATE.marketHistory=vals[7]||{};STATE.signalHistory=vals[8]||{};STATE.candles=(vals[9]||{}).syms||{};STATE.candlesUpdated=(vals[9]||{}).updated||null;maybeNotifyAlerts(STATE.alerts);
  });
}
function boot(){
  var h=document.getElementById("research-radar");if(!h)return;
  h.dataset.rrProfessional="1";
  installCSS();
  h.innerHTML='<div class="card" style="margin-top:10px;padding:18px">Loading Research Lab + 44 Research Radar modules…</div>';
  optionalJSON("data/research-radar.json",null).then(function(d){if(!d)throw Error("research-radar.json unavailable");STATE.radar=d;return loadSupport().then(function(){render(d);});}).catch(function(e){
    h.innerHTML='<div class="card" style="margin-top:10px;padding:18px"><b>Research Radar data could not load.</b><div class="mut" style="padding-left:0">Check Pages deployment / published data files. '+esc(e.message)+'</div></div>';
  });
}
document.addEventListener("click",function(e){
  var el=e.target.closest?e.target.closest("[data-symbol]"):null;
  if(el&&!el.hasAttribute("data-close-rr")){
    var sym=el.getAttribute("data-symbol");if(sym){e.preventDefault();openDetail(sym);}
  }
  var tw=e.target.closest?e.target.closest("[data-toggle-watch]"):null;
  if(tw){var sw=tw.getAttribute("data-toggle-watch");toggleWatch(sw);openDetail(sw);return;}
  var sn=e.target.closest?e.target.closest("[data-save-modal-note]"):null;
  if(sn){var snsym=sn.getAttribute("data-save-modal-note"),ta=document.getElementById("rr-modal-note");saveNote(snsym,ta?ta.value:"");alert("Saved in this browser.");return;}
  if(e.target.closest&&e.target.closest("[data-close-rr]")){
    var ov=document.getElementById("rr-overlay");if(ov)ov.classList.remove("open");
  }
});
document.addEventListener("keydown",function(e){if(e.key==="Escape"){var ov=document.getElementById("rr-overlay");if(ov)ov.classList.remove("open");}});
window.addEventListener("hashchange",function(){setTimeout(boot,100);});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",function(){boot();});else boot();

var ov=document.createElement("div");ov.id="rr-overlay";ov.className="rr-overlay";document.body.appendChild(ov);
})();
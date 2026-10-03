(function(){
"use strict";

var STATE={radar:null,stocks:{},delivery:{},futures:{},filings:[],results:{},historyCache:{}};

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
  if(document.getElementById("rr44-style"))return;
  var s=document.createElement("style");s.id="rr44-style";
  s.textContent=[
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
    "@media(max-width:720px){.rr-grid{grid-template-columns:1fr}.rr-wide{grid-column:auto}.rr-cols{grid-template-columns:1fr}.rr-head{align-items:flex-start;flex-direction:column}.rr-badges{justify-content:flex-start}.rr-metric-grid{grid-template-columns:1fr 1fr}}"
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
    fetch(histUrl,{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("history "+r.status);return r.json();}).catch(function(){return[];})
  ]).then(function(vals){
    var hist=vals[0]||[];
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
      row("20D return",p(r.return_20d))+row("60D return",p(r.return_60d))+row("Relative strength vs NIFTY",p(r.relative_strength_20d))+row("MACD histogram",n(r.macd_hist))+row("20D volume ratio",n(r.vol_vs_avg20))+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">F&O</div>'+
      row("Expiry",fo?fo.expiry:"Not available")+row("OI",fo?n(fo.oi):"—")+row("OI change",fo?n(fo.oi_chg):"—")+row("Basis",fo?p(fo.basis_pct):"—")+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">CORPORATE / RESULTS</div>'+eventBody(filings)+
      (next?'<div class="ni"><b>Next result / event: '+esc(next.date||"—")+'</b><small>'+esc(next.company||"")+'</small></div>':"")+'</div>';
    body+='<div class="rr-detail-section"><div class="sh2">DATA SOURCE</div>'+row("Screener","ArthaSaar brain-screener snapshot")+row("Historical","ArthaSaar history file")+row("Corporate","NSE/public filings snapshot")+row("Research timestamp",safeDate((STATE.radar||{}).updated))+'</div>';
    host.innerHTML='<div class="rr-modal"><div class="rr-modal-head"><div class="rr-modal-title"><b>'+esc(symbol)+' · '+esc(r.company||"")+'</b><small>'+esc(r.industry||"")+'</small></div><button class="rr-btn" data-close-rr>✕ CLOSE</button></div><div class="rr-modal-body">'+body+'</div></div>';
  });
}

function renderResearchLab(d){
  var lab=d.research_lab||{},bt=(lab.backtests||{}).signals||{},daily=lab.daily_history||[];
  var signals=Object.keys(bt);
  var back='<div style="overflow:auto"><table class="rr-lab-table"><thead><tr><th>Signal</th><th>Events</th><th>Next 5D avg</th><th>5D positive</th><th>Next 20D avg</th><th>20D positive</th></tr></thead><tbody>'+
    (signals.map(function(k){var x=bt[k]||{};return'<tr><td><b>'+esc(k.replace(/_/g," ").toUpperCase())+'</b></td><td class="numr">'+n(x.observations)+'</td><td class="numr">'+p(x.next5_mean_pct)+'</td><td class="numr">'+pct0(x.next5_positive_pct)+'</td><td class="numr">'+p(x.next20_mean_pct)+'</td><td class="numr">'+pct0(x.next20_positive_pct)+'</td></tr>';}).join("")||'<tr><td colspan="6">No backtest observations yet.</td></tr>')+
    '</tbody></table></div><div class="rr-kicker">'+esc((lab.backtests||{}).method||"")+' · scanned '+n((lab.backtests||{}).history_files_scanned)+' history files.</div>';
  var hist='<div class="rr-history"><table class="rr-lab-table"><thead><tr><th>Date</th><th>Advancers</th><th>Decliners</th><th>Advance ratio</th><th>High zone</th><th>Low zone</th></tr></thead><tbody>'+
    daily.slice(-20).reverse().map(function(x){return'<tr><td>'+esc(x.date)+'</td><td class="numr">'+n(x.advancers)+'</td><td class="numr">'+n(x.decliners)+'</td><td class="numr">'+pct0(x.advance_ratio_pct)+'</td><td class="numr">'+n(x.new_high_zone_count)+'</td><td class="numr">'+n(x.new_low_zone_count)+'</td></tr>';}).join("")+
    '</tbody></table></div>';
  return '<div class="rr-lab-grid">'+
    '<div class="card rr-card"><div class="sh2">RESEARCH LAB · STOCK DRILL-DOWN</div><div style="padding:10px 12px"><div class="rr-search"><input id="rr-stock-search" type="search" placeholder="Search symbol or company…"><button class="rr-btn" id="rr-clear-search">CLEAR</button></div><div id="rr-search-results"></div><div class="rr-chiprow"><button class="rr-chip" data-symbol="RELIANCE">RELIANCE</button><button class="rr-chip" data-symbol="HDFCBANK">HDFCBANK</button><button class="rr-chip" data-symbol="ICICIBANK">ICICIBANK</button><button class="rr-chip" data-symbol="TCS">TCS</button><button class="rr-chip" data-symbol="INFY">INFY</button></div><div class="rr-kicker">Click any symbol anywhere in Research Radar to open a full stock research profile.</div></div></div>'+
    '<div class="card rr-card"><div class="sh2">RESEARCH LAB · COVERAGE</div>'+row("Universe searchable",n(lab.search_universe))+row("Radar modules",n(lab.module_count))+row("Source policy","Free/public only")+row("Updated",safeDate((d||{}).updated))+'</div>'+
    '<div class="card rr-card rr-wide"><div class="sh2">SIGNAL HISTORY / BACKTEST</div>'+back+'</div>'+
    '<div class="card rr-card rr-wide"><div class="sh2">BREADTH HISTORY</div>'+hist+'</div>'+
    '</div>';
}

function wireLab(){
  var input=document.getElementById("rr-stock-search"),res=document.getElementById("rr-search-results");
  function paint(q){
    if(!res)return;
    var arr=stockUniverseSearch(q);
    if(!q){res.innerHTML="";return;}
    res.innerHTML='<div class="rr-results">'+(arr.length?arr.map(function(x){return'<button class="rr-result" data-symbol="'+esc(String(x.symbol).toUpperCase())+'"><b>'+esc(x.symbol)+'</b><small>'+esc(x.company||"")+'</small></button>';}).join(""):'<div class="mut">No matching stock.</div>')+'</div>';
  }
  if(input)input.addEventListener("input",function(){paint(input.value);});
  var clear=document.getElementById("rr-clear-search");
  if(clear)clear.addEventListener("click",function(){if(input)input.value="";paint("");if(input)input.focus();});
  document.querySelectorAll("[data-symbol]").forEach(function(el){
    el.addEventListener("click",function(e){e.preventDefault();openDetail(el.getAttribute("data-symbol"));});
  });
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

  var html=renderResearchLab(d)+'<div class="rr-grid">';
  html+=card("01","CORPORATE ACTIONS",eventBody(ca.events),"NSE filings",d.updated);
  html+=card("02","52-WEEK MAP",row("Near high zone",n(w.new_high_zone_count),"up")+row("Near low zone",n(w.new_low_zone_count),"dn")+rows(w.near_highs,"symbol","from_high_pct",function(){return"up";},4)+rows(w.near_lows,"symbol","from_low_pct",function(){return"dn";},4),"ArthaSaar screener",d.updated);
  html+=card("03","BREADTH HISTORY",row("Advancers",n((br.today||{}).advancers))+row("Decliners",n((br.today||{}).decliners))+row("Advance ratio",p((br.today||{}).advance_ratio_pct))+row("200D EMA",pct0((br.today||{}).ema200_pct)),"Derived universe",d.updated);
  html+=card("04","INDEX / CONSTITUENT CHANGES",Object.keys(ix.membership_changes||{}).map(function(k){var z=ix.membership_changes[k]||{};return row(k,(z.added||[]).length+" in · "+(z.removed||[]).length+" out");}).join("")+row("Indices tracked",n(ix.indices_count)),"NSE",d.updated);
  html+=card("05","RBI / MACRO PULSE",itemList(ma.indicators,function(x){return'<div class="ni"><b>'+esc(x.name||"Macro")+'</b><small>'+esc(x.value||"—")+' · '+esc(x.date||"")+'</small></div>';},6),"RBI/public macro",ma.macro_updated||d.updated);
  html+=card("06","BULK / BLOCK DEALS",'<div class="rr-cols"><div>'+rows(bb.bulk,"s","t",null,5)+'</div><div>'+rows(bb.block,"s","t",null,5)+'</div></div>',"NSE-derived",bb.updated||d.updated);
  html+=card("07","RESULTS CALENDAR",rows(re.items,"sym","date",null,8),re.quarter||"Public results",re.updated||d.updated);
  html+=card("08","SECTOR ROTATION",rows(se.sectors,"sector","avg_1d_pct",function(x){return(x.avg_1d_pct||0)>=0?"up":"dn";},8),"Derived sectors",d.updated);
  html+=card("09","MARKET REGIME",row("Regime",rg.label||"—")+row("Composite",n(rg.score)+"/4")+row("Breadth",p(rg.advance_ratio_pct))+row("NIFTY 50",p(rg.nifty_change_pct),(rg.nifty_change_pct||0)>=0?"up":"dn"),"Derived, not forecast",d.updated);
  var hs=dr.summary||{};html+=card("10","DATA RESILIENCE",row("Feeds OK",n(hs.ok)+"/"+n(hs.total))+row("Problems",n(hs.problems),hs.problems?"dn":"up")+row("Fallback","NSE → Yahoo → last valid"),"Data health",dr.health_updated||d.updated);

  html+=card("11","52W BREAKOUT RADAR",row("Candidates",n(h.count))+rows(h.rows,"symbol","distance_252_high_pct",function(){return"up";},7),"Derived 252D",d.updated);
  html+=card("12","VOLUME SHOCK RADAR",rows(vs.rows,"symbol","vol_vs_avg20",function(){return"up";},8),"NSE/Yahoo history",d.updated);
  html+=card("13","DELIVERY CONVICTION",row("Coverage",n(dc.coverage))+row("Avg delivery",pct0(dc.avg_delivery_pct))+rows(dc.high_delivery_up,"symbol","delivery_pct",function(){return"up";},4),"NSE delivery",d.updated);
  html+=card("14","PRICE × VOLUME ACCUMULATION",'<div class="rr-cols"><div><div class="rr-sub">Accumulation</div>'+rows(ad.accumulation,"symbol","volume_ratio",function(){return"up";},5)+'</div><div><div class="rr-sub">Distribution</div>'+rows(ad.distribution,"symbol","volume_ratio",function(){return"dn";},5)+'</div></div>',"Derived",d.updated);
  html+=card("15","GAP-UP / GAP-DOWN RADAR",row("Status",gap.available?"LIVE":"WAITING")+'<div class="rr-kicker">'+esc(gap.reason||"")+'</div>',"OHLC dependent",d.updated);
  html+=card("16","RELATIVE STRENGTH vs NIFTY",row("NIFTY 20D",p(rs.benchmark_return_20d_pct))+rows(rs.leaders,"symbol","relative_strength_20d",function(){return"up";},6)+rows(rs.laggards,"symbol","relative_strength_20d",function(){return"dn";},6),"Derived",d.updated);
  html+=card("17","SECTOR STRENGTH MATRIX",rows(sm.sectors,"sector","avg_20d_pct",function(x){return(x.avg_20d_pct||0)>=0?"up":"dn";},10),"Derived",d.updated);
  html+=card("18","VOLATILITY EXPANSION",rows(ve.rows,"symbol","vol_expansion",function(x){return(x.vol_expansion||0)>=1?"up":"";},8),"ArthaSaar history",d.updated);
  html+=card("19","ATR / RANGE EXPANSION",row("Status",rx.available?"LIVE":"Proxy only")+row("Proxy","Close-to-close volatility")+'<div class="rr-kicker">'+esc(rx.reason||"")+'</div>',"OHLC dependent",d.updated);
  html+=card("20","MOMENTUM DASHBOARD",row("RSI >60",n((mo.rsi_high||[]).length),"up")+row("RSI <40",n((mo.rsi_low||[]).length),"dn")+row("MACD positive",n((mo.macd_positive||[]).length),"up")+rows(mo.roc_leaders,"symbol","return_20d",function(){return"up";},5),"RSI/MACD/ROC",d.updated);
  html+=card("21","TREND HEALTH",row("Above EMA200",pct0(th.above_ema200_pct))+rows(th.above_ema200,"symbol","return_20d",function(){return"up";},5)+rows(th.below_ema200,"symbol","return_20d",function(){return"dn";},5),"Derived trend",d.updated);
  html+=card("22","GOLDEN / DEATH CROSS",row("Golden",n(cross.golden_cross_count),"up")+row("Death",n(cross.death_cross_count),"dn")+rows(cross.golden_candidates,"symbol","return_20d",function(){return"up";},4)+rows(cross.death_candidates,"symbol","return_20d",function(){return"dn";},4),"50D / 200D",d.updated);
  html+=card("23","52W HIGH / LOW DISTANCE",rows(dm.near_high_200d,"symbol","distance_252_high_pct",function(){return"up";},5)+rows(dm.near_low_200d,"symbol","distance_252_low_pct",function(){return"dn";},5),"252D history",d.updated);
  html+=card("24","EARNINGS SURPRISE TRACKER",row("Standardized surprise","Unavailable")+row("Upcoming results",n((es.upcoming_results||[]).length))+eventBody(es.results_filing_events),"Public coverage",d.updated);
  html+=card("25","PROMOTER / INSIDER ACTIVITY",row("Events",n(pi.count))+eventBody(pi.events),"NSE/public filings",d.updated);
  html+=card("26","PLEDGE / ENCUMBRANCE WATCH",row("Events",n(pl.count))+eventBody(pl.events),"NSE/public filings",d.updated);
  html+=card("27","CORPORATE ACTION CALENDAR",rows(cc.next_results,"sym","date",null,10),"Results/filings",re.updated||d.updated);
  html+=card("28","DIVIDEND RADAR",row("Events",n(dv.count))+eventBody(dv.events),"NSE/public filings",d.updated);
  html+=card("29","BUYBACK / OPEN OFFER",row("Events",n(bo.count))+eventBody(bo.events),"NSE/public filings",d.updated);
  html+=card("30","F&O OI CHANGE RADAR",rows(foi.rows,"symbol","oi_change_pct",function(x){return(x.oi_change_pct||0)>=0?"up":"dn";},10),"NSE futures",f.futures_updated||d.updated);
  html+=card("31","OI × PRICE MATRIX",row("Long build",n((fb.counts||{})["LONG BUILD"]),"up")+row("Short build",n((fb.counts||{})["SHORT BUILD"]),"dn")+row("Short cover",n((fb.counts||{})["SHORT COVER"]),"up")+row("Long unwind",n((fb.counts||{})["LONG UNWIND"]),"dn"),"NSE futures",f.futures_updated||d.updated);
  html+=card("32","PUT / CALL + MAX PAIN",row("PCR OI",n(op.nifty_pcr_oi))+row("PCR volume",n(op.nifty_pcr_vol))+row("Max pain",n(op.max_pain))+row("Expiry",op.expiry||"—")+row("Spot",n(op.spot)),"NSE options",f.futures_updated||d.updated);
  html+=card("33","FUTURES BASIS / SPREAD",rows(fm.rows,"symbol","basis_pct",function(x){return(x.basis_pct||0)>=0?"up":"dn";},10),"NSE futures",f.futures_updated||d.updated);
  html+=card("34","LONG / SHORT BUILDUP RADAR",'<div class="rr-cols"><div>'+rows(fb.long_build,"symbol","oi_change_pct",function(){return"up";},5)+rows(fb.short_cover,"symbol","oi_change_pct",function(){return"up";},5)+'</div><div>'+rows(fb.short_build,"symbol","oi_change_pct",function(){return"dn";},5)+rows(fb.long_unwind,"symbol","oi_change_pct",function(){return"dn";},5)+'</div></div>',"NSE futures",f.futures_updated||d.updated);
  html+=card("35","BULK DEAL FOLLOW-THROUGH",rows(bt.rows,"symbol","change_pct",function(x){return(x.change_pct||0)>=0?"up":"dn";},10),"NSE bulk deals",bb.updated||d.updated);
  html+=card("36","INSTITUTIONAL FLOW TREND",row("FII current",n((iflow.current||{}).net_cr))+row("DII current",n((iflow.dii_current||{}).net_cr))+row("FII sell days",n(iflow.fii_sell_days),(iflow.fii_sell_days||0)>0?"dn":"up")+rows(iflow.history,"date","fii_net_cr",function(x){return(x.fii_net_cr||0)>=0?"up":"dn";},6),"FII/DII + macro history",d.updated);
  html+=card("37","MARKET BREADTH MOMENTUM",row("3D up streak",n(bm.three_day_up),"up")+row("3D down streak",n(bm.three_day_down),"dn")+row("Volume >2×",n(bm.volume_spike_2x)),"Universe",d.updated);
  html+=card("38","NEW HIGH / NEW LOW BREADTH",row("New-high zone",n(hlb.new_high_zone),"up")+row("New-low zone",n(hlb.new_low_zone),"dn")+rows(hlb.near_highs,"symbol","change_pct",function(){return"up";},4)+rows(hlb.near_lows,"symbol","change_pct",function(){return"dn";},4),"Universe",d.updated);
  html+=card("39","MARKET CONCENTRATION",itemList(mc.indices,function(x){return row(x.index,"Top10 "+n(x.top10_weight_pct)+"%");},4),"NSE constituent weights",d.updated);
  html+=card("40","NIFTY LEADERSHIP RADAR",rows(nl.leaders,"symbol","relative_strength_20d",function(){return"up";},12),"NIFTY 50 + derived RS",d.updated);
  html+=card("41","SMALL / MID / LARGE BUCKET BREADTH",rows(ib.buckets,"bucket","breadth_pct",function(x){return(x.breadth_pct||0)>=50?"up":"dn";},4),"NSE membership",d.updated);
  html+=card("42","LIQUIDITY STRESS RADAR",row("Low volume <0.5×",n(ls.low_volume_lt_0_5x),"dn")+row("High volume >2×",n(ls.high_volume_gt_2x),"up")+row("History <60D",n(ls.illiquid_history_lt_60d),"dn")+row("Universe",n(ls.coverage)),"ArthaSaar coverage",d.updated);
  html+=card("43","DATA RELIABILITY SCORE",row("Coverage score",pct0(rel.coverage_score_pct))+row("History ≥200D",pct0(rel.history_ge_200d_pct))+row("Delivery rows",n(rel.delivery_coverage))+row("F&O rows",n(rel.futures_stock_coverage)),"Repo data-health",d.updated);
  html+=card("44","DATA RESILIENCE DETAIL",row("History files",n(rdd.history_files))+row("EMA200 coverage",pct0(rdd.ema200_coverage_pct))+row("Delivery coverage",n(rdd.delivery_coverage))+row("Futures coverage",n(rdd.futures_stock_coverage))+row("Coverage score",pct0(rdd.coverage_score_pct))+row("EOD fallback","NSE → Yahoo → last valid"),"System health",rdd.health_updated||d.updated);
  html+='</div><div class="rr-note"><b>Research Lab + 44 free-data modules.</b> Search any stock, open its drill-down, inspect signal history, and review event-study results. Freshness badges are derived from the published snapshot timestamps. No paid API is used.</div>';
  host.innerHTML=html;
  wireLab();
}

function optionalJSON(path,def){
  return fetch(path+"?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(path+" "+r.status);return r.json();}).catch(function(){return def;});
}
function loadSupport(){
  var csvP=fetch("data/brain-screener.csv?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("csv "+r.status);return r.text();}).catch(function(){return"";});
  return Promise.all([
    csvP,optionalJSON("data/delivery.json",{}),optionalJSON("data/futures.json",{}),optionalJSON("data/filings.json",{}),optionalJSON("data/results.json",{})
  ]).then(function(vals){
    parseCSV(vals[0]).forEach(function(x){var sym=String(x.symbol||"").trim().toUpperCase();if(sym)STATE.stocks[sym]=x;});
    var d=vals[1]||{};STATE.delivery=d.d||{};
    STATE.futures=vals[2]||{};
    STATE.filings=(vals[3]||{}).filings||[];
    var rr=vals[4]||{};STATE.results={};(rr.results||[]).forEach(function(x){if(x.sym)STATE.results[String(x.sym).toUpperCase()]=x;});
  });
}
function boot(){
  var h=document.getElementById("research-radar");if(!h)return;
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
  if(e.target.closest&&e.target.closest("[data-close-rr]")){
    var ov=document.getElementById("rr-overlay");if(ov)ov.classList.remove("open");
  }
});
document.addEventListener("keydown",function(e){if(e.key==="Escape"){var ov=document.getElementById("rr-overlay");if(ov)ov.classList.remove("open");}});
window.addEventListener("hashchange",function(){setTimeout(boot,100);});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",function(){boot();});else boot();

var ov=document.createElement("div");ov.id="rr-overlay";ov.className="rr-overlay";document.body.appendChild(ov);
})();
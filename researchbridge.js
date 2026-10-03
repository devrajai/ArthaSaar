(function(){
"use strict";

var DATA={radar:null,stocks:{},delivery:{},futures:{},filings:[],results:{},mfTop:null,ci:{}};

function base(){return location.pathname.indexOf("/app/")>=0?"../data/":"data/";}
function J(file){
  return fetch(base()+file+"?v="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function num(x){var n=parseFloat(String(x==null?"":x).replace(/,/g,"").replace("%",""));return isNaN(n)?null:n;}
function pct(x){var n=num(x);return n==null?"—":(n>=0?"+":"")+n.toFixed(2)+"%";}
function nf(x){var n=num(x);return n==null?"—":n.toLocaleString("en-IN",{maximumFractionDigits:2});}
function safeDate(x){return x?String(x).replace("T"," ").replace("Z",""):"—";}

function parseCSV(text){
  if(!text)return [];
  var rows=[],line="",q=false,cur=[],cols=[];
  for(var i=0;i<text.length;i++){
    var ch=text[i];
    if(ch==='"'){ if(q && text[i+1]==='"'){line+='"';i++;}else q=!q; }
    else if(ch===','&&!q){cur.push(line);line="";}
    else if((ch==='\n'||ch==='\r')&&!q){
      if(ch==='\r'&&text[i+1]==='\n')i++;
      cur.push(line);line="";
      if(!cols.length){cols=cur;cur=[];}
      else if(cur.length===cols.length){var o={};cols.forEach(function(k,j){o[k]=cur[j];});rows.push(o);cur=[];}
    } else line+=ch;
  }
  if(line.length||cur.length){cur.push(line);if(!cols.length)cols=cur;else if(cur.length===cols.length){var o2={};cols.forEach(function(k,j){o2[k]=cur[j];});rows.push(o2);}}
  return rows;
}

function load(){
  return Promise.all([
    J("research-radar.json"),
    J("delivery.json"),
    J("futures.json"),
    J("filings.json"),
    J("results.json"),
    J("mf-top.json"),
    J("company-index.json"),
    fetch(base()+"brain-screener.csv?v="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.text():"";}).catch(function(){return "";})
  ]).then(function(v){
    DATA.radar=v[0]||{};
    DATA.delivery=(v[1]||{}).d||{};
    DATA.futures=v[2]||{};
    DATA.filings=(v[3]||{}).filings||[];
    DATA.results=(v[4]||{}).results||[];
    DATA.mfTop=v[5]||{};
    DATA.ci=v[6]||{};
    parseCSV(v[7]).forEach(function(x){var s=String(x.symbol||"").trim().toUpperCase();if(s)DATA.stocks[s]=x;});
    return DATA;
  });
}

function featureHits(sym){
  sym=String(sym||"").toUpperCase();
  var f=DATA.radar.features||{}, out=[];
  function add(title,text,cls){if(text!==null&&text!==undefined&&text!=="")out.push({title:title,text:String(text),cls:cls||""});}
  function find(list,key){
    return (list||[]).find(function(x){return String(x.symbol||x.sym||"").toUpperCase()===sym;});
  }
  var h=find((f.breakout_radar||{}).rows); if(h)add("52W breakout zone","Within 0.75% of 252-session high · "+pct(h.distance_252_high_pct),"up");
  var vs=find((f.volume_shock||{}).rows); if(vs)add("Volume shock","Volume "+nf(vs.vol_vs_avg20)+"× 20D average","up");
  var dc=find((f.delivery_conviction||{}).high_delivery_up)||find((f.delivery_conviction||{}).high_delivery_down);
  if(dc)add("Delivery context","Delivery "+nf(dc.delivery_pct)+"%","up");
  var rs=find((f.relative_strength||{}).leaders)||find((f.relative_strength||{}).laggards);
  if(rs)add("Relative strength vs NIFTY","20D relative strength "+pct(rs.relative_strength_20d),num(rs.relative_strength_20d)>=0?"up":"dn");
  var em=find((f.trend_health||{}).above_ema200)||find((f.trend_health||{}).below_ema200);
  if(em)add("Trend health",String(em.above_ema200)==="true"?"Above EMA200":"Below EMA200",String(em.above_ema200)==="true"?"up":"dn");
  var fob=find((f.fo_buildup||{}).long_build)||find((f.fo_buildup||{}).short_build)||find((f.fo_buildup||{}).short_cover)||find((f.fo_buildup||{}).long_unwind);
  if(fob)add("F&O structure",String(fob.build||"—")+" · OI change "+nf(fob.oi_change_pct)+"%");
  var filing=(f.corporate_actions||{}).events||[];
  filing=filing.filter(function(x){return String(x.symbol||"").toUpperCase()===sym;})[0];
  if(filing)add("Corporate event",String(filing.kind||filing.category||"Filing")+" · "+String(filing.date||""));
  var result=(f.results||{}).items||[];
  result=result.filter(function(x){return String(x.sym||"").toUpperCase()===sym;})[0];
  if(result)add("Upcoming result",String(result.date||"")+ (result.conf===false?" · unconfirmed":""));
  return out.slice(0,7);
}

function stockResearchMarkup(sym){
  var r=DATA.stocks[sym]||{}, hits=featureHits(sym);
  var f=DATA.radar.features||{}, rg=f.market_regime||{}, dc=f.delivery_conviction||{}, fo=f.fo_buildup||{};
  var events=(DATA.filings||[]).filter(function(x){return String(x.symbol||"").toUpperCase()===sym;}).slice(0,4);
  var result=(DATA.results||[]).filter(function(x){return String(x.sym||"").toUpperCase()===sym;})[0];
  var del=DATA.delivery[sym];
  var fx=((DATA.futures||{}).stocks||[]).find(function(x){return String(x.symbol||"").toUpperCase()===sym;});
  var freshness=DATA.radar.updated||null;

  var h='<div class="asresearch-panel"><div class="asresearch-head"><div><span class="asresearch-eyebrow">RESEARCH RADAR</span><b>Market context · '+esc(sym)+'</b><small>Same committed snapshot used by Research Radar</small></div><span class="asresearch-badge">EOD RESEARCH</span></div>';
  h+='<div class="asresearch-grid">';
  h+='<div><span>Regime</span><b>'+esc(rg.label||"—")+'</b></div><div><span>NIFTY 50</span><b>'+pct(rg.nifty_change_pct)+'</b></div>';
  h+='<div><span>20D return</span><b>'+pct(r.return_20d)+'</b></div><div><span>RSI14</span><b>'+nf(r.rsi14)+'</b></div>';
  h+='<div><span>EMA200</span><b>'+nf(r.ema200)+'</b></div><div><span>Delivery</span><b>'+nf(del)+'%</b></div>';
  h+='<div><span>20D volume</span><b>'+nf(r.vol_vs_avg20)+'×</b></div><div><span>F&O build</span><b>'+esc(fx?fx.build:"—")+'</b></div>';
  h+='</div>';
  h+='<div class="asresearch-sub">WHY THIS STOCK IS IN RESEARCH CONTEXT</div>';
  h+=hits.length?'<div class="asresearch-hits">'+hits.map(function(x){return'<div class="asresearch-hit"><b class="'+esc(x.cls||"")+'">'+esc(x.title)+'</b><small>'+esc(x.text)+'</small></div>';}).join("")+'</div>':'<div class="asresearch-empty">No dedicated trigger in the current Research Radar snapshot.</div>';
  if(events.length||result){
    h+='<div class="asresearch-sub">EVENT / FILING CONTEXT</div><div class="asresearch-events">';
    events.forEach(function(x){h+='<div><b>'+esc(x.kind||x.category||"Filing")+'</b><small>'+esc(x.date||"")+' · '+esc(x.subject||"")+'</small></div>';});
    if(result)h+='<div><b>Next result</b><small>'+esc(result.date||"—")+' · '+esc(result.company||sym)+'</small></div>';
    h+='</div>';
  }
  h+='<div class="asresearch-foot">Source: NSE/public snapshots + ArthaSaar calculations · updated '+esc(safeDate(freshness))+'</div></div>';
  return h;
}

function injectCompany(sym){
  var box=document.querySelector(".cofs .cobody"); if(!box||box.querySelector(".asresearch-panel"))return;
  var markup=stockResearchMarkup(String(sym||"").toUpperCase());
  var wrap=document.createElement("div");wrap.innerHTML=markup;wrap=wrap.firstChild;
  var deep=box.querySelector(".codeep"), note=box.querySelector(".conote");
  if(note)box.insertBefore(wrap,note); else if(deep)box.insertBefore(wrap,deep); else box.appendChild(wrap);
}

function wrapCompany(){
  if(typeof window.openCompanyFS!=="function"||window.openCompanyFS._asResearch)return;
  var orig=window.openCompanyFS;
  function wrapped(sym){orig(sym);setTimeout(function(){injectCompany(sym);},80);}
  wrapped._asResearch=true;wrapped._orig=orig;window.openCompanyFS=wrapped;
}

function fundContextMarkup(){
  var top=DATA.mfTop||{}, f=(top.nifty||{});
  var radar=DATA.radar.features||{}, rg=radar.market_regime||{}, se=radar.sector_rotation||{};
  var rows=(se.sectors||[]).slice(0,4);
  var h='<div class="asresearch-panel asresearch-mf"><div class="asresearch-head"><div><span class="asresearch-eyebrow">RESEARCH RADAR</span><b>Fund / market context</b><small>Free-data linkage; holdings are not assumed when not published in the current local dataset.</small></div><span class="asresearch-badge">MARKET CONTEXT</span></div>';
  h+='<div class="asresearch-grid"><div><span>Market regime</span><b>'+esc(rg.label||"—")+'</b></div><div><span>NIFTY 1Y</span><b>'+pct(f.r1)+'</b></div><div><span>NIFTY 3Y</span><b>'+pct(f.r3)+'</b></div><div><span>NIFTY 5Y</span><b>'+pct(f.r5)+'</b></div></div>';
  h+='<div class="asresearch-sub">SECTOR RESEARCH CONTEXT</div>';
  h+=rows.length?'<div class="asresearch-hits">'+rows.map(function(x){return'<div class="asresearch-hit"><b>'+esc(x.sector||"Sector")+'</b><small>1D '+pct(x.avg_1d_pct)+' · 20D '+pct(x.avg_20d_pct)+' · breadth '+nf(x.breadth_pct)+'%</small></div>';}).join("")+'</div>':'<div class="asresearch-empty">Sector research data is not available in this published snapshot.</div>';
  h+='<div class="asresearch-foot">Fund NAV/return source remains the existing AMFI pipeline. Direct portfolio look-through is a separate monthly-data feature.</div></div>';
  return h;
}

function injectFund(){
  var body=document.querySelector(".fofs .fobody"); if(!body||body.querySelector(".asresearch-panel"))return;
  var wrap=document.createElement("div");wrap.innerHTML=fundContextMarkup();wrap=wrap.firstChild;
  var note=body.querySelector(".fonote"); if(note)body.insertBefore(wrap,note); else body.appendChild(wrap);
}

function wrapFund(){
  if(typeof window.openFundFS!=="function"||window.openFundFS._asResearch)return;
  var orig=window.openFundFS;
  function wrapped(code){orig(code);setTimeout(injectFund,80);}
  wrapped._asResearch=true;wrapped._orig=orig;window.openFundFS=wrapped;
}

function enrichEvents(){
  var host=document.querySelector("#v-events");
  if(!host)return;
  host.querySelectorAll("[data-research-symbol]").forEach(function(){});
}

function boot(){
  load().then(function(){
    wrapCompany();wrapFund();
    var n=0,iv=setInterval(function(){
      wrapCompany();wrapFund();
      if(++n>40)clearInterval(iv);
    },400);
  });
  // Run after the existing company/index/sector/fundamental modules have wired their own
  // click handlers. Their existing click targets funnel into openCompanyFS/openFundFS.
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
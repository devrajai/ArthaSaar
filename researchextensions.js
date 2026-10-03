/* ArthaSaar Research Edge Pack UI */
(function(){
  "use strict";
  var BASE=(location.pathname.indexOf("/app/")>=0?"../data/":"data/");
  function J(n){return fetch(BASE+n+"?edge="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(n);return r.json();});}
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function n(x,d){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?1:d});}
  function pct(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
  function cls(x){return Number(x)>0?"up":Number(x)<0?"dn":"";}
  function tip(metric){
    var m=String(metric||"");
    var text=m==="TRIN"?"TRIN/Arms = selling pressure relative to advancing/declining volume. <1 often means more breadth support; >1 means heavier downside pressure.":"";
    if(m==="McClellan")text="McClellan Oscillator tracks short-term breadth momentum. Positive = breadth improving; negative = breadth weakening.";
    if(m==="Delivery")text="Delivery % tells how much traded quantity was delivered rather than squared off intraday. High delivery needs price/volume context.";
    if(!text)text="This metric is a descriptive market statistic from the current EOD data snapshot.";
    return text;
  }
  function card(title,tag,body){
    return '<div class="rl2-card wide"><div class="rl2-head"><b>'+esc(title)+'</b><span>'+esc(tag)+'</span></div>'+body+'</div>';
  }
  function mount(d){
    var host=document.getElementById("research-lab-v2");
    if(!host||document.getElementById("research-edge-pack"))return;
    var wrap=document.createElement("div");wrap.id="research-edge-pack";
    var today=d.days_like_today||{}, cur=today.today||{}, matches=today.matches||[];
    var days='<div class="rl2-kpis">';
    [["BREADTH",cur.breadth!=null?(cur.breadth*100).toFixed(1)+"%":"—"],["TRIN",n(cur.trin,3)],["McClellan",n(cur.mcos,1)],["FII",cur.fii==null?"—":n(cur.fii,0)+" Cr"]].forEach(function(x){days+='<div><small>'+x[0]+'</small><b>'+esc(x[1])+'</b></div>';});
    days+='</div><div class="rl2-table"><div class="rl2-tr rl2-th"><span>Past day</span><span>Similarity</span><span>NIFTY +5D</span><span>NIFTY +20D</span><span>VIX/FII</span></div>';
    matches.forEach(function(x){days+='<div class="rl2-tr"><span>'+esc(x.date)+'</span><span>'+n(x.similarity,1)+'</span><span class="'+cls(x.next5_pct)+'">'+pct(x.next5_pct)+'</span><span class="'+cls(x.next20_pct)+'">'+pct(x.next20_pct)+'</span><span>'+esc(x.vix==null?"—":n(x.vix,2))+' / '+esc(x.fii==null?"—":n(x.fii,0))+'</span></div>';});
    days+='</div><div class="rl2-note">Nearest historical EOD contexts. Lower similarity score = closer. Forward returns are shown only where the archived NIFTY series has the required future closes. This is context, not a forecast.</div>';
    days+='<div class="rl2-status" style="padding:0 9px 9px"><button class="rl2-tip" data-metric="TRIN">TRIN explain</button><button class="rl2-tip" data-metric="McClellan">McClellan explain</button></div>';

    var sm=(d.smart_money||{}).rows||[];
    var smart='<div class="rl2-table"><div class="rl2-tr rl2-th"><span>Stock</span><span>Tag</span><span>Delivery</span><span>Vol / 20D</span><span>Evidence</span></div>';
    sm.slice(0,20).forEach(function(x){smart+='<div class="rl2-tr"><span><b>'+esc(x.symbol)+'</b></span><span>'+esc(x.tag)+'</span><span>'+n(x.delivery_pct,1)+'%</span><span>'+n(x.volume_ratio,1)+'×</span><span>'+esc((x.evidence||[]).join(" · "))+'</span></div>';});
    smart+='</div><div class="rl2-note">Current footprint combines delivery, volume, Research Radar accumulation/distribution, bulk/block context and circuit-band changes. Each row also stores a 20-session price/volume timeline for future drill-down.</div>';

    var sc=(d.scoreboard||{}).rows||[];
    var score='<div class="rl2-table"><div class="rl2-tr rl2-th"><span>Type</span><span>Signal</span><span>Obs</span><span>5D +ve</span><span>20D +ve</span></div>';
    sc.forEach(function(x){score+='<div class="rl2-tr"><span>'+esc(x.type)+'</span><span>'+esc(x.signal)+'</span><span>'+n(x.observations,0)+'</span><span>'+n(x["5d_positive_pct"],1)+'%</span><span>'+n(x["20d_positive_pct"],1)+'%</span></div>';});
    score+='</div><div class="rl2-note">Only observed outcomes are counted. New GTI and TimesFM tracking starts from this release; there are no hidden wins or backfilled assumptions.</div>';

    var tr=d.trust||{}, src=tr.sources||{};
    var trust='<div class="rl2-cols"><div>'+Object.keys(src).slice(0,4).map(function(k){return '<div class="rl2-row"><span>'+esc(k)+'</span><b>available</b></div>';}).join("")+'</div><div>'+Object.keys(src).slice(4).map(function(k){return '<div class="rl2-row"><span>'+esc(k)+'</span><b>available</b></div>';}).join("")+'</div></div>'+
      '<div class="rl2-note">Next build candidates: results-day expected move, event studies, sector RRG and IPO GMP accuracy. These should only activate when their historical fields are actually present, rather than filling gaps with samples.</div>';

    wrap.innerHTML=card("11 · DAYS LIKE TODAY","HISTORICAL CONTEXT",days)+card("12 · SMART-MONEY FOOTPRINT","DESCRIPTIVE",smart)+card("13 · PUBLIC SCOREBOARD","OUTCOME TRACKER",score)+card("14 · DATA TRUST + ROADMAP","PROVENANCE",trust);
    host.appendChild(wrap);
    wrap.querySelectorAll(".rl2-tip").forEach(function(b){b.addEventListener("click",function(){alert(tip(b.getAttribute("data-metric")));});});
  }
  function boot(){J("research-edge-pack.json").then(mount).catch(function(){});}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
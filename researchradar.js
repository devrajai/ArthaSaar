/* ArthaSaar Research Radar — 10 free-data features in one Home module. */
(function(){
  "use strict";
  var BASE=(location.pathname.indexOf("/app/")>=0?"../data/":"data/");
  function J(n){return fetch(BASE+n+"?t="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(n);return r.json();});}
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function nf(x,d){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?2:d});}
  function pct(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
  function card(title,body,meta){return '<div class="card rr-card"><div class="sh2">'+title+(meta?'<span class="fr">'+esc(meta)+'</span>':"")+"</div>"+body+"</div>";}
  function row(a,b,cl){return '<div class="zrow"><span>'+esc(a)+'</span><b class="'+(cl||"")+'">'+esc(b)+"</b></div>";}
  function mount(d){
    var home=document.getElementById("v-home")||document.querySelector("section#home");
    var dedicated=document.getElementById("research-radar");
    var target=dedicated||home;
    if(!target)return;
    if(dedicated && dedicated.querySelector(".rr-grid"))return;
    if(!dedicated && document.getElementById("as-research-radar"))return;
    var f=d.features||{}, hp=f.corporate_actions||{}, w=f.week52||{}, br=f.breadth_history||{}, ix=f.index_changes||{}, macro=f.rbi_macro||{}, bb=f.bulk_block||{}, res=f.results||{}, sec=f.sector_rotation||{}, reg=f.market_regime||{}, dr=f.data_resilience||{}, hs=(br.history||[]).slice(-14);
    var events=(hp.events||[]).slice(0,8).map(function(x){return '<div class="ni"><div style="display:flex;justify-content:space-between;gap:8px"><b>'+esc(x.symbol)+" · "+esc(x.kind)+'</b><small>'+esc(x.date||"—")+"</small></div><small>"+esc(x.subject||"")+(x.pdf?' · <a target="_blank" rel="noopener" href="'+esc(x.pdf)+'">filing</a>':"")+"</small></div>";}).join("");
    var highs=(w.near_highs||[]).slice(0,6).map(function(x){return row(x.symbol,pct(x.from_high_pct),"up");}).join("");
    var lows=(w.near_lows||[]).slice(0,6).map(function(x){return row(x.symbol,pct(x.from_low_pct),"dn");}).join("");
    var spark=hs.length?'<div class="rr-spark"><svg viewBox="0 0 400 70" preserveAspectRatio="none"><polyline points="'+hs.map(function(x,i){var y=66-Math.max(0,Math.min(100,Number(x.advance_ratio_pct||0)))*0.58;return (i*400/Math.max(1,hs.length-1)).toFixed(1)+","+y.toFixed(1);}).join(" ")+'" fill="none" stroke="var(--accent)" stroke-width="2.5"/></svg></div>':"";
    var addedRemoved=Object.keys(ix.membership_changes||{}).map(function(k){var z=ix.membership_changes[k]||{};return '<div class="zrow"><span>'+esc(k)+'</span><b>'+nf((z.added||[]).length,0)+" in · "+nf((z.removed||[]).length,0)+" out · "+nf((z.weight_changes||[]).length,0)+" weight</b></div>";}).join("");
    var indexRows=(ix.daily_watch||[]).slice(0,7).map(function(x){return row(x.index,pct(x.change_pct),Number(x.change_pct||0)>=0?"up":"dn");}).join("");
    var macroRows=(macro.indicators||[]).slice(0,6).map(function(x){return '<div class="ni"><b>'+esc(x.name)+'</b><small>'+esc(x.value||"—")+" · "+esc(x.date||"")+" · "+esc(x.source||"")+"</small></div>";}).join("");
    var bulk=(bb.bulk||[]).slice(0,5).map(function(x){return row(x.s,(x.bv||0).toFixed(1)+" / "+(x.sv||0).toFixed(1)+" Cr");}).join("");
    var block=(bb.block||[]).slice(0,5).map(function(x){return row(x.s,(x.t||0).toFixed(1)+" Cr");}).join("");
    var resRows=(res.items||[]).filter(function(x){return x.date;}).slice(0,7).map(function(x){return row(x.sym+" · "+x.company,x.date);}).join("");
    var sector=(sec.sectors||[]).slice(0,8).map(function(x){return row(x.sector,pct(x.avg_1d_pct),Number(x.avg_1d_pct||0)>=0?"up":"dn");}).join("");
    var health=dr.summary||{};
    var html='<div id="as-research-radar" class="hp-wrap"><div class="sect">RESEARCH RADAR · 10 FREE-DATA FEATURES <span class="fr">EOD · auto-built by GitHub Actions</span></div>'+
      '<div class="rr-grid">'+
      card("1 · CORPORATE ACTIONS",events||'<div class="mut">No matching filings.</div>',nf(hp.count,0)+" filing events")+
      card("2 · 52-WEEK MAP",row("Near 52W high zone",nf(w.new_high_zone_count,0),"up")+row("Near 52W low zone",nf(w.new_low_zone_count,0),"dn")+'<div class="rr-cols"><div>'+highs+'</div><div>'+lows+"</div></div>","NSE screener")+
      card("3 · BREADTH HISTORY",row("Today",nf((br.today||{}).advancers,0)+" adv / "+nf((br.today||{}).decliners,0)+" dec")+row("Advance ratio",pct((br.today||{}).advance_ratio_pct||0))+row("EMA200 breadth",nf((br.today||{}).ema200_pct,1)+"%")+spark,"260 sessions")+
      card("4 · INDEX / CONSTITUENT CHANGES",indexRows+addedRemoved+'<div class="mut" style="padding:8px 14px">NIFTY 50/100/200 membership and weight changes are tracked when NSE public CSVs expose them.</div>',nf(ix.indices_count,0)+" indices")+
      '</div><div class="rr-grid">'+
      card("5 · RBI / MACRO PULSE",macroRows||'<div class="mut">Macro snapshot unavailable.</div>","RBI/public macro + existing pulse")+
      card("6 · BULK / BLOCK DEALS",'<div class="rr-cols"><div>'+bulk+'</div><div>'+block+"</div></div>","NSE-derived snapshot")+
      card("7 · RESULTS CALENDAR",resRows||'<div class="mut">No dated results in current snapshot.</div>',res.quarter||"exchange filings")+
      card("8 · SECTOR ROTATION",sector||'<div class="mut">Sector data unavailable.</div>","1D move + breadth + EMA200")+
      '</div><div class="rr-grid">'+
      card("9 · MARKET REGIME",row("Regime",reg.label||"—")+row("Composite",nf(reg.score,0)+"/4")+row("Breadth",nf(reg.advance_ratio_pct,1)+"% adv")+row("NIFTY 50",pct(reg.nifty_change_pct),Number(reg.nifty_change_pct||0)>=0?"up":"dn")+'<div class="mut" style="padding:8px 14px">'+esc(reg.method||"Derived snapshot.")+"</div>","descriptive · not forecast")+
      card("10 · DATA RESILIENCE",row("Feeds OK",nf(health.ok,0)+"/"+nf(health.total,0))+row("Problems",nf(health.problems,0),health.problems?"dn":"up")+row("Policy","NSE EOD → Yahoo → last valid"),"updated "+(dr.health_updated||d.updated||"—"))+
      '</div><div class="rr-note">Free/public-data architecture: NSE public reports are primary for Indian EOD data; Yahoo remains the historical backup. Research Radar is informational and preserves previous valid snapshots when a collector fails.</div></div>';
    var brief=document.getElementById("as-home-brief");
    if(dedicated) target.insertAdjacentHTML("beforeend",html);
    else if(brief) brief.insertAdjacentHTML("afterend",html);
    else home.insertAdjacentHTML("afterbegin",html);
  }
  function css(){if(document.getElementById("as-research-radar-css"))return;var s=document.createElement("style");s.id="as-research-radar-css";s.textContent='.rr-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.rr-card{min-width:0}.rr-cols{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:4px 14px 8px}.rr-spark{padding:8px 14px 6px;border-bottom:1px solid var(--border)}.rr-spark svg{width:100%;height:70px;display:block}.rr-note{margin-top:9px;padding:10px 12px;border:1px dashed var(--border);border-radius:9px;color:var(--dim);font:400 10px var(--mono);line-height:1.5}.rr-card a{color:var(--accent);text-decoration:none}.rr-card a:hover{text-decoration:underline}.mut{padding:10px 14px;color:var(--dim);font:400 10px var(--mono)}@media(max-width:720px){.rr-grid{grid-template-columns:1fr}.rr-cols{grid-template-columns:1fr}}';document.head.appendChild(s);}
  function boot(){css();J("research-radar.json").then(mount).catch(function(){});}
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
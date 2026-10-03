(function(){
"use strict";
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":">","\"":"&quot;"}[c];});}
function n(x){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:1});}
function p(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
function row(a,b,cl){return '<div class="zrow"><span>'+esc(a)+'</span><b class="'+(cl||"")+'">'+esc(b)+'</b></div>';}
function card(t,b,m){return '<div class="card" style="margin-top:10px"><div class="sh2">'+esc(t)+(m?'<span class="fr">'+esc(m)+'</span>':"")+'</div>'+b+'</div>';}
function render(d){
 var host=document.getElementById("research-radar"); if(!host)return;
 var f=d.features||{},w=f.week52||{},br=f.breadth_history||{},ix=f.index_changes||{},ma=f.rbi_macro||{},bb=f.bulk_block||{},re=f.results||{},se=f.sector_rotation||{},rg=f.market_regime||{},dr=f.data_resilience||{},ca=f.corporate_actions||{};
 var ev=(ca.events||[]).slice(0,6).map(function(x){return '<div class="ni"><b>'+esc(x.symbol||"—")+' · '+esc(x.kind||"")+'</b><small>'+esc(x.date||"")+' · '+esc(x.subject||"")+'</small></div>';}).join("")||'<div class="mut">No events in snapshot.</div>';
 var hi=(w.near_highs||[]).slice(0,5).map(function(x){return row(x.symbol,p(x.from_high_pct),"up");}).join("");
 var lo=(w.near_lows||[]).slice(0,5).map(function(x){return row(x.symbol,p(x.from_low_pct),"dn");}).join("");
 var mac=(ma.indicators||[]).slice(0,6).map(function(x){return '<div class="ni"><b>'+esc(x.name)+'</b><small>'+esc(x.value||"—")+' · '+esc(x.date||"")+'</small></div>';}).join("")||'<div class="mut">Macro snapshot unavailable.</div>';
 var bu=(bb.bulk||[]).slice(0,5).map(function(x){return row(x.s,(x.bv||0).toFixed(1)+" Cr");}).join("")||'<div class="mut">No bulk deals.</div>';
 var bl=(bb.block||[]).slice(0,5).map(function(x){return row(x.s,(x.t||0).toFixed(1)+" Cr");}).join("")||'<div class="mut">No block deals.</div>';
 var rr=(re.items||[]).filter(function(x){return x.date;}).slice(0,6).map(function(x){return row((x.sym||"")+" · "+(x.company||""),x.date);}).join("")||'<div class="mut">No dated results.</div>';
 var ss=(se.sectors||[]).slice(0,8).map(function(x){return row(x.sector,p(x.avg_1d_pct),Number(x.avg_1d_pct||0)>=0?"up":"dn");}).join("")||'<div class="mut">Sector data unavailable.</div>';
 var changes=Object.keys(ix.membership_changes||{}).map(function(k){var z=ix.membership_changes[k]||{};return row(k,(z.added||[]).length+" in · "+(z.removed||[]).length+" out");}).join("")||'<div class="mut">Membership comparison will populate from the next NSE snapshot.</div>';
 var health=dr.summary||{};
 host.innerHTML='<div class="rr-grid">'+
 card("1 · CORPORATE ACTIONS",ev,n(ca.count)+" events")+
 card("2 · 52-WEEK MAP",row("Near high zone",n(w.new_high_zone_count),"up")+row("Near low zone",n(w.new_low_zone_count),"dn")+'<div class="rr-cols"><div>'+hi+'</div><div>'+lo+'</div></div>',"NSE screener")+
 card("3 · BREADTH HISTORY",row("Advancers",n((br.today||{}).advancers))+row("Decliners",n((br.today||{}).decliners))+row("Advance ratio",p((br.today||{}).advance_ratio_pct)),"daily history")+
 card("4 · INDEX / CONSTITUENT CHANGES",changes+row("Indices tracked",n(ix.indices_count)),"NSE public data")+
 card("5 · RBI / MACRO PULSE",mac,"macro snapshot")+
 card("6 · BULK / BLOCK DEALS",'<div class="rr-cols"><div>'+bu+'</div><div>'+bl+'</div></div>',"NSE-derived")+
 card("7 · RESULTS CALENDAR",rr,re.quarter||"filings")+
 card("8 · SECTOR ROTATION",ss,"1D rotation")+
 card("9 · MARKET REGIME",row("Regime",rg.label||"—")+row("Composite",n(rg.score)+"/4")+row("Breadth",p(rg.advance_ratio_pct))+row("NIFTY 50",p(rg.nifty_change_pct),Number(rg.nifty_change_pct||0)>=0?"up":"dn"),"descriptive · not forecast")+
 card("10 · DATA RESILIENCE",row("Feeds OK",n(health.ok)+"/"+n(health.total))+row("Problems",n(health.problems),health.problems?"dn":"up")+row("Fallback","NSE → Yahoo → last valid"),"updated "+(dr.health_updated||d.updated||"—"))+
 '</div><div class="rr-note">Free/public-data architecture · NSE primary · Yahoo historical backup · GitHub Actions EOD refresh.</div>';
}
function boot(){
 var h=document.getElementById("research-radar");if(!h)return;
 h.innerHTML='<div class="card" style="margin-top:10px;padding:18px">Loading Research Radar data…</div>';
 fetch("data/research-radar.json?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("HTTP "+r.status);return r.json();}).then(render).catch(function(e){h.innerHTML='<div class="card" style="margin-top:10px;padding:18px"><b>Research Radar data could not load.</b><div class="mut" style="padding-left:0">Check GitHub Pages deployment / data file. '+esc(e.message)+'</div></div>';});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
window.addEventListener("hashchange",function(){setTimeout(boot,100);});
})();
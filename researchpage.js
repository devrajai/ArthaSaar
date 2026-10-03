(function(){
"use strict";

function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":">","\"":"&quot;"}[c];});}
function n(x){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:1});}
function p(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
function row(a,b,cl){return '<div class="zrow"><span>'+esc(a)+'</span><b class="'+(cl||"")+'">'+esc(b)+'</b></div>';}
function rows(arr, akey, bkey, clsFn, limit){
 return (arr||[]).slice(0,limit||8).map(function(x){
   var a=x[akey], b=x[bkey], cl=clsFn?clsFn(x):"";
   return row(a==null?"—":a,b==null?"—":b,cl);
 }).join("")||'<div class="mut">No snapshot rows.</div>';
}
function itemList(arr, fn, limit){
 return (arr||[]).slice(0,limit||6).map(fn).join("")||'<div class="mut">No snapshot rows.</div>';
}
function card(num,title,body,meta,wide){
 return '<div class="card rr-card '+(wide?'rr-wide':'')+'"><div class="sh2">'+num+' · '+esc(title)+(meta?'<span class="fr">'+esc(meta)+'</span>':"")+'</div>'+body+'</div>';
}
function installCSS(){
 if(document.getElementById("rr44-style"))return;
 var s=document.createElement("style");s.id="rr44-style";
 s.textContent=[
 ".rr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}",
 ".rr-card{min-width:0}.rr-wide{grid-column:1/-1}",
 ".rr-cols{display:grid;grid-template-columns:1fr 1fr;gap:8px}",
 ".rr-sub{font:600 9px var(--mono);letter-spacing:.14em;color:var(--faint);padding:9px 12px 3px;text-transform:uppercase}",
 ".rr-note{margin:12px 2px 20px;padding:10px 12px;border:1px dashed var(--border2);border-radius:10px;color:var(--dim);font:400 9.5px var(--mono);line-height:1.55}",
 ".mut{padding:12px 14px;color:var(--faint);font:400 10px var(--mono)}",
 ".rr-kicker{padding:10px 12px 2px;color:var(--faint);font:500 9px var(--mono)}",
 "@media(max-width:720px){.rr-grid{grid-template-columns:1fr}.rr-wide{grid-column:auto}.rr-cols{grid-template-columns:1fr}}"
 ].join("");
 document.head.appendChild(s);
}
function eventBody(arr){
 return itemList(arr,function(x){return '<div class="ni"><b>'+esc(x.symbol||x.sym||"—")+' · '+esc(x.kind||x.category||"Event")+'</b><small>'+esc(x.date||"")+' · '+esc(x.subject||x.expected||"")+'</small></div>';},6);
}
function render(d){
 var host=document.getElementById("research-radar"); if(!host)return;
 installCSS();
 var f=d.features||{};
 var w=f.week52||{},br=f.breadth_history||{},ix=f.index_changes||{},ma=f.rbi_macro||{},bb=f.bulk_block||{},re=f.results||{},se=f.sector_rotation||{},rg=f.market_regime||{},dr=f.data_resilience||{},ca=f.corporate_actions||{};
 var h=f.breakout_radar||{},vs=f.volume_shock||{},dc=f.delivery_conviction||{},ad=f.accumulation_distribution||{},gap=f.gap_radar||{};
 var rs=f.relative_strength||{},sm=f.sector_matrix||{},ve=f.volatility_expansion||{},rx=f.range_expansion||{};
 var mo=f.momentum_dashboard||{},th=f.trend_health||{},cross=f.dma_cross_radar||{},dm=f.distance_map||{};
 var es=f.earnings_surprise||{},pi=f.promoter_insider||{},pl=f.pledge_watch||{},cc=f.corporate_calendar||{};
 var dv=f.dividend_radar||{},bo=f.buyback_open_offer||{},foi=f.fo_oi_change||{},op=f.option_pulse||{};
 var fm=f.futures_basis||{},fb=f.fo_buildup||{},bt=f.bulk_followthrough||{},iflow=f.institutional_flow_trend||{};
 var bm=f.breadth_momentum||{},hlb=f.high_low_breadth||{},mc=f.market_concentration||{},nl=f.nifty_leadership||{};
 var ib=f.index_bucket_breadth||{},ls=f.liquidity_stress||{},rel=f.data_reliability||{};

 var html='<div class="rr-grid">';
 html+=card("01","CORPORATE ACTIONS",eventBody(ca.events),n(ca.count)+" events");
 html+=card("02","52-WEEK MAP",row("Near high zone",n(w.new_high_zone_count),"up")+row("Near low zone",n(w.new_low_zone_count),"dn")+rows(w.near_highs,"symbol","from_high_pct",function(){return"up";},4)+rows(w.near_lows,"symbol","from_low_pct",function(){return"dn";},4),"NSE screener");
 html+=card("03","BREADTH HISTORY",row("Advancers",n((br.today||{}).advancers))+row("Decliners",n((br.today||{}).decliners))+row("Advance ratio",p((br.today||{}).advance_ratio_pct))+row("200D EMA",p((br.today||{}).ema200_pct)), "daily history");
 html+=card("04","INDEX / CONSTITUENT CHANGES",Object.keys(ix.membership_changes||{}).map(function(k){var z=ix.membership_changes[k]||{};return row(k,(z.added||[]).length+" in · "+(z.removed||[]).length+" out");}).join("")+row("Indices tracked",n(ix.indices_count)),"NSE public data");
 html+=card("05","RBI / MACRO PULSE",itemList(ma.indicators,function(x){return'<div class="ni"><b>'+esc(x.name||"Macro")+'</b><small>'+esc(x.value||"—")+' · '+esc(x.date||"")+'</small></div>';},6),"macro snapshot");
 html+=card("06","BULK / BLOCK DEALS",'<div class="rr-cols"><div>'+rows(bb.bulk,"s","t",function(){return"";},5)+'</div><div>'+rows(bb.block,"s","t",function(){return"";},5)+'</div></div>',"NSE-derived");
 html+=card("07","RESULTS CALENDAR",rows(re.items,"sym","date",null,8),re.quarter||"results");
 html+=card("08","SECTOR ROTATION",rows(se.sectors,"sector","avg_1d_pct",function(x){return (x.avg_1d_pct||0)>=0?"up":"dn";},8),"1D rotation");
 html+=card("09","MARKET REGIME",row("Regime",rg.label||"—")+row("Composite",n(rg.score)+"/4")+row("Breadth",p(rg.advance_ratio_pct))+row("NIFTY 50",p(rg.nifty_change_pct),(rg.nifty_change_pct||0)>=0?"up":"dn"),"descriptive");
 var hs=dr.summary||{}; html+=card("10","DATA RESILIENCE",row("Feeds OK",n(hs.ok)+"/"+n(hs.total))+row("Problems",n(hs.problems),hs.problems?"dn":"up")+row("Fallback","NSE → Yahoo → last valid"),"updated "+(dr.health_updated||d.updated||"—"));

 html+=card("11","52W BREAKOUT RADAR",row("Candidates",n(h.count))+rows(h.rows,"symbol","distance_252_high_pct",function(){return"up";},7),"≤0.75% from 252D high");
 html+=card("12","VOLUME SHOCK RADAR",rows(vs.rows,"symbol","vol_vs_avg20",function(){return"up";},8),"×20D avg");
 html+=card("13","DELIVERY CONVICTION",row("Coverage",n(dc.coverage))+row("Avg delivery",p((dc.avg_delivery_pct||0)-50))+rows(dc.high_delivery_up,"symbol","delivery_pct",function(){return"up";},4),"delivery %");
 html+=card("14","PRICE × VOLUME ACCUMULATION",'<div class="rr-cols"><div><div class="rr-sub">Accumulation</div>'+rows(ad.accumulation,"symbol","volume_ratio",function(){return"up";},5)+'</div><div><div class="rr-sub">Distribution</div>'+rows(ad.distribution,"symbol","volume_ratio",function(){return"dn";},5)+'</div></div>',"derived");
 html+=card("15","GAP-UP / GAP-DOWN RADAR",row("Status",gap.available?"LIVE":"WAITING"),'<span class="rr-kicker">'+esc(gap.reason||"")+'</span>',"OHLC requirement");
 html+=card("16","RELATIVE STRENGTH vs NIFTY",row("NIFTY 20D",p(rs.benchmark_return_20d_pct))+rows(rs.leaders,"symbol","relative_strength_20d",function(){return"up";},6)+rows(rs.laggards,"symbol","relative_strength_20d",function(){return"dn";},6),"20D");
 html+=card("17","SECTOR STRENGTH MATRIX",rows(sm.sectors,"sector","avg_20d_pct",function(x){return(x.avg_20d_pct||0)>=0?"up":"dn";},10),"1D + 20D + breadth");
 html+=card("18","VOLATILITY EXPANSION",rows(ve.rows,"symbol","vol_expansion",function(x){return(x.vol_expansion||0)>=1?"up":"";},8),"20D / 60D volatility");
 html+=card("19","ATR / RANGE EXPANSION",row("Status",rx.available?"LIVE":"Proxy only")+row("Proxy","Close-to-close volatility"),'<span class="rr-kicker">'+esc(rx.reason||"")+'</span>','range');
 html+=card("20","MOMENTUM DASHBOARD",row("RSI >60",n((mo.rsi_high||[]).length),"up")+row("RSI <40",n((mo.rsi_low||[]).length),"dn")+row("MACD positive",n((mo.macd_positive||[]).length),"up")+rows(mo.roc_leaders,"symbol","return_20d",function(){return"up";},5),"RSI · MACD · ROC");
 html+=card("21","TREND HEALTH",row("Above EMA200",p(th.above_ema200_pct))+rows(th.above_ema200,"symbol","return_20d",function(){return"up";},5)+rows(th.below_ema200,"symbol","return_20d",function(){return"dn";},5),"20/200 trend");
 html+=card("22","GOLDEN / DEATH CROSS",row("Golden",n(cross.golden_cross_count),"up")+row("Death",n(cross.death_cross_count),"dn")+rows(cross.golden_candidates,"symbol","return_20d",function(){return"up";},4)+rows(cross.death_candidates,"symbol","return_20d",function(){return"dn";},4),"50D vs 200D");
 html+=card("23","52W HIGH / LOW DISTANCE",rows(dm.near_high_200d,"symbol","distance_252_high_pct",function(){return"up";},5)+rows(dm.near_low_200d,"symbol","distance_252_low_pct",function(){return"dn";},5),"252-session map");
 html+=card("24","EARNINGS SURPRISE TRACKER",row("Standardized surprise","Unavailable")+row("Upcoming results",n((es.upcoming_results||[]).length))+eventBody(es.results_filing_events), "public data coverage");
 html+=card("25","PROMOTER / INSIDER ACTIVITY",row("Events",n(pi.count))+eventBody(pi.events),"filing keyword radar");
 html+=card("26","PLEDGE / ENCUMBRANCE WATCH",row("Events",n(pl.count))+eventBody(pl.events),"filing keyword radar");
 html+=card("27","CORPORATE ACTION CALENDAR",rows(cc.next_results,"sym","date",null,10),"upcoming");
 html+=card("28","DIVIDEND RADAR",row("Events",n(dv.count))+eventBody(dv.events),"filings");
 html+=card("29","BUYBACK / OPEN OFFER",row("Events",n(bo.count))+eventBody(bo.events),"filings");
 html+=card("30","F&O OI CHANGE RADAR",rows(foi.rows,"symbol","oi_change_pct",function(x){return(x.oi_change_pct||0)>=0?"up":"dn";},10),n(foi.coverage)+" contracts");
 html+=card("31","OI × PRICE MATRIX",row("Long build",n((fb.counts||{})["LONG BUILD"]),"up")+row("Short build",n((fb.counts||{})["SHORT BUILD"]),"dn")+row("Short cover",n((fb.counts||{})["SHORT COVER"]),"up")+row("Long unwind",n((fb.counts||{})["LONG UNWIND"]),"dn"),"F&O derived");
 html+=card("32","PUT / CALL + MAX PAIN",row("PCR OI",n(op.nifty_pcr_oi))+row("PCR volume",n(op.nifty_pcr_vol))+row("Max pain",n(op.max_pain))+row("Expiry",op.expiry||"—")+row("Spot",n(op.spot)),"NIFTY options");
 html+=card("33","FUTURES BASIS / SPREAD",rows(fm.rows,"symbol","basis_pct",function(x){return(x.basis_pct||0)>=0?"up":"dn";},10),"near-month");
 html+=card("34","LONG / SHORT BUILDUP RADAR",'<div class="rr-cols"><div>'+rows(fb.long_build,"symbol","oi_change_pct",function(){return"up";},5)+rows(fb.short_cover,"symbol","oi_change_pct",function(){return"up";},5)+'</div><div>'+rows(fb.short_build,"symbol","oi_change_pct",function(){return"dn";},5)+rows(fb.long_unwind,"symbol","oi_change_pct",function(){return"dn";},5)+'</div></div>',"F&O");
 html+=card("35","BULK DEAL FOLLOW-THROUGH",rows(bt.rows,"symbol","change_pct",function(x){return(x.change_pct||0)>=0?"up":"dn";},10),"deal joined to EOD move");
 html+=card("36","INSTITUTIONAL FLOW TREND",row("FII current",n((iflow.current||{}).net_cr))+row("DII current",n((iflow.dii_current||{}).net_cr))+row("FII sell days",n(iflow.fii_sell_days),(iflow.fii_sell_days||0)>0?"dn":"up")+rows(iflow.history,"date","fii_net_cr",function(x){return(x.fii_net_cr||0)>=0?"up":"dn";},6),"recent");
 html+=card("37","MARKET BREADTH MOMENTUM",row("3D up streak",n(bm.three_day_up),"up")+row("3D down streak",n(bm.three_day_down),"dn")+row("Volume >2×",n(bm.volume_spike_2x)), "universe");
 html+=card("38","NEW HIGH / NEW LOW BREADTH",row("New-high zone",n(hlb.new_high_zone),"up")+row("New-low zone",n(hlb.new_low_zone),"dn")+rows(hlb.near_highs,"symbol","change_pct",function(){return"up";},4)+rows(hlb.near_lows,"symbol","change_pct",function(){return"dn";},4),"universe");
 html+=card("39","MARKET CONCENTRATION",itemList(mc.indices,function(x){return row(x.index,"Top10 "+n(x.top10_weight_pct)+"%");},4),"constituent weights");
 html+=card("40","NIFTY LEADERSHIP RADAR",rows(nl.leaders,"symbol","relative_strength_20d",function(){return"up";},12),"weight + RS");
 html+=card("41","SMALL / MID / LARGE BUCKET BREADTH",rows(ib.buckets,"bucket","breadth_pct",function(x){return(x.breadth_pct||0)>=50?"up":"dn";},4),"index buckets");
 html+=card("42","LIQUIDITY STRESS RADAR",row("Low volume <0.5×",n(ls.low_volume_lt_0_5x),"dn")+row("High volume >2×",n(ls.high_volume_gt_2x),"up")+row("History <60D",n(ls.illiquid_history_lt_60d),"dn")+row("Universe",n(ls.coverage)),"coverage");
 html+=card("43","DATA RELIABILITY SCORE",row("Coverage score",p(rel.coverage_score_pct))+row("History ≥200D",p(rel.history_ge_200d_pct))+row("Delivery rows",n(rel.delivery_coverage))+row("F&O rows",n(rel.futures_stock_coverage)),"repo coverage");
 html+=card("44","DATA RESILIENCE DETAIL",row("History files",n(rel.history_files))+row("EMA200 coverage",p(rel.ema200_coverage_pct))+row("Delivery coverage",n(rel.delivery_coverage))+row("Futures coverage",n(rel.futures_stock_coverage))+row("EOD fallback","NSE → Yahoo → last valid"),"system health");
 html+='</div><div class="rr-note"><b>44 free-data research modules.</b> NSE/public exchange snapshots remain primary; Yahoo is used only for historical backup. Modules explicitly mark unavailable calculations when the stored public snapshot lacks the required field, rather than fabricating values. Updated '+esc(d.updated||"—")+'.</div>';
 host.innerHTML=html;
}
function boot(){
 var h=document.getElementById("research-radar");if(!h)return;
 installCSS();
 h.innerHTML='<div class="card" style="margin-top:10px;padding:18px">Loading 44 Research Radar modules…</div>';
 fetch("data/research-radar.json?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("HTTP "+r.status);return r.json();}).then(render).catch(function(e){h.innerHTML='<div class="card" style="margin-top:10px;padding:18px"><b>Research Radar data could not load.</b><div class="mut" style="padding-left:0">Check Pages deployment / research-radar.json. '+esc(e.message)+'</div></div>';});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
window.addEventListener("hashchange",function(){setTimeout(boot,100);});
})();
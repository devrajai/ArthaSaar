(function(){
"use strict";

function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":">","\"":"&quot;"}[c];});}
function n(x){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:1});}
function p(x){return x==null||isNaN(x)?"—":(Number(x)>=0?"+":"")+Number(x).toFixed(2)+"%";}
function row(a,b,cl){return '<div class="zrow"><span>'+esc(a)+'</span><b class="'+(cl||"")+'">'+esc(b)+'</b></div>';}
function rows(arr, akey, bkey, clsFn, limit){
 return (arr||[]).slice(0,limit||8).map(function(x){
   var a=x[akey], b=x[bkey], cl=clsFn?clsFn(x):"";
   if((akey==="symbol"||akey==="sym") && a){
     return '<div class="zrow"><button class="rr-symbol" data-symbol="'+esc(a)+'">'+esc(a)+'</button><b class="'+(cl||"")+'">'+esc(b==null?"—":b)+'</b></div>';
   }
   return row(a==null?"—":a,b==null?"—":b,cl);
 }).join("")||'<div class="mut">No snapshot rows.</div>';
}
function itemList(arr, fn, limit){
 return (arr||[]).slice(0,limit||6).map(fn).join("")||'<div class="mut">No snapshot rows.</div>';
}
function moduleSource(num){
 var n0=parseInt(num,10)||0;
 if(n0<=4) return "NSE / ArthaSaar";
 if(n0===5) return "RBI / public macro";
 if(n0<=8) return "NSE / filings";
 if(n0===9) return "Derived";
 if(n0===10) return "ArthaSaar health";
 if(n0<=14) return "NSE / EOD";
 if(n0===15) return "OHLC needed";
 if(n0<=23) return "EOD history";
 if(n0<=29) return "Filings / results";
 if(n0<=35) return "NSE F&O";
 if(n0<=38) return "NSE / universe";
 if(n0<=41) return "NSE constituents";
 return "ArthaSaar";
}
function freshnessStamp(iso){
 if(!iso) return {label:"NO TIMESTAMP",cls:"no"};
 var t=Date.parse(iso);
 if(!isFinite(t)) return {label:"NO TIMESTAMP",cls:"no"};
 var h=Math.max(0,(Date.now()-t)/3600000);
 if(h<24) return {label:"FRESH",cls:"fresh"};
 if(h<72) return {label:"AGING",cls:"aging"};
 return {label:"STALE",cls:"stale"};
}
function moduleUpdated(num,d){
 var f=(d&&d.features)||{}, n0=parseInt(num,10)||0;
 if(n0===7 && f.results && f.results.updated) return f.results.updated;
 if(n0===6 && f.bulk_block && f.bulk_block.updated) return f.bulk_block.updated;
 if(n0===10 && f.data_resilience && f.data_resilience.health_updated) return f.data_resilience.health_updated;
 return d&&d.updated;
}
function badgeHtml(num,d){
 var fr=freshnessStamp(moduleUpdated(num,d));
 return '<span class="rr-badges"><span class="rr-badge source">'+esc(moduleSource(num))+'</span><span class="rr-badge '+fr.cls+'">'+fr.label+'</span></span>';
}
function card(num,title,body,meta,wide){
 var d=window.__rr44Data||{};
 return '<div class="card rr-card '+(wide?'rr-wide':'')+'"><div class="sh2"><span>'+num+' · '+esc(title)+'</span><span class="rr-head-right">'+badgeHtml(num,d)+(meta?'<span class="fr">'+esc(meta)+'</span>':"")+'</span></div>'+body+'</div>';
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
 ".rr-head-right{display:flex;align-items:center;gap:5px;flex-wrap:wrap;justify-content:flex-end}.rr-badges{display:inline-flex;gap:4px;align-items:center}.rr-badge{font:600 7.5px var(--mono);letter-spacing:.04em;border:1px solid var(--border);border-radius:999px;padding:2px 5px}.rr-badge.source{color:var(--dim)}.rr-badge.fresh{color:var(--up);border-color:color-mix(in srgb,var(--up) 45%,transparent)}.rr-badge.aging{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}.rr-badge.stale,.rr-badge.no{color:var(--down);border-color:color-mix(in srgb,var(--down) 45%,transparent)}.rr-symbol{border:0;background:none;padding:0;color:var(--text);font:700 11px var(--font);cursor:pointer;text-decoration:underline;text-decoration-color:transparent}.rr-symbol:hover{text-decoration-color:var(--accent);color:var(--accent)}.rr-event-symbol{font-size:11px}.rr-lab{margin-top:10px;overflow:hidden}.rr-lab-top{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--border)}.rr-lab-top b{font-size:13px}.rr-lab-top small{display:block;margin-top:3px;color:var(--dim);font:400 9px var(--mono)}.rr-lab-search{display:flex;gap:6px;min-width:320px}.rr-lab-search input{flex:1;min-width:180px;border:1px solid var(--border2);background:var(--surface);color:var(--text);padding:8px 10px;border-radius:8px;font:500 11px var(--mono)}.rr-lab-search button{border:1px solid var(--accent);background:var(--accent);color:var(--bg);padding:8px 11px;border-radius:8px;font:700 9px var(--mono);cursor:pointer}.rr-lab-grid{display:grid;grid-template-columns:1.2fr repeat(3,1fr);gap:8px;padding:12px 14px}.rr-lab-grid>div{min-width:0}.rr-lab-symbol{font:800 16px var(--mono);letter-spacing:.04em}.rr-lab-price{font:800 25px var(--mono);margin:5px 0 2px}.rr-lab-events{padding:8px 14px;border-top:1px solid var(--border)}.rr-drill-note,.rr-lab-source{padding:8px 14px;color:var(--dim);font:400 9px var(--mono);line-height:1.5}.rr-backtest-bar{padding:9px 14px;border-top:1px solid var(--border);background:color-mix(in srgb,var(--border) 12%,var(--surface))}.rr-backtest-bar label{font:600 9px var(--mono);color:var(--dim)}.rr-backtest-bar select{margin-left:7px;border:1px solid var(--border2);background:var(--surface);color:var(--text);padding:5px 7px;border-radius:7px;font:600 9px var(--mono)}.rr-back-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;padding:8px 0}.rr-back-grid .zrow{padding:7px 8px;display:block;background:var(--surface);border:1px solid var(--border);border-radius:7px}.rr-back-grid .zrow b{display:block;margin-top:3px}.rr-sub{font:600 8.5px var(--mono);letter-spacing:.12em;color:var(--faint);padding:7px 0 2px;text-transform:uppercase}",
 "@media(max-width:880px){.rr-lab-top{flex-direction:column;align-items:stretch}.rr-lab-search{min-width:0}.rr-lab-grid{grid-template-columns:1fr 1fr}.rr-back-grid{grid-template-columns:repeat(2,1fr)}}",
 "@media(max-width:720px){.rr-grid{grid-template-columns:1fr}.rr-wide{grid-column:auto}.rr-cols{grid-template-columns:1fr}.rr-lab-grid{grid-template-columns:1fr}.rr-back-grid{grid-template-columns:1fr 1fr}}"
 ].join("");
 document.head.appendChild(s);
}
function eventBody(arr){
 return itemList(arr,function(x){
   var s=x.symbol||x.sym||"—";
   var head=s!=="—"?'<button class="rr-symbol rr-event-symbol" data-symbol="'+esc(s)+'">'+esc(s)+'</button>':'<b>—</b>';
   return '<div class="ni"><b>'+head+' · '+esc(x.kind||x.category||"Event")+'</b><small>'+esc(x.date||"")+' · '+esc(x.subject||x.expected||"")+'</small></div>';
 },6);
}

function historyRows(arr){
 return (arr||[]).filter(function(x){return x&&x.close!=null;}).sort(function(a,b){return String(a.date||"").localeCompare(String(b.date||""));});
}
function avgTail(vals,n0){
 var a=vals.slice(Math.max(0,vals.length-n0));
 return a.length?a.reduce(function(s,x){return s+x;},0)/a.length:null;
}
function median(vals){
 var a=vals.filter(function(x){return x!=null&&isFinite(x);}).slice().sort(function(a,b){return a-b;});
 if(!a.length)return null;
 var m=Math.floor(a.length/2);
 return a.length%2?a[m]:(a[m-1]+a[m])/2;
}
function backtest(history,kind){
 var rows0=historyRows(history), triggers=[];
 if(rows0.length<80)return {count:0,reason:"Not enough history for this event study."};
 var closes=rows0.map(function(x){return Number(x.close)||0;}), vols=rows0.map(function(x){return Number(x.volume)||0;});
 function smaAt(i,n0){if(i+1<n0)return null;var s=0;for(var j=i-n0+1;j<=i;j++)s+=closes[j];return s/n0;}
 function volRatioAt(i){var av=avgTail(vols.slice(0,i),20);return av>0?vols[i]/av:null;}
 for(var i=20;i<rows0.length-25;i++){
   var c0=closes[i], sma200=smaAt(i,200), vr=volRatioAt(i), prior=closes.slice(Math.max(0,i-252),i), ok=false;
   if(kind==="52W BREAKOUT") ok=prior.length>=60 && c0>=Math.max.apply(Math,prior)*0.99;
   else if(kind==="VOLUME SHOCK") ok=vr!=null && vr>=2;
   else if(kind==="TREND > 200DMA") ok=sma200!=null && c0>sma200;
   else if(kind==="20D MOMENTUM") ok=i>=20 && c0/closes[i-20]>=1.05;
   if(!ok)continue;
   triggers.push({date:rows0[i].date,r5:(closes[i+5]/c0-1)*100,r20:(closes[i+20]/c0-1)*100});
 }
 var r5=triggers.map(function(x){return x.r5;}),r20=triggers.map(function(x){return x.r20;});
 return {count:triggers.length,positive5:r5.length?100*r5.filter(function(x){return x>0;}).length/r5.length:null,positive20:r20.length?100*r20.filter(function(x){return x>0;}).length/r20.length:null,avg5:r5.length?r5.reduce(function(a,b){return a+b;},0)/r5.length:null,avg20:r20.length?r20.reduce(function(a,b){return a+b;},0)/r20.length:null,med5:median(r5),med20:median(r20),examples:triggers.slice(-8).reverse()};
}
function stockFind(d,sym){
 var f=d.features||{}, out={symbol:sym};
 var pools=[
   f.breakout_radar&&f.breakout_radar.rows,f.volume_shock&&f.volume_shock.rows,
   f.relative_strength&&f.relative_strength.leaders,f.relative_strength&&f.relative_strength.laggards,
   f.momentum_dashboard&&f.momentum_dashboard.rsi_high,f.momentum_dashboard&&f.momentum_dashboard.rsi_low,
   f.trend_health&&f.trend_health.above_ema200,f.trend_health&&f.trend_health.below_ema200,
   f.fo_oi_change&&f.fo_oi_change.rows,f.futures_basis&&f.futures_basis.rows,
   f.bulk_followthrough&&f.bulk_followthrough.rows,f.nifty_leadership&&f.nifty_leadership.leaders
 ];
 pools.forEach(function(arr){(arr||[]).forEach(function(x){if(String(x.symbol||"").toUpperCase()===sym)Object.keys(x).forEach(function(k){if(out[k]==null)out[k]=x[k];});});});
 var del=[].concat((f.delivery_conviction&&f.delivery_conviction.high_delivery_up)||[],(f.delivery_conviction&&f.delivery_conviction.high_delivery_down)||[]).find(function(x){return String(x.symbol||"").toUpperCase()===sym;});
 if(del){out.delivery_pct=del.delivery_pct;out.delivery_change_pct=del.change_pct;}
 out.events=(f.corporate_actions&&f.corporate_actions.events||[]).filter(function(x){return String(x.symbol||"").toUpperCase()===sym;}).slice(0,5);
 var fb=f.fo_buildup||{};
 ["long_build","short_build","short_cover","long_unwind"].some(function(k){var z=(fb[k]||[]).find(function(x){return String(x.symbol||"").toUpperCase()===sym;});if(z){out.fo_build=z.build;out.oi_change_pct=z.oi_change_pct;return true;}return false;});
 return out;
}
function initResearchLab(d){
 var host=document.getElementById("rr-lab"); if(!host)return;
 var input=host.querySelector("#rr-stock-input"), btn=host.querySelector("#rr-stock-go"), detail=host.querySelector("#rr-stock-detail"), bt=host.querySelector("#rr-backtest"), out=host.querySelector("#rr-backtest-out");
 function runBack(h,kind){
   var z=backtest(h,kind);
   if(!z.count){out.innerHTML='<div class="mut">'+esc(z.reason||"No trigger occurrences.")+'</div>';return;}
   out.innerHTML='<div class="rr-back-grid">'+row("Occurrences",n(z.count))+row("Positive after 5D",p(z.positive5))+row("Avg 5D",p(z.avg5),z.avg5>=0?"up":"dn")+row("Median 5D",p(z.med5),z.med5>=0?"up":"dn")+row("Positive after 20D",p(z.positive20))+row("Avg 20D",p(z.avg20),z.avg20>=0?"up":"dn")+row("Median 20D",p(z.med20),z.med20>=0?"up":"dn")+'</div><div class="rr-sub">Latest trigger dates</div>'+itemList(z.examples,function(x){return row(x.date,p(x.r20),x.r20>=0?"up":"dn");},8);
 }
 function loadSymbol(s){
   s=String(s||"").trim().toUpperCase().replace(/\s+/g,"");
   if(!s){detail.innerHTML='<div class="mut">Enter an NSE symbol.</div>';return;}
   detail.innerHTML='<div class="mut">Loading '+esc(s)+' history…</div>';
   Promise.all([
     fetch("data/history/"+encodeURIComponent(s)+".json?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("history "+r.status);return r.json();}),
     Promise.resolve(stockFind(d,s))
   ]).then(function(a){
     var h=historyRows(a[0]), x=a[1]||{}, last=h[h.length-1]||{}, price=last.close!=null?Number(last.close):x.price, prev=h.length>1?h[h.length-2].close:null;
     var ch=prev?((price/prev-1)*100):x.change_pct, av=avgTail(h.map(function(z){return Number(z.volume)||0;}),20), vr=av&&last.volume!=null?Number(last.volume)/av:null, s20=h.length>=21?((price/h[h.length-21].close-1)*100):x.return_20d;
     detail.innerHTML='<div class="rr-lab-grid">'+
       '<div><b class="rr-lab-symbol">'+esc(s)+'</b><div class="rr-lab-price">'+n(price)+'</div><div class="'+(ch>=0?"up":"dn")+'">'+p(ch)+'</div></div>'+
       '<div>'+row("20D return",p(s20),s20>=0?"up":"dn")+row("Delivery",x.delivery_pct==null?"—":n(x.delivery_pct)+"%")+row("Volume / 20D",vr==null?"—":vr.toFixed(2)+"×")+'</div>'+
       '<div>'+row("RS vs NIFTY",x.relative_strength_20d==null?"—":p(x.relative_strength_20d))+row("EMA200",x.ema200==null?"—":n(x.ema200))+row("RSI14",x.rsi14==null?"—":n(x.rsi14))+row("52W distance",x.distance_252_high_pct==null?"—":p(x.distance_252_high_pct))+'</div>'+
       '<div>'+row("F&O build",x.fo_build||"—")+row("OI change",x.oi_change_pct==null?"—":p(x.oi_change_pct))+row("History",n(h.length)+" bars")+'</div>'+
       '</div><div class="rr-lab-events"><b>Recent research events</b>'+eventBody(x.events||[])+'</div>'+
       '<div class="rr-drill-note">Historical statistics are event studies over the available file history. They do not predict future returns.</div>';
     host.querySelectorAll(".rr-event-symbol").forEach(function(q){q.onclick=function(){loadSymbol(q.getAttribute("data-symbol"));};});
     bt.dataset.history=JSON.stringify(h); runBack(h,bt.value||"52W BREAKOUT");
   }).catch(function(e){detail.innerHTML='<div class="mut">No history found for '+esc(s)+'. '+esc(e.message)+'</div>';bt.dataset.history="[]";runBack([] ,bt.value);});
 }
 if(btn)btn.addEventListener("click",function(){loadSymbol(input.value);});
 if(input)input.addEventListener("keydown",function(e){if(e.key==="Enter")loadSymbol(input.value);});
 if(bt)bt.addEventListener("change",function(){var h=[];try{h=JSON.parse(bt.dataset.history||"[]");}catch(e){}runBack(h,bt.value);});
 host.querySelectorAll(".rr-symbol").forEach(function(q){q.onclick=function(){loadSymbol(q.getAttribute("data-symbol"));};});
}

function render(d){
 var host=document.getElementById("research-radar"); if(!host)return;
 installCSS();
 window.__rr44Data=d; var f=d.features||{};
 var w=f.week52||{},br=f.breadth_history||{},ix=f.index_changes||{},ma=f.rbi_macro||{},bb=f.bulk_block||{},re=f.results||{},se=f.sector_rotation||{},rg=f.market_regime||{},dr=f.data_resilience||{},ca=f.corporate_actions||{};
 var h=f.breakout_radar||{},vs=f.volume_shock||{},dc=f.delivery_conviction||{},ad=f.accumulation_distribution||{},gap=f.gap_radar||{};
 var rs=f.relative_strength||{},sm=f.sector_matrix||{},ve=f.volatility_expansion||{},rx=f.range_expansion||{};
 var mo=f.momentum_dashboard||{},th=f.trend_health||{},cross=f.dma_cross_radar||{},dm=f.distance_map||{};
 var es=f.earnings_surprise||{},pi=f.promoter_insider||{},pl=f.pledge_watch||{},cc=f.corporate_calendar||{};
 var dv=f.dividend_radar||{},bo=f.buyback_open_offer||{},foi=f.fo_oi_change||{},op=f.option_pulse||{};
 var fm=f.futures_basis||{},fb=f.fo_buildup||{},bt=f.bulk_followthrough||{},iflow=f.institutional_flow_trend||{};
 var bm=f.breadth_momentum||{},hlb=f.high_low_breadth||{},mc=f.market_concentration||{},nl=f.nifty_leadership||{};
 var ib=f.index_bucket_breadth||{},ls=f.liquidity_stress||{},rel=f.data_reliability||{},rdd=f.data_resilience_detail||{};

 var html='<div id="rr-lab" class="rr-lab card">'+
   '<div class="sh2"><span>RESEARCH LAB</span><span class="rr-head-right"><span class="rr-badge source">FREE GITHUB / LOCAL DATA</span><span class="rr-badge fresh">LIVE SNAPSHOT</span></span></div>'+
   '<div class="rr-lab-top"><div><b>Stock drill-down + signal history</b><small>Search any NSE symbol to combine price history, Radar signals, corporate events, F&O and delivery context.</small></div><div class="rr-lab-search"><input id="rr-stock-input" type="search" placeholder="RELIANCE · HDFCBANK · TCS"><button id="rr-stock-go">RESEARCH</button></div></div>'+
   '<div id="rr-stock-detail"><div class="mut">Enter a symbol to begin.</div></div>'+
   '<div class="rr-backtest-bar"><label>Historical signal test <select id="rr-backtest"><option>52W BREAKOUT</option><option>VOLUME SHOCK</option><option>TREND > 200DMA</option><option>20D MOMENTUM</option></select></label><div id="rr-backtest-out"><div class="mut">Load a stock to calculate event-study statistics.</div></div></div>'+
   '<div class="rr-lab-source">Source: ArthaSaar <code>data/history/</code> plus current Radar snapshots. Forward-return statistics describe historical occurrences only; they are not forecasts.</div></div><div class="rr-grid">';
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
 html+=card("44","DATA RESILIENCE DETAIL",row("History files",n(rdd.history_files))+row("EMA200 coverage",p(rdd.ema200_coverage_pct))+row("Delivery coverage",n(rdd.delivery_coverage))+row("Futures coverage",n(rdd.futures_stock_coverage))+row("Coverage score",p(rdd.coverage_score_pct))+row("EOD fallback","NSE → Yahoo → last valid"),"system health");
 html+='</div><div class="rr-note"><b>44 free-data research modules.</b> NSE/public exchange snapshots remain primary; Yahoo is used only for historical backup. Modules explicitly mark unavailable calculations when the stored public snapshot lacks the required field, rather than fabricating values. Updated '+esc(d.updated||"—")+'.</div>';
 host.innerHTML=html;
 initResearchLab(d);
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
(function(){
"use strict";
/* deployment retry: single clean Vercel build */
var A="/api/data?p=",M={
indices:["indices-all.json"],mf:["mf-top.json"],futures:["futures.json"],gti:["gti.json"],
gtizones:["gti.json"],gticharts:["candles.json"],gtiai:["timesfm_forecasts.json"],
internals:["breadth.json","fii-dii.json","futures.json"],idxradar:["radar.json"],
heatmap:["indices-all.json"],screener:["brain-screener.json"],fundamentals:["screener-fundamentals.json"],
deepfund:["screener-fundamentals.json"],filings:["results.json"],news:["news.json","news-digest.json"],
events:["events.json","economy-pulse.json"],crypto:["crypto.json"],global:["world.json"],aibrain:["smart-brain.json","timesfm_forecasts.json"],
home:["indices-all.json","breadth.json","fii-dii.json","news.json"],learn:["education.json"]
};
function e(x){return String(x==null?"":x).replace(/[&<>"]/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]);})}
function n(x){return x==null||x===""?"—":typeof x==="number"?x.toLocaleString("en-IN",{maximumFractionDigits:2}):e(x)}
function p(x){var z=Number(x);return isFinite(z)?(z>0?"+":"")+z.toFixed(2)+"%":n(x)}
function c(x){var z=Number(x);return isFinite(z)?z>0?"pos":z<0?"neg":"neu":"neu"}
function get(f){return fetch(A+encodeURIComponent("data/"+f),{credentials:"same-origin",cache:"no-store"}).then(function(r){if(!r.ok)throw 0;return r.json()})}
function tbl(h,rows){return '<div class="tblwrap"><table><thead><tr>'+h.map(function(x){return"<th>"+e(x)+"</th>"}).join("")+'</tr></thead><tbody>'+rows.join("")+"</tbody></table></div>"}
function card(t,b,s){return '<div class="card as-live"><div class="sh2">LIVE · '+e(t)+'</div><div style="padding:12px 14px">'+b+(s?'<div class="live-meta">updated: '+e(s)+'</div>':"")+"</div></div>"}
function rows(d,f){
 if(f==="indices-all.json"){var L=(d.indices||[]).filter(function(x){return x.price!=null}).slice(0,18);return card("Indices",tbl(["Index","Price","Change","52W"],L.map(function(x){return"<tr><td>"+e(x.index)+"</td><td>"+n(x.price)+"</td><td class='"+c(x.change_pct)+"'>"+p(x.change_pct)+"</td><td>"+n(x.w52_pos)+"</td></tr>"})),d.updated||d.as_of)}
 if(f==="mf-top.json"){var L=(d.funds||[]).slice(0,18);return card("Mutual Funds",tbl(["Fund","Category","1Y","3Y","5Y"],L.map(function(x){return"<tr><td>"+e(x.n)+"</td><td>"+e(x.k)+"</td><td class='"+c(x.r1)+"'>"+p(x.r1)+"</td><td>"+p(x.r3)+"</td><td>"+p(x.r5)+"</td></tr>"})),d.updated)}
 if(f==="futures.json"){var q=d.pcr||{},L=(d.indices||[]).map(function(x){var z=(x.contracts||[])[0]||{};return"<tr><td>"+e(x.symbol)+"</td><td>"+n(x.underlying)+"</td><td>"+n(z.close)+"</td><td>"+n(z.oi)+"</td><td>"+n(z.oi_chg)+"</td></tr>"});return card("F&O / Options",'<div class="live-kpis"><b>PCR '+n(q.nifty_pcr_oi)+'</b><b>MAX PAIN '+n(q.nifty_max_pain)+'</b><b>EXPIRY '+e(q.nifty_expiry||"—")+"</b></div>"+tbl(["Symbol","Spot","Close","OI","OI Δ"],L),d.updated||d.date)}
 if(f==="gti.json"){var S=d.symbols||{},K=Object.keys(S).slice(0,10);return card("GTI · Zones",tbl(["Symbol","Price","Day POC","Nearest","Grid"],K.map(function(k){var x=S[k]||{};return"<tr><td>"+e(k)+"</td><td>"+n(x.price)+"</td><td>"+n(x.day_poc)+"</td><td>"+e((x.nearest||[])[0]||"—")+"</td><td>"+n(x.grid&&x.grid.level)+"</td></tr>"})),d.updated)}
 if(f==="radar.json"){var G=[["Accumulation",d.accumulation],["Hidden selling",d.hidden_selling],["Volume blast",d.volume_blast]];return G.map(function(g){return card("Radar · "+g[0],tbl(["Symbol","Close","Change","Delivery","Turnover"],(g[1]||[]).slice(0,10).map(function(x){return"<tr><td>"+e(x.sym)+"</td><td>"+n(x.close)+"</td><td class='"+c(x.chg)+"'>"+p(x.chg)+"</td><td>"+n(x.deliv)+"%</td><td>"+n(x.tover_l)+"</td></tr>"})),d.updated)}).join("")}
 if(f==="timesfm_forecasts.json"){var L=(d.forecasts||[]).slice(0,16);return card("AI Forecast",tbl(["Asset","21D Median","Low","High","Confidence"],L.map(function(x){return"<tr><td>"+e(x.name||x.symbol)+"</td><td class='"+c(x.median_chg_pct)+"'>"+p(x.median_chg_pct)+"</td><td>"+p(x.low10_chg_pct)+"</td><td>"+p(x.high90_chg_pct)+"</td><td>"+n(x.confidence)+"</td></tr>"})),d.updated)}
 if(f==="news.json"||f==="news-digest.json"){var L=(d.items||d.news||[]).slice(0,15);return card("News Reader",'<div class="live-news">'+L.map(function(x){return'<a class="live-news-row" target="_blank" rel="noopener" href="'+e(x.link||"#")+'"><b>'+e(x.title||x.headline||"Untitled")+'</b><small>'+e(x.publisher||x.source||x.topic||"")+' · '+e(x.published||x.date||"")+"</small></a>"}).join("")+"</div>",d.updated)}
 if(f==="economy-pulse.json"){var L=(d.ind||[]).slice(0,12);return card("Live Economy",tbl(["Indicator","Value","YoY","Date","Source"],L.map(function(x){return"<tr><td>"+e(x.name)+"</td><td>"+e(x.val)+"</td><td>"+e(x.yoy||"—")+"</td><td>"+e(x.date||"—")+"</td><td>"+e(x.src||"—")+"</td></tr>"})),d.updated)}
 if(f==="breadth.json"||f==="fii-dii.json"){var K=Object.keys(d).filter(function(k){return k!=="updated"}).slice(0,12);return card(f==="breadth.json"?"Market Breadth":"FII / DII",tbl(["Field","Value"],K.map(function(k){var v=d[k];return"<tr><td>"+e(k)+"</td><td>"+e(typeof v==="object"?JSON.stringify(v):v)+"</td></tr>"})),d.updated)}
 if(f==="candles.json"){return card("Chart Data","Existing candle feed is connected. Symbols: "+n(Object.keys((d||{}).syms||{}).length),d.updated)}
 var raw=Array.isArray(d)?d:(d.stocks||d.data||d.items||d.events||d.ind||d.rotation||d.movers||[]);
 if(Array.isArray(raw)&&raw.length){return card(f.replace(".json",""),tbl(["Name","Live data"],raw.slice(0,16).map(function(x){var name=x.name||x.symbol||x.sym||x.title||x.n||"—";var z=Object.keys(x).slice(0,5).map(function(k){return k+":"+x[k]}).join(" · ");return"<tr><td>"+e(name)+"</td><td>"+e(z).slice(0,320)+"</td></tr>"})),d.updated||d.date)}
 var K=Object.keys(d||{}).filter(function(k){return k!=="updated"}).slice(0,16);return card(f.replace(".json",""),tbl(["Field","Value"],K.map(function(k){var v=d[k];return"<tr><td>"+e(k)+"</td><td>"+e(typeof v==="object"?JSON.stringify(v):v).slice(0,320)+"</td></tr>"})),d.updated||d.date)
}
function inject(id,items){var host=document.querySelector("#v-"+id);if(!host)return;var old=host.querySelector(".as-live-stack");if(old)old.remove();var s=document.createElement("div");s.className="as-live-stack";s.innerHTML=items.map(function(x){return rows(x[1],x[0])}).join("");var h=host.querySelector(".fshead")||host.querySelector("h2");if(h&&h.parentNode===host)h.insertAdjacentElement("afterend",s);else host.insertBefore(s,host.firstChild)}
function refresh(id){if(!M[id]||id==="ipo")return;Promise.all(M[id].map(function(f){return get(f).then(function(d){return[f,d]})})).then(function(x){inject(id,x)}).catch(function(){})}
function route(){var id=(location.hash||"#home").slice(1).split("/")[0]||"home";refresh(id)}
var st=document.createElement("style");st.textContent=".as-live-stack{display:grid;gap:10px;margin:0 0 14px}.live-meta{margin-top:8px;color:var(--faint);font:10px var(--mono)}.live-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}.live-kpis b{border:1px solid var(--border);border-radius:9px;padding:10px;font:700 11px var(--mono)}.live-news{display:grid;gap:6px}.live-news-row{display:block;padding:9px;border:1px solid var(--border);border-radius:9px;color:var(--text);text-decoration:none;background:var(--bg2)}.live-news-row b{display:block;font-size:12px}.live-news-row small{display:block;color:var(--faint);font:9px var(--mono);margin-top:3px}@media(max-width:600px){.live-kpis{grid-template-columns:1fr}}";document.head.appendChild(st);
addEventListener("hashchange",route);addEventListener("load",route);setInterval(route,300000);
})();
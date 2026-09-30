/* ==========================================================================
   Arthasaar — Market Terminal · data layer
   Renders every view from the live files under /data (and /ipo/data).
   ========================================================================== */
(function () {
"use strict";

/* ---------- tiny helpers ---------- */
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
function num(v,dec){if(v==null||isNaN(v))return "--";var n=Number(v);return n.toLocaleString("en-IN",{minimumFractionDigits:dec||0,maximumFractionDigits:dec==null?2:dec});}
function px(v){if(v==null||isNaN(v))return "--";return Number(v).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2});}
function pct(v){if(v==null||isNaN(v))return "--";var n=Number(v);return (n>=0?"+":"")+n.toFixed(2)+"%";}
function cls(v){return Number(v)>=0?"up":"dn";}
function arw(v){return Number(v)>=0?"\u25B2":"\u25BC";}
function big(v){if(v==null||isNaN(v))return "--";v=Number(v);
  if(Math.abs(v)>=1e7)return (v/1e7).toFixed(2)+" Cr";
  if(Math.abs(v)>=1e5)return (v/1e5).toFixed(2)+" L";
  return num(v,0);}
function usd(v){if(v==null||isNaN(v))return "--";return "$"+num(v,0);}
function ago(iso){if(!iso)return "";var d=new Date(iso);if(isNaN(d))return "";
  var m=Math.round((Date.now()-d.getTime())/60000);
  if(m<1)return "just now";if(m<60)return m+" min ago";var h=Math.round(m/60);
  if(h<24)return h+" hr ago";return Math.round(h/24)+" d ago";}

/* ---------- data store ---------- */
var FILES = {
  indices:"data/indices-all.json", breadth:"data/breadth.json", fiidii:"data/fii-dii.json",
  news:"data/news.json", scrfund:"data/screener-fundamentals.json", brain:"data/brain-screener.json",
  cindex:"data/company-index.json", fund:"data/fundamentals.json", mf:"data/mf-top.json",
  filings:"data/filings.json", futures:"data/futures.json", gti:"data/gti.json",
  crypto:"data/crypto.json", global:"data/global.json", world:"data/world.json",
  events:"data/events.json", smart:"data/smart-brain.json", macro:"data/macro.json",
  scores:"data/stock-scores.json", candles:"data/candles.json", learn:"data/learn-content.json",
  education:"data/education.json", radar:"data/radar.json", results:"data/results.json",
  stress:"data/stress.json", ipo:"ipo/data/ipo-data.json"
};
var D = {};
function loadAll(){
  var keys = Object.keys(FILES);
  return Promise.all(keys.map(function(k){
    return fetch(FILES[k], {cache:"no-store"})
      .then(function(r){ return r.ok ? r.json() : null; })
      .catch(function(){ return null; });
  })).then(function(vals){ keys.forEach(function(k,i){ D[k]=vals[i]; }); });
}

/* ---------- derived lookups ---------- */
function idxList(){ return (D.indices && D.indices.indices) || []; }
function idxFind(name){
  var L=idxList(), i;
  for(i=0;i<L.length;i++) if(String(L[i].index).toUpperCase()===name) return L[i];
  for(i=0;i<L.length;i++) if(String(L[i].index).toUpperCase().indexOf(name)>-1) return L[i];
  return null;
}
function pos52(r){ if(!r||!r.year_high||!r.year_low||r.year_high===r.year_low)return null;
  return Math.round((r.price-r.year_low)/(r.year_high-r.year_low)*100); }
function brainList(){ return (D.brain && D.brain.stocks) || []; }
function sectorOf(sym){ var c=D.cindex||{}, f=(D.fund||{})[sym]; return (c[sym]&&c[sym].sector)||(f&&f.sector)||"Other"; }

/* =======================================================================
   RENDERERS — each returns the inner HTML of a <section class="view">
   ======================================================================= */

/* ---------- HOME ---------- */
function rHome(){
  var n=idxFind("NIFTY 50"), bn=idxFind("NIFTY BANK"), vix=idxFind("INDIA VIX");
  var gi=((D.global&&D.global.items)||[]).filter(function(x){return String(x.name||"").toUpperCase()==="SENSEX";})[0];
  var sx=gi?{price:gi.price,change_pct:gi.chg_pct,change:null}:idxFind("NIFTY NEXT 50");
  var kpi=function(l,r){ if(!r)return "";
    return '<div class="card kpi"><div class="lbl">'+esc(l)+'</div><div class="num">'+px(r.price)+
      '</div><div class="chg '+cls(r.change_pct)+'">'+arw(r.change_pct)+' '+pct(r.change_pct)+
      (r.change!=null?' &middot; '+num(r.change,2):'')+'</div></div>'; };
  var h='<div class="kpis">'+kpi("NIFTY 50",n)+kpi("SENSEX",sx)+kpi("NIFTY BANK",bn)+kpi("INDIA VIX",vix)+'</div>';

  /* chart + breadth */
  h+='<div class="grid2" style="margin-top:10px">';
  h+='<div class="card"><div class="sh2">'+esc(n?n.index:"NIFTY 50")+' &middot; intraday'+
     (n?' <span class="'+cls(n.change_pct)+'">'+pct(n.change_pct)+'</span>':'')+
     (n?'<span class="fr">52W '+num(n.year_low,0)+' \u2013 '+num(n.year_high,0)+'</span>':'')+'</div>'+
     '<div style="padding:10px 12px">'+sparkline("NIFTY")+'</div></div>';

  var b=D.breadth||{};
  h+='<div class="card"><div class="sh2">Market Breadth</div><div style="padding:12px 14px">';
  if(b.above_ema200_pct!=null){
    h+='<div class="breadth"><i style="width:'+Math.max(0,Math.min(100,b.above_ema200_pct))+'%"></i></div>';
    h+='<div class="mono s11" style="margin-top:8px"><b>'+num(b.above_ema200_pct,1)+'%</b> of '+num(b.stocks,0)+' stocks above 200-EMA</div>';
    h+='<div class="zrow"><span>RSI &gt; 60</span><b class="up">'+num(b.rsi_above_60,0)+'</b></div>';
    h+='<div class="zrow"><span>RSI &lt; 40</span><b class="dn">'+num(b.rsi_below_40,0)+'</b></div>';
    h+='<div class="zrow"><span>Near 52W high</span><b class="up">'+num(b.near_52w_high,0)+'</b></div>';
    h+='<div class="zrow"><span>Vol spike &gt;2&times;</span><b>'+num(b.volume_spike_2x,0)+'</b></div>';
  } else h+='<div class="mono s11">Breadth data unavailable.</div>';
  h+='</div></div></div>';

  /* FII / DII */
  var fd=(D.fiidii&&D.fiidii.categories)||null;
  h+='<div class="card" style="margin-top:10px"><div class="sh2">FII / DII'+
     (D.fiidii&&D.fiidii.date?' <span class="fr">'+esc(D.fiidii.date)+'</span>':'')+'</div><div style="padding:6px 14px 10px">';
  if(fd){ Object.keys(fd).forEach(function(k){
    var c=fd[k];
    h+='<div class="zrow"><span>'+esc(k)+'</span><span><b class="'+cls(c.net_cr)+'">'+num(c.net_cr,2)+
       '</b> <small class="mono">net &#8377;cr</small></span></div>';
  });} else h+='<div class="mono s11" style="padding:8px 0">FII/DII data unavailable.</div>';
  h+='</div></div>';

  /* movers */
  var B=brainList().filter(function(s){return s.change_pct!=null;});
  var topG=B.slice().sort(function(a,b){return b.change_pct-a.change_pct;})[0];
  var topL=B.slice().sort(function(a,b){return a.change_pct-b.change_pct;})[0];
  var hi=B.filter(function(s){return s.from_52w_high_pct!=null&&s.from_52w_high_pct>-2;}).length;
  h+='<div class="sect">MARKET MODULES</div><div class="minirow">';
  h+= topG?'<div class="card kpi"><div class="lbl">TOP GAINER</div><div class="num up">'+esc(topG.symbol)+'</div><div class="chg up">'+pct(topG.change_pct)+'</div></div>':'';
  h+= topL?'<div class="card kpi"><div class="lbl">TOP LOSER</div><div class="num dn">'+esc(topL.symbol)+'</div><div class="chg dn">'+pct(topL.change_pct)+'</div></div>':'';
  h+='<div class="card kpi"><div class="lbl">NEAR 52W HIGH</div><div class="num">'+num(hi,0)+'</div><div class="chg">stocks</div></div>';
  h+='<div class="card kpi"><div class="lbl">UNIVERSE</div><div class="num">'+num(B.length,0)+'</div><div class="chg">tracked</div></div>';
  h+='</div>';

  /* IPO */
  var ip=(D.ipo&&D.ipo.ipos)||[];
  var open=ip.filter(function(x){return /open|live/i.test(x.status||"")||/^\d{2}\/\d{2}/.test(x.open||"");}).slice(0,2);
  h+='<div class="sect">IPO TERMINAL</div><div class="grid3"><div class="card"><div class="sh2">OPEN <span class="b buy">LIVE</span></div>';
  if(open.length) open.forEach(function(x){h+='<div class="ni"><b>'+esc(x.name)+'</b><small>'+esc(x.price||"")+(x.sub?" &middot; "+esc(x.sub)+" sub":"")+(x.gmp?" &middot; GMP "+esc(x.gmp):"")+'</small></div>';});
  else h+='<div class="ni"><b>No open issues</b><small>check IPO terminal</small></div>';
  h+='</div>';
  var upc=ip.filter(function(x){return /upcoming|announced/i.test(x.status||"");}).slice(0,2);
  h+='<div class="card"><div class="sh2">UPCOMING</div>';
  if(upc.length) upc.forEach(function(x){h+='<div class="ni"><b>'+esc(x.name)+'</b><small>'+esc(x.open||x.price||"")+'</small></div>';});
  else h+='<div class="ni"><b>See IPO section</b><small>'+num(ip.length,0)+' issues tracked</small></div>';
  h+='</div>';
  var lis=((D.ipo&&D.ipo.listed)||[]).slice(0,2);
  h+='<div class="card"><div class="sh2">CLOSED / LISTED</div>';
  lis.forEach(function(x){h+='<div class="ni"><b>'+esc(x.name)+'</b><small>'+esc(x.listing||x.price||"")+'</small></div>';});
  h+='</div></div>';

  /* news */
  h+='<div class="sect">NEWS</div><div class="grid3">'+newsCards(3)+'</div>';
  return h;
}

function sparkline(sym){
  var c=D.candles&&D.candles.syms&&D.candles.syms[sym];
  if(!c)return '<div class="mono s11" style="color:var(--dim);padding:20px 0">chart data unavailable</div>';
  var ser=(c["1h"]&&c["1h"].c)||(c["15m"]&&c["15m"].c)||(c["5m"]&&c["5m"].c)||(c["1m"]&&c["1m"].c);
  if(!ser||ser.length<2)return '<div class="mono s11" style="color:var(--dim);padding:20px 0">chart data unavailable</div>';
  ser=ser.slice(-80);
  var lo=Math.min.apply(null,ser), hi=Math.max.apply(null,ser), rng=(hi-lo)||1;
  var W=800,H=170, pts=ser.map(function(v,i){return [(i/(ser.length-1))*W, H-((v-lo)/rng)*(H-24)-12];});
  var d="M"+pts.map(function(p){return p[0].toFixed(1)+" "+p[1].toFixed(1);}).join("L");
  return '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" style="width:100%;height:160px">'+
    '<path d="M0 30H800M0 85H800M0 140H800" class="gl"/>'+
    '<path d="'+d+'V'+H+'H0Z" fill="var(--accent)" opacity=".1"/>'+
    '<path d="'+d+'" fill="none" stroke="var(--accent)" stroke-width="2.5"/></svg>';
}

function newsCards(n){
  var items=(D.news&&D.news.items)||[];
  var topics={};
  items.forEach(function(it){var t=it.topic||"News";(topics[t]=topics[t]||[]).push(it);});
  var names=Object.keys(topics).slice(0,n);
  if(!names.length)return '<div class="card"><div class="ni"><b>No news loaded</b></div></div>';
  return names.map(function(t){
    var rows=topics[t].slice(0,3).map(function(it){
      return '<div class="ni"><b>'+esc(it.title)+'</b><small>'+esc(t)+' &middot; '+esc(it.publisher||ago(it.published))+'</small></div>';
    }).join("");
    return '<div class="card"><div class="sh2">'+esc(t)+'</div>'+rows+'</div>';
  }).join("");
}

/* ---------- INDICES ---------- */
function rIndices(){
  var L=idxList();
  var rows=L.map(function(r){var p=pos52(r);
    return '<tr><td>'+esc(r.index)+'</td><td>'+px(r.price)+'</td><td><span class="'+cls(r.change_pct)+'">'+pct(r.change_pct)+
      '</span></td><td>'+(p==null?"\u2014":p+"%")+'</td><td>'+(r.pe||"\u2014")+'</td><td>'+(r.pb||"\u2014")+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Indices \u2014 '+num(L.length,0)+' tracked</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<button class="radarbtn" data-go="idxradar"><span class="t"><b>INDICES RADAR</b><small>breadth &amp; movers</small></span><span class="arw">\u2192</span></button>'+
    '<div class="srow"><input id="qIdx" type="search" placeholder="Search index name\u2026"></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Index</th><th>Price</th><th>Chg%</th><th>52w Pos</th><th>PE</th><th>PB</th></tr></thead><tbody id="idxBody">'+
    rows+'</tbody></table></div>';
}

/* ---------- INDICES RADAR ---------- */
function rIdxRadar(){
  var L=idxList().filter(function(r){return r.change_pct!=null;});
  var green=L.filter(function(r){return r.change_pct>0;}).length, red=L.filter(function(r){return r.change_pct<0;}).length;
  var flat=L.length-green-red, gp=L.length?green/L.length*100:0;
  var sorted=L.slice().sort(function(a,b){return b.change_pct-a.change_pct;});
  var chips=function(arr,cl){return '<div class="rchips">'+arr.map(function(r){
    return '<span class="rchip '+cl+'"><b>'+esc(r.index)+'</b> '+pct(r.change_pct)+'</span>';}).join("")+'</div>';};
  var hi=idxFind("NIFTY 50"), hb=idxFind("NIFTY BANK"), hn=idxFind("NIFTY NEXT 50");
  var card=function(r){if(!r)return "";return '<div class="ridx"><div class="lbl">'+esc(r.index)+'</div><div class="val">'+px(r.price)+'</div><div class="chg '+cls(r.change_pct)+'">'+pct(r.change_pct)+'</div></div>';};
  return '<div class="fshead"><h2>Indices Radar</h2><button class="xbtn" data-go="indices">\u2715 CLOSE</button></div>'+
    '<div class="idxcards">'+card(hi)+card(hb)+card(hn)+'</div>'+
    '<div class="rbreadth"><div class="blab">'+green+'/'+L.length+' GREEN</div>'+
    '<div class="rbar"><i style="width:'+gp.toFixed(1)+'%"></i><em></em></div>'+
    '<div class="rcap">'+red+' red &middot; '+flat+' flat'+(D.indices&&D.indices.updated?' &middot; '+ago(D.indices.updated):'')+'</div></div>'+
    '<div class="sect">TOP GAINERS</div>'+chips(sorted.slice(0,5),"g")+
    '<div class="sect">TOP LOSERS</div>'+chips(sorted.slice(-5).reverse(),"r")+
    '<p class="rnote">Radar: breadth shows how the market is from the inside \u2014 all green = healthy, only Nifty green = weak inside.</p>';
}

/* ---------- SECTOR MAP (heatmap) ---------- */
function rHeatmap(){
  var B=brainList().filter(function(s){return s.change_pct!=null;});
  var by={};
  B.forEach(function(s){var sec=sectorOf(s.symbol);var g=by[sec]=by[sec]||{n:0,sum:0,up:0,stocks:[]};
    g.n++; g.sum+=s.change_pct; if(s.change_pct>0)g.up++; g.stocks.push(s);});
  var secs=Object.keys(by).map(function(k){var g=by[k];return {sector:k,avg:g.sum/g.n,n:g.n,up:g.up,stocks:g.stocks};})
    .sort(function(a,b){return b.avg-a.avg;});
  var top=secs[0]||{}, bottom=secs[secs.length-1]||{};
  var cell=function(x){
    var mag=Math.min(1,Math.abs(x.avg)/2.5), bg=x.avg>=0?'rgba(31,122,77,':"rgba(179,50,60,";
    return '<div class="card" style="padding:10px 12px;background:'+bg+(0.10+mag*0.45).toFixed(2)+')">'+
      '<div class="lbl" style="color:var(--text)">'+esc(x.sector)+'</div>'+
      '<div class="num" style="font-size:15px;color:var(--text)">'+pct(x.avg)+'</div>'+
      '<div class="chg" style="color:var(--text);opacity:.75">'+x.up+'/'+x.n+' up</div></div>';
  };
  var h='<div class="fshead"><h2>Sector Map \u2014 today</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  h+='<div class="smradar"><div class="smpill"><span class="t"><b>SECTOR MAP</b><small>rotation by sector</small></span></div></div>';
  h+='<div class="minirow">'+
     '<div class="card kpi"><div class="lbl">STRONGEST</div><div class="num" style="font-size:14px">'+esc(top.sector||"--")+'</div><div class="chg up">'+pct(top.avg)+'</div></div>'+
     '<div class="card kpi"><div class="lbl">WEAKEST</div><div class="num" style="font-size:14px">'+esc(bottom.sector||"--")+'</div><div class="chg dn">'+pct(bottom.avg)+'</div></div>'+
     '<div class="card kpi"><div class="lbl">SECTORS</div><div class="num">'+num(secs.length,0)+'</div><div class="chg">tracked</div></div>'+
     '<div class="card kpi"><div class="lbl">STOCKS</div><div class="num">'+num(B.length,0)+'</div><div class="chg">mapped</div></div></div>';
  h+='<div class="sect">ALL SECTORS</div><div class="grid3" style="gap:8px">'+secs.map(cell).join("")+'</div>';
  return h;
}

/* ---------- SCREENER ---------- */
function rScreener(){
  var B=brainList().slice().sort(function(a,b){return (b.change_pct||-99)-(a.change_pct||-99);});
  var rows=B.slice(0,400).map(function(s){
    return '<tr><td>'+esc(s.symbol)+'</td><td>'+px(s.price)+'</td><td><span class="'+cls(s.change_pct)+'">'+pct(s.change_pct)+'</span></td>'+
      '<td>'+(s.rsi14==null?"\u2014":num(s.rsi14,1))+'</td><td>'+(s.above_ema200?'<span class="b buy">above</span>':'<span class="b dn">below</span>')+'</td>'+
      '<td>'+(s.vol_vs_avg20==null?"\u2014":num(s.vol_vs_avg20,2)+"\u00d7")+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Screener \u2014 '+num(B.length,0)+' stocks</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="srow"><input id="qScr" type="search" placeholder="Search symbol\u2026"></div>'+
    '<div class="chips" id="ftIndex"><span class="fch on">All</span><span class="fch">Above 200-EMA</span><span class="fch">RSI &gt; 60</span><span class="fch">Volume shock</span></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Price</th><th>Chg%</th><th>RSI14</th><th>200-EMA</th><th>Vol</th></tr></thead><tbody id="scrBody">'+
    rows+'</tbody></table></div>'+
    '<p class="rnote">Showing top 400 of '+num(B.length,0)+' by change. Use the search box to filter.</p>';
}

/* ---------- COMPANY ---------- */
function companyCard(sym){
  var c=(D.cindex||{})[sym]||{}, f=(D.fund||{})[sym]||{}, s=(D.scrfund&&D.scrfund.stocks&&D.scrfund.stocks[sym])||{};
  var b=brainList().filter(function(x){return x.symbol===sym;})[0];
  var price=(b&&b.price)||s["Current Price"]||null, chg=(b&&b.change_pct);
  var row=function(k,v){return '<div class="zrow"><span>'+k+'</span><b>'+v+'</b></div>';};
  var h='<div class="card" style="padding:16px">';
  h+='<div class="lbl">'+esc(sym)+'</div><h2 style="margin:6px 0 10px;border:none;padding:0">'+esc(c.name||sym)+'</h2>';
  h+='<div class="num" style="font-size:26px">'+(price==null?"--":px(price))+(chg!=null?' <span class="chg '+cls(chg)+'">'+pct(chg)+'</span>':'')+'</div>';
  h+='<div class="mono s11" style="color:var(--dim);margin:6px 0 12px">'+esc(c.sector||f.sector||"\u2014")+' &middot; '+esc(c.industry||f.industry||"\u2014")+'</div>';
  h+=row("Market Cap", s["Market Cap"]!=null?big(s["Market Cap"]*1e7):(f.marketCap!=null?big(f.marketCap):"--"));
  h+=row("Stock P/E", (s["Stock P/E"]!=null?s["Stock P/E"]:(f.trailingPE!=null?num(f.trailingPE,1):"\u2014")));
  h+=row("Book Value", s["Book Value"]!=null?num(s["Book Value"],1):"\u2014");
  h+=row("ROE %", (s["ROE"]!=null?s["ROE"]:(f.returnOnEquity!=null?(f.returnOnEquity*100).toFixed(1):"\u2014")));
  h+=row("ROCE %", s["ROCE"]!=null?s["ROCE"]:"\u2014");
  h+=row("Debt / Equity", f.debtToEquity!=null?num(f.debtToEquity,1):"\u2014");
  h+=row("Dividend Yield", (s["Dividend Yield"]!=null?s["Dividend Yield"]:(f.dividendYield!=null?num(f.dividendYield,2):"\u2014")));
  h+=row("52W High / Low", (s["high_52w"]!=null?num(s["high_52w"],0)+" / "+num(s["low_52w"],0):"\u2014"));
  h+=row("Promoter / FII / DII", (s.promoters_pct!=null?num(s.promoters_pct,1)+"% / "+num(s.fii_pct,1)+"% / "+num(s.dii_pct,1)+"%":"\u2014"));
  h+=row("Sales YoY", s["Sales_yoy"]!=null?pct(s["Sales_yoy"]):"\u2014");
  h+=row("Net Profit YoY", s["Net Profit_yoy"]!=null?pct(s["Net Profit_yoy"]):"\u2014");
  h+='</div>';
  return h;
}
function rCompany(){
  var list=Object.keys(D.cindex||{}).filter(function(k){return k[0]!=="_";}).sort();
  var first=list.indexOf("RELIANCE")>-1?"RELIANCE":(list[0]||"");
  var h='<div class="fshead"><h2>Company Card</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  h+='<div class="srow"><input id="qCo" type="search" placeholder="Search symbol (e.g. RELIANCE, TCS)\u2026" value=""></div>';
  h+='<div class="chips" id="coQuick">'+["RELIANCE","TCS","HDFCBANK","INFY","SBIN","ITC"].map(function(s){return '<span class="fch" data-co="'+s+'">'+s+'</span>';}).join("")+'</div>';
  h+='<div id="coCard">'+companyCard(first)+'</div>';
  h+='<p class="rnote">'+num(list.length,0)+' symbols available. Type a symbol or tap a chip.</p>';
  return h;
}

/* ---------- FUNDAMENTALS ---------- */
function rFundamentals(){
  var S=(D.scrfund&&D.scrfund.stocks)||{};
  var rows=Object.keys(S).map(function(k){var s=S[k];return {k:k,s:s};})
    .filter(function(x){return x.s["Market Cap"]!=null;})
    .sort(function(a,b){return b.s["Market Cap"]-a.s["Market Cap"];}).slice(0,300);
  var tr=rows.map(function(x){var s=x.s;
    return '<tr><td>'+esc(x.k)+'</td><td>'+(s["Stock P/E"]!=null?num(s["Stock P/E"],1):"\u2014")+'</td>'+
      '<td>'+(s["ROE"]!=null?num(s["ROE"],1):"\u2014")+'</td><td>'+(s["ROCE"]!=null?num(s["ROCE"],1):"\u2014")+'</td>'+
      '<td>'+big(s["Market Cap"]*1e7)+'</td><td>'+(s["Dividend Yield"]!=null?num(s["Dividend Yield"],2):"\u2014")+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Fundamentals</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="srow"><input id="qFun" type="search" placeholder="Search symbol\u2026"></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>P/E</th><th>ROE%</th><th>ROCE%</th><th>M.Cap</th><th>Div Yld</th></tr></thead><tbody id="funBody">'+
    tr+'</tbody></table></div>'+
    '<p class="rnote">Source: screener-fundamentals.json &middot; '+num(Object.keys(S).length,0)+' companies.</p>';
}

/* ---------- MF ---------- */
function rMf(){
  var mf=D.mf||{}, funds=mf.funds||[];
  var nifty=mf.nifty||{};
  var rows=funds.slice().sort(function(a,b){return (b.r1||-99)-(a.r1||-99);}).slice(0,300).map(function(f){
    return '<tr><td>'+esc(f.n)+'</td><td>'+esc(f.k||"")+'</td><td><span class="'+cls(f.r1)+'">'+(f.r1==null?"\u2014":pct(f.r1))+'</span></td>'+
      '<td>'+(f.r3==null?"\u2014":pct(f.r3))+'</td><td>'+(f.r5==null?"\u2014":pct(f.r5))+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>MF Tracker</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="minirow">'+
    '<div class="card kpi"><div class="lbl">NIFTY 1Y</div><div class="num '+cls(nifty.r1)+'" style="font-size:18px">'+pct(nifty.r1)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">NIFTY 3Y</div><div class="num '+cls(nifty.r3)+'" style="font-size:18px">'+pct(nifty.r3)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">NIFTY 5Y</div><div class="num '+cls(nifty.r5)+'" style="font-size:18px">'+pct(nifty.r5)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">FUNDS</div><div class="num" style="font-size:18px">'+num(funds.length,0)+'</div></div></div>'+
    '<div class="srow"><input id="qMf" type="search" placeholder="Search fund\u2026"></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Fund</th><th>Category</th><th>1Y</th><th>3Y</th><th>5Y</th></tr></thead><tbody id="mfBody">'+
    rows+'</tbody></table></div>';
}

/* ---------- DEEP FUND (stock scores) ---------- */
function rDeepFund(){
  var sc=(D.scores&&D.scores.top)||[];
  var rows=sc.slice(0,300).map(function(x){
    return '<tr><td>'+esc(x.sym)+'</td><td>'+num(x.t,0)+'</td><td>'+num(x.f,0)+'</td><td><b>'+num(x.total,0)+'</b></td>'+
      '<td class="s11">'+esc((x.r||[]).join(" \u00b7 "))+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Deep Fund \u2014 composite scores</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="srow"><input id="qDf" type="search" placeholder="Search symbol\u2026"></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Tech</th><th>Fund</th><th>Total</th><th>Flags</th></tr></thead><tbody id="dfBody">'+
    rows+'</tbody></table></div>'+
    '<p class="rnote">Scale: '+esc((D.scores&&D.scores.scale)||"")+'</p>';
}

/* ---------- FILINGS ---------- */
function rFilings(){
  var F=(D.filings&&D.filings.filings)||[];
  var rows=F.slice(0,300).map(function(f){
    return '<tr><td>'+esc(f.symbol)+'</td><td>'+esc(f.category||"")+'</td><td class="s11">'+esc(f.nse_desc||f.subject||"").slice(0,90)+'</td><td>'+esc(f.date||"")+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Filings \u2014 last '+(D.filings?D.filings.window_days:7)+' days</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="srow"><input id="qFil" type="search" placeholder="Search symbol\u2026"></div>'+
    '<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Type</th><th>Subject</th><th>Date</th></tr></thead><tbody id="filBody">'+
    rows+'</tbody></table></div>'+
    '<p class="rnote">'+num(D.filings?D.filings.tier1_filings:0,0)+' tier-1 filings &middot; '+num(F.length,0)+' shown.</p>';
}

/* ---------- FUTURES ---------- */
function rFutures(){
  var fu=D.futures||{}, pcr=fu.pcr||{};
  var h='<div class="fshead"><h2>Futures &amp; Options</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  h+='<div class="minirow">'+
    '<div class="card kpi"><div class="lbl">NIFTY PCR (OI)</div><div class="num" style="font-size:18px">'+num(pcr.nifty_pcr_oi,3)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">NIFTY PCR (VOL)</div><div class="num" style="font-size:18px">'+num(pcr.nifty_pcr_vol,3)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">MAX PAIN</div><div class="num" style="font-size:18px">'+num(pcr.nifty_max_pain,0)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">EXPIRY</div><div class="num" style="font-size:15px">'+esc(pcr.nifty_expiry||"\u2014")+'</div></div></div>';
  var idx=(fu.indices||[]);
  h+='<div class="sect">INDEX FUTURES</div><div class="grid2">'+idx.slice(0,4).map(function(x){
    var cs=(x.contracts||[]).map(function(c){
      return '<div class="zrow"><span>'+esc(c.expiry)+'</span><span>'+px(c.close)+' <small class="mono">OI '+num(c.oi,0)+'</small></span></div>';}).join("");
    return '<div class="card"><div class="sh2">'+esc(x.symbol)+' <span class="fr">spot '+px(x.underlying)+'</span></div><div style="padding:6px 14px 10px">'+cs+'</div></div>';
  }).join("")+'</div>';
  var st=(fu.stocks||[]).slice(0,60);
  h+='<div class="sect">STOCK FUTURES</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Fut</th><th>Spot</th><th>Basis%</th><th>OI</th></tr></thead><tbody>'+
    st.map(function(s){return '<tr><td>'+esc(s.symbol)+'</td><td>'+px(s.close)+'</td><td>'+px(s.underlying)+'</td><td><span class="'+cls(s.basis_pct)+'">'+num(s.basis_pct,2)+'%</span></td><td>'+num(s.oi,0)+'</td></tr>';}).join("")+
    '</tbody></table></div>';
  return h;
}

/* ---------- GTI (zones / charts / AI) ---------- */
function gtiSym(sym){
  var g=D.gti&&D.gti.symbols&&D.gti.symbols[sym];
  if(!g)return '<div class="card" style="padding:14px"><div class="mono s11">No GTI data for '+esc(sym)+'.</div></div>';
  var z=g.day_zones||{}, wz=g.week_zones||{};
  var row=function(k,v){return '<div class="zrow"><span>'+esc(k)+'</span><b>'+v+'</b></div>';};
  var h='<div class="card" style="padding:14px"><div class="sh2">'+esc(sym)+' <span class="fr">price '+px(g.price)+'</span></div>';
  h+=row("Day open",px(g.day_open)); h+=row("Day POC",px(g.day_poc));
  Object.keys(z).slice(0,6).forEach(function(k){h+=row(k,px(z[k]));});
  h+=row("Week open",px(g.week_open)); h+=row("Week POC",px(g.week_poc));
  if(g.nearest&&g.nearest.length)h+=row("Nearest zones",esc(g.nearest.join(", ")));
  if(g.compression)h+=row("Compression",esc(typeof g.compression==="object"?JSON.stringify(g.compression):g.compression));
  h+='</div>';
  return h;
}
function rGti(){
  var syms=Object.keys((D.gti&&D.gti.symbols)||{});
  var pick=["NIFTY 50","BANKNIFTY","RELIANCE","HDFCBANK","INFY","TCS"].filter(function(s){return syms.indexOf(s)>-1;});
  if(!pick.length)pick=syms.slice(0,3);
  return '<div class="fshead"><h2>GTI \u2014 Gamma / Zones</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="chips">'+pick.map(function(s){return '<span class="fch'+(s===pick[0]?" on":"")+'" data-gti="'+s+'">'+esc(s)+'</span>';}).join("")+'</div>'+
    '<div id="gtiBox">'+gtiSym(pick[0])+'</div>'+
    '<p class="rnote">'+num(syms.length,0)+' symbols with GTI zone data.</p>';
}
function rGtiCharts(){
  var syms=Object.keys((D.gti&&D.gti.symbols)||{});
  var s=syms.indexOf("NIFTY 50")>-1?"NIFTY 50":syms[0];
  return '<div class="fshead"><h2>Charts</h2><button class="xbtn" data-go="gti">\u2715 CLOSE</button></div>'+
    '<div class="card" style="padding:10px 12px">'+sparkline("NIFTY")+'</div>'+
    (s?'<div class="sect">LEVELS</div>'+gtiSym(s):'');
}
function rGtiZones(){
  return '<div class="fshead"><h2>Zones</h2><button class="xbtn" data-go="gti">\u2715 CLOSE</button></div>'+rGti();
}
function rGtiAi(){
  var sm=D.smart||{};
  var pts=(sm.guess&&sm.guess.points)||[];
  return '<div class="fshead"><h2>AI Brain \u2014 read</h2><button class="xbtn" data-go="aibrain">\u2715 CLOSE</button></div>'+
    '<div class="card" style="padding:14px"><div class="sh2">Verdict'+(sm.guess?' <span class="fr">score '+sm.guess.score+'/100</span>':'')+'</div>'+
    '<div class="num" style="font-size:16px">'+esc((sm.guess&&sm.guess.verdict)||"\u2014")+'</div>'+
    '<ul class="s11" style="margin:10px 0 0 16px">'+pts.map(function(p){return '<li>'+esc(p)+'</li>';}).join("")+'</ul></div>';
}

/* ---------- IPO ---------- */
function rIpo(){
  var ip=(D.ipo&&D.ipo.ipos)||[], lis=(D.ipo&&D.ipo.listed)||[];
  var tr=function(arr,cols){return arr.slice(0,80).map(function(x){
    return '<tr><td>'+esc(x.name)+'</td><td>'+esc(x.type||"")+'</td><td>'+esc(x.price||"")+'</td><td>'+esc(x.sub||x.size||"")+'</td><td>'+esc(x.open||x.listing||"")+'</td></tr>';}).join("");};
  return '<div class="fshead"><h2>IPO Terminal</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="minirow">'+
    '<div class="card kpi"><div class="lbl">TRACKED</div><div class="num" style="font-size:18px">'+num(ip.length,0)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">LISTED</div><div class="num" style="font-size:18px">'+num(lis.length,0)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">DOCUMENTS</div><div class="num" style="font-size:18px">'+num(((D.ipo&&D.ipo.documents)||[]).length,0)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">NEWS</div><div class="num" style="font-size:18px">'+num(((D.ipo&&D.ipo.news)||[]).length,0)+'</div></div></div>'+
    '<div class="sect">ISSUES</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Name</th><th>Type</th><th>Price</th><th>Sub / Size</th><th>Open</th></tr></thead><tbody>'+
    tr(ip)+'</tbody></table></div>'+
    '<div class="sect">LISTED</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Name</th><th>Type</th><th>Price</th><th>Sub / Size</th><th>Listing</th></tr></thead><tbody>'+
    tr(lis)+'</tbody></table></div>';
}

/* ---------- AI BRAIN ---------- */
function rAiBrain(){
  var sm=D.smart||{};
  var list=function(arr,cl){return (arr||[]).slice(0,8).map(function(x){
    return '<div class="zrow"><span>'+esc(x.symbol||x.name)+'</span><span><b class="'+cl+'">'+(x.chg!=null?pct(x.chg):"")+'</b> <small class="mono">'+esc(x.why||"")+'</small></span></div>';}).join("");};
  return '<div class="fshead"><h2>AI Brain</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="card" style="padding:14px"><div class="sh2">Market mood</div>'+
    '<div class="num" style="font-size:20px">'+esc((sm.guess&&sm.guess.verdict)||"\u2014")+'</div>'+
    '<div class="chg">median move '+pct(sm.market_med)+'</div>'+
    '<ul class="s11" style="margin:10px 0 0 16px">'+(((sm.guess&&sm.guess.points)||[]).map(function(p){return '<li>'+esc(p)+'</li>';}).join(""))+'</ul></div>'+
    '<div class="sect">BULLISH</div><div class="card" style="padding:4px 14px">'+list(sm.bull,"up")+'</div>'+
    '<div class="sect">BEARISH</div><div class="card" style="padding:4px 14px">'+list(sm.bear,"dn")+'</div>'+
    '<p class="rnote">'+esc(sm.disclaimer||"")+'</p>';
}

/* ---------- INTERNALS ---------- */
function rInternals(){
  var b=D.breadth||{}, m=D.macro||{}, st=D.stress||{};
  var row=function(k,v,c){return '<div class="zrow"><span>'+esc(k)+'</span><b class="'+(c||"")+'">'+v+'</b></div>';};
  return '<div class="fshead"><h2>Internals</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="card" style="padding:14px"><div class="sh2">Breadth</div>'+
    row("Stocks scanned",num(b.stocks,0))+row("Above 200-EMA",num(b.above_ema200_pct,1)+"%","up")+
    row("RSI &gt; 60",num(b.rsi_above_60,0))+row("RSI &lt; 40",num(b.rsi_below_40,0),"dn")+
    row("Up 3+ days",num(b.up_3plus_days,0),"up")+row("Down 3+ days",num(b.down_3plus_days,0),"dn")+
    row("Vol spike &gt;2&times;",num(b.volume_spike_2x,0))+'</div>'+
    '<div class="sect">MACRO</div><div class="card" style="padding:14px">'+
    row("Score",num(m.score,0))+row("Verdict",esc(m.verdict||"\u2014"))+
    row("FII sell streak",num(m.streak_fii_sell_days,0)+" days")+'</div>'+
    (st.score!=null?'<div class="sect">STRESS</div><div class="card" style="padding:14px">'+
    row("Stress score",num(st.score,0))+row("Band",esc(st.band||"\u2014"))+
    (st.nifty?row("Nifty vs DMA",px(st.nifty.c)+" / "+px(st.nifty.dma)):"")+'</div>':'');
}

/* ---------- CRYPTO ---------- */
function rCrypto(){
  var c=D.crypto||{}, g=c.global||{}, fg=c.fear_greed||{}, top=c.top||[];
  var tr=top.slice(0,100).map(function(x){
    return '<tr><td>'+x.rank+'</td><td>'+esc(x.symbol)+'</td><td>'+esc(x.name)+'</td><td>'+usd(x.price_usd)+'</td>'+
      '<td><span class="'+cls(x.chg_24h_pct)+'">'+pct(x.chg_24h_pct)+'</span></td><td>'+(x.chg_7d_pct==null?"\u2014":pct(x.chg_7d_pct))+'</td>'+
      '<td>'+usd(x.market_cap)+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Crypto</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="minirow">'+
    '<div class="card kpi"><div class="lbl">MARKET CAP</div><div class="num" style="font-size:16px">'+usd(g.total_market_cap_usd)+'</div><div class="chg '+cls(g.mcap_chg_24h_pct)+'">'+pct(g.mcap_chg_24h_pct)+'</div></div>'+
    '<div class="card kpi"><div class="lbl">BTC DOM</div><div class="num" style="font-size:16px">'+num(g.btc_dominance,1)+'%</div></div>'+
    '<div class="card kpi"><div class="lbl">ETH DOM</div><div class="num" style="font-size:16px">'+num(g.eth_dominance,1)+'%</div></div>'+
    '<div class="card kpi"><div class="lbl">FEAR / GREED</div><div class="num" style="font-size:16px">'+num(fg.value,0)+'</div><div class="chg">'+esc(fg.label||"")+'</div></div></div>'+
    '<div class="sect">TOP 100</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>#</th><th>Sym</th><th>Name</th><th>Price</th><th>24h</th><th>7d</th><th>M.Cap</th></tr></thead><tbody>'+
    tr+'</tbody></table></div>';
}

/* ---------- GLOBAL ---------- */
function rGlobal(){
  var g=(D.global&&D.global.items)||[], w=D.world||{};
  var tr=g.slice(0,120).map(function(x){
    return '<tr><td>'+esc(x.name)+'</td><td>'+esc(x.symbol||"")+'</td><td>'+px(x.price)+'</td>'+
      '<td><span class="'+cls(x.chg_pct)+'">'+pct(x.chg_pct)+'</span></td><td>'+(x.low_52w!=null?num(x.low_52w,2):"\u2014")+'</td><td>'+(x.high_52w!=null?num(x.high_52w,2):"\u2014")+'</td></tr>';}).join("");
  var wtr=(w.idx||[]).slice(0,30).map(function(x){
    return '<tr><td>'+esc(x.n)+'</td><td>'+px(x.c)+'</td><td><span class="'+cls(x.d1)+'">'+pct(x.d1)+'</span></td><td>'+(x.m1==null?"\u2014":pct(x.m1))+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Global Markets</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="sect">WORLD INDICES</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Index</th><th>Last</th><th>1D</th><th>1M</th></tr></thead><tbody>'+
    wtr+'</tbody></table></div>'+
    '<div class="sect">COMMODITIES &amp; MORE</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Name</th><th>Sym</th><th>Price</th><th>Chg%</th><th>52w L</th><th>52w H</th></tr></thead><tbody>'+
    tr+'</tbody></table></div>';
}

/* ---------- NEWS ---------- */
function rNews(){
  var items=(D.news&&D.news.items)||[];
  var topics={}; items.forEach(function(it){var t=it.topic||"News";(topics[t]=topics[t]||[]).push(it);});
  var names=Object.keys(topics);
  var h='<div class="fshead"><h2>News \u2014 India market</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  h+='<div class="chips">'+names.map(function(t,i){return '<span class="fch'+(i===0?" on":"")+'" data-nt="'+esc(t)+'">'+esc(t)+'</span>';}).join("")+'</div>';
  h+='<div id="newsBox">'+names.map(function(t){
    return '<div class="card" data-ntp="'+esc(t)+'" style="margin-bottom:10px"><div class="sh2">'+esc(t)+'</div>'+
      topics[t].slice(0,20).map(function(it){
        var link=it.link?'<a href="'+esc(it.link)+'" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">':'<span>';
        var end=it.link?'</a>':'</span>';
        return '<div class="ni">'+link+'<b>'+esc(it.title)+'</b>'+end+'<small>'+esc(it.publisher||"")+' &middot; '+esc(ago(it.published))+'</small></div>';
      }).join("")+'</div>';}).join("")+'</div>';
  return h;
}

/* ---------- EVENTS ---------- */
function rEvents(){
  var e=D.events||{}, kd=e.key_dates||[], wk=e.week||[], er=e.earnings||[];
  var tr=(kd.length?kd:wk).slice(0,60).map(function(x){
    return '<tr><td>'+esc(x.title||"")+'</td><td>'+esc(x.country||"")+'</td><td>'+esc(x.date||x.date_ist||"")+'</td><td>'+esc(x.impact||x.time_ist||"")+'</td></tr>';}).join("");
  var ertr=er.slice(0,60).map(function(x){return '<tr><td>'+esc(x.symbol||x.ticker||"")+'</td><td>'+esc(x.country||"")+'</td><td>'+esc(x.date||"")+'</td></tr>';}).join("");
  return '<div class="fshead"><h2>Events</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>'+
    '<div class="sect">KEY DATES</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Event</th><th>Country</th><th>Date</th><th>Impact / Time</th></tr></thead><tbody>'+
    (tr||'<tr><td colspan="4">No events loaded</td></tr>')+'</tbody></table></div>'+
    (ertr?'<div class="sect">EARNINGS</div><div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Country</th><th>Date</th></tr></thead><tbody>'+ertr+'</tbody></table></div>':'');
}

/* ---------- PORTFOLIO ---------- */
function rPortfolio(){
  var raw=null; try{raw=JSON.parse(localStorage.getItem("as-portfolio")||"null");}catch(e){}
  var h='<div class="fshead"><h2>Portfolio</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  if(raw&&raw.length){
    var tr=raw.map(function(p){return '<tr><td>'+esc(p.symbol)+'</td><td>'+num(p.qty,0)+'</td><td>'+px(p.avg)+'</td></tr>';}).join("");
    h+='<div class="card" style="padding:0;overflow:auto"><table><thead><tr><th>Symbol</th><th>Qty</th><th>Avg</th></tr></thead><tbody>'+tr+'</tbody></table></div>';
  } else {
    h+='<div class="card" style="padding:20px;text-align:center"><div class="mono s11" style="color:var(--dim)">No holdings saved on this device yet.</div>'+
       '<div class="s11" style="margin-top:8px">Portfolio is stored locally in your browser.</div></div>';
  }
  return h;
}

/* ---------- LEARN ---------- */
function rLearn(){
  var L=D.learn||{}, E=D.education||{};
  var sec=function(t,rows){return rows&&rows.length?'<div class="sect">'+esc(t)+'</div><div class="card" style="padding:4px 14px">'+rows.join("")+'</div>':"";};
  var rrow=function(a,b){return '<div class="zrow"><span>'+esc(a)+'</span><span class="s11" style="color:var(--dim)">'+esc(b)+'</span></div>';};
  var h='<div class="fshead"><h2>Learn</h2><button class="xbtn" data-go="home">\u2715 CLOSE</button></div>';
  h+=sec("RULES", (L.rules||[]).slice(0,8).map(function(x){return rrow(x.rule,x.why||"");}));
  h+=sec("STRATEGIES \u00b7 INTRADAY", ((L.strategies&&L.strategies.intraday)||[]).slice(0,6).map(function(x){return rrow(x.name||x,x.note||"");}));
  h+=sec("GLOSSARY", (L.glossary||[]).slice(0,10).map(function(x){return rrow(x.term,x.meaning||"");}));
  h+=sec("QUICK TIPS", (L.quick_tips||[]).slice(0,8).map(function(t){return '<div class="zrow"><span>'+esc(t)+'</span></div>';}));
  h+=sec("BOOKS", (E.books||[]).slice(0,8).map(function(b){return rrow(b.title,(b.author||"")+" \u00b7 "+(b.level||""));}));
  return h;
}

/* ---------- registry ---------- */
var VIEWS = [
  ["home","Home",rHome],["company","Company",rCompany],["indices","Indices",rIndices],
  ["idxradar","Indices Radar",rIdxRadar],["heatmap","Sector Map",rHeatmap],["screener","Screener",rScreener],
  ["fundamentals","Fundamentals",rFundamentals],["mf","MF",rMf],["deepfund","Deep Fund",rDeepFund],
  ["filings","Filings",rFilings],["futures","Futures",rFutures],["gti","GTI",rGti],
  ["gticharts","Charts",rGtiCharts],["gtizones","Zones",rGtiZones],["gtiai","AI read",rGtiAi],
  ["ipo","IPO",rIpo],["aibrain","AI Brain",rAiBrain],["internals","Internals",rInternals],
  ["crypto","Crypto",rCrypto],["global","Global",rGlobal],["news","News",rNews],
  ["events","Events",rEvents],["portfolio","Portfolio",rPortfolio],["learn","Learn",rLearn]
];

function mount(){
  var app=document.getElementById("app"); if(!app)return;
  app.innerHTML = VIEWS.map(function(v){
    var body="";
    try{ body=v[2](); }catch(e){ body='<div class="card" style="padding:16px"><div class="mono s11">Could not render '+esc(v[0])+'.</div></div>'; }
    return '<section class="view" id="v-'+v[0]+'"><div class="jd">'+body+'</div></section>';
  }).join("");
  document.getElementById("v-home").classList.add("on");
}

/* =======================================================================
   UI WIRING
   ======================================================================= */
function show(id){
  var ok=false;
  document.querySelectorAll(".view").forEach(function(v){var on=v.id==="v-"+id;if(on)ok=true;v.classList.toggle("on",on);});
  if(!ok)return show("home");
  window.scrollTo(0,0);
  ["dHome:home","dPort:portfolio","dLearn:learn"].forEach(function(p){var a=p.split(":"),el=document.getElementById(a[0]);if(el)el.classList.toggle("on",id===a[1]);});
  var dg=document.getElementById("dGrid"); if(dg)dg.classList.toggle("on",/^gti/.test(id)||id==="aibrain"||id==="futures"||id==="internals");
  document.querySelectorAll(".nav button").forEach(function(b){b.classList.toggle("active",b.getAttribute("data-go")===id);});
}
function wire(){
  var clk=document.getElementById("clock");
  function tick(){var d=new Date(),h=d.getHours(),ap=h>=12?"PM":"AM";h=h%12;if(h===0)h=12;
    clk.textContent=[h,d.getMinutes(),d.getSeconds()].map(function(n){return String(n).padStart(2,"0");}).join(":")+" "+ap;}
  tick(); setInterval(tick,1000);

  function route(){var h=location.hash.replace("#","");if(h)show(h);}
  addEventListener("hashchange",route);
  document.querySelectorAll("[data-go]").forEach(function(b){b.addEventListener("click",function(){location.hash="#"+b.getAttribute("data-go");});});
  var dH=document.getElementById("dHome"); if(dH)dH.addEventListener("click",function(){location.hash="#home";});
  var dL=document.getElementById("dLearn"); if(dL)dL.addEventListener("click",function(){location.hash="#learn";});
  var dP=document.getElementById("dPort"); if(dP)dP.addEventListener("click",function(){location.hash="#portfolio";});
  var dG=document.getElementById("dGrid"); if(dG)dG.addEventListener("click",function(){location.hash="#gti";});

  var mOv=document.getElementById("moreOv"), pOv=document.getElementById("palOv");
  var dM=document.getElementById("dMore"); if(dM)dM.addEventListener("click",function(){mOv.classList.add("open");});
  var dS=document.getElementById("dSearch"); if(dS)dS.addEventListener("click",function(){pOv.classList.add("open");setTimeout(function(){var q=document.getElementById("palQ");if(q)q.focus();},40);});
  var mx=document.getElementById("mx"); if(mx)mx.addEventListener("click",function(){mOv.classList.remove("open");});
  [mOv,pOv].forEach(function(o){if(o)o.addEventListener("click",function(e){if(e.target===o)o.classList.remove("open");});});

  /* menu list */
  var ml=document.getElementById("menuList");
  if(ml){ ml.innerHTML=VIEWS.map(function(v){return '<button class="mli" data-sec="'+v[0]+'"><b>'+esc(v[1])+'</b><small></small></button>';}).join("");
    ml.querySelectorAll(".mli").forEach(function(t){t.addEventListener("click",function(){mOv.classList.remove("open");location.hash="#"+t.getAttribute("data-sec");});}); }

  /* universal search */
  var pq=document.getElementById("palQ"), pl=document.getElementById("palList");
  function groups(q){
    q=(q||"").toLowerCase(); var out="";
    function grp(t,arr,key){ var m=arr.filter(function(x){return !q||(String(x.n)+" "+x.d).toLowerCase().indexOf(q)>-1;});
      if(!m.length)return ""; return '<div class="pg">'+t+'</div>'+m.slice(0,8).map(function(x){
        return '<div class="pi" data-go="'+x.go+'"><b>'+esc(x.n)+'</b><small>'+esc(x.d)+'</small></div>';}).join(""); }
    var B=brainList().map(function(s){return {n:s.symbol,d:px(s.price)+" \u00b7 "+pct(s.change_pct),go:"company"};});
    var have={}; B.forEach(function(x){have[x.n]=1;});
    Object.keys(D.cindex||{}).forEach(function(k){ if(k[0]==="_"||have[k])return;
      var c=D.cindex[k]; B.push({n:k,d:(c.sector||"")+(c.industry?" \u00b7 "+c.industry:""),go:"company"}); });
    out+=grp("LIVE \u00b7 STOCKS",B);
    out+=grp("LIVE \u00b7 INDICES",idxList().map(function(r){return {n:r.index,d:px(r.price)+" \u00b7 "+pct(r.change_pct),go:"indices"};}));
    out+=grp("LIVE \u00b7 MUTUAL FUNDS",((D.mf&&D.mf.funds)||[]).map(function(f){return {n:f.n,d:(f.k||"")+(f.r1!=null?" \u00b7 1Y "+pct(f.r1):""),go:"mf"};}));
    out+=grp("LIVE \u00b7 IPO",((D.ipo&&D.ipo.ipos)||[]).map(function(x){return {n:x.name,d:(x.price||"")+" \u00b7 "+(x.type||""),go:"ipo"};}));
    out+=grp("LIVE \u00b7 CRYPTO",((D.crypto&&D.crypto.top)||[]).map(function(x){return {n:x.symbol,d:usd(x.price_usd)+" \u00b7 "+pct(x.chg_24h_pct),go:"crypto"};}));
    var s=VIEWS.filter(function(v){return !q||(v[1]).toLowerCase().indexOf(q)>-1;});
    if(s.length)out+='<div class="pg">SECTIONS</div>'+s.map(function(v){return '<div class="pi" data-go="'+v[0]+'"><b>'+esc(v[1])+'</b></div>';}).join("");
    pl.innerHTML=out||'<div class="pg">nothing found \u2014 try RELIANCE, nifty, mf, ipo</div>';
  }
  if(pq){ pq.addEventListener("input",function(){groups(pq.value);}); groups(""); }
  if(pl) pl.addEventListener("click",function(e){var i=e.target.closest(".pi");if(!i)return;pOv.classList.remove("open");
    var g=i.getAttribute("data-go"); if(g)location.hash="#"+g;});

  addEventListener("scroll",function(){var h=document.getElementById("hdr");if(h)h.classList.toggle("scrolled",scrollY>70);},{passive:true});
  document.addEventListener("keydown",function(e){
    if(e.key==="Escape"){mOv.classList.remove("open");pOv.classList.remove("open");var w=document.querySelector(".view.win.on");if(w)location.hash="home";}
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();if(dS)dS.click();}
  });

  var ts=document.getElementById("toast"),tt;
  window.__toast=function(m){ts.textContent=m;ts.classList.add("show");clearTimeout(tt);tt=setTimeout(function(){ts.classList.remove("show");},1900);};

  /* theme */
  var T=[["a","LIGHT"],["b","DARK"],["c","AMOLED"],["d","GENZ"],["e","GENZ DARK"]],ti=0;
  try{var sv=localStorage.getItem("as-theme");if(sv){for(var k=0;k<T.length;k++)if(T[k][0]===sv)ti=k;document.documentElement.dataset.theme=T[ti][0];}}catch(e){}
  var tb=document.getElementById("themeBtn"); if(tb)tb.addEventListener("click",function(){
    ti=(ti+1)%T.length;document.documentElement.dataset.theme=T[ti][0];window.__toast(T[ti][1]+" mode");
    try{localStorage.setItem("as-theme",T[ti][0]);}catch(e){}});

  /* per-view interactions (bound after mount) */
  document.querySelectorAll(".ttab").forEach(function(t){t.addEventListener("click",function(){
    t.parentNode.querySelectorAll(".ttab").forEach(function(x){x.classList.remove("on");});t.classList.add("on");});});

  /* company */
  var co=document.getElementById("qCo");
  if(co){ var timer;
    var doCo=function(){var v=co.value.trim().toUpperCase();var box=document.getElementById("coCard");if(!box)return;
      var sym=Object.keys(D.cindex||{}).filter(function(k){return k[0]!=="_"&&k.indexOf(v)>-1;})[0];
      box.innerHTML=sym?companyCard(sym):'<div class="card" style="padding:16px"><div class="mono s11">No symbol matches "'+esc(co.value)+'".</div></div>';};
    co.addEventListener("input",function(){clearTimeout(timer);timer=setTimeout(doCo,120);});
    document.querySelectorAll("#coQuick .fch").forEach(function(c){c.addEventListener("click",function(){co.value=c.getAttribute("data-co");doCo();});});}

  /* gti chips */
  document.querySelectorAll("#gtiBox").length;
  var gb=document.getElementById("gtiBox");
  if(gb){ document.querySelectorAll(".chips .fch[data-gti]").forEach(function(c){c.addEventListener("click",function(){
      document.querySelectorAll(".chips .fch[data-gti]").forEach(function(x){x.classList.remove("on");});c.classList.add("on");
      gb.innerHTML=gtiSym(c.getAttribute("data-gti"));});}); }

  /* news chips */
  var nb=document.getElementById("newsBox");
  if(nb){ document.querySelectorAll(".fch[data-nt]").forEach(function(c){c.addEventListener("click",function(){
      document.querySelectorAll(".fch[data-nt]").forEach(function(x){x.classList.remove("on");});c.classList.add("on");
      var t=c.getAttribute("data-nt");
      nb.querySelectorAll("[data-ntp]").forEach(function(p){p.style.display=(t==="All"||p.getAttribute("data-ntp")===t)?"":"none";});});}); }

  /* generic filters */
  function filt(inp,tbody){var el=document.getElementById(inp);if(!el)return;
    el.addEventListener("input",function(){var v=el.value.toLowerCase();var tb=document.getElementById(tbody);if(!tb)return;
      tb.querySelectorAll("tr").forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(v)>-1?"":"none";});});}
  filt("qIdx","idxBody"); filt("qScr","scrBody"); filt("qFun","funBody"); filt("qMf","mfBody"); filt("qDf","dfBody"); filt("qFil","filBody");

  function chipGroup(sel){var g=document.querySelector(sel);if(!g)return;
    g.addEventListener("click",function(e){var c=e.target.closest(".fch");if(!c||!g.contains(c))return;
      g.querySelectorAll(".fch").forEach(function(x){x.classList.remove("on");});c.classList.add("on");});}
  chipGroup("#ftIndex"); chipGroup("#coQuick");

  route();
}

/* ---------- boot ---------- */
function boot(){
  mount();               /* render immediately (empty/partial) */
  loadAll().then(function(){ mount(); wire(); })
            .catch(function(){ wire(); });
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
else boot();
})();

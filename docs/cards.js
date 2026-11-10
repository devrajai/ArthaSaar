/* ArthaSaar UI additions - loaded from index.html with one <script src>.
   Kept out of index.html on purpose: that file gets rewritten from older bases
   and inline additions were being erased. */

/* ---------- Feature pack: rotation, rollover, promotion watch, corp actions, delivery, why-moved ---------- */
/* ArthaSaar — feature pack: 8 rotation · 5 promotion watch · 4 rollover · 3 corp actions · 2 why-moved · 1 delivery */
(function(){
  "use strict";
  window.__fpRan=1;
  var D={};
  function J(f){ return fetch(f,{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}); }
  function fmt(x,d){ return (x==null||isNaN(x))?"—":Number(x).toFixed(d==null?1:d); }
  function sgn(x,d){ return (x==null||isNaN(x))?"—":(x>0?"+":"")+Number(x).toFixed(d==null?1:d)+"%"; }
  function num(x){ return (x==null||isNaN(x))?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:1}); }
  function ready(id){ return document.getElementById("sec-"+id); }
  function put(secId,node,key){
    var s=ready(secId); if(!s) return false;
    if(s.querySelector('[data-fp="'+key+'"]')) return true;
    node.setAttribute("data-fp",key); s.appendChild(node); return true;
  }

  /* ---------- 8 · sector rotation ---------- */
  function rotationCard(){
    var d=D.rotation; if(!d||!d.items) return null;
    var b=d.bench_r||{};
    var rows=d.items.map(function(x){ return [x.s, x.r1, x.r3, x.rs3, x.rs6, x.rs12]; });
    var kids=[ para("Relative strength is the sector's return minus Nifty's over the same window. Positive = beating the index. Leaders on 3 months whose 1 month is also improving are usually early in the rotation; leaders fading on 1 month are late.", false) ];
    kids.push(tbl({columns:["sector","1m","3m","3m vs Nifty","6m vs Nifty","12m vs Nifty"], rows:rows}, ["1m","3m","3m vs Nifty","6m vs Nifty","12m vs Nifty"]));
    return card("Sector rotation", "vs Nifty 50 · "+ (d.count||rows.length) +" sectors", kids,
      {what:"Every sector index's return over 1, 3, 6 and 12 months, and how much of it is above or below Nifty.", source:"Yahoo Finance sector indices + NIFTY 50.", updated:d.updated,
       note:"Benchmark 1m "+sgn(b["1m"])+", 3m "+sgn(b["3m"])+", 6m "+sgn(b["6m"])+", 12m "+sgn(b["12m"])+". A sector can be up in absolute terms and still lose relative strength - that is the rotation signal."});
  }

  /* ---------- 5 · promotion watch ---------- */
  function rebalanceCard(){
    var d=D.rebalance; if(!d||!d.items) return null;
    var rows=d.items.slice(0,15).map(function(x){ return [x.s, x.r6, x.adtv]; });
    var kids=[ para("Candidates from Nifty Next 50, ranked by 6-month return and average daily traded value. NSE's actual review also weighs free-float market cap, which no free feed gives cleanly - so this is who is knocking on the door, not a guaranteed inclusion list.", false) ];
    kids.push(tbl({columns:["candidate","6m return","avg daily value"], rows:rows}, ["6m return","avg daily value"]));
    return card("Nifty 50 promotion watch", "from Nifty Next 50", kids,
      {what:"Which Next-50 names are building the liquidity and momentum that index inclusion usually needs.", source:"Yahoo Finance (prices, volume) + NSE Next-50 constituent list.", updated:d.updated,
       note:"Educational. Index changes are decided by NSE's index committee, not by this table."});
  }

  /* ---------- 4 · rollover ---------- */
  function rolloverCard(){
    var d=D.rollover; if(!d||!d.items) return null;
    var rows=d.items.slice(0,15).map(function(x){ return [x.s, x.roll, x.near, x.next]; });
    var kids=[ para("Rollover is the share of a stock's futures open interest already sitting in the next expiry. High rollover = positions carried forward with conviction. Low = being squared off before expiry.", false) ];
    kids.push(tbl({columns:["stock","rollover","this expiry OI","next expiry OI"], rows:rows}, ["rollover","this expiry OI","next expiry OI"]));
    return card("F&O rollover", "expiry "+ (d.items[0]?d.items[0].exp:"") , kids,
      {what:"How much of each stock's futures open interest has already rolled to the next series.", source:"NSE F&O bhavcopy (all expiries, end of day).", updated:d.updated, note:d.note});
  }

  /* ---------- 3 · corporate actions ---------- */
  function corpCard(){
    var d=D.corp; if(!d||!d.items) return null;
    var rows=d.items.slice(0,20).map(function(x){ return [x.s, x.d, x.k, (x.k==="split"?("1 : "+x.v):("₹"+x.v))]; });
    var kids=[ para("A split of 10 means one share became ten, so every price before that date must be divided by ten before you compare it. Skip this and every chart, pattern and backtest across that date is wrong.", false) ];
    kids.push(tbl({columns:["stock","date","type","detail"], rows:rows}, []));
    return card("Corporate actions", "splits & dividends · Nifty 50", kids,
      {what:"Recent splits and dividends, the adjustments your price history needs to stay honest.", source:"Yahoo Finance corporate-action fields.", updated:d.updated, note:d.note});
  }

  /* ---------- 1 · delivery ---------- */
  function deliveryCard(){
    var d=D.delivery; if(!d||!d.items) return null;
    var rows=d.items.slice(0,18).map(function(x){ return [x.s, x.d, x.chg, x.score]; });
    var kids=[ para("Delivery % is the share of traded quantity that actually changed hands. A high-delivery move is real accumulation; a big move on low delivery is usually intraday churn that fades.", false) ];
    kids.push(tbl({columns:["stock","delivery %","day move","score"], rows:rows}, ["delivery %","day move","score"]));
    return card("Delivery & accumulation", d.count+" stocks · "+ (d.date||""), kids,
      {what:"Which stocks moved today on genuine delivery rather than intraday churn.", source:"NSE sec_bhavdata_full (delivery quantity and percentage).", updated:d.updated, note:d.note});
  }

  /* ---------- 2 · why did it move ---------- */
  function whyCard(){
    if(!D.delivery) return null;
    var idx={}; (D.delivery.items||[]).forEach(function(x){ idx[x.s]=x; });
    var roll={}; ((D.rollover&&D.rollover.items)||[]).forEach(function(x){ roll[x.s]=x; });
    var corp={}; ((D.corp&&D.corp.items)||[]).forEach(function(x){ (corp[x.s]=corp[x.s]||[]).push(x); });
    var wrap=el("div","");
    wrap.appendChild(para("Type a symbol to see the day's move pulled apart: delivery, futures positioning and any corporate action, in one place.", false));
    var inp=el("input",""); inp.type="search"; inp.placeholder="e.g. RELIANCE"; inp.style.cssText="width:100%;padding:9px 11px;border-radius:10px;border:1px solid #cfe0f5;margin:6px 0 10px;font-size:13px";
    var out=el("div","");
    wrap.appendChild(inp); wrap.appendChild(out);
    function render(){
      var q=(inp.value||"").trim().toUpperCase(); out.innerHTML="";
      if(!q) return;
      var dv=idx[q];
      if(!dv){ out.appendChild(para("No delivery data for "+q+" in today's file (it may not be in the EQ series).",false)); return; }
      out.appendChild(kpi("move", sgn(dv.chg), "today"));
      out.appendChild(kpi("delivery", fmt(dv.d)+"%", "of traded qty"));
      out.appendChild(kpi("score", fmt(dv.score,0)+"/10", "accumulation"));
      var lines=[];
      lines.push((dv.d>=40?"High delivery ("+fmt(dv.d)+"%) - the move had real backing, not just intraday churn.":"Delivery only "+fmt(dv.d)+"% - a lot of this move was intraday, so it can fade."));
      if(dv.chg>0 && dv.d>=40) lines.push("Price up on high delivery is the classic accumulation read.");
      if(dv.chg<0 && dv.d>=40) lines.push("Price down on high delivery means real distribution, not just weak hands.");
      var r=roll[q]; if(r) lines.push("Futures: "+fmt(r.roll)+"% of open interest has rolled to the next expiry ("+(r.roll>=50?"positions being carried with conviction":"being squared off")+").");
      var cs=corp[q]; if(cs&&cs.length) cs.slice(0,2).forEach(function(c){ lines.push("Corporate action: "+c.k+" on "+c.d+" ("+(c.k==="split"?("1:"+c.v):("₹"+c.v))+") - prices before that date are not comparable until adjusted."); });
      lines.push("This explains what happened; it is not a reason to buy or sell.");
      lines.forEach(function(t){ out.appendChild(para(t,false)); });
    }
    inp.addEventListener("input",render);
    return card("Why did it move?", "one symbol, pulled apart", [wrap],
      {what:"Joins today's price move with delivery, futures rollover and corporate actions for a single stock.", source:"NSE sec_bhavdata_full + F&O bhavcopy + Yahoo corporate actions.", updated:D.delivery.updated,
       note:"Only explains what the data shows. It does not know about news you have not fed it, and it is not advice."});
  }

  var placed={};
  function tryPlace(){
    if(!D.delivery && !D.rotation) return;
    var map=[["sectors",rotationCard],["fno",rolloverCard],["fno",rebalanceCard],["corporate",corpCard],["stocks",deliveryCard],["stocks",whyCard]];
    map.forEach(function(m){
      var key=m[0]+"_"+m[1].name;
      try{ var c=m[1](); if(c) put(m[0],c,key); }catch(e){ (window.__fpErr=window.__fpErr||[]).push(key+": "+(e&&e.message||e)); }
    });
  }
  Promise.all([J("sector_rotation.json"),J("rebalance.json"),J("rollover.json"),J("corp_actions.json"),J("delivery.json")])
    .then(function(r){ window.__fpLoad=[!!r[0],!!r[1],!!r[2],!!r[3],!!r[4]]; D.rotation=r[0]; D.rebalance=r[1]; D.rollover=r[2]; D.corp=r[3]; D.delivery=r[4]; tryPlace(); });
  var iv=setInterval(tryPlace,700);
  try{ new MutationObserver(function(){ tryPlace(); }).observe(document.body,{childList:true,subtree:true}); }catch(e){}
  setTimeout(function(){ clearInterval(iv); }, 120000);
})();

/* ---------- Option walls per expiry ---------- */
/* ArthaSaar — option walls PER EXPIRY (spot + expiry carried through, no cross-expiry summing) */
(function(){
  "use strict";
  function J(f){return fetch(f,{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});}
  function n(x){return (x==null||isNaN(x))?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:1});}
  function card2(title,sub,kids,info){
    if(typeof card==="function"){ try{ return card(title,sub,kids,info); }catch(e){} }
    var d=document.createElement("div"); d.className="card";
    d.innerHTML='<div class="cardhead"><h2>'+title+(sub?'<span class="sub">'+sub+'</span>':'')+'</h2></div>';
    kids.forEach(function(k){ d.appendChild(k); });
    return d;
  }
  function p(t){ return (typeof para==="function")?para(t,false):(function(){var e=document.createElement("p");e.textContent=t;return e;})(); }
  function tbl2(cols,rows,nums){
    if(typeof tbl==="function"){ try{ return tbl({columns:cols,rows:rows},nums||[]); }catch(e){} }
    var t=document.createElement("table"); t.innerHTML="<tr>"+cols.map(function(c){return "<th>"+c+"</th>";}).join("")+"</tr>"+rows.map(function(r){return "<tr>"+r.map(function(c){return "<td>"+c+"</td>";}).join("")+"</tr>";}).join("");
    return t;
  }
  var D=null;
  function build(){
    if(!D||!D.indices) return;
    var host=document.getElementById("sec-fno");
    if(!host||host.querySelector('[data-fp="oiExpiry"]')) return;
    var kids=[p("Each expiry is shown on its own, with the spot the chain was quoted against. The older card adds every expiry together, which is why its PCR and walls differ from the nearest one here.")];
    Object.keys(D.indices).forEach(function(sym){
      var v=D.indices[sym];
      v.expiries.forEach(function(e){
        kids.push(p(sym+" · "+e.expiry+" ("+e.label+", "+(e.days_out==null?"—":e.days_out)+"d) · spot "+n(e.spot)+" · PCR "+n(e.pcr)+" · max pain "+n(e.max_pain)));
        kids.push(tbl2(["strike","call OI","put OI","call chg","put chg"],
          e.strikes.slice(0,10).map(function(s){ return [n(s.strike), s.ce_oi, s.pe_oi, s.ce_chg, s.pe_chg]; }),
          ["call OI","put OI","call chg","put chg"]));
      });
    });
    var c=card2("Option walls · per expiry", (D.date||"")+" · nearest two expiries", kids,
      {what:"Where call and put open interest sits, per expiry, with spot - so a wall can be read as distance from price instead of a number in a vacuum.",
       source:"NSE F&O bhavcopy (UDiFF), index options only.", updated:D.updated,
       note:"End of day only. Positioning, not a forecast, and not a recommendation."});
    c.setAttribute("data-fp","oiExpiry");
    host.appendChild(c);
  }
  J("oi_by_expiry.json").then(function(d){ D=d; build(); });
  var iv=setInterval(build,800); setTimeout(function(){clearInterval(iv);},90000);
  try{ new MutationObserver(build).observe(document.body,{childList:true,subtree:true}); }catch(e){}
})();

/* ---------- What changed today + delivery screener ---------- */
/* ArthaSaar — "What changed today" (deltas, not state) + delivery screener */
(function(){
  "use strict";
  function J(f){return fetch(f,{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});}
  function n(x,d){return (x==null||isNaN(x))?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?1:d});}
  function sgn(x,d){return (x==null||isNaN(x))?"—":(x>0?"+":"")+Number(x).toFixed(d==null?1:d)+"%";}
  function card2(t,sub,kids,info){
    if(typeof card==="function"){ try{ return card(t,sub,kids,info); }catch(e){} }
    var d=document.createElement("div"); d.className="card";
    d.innerHTML='<div class="cardhead"><h2>'+t+(sub?'<span class="sub">'+sub+'</span>':'')+'</h2></div>';
    kids.forEach(function(k){ d.appendChild(k); }); return d;
  }
  function p(t){ return (typeof para==="function")?para(t,false):(function(){var e=document.createElement("p");e.textContent=t;return e;})(); }
  function tbl2(cols,rows,nums){
    if(typeof tbl==="function"){ try{ return tbl({columns:cols,rows:rows},nums||[]); }catch(e){} }
    var t=document.createElement("table");
    t.innerHTML="<tr>"+cols.map(function(c){return "<th>"+c+"</th>";}).join("")+"</tr>"+
      rows.map(function(r){return "<tr>"+r.map(function(c){return "<td>"+c+"</td>";}).join("")+"</tr>";}).join("");
    return t;
  }
  var D={};

  /* ---------- What changed today ---------- */
  function changes(){
    var kids=[], lines=0;
    // 1) fresh option OI (change in OI, per strike, nearest expiry)
    try{
      var o=D.oi, idx=o&&o.indices&&o.indices.NIFTY, e=idx&&idx.expiries&&idx.expiries[0];
      if(e&&e.strikes){
        var ce=e.strikes.slice().sort(function(a,b){return (b.ce_chg||0)-(a.ce_chg||0);}).slice(0,2);
        var pe=e.strikes.slice().sort(function(a,b){return (b.pe_chg||0)-(a.pe_chg||0);}).slice(0,2);
        var t=[];
        ce.forEach(function(s){ if(s.ce_chg>0) t.push("fresh call OI at "+n(s.strike,0)+" (+"+n(s.ce_chg/1e5,1)+" L)"); });
        pe.forEach(function(s){ if(s.pe_chg>0) t.push("fresh put OI at "+n(s.strike,0)+" (+"+n(s.pe_chg/1e5,1)+" L)"); });
        if(t.length){ kids.push(p("Options ("+e.expiry+", "+e.label+"): "+t.join("; ")+".")); lines++; }
      }
    }catch(err){}
    // 2) delivery leaders
    try{
      var d=D.delivery&&D.delivery.items;
      if(d&&d.length){
        var top=d.filter(function(x){return x.score>=7 && x.d>=50;}).slice(0,3);
        if(top.length){ kids.push(p("Real delivery, not churn: "+top.map(function(x){return x.s+" "+n(x.d,0)+"% delivery, "+sgn(x.chg);}).join("; ")+".")); lines++; }
      }
    }catch(err){}
    // 3) circuits
    try{
      var c=D.circuits;
      if(c&&c.n_uc!=null){
        var up=(c.uc||[]).slice(0,2).map(function(x){return x.s+" "+sgn(x.p);}).join(", ");
        kids.push(p("Circuits: "+c.n_uc+" locked upper, "+c.n_lc+" locked lower"+(up?" (biggest: "+up+")":"")+".")); lines++;
      }
    }catch(err){}
    // 4) corporate actions in the last 10 days
    try{
      var ca=D.corp&&D.corp.items||[];
      var cut=new Date(Date.now()-10*864e5).toISOString().slice(0,10);
      var recent=ca.filter(function(x){return x.d>=cut;});
      if(recent.length){
        kids.push(p("Corporate actions this fortnight: "+recent.slice(0,3).map(function(x){return x.s+" "+(x.k==="split"?"split 1:"+x.v:"dividend ₹"+x.v)+" on "+x.d;}).join("; ")+(recent.length>3?" and "+(recent.length-3)+" more":"")+".")); lines++;
      }
    }catch(err){}
    // Distinguish "the data never arrived" from "the data arrived and nothing moved".
    // The old message blamed the collectors for both, and on an expiry day it was simply
    // wrong: option OI unwinds across every strike, so no positive build-up exists to report.
    if(!lines){
      var loaded = !!(D.oi && D.delivery && D.circuits && D.corp);
      if(loaded){
        var e0 = D.oi && D.oi.indices && D.oi.indices.NIFTY &&
                 D.oi.indices.NIFTY.expiries && D.oi.indices.NIFTY.expiries[0];
        var unwound = e0 && e0.strikes && e0.strikes.length &&
          e0.strikes.every(function(x){ return (x.ce_chg||0)<=0 && (x.pe_chg||0)<=0; });
        kids.push(p(unwound
          ? "Nothing built up today: open interest fell at every NIFTY strike, which is what an "
            + "expiry day looks like. Positions were closed, not opened. That is itself the "
            + "news - there was no fresh conviction to report."
          : "The data loaded and nothing moved far enough to report today. A quiet day is a "
            + "result, not a missing file."));
      }else{
        kids.push(p("The change data has not arrived yet - the collectors are still running. "
          + "This card fills in once oi_by_expiry and delivery land."));
      }
    }
    kids.unshift(p("Only what moved since the previous close. The rest of the site shows where things stand; this shows what changed."));
    var c2=card2("What changed today", (D.oi&&D.oi.date)||"", kids,
      {what:"The day's actual deltas: fresh option open interest, stocks that moved on real delivery, circuit activity and corporate actions.",
       source:"NSE F&O bhavcopy, NSE delivery file, NSE bhavcopy, Yahoo corporate actions.",
       updated:(D.oi&&D.oi.updated)||"", note:"Deltas are measured against the previous close. A change is not a direction, and this is not advice."});
    c2.setAttribute("data-fp","changed");
    return c2;
  }

  /* ---------- Delivery screener ---------- */
  function deliveryScreener(){
    var d=D.delivery; if(!d||!d.items) return null;
    var mode="all";
    var kids=[p("Delivery is the share of traded quantity that actually changed hands. High delivery with a rising price is accumulation; a big move on thin delivery is usually intraday churn.")];
    var chips=document.createElement("div");
    chips.style.cssText="display:flex;gap:6px;margin:8px 0;flex-wrap:wrap";
    var out=document.createElement("div");
    function chip(label,val){
      var b=document.createElement("button"); b.textContent=label;
      b.style.cssText="padding:6px 11px;border-radius:999px;border:1px solid #cfe0f5;background:"+(mode===val?"#0b57d0":"#fff")+";color:"+(mode===val?"#fff":"#123")+";font:600 11px system-ui;cursor:pointer";
      b.onclick=function(){ mode=val; renderChips(); draw(); };
      return b;
    }
    function renderChips(){ chips.innerHTML=""; chips.appendChild(chip("All","all")); chips.appendChild(chip("Accumulating","acc")); chips.appendChild(chip("High delivery","hi")); }
    function draw(){
      var rows=d.items.slice();
      if(mode==="acc") rows=rows.filter(function(x){return x.score>=7;});
      if(mode==="hi") rows=rows.filter(function(x){return x.d>=50;});
      rows=rows.slice(0,20);
      out.innerHTML="";
      out.appendChild(tbl2(["stock","delivery %","day move","score"],
        rows.map(function(x){return [x.s, x.d, x.chg, x.score];}),
        ["delivery %","day move","score"]));
    }
    renderChips(); draw();
    kids.push(chips); kids.push(out);
    var c=card2("Delivery screener", (d.count||0)+" stocks · "+(d.date||""), kids,
      {what:"Filter the market by delivery instead of price alone - who is taking actual delivery of shares, not just trading them intraday.",
       source:"NSE sec_bhavdata_full (delivery quantity and percentage).", updated:d.updated, note:d.note});
    c.setAttribute("data-fp","delivscreen");
    return c;
  }

  function place(id, node, key){
    var s=document.getElementById("sec-"+id);
    if(!s||!node) return;
    if(s.querySelector('[data-fp="'+key+'"]')) return;
    s.appendChild(node);
  }
  function run(){
    try{ place("overview", changes(), "changed"); }catch(e){}
    try{ place("stocks", deliveryScreener(), "delivscreen"); }catch(e){}
  }
  Promise.all([J("oi_by_expiry.json"),J("delivery.json"),J("circuits.json"),J("corp_actions.json")])
    .then(function(r){ D.oi=r[0]; D.delivery=r[1]; D.circuits=r[2]; D.corp=r[3]; run(); });
  var iv=setInterval(run,800); setTimeout(function(){clearInterval(iv);},90000);
  try{ new MutationObserver(run).observe(document.body,{childList:true,subtree:true}); }catch(e){}
})();

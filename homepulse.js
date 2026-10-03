/* ArthaSaar Home Pulse — daily brief + full stock chart search */
(function(){
  "use strict";
  var BASE=(location.pathname.indexOf("/app/")>=0?"../data/":"data/");
  var state={stocks:[],chartSym:"NIFTY",chartRows:[]};

  function J(name){return fetch(BASE+name,{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(name);return r.json();});}
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function nf(x,d){return x==null||isNaN(x)?"—":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?2:d});}
  function pc(x){return x==null||isNaN(x)?"—":(x>=0?"+":"")+Number(x).toFixed(2)+"%";}
  function signClass(x){return Number(x)>=0?"up":"dn";}
  function money(x){var a=Math.abs(Number(x)||0); if(a>=100) return "₹"+Number(x).toFixed(1)+" Cr"; return "₹"+Number(x).toFixed(2)+" Cr";}
  function card(title,body,meta){
    return '<div class="card hp-card"><div class="sh2">'+title+(meta?'<span class="fr">'+meta+'</span>':'')+'</div>'+body+'</div>';
  }
  function rows(list,kind){
    return '<div class="hp-list">'+list.map(function(x){
      if(kind==="stock") return '<div class="ni hp-row"><span><b>'+esc(x.symbol)+'</b><small>'+esc(x.company||"")+'</small></span><b class="'+signClass(x.change_pct)+'">'+pc(x.change_pct)+'</b></div>';
      if(kind==="big") return '<div class="ni hp-row"><span><b>'+esc(x.s)+'</b><small>'+esc(x.n||"")+'</small></span><span class="hp-dual"><b class="up">'+money(x.bv)+'</b><b class="dn">'+money(x.sv)+'</b></span></div>';
      if(kind==="news") return '<div class="ni"><b>'+esc(x.sym)+' · '+esc(x.tag||"neutral")+'</b><small>'+esc((x.hl&&x.hl[0]&&x.hl[0].t)||"News-volume spike")+" · 7d "+nf(x.total7,0)+" articles · spike "+nf((x.spike||0)*100,0)+"%</small></div>';
      return "";
    }).join("")+'</div>';
  }

  function buildHome(data){
    var home=document.getElementById("v-home"); if(!home||document.getElementById("as-home-brief")) return;
    var b=data.brain||{}, stocks=(b.stocks||[]).slice();
    stocks.sort(function(a,z){return (z.change_pct||0)-(a.change_pct||0);});
    var gain=stocks.slice(0,5), lose=stocks.slice(-5).reverse();
    var fii=data.fii||{}, br=data.breadth||{}, del=data.delivery||{}, bp=data.big||{}, nv=data.newsvol||{}, fu=data.futures||{}, gt=data.gti||{}, xr=data.xray||{};

    var delPairs=Object.keys(del.d||{}).map(function(s){return {s:s,v:Number(del.d[s])};}).sort(function(a,z){return z.v-a.v;}).slice(0,8);
    var delHtml=delPairs.map(function(x){return '<div class="zrow"><span><b>'+esc(x.s)+'</b></span><b>'+nf(x.v,1)+'%</b></div>';}).join("");
    var pcr=fu.pcr||{};
    var ns=nv.companies||[];
    var bpList=(bp.bulk||[]).slice().sort(function(a,z){return (z.bv||0)-(a.bv||0);}).slice(0,6);
    var xrPoints=(xr.points||[]).slice(0,6).map(function(x){return '<div class="ni"><b>'+esc(x.h)+'</b><small>'+esc(x.t)+'</small></div>';}).join("");

    var html='<div id="as-home-brief" class="hp-wrap">'+
      '<div class="sect">DAILY MARKET BRIEF <span class="fr">auto-refresh · 5 min</span></div>'+
      '<div class="hp-grid">'+
        card("TOP 5 GAINERS",rows(gain,"stock"),"screener · "+(b.count||stocks.length))+
        card("TOP 5 LOSERS",rows(lose,"stock"),"screener")+
      '</div>'+
      '<div class="hp-grid">'+
        card("FII / DII",'<div class="hp-kpis">'+
          '<div><span>FII / FPI</span><b class="dn">₹'+nf((fii.categories&&fii.categories["FII/FPI"]&&fii.categories["FII/FPI"].net_cr)||0,0)+' Cr</b></div>'+
          '<div><span>DII</span><b class="up">₹'+nf((fii.categories&&fii.categories.DII&&fii.categories.DII.net_cr)||0,0)+' Cr</b></div>'+
        '</div><div class="zrow"><span>Report date</span><b>'+esc(fii.date||"—")+'</b></div>',"cash flows")+
        card("MARKET BREADTH",'<div class="hp-kpis"><div><span>Stocks</span><b>'+nf(br.stocks,0)+'</b></div><div><span>Above EMA200</span><b>'+nf(br.above_ema200_pct,1)+'%</b></div></div>'+
          '<div class="zrow"><span>RSI &gt; 60</span><b>'+nf(br.rsi_above_60,0)+'</b></div><div class="zrow"><span>RSI &lt; 40</span><b>'+nf(br.rsi_below_40,0)+'</b></div><div class="zrow"><span>Volume spike ≥2×</span><b>'+nf(br.volume_spike_2x,0)+'</b></div>',"breadth")+
      '</div>'+
      '<div class="hp-grid">'+
        card("AFTER-MARKET BUYING / SELLING",rows(bpList,"big"),"bulk/block trades · bv / sv")+
        card("DELIVERY LEADERS",delHtml,"delivery % · "+esc(del.date||"latest"))+
      '</div>'+
      '<div class="hp-grid">'+
        card("F&O LEVELS / OI",'<div class="zrow"><span>NIFTY spot</span><b>'+nf(pcr.nifty_spot,2)+'</b></div><div class="zrow"><span>Max pain</span><b>'+nf(pcr.nifty_max_pain,0)+'</b></div><div class="zrow"><span>PCR · OI</span><b>'+nf(pcr.nifty_pcr_oi,3)+'</b></div><div class="zrow"><span>Call OI</span><b>'+nf((pcr.nifty_call_oi||0)/1e7,2)+' Cr</b></div><div class="zrow"><span>Put OI</span><b>'+nf((pcr.nifty_put_oi||0)/1e7,2)+' Cr</b></div>',"futures")+
        card("GTI LEVELS",'<div class="zrow"><span>NIFTY nearest</span><b>'+esc((gt.symbols&&gt.symbols["NIFTY 50"]&&gt.symbols["NIFTY 50"].nearest||[]).join(" "))+'</b></div><div class="zrow"><span>Day POC</span><b>'+nf(gt.symbols&&gt.symbols["NIFTY 50"]&&gt.symbols["NIFTY 50"].day_poc,0)+'</b></div><div class="zrow"><span>Grid</span><b>'+nf(gt.symbols&&gt.symbols["NIFTY 50"]&&gt.symbols["NIFTY 50"].grid&&gt.symbols["NIFTY 50"].grid.level,0)+'</b></div>',"zones")+
      '</div>'+
      card("NEWS-VOLUME SPIKES",rows(ns.slice(0,6),"news"),"Google News · 7d")+
      card("X-RAY ANALYSIS",'<div class="hp-xray">'+xrPoints+'</div><div class="hp-verdict">'+esc(xr.verdict||"Latest X-ray available")+'</div>',"auto-analysis · "+esc(xr.date||""))+
    '</div>';
    home.insertAdjacentHTML("afterbegin",html);
  }

  function chartSVG(rows){
    if(!rows||rows.length<2)return '<div class="mut">No daily history available.</div>';
    var c=rows.map(function(x){return Number(x.close);}).filter(function(x){return isFinite(x);});
    var w=900,h=250,p=18,hi=Math.max.apply(null,c),lo=Math.min.apply(null,c),rg=(hi-lo)||1;
    var pts=c.map(function(v,i){return (p+i*(w-p*2)/(c.length-1)).toFixed(1)+","+(h-p-(v-lo)/rg*(h-p*2)).toFixed(1);}).join(" ");
    return '<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" style="width:100%;height:250px"><path d="M'+p+' '+(h-p)+'H'+(w-p)+'" class="gl"/><polyline points="'+pts+'" fill="none" stroke="var(--accent)" stroke-width="2.5"/></svg><div class="mut" style="font-size:10px">'+esc(rows[0].date)+' → '+esc(rows[rows.length-1].date)+' · last ₹'+nf(c[c.length-1],2)+'</div>';
  }

  function buildChartSearch(){
    var host=document.getElementById("v-gticharts"); if(!host||document.getElementById("as-chart-universe")) return;
    var anchor=host.querySelector("#cChart"); if(!anchor) return;
    var box=document.createElement("div"); box.id="as-chart-universe"; box.innerHTML=
      '<div class="pbar"><span class="plab">FULL STOCK UNIVERSE · '+nf(state.stocks.length,0)+' listed names</span></div>'+
      '<div class="srow"><input id="asChartSearch" type="search" placeholder="Search 2,288 stocks by symbol or company…"></div>'+
      '<div class="chips" id="asChartMatches"></div>'+
      '<div class="card" id="asStockChart" style="margin-top:8px;padding:10px 12px"><div class="sh2" id="asStockChartHead">Select a stock</div><div id="asStockChartBody" class="mut">Search above to load its daily history.</div></div>';
    anchor.parentNode.insertBefore(box,anchor.nextSibling);
    function renderMatches(q){
      q=(q||"").toLowerCase().trim();
      var list=state.stocks.filter(function(x){return !q||String(x.symbol).toLowerCase().indexOf(q)>=0||String(x.company||"").toLowerCase().indexOf(q)>=0;}).slice(0,40);
      document.getElementById("asChartMatches").innerHTML=list.map(function(x){return '<button class="fch" data-sym="'+esc(x.symbol)+'">'+esc(x.symbol)+'</button>';}).join("");
      document.querySelectorAll("#asChartMatches [data-sym]").forEach(function(b){b.onclick=function(){loadStockChart(b.getAttribute("data-sym"));};});
    }
    function loadStockChart(sym){
      state.chartSym=sym;
      var s=state.stocks.filter(function(x){return x.symbol===sym;})[0]||{};
      document.getElementById("asStockChartHead").textContent=sym+" · daily history";
      document.getElementById("asStockChartBody").innerHTML='<div class="mut">Loading '+esc(sym)+'…</div>';
      J("history/"+encodeURIComponent(sym)+".json").then(function(rows){
        state.chartRows=rows||[];
        document.getElementById("asStockChartBody").innerHTML=chartSVG(state.chartRows.slice(-260));
      }).catch(function(){document.getElementById("asStockChartBody").innerHTML='<div class="mut">History unavailable for '+esc(sym)+'</div>';});
    }
    document.getElementById("asChartSearch").addEventListener("input",function(){renderMatches(this.value);});
    renderMatches("");
  }

  function css(){
    if(document.getElementById("as-home-pulse-css"))return;
    var st=document.createElement("style");st.id="as-home-pulse-css";st.textContent=
      '.hp-wrap{display:block}.hp-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.hp-card{min-width:0}.hp-list{display:flex;flex-direction:column}.hp-row{display:flex;justify-content:space-between;gap:10px;align-items:center}.hp-row>span:first-child{min-width:0}.hp-row small{display:block;color:var(--dim);font:400 9px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}.hp-dual{display:flex;gap:8px;font:700 10px var(--mono)}.hp-kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px 14px}.hp-kpis>div{border:1px solid var(--border);border-radius:9px;padding:9px}.hp-kpis span{display:block;color:var(--dim);font-size:9px}.hp-kpis b{display:block;margin-top:4px;font:800 14px var(--mono)}.hp-xray .ni{padding:9px 14px}.hp-xray .ni small{line-height:1.5}.hp-verdict{margin:10px 14px 12px;padding:10px;border:1px solid var(--border);border-radius:9px;color:var(--dim);font-size:11px;line-height:1.5}.hp-wrap .sect{margin-top:18px}.hp-wrap .fr{float:right}@media(max-width:720px){.hp-grid{grid-template-columns:1fr}.hp-row small{max-width:190px}}'+
      '#v-futures.view.on{min-height:calc(100vh - 120px)}#v-futures #as-fo-card>.card{max-height:calc(100vh - 235px)!important;height:calc(100vh - 235px)!important}#v-futures #as-fo-card table{min-height:100%}';
    document.head.appendChild(st);
  }

  function boot(){
    css();
    Promise.all([
      J("brain-screener.json"),
      J("fii-dii.json"),
      J("breadth.json"),
      J("delivery.json"),
      J("bigplayer.json"),
      J("news-volume.json"),
      J("futures.json"),
      J("gti.json"),
      J("xray.json")
    ]).then(function(a){
      state.stocks=(a[0]&&a[0].stocks)||[];
      buildHome({brain:a[0]||{},fii:a[1]||{},breadth:a[2]||{},delivery:a[3]||{},big:a[4]||{},newsvol:a[5]||{},futures:a[6]||{},gti:a[7]||{},xray:a[8]||{}});
      buildChartSearch();
    }).catch(function(e){console.warn("ArthaSaar Home Pulse",e);});
  }
  boot();
  setInterval(function(){location.reload();},300000);
})();
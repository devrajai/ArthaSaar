/* ArthaSaar Home Pulse — daily brief + full stock chart search */
(function(){
  "use strict";
  var BASE=(location.pathname.indexOf("/app/")>=0?"../data/":"data/");
  var state={stocks:[],indices:[],indexHistory:{},chartSym:"NIFTY",chartRows:[]};

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

  function parseTs(s){
    if(!s) return null;
    var d=new Date(s);
    if(!isNaN(d.getTime())) return d;
    var m=String(s).match(/(\d{2}) (\w{3}) (\d{4}), (\d{2}):(\d{2}) IST/);
    if(m){
      var months={Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
      return new Date(Date.UTC(Number(m[3]),months[m[2]]||0,Number(m[1]),Number(m[4]),Number(m[5]))-330*60000);
    }
    m=String(s).match(/(\d{2})-(\w{3})-(\d{4})/);
    if(m){
      var mm={Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
      return new Date(Date.UTC(Number(m[3]),mm[m[2]]||0,Number(m[1]))-330*60000);
    }
    return null;
  }
  function ageLabel(s){
    var d=parseTs(s); if(!d) return "timestamp unavailable";
    var mins=Math.max(0,Math.round((Date.now()-d.getTime())/60000));
    if(mins<60) return mins+"m ago";
    var hrs=Math.round(mins/60);
    if(hrs<48) return hrs+"h ago";
    return Math.round(hrs/24)+"d ago";
  }
  function freshness(s){
    var d=parseTs(s); if(!d) return "UNKNOWN";
    var hrs=Math.max(0,(Date.now()-d.getTime())/3600000);
    return hrs<=30?"FRESH":(hrs<=72?"EOD":"STALE");
  }
  function buildSourceCenter(meta){
    if(document.getElementById("as-data-center")) return;
    var home=document.getElementById("v-home"); if(!home) return;
    var r=meta.registry||{}, feeds=r.feeds||[], healthMap={};
    (meta.health&&meta.health.feeds||[]).forEach(function(h){healthMap[h.id]=h;});
    var feedData={
      "nse-equity":meta.brain,
      "nse-indices":meta.indices,
      "nse-index-history":meta.indexHistory,
      "nse-fii-dii":meta.fii,
      "nse-delivery":meta.delivery,
      "nse-fo":meta.futures,
      "yahoo-history":meta.historyProbe,
      "amfi-nav":meta.mfTop,
      "google-news":meta.news,
      "coingecko":meta.crypto,
      "derived":meta.xray
    };
    var rows=feeds.map(function(f){
      var d=feedData[f.id]||{}, h=healthMap[f.id]||{};
      var updated=d.updated || h.updated || null;
      var status=h.status ? (h.status==="ok"?"OK":String(h.status).toUpperCase()) :
        (f.id==="yahoo-history"?(d.to?"HISTORY":"NO DATA"):freshness(updated));
      var cov=f.coverage||"—";
      if(f.id==="nse-equity" && meta.brain && Array.isArray(meta.brain.stocks)) cov=nf(meta.brain.stocks.length,0)+" screened stocks";
      if(f.id==="nse-indices" && meta.indices && meta.indices.count) cov=nf(meta.indices.count,0)+" indices";
      if(f.id==="nse-delivery" && meta.delivery && meta.delivery.n) cov=nf(meta.delivery.n,0)+" securities";
      if(f.id==="nse-fo" && meta.futures && meta.futures.stock_count) cov=nf(meta.futures.stock_count,0)+" stock futures";
      if(f.id==="google-news" && meta.news && meta.news.count) cov=nf(meta.news.count,0)+" headlines";
      if(f.id==="coingecko" && meta.crypto && Array.isArray(meta.crypto.top)) cov=nf(meta.crypto.top.length,0)+" coins";
      if(f.id==="derived" && meta.gti && meta.gti.symbols) cov=nf(Object.keys(meta.gti.symbols).length,0)+" model symbols";
      var cls=status==="OK"||status==="FRESH"||status==="HISTORY"?"buy":(status==="EOD"?"hold":"dn");
      var stamp=updated||"—";
      return '<div class="dc-row"><div><b>'+esc(f.label)+'</b><small>'+esc(f.source)+' · '+esc(f.cadence)+'</small></div><div class="dc-mid"><span>'+esc(cov)+'</span><small>'+esc(ageLabel(stamp))+'</small></div><div class="dc-last"><span class="b '+cls+'">'+esc(status)+'</span><small>'+esc(stamp)+'</small></div><a href="'+esc(f.source_url||"#")+'" target="_blank" rel="noopener">SOURCE</a></div>';
    }).join("");
    var card=document.createElement("div");
    card.id="as-data-center";
    card.className="hp-wrap";
    card.innerHTML='<div class="sect">FREE DATA CENTER <span class="fr">source + freshness + coverage</span></div>'+
      '<div class="card hp-card"><div class="sh2">HOSTED SNAPSHOT POLICY</div>'+
      '<div class="dc-note">GitHub Pages serves the latest committed JSON snapshot. Refreshing this page does not fetch exchange prices directly; GitHub Actions collectors update the hosted files. Status comes from the automated data-health check when available. “OK/EOD” is freshness, not a real-time quote.'+((meta.health&&meta.health.summary)?(" Overall: "+nf(meta.health.summary.ok,0)+"/"+nf(meta.health.summary.total,0)+" feeds healthy."):"")+'</div>'+
      '<div class="dc-list">'+rows+'</div></div>';
    var brief=document.getElementById("as-home-brief");
    if(brief) brief.insertAdjacentElement("afterend",card); else home.insertAdjacentElement("afterbegin",card);
  }
  function updateCoverageLabels(count){
    if(!count) return;
    document.querySelectorAll("h2,.ng,.sect,.plab,.ds span,button").forEach(function(el){
      if(el.childElementCount===0 && /2,085 stocks/.test(el.textContent)) el.textContent=el.textContent.replace(/2,085 stocks/g,nf(count,0)+" stocks");
    });
    var h=document.querySelector("#v-screener h2");
    if(h) h.innerHTML="Screener — "+nf(count,0)+" stocks";
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
    var stockList=(state.stocks||[]).map(function(x){return {symbol:x.symbol,company:x.company||"",type:"stock"};});
    var indexList=(state.indices||[]).map(function(x){return {symbol:x.index||x.symbol,company:"NSE Index",type:"index"};});
    var universe=stockList.concat(indexList.filter(function(ix){
      return !stockList.some(function(s){return s.symbol===ix.symbol;});
    }));
    var box=document.createElement("div"); box.id="as-chart-universe"; box.innerHTML=
      '<div class="pbar"><span class="plab">FULL MARKET CHARTS · '+nf(stockList.length,0)+' stocks + '+nf(indexList.length,0)+' indices</span></div>'+
      '<div class="srow"><input id="asChartSearch" type="search" placeholder="Search stock or index by name/symbol…"></div>'+
      '<div class="chips" id="asChartMatches"></div>'+
      '<div class="card" id="asStockChart" style="margin-top:8px;padding:10px 12px"><div class="sh2" id="asStockChartHead">Select a stock or index</div><div id="asStockChartBody" class="mut">Search above to load daily history.</div></div>';
    anchor.parentNode.insertBefore(box,anchor.nextSibling);

    function renderMatches(q){
      q=(q||"").toLowerCase().trim();
      var list=universe.filter(function(x){
        return !q||String(x.symbol).toLowerCase().indexOf(q)>=0||String(x.company||"").toLowerCase().indexOf(q)>=0;
      }).slice(0,50);
      document.getElementById("asChartMatches").innerHTML=list.map(function(x){
        return '<button class="fch" data-sym="'+esc(x.symbol)+'" data-type="'+x.type+'">'+esc(x.symbol)+'</button>';
      }).join("");
      document.querySelectorAll("#asChartMatches [data-sym]").forEach(function(b){
        b.onclick=function(){loadChart(b.getAttribute("data-sym"),b.getAttribute("data-type"));};
      });
    }

    function loadChart(sym,type){
      state.chartSym=sym;
      document.getElementById("asStockChartHead").textContent=sym+" · "+(type==="index"?"NSE daily history":"daily stock history");
      document.getElementById("asStockChartBody").innerHTML='<div class="mut">Loading '+esc(sym)+'…</div>';
      if(type==="index"){
        var rows=state.indexHistory[sym]||[];
        if(rows.length>=2){
          state.chartRows=rows;
          document.getElementById("asStockChartBody").innerHTML=chartSVG(rows.slice(-260));
        }else{
          document.getElementById("asStockChartBody").innerHTML='<div class="mut">NSE history not yet archived for '+esc(sym)+'. Current index snapshot exists, but no historical series is available yet.</div>';
        }
        return;
      }
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
      '#v-futures.view.on{min-height:calc(100vh - 120px)}#v-futures #as-fo-card>.card{max-height:calc(100vh - 235px)!important;height:calc(100vh - 235px)!important}#v-futures #as-fo-card table{min-height:100%}.dc-note{padding:12px 14px;color:var(--dim);font-size:10.5px;line-height:1.55;border-bottom:1px solid var(--border)}.dc-list{display:flex;flex-direction:column}.dc-row{display:grid;grid-template-columns:1.6fr .9fr .9fr auto;gap:10px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--border)}.dc-row:last-child{border-bottom:0}.dc-row b{display:block;font-size:11px}.dc-row small{display:block;color:var(--dim);font:400 8.5px var(--mono);margin-top:3px}.dc-mid span,.dc-last span{font:600 9px var(--mono)}.dc-row a{font:700 8px var(--mono);color:var(--accent);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:4px 6px}.dc-row a:hover{border-color:var(--accent)}@media(max-width:720px){.dc-row{grid-template-columns:1fr auto;gap:5px}.dc-mid{display:none}.dc-last{text-align:right}.dc-row a{justify-self:end}}';
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
      J("xray.json"),
      J("source-registry.json").catch(function(){return {feeds:[]};}),
      J("indices-all.json").catch(function(){return {};}),
      J("index-history-daily.json").catch(function(){return {};}),
      J("mf-top.json").catch(function(){return {};}),
      J("crypto.json").catch(function(){return {};}),
      J("news.json").catch(function(){return {};}),
      J("history-index.json").catch(function(){return {};}),
      J("data-health.json").catch(function(){return {};}),
      J("history/RELIANCE.json").catch(function(){return {};})
    ]).then(function(a){
      state.stocks=(a[0]&&a[0].stocks)||[];
      buildHome({brain:a[0]||{},fii:a[1]||{},breadth:a[2]||{},delivery:a[3]||{},big:a[4]||{},newsvol:a[5]||{},futures:a[6]||{},gti:a[7]||{},xray:a[8]||{}});
      state.indices=(a[10]&&a[10].indices)||[];
      state.indexHistory=(a[11]&&a[11].indices)||{};
      buildSourceCenter({
        registry:a[9]||{},
        indices:a[10]||{},
        indexHistory:a[11]||{},
        mfTop:a[12]||{},
        crypto:a[13]||{},
        news:a[14]||{},
        historyProbe:a[15]||{},
        health:a[16]||{},
        brain:a[0]||{},
        breadth:a[2]||{},
        fii:a[1]||{},
        delivery:a[3]||{},
        futures:a[6]||{},
        gti:a[7]||{},
        xray:a[8]||{}
      });
      updateCoverageLabels(state.stocks.length);
      buildChartSearch();
    }).catch(function(e){console.warn("ArthaSaar Home Pulse",e);});
  }
  boot();
  setInterval(function(){location.reload();},300000);
})();
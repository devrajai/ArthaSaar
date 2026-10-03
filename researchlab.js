/* ArthaSaar Research Lab v2 — 10 free-data research tools.
   Uses only repository snapshots and public-data products already collected by the EOD pipeline.
   No paid API, no prediction, no duplicate company-data injection. */
(function(){
  "use strict";
  var BASE=(location.pathname.indexOf("/app/")>=0?"../data/":"data/");
  var Q={radar:null,signal:null,market:null,filings:null,companies:null,cache:{}};

  function J(name){
    return fetch(BASE+name+"?lab="+Date.now(),{cache:"no-store"})
      .then(function(r){if(!r.ok)throw Error(name);return r.json();});
  }
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function n(x,d){
    if(x==null||isNaN(x))return"—";
    return Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?1:d});
  }
  function pct(x,d){
    if(x==null||isNaN(x))return"—";
    return (Number(x)>=0?"+":"")+Number(x).toFixed(d==null?1:d)+"%";
  }
  function cls(x){return Number(x)>0?"up":Number(x)<0?"dn":"";}
  function dt(x){
    return String(x||"—").replace("T"," ").replace("Z","");
  }
  function card(num,title,body,tag){
    return '<div class="rl2-card"><div class="rl2-head"><b>'+num+' · '+esc(title)+'</b><span>'+esc(tag||"FREE DATA")+'</span></div>'+body+'</div>';
  }
  function row(a,b,c){
    return '<div class="rl2-row"><span>'+esc(a)+'</span><b class="'+(c||"")+'">'+esc(b==null?"—":b)+'</b></div>';
  }
  function list(items,make,limit){
    return (items||[]).slice(0,limit||6).map(make).join("")||'<div class="rl2-empty">No rows in the current snapshot.</div>';
  }

  function whyToday(){
    var f=Q.radar.features||{}, br=f.breadth_history||{}, reg=f.market_regime||{}, rs=f.relative_strength||{};
    var t=br.today||{};
    var leaders=(f.sector_rotation&&f.sector_rotation.sectors||[]).slice(0,3);
    var lag=(f.sector_rotation&&f.sector_rotation.sectors||[]).slice(-3).reverse();
    var h='<div class="rl2-kpis">';
    h+='<div><small>REGIME</small><b>'+esc(reg.label||"—")+'</b></div>';
    h+='<div><small>BREADTH</small><b>'+n(t.advancers,0)+' / '+n(t.decliners,0)+'</b></div>';
    h+='<div><small>EMA200</small><b>'+n(reg.ema200_pct,1)+'%</b></div>';
    h+='<div><small>FII</small><b>'+((reg.fii_net_cr==null)?"—":(n(reg.fii_net_cr,0)+" Cr"))+'</b></div>';
    h+='</div>';
    h+='<div class="rl2-cols"><div><div class="rl2-mini">LEADING SECTORS</div>'+list(leaders,x=>row(x.sector,pct(x.avg_1d_pct),cls(x.avg_1d_pct)),3)+'</div>';
    h+='<div><div class="rl2-mini">WEAK SECTORS</div>'+list(lag,x=>row(x.sector,pct(x.avg_1d_pct),cls(x.avg_1d_pct)),3)+'</div></div>';
    h+='<div class="rl2-note">Evidence chain: breadth + trend + NIFTY + institutional flow + sector rotation. Descriptive snapshot only.</div>';
    return h;
  }

  function marketReplay(){
    var d=(Q.market&&Q.market.daily)||((Q.radar.research_lab||{}).daily_history)||[];
    d=(d||[]).slice(-60);
    var latest=d.length?d[d.length-1]:null;
    var opts=d.slice().reverse().map(function(x){return'<option value="'+esc(x.date)+'">'+esc(x.date)+'</option>';}).join("");
    var h='<div class="rl2-replay"><label>Replay date</label><select id="rl2ReplaySelect">'+opts+'</select><button id="rl2ReplayToday">LATEST</button></div>';
    h+='<div id="rl2ReplayBody"></div>';
    setTimeout(function(){
      var sel=document.getElementById("rl2ReplaySelect"), box=document.getElementById("rl2ReplayBody");
      function paint(x){
        if(!x){box.innerHTML='<div class="rl2-empty">No replay history yet.</div>';return;}
        box.innerHTML='<div class="rl2-kpis">'+
          '<div><small>DATE</small><b>'+esc(x.date)+'</b></div>'+
          '<div><small>BREADTH</small><b>'+n(x.breadth&&x.breadth.advance_ratio_pct,1)+'%</b></div>'+
          '<div><small>HIGH ZONE</small><b>'+n(x.high_low&&x.high_low.new_high_zone,0)+'</b></div>'+
          '<div><small>LOW ZONE</small><b>'+n(x.high_low&&x.high_low.new_low_zone,0)+'</b></div>'+
          '</div><div class="rl2-cols"><div><div class="rl2-mini">REGIME</div>'+row("Label",x.regime&&x.regime.label)+row("Score",x.regime&&x.regime.score)+row("NIFTY",pct(x.regime&&x.regime.nifty_change_pct),cls(x.regime&&x.regime.nifty_change_pct))+'</div><div><div class="rl2-mini">BREADTH</div>'+row("Advancers",n(x.breadth&&x.breadth.advancers,0),"up")+row("Decliners",n(x.breadth&&x.breadth.decliners,0),"dn")+row("EMA200",n(x.breadth&&x.breadth.ema200_pct,1)+"%")+'</div></div>';
      }
      paint(latest);
      if(sel){sel.addEventListener("change",function(){var x=d.find(function(z){return z.date===sel.value;});paint(x);});}
      var b=document.getElementById("rl2ReplayToday"); if(b)b.onclick=function(){if(sel){sel.value=d.length?d[d.length-1].date:"";var x=d.length?d[d.length-1]:null;paint(x);}};
    },0);
    return h;
  }

  function signalLab(){
    var ag=(Q.signal&&Q.signal.aggregate)||((Q.radar.research_lab||{}).signal_outcomes||{}).aggregate||{};
    var keys=["52W_BREAKOUT_ZONE","VOLUME_SHOCK_2X","ABOVE_EMA200","MOMENTUM_20D_5_PLUS","TREND_ALIGNMENT"];
    var h='<div class="rl2-table"><div class="rl2-tr rl2-th"><span>Signal</span><span>Obs</span><span>5D mean</span><span>5D +ve</span><span>20D mean</span></div>';
    keys.forEach(function(k){
      var x=ag[k]||{};
      h+='<div class="rl2-tr"><span>'+esc(k.replace(/_/g," "))+'</span><span>'+n(x.observations,0)+'</span><span class="'+cls(x.next5_mean_pct)+'">'+pct(x.next5_mean_pct)+'</span><span>'+n(x.next5_positive_pct,1)+'%</span><span class="'+cls(x.next20_mean_pct)+'">'+pct(x.next20_mean_pct)+'</span></div>';
    });
    h+='</div><div class="rl2-note">Historical follow-through from stored close series. Samples can contain survivorship bias; this is an evidence archive, not a forecast.</div>';
    return h;
  }

  function eventImpact(){
    var ev=((Q.radar.features||{}).corporate_actions||{}).events||[];
    var h='<div class="rl2-eventgrid">';
    (ev||[]).slice(0,10).forEach(function(x){
      h+='<button class="rl2-event" data-rl2-symbol="'+esc(x.symbol||"")+'"><b>'+esc(x.symbol||"—")+'</b><span>'+esc(x.kind||"Event")+'</span><small>'+esc(x.date||"—")+'</small><em>'+esc(String(x.subject||"").slice(0,90))+'</em></button>';
    });
    h+='</div><div id="rl2EventDetail" class="rl2-detail">Tap an event to inspect its company research record.</div>';
    setTimeout(function(){
      document.querySelectorAll("[data-rl2-symbol]").forEach(function(btn){
        btn.addEventListener("click",function(){
          var s=btn.getAttribute("data-rl2-symbol"); loadCompany(s).then(function(c){
            var q=c&&c.quarters||[], dates=q[0]||[], sales=q.find(function(r){return String(r[0]).toLowerCase().indexOf("sales")===0;})||[], np=q.find(function(r){return String(r[0]).toLowerCase().indexOf("net profit")===0;})||[];
            var body='<b>'+esc((Q.companies&&Q.companies[s]||{}).name||s)+'</b>';
            body+='<div class="rl2-cols"><div>'+row("Event",btn.querySelector("span")&&btn.querySelector("span").textContent)+row("Date",btn.querySelector("small")&&btn.querySelector("small").textContent)+'</div>';
            body+='<div>'+row("Latest sales",sales.length?n(parseFloat(String(sales[sales.length-1]||"").replace(/,/g,"")),0):"—")+row("Latest net profit",np.length?n(parseFloat(String(np[np.length-1]||"").replace(/,/g,"")),0):"—")+'</div></div>';
            document.getElementById("rl2EventDetail").innerHTML=body;
          });
        });
      });
    },0);
    return h;
  }

  function regimeTransitions(){
    var d=(Q.market&&Q.market.daily)||[];
    var out=[];
    for(var i=1;i<d.length;i++){
      var a=d[i-1].regime&&d[i-1].regime.label,b=d[i].regime&&d[i].regime.label;
      if(a&&b&&a!==b)out.push({date:d[i].date,from:a,to:b,nifty:d[i].regime.nifty_change_pct});
    }
    out=out.slice(-12).reverse();
    return out.length?list(out,x=>row(x.date,x.from+" → "+x.to,cls(x.nifty)),12):'<div class="rl2-empty">No regime transitions captured yet. The transition archive grows with each EOD snapshot.</div>';
  }

  function falseBreakouts(){
    var ag=((Q.signal&&Q.signal.aggregate)||{}).["52W_BREAKOUT_ZONE"]||{};
    var fail5=(ag.next5_positive_pct==null)?null:100-Number(ag.next5_positive_pct);
    var fail20=(ag.next20_positive_pct==null)?null:100-Number(ag.next20_positive_pct);
    return '<div class="rl2-kpis">'+
      '<div><small>OBSERVATIONS</small><b>'+n(ag.observations,0)+'</b></div>'+
      '<div><small>5D NON-POSITIVE</small><b class="dn">'+n(fail5,1)+'%</b></div>'+
      '<div><small>20D NON-POSITIVE</small><b class="dn">'+n(fail20,1)+'%</b></div>'+
      '<div><small>5D POSITIVE</small><b class="up">'+n(ag.next5_positive_pct,1)+'%</b></div>'+
      '</div><div class="rl2-note">“False breakout” here means a historical 52W-breakout-zone observation followed by a non-positive forward return in the selected window. It is a classification rule, not a prediction.</div>';
  }

  function filingChanges(){
    var ev=(Q.filings&&Q.filings.filings)||[];
    var by={};
    ev.forEach(function(x){var s=String(x.symbol||"").toUpperCase();if(!s)return;(by[s]||(by[s]=[])).push(x);});
    var h='<div class="rl2-table"><div class="rl2-tr rl2-th"><span>Symbol</span><span>Latest</span><span>Previous</span><span>Change</span><span>Theme</span></div>';
    var count=0;
    Object.keys(by).sort().forEach(function(s){
      if(count>=12)return;
      var a=by[s].slice().sort(function(x,y){return String(y.date||"").localeCompare(String(x.date||""));});
      if(a.length<2)return;
      var latest=String(a[0].subject||"").trim(), prev=String(a[1].subject||"").trim();
      if(latest===prev)return;
      var themes=[];
      ["dividend","results","board","buyback","pledge","insider","rating","order","acquisition","agreement"].forEach(function(k){if(latest.toLowerCase().indexOf(k)>=0&&prev.toLowerCase().indexOf(k)<0)themes.push(k);});
      h+='<div class="rl2-tr"><span><b>'+esc(s)+'</b></span><span>'+esc(dt(a[0].date))+'</span><span>'+esc(dt(a[1].date))+'</span><span>updated</span><span>'+esc(themes.join(", ")||"subject changed")+'</span></div>';
      count++;
    });
    h+='</div><div class="rl2-note">Compares the latest two stored filing subjects per symbol. It flags what changed in the published filing text; full PDF semantic diff is intentionally not fabricated when the archive lacks it.</div>';
    return h;
  }

  function earningsQuality(){
    var rows=((Q.radar.features||{}).momentum_dashboard||{}).roc_leaders||[];
    var h='<div class="rl2-quality-grid">';
    rows.slice(0,8).forEach(function(x){
      h+='<button class="rl2-quality" data-rl2-eq="'+esc(x.symbol)+'"><b>'+esc(x.symbol)+'</b><span>20D '+pct(x.return_20d,1)+'</span><small>history '+n(x.history_days,0)+'d</small></button>';
    });
    h+='</div><div id="rl2EqDetail" class="rl2-detail">Choose a company to calculate a free-data earnings-quality fingerprint.</div>';
    setTimeout(function(){
      document.querySelectorAll("[data-rl2-eq]").forEach(function(btn){
        btn.onclick=function(){
          var s=btn.getAttribute("data-rl2-eq");loadCompany(s).then(function(c){
            var q=c&&c.quarters||[], sales=q.find(function(r){return String(r[0]).toLowerCase().indexOf("sales")===0;})||[], op=q.find(function(r){return String(r[0]).toLowerCase().indexOf("operating profit")===0;})||[], net=q.find(function(r){return String(r[0]).toLowerCase().indexOf("net profit")===0;})||[], other=q.find(function(r){return String(r[0]).toLowerCase().indexOf("other income")===0;})||[];
            function last(vals){for(var i=vals.length-1;i>0;i--){var z=parseFloat(String(vals[i]).replace(/,/g,""));if(!isNaN(z))return z;}return null;}
            function prev(vals){for(var i=vals.length-2;i>0;i--){var z=parseFloat(String(vals[i]).replace(/,/g,""));if(!isNaN(z))return z;}return null;}
            var sl=last(sales),sp=prev(sales),nl=last(net),np=prev(net),ol=last(op),opv=prev(op),oi=last(other);
            var msg='<b>'+esc((Q.companies&&Q.companies[s]||{}).name||s)+'</b><div class="rl2-cols"><div>'+
              row("Sales growth",sp?pct((sl/sp-1)*100,1):"—",cls(sp?sl-sp:0))+
              row("Net profit growth",np?pct((nl/np-1)*100,1):"—",cls(np?nl-np:0))+
              row("OPM latest",sl&&ol?pct((ol/sl)*100,1):"—")+
              '</div><div>'+
              row("OPM prior",sp&&opv?pct((opv/sp)*100,1):"—")+
              row("Other income",oi!=null?n(oi,0):"—")+
              row("Quarter points",q.length-1)+"</div></div><div class="rl2-note">Quality lens = sales growth vs profit growth + operating-margin direction + other-income visibility. It does not assert earnings quality without cash-flow data.</div>';
            document.getElementById("rl2EqDetail").innerHTML=msg;
          });
        };
      });
    },0);
    return h;
  }

  function fingerprint(){
    return '<div class="rl2-search"><input id="rl2FpInput" placeholder="Enter symbol: RELIANCE, TCS, INFY…"><button id="rl2FpBtn">BUILD FINGERPRINT</button></div>'+
      '<div id="rl2FpDetail" class="rl2-detail">Stock Fingerprint combines market regime, trend, momentum, relative strength, liquidity, delivery/F&O context and available company fundamentals.</div>';
  }

  function researchMemory(){
    var d=(Q.market&&Q.market.daily)||[];
    var s=(Q.signal&&Q.signal.records)||[];
    var first=d.length?d[0].date:"—",last=d.length?d[d.length-1].date:"—";
    return '<div class="rl2-kpis">'+
      '<div><small>SNAPSHOTS</small><b>'+n(d.length,0)+'</b></div>'+
      '<div><small>FIRST DATE</small><b>'+esc(first)+'</b></div>'+
      '<div><small>LAST DATE</small><b>'+esc(last)+'</b></div>'+
      '<div><small>SIGNAL RECORDS</small><b>'+n(s.length,0)+'</b></div>'+
      '</div><div class="rl2-note">Research Memory stores prior EOD states so today's dashboard can be compared against its own history rather than relying on hindsight.</div>';
  }

  function css(){
    if(document.getElementById("rl2-css"))return;
    var s=document.createElement("style");s.id="rl2-css";
    s.textContent=[
      "#research-lab-v2{margin-top:12px}",
      "#research-lab-v2 .rl2-banner{border:1px solid var(--border2);background:linear-gradient(180deg,var(--surface),var(--bg2));border-radius:14px;padding:12px;box-shadow:var(--shadow);margin-bottom:10px}",
      ".rl2-title{font-size:20px;line-height:1.2}.rl2-sub{font:400 9px var(--mono);color:var(--dim);margin-top:4px}.rl2-status{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.rl2-status span{border:1px solid var(--border);border-radius:999px;padding:4px 7px;font:500 8px var(--mono);color:var(--dim)}",
      ".rl2-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.rl2-card{min-width:0;border:1px solid var(--border);background:var(--surface);border-radius:12px;overflow:hidden}.rl2-card.wide{grid-column:1/-1}.rl2-head{display:flex;justify-content:space-between;gap:8px;align-items:center;padding:9px 11px;border-bottom:1px solid var(--border);font:700 9px var(--mono);letter-spacing:.08em}.rl2-head span{font:500 7.5px var(--mono);color:var(--faint);white-space:nowrap}.rl2-row{display:flex;justify-content:space-between;gap:10px;padding:7px 10px;border-bottom:1px solid var(--border);font-size:10px}.rl2-row:last-child{border-bottom:0}.rl2-row b{font-family:var(--mono)}.rl2-cols{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:9px}.rl2-mini{font:700 7.5px var(--mono);letter-spacing:.12em;color:var(--faint);padding:0 10px 4px}.rl2-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:9px}.rl2-kpis>div{border:1px solid var(--border);border-radius:9px;background:var(--bg2);padding:8px;min-width:0}.rl2-kpis small{display:block;color:var(--faint);font:600 7px var(--mono);letter-spacing:.1em}.rl2-kpis b{display:block;margin-top:4px;font:700 12px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rl2-note,.rl2-detail{margin:9px;padding:9px 10px;border:1px dashed var(--border2);border-radius:9px;color:var(--dim);font:400 9px var(--mono);line-height:1.5}.rl2-empty{padding:10px;color:var(--faint);font:400 9px var(--mono)}",
      ".rl2-table{overflow:auto}.rl2-tr{display:grid;grid-template-columns:1.6fr .6fr .8fr .8fr .8fr;gap:5px;padding:7px 9px;border-bottom:1px solid var(--border);font-size:8.5px;min-width:520px}.rl2-th{font:700 7.5px var(--mono);letter-spacing:.08em;color:var(--faint);text-transform:uppercase}.rl2-tr span:nth-child(n+2){font-family:var(--mono)}",
      ".rl2-replay{display:flex;gap:6px;padding:9px;align-items:center}.rl2-replay label{font:700 7.5px var(--mono);color:var(--faint);letter-spacing:.1em}.rl2-replay select,.rl2-replay button,.rl2-search input,.rl2-search button{border:1px solid var(--border2);background:var(--bg2);color:var(--text);border-radius:8px;padding:8px 9px;font:500 9px var(--mono)}.rl2-replay select{flex:1;min-width:0}.rl2-replay button,.rl2-search button{cursor:pointer}",
      ".rl2-eventgrid,.rl2-quality-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:9px}.rl2-event,.rl2-quality{border:1px solid var(--border);background:var(--bg2);color:var(--text);border-radius:9px;padding:9px;text-align:left;cursor:pointer}.rl2-event b,.rl2-quality b{font:700 9px var(--mono)}.rl2-event span,.rl2-event small,.rl2-event em,.rl2-quality span,.rl2-quality small{display:block;margin-top:3px;font-style:normal;color:var(--dim);font-size:8.5px;line-height:1.35}.rl2-event em{color:var(--text)}.rl2-quality span{font-family:var(--mono)}",
      ".rl2-search{display:flex;gap:7px;padding:9px}.rl2-search input{flex:1;min-width:0}.rl2-banner .rl2-foot{margin-top:7px;font:400 8px var(--mono);color:var(--faint)}",
      "@media(max-width:720px){.rl2-grid{grid-template-columns:1fr}.rl2-card.wide{grid-column:auto}.rl2-cols{grid-template-columns:1fr}.rl2-kpis{grid-template-columns:1fr 1fr}.rl2-eventgrid,.rl2-quality-grid{grid-template-columns:1fr}.rl2-title{font-size:18px}}"
    ].join("");
    document.head.appendChild(s);
  }

  function companyPath(sym){return BASE+"companies/"+encodeURIComponent(sym)+".json?lab="+Date.now();}
  function loadCompany(sym){
    sym=String(sym||"").trim().toUpperCase().replace(/[^A-Z0-9&_-]/g,"");
    if(!sym)return Promise.resolve(null);
    if(Q.cache[sym])return Promise.resolve(Q.cache[sym]);
    return fetch(companyPath(sym),{cache:"no-store"}).then(function(r){if(!r.ok)throw Error(sym);return r.json();}).then(function(x){Q.cache[sym]=x;return x;}).catch(function(){return null;});
  }

  function buildFingerprint(sym){
    var rows=((Q.radar.features||{}).momentum_dashboard||{}).roc_leaders||[];
    var r=rows.find(function(x){return String(x.symbol).toUpperCase()===sym;})||null;
    if(!r)return '<div class="rl2-empty">Symbol not found in the current research snapshot.</div>';
    return loadCompany(sym).then(function(c){
      var top=(c&&c.top)||{}, sector=(Q.companies&&Q.companies[sym])||{};
      var del=((Q.radar.features||{}).delivery_conviction||{}).high_delivery_up||[];
      var d=del.find(function(x){return String(x.symbol).toUpperCase()===sym;});
      var fo=((Q.radar.features||{}).fo_buildup||{}), foRow;
      ["long_build","short_build","short_cover","long_unwind"].some(function(k){foRow=(fo[k]||[]).find(function(x){return String(x.symbol).toUpperCase()===sym;});return !!foRow;});
      var h='<div class="rl2-kpis">'+
        '<div><small>20D RETURN</small><b class="'+cls(r.return_20d)+'">'+pct(r.return_20d)+'</b></div>'+
        '<div><small>RSI14</small><b>'+n(r.rsi14,0)+'</b></div>'+
        '<div><small>EMA200</small><b>'+n(r.ema200,1)+'</b></div>'+
        '<div><small>DELIVERY</small><b>'+n(d&&d.delivery_pct,1)+'%</b></div></div>';
      h+='<div class="rl2-cols"><div>'+
        row("Company",sector.name||sym)+row("Sector",sector.sector||"—")+row("Relative strength",pct(r.relative_strength_20d),cls(r.relative_strength_20d))+row("Vol / 20D",n(r.vol_vs_avg20,1)+"×")+
        '</div><div>'+
        row("P/E",top["Stock P/E"]||"—")+row("ROE",top["ROE"]||"—")+row("ROCE",top["ROCE"]||"—")+row("F&O build",foRow&&foRow.build||"—")+
        '</div></div>';
      h+='<div class="rl2-note">Fingerprint is a compact descriptive snapshot from free public/repository data. It does not rank or recommend the stock.</div>';
      return h;
    });
  }

  function mount(){
    if(document.getElementById("research-lab-v2"))return;
    var host=document.getElementById("research-radar");
    if(!host)return;
    var lab=(Q.radar||{}).research_lab||{};
    var wrapper=document.createElement("div");wrapper.id="research-lab-v2";
    wrapper.innerHTML=
      '<div class="rl2-banner"><div class="rl2-title">Research Lab · 10 New Evidence Tools</div>'+
      '<div class="rl2-sub">Free/public data · EOD snapshots · historical follow-through · no paid API</div>'+
      '<div class="rl2-status"><span>10 tools</span><span>'+n(lab.search_universe,0)+' stocks</span><span>'+n(lab.module_count,0)+' radar modules</span><span>GitHub Actions memory</span></div>'+
      '<div class="rl2-foot">The Lab extends Research Radar without changing the normal company/fundamentals views.</div></div>'+
      '<div class="rl2-grid">'+
      card("01","WHY TODAY?",whyToday(),"EVIDENCE CHAIN")+
      card("02","MARKET REPLAY",marketReplay(),"60 SNAPSHOTS")+
      card("03","SIGNAL FOLLOW-THROUGH",signalLab(),"HISTORICAL STUDY")+
      card("04","EVENT IMPACT LIBRARY",eventImpact(),"FILING CONTEXT")+
      card("05","REGIME TRANSITIONS",regimeTransitions(),"STATE CHANGES")+
      card("06","FALSE BREAKOUT RADAR",falseBreakouts(),"52W STUDY")+
      card("07","FILING CHANGE DETECTOR",filingChanges(),"LATEST VS PREVIOUS")+
      card("08","EARNINGS QUALITY RADAR",earningsQuality(),"ACCOUNTING LENS")+
      card("09","STOCK FINGERPRINT",fingerprint(),"SEARCH")+
      card("10","RESEARCH MEMORY",researchMemory(),"OWN HISTORY")+
      '</div>';
    host.appendChild(wrapper);

    var fpBtn=document.getElementById("rl2FpBtn"),fpInput=document.getElementById("rl2FpInput"),fpDetail=document.getElementById("rl2FpDetail");
    if(fpBtn)fpBtn.onclick=function(){var s=(fpInput&&fpInput.value||"").trim().toUpperCase();if(!s){fpDetail.innerHTML='<div class="rl2-empty">Enter a symbol first.</div>';return;}fpDetail.innerHTML='<div class="rl2-empty">Building fingerprint…</div>';Promise.resolve(buildFingerprint(s)).then(function(x){fpDetail.innerHTML=x||'<div class="rl2-empty">No fingerprint available.</div>';});};
  }

  function boot(){
    css();
    if(!document.getElementById("research-edge-script")){ var rs=document.createElement("script"); rs.id="research-edge-script"; rs.src="researchextensions.js?v=1"; document.body.appendChild(rs); }
    Promise.all([
      J("research-radar.json"),
      J("research-signal-history.json"),
      J("research-market-history.json"),
      J("filings.json"),
      J("company-index.json")
    ]).then(function(v){
      Q.radar=v[0]||{};Q.signal=v[1]||{};Q.market=v[2]||{};Q.filings=v[3]||{};Q.companies=v[4]||{};
      var ntry=0,iv=setInterval(function(){
        if(document.getElementById("research-radar")){mount();clearInterval(iv);}
        if(++ntry>80)clearInterval(iv);
      },250);
    }).catch(function(){});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
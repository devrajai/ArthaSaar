/* ==========================================================================
   Arthasaar — LIVE indices bridge
   Pulls the daily snapshot the repo already produces:
     data/indices-all.json  (every NSE index + BSE Sensex; refreshed after
                             market close by the brain-collect workflow)
     data/global.json       (global indices — used only for the Sensex fallback)
   Fills:
     - Home index KPI cards  (NIFTY 50 · SENSEX · BANK NIFTY · INDIA VIX)
     - Indices window        (full, scrollable list of every tracked index)
     - Indices Radar         (breadth + top gainers / losers)
   ========================================================================== */
(function () {
"use strict";

var SRC_IDX = "data/indices-all.json";
var SRC_GLOB = "data/global.json";

function el(id) { return document.getElementById(id); }
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function n2(v) {
  if (v == null || isNaN(v)) return "--";
  return Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function pctStr(v) {
  if (v == null || isNaN(v)) return "--";
  var n = Number(v);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}
function dirCls(v) { return Number(v) >= 0 ? "up" : "dn"; }
function arrow(v) { return Number(v) >= 0 ? "\u25B2" : "\u25BC"; }

function get(url) {
  return fetch(url + "?v=" + Date.now(), { cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .catch(function () { return null; });
}

function byName(L, name) {
  var i, up = String(name).toUpperCase();
  for (i = 0; i < L.length; i++) if (String(L[i].index || "").toUpperCase() === up) return L[i];
  for (i = 0; i < L.length; i++) if (String(L[i].index || "").toUpperCase().indexOf(up) > -1) return L[i];
  return null;
}
function pos52(r) {
  if (!r || !r.year_high || !r.year_low || r.year_high === r.year_low) return null;
  return Math.round((r.price - r.year_low) / (r.year_high - r.year_low) * 100);
}
function fmtUpdated(iso) {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString("en-IN",
      { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true });
  } catch (e) { return iso; }
}

/* ---------- home index KPI cards ---------- */
function paintHome(idx, glob) {
  var sensex = byName(idx, "SENSEX");
  if (!sensex && glob && glob.items) {
    for (var i = 0; i < glob.items.length; i++) {
      if (String(glob.items[i].name || "").toUpperCase().indexOf("SENSEX") > -1) {
        var g = glob.items[i];
        sensex = { index: "SENSEX", price: g.price, change_pct: g.chg_pct, change: null };
        break;
      }
    }
  }
  var map = [
    ["kpiNifty", byName(idx, "NIFTY 50")],
    ["kpiSensex", sensex],
    ["kpiBank", byName(idx, "NIFTY BANK")],
    ["kpiVix", byName(idx, "INDIA VIX")]
  ];
  map.forEach(function (p) {
    var card = el(p[0]); if (!card) return;
    var r = p[1];
    var num = card.querySelector(".num"), chg = card.querySelector(".chg");
    if (!r) { if (num) num.textContent = "--"; if (chg) { chg.className = "chg"; chg.textContent = "·"; } return; }
    if (num) num.textContent = n2(r.price);
    if (chg) {
      chg.className = "chg " + dirCls(r.change_pct);
      chg.textContent = arrow(r.change_pct) + " " + pctStr(r.change_pct) +
        (r.change != null ? " \u00b7 " + (r.change >= 0 ? "+" : "") + n2(r.change) : "");
    }
  });
}

/* ---------- Indices window: full scrollable list ---------- */
function paintIndices(data, glob) {
  var L = (data.indices || []).slice();
  var tb = el("idxBody"); if (!tb) return;
  var src = el("idxSource"), fresh = el("idxFresh");
  if (src) src.textContent = "NSE daily snapshot · " + (data.updated ? fmtUpdated(data.updated) : "timestamp unavailable");
  if (fresh) { fresh.textContent = "● DAILY SNAPSHOT"; fresh.className = "fresh"; }

  // add a BSE Sensex row (from global.json) if the snapshot doesn't carry one
  if (!byName(L, "SENSEX") && glob && glob.items) {
    for (var i = 0; i < glob.items.length; i++) {
      if (String(glob.items[i].name || "").toUpperCase().indexOf("SENSEX") > -1) {
        var g = glob.items[i];
        L.push({ index: "BSE SENSEX", price: g.price, change_pct: g.chg_pct,
                 year_high: g.high_52w, year_low: g.low_52w, pe: "", pb: "", source: "Yahoo" });
        break;
      }
    }
  }

  L.sort(function (a, b) { return String(a.index || "").localeCompare(String(b.index || "")); });

  tb.innerHTML = L.map(function (r) {
    var pos = pos52(r);
    return "<tr><td>" + esc(r.index) + "</td><td>" + n2(r.price) + "</td>" +
      "<td><span class='" + dirCls(r.change) + "'>" + (r.change == null ? "—" : (Number(r.change) >= 0 ? "+" : "") + n2(r.change)) + "</span></td>" +
      "<td><span class='" + dirCls(r.change_pct) + "'>" + pctStr(r.change_pct) + "</span></td>" +
      "<td>" + (pos == null ? "—" : pos + "%") + "</td>" +
      "<td>" + (r.pe || "—") + "</td><td>" + (r.pb || "—") + "</td></tr>";
  }).join("");

  var title = el("idxTitle");
  if (title) title.textContent = "Indices \u2014 " + L.length + " tracked";
}

/* ---------- Indices Radar ---------- */
function paintRadar(data) {
  var L = data.indices || [];
  if (!L.length) return;

  var box = el("radarCards");
  if (box) {
    box.innerHTML = ["NIFTY 50", "NIFTY BANK", "NIFTY NEXT 50"].map(function (nm) {
      var r = byName(L, nm); if (!r) return "";
      return '<div class="ridx"><div class="lbl">' + esc(r.index) + '</div><div class="val">' +
        n2(r.price) + '</div><div class="chg ' + dirCls(r.change_pct) + '">' + pctStr(r.change_pct) + '</div></div>';
    }).join("");
  }

  var up = 0, dn = 0, flat = 0;
  L.forEach(function (r) { var c = Number(r.change_pct); if (c > 0) up++; else if (c < 0) dn++; else flat++; });
  var total = L.length, upPct = total ? (up / total * 100) : 0;
  var br = el("radarBreadth");
  if (br) {
    br.innerHTML =
      '<div class="blab">' + up + '/' + total + ' GREEN</div>' +
      '<div class="rbar"><i style="width:' + upPct.toFixed(1) + '%"></i><em></em></div>' +
      '<div class="rcap">' + dn + ' red \u00b7 ' + flat + ' flat \u00b7 ' + fmtUpdated(data.updated) + '</div>';
  }

  var movers = L.filter(function (r) { return r.price != null && !isNaN(Number(r.change_pct)); });
  var sorted = movers.slice().sort(function (a, b) { return Number(b.change_pct) - Number(a.change_pct); });
  var g = el("radarGainers");
  if (g) g.innerHTML = sorted.slice(0, 6).map(function (r) {
    return '<span class="rchip g"><b>' + esc(r.index) + '</b> ' + pctStr(r.change_pct) + '</span>';
  }).join("");
  var lo = el("radarLosers");
  if (lo) lo.innerHTML = sorted.slice(-6).reverse().map(function (r) {
    return '<span class="rchip r"><b>' + esc(r.index) + '</b> ' + pctStr(r.change_pct) + '</span>';
  }).join("");
}

/* ---------- Sector Map: live sector/index rotation ---------- */
function sectorBucket(name) {
  var n = String(name || "").toUpperCase();
  var keys = [
    ["BANK","BANK"],["FINANCIAL","FIN SERV"],["IT","IT"],["AUTO","AUTO"],["PHARMA","PHARMA"],
    ["HEALTHCARE","HEALTHCARE"],["FMCG","FMCG"],["METAL","METAL"],["OIL & GAS","OIL & GAS"],
    ["ENERGY","ENERGY"],["REALTY","REALTY"],["INFRASTRUCTURE","INFRA"],["MEDIA","MEDIA"],
    ["CONSUMER DURABLES","CONS DUR"],["CHEMICAL","CHEMICALS"],["DEFENCE","DEFENCE"],
    ["TOURISM","TOURISM"],["CAPITAL MARKETS","CAPITAL MKT"],["MOBILITY","MOBILITY"],
    ["TRANSPORTATION","TRANSPORT"],["RAILWAYS","RAILWAYS"],["DIGITAL","DIGITAL"],
    ["MANUFACTURING","MANUFACTURING"],["CONSUMPTION","CONSUMPTION"]
  ];
  for (var i=0;i<keys.length;i++) if (n.indexOf(keys[i][0])>-1) return keys[i][1];
  return null;
}
function sectorClass(p) {
  p=Number(p)||0;
  if(p>=1.5)return "g3"; if(p>=0.5)return "g2"; if(p>0)return "g1";
  if(p<=-1.5)return "r3"; if(p<=-0.5)return "r2"; return "r1";
}
function sectorLabelKey(label) {
  return String(label || "").trim().toUpperCase();
}
function sectorRows(L, mode) {
  var rows = [];
  if (mode === "All Indices") {
    return L.filter(function(r){ return r && r.price != null && r.change_pct != null; })
      .map(function(r){ return { k: r.index, r: r, bucket: sectorBucket(r.index) }; })
      .sort(function(a,b){ return Number(b.r.change_pct)-Number(a.r.change_pct); });
  }
  if (mode !== "Sectors") {
    return L.filter(function(r){ return sectorBucket(r.index) === mode && r.price != null && r.change_pct != null; })
      .map(function(r){ return { k: r.index, r: r, bucket: mode }; })
      .sort(function(a,b){ return Number(b.r.change_pct)-Number(a.r.change_pct); });
  }
  var best = {};
  L.forEach(function(r){
    var b = sectorBucket(r.index);
    if(!b || r.change_pct == null || r.price == null) return;
    if(!best[b] || Math.abs(Number(r.change_pct)) > Math.abs(Number(best[b].change_pct))) best[b] = r;
  });
  return Object.keys(best).map(function(k){ return { k:k, r:best[k], bucket:k }; })
    .sort(function(a,b){ return Number(b.r.change_pct)-Number(a.r.change_pct); });
}
function paintSectorMap(data, mode) {
  var host=el("sectorMapGrid"), meta=el("sectorMeta"), radar=el("sectorRadar");
  if(!host)return;
  mode = mode || "Sectors";
  var L=data.indices||[], rows=sectorRows(L,mode);
  var title=el("sectorViewTitle");
  if(title) title.textContent = mode === "Sectors" ? "SECTORS" : mode.toUpperCase();
  host.innerHTML = rows.length ? rows.map(function(x){
    var p=Number(x.r.change_pct)||0, ch=Number(x.r.change)||0;
    var price = x.r.price == null ? "—" : Number(x.r.price).toLocaleString("en-IN",{maximumFractionDigits:2});
    var sym = x.r.symbol || x.r.index || "";
    var point = (ch>0?"+":"")+ch.toLocaleString("en-IN",{maximumFractionDigits:2});
    var sub = mode === "Sectors" ? "" : "<small>"+esc(sym)+"</small>";
    return '<div class="tcell '+sectorClass(p)+'" data-sector-card="'+esc(x.bucket||"")+'" title="'+esc(x.r.index)+'">'+
      '<b>'+esc(x.k)+'</b>'+sub+
      '<span class="'+dirCls(p)+'">'+pctStr(p)+'</span>'+
      '<div class="tp">PRICE · '+esc(price)+'</div>'+
      '<div class="tchg">DAY · '+esc(point)+'</div>'+
      '</div>';
  }).join("") : '<div class="idxload">No matching index data in this snapshot.</div>';
  var green=rows.filter(function(x){return Number(x.r.change_pct)>0;}).length;
  var red=rows.filter(function(x){return Number(x.r.change_pct)<0;}).length;
  if(meta) meta.textContent=rows.length+" shown · "+green+" green · "+red+" red · NSE snapshot "+fmtUpdated(data.updated);
  host.querySelectorAll("[data-sector-card]").forEach(function(card){
    card.addEventListener("click",function(){
      var target=card.getAttribute("data-sector-card");
      if(target) setSectorFilter(target);
    });
  });
  if(radar){
    var top=rows.slice().sort(function(a,b){
      return Math.abs(Number(b.r.change_pct))-Math.abs(Number(a.r.change_pct));
    }).slice(0,6);
    radar.innerHTML='<div class="sect" style="margin-top:0">SECTOR MAP RADAR · '+esc(mode)+'</div>'+
      '<div class="rchips">'+(top.length ? top.map(function(x){
        var p=Number(x.r.change_pct)||0;
        return '<button type="button" class="rchip '+(p>=0?'g':'r')+'" data-radar-sector="'+esc(x.bucket||"")+'"><b>'+esc(x.k)+'</b> '+pctStr(p)+'</button>';
      }).join("") : '<span class="mono" style="color:var(--faint);font-size:10px">No radar data for this filter.</span>')+'</div>'+
      '<div class="mono" style="margin-top:7px;color:var(--faint);font-size:9.5px">'+
      (mode==="Sectors" ? "Sector view · each tile represents the strongest-move tracked index in that sector." :
       mode==="All Indices" ? "All tracked indices · click a radar chip to filter into its sector." :
       "Filtered sector · constituent indices from the same NSE snapshot.")+
      '</div>';
    radar.querySelectorAll("[data-radar-sector]").forEach(function(btn){
      btn.addEventListener("click",function(){
        var target=btn.getAttribute("data-radar-sector");
        if(target) setSectorFilter(target);
      });
    });
  }
}
function setSectorFilter(mode) {
  var chips=document.querySelectorAll("#sectorFilters .fch2");
  chips.forEach(function(c){ c.classList.toggle("on", c.getAttribute("data-sector") === mode); });
  window.__arthaSectorMode = mode;
  if(window.__arthaSectorData) paintSectorMap(window.__arthaSectorData, mode);
}
function bindSectorFilters() {
  document.querySelectorAll("#sectorFilters .fch2").forEach(function(c){
    c.addEventListener("click",function(){
      setSectorFilter(c.getAttribute("data-sector") || c.textContent.trim());
    });
  });
}
function bindSectorRadarToggle() {
  var btn=el("sectorRadarToggle"), panel=el("sectorRadarPanel");
  if(!btn || !panel) return;
  btn.addEventListener("click",function(){
    var open=btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", open ? "false" : "true");
    panel.hidden=open;
  });
}

function fail() {
  var tb = el("idxBody");
  if (tb) tb.innerHTML = '<tr><td colspan="7" class="idxload">Live indices load nahi hue \u2014 data/indices-all.json check karo.</td></tr>';
}

function boot() {
  Promise.all([get(SRC_IDX), get(SRC_GLOB)]).then(function (res) {
    var idx = res[0], glob = res[1];
    if (!idx || !idx.indices || !idx.indices.length) { fail(); return; }
    paintHome(idx.indices, glob);
    paintIndices(idx, glob);
    paintRadar(idx);
    window.__arthaSectorData = idx;
    paintSectorMap(idx, window.__arthaSectorMode || "Sectors");
  });
}

function initLiveUI() {
  var refreshBtn = el("idxRefresh");
  if (refreshBtn) refreshBtn.addEventListener("click", boot);
  bindSectorFilters();
  bindSectorRadarToggle();
  boot();
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initLiveUI);
else initLiveUI();

})();

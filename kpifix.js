/* kpifix.js — home ke index cards me % ke saath POINTS bhi (user request 26 Sep)
   oldapp.js ke kpi() ko override karta hai — file oldapp ke turant baad load hota hai. */
function kpi(name, idx) {
  if (!idx) return "";
  var pt = (idx.change == null || isNaN(idx.change)) ? "" :
    (idx.change > 0 ? "+" : "") + Number(idx.change).toFixed(0) + " pts · ";
  return '<div class="kpi"><div class="k-name">' + esc(name) + '</div>' +
    '<div class="k-val">' + nf2(idx.price) + '</div>' +
    '<div class="k-chg ' + pctCls(idx.change_pct) + '">' + pt + sign(idx.change_pct) + "</div></div>";
}

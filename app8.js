/* ---------- TradingView charts ---------- */
let tvSym = "RELIANCE", tvIv = "D";
function tvSymbol(x) {
  x = (x || "").trim().toUpperCase();
  if (!x) return "NSE:RELIANCE";
  if (x.indexOf(":") !== -1) return x;
  if (/^(NIFTY|BANKNIFTY|MIDCPNIFTY|FINNIFTY|NIFTYNXT50)$/.test(x)) return "NSE:" + x;
  if (/^^SENSEX|BANKEX)$/.test(x)) return "BSE:" + x;
  if (/^^BTC|ETH|SOL|XRP|BNB|DOGE|ADA)$/.test(x)) return "BINANCE:" + x + "USDT";
  if (x === "GOLD") return "MCX:GOLD1!";
  return "NSE:" + x;
}
function renderCharts() {
  const ivs = [["1", "1 min"], ["5", "5 min"], ["15", "15 min"], ["60", "1 hour"], ["D", "Daily"]];
  $("#chIv").innerHTML = ivs.map((v) =>
    '<button class="chip' + (tvIv === v[0] ? " on" : "") + '" data-iv="' + v[0] + '">' + v[1] + "</button>").join("");
  $("#chIv").querySelectorAll(".chip").forEach((b) =>
    b.onclick = () => { tvIv = b.getAttribute("data-iv"); renderCharts(); });
  const draw = () => {
    tvSym = $("#chSym").value.trim() || tvSym;
    const full = tvSymbol(tvSym);
    $("#tvBox").innerHTML = '<div id="tvchart" style="height:430px;border-radius:12px;overflow:hidden"></div>' +
      '<div class="footer-note" style="margin-top:6px">showing ' + esc(full) + " · interval " +
      (ivs.find((v) => v[0] === tvIv) || ["", tvIv][1] + "</div>";
    const mk = () => {
      if (!window.TradingView || !window.TradingView.widget) return false;
      new window.TradingView.widget({
        symbol: full, interval: tvIv,
        theme: document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark",
        style: "1", locale: "en", timezone: "Asia/Kolkata",
        container_id: "tvchart", autosize: true,
        hide_side_toolbar: true, allow_symbol_change: false,
      });
      return true;
    };
    if (!mk()) {
      const s = document.createElement("script");
      s.src = "https://s3.tradingview.com/tv.js";
      s.onload = () => setTimeout(mk, 60);
      s.onerror = () => { $("#tvBox").innerHTML = '<div class="note">chart could not load — check internet and tap Load again</div>'; };
      document.head.appendChild(s);
    }
  };
  draw();
  $("#chGo").onclick = () => { tvSym = $("#chSym").value.trim(); draw(); };
  $("#chSym").onkeydown = (e) => { if (e.key === "Enter") draw(); };
}


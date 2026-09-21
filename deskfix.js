/* deskfix.js — desktop layout: wider, calmer, more columns (mobile unchanged) */
(function () {
  var st = document.createElement("style");
  st.textContent =
    "@media(min-width:900px){" +
    ".wrap{padding:0 28px}" +
    "header{padding:26px 0 14px}" +
    ".logo{width:46px;height:46px;border-radius:14px;font-size:17px}" +
    "h1{font-size:21px}" +
    ".tagline{font-size:12px}" +
    ".clockbox{font-size:13px}" +
    ".meta-row{font-size:11.5px}" +
    "h2{font-size:16px}" +
    ".homegrid{grid-template-columns:repeat(5,1fr);gap:14px}" +
    ".tile{padding:18px 14px}" +
    ".t-ic{font-size:28px}" +
    ".t-nm{font-size:14px}" +
    ".t-sb{font-size:11px}" +
    ".card{padding:18px 20px;border-radius:20px}" +
    "table{font-size:13px}" +
    ".controls{gap:10px}" +
    "#tvBox iframe{height:600px}" +
    ".backbtn{font-size:13px;padding:8px 18px}" +
    "}" +
    "@media(min-width:1250px){.homegrid{grid-template-columns:repeat(6,1fr)}}";
  document.head.appendChild(st);
})();

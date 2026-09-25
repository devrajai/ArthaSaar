/* news.js - DAILY AUTHENTIC NEWS card (sirf sach, no masala): cross-verified stories
   + MARKET X-RAY (Nifty OHLC pattern + FII/DII Puppato). section#news, News Volume ke niche. */
(function () {
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }

  function xrayBlock(x) {
    if (!x || !x.c) return '';
    var green = x.chg >= 0;
    var fiiPos = (x.fii || 0) >= 0;
    var diiPos = (x.dii || 0) >= 0;
    var h = '<div style="margin-top:10px;padding:8px 12px;border-radius:10px;background:rgba(96,165,250,.08);border:1px solid rgba(96,165,250,.3)">' +
      '<div style="font-size:13px;font-weight:700">\uD83E\uDE7C MARKET X-RAY <span style="font-size:10px;opacity:.6;font-weight:400">(aaj ka asli game)</span></div>' +
      '<div style="margin-top:5px;font-size:12.5px">NIFTY <b style="color:' + (green ? '#77f37b' : '#ff8b8b') + '">' + esc(x.c) + ' (' + (green ? '+' : '') + esc(x.chg) + '%)</b>' +
      ' \u00b7 O ' + esc(x.o) + ' | H ' + esc(x.h) + ' | L ' + esc(x.l) + '</div>';
    if (x.pattern) {
      h += '<div style="margin-top:4px;font-size:12px;opacity:.85">\uD83D\uDCCD Pattern: <b>' + esc(x.pattern) + '</b></div>';
    }
    h += '<div style="margin-top:4px;font-size:12px">\uD83D\uDCB8 FII: <b style="color:' + (fiiPos ? '#77f37b' : '#ff8b8b') + '">' + (fiiPos ? 'Buy ' : 'Sell ') + '\u20B9' + esc(Math.abs(x.fii)) + ' Cr</b>' +
      ' | DII: <b style="color:' + (diiPos ? '#77f37b' : '#ff8b8b') + '">' + (diiPos ? 'Buy ' : 'Sell ') + '\u20B9' + esc(Math.abs(x.dii)) + ' Cr</b></div>';
    if (x.fii_streak >= 3) {
      h += '<div style="margin-top:4px;font-size:11.5px;opacity:.75">\uD83D\uDCED FII ne lagatar ' + esc(x.fii_streak) + ' din becha hai' + (x.puppato ? ' - par DII sara maal le raha hai (Puppato)' : '') + '</div>';
    } else if (x.puppato) {
      h += '<div style="margin-top:4px;font-size:11.5px;opacity:.75">\uD83D\uDCED Puppato: FII beche, DII utha raha hai (public ka paisa)</div>';
    }
    return h + '</div>';
  }

  function storyRow(s) {
    var verified = s.x && s.n >= 2;
    var badge = verified
      ? '<span style="font-size:10px;font-weight:700;color:#77f37b;border:1px solid rgba(119,243,123,.4);border-radius:6px;padding:1px 6px;margin-left:6px">\u2713 ' + esc(s.n) + ' outlets</span>'
      : '<span style="font-size:10px;font-weight:700;color:rgba(240,180,41,.9);border:1px solid rgba(240,180,41,.4);border-radius:6px;padding:1px 6px;margin-left:6px">wire</span>';
    return '<div style="font-size:12.5px;line-height:1.5;margin-top:7px;padding:7px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03)">' +
      esc(s.t) + badge +
      '<div style="font-size:11px;opacity:.6;margin-top:2px">' + esc((s.srcs || []).join(' + ')) + ' \u00b7 ' + esc(s.age) + 'h pehle</div></div>';
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(119,243,123,.10);border:1px solid rgba(119,243,123,.45);font-size:14.5px;text-align:center"><b style="color:rgba(150,240,150,.95)">\uD83D\uDCF0 DAILY AUTHENTIC NEWS</b></summary>' +
      '<div id="dgBody" class="note" style="margin-top:8px"></div>';
    fetch('data/news-digest.json').then(function (r) { return r.json(); }).then(function (d) {
      var b = document.getElementById('dgBody');
      var h = '<div class="note" style="margin-top:8px">' + esc(d.u) + ' \u00b7 9 PM daily \u00b7 Google News RSS (free)</div>';
      h += xrayBlock(d.xray);
      (d.cats || []).forEach(function (c) {
        if (!c.stories || !c.stories.length) return;
        h += '<div style="font-size:12px;font-weight:700;margin-top:12px;opacity:.85">' + esc(c.name) + '</div>';
        c.stories.forEach(function (s) { h += storyRow(s); });
      });
      h += '<div style="margin-top:10px;padding:8px 12px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1)">' +
        '<div style="font-size:11px;line-height:1.6;opacity:.75">\u2713 <b>outlets</b> = kitne alag news houses ne same khabar publish ki (2+ = verified). <b>wire</b> = Reuters/Bloomberg direct.' +
        '<br>TV wala sensational masala EXCLUDED - sirf cross-checked data. khud verify karo: news hai, tip nahi.</div></div>';
      b.innerHTML = h;
    }).catch(function () {
      var b = document.getElementById('dgBody');
      if (b) b.innerHTML = 'data load nahi hua - thodi der baad try karo';
    });
  }

  function mount() {
    var sec = document.querySelector('section#news');
    if (!sec || document.getElementById('mbNewsDigest')) return;
    var c = document.createElement('details');
    c.className = 'card'; c.id = 'mbNewsDigest'; c.style.marginTop = '14px';
    var nb = document.getElementById('newsBox');
    if (nb) sec.insertBefore(c, nb); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();

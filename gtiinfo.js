/* gtiinfo.js - GTI Complete Guide: sab GTI info ek jagah (Learn + GTI section) */
(function () {
  function esc(s) { return String(s == null ? "").replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function build(id) {
    var d = document.createElement("details");
    d.className = "gl"; d.id = id; d.style.marginTop = "12px";
    var items = [
      ["ICT Beginner Guide \u2014 CHOCH / BOS / Order Block / FVG simple bhasha me",
       'Naye <b>ICT Terminal</b> (GTI section me sabse upar chart) ke tools \u2014 beginner ke liye ekdum seedha:<br><br>' +
       '<b style="color:#ffd54d">CHOCH = Change of Character</b> (character badal gaya) \u2014 market ka MOOD switch ho gaya. Ab tak upar ja raha tha, ab neeche jaayega (ya ulta). Chart pe yellow arrow = pehla reversal signal. Sabse important marker.<br><br>' +
       '<b style="color:#34d399">BOS = Break of Structure</b> (structure toda) \u2014 trend waise hi chal raha hai, bas naya high/low bana diya. Trend CONTINUE hone ki confirmation. Green/red arrow.<br><br>' +
       '<b style="color:#f87171">PDH / PDL = Previous Day High / Low</b> \u2014 kal ka highest/lowest point, aaj ki deewar. PDH ke UPAR gaya = buyers strong, PDL ke NEECHE gira = sellers strong. Rule: in lines ke PAAS mat trade karo, break ke BAAD karo.<br><br>' +
       '<b style="color:#fbbf24">Weekly / Monthly H/L</b> \u2014 same deewar, lekin badi. Jitna bada level, utna tagdi deewar \u2014 bade moves yahin se aate/rukte hain.<br><br>' +
       '<b style="color:#60a5fa">ASIA box</b> \u2014 raat 9:15 se subah 6:30 tak ka range (Japan/China). Aksar sidha-sadha chalta hai.<br>' +
       '<b style="color:#34d399">LDN KZ (London Kill Zone, 12:30\u201315:30 IST)</b> \u2014 London khulte hi Asia ka range aksar TOD deta hai, bada move aata hai.<br>' +
       '<b style="color:#ffb84d">NY KZ (New York Kill Zone, 17:30\u201320:30 IST)</b> \u2014 America, sabse tez vol; London ka direction continue karta hai ya reversal deta hai.<br>' +
       'Tip: London/NY ke moves serious hote hain, Asia ke aksar trap. (Asia box + NY KZ sirf 24h market jaise BTC pe poore dikhte hain \u2014 NSE raat ko band rehta hai.)<br><br>' +
       '<b style="color:#4da3ff">Order Block (OB)</b> \u2014 bade players (banks/institutions) ka footprint: jahan unhone saari kharidi/bechi wali last ulta candle. Price wapas is box me aaye to wahan se FIR wahi direction me move. Neela OB\u2191 = neeche support, orange OB\u2193 = upar resistance. Entry points yahin se milte hain.<br><br>' +
       '<b style="color:#34d399">FVG = Fair Value Gap</b> \u2014 teen candles ke beech ka khali area. Price ne itni tezi se jump maara ki beech ka gap reh gaya (lift ne floor skip kar diya). Market ka nature: har gap WAPAS bharne aata hai \u2014 gap ke paas price ruk/reverse sakta hai.<br><br>' +
       '<b>Beginner ka sequence:</b> (1) CHOCH se trend dekho (2) OB/FVG zone ka wait karo (3) PDH/PDL level se confirm karo (4) London/NY time me hi trade socho. Aur yaad rakho \u2014 ye READ hai, guarantee nahi. Har trade me SL rakhna hi hai.'],
      ["Zones - SD / WD / WS / SS (GTI ka core)",
       '<b style="color:#77f37b">SD (Strong Demand)</b> = din/hafta ke open se sabse door neeche wala TAGDA support - price yahan aaye to <b>best buying</b><br><br>' +
       '<b style="color:#77f37b">WD (Weak Demand)</b> = open ke paas wala halka support<br><br>' +
       '<b style="color:#ff8b8b">WS (Weak Supply)</b> = upar halka resistance<br><br>' +
       '<b style="color:#ff8b8b">SS (Strong Supply)</b> = sabse upar tagda resistance - <b>selling zone</b><br><br>' +
       'Manish ka rule: <b>buying zone mein sirf BUY, selling mein sirf SELL, target = opposite zone</b> (zone-to-zone trade). SL = zone ke paar 3-min candle CLOSE (wick nahi).'],
      ["POC aur Golden Line",
       '<b style="color:#1E90FF">POC</b> = Point of Control - pichle din/hafte jahan sabse zyada business hua (H+L+C/3) - <b>magnet level</b>, price wapas isko khinchta hai.<br><br>' +
       '<b style="color:#ffd54d">Golden Line</b> = weekly POC. Price iske UPAR = weekly bullish, NEECHE = weekly bearish. POC break sequence = bada move aane ka signal.'],
      ["Compression Detection",
       'Jab <b>day POC aur week POC bilkul paas</b> ho (price se < 0.15% aur aapas mein < 0.2%), market compressed hai. Tab <b>zones kaam nahi karte</b> - levels (grid, POC, Gann) par trade karo. Blast expected: Nifty min <b>200-300 pts</b>, BankNifty min <b>1000 pts</b>. Website pe orange COMPRESSION badge dikhta hai.'],
      ["300-Point Grid",
       'Bade players (operators) apne levels 300 ke multiple par banate hain (25200, 25500, 25800...). Nifty in levels ka <b>magnet</b> hai - breakout ya reversal inhi par hota hai. Website pe har symbol ke saath nearest grid level dikhta hai.'],
      ["Gann Levels (50% + Fibonacci)",
       'W.D. Gann ka sabse solid concept: <b>50% retracement</b> (Manish bhi institutional candle ka 50% use karta hai). Aaj ke range ka midpoint = reversal zone. Fib 38.2% aur 61.8% bhi support/resistance dete hain. Gann angles/astro par mat jao - sirf 50% + time cycles kaam ke hain.'],
      ["Candles - colors ka matlab",
       '<b style="color:#4da3ff">Blue</b> = badi KHARIDI (institutional bullish)<br>' +
       '<b style="color:#bbb">Black</b> = badi BECHDI (institutional bearish)<br>' +
       '<b style="color:#ffd54d">Yellow</b> = operator candle - agle 1.5 ghante trade MAT karo, phir range ka breakout<br>' +
       '<b>Doji</b> = whale invitation (hunting mode - bada move aa raha hai)<br>' +
       '<b>Weak pinbar</b> = trap possible<br>' +
       '<b>No candle (gap)</b> = anomaly, sambhal ke<br><br>' +
       'Candle ka COLOR nahi - <b>STRUCTURE</b> dekho (body vs wick, kahan bana, kahan close hua).'],
      ["Operator hierarchy",
       '<b>Whale</b> (sabse bada, market banata hai) > <b>Shark</b> (trend banata hai) > <b>Stag</b> (buzz banata hai) > <b>Pig</b> (retail - maar khata hai). Hum Pig nahi banenge - whale ke saath chalenge.'],
      ["Probability ladder (confirmations)",
       '1 confirmation = 20% se kam &middot; <b>3 = ~70%</b> &middot; <b>4 = 78%+</b> &middot; <b>5-6 = 98% tak</b>. Stack: GTI zones (4H+D+W) + whale pattern + institutional activity + RS + compression breakout + first-candle break. Kam confirmations = trade MAT karo.'],
      ["Entry + capital rules (Manish)",
       'Entry: <b>pehli 3-min candle ka HIGH break</b> = BUY, LOW break = SELL.<br>Capital: ~35k account, <b>10% per trade</b> max risk.<br>Minimum capture: <b>25 pts</b> (Nifty). Maximum SL: <b>35 pts</b>.<br>Trap zones: gap-up opening, news-based spike, amavasya/panchak din - inme entry mat lo.'],
      ["Panchak calendar 2026",
       '<b>3 Oct</b> (Panchak) &middot; <b>21 Oct</b> (Amavasya) &middot; <b>20 Nov</b> (Amavasya) &middot; <b>27 Nov - 1 Dec</b> (Panchak) &middot; <b>19 Dec</b> (Amavasya + Panchak).<br><br>Manish: panchak mein correction aata hai (~75% cases) - bottom par up-correction, top par ~500-pt fall. Telegram par automatic reminder aayega (2 din pehle + roz). Ye sirf POINTER hai - final decision price action + zones se.'],
      ["Chart pe har color ka matlab (v5.1)",
       '<b style="color:#77f37b">HARA band (Strong Demand)</b> = SD - sabse tagda buying zone. Price yahan aaye to LONG dekho.<br>' +
       '<b style="color:#21c9f3">NEELA band (Demand Zone)</b> = WD - open ke paas halka support.<br>' +
       '<b style="color:#ffb84d">ORANGE band (Supply Zone)</b> = WS - halka resistance.<br>' +
       '<b style="color:#ff8b8b">LAAL band (Strong Supply)</b> = SS - tagda selling zone. Price yahan aaye to SHORT dekho.<br><br>' +
       '<b style="color:#1E90FF">NEELI moti line</b> = POC - magnet level, price isko khinchta hai.<br>' +
       '<b style="color:#DAA520">GOLDEN line</b> = Weekly POC - iske upar weekly bullish, neeche bearish. Sabse important line!<br>' +
       '<b style="color:#ffd54d">Yellow EMA 200</b> = trend filter - iske upar sirf BUY side, neeche sirf SELL side.<br>' +
       '<b>Blue VWAP</b> = intraday fair value - iske upar buyers strong.<br><br>' +
       '<b>Candles:</b> Normal green/red = aam candle. <b style="color:#ffd54d">PEELA candle</b> = operator candle - 1.5 ghante NO TRADE. <b>Safed candle</b> = anomaly/data spike - ignore.<br>' +
       '<b style="color:#4da3ff">Lime line</b> = pehli candle ka HIGH (break = BUY entry). <b style="color:#ff6b6b">Red line</b> = pehli candle ka LOW (break = SELL entry).<br>' +
       '<b style="color:#ffa940">Orange line + dots</b> = Gann 50% + Fib 38.2/61.8 - reversal zone.<br>' +
       '<b>Orange background</b> = COMPRESSION - zones band, levels khologe to blast.<br>' +
       '<b>Top-right table</b> = 10-row dashboard (trend, RSI, POC, compression, operator, golden line, Gann) - ek nazar mein sab.'],

      ["GTI se step-by-step trade (Manish workflow)",
       '<b>Step 1 - Direction:</b> EMA200 ke upar ho + price golden line (weekly POC) ke upar ho = BUY side only. Ulta = SELL side only. Dono mix mat karo.<br><br>' +
       '<b>Step 2 - Zone ka wait karo:</b> Price hara (SD) band mein aaye = buying setup. Laal (SS) band mein = selling setup. Beech mein bhatak raha ho to trade MAT karo.<br><br>' +
       '<b>Step 3 - Confirmations gino:</b> (1) zone touch (2) weekly direction sahi (3) EMA200 side sahi (4) whale/doji label dikhe (5) compression breakout. 3 = 70% prob, 4 = 78%, 5-6 = 98%. 2 ya kam = NO trade.<br><br>' +
       '<b>Step 4 - Entry:</b> Zone ke andar pehli 3-min candle ka HIGH break = BUY. LOW break = SELL.<br><br>' +
       '<b>Step 5 - SL aur target:</b> SL = zone ke paar 3-min candle close, max 35 pts. Target = opposite zone (zone-to-zone). Minimum capture 25 pts. Risk per trade = capital ka 10% max.<br><br>' +
       '<b>NO-TRADE conditions:</b> Peela operator candle ke 1.5 ghante, belan/mother candle (sideways), panchak/amavasya din, gap-up opening pe entry mat lo, white anomaly candle ignore karo.<br><br>' +
       '<b>Algo:</b> Compression hui hai (orange background)? To zones kaam nahi karte - tab POC, 300-grid aur Gann levels par trade karo, breakout ka wait karo (Nifty 200-300 pts blast).'],

      ["TradingView indicator",
       'GTI <b>v5 Final Full Edition</b> file ready hai - zones (6 timeframes), POC, VWAP, EMA200, RSI labels, compression, 300-grid, Gann levels, first-candle lines, golden line, operator/doji labels, trade plan dashboard + 20 alerts. Pine Editor mein paste karo.']
    ];
    var h = '<summary><b>GTI Complete Guide</b> - ICT (CHOCH/BOS/OB/FVG), zones, POC, candles, sab kuch</summary><div style="padding:4px 2px">';
    for (var i = 0; i < items.length; i++) {
      h += '<details class="gl" style="margin-top:8px"><summary>' + esc(items[i][0]) + '</summary><div style="padding:6px 2px;font-size:13px;line-height:1.7">' + items[i][1] + '</div></details>';
    }
    h += '</div>';
    d.innerHTML = h;
    return d;
  }
  function mount() {
    var learn = document.querySelector("section#learn");
    if (learn && !document.getElementById("gtiGuideL")) {
      var m = learn.querySelector("#manishCard");
      var c1 = build("gtiGuideL");
      if (m && m.nextSibling) learn.insertBefore(c1, m.nextSibling);
      else learn.appendChild(c1);
    }
    var gsec = document.querySelector("#gtiMount");
    if (gsec && !document.getElementById("gtiGuideG")) {
      gsec.appendChild(build("gtiGuideG"));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();

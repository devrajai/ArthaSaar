#!/usr/bin/env python3
"""fix_gti4.py - GTI Guide card mein 2 naye topics: har color ka matlab (v5.1)
+ step-by-step trading workflow. gtiinfo.js edit karta hai."""

ITEM_COLORS = r'''      ["Chart pe har color ka matlab (v5.1)",
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

'''

ITEM_WORKFLOW = r'''      ["GTI se step-by-step trade (Manish workflow)",
       '<b>Step 1 - Direction:</b> EMA200 ke upar ho + price golden line (weekly POC) ke upar ho = BUY side only. Ulta = SELL side only. Dono mix mat karo.<br><br>' +
       '<b>Step 2 - Zone ka wait karo:</b> Price hara (SD) band mein aaye = buying setup. Laal (SS) band mein = selling setup. Beech mein bhatak raha ho to trade MAT karo.<br><br>' +
       '<b>Step 3 - Confirmations gino:</b> (1) zone touch (2) weekly direction sahi (3) EMA200 side sahi (4) whale/doji label dikhe (5) compression breakout. 3 = 70% prob, 4 = 78%, 5-6 = 98%. 2 ya kam = NO trade.<br><br>' +
       '<b>Step 4 - Entry:</b> Zone ke andar pehli 3-min candle ka HIGH break = BUY. LOW break = SELL.<br><br>' +
       '<b>Step 5 - SL aur target:</b> SL = zone ke paar 3-min candle close, max 35 pts. Target = opposite zone (zone-to-zone). Minimum capture 25 pts. Risk per trade = capital ka 10% max.<br><br>' +
       '<b>NO-TRADE conditions:</b> Peela operator candle ke 1.5 ghante, belan/mother candle (sideways), panchak/amavasya din, gap-up opening pe entry mat lo, white anomaly candle ignore karo.<br><br>' +
       '<b>Algo:</b> Compression hui hai (orange background)? To zones kaam nahi karte - tab POC, 300-grid aur Gann levels par trade karo, breakout ka wait karo (Nifty 200-300 pts blast).'],

'''

def main():
    src = open("gtiinfo.js", encoding="utf-8").read()
    if "har color ka matlab" in src:
        print("already applied"); return
    anchor = '      ["TradingView indicator",'
    assert anchor in src, "anchor missing"
    src = src.replace(anchor, ITEM_COLORS + ITEM_WORKFLOW + anchor)
    open("gtiinfo.js", "w", encoding="utf-8").write(src)
    print("gtiinfo.js: 2 new guide topics added (colors + workflow)")

if __name__ == "__main__":
    main()
